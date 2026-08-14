#!/usr/bin/env python3
"""Report supported Codex account usage without reading thread content.

The reporter talks only to documented, read-only ``codex app-server`` JSON-RPC
methods. It never requests thread history, opens Codex databases or rollout
JSONL, or reads auth files, prompts, responses, thread previews, or tool items.
"""

from __future__ import annotations

import argparse
import json
import queue
import shutil
import subprocess
import sys
import threading
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, TextIO


class ProtocolError(RuntimeError):
    """Raised when app-server returns an error or malformed response."""


class JsonRpcClient:
    def __init__(self, codex_bin: str, timeout: float = 20.0) -> None:
        self.timeout = timeout
        self.next_id = 1
        self.responses: queue.Queue[dict[str, Any] | BaseException] = queue.Queue()
        self.process = subprocess.Popen(
            [codex_bin, "app-server", "--listen", "stdio://"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )
        assert self.process.stdin is not None
        assert self.process.stdout is not None
        assert self.process.stderr is not None
        self.stdin: TextIO = self.process.stdin
        self.reader = threading.Thread(target=self._read_stdout, daemon=True)
        self.stderr_reader = threading.Thread(
            target=self._discard_stderr, args=(self.process.stderr,), daemon=True
        )
        self.reader.start()
        self.stderr_reader.start()

    def _read_stdout(self) -> None:
        assert self.process.stdout is not None
        try:
            for line in self.process.stdout:
                try:
                    message = json.loads(line)
                except json.JSONDecodeError as exc:
                    self.responses.put(ProtocolError(f"invalid JSON-RPC line: {exc}"))
                    continue
                if "id" in message:
                    self.responses.put(message)
        except BaseException as exc:  # pragma: no cover - defensive transport path
            self.responses.put(exc)

    @staticmethod
    def _discard_stderr(stream: TextIO) -> None:
        for _line in stream:
            pass

    def send(self, message: dict[str, Any]) -> None:
        self.stdin.write(json.dumps(message, separators=(",", ":")) + "\n")
        self.stdin.flush()

    def request(self, method: str, params: Any = None) -> Any:
        request_id = self.next_id
        self.next_id += 1
        message: dict[str, Any] = {"method": method, "id": request_id}
        if params is not None:
            message["params"] = params
        self.send(message)
        deferred: list[dict[str, Any]] = []
        try:
            while True:
                try:
                    response = self.responses.get(timeout=self.timeout)
                except queue.Empty as exc:
                    raise ProtocolError(f"timeout waiting for {method}") from exc
                if isinstance(response, BaseException):
                    raise ProtocolError(str(response))
                if response.get("id") != request_id:
                    deferred.append(response)
                    continue
                if response.get("error") is not None:
                    raise ProtocolError(f"{method}: {response['error']}")
                return response.get("result")
        finally:
            for response in deferred:
                self.responses.put(response)

    def initialize(self) -> dict[str, Any]:
        result = self.request(
            "initialize",
            {
                "clientInfo": {
                    "name": "codex_usage_report",
                    "title": "Codex Usage Report",
                    "version": "0.1.0",
                },
                "capabilities": {"experimentalApi": True},
            },
        )
        self.send({"method": "initialized", "params": {}})
        return result

    def close(self) -> None:
        try:
            self.stdin.close()
        finally:
            try:
                self.process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.process.terminate()
                try:
                    self.process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    self.process.kill()
                    self.process.wait(timeout=2)


def filtered_daily_buckets(
    buckets: list[dict[str, Any]] | None, since_date: str
) -> list[dict[str, Any]] | None:
    if buckets is None:
        return None
    return [bucket for bucket in buckets if bucket.get("startDate", "") >= since_date]


@dataclass(frozen=True)
class ReportOptions:
    days: int
    comparison_days: int


def build_report(client: JsonRpcClient, options: ReportOptions) -> dict[str, Any]:
    initialized = client.initialize()
    now = datetime.now(timezone.utc)
    history_since = (now - timedelta(days=options.days + options.comparison_days)).date()

    usage = client.request("account/usage/read")
    rate_limits = client.request("account/rateLimits/read")

    usage = dict(usage)
    usage["dailyUsageBuckets"] = filtered_daily_buckets(
        usage.get("dailyUsageBuckets"), history_since.isoformat()
    )
    return {
        "schemaVersion": 1,
        "generatedAt": now.isoformat(),
        "window": {
            "recentDays": options.days,
            "comparisonDays": options.comparison_days,
            "dailyBucketsSince": history_since.isoformat(),
        },
        "source": {
            "interface": "codex app-server JSON-RPC",
            "methods": [
                "account/usage/read",
                "account/rateLimits/read",
            ],
            "userAgent": initialized.get("userAgent"),
        },
        "accountUsage": usage,
        "rateLimits": rate_limits,
        "limitations": [
            "Account token activity is aggregated by day, not attributed to threads, models, tools, or repositories.",
            "The reporter deliberately does not request task metadata because current task responses include content-bearing preview fields.",
            "Task lineage, duration, model/reasoning, tool calls, polling, retries, and historical cache behavior require a separate forward collector.",
        ],
    }


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--comparison-days", type=int, default=30)
    parser.add_argument("--codex-bin", default=shutil.which("codex") or "codex")
    parser.add_argument("--timeout", type=float, default=20.0)
    args = parser.parse_args(argv)
    if args.days <= 0 or args.comparison_days < 0:
        parser.error("days must be positive and comparison-days non-negative")
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    client = JsonRpcClient(args.codex_bin, timeout=args.timeout)
    try:
        report = build_report(
            client,
            ReportOptions(
                days=args.days,
                comparison_days=args.comparison_days,
            ),
        )
    finally:
        client.close()
    json.dump(report, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

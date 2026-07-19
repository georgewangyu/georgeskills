#!/usr/bin/env python3
"""Local-first, pauseable macOS screen-activity capture.

Raw images are written only to the caller-configured archive root. Small runtime
state may be written to a separate private state directory. No network or model
calls are made by this script.
"""

from __future__ import annotations

import argparse
import fcntl
import json
import math
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


OPENAI_VISION_DOCS = "https://developers.openai.com/api/docs/guides/images-vision"
DEFAULT_EXCLUDED_APPS = {
    "1Password",
    "Keychain Access",
    "Passwords",
    "SecurityAgent",
    "loginwindow",
}


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def local_now() -> datetime:
    return datetime.now().astimezone()


def isoformat(value: datetime) -> str:
    return value.isoformat(timespec="seconds")


def atomic_write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(str(temporary), str(path))


def append_jsonl(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True) + "\n")


def run_command(args: Sequence[str], timeout: int = 30) -> subprocess.CompletedProcess:
    return subprocess.run(
        list(args),
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


def slugify(value: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip()).strip("-._")
    return normalized[:48] or "unknown"


def load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"Config must be a JSON object: {path}")
    return value


@dataclass(frozen=True)
class Config:
    archive_root: Path
    state_root: Path
    interval_seconds: int = 30
    retention_days: int = 7
    max_width: int = 1600
    jpeg_quality: int = 55
    idle_skip_seconds: int = 900
    capture_cursor: bool = True
    contact_sheet_minutes: int = 10
    contact_sheet_columns: int = 5
    contact_sheet_thumb_width: int = 320
    contact_sheet_thumb_height: int = 180
    excluded_apps: Tuple[str, ...] = tuple(sorted(DEFAULT_EXCLUDED_APPS))
    require_external_archive: bool = True

    @classmethod
    def from_path(cls, path: Path) -> "Config":
        raw = load_json(path)
        required = ("archive_root", "state_root")
        missing = [key for key in required if not raw.get(key)]
        if missing:
            raise ValueError(f"Missing config fields: {', '.join(missing)}")
        config = cls(
            archive_root=Path(str(raw["archive_root"])).expanduser(),
            state_root=Path(str(raw["state_root"])).expanduser(),
            interval_seconds=int(raw.get("interval_seconds", 30)),
            retention_days=int(raw.get("retention_days", 7)),
            max_width=int(raw.get("max_width", 1600)),
            jpeg_quality=int(raw.get("jpeg_quality", 55)),
            idle_skip_seconds=int(raw.get("idle_skip_seconds", 900)),
            capture_cursor=bool(raw.get("capture_cursor", True)),
            contact_sheet_minutes=int(raw.get("contact_sheet_minutes", 10)),
            contact_sheet_columns=int(raw.get("contact_sheet_columns", 5)),
            contact_sheet_thumb_width=int(raw.get("contact_sheet_thumb_width", 320)),
            contact_sheet_thumb_height=int(raw.get("contact_sheet_thumb_height", 180)),
            excluded_apps=tuple(
                str(item) for item in raw.get("excluded_apps", sorted(DEFAULT_EXCLUDED_APPS))
            ),
        )
        config.validate()
        return config

    def validate(self) -> None:
        if self.interval_seconds < 10:
            raise ValueError("interval_seconds must be at least 10")
        if not 1 <= self.retention_days <= 30:
            raise ValueError("retention_days must be between 1 and 30")
        if not 640 <= self.max_width <= 3840:
            raise ValueError("max_width must be between 640 and 3840")
        if not 1 <= self.jpeg_quality <= 100:
            raise ValueError("jpeg_quality must be between 1 and 100")
        if self.idle_skip_seconds < 60:
            raise ValueError("idle_skip_seconds must be at least 60")
        if not 5 <= self.contact_sheet_minutes <= 60:
            raise ValueError("contact_sheet_minutes must be between 5 and 60")
        if not 2 <= self.contact_sheet_columns <= 10:
            raise ValueError("contact_sheet_columns must be between 2 and 10")
        if self.archive_root == self.state_root:
            raise ValueError("archive_root and state_root must be different")
        if self.require_external_archive and configured_volume_root(self.archive_root) is None:
            raise ValueError("archive_root must be on a mounted volume under /Volumes")

    @property
    def pause_file(self) -> Path:
        return self.state_root / "PAUSED"

    @property
    def state_file(self) -> Path:
        return self.state_root / "state.json"


def configured_volume_root(path: Path) -> Optional[Path]:
    if not path.is_absolute() or ".." in path.parts:
        return None
    parts = path.parts
    if len(parts) >= 3 and parts[1] == "Volumes":
        return Path("/Volumes") / parts[2]
    return None


def archive_available(config: Config) -> Tuple[bool, str]:
    volume_root = configured_volume_root(config.archive_root)
    if config.require_external_archive and volume_root is None:
        return False, "archive_not_external"
    if volume_root is not None:
        if not volume_root.exists():
            return False, f"volume_missing:{volume_root}"
        if not os.path.ismount(str(volume_root)):
            return False, f"volume_not_mounted:{volume_root}"
    try:
        config.archive_root.mkdir(parents=True, exist_ok=True)
    except OSError as error:
        return False, f"archive_unwritable:{error.__class__.__name__}"
    try:
        resolved_volume = volume_root.resolve(strict=True) if volume_root else None
        resolved_archive = config.archive_root.resolve(strict=True)
    except OSError as error:
        return False, f"archive_unresolvable:{error.__class__.__name__}"
    if resolved_volume is not None and not resolved_archive.is_relative_to(resolved_volume):
        return False, "archive_outside_volume"
    if not os.access(str(config.archive_root), os.W_OK):
        return False, "archive_unwritable:permission"
    return True, "available"


def screen_locked() -> Optional[bool]:
    completed = run_command(["/usr/sbin/ioreg", "-n", "Root", "-d1"], timeout=10)
    if completed.returncode != 0:
        return None
    match = re.search(
        r'"IOConsoleLocked"\s*=\s*(Yes|No|true|false)', completed.stdout, re.I
    )
    if not match:
        return None
    return match.group(1).casefold() in {"yes", "true"}


def idle_seconds() -> Optional[float]:
    completed = run_command(["/usr/sbin/ioreg", "-c", "IOHIDSystem", "-d", "4"], timeout=10)
    if completed.returncode != 0:
        return None
    match = re.search(r'"HIDIdleTime"\s*=\s*([0-9]+)', completed.stdout)
    if not match:
        return None
    return int(match.group(1)) / 1_000_000_000


def frontmost_app() -> Tuple[Optional[str], Optional[str], Optional[int]]:
    front = run_command(["/usr/bin/lsappinfo", "front"], timeout=10)
    asn = front.stdout.strip()
    if front.returncode != 0 or not asn:
        return None, None, None
    info = run_command(
        ["/usr/bin/lsappinfo", "info", "-only", "name", "-only", "bundleid", "-only", "pid", asn],
        timeout=10,
    )
    name_match = re.search(r'"LSDisplayName"="([^"]*)"', info.stdout)
    bundle_match = re.search(r'"CFBundleIdentifier"="([^"]*)"', info.stdout)
    pid_match = re.search(r'"pid"=([0-9]+)', info.stdout)
    return (
        name_match.group(1) if name_match else None,
        bundle_match.group(1) if bundle_match else None,
        int(pid_match.group(1)) if pid_match else None,
    )


def image_dimensions(path: Path) -> Tuple[int, int]:
    completed = run_command(
        ["/usr/bin/sips", "-g", "pixelWidth", "-g", "pixelHeight", str(path)], timeout=30
    )
    width_match = re.search(r"pixelWidth:\s*([0-9]+)", completed.stdout)
    height_match = re.search(r"pixelHeight:\s*([0-9]+)", completed.stdout)
    if completed.returncode != 0 or not width_match or not height_match:
        raise RuntimeError("Unable to read captured image dimensions")
    return int(width_match.group(1)), int(height_match.group(1))


def day_root(config: Config, value: datetime) -> Path:
    return config.archive_root / value.strftime("%Y/%m/%d")


def state_payload(config: Config, status: str, **extra: Any) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "schema": "screen-activity-capture-state-v1",
        "updated_at": isoformat(utc_now()),
        "status": status,
        "archive_root": str(config.archive_root),
        "interval_seconds": config.interval_seconds,
        "retention_days": config.retention_days,
    }
    payload.update(extra)
    return payload


def set_state(config: Config, status: str, **extra: Any) -> Dict[str, Any]:
    payload = state_payload(config, status, **extra)
    atomic_write_json(config.state_file, payload)
    return payload


def capture_once(config: Config, now: Optional[datetime] = None) -> Dict[str, Any]:
    now = now or local_now()
    config.state_root.mkdir(parents=True, exist_ok=True)
    available, reason = archive_available(config)
    if not available:
        return set_state(config, "waiting_for_archive", reason=reason)
    purge_expired(config, now=now)
    created_days = finalize_completed_contact_sheets(config, now=now)
    for created_day in created_days:
        write_usage_report(config, created_day)
    if config.pause_file.exists():
        return set_state(config, "paused")

    locked = screen_locked()
    if locked is None:
        return set_state(config, "skipped_lock_state_unknown")
    if locked:
        return set_state(config, "skipped_locked")

    idle = idle_seconds()
    if idle is None:
        return set_state(config, "skipped_idle_state_unknown")
    if idle >= config.idle_skip_seconds:
        return set_state(config, "skipped_idle", idle_seconds=round(idle, 1))

    app_name, bundle_id, pid = frontmost_app()
    if app_name is None or bundle_id is None:
        return set_state(config, "skipped_frontmost_app_unknown")
    if app_name.casefold() in {item.casefold() for item in config.excluded_apps}:
        return set_state(config, "skipped_sensitive_app")

    root = day_root(config, now)
    captures = root / "captures"
    captures.mkdir(parents=True, exist_ok=True)
    stem = f"{now.strftime('%Y-%m-%dT%H-%M-%S%z')}_{slugify(app_name)}"
    final_path = captures / f"{stem}.jpg"
    # macOS screencapture refuses a destination whose basename starts with a
    # dot, so keep the staging suffix visible and rename it after compression.
    partial_path = captures / f"{stem}.partial.jpg"

    command = ["/usr/sbin/screencapture", "-m", "-x", "-t", "jpg"]
    if config.capture_cursor:
        command.append("-C")
    command.append(str(partial_path))
    completed = run_command(command, timeout=30)
    if completed.returncode != 0 or not partial_path.exists():
        partial_path.unlink(missing_ok=True)
        return set_state(
            config,
            "capture_error",
            stage="screencapture",
            returncode=completed.returncode,
        )

    try:
        width, height = image_dimensions(partial_path)
        sips_args = ["/usr/bin/sips"]
        if width > config.max_width:
            sips_args.extend(["-Z", str(config.max_width)])
        sips_args.extend(
            ["-s", "format", "jpeg", "-s", "formatOptions", str(config.jpeg_quality)]
        )
        sips_args.extend([str(partial_path), "--out", str(final_path)])
        converted = run_command(sips_args, timeout=60)
        if converted.returncode != 0 or not final_path.exists():
            raise RuntimeError((converted.stderr or converted.stdout or "compression failed")[:300])
        final_width, final_height = image_dimensions(final_path)
    except Exception:
        partial_path.unlink(missing_ok=True)
        final_path.unlink(missing_ok=True)
        return set_state(config, "capture_error", stage="compression")
    partial_path.unlink(missing_ok=True)

    event = {
        "schema": "screen-activity-capture-event-v1",
        "timestamp": isoformat(now),
        "image": str(final_path.relative_to(config.archive_root)),
        "app": app_name,
        "bundle_id": bundle_id,
        "pid": pid,
        "idle_seconds": round(idle, 1) if idle is not None else None,
        "width": final_width,
        "height": final_height,
        "bytes": final_path.stat().st_size,
    }
    append_jsonl(root / "events.jsonl", event)
    result = set_state(
        config,
        "captured",
        latest_capture_at=event["timestamp"],
        bytes=event["bytes"],
        width=final_width,
        height=final_height,
    )
    return result


def purge_expired(config: Config, now: Optional[datetime] = None) -> int:
    available, _ = archive_available(config)
    if not available:
        return 0
    now = now or local_now()
    cutoff = now - timedelta(days=config.retention_days)
    deleted = 0
    for path in config.archive_root.glob("[0-9][0-9][0-9][0-9]/*/*/captures/*.jpg"):
        try:
            captured_at = capture_timestamp(path)
            age_basis = captured_at or datetime.fromtimestamp(
                path.stat().st_mtime, tz=now.tzinfo
            )
            if age_basis < cutoff:
                path.unlink()
                deleted += 1
        except FileNotFoundError:
            continue
    for path in config.archive_root.glob(
        "[0-9][0-9][0-9][0-9]/*/*/analysis/contact-sheets/*"
    ):
        if path.suffix not in {".jpg", ".json"}:
            continue
        try:
            derived_at = contact_sheet_timestamp(config, path, now)
            age_basis = derived_at or datetime.fromtimestamp(
                path.stat().st_mtime, tz=now.tzinfo
            )
            if age_basis < cutoff:
                path.unlink()
                deleted += 1
        except FileNotFoundError:
            continue
    for path in config.archive_root.glob("[0-9][0-9][0-9][0-9]/*/*/events.jsonl"):
        deleted += purge_expired_events(path, cutoff)
    return deleted


def capture_timestamp(path: Path) -> Optional[datetime]:
    match = re.match(r"(\d{4}-\d{2}-\d{2}T\d{2}-\d{2}-\d{2}[+-]\d{4})_", path.name)
    if not match:
        return None
    return datetime.strptime(match.group(1), "%Y-%m-%dT%H-%M-%S%z")


def contact_sheet_timestamp(
    config: Config, path: Path, now: datetime
) -> Optional[datetime]:
    try:
        relative = path.relative_to(config.archive_root)
    except ValueError:
        return None
    if len(relative.parts) < 6 or not re.fullmatch(r"\d{4}", path.stem):
        return None
    try:
        value = datetime.strptime(
            f"{relative.parts[0]}-{relative.parts[1]}-{relative.parts[2]}T{path.stem}",
            "%Y-%m-%dT%H%M",
        )
    except ValueError:
        return None
    return value.replace(tzinfo=now.tzinfo)


def purge_expired_events(path: Path, cutoff: datetime) -> int:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        return 0
    retained: List[str] = []
    removed = 0
    for line in lines:
        try:
            payload = json.loads(line)
            recorded_at = datetime.fromisoformat(str(payload["timestamp"]))
        except (KeyError, TypeError, ValueError, json.JSONDecodeError):
            retained.append(line)
            continue
        if recorded_at < cutoff:
            removed += 1
        else:
            retained.append(line)
    if removed:
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(
            "".join(f"{line}\n" for line in retained), encoding="utf-8"
        )
        os.replace(str(temporary), str(path))
    return removed


def contact_sheet_bucket(value: datetime, minutes: int) -> datetime:
    bucket_minute = (value.minute // minutes) * minutes
    return value.replace(minute=bucket_minute, second=0, microsecond=0)


def build_contact_sheet(
    images: Sequence[Path],
    output: Path,
    columns: int,
    thumb_width: int,
    thumb_height: int,
) -> None:
    if not images:
        raise ValueError("At least one image is required")
    try:
        from PIL import Image, ImageOps
    except ImportError as error:
        raise RuntimeError("Pillow is required to build contact sheets") from error

    rows = int(math.ceil(len(images) / columns))
    sheet = Image.new("RGB", (columns * thumb_width, rows * thumb_height), "black")
    for index, path in enumerate(images):
        with Image.open(path) as source:
            frame = ImageOps.contain(source.convert("RGB"), (thumb_width, thumb_height))
            x = (index % columns) * thumb_width + (thumb_width - frame.width) // 2
            y = (index // columns) * thumb_height + (thumb_height - frame.height) // 2
            sheet.paste(frame, (x, y))
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(".tmp.jpg")
    sheet.save(temporary, "JPEG", quality=65, optimize=True)
    os.replace(str(temporary), str(output))


def contact_sheet_groups(config: Config, day: str) -> Dict[datetime, List[Path]]:
    parsed = datetime.strptime(day, "%Y-%m-%d")
    captures = config.archive_root / parsed.strftime("%Y/%m/%d") / "captures"
    groups: Dict[datetime, List[Path]] = {}
    for path in sorted(captures.glob("*.jpg")):
        timestamp = capture_timestamp(path)
        if timestamp is None:
            continue
        groups.setdefault(contact_sheet_bucket(timestamp, config.contact_sheet_minutes), []).append(path)
    return groups


def finalize_completed_contact_sheets(
    config: Config, now: Optional[datetime] = None
) -> List[str]:
    now = now or local_now()
    days = {
        now.strftime("%Y-%m-%d"),
        (now - timedelta(days=1)).strftime("%Y-%m-%d"),
    }
    completed_days: List[str] = []
    for day in sorted(days):
        for bucket, images in contact_sheet_groups(config, day).items():
            if bucket + timedelta(minutes=config.contact_sheet_minutes) > now:
                continue
            root = day_root(config, bucket)
            output = (
                root
                / "analysis"
                / "contact-sheets"
                / f"{bucket.strftime('%H%M')}.jpg"
            )
            if output.exists():
                continue
            build_contact_sheet(
                images,
                output,
                config.contact_sheet_columns,
                config.contact_sheet_thumb_width,
                config.contact_sheet_thumb_height,
            )
            manifest = {
                "schema": "screen-activity-contact-sheet-v1",
                "bucket_start": isoformat(bucket),
                "bucket_minutes": config.contact_sheet_minutes,
                "contact_sheet": str(output.relative_to(config.archive_root)),
                "frames": [str(path.relative_to(config.archive_root)) for path in images],
            }
            atomic_write_json(output.with_suffix(".json"), manifest)
            completed_days.append(day)
    return sorted(set(completed_days))


def acquire_collector_lock(config: Config) -> Optional[Any]:
    config.state_root.mkdir(parents=True, exist_ok=True)
    handle = (config.state_root / "collector.lock").open("a+", encoding="utf-8")
    try:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        handle.close()
        return None
    return handle


def gpt56_original_tokens(width: int, height: int) -> int:
    return int(math.ceil(width / 32) * math.ceil(height / 32))


def image_token_estimate(path: Path) -> Dict[str, int]:
    width, height = image_dimensions(path)
    return {
        "low": 256,
        "original": gpt56_original_tokens(width, height),
    }


def usage_report(config: Config, day: str) -> Dict[str, Any]:
    parsed = datetime.strptime(day, "%Y-%m-%d")
    root = config.archive_root / parsed.strftime("%Y/%m/%d")
    captures = sorted((root / "captures").glob("*.jpg"))
    sheets = sorted((root / "analysis" / "contact-sheets").glob("*.jpg"))
    capture_bytes = sum(path.stat().st_size for path in captures)
    sheet_bytes = sum(path.stat().st_size for path in sheets)
    raw_original = sum(image_token_estimate(path)["original"] for path in captures)
    sheet_original = sum(image_token_estimate(path)["original"] for path in sheets)
    projected_hours = 8
    projected_captures = int(projected_hours * 3600 / config.interval_seconds)
    projected_sheets = int(
        math.ceil(projected_hours * 60 / config.contact_sheet_minutes)
    )
    frames_per_sheet = max(
        1, int(config.contact_sheet_minutes * 60 / config.interval_seconds)
    )
    projected_sheet_rows = int(
        math.ceil(frames_per_sheet / config.contact_sheet_columns)
    )
    projected_sheet_original = gpt56_original_tokens(
        config.contact_sheet_columns * config.contact_sheet_thumb_width,
        projected_sheet_rows * config.contact_sheet_thumb_height,
    )
    average_capture_bytes = capture_bytes / len(captures) if captures else 0
    average_capture_original = raw_original / len(captures) if captures else 0
    return {
        "schema": "screen-activity-usage-report-v1",
        "day": day,
        "generated_at": isoformat(utc_now()),
        "capture_interval_seconds": config.interval_seconds,
        "captures": {
            "count": len(captures),
            "bytes": capture_bytes,
            "megabytes": round(capture_bytes / 1_000_000, 2),
            "gpt_5_6_tokens_if_all_low_detail": len(captures) * 256,
            "gpt_5_6_tokens_if_all_original_detail": raw_original,
        },
        "contact_sheets": {
            "count": len(sheets),
            "bytes": sheet_bytes,
            "megabytes": round(sheet_bytes / 1_000_000, 2),
            "gpt_5_6_tokens_if_all_low_detail": len(sheets) * 256,
            "gpt_5_6_tokens_if_all_original_detail": sheet_original,
        },
        "recommended_analysis": {
            "first_pass": "contact_sheets_low_detail",
            "second_pass": "selected_frames_original_detail",
            "automatic_model_calls": False,
        },
        "projected_eight_hour_day": {
            "captures_before_lock_idle_sensitive_app_skips": projected_captures,
            "raw_storage_megabytes_at_observed_average": round(
                projected_captures * average_capture_bytes / 1_000_000, 2
            ),
            "tokens_if_all_raw_low_detail": projected_captures * 256,
            "tokens_if_all_raw_original_detail_at_observed_average": round(
                projected_captures * average_capture_original
            ),
            "contact_sheets": projected_sheets,
            "tokens_if_contact_sheets_low_detail": projected_sheets * 256,
            "tokens_if_full_contact_sheets_original_detail": (
                projected_sheets * projected_sheet_original
            ),
        },
        "estimator_basis": {
            "model_family": "GPT-5.6",
            "low_detail_tokens_per_image": 256,
            "original_formula": "ceil(width/32) * ceil(height/32)",
            "official_docs": OPENAI_VISION_DOCS,
            "note": "API-style estimate; Codex product accounting may differ.",
        },
    }


def write_usage_report(config: Config, day: str) -> Dict[str, Any]:
    report = usage_report(config, day)
    parsed = datetime.strptime(day, "%Y-%m-%d")
    output = config.archive_root / parsed.strftime("%Y/%m/%d") / "analysis" / "usage.json"
    atomic_write_json(output, report)
    return report


def run_loop(config: Config) -> int:
    lock_handle = acquire_collector_lock(config)
    if lock_handle is None:
        return 4
    pid_file = config.state_root / "collector.pid"
    pid_file.write_text(f"{os.getpid()}\n", encoding="utf-8")
    stopping = False

    def stop(_signum: int, _frame: Any) -> None:
        nonlocal stopping
        stopping = True

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    try:
        config.state_root.mkdir(parents=True, exist_ok=True)
        set_state(config, "starting")
        while not stopping:
            started = time.monotonic()
            try:
                capture_once(config)
            except Exception as error:
                set_state(
                    config,
                    "loop_error",
                    error=f"{error.__class__.__name__}: {error}"[:300],
                )
            elapsed = time.monotonic() - started
            remaining = max(1.0, config.interval_seconds - elapsed)
            end = time.monotonic() + remaining
            while not stopping and time.monotonic() < end:
                time.sleep(min(1.0, end - time.monotonic()))
        set_state(config, "stopped")
    finally:
        try:
            if pid_file.read_text(encoding="utf-8").strip() == str(os.getpid()):
                pid_file.unlink(missing_ok=True)
        except FileNotFoundError:
            pass
        lock_handle.close()
    return 0


def self_test(config: Config) -> Dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="screen-activity-self-test.") as temporary:
        root = Path(temporary)
        test_config = Config(
            archive_root=root / "archive",
            state_root=root / "state",
            interval_seconds=config.interval_seconds,
            retention_days=config.retention_days,
            max_width=config.max_width,
            jpeg_quality=config.jpeg_quality,
            idle_skip_seconds=86_400,
            capture_cursor=config.capture_cursor,
            contact_sheet_minutes=config.contact_sheet_minutes,
            contact_sheet_columns=config.contact_sheet_columns,
            contact_sheet_thumb_width=config.contact_sheet_thumb_width,
            contact_sheet_thumb_height=config.contact_sheet_thumb_height,
            excluded_apps=tuple(),
            require_external_archive=False,
        )
        result = capture_once(test_config)
        if result.get("status") != "captured":
            return {"status": "failed", "capture_result": result}
        captures = list(test_config.archive_root.glob("*/*/*/captures/*.jpg"))
        if len(captures) != 1:
            return {"status": "failed", "capture_result": result}
        latest = captures[0]
        return {
            "status": "passed",
            "capture_bytes": latest.stat().st_size,
            "width": result["width"],
            "height": result["height"],
            "temporary_artifact_deleted_on_exit": True,
        }


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("capture", help="Capture one frame if allowed")
    subparsers.add_parser("run", help="Run the persistent capture loop")
    subparsers.add_parser("status", help="Print current state")
    subparsers.add_parser("pause", help="Pause capture")
    subparsers.add_parser("resume", help="Resume capture")
    subparsers.add_parser("self-test", help="Capture and delete one temporary test frame")
    sheets = subparsers.add_parser("contact-sheets", help="Finalize completed contact sheets")
    sheets.add_argument("--day", help="YYYY-MM-DD; defaults to today")
    report = subparsers.add_parser("report", help="Write and print storage/token usage")
    report.add_argument("--day", help="YYYY-MM-DD; defaults to today")
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    try:
        config = Config.from_path(args.config)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(json.dumps({"status": "config_error", "error": str(error)}), file=sys.stderr)
        return 2

    if args.command == "capture":
        lock_handle = acquire_collector_lock(config)
        if lock_handle is None:
            print(json.dumps(state_payload(config, "already_running"), indent=2, sort_keys=True))
            return 4
        try:
            print(json.dumps(capture_once(config), indent=2, sort_keys=True))
            return 0
        finally:
            lock_handle.close()
    if args.command == "run":
        return run_loop(config)
    if args.command == "status":
        if config.state_file.exists():
            print(config.state_file.read_text(encoding="utf-8"), end="")
        else:
            print(json.dumps(state_payload(config, "not_started"), indent=2, sort_keys=True))
        return 0
    if args.command == "pause":
        config.state_root.mkdir(parents=True, exist_ok=True)
        config.pause_file.write_text(f"paused_at={isoformat(utc_now())}\n", encoding="utf-8")
        print(json.dumps(set_state(config, "paused"), indent=2, sort_keys=True))
        return 0
    if args.command == "resume":
        config.pause_file.unlink(missing_ok=True)
        print(json.dumps(set_state(config, "resumed"), indent=2, sort_keys=True))
        return 0
    if args.command == "self-test":
        result = self_test(config)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result.get("status") == "passed" else 1
    if args.command == "contact-sheets":
        day = args.day or local_now().strftime("%Y-%m-%d")
        now = local_now()
        if day != now.strftime("%Y-%m-%d"):
            now = datetime.strptime(day, "%Y-%m-%d").astimezone() + timedelta(days=1)
        created_days = finalize_completed_contact_sheets(config, now=now)
        print(
            json.dumps(
                {"status": "ok", "created_days": created_days, "day": day},
                indent=2,
            )
        )
        return 0
    if args.command == "report":
        day = args.day or local_now().strftime("%Y-%m-%d")
        available, reason = archive_available(config)
        if not available:
            print(json.dumps({"status": "waiting_for_archive", "reason": reason}, indent=2))
            return 3
        print(json.dumps(write_usage_report(config, day), indent=2, sort_keys=True))
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

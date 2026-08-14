#!/usr/bin/env python3

import importlib.util
import json
import pathlib
import sys
import unittest


MODULE_PATH = pathlib.Path(__file__).with_name("codex_usage_report.py")
SPEC = importlib.util.spec_from_file_location("codex_usage_report", MODULE_PATH)
assert SPEC and SPEC.loader
REPORTER = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = REPORTER
SPEC.loader.exec_module(REPORTER)


class FakeClient:
    def __init__(self) -> None:
        self.methods = []

    def initialize(self):
        return {"userAgent": "test"}

    def request(self, method):
        self.methods.append(method)
        if method == "account/usage/read":
            return {
                "summary": {"lifetimeTokens": 30},
                "dailyUsageBuckets": [
                    {"startDate": "2026-07-01", "tokens": 10},
                    {"startDate": "2026-08-01", "tokens": 20},
                ],
            }
        if method == "account/rateLimits/read":
            return {"rateLimits": {"primary": {"usedPercent": 25}}}
        raise AssertionError(f"unexpected method: {method}")


class CodexUsageReportTests(unittest.TestCase):
    def test_build_report_never_requests_thread_methods(self) -> None:
        client = FakeClient()
        report = REPORTER.build_report(
            client, REPORTER.ReportOptions(days=30, comparison_days=30)
        )
        self.assertEqual(
            client.methods, ["account/usage/read", "account/rateLimits/read"]
        )
        self.assertNotIn("threads", report)
        self.assertEqual(report["source"]["methods"], client.methods)
        self.assertNotIn("thread/", json.dumps(report))

    def test_daily_bucket_filter_preserves_provider_values(self) -> None:
        buckets = [
            {"startDate": "2026-07-01", "tokens": 10},
            {"startDate": "2026-08-01", "tokens": 20},
        ]
        self.assertEqual(
            REPORTER.filtered_daily_buckets(buckets, "2026-07-15"), [buckets[1]]
        )
        self.assertIsNone(REPORTER.filtered_daily_buckets(None, "2026-07-15"))


if __name__ == "__main__":
    unittest.main()

"""Offline checks: fake HTTP responses, no API key, no network, no real waits.

Run from the repository root:
    .venv/bin/python -B ingest/test_fetch.py
"""

import unittest
from unittest.mock import Mock, call, patch

import requests

import fetch


class FetchRetryTests(unittest.TestCase):
    @staticmethod
    def response(status, headers=None):
        return Mock(status_code=status, headers=headers or {})

    def run_fake_request(self, outcomes, budget=600):
        # This fake session never connects to the Internet.
        session = Mock()
        session.get.side_effect = outcomes
        # Record sleep calls instead of actually waiting.
        with patch.object(fetch.time, "sleep") as sleep:
            result, attempts = fetch.get_response(
                session,
                "https://example.invalid/weather",
                {},  # No key is supplied or read.
                estimated_cost=50,
                remaining_budget=budget,
            )
        return result, attempts, session, sleep

    def test_429_then_success_honors_retry_after(self):
        success = self.response(200)
        result, attempts, session, sleep = self.run_fake_request([
            self.response(429, {"Retry-After": "3"}),
            success,
        ])
        self.assertIs(result, success)
        self.assertEqual(attempts, 2)
        self.assertEqual(session.get.call_count, 2)
        self.assertEqual(sleep.call_args_list, [call(1), call(3.0), call(1)])

    def test_repeated_429_stops_after_four_attempts(self):
        result, attempts, session, sleep = self.run_fake_request([
            self.response(429) for _ in range(4)
        ])
        self.assertIsNone(result)
        self.assertEqual(attempts, 4)
        self.assertEqual(session.get.call_count, 4)
        self.assertEqual(
            sleep.call_args_list,
            [call(1), call(2), call(1), call(4), call(1), call(8), call(1)],
        )

    def test_timeout_then_success_retries(self):
        success = self.response(200)
        result, attempts, session, sleep = self.run_fake_request([
            requests.Timeout(),
            success,
        ])
        self.assertIs(result, success)
        self.assertEqual(attempts, 2)
        self.assertEqual(session.get.call_count, 2)
        self.assertEqual(sleep.call_args_list, [call(1), call(2), call(1)])

    def test_budget_blocks_a_retry(self):
        # Only one estimated 50-record attempt fits. A second must never be sent.
        result, attempts, session, sleep = self.run_fake_request([
            self.response(429),
            self.response(200),
        ], budget=50)
        self.assertIsNone(result)
        self.assertEqual(attempts, 1)
        self.assertEqual(session.get.call_count, 1)
        self.assertEqual(sleep.call_args_list, [call(1), call(2)])


if __name__ == "__main__":
    unittest.main(verbosity=2)

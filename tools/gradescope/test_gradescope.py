from __future__ import annotations

import unittest
from datetime import datetime
from types import SimpleNamespace

import gradescope


class GradescopeCookieTests(unittest.TestCase):
    def test_parse_cookie_header(self) -> None:
        parsed = gradescope.parse_cookie_header(
            "_gradescope_session=abc; remember_me=def; signed_token=ghi"
        )
        self.assertEqual(
            parsed,
            {
                "_gradescope_session": "abc",
                "remember_me": "def",
                "signed_token": "ghi",
            },
        )

    def test_cookie_pairs_use_named_keys(self) -> None:
        cookies = gradescope.cookie_pairs(
            {
                "_gradescope_session": "session-value",
                "remember_me": "remember-value",
                "signed_token": "token-value",
                "email": "not-a-cookie@example.com",
            }
        )
        self.assertEqual(
            cookies,
            {
                "_gradescope_session": "session-value",
                "remember_me": "remember-value",
                "signed_token": "token-value",
            },
        )
        self.assertEqual(
            gradescope.cookie_names(
                {
                    "_gradescope_session": "session-value",
                    "remember_me": "remember-value",
                }
            ),
            ["_gradescope_session", "remember_me"],
        )

    def test_serialize_assignment_dates(self) -> None:
        payload = gradescope.serialize_assignment(
            SimpleNamespace(
                assignment_id="9",
                name="Homework 01",
                release_date=datetime(2026, 8, 24, 8, 0),
                due_date=datetime(2026, 8, 28, 23, 59),
                late_due_date=None,
                submissions_status="open",
                grade=None,
                max_grade="10.0",
            )
        )
        self.assertEqual(payload["id"], "9")
        self.assertEqual(payload["dueDate"], "2026-08-28T23:59:00")
        self.assertIsNone(payload["lateDueDate"])


if __name__ == "__main__":
    unittest.main()

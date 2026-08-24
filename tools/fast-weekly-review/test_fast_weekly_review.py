from __future__ import annotations

import datetime as dt
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "fast-common"))

import fast_weekly_review as wr  # noqa: E402


class TermWeekTests(unittest.TestCase):
    def test_day_before_term_start_is_week_1(self) -> None:
        self.assertEqual(wr.term_week(dt.date(2026, 8, 23)), 1)

    def test_term_start_monday_is_week_1(self) -> None:
        self.assertEqual(wr.term_week(dt.date(2026, 8, 24)), 1)

    def test_following_monday_is_week_2(self) -> None:
        self.assertEqual(wr.term_week(dt.date(2026, 8, 31)), 2)

    def test_week_range_for_week_1(self) -> None:
        start, end = wr.week_date_range(1)
        self.assertEqual(start, dt.date(2026, 8, 24))
        self.assertEqual(end, dt.date(2026, 8, 30))


class CycleAndStatusTests(unittest.TestCase):
    def test_week_from_cycle_name(self) -> None:
        self.assertEqual(wr.week_from_cycle({"name": "Week 01"}), 1)
        self.assertEqual(wr.week_from_cycle({"name": "Week 3"}), 3)
        self.assertIsNone(wr.week_from_cycle({"name": "Sprint A"}))
        self.assertIsNone(wr.week_from_cycle(None))

    def test_open_versus_terminal_status(self) -> None:
        self.assertTrue(wr.is_open_issue({"status": "Todo", "statusType": "unstarted"}))
        self.assertFalse(wr.is_open_issue({"status": "Submitted"}))
        self.assertFalse(wr.is_open_issue({"status": "In Progress", "statusType": "completed"}))
        self.assertFalse(wr.is_open_issue({"status": "Missed"}))


class InboxClassificationTests(unittest.TestCase):
    def test_deadline_versus_capture(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            inbox = Path(temporary)
            capture = inbox / "fleeting.md"
            capture.write_text(
                "---\ntype: capture\ncaptured: 2026-08-20\n---\n\nA thought.\n",
                encoding="utf-8",
            )
            homework = inbox / "quiz reminder.md"
            homework.write_text(
                "---\ntype: capture\ncaptured: 2026-08-21\n---\n\nQuiz due Friday.\n",
                encoding="utf-8",
            )
            classified_capture = wr.classify_inbox_file(capture)
            classified_deadline = wr.classify_inbox_file(homework)
            self.assertEqual(classified_capture["classification"], "capture")
            self.assertFalse(classified_capture["deadline_bearing"])
            self.assertEqual(classified_deadline["classification"], "deadline")
            self.assertTrue(classified_deadline["deadline_bearing"])


if __name__ == "__main__":
    unittest.main()

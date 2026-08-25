from __future__ import annotations

import datetime as dt
import unittest

from fast_assign_cycles import TERM_WEEKS, week_from_due_date
from fast_common import TERM_START


class WeekFromDueDateTests(unittest.TestCase):
    def test_term_start_is_week_01(self) -> None:
        self.assertEqual(week_from_due_date(TERM_START), 1)
        self.assertEqual(week_from_due_date("2026-08-24"), 1)

    def test_same_week_includes_sunday(self) -> None:
        self.assertEqual(week_from_due_date(dt.date(2026, 8, 30)), 1)

    def test_next_monday_is_week_02(self) -> None:
        self.assertEqual(week_from_due_date(dt.date(2026, 8, 31)), 2)
        self.assertEqual(week_from_due_date("2026-08-31T23:59:59"), 2)

    def test_datetime_uses_calendar_date(self) -> None:
        self.assertEqual(
            week_from_due_date(dt.datetime(2026, 8, 31, 0, 0)),
            2,
        )

    def test_week_16_start_and_last_uncapped_day(self) -> None:
        self.assertEqual(week_from_due_date(dt.date(2026, 12, 7)), 16)
        self.assertEqual(week_from_due_date(dt.date(2026, 12, 13)), 16)

    def test_clamps_above_term_weeks(self) -> None:
        self.assertEqual(week_from_due_date(dt.date(2026, 12, 14)), TERM_WEEKS)
        self.assertEqual(week_from_due_date(dt.date(2027, 1, 1)), TERM_WEEKS)

    def test_clamps_before_term_start(self) -> None:
        self.assertEqual(week_from_due_date(dt.date(2026, 8, 23)), 1)
        self.assertEqual(week_from_due_date(dt.date(2026, 1, 1)), 1)

    def test_formula_matches_integer_division(self) -> None:
        due = dt.date(2026, 9, 21)
        expected = max(1, min(16, (due - TERM_START).days // 7 + 1))
        self.assertEqual(week_from_due_date(due), expected)
        self.assertEqual(expected, 5)


if __name__ == "__main__":
    unittest.main()

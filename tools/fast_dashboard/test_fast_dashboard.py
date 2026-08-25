from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "fast_common"))

import fast_dashboard as fd


MATH = {"code": "MATH 212", "hyphen": "MATH-212"}
ECEG = {"code": "ECEG 210", "hyphen": "ECEG-210"}


def issue(**fields: object) -> dict:
    base = {
        "identifier": "JPS-1",
        "title": "Homework 01",
        "status": "Todo",
        "labels": [{"name": "pset"}],
        "dueDate": "2026-08-28",
        "estimate": 2,
        "priority": 3,
        "url": "https://linear.app/example/issue/JPS-1",
    }
    base.update(fields)
    return base


class DashboardGroupingTests(unittest.TestCase):
    def test_closed_statuses_are_excluded(self) -> None:
        self.assertFalse(fd.is_open_issue(issue(status="Done")))
        self.assertFalse(fd.is_open_issue(issue(status="Canceled")))
        self.assertFalse(fd.is_open_issue(issue(status="Graded")))
        self.assertFalse(fd.is_open_issue(issue(status="Missed")))
        self.assertFalse(fd.is_open_issue(issue(status="Excused")))
        self.assertFalse(
            fd.is_open_issue(issue(status="Todo", statusType="completed"))
        )
        self.assertTrue(fd.is_open_issue(issue(status="In Progress")))

    def test_exam_kind_splits_from_due_work_and_sorts_by_due(self) -> None:
        later = issue(
            identifier="JPS-8",
            title="Homework 02",
            dueDate="2026-09-04",
        )
        earlier = issue(
            identifier="JPS-6",
            title="Homework 01",
            dueDate="2026-08-28",
        )
        midterm = issue(
            identifier="JPS-9",
            title="Midterm",
            labels=[{"name": "exam"}],
            dueDate="2026-10-12",
            estimate=5,
        )
        graded = issue(identifier="JPS-2", status="Graded", dueDate="2026-08-25")
        snapshot = fd.collect_dashboard(
            [(MATH, [later, earlier, midterm, graded])],
            cycles=[{"name": "Week 01"}],
        )
        self.assertEqual(
            [item["identifier"] for item in snapshot["due_work"]],
            ["JPS-6", "JPS-8"],
        )
        self.assertEqual(
            [item["identifier"] for item in snapshot["exams"]],
            ["JPS-9"],
        )
        self.assertTrue(
            any(item["kind"] == "live_linear_state" for item in snapshot["needs_llm"])
        )

    def test_weekly_load_uses_cycle_then_term_start_due_date(self) -> None:
        cycled = issue(
            identifier="JPS-6",
            cycle={"name": "Week 01"},
            dueDate="2026-09-10",
            estimate=3,
        )
        from_due = issue(
            identifier="JPS-7",
            labels=[{"name": "quiz"}],
            dueDate="2026-09-02",
            estimate=1,
            cycle=None,
        )
        snapshot = fd.collect_dashboard(
            [(MATH, [cycled]), (ECEG, [from_due])],
            cycles=[{"name": "Week 01"}],
        )
        by_cycle = {item["cycle"]: item for item in snapshot["weekly_load"]}
        self.assertEqual(by_cycle["Week 01"]["estimate_total"], 3)
        self.assertEqual(by_cycle["Week 02"]["estimate_total"], 1)
        self.assertEqual(by_cycle["Week 02"]["week"], 2)

    def test_markdown_lists_open_rows(self) -> None:
        snapshot = fd.collect_dashboard(
            [
                (
                    MATH,
                    [
                        issue(identifier="JPS-6", title="Homework 01"),
                        issue(
                            identifier="JPS-9",
                            title="Exam 01",
                            labels=[{"name": "exam"}],
                            dueDate="2026-10-12",
                        ),
                    ],
                )
            ],
            cycles=[{"name": "Week 01"}],
        )
        text = fd.render_markdown(snapshot)
        self.assertIn("## Due work", text)
        self.assertIn("JPS-6 Homework 01", text)
        self.assertIn("## Exams", text)
        self.assertIn("JPS-9 Exam 01", text)
        self.assertIn("## Weekly load", text)

    def test_output_file_flags_are_rejected(self) -> None:
        with self.assertRaises(fd.ToolError) as raised:
            fd.fetch_dashboard({"output": r"C:/tmp/due_work.json"})
        self.assertIn("stdout", raised.exception.message)
        self.assertEqual(raised.exception.code, "usage")


if __name__ == "__main__":
    unittest.main()

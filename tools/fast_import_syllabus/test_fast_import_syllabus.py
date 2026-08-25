from __future__ import annotations

import sys
import unittest
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_COMMON = _HERE.parent / "fast_common"
for path in (_HERE, _COMMON):
    text = str(path)
    if text not in sys.path:
        sys.path.insert(0, text)

from fast_import_syllabus import (  # noqa: E402
    extract_dated_obligations,
    has_linear_deadlines_note,
    infer_kind,
    week_from_due,
)


class ImportSyllabusExtractionTests(unittest.TestCase):
    def test_iso_homework_maps_to_pset(self) -> None:
        proposed, remaining = extract_dated_obligations(
            "Homework 1 due 2026-09-04\n"
        )
        self.assertEqual(remaining, [])
        self.assertEqual(len(proposed), 1)
        self.assertEqual(proposed[0]["kind"], "pset")
        self.assertEqual(proposed[0]["due_date"], "2026-09-04")
        self.assertEqual(proposed[0]["week"], 2)
        self.assertIn("Homework", proposed[0]["name"])

    def test_named_month_exam_and_month_day_default_year(self) -> None:
        text = (
            "Midterm I — October 8, 2026\n"
            "Quiz 2 due November 3\n"
            "Lab 3 due 11/10/2026\n"
            "Reading 4 due 2026-11-17\n"
        )
        proposed, remaining = extract_dated_obligations(text)
        self.assertEqual(remaining, [])
        kinds = {item["name"]: item for item in proposed}
        self.assertEqual(len(proposed), 4)
        midterm = next(item for item in proposed if item["kind"] == "exam")
        self.assertEqual(midterm["due_date"], "2026-10-08")
        quiz = next(item for item in proposed if item["kind"] == "quiz")
        self.assertEqual(quiz["due_date"], "2026-11-03")
        lab = next(item for item in proposed if item["kind"] == "lab")
        self.assertEqual(lab["due_date"], "2026-11-10")
        reading = next(item for item in proposed if item["kind"] == "reading")
        self.assertEqual(reading["due_date"], "2026-11-17")
        self.assertTrue(kinds)

    def test_tentative_exam_prefixes_title(self) -> None:
        proposed, remaining = extract_dated_obligations(
            "Final exam (tentative) December 15, 2026\n"
        )
        self.assertEqual(remaining, [])
        self.assertEqual(proposed[0]["kind"], "exam")
        self.assertTrue(proposed[0]["tentative"])
        self.assertTrue(proposed[0]["name"].lower().startswith("(tentative)"))

    def test_problem_set_maps_to_pset(self) -> None:
        proposed, _remaining = extract_dated_obligations(
            "- Problem set 2 due September 11, 2026\n"
        )
        self.assertEqual(proposed[0]["kind"], "pset")

    def test_undated_numbered_homework_needs_llm(self) -> None:
        proposed, remaining = extract_dated_obligations("Homework 5 is assigned.\n")
        self.assertEqual(proposed, [])
        self.assertEqual(remaining[0]["kind"], "missing_due")

    def test_policy_sentences_are_not_obligations(self) -> None:
        proposed, remaining = extract_dated_obligations(
            "- **Homework:** Assigned problem-by-problem with individual due dates. Box the final answer.\n"
            "- If you miss a Midterm due to an excused absence, remaining midterms are reweighted.\n"
            "This copy was verified against Homework 01.\n"
        )
        self.assertEqual(proposed, [])
        self.assertEqual(remaining, [])

    def test_due_without_kind_needs_llm(self) -> None:
        proposed, remaining = extract_dated_obligations(
            "Work due October 1, 2026\n"
        )
        self.assertEqual(proposed, [])
        self.assertEqual(remaining[0]["kind"], "missing_kind")

    def test_linear_deadlines_note_and_no_dates(self) -> None:
        text = (
            "Exam dates and assignment deadlines are tracked in Linear "
            "rather than duplicated here.\n"
            "Homework: 10%\n"
            "Midterm exam I: 16%\n"
        )
        proposed, remaining = extract_dated_obligations(text)
        self.assertEqual(proposed, [])
        self.assertEqual(remaining, [])
        self.assertTrue(has_linear_deadlines_note(text))

    def test_grading_weights_are_not_obligations(self) -> None:
        proposed, remaining = extract_dated_obligations(
            "- Three midterm exams: 57%\n- Final exam: 23%\n- Problem sets: 10%\n"
        )
        self.assertEqual(proposed, [])
        self.assertEqual(remaining, [])

    def test_kind_inference(self) -> None:
        self.assertEqual(infer_kind("in-class midterm"), "exam")
        self.assertEqual(infer_kind("weekly quiz"), "quiz")
        self.assertEqual(infer_kind("laboratory report"), "lab")
        self.assertEqual(infer_kind("reading guide"), "reading")
        self.assertEqual(infer_kind("homework 01"), "pset")
        self.assertIsNone(infer_kind("office hours Wednesday"))

    def test_week_from_due_clamps(self) -> None:
        self.assertEqual(week_from_due("2026-08-24"), 1)
        self.assertEqual(week_from_due("2026-08-28"), 1)
        self.assertEqual(week_from_due("2026-09-04"), 2)
        self.assertEqual(week_from_due("2026-08-01"), 1)
        self.assertEqual(week_from_due("2027-01-01"), 16)

    def test_frontmatter_dates_are_ignored(self) -> None:
        text = (
            "---\n"
            "type: syllabus\n"
            "captured: 2026-08-24\n"
            "---\n"
            "Homework 01 due September 4, 2026\n"
        )
        proposed, remaining = extract_dated_obligations(text)
        self.assertEqual(remaining, [])
        self.assertEqual(len(proposed), 1)
        self.assertEqual(proposed[0]["due_date"], "2026-09-04")

    def test_duplicate_lines_collapse(self) -> None:
        proposed, _remaining = extract_dated_obligations(
            "Homework 1 due 2026-09-04\n"
            "Homework 1 due 2026-09-04\n"
        )
        self.assertEqual(len(proposed), 1)

    def test_generic_project_is_not_a_kind(self) -> None:
        proposed, remaining = extract_dated_obligations(
            "Course project due 2026-12-01\n"
        )
        self.assertEqual(proposed, [])
        self.assertEqual(remaining[0]["kind"], "missing_kind")


if __name__ == "__main__":
    unittest.main()

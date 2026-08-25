from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "fast_common"))

from fast_common import FORBIDDEN_FIELDS
from linear_apply import project_id_for
from vault_apply import dump_note

from fast_scaffold_work_note import (
    KIND_LABELS,
    assignment_frontmatter,
    course_for_issue,
    kind_from_issue,
    week_from_cycle,
)


class ScaffoldMetadataTests(unittest.TestCase):
    def test_dumped_metadata_omits_forbidden_keys(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary) / "MATH-245-Linear-Algebra-Fall-2026"
            folder.mkdir()
            index = folder / "MATH-245.md"
            index.write_text("# MATH 245\n", encoding="utf-8")
            course = {
                "code": "MATH 245",
                "hyphen": "MATH-245",
                "folder": folder,
                "index": index,
            }
            issue = {
                "identifier": "JPS-5",
                "title": "MATH 245 Homework 01",
                "url": "https://linear.app/example/issue/JPS-5",
                "status": "Todo",
                "dueDate": "2026-08-28",
                "priority": 2,
                "estimate": 3,
            }
            metadata = assignment_frontmatter(
                course, issue, kind="pset", week=1
            )
            dumped = dump_note(metadata, "# MATH 245 Homework 01\n")
            for field in FORBIDDEN_FIELDS:
                self.assertNotIn(field, metadata)
                self.assertNotRegex(dumped, rf"(?m)^{field}:")
            self.assertEqual(metadata["type"], "assignment")
            self.assertEqual(metadata["linear"], "JPS-5")
            self.assertEqual(metadata["kind"], "pset")
            self.assertIn("linear_url", metadata)
            self.assertNotIn("dueDate", metadata)
            self.assertNotIn("status", dumped)

    def test_kind_labels_stay_in_vault_ontology(self) -> None:
        self.assertEqual(
            kind_from_issue({"labels": [{"name": "pset"}]})[0],
            "pset",
        )
        self.assertEqual(
            kind_from_issue({"labels": [{"name": "course project"}]})[0],
            "course project",
        )
        self.assertIsNone(
            kind_from_issue({"labels": [{"name": "pset"}, {"name": "exam"}]})[0]
        )
        self.assertTrue({"pset", "course project"} <= KIND_LABELS)

    def test_week_comes_from_cycle_name_not_due_date(self) -> None:
        issue = {
            "dueDate": "2026-12-01",
            "cycle": {"name": "Week 01"},
        }
        self.assertEqual(week_from_cycle(issue), 1)
        self.assertIsNone(week_from_cycle({"dueDate": "2026-08-28"}))

    def test_course_matches_project_id(self) -> None:
        course = {
            "code": "MATH 245",
            "hyphen": "MATH-245",
            "linear_project": (
                "https://linear.app/example/project/math-245-linear-algebra-7c79967af29c"
            ),
            "linear_slug": "math-245-linear-algebra-7c79967af29c",
        }
        other = {
            "code": "MATH 212",
            "hyphen": "MATH-212",
            "linear_project": (
                "https://linear.app/example/project/math-212-differential-equations-db95533679b2"
            ),
            "linear_slug": "math-212-differential-equations-db95533679b2",
        }
        projects = [
            {
                "id": "math-245-id",
                "name": "MATH 245 — Linear Algebra",
                "slugId": "7c79967af29c",
                "url": course["linear_project"],
            },
            {
                "id": "math-212-id",
                "name": "MATH 212 — Differential Equations",
                "slugId": "db95533679b2",
                "url": other["linear_project"],
            },
        ]
        self.assertEqual(project_id_for(course, projects), "math-245-id")
        matched = course_for_issue(
            {
                "identifier": "JPS-5",
                "project": {"id": "math-245-id", "name": "MATH 245 — Linear Algebra"},
            },
            [other, course],
            projects,
        )
        self.assertIs(matched, course)


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import fast_common as fc


class FastCommonTests(unittest.TestCase):
    def test_course_code_forms(self) -> None:
        self.assertEqual(fc.hyphen_code("MATH 212"), "MATH-212")
        self.assertEqual(fc.spaced_code("MATH212"), "MATH 212")
        self.assertEqual(fc.compact_code("math-212"), "MATH212")

    def test_drive_and_linear_ids(self) -> None:
        self.assertEqual(
            fc.extract_drive_folder_id(
                "https://drive.google.com/drive/folders/1LUJ_xIB1Bm_FJYh9rwN5LFsaWXYYiGW2"
            ),
            "1LUJ_xIB1Bm_FJYh9rwN5LFsaWXYYiGW2",
        )
        self.assertEqual(
            fc.extract_linear_project_slug(
                "https://linear.app/jpdagostino/project/math-245-linear-algebra-7c79967af29c"
            ),
            "math-245-linear-algebra-7c79967af29c",
        )

    def test_classify_and_retain_names(self) -> None:
        course = {"hyphen": "MATH-212", "compact": "MATH212", "code": "MATH 212"}
        homework = fc.classify_item("Homework 1 Section 1.1.pdf", parent="Assignments")
        self.assertEqual(homework["kind"], "homework")
        self.assertEqual(homework["action"], "retain")
        self.assertTrue(homework["deadline"])
        self.assertEqual(
            fc.suggested_retain_name(course, "Homework 1 Section 1.1.pdf"),
            "MATH-212 Homework-01 Section 1.1.pdf",
        )
        textbook = fc.classify_item(
            "Elementary Linear Algebra 9th Edition.pdf", size=9_000_000
        )
        self.assertEqual(textbook["kind"], "textbook")
        self.assertEqual(textbook["action"], "textbook")
        skip = fc.classify_item("intro.mp4")
        self.assertEqual(skip["action"], "skip")
        prefixed = fc.classify_item(
            "H01--Sec1-1.pdf",
            parent="Differential Equations (MATH212-01-FA2026)/Week 1/H01--Sec1-1.pdf",
        )
        self.assertEqual(prefixed["kind"], "homework")
        self.assertEqual(prefixed["week"], 1)
        reading = fc.classify_item(
            "R01_Section1-1and2-1.pdf",
            parent="Week 1/Reading Guides/R01_Section1-1and2-1.pdf",
        )
        self.assertEqual(reading["kind"], "reading")

    def test_boolean_flags_can_follow_each_other(self) -> None:
        command, payload = fc.parse_invocation(
            ["--class", "MATH 212", "--skip-download", "--skip-convert"],
            default_command="run",
        )
        self.assertEqual(command, "run")
        self.assertEqual(payload["class"], "MATH 212")
        self.assertTrue(payload["skip-download"])
        self.assertTrue(payload["skip-convert"])

    def test_page_citations_and_due_dates(self) -> None:
        text = "Complete pp. 5-6 and page 12. Due: Friday, August 28."
        citations = fc.extract_page_citations(text)
        self.assertEqual(citations[0], {"start": 5, "end": 6})
        self.assertEqual(citations[1], {"start": 12, "end": 12})
        self.assertEqual(fc.printed_spec(citations), "5-6,12")
        self.assertEqual(fc.parse_due_date(text), "2026-08-28")
        self.assertEqual(fc.extract_section_citations("See Section 1.1 and 2.2"), ["1.1", "2.2"])
        self.assertEqual(
            fc.lecture_dates_for_week(1, "MWF 8:00–8:50, OLIN 371"),
            ["2026-08-24", "2026-08-26", "2026-08-28"],
        )

    def test_moodle_urls_use_hostname_prefix(self) -> None:
        self.assertTrue(fc.is_moodle_url("https://moodle.bucknell.edu/course/view.php?id=1"))
        self.assertTrue(fc.is_moodle_url("moodle.example.edu/my"))
        self.assertFalse(fc.is_moodle_url("https://example.com/moodle"))
        self.assertFalse(fc.is_moodle_url("https://learn.example.edu"))
        self.assertFalse(fc.is_moodle_url(""))

    def test_secret_paths_are_skipped(self) -> None:
        self.assertTrue(fc.is_secret_path(Path("config.json")))
        self.assertTrue(fc.is_secret_path(Path("Cookies.txt")))
        self.assertFalse(fc.is_secret_path(Path("Homework 01.pdf")))

    def test_course_blob_matching(self) -> None:
        course = {
            "compact": "MATH212",
            "hyphen": "MATH-212",
            "code": "MATH 212",
            "title": "Differential Equations",
        }
        self.assertTrue(
            fc.course_matches_blob(
                course, "Mathematics (MATH212) FA2026/Homework 1.pdf"
            )
        )
        self.assertFalse(fc.course_matches_blob(course, "CSCI204 FA2026/Lecture.pdf"))
        self.assertFalse(
            fc.course_matches_blob(
                course, "Mathematics (MATH212) FA2025/Homework 1.pdf"
            )
        )
        self.assertFalse(
            fc.course_matches_blob(course, "MATH212 SP2026/Homework 1.pdf")
        )

    def test_powershell_json_args_are_quoted(self) -> None:
        quoted = fc.powershell_file_args(
            ["save_issue", "--labelIds", '["353fdde3-4428-46a7-a145-b88193b1e961"]']
        )
        self.assertEqual(quoted[0], "save_issue")
        self.assertTrue(quoted[2].startswith("'["))
        self.assertTrue(quoted[2].endswith("]'"))

    def test_drive_download_plan_skips_folders_and_exports_docs(self) -> None:
        self.assertEqual(
            fc.drive_download_plan(
                {"id": "folder", "title": "Homework", "mimeType": fc.DRIVE_FOLDER_MIME}
            )["action"],
            "skip_folder",
        )
        pdf = fc.drive_download_plan(
            {"id": "pdf", "title": "Syllabus", "mimeType": "application/pdf"}
        )
        self.assertEqual(pdf["filename"], "Syllabus.pdf")
        doc = fc.drive_download_plan(
            {
                "id": "doc",
                "title": "Assignment Checklist",
                "mimeType": "application/vnd.google-apps.document",
            }
        )
        self.assertEqual(doc["action"], "download")
        self.assertEqual(doc["filename"], "Assignment Checklist.pdf")
        self.assertEqual(doc["exportMimeType"], "application/pdf")

    def test_discover_classes_reads_vault(self) -> None:
        classes = {course["hyphen"]: course for course in fc.discover_classes()}
        self.assertIn("MATH-212", classes)
        self.assertIn("MATH-245", classes)
        math_245 = fc.resolve_class("MATH245")
        self.assertEqual(math_245["hyphen"], "MATH-245")
        self.assertTrue(math_245["drive_folder_id"])

    def test_frontmatter_key_updates(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "note.md"
            path.write_text(
                "---\ntype: assignment\nlinear: JPS-5\ndue: 2026-08-28\n---\nBody\n",
                encoding="utf-8",
            )
            self.assertTrue(fc.strip_frontmatter_keys(path, ["due"]))
            self.assertTrue(
                fc.upsert_frontmatter_key(
                    path, "linear_url", "https://linear.app/example"
                )
            )
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("due:", text)
            self.assertIn("linear_url: https://linear.app/example", text)
            self.assertIn("Body", text)


class LinearApplyTests(unittest.TestCase):
    def test_project_id_matches_url_slug_not_short_slug_id(self) -> None:
        from linear_apply import project_id_for

        course = {
            "code": "MATH 212",
            "hyphen": "MATH-212",
            "linear_slug": "math-212-differential-equations-db95533679b2",
            "linear_project": (
                "https://linear.app/jpdagostino/project/"
                "math-212-differential-equations-db95533679b2"
            ),
        }
        projects = [
            {
                "id": "other",
                "name": "MATH 245 — Linear Algebra",
                "slugId": "7c79967af29c",
                "url": "https://linear.app/jpdagostino/project/math-245-linear-algebra-7c79967af29c",
            },
            {
                "id": "math-212-id",
                "name": "MATH 212 — Differential Equations",
                "slugId": "db95533679b2",
                "url": course["linear_project"],
            },
        ]
        self.assertEqual(project_id_for(course, projects), "math-212-id")

    def test_issue_title_uses_retained_name_and_matches_existing(self) -> None:
        from linear_apply import issue_title, match_existing_issue

        course = {"code": "MATH 212", "hyphen": "MATH-212"}
        item = {
            "name": "H01--Sec1-1.pdf",
            "suggested_name": "MATH-212 H01--Sec1-1.pdf",
            "matched": "attachments/MATH-212 Homework-01 Section-1-1.pdf",
        }
        title = issue_title(course, item)
        self.assertEqual(title, "MATH 212 — Homework-01 Section-1-1")
        matched = match_existing_issue(
            title,
            [
                {
                    "identifier": "JPS-6",
                    "title": "MATH 212 — Homework 01 — Section 1.1",
                    "description": (
                        "Vault source: `attachments/MATH-212 Homework-01 Section-1-1.pdf`"
                    ),
                }
            ],
            item,
        )
        self.assertEqual(matched["identifier"], "JPS-6")
        compact = issue_title(
            course, {"name": "H01--Sec1-1.pdf", "suggested_name": "MATH-212 H01--Sec1-1.pdf"}
        )
        self.assertEqual(compact, "MATH 212 — Homework 01 — Sec1-1")


    def test_unknown_command_lists_known_names(self) -> None:
        from io import StringIO
        from unittest import mock

        stderr = StringIO()
        with mock.patch("sys.stderr", stderr):
            code = fc.run_cli("demo", {"ping": lambda payload: payload}, argv=["upcoming"])
        self.assertEqual(code, 1)
        message = stderr.getvalue()
        self.assertIn("Unknown command: upcoming", message)
        self.assertIn("ping", message)
        self.assertIn("commands", message)

    def test_help_flag_lists_commands_not_default_run(self) -> None:
        from io import StringIO
        from unittest import mock

        stdout = StringIO()
        with mock.patch("sys.stdout", stdout):
            code = fc.run_cli(
                "demo",
                {"run": lambda payload: payload, "ping": lambda payload: payload},
                argv=["--help"],
                default_command="run",
            )
        self.assertEqual(code, 0)
        payload = json.loads(stdout.getvalue())
        self.assertEqual(payload["command"], "commands")
        self.assertIn("ping", payload["data"]["commands"])
        self.assertEqual(payload["data"]["shell"], "powershell")

    def test_empty_argv_keeps_default_command(self) -> None:
        command, payload = fc.parse_invocation([], default_command="run")
        self.assertEqual(command, "run")
        self.assertEqual(payload, {})

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import search_content as sc


class SearchContentTests(unittest.TestCase):
    def test_positional_parse(self) -> None:
        command, payload = sc.parse_invocation(["grep", "courses", "linear:"])
        self.assertEqual(command, "grep")
        self.assertEqual(payload["path"], "courses")
        self.assertEqual(payload["pattern"], "linear:")

    def test_flag_parse(self) -> None:
        command, payload = sc.parse_invocation(
            ["--path", "courses", "--pattern", "foo", "--glob", "*.md", "-i"]
        )
        self.assertEqual(command, "search")
        self.assertEqual(payload["path"], "courses")
        self.assertEqual(payload["pattern"], "foo")
        self.assertEqual(payload["glob"], "*.md")
        self.assertTrue(payload["i"])

    def test_find_lists_glob_matches(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "notes").mkdir()
            (root / "notes" / "Week-01.md").write_text("hello\n", encoding="utf-8")
            (root / "notes" / "Week-02.md").write_text("other\n", encoding="utf-8")
            (root / "skip.txt").write_text("nope\n", encoding="utf-8")
            data = sc.search_content("find", {"path": str(root), "glob": "**/Week-01.md"})
            self.assertEqual(data["mode"], "find")
            self.assertEqual(data["files"], ["notes/Week-01.md"])

    def test_grep_returns_line_matches(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            path = root / "note.md"
            path.write_text("alpha\nlinear: JPS-5\nomega\n", encoding="utf-8")
            data = sc.search_content(
                "grep",
                {
                    "path": str(root),
                    "pattern": "linear:",
                    "glob": "*.md",
                    "context": 1,
                },
            )
            self.assertEqual(data["mode"], "grep")
            self.assertEqual(data["file_count"], 1)
            self.assertEqual(data["matches"][0]["line"], 2)
            self.assertEqual(data["matches"][0]["text"], "linear: JPS-5")
            self.assertEqual(data["matches"][0]["before"], ["alpha"])
            self.assertEqual(data["matches"][0]["after"], ["omega"])

    def test_grep_requires_pattern(self) -> None:
        with self.assertRaises(sc.ToolError) as raised:
            sc.search_content("grep", {"path": ".", "glob": "*.md"})
        self.assertEqual(raised.exception.code, "usage")

    def test_missing_path(self) -> None:
        with self.assertRaises(sc.ToolError) as raised:
            sc.search_content("search", {"path": "no-such-dir-xyz"})
        self.assertEqual(raised.exception.code, "not_found")

    def test_refuses_env_yml_name(self) -> None:
        self.assertTrue(sc.is_secret(Path("C:/vault/.env.yml")))

    def test_glob_matches_basename_anywhere(self) -> None:
        self.assertTrue(sc.glob_matches("courses/MATH-212.md", "*.md"))
        self.assertTrue(sc.glob_matches("courses/notes/Week-01.md", "**/Week-01.md"))
        self.assertFalse(sc.glob_matches("courses/notes/Week-02.md", "**/Week-01.md"))

    def test_files_with_matches_omits_line_payload(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "a.md").write_text("keep\n", encoding="utf-8")
            (root / "b.md").write_text("drop\n", encoding="utf-8")
            data = sc.search_content(
                "search",
                {
                    "path": str(root),
                    "pattern": "keep",
                    "files-with-matches": True,
                },
            )
            self.assertEqual(data["output"], "files")
            self.assertEqual(data["files"], ["a.md"])
            self.assertNotIn("matches", data)


if __name__ == "__main__":
    unittest.main()

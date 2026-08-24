from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import read_file_lines as rfl


class ReadFileLinesTests(unittest.TestCase):
    def test_select_range_defaults_to_whole_file(self) -> None:
        self.assertEqual(rfl.select_range(10), (1, 10))
        self.assertEqual(rfl.select_range(10, start=3, limit=2), (3, 4))
        self.assertEqual(rfl.select_range(10, start=8, end=20), (8, 10))

    def test_reads_inclusive_line_window(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "note.md"
            path.write_text("a\nb\nc\nd\n", encoding="utf-8")
            data = rfl.read_file_lines({"path": str(path), "start": 2, "end": 3})
            self.assertEqual(data["text"], "b\nc")
            self.assertEqual(data["lines"], ["2| b", "3| c"])
            self.assertEqual(data["total"], 4)

    def test_positional_parse(self) -> None:
        command, payload = rfl.parse_invocation(["note.md", "4", "9"])
        self.assertEqual(command, "read")
        self.assertEqual(payload["path"], "note.md")
        self.assertEqual(payload["start"], "4")
        self.assertEqual(payload["end"], "9")

    def test_missing_file(self) -> None:
        with self.assertRaises(rfl.ToolError) as raised:
            rfl.read_file_lines({"path": "no-such-file-xyz.md"})
        self.assertEqual(raised.exception.code, "not_found")

    def test_refuses_env_yml_name(self) -> None:
        with self.assertRaises(rfl.ToolError):
            rfl.assert_not_secret(Path("C:/vault/.env.yml"))


if __name__ == "__main__":
    unittest.main()

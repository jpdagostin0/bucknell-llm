from __future__ import annotations

import json
import unittest
from pathlib import Path

import run_tool


class RunToolTests(unittest.TestCase):
    def test_catalog_includes_session_tools(self) -> None:
        names = run_tool.catalog_names()
        for expected in (
            "linear",
            "gmail",
            "google-drive",
            "google-calendar",
            "moodle-dl",
            "gradescope",
            "selenium",
            "fast-linear",
            "fast-gradescope",
            "fast-selenium",
            "fast-fetch-webpage",
            "fast-import-syllabus",
            "fast-assign-cycles",
            "fast-dashboard",
            "fast-weekly-review",
            "fast-scaffold-work-note",
            "example-tool",
            "read-file-lines",
            "read_file_lines",
        ):
            self.assertIn(expected, names)

    def test_selenium_uses_cli_script(self) -> None:
        command, _, cwd = run_tool.build_command("selenium", ["ping"])
        self.assertEqual(Path(command[1]).name, "selenium_cli.py")
        self.assertEqual(cwd, run_tool.vault_root())
        self.assertEqual(command[-1], "ping")

    def test_example_tool_command_uses_template_script(self) -> None:
        command, _, cwd = run_tool.build_command("example-tool", ["ping"])
        self.assertEqual(Path(command[1]).name, "example_tool.py")
        self.assertEqual(cwd, run_tool.vault_root())
        self.assertEqual(command[-1], "ping")

    def test_read_file_lines_alias_uses_the_same_script(self) -> None:
        hyphen, _, _ = run_tool.build_command("read-file-lines", ["Home.md", "1", "5"])
        underscore, _, _ = run_tool.build_command("read_file_lines", ["Home.md", "1", "5"])
        self.assertEqual(Path(hyphen[1]).name, "read_file_lines.py")
        self.assertEqual(hyphen[1], underscore[1])

    def test_moodle_adds_state_path_unless_present(self) -> None:
        root = run_tool.vault_root()
        exe = root / "tools" / "moodle-dl" / ".venv" / "Scripts" / "moodle-dl.exe"
        if not exe.exists():
            self.skipTest("moodle-dl is not installed")
        command, _, _ = run_tool.build_command("moodle-dl", ["--help"])
        self.assertIn("--path", command)
        command_kept, _, _ = run_tool.build_command(
            "moodle-dl", ["--path", "C:\\tmp", "--help"]
        )
        self.assertEqual(command_kept.count("--path"), 1)

    def test_unknown_tool_lists_known_names(self) -> None:
        with self.assertRaises(run_tool.ToolError) as raised:
            run_tool.spec("not-a-tool", run_tool.vault_root())
        self.assertIn("linear", raised.exception.message)


    def test_catalog_help_mentions_calendar_upcoming(self) -> None:
        import io
        from contextlib import redirect_stdout

        stdout = io.StringIO()
        with redirect_stdout(stdout):
            code = run_tool.main(["--help"])
        self.assertEqual(code, 0)
        payload = json.loads(stdout.getvalue())
        self.assertIn("google-calendar upcoming", payload["data"]["usage"][2])
        self.assertEqual(payload["data"]["shell"], "powershell")

from __future__ import annotations

import json
import tempfile
import unittest
import unittest.mock
from pathlib import Path

import run_tool


class RunToolTests(unittest.TestCase):
    def test_catalog_includes_session_tools(self) -> None:
        names = run_tool.catalog_names()
        for expected in (
            "linear",
            "gmail",
            "google_drive",
            "google_calendar",
            "moodle_dl",
            "fast_google_drive",
            "fast_google_calendar",
            "fast_moodle_dl",
            "gradescope",
            "selenium",
            "fast_linear",
            "fast_gradescope",
            "fast_selenium",
            "fast_fetch_webpage",
            "fast_index_repo",
            "fast_import_syllabus",
            "fast_assign_cycles",
            "fast_dashboard",
            "fast_weekly_review",
            "fast_scaffold_work_note",
            "example_tool",
            "read_file_lines",
            "search_content",
        ):
            self.assertIn(expected, names)

    def test_unlisted_python_tool_is_discovered(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            folder = root / "tools" / "fast_demo"
            folder.mkdir(parents=True)
            (folder / "fast_demo.py").write_text("print(1)\n", encoding="utf-8")
            (folder / "README.md").write_text(
                "---\ntype: tool\n---\n\n# Demo\n", encoding="utf-8"
            )
            catalog = run_tool.tool_catalog(root)
            self.assertIn("fast_demo", catalog)
            self.assertEqual(catalog["fast_demo"]["script"], folder / "fast_demo.py")
            self.assertEqual(
                catalog["fast_demo"]["pythonpath"],
                str(root / "tools" / "fast_common"),
            )

    def test_invoke_false_readme_is_not_discovered(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            folder = root / "tools" / "fast_lib"
            folder.mkdir(parents=True)
            (folder / "fast_lib.py").write_text("print(1)\n", encoding="utf-8")
            (folder / "README.md").write_text(
                "---\ntype: tool\ninvoke: false\n---\n\n# Lib\n",
                encoding="utf-8",
            )
            catalog = run_tool.tool_catalog(root)
            self.assertNotIn("fast_lib", catalog)

    def test_selenium_uses_cli_script(self) -> None:
        command, _, cwd = run_tool.build_command("selenium", ["ping"])
        self.assertEqual(Path(command[1]).name, "selenium_cli.py")
        self.assertEqual(cwd, run_tool.vault_root())
        self.assertEqual(command[-1], "ping")

    def test_example_tool_command_uses_template_script(self) -> None:
        command, _, cwd = run_tool.build_command("example_tool", ["ping"])
        self.assertEqual(Path(command[1]).name, "example_tool.py")
        self.assertEqual(cwd, run_tool.vault_root())
        self.assertEqual(command[-1], "ping")

    def test_read_file_lines_alias_uses_the_same_script(self) -> None:
        hyphen, _, _ = run_tool.build_command("read_file_lines", ["Home.md", "1", "5"])
        underscore, _, _ = run_tool.build_command("read_file_lines", ["Home.md", "1", "5"])
        self.assertEqual(Path(hyphen[1]).name, "read_file_lines.py")
        self.assertEqual(hyphen[1], underscore[1])

    def test_search_content_alias_uses_the_same_script(self) -> None:
        hyphen, _, _ = run_tool.build_command("search_content", ["--glob", "*.md"])
        underscore, _, _ = run_tool.build_command("search_content", ["--glob", "*.md"])
        self.assertEqual(Path(hyphen[1]).name, "search_content.py")
        self.assertEqual(hyphen[1], underscore[1])

    def test_moodle_adds_state_path_unless_present(self) -> None:
        root = run_tool.vault_root()
        python = root / "tools" / "moodle_dl" / ".venv" / "Scripts" / "python.exe"
        if not python.exists():
            self.skipTest("moodle_dl is not installed")
        command, _, _ = run_tool.build_command("moodle_dl", ["--help"])
        self.assertEqual(Path(command[0]).name, "python.exe")
        self.assertEqual(command[1], "-c")
        self.assertNotIn("moodle-dl.exe", command[0])
        self.assertIn("--path", command)
        command_kept, _, _ = run_tool.build_command(
            "moodle_dl", ["--path", "C:\\tmp", "--help"]
        )
        self.assertEqual(command_kept.count("--path"), 1)

    def test_entry_argv_skips_uv_trampolines(self) -> None:
        command = run_tool.entry_argv(
            Path("python.exe"), "moodle_dl.main:main", "moodle-dl", ["--help"]
        )
        self.assertEqual(
            command[:2],
            ["python.exe", "-c"],
        )
        self.assertIn("from moodle_dl.main import main", command[2])
        self.assertEqual(command[3:], ["--", "--help"])

    def test_markitdown_and_pymarkdown_use_python_module(self) -> None:
        root = run_tool.vault_root()
        checked = 0
        for name, module, args in (
            ("markitdown", "markitdown", ["--help"]),
            ("pymarkdown", "pymarkdown", ["version"]),
        ):
            python = root / "tools" / name / ".venv" / "Scripts" / "python.exe"
            if not python.exists():
                continue
            command, _, _ = run_tool.build_command(name, args)
            self.assertEqual(Path(command[0]).name, "python.exe")
            self.assertEqual(command[1:3], ["-m", module])
            checked += 1
        if checked == 0:
            self.skipTest("markitdown and pymarkdown are not installed")

    def test_flint_stays_a_native_exe(self) -> None:
        root = run_tool.vault_root()
        flint = root / "tools" / "flint" / "bin" / "flint.exe"
        if not flint.exists():
            self.skipTest("flint is not installed")
        command, _, _ = run_tool.build_command("flint", ["--help"])
        self.assertEqual(Path(command[0]).name, "flint.exe")

    def test_unknown_tool_lists_known_names(self) -> None:
        with self.assertRaises(run_tool.ToolError) as raised:
            run_tool.spec("not-a-tool", run_tool.vault_root())
        self.assertIn("linear", raised.exception.message)


    def test_catalog_help_is_three_invoke_lines(self) -> None:
        import io
        from contextlib import redirect_stdout

        stdout = io.StringIO()
        with redirect_stdout(stdout):
            code = run_tool.main(["--help"])
        self.assertEqual(code, 0)
        payload = json.loads(stdout.getvalue())
        invoke = payload["data"]["invoke"]
        self.assertEqual(len(invoke), 3)
        self.assertEqual(invoke[0], "python tools/run_tool/run_tool.py commands")
        self.assertEqual(
            invoke[1],
            'python tools/run_tool/run_tool.py fast_dashboard --class "MATH 212"',
        )
        self.assertNotIn("shell", payload["data"])
        self.assertNotIn("rule", payload["data"])

    def test_emulated_python_is_rejected(self) -> None:
        with unittest.mock.patch.object(run_tool.sys, "platform", "emscripten"):
            with self.assertRaises(run_tool.ToolError):
                run_tool.require_host_python()


if __name__ == "__main__":
    unittest.main()

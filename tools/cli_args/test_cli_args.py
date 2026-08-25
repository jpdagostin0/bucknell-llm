from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cli_args as cli


class CliArgsTests(unittest.TestCase):
    def test_scalar_flags_do_not_need_a_json_file(self) -> None:
        command, payload = cli.parse_invocation(
            ["get_issue", "--id", "JPS-5", "--limit", "10"],
            default_command="commands",
        )
        self.assertEqual(command, "get_issue")
        self.assertEqual(payload["id"], "JPS-5")
        self.assertEqual(payload["limit"], 10)

    def test_repeated_flags_build_a_list(self) -> None:
        _, payload = cli.parse_invocation(
            ["run", "--class", "MATH-245", "--class", "MATH-212"],
            default_command="run",
        )
        self.assertEqual(payload["class"], ["MATH-245", "MATH-212"])

    def test_json_and_flags_merge_with_flags_winning(self) -> None:
        _, payload = cli.parse_invocation(
            [
                "save_issue",
                "--json",
                json.dumps({"id": "JPS-5", "title": "from-json"}),
                "--title",
                "from-flag",
                "--apply",
            ]
        )
        self.assertEqual(payload["id"], "JPS-5")
        self.assertEqual(payload["title"], "from-flag")
        self.assertTrue(payload["apply"])

    def test_json_file_then_json_then_flags(self) -> None:
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", suffix=".json", delete=False
        ) as handle:
            handle.write(json.dumps({"id": "JPS-5", "team": "from-file"}))
            path = handle.name
        try:
            _, payload = cli.parse_invocation(
                [
                    "save_issue",
                    "--json-file",
                    path,
                    "--json",
                    json.dumps({"team": "from-json"}),
                    "--title",
                    "Homework 01",
                ]
            )
        finally:
            Path(path).unlink(missing_ok=True)
        self.assertEqual(payload["id"], "JPS-5")
        self.assertEqual(payload["team"], "from-json")
        self.assertEqual(payload["title"], "Homework 01")

    def test_boolean_flags_can_follow_each_other(self) -> None:
        _, payload = cli.parse_invocation(
            ["--class", "MATH 212", "--skip-download", "--skip-convert"],
            default_command="run",
        )
        self.assertEqual(payload["class"], "MATH 212")
        self.assertTrue(payload["skip-download"])
        self.assertTrue(payload["skip-convert"])

    def test_missing_json_file_is_usage_error(self) -> None:
        with self.assertRaises(cli.CliError) as raised:
            cli.parse_invocation(["run", "--json-file", "missing-payload.json"])
        self.assertIn("not found", raised.exception.message)

    def test_fast_runners_reject_json(self) -> None:
        with self.assertRaises(cli.CliError) as raised:
            cli.parse_invocation(
                ["run", "--json", '{"class":"MATH 212"}'],
                allow_json=False,
            )
        self.assertIn("Never pass --json", raised.exception.message)


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import json
import unittest
from io import StringIO
from unittest import mock

import selenium_cli as tool


class SeleniumRoutingTests(unittest.TestCase):
    def test_moodle_host_prefix(self) -> None:
        self.assertTrue(tool.is_moodle_url("https://moodle.bucknell.edu/course/view.php?id=1"))
        self.assertTrue(tool.is_moodle_url("moodle.example.edu"))
        self.assertFalse(tool.is_moodle_url("https://example.com/moodle"))
        self.assertFalse(tool.is_moodle_url("https://csci.example.edu"))

    def test_fetch_rejects_moodle_before_chrome(self) -> None:
        with self.assertRaises(tool.ToolError) as raised:
            tool.require_http_url("https://moodle.example.edu/my")
        self.assertEqual(raised.exception.code, "routing")

    def test_fetch_rejects_non_http(self) -> None:
        with self.assertRaises(tool.ToolError) as raised:
            tool.require_http_url("file:///C:/secrets.txt")
        self.assertEqual(raised.exception.code, "safety")

    def test_chrome_missing_error_is_explicit(self) -> None:
        hint = tool.chrome_hint(FileNotFoundError(2, "The system cannot find the file specified"))
        self.assertIn("Helium", hint)

    def test_helium_is_preferred_browser_candidate(self) -> None:
        first = tool.browser_candidates()[0]
        self.assertEqual(first, tool.DEFAULT_HELIUM)
        self.assertTrue(str(first).endswith("imput\\Helium\\Application\\chrome.exe") or "Helium" in str(first))

    def test_page_slug_is_filename_safe(self) -> None:
        slug = tool.page_slug("https://example.com/path/to/page?q=1")
        self.assertNotIn("/", slug)
        self.assertNotIn("?", slug)
        self.assertTrue(slug.startswith("example-com"))

    def test_commands_lists_fetch(self) -> None:
        stdout = StringIO()
        with mock.patch("sys.stdout", stdout):
            code = tool.main(["commands"])
        self.assertEqual(code, 0)
        payload = json.loads(stdout.getvalue())
        self.assertIn("fetch", payload["data"]["commands"])
        self.assertIn("navigate", payload["data"]["commands"])
        self.assertEqual(len(payload["data"]["invoke"]), 3)
        self.assertIn("run_tool.py selenium commands", payload["data"]["invoke"][0])


if __name__ == "__main__":
    unittest.main()

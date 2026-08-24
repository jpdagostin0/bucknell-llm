from __future__ import annotations

import unittest

from fast_common import ToolError
from fast_fetch_webpage import run


class FastFetchWebpageTests(unittest.TestCase):
    def test_moodle_urls_are_rejected(self) -> None:
        with self.assertRaises(ToolError) as raised:
            run({"url": "https://moodle.example.edu/course/view.php?id=1"})
        self.assertEqual(raised.exception.code, "routing")


if __name__ == "__main__":
    unittest.main()

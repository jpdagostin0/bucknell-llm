from __future__ import annotations

import contextlib
import io
import subprocess
import tempfile
import unittest
from pathlib import Path

import yaml

from validate_vault import SCHEMAS, Validator


VAULT_ROOT = Path(__file__).resolve().parents[2]


class VaultValidatorTests(unittest.TestCase):
    def test_current_vault_passes(self) -> None:
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            result = Validator(VAULT_ROOT).run()
        self.assertEqual(result, 0, output.getvalue())

    def test_unknown_markdown_path_is_unscoped(self) -> None:
        validator = Validator(VAULT_ROOT)
        self.assertIsNone(validator._classify(Path("rogue.md")))

    def test_schema_rejects_wrong_type_unknown_and_mutable_fields(self) -> None:
        validator = Validator(VAULT_ROOT)
        metadata = {
            "type": "week",
            "linear": "JPS-1",
            "class": "[[courses/TEST-100-Course-Fall-2026/TEST-100]]",
            "kind": "pset",
            "due": "2026-09-01",
            "extra": "unexpected",
        }
        validator._validate_schema(
            VAULT_ROOT / "courses" / "example.md",
            metadata,
            SCHEMAS["assignment"],
        )
        combined = "\n".join(validator.errors)
        self.assertIn("type must be 'assignment'", combined)
        self.assertIn("Linear-owned fields are forbidden: due", combined)
        self.assertIn("unknown fields for assignment: due, extra", combined)

    def test_wikilinks_must_be_qualified_and_resolve(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            note = root / "Home.md"
            note.write_text(
                "[[Syllabus]]\n[[courses/Missing/Course]]\n",
                encoding="utf-8",
            )
            validator = Validator(root)
            validator._validate_wikilinks(note)
            combined = "\n".join(validator.errors)
            self.assertIn("wikilink must be path-qualified", combined)
            self.assertIn("wikilink target does not exist", combined)


class FlintIntegrationTests(unittest.TestCase):
    def test_every_content_block_has_one_path(self) -> None:
        config = yaml.safe_load((VAULT_ROOT / ".flint.yml").read_text(encoding="utf-8"))
        for block in config["content"]:
            self.assertEqual(
                len(block["paths"]),
                1,
                f"{block['name']} would trigger Flint 0.0.6's path overwrite bug",
            )

    def test_flint_rejects_invalid_course_index(self) -> None:
        flint = VAULT_ROOT / "tools" / "flint" / "bin" / "flint.exe"
        if not flint.exists():
            self.skipTest("Flint is not installed")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            course = root / "courses" / "TEST-100-Course-Fall-2026"
            course.mkdir(parents=True)
            (course / "TEST-100.md").write_text(
                "\n".join(
                    (
                        "---",
                        "type: class",
                        "code: bad",
                        "credits: nope",
                        "meetings:",
                        "linear_project: http://example.com",
                        "---",
                        "",
                        "# Invalid Fixture",
                        "",
                    )
                ),
                encoding="utf-8",
            )
            result = subprocess.run(
                (
                    str(flint),
                    "--config",
                    str(VAULT_ROOT / ".flint.yml"),
                    "--color=false",
                    str(root),
                ),
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertIn("CLASS001", result.stdout)
            self.assertIn("CLASS003", result.stdout)
            self.assertIn("CLASS004", result.stdout)


if __name__ == "__main__":
    unittest.main()

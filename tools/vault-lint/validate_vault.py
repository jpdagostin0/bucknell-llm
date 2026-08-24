from __future__ import annotations

import datetime as dt
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import yaml


FORBIDDEN_FIELDS = {"status", "due", "priority", "estimate"}
FORBIDDEN_FILENAME_CHARACTERS = set("#|^[]:")
KINDS = {
    "pset",
    "reading",
    "lab",
    "quiz",
    "exam",
    "course project",
    "study",
    "admin",
}
LINEAR_KEY = re.compile(r"^[A-Z][A-Z0-9]*-[0-9]+$")
COURSE_CODE = re.compile(r"^[A-Z]{2,4} [0-9]{3}$")
COURSE_FOLDER = re.compile(
    r"^(?P<code>[A-Z]{2,4}-[0-9]{3})"
    r"(?:-[A-Za-z0-9]+)+-Fall-2026$"
)
WEEK_FILE = re.compile(r"^Week-(?P<number>[0-9]{2})\.md$")
WORK_FILE = re.compile(r"^(?P<code>[A-Z]{2,4}-[0-9]{3}) .+\.md$")
COURSE_PREFIXED_FILE = re.compile(r"^[A-Z]{2,4}-[0-9]{3} .+")
NUMBERED_ITEM = re.compile(
    r"(?:Homework|Assignment|Quiz|Lab|Exam)[ -](?P<number>[0-9]+)",
    re.IGNORECASE,
)
WIKILINK = re.compile(r"\[\[([^\]]+)\]\]")


@dataclass(frozen=True)
class Schema:
    note_type: str
    required: frozenset[str]
    allowed: frozenset[str]


SCHEMAS = {
    "dashboard": Schema(
        "dashboard",
        frozenset({"type", "title"}),
        frozenset({"type", "title"}),
    ),
    "schedule": Schema(
        "schedule",
        frozenset({"type", "term"}),
        frozenset({"type", "term"}),
    ),
    "class": Schema(
        "class",
        frozenset(
            {
                "type",
                "code",
                "title",
                "credits",
                "meetings",
                "linear_project",
            }
        ),
        frozenset(
            {
                "type",
                "code",
                "title",
                "instructor",
                "credits",
                "meetings",
                "linear_project",
                "content",
            }
        ),
    ),
    "syllabus": Schema(
        "syllabus",
        frozenset({"type", "class", "source"}),
        frozenset({"type", "class", "source"}),
    ),
    "week": Schema(
        "week",
        frozenset({"type", "class", "week", "lectures", "unit"}),
        frozenset({"type", "class", "week", "lectures", "unit"}),
    ),
    "assignment": Schema(
        "assignment",
        frozenset({"type", "linear", "class", "kind"}),
        frozenset(
            {
                "type",
                "linear",
                "linear_url",
                "class",
                "kind",
                "parent",
                "worked",
            }
        ),
    ),
    "capture": Schema(
        "capture",
        frozenset({"type", "captured"}),
        frozenset({"type", "captured", "class"}),
    ),
}


class Validator:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.errors: list[str] = []

    def error(self, path: Path, message: str) -> None:
        relative = path.relative_to(self.root).as_posix()
        self.errors.append(f"{relative}: {message}")

    def run(self) -> int:
        self._validate_required_structure()
        notes: list[tuple[Path, Schema, bool]] = []
        for path in sorted(self.root.rglob("*.md")):
            relative = path.relative_to(self.root)
            if self._is_ignored_documentation(relative):
                continue
            classification = self._classify(relative)
            if classification is None:
                self.error(path, "Markdown file is outside the approved vault layout")
                continue
            schema, is_template = classification
            notes.append((path, schema, is_template))

        for path, schema, is_template in notes:
            metadata = self._read_frontmatter(path)
            if metadata is None:
                continue
            self._validate_schema(path, metadata, schema)
            self._validate_values(path, metadata, schema, is_template)
            if not is_template:
                self._validate_wikilinks(path)

        self._validate_managed_names()
        self._validate_course_indexes()

        for message in self.errors:
            print(message)
        if self.errors:
            print(f"{len(self.errors)} vault integrity error(s)")
            return 1
        print("No vault integrity errors found")
        return 0

    def _validate_required_structure(self) -> None:
        required = (
            "Home.md",
            "classes.md",
            "inbox",
            "courses",
            "templates",
            "attachments",
            "tools",
            "skills",
            "templates/Assignment.md",
            "templates/Class Index.md",
            "templates/Parent Deliverable.md",
            "templates/Syllabus.md",
            "templates/Week.md",
        )
        for relative in required:
            path = self.root / relative
            if not path.exists():
                self.error(path, "required vault path is missing")

    @staticmethod
    def _is_ignored_documentation(relative: Path) -> bool:
        return (
            relative.as_posix() == "AGENTS.md"
            or relative.parts[0] in {"skills", "tools"}
        )

    def _classify(self, relative: Path) -> tuple[Schema, bool] | None:
        normalized = relative.as_posix()
        if normalized == "Home.md":
            return SCHEMAS["dashboard"], False
        if normalized == "classes.md":
            return SCHEMAS["schedule"], False
        if len(relative.parts) == 2 and relative.parts[0] == "inbox":
            return SCHEMAS["capture"], False
        if len(relative.parts) == 2 and relative.parts[0] == "templates":
            template_types = {
                "Assignment.md": "assignment",
                "Class Index.md": "class",
                "Parent Deliverable.md": "assignment",
                "Syllabus.md": "syllabus",
                "Week.md": "week",
            }
            note_type = template_types.get(relative.name)
            if note_type:
                return SCHEMAS[note_type], True
            return None
        if relative.parts[0] != "courses" or len(relative.parts) < 3:
            return None

        if len(relative.parts) == 3:
            if relative.name == "Syllabus.md":
                return SCHEMAS["syllabus"], False
            if re.fullmatch(r"[A-Z]{2,4}-[0-9]{3}\.md", relative.name):
                return SCHEMAS["class"], False
            return None
        if (
            len(relative.parts) == 4
            and relative.parts[2] == "notes"
            and WEEK_FILE.fullmatch(relative.name)
        ):
            return SCHEMAS["week"], False
        if len(relative.parts) == 4 and relative.parts[2] == "work":
            return SCHEMAS["assignment"], False
        return None

    def _read_frontmatter(self, path: Path) -> dict[str, Any] | None:
        text = path.read_text(encoding="utf-8-sig")
        lines = text.splitlines()
        if not lines or lines[0] != "---":
            self.error(path, "missing YAML frontmatter")
            return None
        try:
            closing = lines.index("---", 1)
        except ValueError:
            self.error(path, "frontmatter has no closing delimiter")
            return None
        try:
            loaded = yaml.safe_load("\n".join(lines[1:closing]))
        except yaml.YAMLError as exc:
            self.error(path, f"invalid YAML frontmatter: {exc}")
            return None
        if not isinstance(loaded, dict):
            self.error(path, "frontmatter must be a mapping")
            return None
        if not all(isinstance(key, str) for key in loaded):
            self.error(path, "frontmatter keys must be strings")
            return None
        return loaded

    def _validate_schema(
        self,
        path: Path,
        metadata: dict[str, Any],
        schema: Schema,
    ) -> None:
        actual_type = metadata.get("type")
        if actual_type != schema.note_type:
            self.error(
                path,
                f"type must be {schema.note_type!r}, found {actual_type!r}",
            )
        missing = sorted(schema.required - metadata.keys())
        if missing:
            self.error(path, f"missing required fields: {', '.join(missing)}")
        forbidden = sorted(FORBIDDEN_FIELDS & metadata.keys())
        if forbidden:
            self.error(path, f"Linear-owned fields are forbidden: {', '.join(forbidden)}")
        unknown = sorted(metadata.keys() - schema.allowed)
        if unknown:
            self.error(path, f"unknown fields for {schema.note_type}: {', '.join(unknown)}")
        for key in schema.required:
            if key in metadata and self._is_empty(metadata[key]):
                self.error(path, f"required field {key!r} cannot be empty")

    @staticmethod
    def _is_empty(value: Any) -> bool:
        return value is None or value == "" or value == []

    def _validate_values(
        self,
        path: Path,
        metadata: dict[str, Any],
        schema: Schema,
        is_template: bool,
    ) -> None:
        if schema.note_type == "dashboard":
            self._require_string(path, metadata, "title")
        elif schema.note_type == "schedule":
            self._require_string(path, metadata, "term")
        elif schema.note_type == "class":
            self._validate_class(path, metadata, is_template)
        elif schema.note_type == "syllabus":
            self._validate_syllabus(path, metadata, is_template)
        elif schema.note_type == "week":
            self._validate_week(path, metadata, is_template)
        elif schema.note_type == "assignment":
            self._validate_assignment(path, metadata, is_template)
        elif schema.note_type == "capture":
            self._validate_capture(path, metadata)

    def _validate_class(
        self,
        path: Path,
        metadata: dict[str, Any],
        is_template: bool,
    ) -> None:
        code = self._require_string(path, metadata, "code")
        for key in ("title", "meetings"):
            self._require_string(path, metadata, key)
        if "instructor" in metadata:
            self._require_string(path, metadata, "instructor")
        elif not is_template and self._has_instructor_syllabus(path):
            self.error(path, "instructor is required after importing an instructor syllabus")
        credits = metadata.get("credits")
        if (
            isinstance(credits, bool)
            or not isinstance(credits, (int, float))
            or credits <= 0
        ):
            self.error(path, "credits must be a positive number")
        self._require_url(path, metadata, "linear_project", host="linear.app")
        if "content" in metadata:
            self._require_url(path, metadata, "content")
        if not is_template and code and COURSE_CODE.fullmatch(code):
            expected_filename = code.replace(" ", "-") + ".md"
            if path.name != expected_filename:
                self.error(path, f"class index filename must be {expected_filename}")
            folder_match = COURSE_FOLDER.fullmatch(path.parent.name)
            if not folder_match or folder_match.group("code") != code.replace(" ", "-"):
                self.error(path, "class code does not match its course folder")
        elif code and not COURSE_CODE.fullmatch(code) and not is_template:
            self.error(path, "code must match DEPT 000")

    @staticmethod
    def _has_instructor_syllabus(class_index: Path) -> bool:
        syllabus = class_index.parent / "Syllabus.md"
        if not syllabus.exists():
            return False
        lines = syllabus.read_text(encoding="utf-8-sig").splitlines()
        if not lines or lines[0] != "---":
            return False
        try:
            closing = lines.index("---", 1)
            metadata = yaml.safe_load("\n".join(lines[1:closing]))
        except (ValueError, yaml.YAMLError):
            return False
        return isinstance(metadata, dict) and isinstance(
            metadata.get("source"), str
        ) and metadata["source"].startswith("[[attachments/")

    def _validate_syllabus(
        self,
        path: Path,
        metadata: dict[str, Any],
        is_template: bool,
    ) -> None:
        self._require_class_link(path, metadata, is_template)
        source = self._require_string(path, metadata, "source")
        if source and not (self._is_url(source) or self._is_wikilink(source)):
            self.error(path, "source must be an HTTPS URL or wikilink")

    def _validate_week(
        self,
        path: Path,
        metadata: dict[str, Any],
        is_template: bool,
    ) -> None:
        self._require_class_link(path, metadata, is_template)
        week = metadata.get("week")
        if isinstance(week, bool) or not isinstance(week, int) or not 1 <= week <= 99:
            self.error(path, "week must be an integer from 1 through 99")
        lectures = metadata.get("lectures")
        if not isinstance(lectures, list) or not lectures:
            self.error(path, "lectures must be a non-empty list of ISO dates")
        else:
            for value in lectures:
                if not self._is_date(value):
                    self.error(path, f"invalid lecture date: {value!r}")
        self._require_string(path, metadata, "unit")
        if not is_template:
            match = WEEK_FILE.fullmatch(path.name)
            if match and isinstance(week, int) and int(match.group("number")) != week:
                self.error(path, "week number does not match the filename")

    def _validate_assignment(
        self,
        path: Path,
        metadata: dict[str, Any],
        is_template: bool,
    ) -> None:
        linear = self._require_string(path, metadata, "linear")
        if linear and not LINEAR_KEY.fullmatch(linear):
            self.error(path, "linear must be a stable issue key such as JPS-123")
        self._require_class_link(path, metadata, is_template)
        kind = self._require_string(path, metadata, "kind")
        if kind and kind not in KINDS:
            self.error(path, f"kind must be one of: {', '.join(sorted(KINDS))}")
        if "linear_url" in metadata:
            self._require_url(path, metadata, "linear_url", host="linear.app")
        if "parent" in metadata:
            self._require_wikilink(path, metadata, "parent")
        if "worked" in metadata:
            worked = metadata["worked"]
            if not isinstance(worked, list) or not all(
                isinstance(item, str) and self._is_wikilink(item) for item in worked
            ):
                self.error(path, "worked must be a list of wikilinks")
        if not is_template:
            match = WORK_FILE.fullmatch(path.name)
            if not match:
                self.error(path, "work-note filename must begin with DEPT-000 and a space")
            elif match.group("code") != path.parents[1].name[: len(match.group("code"))]:
                self.error(path, "work-note prefix does not match its course folder")

    def _validate_capture(self, path: Path, metadata: dict[str, Any]) -> None:
        if not self._is_date(metadata.get("captured"), allow_datetime=True):
            self.error(path, "captured must be an ISO date or datetime")
        if "class" in metadata:
            self._require_wikilink(path, metadata, "class")

    def _require_class_link(
        self,
        path: Path,
        metadata: dict[str, Any],
        is_template: bool,
    ) -> None:
        value = self._require_wikilink(path, metadata, "class")
        if is_template or not value:
            return
        course_folder = path.relative_to(self.root).parts[1]
        match = COURSE_FOLDER.fullmatch(course_folder)
        if not match:
            self.error(path, "owning course folder is invalid")
            return
        expected = f"[[courses/{course_folder}/{match.group('code')}]]"
        if value != expected:
            self.error(path, f"class must point to the owning index: {expected}")

    def _require_string(
        self,
        path: Path,
        metadata: dict[str, Any],
        key: str,
    ) -> str | None:
        value = metadata.get(key)
        if not isinstance(value, str) or not value.strip():
            if key in metadata:
                self.error(path, f"{key} must be a non-empty string")
            return None
        return value

    def _require_wikilink(
        self,
        path: Path,
        metadata: dict[str, Any],
        key: str,
    ) -> str | None:
        value = self._require_string(path, metadata, key)
        if value and not self._is_wikilink(value):
            self.error(path, f"{key} must be a wikilink")
            return None
        return value

    def _require_url(
        self,
        path: Path,
        metadata: dict[str, Any],
        key: str,
        host: str | None = None,
    ) -> str | None:
        value = self._require_string(path, metadata, key)
        if not value:
            return None
        parsed = urlparse(value)
        if parsed.scheme != "https" or not parsed.netloc:
            self.error(path, f"{key} must be an HTTPS URL")
        elif host and parsed.netloc != host:
            self.error(path, f"{key} must use {host}")
        return value

    @staticmethod
    def _is_url(value: str) -> bool:
        parsed = urlparse(value)
        return parsed.scheme == "https" and bool(parsed.netloc)

    @staticmethod
    def _is_wikilink(value: str) -> bool:
        return bool(re.fullmatch(r"\[\[[^\[\]]+\]\]", value))

    @staticmethod
    def _is_date(value: Any, allow_datetime: bool = False) -> bool:
        if isinstance(value, dt.datetime):
            return allow_datetime
        if isinstance(value, dt.date):
            return True
        if not isinstance(value, str):
            return False
        try:
            if allow_datetime and "T" in value:
                dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
            else:
                dt.date.fromisoformat(value)
        except ValueError:
            return False
        return True

    def _validate_wikilinks(self, path: Path) -> None:
        text = path.read_text(encoding="utf-8-sig")
        for match in WIKILINK.finditer(text):
            target = match.group(1).split("|", 1)[0].split("#", 1)[0].strip()
            if not target:
                continue
            if "\\" in target:
                self.error(path, f"wikilink must use forward slashes: [[{match.group(1)}]]")
                continue
            if "/" not in target:
                self.error(path, f"wikilink must be path-qualified: [[{match.group(1)}]]")
                continue
            candidate = self.root / target
            if candidate.exists():
                continue
            if candidate.suffix == "" and candidate.with_suffix(".md").exists():
                continue
            self.error(path, f"wikilink target does not exist: [[{match.group(1)}]]")

    def _validate_managed_names(self) -> None:
        managed_roots = ("courses", "attachments", "inbox", "templates")
        for root_name in managed_roots:
            root = self.root / root_name
            if not root.exists():
                continue
            for path in root.rglob("*"):
                relative = path.relative_to(self.root)
                if any(character in path.name for character in FORBIDDEN_FILENAME_CHARACTERS):
                    self.error(path, "filename contains a forbidden character")
                numbered = NUMBERED_ITEM.search(path.stem)
                if numbered and len(numbered.group("number")) != 2:
                    self.error(path, "assignment-like numbers must be zero-padded")
                if (
                    path.is_file()
                    and root_name == "attachments"
                    and path.name != ".gitkeep"
                    and not COURSE_PREFIXED_FILE.fullmatch(path.name)
                ):
                    self.error(path, "attachment filename must begin with DEPT-000 and a space")
                if (
                    path.is_file()
                    and len(relative.parts) >= 4
                    and relative.parts[0] == "courses"
                    and relative.parts[2] == "textbooks"
                    and not COURSE_PREFIXED_FILE.fullmatch(path.name)
                ):
                    self.error(path, "textbook filename must begin with DEPT-000 and a space")

        courses = self.root / "courses"
        if courses.exists():
            for path in courses.iterdir():
                if path.is_dir() and not COURSE_FOLDER.fullmatch(path.name):
                    self.error(path, "course folder does not match DEPT-000-Title-Fall-2026")

    def _validate_course_indexes(self) -> None:
        courses = self.root / "courses"
        if not courses.exists():
            return
        for course in sorted(path for path in courses.iterdir() if path.is_dir()):
            folder_match = COURSE_FOLDER.fullmatch(course.name)
            if not folder_match:
                continue
            code = folder_match.group("code")
            class_index = course / f"{code}.md"
            syllabus = course / "Syllabus.md"
            notes = course / "notes"
            work = course / "work"
            for required in (class_index, syllabus, notes, work):
                if not required.exists():
                    self.error(required, "required course path is missing")
            if not class_index.exists():
                continue

            linked = self._wikilink_targets(class_index)
            expected: list[Path] = []
            if syllabus.exists():
                expected.append(syllabus)
            if notes.exists():
                expected.extend(sorted(notes.glob("*.md")))
            if work.exists():
                expected.extend(sorted(work.glob("*.md")))
            textbooks = course / "textbooks"
            if textbooks.exists():
                expected.extend(sorted(path for path in textbooks.iterdir() if path.is_file()))

            for target in expected:
                normalized = self._normalized_target(target.relative_to(self.root).as_posix())
                if normalized not in linked:
                    self.error(
                        class_index,
                        f"class index does not link {target.relative_to(self.root).as_posix()}",
                    )

            if not work.exists() or not notes.exists():
                continue
            for work_note in sorted(work.glob("*.md")):
                metadata = self._read_frontmatter(work_note)
                if not metadata or "worked" not in metadata:
                    continue
                work_target = self._normalized_target(
                    work_note.relative_to(self.root).as_posix()
                )
                for week_link in metadata["worked"]:
                    if not isinstance(week_link, str) or not self._is_wikilink(week_link):
                        continue
                    raw_target = week_link[2:-2].split("|", 1)[0].split("#", 1)[0]
                    week_path = self.root / (
                        raw_target
                        if Path(raw_target).suffix
                        else f"{raw_target}.md"
                    )
                    if week_path.exists() and work_target not in self._wikilink_targets(week_path):
                        self.error(
                            week_path,
                            f"week note does not link back to {work_note.name}",
                        )

    def _wikilink_targets(self, path: Path) -> set[str]:
        text = path.read_text(encoding="utf-8-sig")
        targets: set[str] = set()
        for match in WIKILINK.finditer(text):
            target = match.group(1).split("|", 1)[0].split("#", 1)[0].strip()
            if target:
                targets.add(self._normalized_target(target))
        return targets

    @staticmethod
    def _normalized_target(target: str) -> str:
        return target[:-3] if target.endswith(".md") else target


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    return Validator(root).run()


if __name__ == "__main__":
    raise SystemExit(main())

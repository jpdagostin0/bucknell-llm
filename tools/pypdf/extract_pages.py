from __future__ import annotations

import argparse
import re
from pathlib import Path

from pypdf import PdfReader, PdfWriter


def parse_ranges(specification: str) -> list[int]:
    values: list[int] = []
    for part in specification.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            start_text, end_text = part.split("-", 1)
            start = int(start_text)
            end = int(end_text)
            if start > end:
                raise ValueError(f"Invalid descending range: {part}")
            values.extend(range(start, end + 1))
        else:
            values.append(int(part))
    if not values:
        raise ValueError("At least one page is required.")
    return values


def resolve_pdf_pages(page_numbers: list[int], page_count: int) -> list[int]:
    indices = [number - 1 for number in page_numbers]
    invalid = [number for number in page_numbers if number < 1 or number > page_count]
    if invalid:
        raise ValueError(
            f"PDF page numbers out of range: {invalid}; document has {page_count} pages."
        )
    return indices


def resolve_page_labels(
    requested_labels: list[int], labels: list[str], page_count: int
) -> list[int]:
    if len(labels) != page_count:
        raise ValueError("The PDF does not expose a complete page-label map.")

    indices: list[int] = []
    for requested in requested_labels:
        requested_text = str(requested)
        matches = [index for index, label in enumerate(labels) if label == requested_text]
        if len(matches) != 1:
            raise ValueError(
                f"Printed page label {requested_text!r} matched {len(matches)} pages. "
                "Use --list-labels and then select physical pages with --pages."
            )
        indices.append(matches[0])
    return indices


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Extract selected pages from a trusted local PDF."
    )
    parser.add_argument("input", type=Path, help="Source PDF path")
    parser.add_argument("output", type=Path, nargs="?", help="Output PDF path")
    selection = parser.add_mutually_exclusive_group()
    selection.add_argument(
        "--pages",
        help="One-based physical PDF pages, for example 5-6,9",
    )
    selection.add_argument(
        "--printed-pages",
        help="Numeric printed page labels, for example 5-6",
    )
    parser.add_argument(
        "--list-labels",
        action="store_true",
        help="Print physical page numbers and PDF page labels without extracting",
    )
    parser.add_argument(
        "--find-section",
        help="Print printed page labels whose text contains this section id",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    source = args.input.resolve(strict=True)
    if source.suffix.lower() != ".pdf":
        raise ValueError("Input must be a PDF.")

    reader = PdfReader(source)
    page_count = len(reader.pages)
    labels = list(reader.page_labels)

    if args.list_labels:
        for index, label in enumerate(labels, start=1):
            print(f"{index}\t{label}")
        return 0

    if args.find_section:
        needle = str(args.find_section).strip()
        patterns = [
            re.compile(rf"\bsection\s+{re.escape(needle)}\b", re.I),
            re.compile(rf"\bsec\.?\s+{re.escape(needle)}\b", re.I),
            re.compile(rf"§\s*{re.escape(needle)}\b"),
        ]
        for index, page in enumerate(reader.pages):
            text = page.extract_text() or ""
            if any(pattern.search(text) for pattern in patterns):
                print(labels[index] if index < len(labels) else str(index + 1))
        return 0

    if args.output is None:
        raise ValueError("Output path is required when extracting pages.")
    if not args.pages and not args.printed_pages:
        raise ValueError("Select pages with --pages or --printed-pages.")

    if args.pages:
        indices = resolve_pdf_pages(parse_ranges(args.pages), page_count)
    else:
        indices = resolve_page_labels(
            parse_ranges(args.printed_pages), labels, page_count
        )

    destination = args.output.resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        raise FileExistsError(f"Refusing to overwrite existing file: {destination}")

    writer = PdfWriter()
    for index in indices:
        writer.add_page(reader.pages[index])
    with destination.open("wb") as output_file:
        writer.write(output_file)

    print(destination)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

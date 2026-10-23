"""Extract searchable text from the labour-law PDF collection.

Usage:
    python scripts/extract.py
    python scripts/extract.py --source raw_pdfs --destination text

The source PDFs are never modified. Each output file contains page boundaries
as ``[[PAGE]]`` markers so later phases can retain source-page information.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import fitz  # PyMuPDF


PAGE_MARKER = "\n\n[[PAGE]]\n\n"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def extract_pdf(
    pdf_path: Path, destination: Path, source_name: str | None = None
) -> dict[str, object]:
    with fitz.open(pdf_path) as document:
        pages = [page.get_text("text") for page in document]

    output_path = destination / f"{pdf_path.stem}.txt"
    output_path.write_text(PAGE_MARKER.join(pages), encoding="utf-8")

    page_lengths = [len(page.strip()) for page in pages]
    short_pages = sum(length < 200 for length in page_lengths)
    return {
        "source_file": source_name or pdf_path.name,
        "extracted_from": pdf_path.name,
        "text_file": output_path.name,
        "pages": len(pages),
        "characters": sum(page_lengths),
        "short_pages": short_pages,
        "sha256": sha256(pdf_path),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=Path("raw_pdfs"))
    parser.add_argument("--destination", type=Path, default=Path("text"))
    parser.add_argument(
        "--ocr-source",
        type=Path,
        help="optional directory containing OCR-derived PDFs overriding matching source PDFs",
    )
    args = parser.parse_args()

    if not args.source.is_dir():
        parser.error(f"source directory does not exist: {args.source}")

    pdfs = sorted(args.source.glob("*.pdf"))
    if not pdfs:
        parser.error(f"no PDF files found in {args.source}")

    args.destination.mkdir(parents=True, exist_ok=True)
    reports = []
    for pdf in pdfs:
        input_pdf = pdf
        if args.ocr_source:
            ocr_pdf = args.ocr_source / pdf.name
            if ocr_pdf.exists():
                input_pdf = ocr_pdf
        reports.append(extract_pdf(input_pdf, args.destination, source_name=pdf.name))
    report_path = args.destination / "extraction_report.json"
    report_path.write_text(
        json.dumps(reports, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    duplicate_groups: dict[str, list[str]] = {}
    for report in reports:
        duplicate_groups.setdefault(str(report["sha256"]), []).append(
            str(report["source_file"])
        )
    duplicates = [files for files in duplicate_groups.values() if len(files) > 1]
    short_page_files = [
        report for report in reports if int(report["short_pages"]) > 0
    ]

    print(f"Extracted {len(reports)} PDFs into {args.destination}/")
    print(f"Pages: {sum(int(r['pages']) for r in reports):,}")
    print(f"Characters: {sum(int(r['characters']) for r in reports):,}")
    print(f"Short-page warnings (<200 chars): {len(short_page_files)} files")
    print(f"Exact duplicate groups: {len(duplicates)}")

    if short_page_files:
        print("\nPossible scans or sparse pages:")
        for report in short_page_files:
            print(
                f"  {report['source_file']}: "
                f"{report['short_pages']}/{report['pages']} short pages"
            )
    if duplicates:
        print("\nExact duplicate groups:")
        for group in duplicates:
            print("  " + ", ".join(group))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())


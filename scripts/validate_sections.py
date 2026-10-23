"""Run Phase 3 quality checks over the generated section records.

The report is intentionally conservative: warnings are surfaced for legal
review rather than silently corrected. Known cross-document conflicts are
linked with ``conflict_status: lawyer_review_required``.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path


SECTIONS = Path("sections")
REPORT = SECTIONS / "qc_report.json"
SHORT_WORD_LIMIT = 10
ODD_SYMBOLS = re.compile(r"[�]|Â§|â€“|â€”|â€™|â€œ|â€")
HEADER_LIKE = re.compile(r"^\d{1,4}\s+[A-Z][A-Z &(),.'-]{4,}$")


def load_records() -> tuple[list[Path], list[dict]]:
    files = sorted(p for p in SECTIONS.glob("*.json") if p.name not in {"split_report.json", "qc_report.json"})
    records: list[dict] = []
    for path in files:
        records.extend(json.loads(path.read_text(encoding="utf-8")))
    return files, records


def add_conflict(records: list[dict], ids: list[str], description: str) -> None:
    for record in records:
        if record["id"] in ids:
            record.setdefault("conflicts_with", [])
            for other in ids:
                if other != record["id"] and other not in record["conflicts_with"]:
                    record["conflicts_with"].append(other)
            record["conflict_status"] = "lawyer_review_required"
            record.setdefault("conflict_notes", []).append(description)


def main() -> int:
    files, records = load_records()
    text_report_path = Path("text") / "extraction_report.json"
    text_report = {}
    if text_report_path.exists():
        text_report = {
            item["source_file"]: item["pages"]
            for item in json.loads(text_report_path.read_text(encoding="utf-8"))
        }

    warnings: list[dict] = []
    seen_ids: Counter[str] = Counter(record["id"] for record in records)
    for record in records:
        text = record.get("text", "")
        issues: list[str] = []
        if len(text.split()) < SHORT_WORD_LIMIT:
            issues.append("fewer_than_10_words")
        if "[[PAGE]]" in text:
            issues.append("page_marker_remaining")
        if ODD_SYMBOLS.search(text):
            issues.append("suspicious_encoding_symbols")
        if any(HEADER_LIKE.match(line.strip()) for line in text.splitlines()):
            issues.append("possible_repeated_header")
        max_page = text_report.get(record.get("source_file"))
        if max_page and not (1 <= int(record["source_page"]) <= int(max_page)):
            issues.append("source_page_out_of_range")
        if seen_ids[record["id"]] > 1:
            issues.append("duplicate_id")
        if issues:
            warnings.append({"id": record["id"], "source_file": record["source_file"], "issues": issues})

    # These are intentionally unresolved links; a lawyer must determine which
    # rule controls for the user's facts and the applicable edition/amendments.
    conflicts = [
        (
            [
                "ch01_industrial_disputes_act_s31c",
                "ch01_industrial_disputes_hearing_and_determination_of_proceeding_s5",
            ],
            "Labour tribunal deadline appears as six months versus four months in the compiled sources.",
        ),
        (
            [
                "ch01_termination_of_employment_of_workmen_s2",
                "ch01_industrial_disputes_hearing_and_determination_of_proceeding_s11",
            ],
            "Commissioner's decision deadline appears as three months versus two months in the compiled sources.",
        ),
    ]
    for ids, description in conflicts:
        add_conflict(records, ids, description)

    by_file: dict[str, list[dict]] = {}
    for record in records:
        by_file.setdefault(record["source_file"], []).append(record)
    for path in files:
        file_records = by_file.get(path.with_suffix(".pdf").name, [])
        path.write_text(json.dumps(file_records, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    report = {
        "files_checked": len(files),
        "records_checked": len(records),
        "warning_count": len(warnings),
        "warnings": warnings,
        "known_conflicts": [
            {"record_ids": ids, "description": description, "status": "lawyer_review_required"}
            for ids, description in conflicts
        ],
        "all_records_status": Counter(record.get("status") for record in records),
        "manual_review_required": True,
        "manual_review_notes": [
            "Confirm section boundaries and OCR against the source PDFs.",
            "Confirm each Act is in force and capture post-edition amendments.",
            "Approve plain-language summaries before using them in answers.",
            "Review all fines, rates, allowances, and compensation formulas as time-sensitive.",
        ],
    }
    REPORT.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Checked {len(files)} files and {len(records):,} records")
    print(f"Warnings: {len(warnings):,}")
    print(f"Known conflicts linked for legal review: {len(conflicts)}")
    print("Manual legal review required: yes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


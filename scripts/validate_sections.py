"""Run Phase 3 quality checks over the generated section records.

The report is intentionally conservative: warnings are surfaced for source-quality follow-up rather than silently corrected. Known cross-document conflicts are linked with conservative operational cautions; formal reviewer sign-off is not a project gate.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path


SECTIONS = Path("sections")
REPORT = SECTIONS / "qc_report.json"
SHORT_REVIEW = Path("audit") / "short_section_review.json"
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
            record["conflict_status"] = "operational_caution"
            notes = record.setdefault("conflict_notes", [])
            if description not in notes:
                notes.append(description)


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
    reviewed_items = {}
    if SHORT_REVIEW.exists():
        reviewed_items = {
            item["record_id"]: item
            for item in json.loads(SHORT_REVIEW.read_text(encoding="utf-8"))["items"]
        }
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
            warning = {
                "id": record["id"],
                "source_file": record["source_file"],
                "source_page": record.get("source_page"),
                "issues": issues,
            }
            disposition = reviewed_items.get(record["id"])
            if (
                disposition
                and disposition.get("source_pdf") == record.get("source_file")
                and disposition.get("source_page") == record.get("source_page")
            ):
                warning["review_disposition"] = disposition.get("disposition")
                warning["review_rationale"] = disposition.get("rationale")
            warnings.append(warning)

    warning_ids = {warning["id"] for warning in warnings}
    unreviewed_warnings = [
        warning["id"] for warning in warnings if "review_disposition" not in warning
    ]
    stale_dispositions = sorted(set(reviewed_items) - warning_ids)

    required_fields = (
        "act_name", "act_number_year", "doc_type", "section_number", "text",
        "source_file", "source_page", "scope_notes", "scope_status", "topics", "status",
    )
    metadata_gaps: list[dict] = []
    for record in records:
        for field in required_fields:
            value = record.get(field)
            missing = value is None or value == "" or (field == "topics" and not value)
            if missing:
                metadata_gaps.append({"id": record["id"], "field": field})

    # These cross-document links preserve the conflict and operational caution;
    # the validator does not decide which rule controls for a user's facts.
    conflicts = [
        (
            [
                "ch01_industrial_disputes_act_s31c",
                "ch01_industrial_disputes_hearing_and_determination_of_proceeding_s5",
            ],
            "Labour tribunal deadline appears as six months versus four months in the compiled sources; cite both and retain the conservative four-month operational target.",
        ),
        (
            [
                "ch01_termination_of_employment_of_workmen_s2",
                "ch01_industrial_disputes_hearing_and_determination_of_proceeding_s11",
            ],
            "Commissioner's decision deadline appears as three months versus two months in the compiled sources; cite both and retain the conservative two-month operational target.",
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
        "reviewed_warning_count": len(warnings) - len(unreviewed_warnings),
        "unreviewed_warning_count": len(unreviewed_warnings),
        "unreviewed_warning_ids": unreviewed_warnings,
        "stale_disposition_count": len(stale_dispositions),
        "stale_disposition_ids": stale_dispositions,
        "metadata_gap_count": len(metadata_gaps),
        "metadata_gaps": metadata_gaps,
        "phase_2_closeout_pass": not unreviewed_warnings and not stale_dispositions and not metadata_gaps,
        "warnings": warnings,
        "known_conflicts": [
            {"record_ids": ids, "description": description, "status": "operational_caution"}
            for ids, description in conflicts
        ],
        "all_records_status": Counter(record.get("status") for record in records),
        "manual_quality_checks_advisable": True,
        "formal_legal_reviewer_gate": "waived_by_owner; see audit/legal_review_gate_waiver.md",
        "manual_review_notes": [
            "Confirm section boundaries and OCR against the source PDFs.",
            "Confirm each Act is in force and capture post-edition amendments.",
            "Keep the AI/current-law warning visible; formal reviewer sign-off is waived by owner decision.",
            "Review all fines, rates, allowances, and compensation formulas as time-sensitive.",
        ],
    }
    REPORT.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Checked {len(files)} files and {len(records):,} records")
    print(f"Warnings: {len(warnings):,}")
    print(f"Reviewed warnings: {len(warnings) - len(unreviewed_warnings):,}; unreviewed: {len(unreviewed_warnings):,}")
    print(f"Required metadata gaps: {len(metadata_gaps):,}")
    print(f"Phase 2 closeout pass: {'yes' if report['phase_2_closeout_pass'] else 'no'}")
    print(f"Known conflicts linked with operational cautions: {len(conflicts)}")
    print("Formal legal reviewer gate: waived by owner decision")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


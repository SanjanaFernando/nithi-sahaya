"""Compare a fresh split with enriched records, then keep reviewed metadata."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CURRENT = ROOT / "sections"
CANDIDATE = ROOT / "audit" / "split_candidate"
INDEX_RECORDS = ROOT / "index" / "records.json"
REPORT = ROOT / "audit" / "split_comparison.json"
REPORTS = {"qc_report.json", "split_report.json"}
CORE_FIELDS = (
    "id", "act_name", "doc_type", "chapter", "section_number", "heading",
    "text", "source_file", "source_page",
)


def load_records(directory: Path) -> dict[str, dict]:
    records = {}
    for path in sorted(directory.glob("*.json")):
        if path.name in REPORTS:
            continue
        for record in json.loads(path.read_text(encoding="utf-8")):
            if record["id"] in records:
                raise ValueError(f"duplicate section ID: {record['id']}")
            records[record["id"]] = record
    return records


def required_metadata_gaps(records: dict[str, dict]) -> list[dict]:
    required = (
        "act_name", "act_number_year", "doc_type", "section_number", "text",
        "source_file", "source_page", "scope_notes", "scope_status", "topics", "status",
    )
    gaps = []
    for record in records.values():
        for field in required:
            value = record.get(field)
            if value is None or value == "" or (field == "topics" and not value):
                gaps.append({"id": record["id"], "field": field})
    return gaps


def main() -> int:
    previous = load_records(CURRENT)
    fresh = load_records(CANDIDATE)
    if set(previous) != set(fresh):
        raise ValueError(
            f"split IDs changed: {len(set(previous) - set(fresh))} removed, "
            f"{len(set(fresh) - set(previous))} added"
        )

    core_changes = []
    field_comparisons = Counter()
    preserved_metadata_fields = Counter()
    merged = {}
    for record_id, new_record in fresh.items():
        old_record = previous[record_id]
        for field in CORE_FIELDS:
            field_comparisons[field] += 1
            if old_record.get(field) != new_record.get(field):
                core_changes.append({
                    "id": record_id,
                    "field": field,
                    "previous": str(old_record.get(field))[:160],
                    "fresh_split": str(new_record.get(field))[:160],
                })
        if core_changes:
            continue
        # Keep all curated metadata and reviewer annotations from the existing
        # record; the splitter owns only the core text and source fields above.
        for field, value in old_record.items():
            if field not in CORE_FIELDS:
                new_record[field] = value
                preserved_metadata_fields[field] += 1
        merged[record_id] = new_record

    if core_changes:
        raise ValueError(f"fresh split changed {len(core_changes)} core record fields")
    gaps = required_metadata_gaps(merged)
    if gaps:
        raise ValueError(f"required metadata gaps after merge: {len(gaps)}")

    by_file: dict[str, list[dict]] = {}
    for record in merged.values():
        by_file.setdefault(record["source_file"].replace(".pdf", ".json"), []).append(record)
    for filename, records in by_file.items():
        (CURRENT / filename).write_text(
            json.dumps(records, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )

    split_report = CANDIDATE / "split_report.json"
    (CURRENT / "split_report.json").write_text(
        split_report.read_text(encoding="utf-8"), encoding="utf-8"
    )

    index_records = json.loads(INDEX_RECORDS.read_text(encoding="utf-8"))
    if len(index_records) != len(merged):
        raise ValueError("active index record count differs from merged sections")
    for index_record in index_records:
        record = merged.get(index_record["id"])
        if record is None:
            raise ValueError(f"active index ID missing from sections: {index_record['id']}")
        for field in ("act_name", "section_number", "heading", "text"):
            if index_record.get(field) != record.get(field):
                raise ValueError(f"active index embedding text differs for {record['id']} field {field}")
        index_record.update(record)
    INDEX_RECORDS.write_text(
        json.dumps(index_records, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    count_by_source = Counter(record["source_file"] for record in merged.values())
    previous_by_source = Counter(record["source_file"] for record in previous.values())
    fresh_by_source = Counter(record["source_file"] for record in fresh.values())
    extraction_report = json.loads((ROOT / "text" / "extraction_report.json").read_text(encoding="utf-8"))
    max_pages = {item["source_file"]: int(item["pages"]) for item in extraction_report}
    page_range_failures = [
        {"id": record["id"], "source_file": record["source_file"], "source_page": record["source_page"],
         "extracted_pages": max_pages.get(record["source_file"])}
        for record in merged.values()
        if record["source_file"] not in max_pages or not (1 <= int(record["source_page"]) <= max_pages[record["source_file"]])
    ]
    report = {
        "comparison": "passed",
        "previous_record_count": len(previous),
        "fresh_split_record_count": len(fresh),
        "merged_record_count": len(merged),
        "record_ids_match": True,
        "core_field_changes": core_changes,
        "core_field_comparisons": dict(field_comparisons),
        "section_number_comparison": {"records_compared": len(merged), "changes": sum(1 for r in merged.values() if previous[r["id"]].get("section_number") != r.get("section_number"))},
        "source_page_reference_comparison": {"records_compared": len(merged), "changes": sum(1 for r in merged.values() if previous[r["id"]].get("source_file") != r.get("source_file") or previous[r["id"]].get("source_page") != r.get("source_page")), "out_of_range_count": len(page_range_failures), "out_of_range": page_range_failures},
        "per_source_record_counts_match": previous_by_source == fresh_by_source,
        "previous_record_count_by_source": dict(sorted(previous_by_source.items())),
        "fresh_record_count_by_source": dict(sorted(fresh_by_source.items())),
        "required_metadata_gap_count": len(gaps),
        "preserved_metadata_field_counts": dict(preserved_metadata_fields),
        "record_count_by_source": dict(sorted(count_by_source.items())),
        "active_index_records_synchronized": len(index_records),
        "vectors_rebuilt": False,
    }
    REPORT.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Split comparison passed: {len(previous):,} IDs; core fields unchanged")
    print(f"Metadata gaps: {len(gaps)}; synchronized index records: {len(index_records):,}")
    print(f"Comparison report: {REPORT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Fill the two missing Phase 2 Act identifiers from their title pages."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import fitz


ROOT = Path(__file__).resolve().parents[1]
SECTIONS = ROOT / "sections"
INDEX_RECORDS = ROOT / "index" / "records.json"
TEXT_REPORT = ROOT / "text" / "extraction_report.json"
AUDIT_REPORT = ROOT / "audit" / "act_number_year_review.json"

SOURCES = {
    "ch07_minimum_wages.pdf": {
        "act_name": "Minimum Wages (Indian Labour) Ordinance",
        "value": "Ordinance No. 27 of 1927",
        "title_page_identifiers": [
            "Ordinance No. 27 of 1927",
            "Ordinance No. 34 of 1935",
            "Act No. 25 of 2000",
        ],
        "official_url": "https://labourdept.gov.lk/downloads/labour_code/62.pdf",
        "reason": "The official Department of Labour copy lists Ordinances Nos. 27 of 1927 and 34 of 1935, and Act No. 25 of 2000; the original ordinance identifier is 27 of 1927.",
    },
    "ch07_service_contracts.pdf": {
        "act_name": "Service Contracts Ordinance",
        "value": "Ordinance No. 11 of 1865",
        "title_page_identifiers": [
            "Ordinance No. 11 of 1865",
            "Ordinance No. 16 of 1884",
            "Ordinance No. 16 of 1905",
            "Ordinance No. 23 of 1912",
            "Ordinance No. 41 of 1916",
            "Ordinance No. 43 of 1921",
            "Ordinance No. 27 of 1927",
        ],
        "official_url": "https://labourdept.gov.lk/labour-code-of-sri-lanka/",
        "reason": "The source title page lists Ordinances Nos. 11 of 1865, 16 of 1884, 16 of 1905, 23 of 1912, 41 of 1916, 43 of 1921, and 27 of 1927. The original ordinance identifier is 11 of 1865; the separately printed 1 July 1866 date is not its number/year.",
    },
}


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def main() -> int:
    extraction = {item["source_file"]: item for item in load(TEXT_REPORT)}
    section_files = sorted(
        path for path in SECTIONS.glob("*.json")
        if path.name not in {"qc_report.json", "split_report.json"}
    )
    updates: dict[str, dict] = {}
    audit_sources = {}
    missing_before = []

    for path in section_files:
        records = load(path)
        changed = False
        for record in records:
            if str(record.get("act_number_year", "")).strip():
                continue
            missing_before.append(record)
            source = record["source_file"]
            spec = SOURCES.get(source)
            if not spec or record["act_name"] != spec["act_name"]:
                raise ValueError(f"No verified source mapping for {record['id']}")
            record["act_number_year"] = spec["value"]
            updates[record["id"]] = record
            changed = True
            if source not in audit_sources:
                pdf = ROOT / "raw_pdfs" / source
                with fitz.open(pdf) as document:
                    title_page = document[0].get_text("text").strip()
                if not title_page:
                    raise ValueError(f"Title page has no extractable text: {source}")
                report_row = extraction[source]
                audit_sources[source] = {
                    "act_name": spec["act_name"],
                    "assigned_value": spec["value"],
                    "source_pdf": f"raw_pdfs/{source}",
                    "source_pdf_sha256": report_row["sha256"],
                    "title_page": 1,
                    "title_page_identifiers": spec["title_page_identifiers"],
                    "title_page_text_excerpt": title_page[:1500],
                    "official_reference": spec["official_url"],
                    "reason": spec["reason"],
                }
        if changed:
            path.write_text(json.dumps(records, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    if len(missing_before) != 31 or len(updates) != 31:
        raise ValueError(f"Expected 31 missing records; found {len(missing_before)}")

    indexed = load(INDEX_RECORDS)
    indexed_updates = 0
    for record in indexed:
        replacement = updates.get(record["id"])
        if replacement:
            if record.get("text") != replacement.get("text"):
                raise ValueError(f"Section/index text mismatch for {record['id']}")
            record["act_number_year"] = replacement["act_number_year"]
            indexed_updates += 1
    if indexed_updates != 31:
        raise ValueError(f"Expected to update 31 active-index records; updated {indexed_updates}")
    INDEX_RECORDS.write_text(json.dumps(indexed, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    report = {
        "review_date": "2026-10-25",
        "field": "act_number_year",
        "records_updated": len(updates),
        "unknown_records": [],
        "sources": audit_sources,
        "records": [
            {
                "record_id": record_id,
                "source_pdf": updates[record_id]["source_file"],
                "act_name": updates[record_id]["act_name"],
                "value": updates[record_id]["act_number_year"],
                "evidence_page": 1,
            }
            for record_id in sorted(updates)
        ],
    }
    AUDIT_REPORT.parent.mkdir(parents=True, exist_ok=True)
    AUDIT_REPORT.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Filled act_number_year for {len(updates)} records from two title pages")
    print(f"Synchronized {indexed_updates} active index records without changing vectors")
    print(f"Evidence: {AUDIT_REPORT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

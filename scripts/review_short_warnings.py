"""Create source-linked dispositions for short-page and short-section warnings."""

from __future__ import annotations

import json
from pathlib import Path

import fitz


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "raw_pdfs"
OCR = ROOT / "ocr_pdfs"
TEXT = ROOT / "text"
SECTIONS = ROOT / "sections"
OUT = ROOT / "audit"
PAGE_LIMIT = 200
WORD_LIMIT = 10


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def load_records() -> dict[str, dict]:
    result = {}
    for path in SECTIONS.glob("*.json"):
        if path.name in {"qc_report.json", "split_report.json"}:
            continue
        for record in read_json(path):
            result[record["id"]] = record
    return result


def page_text(path: Path, page_number: int) -> str:
    with fitz.open(path) as document:
        return document[page_number - 1].get_text("text").strip()


def page_disposition(source: str, page: int) -> tuple[str, str]:
    specific = {
        ("ch02_wages_boards_ordinance.pdf", 2): (
            "valid_running_header",
            "The source page contains only its folio and the Wages Boards running title.",
        ),
        ("ch03_employment_of_female_in_mines_ordinance.pdf", 2): (
            "valid_running_header",
            "The source page contains only its folio and the Employment of Females in Mines running title.",
        ),
        ("ch04_factories_ordinance.pdf", 1): (
            "valid_chapter_contents_page",
            "The source page is the Chapter 4 divider and contents list, not operative law.",
        ),
        ("ch04_factories_ordinance.pdf", 2): (
            "valid_running_header",
            "The source page contains only its folio and the Factories running title.",
        ),
        ("ch05_employees_provident_fund.pdf", 2): (
            "valid_running_header",
            "The source page contains only its folio and the Employees' Provident Fund running title.",
        ),
        ("ch06_fee_charging_employment_agencies.pdf", 1): (
            "valid_chapter_contents_page",
            "The source page is the Chapter 6 divider and contents list, not operative law.",
        ),
        ("ch06_fee_charging_employment_agencies.pdf", 2): (
            "valid_running_header",
            "The source page contains only its folio and the Fee-Charging Employment Agencies running title.",
        ),
        ("ch07_estate_labour_indian.pdf", 2): (
            "valid_running_header",
            "The source page contains only its folio and the Estate Labour running title.",
        ),
    }
    if (source, page) not in specific:
        raise ValueError(f"unreviewed short page: {source} p.{page}")
    return specific[(source, page)]


def classify_section(record: dict) -> tuple[str, str]:
    source = record["source_file"]
    page = int(record["source_page"])
    record_id = record["id"]

    if source == "ch04_factories_ordinance_regulations_and_forms_1_13.pdf":
        if page in {23, 24, 26, 31}:
            return (
                "regulation_title_continuation",
                "The source page starts a regulation instrument; the short text completes its formal title/year after the heading field.",
            )
        if page in {27, 28, 29}:
            return (
                "schedule_quantity_row",
                "The source page is a first-aid schedule table; this record is one item name or its prescribed quantity.",
            )
        if page == 34:
            return (
                "schedule_form_field",
                "The source page is Schedule II, Form 13; this record is a numbered field on the prescribed industrial-disease notice.",
            )
        if 2 <= page <= 17:
            return (
                "prescribed_form_field",
                "The source page is a prescribed Factories Ordinance form; this record is a prompt, blank, or continuation of a form field.",
            )
        raise ValueError(f"unreviewed Factories short record: {record_id} p.{page}")

    toc_ids = {
        "ch01_industrial_disputes_act_s2",
        "ch01_industrial_disputes_act_s4",
        "ch02_wages_boards_ordinance_s2",
    }
    if record_id in toc_ids:
        return (
            "chapter_contents_entry",
            "The source page is a chapter contents list; this is an Act title entry, not an operative section.",
        )

    part_heading_ids = {
        "ch02_wages_boards_ordinance_s1",
        "ch03_employment_of_women_young_person_and_children_s1",
        "ch05_employees_provident_fund_regulations_s1",
        "ch05_employees_trust_fund_regulations_s1",
    }
    if record_id in part_heading_ids:
        return (
            "part_or_trade_heading",
            "The source page shows a Part/trade heading alongside the short-title clause; this is a structural heading, not a truncated rule.",
        )

    short_title_ids = {
        "ch01_employees_councils_regulations_s1",
        "ch01_termination_of_employment_of_workmen_s1",
        "ch02_budgetary_relief_allowance_of_workers_act_no_4_of_2016_s1",
        "ch03_employment_of_female_in_mines_ordinance_s1",
        "ch03_employment_of_women_young_person_and_children_regulations_s1",
        "ch03_employment_of_women_young_person_and_children_regulations_s1_p2_2",
        "ch05_employees_trust_fund_special_provisions_s1",
    }
    if record_id in short_title_ids:
        return (
            "short_title_clause",
            "The source page's short-title sentence is split between heading and body by a line wrap/page split; the combined fields contain the full cited title.",
        )

    if record_id == "ch01_trade_unions_ordinance_s3_p17_2":
        return (
            "marginal_section_heading",
            "The source page presents this phrase as the section's marginal heading; it is a valid short heading.",
        )

    if source == "ch02_shop_and_office_employees_regulations.pdf":
        if page == 21:
            return (
                "gazette_schedule_officer_entry",
                "The source page's Gazette order schedule lists appointed Department of Labour officers; this is one complete list entry.",
            )
        return (
            "prescribed_form_field",
            "The source page contains prescribed service-record fields; the OCR text in the body represents a blank dotted field, not legal prose.",
        )

    if source == "ch04_workmens_compensation_regulations.pdf":
        if record_id == "ch04_workmens_compensation_regulations_s47":
            return (
                "complete_provision_continuation",
                "The source page's heading and body together form the complete rule limiting a party to one set of costs.",
            )
        return (
            "prescribed_form_field",
            "The source page is a prescribed compensation form; the short text completes a field label or supplies a remarks prompt.",
        )

    if source == "ch05_employees_provident_fund_regulations.pdf":
        if record_id == "ch05_employees_provident_fund_regulations_s53":
            return (
                "complete_short_provision",
                "The source contains a complete operative sentence appointing a Tribunal secretary; it is short but not truncated.",
            )
        if record_id == "ch05_employees_provident_fund_regulations_s5_p27_2":
            return (
                "cross_reference_note",
                "The source form contains a parenthetical cross-reference to section 23 of the Act.",
            )
        return (
            "prescribed_form_field",
            "The source page is a prescribed EPF return, cessation, death-benefit, or member form; this is a field label or blank column.",
        )

    if source == "ch05_employees_provident_fund_regulations_part_2.pdf":
        return (
            "employment_category_entry",
            "The source page lists an employment category; the heading and body together give the complete category wording.",
        )

    if source == "ch05_employees_trust_fund_regulations.pdf":
        if record_id == "ch05_employees_trust_fund_regulations_s1_p18_2":
            return (
                "employment_category_entry",
                "The source page lists a covered-employment category; the heading and body together give the complete category wording.",
            )
        return (
            "prescribed_form_field",
            "The source page is a prescribed ETF form; this record is a property-report field or blank entry.",
        )

    if source == "ch06_sri_lanka_bureau_of_foreign_employment_act.pdf":
        return (
            "schedule_fee_table_row",
            "The source page is a fee table; this record contains one salary band and its corresponding fee.",
        )

    if source == "ch07_medical_wants.pdf":
        if record_id == "ch07_medical_wants_s6_p16_3":
            return (
                "prescribed_form_field",
                "The source page is a medical form; this is the blank charge field.",
            )
        if record_id == "ch07_medical_wants_s12_p11_2":
            return (
                "complete_provision_continuation",
                "The heading and body together state the complete visiting-hours provision.",
            )
        return (
            "complete_short_provision",
            "The source page contains a complete rule requiring separate accommodation for males and females.",
        )

    raise ValueError(f"unreviewed short section: {record_id} ({source} p.{page})")


def main() -> int:
    extraction = read_json(TEXT / "extraction_report.json")
    extraction_by_source = {item["source_file"]: item for item in extraction}
    qc = read_json(SECTIONS / "qc_report.json")
    records = load_records()
    OUT.mkdir(parents=True, exist_ok=True)

    page_items = []
    for report in extraction:
        source = report["source_file"]
        raw_path = RAW / source
        raw_doc = fitz.open(raw_path)
        selected_path = (
            OCR / source
            if report.get("used_ocr_override") and (OCR / source).exists()
            else raw_path
        )
        selected_doc = fitz.open(selected_path)
        if len(raw_doc) != len(selected_doc):
            raise ValueError(f"page-count mismatch for {source}")
        for index, (raw_page, selected_page) in enumerate(zip(raw_doc, selected_doc), start=1):
            raw_text = raw_page.get_text("text").strip()
            if len(raw_text) >= PAGE_LIMIT:
                continue
            selected_text = selected_page.get_text("text").strip()
            if selected_path != raw_path:
                if len(selected_text) < PAGE_LIMIT:
                    raise ValueError(f"OCR did not recover {source} p.{index}")
                disposition = "repaired_using_existing_ocr_copy"
                rationale = (
                    "The source PDF page is image-only or has fewer than 200 text characters; "
                    "the matching OCR copy supplies searchable text now present in the extraction. "
                    "OCR wording still requires normal legal proofreading."
                )
            else:
                disposition, rationale = page_disposition(source, index)
                if not selected_text:
                    rationale += " No substantive text is present on the source page image."
            page_items.append({
                "source_pdf": source,
                "page": index,
                "raw_text_characters": len(raw_text),
                "extraction_source": selected_path.relative_to(ROOT).as_posix(),
                "extracted_text_characters": len(selected_text),
                "disposition": disposition,
                "rationale": rationale,
                "source_page_text": selected_text[:800],
            })
        raw_doc.close()
        selected_doc.close()

    if len(page_items) != 82:
        raise ValueError(f"expected 82 page warnings, reviewed {len(page_items)}")
    page_report = {
        "review_date": "2026-10-25",
        "threshold_characters": PAGE_LIMIT,
        "warning_count": len(page_items),
        "repaired_with_ocr": sum(item["disposition"] == "repaired_using_existing_ocr_copy" for item in page_items),
        "valid_sparse_pages": sum(item["disposition"].startswith("valid_") for item in page_items),
        "items": page_items,
    }
    (OUT / "short_page_review.json").write_text(
        json.dumps(page_report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    evidence_pages: dict[str, dict] = {}
    section_items = []
    for warning in qc["warnings"]:
        record = records[warning["id"]]
        category, rationale = classify_section(record)
        source = record["source_file"]
        page = int(record["source_page"])
        key = f"{source}#p{page}"
        if key not in evidence_pages:
            raw_path = RAW / source
            raw_text = page_text(raw_path, page)
            extraction_row = extraction_by_source[source]
            if len(raw_text) < PAGE_LIMIT and extraction_row.get("used_ocr_override"):
                evidence_text = page_text(OCR / source, page)
                evidence_source = f"ocr_pdfs/{source}"
            else:
                evidence_text = raw_text
                evidence_source = f"raw_pdfs/{source}"
            evidence_pages[key] = {
                "source_pdf": source,
                "page": page,
                "evidence_source": evidence_source,
                "page_text_characters": len(evidence_text),
                "page_text": evidence_text,
            }
        section_items.append({
            "record_id": record["id"],
            "source_pdf": source,
            "source_page": page,
            "section_number": record.get("section_number"),
            "heading": record.get("heading", ""),
            "text": record.get("text", ""),
            "word_count": len(record.get("text", "").split()),
            "qc_issues": warning["issues"],
            "disposition": category,
            "rationale": rationale,
            "source_evidence_key": key,
        })

    if len(section_items) != qc["warning_count"] or len(section_items) != 158:
        raise ValueError(f"expected 158 section warnings, reviewed {len(section_items)}")
    section_report = {
        "review_date": "2026-10-25",
        "word_limit_exclusive": WORD_LIMIT,
        "warning_count": len(section_items),
        "dispositions": {},
        "items": section_items,
        "source_pages": evidence_pages,
        "review_note": (
            "Shortness alone does not mean a split error. Each item is linked to its source page; "
            "form blanks, headings, contents entries, schedule rows, cross-references, and complete "
            "short provisions are retained with their specific disposition. OCR-derived text must "
            "still receive legal proofreading before public use."
        ),
    }
    for item in section_items:
        category = item["disposition"]
        section_report["dispositions"][category] = section_report["dispositions"].get(category, 0) + 1
    (OUT / "short_section_review.json").write_text(
        json.dumps(section_report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(
        f"Reviewed {len(page_items)} short pages: "
        f"{page_report['repaired_with_ocr']} OCR repairs, {page_report['valid_sparse_pages']} valid sparse pages"
    )
    print(f"Reviewed {len(section_items)} short section records: {section_report['dispositions']}")
    print(f"Reports: {OUT / 'short_page_review.json'}, {OUT / 'short_section_review.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

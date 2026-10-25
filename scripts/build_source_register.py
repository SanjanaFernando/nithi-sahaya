"""Build a source inventory for the 44 Department of Labour corpus PDFs."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PDF_DIR = ROOT / "raw_pdfs"
SECTIONS = ROOT / "sections"
OUT_JSON = ROOT / "audit" / "source_register.json"
OUT_CSV = ROOT / "audit" / "source_register.csv"
OFFICIAL_CATALOG = "https://labourdept.gov.lk/labour-code-of-sri-lanka/"
REVIEW_DATE = "2026-10-25"

# English titles as listed in the Department of Labour's Labour Code catalogue.
TITLES = {
    "ch00_minimum_retirement_age_of_workers.pdf": "Minimum Retirement Age of Workers Act, No. 28 of 2021",
    "ch01_employees_councils.pdf": "Employees' Councils Act",
    "ch01_employees_councils_regulations.pdf": "Employees' Councils (Orders and Regulations)",
    "ch01_industrial_disputes_act.pdf": "Industrial Disputes Act",
    "ch01_industrial_disputes_hearing_and_determination_of_proceeding.pdf": "Industrial Disputes (Hearing and Determination of Proceedings) (Special Provisions) Act",
    "ch01_termination_of_employment_of_workmen.pdf": "Termination of Employment of Workmen (Special Provisions) Act",
    "ch01_trade_unions_ordinance.pdf": "Trade Unions Ordinance",
    "ch02_budgetary_relief_allowance_of_workers_act_no_1.pdf": "Budgetary Relief Allowance of Workers (No. 1) Law",
    "ch02_budgetary_relief_allowance_of_workers_act_no_2.pdf": "Budgetary Relief Allowance of Workers (No. 2) Law",
    "ch02_budgetary_relief_allowance_of_workers_act_no_3.pdf": "Budgetary Relief Allowance of Workers Act",
    "ch02_budgetary_relief_allowance_of_workers_act_no_4_of_2016.pdf": "Budgetary Relief Allowance of Workers Act, No. 4 of 2016",
    "ch02_employment_of_trainees_private_sector.pdf": "Employment of Trainees (Private Sector) Act",
    "ch02_national_minimum_wage_of_workers_act_no_3_of_2016.pdf": "National Minimum Wage of Workers Act, No. 3 of 2016",
    "ch02_shop_and_office_employees.pdf": "Shop and Office Employees (Regulation of Employment and Remuneration) Act",
    "ch02_shop_and_office_employees_regulations.pdf": "Shop and Office Employees Regulations",
    "ch02_wages_boards_ordinance.pdf": "Wages Boards Ordinance",
    "ch03_employment_of_female_in_mines_ordinance.pdf": "Employment of Females in Mines Ordinance",
    "ch03_employment_of_women_young_person_and_children.pdf": "Employment of Women, Young Persons and Children Act",
    "ch03_employment_of_women_young_person_and_children_regulations.pdf": "Employment of Women, Young Persons and Children Regulations",
    "ch03_maternity_benefits_ordinance.pdf": "Maternity Benefits Ordinance",
    "ch03_maternity_benefits_ordinance_regulations.pdf": "Maternity Benefits Regulations",
    "ch04_factories_ordinance.pdf": "Factories Ordinance",
    "ch04_factories_ordinance_regulations_and_forms_1_13.pdf": "Factories Ordinance Regulations and Forms 1–13",
    "ch04_workmens_compensation.pdf": "Workmen's Compensation Ordinance",
    "ch04_workmens_compensation_regulations.pdf": "Workmen's Compensation Regulations",
    "ch05_employees_provident_fund.pdf": "Employees' Provident Fund Act",
    "ch05_employees_provident_fund_regulations.pdf": "Employees' Provident Fund Regulations",
    "ch05_employees_provident_fund_regulations_part_2.pdf": "Employees' Provident Fund Regulations (Part 2)",
    "ch05_employees_provident_fund_special_provisions.pdf": "Employees' Provident Fund (Special Provisions) Law",
    "ch05_employees_trust_fund.pdf": "Employees' Trust Fund Act",
    "ch05_employees_trust_fund_regulations.pdf": "Employees' Trust Fund Regulations",
    "ch05_employees_trust_fund_special_provisions.pdf": "Employees' Trust Fund (Special Provisions) Act",
    "ch05_payment_of_gratuity.pdf": "Payment of Gratuity Act",
    "ch06_fee_charging_employment_agencies.pdf": "Fee-Charging Employment Agencies Act",
    "ch06_sri_lanka_bureau_of_foreign_employment_act.pdf": "Sri Lanka Bureau of Foreign Employment Act",
    "ch06_sri_lanka_bureau_of_foreign_employment_act_regulations.pdf": "Sri Lanka Bureau of Foreign Employment Act Regulations and Orders",
    "ch07_allowances_to_plantation_workers.pdf": "Allowances to Plantation Workers Act",
    "ch07_estate_labour_indian.pdf": "Estate Labour (Indian) Ordinance",
    "ch07_estates_quarters.pdf": "Estates Quarters (Special Provisions) Act",
    "ch07_indian_immigrant_labour.pdf": "Indian Immigrant Labour Ordinance",
    "ch07_medical_wants.pdf": "Medical Wants Ordinance",
    "ch07_minimum_wages.pdf": "Minimum Wages (Indian Labour) Ordinance",
    "ch07_service_contracts.pdf": "Service Contracts Ordinance",
    "ch07_trade_union_representatives_entry_into_estates.pdf": "Trade Union Representatives (Entry into Estates) Act",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    source_files = sorted(PDF_DIR.glob("*.pdf"))
    if len(source_files) != 44 or set(TITLES) != {path.name for path in source_files}:
        raise ValueError("Expected a title mapping for exactly the 44 corpus PDFs")

    ids_by_source: dict[str, set[str]] = {}
    identifiers_by_source: dict[str, set[str]] = {}
    for path in sorted(SECTIONS.glob("*.json")):
        if path.name in {"qc_report.json", "split_report.json"}:
            continue
        for record in json.loads(path.read_text(encoding="utf-8")):
            source = record["source_file"]
            ids_by_source.setdefault(source, set()).add(record["id"])
            identifier = str(record.get("act_number_year", "")).strip()
            if identifier:
                identifiers_by_source.setdefault(source, set()).add(identifier)

    rows = []
    for path in source_files:
        source = path.name
        identifiers = sorted(identifiers_by_source.get(source, set()))
        rows.append({
            "source_file": source,
            "title": TITLES[source],
            "act_number_year_as_recorded": "; ".join(identifiers) if identifiers else "unknown — not established in current section metadata",
            "act_number_year_verification": "From current corpus metadata; verify against the instrument title page before legal use",
            "official_source_url": OFFICIAL_CATALOG,
            "official_source_link_type": "Department of Labour Labour Code catalogue page; individual PDF button is on this page",
            "source_date": "Edition/compilation date not stated in the downloaded copy; catalogue checked " + REVIEW_DATE,
            "amendments_checked": "No — amendment/current-law check remains pending under Phase 6A.2",
            "reviewer": "AI-assisted source inventory; no instrument-level reviewer attribution recorded",
            "review_date": REVIEW_DATE,
            "source_pdf_sha256": sha256(path),
            "corpus_record_count": len(ids_by_source.get(source, set())),
        })

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps({
        "register_date": REVIEW_DATE,
        "source_count": len(rows),
        "official_catalogue": OFFICIAL_CATALOG,
        "limitations": [
            "The catalogue is an official Department of Labour source, but individual PDF download links are provided as buttons on the catalogue page and were not captured as stable direct URLs in this register.",
            "Compiled-copy edition dates are not stated consistently; source_date records the catalogue check date and explicitly notes that limitation.",
            "Amendments have not been checked. This register does not establish that any instrument is current or in force.",
            "Act identifiers are transcribed from existing corpus metadata and require title-page confirmation; this is a source inventory, not a legal review.",
        ],
        "sources": rows,
    }, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    with OUT_CSV.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} source entries to {OUT_JSON.relative_to(ROOT)} and {OUT_CSV.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Record current-law source checks and unresolved amendment chains."""

from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REGISTER_JSON = ROOT / "audit" / "source_register.json"
REGISTER_CSV = ROOT / "audit" / "source_register.csv"
OUT_JSON = ROOT / "audit" / "current_law_review.json"
OUT_CSV = ROOT / "audit" / "current_law_review.csv"
DATE = "2026-10-25"
CATALOG = "https://labourdept.gov.lk/labour-code-of-sri-lanka/"
PARLIAMENT = "https://www.parliament.lk/en/business-of-parliament/acts-listing"
GOV_PRINTING = "https://www.documents.gov.lk/home"

FINDINGS = {
    "ch00_minimum_retirement_age_of_workers.pdf": (
        "No later amendment confirmed in this targeted review. The principal Act is dated 2021; check commencement orders and any later Gazette notices.", [], "not_confirmed"
    ),
    "ch01_employees_councils.pdf": (
        "The official Acts listing identifies Employees' Councils (Amendment) Act No. 5 of 1984. No later amending Act was confirmed here.",
        ["https://www.documents.gov.lk/view/act/acts_1984.html"], "partial"
    ),
    "ch01_employees_councils_regulations.pdf": (
        "Source is subsidiary instruments/orders under the Employees' Councils Act. No complete current Gazette-by-Gazette instrument history was established.", [], "partial"
    ),
    "ch01_industrial_disputes_act.pdf": (
        "Official records confirm Industrial Disputes (Amendment) Act No. 22 of 2022 (sections 31DD) and older amendments including Nos. 56/1999 and 11/2003. Full amendment chain and commencement/cross-reference check remain open.",
        ["https://documents.gov.lk/view/acts/2022/9/22-2022_E.pdf", "https://documents.gov.lk/view/acts/1999/12/56-1999_E.pdf", "https://www.documents.gov.lk/view/act/acts_2003.html"], "partial"
    ),
    "ch01_industrial_disputes_hearing_and_determination_of_proceeding.pdf": (
        "The 2003 Act No. 13 is a special-provisions statute related to the Industrial Disputes Act. Later amendments, current applicability, and the two deadline conflicts remain uncertain in this targeted source check. Owner-reported informal lawyer-friend review is recorded separately; formal sign-off is not a project gate.",
        ["https://www.documents.gov.lk/view/act/acts_2003.html"], "partial"
    ),
    "ch01_termination_of_employment_of_workmen.pdf": (
        "Official record confirms Amendment Act No. 29 of 2021, which changes section 3(1)(c) by reference to the minimum retirement age. Amendment Act No. 12 of 2003 also appears in official Acts records. Full chain and commencement orders remain open.",
        ["https://documents.gov.lk/view/act/2021/11/29-2021_E.pdf", "https://documents.gov.lk/view/act/2003/3/12-2003_E.pdf"], "partial"
    ),
    "ch01_trade_unions_ordinance.pdf": (
        "No later amendment or current consolidated text was confirmed in this targeted review; historical amendment chain remains unresolved.", [], "not_confirmed"
    ),
    "ch02_budgetary_relief_allowance_of_workers_act_no_1.pdf": (
        "No later amending Act confirmed in this targeted review. Confirm current status, duration, and any repeal/supersession against official law before use.", [], "not_confirmed"
    ),
    "ch02_budgetary_relief_allowance_of_workers_act_no_2.pdf": (
        "No later amending Act confirmed in this targeted review. Confirm current status, duration, and any repeal/supersession against official law before use.", [], "not_confirmed"
    ),
    "ch02_budgetary_relief_allowance_of_workers_act_no_3.pdf": (
        "A 2025 Bill was published to amend the Budgetary Relief Allowance of Workers Act No. 36 of 2005; a Bill is not itself an enacted amendment. Current enactment/status remains unresolved in this review.",
        ["https://www.documents.gov.lk/view/bills/2025/5/588-2025_E.pdf"], "partial"
    ),
    "ch02_budgetary_relief_allowance_of_workers_act_no_4_of_2016.pdf": (
        "Official record confirms Budgetary Relief Allowance of Workers (Amendment) Act No. 10 of 2025. It amends Act No. 4 of 2016 and deems the changes operative from 1 April 2025. The corpus text predates this change.",
        ["https://documents.gov.lk/view/acts/2025/7/10-2025_E.pdf"], "corpus_update_required"
    ),
    "ch02_employment_of_trainees_private_sector.pdf": (
        "No later amendment or complete current official consolidation confirmed in this targeted review; verify the principal Act identifier and any repeal/overlap with later employment laws.", [], "not_confirmed"
    ),
    "ch02_national_minimum_wage_of_workers_act_no_3_of_2016.pdf": (
        "Official record confirms National Minimum Wage of Workers (Amendment) Act No. 11 of 2025, effective from 1 April 2025 and setting new minimums from 1 January 2026. Corpus copy predates it; check later notices/sector-specific rates.",
        ["https://documents.gov.lk/view/acts/2025/7/11-2025_E.pdf"], "corpus_update_required"
    ),
    "ch02_shop_and_office_employees.pdf": (
        "Official record confirms amendments including Act No. 1 of 2021 and Act No. 14 of 2018; the 2021 amendment changes the minimum age in section 10. Full consolidation/amendment chain remains open.",
        ["https://documents.gov.lk/view/act/2021/1/01-2021_E.pdf", "https://www.documents.gov.lk/view/act/acts_2018.html"], "partial"
    ),
    "ch02_shop_and_office_employees_regulations.pdf": (
        "Official Gazette Extraordinary No. 2473/25 dated 30 January 2026 amends regulation 3 only. The corpus does not include that revision. Regulations 2 and 6, which contain daily-hour and overtime provisions, are not changed by this Gazette; the broader amendment history remains incomplete.",
        ["https://www.documents.gov.lk/view/egz/egz_2026.html", "https://documents.gov.lk/view/extra-gazettes/2026/1/2473-25_E.pdf"], "corpus_update_required"
    ),
    "ch02_wages_boards_ordinance.pdf": (
        "Official sources show a Wages Boards (Amendment) Bill in 2019, but this review did not confirm enactment of that Bill. Wage Board decisions/notices continue to be made by trade and date; the Government Printer index lists 2025–2026 notices. A current trade-specific notice review is required.",
        ["https://documents.gov.lk/view/bills/2019/7/31-2019_E.pdf", "https://www.documents.gov.lk/view/egz/egz_2026.html", "https://www.documents.gov.lk/view/egz/egz_2025.html"], "partial"
    ),
    "ch03_employment_of_female_in_mines_ordinance.pdf": (
        "No later amendment confirmed in this targeted review. Verify current force/repeal and interaction with later occupational and gender laws.", [], "not_confirmed"
    ),
    "ch03_employment_of_women_young_person_and_children.pdf": (
        "Official Parliament record confirms Employment of Women, Young Persons and Children (Amendment) Act No. 21 of 2026, certified 8 September 2026. It amends sections 7, 13 and 20A penalty amounts. Corpus copy predates this Act.",
        ["https://www.parliament.lk/en/business-of-parliament/act-details/G6434", "https://www.parliament.lk/uploads/acts/gbills/english/6434.pdf"], "corpus_update_required"
    ),
    "ch03_employment_of_women_young_person_and_children_regulations.pdf": (
        "The parent Act received Amendment Act No. 21 of 2026. This regulations compilation and the Gazette notices it contains were not individually checked for later amendments/revocations.",
        ["https://www.parliament.lk/uploads/acts/gbills/english/6434.pdf"], "corpus_update_required"
    ),
    "ch03_maternity_benefits_ordinance.pdf": (
        "Official record confirms Maternity Benefits (Amendment) Act No. 52 of 1981. A 2024 Bill entry appears in the official Bill index, but enactment was not confirmed here. Current consolidated text and commencement history remain unresolved.",
        ["https://documents.gov.lk/view/acts/1981/8/52-1981_E.pdf", "https://www.documents.gov.lk/view/bill/bl_2024.html"], "partial"
    ),
    "ch03_maternity_benefits_ordinance_regulations.pdf": (
        "No complete current Gazette amendment/revocation history for these regulations was established. Parent Ordinance amendment history is also incomplete.", [], "not_confirmed"
    ),
    "ch04_factories_ordinance.pdf": (
        "Official record confirms Factories (Amendment) Act No. 4 of 2021, changing provisions on young persons' work hours and ages. Corpus copy predates this Act; other regulations and commencement details still need review.",
        ["https://documents.gov.lk/view/acts/2021/1/04-2021_E.pdf"], "corpus_update_required"
    ),
    "ch04_factories_ordinance_regulations_and_forms_1_13.pdf": (
        "Parent Factories Ordinance was amended by Act No. 4 of 2021. No complete Gazette-by-Gazette review of the regulations/forms compilation, including amendments/revocations, was established.",
        ["https://documents.gov.lk/view/acts/2021/1/04-2021_E.pdf"], "corpus_update_required"
    ),
    "ch04_workmens_compensation.pdf": (
        "No later amending Act confirmed in this targeted review. Verify current Act/Ordinance title, amendments, repeals and any current compensation schedules before use.", [], "not_confirmed"
    ),
    "ch04_workmens_compensation_regulations.pdf": (
        "No complete current Gazette amendment/revocation history for the regulations or compensation schedule was established.", [], "not_confirmed"
    ),
    "ch05_employees_provident_fund.pdf": (
        "Official record confirms Employees' Provident Fund (Amendment) Act No. 23 of 2021, changing definitions in section 47. Official 2024 Bill entries propose another amendment, but enactment was not confirmed in this review. Corpus copy predates at least the 2021 Act.",
        ["https://documents.gov.lk/view/acts/2021/10/23-2021_E.pdf", "https://www.documents.gov.lk/view/bill/bl_2024.html"], "corpus_update_required"
    ),
    "ch05_employees_provident_fund_regulations.pdf": (
        "Parent Act was amended by Act No. 23 of 2021. No complete Gazette-by-Gazette review of EPF regulations/orders or commencement notices was established.",
        ["https://documents.gov.lk/view/acts/2021/10/23-2021_E.pdf"], "corpus_update_required"
    ),
    "ch05_employees_provident_fund_regulations_part_2.pdf": (
        "Parent Act was amended by Act No. 23 of 2021. No complete Gazette-by-Gazette review of this regulations/orders compilation or later amendments was established.",
        ["https://documents.gov.lk/view/acts/2021/10/23-2021_E.pdf"], "corpus_update_required"
    ),
    "ch05_employees_provident_fund_special_provisions.pdf": (
        "No later amendment or repeal status confirmed in this targeted review; verify principal-law identity and current force.", [], "not_confirmed"
    ),
    "ch05_employees_trust_fund.pdf": (
        "Official 1980 principal Act located; no later amending Act confirmed by this targeted search. This is not proof that no amendments or relevant Gazette orders exist.",
        ["https://documents.gov.lk/view/acts/1980/10/46-1980_E.pdf"], "partial"
    ),
    "ch05_employees_trust_fund_regulations.pdf": (
        "No complete current Gazette order/regulation history was established; instrument-by-instrument review remains open.", [], "not_confirmed"
    ),
    "ch05_employees_trust_fund_special_provisions.pdf": (
        "No later amendment or repeal status confirmed in this targeted review; verify current force and relationship to the Employees' Trust Fund Act.", [], "not_confirmed"
    ),
    "ch05_payment_of_gratuity.pdf": (
        "Official Act index confirms Payment of Gratuity (Amendment) Act No. 12 of 1983. Later changes, current thresholds, amendments and relevant Gazette orders were not completely traced.",
        ["https://www.documents.gov.lk/view/act/acts_1983.html"], "partial"
    ),
    "ch06_fee_charging_employment_agencies.pdf": (
        "Official Foreign Employment Agency Act No. 32 of 1980 expressly amended the Fee-Charging Employment Agencies Act No. 37 of 1956. The 1985 SLBFE Act may affect the regulatory framework; repeal/savings/current force not determined.",
        ["https://documents.gov.lk/view/acts/1980/8/32-1980_E.pdf"], "partial"
    ),
    "ch06_sri_lanka_bureau_of_foreign_employment_act.pdf": (
        "No later amending Act confirmed in this targeted review. Regulations and fee/licensing notices are separate and require a Gazette-level review.", [], "not_confirmed"
    ),
    "ch06_sri_lanka_bureau_of_foreign_employment_act_regulations.pdf": (
        "Official Gazette No. 2337/27 dated 23 June 2023 further amended the 1985 regulations, following an amendment in Gazette No. 1765/21 dated 6 July 2012. Later regulatory notices were not exhaustively checked.",
        ["https://documents.gov.lk/view/extra-gazettes/2023/6/2337-27_E.pdf"], "partial"
    ),
    "ch07_allowances_to_plantation_workers.pdf": (
        "No later amending Act confirmed in this targeted review. Check current force, statutory orders and wage/allowance Gazette notices affecting plantation workers.", [], "not_confirmed"
    ),
    "ch07_estate_labour_indian.pdf": (
        "No later amendment or repeal status confirmed in this targeted review; verify current force and interaction with later labour statutes.", [], "not_confirmed"
    ),
    "ch07_estates_quarters.pdf": (
        "No later amendment or repeal status confirmed in this targeted review; verify current force and any relevant regulations/Gazette orders.", [], "not_confirmed"
    ),
    "ch07_indian_immigrant_labour.pdf": (
        "No later amendment or repeal status confirmed in this targeted review; verify current force and interaction with immigration and foreign-employment laws.", [], "not_confirmed"
    ),
    "ch07_medical_wants.pdf": (
        "No later amendment or repeal status confirmed in this targeted review; verify current force and any regulations/health notices.", [], "not_confirmed"
    ),
    "ch07_minimum_wages.pdf": (
        "No later amendment or repeal status confirmed in this targeted review; verify current force and related Wages Board/Gazette rates before use.", [], "not_confirmed"
    ),
    "ch07_service_contracts.pdf": (
        "No later amendment or repeal status confirmed in this targeted review; verify current force and interaction with later employment legislation.", [], "not_confirmed"
    ),
    "ch07_trade_union_representatives_entry_into_estates.pdf": (
        "No later amendment or repeal status confirmed in this targeted review; verify current force and any relevant regulations/Gazette orders.", [], "not_confirmed"
    ),
}

# Principal enactment numbers verified in official government publications.
VERIFIED_IDENTIFIERS = {
    "ch01_employees_councils.pdf": "Act No. 32 of 1979",
    "ch01_trade_unions_ordinance.pdf": "Ordinance No. 14 of 1935",
    "ch02_shop_and_office_employees.pdf": "Act No. 19 of 1954",
    "ch02_wages_boards_ordinance.pdf": "Ordinance No. 27 of 1941",
    "ch03_employment_of_women_young_person_and_children.pdf": "Act No. 47 of 1956",
    "ch03_maternity_benefits_ordinance.pdf": "Ordinance No. 32 of 1939",
    "ch04_factories_ordinance.pdf": "Ordinance No. 45 of 1942",
    "ch04_workmens_compensation.pdf": "Ordinance No. 19 of 1934",
    "ch05_employees_provident_fund.pdf": "Act No. 15 of 1958",
    "ch05_employees_trust_fund.pdf": "Act No. 46 of 1980",
    "ch05_payment_of_gratuity.pdf": "Act No. 12 of 1983",
    "ch06_fee_charging_employment_agencies.pdf": "Act No. 37 of 1956",
    "ch01_termination_of_employment_of_workmen.pdf": "Act No. 45 of 1971",
}
IDENTIFIER_LINKS = {
    "ch01_employees_councils.pdf": "https://documents.gov.lk/view/extra-gazettes/2022/4/2277-53_E.pdf",
    "ch01_trade_unions_ordinance.pdf": "https://documents.gov.lk/view/extra-gazettes/2022/4/2277-53_E.pdf",
    "ch02_shop_and_office_employees.pdf": "https://documents.gov.lk/view/extra-gazettes/2022/4/2277-53_E.pdf",
    "ch02_wages_boards_ordinance.pdf": "https://documents.gov.lk/view/extra-gazettes/2022/4/2277-53_E.pdf",
    "ch03_employment_of_women_young_person_and_children.pdf": "https://documents.gov.lk/view/extra-gazettes/2022/4/2277-53_E.pdf",
    "ch03_maternity_benefits_ordinance.pdf": "https://documents.gov.lk/view/extra-gazettes/2022/4/2277-53_E.pdf",
    "ch04_factories_ordinance.pdf": "https://documents.gov.lk/view/extra-gazettes/2022/4/2277-53_E.pdf",
    "ch04_workmens_compensation.pdf": "https://documents.gov.lk/view/extra-gazettes/2022/4/2277-53_E.pdf",
    "ch05_employees_provident_fund.pdf": "https://documents.gov.lk/view/extra-gazettes/2022/4/2277-53_E.pdf",
    "ch05_employees_trust_fund.pdf": "https://documents.gov.lk/view/acts/1980/10/46-1980_E.pdf",
    "ch05_payment_of_gratuity.pdf": "https://documents.gov.lk/view/extra-gazettes/2022/4/2277-53_E.pdf",
    "ch06_fee_charging_employment_agencies.pdf": "https://documents.gov.lk/view/acts/1980/8/32-1980_E.pdf",
    "ch01_termination_of_employment_of_workmen.pdf": "https://documents.gov.lk/view/extra-gazettes/2022/4/2277-53_E.pdf",
}

AFFECTED_SECTIONS = {
    "ch02_shop_and_office_employees_regulations.pdf": ["3"],
}


def main() -> int:
    register = json.loads(REGISTER_JSON.read_text(encoding="utf-8"))
    if len(register["sources"]) != 44 or set(FINDINGS) != {row["source_file"] for row in register["sources"]}:
        raise ValueError("Review findings must cover the 44 registered source files")

    review_rows = []
    for row in register["sources"]:
        source = row["source_file"]
        finding, links, status = FINDINGS[source]
        if source in IDENTIFIER_LINKS:
            links = [*links, IDENTIFIER_LINKS[source]]
        if source in VERIFIED_IDENTIFIERS:
            row["act_number_year_as_recorded"] = VERIFIED_IDENTIFIERS[source]
            row["act_number_year_verification"] = "Principal identifier checked against official government publication; amendments remain separately reviewed"
        row["amendments_checked"] = "Targeted official-source review on " + DATE + "; see audit/current_law_review.json"
        review_rows.append({
            "source_file": source,
            "title": row["title"],
            "principal_act_number_year": row["act_number_year_as_recorded"],
            "review_date": DATE,
            "applicable_date": "2026-10-25 (review cutoff; individual amendments may have different commencement dates)",
            "status": status,
            "official_sources_checked": [CATALOG, PARLIAMENT, GOV_PRINTING, *links],
            "amendment_and_gazette_findings": finding,
            "unresolved_uncertainty": "This targeted review does not establish an exhaustive amendment/repeal history or current legal status. The remaining source-currentness uncertainty is retained in the audit; owner-reported informal lawyer-friend review is recorded separately and formal sign-off is not a project gate.",
            **({"affected_sections": AFFECTED_SECTIONS[source]} if source in AFFECTED_SECTIONS else {}),
        })

    register["sources"] = register["sources"]
    register["register_date"] = DATE
    register["current_law_review"] = "audit/current_law_review.json"
    register["limitations"] = [
        "The catalogue is an official Department of Labour source, but individual PDF download links are provided as buttons on the catalogue page and are not captured as stable direct URLs for every row.",
        "Compiled-copy edition dates are not stated consistently; source_date records the catalogue check date and explicitly notes that limitation.",
        "Amendments and current law have not been exhaustively checked; see audit/current_law_review.json for findings and open items.",
        "Principal Act identifiers for 13 rows were checked/corrected against official government publications. Other identifiers remain as corpus metadata pending title-page verification.",
    ]
    REGISTER_JSON.write_text(json.dumps(register, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    with REGISTER_CSV.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(register["sources"][0]))
        writer.writeheader()
        writer.writerows(register["sources"])

    summary = {
        "review_date": DATE,
        "applicable_date_cutoff": DATE,
        "source_count": len(review_rows),
        "method": "Compared the Department of Labour Labour Code catalogue and source copies with targeted searches of Parliament Acts and Department of Government Printing Acts/Gazette records. Search non-results are not treated as proof that no amendment exists.",
        "status_counts": {},
        "review_scope_limitations": [
            "No exhaustive title-by-title historic amendment chain was established for every principal Act.",
            "Subsidiary legislation, annual or trade-specific rates, commencement orders, revocations, and corrections require Gazette-by-Gazette verification.",
            "Official source copies and amendment entries were not reconciled clause-by-clause for all instruments.",
            "This is a research inventory, not a legal opinion or confirmation that any law is in force.",
        ],
        "sources": review_rows,
    }
    from collections import Counter
    summary["status_counts"] = dict(Counter(item["status"] for item in review_rows))
    OUT_JSON.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    flat = [{**item, "official_sources_checked": " ; ".join(item["official_sources_checked"])} for item in review_rows]
    with OUT_CSV.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(flat[0]))
        writer.writeheader()
        writer.writerows(flat)

    print(f"Recorded official-source findings for {len(review_rows)} instruments")
    print(f"Statuses: {summary['status_counts']}")
    print("Review: audit/current_law_review.json and .csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

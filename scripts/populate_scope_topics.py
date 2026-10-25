"""Populate conservative, source-grounded topics and scope notes."""

from __future__ import annotations

import json
import re
import unicodedata
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SECTIONS = ROOT / "sections"
INDEX_RECORDS = ROOT / "index" / "records.json"
AUDIT_REPORT = ROOT / "audit" / "scope_topics_review.json"

TOPIC_RULES: list[tuple[str, re.Pattern[str]]] = [
    ("retirement_age", re.compile(r"\bretir(?:e|ed|ement|ing)\b", re.I)),
    ("termination_and_dismissal", re.compile(r"\bterminat(?:e|ed|ion|ing)\b|\bdismiss(?:al|ed|ing)?\b|\bretrench(?:ment|ed)?\b", re.I)),
    ("minimum_wages", re.compile(r"\bminimum\s+(?:rate[s]?\s+of\s+)?wages?\b|\bwages boards?\b", re.I)),
    ("wages_and_remuneration", re.compile(r"\bwages?\b|\bremuneration\b|\bsalar(?:y|ies)\b", re.I)),
    ("overtime", re.compile(r"\bovertime\b", re.I)),
    ("working_hours_and_night_work", re.compile(r"\bnight work\b|\bworking hours?\b|\bhours? of work\b|\bweekly holidays?\b", re.I)),
    ("leave_and_holidays", re.compile(r"\bholidays?\b|\bleave\b|\bvacation\b|\brest day\b|\bpoya\b", re.I)),
    ("maternity_and_nursing", re.compile(r"\bmatern(?:ity|al)\b|\bconfinement\b|\bnursing\b", re.I)),
    ("women_young_workers_and_children", re.compile(r"\bwoman\b|\bwomen\b|\bfemale\b|\byoung person\b|\bchild(?:ren)?\b|\bminor\b", re.I)),
    ("workplace_safety_and_inspection", re.compile(r"\bsafety\b|\binspect(?:ion|or|ors|ed)?\b|\bmachine(?:ry)?\b|\bboiler\b|\bdangerous\b|\bsanitary\b", re.I)),
    ("work_injury_compensation", re.compile(r"\bcompensation\b|\baccident\b|\binjur(?:y|ies|ed)\b|\bindustrial disease\b", re.I)),
    ("employees_provident_fund", re.compile(r"\bprovident fund\b|\bEPF\b", re.I)),
    ("employees_trust_fund", re.compile(r"\btrust fund\b|\bETF\b", re.I)),
    ("gratuity", re.compile(r"\bgratuity\b", re.I)),
    ("trade_unions", re.compile(r"\btrade union\b|\btrade unions\b|\btrade unionist\b", re.I)),
    ("employee_councils", re.compile(r"\bemployees?['’ ]+ councils?\b|\bcouncil of employees\b", re.I)),
    ("industrial_disputes", re.compile(r"\bindustrial dispute\b|\btrade dispute\b|\bdispute between\b", re.I)),
    ("tribunal_and_case_procedure", re.compile(r"\btribunal\b|\bcourt\b|\bproceedings?\b|\bhearing\b|\bappeal\b", re.I)),
    ("employment_agencies_and_recruitment", re.compile(r"\bemployment agenc(?:y|ies)\b|\brecruit(?:ment|er|ers)?\b|\bforeign employment\b|\blicen[cs](?:e|ed|ing)\b", re.I)),
    ("plantation_and_estate_labour", re.compile(r"\bestate\b|\bplantation\b|\bindian labour\b|\bindian immigrant\b", re.I)),
    ("medical_and_welfare_facilities", re.compile(r"\bmedical\b|\bhospital\b|\bfirst aid\b|\bquarters\b|\bwater supply\b", re.I)),
    ("employment_contracts", re.compile(r"\bcontract of service\b|\bcontracts? of hire\b|\bhire and service\b|\bservant\b|\bservice contract\b", re.I)),
    ("registration_and_records", re.compile(r"\bregister\b|\bregistration\b|\brecord cards?\b|\breturns?\b", re.I)),
    ("offences_and_penalties", re.compile(r"\boffence\b|\boffences\b|\bpenalt(?:y|ies)\b|\bfine not exceeding\b|\bprosecution\b", re.I)),
    ("appointments_and_authorities", re.compile(r"\bappoint(?:ment|ed|ing)?\b|\bconstitution of (?:the )?(?:board|tribunal)\b|\bappointment of\b", re.I)),
    ("definitions_and_interpretation", re.compile(r"\binterpretation\b|\bmeans\b|\bshall be construed\b|\bdefinition\b", re.I)),
    ("exemptions_and_permits", re.compile(r"\bexempt(?:ion|ions|ed)?\b|\bpermit(?:ted|ting)?\b|\bauthori[sz](?:e|ed|ation)\b", re.I)),
    ("benefits_and_allowances", re.compile(r"\ballowance\b|\ballowances\b|\bbenefit\b|\bbenefits\b", re.I)),
]

SCOPE_MARKER = re.compile(
    r"\b(?:shall\s+)?(?:not\s+)?apply\s+to\b|"
    r"\b(?:does|do)\s+not\s+apply\s+to\b|"
    r"\bapplicable\s+to\b|"
    r"\bexempt(?:ed)?\s+from\b|\bexcluded\s+from\b|"
    r"\bcovered\s+employment\b|\bcoverage\s+of\b",
    re.I,
)
STOP_WORDS = {"act", "ordinance", "regulations", "regulation", "of", "the", "and", "for", "no"}
FORM_DISPOSITIONS = {
    "prescribed_form_field",
    "schedule_quantity_row",
    "schedule_form_field",
    "gazette_schedule_officer_entry",
    "schedule_fee_table_row",
}

ACT_TOPIC_BY_SOURCE = {
    "ch00_minimum_retirement_age_of_workers.pdf": "retirement_age",
    "ch01_employees_councils.pdf": "employee_councils",
    "ch01_employees_councils_regulations.pdf": "employee_councils",
    "ch01_industrial_disputes_act.pdf": "industrial_disputes",
    "ch01_industrial_disputes_hearing_and_determination_of_proceeding.pdf": "industrial_dispute_procedure",
    "ch01_termination_of_employment_of_workmen.pdf": "termination_of_employment",
    "ch01_trade_unions_ordinance.pdf": "trade_unions",
    "ch02_budgetary_relief_allowance_of_workers_act_no_1.pdf": "wage_relief_allowances",
    "ch02_budgetary_relief_allowance_of_workers_act_no_2.pdf": "wage_relief_allowances",
    "ch02_budgetary_relief_allowance_of_workers_act_no_3.pdf": "wage_relief_allowances",
    "ch02_budgetary_relief_allowance_of_workers_act_no_4_of_2016.pdf": "wage_relief_allowances",
    "ch02_employment_of_trainees_private_sector.pdf": "trainee_employment",
    "ch02_national_minimum_wage_of_workers_act_no_3_of_2016.pdf": "minimum_wages",
    "ch02_shop_and_office_employees.pdf": "shop_and_office_employment",
    "ch02_shop_and_office_employees_regulations.pdf": "shop_and_office_employment",
    "ch02_wages_boards_ordinance.pdf": "wage_boards",
    "ch03_employment_of_female_in_mines_ordinance.pdf": "women_in_mining",
    "ch03_employment_of_women_young_person_and_children.pdf": "women_young_workers_and_children",
    "ch03_employment_of_women_young_person_and_children_regulations.pdf": "women_young_workers_and_children",
    "ch03_maternity_benefits_ordinance.pdf": "maternity_benefits",
    "ch03_maternity_benefits_ordinance_regulations.pdf": "maternity_benefits",
    "ch04_factories_ordinance.pdf": "factory_safety",
    "ch04_factories_ordinance_regulations_and_forms_1_13.pdf": "factory_safety",
    "ch04_workmens_compensation.pdf": "work_injury_compensation",
    "ch04_workmens_compensation_regulations.pdf": "work_injury_compensation",
    "ch05_employees_provident_fund.pdf": "employees_provident_fund",
    "ch05_employees_provident_fund_regulations.pdf": "employees_provident_fund",
    "ch05_employees_provident_fund_regulations_part_2.pdf": "employees_provident_fund",
    "ch05_employees_provident_fund_special_provisions.pdf": "employees_provident_fund",
    "ch05_employees_trust_fund.pdf": "employees_trust_fund",
    "ch05_employees_trust_fund_regulations.pdf": "employees_trust_fund",
    "ch05_employees_trust_fund_special_provisions.pdf": "employees_trust_fund",
    "ch05_payment_of_gratuity.pdf": "gratuity",
    "ch06_fee_charging_employment_agencies.pdf": "employment_agencies",
    "ch06_sri_lanka_bureau_of_foreign_employment_act.pdf": "foreign_employment",
    "ch06_sri_lanka_bureau_of_foreign_employment_act_regulations.pdf": "employment_agency_licensing",
    "ch07_allowances_to_plantation_workers.pdf": "plantation_allowances",
    "ch07_estate_labour_indian.pdf": "estate_labour",
    "ch07_estates_quarters.pdf": "plantation_housing",
    "ch07_indian_immigrant_labour.pdf": "indian_immigrant_labour",
    "ch07_medical_wants.pdf": "medical_welfare",
    "ch07_minimum_wages.pdf": "minimum_wages_indian_labour",
    "ch07_service_contracts.pdf": "service_contracts",
    "ch07_trade_union_representatives_entry_into_estates.pdf": "trade_union_access_to_estates",
}


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def act_topic(act_name: str) -> str:
    normalized = unicodedata.normalize("NFKD", act_name).encode("ascii", "ignore").decode().lower()
    words = re.findall(r"[a-z]+", normalized)
    words = [word for word in words if word not in STOP_WORDS]
    return "_".join(words) or "act_specific_provision"


def scope_metadata(record: dict, form_record_ids: set[str]) -> tuple[str, str, str]:
    text = " ".join(str(record.get("text", "")).split())
    # Keep exact source wording, selecting only clauses with explicit scope terms.
    clauses = re.split(r"(?<=[.;:])\s+", text)
    explicit = []
    for clause in clauses:
        if SCOPE_MARKER.search(clause):
            clipped = clause.strip()
            words = clipped.lower().split()
            if len(words) <= 20 and re.match(
                r"^(?:application of (?:this )?(?:act|ordinance|part)|"
                r"certain provisions of .*(?:not to apply|apply to)|"
                r"non[- ]application of)", clipped.lower()
            ):
                continue
            if clipped and clipped not in explicit:
                explicit.append(clipped[:500])
            if len(explicit) == 2:
                break
    if explicit:
        return "explicit_in_section", "Source scope wording: " + " | ".join(explicit), " | ".join(explicit)

    short = len(text.split()) < 10
    if record["id"] in form_record_ids:
        note = (
            "Scope is not established by this form/schedule entry; consult the complete "
            "parent provision and the Act's application and interpretation provisions."
        )
        return "not_established_by_form_or_schedule", note, ""
    if short:
        note = (
            "Scope is unclear from this short record alone; consult the complete parent provision "
            "and the Act's application and interpretation provisions."
        )
        return "unclear_from_short_record", note, ""
    note = (
        "No separate coverage boundary is explicit in this provision; this does not determine "
        "Act-wide coverage. Consult the Act's application and interpretation provisions."
    )
    return "not_stated_in_section", note, ""


def topic_metadata(record: dict) -> tuple[list[str], dict[str, list[str]]]:
    act = str(record.get("act_name", ""))
    heading = str(record.get("heading", ""))
    body = " ".join(str(record.get("text", "")).split())[:1200]
    content = " ".join([act, heading, body])
    source_file = record["source_file"]
    if source_file not in ACT_TOPIC_BY_SOURCE:
        raise ValueError(f"No Act-level topic mapping for {source_file}")
    selected = []
    matched: dict[str, list[str]] = {}
    for order, (topic, pattern) in enumerate(TOPIC_RULES):
        hits = [match.group(0).lower() for match in pattern.finditer(content)]
        if hits:
            matched[topic] = list(dict.fromkeys(hits[:8]))
            if pattern.search(heading):
                priority = 0
            elif pattern.search(act):
                priority = 1
            else:
                priority = 2
            selected.append((priority, order, topic))
    # Heading matches are the clearest section-level topics. Cap tags to keep
    # incidental cross-references in long provisions from swamping the Act tag.
    selected.sort()
    topics = [ACT_TOPIC_BY_SOURCE[source_file]]
    topics.extend(topic for _, _, topic in selected[:4])
    topics = list(dict.fromkeys(topics))
    matched = {topic: matched[topic] for topic in topics if topic in matched}
    return topics, matched


def main() -> int:
    section_files = sorted(
        path for path in SECTIONS.glob("*.json")
        if path.name not in {"qc_report.json", "split_report.json"}
    )
    records_by_id: dict[str, dict] = {}
    audit_items = []
    scope_counts: Counter[str] = Counter()
    topic_counts: Counter[str] = Counter()
    changed = 0

    short_review = load_json(ROOT / "audit" / "short_section_review.json")
    form_record_ids = {
        item["record_id"] for item in short_review["items"]
        if item["disposition"] in FORM_DISPOSITIONS
    }

    for path in section_files:
        records = load_json(path)
        for record in records:
            scope_status, scope_notes, scope_evidence = scope_metadata(record, form_record_ids)
            topics, topic_evidence = topic_metadata(record)
            record["scope_notes"] = scope_notes
            record["scope_status"] = scope_status
            record["topics"] = topics
            records_by_id[record["id"]] = record
            scope_counts[scope_status] += 1
            topic_counts.update(topics)
            audit_items.append({
                "record_id": record["id"],
                "source_file": record["source_file"],
                "source_page": record["source_page"],
                "act_name": record["act_name"],
                "topics": topics,
                "topic_evidence_terms": topic_evidence,
                "scope_status": scope_status,
                "scope_evidence_excerpt": scope_evidence,
                "scope_notes": scope_notes,
            })
        path.write_text(json.dumps(records, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        changed += len(records)

    if changed != 2094 or len(records_by_id) != changed:
        raise ValueError(f"Expected 2,094 unique records, wrote {changed} records")

    # These metadata fields are not part of embedding_text(); synchronize the
    # records served beside FAISS without changing vectors or rebuilding FAISS.
    index_records = load_json(INDEX_RECORDS)
    if len(index_records) != len(records_by_id):
        raise ValueError("Index record count does not match section records")
    index_ids = {record["id"] for record in index_records}
    if index_ids != set(records_by_id):
        raise ValueError("Index record IDs do not match section record IDs")
    for record in index_records:
        source = records_by_id[record["id"]]
        record["scope_notes"] = source["scope_notes"]
        record["scope_status"] = source["scope_status"]
        record["topics"] = source["topics"]
    INDEX_RECORDS.write_text(json.dumps(index_records, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    report = {
        "review_date": "2026-10-25",
        "records_updated": changed,
        "scope_status_counts": dict(scope_counts),
        "topic_record_counts": dict(topic_counts.most_common()),
        "method": {
            "topics": "A reviewed source-file Act-domain tag plus up to four deterministic section tags from exact words in the heading or first 1,200 source-text characters; matching terms are recorded per record.",
            "scope_notes": "Exact scope clauses are quoted only when explicit applicability/exemption wording occurs. Headings such as 'Application of this Act' and procedural phrases such as 'application for a licence' do not count alone as coverage. Otherwise the note states scope is absent or unclear in that section and points to Act application/interpretation provisions; no Act-wide coverage is inferred.",
            "legal_review": "These annotations describe source text and still require the legal review gate before public answers are relied on.",
        },
        "records": audit_items,
    }
    AUDIT_REPORT.parent.mkdir(parents=True, exist_ok=True)
    AUDIT_REPORT.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Updated scope_notes and topics for {changed:,} records")
    print(f"Scope statuses: {dict(scope_counts)}")
    print(f"Unique topic tags: {len(topic_counts)}; records with empty topics: 0")
    print(f"Synchronized index metadata without re-embedding: {INDEX_RECORDS}")
    print(f"Audit: {AUDIT_REPORT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

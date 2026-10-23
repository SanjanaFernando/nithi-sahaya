"""Clean extracted labour-law text and split it into section records.

Usage:
    python scripts/split.py
    python scripts/split.py --source text --destination sections

This is an automated first pass. The output intentionally uses ``status:
"verify"`` because section boundaries, amendments, and legal metadata still
need human/legal review in Phase 3.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path


PAGE_MARKER = "[[PAGE]]"
AMENDMENT_TAG = re.compile(r"\[(?:Â§|§)\s*([^\]]+)\]")
NUMBERED_SECTION = re.compile(
    r"^\s*(\d{1,3}[A-Z]{0,4})\.\s+(?=[A-Z(])", re.MULTILINE
)
REGULATION_SECTION = re.compile(
    r"^\s*(?:Regulation\s+)?(\d{1,3}[A-Z]{0,4})\.\s+(?=\(?\d|[A-Z])",
    re.IGNORECASE | re.MULTILINE,
)
SUBSECTION = re.compile(r"^\s*\((\d{1,3}[A-Z]?)\)\s+", re.MULTILINE)
PAGE_NUMBER = re.compile(r"^\s*\d{1,4}\s*$")


@dataclass
class Chunk:
    number: str
    raw_text: str
    page: int


def fix_mojibake(value: str) -> str:
    """Repair the common UTF-8-as-Windows-1252 artefacts in PDF text."""
    if not any(token in value for token in ("â", "Â", "Ã", "�")):
        return value
    try:
        repaired = value.encode("cp1252").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return value
    return repaired if repaired.count("�") <= value.count("�") else value


def page_number_at(text: str, position: int) -> int:
    return text[:position].count(PAGE_MARKER) + 1


def clean_page(page: str) -> str:
    lines: list[str] = []
    for original in page.splitlines():
        line = fix_mojibake(original).replace("\u00a0", " ").strip()
        if not line or PAGE_NUMBER.fullmatch(line):
            continue
        lines.append(line)
    return "\n".join(lines)


def clean_document(raw: str) -> tuple[str, list[str]]:
    pages = [clean_page(page) for page in raw.split(PAGE_MARKER)]
    amendments: list[str] = []
    cleaned_pages: list[str] = []
    for page in pages:
        found = AMENDMENT_TAG.findall(page)
        amendments.extend(item.strip().rstrip(".") for item in found)
        page = AMENDMENT_TAG.sub("", page)
        cleaned_pages.append(page)
    return f"\n{PAGE_MARKER}\n".join(cleaned_pages), sorted(set(amendments))


def title_from_text(text: str, filename: str) -> str:
    candidates = [line.strip() for line in text.splitlines() if line.strip()]
    candidates = [
        line
        for line in candidates[:100]
        if not any(token in line.lower() for token in ("downloaded from", "www.", "printed at", "purchased at"))
    ]
    cited_as = re.compile(
        r"cited\s+as\s+(?:the\s+)?(.+?)(?:,\s*No\.?\s*[\w./-]+\s+of\s+\d{4}|\.$|$)",
        re.IGNORECASE,
    )
    for line in candidates:
        match = cited_as.search(line)
        if match and len(match.group(1).strip()) >= 5:
            return re.sub(r"\s+", " ", match.group(1)).strip()
    preferred = re.compile(
        r"\b(?:ACT|ORDINANCE)\b(?:\s*,?\s*NO\.?|\s+NO\.?|\s+OF\s+\d{4})",
        re.IGNORECASE,
    )
    for line in candidates:
        upper = line.upper()
        if preferred.search(line) or "REGULATIONS" in upper:
            if len(line) <= 220:
                if re.fullmatch(r"ACT\s*,?\s*NO\.?\s*[\w./-]+\s+OF\s+\d{4}", line, re.IGNORECASE):
                    break
                return line
    stem = Path(filename).stem
    stem = re.sub(r"^ch\d+_", "", stem, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", stem.replace("_", " ")).strip().title()


def act_number_year(text: str) -> str:
    patterns = [
        r"((?:Act|Ordinance)\s*,?\s*No\.\s*[\w./-]+\s+of\s+\d{4})",
        r"(No\.\s*[\w./-]+\s+of\s+\d{4})",
        r"(Law\s+No\.\s*[\w./-]+\s+of\s+\d{4})",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return re.sub(r"\s+", " ", match.group(1)).strip(" .")
    return ""


def find_chunks(text: str, regulations: bool) -> list[Chunk]:
    # The normal section pattern is preferred. Regulation files often use
    # numbered rules with a subsection immediately after the number.
    matches = list(NUMBERED_SECTION.finditer(text))
    if regulations:
        regulation_matches = list(REGULATION_SECTION.finditer(text))
        if len(regulation_matches) > len(matches):
            matches = regulation_matches

    chunks: list[Chunk] = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        body = text[match.end() : end].strip()
        if not body:
            continue
        chunks.append(
            Chunk(
                number=match.group(1).upper(),
                raw_text=body,
                page=page_number_at(text, match.start()),
            )
        )
    return chunks


def heading_and_body(raw_text: str) -> tuple[str, str]:
    raw_text = raw_text.replace(PAGE_MARKER, "\n")
    lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
    if not lines:
        return "", ""
    first = lines[0]
    # Most compiled Acts put a short heading before the operative text.
    if len(first) <= 180 and not first.startswith(("(", "[")):
        return first.rstrip("."), "\n".join(lines[1:]).strip()
    return "", "\n".join(lines).strip()


def split_long_chunk(chunk: Chunk) -> list[Chunk]:
    if len(chunk.raw_text.split()) <= 800:
        return [chunk]
    matches = list(SUBSECTION.finditer(chunk.raw_text))
    if len(matches) < 2:
        return [chunk]
    pieces: list[Chunk] = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(chunk.raw_text)
        body = chunk.raw_text[match.start() : end].strip()
        pieces.append(Chunk(f"{chunk.number}({match.group(1)})", body, chunk.page))
    return pieces


def make_records(text: str, source_file: str) -> tuple[list[dict[str, object]], list[str]]:
    cleaned, amendments = clean_document(text)
    regulations = "regulation" in source_file.lower()
    chunks = find_chunks(cleaned, regulations)
    act_name = title_from_text(cleaned.replace(PAGE_MARKER, "\n"), source_file)
    number_year = act_number_year(cleaned)
    records: list[dict[str, object]] = []
    seen_ids: dict[str, int] = {}
    for chunk in chunks:
        for piece in split_long_chunk(chunk):
            heading, body = heading_and_body(piece.raw_text)
            if not body:
                continue
            suffix = re.sub(r"[^a-z0-9]+", "_", piece.number.lower()).strip("_")
            base_id = f"{Path(source_file).stem}_s{suffix}"
            seen_ids[base_id] = seen_ids.get(base_id, 0) + 1
            record_id = base_id
            if seen_ids[base_id] > 1:
                record_id = f"{base_id}_p{piece.page}_{seen_ids[base_id]}"
            records.append(
                {
                    "id": record_id,
                    "act_name": act_name,
                    "act_number_year": number_year,
                    "doc_type": "regulations" if regulations else "act",
                    "chapter": "",
                    "section_number": piece.number,
                    "heading": heading,
                    "text": body,
                    "amended_by": amendments,
                    "scope_notes": "",
                    "source_file": Path(source_file).with_suffix(".pdf").name,
                    "source_page": piece.page,
                    "topics": [],
                    "conflicts_with": [],
                    "status": "verify",
                }
            )
    warnings: list[str] = []
    if not chunks:
        warnings.append("no numbered sections detected")
    if any(len(record["text"].split()) < 10 for record in records):
        warnings.append("contains section text shorter than 10 words")
    if "[Â§" in cleaned or "[§" in cleaned:
        warnings.append("amendment tags remain")
    return records, warnings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=Path("text"))
    parser.add_argument("--destination", type=Path, default=Path("sections"))
    args = parser.parse_args()
    if not args.source.is_dir():
        parser.error(f"source directory does not exist: {args.source}")

    files = sorted(args.source.glob("*.txt"))
    if not files:
        parser.error(f"no text files found in {args.source}")
    args.destination.mkdir(parents=True, exist_ok=True)

    report: list[dict[str, object]] = []
    total_records = 0
    for source_file in files:
        records, warnings = make_records(
            source_file.read_text(encoding="utf-8"), source_file.name
        )
        output = args.destination / f"{source_file.stem}.json"
        output.write_text(
            json.dumps(records, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        total_records += len(records)
        report.append(
            {
                "source_file": source_file.name,
                "output_file": output.name,
                "records": len(records),
                "warnings": warnings,
            }
        )

    report_path = args.destination / "split_report.json"
    report_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"Processed {len(files)} text files into {args.destination}/")
    print(f"Created {total_records:,} section records")
    warned = [item for item in report if item["warnings"]]
    print(f"Files with review warnings: {len(warned)}")
    for item in warned:
        print(f"  {item['source_file']}: {'; '.join(item['warnings'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


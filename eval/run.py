"""Run the Phase 6 evaluation set.

Default mode is local keyword retrieval and does not call Gemini. Use --api
when quota is available to evaluate generated answers and refusal behavior.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


TOKEN = re.compile(r"[\w]+", re.UNICODE)
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def load_records(index_dir: Path) -> list[dict]:
    records_path = index_dir / "records.json"
    if records_path.exists():
        return json.loads(records_path.read_text(encoding="utf-8"))
    records: list[dict] = []
    for path in sorted(index_dir.glob("*.json")):
        if path.name in {"qc_report.json", "split_report.json"}:
            continue
        records.extend(json.loads(path.read_text(encoding="utf-8")))
    if not records:
        raise FileNotFoundError(f"no index records or section JSON files found in {index_dir}")
    return records


def keyword_search(question: str, records: list[dict], k: int) -> list[dict]:
    query = set(TOKEN.findall(question.lower()))
    scored = []
    for record in records:
        haystack = " ".join([
            record.get("act_name", ""), record.get("section_number", ""),
            record.get("heading", ""), record.get("text", ""),
        ]).lower()
        words = set(TOKEN.findall(haystack))
        score = len(query & words) / max(1, len(query))
        scored.append((score, record))
    return [record for _, record in sorted(scored, key=lambda item: item[0], reverse=True)[:k]]


def expected_hit(item: dict, results: list[dict]) -> bool | None:
    source = item["expected_source_file"]
    sections = set(item["expected_section_numbers"])
    if not source:
        return None
    return any(r["source_file"] == source and r["section_number"] in sections for r in results)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api", action="store_true", help="call Gemini for full answer evaluation")
    parser.add_argument("--k", type=int, default=8)
    parser.add_argument("--questions", type=Path, default=Path("eval/questions.json"))
    parser.add_argument(
        "--index", type=Path, default=Path("index"),
        help="index/records.json for vector evaluation, or a directory of section JSON for keyword baseline",
    )
    parser.add_argument("--output", type=Path, default=Path("eval/results/latest.json"))
    args = parser.parse_args()

    questions = json.loads(args.questions.read_text(encoding="utf-8"))
    records = load_records(args.index)
    engine = None
    if args.api:
        from scripts.ask import AnswerEngine
        engine = AnswerEngine(args.index)

    results = []
    for item in questions:
        if engine:
            try:
                answer = engine.ask(item["question"], item["language"], args.k)
                retrieved = answer["sources"]
                cited = re.findall(r"\[CITE:([^\]]+)\]", answer.get("answer", ""))
                known_ids = {r["id"] for r in retrieved}
                result = {
                    "id": item["id"],
                    "expected_retrieved": expected_hit(item, retrieved),
                    "refusal_correct": answer["refused"] == item["should_say_not_sure"],
                    "hallucinated_citation": any(value not in known_ids for value in cited),
                    "expected_section_cited": (
                        any(
                            source["source_file"] == item["expected_source_file"]
                            and source["section_number"] in set(item["expected_section_numbers"])
                            and source["id"] in cited
                            for source in retrieved
                        )
                        if item["expected_source_file"] else not cited
                    ),
                    "reference_answer": item.get("reference_answer", ""),
                    "answer": answer["answer"],
                }
            except Exception as exc:
                # A temporary Gemini 503/429 should not discard results for
                # questions that were already evaluated.
                result = {
                    "id": item["id"],
                    "api_error": f"{type(exc).__name__}: {exc}",
                    "expected_retrieved": None,
                    "refusal_correct": None,
                    "hallucinated_citation": None,
                }
        else:
            retrieved = keyword_search(item["question"], records, args.k)
            result = {
                "id": item["id"],
                "expected_retrieved": expected_hit(item, retrieved),
                "refusal_correct": None,
                "hallucinated_citation": None,
                "expected_section_cited": None,
                "reference_answer": item.get("reference_answer", ""),
                "top_ids": [r["id"] for r in retrieved],
            }
        results.append(result)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(results, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Questions: {len(results)}")
    retrieval_checks = [r for r in results if r["expected_retrieved"] is not None]
    print(
        "Expected section retrieved: "
        f"{sum(r['expected_retrieved'] is True for r in retrieval_checks)}/{len(retrieval_checks)}"
    )
    if args.api:
        completed = [r for r in results if "api_error" not in r]
        print(f"API-completed questions: {len(completed)}/{len(results)}")
        print(f"Correct refusal: {sum(r['refusal_correct'] for r in completed)}/{len(completed)}")
        print(f"Hallucinated citations: {sum(r['hallucinated_citation'] for r in completed)}")
        print(f"Expected section cited: {sum(r['expected_section_cited'] for r in completed)}/{len(completed)}")
        print(f"API errors: {len(results) - len(completed)}")
    else:
        print("Answer generation/refusal checks: not run (use --api)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


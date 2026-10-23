"""Answer a labour-law question with retrieval, Gemini, and citation checks."""

from __future__ import annotations

import argparse
import json
import os
import re
import time
from dataclasses import dataclass
from pathlib import Path

import faiss
import numpy as np
from dotenv import load_dotenv
from google import genai
from google.genai import types


EMERGENCY_TERMS = re.compile(r"\b(assault|arrest|abuse|self[- ]harm|suicide|violence)\b", re.IGNORECASE)
CITATION = re.compile(r"\[CITE:([^\]]+)\]")


@dataclass
class SearchResult:
    record: dict
    score: float


class AnswerEngine:
    def __init__(self, index_dir: Path = Path("index")) -> None:
        load_dotenv()
        self.embedding_model = os.getenv("EMBED_MODEL")
        self.chat_model = os.getenv("CHAT_MODEL")
        if not os.getenv("GEMINI_API_KEY"):
            raise RuntimeError("GEMINI_API_KEY is missing from .env")
        if not self.embedding_model or not self.chat_model:
            raise RuntimeError("EMBED_MODEL and CHAT_MODEL must be set in .env")
        self.index = faiss.read_index(str(index_dir / "sections.faiss"))
        self.records = json.loads((index_dir / "records.json").read_text(encoding="utf-8"))
        self.client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
        self.min_score = float(os.getenv("MIN_RETRIEVAL_SCORE", "0.35"))

    def retrieve(self, question: str, k: int = 8) -> list[SearchResult]:
        response = self.client.models.embed_content(model=self.embedding_model, contents=[question])
        query = np.asarray([response.embeddings[0].values], dtype="float32")
        faiss.normalize_L2(query)
        scores, positions = self.index.search(query, min(k, len(self.records)))
        return [
            SearchResult(self.records[int(position)], float(score))
            for score, position in zip(scores[0], positions[0])
            if int(position) >= 0
        ]

    @staticmethod
    def emergency_response() -> dict:
        return {
            "answer": (
                "This may involve an immediate safety or criminal concern. If anyone "
                "is in immediate danger, contact local emergency services or the police. "
                "For legal assistance, contact the Legal Aid Commission or a qualified lawyer."
            ),
            "sources": [], "refused": True, "reason": "emergency_safety_concern",
        }

    @staticmethod
    def low_confidence_response(results: list[SearchResult]) -> dict:
        return {
            "answer": (
                "I’m not sure this collection contains enough information to answer "
                "that question reliably. Please contact the Department of Labour, the "
                "Legal Aid Commission, or a qualified lawyer."
            ),
            "sources": [r.record for r in results[:3]],
            "refused": True, "reason": "low_retrieval_confidence",
        }

    @staticmethod
    def context(results: list[SearchResult]) -> str:
        blocks = []
        for number, result in enumerate(results, start=1):
            record = result.record
            blocks.append("\n".join([
                f"SOURCE {number}",
                f"ID: {record['id']}",
                f"Act: {record['act_name']}",
                f"Section: {record['section_number']}",
                f"Heading: {record.get('heading', '')}",
                f"Status: {record.get('status', 'verify')}",
                f"Text: {record['text']}",
            ]))
        return "\n\n---\n\n".join(blocks)

    def prompt(self, question: str, language: str, results: list[SearchResult], strict: bool = False) -> str:
        citation_rule = (
            "Every legal claim must end with an exact marker like [CITE:record_id]. "
            "Use only IDs in the sources."
        )
        if strict:
            citation_rule += " Do not mention any Act, section, deadline, amount, or exception without a citation marker."
        return f"""You are Nithi Sahaya, a Sri Lankan labour-law information assistant.

Answer using ONLY the source records below. Never invent law, section numbers,
deadlines, amounts, coverage rules, or procedures.

Format the answer as:
A. Simple answer
B. Legal basis
C. What to do next

Use plain language and reply in: {language}.
Say when the sources are insufficient. Mention relevant exclusions. Amounts and
rates marked verify must be confirmed with the Department of Labour.
This is legal information, not legal advice. Recommend a lawyer or Legal Aid
Commission for serious matters.

{citation_rule}

USER QUESTION:
{question}

{self.context(results)}
"""

    @staticmethod
    def citation_valid(answer: str, results: list[SearchResult]) -> bool:
        allowed = {result.record["id"] for result in results}
        cited = CITATION.findall(answer)
        return bool(cited) and all(item in allowed for item in cited)

    def generate(self, prompt: str) -> str:
        last_error: Exception | None = None
        for attempt in range(4):
            try:
                response = self.client.models.generate_content(
                    model=self.chat_model,
                    contents=prompt,
                )
                return response.text or ""
            except Exception as exc:
                last_error = exc
                if attempt == 3 or not any(code in str(exc) for code in ("503", "429")):
                    raise
                time.sleep(10 * (attempt + 1))
        raise RuntimeError("Gemini generation failed") from last_error

    @staticmethod
    def fallback(results: list[SearchResult]) -> dict:
        return {
            "answer": (
                "I could not produce a safely verified answer from the retrieved legal "
                "sections. Please contact the Department of Labour, the Legal Aid Commission, "
                "or a qualified lawyer."
            ),
            "sources": [r.record for r in results],
            "refused": True, "reason": "citation_validation_failed",
        }

    def ask(self, question: str, language: str = "English", k: int = 8) -> dict:
        if EMERGENCY_TERMS.search(question):
            return self.emergency_response()
        results = self.retrieve(question, k)
        if not results or results[0].score < self.min_score:
            return self.low_confidence_response(results)

        answer = self.generate(self.prompt(question, language, results))
        if not self.citation_valid(answer, results):
            answer = self.generate(self.prompt(question, language, results, strict=True))
        if not self.citation_valid(answer, results):
            return self.fallback(results)
        return {
            "answer": answer,
            "sources": [r.record for r in results],
            "refused": False,
            "retrieval_scores": [r.score for r in results],
        }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("question")
    parser.add_argument("--language", default="English", help="response language, e.g. English, Sinhala, or Tamil")
    parser.add_argument("--k", type=int, default=8)
    args = parser.parse_args()
    result = AnswerEngine().ask(args.question, language=args.language, k=args.k)
    print(result["answer"])
    print("\nSources:")
    for source in result["sources"]:
        print(f"- {source['act_name']} s.{source['section_number']} ({source['source_file']} p.{source['source_page']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


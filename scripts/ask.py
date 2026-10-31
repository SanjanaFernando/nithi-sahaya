"""Answer a labour-law question with retrieval, Gemini, and citation checks."""

from __future__ import annotations

import argparse
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path

import faiss
import numpy as np
from dotenv import load_dotenv
from google import genai
from google.genai import types


EMERGENCY_TERMS = re.compile(r"\b(assault|arrest|abuse|self[- ]harm|suicide|violence)\b", re.IGNORECASE)
CITATION = re.compile(r"\[CITE:([^\]]+)\]")
LABOUR_INTENT = re.compile(
    r"\b(employer|employee|worker|work|workplace|job|employment|labour|labor|"
    r"wage|salary|payroll|overtime|shift|hours|leave|maternity|epf|etf|"
    r"gratuity|dismiss\w*|terminat\w*|retir\w*|redundan\w*|union|factory|"
    r"workman|commissioner|pension|allowance|deduction|weda|wada|sewak\w*|"
    r"sevaka|vetan|wetan|padi|niwadu|sramaya)\b",
    re.IGNORECASE,
)
LOCAL_LABOUR_TERMS = re.compile(
    r"\u0dc3\u0dda\u0dc0\u0d9a|\u0d9a\u0db8\u0dca\u0d9a\u0dbb\u0dd4|"
    r"\u0dbb\u0dd0\u0d9a\u0dd2\u0dba\u0dcf|\u0dc0\u0dd0\u0da9|"
    r"\u0dc0\u0dd0\u0da7\u0dd4\u0db4\u0dca|\u0d85\u0dad\u0dd2\u0d9a\u0dcf\u0dbd|"
    r"\u0db1\u0dd2\u0dc0\u0dcf\u0da9\u0dd4|\u0dc0\u0dd2\u0dc1\u0dca\u200d\u0dbb\u0dcf\u0db8|"
    r"\u0ba4\u0bca\u0bb4\u0bbf\u0bb2\u0bbe\u0bb3\u0bbf|\u0ba4\u0bca\u0bb4\u0bbf\u0bb2|"
    r"\u0bb5\u0bc7\u0bb2\u0bc8|\u0b8a\u0bb4\u0bbf\u0baf\u0bb0|"
    r"\u0b9a\u0bae\u0bcd\u0baa\u0bb3\u0bae|\u0b8a\u0ba4\u0bbf\u0baf\u0bae|"
    r"\u0b93\u0baf\u0bcd\u0bb5\u0bc1|\u0bb5\u0bbf\u0b9f\u0bc1\u0baa\u0bcd\u0baa\u0bc1|"
    r"\u0baa\u0ba3\u0bbf\u0ba8\u0bc0\u0b95\u0bcd\u0b95\u0bae"
)
CLEAR_NON_LABOUR = re.compile(
    r"\b(adoption|divorce|custody|house rent|property law|income tax|"
    r"weather|recipe|football|homework)\b",
    re.IGNORECASE,
)


@dataclass
class SearchResult:
    record: dict
    score: float


class GeminiRequestFailure(RuntimeError):
    """A Gemini API failure annotated with a safe operation label."""

    def __init__(self, stage: str, status: int | None = None, detail: str = "") -> None:
        super().__init__(f"Gemini request failed during {stage}")
        self.stage = stage
        self.code = status
        # Keep a short upstream diagnostic for server logs; never expose it to API callers.
        api_key = os.getenv("GEMINI_API_KEY", "")
        safe_detail = str(detail).replace(api_key, "[redacted]") if api_key else str(detail)
        self.detail = " ".join(safe_detail.split())[:500]


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
        review_path = Path("audit/current_law_review.json")
        review = json.loads(review_path.read_text(encoding="utf-8")) if review_path.exists() else {}
        self.law_review = {
            item["source_file"]: item
            for item in review.get("sources", [])
        }
        timeout_ms = max(1_000, int(os.getenv("GEMINI_HTTP_TIMEOUT_MS", "120000")))
        retry_attempts = max(1, min(3, int(os.getenv("GEMINI_RETRY_ATTEMPTS", "1"))))
        self.client = genai.Client(
            api_key=os.environ["GEMINI_API_KEY"],
            http_options=types.HttpOptions(
                timeout=timeout_ms,
                retry_options=types.HttpRetryOptions(
                    attempts=retry_attempts,
                    initial_delay=0.5,
                    max_delay=2.0,
                    jitter=0.2,
                ),
            ),
        )
        thinking_level = os.getenv("GEMINI_THINKING_LEVEL", "low").casefold()
        self.thinking_level = thinking_level if thinking_level in {"low", "medium", "high"} else "low"
        self.min_score = float(os.getenv("MIN_RETRIEVAL_SCORE", "0.35"))

    def retrieve(self, question: str, k: int = 8) -> list[SearchResult]:
        try:
            response = self.client.models.embed_content(model=self.embedding_model, contents=[question])
        except Exception as exc:
            raise GeminiRequestFailure("query_embedding", getattr(exc, "code", None), str(exc)) from exc
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

    def check_scope(self, question: str) -> tuple[bool, str]:
        """Use fast local topic checks; fail closed without a separate model call."""
        normalized = question.casefold()
        if CLEAR_NON_LABOUR.search(normalized) and not LABOUR_INTENT.search(normalized):
            return False, "matched a clearly unrelated topic"
        if LABOUR_INTENT.search(normalized) or LOCAL_LABOUR_TERMS.search(question):
            return True, "matched a local labour-law topic phrase"
        return False, "no supported labour-law topic phrase was detected"

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
                f"Corpus QA status (not a legal-value marker): {record.get('status', 'verify')}",
                f"Scope status: {record.get('scope_status', 'not reviewed')}",
                f"Scope notes: {record.get('scope_notes', 'No scope notes available.')}",
                f"Text: {record['text']}",
            ]))
        return "\n\n---\n\n".join(blocks)

    def prompt(self, question: str, language: str, results: list[SearchResult], strict: bool = False) -> str:
        citation_rule = "Return only the JSON object described below. Never invent record IDs."
        if strict:
            citation_rule += " If any statement cannot be tied to a supplied record ID, omit it or refuse."
        freshness = []
        for result in results:
            record = result.record
            check = self.law_review.get(record.get("source_file"), {})
            if check:
                affected_sections = {str(value) for value in check.get("affected_sections", [])}
                section_number = str(record.get("section_number", ""))
                section_currentness = (
                    f"Known stale section(s): {', '.join(sorted(affected_sections))}; "
                    f"cited section {section_number} is not among them. Full source history remains incomplete."
                    if affected_sections and section_number not in affected_sections
                    else f"This cited section is in the source-currentness review; affected sections: {', '.join(sorted(affected_sections)) or 'not narrowed'}"
                )
                freshness.append(
                    f"{record.get('source_file')} section {section_number}: AI-assisted targeted law check dated "
                    f"{check.get('review_date', 'unknown')}; source status {check.get('status', 'unknown')}; "
                    f"findings: {check.get('amendment_and_gazette_findings', 'not recorded')}; "
                    f"section note: {section_currentness}; "
                    f"uncertainty: {check.get('unresolved_uncertainty', 'not recorded')}"
                )
        freshness_context = "\n".join(freshness) or "No law-check metadata is available for these sources."
        return f"""You are Nithi Sahaya, a Sri Lankan labour-law information assistant.

Answer using ONLY the source records below. Never invent law, section numbers,
deadlines, amounts, coverage rules, or procedures.
The corpus QA status label (for example, "verify") is workflow metadata; it does
not mean that an age, amount, rate, or deadline in the source text is marked for
verification. Do not say a legal value is marked verify unless the source text
or current-law notes explicitly say so.

Use plain language and reply in: {language}.
Say when the sources are insufficient. Mention relevant exclusions. Amounts and
rates marked verify must be confirmed with the Department of Labour.
This is legal information, not legal advice. Recommend a lawyer or Legal Aid
Commission for serious matters.
For every legal statement, return a separate object with its exact supporting
record ID(s). Treat dated checks below as AI-assisted research, not proof of
current law.

For the two known statutory deadline conflicts, do not claim that either law
legally overrides the other. State both statutory periods and citations. The
interim operational target is four months for the tribunal-order conflict
(Industrial Disputes Act s.31C: six months; Act No. 13 of 2003 s.5: four months)
and two months for the TEWA approval conflict (TEWA s.2(2)(c): three months;
Act No. 13 of 2003 s.11: two months). Explicitly label these as conservative
operational targets pending legal interpretation, not settled legal deadlines.

{citation_rule}

Required JSON schema (no markdown fences):
{{
  "refuse": false,
  "refusal_text": "",
  "simple_answer": [{{"text": "one concise factual statement", "source_ids": ["exact_record_id"]}}],
  "legal_basis": [{{"text": "one legal statement", "source_ids": ["exact_record_id"]}}],
  "what_to_do_next": [{{"text": "one supported practical step", "source_ids": ["exact_record_id"]}}],
  "freshness_warning": "In {language}: say this AI-generated answer may be wrong or incomplete and may not reflect a later Act, amendment, or Gazette notice; advise checking with the Department of Labour or a qualified lawyer."
}}
Every non-empty statement item MUST cite one or more exact source IDs supplied below. If the records do not support a reliable answer, set refuse=true and provide a safe referral in refusal_text; leave statement arrays empty. Do not put legal claims in freshness_warning.

AI-ASSISTED CURRENT-LAW CHECK NOTES (not a legal determination):
{freshness_context}

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
        try:
            response = self.client.models.generate_content(
                model=self.chat_model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    thinking_config=types.ThinkingConfig(thinking_level=self.thinking_level),
                ),
            )
            return response.text or ""
        except Exception as exc:
            error_text = str(exc).casefold()
            daily_quota_exhausted = any(
                marker in error_text
                for marker in ("per day", "per-day", "requests per day", "daily quota")
            )
            if daily_quota_exhausted:
                raise RuntimeError(
                    "Gemini's daily generation quota is exhausted; retry after the quota resets."
                ) from exc
            raise GeminiRequestFailure("answer_generation", getattr(exc, "code", None), str(exc)) from exc

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

    @staticmethod
    def render_structured_answer(raw: str, results: list[SearchResult]) -> str | None:
        """Validate model-provided source IDs and render resolvable citations."""
        try:
            data = json.loads(raw)
        except (TypeError, json.JSONDecodeError):
            return None
        if not isinstance(data, dict) or data.get("refuse") is True:
            return None
        allowed = {result.record["id"] for result in results}
        rendered = []
        for label, key in (("A. Simple answer", "simple_answer"), ("B. Legal basis", "legal_basis"), ("C. What to do next", "what_to_do_next")):
            statements = data.get(key)
            if not isinstance(statements, list):
                return None
            lines = []
            for item in statements:
                if not isinstance(item, dict) or not isinstance(item.get("text"), str):
                    return None
                text = item["text"].strip()
                ids = item.get("source_ids")
                if not text or not isinstance(ids, list) or not ids:
                    return None
                if any(not isinstance(source_id, str) or source_id not in allowed for source_id in ids):
                    return None
                markers = " ".join(f"[CITE:{source_id}]" for source_id in ids)
                lines.append(f"{text} {markers}")
            if lines:
                rendered.append(label + "\n" + "\n".join(lines))
        warning = data.get("freshness_warning")
        if not rendered or not isinstance(warning, str) or not warning.strip():
            return None
        rendered.append(warning.strip())
        answer = "\n\n".join(rendered)
        return answer if AnswerEngine.citation_valid(answer, results) else None

    def ask(self, question: str, language: str = "English", k: int = 8) -> dict:
        if EMERGENCY_TERMS.search(question):
            return self.emergency_response()
        in_scope, scope_reason = self.check_scope(question)
        if not in_scope:
            unavailable = scope_reason.startswith("scope_check_unavailable:")
            return {
                "answer": (
                    "I cannot safely determine that this question is within this Sri Lankan labour-law "
                    "assistant's scope. Please ask a qualified professional in the relevant area. "
                    "AI-generated answers may be wrong or incomplete and may not reflect a later Act, "
                    "amendment, or Gazette notice; verify current law with an official source or a qualified lawyer."
                ),
                "sources": [],
                "refused": True,
                "reason": "scope_check_unavailable" if unavailable else "out_of_scope",
            }
        results = self.retrieve(question, k)
        if not results or results[0].score < self.min_score:
            return self.low_confidence_response(results)

        top_score = results[0].score
        stale_sources = [
            r for rank, r in enumerate(results[:3], start=1)
            if self.law_review.get(r.record.get("source_file"), {}).get("status") == "corpus_update_required"
            and (
                not self.law_review.get(r.record.get("source_file"), {}).get("affected_sections")
                or str(r.record.get("section_number")) in {
                    str(value) for value in self.law_review.get(r.record.get("source_file"), {}).get("affected_sections", [])
                }
            )
            and top_score - r.score <= 0.05
        ]
        if stale_sources:
            return {
                "answer": (
                    "I cannot safely answer from this result because the retrieved legal text is known to "
                    "need an update. An AI-generated answer may be wrong or may not reflect a later Act, "
                    "amendment, or Gazette notice. Please verify the current text with the Department of "
                    "Labour or a qualified lawyer."
                ),
                "sources": [r.record for r in stale_sources],
                "refused": True,
                "reason": "corpus_update_required",
            }

        raw = self.generate(self.prompt(question, language, results))
        answer = self.render_structured_answer(raw, results)
        if answer is None:
            raw = self.generate(self.prompt(question, language, results, strict=True))
            answer = self.render_structured_answer(raw, results)
        if answer is None:
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


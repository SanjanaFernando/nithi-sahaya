"""Answer a labour-law question with retrieval, Gemini, and citation checks."""

from __future__ import annotations

import argparse
import json
import math
import os
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

import faiss
import numpy as np
from dotenv import load_dotenv
from google import genai
from google.genai import types


EMERGENCY_TERMS = re.compile(r"\b(assault|arrest|abuse|self[- ]harm|suicide|violence)\b", re.IGNORECASE)
CITATION = re.compile(r"\[CITE:([^\]]+)\]")
WEB_CITATION = re.compile(r"\[WEB:([^\]]+)\]")
TOKEN = re.compile(r"[a-z0-9]+|[\u0b80-\u0bff]+|[\u0c00-\u0d7f]+", re.IGNORECASE)
LABOUR_INTENT = re.compile(
    r"\b(employer|employee|worker|work|workplace|job|employment|labour|labor|"
    r"wages?|salar(?:y|ies)|payroll|overtime|shift|hours|leave|maternity|epf|etf|"
    r"gratuity|dismiss\w*|terminat\w*|retir\w*|redundan\w*|union|factory|"
    r"workman|commissioner|pension|allowance|deduction|weda|wada|sewak\w*|"
    r"sevaka|vetan|wetan|padi|niwadu|sramaya)\b",
    re.IGNORECASE,
)
UNPAID_WAGES_INTENT = re.compile(
    r"\b(unpaid|underpaid|short[- ]paid|withheld\s+(?:pay|wages?|salary)|"
    r"(?:not|never)\s+(?:been\s+|getting\s+|being\s+)?pa(?:i|y)ed|"
    r"(?:haven't|havent|hasn't|hasnt)\s+been\s+pa(?:i|y)ed|"
    r"missing\s+(?:pay|wages?|salary)|salary\s+(?:not\s+paid|delay\w*))\b",
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
SMALLTALK = re.compile(
    r"\s*(?:(?:hi|hello|hey|good morning|good afternoon|good evening|good night)"
    r"(?:\s+(?:there|srilaw))?(?:\s*,?\s+how are you(?: doing)?)?|"
    r"how are you(?: doing)?|how's it going|"
    r"what's up|thank you|thanks|thanks a lot|who are you|what is your name|"
    r"what's your name|nice to meet you|bye|goodbye)[.!?,\s]*\s*",
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
        self.lexical_documents = [
            Counter(self._tokens(" ".join(str(record.get(key, "")) for key in ("act_name", "section_number", "heading", "text"))))
            for record in self.records
        ]
        self.average_document_length = (
            sum(sum(document.values()) for document in self.lexical_documents) / max(len(self.lexical_documents), 1)
        )
        self.document_frequency: Counter[str] = Counter()
        for document in self.lexical_documents:
            self.document_frequency.update(document.keys())
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
        self.google_search_enabled = os.getenv("GEMINI_GOOGLE_SEARCH", "true").casefold() not in {"0", "false", "no", "off"}
        self.min_score = float(os.getenv("MIN_RETRIEVAL_SCORE", "0.35"))

    @staticmethod
    def _tokens(text: str) -> list[str]:
        return [token.casefold() for token in TOKEN.findall(text)]

    def _lexical_scores(self, query: str) -> list[float]:
        terms = self._tokens(query)
        if not terms:
            return [0.0] * len(self.records)
        total_docs = len(self.records)
        scores = []
        for document in self.lexical_documents:
            length = sum(document.values())
            score = 0.0
            for term in terms:
                frequency = document.get(term, 0)
                if not frequency:
                    continue
                df = self.document_frequency.get(term, 0)
                inverse_frequency = math.log(1 + (total_docs - df + 0.5) / (df + 0.5))
                normalization = frequency + 1.2 * (1 - 0.75 + 0.75 * length / max(self.average_document_length, 1))
                score += inverse_frequency * frequency * 2.2 / normalization
            scores.append(score)
        return scores

    def retrieve(self, question: str, k: int = 8) -> list[SearchResult]:
        try:
            retrieval_query = question
            if UNPAID_WAGES_INTENT.search(question):
                retrieval_query += " unpaid wages salary non-payment wage complaint Labour Department Commissioner of Labour"
            if re.search(r"\bETF\b", question, re.IGNORECASE) and not re.search(r"\bEPF\b", question, re.IGNORECASE):
                retrieval_query += " Employees' Trust Fund Act"
                if re.search(r"\b(age|claim|withdraw|benefit|retire)\w*\b", question, re.IGNORECASE):
                    retrieval_query += " section 23 termination employment five years over sixty"
            elif re.search(r"\bEPF\b", question, re.IGNORECASE) and not re.search(r"\bETF\b", question, re.IGNORECASE):
                retrieval_query += " Employees' Provident Fund Act"
            response = self.client.models.embed_content(model=self.embedding_model, contents=[retrieval_query])
        except Exception as exc:
            raise GeminiRequestFailure("query_embedding", getattr(exc, "code", None), str(exc)) from exc
        query = np.asarray([response.embeddings[0].values], dtype="float32")
        faiss.normalize_L2(query)
        candidate_count = min(max(k * 3, k), len(self.records))
        semantic_scores, semantic_positions = self.index.search(query, candidate_count)
        lexical_scores = self._lexical_scores(retrieval_query)
        lexical_positions = np.argsort(np.asarray(lexical_scores))[-candidate_count:][::-1]
        max_lexical = max((lexical_scores[int(position)] for position in lexical_positions), default=0.0)
        candidates: dict[int, tuple[float, float]] = {}
        for score, position in zip(semantic_scores[0], semantic_positions[0]):
            if int(position) >= 0:
                candidates[int(position)] = (float(score), lexical_scores[int(position)])
        for position in lexical_positions:
            position = int(position)
            semantic, _ = candidates.get(position, (0.0, 0.0))
            candidates[position] = (semantic, lexical_scores[position])
        ranked = sorted(
            candidates.items(),
            key=lambda item: 0.65 * item[1][0] + 0.35 * (item[1][1] / max_lexical if max_lexical else 0.0),
            reverse=True,
        )[:min(k, len(candidates))]
        return [
            SearchResult(
                self.records[position],
                0.65 * semantic + 0.35 * (lexical / max_lexical if max_lexical else 0.0),
            )
            for position, (semantic, lexical) in ranked
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
        """Reject clearly unrelated topics; defer ambiguous intent to grounded classification."""
        normalized = question.casefold()
        if CLEAR_NON_LABOUR.search(normalized) and not LABOUR_INTENT.search(normalized):
            return False, "matched a clearly unrelated topic"
        if LABOUR_INTENT.search(normalized) or UNPAID_WAGES_INTENT.search(normalized) or LOCAL_LABOUR_TERMS.search(question):
            return True, "matched a local labour-law topic phrase"
        return True, "ambiguous intent deferred to grounded classification"

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

    def prompt(
        self,
        question: str,
        language: str,
        results: list[SearchResult],
        strict: bool = False,
        retrieval_low_confidence: bool = False,
    ) -> str:
        citation_rule = "Return only the JSON object described below. Never invent record IDs or web URLs."
        if strict:
            citation_rule += (
                " If any statement cannot be tied to a supplied record ID or returned web URL, omit it or refuse."
                if not retrieval_low_confidence else
                " Never invent record IDs or web URLs; for this knowledge-base gap, use the cautious alternative-answer instructions if no source is available."
            )
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
        retrieval_note = (
            "The local knowledge-base search did not find sufficiently relevant passages. "
            "Do not cite or rely on unrelated local passages. Give a useful alternative "
            "Gemini answer based on relevant authoritative Google Search results when "
            "available. If none are available, provide a cautious general overview, "
            "identify it as not verified against the knowledge base, and direct the "
            "user to confirm current legal details with an official source. Do not say "
            "that you cannot answer."
            if retrieval_low_confidence else ""
        )
        return f"""You are SriLaw AI, a Sri Lankan labour-law information assistant.

First determine whether the user's intent is about a Sri Lankan workplace,
employment relationship, worker entitlement, employer obligation, or labour-law
complaint. Interpret ordinary typos, misspellings, and imperfect grammar from
context. Do not require exact legal vocabulary. If the intent is clearly outside
Sri Lankan labour law, or cannot reasonably be understood as a labour-law
question, set refuse=true and give a brief referral; do not answer another legal
area. For unclear but plausibly labour-related questions, ask one concise
clarifying question instead of making up the situation.

Use the retrieved source records and Google Search results together. Never invent
law, section numbers, deadlines, amounts, coverage rules, or procedures. Treat the
knowledge base as a record of the indexed legal text, and use Google Search to
check for newer official Sri Lankan laws, amendments, regulations, and notices.
Prefer official sources such as labourdept.gov.lk, documents.gov.lk,
parliament.lk, etfb.lk, and cbsl.gov.lk for legal or fund information.
The corpus QA status label (for example, "verify") is workflow metadata; it does
not mean that an age, amount, rate, or deadline in the source text is marked for
verification. Do not say a legal value is marked verify unless the source text
or current-law notes explicitly say so.

Use plain language and reply in: {language}.
Say when the sources are insufficient. Mention relevant exclusions. Amounts and
rates marked verify must be confirmed with the Department of Labour.
This is legal information, not legal advice. Recommend a lawyer or Legal Aid
Commission for serious matters.
For every legal statement, return a separate object and cite exact supporting
knowledge-base record IDs and/or exact Google Search URLs returned by the tool.
Treat dated checks below as AI-assisted research, not proof of current law.
Keep Employees' Provident Fund (EPF) and Employees' Trust Fund (ETF) rules
separate. Never transfer an age or withdrawal condition from one fund to the other.

If a source below has status corpus_update_required or an unresolved currentness
warning, still answer the labour-law question from retrieved text when it supports
an answer. Do not refuse solely because a source may be outdated. Clearly say the
answer is based on available source text and may not reflect later amendments,
regulations, or Gazette notices. Do not describe that source as confirmed current
law. Refuse only if the retrieved text does not support a reliable answer or
another safety rule requires refusal.
When search results are available, compare them with the retrieved sections.
Never treat an unofficial page as authoritative. If an official web source
conflicts with an older knowledge-base record, state the discrepancy, cite both
sources, and explain which information appears newer. If no useful official web
result is found, answer from the knowledge-base text with a clear currentness
warning. Do not silently present an older record as current law.

For the two known statutory deadline conflicts, do not claim that either law
legally overrides the other. State both statutory periods and citations. The
interim operational target is four months for the tribunal-order conflict
(Industrial Disputes Act s.31C: six months; Act No. 13 of 2003 s.5: four months)
and two months for the TEWA approval conflict (TEWA s.2(2)(c): three months;
Act No. 13 of 2003 s.11: two months). Explicitly label these as conservative
operational targets pending legal interpretation, not settled legal deadlines.

{citation_rule}
{retrieval_note}

Required JSON schema (no markdown fences):
{{
  "refuse": false,
  "refusal_text": "",
  "simple_answer": [{{"text": "one concise factual statement", "source_ids": ["exact_record_id"], "web_urls": []}}],
  "legal_basis": [{{"text": "one legal statement", "source_ids": ["exact_record_id"], "web_urls": []}}],
  "what_to_do_next": [{{"text": "one supported practical step", "source_ids": ["exact_record_id"], "web_urls": []}}],
  "freshness_warning": "In {language}: say this AI-generated answer may be wrong or incomplete and may not reflect a later Act, amendment, or Gazette notice; advise checking with the Department of Labour or a qualified lawyer."
}}
Every non-empty statement item MUST cite one or more exact knowledge-base IDs
or exact web URLs supplied by Google Search. If neither source supports a
reliable answer for a knowledge-base gap, answer cautiously from general
knowledge and leave source_ids and web_urls empty. Clearly state that the
alternative is not verified against the knowledge base. For other cases, if
neither source supports a reliable answer, set refuse=true and provide a safe
referral in refusal_text; leave statement arrays empty. Do not put legal claims
in freshness_warning.

AI-ASSISTED CURRENT-LAW CHECK NOTES (not a legal determination):
{freshness_context}

USER QUESTION:
{question}

{self.context(results)}
"""

    @staticmethod
    def citation_valid(answer: str, results: list[SearchResult], web_sources: list[dict] | None = None) -> bool:
        allowed = {result.record["id"] for result in results}
        allowed_web = {item.get("url") for item in (web_sources or []) if isinstance(item.get("url"), str)}
        cited = CITATION.findall(answer)
        cited_web = WEB_CITATION.findall(answer)
        return bool(cited or cited_web) and all(item in allowed for item in cited) and all(item in allowed_web for item in cited_web)

    def generate(self, prompt: str, use_google_search: bool = False) -> tuple[str, list[dict]]:
        try:
            config = types.GenerateContentConfig(
                response_mime_type="application/json",
                thinking_config=types.ThinkingConfig(thinking_level=self.thinking_level),
                tools=[types.Tool(google_search=types.GoogleSearch())] if use_google_search else None,
            )
            response = self.client.models.generate_content(
                model=self.chat_model,
                contents=prompt,
                config=config,
            )
            web_sources = []
            candidates = getattr(response, "candidates", None) or []
            metadata = getattr(candidates[0], "grounding_metadata", None) if candidates else None
            for chunk in getattr(metadata, "grounding_chunks", None) or []:
                web = getattr(chunk, "web", None)
                uri = getattr(web, "uri", None) if web else None
                if isinstance(uri, str) and uri.startswith(("https://", "http://")):
                    item = {"url": uri, "title": getattr(web, "title", None) or uri}
                    if item not in web_sources:
                        web_sources.append(item)
            return response.text or "", web_sources
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
            if use_google_search:
                # If Search grounding is unavailable for this key or request, still
                # provide the knowledge-base answer with its freshness warning.
                return self.generate(prompt, use_google_search=False)
            raise GeminiRequestFailure("answer_generation", getattr(exc, "code", None), str(exc)) from exc

    def generate_smalltalk(self, message: str, language: str) -> str:
        prompt = (
            "You are SriLaw AI, a friendly assistant. Reply naturally and briefly to this "
            "casual greeting or social message in " + language + ". Do not turn it into a "
            "legal answer, mention the knowledge base, or claim personal feelings or experiences.\n\n"
            "User: " + message
        )
        try:
            response = self.client.models.generate_content(
                model=self.chat_model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    thinking_config=types.ThinkingConfig(thinking_level=self.thinking_level),
                ),
            )
            answer = (response.text or "").strip()
            return answer or "Hi! How can I help you today?"
        except Exception as exc:
            raise GeminiRequestFailure("smalltalk_generation", getattr(exc, "code", None), str(exc)) from exc

    @staticmethod
    def fallback(results: list[SearchResult]) -> dict:
        return {
            "answer": (
                "Please confirm this with the Department of Labour, the Legal Aid Commission, or a qualified lawyer. "
                "The available legal sources do not provide enough support for a reliable answer."
            ),
            "sources": [r.record for r in results],
            "refused": True, "reason": "citation_validation_failed",
        }

    @staticmethod
    def render_structured_answer(raw: str, results: list[SearchResult], web_sources: list[dict] | None = None, allow_uncited: bool = False) -> str | None:
        """Validate model-provided source IDs and render resolvable citations."""
        try:
            data = json.loads(raw)
        except (TypeError, json.JSONDecodeError):
            return None
        if not isinstance(data, dict) or data.get("refuse") is True:
            return None
        allowed = {result.record["id"] for result in results}
        allowed_web = {item.get("url") for item in (web_sources or []) if isinstance(item.get("url"), str)}
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
                urls = item.get("web_urls", [])
                if not text or not isinstance(ids, list) or not isinstance(urls, list):
                    return None
                if not (ids or urls) and not allow_uncited:
                    # Drop a single uncited statement (often a generic "consult a lawyer"
                    # step) instead of discarding an otherwise fully cited answer.
                    continue
                if any(not isinstance(source_id, str) or source_id not in allowed for source_id in ids):
                    return None
                if any(not isinstance(url, str) or url not in allowed_web for url in urls):
                    return None
                markers = " ".join([*(f"[CITE:{source_id}]" for source_id in ids), *(f"[WEB:{url}]" for url in urls)])
                lines.append(f"{text} {markers}")
            if lines:
                rendered.append(label + "\n" + "\n".join(lines))
        warning = data.get("freshness_warning")
        if not rendered or not isinstance(warning, str) or not warning.strip():
            return None
        rendered.append(warning.strip())
        answer = "\n\n".join(rendered)
        return answer if allow_uncited or AnswerEngine.citation_valid(answer, results, web_sources) else None

    def ask(self, question: str, language: str = "English", k: int = 8) -> dict:
        if EMERGENCY_TERMS.search(question):
            return self.emergency_response()
        if SMALLTALK.fullmatch(question):
            return {
                "answer": self.generate_smalltalk(question, language),
                "sources": [], "refused": False, "reason": "smalltalk",
            }
        in_scope, _ = self.check_scope(question)
        if not in_scope:
            return {
                "answer": (
                    "SriLaw AI focuses on Sri Lankan labour law, so this topic may be outside its scope. "
                    "Please check with an official source or a qualified professional for guidance. "
                    "AI-generated information may be incomplete or may not reflect recent changes to the law."
                ),
                "sources": [],
                "refused": True,
                "reason": "out_of_scope",
            }
        retrieved = self.retrieve(question, k)
        retrieval_low_confidence = not retrieved or retrieved[0].score < self.min_score
        results = [] if retrieval_low_confidence else retrieved

        raw, web_sources = self.generate(
            self.prompt(question, language, results, retrieval_low_confidence=retrieval_low_confidence),
            use_google_search=self.google_search_enabled,
        )
        answer = self.render_structured_answer(raw, results, web_sources, allow_uncited=retrieval_low_confidence)
        if answer is None:
            raw, web_sources = self.generate(
                self.prompt(
                    question,
                    language,
                    results,
                    strict=True,
                    retrieval_low_confidence=retrieval_low_confidence,
                ),
                use_google_search=self.google_search_enabled,
            )
            answer = self.render_structured_answer(raw, results, web_sources, allow_uncited=retrieval_low_confidence)
        if answer is None:
            if retrieval_low_confidence:
                return {
                    "answer": (
                        "The current knowledge base did not find relevant supporting documents. "
                        "Please check an official source or contact the Department of Labour, "
                        "the Legal Aid Commission, or a qualified lawyer for guidance on this question."
                    ),
                    "sources": [], "refused": False, "reason": "alternative_generation_unavailable",
                }
            return self.fallback(results)
        if retrieval_low_confidence:
            answer = (
                "The current knowledge base did not find relevant supporting documents. "
                "Alternative Gemini answer (not verified against the knowledge base):\n\n"
                + answer
            )
        cited_ids = set(CITATION.findall(answer))
        cited_urls = set(WEB_CITATION.findall(answer))
        cited_records = [r.record for r in results if r.record.get("id") in cited_ids]
        cited_web_sources = [item for item in web_sources if item.get("url") in cited_urls]
        return {
            "answer": answer,
            "sources": cited_records,
            "refused": False,
            "retrieval_scores": [r.score for r in results],
            "web_sources": cited_web_sources,
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


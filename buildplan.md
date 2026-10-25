# Nithi Sahaya: Build Plan from 44 Labour-Law PDFs to a Working AI Website

Goal: turn 44 clear English PDFs (Department of Labour compiled labour code) into a legal-information assistant with a website, using free tools.

## Re-audit update — 25 October 2026

This is a working status snapshot after rechecking Phases 1–6. A checked box means
the repository artifact exists and its automated checks passed; it does not mean
the legal content has been approved for public use.

| Phase | Status | Current finding |
|---|---|---|
| 0 Setup | Done locally | The project environment and required Python packages are present. |
| 1 Extract | Inventory passed; sparse-page dispositions recorded | On 25 October 2026, 44 source PDFs matched 44 text extracts by filename; the extraction report records 44 original-source SHA-256 hashes and zero duplicate groups. The 82 short-page warnings are dispositioned: 74 repaired using matching OCR copies, 8 verified as chapter contents/divider or running-header pages. OCR accuracy still needs proofreading before legal use. |
| 2 Clean and split | Partial; warning and metadata reviews complete | 2,094 records are produced. All 158 fewer-than-10-word warnings have source-linked dispositions in `audit/short_section_review.json`; warnings remain visible in QC. The 31 missing Act identifiers are filled with title-page evidence in `audit/act_number_year_review.json`. `scope_notes` and `topics` are populated for all records with source-linked method and evidence in `audit/scope_topics_review.json`; Act-wide scope has not been inferred. |
| 3 Legal checks | Not complete; current-law review underway | Targeted official-source checks found later amendments to employment-of-women, national-minimum-wage, budgetary-relief, factories, EPF, termination, industrial-disputes, and shop-and-office laws, plus updated subsidiary instruments. The corpus needs updates and a complete amendment/Gazette review. Two known deadline conflicts and lawyer-approved summaries remain open. |
| 4 Search index | Built; retrieval review pending | The corrected index now contains 2,094 records and 2,094 normalized, 3,072-dimensional vectors using `gemini-embedding-001`. The checkpoint is complete. Representative semantic-search checks still need review. |
| 5 Answer engine | Implemented, not fully evaluated | The answer engine exists, but it must be evaluated after Phase 4 completes. |
| 6 Evaluation | Test set improved; full run pending | There are 42 questions, 10 in Sinhala, Tamil, or Singlish, each with a reference answer. The keyword baseline retrieved an expected section for 18 of 37 in-scope questions. Generated-answer, citation, and refusal evaluation must be rerun against the rebuilt index. |

The Gemini free-tier daily and per-minute embedding quotas slowed the re-index.
The complete checkpoint is saved, and the corrected index has now been built.
Do not launch the public pilot until the completion gate below and Phase 3
review are complete.

Approach: **RAG (retrieval-augmented generation)**. You do not train a model. For each question, the system finds the most relevant sections from your PDFs and gives them to Gemini, which writes a plain-language answer with citations.

> Model names, free-tier limits and library versions change often. Keep model names in a `.env` file and check the current docs before you start.

---

## Folder layout

```
nithi-sahaya/
  raw_pdfs/            the 44 PDFs, untouched
  text/                one .txt per PDF (Phase 1)
  sections/            one .json per Act, one record per section (Phase 2)
  index/               embeddings + search index (Phase 4)
  eval/                test questions and results (Phase 6)
  backend/             API code (Phase 7)
  frontend/            website (Phase 8)
  scripts/             extract.py, split.py, build_index.py, ask.py
  .env                 API key and model names (never commit this)
```

---

## Phase 0: Setup (half a day)

1. Install Python 3.11+ and Git. Create a virtual environment.
2. Install the libraries:
   `pip install pymupdf google-genai faiss-cpu numpy python-dotenv fastapi uvicorn`
3. Get a Gemini API key from Google AI Studio. Put it in `.env`:
   ```
   GEMINI_API_KEY=your_key
   CHAT_MODEL=<current flash model name>
   EMBED_MODEL=<current embedding model name>
   ```
4. Create a GitHub repository (private). Add `.env` to `.gitignore`.
5. Copy the 44 PDFs into `raw_pdfs/`. Never edit them.

Done when: `python -c "import fitz, faiss"` runs without errors.

---

## Phase 1: Extract text from all 44 PDFs (1 day)

Script `scripts/extract.py`:

```python
import fitz, pathlib
src, dst = pathlib.Path("raw_pdfs"), pathlib.Path("text")
dst.mkdir(exist_ok=True)
for pdf in sorted(src.glob("*.pdf")):
    with fitz.open(pdf) as doc:
        pages = [p.get_text() for p in doc]
    (dst / f"{pdf.stem}.txt").write_text("\n\n[[PAGE]]\n\n".join(pages), encoding="utf-8")
    print(pdf.name, len(pages), "pages,", sum(len(p) for p in pages), "chars")
```

Checks:
- Any file with fewer than ~200 characters per page is a scan and needs OCR (try `ocrmypdf` or Gemini vision).
- Open 5 random `.txt` files and read a paragraph. It should look like normal English.
- The two very large "Employment of women, young persons and children" PDFs (7 MB and 1.3 MB) are the most likely to be scans.
- Delete exact duplicates.

Done when: all 44 files have a `.txt` that reads normally.

---

## Phase 2: Clean the text and split into sections (2 to 3 days)

This phase decides most of the quality of your final answers.

### 2.1 Clean
Remove from the body text:
- repeated page headers and numbers (for example "126 WAGES BOARDS")
- the `[[PAGE]]` markers (join pages after cleaning)
- inline amendment tags like `[§ 3, 27 of 1962.]`. Save them in an `amended_by` field instead
- margin headings (for example "Short title.") if they sit on their own line. Save them as `heading`

### 2.2 Split
Cut at section numbers. A starting pattern:

```python
import re
SECTION = re.compile(r"^\s*(\d{1,3}[A-Z]{0,4})\.\s+(?=[A-Z(])", re.M)
```

It handles `1.`, `31A.`, `31DD.`, `44C.`. Special cases to handle by hand or with extra rules:
- Regulations use "2. (1)" and "Regulation 5". Split on regulation numbers.
- Schedules, forms and Gazette orders (for example the compensation formula table) are not numbered sections. Make one record per schedule or table.
- Section 31D heading is missing in the compiled Industrial Disputes Act. Check any gap in numbering (31C, 31DD) and fix it.
- Long sections (over about 800 words): split by subsection `(1)`, `(2)` and keep the parent section number in every piece.

### 2.3 Record format
One JSON object per section:

```json
{
  "id": "termination_of_employment_s2",
  "act_name": "Termination of Employment of Workmen (Special Provisions) Act",
  "act_number_year": "No. 45 of 1971",
  "doc_type": "act",
  "chapter": "Terms and Conditions of Employment",
  "section_number": "2",
  "heading": "Regulation of the termination by employers of scheduled employments",
  "text": "No employer shall terminate ...",
  "amended_by": ["Law 4 of 1976", "Act 12 of 2003"],
  "scope_notes": "Employers with 15 or more workmen; workmen with 180+ days service",
  "source_file": "ch02_termination_of_employment_act.pdf",
  "source_page": 97,
  "topics": ["dismissal", "termination", "commissioner approval"],
  "status": "verify"
}
```

`act_number_year` and `scope_notes` can be filled per Act (44 rows), then copied into every section.

Done when: `sections/` has 44 JSON files, and a spot check of 10 sections per Act shows correct numbering and text.

---

## Phase 3: Quality control and legal checks (3 to 5 days, runs alongside Phase 4)

1. **Automatic checks:** gaps or duplicates in section numbers, sections with fewer than 10 words, leftover headers or "[§" tags, odd symbols.
2. **Conflicts between documents.** Add a `conflicts_with` field and decide which controls. Known cases:
   - Labour tribunal order deadline: 6 months (Industrial Disputes Act s.31C) vs 4 months (Special Provisions Act 2003 s.5)
   - Commissioner's decision on an employer's termination application: 3 months (Termination Act s.2) vs 2 months (Special Provisions Act s.11)
3. **Time-sensitive material.** Mark fines, allowances, wage rates and compensation formulas `status: verify`. The assistant must say "please confirm the current amount with the Labour Department" when quoting these.
4. **Currency check by a lawyer:** is each Act in force, and what amended it after the edition date?
5. **Plain-language summaries:** generate a one-paragraph summary per section with Gemini, then have your legal reviewer approve them. Store as `plain_summary`.

Done when: the reviewer has signed off on at least the Acts you will launch with first.

---

## Phase 4: Embeddings and search index (1 day)

Script `scripts/build_index.py`:

1. For each record, build the text to embed: `Act name + section number + heading + text`.
2. Call the Gemini embedding model in batches (respect the free-tier rate limit; add a short sleep and retries).
3. Save vectors with `numpy` and build a FAISS index. Save the record list next to it.

```python
import json, glob, numpy as np, faiss
from google import genai
client = genai.Client()          # reads GEMINI_API_KEY
records = [r for f in glob.glob("sections/*.json") for r in json.load(open(f, encoding="utf-8"))]
texts = [f'{r["act_name"]} s.{r["section_number"]} {r["heading"]}\n{r["text"]}' for r in records]
vecs = []
for i in range(0, len(texts), 50):
    out = client.models.embed_content(model=EMBED_MODEL, contents=texts[i:i+50])
    vecs += [e.values for e in out.embeddings]
arr = np.array(vecs, dtype="float32"); faiss.normalize_L2(arr)
index = faiss.IndexFlatIP(arr.shape[1]); index.add(arr)
faiss.write_index(index, "index/sections.faiss")
json.dump(records, open("index/records.json", "w", encoding="utf-8"))
```

Improvements to add after the first version works:
- **Hybrid search:** combine vector search with keyword search (BM25) so exact terms like "gratuity" or "section 31B" are always found.
- **Query translation:** if the question is in Sinhala, Tamil or Singlish, ask Gemini to translate it to English first, and search with both the original and the translation.

Done when: searching "retirement age private sector" returns Minimum Retirement Age Act sections at the top.

---

## Phase 5: The answer engine (2 to 3 days)

Script `scripts/ask.py`. For each question:

1. Retrieve the top 6 to 8 sections.
2. Build a prompt with the question and the numbered sections.
3. Call Gemini with temperature 0.2 or lower.
4. Return the answer, plus a list of the sections used.

### System prompt (starting point)

```
You are Nithi Sahaya, a Sri Lankan labour-law information assistant.
Rules:
1. Answer ONLY from the numbered sections provided. If they do not answer the
   question, say you are not sure and tell the user to contact the Department of
   Labour or the Legal Aid Commission. Never invent sections, numbers, or amounts.
2. Format every answer as:
   A. Simple answer (plain language, no jargon)
   B. Legal basis (Act name and section number for each point)
   C. What to do next (office to visit, form, deadline)
3. If a section says its amount or rate may be outdated or "verify", tell the
   user to confirm the current figure.
4. Always mention exceptions: who is NOT covered (for example employers with
   fewer than 15 workers, probationary or casual workers, public sector).
5. Reply in the language and script of the user's question.
6. You give legal information, not legal advice. For serious matters
   recommend a lawyer or the Legal Aid Commission.
```

### Safeguards
- **Citation check:** after generation, confirm every Act and section named in the answer exists in the retrieved sections. If not, regenerate once, then fall back to the "not sure" answer.
- **Low-confidence rule:** if the best search score is below a threshold, skip generation and show the referral message.
- **Emergency rule (code, not the model):** detect words about assault, arrest, abuse or self-harm and show verified emergency contacts first. Verify every number from an official source before launch.

Done when: you can run `python scripts/ask.py "Can my employer retire me at 55?"` and get a correct answer that cites the Minimum Retirement Age Act.

---

## Phase 6: Evaluation (ongoing, start now)

1. Write **40 questions** in `eval/questions.json`, each with the correct answer, the correct section, and a flag for "should say not sure". Cover: dismissal, retrenchment, retirement age, wages and deductions, Poya day pay, EPF/ETF, gratuity, maternity benefits, trade unions, labour tribunal procedure and deadlines, women and young persons, plantation workers.
2. Include **Sinhala, Tamil and Singlish** versions of at least 10 of them.
3. Include **trick questions** where the answer is not in the data, and ones the law doesn't cover (for example a government worker asking about the Industrial Disputes Act).
4. Write `eval/run.py` that asks all questions and prints: correct section retrieved? correct citation? hallucinated section? correct refusal?
5. Re-run after every change to chunking, prompt or model.

Target before public launch: every citation real, no invented sections, and lawyer approval of the answers.

---

## Phase 6A: Complete Phases 1–6 before starting Phase 7

This is a required closeout phase. Work through each subphase and record its
artifact and pass result. Development of later phases must not be treated as
evidence that this gate has passed.

### 6A.1 Close Phase 1 and Phase 2 data-quality gaps

1. **Done 25 October 2026:** Re-ran `scripts/extract.py`. Confirmed 44 source
   PDFs, 44 text extracts, matching source names, 44 SHA-256 hashes, and zero
   exact duplicate groups. The source PDFs were only read; extraction outputs
   and `text/extraction_report.json` were written under `text/`.
2. **Done 25 October 2026:** Reviewed all 82 source-page warnings and saved
   per-page evidence/dispositions in `audit/short_page_review.json`. Re-extracted
   74 image-only pages from matching OCR copies; visually checked and recorded
   the other 8 as chapter contents/dividers or running headers. Reviewed all
   158 short section records against their source pages and saved a disposition
   and source-page evidence for each in `audit/short_section_review.json`.
   These warnings remain in QC; the review records why they are legitimate
   short titles, contents entries, form fields, schedule rows, cross-references,
   or complete short provisions. OCR accuracy proofreading remains part of
   legal review.
3. **Done 25 October 2026:** Filled `act_number_year` for all 31 affected
   records from the two source title pages. No identifier was marked unknown:
   the Minimum Wages (Indian Labour) Ordinance is No. 27 of 1927, and the
   Service Contracts Ordinance is No. 11 of 1865. Evidence, source hashes, and
   every updated record ID are in `audit/act_number_year_review.json`; the
   active index metadata was synchronized without changing vectors.
4. **Done 25 October 2026:** Populated `topics`, `scope_notes`, and
   `scope_status` for all 2,094 records; synchronized the active index metadata
   without rebuilding vectors. Topics use a reviewed Act-domain tag plus
   source-word matches. Scope clauses are quoted only when explicit applicability
   or exemption wording is present; otherwise notes say scope is not established
   or is unclear in that record. Evidence and per-record annotations are in
   `audit/scope_topics_review.json`.
5. **Done 25 October 2026:** Re-ran `scripts/split.py` into
   `audit/split_candidate/`, compared and merged the reviewed metadata, and
   synchronized `index/records.json` without rebuilding vectors. The fresh
   split and reviewed corpus both contain 2,094 records with matching IDs and
   per-source counts. All 2,094 section numbers and source page references
   match; every page reference is within its extracted source's page range.
   Required metadata gaps: 0. The refreshed split report is
   `sections/split_report.json`; detailed comparisons are in
   `audit/split_comparison.json`.
6. **Pass 25 October 2026:** Re-ran `scripts/validate_sections.py` and saved
   `sections/qc_report.json`. It reports 158 warnings, all with matching
   dispositions, 0 unreviewed warnings, 0 stale dispositions, and 0 required
   metadata gaps. `phase_2_closeout_pass` is true. The warnings remain visible
   for auditability; the two known deadline conflicts still require the Phase 3
   legal review listed below.

**Pass condition:** every short-record warning has a disposition, every
metadata gap is resolved or explicitly justified, and the validator has no
unreviewed errors.

### 6A.2 Close Phase 3 legal-review gaps

1. **Register assembled 25 October 2026; legal verification pending:**
   `audit/source_register.csv` and `.json` list all 44 corpus instruments,
   catalogue titles, official source links, principal Act identifiers, source
   hashes, source-date limitations, amendment-check status, and inventory
   reviewer/date. Thirteen principal identifiers were verified or corrected
   from official publications; the rest remain flagged for verification. The
   downloaded compiled copies do not consistently state an edition date. The
   targeted amendment findings and unresolved current-law checks are recorded
   in `audit/current_law_review.csv` and `.json`; a human legal reviewer remains
   outstanding.
2. **Targeted source review recorded 25 October 2026; not a legal closeout:**
   `audit/current_law_review.csv` and `.json` contain entries for all 44 source
   instruments, a review cutoff date, findings and links from the official
   Department of Labour, Parliament, and Government Printer sources, and
   explicit uncertainty notes. The review found 10 corpus instruments that
   need updating, 13 partial amendment histories, and 21 instruments whose
   later amendments/current status were not confirmed. For example, the
   Employment of Women, Young Persons and Children (Amendment) Act No. 21 of
   2026 was certified 8 September 2026; the National Minimum Wage and
   Budgetary Relief Allowance amendment Acts are both No. 11/2025 and No.
   10/2025 respectively; further Act and Gazette findings are in the report.
   Search non-results are not evidence that no amendment exists. A complete
   amendment/repeal and subsidiary-Gazette history, commencement check, and
   human legal review remain outstanding.
3. **Conflict register assembled 25 October 2026:**
   `audit/deadline_conflict_register.md` records both pairs of provisions with
   quoted deadline text, official source links, commencement date evidence,
   the four-to-six-month and two-to-three-month differences, and conservative
   handling proposals. Both shorter periods are recommended only as internal
   planning targets; the register does not resolve statutory interpretation.
   Sri Lankan labour-law reviewer sign-off remains outstanding.
4. **Reviewer packet prepared 25 October 2026; sign-off pending:** `audit/legal_review_packet.md` records the exact corpus/runtime hashes, review gaps, conflict decisions required, and approval fields. `audit/legal_reviewer_act_decisions.csv` provides a decision row for every instrument. The answer engine has no curated `plain_summary` corpus, and currently does not pass `scope_notes`/`scope_status` to generation; reviewer approval of implemented summaries/exclusions must wait until representative samples and scope handling are available. A qualified Sri Lankan labour-law reviewer must decide both conflicts, approve the launch subset and answer summaries/exclusions, and complete the decision sheet with credentials, date, rationale, and corpus/version acknowledged.
5. **AI operational dispositions recorded 25 October 2026:** `audit/ai_operational_law_dispositions.csv` records a safe answer policy for all 44 instruments. Ten known-stale sources are refused until their corpus text is updated. Thirteen partial-history and 21 unconfirmed sources require citations and a warning that AI answers may be wrong/incomplete or may not reflect a later Act, amendment, or Gazette notice; the model must not claim those sources are confirmed current. The two conflicts use four-month and two-month internal escalation targets respectively, with both statutory periods cited and no claim that either provision legally overrides the other. These are AI safeguards, not legal verification or qualified-review sign-off.

**Pass condition:** every Act planned for the pilot has a dated legal check,
the conflicts have a documented resolution, and a qualified reviewer has
approved the launch subset and summaries. Automated checks cannot replace this
human legal review.

### 6A.3 Finish Phase 4 using the saved vectors

1. **Backup created 25 October 2026 before future rebuilds:** `index/backups/2026-10-25_073700/` contains the current corrected index artifacts and `backup_manifest.json`. The manifest records SHA-256 hashes, sizes, and successful source-to-backup comparisons for all six files. The earlier 2,148-record index is still unavailable; this backup preserves the current 2,094-record index only.
2. **Verified 25 October 2026:** `index/embedding_checkpoint.npy` and the active vectors both contain 2,094 vectors of 3,072 dimensions for 2,094 records. `.env` `EMBED_MODEL`, the checkpoint model, and active index metadata all match `gemini-embedding-001`. No partial build remains to resume; retain this model setting if a future partial build is needed.
3. **Verified 25 October 2026:** source-section order, active `records.json` order, and checkpoint `record_ids` match exactly. Recomputed record fingerprint matches the checkpoint: `9960e99fd1438c8856ee48b664cc199e6a19d1dd5ce92bdbfa1b41e201398864`. Configured model, checkpoint, and metadata all agree on `gemini-embedding-001`; JSON, vector matrix, checkpoint, and FAISS each contain 2,094 records at 3,072 dimensions. FAISS reconstructed vectors match `vectors.npy` exactly; active vector norms differ from 1 by at most 2.4e-7. The checkpoint vectors differ from final normalized vectors by at most 4.5e-8, consistent with final normalization. All index consistency checks passed.
4. **Representative semantic searches and scope check passed on 25 October 2026:** queries covered retirement age, current minimum wage, gratuity, TEWA dismissal, and out-of-scope child adoption. Full top-8 rankings and relevance judgments are in `audit/semantic_search_review.md` and `.json`. Retirement, gratuity, and TEWA dismissal retrieved relevant provisions at rank 1. The wage query retrieved the correct Act but its section contains a superseded amount; the stale-source refusal path was verified. Adoption retrieved unrelated labour provisions at scores 0.6198-0.6311, so a fail-closed Gemini scope check was added before retrieval. Live smoke checks classified the four labour queries in scope, classified adoption out of scope, and verified `AnswerEngine.ask` refused it before retrieval. Classifier failure/malformed output also fails closed. This is a targeted AI smoke check, not a guarantee against every misclassification.

**Pass condition:** met on 25 October 2026 for index integrity and the representative retrieval/scope smoke set. Corrected records and vectors match 2,094-to-2,094, FAISS loads with matching count/dimension, record order and fingerprint agree, and saved search examples retrieve expected in-scope provisions. The stale wage source is refused; the out-of-scope adoption query is refused before retrieval. This sample does not establish error-free behavior for all queries.

### 6A.4 Close Phase 5 answer-engine checks

1. Run the answer engine against the corrected index with English, Sinhala,
   Tamil, and Singlish questions.
2. Verify every cited record ID is among the retrieved records and maps to the
   section text shown to the user. Check unsupported questions refuse safely.
3. Fix answer, retrieval, language, or citation failures, then repeat the
   affected checks and record the prompt/model/index versions.

**Pass condition:** the engine uses the corrected index, citations resolve to
real retrieved records, and unsupported questions receive the safe referral
response.

### 6A.5 Complete Phase 6 evaluation

1. Run all 42 questions against the corrected index, not the earlier 2,148
   record index. Preserve the result file and record the index fingerprint.
2. Review retrieval for all 37 in-scope questions; review refusal behavior for
   every out-of-scope question; compare generated answers with the reference
   answers; inspect citations for every result.
3. Fix failures in the corpus, retrieval, or prompt and rerun the affected
   cases. Keep a failure log so a passing aggregate cannot hide a serious
   legal or language error.
4. Have the legal reviewer approve answer samples in all supported languages
   and sign off on the final evaluation report.
5. **Phase 5 fixes applied; live retest blocked by Gemini quota (25 October 2026):** `scripts/ask.py` now requests structured JSON claims with source IDs, validates IDs against retrieved records, and renders citation markers only for valid IDs. It recognizes the tested Sinhala/Tamil/Singlish retirement phrases locally, fails closed on uncertain scope, and only blocks a stale source when it is among the top three and within 0.05 of the top retrieval score. Local path checks and Python compilation pass. The post-fix live attempt reached English generation but Gemini returned its free-tier daily `generate_content` quota error. A probe using stable `gemini-3.7-flash` reported the same daily-quota exhaustion, so the configured model was left unchanged. The remaining languages were not rerun after the fixes. Previous live outcomes remain in `audit/multilingual_answer_smoke.json`; post-fix details and index/model/code versions are in `audit/phase5_multilingual_answer_run.json`. **Pass condition not met:** rerun English, Sinhala, Tamil, Singlish, and unsupported queries after quota reset; verify generated answers, cited IDs, source text mappings, and safe refusals.

6. **42-question retrieval pass run 25 October 2026 after correcting test data:** `eval/results/phase6_vector_retrieval_corrected.json` records all top-8 vector results, expected references, model/index fingerprints, and question hash. Expected section retrieval is 37/37 for in-scope questions. q05 had incorrect expected sections; q41/q42 had corrupted Sinhala/Tamil text; reference apostrophes were also repaired. The original test set is preserved at `eval/questions.pre_phase6_repair.json`; corrections and remaining failures are in `eval/results/phase6_failure_log.md`.
7. **Generated-answer evaluation and legal approval remain open:** Gemini daily generation quota is exhausted, so reference-answer comparison, 5 refusal checks, and citation/source-text validation for generated answers were not run. No qualified reviewer sign-off is present. Rerun `eval/run.py --api` after quota reset, inspect every answer and citation, fix failures, and obtain the required human review.

**Pass condition: NOT MET.** Retrieval now finds the expected section for all 37 in-scope questions after test-data corrections, but generated answers, citations, and all five should-refuse decisions remain unevaluated because the Gemini generation quota is exhausted. Qualified legal reviewer approval is also outstanding. Close only after the API evaluation and human sign-off are recorded.

### Phase 6A completion gate

Before Phase 7 is treated as the next project phase, save the updated Phase 1–6
reports, the corrected-index metadata, the full Phase 6 results, the resolved
legal-conflict register, and reviewer sign-off. Until then, Phases 1–6 remain
open and public-pilot work is blocked.

---

## Phase 7: Backend API (2 days)

A small FastAPI app that exposes `POST /ask` with `{question, language}` and streams the answer. It should:
- load the FAISS index and records once at startup
- call the same code as `ask.py`
- apply per-IP rate limits to protect the Gemini quota; keep CAPTCHA out of the first pilot unless abuse data shows it is needed
- cache answers to repeated questions
- log nothing that identifies the user; store no question text unless the user opts in
- send the API key only from environment variables

Done when: `curl` to `/ask` returns a streamed answer with citations.

---

## Phase 8: Website (1 week)

Mobile-first chat page (Next.js or plain React with Tailwind):
1. Chat box, language switch (English, Sinhala, Tamil), and a clear banner: "Legal information, not legal advice."
2. Starter questions: "My employer retired me at 55. What can I do?", "How is overtime pay calculated?", "How do I complain about unpaid wages?"
3. Answer card layout: simple answer, legal basis (sections shown as chips), next steps.
4. A "Sources" panel showing the exact section text the answer relied on.
5. A "Was this correct?" thumbs up/down button, with no personal data.
6. A **Contacts page**: Labour Department district offices, Legal Aid Commission, labour tribunals (add from official sources; assign an owner to keep it current).
7. Test Sinhala and Tamil fonts on an older Android phone and on slow connections.

Defer voice input and document upload until the text chat is solid.

---

## Phase 9: Deploy (2 days)

- Frontend: Vercel or another static-site host.
- Backend: a free container host (Render, Fly.io or Hugging Face Spaces). Free hosts may sleep, so add an uptime monitor and a "waking up" message.
- Store the API key as a secret in the host, not in the code.
- Keep host-level or application-level rate limits enabled.
- Add monitoring (UptimeRobot, Sentry) and a daily check on Gemini quota use.
- Launch as a **closed pilot** to law students and legal-aid volunteers before opening to the public.

---

## Phase 10: Maintenance and growth

- **Quarterly update:** a named owner checks for new Acts, amendments and Gazette orders (minimum wage, allowances, compensation formulas), updates the section files, rebuilds the index and re-runs the 40 test questions.
- Add a **Gazette collection** (dated, with `valid_from` and `valid_to`) so the assistant can quote current rates.
- Add **case-law summaries** chosen by a lawyer.
- Add **Sinhala and Tamil official texts** so answers can cite them (the Sinhala text prevails in case of conflict).
- Review the thumbs-down answers monthly and add them to the test set.
- Move to a paid or no-training API tier before accepting real citizen documents, and align with the Personal Data Protection Act No. 9 of 2022.

---

## Time estimate (one person, part-time)

| Phase | Time |
|---|---|
| 0 Setup | 0.5 day |
| 1 Extract | 1 day |
| 2 Clean and split | 2 to 3 days |
| 3 Quality and legal checks | 3 to 5 days (parallel) |
| 4 Index | 1 day |
| 5 Answer engine | 2 to 3 days |
| 6 Evaluation | ongoing, 2 days to start |
| 7 Backend | 2 days |
| 8 Website | 5 to 7 days |
| 9 Deploy and pilot | 2 days plus pilot |

About 4 to 6 weeks to a pilot, depending on how fast the legal review goes.

---

## Top risks

| Risk | What to do |
|---|---|
| Wrong or invented legal answers | Citation check, "not sure" fallback, lawyer review, test set |
| Outdated law or amounts | `status: verify`, dated Gazette collection, quarterly updates |
| Conflicting time limits between Acts | `conflicts_with` field and `audit/deadline_conflict_register.md`; legal interaction unresolved pending qualified reviewer decision. Use only the register's conservative internal target meanwhile; do not claim which provision controls. |
| Splitting errors in compiled text | Automatic numbering checks, manual spot checks per Act |
| Free quota runs out | Cache, rate limits, CAPTCHA, FAQ answers prepared in advance |
| Privacy | No accounts, no question logging, no document uploads on the free tier |
| Users not covered by the law | Always state exclusions and scope in the answer |

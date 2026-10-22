# Nithi Sahaya: Build Plan from 44 Labour-Law PDFs to a Working AI Website

Goal: turn 44 clear English PDFs (Department of Labour compiled labour code) into a legal-information assistant with a website, using free tools.

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

## Phase 7: Backend API (2 days)

A small FastAPI app that exposes `POST /ask` with `{question, language}` and streams the answer. It should:
- load the FAISS index and records once at startup
- call the same code as `ask.py`
- add rate limiting per IP and a CAPTCHA (for example Cloudflare Turnstile) to protect the free Gemini quota
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

- Frontend: Cloudflare Pages (or Vercel).
- Backend: a free container host (Render, Fly.io or Hugging Face Spaces). Free hosts may sleep, so add an uptime monitor and a "waking up" message.
- Store the API key as a secret in the host, not in the code.
- Add Cloudflare rate limiting.
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
| Conflicting time limits between Acts | `conflicts_with` field, later Act controls, lawyer sign-off |
| Splitting errors in compiled text | Automatic numbering checks, manual spot checks per Act |
| Free quota runs out | Cache, rate limits, CAPTCHA, FAQ answers prepared in advance |
| Privacy | No accounts, no question logging, no document uploads on the free tier |
| Users not covered by the law | Always state exclusions and scope in the answer |
# Sri Lankan labour-law reviewer packet

**Status: OPEN - no qualified reviewer decision or approval is recorded.** This packet is prepared for a Sri Lankan labour-law reviewer; it does not itself provide legal approval.

## Review requested

1. Decide the two statutory deadline conflicts in `deadline_conflict_register.md`, with legal reasoning, applicable provisions, and any limits/uncertainty.
2. Review and approve or reject the proposed pilot launch subset. There is currently no reviewer-approved subset.
3. Review plain-language answer summaries and exclusions used by the product, approve or require changes, and identify covered languages. The answer engine currently generates answers dynamically; there are **0 stored/curated `plain_summary` fields**, so there is no fixed summary set to approve. Reviewer must assess representative generated answer samples for each launch topic/language after scope/exclusion handling is available.
4. Complete `legal_reviewer_act_decisions.csv` for every instrument in the corpus proposed for pilot; record reviewer identity/qualification, decision, source citations, and date. Existing 2026-10-25 entries are AI-assisted targeted source checks, not lawyer checks.

## Corpus and runtime version under review

- Corpus: `2,094` section records across 44 instruments (source register).
- Embedding checkpoint fingerprint: `9960e99fd1438c8856ee48b664cc199e6a19d1dd5ce92bdbfa1b41e201398864`; embedding model `gemini-embedding-001`.
- Review cutoff recorded: 2026-10-25 (Asia/Colombo).
- Evaluation set: 42 questions; test-set hash below.
- This packet is tied to exact artifacts by SHA-256; any content/index/prompt change requires a new version and reviewer confirmation.

| Artifact | SHA-256 |
|---|---|
| `audit/ai_operational_law_dispositions.csv` | `1ed7edc450416cbacfa1d4344a15da4642f244c4a41150d2dda82bc5ec36de3e` |
| `index/records.json` | `73302f89fd473c307415931c6836182641230fa01ebf4af79e211bbaff0f0367` |
| `index/metadata.json` | `ff6177c62c577b834c70b2c4abff41563b523ffaf80466a02c4dc184037c9929` |
| `index/sections.faiss` | `e9f12dfcb1e82741cde522ffe118a4b51bcb9b97c6f8097c00b9f1c4375b6ca4` |
| `index/vectors.npy` | `294a180a002073d0299913e1d7dcaa0f7b06a6faf21004c10a5c4ae51d5439bf` |
| `index/embedding_checkpoint.json` | `5e36283fe12badb34c4da00e0484f13fbe7b38a079b35f3eaa1738e455504875` |
| `scripts/ask.py` | `68587710d1e7910f59a47dbb7f081ebe669ceb54da4721b1bd1f2426081b4106` |
| `eval/questions.json` | `51bcc29a7f82fdf10be1f1c140827f1d539906fe43f4808e536f9cd64f399946` |
| `audit/current_law_review.json` | `f29a555b0034ad380f705debed101a591602e9ebf154c730b3e7679f7102d381` |
| `audit/deadline_conflict_register.md` | `846c438d178ee4d2be359a7ebe2ec49d6df32127bf7afd3dd8cb9d0a98cbe19d` |

## Act review status at cutoff

- Dated targeted checks recorded for all 44 instruments on 2026-10-25.
- Status counts: corpus_update_required: 10, not_confirmed: 21, partial: 13.
- Thus, dated research exists for each instrument, but 10 corpus updates remain required, 13 amendment histories are partial, and 21 current-status checks are not confirmed. No row is a qualified reviewer sign-off.
- Complete one reviewer decision per row in `legal_reviewer_act_decisions.csv`. In particular, an Act may only enter the launch subset after the reviewer records its current text, commencement, amendments/repeals, subsidiary instruments, and any remaining uncertainty.

## Answer handling and scope limitations

- `scripts/ask.py` uses a generative prompt, not a reviewed library of stored plain-language summaries.
- The answer engine now passes `scope_notes` and `scope_status` into the generation prompt. These are source annotations, not legal approvals; a qualified reviewer still needs to approve exclusion handling and representative outputs.
- Operational status decisions for every instrument are recorded in `ai_operational_law_dispositions.csv`: the 10 known-stale corpus sources are excluded/refused until updated; 13 partial-history sources and 21 unconfirmed sources may only support cited answers with an explicit AI/currentness warning and no claim of present legal validity. Their legal histories remain unresolved.
- Reviewer should record the actual reviewed prompts/samples (including Sinhala, Tamil, and Singlish where intended), exact application version, and decision for each launch topic. Record exclusions and no-answer/referral cases explicitly.

## Conflict decisions

Use `deadline_conflict_register.md` for exact quotations and official links. AI operational decision: use four months for the tribunal order and two months for TEWA Commissioner approval as conservative escalation targets; state both statutory periods and citations; do not claim that either provision overrides the other. Statutory construction and consequences in the intervals remain legally unresolved pending qualified review.

| Conflict | Reviewer resolution | Reasoning / sources / interval consequence | Reviewer / qualification | Date |
|---|---|---|---|---|
| Industrial Disputes Act s.31C (six months) vs Act No. 13 of 2003 s.5 (four months) | **AI operational target: four months; legal construction unresolved** | Cite both periods; use four months as an escalation target, not a ruling that one provision controls. | Pending | 2026-10-25 policy date |
| TEWA s.2(2)(c) (three months) vs Act No. 13 of 2003 s.11 (two months) | **AI operational target: two months from application receipt; legal construction unresolved** | Cite both periods; use two months as an escalation target, not a ruling that one provision controls. | Pending | 2026-10-25 policy date |

## Launch subset and summary approval

| Field | Reviewer completion |
|---|---|
| Approved launch Acts/instruments (list exact source files and IDs) | Pending |
| Excluded Acts/instruments and rationale | Pending |
| Summary/answer sample artifact, language, and hash | Pending; no curated summary corpus currently exists |
| Approved answer exclusions and referral/refusal rules | Pending |
| Known conditions, limitations, and expiry/recheck date | Pending |
| Reviewer full name, Sri Lankan labour-law qualification/role, organization | Pending |
| Sign-off date and signature/reference | Pending |
| Corpus fingerprint and artifact hashes acknowledged | Pending |

## Pass-condition assessment (2026-10-25)

- **Every pilot Act has a dated legal check:** dated targeted checks are recorded across all 44 instruments, but their status is incomplete and they are AI-assisted research, not reviewer-approved legal checks. **Not met.**
- **Conflicts have documented operational handling:** shorter targets (four months and two months) are recorded with a no-hierarchy rule and mandatory dual citation. The legal questions and interval consequences remain unresolved pending human review. Operational handling recorded; legal-resolution criterion not met.
- **Qualified reviewer approved launch subset and summaries:** no qualified reviewer identity, approval, or signature is present; no fixed summary corpus exists. **Not met.**

**Overall: FAIL / NOT READY for a legally approved pilot.** AI operational safeguards are recorded, including a warning that AI answers may be wrong/incomplete or omit a later Act, amendment, or Gazette notice. Ten stale sources are excluded from answers. This does not resolve the 13 partial or 21 unconfirmed amendment histories, and it does not substitute for the required qualified reviewer approval. Complete the decision sheet, update affected corpus text, and re-evaluate before launch.

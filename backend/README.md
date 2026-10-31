# Backend API

Run from the project root after installing `requirements.txt` and configuring
`.env`:

```powershell
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --no-access-log
```

The API loads the retrieval engine on the first `/ask` request and reuses it.
`POST /ask` accepts JSON with `question` and optional `language`. It responds
as Server-Sent Events: first a `metadata` event
containing local `sources`, `web_sources`, and refusal status, then `message` events containing text,
and finally a `[DONE]` event. Generation currently completes before text chunks
are sent; the response is chunked for clients, while Gemini itself is not
streamed.

## Retrieval and grounding

The answer pipeline combines dense FAISS retrieval over the local legal corpus
with BM25-style lexical matching, then reranks the combined candidates before
building the model context. ETF and EPF acronyms are expanded to their distinct
fund names during retrieval. Gemini Google Search grounding is enabled by
`GEMINI_GOOGLE_SEARCH=true` (default); the prompt prioritizes official Sri Lankan
sources and asks the model to compare current web material with indexed text.
Each answer claim must cite a retrieved record ID, a returned Google URL, or
both. Response metadata carries local section text and web links separately so
the frontend can render each citation type. Set the option to `false` to disable
Google Search grounding.

Set `CORS_ORIGINS` to a comma-separated list of trusted frontend origins. Rate
limits and cached answers are held in process memory, so production should run
one worker or replace these with shared storage before scaling horizontally.
The service does not log question text, client addresses, or raw questions in its cache; it
uses a hash as the cache key. Run Uvicorn with `--no-access-log` to keep client
addresses out of access logs. Internal failure logging keeps user questions and
API keys out of logs; upstream error summaries are redacted and truncated.

Example request:

```powershell
curl.exe -N -X POST http://127.0.0.1:8000/ask `
  -H "Content-Type: application/json" `
  -d '{"question":"Can my employer retire me at 55?","language":"English"}'
```

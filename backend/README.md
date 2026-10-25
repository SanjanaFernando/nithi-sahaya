# Backend API

Run from the project root after installing `requirements.txt` and configuring
`.env`:

```powershell
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --no-access-log
```

The API loads the retrieval engine on the first `/ask` request and reuses it.
`POST /ask` accepts JSON with `question` and optional `language`. It responds
as Server-Sent Events: first a `metadata` event
containing `sources` and refusal status, then `message` events containing text,
and finally a `[DONE]` event. Generation currently completes before text chunks
are sent; the response is chunked for clients, while Gemini itself is not
streamed.

Set `CORS_ORIGINS` to a comma-separated list of trusted frontend origins. Rate
limits and cached answers are held in process memory, so production should run
one worker or replace these with shared storage before scaling horizontally.
The service does not log question text, client addresses, or raw questions in its cache; it
uses a hash as the cache key. Run Uvicorn with `--no-access-log` to keep client
addresses out of access logs. Internal failure logging records exception types only.

Example request:

```powershell
curl.exe -N -X POST http://127.0.0.1:8000/ask `
  -H "Content-Type: application/json" `
  -d '{"question":"Can my employer retire me at 55?","language":"English"}'
```

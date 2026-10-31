# Nithi Sahaya frontend

This is a static, dependency-free frontend. It keeps chat state in memory only;
questions and feedback are not written to browser storage. API requests go to
`http://127.0.0.1:8000` by default and use the existing backend SSE endpoint.

## Run locally

Start the API in one PowerShell terminal from the repository root:

```powershell
.venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --no-access-log
```

Start the static site in another terminal:

```powershell
python -m http.server 3000 --bind 127.0.0.1 --directory frontend
```

Open `http://localhost:3000`, which matches the default CORS origin in `.env.example`. If you use a different hostname or port, add that exact origin to `CORS_ORIGINS`. Never put the Gemini API key in frontend files. For hosting, set the `data-api-base` attribute on the root `<html>` element to the HTTPS API URL and configure the backend's CORS allowlist to the hosted site origin.

The contact page links to the Department of Labour's office directories, the
Legal Aid Commission contact page, and the Ministry of Justice Labour Tribunal
directory. Those links were checked on 25 October 2026. The project owner is
responsible for checking them monthly.

## Pilot limitations

- The answer is generated before the backend sends its SSE chunks, so this UI
  receives a streamed response format but not token-by-token Gemini generation.
- Common labour questions use a local scope check and then need a retrieval
  embedding call plus answer generation. Gemini thinking defaults to `low` for
  everyday questions and HTTP timeout to 120 seconds per request, with no SDK
  retry by default; users can retry after a transient error. Remote service
  latency can still vary. Repeated identical questions may use the server's
  answer cache.
- The feedback buttons only acknowledge the click in the current page. They do
  not submit or store a vote.
- Check Sinhala/Tamil rendering and performance on a physical older Android
  device and a slow mobile connection before public release.

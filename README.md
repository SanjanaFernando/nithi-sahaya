# Nithi Sahaya

Nithi Sahaya is a Sri Lankan labour law information pilot. It provides answers in English, Sinhala, and Tamil, with citations to retrieved legal sections. It is for legal information, not legal advice.

## Run locally (Windows / PowerShell)

### 1. Requirements

- Python 3.10 or newer
- A Gemini API key (needed when you submit a question)

Run commands below from the repository root (`C:\Top Projects\Srilaw`).

### 2. Create the Python environment and install dependencies

```powershell
py -3 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

If PowerShell blocks environment activation, you can skip activation and use `.venv\Scripts\python.exe` in place of `python` in the commands below.

### 3. Configure the API key

Copy the example environment file, then open `.env` and replace `your_key_here` with your Gemini API key:

```powershell
Copy-Item .env.example .env
notepad .env
```

Keep the key in `.env`; never put it in frontend files or commit it. `.env` is ignored by Git. The other settings in `.env.example` work for the default local setup.

### 4. Start the backend

Open a PowerShell terminal at the repository root and run:

```powershell
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --no-access-log
```

The API is at `http://127.0.0.1:8000`. Check it at `http://127.0.0.1:8000/health`; it should return `{"status":"ok"}`. The retrieval index in `index/` is loaded on the first question, so that request can take longer.

### 5. Start the frontend

Open a second PowerShell terminal at the repository root. Serve the `frontend` folder directly:

```powershell
python -m http.server 3000 --bind 127.0.0.1 --directory frontend
```

Visit [http://localhost:3000](http://localhost:3000). The default API address is `http://127.0.0.1:8000`, and `.env.example` allows this frontend origin through CORS.

Stop either server with `Ctrl+C` in its terminal.

## Troubleshooting

- **Missing API key:** make sure `.env` exists at the repository root and contains a valid `GEMINI_API_KEY`.
- **Frontend cannot reach the API:** keep both servers running and check that `CORS_ORIGINS` in `.env` includes the exact frontend origin, such as `http://localhost:3000`. Restart the backend after changing `.env`.
- **Missing index files:** the API expects `index/sections.faiss` and `index/records.json`. If these files are absent, build the index with `python scripts/build_index.py`; this requires a working Gemini API key and may incur API usage.
- **Python package installation issues:** use a supported 64-bit Python version and install from an activated virtual environment.

## Project layout

- `backend/` - FastAPI API (`POST /ask`, `GET /health`)
- `frontend/` - static chat site and contacts page
- `sections/` - structured legal section records
- `index/` - retrieval index and records used by the answer engine
- `scripts/` - extraction, indexing, and evaluation utilities
- `buildplan.md` - project phases, status, and remaining work

More detail: [backend/README.md](backend/README.md) and [frontend/README.md](frontend/README.md).

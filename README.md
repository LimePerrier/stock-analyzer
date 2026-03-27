# Stock Analyzer Web Starter

This package keeps your existing Python engine and desktop entry point, and adds:

- a thin FastAPI layer in `web_backend/`
- a Next.js frontend in `frontend/`

## What still works

You can still run the desktop app the same way:

```bash
python stock_analyzerv6.py
```

## Web backend

From the project root:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r web_backend/requirements.txt
set ANTHROPIC_API_KEY=sk-ant-...
python -m uvicorn web_backend.app.main:app --reload --port 8000
```

Then visit:

- `http://127.0.0.1:8000/api/health`
- `http://127.0.0.1:8000/docs` (FastAPI docs)

## Frontend

In a second terminal:

```bash
cd frontend
copy .env.example .env.local
npm install
npm run dev
```

Then visit:

- `http://localhost:3000`

## Backend endpoints

- `GET /api/health`
- `GET /api/dashboard`
- `GET /api/jobs`
- `POST /api/jobs/url`
- `POST /api/jobs/text`
- `POST /api/jobs/run-next`
- `GET /api/analyses`
- `GET /api/analyses/{id}`
- `GET /api/market-regime`
- `PUT /api/market-regime`
- `GET /api/twitter-prompt`
- `PUT /api/twitter-prompt`

## Notes

- `.txt` uploads are saved under `uploads/`
- generated markdown reports are saved under `reports/`
- API metadata is stored in `web_backend/stockscope_web.db`

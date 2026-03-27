from pathlib import Path
import sys

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from . import store
from .schemas import PromptUpdate, TextJobCreate, UrlJobCreate
from .services import WebEngine

store.init_db()
engine = WebEngine()

app = FastAPI(title="Stock Analyzer Web API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    return {"ok": True}


@app.get("/api/dashboard")
def dashboard():
    return engine.dashboard()


@app.get("/api/jobs")
def jobs():
    return engine.dashboard()["jobs"]


@app.post("/api/jobs/url")
def create_url_job(body: UrlJobCreate):
    try:
        return engine.queue_url_job(
            ticker=body.ticker,
            title=body.title,
            analysis_type=body.analysis_type,
            urls=body.urls,
            model=body.model,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/jobs/text")
async def create_text_job(
    ticker: str,
    title: str = "",
    model: str = "claude-sonnet-4-5",
    file: UploadFile = File(...),
):
    try:
        return await engine.queue_text_job(ticker=ticker, title=title or None, upload=file, model=model)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/jobs/run-next")
def run_next_job():
    result = engine.run_next()
    if not result:
        return {"message": "No queued jobs."}
    return result


@app.get("/api/analyses")
def analyses():
    return store.fetch_all_analyses()


@app.get("/api/analyses/{analysis_id}")
def get_analysis(analysis_id: int):
    analysis = store.fetch_analysis(analysis_id)
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found.")
    return analysis


@app.get("/api/market-regime")
def get_market_regime():
    return {"content": engine.get_market_regime()}


@app.put("/api/market-regime")
def put_market_regime(body: PromptUpdate):
    try:
        return {"content": engine.save_market_regime(body.content)}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/twitter-prompt")
def get_twitter_prompt():
    return {"content": engine.get_twitter_prompt()}


@app.put("/api/twitter-prompt")
def put_twitter_prompt(body: PromptUpdate):
    try:
        return {"content": engine.save_twitter_prompt(body.content)}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

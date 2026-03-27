from __future__ import annotations

import shutil
from pathlib import Path

from fastapi import UploadFile

from stock_analyzer.queue import AnalysisJob, QueueService
from stock_analyzer.runner import AnalysisRunner
from stock_analyzer.regime import load_market_regime, save_market_regime
from stock_analyzer.twitter_prompt import load_twitter_prompt, save_twitter_prompt
from . import store


class WebEngine:
    def __init__(self):
        self.queue = QueueService(max_jobs=100)
        self.runner = AnalysisRunner(output_dir=store.REPORT_DIR)
        self._hydrate_queue()

    def _hydrate_queue(self) -> None:
        for row in store.fetch_pending_rows():
            self.queue.add_job(self._row_to_job(row))

    def _row_to_job(self, row: dict) -> AnalysisJob:
        return AnalysisJob(
            ticker=row["ticker"],
            urls=row["urls"],
            analysis_type=row["analysis_type"],
            model=row["model"],
            txt_path=row.get("txt_path", ""),
            id=str(row["id"]),
            status=row["status"],
        )

    def queue_url_job(self, *, ticker: str, title: str | None, analysis_type: str, urls: list[str], model: str) -> dict:
        clean_ticker = ticker.strip().upper()
        clean_urls = [u.strip() for u in urls if u.strip()]
        if not clean_urls:
            raise ValueError("Add at least one URL.")
        clean_title = (title or clean_ticker).strip()
        analysis_id = store.insert_analysis(
            ticker=clean_ticker,
            title=clean_title,
            analysis_type=analysis_type,
            model=model.strip() or "claude-sonnet-4-5",
            urls=clean_urls,
        )
        job = AnalysisJob(
            ticker=clean_ticker,
            urls=clean_urls,
            analysis_type=analysis_type,
            model=model.strip() or "claude-sonnet-4-5",
            id=str(analysis_id),
        )
        self.queue.add_job(job)
        return store.fetch_analysis(analysis_id)

    async def queue_text_job(self, *, ticker: str, title: str | None, upload: UploadFile, model: str) -> dict:
        clean_ticker = ticker.strip().upper()
        filename = upload.filename or "twitter_feed.txt"
        if not filename.lower().endswith(".txt"):
            raise ValueError("Upload a .txt file.")
        target = store.UPLOAD_DIR / f"{clean_ticker}_{filename}"
        with target.open("wb") as fh:
            shutil.copyfileobj(upload.file, fh)
        clean_title = (title or Path(filename).stem or clean_ticker).strip()
        analysis_id = store.insert_analysis(
            ticker=clean_ticker,
            title=clean_title,
            analysis_type="twitter_feed",
            model=model.strip() or "claude-sonnet-4-5",
            urls=[],
            txt_path=str(target),
        )
        job = AnalysisJob(
            ticker=clean_ticker,
            urls=[],
            analysis_type="twitter_feed",
            model=model.strip() or "claude-sonnet-4-5",
            txt_path=str(target),
            id=str(analysis_id),
        )
        self.queue.add_job(job)
        return store.fetch_analysis(analysis_id)

    def run_next(self) -> dict | None:
        job = self.queue.get_next_job()
        if not job:
            return None
        analysis_id = int(job.id)
        store.update_analysis_status(analysis_id, "running")
        try:
            result = self.runner.run_job(job)
            store.complete_analysis(
                analysis_id,
                article_text_path=str(result.scraped_path),
                report_path=str(result.report_path),
                report_markdown=result.report,
                token_input=result.total_in,
                token_output=result.total_out,
                estimated_cost=result.est_cost,
            )
            self.queue.mark_done(job.id)
        except Exception as exc:
            message = str(exc)
            store.fail_analysis(analysis_id, message)
            self.queue.mark_failed(job.id)
        return store.fetch_analysis(analysis_id)

    def dashboard(self) -> dict:
        return {
            "tickers": store.fetch_tickers(),
            "analyses": store.fetch_all_analyses(),
            "jobs": [a for a in store.fetch_all_analyses() if a["status"] in {"queued", "running"}],
            "market_regime": load_market_regime(),
            "twitter_prompt": load_twitter_prompt(),
        }

    def get_market_regime(self) -> str:
        return load_market_regime()

    def save_market_regime(self, content: str) -> str:
        save_market_regime(content)
        return load_market_regime()

    def get_twitter_prompt(self) -> str:
        return load_twitter_prompt()

    def save_twitter_prompt(self, content: str) -> str:
        save_twitter_prompt(content)
        return load_twitter_prompt()

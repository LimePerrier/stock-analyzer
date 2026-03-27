from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

from .analysis import run_analysis
from .dependencies import anthropic
from .queue import AnalysisJob
from .regime import load_market_regime
from .scraper import scrape_urls_to_text

StopCheck = Optional[Callable[[], bool]]
LogFn = Optional[Callable[[str], None]]


@dataclass
class AnalysisRunResult:
    job: AnalysisJob
    article_text: str
    report: str
    total_in: int
    total_out: int
    est_cost: float
    scraped_path: Path
    report_path: Path
    market_regime: str


class AnalysisRunner:
    """Reusable execution pipeline for desktop UI and future API routes."""

    def __init__(self, output_dir: str | Path | None = None, client_factory=None):
        self.output_dir = Path(output_dir) if output_dir else Path.cwd()
        self.client_factory = client_factory or self._default_client_factory

    def _default_client_factory(self):
        if anthropic is None:
            raise RuntimeError("anthropic not installed.")
        return anthropic.Anthropic()

    def _check_stop(self, stop_check: StopCheck) -> None:
        if stop_check and stop_check():
            raise InterruptedError("Run stopped by user.")

    def _load_job_text(self, job: AnalysisJob, log_fn: LogFn = None) -> tuple[str, Path]:
        if job.analysis_type == "twitter_feed":
            if not job.txt_path:
                raise ValueError("Twitter feed analysis requires a .txt file.")
            txt_path = Path(job.txt_path)
            if not txt_path.exists():
                raise FileNotFoundError(f"Input text file not found: {txt_path}")
            if txt_path.suffix.lower() != ".txt":
                raise ValueError("Twitter feed analysis requires a .txt file.")
            if log_fn:
                log_fn(f"Loading Twitter feed from {txt_path.name}...")
            text = txt_path.read_text(encoding="utf-8").strip()
            if not text:
                raise ValueError(f"Input text file is empty: {txt_path.name}")
            return text, txt_path

        if log_fn:
            log_fn(f"Scraping {len(job.urls)} URL(s)...")
        article_text = scrape_urls_to_text(job.urls, log_fn=log_fn)
        if not article_text.strip():
            raise ValueError(f"No content scraped for {job.ticker}.")
        scraped_path = self.output_dir / f"{job.ticker}_articles.txt"
        scraped_path.write_text(article_text, encoding="utf-8")
        return article_text, scraped_path

    def run_job(self, job: AnalysisJob, log_fn: LogFn = None, stop_check: StopCheck = None) -> AnalysisRunResult:
        self._check_stop(stop_check)

        article_text, scraped_path = self._load_job_text(job, log_fn=log_fn)
        self._check_stop(stop_check)

        market_regime = ""
        if job.analysis_type != "twitter_feed":
            market_regime = load_market_regime()
            if log_fn:
                type_label = "Earnings" if job.analysis_type == "earnings" else "Catalyst"
                log_fn(f"\n{type_label} analysis...")
        elif log_fn:
            log_fn("\nTwitter feed analysis...")

        client = self.client_factory()
        report, total_in, total_out, est_cost = run_analysis(
            client,
            job.model,
            job.analysis_type,
            article_text,
            job.ticker,
            log_fn=log_fn,
            market_regime=market_regime or None,
        )
        self._check_stop(stop_check)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        if job.analysis_type == "earnings":
            prefix = "earnings"
        elif job.analysis_type == "catalyst":
            prefix = "catalyst"
        else:
            prefix = "twitter_feed"
        safe_title = "".join(ch if ch.isalnum() or ch in ('-', '_') else '_' for ch in job.ticker).strip('_') or 'analysis'
        report_path = self.output_dir / f"{prefix}_{safe_title}_{timestamp}.md"
        report_path.write_text(report, encoding="utf-8")

        return AnalysisRunResult(
            job=job,
            article_text=article_text,
            report=report,
            total_in=total_in,
            total_out=total_out,
            est_cost=est_cost,
            scraped_path=scraped_path,
            report_path=report_path,
            market_regime=market_regime,
        )

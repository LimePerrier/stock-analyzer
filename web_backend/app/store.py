import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

ROOT_DIR = Path(__file__).resolve().parents[2]
DB_PATH = ROOT_DIR / "web_backend" / "stockscope_web.db"
UPLOAD_DIR = ROOT_DIR / "uploads"
REPORT_DIR = ROOT_DIR / "reports"

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
REPORT_DIR.mkdir(parents=True, exist_ok=True)


def utcnow() -> str:
    return datetime.utcnow().isoformat(timespec="seconds") + "Z"


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with get_conn() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS analyses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT NOT NULL,
                title TEXT NOT NULL,
                analysis_type TEXT NOT NULL,
                model TEXT NOT NULL,
                urls_json TEXT NOT NULL DEFAULT '[]',
                txt_path TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'queued',
                created_at TEXT NOT NULL,
                started_at TEXT,
                completed_at TEXT,
                article_text_path TEXT NOT NULL DEFAULT '',
                report_path TEXT NOT NULL DEFAULT '',
                report_markdown TEXT NOT NULL DEFAULT '',
                token_input INTEGER NOT NULL DEFAULT 0,
                token_output INTEGER NOT NULL DEFAULT 0,
                estimated_cost REAL NOT NULL DEFAULT 0,
                error_message TEXT NOT NULL DEFAULT ''
            );
            CREATE TABLE IF NOT EXISTS app_state (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            """
        )


def insert_analysis(*, ticker: str, title: str, analysis_type: str, model: str, urls: list[str], txt_path: str = "") -> int:
    now = utcnow()
    with get_conn() as conn:
        cur = conn.execute(
            """
            INSERT INTO analyses (
                ticker, title, analysis_type, model, urls_json, txt_path, status, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, 'queued', ?)
            """,
            (ticker, title, analysis_type, model, json.dumps(urls), txt_path, now),
        )
        return int(cur.lastrowid)


def update_analysis_status(analysis_id: int, status: str, *, error_message: str = "") -> None:
    started_at = utcnow() if status == "running" else None
    completed_at = utcnow() if status in {"completed", "failed"} else None
    with get_conn() as conn:
        if status == "running":
            conn.execute(
                "UPDATE analyses SET status = ?, started_at = ?, error_message = ? WHERE id = ?",
                (status, started_at, error_message, analysis_id),
            )
        elif status in {"completed", "failed"}:
            conn.execute(
                "UPDATE analyses SET status = ?, completed_at = ?, error_message = ? WHERE id = ?",
                (status, completed_at, error_message, analysis_id),
            )
        else:
            conn.execute(
                "UPDATE analyses SET status = ?, error_message = ? WHERE id = ?",
                (status, error_message, analysis_id),
            )


def complete_analysis(
    analysis_id: int,
    *,
    article_text_path: str,
    report_path: str,
    report_markdown: str,
    token_input: int,
    token_output: int,
    estimated_cost: float,
) -> None:
    with get_conn() as conn:
        conn.execute(
            """
            UPDATE analyses
            SET status = 'completed',
                completed_at = ?,
                article_text_path = ?,
                report_path = ?,
                report_markdown = ?,
                token_input = ?,
                token_output = ?,
                estimated_cost = ?,
                error_message = ''
            WHERE id = ?
            """,
            (utcnow(), article_text_path, report_path, report_markdown, token_input, token_output, estimated_cost, analysis_id),
        )


def fail_analysis(analysis_id: int, error_message: str) -> None:
    with get_conn() as conn:
        conn.execute(
            "UPDATE analyses SET status = 'failed', completed_at = ?, error_message = ? WHERE id = ?",
            (utcnow(), error_message, analysis_id),
        )


def fetch_analysis(analysis_id: int) -> dict[str, Any] | None:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM analyses WHERE id = ?", (analysis_id,)).fetchone()
    return row_to_analysis(row) if row else None


def fetch_all_analyses() -> list[dict[str, Any]]:
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM analyses ORDER BY created_at DESC, id DESC").fetchall()
    return [row_to_analysis(r) for r in rows]


def fetch_pending_rows() -> list[dict[str, Any]]:
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM analyses WHERE status = 'queued' ORDER BY id ASC").fetchall()
    return [row_to_analysis(r) for r in rows]


def row_to_analysis(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    data = dict(row)
    data["urls"] = json.loads(data.pop("urls_json") or "[]")
    data["estimated_cost"] = float(data["estimated_cost"] or 0)
    return data


def fetch_tickers() -> list[dict[str, Any]]:
    analyses = fetch_all_analyses()
    latest_by_ticker: dict[str, dict[str, Any]] = {}
    for item in analyses:
        if item["ticker"] not in latest_by_ticker:
            latest_by_ticker[item["ticker"]] = {
                "ticker": item["ticker"],
                "latest_analysis_id": item["id"],
                "latest_title": item["title"],
                "status": item["status"],
                "updated_at": item["completed_at"] or item["started_at"] or item["created_at"],
            }
    return list(latest_by_ticker.values())

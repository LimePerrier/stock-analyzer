import json
import os
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import psycopg2
import psycopg2.extras

ROOT_DIR = Path(__file__).resolve().parents[2]
UPLOAD_DIR = ROOT_DIR / "uploads"
REPORT_DIR = ROOT_DIR / "reports"

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
REPORT_DIR.mkdir(parents=True, exist_ok=True)

DATABASE_URL = os.environ.get("DATABASE_URL", "")


def utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@contextmanager
def get_conn():
    conn = psycopg2.connect(DATABASE_URL)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS analyses (
                    id SERIAL PRIMARY KEY,
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
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS app_state (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
            """)


def insert_analysis(*, ticker: str, title: str, analysis_type: str,
                    model: str, urls: list[str], txt_path: str = "") -> int:
    now = utcnow()
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO analyses
                   (ticker, title, analysis_type, model, urls_json, txt_path, status, created_at)
                   VALUES (%s, %s, %s, %s, %s, %s, 'queued', %s)
                   RETURNING id""",
                (ticker, title, analysis_type, model, json.dumps(urls), txt_path, now),
            )
            return cur.fetchone()[0]


def update_analysis_status(analysis_id: int, status: str, *,
                           error_message: str = "") -> None:
    now = utcnow()
    with get_conn() as conn:
        with conn.cursor() as cur:
            if status == "running":
                cur.execute(
                    """UPDATE analyses
                       SET status=%s, started_at=%s, error_message=%s
                       WHERE id=%s""",
                    (status, now, error_message, analysis_id),
                )
            elif status in {"completed", "failed"}:
                cur.execute(
                    """UPDATE analyses
                       SET status=%s, completed_at=%s, error_message=%s
                       WHERE id=%s""",
                    (status, now, error_message, analysis_id),
                )
            else:
                cur.execute(
                    """UPDATE analyses
                       SET status=%s, error_message=%s WHERE id=%s""",
                    (status, error_message, analysis_id),
                )


def complete_analysis(analysis_id: int, *, article_text_path: str,
                      report_path: str, report_markdown: str,
                      token_input: int, token_output: int,
                      estimated_cost: float) -> None:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """UPDATE analyses
                   SET status='completed', completed_at=%s,
                       article_text_path=%s, report_path=%s,
                       report_markdown=%s, token_input=%s,
                       token_output=%s, estimated_cost=%s,
                       error_message=''
                   WHERE id=%s""",
                (utcnow(), article_text_path, report_path, report_markdown,
                 token_input, token_output, estimated_cost, analysis_id),
            )


def fail_analysis(analysis_id: int, error_message: str) -> None:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """UPDATE analyses
                   SET status='failed', completed_at=%s, error_message=%s
                   WHERE id=%s""",
                (utcnow(), error_message, analysis_id),
            )


def _row_to_dict(row: tuple, columns: list[str]) -> dict[str, Any]:
    return dict(zip(columns, row))


def _analysis_columns() -> list[str]:
    return [
        "id", "ticker", "title", "analysis_type", "model", "urls_json",
        "txt_path", "status", "created_at", "started_at", "completed_at",
        "article_text_path", "report_path", "report_markdown",
        "token_input", "token_output", "estimated_cost", "error_message",
    ]


def row_to_analysis(row: tuple, columns: list[str]) -> dict[str, Any]:
    data = _row_to_dict(row, columns)
    data["urls"] = json.loads(data.pop("urls_json") or "[]")
    data["estimated_cost"] = float(data["estimated_cost"] or 0)
    return data


def fetch_analysis(analysis_id: int) -> dict[str, Any] | None:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM analyses WHERE id = %s", (analysis_id,))
            row = cur.fetchone()
            if not row:
                return None
            columns = [desc[0] for desc in cur.description]
            return row_to_analysis(row, columns)


def fetch_all_analyses() -> list[dict[str, Any]]:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM analyses ORDER BY created_at DESC, id DESC"
            )
            columns = [desc[0] for desc in cur.description]
            return [row_to_analysis(r, columns) for r in cur.fetchall()]


def fetch_pending_rows() -> list[dict[str, Any]]:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM analyses WHERE status = 'queued' ORDER BY id ASC"
            )
            columns = [desc[0] for desc in cur.description]
            return [row_to_analysis(r, columns) for r in cur.fetchall()]


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
                "updated_at": (item["completed_at"]
                               or item["started_at"]
                               or item["created_at"]),
            }
    return list(latest_by_ticker.values())
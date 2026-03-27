from __future__ import annotations

from pathlib import Path


def get_twitter_prompt_path() -> Path:
    return Path(__file__).resolve().parent.parent / "twitter_feed_prompt.txt"


def load_twitter_prompt() -> str:
    path = get_twitter_prompt_path()
    if not path.exists():
        raise FileNotFoundError(
            f"{path.name} not found. Please create it before running Twitter feed analysis."
        )
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        raise ValueError(f"{path.name} is empty. Please add the Twitter feed prompt.")
    return text


def save_twitter_prompt(text: str) -> Path:
    normalized = text.strip()
    if not normalized:
        raise ValueError("Twitter feed prompt cannot be empty.")
    path = get_twitter_prompt_path()
    path.write_text(normalized + "\n", encoding="utf-8")
    return path

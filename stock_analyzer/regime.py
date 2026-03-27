from __future__ import annotations

from pathlib import Path


def get_market_regime_path() -> Path:
    """Return the single source-of-truth market regime file in the project root."""
    return Path(__file__).resolve().parent.parent / "market_regime.txt"


def load_market_regime() -> str:
    path = get_market_regime_path()
    if not path.exists():
        raise FileNotFoundError(
            f"{path.name} not found. Please create it before running analysis."
        )

    text = path.read_text(encoding="utf-8").strip()
    if not text:
        raise ValueError(f"{path.name} is empty. Please add market regime text.")
    return text


def save_market_regime(text: str) -> Path:
    normalized = text.strip()
    if not normalized:
        raise ValueError("Market regime cannot be empty.")
    path = get_market_regime_path()
    path.write_text(normalized + "\n", encoding="utf-8")
    return path

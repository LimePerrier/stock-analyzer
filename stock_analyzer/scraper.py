from __future__ import annotations

from datetime import datetime

from .dependencies import Article

# ─────────────────────────────────────────────────────────
# ARTICLE SCRAPER (from save_articles.py)
# ─────────────────────────────────────────────────────────



def scrape_urls_to_text(urls: list[str], log_fn=None) -> str:
    """Scrape a list of URLs and return combined text."""
    if Article is None:
        raise ImportError("newspaper3k is not installed. Run: pip install newspaper3k")

    combined = ""
    for url in urls:
        url = url.strip()
        if not url:
            continue
        try:
            if log_fn:
                log_fn(f"Scraping: {url}")
            article = Article(url)
            article.download()
            article.parse()
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            combined += "\n" + "=" * 100 + "\n"
            combined += f"URL: {url}\n"
            combined += f"Scraped: {timestamp}\n"
            combined += f"Title: {article.title}\n"
            combined += "=" * 100 + "\n\n"
            combined += (article.text or "").strip() + "\n"
            if log_fn:
                log_fn(f"  ✓ {article.title}")
        except Exception as e:
            if log_fn:
                log_fn(f"  ✗ Failed: {url} — {e}")
    return combined




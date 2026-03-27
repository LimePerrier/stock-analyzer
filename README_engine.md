# Stock Analyzer Modular Refactor

This refactor keeps the desktop behavior the same while splitting the script into reusable modules that are easier to expose through an API later.

## Run exactly like before

```bash
python stock_analyzerv6.py
```

## Structure

- `stock_analyzerv6.py` — compatibility entry point
- `stock_analyzer/dependencies.py` — optional third-party imports
- `stock_analyzer/config.py` — market regime and theme constants
- `stock_analyzer/prompts.py` — prompt templates
- `stock_analyzer/scraper.py` — URL scraping
- `stock_analyzer/analysis.py` — Anthropic pipeline
- `stock_analyzer/markdown.py` — markdown to HTML rendering
- `stock_analyzer/gui.py` — Tkinter UI
- `stock_analyzer/main.py` — `run()` app bootstrap

## Why this is API-ready

The main non-UI logic now lives in standalone modules:
- `scrape_urls_to_text(...)`
- `run_analysis(...)`
- `md_to_html(...)`

A future FastAPI layer can import those functions directly without pulling in the desktop UI.


## New in v5
- Added Twitter/X feed text-file analysis via `twitter_feed_prompt.txt`.
- Added prompt editor in the desktop UI for the Twitter feed analysis prompt.
- `market_regime.txt` and `twitter_feed_prompt.txt` are now the editable text-file sources of truth.

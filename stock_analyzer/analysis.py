from __future__ import annotations

import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

from .prompts import (
    CATALYST_BEAR,
    CATALYST_BULL,
    CATALYST_SYNTH,
    EARNINGS_BEAR,
    EARNINGS_BULL,
    EARNINGS_SYNTH,
)
from .regime import load_market_regime
from .twitter_prompt import load_twitter_prompt


def run_agent(client, model, system_prompt, user_message):
    """Run a single agent and return (text, tokens_in, tokens_out)."""
    response = client.messages.create(
        model=model,
        max_tokens=4096,
        system=system_prompt,
        messages=[{"role": "user", "content": user_message}],
    )
    return (
        response.content[0].text,
        response.usage.input_tokens,
        response.usage.output_tokens,
    )


def _find_section_block(text: str, heading: str) -> str | None:
    lines = text.splitlines()
    target = heading.strip().upper()
    start = None

    def normalize(line: str) -> str:
        s = line.strip()
        s = re.sub(r'^#{1,6}\s*', '', s)
        s = s.strip('*_ ').strip()
        return s.upper()

    for idx, line in enumerate(lines):
        if normalize(line) == target:
            start = idx
            break

    if start is None:
        return None

    end = len(lines)
    next_heading_pattern = re.compile(r'^\s*(?:#{1,6}\s*)?\d+\.\s+[A-Z]')
    for idx in range(start + 1, len(lines)):
        if next_heading_pattern.match(lines[idx].strip()):
            end = idx
            break

    block = "\n".join(lines[start:end]).strip()
    return block or None


def _build_summary_section(bull_text: str, synthesis_text: str) -> str:
    requested_sections = [
        ("Bull", bull_text, ["6. CONVICTION STATEMENT"]),
        (
            "Synthesis & Decision",
            synthesis_text,
            [
                "1. THE CENTRAL QUESTION",
                "4. THE REGIME CHECK",
                "6. DECISION",
                "7. FINAL WORD",
            ],
        ),
    ]

    blocks: list[str] = []
    for group_label, source_text, headings in requested_sections:
        extracted = []
        for heading in headings:
            block = _find_section_block(source_text, heading)
            if block:
                extracted.append(block)
        if extracted:
            blocks.append(f"## {group_label}\n\n" + "\n\n".join(extracted))

    if not blocks:
        return ""

    return "# SUMMARY\n\n" + "\n\n---\n\n".join(blocks) + "\n\n---\n\n"


def _estimate_cost(model: str, total_in: int, total_out: int) -> float:
    if "opus" in model:
        return (total_in * 0.015 + total_out * 0.075) / 1000
    return (total_in * 0.003 + total_out * 0.015) / 1000


def run_twitter_feed_analysis(client, model, feed_text, title, log_fn=None, prompt_text: str | None = None):
    prompt_text = (prompt_text or load_twitter_prompt()).strip()
    user_message = f"Analyze the following Twitter/X feed text.\n\nTITLE: {title}\n\nFEED TEXT:\n{feed_text}"
    if log_fn:
        log_fn(f"[{title}] Running Twitter feed analysis...")
    output, t_in, t_out = run_agent(client, model, prompt_text, user_message)
    est_cost = _estimate_cost(model, t_in, t_out)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    report = f"""# Twitter Feed Analysis: {title}
*Generated: {timestamp}*
*Model: {model}*

---

# OUTPUT

{output}
"""
    return report, t_in, t_out, est_cost


def run_analysis(client, model, analysis_type, article_text, ticker, log_fn=None, market_regime: str | None = None):
    if analysis_type == "twitter_feed":
        return run_twitter_feed_analysis(client, model, article_text, ticker, log_fn=log_fn)

    if analysis_type == "earnings":
        bull_sys, bear_sys, synth_sys = EARNINGS_BULL, EARNINGS_BEAR, EARNINGS_SYNTH
        label = "earnings report"
        synth_header = "EARNINGS BEING ANALYZED"
    else:
        bull_sys, bear_sys, synth_sys = CATALYST_BULL, CATALYST_BEAR, CATALYST_SYNTH
        label = "catalyst"
        synth_header = "CATALYST BEING ANALYZED"

    market_regime = (market_regime or load_market_regime()).strip()
    user_prompt = f"Analyze this {label}:\n\n{article_text}\n\n{market_regime}"

    total_in = 0
    total_out = 0

    if log_fn:
        log_fn(f"[{ticker}] Running Bull & Bear analysts in parallel...")

    results = {}
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = {
            executor.submit(run_agent, client, model, bull_sys, user_prompt): "Bull Analyst",
            executor.submit(run_agent, client, model, bear_sys, user_prompt): "Bear Analyst",
        }
        for future in as_completed(futures):
            name = futures[future]
            text, t_in, t_out = future.result()
            results[name] = text
            total_in += t_in
            total_out += t_out
            if log_fn:
                log_fn(f"  ✓ {name} complete ({t_in:,} in / {t_out:,} out)")

    if log_fn:
        log_fn(f"[{ticker}] Synthesizing...")

    synthesis_input = f"""{synth_header}:
{article_text}

{market_regime}

{'='*60}
BULL CASE:
{'='*60}
{results['Bull Analyst']}

{'='*60}
BEAR CASE:
{'='*60}
{results['Bear Analyst']}

{'='*60}
Now synthesize into your final decision."""

    synthesis, t_in, t_out = run_agent(client, model, synth_sys, synthesis_input)
    total_in += t_in
    total_out += t_out

    if log_fn:
        log_fn(f"  ✓ Synthesis complete ({t_in:,} in / {t_out:,} out)")

    est_cost = _estimate_cost(model, total_in, total_out)

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    type_label = "Earnings" if analysis_type == "earnings" else "Catalyst"
    summary_section = _build_summary_section(results['Bull Analyst'], synthesis)

    report = f"""# {type_label} Analysis: {ticker}
*Generated: {timestamp}*
*Model: {model}*

---

{summary_section}# BULL CASE

{results['Bull Analyst']}

---

# BEAR CASE

{results['Bear Analyst']}

---

# SYNTHESIS & DECISION

{synthesis}
"""

    return report, total_in, total_out, est_cost

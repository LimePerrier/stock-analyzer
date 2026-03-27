from __future__ import annotations

import re

# ─────────────────────────────────────────────────────────
# MARKDOWN → HTML CONVERTER
# ─────────────────────────────────────────────────────────

def _inline_md(text):
    """Convert inline markdown (bold, italic) to HTML."""
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'(?<!\*)\*([^*]+?)\*(?!\*)', r'<em>\1</em>', text)
    return text


def md_to_html(md_text):
    """Convert markdown to styled HTML for the report viewer."""
    lines = md_text.split("\n")
    html_parts = []
    in_table = False
    in_list = False
    in_ol = False

    for line in lines:
        stripped = line.strip()

        # Horizontal rule
        if stripped in ("---", "***", "___"):
            if in_table:
                html_parts.append("</tbody></table>")
                in_table = False
            if in_list:
                html_parts.append("</ul>")
                in_list = False
            if in_ol:
                html_parts.append("</ol>")
                in_ol = False
            html_parts.append('<hr>')
            continue

        # Table rows
        if stripped.startswith("|") and stripped.endswith("|"):
            cells = [c.strip() for c in stripped.strip("|").split("|")]
            if all(c.replace("-", "").replace(":", "").strip() == "" for c in cells):
                continue
            if not in_table:
                if in_list:
                    html_parts.append("</ul>")
                    in_list = False
                if in_ol:
                    html_parts.append("</ol>")
                    in_ol = False
                html_parts.append('<table><tbody>')
                in_table = True
            row_html = "".join(f"<td>{_inline_md(c)}</td>" for c in cells)
            html_parts.append(f"<tr>{row_html}</tr>")
            continue

        if in_table:
            html_parts.append("</tbody></table>")
            in_table = False

        # Headers
        if stripped.startswith("### "):
            if in_list: html_parts.append("</ul>"); in_list = False
            if in_ol: html_parts.append("</ol>"); in_ol = False
            html_parts.append(f"<h3>{_inline_md(stripped[4:])}</h3>")
            continue
        if stripped.startswith("## "):
            if in_list: html_parts.append("</ul>"); in_list = False
            if in_ol: html_parts.append("</ol>"); in_ol = False
            html_parts.append(f"<h2>{_inline_md(stripped[3:])}</h2>")
            continue
        if stripped.startswith("# "):
            if in_list: html_parts.append("</ul>"); in_list = False
            if in_ol: html_parts.append("</ol>"); in_ol = False
            heading = stripped[2:]
            css_class = ""
            if "BULL" in heading.upper():
                css_class = ' class="bull"'
            elif "BEAR" in heading.upper():
                css_class = ' class="bear"'
            elif "SYNTHESIS" in heading.upper() or "DECISION" in heading.upper():
                css_class = ' class="synth"'
            html_parts.append(f"<h1{css_class}>{_inline_md(heading)}</h1>")
            continue

        # Unordered list
        if stripped.startswith("- ") or (stripped.startswith("* ") and not stripped.endswith("*")):
            if in_ol: html_parts.append("</ol>"); in_ol = False
            if not in_list:
                html_parts.append("<ul>")
                in_list = True
            html_parts.append(f"<li>{_inline_md(stripped[2:])}</li>")
            continue

        # Ordered list
        m = re.match(r'^(\d+)\.\s+(.*)', stripped)
        if m:
            if in_list: html_parts.append("</ul>"); in_list = False
            if not in_ol:
                html_parts.append("<ol>")
                in_ol = True
            html_parts.append(f"<li>{_inline_md(m.group(2))}</li>")
            continue

        # Close lists
        if in_list: html_parts.append("</ul>"); in_list = False
        if in_ol: html_parts.append("</ol>"); in_ol = False

        # Empty line
        if not stripped:
            continue

        # Metadata: *Generated: ...*
        if stripped.startswith("*") and stripped.endswith("*") and len(stripped) > 2 and "**" not in stripped:
            html_parts.append(f'<p class="meta">{stripped.strip("*")}</p>')
            continue

        # Regular paragraph
        html_parts.append(f"<p>{_inline_md(stripped)}</p>")

    if in_table: html_parts.append("</tbody></table>")
    if in_list: html_parts.append("</ul>")
    if in_ol: html_parts.append("</ol>")

    body = "\n".join(html_parts)

    return f'''<!DOCTYPE html>
<html><head><meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Instrument+Serif:ital@0;1&family=DM+Sans:ital,wght@0,300;0,400;0,500;1,300;1,400&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
:root {{
    --bg: #FAFAF8;
    --text: #1A1A18;
    --text-muted: #8A8880;
    --text-light: #B0ADA6;
    --accent: #C4613A;
    --accent-light: #F0DDD4;
    --border: #E5E2DC;
    --code-bg: #EDEAE4;
    --bull: #2D7A4F;
    --bull-bg: #F0F7F2;
    --bull-border: #C8E0CF;
    --bear: #B33B2E;
    --bear-bg: #FDF3F2;
    --bear-border: #E5C5C1;
    --synth: #9A6B1E;
    --synth-bg: #FBF6ED;
    --synth-border: #E2D5B8;
}}

* {{ margin: 0; padding: 0; box-sizing: border-box; }}

body {{
    font-family: 'DM Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    background: var(--bg);
    color: var(--text);
    font-size: 15.5px;
    line-height: 1.75;
}}

.rendered {{
    max-width: 720px;
    margin: 0 auto;
    padding: 48px 40px 120px;
}}

h1 {{
    font-family: 'Instrument Serif', Georgia, serif;
    font-size: 38px;
    font-weight: 400;
    line-height: 1.15;
    letter-spacing: -0.025em;
    margin-top: 48px;
    margin-bottom: 20px;
    padding-bottom: 12px;
    border-bottom: 1px solid var(--border);
    color: var(--text);
}}

h1:first-child {{
    margin-top: 0;
}}

h1.bull {{
    color: var(--bull);
    border-bottom-color: var(--bull-border);
}}

h1.bear {{
    color: var(--bear);
    border-bottom-color: var(--bear-border);
}}

h1.synth {{
    color: var(--synth);
    border-bottom-color: var(--synth-border);
}}

h2 {{
    font-family: 'Instrument Serif', Georgia, serif;
    font-size: 26px;
    font-weight: 400;
    line-height: 1.25;
    letter-spacing: -0.015em;
    margin-top: 44px;
    margin-bottom: 14px;
    color: var(--text);
}}

h3 {{
    font-family: 'DM Sans', sans-serif;
    font-size: 13px;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    margin-top: 32px;
    margin-bottom: 10px;
    color: var(--text-muted);
}}

p {{
    font-size: 15.5px;
    line-height: 1.75;
    color: var(--text);
    margin-bottom: 16px;
    font-weight: 300;
}}

p.meta {{
    color: var(--text-light);
    font-size: 13px;
    font-style: italic;
    margin-bottom: 4px;
}}

strong {{
    font-weight: 500;
    color: var(--text);
}}

em {{
    font-style: italic;
    color: var(--text-muted);
}}

hr {{
    border: none;
    height: 1px;
    background: var(--border);
    margin: 44px 0;
}}

ul, ol {{
    margin: 14px 0;
    padding-left: 24px;
}}

li {{
    font-size: 15.5px;
    line-height: 1.75;
    font-weight: 300;
    margin-bottom: 6px;
    color: var(--text);
}}

ol {{
    list-style: none;
    counter-reset: item;
    padding-left: 0;
}}

ol li {{
    counter-increment: item;
    position: relative;
    padding-left: 32px;
}}

ol li::before {{
    content: counter(item);
    position: absolute;
    left: 0;
    top: 2px;
    color: var(--accent);
    font-weight: 500;
    font-size: 14px;
    width: 22px;
    height: 22px;
    line-height: 22px;
    text-align: center;
    border-radius: 5px;
    background: var(--accent-light);
}}

table {{
    width: 100%;
    border-collapse: collapse;
    margin: 20px 0;
    font-size: 14px;
}}

th {{
    text-align: left;
    font-weight: 500;
    padding: 10px 16px;
    border-bottom: 2px solid var(--border);
    font-size: 11.5px;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: var(--text-muted);
}}

td {{
    padding: 10px 16px;
    border-bottom: 1px solid var(--border);
    font-weight: 300;
    vertical-align: top;
    color: var(--text);
}}

tr:first-child td {{
    font-weight: 500;
    font-size: 11.5px;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: var(--text-muted);
    border-bottom: 2px solid var(--border);
}}

blockquote {{
    border-left: 3px solid var(--accent);
    padding: 4px 0 4px 24px;
    margin: 24px 0;
    color: var(--text-muted);
    font-style: italic;
}}

code {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 13.5px;
    background: var(--code-bg);
    padding: 2px 7px;
    border-radius: 4px;
    color: var(--accent);
}}

pre {{
    background: var(--code-bg);
    border-radius: 8px;
    padding: 20px 24px;
    margin: 24px 0;
    overflow-x: auto;
    border: 1px solid var(--border);
}}

pre code {{
    background: none;
    padding: 0;
    font-size: 13px;
    line-height: 1.65;
    color: var(--text);
}}
</style></head>
<body><div class="rendered">
{body}
</div></body></html>'''





from __future__ import annotations

import os
import re
import sys
import threading
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from .queue import AnalysisJob, QueueService
from .regime import get_market_regime_path, load_market_regime, save_market_regime
from .twitter_prompt import get_twitter_prompt_path, load_twitter_prompt, save_twitter_prompt
from .runner import AnalysisRunner
from .config import (
    ACCENT,
    ACCENT_HOVER,
    BG,
    BG_CARD,
    BG_INPUT,
    BORDER,
    FONT,
    FONT_BOLD,
    FONT_SMALL,
    GREEN,
    ORANGE,
    RED,
    TEXT,
    TEXT_DIM,
    TEXT_LIGHT,
)
from .dependencies import Article, anthropic
from .markdown import md_to_html

# ─────────────────────────────────────────────────────────
# GUI APPLICATION
# ─────────────────────────────────────────────────────────

class StockAnalyzerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Stock Analyzer")
        self.root.geometry("960x860")
        self.root.configure(bg=BG)
        self.root.minsize(780, 680)
        self._stop_flag = False
        self._running = False
        self.queue_service = QueueService(max_jobs=25)
        self.runner = AnalysisRunner()
        self.txt_path_var = tk.StringVar(value="")

        try:
            self.root.iconbitmap(default="")
        except Exception:
            pass

        self._build_ui()

    def _build_ui(self):
        style = ttk.Style()
        style.theme_use("clam")

        style.configure("Mote.TNotebook", background=BG, borderwidth=0)
        style.configure("Mote.TNotebook.Tab",
                        background=BG_CARD, foreground=TEXT_DIM,
                        font=("Segoe UI", 10, "bold"),
                        padding=[18, 8])
        style.map("Mote.TNotebook.Tab",
                  background=[("selected", BG), ("active", BG_INPUT)],
                  foreground=[("selected", ACCENT), ("active", TEXT)])
        style.layout("Mote.TNotebook", [("Mote.TNotebook.client", {"sticky": "nswe"})])

        style.configure("Mote.Vertical.TScrollbar",
                        background=BG_CARD, troughcolor=BG,
                        borderwidth=0, arrowsize=0, width=6)
        style.map("Mote.Vertical.TScrollbar",
                  background=[("active", BORDER), ("!active", BG_CARD)])

        self.notebook = ttk.Notebook(self.root, style="Mote.TNotebook")
        self.notebook.pack(fill="both", expand=True)

        self.analysis_tab = tk.Frame(self.notebook, bg=BG)
        self.notebook.add(self.analysis_tab, text="  Analysis  ")

        self.report_tabs = {}
        self.notebook.bind("<Button-3>", self._on_tab_right_click)

        self._build_analysis_tab()
        self._on_analysis_type_changed()

    # ── ANALYSIS TAB ────────────────────────────────────

    def _build_analysis_tab(self):
        container = tk.Frame(self.analysis_tab, bg=BG, padx=40, pady=24)
        container.pack(fill="both", expand=True)

        # ── Header ──
        header = tk.Frame(container, bg=BG)
        header.pack(fill="x", pady=(0, 20))
        tk.Label(header, text="●", bg=BG, fg=ACCENT, font=("Segoe UI", 10)).pack(side="left")
        tk.Label(header, text="Stock Analyzer", bg=BG, fg=TEXT,
                 font=("Georgia", 20)).pack(side="left", padx=(8, 0))
        tk.Label(header, text="Earnings & Catalyst Analysis", bg=BG, fg=TEXT_LIGHT,
                 font=("Segoe UI", 10)).pack(side="left", padx=(14, 0), pady=(5, 0))

        # ════════════════════════════════════════════════════
        # ADD TO QUEUE SECTION
        # ════════════════════════════════════════════════════

        add_section = tk.Frame(container, bg=BG)
        add_section.pack(fill="both", expand=True)

        # Ticker input row
        ticker_row = tk.Frame(add_section, bg=BG)
        ticker_row.pack(fill="x", pady=(0, 6))

        tk.Label(ticker_row, text="TICKER", bg=BG, fg=TEXT_DIM,
                 font=("Segoe UI", 9, "bold")).pack(side="left")
        self.ticker_var = tk.StringVar(value="")
        self.ticker_entry = tk.Entry(ticker_row, textvariable=self.ticker_var,
                                     bg=BG_INPUT, fg=TEXT, insertbackground=TEXT,
                                     font=("Segoe UI", 11, "bold"),
                                     bd=0, highlightthickness=1,
                                     highlightcolor=ACCENT, highlightbackground=BORDER,
                                     width=10)
        self.ticker_entry.pack(side="left", padx=(10, 0), ipady=5, ipadx=6)

        # Source input label
        tk.Label(add_section, text="ARTICLE URLs / TEXT FILE", bg=BG, fg=TEXT_DIM,
                 font=("Segoe UI", 9, "bold"), anchor="w").pack(fill="x", pady=(6, 0))
        self.source_help_label = tk.Label(add_section, text="Paste one URL per line for this ticker", bg=BG, fg=TEXT_LIGHT,
                 font=("Segoe UI", 9), anchor="w")
        self.source_help_label.pack(fill="x", pady=(0, 4))

        # URL text area
        url_frame = tk.Frame(add_section, bg=BORDER)
        url_frame.pack(fill="both", expand=True, pady=(0, 8))

        txt_file_row = tk.Frame(add_section, bg=BG)
        txt_file_row.pack(fill="x", pady=(0, 8))

        self.txt_file_btn = tk.Button(
            txt_file_row, text="Attach .txt File", bg=BG, fg=ACCENT,
            font=("Segoe UI", 10, "bold"), bd=1, padx=12, pady=6,
            activebackground=BG_CARD, activeforeground=ACCENT,
            cursor="hand2", command=self._on_browse_txt,
            relief="solid", highlightthickness=0,
        )
        self.txt_file_btn.configure(highlightbackground=BORDER)
        self.txt_file_btn.pack(side="left")

        self.txt_file_label = tk.Label(
            txt_file_row, text="No file selected", bg=BG, fg=TEXT_LIGHT, font=("Segoe UI", 9), anchor="w"
        )
        self.txt_file_label.pack(side="left", padx=(10, 0), fill="x", expand=True)

        self.url_text = tk.Text(
            url_frame, bg="#FFFFFF", fg=TEXT, insertbackground=TEXT,
            font=("Consolas", 10), bd=0, wrap="word", height=5,
            highlightthickness=0, padx=14, pady=10,
            selectbackground=ACCENT, selectforeground="#FFFFFF",
        )
        url_sb = ttk.Scrollbar(url_frame, orient="vertical", command=self.url_text.yview,
                                style="Mote.Vertical.TScrollbar")
        self.url_text.configure(yscrollcommand=url_sb.set)
        self.url_text.pack(side="left", fill="both", expand=True, padx=1, pady=1)
        url_sb.pack(side="right", fill="y", padx=1, pady=1)

        # Add button
        add_btn_row = tk.Frame(add_section, bg=BG)
        add_btn_row.pack(fill="x", pady=(0, 12))

        self.add_btn = tk.Button(
            add_btn_row, text="+ Add to Queue", bg=BG, fg=ACCENT,
            font=("Segoe UI", 10, "bold"), bd=1, padx=14, pady=6,
            activebackground=BG_CARD, activeforeground=ACCENT,
            cursor="hand2", command=self._on_add_to_queue,
            relief="solid", highlightthickness=0,
        )
        self.add_btn.configure(highlightbackground=BORDER)
        self.add_btn.pack(side="left")

        self.queue_count_label = tk.Label(
            add_btn_row, text="", bg=BG, fg=TEXT_LIGHT, font=("Segoe UI", 9))
        self.queue_count_label.pack(side="left", padx=(12, 0))

        # ════════════════════════════════════════════════════
        # QUEUE DISPLAY
        # ════════════════════════════════════════════════════

        queue_section = tk.Frame(container, bg=BG)
        queue_section.pack(fill="x", pady=(0, 12))

        tk.Label(queue_section, text="QUEUE", bg=BG, fg=TEXT_DIM,
                 font=("Segoe UI", 9, "bold"), anchor="w").pack(fill="x")

        # Queue list container (items will be packed here)
        self.queue_list_frame = tk.Frame(queue_section, bg=BG)
        self.queue_list_frame.pack(fill="x", pady=(4, 0))

        self.queue_empty_label = tk.Label(
            self.queue_list_frame, text="No tickers queued — add one above",
            bg=BG, fg=TEXT_LIGHT, font=("Segoe UI", 9, "italic"), anchor="w")
        self.queue_empty_label.pack(fill="x")

        # ════════════════════════════════════════════════════
        # MARKET REGIME
        # ════════════════════════════════════════════════════

        regime_section = tk.Frame(container, bg=BG)
        regime_section.pack(fill="both", pady=(0, 12))

        regime_header = tk.Frame(regime_section, bg=BG)
        regime_header.pack(fill="x")
        tk.Label(regime_header, text="MARKET REGIME", bg=BG, fg=TEXT_DIM,
                 font=("Segoe UI", 9, "bold"), anchor="w").pack(side="left")
        self.regime_path_label = tk.Label(regime_header, text=str(get_market_regime_path().name),
                                          bg=BG, fg=TEXT_LIGHT, font=("Segoe UI", 9))
        self.regime_path_label.pack(side="right")

        tk.Label(regime_section, text="Edit here and save — future runs will use the updated regime without changing code.",
                 bg=BG, fg=TEXT_LIGHT, font=("Segoe UI", 9), anchor="w").pack(fill="x", pady=(0, 4))

        regime_frame = tk.Frame(regime_section, bg=BORDER)
        regime_frame.pack(fill="both", expand=False)

        self.regime_text = tk.Text(
            regime_frame, bg="#FFFFFF", fg=TEXT, insertbackground=TEXT,
            font=("Consolas", 9), bd=0, wrap="word", height=8,
            highlightthickness=0, padx=14, pady=10,
            selectbackground=ACCENT, selectforeground="#FFFFFF",
        )
        regime_sb = ttk.Scrollbar(regime_frame, orient="vertical", command=self.regime_text.yview,
                                  style="Mote.Vertical.TScrollbar")
        self.regime_text.configure(yscrollcommand=regime_sb.set)
        self.regime_text.pack(side="left", fill="both", expand=True, padx=1, pady=1)
        regime_sb.pack(side="right", fill="y", padx=1, pady=1)
        try:
            self.regime_text.insert("1.0", load_market_regime())
        except (FileNotFoundError, ValueError) as exc:
            self._log(f"! {exc}")
            self._set_status("Market regime file issue", RED)

        regime_btn_row = tk.Frame(regime_section, bg=BG)
        regime_btn_row.pack(fill="x", pady=(6, 0))

        self.save_regime_btn = tk.Button(
            regime_btn_row, text="Save Regime", bg=BG, fg=ACCENT,
            font=("Segoe UI", 10, "bold"), bd=1, padx=14, pady=6,
            activebackground=BG_CARD, activeforeground=ACCENT,
            cursor="hand2", command=self._on_save_regime,
            relief="solid", highlightthickness=0,
        )
        self.save_regime_btn.configure(highlightbackground=BORDER)
        self.save_regime_btn.pack(side="left")

        self.reload_regime_btn = tk.Button(
            regime_btn_row, text="Reload", bg=BG, fg=TEXT_DIM,
            font=("Segoe UI", 10), bd=1, padx=14, pady=6,
            activebackground=BG_CARD, activeforeground=TEXT,
            cursor="hand2", command=self._on_reload_regime,
            relief="solid", highlightthickness=0,
        )
        self.reload_regime_btn.configure(highlightbackground=BORDER)
        self.reload_regime_btn.pack(side="left", padx=(8, 0))

        # ════════════════════════════════════════════════════
        # TWITTER FEED PROMPT
        # ════════════════════════════════════════════════════

        twitter_section = tk.Frame(container, bg=BG)
        twitter_section.pack(fill="both", pady=(0, 12))

        twitter_header = tk.Frame(twitter_section, bg=BG)
        twitter_header.pack(fill="x")
        tk.Label(twitter_header, text="TWITTER FEED PROMPT", bg=BG, fg=TEXT_DIM,
                 font=("Segoe UI", 9, "bold"), anchor="w").pack(side="left")
        self.twitter_prompt_path_label = tk.Label(twitter_header, text=str(get_twitter_prompt_path().name),
                                                  bg=BG, fg=TEXT_LIGHT, font=("Segoe UI", 9))
        self.twitter_prompt_path_label.pack(side="right")

        tk.Label(twitter_section, text="Edit here and save — Twitter/X text-file analyses will use this exact prompt.",
                 bg=BG, fg=TEXT_LIGHT, font=("Segoe UI", 9), anchor="w").pack(fill="x", pady=(0, 4))

        twitter_frame = tk.Frame(twitter_section, bg=BORDER)
        twitter_frame.pack(fill="both", expand=False)

        self.twitter_prompt_text = tk.Text(
            twitter_frame, bg="#FFFFFF", fg=TEXT, insertbackground=TEXT,
            font=("Consolas", 9), bd=0, wrap="word", height=10,
            highlightthickness=0, padx=14, pady=10,
            selectbackground=ACCENT, selectforeground="#FFFFFF",
        )
        twitter_sb = ttk.Scrollbar(twitter_frame, orient="vertical", command=self.twitter_prompt_text.yview,
                                   style="Mote.Vertical.TScrollbar")
        self.twitter_prompt_text.configure(yscrollcommand=twitter_sb.set)
        self.twitter_prompt_text.pack(side="left", fill="both", expand=True, padx=1, pady=1)
        twitter_sb.pack(side="right", fill="y", padx=1, pady=1)
        try:
            self.twitter_prompt_text.insert("1.0", load_twitter_prompt())
        except (FileNotFoundError, ValueError) as exc:
            self._log(f"! {exc}")
            self._set_status("Twitter prompt file issue", RED)

        twitter_btn_row = tk.Frame(twitter_section, bg=BG)
        twitter_btn_row.pack(fill="x", pady=(6, 0))

        self.save_twitter_prompt_btn = tk.Button(
            twitter_btn_row, text="Save Twitter Prompt", bg=BG, fg=ACCENT,
            font=("Segoe UI", 10, "bold"), bd=1, padx=14, pady=6,
            activebackground=BG_CARD, activeforeground=ACCENT,
            cursor="hand2", command=self._on_save_twitter_prompt,
            relief="solid", highlightthickness=0,
        )
        self.save_twitter_prompt_btn.configure(highlightbackground=BORDER)
        self.save_twitter_prompt_btn.pack(side="left")

        self.reload_twitter_prompt_btn = tk.Button(
            twitter_btn_row, text="Reload", bg=BG, fg=TEXT_DIM,
            font=("Segoe UI", 10), bd=1, padx=14, pady=6,
            activebackground=BG_CARD, activeforeground=TEXT,
            cursor="hand2", command=self._on_reload_twitter_prompt,
            relief="solid", highlightthickness=0,
        )
        self.reload_twitter_prompt_btn.configure(highlightbackground=BORDER)
        self.reload_twitter_prompt_btn.pack(side="left", padx=(8, 0))

        # ════════════════════════════════════════════════════
        # OPTIONS + RUN
        # ════════════════════════════════════════════════════

        opts_frame = tk.Frame(container, bg=BG)
        opts_frame.pack(fill="x", pady=(0, 12))

        # Model
        model_section = tk.Frame(opts_frame, bg=BG)
        model_section.pack(side="left", fill="x", expand=True)
        tk.Label(model_section, text="MODEL", bg=BG, fg=TEXT_DIM,
                 font=("Segoe UI", 9, "bold")).pack(anchor="w")

        self.model_var = tk.StringVar(value="claude-sonnet-4-6")
        model_radios = tk.Frame(model_section, bg=BG)
        model_radios.pack(anchor="w", pady=(4, 0))

        for val, label in [("claude-opus-4-6", "Opus"), ("claude-sonnet-4-6", "Sonnet")]:
            rb = tk.Radiobutton(model_radios, text=label, variable=self.model_var, value=val,
                                bg=BG, fg=TEXT, selectcolor=BG_INPUT, activebackground=BG,
                                activeforeground=ACCENT, font=FONT, indicatoron=True,
                                highlightthickness=0, bd=0, command=self._on_analysis_type_changed)
            rb.pack(side="left", padx=(0, 18))

        sep = tk.Frame(opts_frame, bg=BORDER, width=1)
        sep.pack(side="left", fill="y", padx=20, pady=2)

        # Analysis type
        type_section = tk.Frame(opts_frame, bg=BG)
        type_section.pack(side="left", fill="x", expand=True)
        tk.Label(type_section, text="ANALYSIS TYPE", bg=BG, fg=TEXT_DIM,
                 font=("Segoe UI", 9, "bold")).pack(anchor="w")

        self.type_var = tk.StringVar(value="earnings")
        type_radios = tk.Frame(type_section, bg=BG)
        type_radios.pack(anchor="w", pady=(4, 0))

        for val, label in [("earnings", "Earnings"), ("catalyst", "Catalyst"), ("twitter_feed", "Twitter Feed (.txt)")]:
            rb = tk.Radiobutton(type_radios, text=label, variable=self.type_var, value=val,
                                bg=BG, fg=TEXT, selectcolor=BG_INPUT, activebackground=BG,
                                activeforeground=ACCENT, font=FONT, indicatoron=True,
                                highlightthickness=0, bd=0, command=self._on_analysis_type_changed)
            rb.pack(side="left", padx=(0, 18))

        # Run / Stop buttons
        btn_row = tk.Frame(container, bg=BG)
        btn_row.pack(fill="x", pady=(0, 12))

        self.go_btn = tk.Button(
            btn_row, text="Run All", bg=ACCENT, fg="#FFFFFF",
            font=("Segoe UI", 11, "bold"), bd=0, padx=28, pady=9,
            activebackground=ACCENT_HOVER, activeforeground="#FFFFFF",
            cursor="hand2", command=self._on_go,
        )
        self.go_btn.pack(side="left")

        self.stop_btn = tk.Button(
            btn_row, text="Stop", bg=BG, fg=RED,
            font=("Segoe UI", 10), bd=1, padx=16, pady=8,
            activebackground=BG_CARD, activeforeground=RED,
            cursor="hand2", command=self._on_stop,
            highlightthickness=0, relief="solid",
        )
        self.stop_btn.configure(highlightbackground=BORDER)

        self.clear_queue_btn = tk.Button(
            btn_row, text="Clear Pending", bg=BG, fg=TEXT_DIM,
            font=("Segoe UI", 10), bd=1, padx=14, pady=8,
            activebackground=BG_CARD, activeforeground=TEXT,
            cursor="hand2", command=self._on_clear_queue,
            highlightthickness=0, relief="solid",
        )
        self.clear_queue_btn.configure(highlightbackground=BORDER)
        self.clear_queue_btn.pack(side="right")

        # ── Status / Log ──
        status_row = tk.Frame(container, bg=BG)
        status_row.pack(fill="x", pady=(0, 4))
        tk.Label(status_row, text="STATUS", bg=BG, fg=TEXT_DIM,
                 font=("Segoe UI", 9, "bold")).pack(side="left")
        self.status_label = tk.Label(status_row, text="Ready", bg=BG, fg=GREEN,
                                     font=("Segoe UI", 9, "bold"))
        self.status_label.pack(side="right")

        log_frame = tk.Frame(container, bg=BORDER)
        log_frame.pack(fill="both", expand=True)

        self.log_text = tk.Text(
            log_frame, bg=BG_CARD, fg=TEXT_DIM, font=("Consolas", 9),
            bd=0, wrap="word", height=5, state="disabled",
            highlightthickness=0, padx=14, pady=10,
            selectbackground=ACCENT, selectforeground="#FFFFFF",
        )
        log_sb = ttk.Scrollbar(log_frame, orient="vertical", command=self.log_text.yview,
                                style="Mote.Vertical.TScrollbar")
        self.log_text.configure(yscrollcommand=log_sb.set)
        self.log_text.pack(side="left", fill="both", expand=True, padx=1, pady=1)
        log_sb.pack(side="right", fill="y", padx=1, pady=1)

    def _on_browse_txt(self):
        path = filedialog.askopenfilename(
            title="Select Twitter/X feed text file",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
        )
        if not path:
            return
        self.txt_path_var.set(path)
        self.txt_file_label.configure(text=Path(path).name)
        self._set_status("Text file attached", GREEN)

    def _on_analysis_type_changed(self):
        analysis_type = self.type_var.get()
        is_twitter = analysis_type == "twitter_feed"
        if is_twitter:
            self.source_help_label.configure(text="Attach a .txt file containing the raw Twitter/X feed text")
            self.url_text.configure(state="disabled")
            self.txt_file_btn.configure(state="normal")
            if not self.ticker_var.get().strip() and self.txt_path_var.get().strip():
                self.ticker_var.set(Path(self.txt_path_var.get()).stem)
        else:
            self.source_help_label.configure(text="Paste one URL per line for this ticker")
            self.url_text.configure(state="normal")
            self.txt_file_btn.configure(state="normal")

    def _on_save_twitter_prompt(self):
        text_value = self.twitter_prompt_text.get("1.0", "end").strip()
        try:
            path = save_twitter_prompt(text_value)
        except ValueError as exc:
            messagebox.showwarning("Invalid Twitter Prompt", str(exc))
            return

        self.twitter_prompt_path_label.configure(text=str(path.name))
        self._log(f"✓ Saved Twitter feed prompt to {path.name}")
        self._set_status("Twitter prompt saved", GREEN)

    def _on_reload_twitter_prompt(self):
        self.twitter_prompt_text.delete("1.0", "end")
        try:
            self.twitter_prompt_text.insert("1.0", load_twitter_prompt())
        except (FileNotFoundError, ValueError) as exc:
            messagebox.showerror("Twitter Prompt Error", str(exc))
            self._log(f"! {exc}")
            self._set_status("Twitter prompt file issue", RED)
            return
        self._log("↻ Reloaded Twitter feed prompt from file")
        self._set_status("Twitter prompt reloaded", GREEN)

    def _on_save_regime(self):
        text = self.regime_text.get("1.0", "end").strip()
        try:
            path = save_market_regime(text)
        except ValueError as exc:
            messagebox.showwarning("Invalid Regime", str(exc))
            return

        self.regime_path_label.configure(text=str(path.name))
        self._log(f"✓ Saved market regime to {path.name}")
        self._set_status("Market regime saved", GREEN)

    def _on_reload_regime(self):
        self.regime_text.delete("1.0", "end")
        try:
            self.regime_text.insert("1.0", load_market_regime())
        except (FileNotFoundError, ValueError) as exc:
            messagebox.showerror("Market Regime Error", str(exc))
            self._log(f"! {exc}")
            self._set_status("Market regime file issue", RED)
            return
        self._log("↻ Reloaded market regime from file")
        self._set_status("Market regime reloaded", GREEN)

    # ── QUEUE MANAGEMENT ────────────────────────────────

    def _on_add_to_queue(self):
        analysis_type = self.type_var.get()
        raw_title = self.ticker_var.get().strip()
        ticker = raw_title.upper() if analysis_type != "twitter_feed" else raw_title
        model = self.model_var.get()
        txt_path = ""
        urls = []

        if analysis_type == "twitter_feed":
            txt_path = self.txt_path_var.get().strip()
            if not txt_path:
                messagebox.showwarning("No Text File", "Please attach a .txt file.")
                return
            if not ticker:
                ticker = Path(txt_path).stem
        else:
            if not ticker:
                messagebox.showwarning("No Ticker", "Please enter a ticker symbol.")
                return
            urls_raw = self.url_text.get("1.0", "end").strip()
            urls = [u.strip() for u in urls_raw.splitlines() if u.strip()]
            if not urls:
                messagebox.showwarning("No URLs", "Please paste at least one URL.")
                return

        if self.queue_service.pending_count() >= 25:
            messagebox.showwarning("Queue Full", "Maximum 25 queued jobs.")
            return

        if self.queue_service.has_duplicate(ticker, analysis_type, txt_path=txt_path):
            messagebox.showwarning("Duplicate", f"{ticker} already has a queued {analysis_type} job.")
            return

        self.queue_service.add_job(AnalysisJob(
            ticker=ticker,
            urls=urls,
            analysis_type=analysis_type,
            model=model,
            txt_path=txt_path,
        ))

        self.ticker_var.set("")
        self.url_text.delete("1.0", "end")
        self.txt_path_var.set("")
        self.txt_file_label.configure(text="No file selected")
        self.ticker_entry.focus()

        self._refresh_queue_display()

    def _on_remove_from_queue(self, index):
        if self.queue_service.remove_queued_at_index(index):
            self._refresh_queue_display()

    def _on_clear_queue(self):
        self.queue_service.clear_pending()
        self._refresh_queue_display()

    def _refresh_queue_display(self):
        for w in self.queue_list_frame.winfo_children():
            w.destroy()

        queue_items = [job for job in self.queue_service.snapshot() if job.status == "queued"]

        if not queue_items:
            self.queue_empty_label = tk.Label(
                self.queue_list_frame, text="No tickers queued — add one above",
                bg=BG, fg=TEXT_LIGHT, font=("Segoe UI", 9, "italic"), anchor="w")
            self.queue_empty_label.pack(fill="x")
            self.queue_count_label.configure(text="")
            return

        self.queue_count_label.configure(text=f"{len(queue_items)} job(s) queued")

        for i, item in enumerate(queue_items):
            row = tk.Frame(self.queue_list_frame, bg=BG_CARD)
            row.pack(fill="x", pady=1)

            # Ticker label
            tk.Label(row, text=item.ticker, bg=BG_CARD, fg=TEXT,
                     font=("Segoe UI", 10, "bold"), padx=10, pady=4).pack(side="left")

            # Source count / file
            if item.analysis_type == "twitter_feed":
                source_text = Path(item.txt_path).name if item.txt_path else "txt file"
            else:
                n = len(item.urls)
                source_text = f"{n} url{'s' if n != 1 else ''}"
            tk.Label(row, text=source_text,
                     bg=BG_CARD, fg=TEXT_LIGHT, font=("Segoe UI", 9),
                     padx=6).pack(side="left")

            if item.analysis_type == "earnings":
                type_label = "Earnings"
                type_color = GREEN
            elif item.analysis_type == "catalyst":
                type_label = "Catalyst"
                type_color = ORANGE
            else:
                type_label = "Twitter Feed"
                type_color = ACCENT
            tk.Label(row, text=type_label, bg=BG_CARD, fg=type_color,
                     font=("Segoe UI", 9, "bold"), padx=8).pack(side="left")

            # Remove button
            idx = i  # capture for closure
            tk.Button(row, text="✕", bg=BG_CARD, fg=TEXT_LIGHT,
                      font=("Segoe UI", 9), bd=0, padx=8, pady=2,
                      cursor="hand2", activebackground=BG_CARD, activeforeground=RED,
                      command=lambda ix=idx: self._on_remove_from_queue(ix)
                      ).pack(side="right", padx=(0, 4))

    # ── REPORT TABS ─────────────────────────────────────

    def _on_tab_right_click(self, event):
        try:
            tab_index = self.notebook.index(f"@{event.x},{event.y}")
        except Exception:
            return
        if tab_index == 0:
            return
        tab_id = self.notebook.tabs()[tab_index]
        frame = self.notebook.nametowidget(tab_id)
        self.notebook.forget(tab_index)
        frame.destroy()
        self.report_tabs.pop(tab_id, None)

    def _show_report(self, markdown_text, filepath):
        report_frame = tk.Frame(self.notebook, bg="#FAFAF8")
        basename = os.path.basename(filepath)
        ticker = basename.split("_")[1] if "_" in basename else "Report"
        self.notebook.add(report_frame, text=f"  {ticker}  ✕")
        tab_id = str(report_frame)
        self.report_tabs[tab_id] = report_frame

        top_bar = tk.Frame(report_frame, bg=BG_CARD, padx=16, pady=8)
        top_bar.pack(fill="x")

        tk.Label(top_bar, text=basename, bg=BG_CARD, fg=ACCENT,
                 font=FONT_BOLD).pack(side="left")

        def _open_external():
            if sys.platform == "win32":
                os.startfile(filepath)
            else:
                os.system(f"open '{filepath}'")

        def _open_folder():
            folder = os.path.dirname(filepath)
            if sys.platform == "win32":
                os.startfile(folder)
            else:
                os.system(f"open '{folder}'")

        def _close_tab():
            idx = self.notebook.index(report_frame)
            self.notebook.forget(idx)
            report_frame.destroy()
            self.report_tabs.pop(tab_id, None)

        btn_frame = tk.Frame(top_bar, bg=BG_CARD)
        btn_frame.pack(side="right")

        for txt, cmd in [("Open File", _open_external), ("Open Folder", _open_folder)]:
            tk.Button(btn_frame, text=txt, bg=BG, fg=TEXT_DIM,
                      font=FONT_SMALL, bd=0, padx=10, pady=3, cursor="hand2",
                      activebackground=BORDER, activeforeground=TEXT,
                      command=cmd).pack(side="left", padx=2)

        tk.Button(btn_frame, text="✕ Close", bg=RED, fg="#FFFFFF",
                  font=("Segoe UI", 9, "bold"), bd=0, padx=10, pady=3, cursor="hand2",
                  activebackground="#922F24", activeforeground="#FFFFFF",
                  command=_close_tab).pack(side="left", padx=(8, 0))

        html_content = md_to_html(markdown_text)
        rendered = False

        if not rendered:
            try:
                from tkinterweb import HtmlFrame
                frame = HtmlFrame(report_frame, messages_enabled=False)
                frame.load_html(html_content)
                frame.pack(fill="both", expand=True)
                rendered = True
            except Exception:
                pass

        if not rendered:
            try:
                from tkhtmlview import HTMLScrolledText
                view = HTMLScrolledText(report_frame, html=html_content,
                                        background=BG, padx=20, pady=16)
                view.pack(fill="both", expand=True)
                rendered = True
            except Exception:
                pass

        if not rendered:
            self._render_text_fallback(report_frame, markdown_text)

        self.notebook.select(report_frame)

    def _render_text_fallback(self, parent, markdown_text):
        text_w = tk.Text(
            parent, bg="#FAFAF8", fg="#1A1A18",
            font=("Segoe UI", 11), bd=0, wrap="word",
            padx=40, pady=32, insertbackground="#1A1A18",
            selectbackground="#C4613A", selectforeground="#FAFAF8",
            highlightthickness=0, spacing1=3, spacing3=3,
        )
        sb = ttk.Scrollbar(parent, orient="vertical", command=text_w.yview,
                            style="Mote.Vertical.TScrollbar")
        text_w.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        text_w.pack(fill="both", expand=True)

        text_w.tag_configure("h1", font=("Georgia", 26), foreground="#1A1A18",
                             spacing1=28, spacing3=14)
        text_w.tag_configure("h1_bull", font=("Georgia", 26), foreground="#2D7A4F",
                             spacing1=28, spacing3=14)
        text_w.tag_configure("h1_bear", font=("Georgia", 26), foreground="#B33B2E",
                             spacing1=28, spacing3=14)
        text_w.tag_configure("h1_synth", font=("Georgia", 26), foreground="#9A6B1E",
                             spacing1=28, spacing3=14)
        text_w.tag_configure("h2", font=("Georgia", 20), foreground="#1A1A18",
                             spacing1=24, spacing3=12)
        text_w.tag_configure("h3", font=("Segoe UI", 11, "bold"), foreground="#8A8880",
                             spacing1=18, spacing3=8)
        text_w.tag_configure("bold", font=("Segoe UI", 11, "bold"), foreground="#1A1A18")
        text_w.tag_configure("body", font=("Segoe UI", 11), foreground="#1A1A18",
                             spacing1=2, spacing3=2, lmargin1=4, lmargin2=4)
        text_w.tag_configure("meta", font=("Segoe UI", 9, "italic"), foreground="#B0ADA6")
        text_w.tag_configure("hr", foreground="#E5E2DC", font=("Segoe UI", 4),
                             spacing1=20, spacing3=20)
        text_w.tag_configure("li", font=("Segoe UI", 11), foreground="#1A1A18",
                             lmargin1=24, lmargin2=36, spacing1=2, spacing3=2)
        text_w.tag_configure("li_marker", font=("Segoe UI", 11), foreground="#B0ADA6")
        text_w.tag_configure("num", font=("Segoe UI", 11, "bold"), foreground="#C4613A")

        for line in markdown_text.splitlines():
            stripped = line.strip()
            if stripped in ("---", "***"):
                text_w.insert("end", "─" * 64 + "\n", "hr")
            elif stripped.startswith("# ") and not stripped.startswith("## "):
                heading = stripped[2:]
                if "BULL" in heading.upper(): tag = "h1_bull"
                elif "BEAR" in heading.upper(): tag = "h1_bear"
                elif "SYNTHESIS" in heading.upper() or "DECISION" in heading.upper(): tag = "h1_synth"
                else: tag = "h1"
                text_w.insert("end", heading + "\n", tag)
            elif stripped.startswith("### "):
                text_w.insert("end", stripped[4:] + "\n", "h3")
            elif stripped.startswith("## "):
                text_w.insert("end", stripped[3:] + "\n", "h2")
            elif stripped.startswith("*") and stripped.endswith("*") and len(stripped) > 2 and "**" not in stripped:
                text_w.insert("end", stripped.strip("*") + "\n", "meta")
            elif stripped.startswith("- ") or stripped.startswith("* "):
                text_w.insert("end", "  — ", "li_marker")
                self._insert_bold(text_w, stripped[2:] + "\n", "li")
            elif re.match(r'^\d+\.\s', stripped):
                m = re.match(r'^(\d+\.)\s+(.*)', stripped)
                text_w.insert("end", f"  {m.group(1)} ", "num")
                self._insert_bold(text_w, m.group(2) + "\n", "body")
            elif not stripped:
                text_w.insert("end", "\n")
            else:
                self._insert_bold(text_w, stripped + "\n", "body")

        text_w.configure(state="disabled")

    def _insert_bold(self, widget, text, base_tag):
        parts = re.split(r'(\*\*.*?\*\*)', text)
        for part in parts:
            if part.startswith("**") and part.endswith("**"):
                widget.insert("end", part[2:-2], "bold")
            else:
                widget.insert("end", part, base_tag)

    # ── LOGGING ─────────────────────────────────────────

    def _log(self, message):
        def _append():
            self.log_text.configure(state="normal")
            self.log_text.insert("end", message + "\n")
            self.log_text.see("end")
            self.log_text.configure(state="disabled")
        self.root.after(0, _append)

    def _set_status(self, text, color=GREEN):
        self.root.after(0, lambda: self.status_label.configure(text=text, fg=color))

    def _set_running(self, running):
        self._running = running
        def _update():
            if running:
                self.go_btn.configure(state="disabled", bg=BORDER, fg=TEXT_DIM,
                                      text="Running...")
                self.stop_btn.pack(side="left", padx=(10, 0))
                self.add_btn.configure(state="normal", fg=ACCENT)
                self.clear_queue_btn.configure(state="normal", fg=TEXT_DIM)
            else:
                self.go_btn.configure(state="normal", bg=ACCENT, fg="#FFFFFF",
                                      text="Run All")
                self.stop_btn.pack_forget()
                self.add_btn.configure(state="normal", fg=ACCENT)
                self.clear_queue_btn.configure(state="normal", fg=TEXT_DIM)
                self._stop_flag = False
        self.root.after(0, _update)

    def _on_stop(self):
        if self._running:
            self._stop_flag = True
            self._set_status("Stopping...", ORANGE)
            self._log("\n⏹ Stop requested — will halt after current API call.")

    # ── WORKFLOW ────────────────────────────────────────

    def _on_go(self):
        if not self.queue_service.has_pending():
            messagebox.showwarning("Empty Queue", "Add at least one ticker to the queue first.")
            return

        if self._running:
            messagebox.showinfo("Already Running", "Queue processing is already running. You can keep adding jobs while it runs.")
            return

        if not os.environ.get("ANTHROPIC_API_KEY", ""):
            messagebox.showerror("API Key Missing",
                "Set the ANTHROPIC_API_KEY environment variable.\n\n"
                "Windows:\n  setx ANTHROPIC_API_KEY sk-ant-...\n\nThen restart this app.")
            return
        if anthropic is None:
            messagebox.showerror("Missing Package", "anthropic not installed.\nRun: py -m pip install anthropic")
            return
        if Article is None:
            messagebox.showerror("Missing Package", "newspaper3k not installed.\nRun: py -m pip install newspaper3k")
            return

        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")
        self._set_running(True)
        self._refresh_queue_display()

        threading.Thread(target=self._run_queue, daemon=True).start()

    def _run_queue(self):
        grand_cost = 0.0
        processed = 0
        self._log("Starting queue processor...\n")

        while True:
            if self._stop_flag:
                self._log("\n⏹ Stop requested — pending queued jobs were left in the queue.")
                self._set_status("Stopped", RED)
                break

            job = self.queue_service.get_next_job()
            if job is None:
                break

            processed += 1
            self.root.after(0, self._refresh_queue_display)

            ticker = job.ticker
            urls = job.urls
            model = job.model
            analysis_type = job.analysis_type
            model_short = "Opus" if "opus" in model else "Sonnet"
            if analysis_type == "earnings":
                type_label = "Earnings"
            elif analysis_type == "catalyst":
                type_label = "Catalyst"
            else:
                type_label = "Twitter Feed"

            self._set_status(f"Running {type_label.lower()} for {ticker}...", ORANGE)
            self._log(f"{'─'*40}")
            self._log(f"[{processed}] {ticker} — {type_label} ({model_short})")
            self._log(f"{'─'*40}")

            try:
                result = self.runner.run_job(job, log_fn=self._log, stop_check=lambda: self._stop_flag)
                grand_cost += result.est_cost

                self._log(f"\n✓ {ticker} complete — {result.report_path.name}")
                self._log(f"  Tokens: {result.total_in:,} in + {result.total_out:,} out (~${result.est_cost:.3f})\n")

                self.queue_service.mark_done(job.id)
                self.root.after(0, self._refresh_queue_display)
                self.root.after(0, lambda r=result.report, f=str(result.report_path.resolve()): self._show_report(r, f))

            except InterruptedError:
                self.queue_service.add_job(AnalysisJob(ticker=ticker, urls=urls, analysis_type=analysis_type, model=model, txt_path=job.txt_path))
                self.root.after(0, self._refresh_queue_display)
                break
            except Exception as e:
                if self._stop_flag:
                    self.queue_service.add_job(AnalysisJob(ticker=ticker, urls=urls, analysis_type=analysis_type, model=model, txt_path=job.txt_path))
                    self.root.after(0, self._refresh_queue_display)
                    break
                self.queue_service.mark_failed(job.id)
                self._log(f"\n✗ ERROR on {ticker}: {e}\n")
                self.root.after(0, self._refresh_queue_display)

        if not self._stop_flag:
            self._log(f"{'═'*40}")
            self._log(f"Queue complete — {processed} job(s)")
            self._log(f"Total est. cost: ~${grand_cost:.3f}")
            self._set_status(f"Done — {processed} reports", GREEN)

        self._set_running(False)

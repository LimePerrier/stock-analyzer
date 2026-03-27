"use client";

import { useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api";
import type { AnalysisItem, AnalysisType, DashboardResponse } from "@/lib/types";
import { MarkdownViewer } from "@/components/MarkdownViewer";
import { StatusBadge } from "@/components/StatusBadge";

function formatDate(value?: string) {
  if (!value) return "";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  return d.toISOString().slice(0, 16).replace("T", " ");
}

const URL_FORM_DEFAULT = {
  ticker: "",
  analysisType: "earnings" as AnalysisType,
  model: "claude-sonnet-4-5",
  urls: "",
};

const TXT_FORM_DEFAULT = {
  model: "claude-sonnet-4-5",
  file: null as File | null,
};

export function StockAnalyzerClient({
  initialData,
}: {
  initialData: DashboardResponse;
}) {
  const [analyses, setAnalyses] = useState<AnalysisItem[]>(initialData.analyses);
  const [jobs, setJobs] = useState<AnalysisItem[]>(initialData.jobs);
  const [marketRegime, setMarketRegime] = useState(initialData.market_regime);
  const [twitterPrompt, setTwitterPrompt] = useState(initialData.twitter_prompt);
  const [selectedAnalysisId, setSelectedAnalysisId] = useState<number | null>(
    initialData.analyses[0]?.id ?? null
  );
  const [selectedAnalysis, setSelectedAnalysis] = useState<AnalysisItem | null>(
    initialData.analyses[0] ?? null
  );
  const [urlForm, setUrlForm] = useState(URL_FORM_DEFAULT);
  const [txtForm, setTxtForm] = useState(TXT_FORM_DEFAULT);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [peekOpen, setPeekOpen] = useState(false);
  const [reportSearch, setReportSearch] = useState("");
  const [isRunningJob, setIsRunningJob] = useState(false);
  const [isDragOver, setIsDragOver] = useState(false);

  const sortedAnalyses = useMemo(
    () =>
      [...analyses].sort(
        (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
      ),
    [analyses]
  );

  const filteredAnalyses = useMemo(() => {
    const q = reportSearch.trim().toLowerCase();
    if (!q) return sortedAnalyses;
    return sortedAnalyses.filter((item) => {
      const haystack = `${item.ticker} ${item.title} ${item.analysis_type}`.toLowerCase();
      return haystack.includes(q);
    });
  }, [sortedAnalyses, reportSearch]);

  useEffect(() => {
    if (!selectedAnalysisId && sortedAnalyses[0]) {
      setSelectedAnalysisId(sortedAnalyses[0].id);
    }
  }, [selectedAnalysisId, sortedAnalyses]);

  useEffect(() => {
    if (!selectedAnalysisId) {
      setSelectedAnalysis(null);
      return;
    }
    void loadAnalysis(selectedAnalysisId);
  }, [selectedAnalysisId]);

  async function refreshDashboard() {
    const data = await api.dashboard();
    setAnalyses(data.analyses);
    setJobs(data.jobs);
    setMarketRegime(data.market_regime);
    setTwitterPrompt(data.twitter_prompt);
    if (!selectedAnalysisId && data.analyses[0]) {
      setSelectedAnalysisId(data.analyses[0].id);
    }
  }

  async function loadAnalysis(id: number) {
    const data = await api.getAnalysis(id);
    setSelectedAnalysis(data);
  }

  async function handleQueueUrlJob() {
    setBusy(true);
    setError(null);
    try {
      const created = await api.queueUrlJob({
        ticker: urlForm.ticker.trim().toUpperCase(),
        analysis_type:
          urlForm.analysisType === "twitter_feed"
            ? "earnings"
            : (urlForm.analysisType as "earnings" | "catalyst"),
        urls: urlForm.urls
          .split(/\n+/)
          .map((x) => x.trim())
          .filter(Boolean),
        model: urlForm.model,
      });
      setUrlForm(URL_FORM_DEFAULT);
      await refreshDashboard();
      setSelectedAnalysisId(created.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not queue URL job.");
    } finally {
      setBusy(false);
    }
  }

  async function handleQueueTextJob() {
    if (!txtForm.file) return;
    setBusy(true);
    setError(null);
    try {
      const created = await api.queueTextJob({
        ticker: "",
        model: txtForm.model,
        file: txtForm.file,
      });
      setTxtForm(TXT_FORM_DEFAULT);
      await refreshDashboard();
      setSelectedAnalysisId(created.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not queue text job.");
    } finally {
      setBusy(false);
    }
  }

  async function handleRunNext() {
    setBusy(true);
    setIsRunningJob(true);
    setError(null);
    try {
      const result = await api.runNext();
      await refreshDashboard();
      if ("id" in result) {
        setSelectedAnalysisId(result.id);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not run next job.");
    } finally {
      setBusy(false);
      setIsRunningJob(false);
    }
  }

  async function handleSaveRegime() {
    setBusy(true);
    setError(null);
    try {
      await api.saveMarketRegime(marketRegime);
      await refreshDashboard();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save market regime.");
    } finally {
      setBusy(false);
    }
  }

  async function handleSaveTwitterPrompt() {
    setBusy(true);
    setError(null);
    try {
      await api.saveTwitterPrompt(twitterPrompt);
      await refreshDashboard();
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Could not save twitter prompt."
      );
    } finally {
      setBusy(false);
    }
  }


  function handleTxtDrop(e: any) {
    e.preventDefault();
    setIsDragOver(false);
    const file = e.dataTransfer?.files?.[0];
    if (file && String(file.name).toLowerCase().endsWith(".txt")) {
      setTxtForm((p) => ({ ...p, file }));
      setError(null);
    } else if (file) {
      setError("Please drop a .txt file.");
    }
  }

  function handleTxtDragOver(e: any) {
    e.preventDefault();
    setIsDragOver(true);
  }

  function handleTxtDragLeave(e: any) {
    e.preventDefault();
    setIsDragOver(false);
  }

  return (
    <div className="page-shell app-layout">
      <aside className="panel reports-sidebar">
        <div className="sidebar-topbar">
          <button
            className="sidebar-collapse-btn"
            type="button"
            aria-label="Collapse sidebar"
          >
            <span className="chevron-double">«</span>
          </button>
          <div className="sidebar-title">Reports</div>
        </div>

        <div className="sidebar-search-wrap">
          <input
            className="sidebar-search"
            placeholder="Search..."
            value={reportSearch}
            onChange={(e) => setReportSearch(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Escape") setReportSearch("");
            }}
          />
          <span className="sidebar-search-icon">⌕</span>
          {reportSearch && (
            <button
              className="sidebar-search-clear"
              type="button"
              onClick={() => setReportSearch("")}
              aria-label="Clear search"
            >
              ✕
            </button>
          )}
        </div>

        <div className="reports-list">
          {filteredAnalyses.length === 0 ? (
            <div className="empty-list padded">
              {reportSearch ? "No matches" : "No analyses yet"}
            </div>
          ) : (
            filteredAnalyses.map((item) => (
              <button
                key={item.id}
                className={`ticker-card ${
                  selectedAnalysisId === item.id ? "active" : ""
                }`}
                onClick={() => setSelectedAnalysisId(item.id)}
              >
                <div className="ticker-top">
                  <span className="ticker-symbol">{item.ticker}</span>
                  <StatusBadge status={item.status} />
                </div>
                <div className="ticker-title">{item.title.replace(item.ticker, "").trim()}</div>
                <div className="ticker-meta">
                  {item.analysis_type} • {formatDate(item.created_at)}
                </div>
              </button>
            ))
          )}
        </div>
      </aside>

      <header className="panel top-toolbar">
        <div className="toolbar-row">
          <div className="toolbar-run-inline">
            <button className="run-btn" disabled={busy} onClick={handleRunNext}>
              {isRunningJob ? "Running..." : "Run"}
            </button>
            <div className="run-status-wrap">
              <div className={`run-status-dot ${isRunningJob ? "active" : ""}`} />
              <div className="tiny-note">
                {isRunningJob ? "Processing job..." : `${jobs.length} pending`}
              </div>
            </div>
            <button className="stop-btn" type="button" disabled title="Needs backend stop endpoint">
              Stop
            </button>
          </div>

          <div className="toolbar-card form-card">
            <div className="label">Queue URL analysis</div>
            <input
              className="field mono"
              placeholder="Ticker"
              value={urlForm.ticker}
              onChange={(e) =>
                setUrlForm((p) => ({ ...p, ticker: e.target.value }))
              }
            />
            <select
              className="select"
              value={urlForm.analysisType}
              onChange={(e) =>
                setUrlForm((p) => ({
                  ...p,
                  analysisType: e.target.value as AnalysisType,
                }))
              }
            >
              <option value="earnings">Earnings</option>
              <option value="catalyst">Catalyst</option>
            </select>
            <input
              className="field"
              placeholder="Model"
              value={urlForm.model}
              onChange={(e) => setUrlForm((p) => ({ ...p, model: e.target.value }))}
            />
            <textarea
              className="textarea mono compact-area"
              placeholder="One URL per line"
              value={urlForm.urls}
              onChange={(e) => setUrlForm((p) => ({ ...p, urls: e.target.value }))}
            />
            <button className="ghost-btn queue-btn" disabled={busy} onClick={handleQueueUrlJob}>
              Add to queue
            </button>
          </div>

          <div className="toolbar-card form-card">
            <div className="label">Queue Twitter .txt analysis</div>
            <input
              className="field"
              placeholder="Model"
              value={txtForm.model}
              onChange={(e) => setTxtForm((p) => ({ ...p, model: e.target.value }))}
            />
            <div
              className={`drop-zone ${isDragOver ? "drag-over" : ""} ${txtForm.file ? "has-file" : ""}`}
              onDrop={handleTxtDrop}
              onDragOver={handleTxtDragOver}
              onDragLeave={handleTxtDragLeave}
            >
              <div className="drop-zone-copy">
                <div className="drop-zone-title">
                  {txtForm.file ? txtForm.file.name : "Drag and drop a .txt file"}
                </div>
                <div className="drop-zone-subtitle">
                  {txtForm.file ? "Ready to queue" : "Drop file here or click to browse"}
                </div>
              </div>
              <input
                className="drop-zone-input"
                type="file"
                accept=".txt"
                onChange={(e) =>
                  setTxtForm((p) => ({ ...p, file: e.target.files?.[0] || null }))
                }
              />
            </div>
            <button
              className="ghost-btn queue-btn"
              disabled={busy || !txtForm.file}
              onClick={handleQueueTextJob}
            >
              Add to queue
            </button>
          </div>

          <div className="toolbar-settings">
            <details className="settings-toggle">
              <summary>Market regime</summary>
              <div className="settings-body stack">
                <textarea
                  className="textarea tall"
                  value={marketRegime}
                  onChange={(e) => setMarketRegime(e.target.value)}
                />
                <button
                  className="ghost-btn"
                  disabled={busy}
                  onClick={handleSaveRegime}
                >
                  Save regime
                </button>
              </div>
            </details>

            <details className="settings-toggle">
              <summary>Twitter feed prompt</summary>
              <div className="settings-body stack">
                <textarea
                  className="textarea tall"
                  value={twitterPrompt}
                  onChange={(e) => setTwitterPrompt(e.target.value)}
                />
                <button
                  className="ghost-btn"
                  disabled={busy}
                  onClick={handleSaveTwitterPrompt}
                >
                  Save twitter prompt
                </button>
              </div>
            </details>
          </div>
        </div>
      </header>

      <main className="panel main report-viewer-panel">
        <div className="topbar">
          <div>
            <div className="viewer-title">
              {selectedAnalysis?.title || "Select a report"}
            </div>
            <div className="viewer-subtitle">
              {selectedAnalysis
                ? selectedAnalysis.analysis_type
                : "Choose a previous report from the left."}
            </div>
          </div>
          {selectedAnalysis && <StatusBadge status={selectedAnalysis.status} />}
        </div>

        {error && <div className="error-banner">{error}</div>}

        {selectedAnalysis ? (
          <div className="viewer-card">
            <div className="viewer-head">
              <div className="stat-grid">
                <div className="stat-card">
                  <div className="label">Input tokens</div>
                  <div className="stat-value mono">
                    {selectedAnalysis.token_input?.toLocaleString() || 0}
                  </div>
                </div>
                <div className="stat-card">
                  <div className="label">Output tokens</div>
                  <div className="stat-value mono">
                    {selectedAnalysis.token_output?.toLocaleString() || 0}
                  </div>
                </div>
                <div className="stat-card">
                  <div className="label">Est. cost</div>
                  <div className="stat-value mono">
                    ${(selectedAnalysis.estimated_cost || 0).toFixed(4)}
                  </div>
                </div>
              </div>
            </div>

            <div className="viewer-body">
              {selectedAnalysis.status === "completed" &&
              selectedAnalysis.report_markdown ? (
                <MarkdownViewer content={selectedAnalysis.report_markdown} />
              ) : selectedAnalysis.status === "failed" ? (
                <div className="empty-state">
                  This analysis failed:{" "}
                  {selectedAnalysis.error_message || "Unknown error."}
                </div>
              ) : (
                <div className="empty-state">
                  This report is {selectedAnalysis.status}. Click Run next to process
                  it.
                </div>
              )}
            </div>
          </div>
        ) : (
          <div className="empty-state">No report selected yet.</div>
        )}
      </main>

      <aside className={`panel peek-panel ${peekOpen ? "open" : "collapsed"}`}>
        <div className="peek-inner">
          <div className="peek-resize-handle" />
          <div className="peek-header">
            <button
              className="peek-toggle"
              type="button"
              onClick={() => setPeekOpen((v) => !v)}
              aria-label={peekOpen ? "Collapse peek" : "Expand peek"}
            >
              <span className="chevron-double">{peekOpen ? "»" : "«"}</span>
            </button>
            {peekOpen && (
              <div className="peek-header-copy">
                <div className="peek-title">Peek</div>
                <div className="peek-subtitle">Chat will live here later</div>
              </div>
            )}
          </div>

          {peekOpen && (
            <div className="peek-body">
              <div className="empty-state">
                This panel is reserved for the future chat / follow-up workflow.
              </div>
            </div>
          )}
        </div>
      </aside>
    </div>
  );
}

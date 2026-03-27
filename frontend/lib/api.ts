import type { AnalysisItem, DashboardResponse } from "@/lib/types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      ...(init?.body instanceof FormData ? {} : { "Content-Type": "application/json" }),
      ...(init?.headers || {}),
    },
    cache: "no-store",
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text);
  }
  return res.json();
}

export const api = {
  dashboard: () => request<DashboardResponse>("/api/dashboard"),
  queueUrlJob: (body: { ticker: string; title?: string; analysis_type: "earnings" | "catalyst"; urls: string[]; model?: string }) =>
    request<AnalysisItem>("/api/jobs/url", { method: "POST", body: JSON.stringify(body) }),
  queueTextJob: async (input: { ticker: string; title?: string; model?: string; file: File }) => {
    const form = new FormData();
    form.append("ticker", input.ticker);
    if (input.title) form.append("title", input.title);
    if (input.model) form.append("model", input.model);
    form.append("file", input.file);
    return request<AnalysisItem>("/api/jobs/text", { method: "POST", body: form });
  },
  runNext: () => request<AnalysisItem | { message: string }>("/api/jobs/run-next", { method: "POST" }),
  getAnalysis: (analysisId: number) => request<AnalysisItem>(`/api/analyses/${analysisId}`),
  saveMarketRegime: (content: string) => request<{ content: string }>("/api/market-regime", { method: "PUT", body: JSON.stringify({ content }) }),
  saveTwitterPrompt: (content: string) => request<{ content: string }>("/api/twitter-prompt", { method: "PUT", body: JSON.stringify({ content }) }),
};

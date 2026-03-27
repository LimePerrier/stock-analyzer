export type AnalysisStatus = "queued" | "running" | "completed" | "failed";
export type AnalysisType = "earnings" | "catalyst" | "twitter_feed";

export interface AnalysisItem {
  id: number;
  ticker: string;
  title: string;
  analysis_type: AnalysisType;
  model: string;
  urls: string[];
  txt_path: string;
  status: AnalysisStatus;
  created_at: string;
  started_at?: string | null;
  completed_at?: string | null;
  article_text_path?: string;
  report_path?: string;
  report_markdown?: string;
  token_input?: number;
  token_output?: number;
  estimated_cost?: number;
  error_message?: string;
}

export interface TickerSummary {
  ticker: string;
  latest_analysis_id: number;
  latest_title: string;
  status: AnalysisStatus;
  updated_at: string;
}

export interface DashboardResponse {
  tickers: TickerSummary[];
  analyses: AnalysisItem[];
  jobs: AnalysisItem[];
  market_regime: string;
  twitter_prompt: string;
}

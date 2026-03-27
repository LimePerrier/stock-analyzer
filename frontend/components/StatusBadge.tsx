import type { AnalysisStatus } from "@/lib/types";

export function StatusBadge({ status }: { status: AnalysisStatus }) {
  return <span className={`status-badge ${status}`}>{status}</span>;
}

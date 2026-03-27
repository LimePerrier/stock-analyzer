import { api } from "@/lib/api";
import { StockAnalyzerClient } from "@/components/StockAnalyzerClient";

export default async function HomePage() {
  const initialData = await api.dashboard();
  return <StockAnalyzerClient initialData={initialData} />;
}

"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { StockAnalyzerClient } from "@/components/StockAnalyzerClient";
import type { DashboardResponse } from "@/lib/types";

export default function HomePage() {
  const [data, setData] = useState<DashboardResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.dashboard()
      .then(setData)
      .catch((err) => setError(err.message || "Failed to load dashboard"));
  }, []);

  if (error) {
    return (
      <div style={{ padding: "2rem", textAlign: "center" }}>
        <h2>Could not connect to backend</h2>
        <p>{error}</p>
      </div>
    );
  }

  if (!data) {
    return (
      <div style={{ padding: "2rem", textAlign: "center" }}>
        Loading...
      </div>
    );
  }

  return <StockAnalyzerClient initialData={data} />;
}
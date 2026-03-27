import "./globals.css";
import type { ReactNode } from "react";

export const metadata = {
  title: "Stock Analyzer Web",
  description: "ThoughtStream-style UI for the stock analyzer engine",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}

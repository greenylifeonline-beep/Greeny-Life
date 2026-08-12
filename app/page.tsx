"use client";

import { useEffect, useState } from "react";

type Result = { success: boolean; count?: number; error?: string };

const endpoints = [
  ["Products", "/api/products"],
  ["Suppliers", "/api/suppliers"],
  ["Sales Orders", "/api/sales-orders"],
] as const;

export default function HomePage() {
  const [counts, setCounts] = useState<Record<string, number>>({});
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all(
      endpoints.map(async ([label, endpoint]) => {
        const response = await fetch(endpoint, { cache: "no-store" });
        const result = (await response.json()) as Result;
        if (!response.ok || !result.success) throw new Error(result.error || "API unavailable");
        return [label, result.count ?? 0] as const;
      })
    )
      .then((items) => setCounts(Object.fromEntries(items)))
      .catch((reason: Error) => setError(reason.message));
  }, []);

  return (
    <main style={{ maxWidth: 1000, margin: "0 auto", padding: "56px 24px" }}>
      <p style={{ color: "#3f7d4b", fontWeight: 700, letterSpacing: 1.5 }}>GREENY LIFE</p>
      <h1 style={{ fontSize: 38 }}>Digital Operating System</h1>
      <p style={{ color: "#58705f" }}>Live development environment connected to PostgreSQL.</p>

      <section style={{ display: "flex", gap: 16, flexWrap: "wrap", marginTop: 32 }}>
        {endpoints.map(([label, endpoint]) => (
          <article key={endpoint} style={{ background: "#fff", border: "1px solid #dce6dd", borderRadius: 12, padding: 22, minWidth: 210 }}>
            <p style={{ color: "#58705f", margin: 0 }}>{label}</p>
            <p style={{ fontSize: 38, fontWeight: 700, margin: "10px 0" }}>{error ? "—" : (counts[label] ?? "…")}</p>
            <code style={{ color: "#3f7d4b" }}>{endpoint}</code>
          </article>
        ))}
      </section>

      <section style={{ background: "#fff", border: "1px solid #dce6dd", borderRadius: 12, padding: 22, marginTop: 24 }}>
        <h2>Execution truth</h2>
        <p>{error || "Application, API routes, Prisma, and PostgreSQL are live. Zero counts mean approved operational data has not been loaded yet."}</p>
      </section>
    </main>
  );
}
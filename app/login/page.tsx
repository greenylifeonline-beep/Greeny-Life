"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("admin@greeny-life.local");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    fetch("/api/auth/session", { cache: "no-store" })
      .then((response) => response.ok ? response.json() : null)
      .then((result) => { if (result?.authenticated === true) router.replace("/data-control"); })
      .catch(() => undefined);
  }, [router]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setSubmitting(true); setError("");
    try {
      const response = await fetch("/api/auth/login", {
        method: "POST", headers: { "content-type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
      const result = await response.json() as { success?: boolean; error?: string };
      if (!response.ok || !result.success) { setError(result.error || "Sign-in failed."); return; }
      router.replace("/data-control"); router.refresh();
    } catch { setError("The sign-in service is unavailable."); }
    finally { setSubmitting(false); }
  }

  return <main style={{ minHeight: "100vh", display: "grid", placeItems: "center", padding: 24, fontFamily: "Arial, sans-serif", background: "#f5faf5", color: "#18371e" }}>
    <form onSubmit={submit} style={{ width: "min(100%, 420px)", background: "white", padding: 30, border: "1px solid #d6e5d8", borderRadius: 16, boxShadow: "0 8px 30px #18371e14" }}>
      <p style={{ margin: 0, color: "#3f7d4b", fontWeight: 700, letterSpacing: 1.2 }}>GREENY LIFE</p>
      <h1 style={{ margin: "10px 0" }}>Sign in</h1>
      <p style={{ color: "#58705f" }}>Use your authorized account to access commercial data and controlled changes.</p>
      <label style={{ display: "grid", gap: 6, marginTop: 20 }}>Email
        <input required type="email" value={email} onChange={(event) => setEmail(event.target.value)} style={{ padding: 11, border: "1px solid #9ebaa2", borderRadius: 8 }} />
      </label>
      <label style={{ display: "grid", gap: 6, marginTop: 14 }}>Password
        <input required type="password" value={password} onChange={(event) => setPassword(event.target.value)} style={{ padding: 11, border: "1px solid #9ebaa2", borderRadius: 8 }} />
      </label>
      {error && <p role="alert" style={{ color: "#b42318" }}>{error}</p>}
      <button disabled={submitting} type="submit" style={{ width: "100%", marginTop: 22, padding: 12, border: 0, borderRadius: 8, background: "#3f7d4b", color: "white", fontWeight: 700, cursor: "pointer" }}>{submitting ? "Signing in..." : "Sign in"}</button>
    </form>
  </main>;
}
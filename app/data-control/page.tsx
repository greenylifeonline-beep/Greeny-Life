"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";

type Row = Record<string, unknown>;
type Workspace = { products: Row[]; suppliers: Row[]; customers: Row[]; commercialChanges: Row[] };
const empty: Workspace = { products: [], suppliers: [], customers: [], commercialChanges: [] };
const tabs = ["products", "suppliers", "customers", "commercialChanges"] as const;
type Tab = typeof tabs[number];
type SupplierEditor = { id: string; supplierId: string; name: string; status: string; verificationStatus: string; sourceUrl: string; sourceReference: string; deactivationReason: string };

function csv(rows: Row[]) {
  const columns = [...new Set(rows.flatMap((row) => Object.keys(row)))];
  const quote = (value: unknown) => `"${String(value ?? "").replaceAll('"', '""')}"`;
  return [columns.join(","), ...rows.map((row) => columns.map((column) => quote(typeof row[column] === "object" ? JSON.stringify(row[column]) : row[column])).join(","))].join("\n");
}
function download(name: string, content: string, type: string) {
  const url = URL.createObjectURL(new Blob([content], { type })); const a = document.createElement("a"); a.href = url; a.download = name; a.click(); URL.revokeObjectURL(url);
}

export default function DataControlPage() {
  const [data, setData] = useState<Workspace>(empty); const [tab, setTab] = useState<Tab>("products");
  const [query, setQuery] = useState(""); const [error, setError] = useState(""); const [notice, setNotice] = useState(""); const [supplierEditor, setSupplierEditor] = useState<SupplierEditor | null>(null);
  const [form, setForm] = useState({ domain: "PRICE", subjectType: "PRODUCT", subjectId: "", changeType: "UPDATE", source: "", rationale: "", effectiveFrom: "", effectiveTo: "", payload: "{}" });
  const load = async () => { setError(""); const response = await fetch("/api/data-control", { cache: "no-store" }); const result = await response.json(); if (response.status === 401) { window.location.assign("/login?next=/data-control"); return; } if (!response.ok || !result.success) { setError(result.error || "Unable to load commercial data."); return; } setData(result.data); };
  useEffect(() => { void load(); }, []);
  const rows = data[tab] ?? []; const filtered = useMemo(() => rows.filter((row) => JSON.stringify(row).toLowerCase().includes(query.toLowerCase())), [rows, query]);
  const submit = async (event: FormEvent) => { event.preventDefault(); setNotice(""); setError(""); let payload: unknown; try { payload = JSON.parse(form.payload); } catch { setError("Payload must be valid JSON."); return; }
    const response = await fetch("/api/commercial-changes", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ ...form, payload, riskLevel: "HIGH" }) });
    const result = await response.json(); if (!response.ok || !result.success) { setError(result.error || "Proposal was rejected."); return; }
    setNotice(`Proposal recorded as ${result.data.status}. It was not silently applied.`); setForm({ ...form, source: "", rationale: "", payload: "{}" }); await load();
  };
  const beginSupplierEdit = (supplier: Row) => setSupplierEditor({ id: String(supplier.id ?? ""), supplierId: String(supplier.supplierId ?? ""), name: String(supplier.nameEn ?? supplier.nameAr ?? supplier.supplierId ?? "Supplier"), status: String(supplier.status ?? "PENDING_VERIFICATION"), verificationStatus: String(supplier.verificationStatus ?? "UNVERIFIED"), sourceUrl: String(supplier.sourceUrl ?? ""), sourceReference: String(supplier.sourceReference ?? ""), deactivationReason: String(supplier.deactivationReason ?? "") });
  const saveSupplier = async (event: FormEvent) => { event.preventDefault(); if (!supplierEditor) return; setError(""); setNotice(""); const response = await fetch("/api/suppliers", { method: "PATCH", headers: { "content-type": "application/json" }, body: JSON.stringify({ id: supplierEditor.id, status: supplierEditor.status, verificationStatus: supplierEditor.verificationStatus, sourceUrl: supplierEditor.sourceUrl || null, sourceReference: supplierEditor.sourceReference || null, deactivationReason: supplierEditor.deactivationReason || null }) }); const result = await response.json(); if (!response.ok || !result.success) { setError(result.details || result.error || "Supplier update was rejected."); return; } setNotice(`Supplier ${supplierEditor.supplierId} was updated.`); setSupplierEditor(null); await load(); };
  return <main style={{ maxWidth: 1380, margin: "0 auto", padding: "32px 20px", fontFamily: "Arial, sans-serif", color: "#18371e" }}>
    <p style={{ color: "#3f7d4b", fontWeight: 700, letterSpacing: 1.2 }}>GREENY LIFE · DATA CONTROL CENTER</p>
    <h1 style={{ marginTop: 0 }}>Commercial Data Control Center</h1>
    <p>Products, suppliers, customers, prices, shipments, and offers are editable operating data. Every material change has a source, owner, and validity period before approval. Nothing is applied silently.</p>
    <div style={{ display: "flex", gap: 8, flexWrap: "wrap", margin: "24px 0" }}>{tabs.map((item) => <button key={item} onClick={() => setTab(item)} style={{ padding: "10px 14px", borderRadius: 8, border: "1px solid #75a57b", background: tab === item ? "#3f7d4b" : "white", color: tab === item ? "white" : "#18371e" }}>{item}</button>)}</div>
    <section style={{ border: "1px solid #d6e5d8", borderRadius: 14, padding: 18, background: "#fff" }}>
      <div style={{ display: "flex", justifyContent: "space-between", gap: 16, flexWrap: "wrap" }}><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search records" style={{ padding: 10, minWidth: 260 }} /><div><button onClick={() => download(`${tab}.csv`, csv(filtered), "text/csv")}>Export CSV</button> <button onClick={() => download(`${tab}.json`, JSON.stringify(filtered, null, 2), "application/json")}>Export JSON</button></div></div>
      <p>{filtered.length} visible records out of {rows.length}</p>
      <div style={{ overflowX: "auto", maxHeight: 440 }}><table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}><thead><tr>{Object.keys(filtered[0] ?? {}).slice(0, 9).map((key) => <th key={key} style={{ textAlign: "left", padding: 9, borderBottom: "1px solid #ddd" }}>{key}</th>)}{tab === "suppliers" && <th style={{ textAlign: "left", padding: 9, borderBottom: "1px solid #ddd" }}>actions</th>}</tr></thead><tbody>{filtered.slice(0, 100).map((row, index) => <tr key={String(row.id ?? index)}>{Object.keys(filtered[0] ?? {}).slice(0, 9).map((key) => <td key={key} style={{ padding: 9, borderBottom: "1px solid #eee", verticalAlign: "top" }}>{typeof row[key] === "object" ? JSON.stringify(row[key]) : String(row[key] ?? "")}</td>)}{tab === "suppliers" && <td style={{ padding: 9, borderBottom: "1px solid #eee" }}><button type="button" onClick={() => beginSupplierEdit(row)}>Review / edit</button></td>}</tr>)}</tbody></table></div>
    </section>
    {supplierEditor && <section style={{ marginTop: 24, border: "1px solid #d6e5d8", borderRadius: 14, padding: 18, background: "#f8fcf8" }}><h2>Supplier verification: {supplierEditor.name}</h2><p>Activation requires verified evidence and a source. Deactivation keeps the supplier history and linked products.</p><form onSubmit={saveSupplier} style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(230px, 1fr))", gap: 12 }}><label>Operating status<select value={supplierEditor.status} onChange={(event) => setSupplierEditor({ ...supplierEditor, status: event.target.value })}>{["PENDING_VERIFICATION", "ACTIVE", "INACTIVE", "REJECTED"].map((value) => <option key={value}>{value}</option>)}</select></label><label>Verification status<select value={supplierEditor.verificationStatus} onChange={(event) => setSupplierEditor({ ...supplierEditor, verificationStatus: event.target.value })}>{["UNVERIFIED", "VERIFIED", "EXPIRED", "REJECTED"].map((value) => <option key={value}>{value}</option>)}</select></label><label>Evidence URL<input type="url" value={supplierEditor.sourceUrl} onChange={(event) => setSupplierEditor({ ...supplierEditor, sourceUrl: event.target.value })} placeholder="https://…" /></label><label>Evidence reference<input value={supplierEditor.sourceReference} onChange={(event) => setSupplierEditor({ ...supplierEditor, sourceReference: event.target.value })} placeholder="Audit, certificate, or registry reference" /></label>{supplierEditor.status === "INACTIVE" && <label style={{ gridColumn: "1 / -1" }}>Deactivation reason<textarea required value={supplierEditor.deactivationReason} onChange={(event) => setSupplierEditor({ ...supplierEditor, deactivationReason: event.target.value })} /></label>}<div style={{ display: "flex", gap: 10 }}><button type="submit" style={{ padding: 12, background: "#3f7d4b", color: "white", border: 0, borderRadius: 8 }}>Save controlled update</button><button type="button" onClick={() => setSupplierEditor(null)}>Cancel</button></div></form></section>}
    <section style={{ marginTop: 24, border: "1px solid #d6e5d8", borderRadius: 14, padding: 18, background: "#f8fcf8" }}>
      <h2>Propose an addition or change</h2><p>For authorized administration only. This form never executes a shipment, payment, or customs clearance.</p>
      <form onSubmit={submit} style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(210px, 1fr))", gap: 12 }}>
        {(["domain", "subjectType", "subjectId", "changeType", "source", "effectiveFrom", "effectiveTo"] as const).map((field) => <label key={field}>{field}<input required={["domain", "subjectType", "subjectId", "changeType", "source"].includes(field)} value={form[field]} onChange={(event) => setForm({ ...form, [field]: event.target.value })} placeholder={field.includes("effective") ? "2026-12-31" : ""} /></label>)}
        <label style={{ gridColumn: "1 / -1" }}>rationale<textarea value={form.rationale} onChange={(event) => setForm({ ...form, rationale: event.target.value })} /></label>
        <label style={{ gridColumn: "1 / -1" }}>payload JSON<textarea value={form.payload} onChange={(event) => setForm({ ...form, payload: event.target.value })} style={{ minHeight: 110, fontFamily: "monospace" }} /></label>
        <button type="submit" style={{ padding: 12, background: "#3f7d4b", color: "white", border: 0, borderRadius: 8 }}>Send for review</button>
      </form>{notice && <p style={{ color: "#16712a" }}>{notice}</p>}{error && <p style={{ color: "#b42318" }}>{error}</p>}
    </section>
  </main>;
}

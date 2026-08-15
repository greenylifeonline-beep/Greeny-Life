import { NextResponse } from "next/server";

/** Shared, strict request-input helpers for Current API routes. */
export const hasText = (value: unknown): value is string => typeof value === "string" && value.trim().length > 0;

export const finiteNumber = (value: unknown): number | null => {
  if (typeof value === "number" && Number.isFinite(value)) return value;
  if (typeof value === "string" && value.trim() !== "" && Number.isFinite(Number(value))) return Number(value);
  return null;
};

export const invalidRequest = (error: string) => NextResponse.json({ success: false, error }, { status: 400 });
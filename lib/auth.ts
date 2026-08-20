import crypto from "node:crypto";
import { NextRequest, NextResponse } from "next/server";

export const roles = ["ADMIN", "EXPORT", "WAREHOUSE", "SALES", "FINANCE", "VIEWER"] as const;
export type AppRole = typeof roles[number];
export type Session = { userId: string; email: string; role: AppRole; expiresAt: number };

const cookieName = "gl_session";
const hashIterations = 310_000;
const sessionHours = 8;

function secret() {
  const value = process.env.APP_SESSION_SECRET;
  if (!value || value.length < 32) throw new Error("APP_SESSION_SECRET must be set to at least 32 characters.");
  return value;
}
function base64url(value: string | Buffer) { return Buffer.from(value).toString("base64url"); }
function unbase64url(value: string) { return Buffer.from(value, "base64url"); }
function signature(payload: string) { return crypto.createHmac("sha256", secret()).update(payload).digest("base64url"); }
function timingSafeEqual(left: string, right: string) { const a = Buffer.from(left); const b = Buffer.from(right); return a.length === b.length && crypto.timingSafeEqual(a, b); }

export function hashPassword(password: string) {
  if (password.length < 14) throw new Error("Password must be at least 14 characters.");
  const salt = crypto.randomBytes(16);
  const hash = crypto.pbkdf2Sync(password, salt, hashIterations, 32, "sha256");
  return `pbkdf2$sha256$${hashIterations}$${base64url(salt)}$${base64url(hash)}`;
}
export function verifyPassword(password: string, encoded: string) {
  const [scheme, digest, rounds, salt, expected] = encoded.split("$");
  if (scheme !== "pbkdf2" || digest !== "sha256" || !rounds || !salt || !expected) return false;
  const derived = crypto.pbkdf2Sync(password, unbase64url(salt), Number(rounds), 32, "sha256");
  return timingSafeEqual(base64url(derived), expected);
}
export function createSession(input: Omit<Session, "expiresAt">) {
  const session: Session = { ...input, expiresAt: Date.now() + sessionHours * 60 * 60 * 1000 };
  const payload = base64url(JSON.stringify(session));
  return `${payload}.${signature(payload)}`;
}
export function readSession(token?: string): Session | null {
  if (!token) return null;
  const [payload, provided] = token.split(".");
  if (!payload || !provided || !timingSafeEqual(signature(payload), provided)) return null;
  try {
    const parsed = JSON.parse(unbase64url(payload).toString("utf8")) as Session;
    return roles.includes(parsed.role) && parsed.expiresAt > Date.now() ? parsed : null;
  } catch { return null; }
}
export function cookieShouldBeSecure(input?: { protocol?: string | null; forwardedProto?: string | null }) {
  const forwarded = String(input?.forwardedProto || "").split(",")[0].trim().toLowerCase();
  if (forwarded === "https") return true;
  if (forwarded === "http") return false;
  const protocol = String(input?.protocol || "").toLowerCase();
  if (protocol === "https:" || protocol === "https") return true;
  if (protocol === "http:" || protocol === "http") return false;
  return process.env.NODE_ENV === "production";
}
export function sessionCookieSecure(request: NextRequest) {
  return cookieShouldBeSecure({
    protocol: request.nextUrl.protocol,
    forwardedProto: request.headers.get("x-forwarded-proto"),
  });
}
function sessionCookieOptions(request: NextRequest, maxAge: number) {
  return { httpOnly: true, secure: sessionCookieSecure(request), sameSite: "lax" as const, path: "/", maxAge };
}
export function setSessionCookie(response: NextResponse, token: string, request: NextRequest) {
  response.cookies.set(cookieName, token, sessionCookieOptions(request, sessionHours * 60 * 60));
}
export function clearSessionCookie(response: NextResponse, request: NextRequest) {
  response.cookies.set(cookieName, "", sessionCookieOptions(request, 0));
}
export function requireRole(request: NextRequest, allowed: readonly AppRole[]) {
  const session = readSession(request.cookies.get(cookieName)?.value);
  if (!session) return { session: null, response: NextResponse.json({ success: false, error: "Authentication required." }, { status: 401 }) };
  if (!allowed.includes(session.role)) return { session, response: NextResponse.json({ success: false, error: "Insufficient role." }, { status: 403 }) };
  return { session, response: null };
}
export const authCookieName = cookieName;
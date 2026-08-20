import { NextRequest, NextResponse } from "next/server";
import { createSession, setSessionCookie, verifyPassword } from "@/lib/auth";
import { prisma } from "@/lib/prisma";

export async function POST(request: NextRequest) {
  try {
    const body = await request.json() as Record<string, unknown>;
    const email = typeof body.email === "string" ? body.email.trim().toLowerCase() : "";
    const password = typeof body.password === "string" ? body.password : "";
    if (!email || !password) return NextResponse.json({ success: false, error: "Email and password are required." }, { status: 400 });
    const user = await prisma.user.findUnique({ where: { email } });
    if (!user || !user.passwordHash || !verifyPassword(password, user.passwordHash)) return NextResponse.json({ success: false, error: "Invalid credentials." }, { status: 401 });
    const token = createSession({ userId: user.id, email: user.email, role: user.role as import("@/lib/auth").AppRole });
    const response = NextResponse.json({ success: true, user: { id: user.id, email: user.email, name: user.name, role: user.role } });
    setSessionCookie(response, token, request);
    return response;
  } catch (error) { return NextResponse.json({ success: false, error: "Login unavailable", details: (error as Error).message }, { status: 503 }); }
}
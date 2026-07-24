import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

export function middleware(request: NextRequest) {
  const token = request.headers.get("authorization") || request.cookies.get("next-auth.session-token");
  const path = request.nextUrl.pathname;

  // حماية مسارات الـ API الإدارية وسير العمل
  if (path.startsWith("/api/workflow") || path.startsWith("/api/sales-orders")) {
    if (!token) {
      return NextResponse.json(
        { success: false, error: "Unauthorized access. Authentication token missing." },
        { status: 401 }
      );
    }
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/api/workflow/:path*", "/api/sales-orders/:path*"],
};

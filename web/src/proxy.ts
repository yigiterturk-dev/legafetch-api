import { NextResponse, type NextRequest } from "next/server";
import { verifySessionToken } from "@/lib/session";

// Uygulama sayfalarını korur: imzalı oturum cookie'si yoksa /login'e yönlendirir.
const PROTECTED = ["/", "/admin", "/api/proxy"];

export async function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const needsAuth = PROTECTED.some((p) => pathname === p || pathname.startsWith(p + "/"));
  if (!needsAuth) return NextResponse.next();

  if (await verifySessionToken(request.cookies.get("insure_session")?.value)) {
    return NextResponse.next();
  }
  return NextResponse.redirect(new URL("/login", request.url));
}

export const config = {
  matcher: ["/", "/admin/:path*", "/api/proxy/:path*"],
};

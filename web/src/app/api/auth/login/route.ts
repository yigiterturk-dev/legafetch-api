import { NextRequest, NextResponse } from "next/server";
import { BACKEND, getApiKey } from "@/lib/backend";
import { createSessionToken } from "@/lib/session";

export async function POST(req: NextRequest) {
  const { license } = await req.json().catch(() => ({}) as { license?: string });
  if (!license) return NextResponse.json({ ok: false }, { status: 401 });

  let r: Response;
  try {
    r = await fetch(`${BACKEND}/api/auth/verify`, {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-API-Key": getApiKey() },
      body: JSON.stringify({ license_key: license }),
      cache: "no-store",
    });
  } catch {
    return NextResponse.json(
      { ok: false, detail: "Kimlik servisine erisilemedi." },
      { status: 502 }
    );
  }
  if (!r.ok) return NextResponse.json({ ok: false }, { status: 401 });

  const res = NextResponse.json({ ok: true });
  res.cookies.set("insure_session", await createSessionToken(), {
    httpOnly: true,
    sameSite: "lax",
    path: "/",
    maxAge: 7 * 24 * 3600,
    secure: process.env.COOKIE_SECURE === "1",
  });
  return res;
}

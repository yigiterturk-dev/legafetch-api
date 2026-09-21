import { NextRequest, NextResponse } from "next/server";

// Form gonderimiyle de cagrilir; JSON degil ana sayfaya yonlendirir.
export async function POST(req: NextRequest) {
  const res = NextResponse.redirect(new URL("/", req.url), 303);
  res.cookies.set("insure_session", "", { httpOnly: true, path: "/", maxAge: 0 });
  return res;
}

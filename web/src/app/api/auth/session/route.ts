import { NextRequest, NextResponse } from "next/server";
import { verifySessionToken } from "@/lib/session";

export async function GET(req: NextRequest) {
  return NextResponse.json({
    authenticated: await verifySessionToken(req.cookies.get("insure_session")?.value),
  });
}

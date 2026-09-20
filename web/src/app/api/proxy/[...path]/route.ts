import type { NextRequest } from "next/server";

import { BACKEND, getApiKey } from "@/lib/backend";

const BACKEND_TIMEOUT_MS = 60_000;

async function fetchWithTimeout(url: string, init: RequestInit): Promise<Response> {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), BACKEND_TIMEOUT_MS);
  try {
    return await fetch(url, { ...init, signal: ctrl.signal });
  } finally {
    clearTimeout(timer);
  }
}

async function forward(req: NextRequest, path: string[]): Promise<Response> {
  const url = `${BACKEND}/api/${path.map(encodeURIComponent).join("/")}`;
  const headers = new Headers({ "X-API-Key": getApiKey() });
  const ct = req.headers.get("content-type");
  if (ct) headers.set("content-type", ct);
  // Gerçek istemci adresini API'ye taşı: aksi halde API tüm oturum sahiplerini
  // TEK bir IP (bu konteyner) sanıp hepsini aynı hız-limiti kovasına koyar —
  // bir kullanıcı kovayı doldurunca herkes 429 yer. Caddy'nin eklediği zincir
  // olduğu gibi geçirilir; API en sağdaki (güvenilen) değeri kullanır.
  const xff = req.headers.get("x-forwarded-for");
  if (xff) headers.set("x-forwarded-for", xff);

  let backendRes: Response;
  try {
    backendRes = await fetchWithTimeout(url, {
    method: req.method,
    headers,
    body: req.method === "GET" || req.method === "HEAD" ? undefined : await req.arrayBuffer(),
    cache: "no-store",
    });
  } catch {
    return Response.json(
      { detail: "AI motoruna erisilemedi; servis kapabilir." },
      { status: 502 }
    );
  }

  const buf = await backendRes.arrayBuffer();
  const outHeaders = new Headers();
  const bct = backendRes.headers.get("content-type");
  if (bct) outHeaders.set("content-type", bct);
  return new Response(buf, { status: backendRes.status, headers: outHeaders });
}

export async function GET(req: NextRequest, ctx: { params: Promise<{ path: string[] }> }) {
  const { path } = await ctx.params;
  return forward(req, path);
}

export async function POST(req: NextRequest, ctx: { params: Promise<{ path: string[] }> }) {
  const { path } = await ctx.params;
  return forward(req, path);
}

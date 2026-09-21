import type { NextRequest } from "next/server";

import { BACKEND, getApiKey } from "@/lib/backend";
import { oturumKimligi } from "@/lib/session";

const BACKEND_TIMEOUT_MS = 60_000;
// Dilekçe ve sözleşme denetimi tek çağrıda uzun metin işler: arama (~12 sn)
// + LLM (120 sn'ye kadar). 60 sn'lik sohbet sınırı bunları ortasında keser,
// kullanıcı sebepsiz bir hata görürdü.
const UZUN_UCLAR = ["dilekce", "analyze-contract"];
const UZUN_TIMEOUT_MS = 180_000;

async function fetchWithTimeout(
  url: string,
  init: RequestInit,
  timeoutMs: number = BACKEND_TIMEOUT_MS,
): Promise<Response> {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), timeoutMs);
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
  // Dosya/proje alanı kayıtları kullanıcıya bağlar. Kimlik İMZALI oturumdan
  // çıkarılır — istemcinin gönderdiği başlığa güvenilmez, o yüzden burada
  // hem okunur hem (varsa) üzerine yazılır.
  headers.delete("x-kullanici");
  const kim = await oturumKimligi(req.cookies.get("insure_session")?.value);
  if (kim) headers.set("x-kullanici", kim);

  const sure = UZUN_UCLAR.includes(path[0] ?? "") ? UZUN_TIMEOUT_MS : BACKEND_TIMEOUT_MS;
  let backendRes: Response;
  try {
    backendRes = await fetchWithTimeout(url, {
    method: req.method,
    headers,
    body: req.method === "GET" || req.method === "HEAD" ? undefined : await req.arrayBuffer(),
    cache: "no-store",
    }, sure);
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
  // Word indirmesi için dosya adı başlığı istemciye geçmeli.
  const bcd = backendRes.headers.get("content-disposition");
  if (bcd) outHeaders.set("content-disposition", bcd);
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

// DELETE unutulmustu: dosya/kayit silme ucu 405 aliyordu, arayuzdeki "sil"
// dugmesi sessizce hicbir sey yapmiyordu (tarayicidan bakilinca goruldu).
export async function DELETE(req: NextRequest, ctx: { params: Promise<{ path: string[] }> }) {
  const { path } = await ctx.params;
  return forward(req, path);
}

export async function PATCH(req: NextRequest, ctx: { params: Promise<{ path: string[] }> }) {
  const { path } = await ctx.params;
  return forward(req, path);
}

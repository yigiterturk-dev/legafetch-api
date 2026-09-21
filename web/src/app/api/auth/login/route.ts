import { NextRequest, NextResponse } from "next/server";
import { BACKEND, getApiKey } from "@/lib/backend";
import { createSessionToken } from "@/lib/session";
import { lisansDogrula, tanimliLisanslar } from "@/lib/lisans";

// Basit deneme sınırı: IP başına dakikada 10. Tek örnek çalıştığı için bellekte tutmak yeterli.
const denemeler = new Map<string, { adet: number; pencere: number }>();
const SINIR = 10;
const PENCERE_MS = 60_000;

function istemciIp(req: NextRequest): string {
  const xff = req.headers.get("x-forwarded-for");
  // Caddy gerçek adresi zincirin SONUNA ekler; istemcinin yazdığı baştaki değere güvenilmez.
  if (xff) return xff.split(",").pop()!.trim();
  return "bilinmiyor";
}

function sinirAsildiMi(ip: string): boolean {
  const simdi = Date.now();
  const kayit = denemeler.get(ip);
  if (!kayit || simdi - kayit.pencere > PENCERE_MS) {
    denemeler.set(ip, { adet: 1, pencere: simdi });
    return false;
  }
  kayit.adet += 1;
  return kayit.adet > SINIR;
}

export async function POST(req: NextRequest) {
  const { license } = await req.json().catch(() => ({}) as { license?: string });
  if (!license) return NextResponse.json({ ok: false }, { status: 401 });

  if (sinirAsildiMi(istemciIp(req))) {
    return NextResponse.json({ ok: false }, { status: 429 });
  }

  const lisanslar = tanimliLisanslar();

  if (lisanslar.length > 0) {
    // LGF-XXXX-XXXX-XXXX biçimindeki insan anahtarı burada doğrulanır.
    const bulunan = lisansDogrula(license);
    if (!bulunan) return NextResponse.json({ ok: false }, { status: 401 });
    console.log(`[giris] lisans=${bulunan.etiket}`);
  } else {
    // LISANS_ANAHTARLARI tanımlanmadıysa eski davranış: API anahtarını kabul et.
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
        { status: 502 },
      );
    }
    if (!r.ok) return NextResponse.json({ ok: false }, { status: 401 });
  }

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

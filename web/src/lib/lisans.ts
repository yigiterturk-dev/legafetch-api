// İnsana verilen lisans anahtarı: LGF-XXXX-XXXX-XXXX.
// 64 karakterlik API anahtarı SUNUCULAR ARASINDA kalır, kullanıcı onu görmez.
//
// Tanım env'den gelir: LISANS_ANAHTARLARI="LGF-7K2M-9QX4-3ZP8:Deneme, LGF-...:Büro adı"
// Etiket zorunlu değil; kimin hangi anahtarı kullandığını ayırt etmek için.

export type Lisans = { anahtar: string; etiket: string };

// Karıştırılabilen harf/rakamlar (I, O, 0, 1) alfabede yok.
const ALFABE = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ";

export function bicimle(ham: string): string {
  const temiz = (ham || "")
    .toUpperCase()
    .replace(/[^A-Z0-9]/g, "")
    .replace(/^LGF/, "");
  if (temiz.length !== 12) return "";
  return `LGF-${temiz.slice(0, 4)}-${temiz.slice(4, 8)}-${temiz.slice(8, 12)}`;
}

export function tanimliLisanslar(): Lisans[] {
  const ham = process.env.LISANS_ANAHTARLARI?.trim();
  if (!ham) return [];
  return ham
    .split(",")
    .map((parca) => {
      const [anahtar, ...etiket] = parca.split(":");
      const b = bicimle(anahtar);
      return b ? { anahtar: b, etiket: etiket.join(":").trim() || "isimsiz" } : null;
    })
    .filter((x): x is Lisans => x !== null);
}

// Sabit zamanlı karşılaştırma: eşleşmeyen anahtarda da aynı süre harcanır.
function esitMi(a: string, b: string): boolean {
  if (a.length !== b.length) return false;
  let fark = 0;
  for (let i = 0; i < a.length; i++) fark |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return fark === 0;
}

export function lisansDogrula(girilen: string): Lisans | null {
  const b = bicimle(girilen);
  let bulunan: Lisans | null = null;
  for (const l of tanimliLisanslar()) {
    if (esitMi(l.anahtar, b) && b !== "") bulunan = l;
  }
  return bulunan;
}

export function yeniAnahtar(): string {
  const bayt = new Uint8Array(12);
  crypto.getRandomValues(bayt);
  const harfler = Array.from(bayt, (b) => ALFABE[b % ALFABE.length]).join("");
  return `LGF-${harfler.slice(0, 4)}-${harfler.slice(4, 8)}-${harfler.slice(8, 12)}`;
}

// Lemon Squeezy satın alım anahtarları: statik listede yokken LS License API'si
// sorulur (uç anahtarsız çalışır). Sonuç 6 saat önbelleklenir; her giriş LS'e
// gitmesin. LS_LISANS=1 olmadan bu yol hiç açılmaz — mağaza açılana dek davranış
// birebir bugünkü gibi kalır.
const lsOnbellek = new Map<string, { gecerli: boolean; t: number }>();
const LS_TTL_MS = 6 * 3_600_000;

export async function lsLisansDogrula(anahtar: string): Promise<boolean> {
  if (process.env.LS_LISANS !== "1") return false;
  const kayit = lsOnbellek.get(anahtar);
  const simdi = Date.now();
  if (kayit && simdi - kayit.t < LS_TTL_MS) return kayit.gecerli;
  let gecerli = false;
  try {
    const r = await fetch("https://api.lemonsqueezy.com/v1/licenses/validate", {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify({ license_key: anahtar }),
      cache: "no-store",
      signal: AbortSignal.timeout(10_000),
    });
    const j = (await r.json().catch(() => null)) as { valid?: boolean } | null;
    gecerli = r.ok && j?.valid === true;
  } catch {
    gecerli = false;
  }
  lsOnbellek.set(anahtar, { gecerli, t: simdi });
  return gecerli;
}

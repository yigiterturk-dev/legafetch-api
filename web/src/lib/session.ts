// Stateless imzalı oturum: HMAC-SHA256 (Web Crypto) ile imzalanmış cookie.
// Proxy (edge) ve route handler'lar aynı doğrulamayı kullanır; sunucu tarafında oturum defteri tutulmaz.
// NOT: SESSION_SECRET üretimde mutlaka env'den verilmelidir.
const SESSION_TTL_MS = 7 * 24 * 3600 * 1000; // 7 gün

function b64urlEncode(bytes: Uint8Array): string {
  let bin = "";
  for (const b of bytes) bin += String.fromCharCode(b);
  return btoa(bin).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

function b64urlDecode(s: string): Uint8Array {
  const bin = atob(s.replace(/-/g, "+").replace(/_/g, "/"));
  const out = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
  return out;
}

async function hmacKey(): Promise<CryptoKey> {
  const secret = process.env.SESSION_SECRET;
  if (!secret) throw new Error("SESSION_SECRET tanimli olmali");
  return crypto.subtle.importKey(
    "raw",
    new TextEncoder().encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"]
  );
}

// Sabit zamanlı karşılaştırma (timing-safe)
function ctEqual(a: Uint8Array, b: Uint8Array): boolean {
  if (a.length !== b.length) return false;
  let diff = 0;
  for (let i = 0; i < a.length; i++) diff |= a[i] ^ b[i];
  return diff === 0;
}

/**
 * Oturum artık kimlik de taşır: `kim` = lisans anahtarının SHA-256'sı.
 * Dosya/proje alanı bunu kullanarak kayıtları kullanıcıya bağlar. Anahtarın
 * kendisi çereze YAZILMAZ — özet yeterli, sızarsa anahtar ele geçmez.
 */
export async function kullaniciKimligi(lisansAnahtari: string): Promise<string> {
  const ozet = await crypto.subtle.digest(
    "SHA-256",
    new TextEncoder().encode(lisansAnahtari)
  );
  return Array.from(new Uint8Array(ozet).slice(0, 16))
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}

export async function createSessionToken(kim?: string): Promise<string> {
  const payload = b64urlEncode(
    new TextEncoder().encode(
      JSON.stringify({ exp: Date.now() + SESSION_TTL_MS, ...(kim ? { kim } : {}) })
    )
  );
  const mac = await crypto.subtle.sign("HMAC", await hmacKey(), new TextEncoder().encode(payload));
  return `${payload}.${b64urlEncode(new Uint8Array(mac))}`;
}

export async function verifySessionToken(token: string | undefined | null): Promise<boolean> {
  if (!token) return false;
  const dot = token.lastIndexOf(".");
  if (dot < 0) return false;
  const payload = token.slice(0, dot);
  const mac = b64urlDecode(token.slice(dot + 1));
  const expected = new Uint8Array(
    await crypto.subtle.sign("HMAC", await hmacKey(), new TextEncoder().encode(payload))
  );
  if (!ctEqual(mac, expected)) return false;
  try {
    const data = JSON.parse(new TextDecoder().decode(b64urlDecode(payload))) as { exp?: number };
    return typeof data.exp === "number" && Date.now() < data.exp;
  } catch {
    return false;
  }
}

/** Geçerli oturumun kimlik özetini döndürür; imza tutmuyorsa null. */
export async function oturumKimligi(token: string | undefined | null): Promise<string | null> {
  if (!token || !(await verifySessionToken(token))) return null;
  try {
    const payload = token.slice(0, token.lastIndexOf("."));
    const data = JSON.parse(new TextDecoder().decode(b64urlDecode(payload))) as { kim?: string };
    return typeof data.kim === "string" && data.kim ? data.kim : null;
  } catch {
    return null;
  }
}

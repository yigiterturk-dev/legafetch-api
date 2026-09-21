// Lisans anahtari uretir: node scripts/anahtar-uret.mjs [adet] [etiket]
// Ciktiyi web/.env.production icindeki LISANS_ANAHTARLARI satirina koyun.
import { webcrypto as crypto } from "node:crypto";

const ALFABE = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ";
const adet = Number(process.argv[2] || 1);
const etiket = process.argv[3] || "isimsiz";

const uret = () => {
  const bayt = new Uint8Array(12);
  crypto.getRandomValues(bayt);
  const h = Array.from(bayt, (b) => ALFABE[b % ALFABE.length]).join("");
  return `LGF-${h.slice(0, 4)}-${h.slice(4, 8)}-${h.slice(8, 12)}`;
};

const liste = Array.from({ length: adet }, () => `${uret()}:${etiket}`);
console.log(liste.join(", "));

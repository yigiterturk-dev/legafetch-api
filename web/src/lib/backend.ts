// Sunucu tarafinda kullanilir; client bundle'ina sismaz.
export const BACKEND = process.env.API_BACKEND_URL ?? "http://localhost:8001";
export function getApiKey(): string {
  const key = process.env.API_SECRET_KEY;
  if (!key) {
    throw new Error("API_SECRET_KEY tanimli olmali (gizli anahtar kodda durmaz)");
  }
  return key;
}

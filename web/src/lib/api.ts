// Tek noktadan API adresi:
// - Tarayıcı, aynı origin'deki Next.js proxy'sine istek atar (lisans anahtarı client'a sızmaz).
// - Proxy, anahtarı sunucu tarafında ekleyip FastAPI'ye iletir.
export const API_PROXY = "/api/proxy";

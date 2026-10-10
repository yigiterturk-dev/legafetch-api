# LegaFetch API

Production architecture and failure boundaries: [ARCHITECTURE.md](ARCHITECTURE.md).
Recruiter-facing evidence draft: [PORTFOLIO.md](PORTFOLIO.md).
Observability coverage: [OBSERVABILITY.md](OBSERVABILITY.md).
Role feedback mapped to concrete evidence: [ROLE-GAP-CLOSURE.md](ROLE-GAP-CLOSURE.md).

Hukuk mevzuat pasajlarını çok dilli embedding ile vektörleştirip (Qdrant), sorguları
yasal referanslarla eşleştiren FastAPI servisi. InsureFetch ile aynı mimariyi paylaşır.

## Çalıştırma (lokal)

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Not: `--reload` + Qdrant local-path dosya kilidi çakışabilir; ölürse `pkill -f uvicorn` ile tamamen kesip yeniden başlatın.

## Veri ingest

```bash
python ingest.py dosya.json
# Format: [{"content": "...", "source": "TTK Madde 332", "jurisdiction": "TR", "authority_score": 98}]
```
İdempotenttir: aynı içerik tekrar yüklenmez. API boş veritabanını örnek pasajlarla oto-seed eder.

## API Uçları (hepsi `X-API-Key` ister, `/health` hariç)

| Uç | Yöntem | İş |
|---|---|---|
| `/health` | GET | Kimliksiz sağlık kontrolü |
| `/api/chat` | POST | Jurisdiction filtreli semantic arama, numaralı kaynaklı cevap |
| `/api/analyze-contract` | POST | Sözleşme PDF'ini (pypdf) mevzuatla karşılaştırır (≤10 MB) |
| `/api/admin/stats` | GET | Gerçek kullanım sayaçları |
| `/api/auth/verify` | POST | Lisans anahtarı doğrulama (web login bunu kullanır) |

Rate limit: IP başına 120 istek/dk (env `RATE_LIMIT_PER_MIN`).

## Ortam Değişkenleri

| Değişken | Varsayılan | Anlamı |
|---|---|---|
| `X_API_KEY` | `LGF-ENV-KEY` | API lisans anahtarı |
| `X_LICENSE_KEYS` | `X_API_KEY` | Virgülle ayrılmış lisans anahtarları |
| `RATE_LIMIT_PER_MIN` | `120` | IP başına dakikalık limit |
| `CORS_ORIGINS` | `http://localhost:3000,http://localhost:3001` | İzinli origin'ler |
| `QDRANT_URL` | _(boş)_ | Tanımlıysa KORPUS MODU: uzak Qdrant'a bağlanır (ör. `http://localhost:6333`) |
| `QDRANT_API_KEY` | _(boş)_ | Uzak Qdrant API anahtarı (korpus modu) |
| `QDRANT_COLLECTION` | `lexordo_pasajlar` | Uzak koleksiyon adı (korpus modu) |
| `CORPUS_K` | `6` | Korpus modunda döndürülecek pasaj sayısı |

### Korpus Modu (8M+ içtihat)

`QDRANT_URL` tanımlandığında API, lokal demo koleksiyonu yerine uzak `lexordo_pasajlar`
koleksiyonunda arama yapar (salt-okunur). Korpus e5/multilingual-e5-small ile gömülüdür;
sorgular `query: ` önekiyle embed edilir. Lokal demo modu (`QDRANT_URL` boş) MiniLM
modeliyle `qdrant_storage/` kullanır ve hiç değişmez.

## Test

```bash
pip install -r requirements-dev.txt
# Dev uvicorn'u durdurun, sonra:
pytest tests/test_api.py
```

## Node.js gateway verification

The production gateway is under `gateway/`. From the repository root:

```bash
make verify
```

This runs the TypeScript build, tests, strict type/lint check, and production
dependency audit. The gateway also has a committed `package-lock.json` so CI
and local installs resolve the same dependency tree.

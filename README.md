# LegaFetch API

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

## Test

```bash
pip install -r requirements-dev.txt
# Dev uvicorn'u durdurun, sonra:
pytest tests/test_api.py
```

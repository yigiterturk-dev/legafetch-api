# LegaFetch API

Turkish legal research backend: hybrid retrieval and reranking over statutes and case law,
citation-grounded answers, and a deliberate refusal to answer when the sources do not support one.

FastAPI AI core · Node.js/TypeScript gateway · Qdrant · Docker Compose · Caddy

## What it does

- **Citation-grounded answers.** `/api/chat` retrieves passages with jurisdiction filtering and
  returns an answer with numbered sources. No retrievable source, no answer.
- **Contract analysis.** `/api/analyze-contract` compares an uploaded PDF (up to 10 MB) against
  the statute corpus.
- **Large case-law corpus mode.** With `QDRANT_URL` set, the API searches a read-only remote
  collection of roughly ten million case-law passages embedded with multilingual-e5-small;
  without it, a local demo collection runs with no external dependency.
- **Production gateway.** A TypeScript gateway adds request IDs, bounded bodies, timeouts and
  API-key auth in front of the Python core; failures map to explicit `401` / `502` / `503`.

## Measured, not claimed

Retrieval quality is evaluated on a labelled question set and recorded in `OLCUM.md`:
**61 of 70 questions answered with the correct provision in the top 5 (87% hit@5)**, up from
79% before the latest statute coverage and reranking changes. Failure cases are listed there too.

Architecture and failure boundaries: [ARCHITECTURE.md](ARCHITECTURE.md) ·
Observability: [OBSERVABILITY.md](OBSERVABILITY.md) · Operations: [RUNBOOK.md](RUNBOOK.md) ·
Security: [SECURITY.md](SECURITY.md)

## Run locally

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

The API seeds an empty database with sample passages. To load your own:

```bash
python ingest.py file.json
# [{"content": "...", "source": "TTK Madde 332", "jurisdiction": "TR", "authority_score": 98}]
```

Ingestion is idempotent: identical content is never loaded twice.

## API

All routes except `/health` require an `X-API-Key` header. Rate limit: 120 requests/min per IP
(`RATE_LIMIT_PER_MIN`).

| Route | Method | Purpose |
|---|---|---|
| `/health` | GET | Unauthenticated health check |
| `/api/chat` | POST | Jurisdiction-filtered semantic search, answer with numbered sources |
| `/api/analyze-contract` | POST | Compare a contract PDF with the statute corpus |
| `/api/admin/stats` | GET | Real usage counters |
| `/api/auth/verify` | POST | License key verification |

## Configuration

| Variable | Default | Meaning |
|---|---|---|
| `X_API_KEY` | none, set it | API license key |
| `X_LICENSE_KEYS` | `X_API_KEY` | Comma-separated license keys |
| `RATE_LIMIT_PER_MIN` | `120` | Per-IP request limit |
| `CORS_ORIGINS` | `http://localhost:3000,http://localhost:3001` | Allowed origins |
| `QDRANT_URL` | empty | Set to use corpus mode (remote Qdrant) |
| `QDRANT_API_KEY` | empty | Remote Qdrant key |
| `QDRANT_COLLECTION` | `lexordo_pasajlar` | Remote collection name |
| `CORPUS_K` | `6` | Passages returned in corpus mode |

## Test

```bash
pip install -r requirements-dev.txt
pytest tests/test_api.py
make verify        # gateway: TypeScript build, tests, strict lint, production dependency audit
```

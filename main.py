from fastapi import FastAPI, UploadFile, File, Security, HTTPException, status
from fastapi.security import APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Optional
from collections import deque

from langchain_huggingface import HuggingFaceEmbeddings
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, Filter, FieldCondition, MatchValue
from langchain_core.documents import Document

import os
import io
import time
import secrets
import hashlib
import uuid as uuidlib
import pypdf

app = FastAPI(title="LegaFetch Core - Legal AI Infrastructure")

# --- CORS: env ile sinirlandi ---
CORS_ORIGINS = [
    o.strip() for o in os.environ.get(
        "CORS_ORIGINS",
        "http://localhost:3000,http://localhost:3001",
    ).split(",") if o.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- API KEY AUTHENTICATION ---
API_KEY = os.environ.get("X_API_KEY", "LGF-ROTATED-2026")
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=True)

# Lisans anahtarlari: env'den coklu verilebilir (virgulle)
LICENSE_KEYS = set(k.strip() for k in os.environ.get("X_LICENSE_KEYS", API_KEY).split(",") if k.strip())


def get_api_key(api_key_header: str = Security(api_key_header)):
    if secrets.compare_digest(api_key_header or "", API_KEY):
        return api_key_header
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid API Key. Purchase a license at legafetch.com",
    )
# ------------------------------

# --- Gerçek kullanım sayaçları ---
STATS = {"chat": 0, "contract": 0}
JURISDICTION_COUNTS: dict = {}
PROCESS_START = time.time()
MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB

# --- Rate limiting: IP basina kayan pencere ---
RATE_LIMIT_PER_MIN = int(os.environ.get("RATE_LIMIT_PER_MIN", "120"))
_hits: dict = {}
_last_cleanup = 0.0


def _prune_stale_ips(now: float) -> None:
    global _last_cleanup
    if now - _last_cleanup < 60:
        return
    _last_cleanup = now
    for ip in list(_hits.keys()):
        q = _hits[ip]
        while q and now - q[0] > 60:
            q.popleft()
        if not q:
            del _hits[ip]


def check_rate_limit(client_ip: str) -> bool:
    now = time.time()
    _prune_stale_ips(now)
    q = _hits.setdefault(client_ip, deque())
    while q and now - q[0] > 60:
        q.popleft()
    if len(q) >= RATE_LIMIT_PER_MIN:
        return False
    q.append(now)
    return True


@app.middleware("http")
async def rate_limit_middleware(request, call_next):
    ip = request.headers.get("x-forwarded-for", "").split(",")[0].strip() or (
        request.client.host if request.client else "unknown"
    )
    if not check_rate_limit(ip):
        return JSONResponse(status_code=429, content={"detail": "Dakikalik istek limitini astiniz."})
    return await call_next(request)


class VerifyRequest(BaseModel):
    license_key: str


@app.post("/api/auth/verify")
async def verify_license(request: VerifyRequest):
    if any(secrets.compare_digest(request.license_key or "", k) for k in LICENSE_KEYS):
        return {"valid": True, "plan": "pro"}
    raise HTTPException(status_code=401, detail="Gecersiz lisans anahtari.")


class ChatRequest(BaseModel):
    query: str
    jurisdiction: Optional[str] = "global"

class SourceMetadata(BaseModel):
    source: str
    authority_score: int
    jurisdiction: str

class ChatResponse(BaseModel):
    text: str
    sources: List[SourceMetadata]

# 1. Çok Dilli (Multi-lingual) Embedding Modeli
embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")

# 2. Qdrant: kalici lokal depo (restart'te veri kaybolmaz)
qdrant_path = os.path.join(os.path.dirname(__file__), "qdrant_storage")
client = QdrantClient(path=qdrant_path)
collection_name = "legal_documents"

if not client.collection_exists(collection_name):
    client.create_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(size=384, distance=Distance.COSINE),
    )

vector_store = QdrantVectorStore(
    client=client,
    collection_name=collection_name,
    embedding=embeddings,
)


def stable_id(doc: Document) -> str:
    return str(uuidlib.UUID(hashlib.sha256(doc.page_content.encode("utf-8")).hexdigest()[:32]))


# 3. Bos veritabanini ornek pasajlarla oto-seed (idempotent — restart'ta cogaltmaz)
sample_docs = [
    Document(
        page_content="Türkiye'de anonim şirket (A.Ş.) kurmak için asgari sermaye tutarı 250.000 TL'dir. Kurumlar vergisi genel oranı %25'tir.",
        metadata={"source": "TTK Madde 332", "authority_score": 98, "jurisdiction": "TR"}
    ),
    Document(
        page_content="İspanya'da anonim şirket (Sociedad Anónima - S.A.) asgari kuruluş sermayesi 60.000 Euro'dur. Yeni kurulan şirketler için kurumlar vergisi ilk iki yıl %15 olarak uygulanır.",
        metadata={"source": "İspanya Şirketler Kanunu (LSC)", "authority_score": 95, "jurisdiction": "ES"}
    ),
    Document(
        page_content="Limited şirket (Ltd. Şti.) kuruluşunda asgari sermaye 50.000 TL'dir; ortak sayısı en az 1, en fazla 50 olabilir.",
        metadata={"source": "TTK Madde 573", "authority_score": 98, "jurisdiction": "TR"}
    ),
    Document(
        page_content="Türkiye'de imar ve iskân mevzuatına göre, ruhsatsız yapıların yıkımı ancak mahkeme kararıyla mümkündür.",
        metadata={"source": "İmar Kanunu Ek Madde", "authority_score": 90, "jurisdiction": "TR"},
    ),
]

def ensure_seed() -> None:
    if client.count(collection_name).count == 0:
        vector_store.add_documents(
            [d for d in sample_docs if d.page_content],
            ids=[stable_id(d) for d in sample_docs if d.page_content],
        )

ensure_seed()


@app.get("/health")
async def health():
    """Compose healthcheck icin kimliksiz, hafif endpoint."""
    return {
        "status": "ok",
        "engine": "Online",
        "vector_count": client.count(collection_name).count,
    }


@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest, api_key: str = Security(get_api_key)):
    try:
        STATS["chat"] += 1
        jur = request.jurisdiction if request.jurisdiction and request.jurisdiction != "global" else None
        if jur:
            JURISDICTION_COUNTS[jur] = JURISDICTION_COUNTS.get(jur, 0) + 1

        search_kwargs = {"k": 2}
        if jur:
            search_kwargs["filter"] = Filter(
                must=[FieldCondition(key="metadata.jurisdiction",
                                     match=MatchValue(value=jur))]
            )
        retriever = vector_store.as_retriever(search_kwargs=search_kwargs)
        docs = retriever.invoke(request.query)

        if not docs:
             return ChatResponse(
                text="Bu sorguya uygun bir pasaj kendi veritabanınızda bulunamadı.",
                sources=[]
            )

        # Keyless extractive kompozisyon: otorite skoruna gore numaralandir
        ranked = sorted(docs, key=lambda d: d.metadata.get("authority_score", 50), reverse=True)
        parts = [
            f"[{i}] {doc.page_content}\n"
            f"    Kaynak: {doc.metadata.get('source', 'Bilinmeyen')} "
            f"(güven %{doc.metadata.get('authority_score', 50)}, "
            f"{doc.metadata.get('jurisdiction', 'Global')})"
            for i, doc in enumerate(ranked, start=1)
        ]
        context_text = (
            f"Toplam {len(ranked)} kaynak bulundu. En alakalı pasajlar:\n\n"
            + "\n\n".join(parts)
            + "\n\nNot: Cevap vektör aramasından derlenmiştir; üretici dil modeli henüz bağlı değildir."
        )

        sources_meta = [
            SourceMetadata(
                source=doc.metadata.get("source", "Bilinmeyen"),
                authority_score=doc.metadata.get("authority_score", 50),
                jurisdiction=doc.metadata.get("jurisdiction", "Global")
            )
            for doc in ranked
        ]

        return ChatResponse(text=context_text, sources=sources_meta)
    except Exception as e:
         return ChatResponse(text=f"Hata: {str(e)}", sources=[])


@app.post("/api/analyze-contract")
async def analyze_contract(file: UploadFile = File(...), api_key: str = Security(get_api_key)):
    raw = await file.read()
    if len(raw) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Dosya 10 MB sınırını aşıyor.")
    STATS["contract"] += 1

    # Gercel PDF metni + yasal pasajlarla semantic carpistirma
    text = ""
    if (file.filename or "").lower().endswith(".pdf"):
        try:
            reader = pypdf.PdfReader(io.BytesIO(raw))
            text = "\n".join((page.extract_text() or "") for page in reader.pages[:10])
        except Exception:
            text = ""

    query = text[:500] or f"{file.filename} sözleşme"
    docs = vector_store.as_retriever(search_kwargs={"k": 2}).invoke(query)

    sources_meta = [
        {
            "source": d.metadata.get("source", "Bilinmeyen"),
            "authority_score": d.metadata.get("authority_score", 50),
            "jurisdiction": d.metadata.get("jurisdiction", "Global"),
        }
        for d in docs
    ]

    if docs:
        analysis = (
            "Sözleşme metni yürürlükteki mevzuatla karşılaştırıldı. "
            f"En alakalı hukuki referans: {docs[0].page_content}"
        )
    else:
        analysis = "Sözleşme metninde eşleşen yasa maddesi bulunamadı."

    return {
        "filename": file.filename,
        "status": "success",
        "analysis": analysis,
        "sources": sources_meta,
    }


@app.get("/api/admin/stats")
async def get_admin_stats(api_key: str = Security(get_api_key)):
    top_jur = max(JURISDICTION_COUNTS, key=JURISDICTION_COUNTS.get) if JURISDICTION_COUNTS else "Henüz veri yok"
    return {
        "total_queries": sum(STATS.values()),
        "breakdown": STATS,
        "active_api_keys": 1,  # Su an tek lisans anahtari (multi-tenant yok)
        "top_jurisdiction": top_jur,
        "vector_count": client.count(collection_name).count,
        "uptime_hours": round((time.time() - PROCESS_START) / 3600, 2),
    }

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
import re
from concurrent.futures import ThreadPoolExecutor
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
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

API_KEY = os.environ.get("X_API_KEY", "")
if not API_KEY:
    raise RuntimeError("X_API_KEY tanimli degil: .env dosyasina yazilmali (gizli anahtar kodda durmaz)")
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=True)

# Lisans anahtarlari: env'den coklu verilebilir (virgulle)
LICENSE_KEYS = set(k.strip() for k in os.environ.get("X_LICENSE_KEYS", API_KEY).split(",") if k.strip())

# --- KORPUS MODU: QDRANT_URL tanimliysa uzak (VPS) koleksiyona baglanir ---
# Uzak korpus (lexordo_pasajlar) e5/Xenova-multilingual-e5-small ile gomulmustur;
# e5 asimetrik oldugundan sorgular "query: " onekiyle embed edilir.
QDRANT_URL = os.environ.get("QDRANT_URL", "").strip()
QDRANT_API_KEY = os.environ.get("QDRANT_API_KEY", "").strip()
CORPUS_COLLECTION = os.environ.get("QDRANT_COLLECTION", "lexordo_pasajlar").strip()
CORPUS_K = int(os.environ.get("CORPUS_K", "6"))
# Rerank maliyeti cift sayisiyla dogrusal (CPU): 40+8 cift v2-m3 ile ~110 sn olculdu.
# Varsayilanlar ~20 cifte indirildi (base model ile ~6-7 sn).
CORPUS_FETCH_K = int(os.environ.get("CORPUS_FETCH_K", "15"))
CORPUS_MEVZUAT_K = int(os.environ.get("CORPUS_MEVZUAT_K", "8"))
# Mevzuat kolu 2026-09-17 audit sonrasi: fetch 24 zaten vardi ama MEVZUAT_K 6
# kalince dogru madde (TKHK m.5 gibi) semantik top-6'ya girip rerank'a
# ulasamiyordu; cap 8'e cikarildi ve anahtar-sorgu probe'u eklendi.
CORPUS_MEVZUAT_FETCH_K = int(os.environ.get("CORPUS_MEVZUAT_FETCH_K", "24"))
# Mevzuat seciminde anahtar-kelime cakisma boost'u: bge-reranker-base kisa
# kanun maddelerinde ~0 skor uretip ayirt edemedigi icin, sorgu terimlerinin
# madde metninde gecme oranina kucuk bir bonus eklenir (yalnizca mevzuat
# seciminde; ictihat siralamasi saf rerank skoruyla kalir).
MEVZUAT_KW_BOOST = float(os.environ.get("MEVZUAT_KW_BOOST", "0.6"))
from rerank import rerank, rerank_scored, RERANK_ENABLED  # noqa: E402
CORPUS_MAX_PER_BELGE = int(os.environ.get("CORPUS_MAX_PER_BELGE", "2"))
REMOTE_MODE = bool(QDRANT_URL)


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

# 1. Embedding modeli: uzak korpus = e5 (korpusun gomulme uzayiyla ayni);
#    lokal demo modu = MiniLM (mevcut lokal koleksiyon degismez).
embeddings = HuggingFaceEmbeddings(
    model_name="intfloat/multilingual-e5-small" if REMOTE_MODE
    else "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
)

# 2. Qdrant: REMOTE_MODE'da salt-okunur uzak koleksiyon; degilse kalici lokal depo
if REMOTE_MODE:
    client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY or None, timeout=30)
    collection_name = CORPUS_COLLECTION
else:
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


# --- KORPUS ARAMA (REMOTE_MODE): lexordo payload -> Document donusumu ---
CORPUS_AUTHORITY = [
    ("anayasa", 97),
    ("mevzuat", 96),
    ("danistay", 93),
    ("yargitay", 90),
    ("bolge", 75),
]


def corpus_authority(payload: dict) -> int:
    # yargiKademesi/belgeSinifi/id alanlarindan otorite skoru turetir.
    hayir = " ".join(
        str(payload.get(k, "")) for k in ("yargiKademesi", "belgeSinifi", "id")
    ).lower()
    for anahtar, skor in CORPUS_AUTHORITY:
        if anahtar in hayir:
            return skor
    return 60


def temiz_kaynak(p: dict) -> str:
    """Yapısal alanlardan (yargiKademesi, daire, esasNo, kararNo) okunur
    kaynak etiketi kurar. 2026-09-17 audit bulgusu: istinaf kayıtlarında
    ham 'kaynak' BAM önekiyle ilk derece mahkemesini iç içe gösteriyordu:
    'Bölge Adliye Mahkemesi Bursa 2. Asliye Ticaret Mahkemesi E. ...'
    Aynı sorunu tekrarlayan etiketler de vardı ('İstanbul BAM İstanbul BAM
    6. Hukuk'). Alanlar varsa temiz kur, yoksa ham 'kaynak'a dön."""
    if (p.get("belgeSinifi") or "") != "yargi-karari":
        return p.get("kaynak") or "Bilinmeyen"
    daire = (p.get("daire") or "").strip()
    if not daire:
        return p.get("kaynak") or "Bilinmeyen"
    kademe = (p.get("yargiKademesi") or "").strip()
    d_low = _norm_metin(daire)
    if kademe == "istinaf":
        # daire alanı şehirli tam ad taşıyor ("Bursa 2. Asliye Ticaret ...")
        mahkeme = daire
    elif kademe == "temyiz":
        mahkeme = daire if "yargitay" in d_low else f"Yargıtay {daire}"
    elif kademe == "yuksek-mahkeme":
        mahkeme = daire if "danistay" in d_low else f"Danıştay {daire}"
    else:
        return p.get("kaynak") or "Bilinmeyen"
    parcalar = [mahkeme]
    if p.get("esasNo"):
        parcalar.append("E. " + str(p["esasNo"]))
    if p.get("kararNo"):
        parcalar.append("K. " + str(p["kararNo"]))
    return ", ".join(parcalar)


KANUN_NO_RE = re.compile(r"(\d{3,5})\s*(?:say[iı]l[iı]|sayili)")

# --- Anahtar-sorgu araci (mevzuat kolu icin) ------------------------------
_TR_FOLD = str.maketrans("çğıöşüÇĞİÖŞÜ", "cgiösuCGIOSU")
_MEVZUAT_DURAK = {
    "ve", "veya", "ile", "icin", "gibi", "hangi", "nasil", "ne", "kim",
    "mi", "midir", "mudur", "olur", "olabilir", "kac", "gundur", "gune",
    "gununde", "surede", "suresi", "sure", "tarihi", "tarihinden",
    "uygulanir", "kabul", "edilir", "alabilir", "bakilabilir",
    "acilabilir", "edilebilir", "isler", "yapilabilir", "davasi",
    "davasinda", "davasindan", "davasiyla", "davada",
}


def _norm_metin(s: str) -> str:
    """Turkce karakterleri ASCII'ye indirip kucultur — karsilastirma icin.
    NOT: ceviri lower()'dan ONCE yapilir — 'İ'.lower() Python'da 'i'+
    birlestiren nokta (U+0307) uretip eslesmeyi bozar."""
    return (s or "").translate(_TR_FOLD).lower()


def _anahtar_sorgu(query: str) -> str:
    """Sorgudan stopword'suz anahtar probe uretir. Orn.
    'tuketici sozlesmesindeki haksiz madde iptali davasi' ->
    'tuketici sozlesmesindeki haksiz madde iptali'."""
    tok = [
        t for t in re.findall(r"[a-z0-9]+", _norm_metin(query))
        if len(t) > 2 and t not in _MEVZUAT_DURAK
    ]
    return " ".join(tok[:6])


def _anahtar_hit_orani(query: str, metin: str) -> float:
    """Sorgunun icerik sozcuklerinin kaci madde metninde geciyor — orani."""
    tok = {
        t for t in re.findall(r"[a-z0-9]+", _norm_metin(query))
        if len(t) > 2 and t not in _MEVZUAT_DURAK
    }
    if not tok:
        return 0.0
    metin_n = _norm_metin(metin or "")
    return sum(1 for t in tok if t in metin_n) / len(tok)


def mevzuat_havuz_daralt(query: str, mev_aday: list) -> list:
    """Sorguda acikca kanun numarasi (orn. '4857 sayili') geciyorsa mevzuat
    adaylarini o kanuna daralt — cross-encoder yanlis kanundan madde
    secmesin. Numara bulunamazsa havuz aynen doner."""
    nolar = KANUN_NO_RE.findall(query)
    if not nolar or not mev_aday:
        return mev_aday
    daralt = [
        d for d in mev_aday
        if any(no in d.metadata.get("source", "") for no in nolar)
    ]
    return daralt or mev_aday


def _mevzuat_dense_ara(sorgu: str, k: int) -> list:
    """Tek bir sorgu icin mevzuat filtreli dense arama."""
    vec = embeddings.embed_query("query: " + sorgu)
    sonuc = client.query_points(
        collection_name,
        query=vec,
        limit=k,
        query_filter=Filter(
            must=[
                FieldCondition(key="belgeSinifi", match=MatchValue(value="mevzuat")),
                FieldCondition(key="sentetik", match=MatchValue(value=False)),
            ]
        ),
        with_payload=True,
        with_vectors=False,
    )
    docs = []
    for pt in sonuc.points:
        p = pt.payload or {}
        docs.append(
            Document(
                page_content=p.get("metin", ""),
                metadata={
                    "source": temiz_kaynak(p),
                    "authority_score": corpus_authority(p),
                    "jurisdiction": "TR",
                    "tarih": p.get("tarih", ""),
                    "daire": p.get("daire", ""),
                    "esasNo": p.get("esasNo", ""),
                    "kararNo": p.get("kararNo", ""),
                    "docId": p.get("docId", ""),
                    "tur": "mevzuat",
                },
            )
        )
    return docs


def corpus_search_mevzuat(query: str, k: int) -> list:
    """Mevzuat kolunda IKI probe: tam soru + anahtar sorgu. 2026-09-17 audit
    olcumu: tam soru embedding'i konu-yonlu sorularda kanun maddesini
    bulamıyor (TKHK m.5 top-24'te bile gorunmuyordu); stopword'suz anahtar
    probe'u m.5'i top-7'ye cikardi. Iki sonuc interleave edilir — her iki
    siralamanin da en iyileri rerank havuzuna girer."""
    tam = _mevzuat_dense_ara(query, k)
    anahtar = _anahtar_sorgu(query)
    if not anahtar or _norm_metin(anahtar) == _norm_metin(query):
        return tam
    probe = _mevzuat_dense_ara(anahtar, max(2, k // 2))
    gorulen, birlesik = set(), []
    for a, b in zip(tam, probe + [None] * len(tam)):
        for d in (a, b):
            if d is None:
                continue
            anahtar_k = (
                d.metadata.get("source", ""),
                (d.page_content or "")[:80],
            )
            if anahtar_k in gorulen:
                continue
            gorulen.add(anahtar_k)
            birlesik.append(d)
    return birlesik


def corpus_search(query: str, k: int) -> list:
    # Uzak korpusa e5 'query: ' onekiyle semantic arama yapar.
    vec = embeddings.embed_query("query: " + query)
    sonuc = client.query_points(
        collection_name,
        query=vec,
        limit=k,
        query_filter=Filter(
            must=[FieldCondition(key="sentetik", match=MatchValue(value=False))]
        ),
        with_payload=True,
        with_vectors=False,
    )
    docs = []
    belge_sayaci = {}
    for pt in sonuc.points:
        p = pt.payload or {}
        did = p.get("docId", "")
        if did:
            sayi = belge_sayaci.get(did, 0)
            if sayi >= CORPUS_MAX_PER_BELGE:
                continue  # ayni karar chunk patlamasi -> cesitlilik icin atla
            belge_sayaci[did] = sayi + 1
        docs.append(
            Document(
                page_content=p.get("metin", ""),
                metadata={
                    "source": temiz_kaynak(p),
                    "authority_score": corpus_authority(p),
                    "jurisdiction": "TR",
                    "tarih": p.get("tarih", ""),
                    "daire": p.get("daire", ""),
                    "esasNo": p.get("esasNo", ""),
                    "kararNo": p.get("kararNo", ""),
                    "docId": p.get("docId", ""),
                    "tur": p.get("belgeSinifi", ""),
                },
            )
        )
    return docs


def _tekillestir(docs: list) -> list:
    gorulen, out = set(), []
    for d in docs:
        anahtar = (d.metadata.get("source", ""), (d.page_content or "")[:120])
        if anahtar in gorulen:
            continue
        gorulen.add(anahtar)
        out.append(d)
    return out


# --- URETIM SIRALAMA HATTI (REMOTE_MODE) --------------------------------
# /api/chat ile eval'lerin AYNI yolu olcmesi icin handler'dan cikarildi.
# Ders (2026-09-17 eval_rerank): eval kendi kopyasini yazinca mevzuat kolu
# hic olculmedi ve "mevzuat=0" yanlisi cikti — olcum = uretim olmali.
def corpus_rank(query: str, k: int = None) -> list:
    """Ictihat + mevzuat kollari (paralel) -> kanun-no daraltma -> tek gecis
    rerank -> garanti en iyi 2 FARKLI mevzuat madde. Uretim ve eval ortak yol."""
    k = k if k is not None else CORPUS_K
    with ThreadPoolExecutor(max_workers=2) as havuz:
        f_aday = havuz.submit(corpus_search, query, max(k, CORPUS_FETCH_K))
        f_mev = havuz.submit(corpus_search_mevzuat, query, CORPUS_MEVZUAT_FETCH_K)
        aday, mev_ham = f_aday.result(), f_mev.result()
    # Mevzuat havuzu Qdrant'tan genis cekilir (ucuz), kanun no'ya daraltilir,
    # sonra yalnizca ilk CORPUS_MEVZUAT_K'si rerank'e girer (pahali).
    mev_aday = mevzuat_havuz_daralt(query, mev_ham)[:CORPUS_MEVZUAT_K]
    # Genel havuzdan gelen mevzuat parcalari da kanun-no daraltmasindan gecsin
    mev_aday = mevzuat_havuz_daralt(
        query,
        [d for d in aday if d.metadata.get("tur") == "mevzuat"] + mev_aday,
    )
    ictihat_aday = [d for d in aday if d.metadata.get("tur") != "mevzuat"]
    skorlu = rerank_scored(query, _tekillestir(ictihat_aday + mev_aday))
    # Mevzuat secimi: rerank skoru + anahtar-cakisma boost'u. Olculdu
    # (2026-09-17): bge-reranker-base kisa kanun maddelerinde ~0 skor
    # uretip TCK Geçici-1'i TKHK'nin ustune koyabiliyor; keyword cakismasi
    # ikinci bir sinyal olarak eklenir (yalnizca mevzuat seciminde).
    mev_skorlu = [
        (
            d,
            (s if s is not None else 0.0)
            + MEVZUAT_KW_BOOST * _anahtar_hit_orani(query, d.page_content),
        )
        for d, s in skorlu
        if d.metadata.get("tur") == "mevzuat"
    ]
    mev_skorlu.sort(key=lambda x: x[1], reverse=True)
    # Kanun dayanagi temsili garanti: en iyi 2 FARKLI madde her cevapta yer
    # alir (içtihat maddeye ATIF yapar, maddeyi İÇERMEZ)
    mev_eniyi, gorulen_madde = [], set()
    for d, _ in mev_skorlu:
        kaynak = d.metadata.get("source", "")
        if kaynak not in gorulen_madde:
            gorulen_madde.add(kaynak)
            mev_eniyi.append(d)
        if len(mev_eniyi) == 2:
            break
    ictihat = [d for d, _ in skorlu if d.metadata.get("tur") != "mevzuat"]
    return ictihat[: max(0, k - len(mev_eniyi))] + mev_eniyi


if not REMOTE_MODE:
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

        if REMOTE_MODE:
            # Uzak korpus ictihat + mevzuat; siralama hatti corpus_rank'ta —
            # eval ayni fonksiyonu olcer (olcum = uretim).
            if jur and jur != "TR":
                docs = []
            else:
                docs = corpus_rank(request.query)
        else:
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
    if REMOTE_MODE:
        aday = corpus_search(query, max(3, CORPUS_FETCH_K))
        docs = rerank(query, aday, 3)
    else:
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

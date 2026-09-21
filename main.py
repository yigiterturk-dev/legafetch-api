from fastapi import FastAPI, UploadFile, File, Security, HTTPException, status, Request
from fastapi.security import APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel
from typing import List, Optional
from collections import deque

from langchain_huggingface import HuggingFaceEmbeddings
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance, VectorParams, Filter, FieldCondition, MatchValue, DatetimeRange,
)
from langchain_core.documents import Document

import ipaddress
import os
from datetime import datetime, timezone
import re
import json
import urllib.request
from concurrent.futures import ThreadPoolExecutor
import io
import time
import secrets
import hashlib
import uuid as uuidlib
import pypdf
import zipfile

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
# Sozcuksel (BM25) mevzuat kolunun aday sayisi. Bellek ici indeks,
# maliyeti milisaniye — rerank'e giren cift sayisini artirdigi icin
# yine de olculu tutulur.
CORPUS_MEVZUAT_BM25_K = int(os.environ.get("CORPUS_MEVZUAT_BM25_K", "0"))
# BM25 skorunun secim formulundeki agirligi. Olculdu 2026-09-21:
# BM25 adaylarini havuza EKLEMEK tek basina erisimi kotulestirdi
# (hit@5 15->14) — cunku secim hala yalniz rerank + anahtar boost ile
# yapiliyordu, havuz buyuyunce rerank yanlis maddeyi seciyordu.
# Sozcuksel sinyal secime de girmeli.
# 🔴 OLCUM SONUCU (2026-09-21, grid_hat.py — 10 kombinasyon x 20 soru):
# BM25 kolu mevzuat erisimine FAYDA SAGLAMADI, sadece zarar verdi:
#   bm25_k=0 boost=0.0 -> hit@5 15/20  MRR 0.725   (KAPALI = en iyi)
#   bm25_k=8 boost=0.3 -> hit@5 15/20  MRR 0.700
#   bm25_k=8 boost=0.5 -> hit@5 14/20  MRR 0.675
#   bm25_k=8 boost=1.0 -> hit@5 13/20  MRR 0.625
# Sozcuksel kol "itirazin iptali" gibi fraz sorularini kurtariyor ama
# "garanti 2 mevzuat maddesi" kurali yuzunden havuz buyudukce baska
# sorularda yanlis madde seciliyor; net etki sifir ya da eksi.
# Kod SILINMEDI: ictihat kolunda (9,86M pasaj, dense'in zayif oldugu yer)
# denenmeye deger ve es anlamli sozlugu orada da lazim olacak.
# Acmadan once grid_hat.py'yi yeniden kosun.
MEVZUAT_BM25_BOOST = float(os.environ.get("MEVZUAT_BM25_BOOST", "0"))

# Mevzuat maddesi listenin BASINA yalniz yeterince guclu bir isabetse
# konur. Olculdu 2026-09-21: maddeleri kosulsuz basa almak MRR'i 0.185'ten
# 0.725'e cikardi AMA alakasiz maddeleri de vitrine tasidi — "tuketici
# sozlesmesindeki haksiz madde" sorgusuna @1 TCK Gecici-1, @2 İİK m.281
# geliyordu (ham rerank skorlari 0.370 ve 0.246). Dogru isabetlerin ham
# skoru tipik olarak 0.68+ (1475 m.14: 0.684, 4857 m.53: 0.988).
# Esigin ALTINDA kalan madde atilmaz — sadece ictihadin ARDINA dusurulur:
# kanun dayanagi cevapta kalsin ama yanlissa ilk gorulen sey olmasin.
# TARANDI 2026-09-21 (grid_esik.py, IKI olcum setinde): esik YUKSELDIKCE
# erisim kotulesiyor — 0.0 ort MRR 0.613, 0.5 -> 0.568, 0.7 -> 0.549,
# tamamen kapali (eski davranis) -> 0.155. Yani "zayif mevzuati geri it"
# sezgim olcumde curudu; varsayilan 0 (kosulsuz basa).
# NOT: bu setler "dogru madde kacinci sirada" olcer, "alakasiz madde ne
# siklikla @1" OLCMEZ. Gurultu ayri bir olcumun konusu (test_gurultu.py).
MEVZUAT_BASA_ESIK = float(os.environ.get("MEVZUAT_BASA_ESIK", "0"))
# Mevzuat seciminde anahtar-kelime cakisma boost'u: bge-reranker-base kisa
# kanun maddelerinde ~0 skor uretip ayirt edemedigi icin, sorgu terimlerinin
# madde metninde gecme oranina kucuk bir bonus eklenir (yalnizca mevzuat
# seciminde; ictihat siralamasi saf rerank skoruyla kalir).
MEVZUAT_KW_BOOST = float(os.environ.get("MEVZUAT_KW_BOOST", "0.6"))
# Mevzuat maddesi cevaba ancak bu skorun USTUNDEyse girer. Olculdu 2026-09-20:
# "garanti en iyi 2 madde" kurali alaka gozetmedigi icin iş hukuku sorgusuna
# CMK m.61, ticaret sorgusuna TMK m.119 gibi tamamen alakasiz maddeler
# basiyordu. -999 = esik kapali (eski davranis); olcum sonrasi gercek deger
# env ile verilir.
MEVZUAT_MIN_SKOR = float(os.environ.get("MEVZUAT_MIN_SKOR", "-999"))
# Zorunlu mevzuat enjeksiyonunda yalnız reranker puanı yeterli değil:
# ölçümde tamamen alakasız CMK m.61 yüksek ham skor (0.642) alırken sorguyla
# hiçbir içerik sözcüğü paylaşmıyordu. En az bir anlamlı sözcük örtüşmesini
# oranla şart koş; 0.15 değeri ölçüm setindeki en düşük doğru adayın (0.20)
# altında kalır. Genel arama kolundan doğal biçimde gelen mevzuatı etkilemez.
# Nihai cevaba giren AZAMI farkli kanun maddesi sayisi. 2 degeri mevzuat
# 19 kanunken konmustu; 73 kanunda havuz yogunlasti ve 2026-09-21 teshisinde
# 15 kayip sorunun 7'sinde dogru madde ilk 8 aday arasina girdigi halde
# (hatta @2-@3) bu kota yuzunden cevaba giremedi (teshis_madde.py, asama D).
# Olculdu 2026-09-21, kota 2->4: kapsam 23->26/30, erisim 15->17/20,
# dogrulama 17->18/20 (toplam %79 -> %87); ictihat seti DEGISMEDI
# (konu@1 %96, merci %92). Uc setin ucunde de kazandi: asiri uyum degil.
# k=6'da 4 madde ictihada 2 yer birakirdi; CORPUS_K 8'e cikarildi ki
# dayanak artarken ictihat sayisi (4) korunsun.
MEVZUAT_GARANTI = int(os.environ.get("MEVZUAT_GARANTI", "4"))
MEVZUAT_MIN_ANAHTAR_ORANI = float(
    os.environ.get("MEVZUAT_MIN_ANAHTAR_ORANI", "0.15")
)
# --- Uretici katman (OpenAI) ---------------------------------------------
# OPENAI_API_KEY tanimliysa /api/chat pasajlari modele verip gercek bir
# yanit uretir; anahtar yoksa veya cagri hata verirse keyless extractive
# kompozisyona dusulur (fail-open — urun asla bozulmaz).
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "").strip()
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini").strip()
# Uc nokta yapilandirilabilir: DeepSeek, Groq, Together ve yerel sunucular
# ayni /chat/completions sozlesmesini konusuyor, yalniz alan adi degisiyor.
# Sabit api.openai.com yazilirsa saglayici degistirmek kod degisikligi ister.
OPENAI_BASE_URL = os.environ.get(
    "OPENAI_BASE_URL", "https://api.openai.com/v1"
).strip().rstrip("/")
OPENAI_TIMEOUT_S = int(os.environ.get("OPENAI_TIMEOUT_S", "40"))
# Sozlesme analizinde LLM'e gonderilecek azami karakter (~12 sayfa).
SOZLESME_AZAMI_KARAKTER = int(os.environ.get("SOZLESME_AZAMI_KARAKTER", "24000"))
# Sozlesme analizi tek cagrida uzun metin isler; sohbetin 40 sn'si yetmez.
SOZLESME_TIMEOUT_S = int(os.environ.get("SOZLESME_TIMEOUT_S", "120"))
from rerank import rerank, rerank_scored, RERANK_ENABLED  # noqa: E402
import mevzuat_bm25  # noqa: E402
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
# Lisans dogrulamasi icin AYRI ve cok daha sikı kova: anahtar denemesi kaba
# kuvvete acik oldugundan genel istek limitiyle ayni kovadan sayilmamali.
AUTH_RATE_LIMIT_PER_MIN = int(os.environ.get("AUTH_RATE_LIMIT_PER_MIN", "10"))
_hits: dict = {}
_auth_hits: dict = {}
_last_cleanup = 0.0


def _ozel_ip(ip: str) -> bool:
    """Onumuzdeki guvenilen vekiller (Caddy, web konteyneri) hep ozel aglardan gelir."""
    try:
        return ipaddress.ip_address(ip).is_private or ipaddress.ip_address(ip).is_loopback
    except ValueError:
        return False


def istemci_ip(request) -> str:
    """Gercek istemci adresi.

    🔴 ONCEKI HALI GUVENLIKSIZDI (duzeltildi 2026-09-21): X-Forwarded-For'un
    ILK degeri aliniyordu; o deger tamamen istemcinin yazdigi seydir. Caddy
    gercek adresi basligin SONUNA ekler, bastakini silmez — dolayisiyla her
    istege rastgele bir XFF yazan biri her seferinde yeni bir kovaya dusup
    hiz sinirini TAMAMEN atlayabiliyordu.

    Dogrusu: yalnizca istek guvenilen bir vekilden (ozel ag) geliyorsa XFF'e
    bakilir ve EN SAGDAKI deger alinir; aksi halde soketin kendi adresi.
    """
    peer = request.client.host if request.client else "unknown"
    if not _ozel_ip(peer):
        return peer
    xff = request.headers.get("x-forwarded-for", "")
    parcalar = [p.strip() for p in xff.split(",") if p.strip()]
    return parcalar[-1] if parcalar else peer


def _prune_stale_ips(now: float) -> None:
    global _last_cleanup
    if now - _last_cleanup < 60:
        return
    _last_cleanup = now
    for sozluk in (_hits, _auth_hits):
        for ip in list(sozluk.keys()):
            q = sozluk[ip]
            while q and now - q[0] > 60:
                q.popleft()
            if not q:
                del sozluk[ip]


def check_rate_limit(client_ip: str, sozluk: dict = None, tavan: int = None) -> bool:
    now = time.time()
    _prune_stale_ips(now)
    sozluk = _hits if sozluk is None else sozluk
    tavan = RATE_LIMIT_PER_MIN if tavan is None else tavan
    q = sozluk.setdefault(client_ip, deque())
    while q and now - q[0] > 60:
        q.popleft()
    if len(q) >= tavan:
        return False
    q.append(now)
    return True


# Izleme uclari hiz sinirinin DISINDA: /health kimliksiz ve ucuz, ama kotaya
# dahilken normal trafik kotayi doldurunca 429 donuyordu -> izleme yanlis alarm
# veriyordu (konteyner ici healthcheck ayri kovadan geldigi icin uretim
# dusmuyordu, sadece olcum yalan soyluyordu).
IZLEME_YOLLARI = frozenset({"/health"})


@app.middleware("http")
async def rate_limit_middleware(request, call_next):
    if request.url.path in IZLEME_YOLLARI:
        return await call_next(request)
    ip = istemci_ip(request)
    if request.url.path == "/api/auth/verify" and not check_rate_limit(
        ip, _auth_hits, AUTH_RATE_LIMIT_PER_MIN
    ):
        return JSONResponse(
            status_code=429, content={"detail": "Cok fazla dogrulama denemesi; sonra tekrar deneyin."}
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
    # Suzgecler (2026-09-21). Qdrant payload'inda INDEKSLI alanlar uzerinden
    # calisir: tur (keyword) ve tarih (datetime). 'jurisdiction' alani
    # payload'da YOK — onunla suzmeye kalkma, sessizce bos doner.
    tur: Optional[str] = None          # "Yargitay karari" | "Danistay karari" | "AYM karari" | "ictihat" | "kanun"
    tarih_bas: Optional[str] = None    # YYYY-MM-DD
    tarih_son: Optional[str] = None    # YYYY-MM-DD

class SourceMetadata(BaseModel):
    source: str
    authority_score: int
    jurisdiction: str
    # Konsolda kaynak panelini besleyen alanlar (2026-09-21). Hepsi Qdrant
    # payload'inda zaten duruyordu, API'den disari verilmiyordu.
    metin: str = ""
    tarih: str = ""
    daire: str = ""
    esasNo: str = ""
    kararNo: str = ""
    kurum: str = ""          # payload "tur": Yargitay karari / kanun / ...
    belgeSinifi: str = ""    # "yargi-karari" | "mevzuat"
    docId: str = ""

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


# --- SUZGECLER (2026-09-21) ------------------------------------------
# Yalniz INDEKSLI payload alanlari kullanilir; indekssiz alanla suzmek
# 9,87M noktada tam tarama demek (olculdu: sentetik indekssizken kol 5 sn,
# indeksliyken 1,3 sn). Indeksliler: tur, belgeSinifi, yargiKademesi,
# yargiMercii, daire, esasNo, kararNo, docId, sentetik, alan, kararTuru
# + 2026-09-21'de eklenen tarih (datetime).
MEVZUAT_TURLERI = {"kanun", "yönetmelik"}


def suzgec_kosullari(suzgec: dict | None) -> list:
    """ChatRequest suzgeclerini Qdrant kosullarina cevirir."""
    if not suzgec:
        return []
    kosullar = []
    tur = (suzgec.get("tur") or "").strip()
    if tur:
        kosullar.append(FieldCondition(key="tur", match=MatchValue(value=tur)))
    bas = (suzgec.get("tarih_bas") or "").strip()
    son = (suzgec.get("tarih_son") or "").strip()
    if bas or son:
        kosullar.append(
            FieldCondition(
                key="tarih",
                range=DatetimeRange(
                    gte=f"{bas}T00:00:00Z" if bas else None,
                    lte=f"{son}T23:59:59Z" if son else None,
                ),
            )
        )
    return kosullar


def mevzuat_kolu_acik(suzgec: dict | None) -> bool:
    """Tur suzgeci ictihada kilitliyse mevzuat kolunu hic calistirma."""
    tur = ((suzgec or {}).get("tur") or "").strip()
    return (not tur) or (tur in MEVZUAT_TURLERI)


def ictihat_kolu_acik(suzgec: dict | None) -> bool:
    tur = ((suzgec or {}).get("tur") or "").strip()
    return (not tur) or (tur not in MEVZUAT_TURLERI)


def payload_suzgece_uyar(p: dict, suzgec: dict | None) -> bool:
    """BM25 kolu bellek ici calisir, Qdrant suzgecinden gecmez — ayni
    kurallar burada payload uzerinde uygulanir."""
    if not suzgec:
        return True
    tur = (suzgec.get("tur") or "").strip()
    if tur and (p.get("tur") or "") != tur:
        return False
    t = (p.get("tarih") or "")[:10]
    bas, son = (suzgec.get("tarih_bas") or ""), (suzgec.get("tarih_son") or "")
    if bas and (not t or t < bas):
        return False
    if son and (not t or t > son):
        return False
    return True


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


def _mevzuat_metin(p: dict) -> str:
    """Madde metnine kenar basligini onekler.

    Kenar basligi ("Yoksulluk nafakasi") avukatin aradigi terimdir ve madde
    GOVDESINDE cogu zaman hic gecmez: TMK m.175'in metninde ne "yoksulluk" ne
    "nafaka" gecer, ikisi de yalnizca kenar basligindadir. Baslik metnin onune
    konmazsa reranker ve anahtar-orani kapisi maddeyi konuyla iliskilendiremez
    (olculdu 2026-09-21).
    """
    metin = p.get("metin", "") or ""
    baslik = (p.get("baslik", "") or "").strip()
    if not baslik:
        return metin
    if baslik.split(" \u2014 ")[-1].lower() in metin.lower():
        return metin
    return baslik + "\n" + metin


def _mevzuat_dense_ara(sorgu: str, k: int, suzgec: dict | None = None) -> list:
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
            ] + suzgec_kosullari(suzgec)
        ),
        with_payload=True,
        with_vectors=False,
    )
    docs = []
    for pt in sonuc.points:
        p = pt.payload or {}
        docs.append(
            Document(
                page_content=_mevzuat_metin(p),
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
                    "kurum": p.get("tur", ""),
                    "belgeSinifi": p.get("belgeSinifi", ""),
                },
            )
        )
    return docs


def corpus_search_mevzuat(query: str, k: int, suzgec: dict | None = None) -> list:
    """Mevzuat kolunda IKI probe: tam soru + anahtar sorgu. 2026-09-17 audit
    olcumu: tam soru embedding'i konu-yonlu sorularda kanun maddesini
    bulamıyor (TKHK m.5 top-24'te bile gorunmuyordu); stopword'suz anahtar
    probe'u m.5'i top-7'ye cikardi. Iki sonuc interleave edilir — her iki
    siralamanin da en iyileri rerank havuzuna girer."""
    tam = _mevzuat_dense_ara(query, k, suzgec)
    anahtar = _anahtar_sorgu(query)
    if not anahtar or _norm_metin(anahtar) == _norm_metin(query):
        return tam
    probe = _mevzuat_dense_ara(anahtar, max(2, k // 2), suzgec)
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


def corpus_search(query: str, k: int, suzgec: dict | None = None) -> list:
    # Uzak korpusa e5 'query: ' onekiyle semantic arama yapar.
    vec = embeddings.embed_query("query: " + query)
    sonuc = client.query_points(
        collection_name,
        query=vec,
        limit=k,
        query_filter=Filter(
            must=[FieldCondition(key="sentetik", match=MatchValue(value=False))]
            + suzgec_kosullari(suzgec)
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
                    "kurum": p.get("tur", ""),
                    "belgeSinifi": p.get("belgeSinifi", ""),
                },
            )
        )
    return docs


# Gercek sorgu kaydi. Elle yazilmis 50 soruluk setler egilim olcer; urunun
# gercek erisim kalitesi ancak KULLANICININ sordugu sorularla olculur
# (avukat "muvekkilim 3 yil 8 ay calisti, ihbar oneli ne kadar" diye sorar,
# bizim setimizdeki gibi "ihbar oneli sureleri nedir" diye degil).
# Yalnizca sorgu ve donen kaynaklar yazilir: kimlik, IP, oturum YOK.
SORGU_KAYDI = os.environ.get("SORGU_KAYDI", "/app/loglar/sorgular.jsonl").strip()


def sorgu_kaydet(query: str, ranked: list, sure_ms: int, llm: bool) -> None:
    """Sorguyu ve donen kaynaklari JSONL'e ekler. Kayit ASLA istegi dusurmez."""
    if not SORGU_KAYDI:
        return
    try:
        os.makedirs(os.path.dirname(SORGU_KAYDI), exist_ok=True)
        satir = {
            "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "sorgu": query,
            "sure_ms": sure_ms,
            "llm": llm,
            "sonuc": [
                {
                    "kaynak": d.metadata.get("source", ""),
                    "docId": d.metadata.get("docId", ""),
                    "tur": d.metadata.get("tur", ""),
                }
                for d in ranked[:5]
            ],
        }
        with open(SORGU_KAYDI, "a", encoding="utf-8") as f:
            f.write(json.dumps(satir, ensure_ascii=False) + "\n")
    except Exception as e:  # disk dolu, izin, vs. — yanit yine de gitsin
        print(f"[sorgu-kaydi] yazilamadi: {e}", flush=True)


def llm_cagir(system: str, kullanici: str, azami_token: int = 700,
              sicaklik: float = 0.2, json_modu: bool = False,
              timeout_s: int | None = None) -> str | None:
    """Tek noktadan OpenAI chat cagrisi. Anahtar yok / hata olursa None."""
    if not OPENAI_API_KEY:
        return None
    govde = {
        "model": OPENAI_MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": kullanici},
        ],
        "temperature": sicaklik,
        "max_tokens": azami_token,
    }
    if json_modu:
        govde["response_format"] = {"type": "json_object"}
    istek = urllib.request.Request(
        f"{OPENAI_BASE_URL}/chat/completions",
        data=json.dumps(govde, ensure_ascii=False).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {OPENAI_API_KEY}",
        },
        method="POST",
    )
    try:
        yanit = json.loads(
            urllib.request.urlopen(
                istek, timeout=timeout_s or OPENAI_TIMEOUT_S
            ).read()
        )
        return (yanit["choices"][0]["message"]["content"] or "").strip() or None
    except Exception as e:
        print(f"[llm] cagri basarisiz: {e}", flush=True)
        return None


def belge_metni_cikar(ad: str, ham: bytes) -> str:
    """PDF / DOCX / duz metin dosyasindan metin cikarir.

    DOCX icin ek bagimlilik yok: .docx bir zip, govde word/document.xml.
    Etiketler soyulur, paragraf sonlari korunur."""
    ad = (ad or "").lower()
    if ad.endswith(".pdf"):
        try:
            okuyucu = pypdf.PdfReader(io.BytesIO(ham))
            return "\n".join((sayfa.extract_text() or "") for sayfa in okuyucu.pages[:40])
        except Exception:
            return ""
    if ad.endswith(".docx"):
        try:
            with zipfile.ZipFile(io.BytesIO(ham)) as z:
                xml = z.read("word/document.xml").decode("utf-8", "ignore")
            xml = re.sub(r"</w:p>", "\n", xml)
            xml = re.sub(r"<w:tab[^>]*/>", "\t", xml)
            return re.sub(r"<[^>]+>", "", xml)
        except Exception:
            return ""
    try:
        return ham.decode("utf-8")
    except UnicodeDecodeError:
        try:
            return ham.decode("windows-1254")
        except Exception:
            return ""


def llm_cevap(query: str, ranked: list) -> str | None:
    """Pasajlara dayalı OpenAI sentezi. Anahtar yok / hata olursa None —
    çağıran taraf keyless extractive kompozisyona düşer."""
    if not OPENAI_API_KEY or not ranked:
        return None
    pasajlar = "\n\n".join(
        f"[{i}] (Kaynak: {d.metadata.get('source', 'Bilinmeyen')})\n"
        f"{(d.page_content or '')[:900]}"
        for i, d in enumerate(ranked, start=1)
    )
    system = (
        "Sen Türk hukuku konusunda uzman bir hukuk asistanısın. Sana kullanıcının "
        "sorusu ve numaralandırılmış yargı kararı / mevzuat pasajları verilecek.\n"
        "Kurallar:\n"
        "1) YALNIZCA verilen pasajlara dayanarak yanıt ver; pasajlarda olmayan "
        "hukuki bilgi veya karar uydurma.\n"
        "2) Her somut iddiayı [n] biçiminde pasaj numarasına atıfla.\n"
        "3) Pasajlar soruyu karşılamıyorsa bunu açıkça söyle; tahmin yürütme.\n"
        "4) Türkçe, profesyonel ve sade yaz; 350 kelimeyi aşma.\n"
        "5) Sonda tek cümlelik yasal uyarı ekle."
    )
    govde = json.dumps(
        {
            "model": OPENAI_MODEL,
            "messages": [
                {"role": "system", "content": system},
                {
                    "role": "user",
                    "content": f"Soru: {query}\n\nPasajlar:\n{pasajlar}",
                },
            ],
            "temperature": 0.2,
            "max_tokens": 700,
        },
        ensure_ascii=False,
    )
    istek = urllib.request.Request(
        f"{OPENAI_BASE_URL}/chat/completions",
        data=govde.encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {OPENAI_API_KEY}",
        },
        method="POST",
    )
    try:
        yanit = json.loads(
            urllib.request.urlopen(istek, timeout=OPENAI_TIMEOUT_S).read()
        )
        metin = (yanit["choices"][0]["message"]["content"] or "").strip()
        return metin or None
    except Exception:
        return None


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
def _mevzuat_bm25_ara(query: str, k: int, suzgec: dict | None = None) -> list:
    """Sozcuksel mevzuat kolu (bellek ici BM25).

    Dense kolun kor noktasi: 9,86M ictihata karsi 8,4K mevzuat var, ve e5
    gommesi diakritige duyarli. Olculdu 2026-09-21: ICRA sorulari (itirazin
    iptali / odeme emrine itiraz / ihtiyati haciz) dense kolda HIC gelmiyor,
    ASCII yazimda hit@5 %75'ten %50'ye dusuyor. BM25 ikisini de kapatir:
    tam sozcuk eslesmesi + sorgu/dokuman ayni normalizasyondan geciyor."""
    if not mevzuat_bm25.BM25_ENABLED:
        return []
    try:
        idx = mevzuat_bm25.indeks_al(client, collection_name)
    except Exception as e:  # indeks kurulamazsa dense kol tek basina calissin
        print(f"[mevzuat-bm25] indeks kurulamadi, atlaniyor: {e}", flush=True)
        return []
    docs = []
    for pl, skor in idx.ara(query, k):
        if not payload_suzgece_uyar(pl, suzgec):
            continue
        docs.append(
            Document(
                page_content=pl.get("metin", ""),
                metadata={
                    "source": temiz_kaynak(pl),
                    "authority_score": corpus_authority(pl),
                    "jurisdiction": "TR",
                    "tarih": pl.get("tarih", ""),
                    "daire": pl.get("daire", ""),
                    "esasNo": pl.get("esasNo", ""),
                    "kararNo": pl.get("kararNo", ""),
                    "docId": pl.get("docId", ""),
                    "tur": "mevzuat",
                    "kurum": pl.get("tur", ""),
                    "belgeSinifi": pl.get("belgeSinifi", ""),
                    "bm25_skor": round(skor, 3),
                },
            )
        )
    return docs


def corpus_rank(query: str, k: int = None, suzgec: dict | None = None) -> list:
    """Ictihat + mevzuat kollari (paralel) -> kanun-no daraltma -> tek gecis
    rerank -> garanti en iyi 2 FARKLI mevzuat madde. Uretim ve eval ortak yol."""
    k = k if k is not None else CORPUS_K
    # Tur suzgeci bir kolu tamamen disarida birakiyorsa o kolu hic calistirma:
    # bos donecek bir Qdrant sorgusu da ~5 sn suruyor.
    mev_acik = mevzuat_kolu_acik(suzgec)
    ict_acik = ictihat_kolu_acik(suzgec)
    with ThreadPoolExecutor(max_workers=3) as havuz:
        f_aday = (
            havuz.submit(corpus_search, query, max(k, CORPUS_FETCH_K), suzgec)
            if ict_acik else None
        )
        f_mev = (
            havuz.submit(corpus_search_mevzuat, query, CORPUS_MEVZUAT_FETCH_K, suzgec)
            if mev_acik else None
        )
        f_bm25 = (
            havuz.submit(_mevzuat_bm25_ara, query, CORPUS_MEVZUAT_BM25_K, suzgec)
            if CORPUS_MEVZUAT_BM25_K > 0 and mev_acik
            else None
        )
        aday = f_aday.result() if f_aday is not None else []
        mev_ham = f_mev.result() if f_mev is not None else []
        mev_bm25 = f_bm25.result() if f_bm25 is not None else []
    # Mevzuat havuzu Qdrant'tan genis cekilir (ucuz), kanun no'ya daraltilir,
    # sonra yalnizca ilk CORPUS_MEVZUAT_K'si rerank'e girer (pahali).
    mev_aday = mevzuat_havuz_daralt(query, mev_ham)[:CORPUS_MEVZUAT_K]
    # Genel havuzdan gelen mevzuat parcalari da kanun-no daraltmasindan gecsin
    mev_aday = mevzuat_havuz_daralt(
        query,
        [d for d in aday if d.metadata.get("tur") == "mevzuat"] + mev_aday,
    )
    # Sozcuksel kol daraltmanin DISINDA eklenir: kanun-no daraltmasi dense
    # havuzu icin yazilmisti, BM25 zaten tam sozcuk eslesmesiyle geliyor.
    mev_aday = _tekillestir(mev_aday + mev_bm25)
    ictihat_aday = [d for d in aday if d.metadata.get("tur") != "mevzuat"]
    skorlu = rerank_scored(query, _tekillestir(ictihat_aday + mev_aday))
    # Mevzuat secimi: rerank skoru + anahtar-cakisma boost'u. Olculdu
    # (2026-09-17): bge-reranker-base kisa kanun maddelerinde ~0 skor
    # uretip TCK Geçici-1'i TKHK'nin ustune koyabiliyor; keyword cakismasi
    # ikinci bir sinyal olarak eklenir (yalnizca mevzuat seciminde).
    # Sozcuksel skor: adaylarin TAMAMI icin (dense kolundan gelenler dahil).
    # Yalniz BM25 kolundan gelenlere boost vermek adaletsiz olurdu ve ayni
    # maddeyi iki kolun birden bulmasini odullendirmezdi.
    try:
        if MEVZUAT_BM25_BOOST <= 0:
            raise RuntimeError("bm25 kapali")  # indeksi hic kurma
        bm25_skorlari = mevzuat_bm25.skor_sozlugu(client, collection_name, query)
        bm25_azami = max(bm25_skorlari.values()) if bm25_skorlari else 0.0
    except Exception as e:
        if MEVZUAT_BM25_BOOST > 0:
            print(f"[mevzuat-bm25] skor sozlugu alinamadi: {e}", flush=True)
        bm25_skorlari, bm25_azami = {}, 0.0

    mev_skorlu = []
    for d, s in skorlu:
        if d.metadata.get("tur") != "mevzuat":
            continue
        ham_skor = s if s is not None else 0.0
        anahtar_orani = _anahtar_hit_orani(query, d.page_content)
        # BM25 skoru sorgudan sorguya olcek degistirir (terim sayisi, IDF);
        # havuzun azamisine bolunerek 0..1 arasina cekilir, boylece rerank
        # skoruyla kiyaslanabilir bir katki olur.
        bm25_ham = bm25_skorlari.get(d.metadata.get("docId", ""), 0.0)
        bm25_oran = (bm25_ham / bm25_azami) if bm25_azami > 0 else 0.0
        mev_skorlu.append(
            (d,
             ham_skor + MEVZUAT_KW_BOOST * anahtar_orani
             + MEVZUAT_BM25_BOOST * bm25_oran,
             ham_skor, anahtar_orani)
        )
    mev_skorlu.sort(key=lambda x: x[1], reverse=True)
    # Kanun dayanagi temsili garanti: en iyi MEVZUAT_GARANTI adet FARKLI
    # madde her cevapta yer
    # alir (içtihat maddeye ATIF yapar, maddeyi İÇERMEZ)
    # (dokuman, ham_rerank_skoru) — ham skor basa-koyma kararinda kullanilir
    mev_eniyi, gorulen_madde = [], set()
    for d, skor, ham_skor, anahtar_orani in mev_skorlu:
        kaynak = d.metadata.get("source", "")
        if anahtar_orani < MEVZUAT_MIN_ANAHTAR_ORANI:
            print(f"[mevzuat-elendi] skor={skor:.3f} ham={ham_skor:.3f} "
                  f"hit={anahtar_orani:.3f} < hit_min={MEVZUAT_MIN_ANAHTAR_ORANI} "
                  f":: {kaynak[:70]}", flush=True)
            continue
        if skor < MEVZUAT_MIN_SKOR:
            print(f"[mevzuat-elendi] skor={skor:.3f} ham={ham_skor:.3f} "
                  f"hit={anahtar_orani:.3f} < {MEVZUAT_MIN_SKOR} :: {kaynak[:70]}", flush=True)
            continue
        if kaynak not in gorulen_madde:
            gorulen_madde.add(kaynak)
            mev_eniyi.append((d, ham_skor))
            print(f"[mevzuat-secildi] skor={skor:.3f} ham={ham_skor:.3f} "
                  f"hit={anahtar_orani:.3f} :: {kaynak[:70]}", flush=True)
        if len(mev_eniyi) >= MEVZUAT_GARANTI:
            break
    ictihat = [d for d, _ in skorlu if d.metadata.get("tur") != "mevzuat"]
    # SIRALAMA (2026-09-21 olculdu): mevzuat sona eklenince dogru kanun
    # maddesi yapisal olarak 4.-5. siraya mahkum kaliyordu - hit@5 %75
    # iken MRR yalniz 0.185. Hukuki sunum sirasi da ayni yone isaret
    # eder: once dayanak (norm), sonra onu yorumlayan ictihat.
    # Ama kosulsuz one almak alakasiz maddeyi de vitrine tasiyor; bu yuzden
    # yalniz guclu isabetler basa gecer, zayiflar ictihadin ardina duser.
    basta = [d for d, ham in mev_eniyi if ham >= MEVZUAT_BASA_ESIK]
    sonda = [d for d, ham in mev_eniyi if ham < MEVZUAT_BASA_ESIK]
    kalan = max(0, k - len(basta) - len(sonda))
    return basta + ictihat[:kalan] + sonda


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
                docs = corpus_rank(
                    request.query,
                    suzgec={
                        "tur": request.tur,
                        "tarih_bas": request.tarih_bas,
                        "tarih_son": request.tarih_son,
                    },
                )
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
            suzgecli = any([request.tur, request.tarih_bas, request.tarih_son])
            return ChatResponse(
                text=(
                    "Seçtiğiniz süzgeçlere uyan bir pasaj bulunamadı. "
                    "Süzgeçleri gevşetip tekrar deneyin."
                    if suzgecli
                    else "Bu sorguya uygun bir pasaj külliyatta bulunamadı."
                ),
                sources=[],
            )

        # Keyless extractive kompozisyon: otorite skoruna gore numaralandir
        ranked = sorted(docs, key=lambda d: d.metadata.get("authority_score", 50), reverse=True)
        # Kaynak numaralari LLM atiflariyla ayni sirada dursun diye once kur
        kaynak_listesi = "\n".join(
            f"[{i}] {d.metadata.get('source', 'Bilinmeyen')}"
            for i, d in enumerate(ranked, start=1)
        )
        # Uretici katman: OPENAI_API_KEY varsa pasajlara dayali gercek yanit;
        # anahtar yok / cagri basarisizsa keyless extractive kompozisyona dus.
        _t0_llm = time.time()
        uretilen = llm_cevap(request.query, ranked)
        sorgu_kaydet(
            request.query, ranked, int((time.time() - _t0_llm) * 1000), bool(uretilen)
        )
        if uretilen:
            context_text = uretilen + "\n\nKaynaklar:\n" + kaynak_listesi
        else:
            parts = [
                f"[{i}] {doc.page_content}\n"
                f"    Kaynak: {doc.metadata.get('source', 'Bilinmeyen')} "
                f"(kaynak kademesi {doc.metadata.get('authority_score', 50)}/100)"
                for i, doc in enumerate(ranked, start=1)
            ]
            context_text = (
                f"Toplam {len(ranked)} kaynak bulundu. En alakalı pasajlar:\n\n"
                + "\n\n".join(parts)
                + "\n\nNot: Cevap vektör aramasından derlenmiştir; üretici dil modeli bağlı değil."
            )

        sources_meta = [
            SourceMetadata(
                source=doc.metadata.get("source", "Bilinmeyen"),
                authority_score=doc.metadata.get("authority_score", 50),
                jurisdiction=doc.metadata.get("jurisdiction", "Global"),
                # Pasajin kendi metni: konsolda kaynak panelinde acilir.
                # 4.000 kr sinir — tek bir chunk bundan uzun olmuyor.
                metin=(doc.page_content or "")[:4000],
                tarih=doc.metadata.get("tarih", ""),
                daire=doc.metadata.get("daire", ""),
                esasNo=doc.metadata.get("esasNo", ""),
                kararNo=doc.metadata.get("kararNo", ""),
                kurum=doc.metadata.get("kurum", ""),
                belgeSinifi=doc.metadata.get("belgeSinifi", ""),
                docId=doc.metadata.get("docId", ""),
            )
            for doc in ranked
        ]

        return ChatResponse(text=context_text, sources=sources_meta)
    except Exception as e:
         return ChatResponse(text=f"Hata: {str(e)}", sources=[])


class SozlesmeRisk(BaseModel):
    madde: str = ""       # sözleşmedeki ilgili madde/cümle (alıntı)
    bulgu: str            # ne sorunlu
    onem: str = "orta"    # yuksek | orta | dusuk
    dayanak: List[int] = []   # kaynak numaraları ([n])


class SozlesmeAnaliz(BaseModel):
    filename: str
    status: str
    tur: str = ""             # sözleşmenin türü (kira, iş, satış…)
    ozet: str = ""
    riskler: List[SozlesmeRisk] = []
    eksikler: List[str] = []
    analysis: str = ""        # düz metin özet (eski istemciler için)
    karakter: int = 0
    sources: List[SourceMetadata] = []
    uyari: str = ""


SOZLESME_SISTEM = (
    "Sen Türk hukuku alanında uzman bir sözleşme denetçisisin. Sana bir "
    "sözleşmenin metni ve külliyattan seçilmiş numaralı kanun/içtihat "
    "pasajları verilecek.\n"
    "Kurallar:\n"
    "1) YALNIZCA sözleşme metnine ve verilen pasajlara dayan; pasajlarda "
    "olmayan hukuki kural uydurma.\n"
    "2) Riskleri sözleşmeden ALINTIYLA göster — hangi madde/cümle sorunlu.\n"
    "3) Bir riski bir pasaj destekliyorsa numarasını 'dayanak' dizisine yaz; "
    "destekleyen pasaj yoksa diziyi BOŞ bırak, uydurma atıf verme.\n"
    "4) 'eksikler' sözleşmede bulunmayan ama bu tür sözleşmede beklenen "
    "maddelerdir.\n"
    "5) Türkçe yaz. Çıktı SADECE şu JSON: "
    '{"tur": "...", "ozet": "...", "riskler": [{"madde": "...", "bulgu": "...", '
    '"onem": "yuksek|orta|dusuk", "dayanak": [1,2]}], "eksikler": ["..."]}'
)


@app.post("/api/analyze-contract")
async def analyze_contract(file: UploadFile = File(...), api_key: str = Security(get_api_key)):
    raw = await file.read()
    if len(raw) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Dosya 10 MB sınırını aşıyor.")
    STATS["contract"] += 1

    metin = belge_metni_cikar(file.filename or "", raw).strip()
    if len(metin) < 200:
        return SozlesmeAnaliz(
            filename=file.filename or "",
            status="bos",
            analysis=(
                "Belgeden okunabilir metin çıkarılamadı. Taranmış (görüntü) PDF "
                "ise metin katmanı yok — OCR'lı bir sürüm yükleyin."
            ),
            karakter=len(metin),
        )

    # Arama sorgusu: sözleşmenin BAŞI (taraflar/konu) + türünü ele veren
    # başlık. Tüm metni gömmek gürültü: 40 sayfalık metnin vektörü hiçbir
    # şeye yakın değil.
    sorgu = re.sub(r"\s+", " ", metin[:800])
    docs = corpus_rank(sorgu) if REMOTE_MODE else \
        vector_store.as_retriever(search_kwargs={"k": 3}).invoke(sorgu)

    sources_meta = [
        SourceMetadata(
            source=d.metadata.get("source", "Bilinmeyen"),
            authority_score=d.metadata.get("authority_score", 50),
            jurisdiction=d.metadata.get("jurisdiction", "Global"),
            metin=(d.page_content or "")[:4000],
            tarih=d.metadata.get("tarih", ""),
            daire=d.metadata.get("daire", ""),
            esasNo=d.metadata.get("esasNo", ""),
            kararNo=d.metadata.get("kararNo", ""),
            kurum=d.metadata.get("kurum", ""),
            belgeSinifi=d.metadata.get("belgeSinifi", ""),
            docId=d.metadata.get("docId", ""),
        )
        for d in docs
    ]

    pasajlar = "\n\n".join(
        f"[{i}] (Kaynak: {d.metadata.get('source', 'Bilinmeyen')})\n"
        f"{(d.page_content or '')[:900]}"
        for i, d in enumerate(docs, start=1)
    )
    # Sözleşme metni kırpılır: gpt-4o-mini bağlamı bol ama maliyet metinle
    # doğrusal artıyor; 24.000 karakter ~ 12 sayfa, tipik sözleşmeyi kapsıyor.
    kirpildi = len(metin) > SOZLESME_AZAMI_KARAKTER
    govde = metin[:SOZLESME_AZAMI_KARAKTER]
    ham = llm_cagir(
        SOZLESME_SISTEM,
        f"SÖZLEŞME METNİ:\n{govde}\n\nPASAJLAR:\n{pasajlar or '(pasaj yok)'}",
        azami_token=1600,
        json_modu=True,
        timeout_s=SOZLESME_TIMEOUT_S,
    )

    if not ham:
        # Anahtar yok / çağrı düştü: uydurma analiz üretme, açıkça söyle.
        return SozlesmeAnaliz(
            filename=file.filename or "",
            status="llm-yok",
            karakter=len(metin),
            sources=sources_meta,
            analysis=(
                "Belge okundu ancak analiz katmanı şu an çalışmıyor "
                "(dil modeli yanıt vermedi). Aşağıda yalnızca sözleşmenin "
                "konusuyla eşleşen mevzuat/içtihat pasajları listelenmiştir."
            ),
        )

    try:
        veri = json.loads(ham)
    except json.JSONDecodeError:
        veri = {"ozet": ham, "riskler": [], "eksikler": []}

    riskler = []
    for r in (veri.get("riskler") or [])[:20]:
        if not isinstance(r, dict):
            continue
        dayanak = [
            n for n in (r.get("dayanak") or [])
            if isinstance(n, int) and 1 <= n <= len(sources_meta)
        ]
        riskler.append(
            SozlesmeRisk(
                madde=str(r.get("madde", ""))[:600],
                bulgu=str(r.get("bulgu", ""))[:800],
                onem=str(r.get("onem", "orta")).lower(),
                dayanak=dayanak,
            )
        )

    ozet = str(veri.get("ozet", ""))[:1500]
    eksikler = [str(e)[:300] for e in (veri.get("eksikler") or [])[:15]]
    duz = ozet
    if riskler:
        duz += "\n\nRiskli görülen noktalar:\n" + "\n".join(
            f"- {r.bulgu}" for r in riskler
        )

    return SozlesmeAnaliz(
        filename=file.filename or "",
        status="success",
        tur=str(veri.get("tur", ""))[:120],
        ozet=ozet,
        riskler=riskler,
        eksikler=eksikler,
        analysis=duz,
        karakter=len(metin),
        sources=sources_meta,
        uyari=(
            "Sözleşmenin ilk ~12 sayfası incelendi; gerisi analize girmedi."
            if kirpildi else ""
        ),
    )


# --- DILEKCE URETIMI (2026-09-21) --------------------------------------
# Rakiplerin asil sattigi sey arama degil, belge uretimi. Hat sohbetle ayni:
# once korpustan dayanak cek, sonra YALNIZ o dayanaklarla yazdir. Fark,
# ciktinin serbest metin degil yapili bir dilekce olmasi — kullanici
# duzeltip Word olarak indirebilsin diye alanlar ayri doner.

DILEKCE_TURLERI = {
    "dava": "dava dilekçesi (HMK m.119 unsurlarıyla)",
    "cevap": "cevap dilekçesi (HMK m.129 unsurlarıyla)",
    "cevaba-cevap": "cevaba cevap (replik) dilekçesi",
    "istinaf": "istinaf başvuru dilekçesi (HMK m.342)",
    "temyiz": "temyiz dilekçesi",
    "itiraz-iptali": "itirazın iptali davası dilekçesi (İİK m.67)",
    "ihtarname": "noter ihtarnamesi",
    "sikayet": "savcılığa suç duyurusu / şikâyet dilekçesi",
    "cevap-idari": "idari dava (iptal) dilekçesi (İYUK m.3)",
    "beyan": "beyan dilekçesi",
}


class DilekceRequest(BaseModel):
    tur: str = "dava"
    olay: str                       # kullanıcının anlattığı maddi olay
    mahkeme: Optional[str] = ""     # "İstanbul 3. Asliye Hukuk Mahkemesi"
    davaci: Optional[str] = ""
    davali: Optional[str] = ""
    talep: Optional[str] = ""       # istenen sonuç
    dosya_no: Optional[str] = ""
    ek_notlar: Optional[str] = ""


class Dilekce(BaseModel):
    tur: str
    baslik: str = ""
    mahkeme: str = ""
    taraflar: str = ""
    konu: str = ""
    aciklamalar: List[str] = []
    hukuki_sebepler: List[str] = []
    deliller: List[str] = []
    sonuc: str = ""
    sources: List[SourceMetadata] = []
    uyari: str = ""


DILEKCE_SISTEM = (
    "Sen Türk hukukunda deneyimli bir avukatsın ve dilekçe yazıyorsun. Sana "
    "dilekçe türü, maddi olay ve külliyattan seçilmiş numaralı kanun/içtihat "
    "pasajları verilecek.\n"
    "Kurallar:\n"
    "1) Hukuki dayanağı YALNIZCA verilen pasajlardan al. Pasajlarda olmayan "
    "madde numarası, karar veya kural YAZMA.\n"
    "2) 'aciklamalar' maddi olayın numaralı anlatımıdır; dayanağa atıf "
    "yaparken [n] biçimini kullan.\n"
    "3) 'hukuki_sebepler' yalnızca pasajlarda geçen mevzuattan oluşur; "
    "pasajlarda kanun metni yoksa 'İlgili mevzuat' yazıp geç, uydurma.\n"
    "4) Kullanıcının vermediği isim, tarih, tutar, dosya numarası UYDURMA — "
    "eksikse '[...]' köşeli parantezli boşluk bırak.\n"
    "5) Türkçe, resmî dilekçe üslubu. Çıktı SADECE şu JSON: "
    '{"baslik": "...", "konu": "...", "aciklamalar": ["..."], '
    '"hukuki_sebepler": ["..."], "deliller": ["..."], "sonuc": "..."}'
)


@app.post("/api/dilekce", response_model=Dilekce)
async def dilekce_uret(request: DilekceRequest, api_key: str = Security(get_api_key)):
    STATS["dilekce"] = STATS.get("dilekce", 0) + 1
    tur_adi = DILEKCE_TURLERI.get(request.tur, DILEKCE_TURLERI["dava"])

    # Dayanak aramasi: olay + talep. Dilekce turu sorguya girmez (usul
    # kelimeleri korpusta her yerde geciyor, gurultu yapiyor).
    sorgu = " ".join(x for x in [request.olay, request.talep or ""] if x)[:1200]
    docs = corpus_rank(sorgu) if REMOTE_MODE else \
        vector_store.as_retriever(search_kwargs={"k": 3}).invoke(sorgu)

    sources_meta = [
        SourceMetadata(
            source=d.metadata.get("source", "Bilinmeyen"),
            authority_score=d.metadata.get("authority_score", 50),
            jurisdiction=d.metadata.get("jurisdiction", "Global"),
            metin=(d.page_content or "")[:4000],
            tarih=d.metadata.get("tarih", ""),
            daire=d.metadata.get("daire", ""),
            esasNo=d.metadata.get("esasNo", ""),
            kararNo=d.metadata.get("kararNo", ""),
            kurum=d.metadata.get("kurum", ""),
            belgeSinifi=d.metadata.get("belgeSinifi", ""),
            docId=d.metadata.get("docId", ""),
        )
        for d in docs
    ]
    pasajlar = "\n\n".join(
        f"[{i}] (Kaynak: {d.metadata.get('source', 'Bilinmeyen')})\n"
        f"{(d.page_content or '')[:900]}"
        for i, d in enumerate(docs, start=1)
    )

    taraflar = []
    if request.davaci:
        taraflar.append(f"DAVACI: {request.davaci}")
    if request.davali:
        taraflar.append(f"DAVALI: {request.davali}")

    kullanici = (
        f"DİLEKÇE TÜRÜ: {tur_adi}\n"
        f"MAHKEME/MERCİ: {request.mahkeme or '[...]'}\n"
        f"DOSYA NO: {request.dosya_no or '[...]'}\n"
        f"TARAFLAR: {'; '.join(taraflar) or '[...]'}\n"
        f"TALEP: {request.talep or '(belirtilmedi)'}\n"
        f"EK NOTLAR: {request.ek_notlar or '-'}\n\n"
        f"MADDİ OLAY:\n{request.olay}\n\n"
        f"PASAJLAR:\n{pasajlar or '(pasaj yok)'}"
    )
    ham = llm_cagir(
        DILEKCE_SISTEM, kullanici,
        azami_token=2200, sicaklik=0.3, json_modu=True,
        timeout_s=SOZLESME_TIMEOUT_S,
    )
    if not ham:
        return Dilekce(
            tur=request.tur,
            sources=sources_meta,
            uyari=(
                "Dilekçe üretilemedi: dil modeli yanıt vermedi. Aşağıdaki "
                "pasajlar olayla eşleşen dayanaklardır."
            ),
        )
    try:
        veri = json.loads(ham)
    except json.JSONDecodeError:
        veri = {"konu": "", "aciklamalar": [ham], "hukuki_sebepler": [], "deliller": [], "sonuc": ""}

    def liste(ad, sinir=25, uzunluk=1200):
        return [str(x)[:uzunluk] for x in (veri.get(ad) or [])[:sinir] if str(x).strip()]

    return Dilekce(
        tur=request.tur,
        baslik=str(veri.get("baslik", ""))[:200],
        mahkeme=request.mahkeme or "",
        taraflar="\n".join(taraflar),
        konu=str(veri.get("konu", ""))[:600],
        aciklamalar=liste("aciklamalar"),
        hukuki_sebepler=liste("hukuki_sebepler", 20, 300),
        deliller=liste("deliller", 20, 300),
        sonuc=str(veri.get("sonuc", ""))[:1500],
        sources=sources_meta,
        uyari=(
            "Taslaktır. Dayanaklar aşağıdaki pasajlardan üretildi; imzalamadan "
            "önce her atfı kaynağından doğrulayın."
        ),
    )


# --- .docx URETIMI (bagimliliksiz) -------------------------------------
# python-docx eklemedik: .docx bir zip + birkac XML. Tek bir sablondan
# paragraf uretmek 60 satir; imaja 9,9 GB'lik yiginin ustune yeni bagimlilik
# bindirmeye degmez.
def _xml_kacis(m: str) -> str:
    return (
        (m or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    )


def docx_yap(paragraflar: list) -> bytes:
    """paragraflar: [(metin, stil)] — stil: 'baslik' | 'ortali' | 'kalin' | ''."""
    govde = []
    for metin, stil in paragraflar:
        hizala = '<w:jc w:val="center"/>' if stil in ("baslik", "ortali") else ""
        kalin = "<w:b/>" if stil in ("baslik", "kalin") else ""
        boyut = '<w:sz w:val="28"/>' if stil == "baslik" else '<w:sz w:val="22"/>'
        govde.append(
            "<w:p><w:pPr>"
            f"{hizala}<w:spacing w:after=\"120\"/>"
            f"<w:rPr>{kalin}{boyut}</w:rPr>"
            "</w:pPr>"
            f"<w:r><w:rPr>{kalin}{boyut}</w:rPr>"
            f'<w:t xml:space="preserve">{_xml_kacis(metin)}</w:t></w:r></w:p>'
        )
    document = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        f'<w:body>{"".join(govde)}</w:body></w:document>'
    )
    content_types = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
        "</Types>"
    )
    rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
        "</Relationships>"
    )
    tampon = io.BytesIO()
    with zipfile.ZipFile(tampon, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", content_types)
        z.writestr("_rels/.rels", rels)
        # Word bazi surumlerde govdenin kendi iliski parcasini arar; bos da
        # olsa bulunmazsa "onarilmasi gerekiyor" uyarisi veriyor.
        z.writestr(
            "word/_rels/document.xml.rels",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"/>',
        )
        z.writestr("word/document.xml", document)
    return tampon.getvalue()


def dilekce_paragraflari(d: Dilekce) -> list:
    p = []
    if d.mahkeme:
        p.append((d.mahkeme.upper() + "'NE", "baslik"))
    elif d.baslik:
        p.append((d.baslik.upper(), "baslik"))
    p.append(("", ""))
    for satir in (d.taraflar or "").split("\n"):
        if satir.strip():
            p.append((satir, ""))
    if d.konu:
        p.append(("KONU: " + d.konu, ""))
    p.append(("", ""))
    if d.aciklamalar:
        p.append(("AÇIKLAMALAR", "kalin"))
        for i, a in enumerate(d.aciklamalar, start=1):
            p.append((f"{i}. {a}", ""))
        p.append(("", ""))
    if d.hukuki_sebepler:
        p.append(("HUKUKİ SEBEPLER", "kalin"))
        p.append(("; ".join(d.hukuki_sebepler), ""))
        p.append(("", ""))
    if d.deliller:
        p.append(("DELİLLER", "kalin"))
        p.append(("; ".join(d.deliller), ""))
        p.append(("", ""))
    if d.sonuc:
        p.append(("SONUÇ VE İSTEM", "kalin"))
        p.append((d.sonuc, ""))
    p.append(("", ""))
    if d.sources:
        p.append(("KULLANILAN KAYNAKLAR", "kalin"))
        for i, k in enumerate(d.sources, start=1):
            p.append((f"[{i}] {k.source}", ""))
    return p


@app.post("/api/dilekce/docx")
async def dilekce_docx(d: Dilekce, api_key: str = Security(get_api_key)):
    """Duzenlenmis dilekceyi Word dosyasina cevirir. Istemci metni degistirmis
    olabilir; sunucu yeniden uretmez, GELENI yazar."""
    icerik = docx_yap(dilekce_paragraflari(d))
    ad = f"dilekce-{d.tur or 'taslak'}.docx"
    return Response(
        content=icerik,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{ad}"'},
    )


# --- DOSYA / PROJE ALANI (2026-09-21) ----------------------------------
# Avukat tek sorgu sormuyor; bir DOSYA uzerinde calisiyor. Aramalar, uretilen
# dilekceler ve sozlesme analizleri o dosyanin altinda birikmeli.
#
# Depo: SQLite, /app/loglar altinda (compose'da ./api/loglar olarak host'a
# baglanmis tek kalici dizin — konteyner yeniden yaratilinca kaybolmaz).
# localStorage KULLANILMADI: tarayici temizlenince musterinin dosyasi ucar,
# bu bir hukuk urununde kabul edilemez.
#
# ⚠️ Kullanici kimligi web katmanindan `X-Kullanici` basligiyla gelir (lisans
# anahtarinin SHA-256'si). API'yi dogrudan API anahtariyla cagiran biri baska
# bir kullaniciyi taklit edebilir; ayrim musteri izolasyonu icin degil, ayni
# kurulumdaki kullanicilarin dosyalarini ayirmak icin. Gercek izolasyon
# gerekirse anahtar basina ayri API anahtari sart.
import sqlite3

DOSYA_DB = os.environ.get("DOSYA_DB", "/app/loglar/dosyalar.db")


def db_ac() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DOSYA_DB), exist_ok=True)
    baglanti = sqlite3.connect(DOSYA_DB, timeout=10)
    baglanti.row_factory = sqlite3.Row
    baglanti.execute("PRAGMA journal_mode=WAL")
    baglanti.executescript(
        """
        CREATE TABLE IF NOT EXISTS dosyalar (
            id TEXT PRIMARY KEY,
            kullanici TEXT NOT NULL,
            ad TEXT NOT NULL,
            aciklama TEXT DEFAULT '',
            olusturma TEXT NOT NULL,
            guncelleme TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS kayitlar (
            id TEXT PRIMARY KEY,
            dosya_id TEXT NOT NULL,
            tur TEXT NOT NULL,
            baslik TEXT DEFAULT '',
            icerik TEXT DEFAULT '',
            veri TEXT DEFAULT '',
            olusturma TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS test_notlari (
            id TEXT PRIMARY KEY,
            kullanici TEXT NOT NULL,
            alan TEXT NOT NULL,
            soru TEXT DEFAULT '',
            cevap TEXT DEFAULT '',
            kaynaklar TEXT DEFAULT '',
            karar TEXT DEFAULT '',
            dogru_madde TEXT DEFAULT '',
            notu TEXT DEFAULT '',
            saniye REAL DEFAULT 0,
            olusturma TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS ix_dosya_kullanici ON dosyalar(kullanici);
        CREATE INDEX IF NOT EXISTS ix_kayit_dosya ON kayitlar(dosya_id);
        CREATE INDEX IF NOT EXISTS ix_test_kullanici ON test_notlari(kullanici);
        """
    )
    return baglanti


def kullanici_kimligi(request: Request) -> str:
    """Web katmani lisans anahtarinin SHA-256'sini yollar. Yoksa 'ortak'
    havuzuna dusulur (eski istemciler kirilmasin)."""
    ham = (request.headers.get("X-Kullanici") or "").strip()
    return re.sub(r"[^a-zA-Z0-9_-]", "", ham)[:64] or "ortak"


def _simdi() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class DosyaRequest(BaseModel):
    ad: str
    aciklama: Optional[str] = ""


class KayitRequest(BaseModel):
    tur: str = "not"          # not | sorgu | dilekce | analiz
    baslik: Optional[str] = ""
    icerik: Optional[str] = ""
    veri: Optional[dict] = None   # yapılı içerik (dilekçe/analiz JSON'u)


@app.get("/api/dosyalar")
async def dosyalari_listele(request: Request, api_key: str = Security(get_api_key)):
    kim = kullanici_kimligi(request)
    with db_ac() as b:
        satirlar = b.execute(
            "SELECT d.*, (SELECT COUNT(*) FROM kayitlar k WHERE k.dosya_id = d.id) AS kayit "
            "FROM dosyalar d WHERE kullanici = ? ORDER BY guncelleme DESC LIMIT 200",
            (kim,),
        ).fetchall()
    return {"dosyalar": [dict(r) for r in satirlar]}


@app.post("/api/dosyalar")
async def dosya_olustur(govde: DosyaRequest, request: Request,
                        api_key: str = Security(get_api_key)):
    ad = (govde.ad or "").strip()[:200]
    if not ad:
        raise HTTPException(status_code=400, detail="Dosya adı boş olamaz.")
    kim, kimlik, t = kullanici_kimligi(request), uuidlib.uuid4().hex, _simdi()
    with db_ac() as b:
        b.execute(
            "INSERT INTO dosyalar (id, kullanici, ad, aciklama, olusturma, guncelleme) "
            "VALUES (?,?,?,?,?,?)",
            (kimlik, kim, ad, (govde.aciklama or "")[:1000], t, t),
        )
    return {"id": kimlik, "ad": ad}


@app.get("/api/dosyalar/{dosya_id}")
async def dosya_getir(dosya_id: str, request: Request,
                      api_key: str = Security(get_api_key)):
    kim = kullanici_kimligi(request)
    with db_ac() as b:
        d = b.execute(
            "SELECT * FROM dosyalar WHERE id = ? AND kullanici = ?", (dosya_id, kim)
        ).fetchone()
        if not d:
            raise HTTPException(status_code=404, detail="Dosya bulunamadı.")
        kayitlar = b.execute(
            "SELECT * FROM kayitlar WHERE dosya_id = ? ORDER BY olusturma DESC LIMIT 500",
            (dosya_id,),
        ).fetchall()
    return {
        "dosya": dict(d),
        "kayitlar": [
            {**dict(k), "veri": json.loads(k["veri"]) if k["veri"] else None}
            for k in kayitlar
        ],
    }


@app.post("/api/dosyalar/{dosya_id}/kayit")
async def kayit_ekle(dosya_id: str, govde: KayitRequest, request: Request,
                     api_key: str = Security(get_api_key)):
    kim = kullanici_kimligi(request)
    with db_ac() as b:
        sahip = b.execute(
            "SELECT 1 FROM dosyalar WHERE id = ? AND kullanici = ?", (dosya_id, kim)
        ).fetchone()
        if not sahip:
            raise HTTPException(status_code=404, detail="Dosya bulunamadı.")
        kimlik, t = uuidlib.uuid4().hex, _simdi()
        b.execute(
            "INSERT INTO kayitlar (id, dosya_id, tur, baslik, icerik, veri, olusturma) "
            "VALUES (?,?,?,?,?,?,?)",
            (
                kimlik, dosya_id, (govde.tur or "not")[:20],
                (govde.baslik or "")[:300], (govde.icerik or "")[:200000],
                json.dumps(govde.veri, ensure_ascii=False) if govde.veri else "",
                t,
            ),
        )
        b.execute("UPDATE dosyalar SET guncelleme = ? WHERE id = ?", (t, dosya_id))
    return {"id": kimlik}


@app.delete("/api/dosyalar/{dosya_id}/kayit/{kayit_id}")
async def kayit_sil(dosya_id: str, kayit_id: str, request: Request,
                    api_key: str = Security(get_api_key)):
    kim = kullanici_kimligi(request)
    with db_ac() as b:
        sahip = b.execute(
            "SELECT 1 FROM dosyalar WHERE id = ? AND kullanici = ?", (dosya_id, kim)
        ).fetchone()
        if not sahip:
            raise HTTPException(status_code=404, detail="Dosya bulunamadı.")
        b.execute("DELETE FROM kayitlar WHERE id = ? AND dosya_id = ?", (kayit_id, dosya_id))
    return {"silindi": True}


@app.delete("/api/dosyalar/{dosya_id}")
async def dosya_sil(dosya_id: str, request: Request,
                    api_key: str = Security(get_api_key)):
    kim = kullanici_kimligi(request)
    with db_ac() as b:
        n = b.execute(
            "DELETE FROM dosyalar WHERE id = ? AND kullanici = ?", (dosya_id, kim)
        ).rowcount
        if not n:
            raise HTTPException(status_code=404, detail="Dosya bulunamadı.")
        b.execute("DELETE FROM kayitlar WHERE dosya_id = ?", (dosya_id,))
    return {"silindi": True}


# --- Saha testi notlari ---------------------------------------------------
#
# Neden ayri tablo: avukat denemesinde olculen sey "cevap dogru mu" degil,
# "bunu bir dilekcede kullanir miydin" — bu yargiyi ancak insan verir ve
# kaybolmamasi gerekir. hit@5 otomatik olculuyor (eval_*.py); burasi onun
# insan tarafi. Dosyalar tablosuna karistirilmadi: dosyalar musteri isi,
# bu ise urun gelistirme verisi.

KARARLAR = {"evet", "duzelterek", "hayir"}
ALANLAR = {"arama", "sozlesme", "dilekce", "genel"}


class TestNotuRequest(BaseModel):
    alan: str = "arama"                  # arama | sozlesme | dilekce | genel
    soru: Optional[str] = ""
    cevap: Optional[str] = ""
    kaynaklar: Optional[list] = None     # gosterilen kaynak basliklari
    karar: Optional[str] = ""            # evet | duzelterek | hayir
    dogru_madde: Optional[str] = ""      # "olmasi gereken" — kacirilan madde
    notu: Optional[str] = ""
    saniye: Optional[float] = 0


@app.post("/api/test-notu")
async def test_notu_ekle(govde: TestNotuRequest, request: Request,
                         api_key: str = Security(get_api_key)):
    karar = (govde.karar or "").strip().lower()
    alan = (govde.alan or "arama").strip().lower()
    if alan not in ALANLAR:
        raise HTTPException(status_code=400, detail="Bilinmeyen alan.")
    if karar and karar not in KARARLAR:
        raise HTTPException(status_code=400, detail="Bilinmeyen karar.")
    if not karar and not (govde.notu or "").strip():
        raise HTTPException(status_code=400, detail="Karar ya da not gerekli.")
    kimlik = uuidlib.uuid4().hex
    with db_ac() as b:
        b.execute(
            "INSERT INTO test_notlari (id, kullanici, alan, soru, cevap, kaynaklar,"
            " karar, dogru_madde, notu, saniye, olusturma) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (
                kimlik, kullanici_kimligi(request), alan,
                (govde.soru or "")[:2000], (govde.cevap or "")[:8000],
                json.dumps((govde.kaynaklar or [])[:10], ensure_ascii=False),
                karar, (govde.dogru_madde or "")[:200], (govde.notu or "")[:4000],
                float(govde.saniye or 0), _simdi(),
            ),
        )
    return {"id": kimlik}


@app.get("/api/test-notlari")
async def test_notlari(api_key: str = Security(get_api_key)):
    """Tum notlar tek havuzda: degerlendirmeyi kim yazdiysa yazsin,
    urun kararini toplamina bakarak veriyoruz."""
    with db_ac() as b:
        satirlar = [dict(r) for r in b.execute(
            "SELECT * FROM test_notlari ORDER BY olusturma DESC LIMIT 500"
        ).fetchall()]
    ozet = {"evet": 0, "duzelterek": 0, "hayir": 0, "notsuz": 0}
    alan_dagilimi: dict = {}
    for r in satirlar:
        if r["karar"] in KARARLAR:
            ozet[r["karar"]] += 1
        else:
            ozet["notsuz"] += 1        # karar verilmemis, serbest not
        alan_dagilimi[r["alan"]] = alan_dagilimi.get(r["alan"], 0) + 1
        try:
            r["kaynaklar"] = json.loads(r["kaynaklar"] or "[]")
        except Exception:
            r["kaynaklar"] = []
    kararli = ozet["evet"] + ozet["duzelterek"] + ozet["hayir"]
    return {
        "notlar": satirlar,
        "ozet": ozet,
        "alan": alan_dagilimi,
        "kararli": kararli,
        "kullanilabilir_oran": round(
            100 * (ozet["evet"] + ozet["duzelterek"]) / kararli) if kararli else None,
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

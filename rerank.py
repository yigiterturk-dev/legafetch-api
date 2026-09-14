"""Cross-encoder reranker — hibrit aramanin ustu.

Yaklasim: corpus_search zaten dense+BM25 ile aday uretir (genis CORPUS_FETCH_K).
CrossEncoder sorgu-pasaj ciftlerini birlikte okuyup daha isabetli skor uretir;
en alakali top_n dondurulur. Model ilk cagride bir kez yuklenir (lazy).

Model: BAAI/bge-reranker-base (Apache-2.0, cok dilli, CPU dostu).
Env:   RERANK_ENABLED (vars 1), RERANK_MODEL, RERANK_MAX_LEN.
"""
import os
import threading

_lock = threading.Lock()
_model = None

RERANK_MODEL = os.environ.get("RERANK_MODEL", "BAAI/bge-reranker-base").strip()
RERANK_ENABLED = os.environ.get("RERANK_ENABLED", "1").strip() == "1"
RERANK_MAX_LENGTH = int(os.environ.get("RERANK_MAX_LENGTH", "384"))


def _get_model():
    global _model
    if _model is None:
        with _lock:
            if _model is None:
                from sentence_transformers import CrossEncoder

                _model = CrossEncoder(
                    RERANK_MODEL, max_length=RERANK_MAX_LENGTH, device="cpu"
                )
    return _model


RERANK_DOC_CHARS = int(os.environ.get("RERANK_DOC_CHARS", "900"))


def rerank_scored(query: str, docs: list) -> list:
    """Tum dokumanlari TEK gecişte skorlar; (doc, skor) listesi, skora gore azalan.
    Reranker kapaliysa veya duserse orijinal sira korunur (fail-open), skor None."""
    if not docs:
        return []
    if not RERANK_ENABLED:
        return [(d, None) for d in docs]
    try:
        model = _get_model()
        pairs = [[query, (d.page_content or "")[:RERANK_DOC_CHARS]] for d in docs]
        scores = model.predict(pairs, batch_size=8, show_progress_bar=False)
        return sorted(zip(docs, (float(x) for x in scores)), key=lambda x: x[1], reverse=True)
    except Exception:
        return [(d, None) for d in docs]


def rerank(query: str, docs: list, top_n: int) -> list:
    """Dokumanlari cross-encoder skoruyla yeniden siralar, ilk top_n dondurur."""
    if not docs or not RERANK_ENABLED or top_n >= len(docs):
        return docs[:top_n]
    return [d for d, _ in rerank_scored(query, docs)[:top_n]]

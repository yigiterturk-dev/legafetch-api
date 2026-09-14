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


def rerank(query: str, docs: list, top_n: int) -> list:
    """Dokumanlari cross-encoder skoruyla yeniden siralar, ilk top_n dondurur."""
    if not docs:
        return docs
    if not RERANK_ENABLED or top_n >= len(docs):
        return docs[:top_n]
    try:
        model = _get_model()
        pairs = [[query, (d.page_content or "")[:1200]] for d in docs]
        scores = model.predict(pairs, batch_size=8, show_progress_bar=False)
        sirali = sorted(zip(docs, scores), key=lambda x: float(x[1]), reverse=True)
        return [d for d, _ in sirali[:top_n]]
    except Exception:
        # Reranker her sebeple olmezse eski sirayla devam et (fail-open)
        return docs[:top_n]

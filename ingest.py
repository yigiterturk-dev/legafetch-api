import json
import argparse
import os
import hashlib
import uuid as uuidlib
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams
from langchain_core.documents import Document

def ingest_data(file_path: str):
    print(f"[*] Ingesting data from {file_path}...")

    print("[*] Loading embedding model (paraphrase-multilingual-MiniLM-L12-v2)...")
    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    )

    print("[*] Connecting to local Qdrant storage...")
    qdrant_path = os.path.join(os.path.dirname(__file__), "qdrant_storage")
    client = QdrantClient(path=qdrant_path)
    collection_name = "legal_documents"

    if not client.collection_exists(collection_name):
        print(f"[*] Creating new collection: {collection_name}")
        client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=384, distance=Distance.COSINE),
        )

    vector_store = QdrantVectorStore(
        client=client,
        collection_name=collection_name,
        embedding=embeddings,
    )

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            raw_data = json.load(f)

        docs = [
            Document(
                page_content=item.get("content", ""),
                metadata={
                    "source": item.get("source", "Bilinmeyen Kaynak"),
                    "jurisdiction": item.get("jurisdiction", "Global"),
                    "authority_score": item.get("authority_score", 50),
                },
            )
            for item in raw_data if "content" in item
        ]

        if not docs:
            print("[!] Hata: JSON dosyasında geçerli veri bulunamadı. JSON içinde 'content' ve 'source' anahtarları olduğundan emin olun.")
            return

        print(f"[*] {len(docs)} adet hukuki belge vektörel formata çevriliyor...")
        # Idempotent: ayni icerik tekrar ingest edilirse duplicate olusmaz
        def stable_id(doc: Document) -> str:
            return str(uuidlib.UUID(hashlib.sha256(doc.page_content.encode("utf-8")).hexdigest()[:32]))

        vector_store.add_documents(docs, ids=[stable_id(d) for d in docs])
        client.close()
        print("[+] Tamam! Verileriniz './qdrant_storage' klasöründe kalıcı olarak kaydedildi.")

    except Exception as e:
        print(f"[!] Dosya okuma veya vektörizasyon hatası: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="LegaFetch: Özel hukuki pasajlarınızı Qdrant Vektör veritabanına kalıcı olarak ekler.")
    parser.add_argument("filepath", help="Yüklemek istediğiniz JSON dosyasının yolu.")
    args = parser.parse_args()

    if not os.path.exists(args.filepath):
        print(f"[!] Hata: Belirtilen dosya bulunamadı: {args.filepath}")
    else:
        ingest_data(args.filepath)

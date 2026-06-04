from __future__ import annotations

from pathlib import Path

from langchain_core.tools import tool

NOTES_DIR = Path(__file__).parent.parent.parent / "data" / "astrology_notes"
CHROMA_DIR = Path(__file__).parent.parent.parent / "chroma_db"

_collection = None


def _get_collection():
    global _collection
    if _collection is not None:
        return _collection

    try:
        import chromadb
        from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
    except ImportError:
        raise ImportError("chromadb and sentence-transformers are required. Run: pip install chromadb sentence-transformers")

    ef = SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    collection = client.get_or_create_collection("astrology_notes", embedding_function=ef)

    # build index on first call if collection is empty
    if collection.count() == 0:
        _index_notes(collection)

    _collection = collection
    return collection


def _index_notes(collection) -> None:
    if not NOTES_DIR.exists():
        return

    docs, ids, metadatas = [], [], []
    for note_file in sorted(NOTES_DIR.glob("*.md")):
        text = note_file.read_text(encoding="utf-8")
        # split on blank lines to get natural paragraph chunks
        chunks = [c.strip() for c in text.split("\n\n") if len(c.strip()) > 60]
        for j, chunk in enumerate(chunks):
            doc_id = f"{note_file.stem}_{j}"
            if doc_id not in ids:  # avoid duplicates on re-index
                docs.append(chunk)
                ids.append(doc_id)
                metadatas.append({"source": note_file.name})

    if docs:
        collection.add(documents=docs, ids=ids, metadatas=metadatas)


def warmup() -> None:
    """Load the embedding model and build the Chroma index ahead of time.

    The very first knowledge_lookup otherwise pays a one-time ~15-20s cost to load
    the sentence-transformer weights and index the notes — which lands on an
    unlucky user's first question. Calling this at server startup moves that cost
    off the request path so every real lookup is fast.
    """
    try:
        collection = _get_collection()
        collection.query(query_texts=["sun in leo"], n_results=1)
    except Exception:
        pass  # warmup is best-effort; a failure just means the first lookup is slow


@tool
def knowledge_lookup(query: str) -> str:
    """
    Search the astrology knowledge base for relevant interpretations and meanings.

    Use this when interpreting a planetary placement, house, aspect, or transit.
    It grounds the response in established astrological tradition rather than
    relying on general knowledge alone.
    """
    try:
        collection = _get_collection()
        results = collection.query(query_texts=[query], n_results=3)
        passages = results["documents"][0] if results.get("documents") else []
        if not passages:
            return "No relevant reference material found for this query."
        return "\n\n---\n\n".join(passages)
    except Exception as e:
        return f"Knowledge lookup unavailable: {e}"

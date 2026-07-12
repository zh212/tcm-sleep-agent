"""Retrieval: Chroma vector search + BM25 sparse search + RRF hybrid fusion."""

import chromadb
from chromadb.config import Settings as ChromaSettings

from config.settings import (
    VECTOR_STORE_PATH,
    COLLECTION_NAME,
    DEFAULT_TOP_K,
)
from src.services.embedding_service import embed_text, embed_batch
from src.services.knowledge_service import sync_from_json, list_all
from src.services.bm25_service import bm25_search, build_bm25_index


def _get_collection() -> chromadb.Collection:
    import os
    os.makedirs(VECTOR_STORE_PATH, exist_ok=True)
    client = chromadb.PersistentClient(
        path=VECTOR_STORE_PATH,
        settings=ChromaSettings(anonymized_telemetry=False),
    )
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )


def build_index(force_rebuild: bool = False) -> int:
    """Index knowledge base entries into Chroma + sync to SQLite.

    Returns number of documents indexed.
    """
    collection = _get_collection()

    existing = collection.count()
    if existing > 0 and not force_rebuild:
        # Also refresh BM25 if it hasn't been built yet
        build_bm25_index()
        return existing

    if force_rebuild and existing > 0:
        all_ids = collection.get()["ids"]
        if all_ids:
            collection.delete(ids=all_ids)

    # Sync to SQLite first
    sync_from_json()

    # Read from SQLite for indexing
    formulas = list_all()

    texts = []
    metadatas = []
    ids = []
    for item in formulas:
        text_parts = [
            f"方剂：{item['name']}",
            f"证型：{item['syndrome']}",
            f"适用症状：{item['symptoms']}",
            f"功效：{item['effects']}",
            f"组成：{item['ingredients']}",
            f"分类：{item.get('category', '')}",
            f"出处：{item.get('source', '')}",
            f"注意事项：{item.get('notes', '')}",
        ]
        texts.append("\n".join(text_parts))
        metadatas.append({
            "formula_id": item["id"],
            "name": item["name"],
            "syndrome": item["syndrome"],
            "symptoms": item["symptoms"],
            "effects": item["effects"],
            "ingredients": item["ingredients"],
            "notes": item.get("notes", ""),
            "category": item.get("category", ""),
            "source": item.get("source", ""),
        })
        ids.append(item["id"])

    embeddings = embed_batch(texts, text_type="document")

    collection.add(
        ids=ids,
        embeddings=embeddings,
        documents=texts,
        metadatas=metadatas,
    )

    # Build BM25 index from the same data
    build_bm25_index()

    return collection.count()


def search(query: str, top_k: int = DEFAULT_TOP_K) -> list[dict]:
    """Semantic search the knowledge base."""
    collection = _get_collection()

    if collection.count() == 0:
        build_index()

    query_embedding = embed_text(query, text_type="query")

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )

    output = []
    if not results["ids"] or not results["ids"][0]:
        return output

    for i, doc_id in enumerate(results["ids"][0]):
        metadata = results["metadatas"][0][i] if results["metadatas"] else {}
        distance = results["distances"][0][i] if results["distances"] else 0.0
        similarity = 1.0 - distance

        output.append({
            "id": doc_id,
            "name": metadata.get("name", ""),
            "syndrome": metadata.get("syndrome", ""),
            "symptoms": metadata.get("symptoms", ""),
            "effects": metadata.get("effects", ""),
            "ingredients": metadata.get("ingredients", ""),
            "notes": metadata.get("notes", ""),
            "category": metadata.get("category", ""),
            "source": metadata.get("source", ""),
            "similarity_score": round(similarity, 4),
            "document": results["documents"][0][i] if results["documents"] else "",
        })

    return output


# ── RRF Hybrid Retrieval ──────────────────────────────────────────────────────

_RRF_K = 60  # standard RRF smoothing constant


def _rrf_score(rank: int, k: int = _RRF_K) -> float:
    return 1.0 / (k + rank)


def hybrid_search(
    query: str,
    top_k: int = DEFAULT_TOP_K,
    vector_weight: float = 0.6,
    bm25_weight: float = 0.4,
    candidate_multiplier: int = 3,
) -> list[dict]:
    """Hybrid search: RRF fusion of vector + BM25 results.

    Args:
        query: Natural language query.
        top_k: Final result count to return.
        vector_weight: Relative weight for vector search scores.
        bm25_weight: Relative weight for BM25 scores.
        candidate_multiplier: Retrieve top_k * multiplier candidates from each
            source before merging, to give RRF more data to fuse.

    Returns:
        List of formula dicts with hybrid_score, vector_rank, bm25_rank.
    """
    candidate_k = top_k * candidate_multiplier

    # --- Vector retrieval ---
    vector_results = search(query, top_k=candidate_k)
    vector_rank_map: dict[str, int] = {
        r["id"]: rank + 1 for rank, r in enumerate(vector_results)
    }

    # --- BM25 retrieval ---
    bm25_results = bm25_search(query, top_k=candidate_k)
    bm25_rank_map: dict[str, int] = {r["id"]: r["rank"] for r in bm25_results}

    # --- RRF fusion ---
    all_ids = set(vector_rank_map.keys()) | set(bm25_rank_map.keys())
    rrf_scores: dict[str, float] = {}
    for doc_id in all_ids:
        v_rank = vector_rank_map.get(doc_id, candidate_k + 1)
        b_rank = bm25_rank_map.get(doc_id, candidate_k + 1)
        rrf_scores[doc_id] = (
            vector_weight * _rrf_score(v_rank)
            + bm25_weight * _rrf_score(b_rank)
        )

    # Sort by RRF score descending
    ranked_ids = sorted(rrf_scores, key=lambda x: rrf_scores[x], reverse=True)[:top_k]

    # --- Fetch full records from SQLite (via Chroma metadata fallback) ---
    # Build a lookup from vector results (already has full metadata)
    vector_lookup: dict[str, dict] = {r["id"]: r for r in vector_results}

    # For IDs only in BM25 results, fetch from SQLite
    missing_ids = [i for i in ranked_ids if i not in vector_lookup]
    if missing_ids:
        from src.db.crud import get_formula_by_id
        for mid in missing_ids:
            row = get_formula_by_id(mid)
            if row:
                vector_lookup[mid] = {**row, "similarity_score": 0.0, "document": ""}

    output = []
    for rank, doc_id in enumerate(ranked_ids):
        base = vector_lookup.get(doc_id)
        if not base:
            continue
        output.append({
            **base,
            "hybrid_score": round(rrf_scores[doc_id], 6),
            "vector_rank": vector_rank_map.get(doc_id),
            "bm25_rank": bm25_rank_map.get(doc_id),
            "retrieval_method": "hybrid_rrf",
        })

    return output

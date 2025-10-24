# backend/graph/graph_langchain.py
# Embeddings + FAISS only. LLM logic moved to backend/llm/graph_agent.py

from utility.backend_log import logger

import os
from pathlib import Path
from typing import List

import faiss
from sentence_transformers import SentenceTransformer

from graph.neo4j_connect import graph
from graph.graph_query import get_course_info
from utility.path_utils import models_dir

# ────────────────
# Embedding model, FAISS index
# ────────────────
EMBED_MODEL_NAME = os.getenv(
    "SENTENCE_TRANSFORMER_MODEL", "sentence-transformers/all-MiniLM-L12-v2"
)
EMBEDDING_DIM = 384
TOP_K = 5

_configured_local_path = os.getenv("SENTENCE_TRANSFORMER_LOCAL_PATH")
_local_only = os.getenv("SENTENCE_TRANSFORMER_LOCAL_ONLY", "0").lower() in {"1","true","yes"}
_embed_cache_dir = os.getenv("SENTENCE_TRANSFORMER_CACHE_DIR") or os.getenv("HF_HOME")

_default_model_dir = models_dir() / EMBED_MODEL_NAME.split("/")[-1]
_local_model_path = (
    Path(_configured_local_path).expanduser()
    if _configured_local_path
    else _default_model_dir
)


def _load_sentence_transformer() -> SentenceTransformer:
    """Load the sentence-transformer model, preferring a local path when available."""
    model_id = EMBED_MODEL_NAME
    kwargs = {}

    if _embed_cache_dir:
        kwargs["cache_folder"] = _embed_cache_dir

    if _local_model_path and _local_model_path.exists():
        model_id = str(_local_model_path)
        kwargs["local_files_only"] = True
    elif _local_only or _configured_local_path:
        raise FileNotFoundError(
            f"SentenceTransformer local path {_local_model_path} not found."
        )

    logger.info(
        "Loading SentenceTransformer model: %s (cache=%s, local_only=%s)",
        model_id,
        _embed_cache_dir,
        kwargs.get("local_files_only", False),
    )
    return SentenceTransformer(model_id, **kwargs)


embed_model: SentenceTransformer = _load_sentence_transformer()
EMBEDDING_DIM = embed_model.get_sentence_embedding_dimension()

_course_codes: List[str] = []
_faiss_index: faiss.IndexFlatIP


def build_faiss_index() -> None:
    """Build the in-memory FAISS index over all Course descriptions."""
    global _course_codes, _faiss_index

    records = graph.run(
        """
        MATCH (c:Course)
        RETURN c.course_code AS code,
               coalesce(c.course_description, c.course_name) AS text
        """
    ).data()

    _course_codes = [r["code"] for r in records]
    texts = [r["text"] for r in records]

    if not texts:
        _faiss_index = faiss.IndexFlatIP(EMBEDDING_DIM)
        logger.warning("FAISS index built with 0 vectors. Did you seed courses?")
        return

    embeddings = embed_model.encode(
        texts,
        convert_to_numpy=True,
        show_progress_bar=False,
    )
    if embeddings.ndim == 1:
        embeddings = embeddings.reshape(1, -1)
    faiss.normalize_L2(embeddings)

    index = faiss.IndexFlatIP(EMBEDDING_DIM)
    index.add(embeddings)
    _faiss_index = index
    logger.info("✅ FAISS index built with %d vectors.", len(_course_codes))


def search_similar_courses_data(query: str, top_k: int = TOP_K) -> List[dict]:
    """Return top_k nearest courses to the query from FAISS."""
    q_emb = embed_model.encode([query], convert_to_numpy=True)
    if q_emb.ndim == 1:
        q_emb = q_emb.reshape(1, -1)
    faiss.normalize_L2(q_emb)

    scores, indices = _faiss_index.search(q_emb, top_k)
    results = []
    for score, idx in zip(scores[0], indices[0]):
        if 0 <= idx < len(_course_codes):
            results.append({"code": _course_codes[idx], "score": float(score)})
    return results


def ensure_faiss_index() -> None:
    """Ensure the FAISS index exists before running similarity searches."""
    if not _course_codes or "_faiss_index" not in globals() or not hasattr(_faiss_index, "search"):
        build_faiss_index()


def build_course_context(question: str, top_k: int = TOP_K) -> str:
    """Create a simple context block from the top_k similar courses."""
    ensure_faiss_index()
    sims = search_similar_courses_data(question, top_k)
    lines: List[str] = []
    for item in sims:
        info = get_course_info(item["code"])  # maps JSON fields to stable interface
        if not info:
            continue
        prereqs = info.get("requires") or []
        lines.append(
            f"{info['code']} – {info['name']} (Units: {info.get('units')}; "
            f"Prereqs: {', '.join(prereqs) if prereqs else 'None'})"
        )
    return "\n".join(lines)


__all__ = [
    "EMBED_MODEL_NAME",
    "EMBEDDING_DIM",
    "TOP_K",
    "embed_model",
    "build_faiss_index",
    "ensure_faiss_index",
    "search_similar_courses_data",
    "build_course_context",
]

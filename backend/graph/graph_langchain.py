# backend/graph/graph_langchain.py
# Main LLM and Graph-RAG integration for Degree Planner


# -----------Import statements-----------

# logger for log messages
from utility.backend_log import logger
# --------------------------------------

import os
from pathlib import Path

# embedding & vector store
import faiss
# --------------------------------------

# async generator for streaming
from typing import AsyncGenerator, List
# --------------------------------------

# sentence transformer for embeddings
from sentence_transformers import SentenceTransformer
# --------------------------------------

# langchain LLM and message schema for general LLM usage
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage
# --------------------------------------
# system prompts for LLM
from llm_system_prompts import COURSE_SYSTEM_MESSAGE
# --------------------------------------

# neo4j graph connection, importing the graph instance from neo4j_connect.py
from graph.neo4j_connect import graph


# ────────────────
# Embedding model, FAISS index, and LLM for Graph-RAG
# ────────────────
# Faiss configuration for embedding search
EMBED_MODEL_NAME = os.getenv(
    "SENTENCE_TRANSFORMER_MODEL", "sentence-transformers/all-MiniLM-L12-v2"
)
EMBEDDING_DIM = 384
TOP_K = 5
# ────────────────
# Embedding model & placeholders
# ────────────────

_configured_local_path = os.getenv("SENTENCE_TRANSFORMER_LOCAL_PATH")
_local_only = os.getenv("SENTENCE_TRANSFORMER_LOCAL_ONLY", "0").lower() in {"1","true","yes"}
_embed_cache_dir = os.getenv("SENTENCE_TRANSFORMER_CACHE_DIR") or os.getenv("HF_HOME")

# Default to bundled model directory if present (e.g., /app/models/<model-name>)
_default_model_dir = (
    Path(__file__).resolve().parents[1]
    / "models"
    / EMBED_MODEL_NAME.split("/")[-1]
)
_local_model_path = (
    Path(_configured_local_path).expanduser()
    if _configured_local_path
    else _default_model_dir
)


def _load_sentence_transformer() -> SentenceTransformer:
    """
    Load the embedding model, optionally from a local path to avoid Hugging Face downloads.
    """
    model_id = EMBED_MODEL_NAME
    kwargs = {}

    if _embed_cache_dir:
        kwargs["cache_folder"] = _embed_cache_dir

    # Prefer a local path when available
    if _local_model_path and _local_model_path.exists():
        model_id = str(_local_model_path)
        kwargs["local_files_only"] = True
    elif _local_only or _configured_local_path:
        # Caller explicitly requested local-only mode but path missing
        raise FileNotFoundError(
            f"SentenceTransformer local path {_local_model_path} not found. "
            "Bundle the model files (e.g., backend/models/<model>) or update "
            "SENTENCE_TRANSFORMER_LOCAL_PATH."
        )
    elif _local_only:
        raise RuntimeError(
            "SENTENCE_TRANSFORMER_LOCAL_ONLY is set but no local model path is configured."
        )

    logger.info(
        "Loading SentenceTransformer model: %s (cache=%s, local_only=%s)",
        model_id,
        _embed_cache_dir,
        kwargs.get("local_files_only", False),
    )
    return SentenceTransformer(model_id, **kwargs)


embed_model: SentenceTransformer = _load_sentence_transformer()

# derive dim from the model
EMBEDDING_DIM = embed_model.get_sentence_embedding_dimension()

_course_codes: List[str] = []
_faiss_index: faiss.IndexFlatIP

def build_faiss_index() -> None:
    """
    Build the in-memory FAISS index over all Course descriptions.
    """
    global _course_codes, _faiss_index

    records = graph.run(
        """
        MATCH (c:Course)
        RETURN c.code AS code,
               coalesce(c.description, c.name) AS text
        """
    ).data()

    _course_codes = [r["code"] for r in records]
    texts = [r["text"] for r in records]

    if not texts:
        _faiss_index = faiss.IndexFlatIP(EMBEDDING_DIM)
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
    logger.info(f"✅ FAISS index built with {len(_course_codes)} vectors.")


def search_similar_courses_data(query: str, top_k: int = TOP_K) -> List[dict]:
    """
    Return top_k nearest courses to the query.
    """
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


def build_course_context(question: str, top_k: int = TOP_K) -> str:
    """
    Create a context block from the top_k similar courses.
    """
    sims = search_similar_courses_data(question, top_k)
    lines: List[str] = []
    for item in sims:
        rec = graph.run(
            """
            MATCH (c:Course {code: $code})
            RETURN c.code AS code, c.name AS name, c.units AS units,
                   c.requires AS requires
            """,
            code=item["code"],
        ).data()
        if not rec:
            continue
        info = rec[0]
        prereqs = info.get("requires") or []
        lines.append(
            f"{info['code']} – {info['name']} "
            f"(Units: {info['units']}; "
            f"Prereqs: {', '.join(prereqs) if prereqs else 'None'})"
        )
    return "\n".join(lines)


# ────────────────
# LLM & streaming
# ────────────────
llm = ChatOpenAI(
    model="mistral",
    streaming=True,
    temperature=0.0,
)


async def run_graph_rag_stream(question: str) -> AsyncGenerator[str, None]:
    logger.debug("Running Graph-RAG stream for question: %s", question)
    """
    Stream a Graph-RAG response for the given question.
    """
    if not question:
        yield "❌ No question provided."
        return

    # Ensure FAISS index exists
    if not _course_codes or not hasattr(_faiss_index, 'search'):
        build_faiss_index()

    # Build context and log
    context = build_course_context(question)
    logger.debug("Graph-RAG context built: %s", context)

    system = SystemMessage(
        content= COURSE_SYSTEM_MESSAGE
    )
    courses = SystemMessage(content=f"Relevant courses:\n{context}")
    human   = HumanMessage(content=question)

    async for chunk in llm.astream([system, courses, human]):
        text = None
        # Prefer content if non-empty
        if hasattr(chunk, 'content') and chunk.content:
            text = chunk.content
        # Fallback to text() or text attribute
        elif hasattr(chunk, 'text'):
            maybe = chunk.text
            text = maybe() if callable(maybe) else maybe
        else:
            text = str(chunk)

        # Only yield real text, skip empty
        if text:
            yield text
# Expose LLM instance to be used from app.py
__all__ = ["run_graph_rag_stream", "llm"]

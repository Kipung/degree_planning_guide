"""
backend/app.py — FastAPI entry point for the Degree Planner backend.

Responsibilities:
  • Initialize the FastAPI app and enable CORS for frontend.
  • Seed Neo4j from course JSON when the server starts.
  • Stream responses from the LLM to the frontend (/plan_stream).
  • Maintain minimal in-memory message history.
  • Provide debug utilities (reset history).

This version removes redundant logic and simplifies readability.
"""

import json
from typing import AsyncIterator, List

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from langchain.schema import HumanMessage, AIMessage, BaseMessage, SystemMessage

from LLM.load import (
    build_system_message,
    get_async_openai_client,
    get_llm_config,
)
from graph.seed_graph import seed_graph_from_json
from utility.backend_log import logger

# -----------------------------------------------------------------------------
# Application setup
# -----------------------------------------------------------------------------

app = FastAPI(title="Degree Planner API")

# Allow frontend access from the Vite dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------------------------------------------------------
# Initialization and Health
# -----------------------------------------------------------------------------

@app.on_event("startup")
def on_startup() -> None:
    """Seed Neo4j when the backend starts."""
    try:
        logger.info("🌱 Seeding Neo4j graph on startup…")
        seed_graph_from_json()
        logger.info("✅ Neo4j seed complete.")
    except Exception as exc:
        logger.exception("Neo4j seed failed: %s", exc)


@app.get("/", tags=["Health"])
async def health_check() -> dict:
    """Simple health endpoint."""
    return {"status": "ok"}


# -----------------------------------------------------------------------------
# Global in-memory history
# -----------------------------------------------------------------------------
# Shared across all sessions for now — replace with user-specific store later.

_openai_client = get_async_openai_client()

global_history: List[BaseMessage] = [build_system_message()]


def _format_chat_history(messages: List[BaseMessage]) -> List[dict[str, str]]:
    """Convert LangChain message objects into OpenAI-style messages."""
    formatted: List[dict[str, str]] = []
    for msg in messages:
        if isinstance(msg, HumanMessage):
            formatted.append({"role": "user", "content": msg.content})
        elif isinstance(msg, AIMessage):
            formatted.append({"role": "assistant", "content": msg.content})
        elif isinstance(msg, SystemMessage):
            formatted.append({"role": "system", "content": msg.content})
    return formatted


async def stream_llm_tokens(messages: List[BaseMessage]) -> AsyncIterator[str]:
    """Stream text tokens from the configured LLM."""
    payload = _format_chat_history(messages)
    if not payload or payload[-1]["role"] != "user":
        raise ValueError("Last message must be a user question before streaming.")

    cfg = get_llm_config()
    params = {
        "model": cfg.model,
        "messages": payload,
        "temperature": cfg.temperature,
        "stream": True,
    }
    if cfg.max_tokens is not None:
        params["max_tokens"] = cfg.max_tokens

    stream = await _openai_client.chat.completions.create(**params)
    async for chunk in stream:
        for choice in getattr(chunk, "choices", []):
            delta = getattr(choice, "delta", None)
            if not delta:
                continue
            content = getattr(delta, "content", None)
            text = ""
            if isinstance(content, str):
                text = content
            elif isinstance(content, list):
                text = "".join(
                    getattr(part, "text", "") for part in content if getattr(part, "text", None)
                )
            if text:
                yield text

# -----------------------------------------------------------------------------
# Planner endpoint — core LLM communication
# -----------------------------------------------------------------------------

@app.get("/plan_stream", tags=["Planner"])
async def plan_stream(question: str = Query(..., description="User query.")):
    """Stream token-by-token LLM responses back to the frontend."""
    logger.debug("global_history size=%d", len(global_history))

    history_seed: List[BaseMessage] = list(global_history)
    messages: List[BaseMessage] = list(history_seed)

    # 2. Add user question
    human_msg = HumanMessage(content=question)
    messages.append(human_msg)

    # 3. Stream tokens from the LLM
    async def event_generator():
        full_reply = ""

        async for token in stream_llm_tokens(messages):
            if token and not token.startswith("content="):
                full_reply += token
                yield f"data: {json.dumps({'token': token})}\n"

        # 4. After streaming finishes, update conversation history
        if full_reply.strip():
            new_history: List[BaseMessage] = list(history_seed)
            new_history.append(human_msg)
            new_history.append(AIMessage(content=full_reply))

            global_history.clear()
            global_history.extend(new_history)

            logger.debug("Updated global history (%d messages)", len(global_history))
            for m in global_history:
                logger.debug("%s: %s", m.__class__.__name__, getattr(m, "content", ""))

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache"},
    )


# -----------------------------------------------------------------------------
# Debug utilities
# -----------------------------------------------------------------------------

@app.get("/reset_session", tags=["Debug"])
async def reset_session() -> dict:
    """Reset in-memory history (for debugging)."""
    global global_history
    global_history.clear()
    global_history.append(build_system_message())
    logger.info("🧹 Global history reset.")
    return {"status": "cleared"}

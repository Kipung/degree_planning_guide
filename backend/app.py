# backend/app.py
# Main application for the Degree Planner API
import json
from typing import List

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from langchain.schema import SystemMessage, HumanMessage, AIMessage

from llm_system_prompts import GENERAL_SYSTEM_MESSAGE, COURSE_SYSTEM_MESSAGE
from graph.seed_graph import seed_graph_from_json
from graph.graph_langchain import llm
from utility.backend_log import logger


app = FastAPI(title="Degree Planner API")

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Utility function to determine if the question is course-related
def is_course_related(query: str) -> bool:
    keywords = ["course", "class", "take", "semester", "prereq", "plan", "credit", "requirement"]
    return any(word in query.lower() for word in keywords)

# 🌱 Seed Neo4j graph on startup
@app.on_event("startup")
def on_startup():
    logger.debug("🌱 Seeding Neo4j graph on startup...")
    seed_graph_from_json()

@app.get("/", tags=["Health"])
async def health_check():
    return {"status": "ok"}

# 🧠 Global in-memory history shared for all users
global_history: List = []

@app.get("/plan_stream", tags=["Planner"])
async def plan_stream(question: str = Query(...)):
    logger.debug("global_history: %s", global_history)

    # Determine message context
    is_course = is_course_related(question)

    if not global_history:
        # First user message — include system message
        system_msg = SystemMessage(
            content=COURSE_SYSTEM_MESSAGE if is_course else GENERAL_SYSTEM_MESSAGE
        )
        messages = [system_msg, HumanMessage(content=question)]
    else:
        # Subsequent messages — reuse history only
        messages = global_history + [HumanMessage(content=question)]

    async def event_generator():
        full_reply = ""

        async for chunk in llm.astream(messages):
            content = getattr(chunk, "content", "") or (
                chunk.text() if callable(getattr(chunk, "text", None)) else getattr(chunk, "text", "")
            ) or str(chunk)

            if content and not content.startswith("content="):
                full_reply += content
                json_data = json.dumps({"token": content})
                yield f"data: {json_data}\n"

        # Update static global memory
        if full_reply.strip():
            global_history.append(HumanMessage(content=question))
            global_history.append(AIMessage(content=full_reply))

            logger.debug("Updated global history:")
            for m in global_history:
                logger.debug(f"{m.__class__.__name__}: {getattr(m, 'content', '')}")

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache"},
    )

@app.get("/reset_session", tags=["Debug"])
async def reset_session():
    global global_history
    global_history.clear()
    logger.info("🧹 Global history reset.")
    return {"status": "cleared"}
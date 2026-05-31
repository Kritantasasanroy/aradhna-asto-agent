from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import AsyncIterator, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from langchain_core.messages import HumanMessage
from pydantic import BaseModel

from agent.graph import graph
from agent.state import AgentState, BirthDetails
from db.sessions import get_session_meta, init_db, load_session, save_session

app = FastAPI(title="AstroAgent API", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    init_db()


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    birth_details: Optional[BirthDetails] = None


async def stream_agent(req: ChatRequest) -> AsyncIterator[str]:
    session_id = req.session_id or str(uuid.uuid4())

    # load existing session so the agent remembers prior turns
    session = load_session(session_id)
    history = session["messages"] if session else []
    cached_chart = session["birth_chart"] if session else None

    # request birth_details take priority; fall back to what's in the session
    birth_details = req.birth_details or (session["birth_details"] if session else None)

    initial_state: AgentState = {
        "messages": history + [HumanMessage(content=req.message)],
        "birth_details": birth_details,
        "birth_chart": cached_chart,
        "intent": "",
        "tool_calls_made": [],
        "step_count": 0,
        "session_id": session_id,
    }

    # send session_id upfront so the client can store it
    yield f"data: {json.dumps({'type': 'session_id', 'session_id': session_id})}\n\n"

    final_messages = initial_state["messages"].copy()
    final_birth_chart = cached_chart

    async for event in graph.astream_events(initial_state, version="v2"):
        kind = event.get("event")

        if kind == "on_chat_model_stream":
            chunk = event["data"].get("chunk")
            if chunk and chunk.content:
                payload = {"type": "token", "content": chunk.content}
                yield f"data: {json.dumps(payload)}\n\n"

        elif kind == "on_tool_start":
            payload = {"type": "tool_start", "tool": event.get("name")}
            yield f"data: {json.dumps(payload)}\n\n"

        elif kind == "on_tool_end":
            payload = {"type": "tool_end", "tool": event.get("name")}
            yield f"data: {json.dumps(payload)}\n\n"

        elif kind == "on_chain_end" and event.get("name") == "LangGraph":
            output = event["data"].get("output", {})
            if output.get("messages"):
                final_messages = output["messages"]
            if output.get("birth_chart"):
                final_birth_chart = output["birth_chart"]

    # persist after stream completes
    try:
        save_session(session_id, final_messages, birth_details, final_birth_chart)
    except Exception:
        pass  # never fail the response over a session save error

    yield f"data: {json.dumps({'type': 'done', 'session_id': session_id})}\n\n"


@app.post("/chat")
async def chat(req: ChatRequest):
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")
    return StreamingResponse(stream_agent(req), media_type="text/event-stream")


@app.get("/session/{session_id}")
def get_session(session_id: str):
    """Returns session metadata — whether a chart exists, birth details, timestamps."""
    meta = get_session_meta(session_id)
    if not meta:
        raise HTTPException(status_code=404, detail="Session not found")
    return meta


@app.get("/health")
def health():
    return {"status": "ok", "version": "0.2.0"}


# Serve the frontend — must come last so API routes take priority
_FRONTEND = Path(__file__).parent.parent.parent / "frontend"
if _FRONTEND.exists():
    app.mount("/", StaticFiles(directory=_FRONTEND, html=True), name="frontend")

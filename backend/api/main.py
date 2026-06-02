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


_EMPTY_GREETING = (
    "Hello, I'm Aradhana — your astrology companion. Whenever you're ready, share "
    "your birth date, time, and place, and ask me anything: your chart, the energy "
    "of today, your rising sign. What would you like to explore?"
)


def _last_ai_text(messages: list) -> str:
    """Return the text of the last AI message, or '' if there isn't one."""
    for msg in reversed(messages):
        if getattr(msg, "type", None) == "ai":
            content = msg.content
            return content if isinstance(content, str) else ""
    return ""


async def stream_agent(req: ChatRequest) -> AsyncIterator[str]:
    session_id = req.session_id or str(uuid.uuid4())

    yield f"data: {json.dumps({'type': 'session_id', 'session_id': session_id})}\n\n"

    if not req.message.strip():
        yield f"data: {json.dumps({'type': 'token', 'content': _EMPTY_GREETING})}\n\n"
        yield f"data: {json.dumps({'type': 'done', 'session_id': session_id})}\n\n"
        return

    session = load_session(session_id)
    history = session["messages"] if session else []
    cached_chart = session["birth_chart"] if session else None
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

    final_messages = initial_state["messages"].copy()
    final_birth_chart = cached_chart
    streamed_text = ""

    try:
        async for event in graph.astream_events(initial_state, version="v2"):
            kind = event.get("event")

            if kind == "on_chat_model_stream":
                chunk = event["data"].get("chunk")
                if chunk and chunk.content:
                    streamed_text += chunk.content
                    yield f"data: {json.dumps({'type': 'token', 'content': chunk.content})}\n\n"

            elif kind == "on_tool_start":
                yield f"data: {json.dumps({'type': 'tool_start', 'tool': event.get('name')})}\n\n"

            elif kind == "on_tool_end":
                yield f"data: {json.dumps({'type': 'tool_end', 'tool': event.get('name')})}\n\n"

            elif kind == "on_chain_end" and event.get("name") == "LangGraph":
                output = event["data"].get("output", {})
                if output.get("messages"):
                    final_messages = output["messages"]
                if output.get("birth_chart"):
                    final_birth_chart = output["birth_chart"]

    except Exception as e:
        print(f"[stream_agent] graph error: {e}")
        warm = (
            "The stars are a little crowded right now and I couldn't finish that "
            "reading — it's usually a brief rate limit on the free model. Give it "
            "a few seconds and ask me again."
        )
        if not streamed_text:
            yield f"data: {json.dumps({'type': 'token', 'content': warm})}\n\n"
        yield f"data: {json.dumps({'type': 'error', 'message': warm})}\n\n"
        yield f"data: {json.dumps({'type': 'done', 'session_id': session_id})}\n\n"
        return

    # Off-topic redirects and rate-limit fallbacks are built directly as
    # AIMessage objects, not streamed token-by-token. Emit any text that
    # hasn't been sent yet so the client always sees the full response.
    final_text = _last_ai_text(final_messages)
    if final_text:
        if final_text.startswith(streamed_text):
            remainder = final_text[len(streamed_text):]
        elif not streamed_text:
            remainder = final_text
        else:
            remainder = ""
        if remainder:
            yield f"data: {json.dumps({'type': 'token', 'content': remainder})}\n\n"

    try:
        save_session(session_id, final_messages, birth_details, final_birth_chart)
    except Exception:
        pass

    yield f"data: {json.dumps({'type': 'done', 'session_id': session_id})}\n\n"


@app.post("/chat")
async def chat(req: ChatRequest):
    return StreamingResponse(stream_agent(req), media_type="text/event-stream")


@app.get("/session/{session_id}")
def get_session(session_id: str):
    meta = get_session_meta(session_id)
    if not meta:
        raise HTTPException(status_code=404, detail="Session not found")
    return meta


@app.get("/health")
def health():
    return {"status": "ok", "version": "0.2.0"}


# Frontend served last so API routes take priority
_FRONTEND = Path(__file__).parent.parent.parent / "frontend"
if _FRONTEND.exists():
    app.mount("/", StaticFiles(directory=_FRONTEND, html=True), name="frontend")

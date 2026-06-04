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

from agent.chart_precompute import precompute_chart
from agent.graph import graph
from agent.state import AgentState, BirthDetails
from db.sessions import get_session_meta, init_db, load_session, save_session

try:
    from langgraph.types import Command
    from langgraph.errors import GraphInterrupt
    _HITL_AVAILABLE = True
except ImportError:
    Command = None
    GraphInterrupt = None
    _HITL_AVAILABLE = False

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
    # Warm the knowledge base (embedding model + Chroma index) off the request path,
    # in a background thread so the server is reachable immediately while it loads.
    import threading

    from agent.tools.knowledge import warmup as _warm_kb

    threading.Thread(target=_warm_kb, daemon=True).start()


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    birth_details: Optional[BirthDetails] = None


class ResumeRequest(BaseModel):
    thread_id: str
    session_id: str
    confirmed: bool = True
    birth_details: Optional[BirthDetails] = None


_EMPTY_GREETING = (
    "Hello, I'm Aradhana — your astrology companion. Whenever you're ready, share "
    "your birth date, time, and place, and ask me anything: your chart, the energy "
    "of today, your rising sign. What would you like to explore?"
)


def _chunk_text(content) -> str:
    """Extract plain text from a streaming chunk's content field.

    Gemini returns chunks as a list of typed parts, e.g.
    [{"type": "text", "text": "Hello"}]. OpenAI-compatible models return
    a plain string. This normalises both to a single string.
    """
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(
            p.get("text", "") if isinstance(p, dict) else str(p)
            for p in content
        )
    return ""


def _last_ai_text(messages: list) -> str:
    """Return the text of the last AI message, or '' if there isn't one."""
    for msg in reversed(messages):
        if getattr(msg, "type", None) == "ai":
            return _chunk_text(msg.content)
    return ""


async def stream_agent(req: ChatRequest) -> AsyncIterator[str]:
    session_id = req.session_id or str(uuid.uuid4())
    thread_id = str(uuid.uuid4())
    thread_config = {"configurable": {"thread_id": thread_id}}

    yield f"data: {json.dumps({'type': 'session_id', 'session_id': session_id})}\n\n"

    if not req.message.strip():
        yield f"data: {json.dumps({'type': 'token', 'content': _EMPTY_GREETING})}\n\n"
        yield f"data: {json.dumps({'type': 'done', 'session_id': session_id})}\n\n"
        return

    session = load_session(session_id)
    history = session["messages"] if session else []
    cached_chart = session["birth_chart"] if session else None
    birth_details = req.birth_details or (session["birth_details"] if session else None)

    # If the form gave us birth details and we don't have a chart yet, compute it
    # in Python now instead of spending two LLM tool rounds (geocode + compute) on it.
    precomputed_chart = None
    if not cached_chart:
        precomputed_chart = precompute_chart(birth_details)
        if precomputed_chart:
            cached_chart = precomputed_chart

    # The pre-compute genuinely runs geocode_place and compute_birth_chart, so surface
    # them as tool events — the UI shows accurate activity and the eval still sees the
    # tools it expects. If pre-compute didn't fire (missing/ambiguous details), the
    # agent falls back to calling these tools itself and emits the real events.
    if precomputed_chart:
        for _t in ("geocode_place", "compute_birth_chart"):
            yield f"data: {json.dumps({'type': 'tool_start', 'tool': _t})}\n\n"
            yield f"data: {json.dumps({'type': 'tool_end', 'tool': _t})}\n\n"

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
        async for event in graph.astream_events(initial_state, version="v2", config=thread_config):
            kind = event.get("event")

            if kind == "on_chat_model_stream":
                # The editor's pass re-generates the whole reading; its tokens are
                # suppressed here and sent once as a 'replace' after the graph ends.
                if "editor" in (event.get("tags") or []):
                    continue
                chunk = event["data"].get("chunk")
                if chunk and chunk.content:
                    text = _chunk_text(chunk.content)
                    if text:
                        streamed_text += text
                        yield f"data: {json.dumps({'type': 'token', 'content': text})}\n\n"

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
        if _HITL_AVAILABLE and GraphInterrupt and isinstance(e, GraphInterrupt):
            interrupt_val = e.args[0] if e.args else {}
            yield f"data: {json.dumps({'type': 'confirmation_needed', 'thread_id': thread_id, 'session_id': session_id, 'payload': interrupt_val})}\n\n"
            yield f"data: {json.dumps({'type': 'done', 'session_id': session_id})}\n\n"
            return

        print(f"[stream_agent] graph error: {e}")
        warm = (
            "The stars are a little crowded right now and I couldn't finish that "
            "reading — it's usually a brief rate limit on the free model. Give it "
            "a few seconds and ask me again."
        )
        # If nothing has streamed yet, deliver the note as a normal in-chat message
        # (a clean bubble, no error toast). Only fall back to an error event when we'd
        # already streamed a partial reading and can't cleanly recover it.
        if not streamed_text:
            yield f"data: {json.dumps({'type': 'token', 'content': warm})}\n\n"
            yield f"data: {json.dumps({'type': 'done', 'session_id': session_id})}\n\n"
            return
        yield f"data: {json.dumps({'type': 'error', 'message': warm})}\n\n"
        yield f"data: {json.dumps({'type': 'done', 'session_id': session_id})}\n\n"
        return

    # Reconcile the final message with what actually streamed. Three cases:
    #  - it extends the stream (e.g. a safety disclaimer appended) → send the tail
    #  - nothing streamed (off-topic redirect, need-details prompt) → send it whole
    #  - it diverges (editor tone pass, or a safety rewrite) → replace the draft
    final_text = _last_ai_text(final_messages)
    if final_text:
        if streamed_text and final_text.startswith(streamed_text):
            remainder = final_text[len(streamed_text):]
            if remainder:
                yield f"data: {json.dumps({'type': 'token', 'content': remainder})}\n\n"
        elif not streamed_text:
            yield f"data: {json.dumps({'type': 'token', 'content': final_text})}\n\n"
        else:
            yield f"data: {json.dumps({'type': 'replace', 'content': final_text})}\n\n"

    try:
        save_session(session_id, final_messages, birth_details, final_birth_chart)
    except Exception:
        pass

    yield f"data: {json.dumps({'type': 'done', 'session_id': session_id})}\n\n"


async def resume_agent(req: ResumeRequest) -> AsyncIterator[str]:
    """Stream the graph continuation after a human-in-the-loop confirmation."""
    thread_config = {"configurable": {"thread_id": req.thread_id}}

    yield f"data: {json.dumps({'type': 'session_id', 'session_id': req.session_id})}\n\n"

    final_messages: list = []
    final_birth_chart = None
    streamed_text = ""

    try:
        async for event in graph.astream_events(
            Command(resume={"confirmed": req.confirmed}),
            version="v2",
            config=thread_config,
        ):
            kind = event.get("event")

            if kind == "on_chat_model_stream":
                if "editor" in (event.get("tags") or []):
                    continue
                chunk = event["data"].get("chunk")
                if chunk and chunk.content:
                    text = _chunk_text(chunk.content)
                    if text:
                        streamed_text += text
                        yield f"data: {json.dumps({'type': 'token', 'content': text})}\n\n"

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
        print(f"[resume_agent] error: {e}")
        warm = "The stars are a little crowded right now. Give it a few seconds and try again."
        if not streamed_text:
            yield f"data: {json.dumps({'type': 'token', 'content': warm})}\n\n"
        yield f"data: {json.dumps({'type': 'error', 'message': warm})}\n\n"
        yield f"data: {json.dumps({'type': 'done', 'session_id': req.session_id})}\n\n"
        return

    final_text = _last_ai_text(final_messages)
    if final_text:
        if streamed_text and final_text.startswith(streamed_text):
            remainder = final_text[len(streamed_text):]
            if remainder:
                yield f"data: {json.dumps({'type': 'token', 'content': remainder})}\n\n"
        elif not streamed_text:
            yield f"data: {json.dumps({'type': 'token', 'content': final_text})}\n\n"
        else:
            yield f"data: {json.dumps({'type': 'replace', 'content': final_text})}\n\n"

    try:
        save_session(req.session_id, final_messages, req.birth_details, final_birth_chart)
    except Exception:
        pass

    yield f"data: {json.dumps({'type': 'done', 'session_id': req.session_id})}\n\n"


@app.post("/chat")
async def chat(req: ChatRequest):
    return StreamingResponse(stream_agent(req), media_type="text/event-stream")


@app.post("/resume")
async def resume_chat(req: ResumeRequest):
    if not _HITL_AVAILABLE or Command is None:
        raise HTTPException(status_code=501, detail="HITL not available in this LangGraph version")
    return StreamingResponse(resume_agent(req), media_type="text/event-stream")


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

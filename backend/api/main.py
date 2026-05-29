from __future__ import annotations

import json
import uuid
from typing import AsyncIterator, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage
from pydantic import BaseModel

from agent.graph import graph
from agent.state import AgentState, BirthDetails

app = FastAPI(title="AstroAgent API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    birth_details: Optional[BirthDetails] = None


async def stream_agent(req: ChatRequest) -> AsyncIterator[str]:
    session_id = req.session_id or str(uuid.uuid4())

    initial_state: AgentState = {
        "messages": [HumanMessage(content=req.message)],
        "birth_details": req.birth_details,
        "birth_chart": None,
        "intent": "",
        "tool_calls_made": [],
        "step_count": 0,
        "session_id": session_id,
    }

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

    yield "data: {\"type\": \"done\"}\n\n"


@app.post("/chat")
async def chat(req: ChatRequest):
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")
    return StreamingResponse(stream_agent(req), media_type="text/event-stream")


@app.get("/health")
def health():
    return {"status": "ok", "version": "0.1.0"}

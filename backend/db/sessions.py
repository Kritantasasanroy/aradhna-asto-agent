"""
SQLite-backed session store. Keeps conversation history and cached chart data
so a returning user picks up exactly where they left off without re-entering
their birth details or waiting for the chart to recompute.

SQLite ships with Python so no extra dependency needed.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage

DB_PATH = Path(__file__).parent.parent / "sessions.db"


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id   TEXT PRIMARY KEY,
                messages     TEXT NOT NULL DEFAULT '[]',
                birth_details TEXT,
                birth_chart  TEXT,
                created_at   TEXT NOT NULL,
                updated_at   TEXT NOT NULL
            )
        """)
        conn.commit()


def _serialize_messages(messages: list[BaseMessage]) -> list[dict]:
    out = []
    for m in messages:
        entry: dict = {"type": m.type, "content": m.content}
        if m.type == "ai":
            tool_calls = getattr(m, "tool_calls", None)
            if tool_calls:
                entry["tool_calls"] = tool_calls
        elif m.type == "tool":
            entry["tool_call_id"] = getattr(m, "tool_call_id", "")
            entry["name"] = getattr(m, "name", "")
        out.append(entry)
    return out


def _deserialize_messages(data: list[dict]) -> list[BaseMessage]:
    msgs: list[BaseMessage] = []
    for d in data:
        t = d.get("type", "")
        content = d.get("content", "")
        if t == "human":
            msgs.append(HumanMessage(content=content))
        elif t == "ai":
            msgs.append(AIMessage(content=content, tool_calls=d.get("tool_calls", [])))
        elif t == "tool":
            msgs.append(ToolMessage(
                content=content,
                tool_call_id=d.get("tool_call_id", ""),
                name=d.get("name", ""),
            ))
    return msgs


def load_session(session_id: str) -> Optional[dict]:
    """Returns {messages, birth_details, birth_chart} or None if session doesn't exist."""
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM sessions WHERE session_id = ?", (session_id,)
        ).fetchone()

    if not row:
        return None

    return {
        "messages": _deserialize_messages(json.loads(row["messages"])),
        "birth_details": json.loads(row["birth_details"]) if row["birth_details"] else None,
        "birth_chart": json.loads(row["birth_chart"]) if row["birth_chart"] else None,
    }


def save_session(
    session_id: str,
    messages: list[BaseMessage],
    birth_details: Optional[dict],
    birth_chart: Optional[dict],
) -> None:
    now = datetime.utcnow().isoformat()
    with _connect() as conn:
        conn.execute("""
            INSERT INTO sessions (session_id, messages, birth_details, birth_chart, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(session_id) DO UPDATE SET
                messages      = excluded.messages,
                birth_details = excluded.birth_details,
                birth_chart   = excluded.birth_chart,
                updated_at    = excluded.updated_at
        """, (
            session_id,
            json.dumps(_serialize_messages(messages)),
            json.dumps(birth_details) if birth_details else None,
            json.dumps(birth_chart) if birth_chart else None,
            now,
            now,
        ))
        conn.commit()


def get_session_meta(session_id: str) -> Optional[dict]:
    """Lightweight check — returns metadata without deserializing messages."""
    with _connect() as conn:
        row = conn.execute(
            "SELECT session_id, birth_details, birth_chart, created_at, updated_at FROM sessions WHERE session_id = ?",
            (session_id,)
        ).fetchone()

    if not row:
        return None

    return {
        "session_id": row["session_id"],
        "has_chart": row["birth_chart"] is not None,
        "birth_details": json.loads(row["birth_details"]) if row["birth_details"] else None,
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }

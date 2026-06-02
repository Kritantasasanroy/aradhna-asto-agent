from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv(Path(__file__).parent.parent / ".env")

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


def get_llm(temperature: float = 0.7) -> ChatOpenAI:
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "OPENROUTER_API_KEY is not set. "
            "Get a free key at https://openrouter.ai and add it to backend/.env"
        )

    model = os.getenv("LLM_MODEL", "openai/gpt-oss-20b:free")
    app_name = os.getenv("OPENROUTER_APP_NAME", "aradhna-astroagent")

    return ChatOpenAI(
        model=model,
        api_key=api_key,
        base_url=OPENROUTER_BASE_URL,
        temperature=temperature,
        max_retries=4,
        timeout=60,
        default_headers={
            "HTTP-Referer": "https://github.com/Kritantasasanroy/aradhna-asto-agent",
            "X-Title": app_name,
        },
    )

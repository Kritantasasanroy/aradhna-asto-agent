from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")


def get_llm(temperature: float = 0.7):
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "GEMINI_API_KEY is not set. "
            "Get a free key at https://aistudio.google.com and add it to backend/.env"
        )

    model = os.getenv("LLM_MODEL", "gemini-flash-lite-latest")

    from langchain_google_genai import ChatGoogleGenerativeAI

    # thinking_budget=0 disables Gemini 2.5's internal reasoning pass — this is a
    # direct constructor field in langchain-google-genai (not generation_config),
    # and it cuts latency from ~30-37s per call down to ~2-4s.
    return ChatGoogleGenerativeAI(
        model=model,
        google_api_key=api_key,
        temperature=temperature,
        thinking_budget=0,
        max_output_tokens=2048,
    )

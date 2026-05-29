"""
Single place to build the LLM client. Everything that needs an LLM imports from here.

We use OpenRouter because it gives free access to capable open models with no
credit card required. The API is OpenAI-compatible, so langchain-openai works
as-is — we just point it at OpenRouter's base URL.

Free models that work well here:
  meta-llama/llama-3.1-8b-instruct:free   (default — good reasoning, tool use)
  google/gemma-2-9b-it:free
  mistralai/mistral-7b-instruct:free
  qwen/qwen-2.5-7b-instruct:free
"""

from __future__ import annotations

import os

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


def get_llm(temperature: float = 0.7) -> ChatOpenAI:
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "OPENROUTER_API_KEY is not set. "
            "Get a free key at https://openrouter.ai and add it to backend/.env"
        )

    model = os.getenv("LLM_MODEL", "meta-llama/llama-3.1-8b-instruct:free")
    app_name = os.getenv("OPENROUTER_APP_NAME", "aradhna-astroagent")

    return ChatOpenAI(
        model=model,
        api_key=api_key,
        base_url=OPENROUTER_BASE_URL,
        temperature=temperature,
        default_headers={
            "HTTP-Referer": "https://github.com/Kritantasasanroy/aradhna-asto-agent",
            "X-Title": app_name,
        },
    )

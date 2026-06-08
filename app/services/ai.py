"""
app/services/ai.py

Thin wrapper around Anthropic SDK.
Import and use in endpoint files — never call httpx/requests directly.
"""
import os
import anthropic

_client: anthropic.AsyncAnthropic | None = None


def get_ai_client() -> anthropic.AsyncAnthropic:
    global _client
    if _client is None:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError("ANTHROPIC_API_KEY is not set in environment")
        _client = anthropic.AsyncAnthropic(api_key=api_key)
    return _client


MODEL = "claude-sonnet-4-20250514"
MAX_TOKENS = 1024

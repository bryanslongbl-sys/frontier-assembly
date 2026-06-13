"""Model router: role/provider -> the right API client, with one place to add vendors.

Most frontier vendors expose an OpenAI-compatible Chat Completions endpoint, so we
drive them all through the OpenAI SDK with a per-provider base_url + key. Anthropic
is the exception (no OpenAI-compatible Chat Completions surface), so Claude is routed
through the native `anthropic` SDK.

Sanctions warranty: only Western providers + native Nebius endpoints are wired here.
No dependency routes through a restricted jurisdiction.
"""
from __future__ import annotations

import os
from typing import TYPE_CHECKING, List, Tuple

from shared.config import MAX_TOKENS, MODEL_TIMEOUT, NEBIUS_BASE_URL

if TYPE_CHECKING:
    from openai import OpenAI

# provider -> (base_url or None for OpenAI default, api-key env var)
OPENAI_COMPATIBLE = {
    "nebius": (NEBIUS_BASE_URL, "NEBIUS_API_KEY"),
    "openai": (None, "OPENAI_API_KEY"),
    "xai": ("https://api.x.ai/v1", "XAI_API_KEY"),                                  # Grok
    "google": ("https://generativelanguage.googleapis.com/v1beta/openai/", "GEMINI_API_KEY"),
    "meta": ("https://api.llama.com/compat/v1/", "LLAMA_API_KEY"),                  # Meta Llama API
}

ChatResult = Tuple[str, int, int]  # (text, tokens_in, tokens_out)


class ModelRouter:
    def __init__(self) -> None:
        self._openai_clients: dict[str, OpenAI] = {}
        self._anthropic = None

    def _client(self, provider: str) -> "OpenAI":
        if provider not in self._openai_clients:
            if provider not in OPENAI_COMPATIBLE:
                raise ValueError(f"Unknown provider: {provider}")
            from openai import OpenAI

            base_url, key_var = OPENAI_COMPATIBLE[provider]
            key = os.getenv(key_var)
            if not key:
                raise RuntimeError(f"Missing {key_var} for provider '{provider}'")
            self._openai_clients[provider] = OpenAI(
                base_url=base_url, api_key=key, timeout=MODEL_TIMEOUT, max_retries=0
            )
        return self._openai_clients[provider]

    def chat(
        self,
        provider: str,
        model: str,
        messages: List[dict],
        *,
        max_tokens: int = MAX_TOKENS,
        temperature: float = 0.5,
    ) -> ChatResult:
        if provider == "anthropic":
            return self._anthropic_chat(model, messages, max_tokens, temperature)

        client = self._client(provider)
        resp = client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        text = resp.choices[0].message.content or ""
        usage = resp.usage
        tin = getattr(usage, "prompt_tokens", 0) or 0
        tout = getattr(usage, "completion_tokens", 0) or 0
        return text, tin, tout

    def _anthropic_chat(
        self, model: str, messages: List[dict], max_tokens: int, temperature: float
    ) -> ChatResult:
        if self._anthropic is None:
            from anthropic import Anthropic

            key = os.getenv("ANTHROPIC_API_KEY")
            if not key:
                raise RuntimeError("Missing ANTHROPIC_API_KEY for provider 'anthropic'")
            self._anthropic = Anthropic(api_key=key, timeout=MODEL_TIMEOUT)

        system = "\n\n".join(m["content"] for m in messages if m["role"] == "system")
        convo = [
            {"role": m["role"], "content": m["content"]}
            for m in messages
            if m["role"] != "system"
        ]
        msg = self._anthropic.messages.create(
            model=model,
            system=system or None,
            messages=convo,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        text = "".join(b.text for b in msg.content if getattr(b, "type", None) == "text")
        return text, msg.usage.input_tokens, msg.usage.output_tokens

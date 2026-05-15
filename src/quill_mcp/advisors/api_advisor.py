"""
API-backed advisor.

Calls an OpenAI-compatible /chat/completions endpoint. This is the
default backend — Elysia (via app.yg3.ai) and any BYO endpoint
(OpenAI, OpenRouter, Ollama, Together, Groq, Anyscale, etc.) all
land here.
"""

from __future__ import annotations

import logging

import httpx

from .base import Advisor

log = logging.getLogger("bridge")


class APIAdvisor(Advisor):
    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        default_model: str,
        timeout: float = 30.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.default_model = default_model
        self.default_timeout = timeout
        self._client = httpx.AsyncClient(timeout=timeout)

    async def chat(
        self,
        messages: list[dict],
        *,
        model_hint: str | None = None,
        max_tokens: int = 400,
        temperature: float = 0.6,
        timeout: float | None = None,
    ) -> str:
        model = model_hint or self.default_model
        try:
            resp = await self._client.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "messages": messages,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                },
                timeout=timeout if timeout is not None else self.default_timeout,
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"].strip()
        except httpx.HTTPStatusError as e:
            log.error(f"AI API returned {e.response.status_code}: {e.response.text[:200]}")
            return ""
        except Exception as e:
            log.error(f"Advisor call failed ({type(e).__name__}: {e})")
            return ""

    async def aclose(self) -> None:
        await self._client.aclose()

    @property
    def description(self) -> str:
        return f"api({self.base_url}, model={self.default_model})"

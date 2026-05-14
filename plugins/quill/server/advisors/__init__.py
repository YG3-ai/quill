"""
Advisor backends — pick one with `ADVISOR_BACKEND` in `.env`.

  - `api`         → call an OpenAI-compatible API (Elysia, OpenAI, OpenRouter, Ollama, etc.)
  - `codex_cli`   → shell out to OpenAI's `codex` CLI; uses the developer's
                    Codex Pro subscription, no API key needed
  - `claude_cli`  → shell out to Anthropic's `claude` CLI; uses the developer's
                    Claude Pro subscription, no API key needed

The `claude_cli` and `codex_cli` backends are what enable Quill's headline
move: two coding agents in deliberate dialogue, mediated by a third process,
without paying per-token API fees.
"""

from __future__ import annotations

import os

from .base import Advisor


def build_advisor() -> Advisor:
    """Construct the configured advisor backend. Reads env at call time."""
    backend = os.environ.get("ADVISOR_BACKEND", "api").strip().lower()

    if backend == "api":
        from .api_advisor import APIAdvisor
        return APIAdvisor(
            base_url=_required("AI_BASE_URL"),
            api_key=_required("AI_API_KEY"),
            default_model=_required("AI_MODEL"),
            timeout=float(os.environ.get("REQUEST_TIMEOUT", "30")),
        )

    if backend == "codex_cli":
        from .codex_cli_advisor import CodexCLIAdvisor
        return CodexCLIAdvisor(
            binary=os.environ.get("CODEX_BIN", "codex"),
            timeout=float(os.environ.get("CLI_TIMEOUT", "120")),
        )

    if backend == "claude_cli":
        from .claude_cli_advisor import ClaudeCLIAdvisor
        return ClaudeCLIAdvisor(
            binary=os.environ.get("CLAUDE_BIN", "claude"),
            timeout=float(os.environ.get("CLI_TIMEOUT", "120")),
        )

    raise ValueError(
        f"Unknown ADVISOR_BACKEND={backend!r}. "
        f"Options: api, codex_cli, claude_cli"
    )


def _required(name: str) -> str:
    val = os.environ.get(name, "").strip()
    if not val:
        raise RuntimeError(
            f"ADVISOR_BACKEND=api requires {name} to be set in the environment."
        )
    return val


__all__ = ["Advisor", "build_advisor"]

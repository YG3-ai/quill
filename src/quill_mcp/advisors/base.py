"""
Advisor backend interface.

An Advisor takes a list of chat messages (system + user(s) + assistant(s))
and returns reply text. Implementations decide *who* answers — an LLM API,
a Codex CLI subprocess, a Claude CLI subprocess, or anything else with
that shape.

This is the seam that lets Quill mediate dialogue between two coding
agents (e.g. Claude Code as the doer, Codex CLI as the advisor) without
the rest of the server knowing or caring which backend is on the other
end of the line.
"""

from __future__ import annotations


class Advisor:
    async def chat(
        self,
        messages: list[dict],
        *,
        model_hint: str | None = None,
        max_tokens: int = 400,
        temperature: float = 0.6,
        timeout: float | None = None,
    ) -> str:
        """Send messages, return reply text. Empty string on failure.

        `model_hint` is honored by the API backend (selects between e.g.
        consult/perspective/assumptions models) and ignored by CLI backends
        (which only have one binary configured).

        `max_tokens` and `temperature` are honored by the API backend and
        ignored by CLI backends (which use whatever the CLI defaults are).

        `timeout` overrides the backend's default timeout for this call.
        Used by the gatekeeper for tighter latency.
        """
        raise NotImplementedError

    async def aclose(self) -> None:
        """Release resources held by the backend (HTTP client, etc.)."""
        return None

    @property
    def description(self) -> str:
        """Short string describing this backend, for log lines on startup."""
        return self.__class__.__name__

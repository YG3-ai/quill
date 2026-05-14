"""
Shared plumbing for CLI-backed advisors (codex_cli, claude_cli).

The model: shell out to another coding agent's CLI in non-interactive mode,
pass the prompt as an arg, capture stdout. The agent does whatever it does
(may read files, run commands, etc.) and returns its response.

This is the seam that lets Quill mediate dialogue between two coding agents
without a paid API key on either side — both Claude Code and Codex CLI ship
with their own auth flows that bill against the developer's existing
subscription.
"""

from __future__ import annotations

import asyncio
import logging

from .base import Advisor

log = logging.getLogger("bridge")


SUB_AGENT_PREAMBLE = (
    "You are being invoked as a sub-agent to give a single thinking-partner "
    "response. Do not write code, edit files, or run commands unless strictly "
    "necessary to answer. Read the ROLE below, then reply directly to the "
    "QUESTION with your response.\n\n"
)

REPLY_INSTRUCTION = (
    "\n\nReply with only your thinking-partner response. No preamble, no "
    "follow-up questions, no offers to take action. Just your answer."
)


def format_prompt(messages: list[dict]) -> str:
    """Flatten chat messages into a single prompt a CLI agent can consume.

    System message becomes the ROLE block; user/assistant turns become
    a labeled transcript. The preamble + closing instruction nudge the
    CLI agent toward "respond as a thinking partner" rather than its
    default "do agentic work" behavior.
    """
    system = ""
    convo: list[str] = []
    for m in messages:
        role = m.get("role", "")
        content = (m.get("content") or "").strip()
        if not content:
            continue
        if role == "system":
            system = content
        elif role == "user":
            convo.append(f"QUESTION (from Claude):\n{content}")
        elif role == "assistant":
            convo.append(f"PRIOR REPLY (from you):\n{content}")

    parts = [SUB_AGENT_PREAMBLE]
    if system:
        parts.append(f"ROLE:\n{system}\n\n")
    parts.append("\n\n".join(convo))
    parts.append(REPLY_INSTRUCTION)
    return "".join(parts)


class BaseCLIAdvisor(Advisor):
    """Common subprocess plumbing for CLI-backed advisor backends."""

    name: str = "cli"

    def __init__(self, *, binary: str, args: list[str], timeout: float):
        self.binary = binary
        self.args = list(args)
        self.default_timeout = timeout

    async def chat(
        self,
        messages: list[dict],
        *,
        model_hint: str | None = None,
        max_tokens: int = 400,
        temperature: float = 0.6,
        timeout: float | None = None,
    ) -> str:
        prompt = format_prompt(messages)
        cmd = [self.binary, *self.args, prompt]
        effective_timeout = timeout if timeout is not None else self.default_timeout

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        except FileNotFoundError:
            log.error(
                f"{self.name}: binary {self.binary!r} not found. "
                f"Set {self.env_binary_var} in .env to override, or install the CLI."
            )
            return ""
        except Exception as e:
            log.error(f"{self.name}: failed to spawn subprocess ({type(e).__name__}: {e})")
            return ""

        try:
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(),
                timeout=effective_timeout,
            )
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            log.error(f"{self.name}: timed out after {effective_timeout:.1f}s")
            return ""

        if proc.returncode != 0:
            err = stderr.decode("utf-8", errors="replace").strip()[:500]
            log.error(f"{self.name}: exited {proc.returncode}: {err}")
            return ""

        return stdout.decode("utf-8", errors="replace").strip()

    @property
    def env_binary_var(self) -> str:
        """Subclasses set the env var name used to override the binary path."""
        return "CLI_BIN"

    @property
    def description(self) -> str:
        return f"{self.name}({self.binary} {' '.join(self.args)}, timeout={self.default_timeout:.0f}s)"

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
import os
import tempfile

from .base import Advisor

log = logging.getLogger("bridge")


SUB_AGENT_PREAMBLE = (
    "You are being invoked as a thinking partner for another coding agent "
    "(the 'doer') working in the developer's terminal. Take your time on "
    "the *exploration* — read the codebase, look at git history, check "
    "config files, whatever helps you give a grounded perspective. Don't "
    "take agentic actions on the developer's behalf (no edits, no commits, "
    "no commands that change state); the doer handles execution. You're "
    "the second pair of eyes.\n\n"
    "Keep the *final reply* focused — a couple of paragraphs, even after "
    "deep exploration. Cite specific files or lines when you're pointing "
    "at something concrete (`foo.py:42`), but don't dump the whole "
    "investigation. The ROLE below describes the kind of perspective the "
    "doer wants; treat its length suggestion as a floor, not a ceiling, "
    "and stay focused.\n\n"
)

REPLY_INSTRUCTION = (
    "\n\nReply with your thinking-partner response. Speak directly to the "
    "doer so they can synthesize your view with their own and show the "
    "developer the dialogue. A follow-up observation or question is fine "
    "if it'd actually help."
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
    """Common subprocess plumbing for CLI-backed advisor backends.

    By default, the agent's reply is whatever the subprocess prints to
    stdout. If `output_file_arg` is set, Quill creates a tempfile,
    inserts `<output_file_arg> <tempfile>` into the command, and reads
    the reply from the tempfile instead. This is for CLIs that print
    metadata + transcript to stdout but offer a flag to write just the
    final assistant message to a file (codex's `--output-last-message`).
    """

    name: str = "cli"

    def __init__(
        self,
        *,
        binary: str,
        args: list[str],
        timeout: float,
        output_file_arg: str | None = None,
    ):
        self.binary = binary
        self.args = list(args)
        self.default_timeout = timeout
        self.output_file_arg = output_file_arg

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
        effective_timeout = timeout if timeout is not None else self.default_timeout

        output_file_path: str | None = None
        if self.output_file_arg:
            fd, output_file_path = tempfile.mkstemp(prefix="quill-", suffix=".txt")
            os.close(fd)
            cmd = [self.binary, *self.args, self.output_file_arg, output_file_path, prompt]
        else:
            cmd = [self.binary, *self.args, prompt]

        try:
            try:
                # stdin=DEVNULL is load-bearing: when Quill MCP is itself a
                # subprocess of an agentic CLI (e.g. `claude -p` registering
                # us as an MCP server), our stdin is the JSON-RPC pipe from
                # that parent. Without DEVNULL here, child CLI advisors like
                # `codex exec` inherit that pipe and hang waiting for sensible
                # input. Diagnosed during research/spike-002 (2026-05-15).
                proc = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdin=asyncio.subprocess.DEVNULL,
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

            if output_file_path:
                try:
                    with open(output_file_path, "r", encoding="utf-8", errors="replace") as f:
                        return f.read().strip()
                except OSError as e:
                    log.error(f"{self.name}: could not read output file {output_file_path}: {e}")
                    return ""

            return stdout.decode("utf-8", errors="replace").strip()
        finally:
            if output_file_path:
                try:
                    os.unlink(output_file_path)
                except OSError:
                    pass

    @property
    def env_binary_var(self) -> str:
        """Subclasses set the env var name used to override the binary path."""
        return "CLI_BIN"

    @property
    def description(self) -> str:
        return f"{self.name}({self.binary} {' '.join(self.args)}, timeout={self.default_timeout:.0f}s)"

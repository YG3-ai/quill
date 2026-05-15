"""
Claude CLI advisor — Quill talks to Anthropic's `claude` CLI as the advisor.

Auth flows through the developer's existing Claude Pro/Max subscription
(or whatever auth `claude` is logged in as), so there's no per-token API
cost. The doer (e.g. Codex CLI in the terminal) sends a framing; this
backend shells out to `claude -p "<prompt>"`, captures stdout, and returns
it as the advisor's response.

`claude -p` is Claude Code's documented one-shot prompt mode and prints
the model's reply to stdout with no interactive UI.
"""

from __future__ import annotations

from ._cli_common import BaseCLIAdvisor


class ClaudeCLIAdvisor(BaseCLIAdvisor):
    name = "claude_cli"

    def __init__(self, *, binary: str = "claude", timeout: float = 300.0):
        super().__init__(binary=binary, args=["-p"], timeout=timeout)

    @property
    def env_binary_var(self) -> str:
        return "CLAUDE_BIN"

"""
Codex CLI advisor — Quill talks to OpenAI's `codex` CLI as the advisor.

Auth flows through the developer's existing ChatGPT Plus/Pro subscription,
so there's no per-token API cost. The doer (e.g. Claude Code in the
terminal) sends a framing; this backend shells out to `codex exec
"<prompt>"`, captures stdout, and returns it as the advisor's response.

If the local Codex CLI uses different invocation flags than `exec`,
override `CODEX_BIN` to point at a wrapper script that adapts.
"""

from __future__ import annotations

from ._cli_common import BaseCLIAdvisor


class CodexCLIAdvisor(BaseCLIAdvisor):
    name = "codex_cli"

    def __init__(self, *, binary: str = "codex", timeout: float = 120.0):
        super().__init__(binary=binary, args=["exec"], timeout=timeout)

    @property
    def env_binary_var(self) -> str:
        return "CODEX_BIN"

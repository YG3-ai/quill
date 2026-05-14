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

    def __init__(self, *, binary: str = "codex", timeout: float = 300.0):
        super().__init__(
            binary=binary,
            # --skip-git-repo-check: Codex refuses to run in untrusted dirs by
            #   default; the advisor needs to work regardless of where Quill
            #   was launched from.
            # --sandbox read-only: defense in depth — the advisor should never
            #   modify state. Belt-and-suspenders with the preamble's "no
            #   agentic actions" instruction.
            args=["exec", "--skip-git-repo-check", "--sandbox", "read-only"],
            timeout=timeout,
            # Codex prints metadata + transcript to stdout; --output-last-message
            # writes just the agent's final reply to a file. Cleaner than
            # parsing the stdout block.
            output_file_arg="--output-last-message",
        )

    @property
    def env_binary_var(self) -> str:
        return "CODEX_BIN"

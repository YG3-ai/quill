"""
Quill MCP server.

Exposes the three thinking-partner skills (consult, perspective, assumptions)
as MCP tools so any MCP-aware coding agent can use them — Codex CLI, Cursor,
Cline, Continue, or anything else that speaks Model Context Protocol.

Pairs naturally with the CLI advisor backends: a developer can run Codex CLI
as the doer, configure Quill with ADVISOR_BACKEND=claude_cli (or vice versa),
and get a thinking-partner dialogue between two coding agents that bills
against the developer's existing Pro subscriptions instead of an API key.

Run as the installed console script:

    quill-mcp

Or directly:

    python3 -m quill_mcp.server

Wire into an MCP-aware client's config under whatever name it expects
(e.g. for Codex CLI: `codex mcp add quill -- quill-mcp`; for Cursor:
Settings → Features → MCP Servers).
"""

from __future__ import annotations

import logging
import sys

from dotenv import load_dotenv

load_dotenv()

# MCP speaks JSON-RPC over stdio; logs MUST go to stderr or they'll corrupt
# the protocol stream.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    stream=sys.stderr,
)
log = logging.getLogger("quill-mcp")

from mcp.server.fastmcp import FastMCP  # noqa: E402

from .advisors import build_advisor  # noqa: E402
from .prompts import (  # noqa: E402
    consult_prompt,
    perspective_prompt,
    assumptions_prompt,
)


mcp = FastMCP("quill")
_advisor = build_advisor()
log.info(f"Quill MCP started — advisor: {_advisor.description}")


async def _ask(system_prompt: str, framing: str) -> str:
    framing = (framing or "").strip()
    if not framing:
        return "Quill needs a framing string from you — pass the situation you want a perspective on."
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": framing},
    ]
    reply = await _advisor.chat(messages, max_tokens=400, temperature=0.6)
    return reply or "Quill's advisor returned no reply (check the server log on stderr)."


@mcp.tool()
async def quill_consult(framing: str) -> str:
    """Reframe a stuck or frustrated moment from a humanistic perspective.

    Use when the developer seems stuck, frustrated, or when the conversation
    feels like it's spinning. Pass your framing of what's going on (2-4
    sentences). Quill's advisor returns a 2-4 sentence reframing — surface
    it to the developer alongside your own view.
    """
    return await _ask(consult_prompt(), framing)


@mcp.tool()
async def quill_perspective(framing: str) -> str:
    """Layer in another vantage point alongside your current thinking.

    Use when the developer is curious or exploring (NOT stuck) and would
    benefit from a perspective you haven't taken. Pass your framing of
    your current angle. Returns a 2-4 sentence perspective that's
    additive, not corrective.
    """
    return await _ask(perspective_prompt(), framing)


@mcp.tool()
async def quill_assumptions(framing: str) -> str:
    """Translate the technical assumptions you've been making into plain language.

    Use when the developer might be making decisions they don't understand
    because of technical jargon. Pass an enumeration of the load-bearing
    technical assumptions baked into your current approach. Returns a 3-5
    item plain-language yes/no checklist the developer can actually answer.
    """
    return await _ask(assumptions_prompt(), framing)


@mcp.tool()
async def quill_mosaic(task: str) -> str:
    """Produce a mosaic response to a multi-aspect task — two heads, not one.

    Decomposes the task into 2-4 voice-assigned slices, executes them in
    parallel with independent priors preserved (no agent sees the others'
    WIP), cross-reviews for consistency without homogenizing voice, and
    returns a structured response that *surfaces* rather than smooths the
    seams between agents.

    Best for multi-texture work where different aspects benefit from
    different voices: code + docs + UX + tests, or backend + frontend +
    migration plan, or methodology + findings + caveats. NOT for
    single-aspect tasks — the overhead isn't worth it.

    Cost: ~4-6x a single quill_consult call; wall-clock 60-180s.

    Requires both `codex` and `claude` CLIs installed and logged in
    (free with ChatGPT Plus + Claude Pro subscriptions).

    Returns the full structured response as JSON (task, plan, slices,
    cross_review_flags, voice_map, assembled_response). Surface the
    `assembled_response` field to the developer and treat the rest as
    metadata they can drill into if curious.
    """
    import json as _json
    from .mosaic import run_mosaic

    task = (task or "").strip()
    if not task:
        return "Quill mosaic needs a task description from you."
    result = await run_mosaic(task)
    return _json.dumps(result, indent=2, ensure_ascii=False)


def run() -> None:
    """Console-script entry point. `quill-mcp` runs this."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    run()

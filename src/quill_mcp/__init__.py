"""
Quill — a free open-source thinking partner for coding agents.

Mediates dialogue between the AI doing the work (Claude Code, Codex CLI,
Cursor, Cline, etc.) and a second AI giving perspective. Pairs naturally
with the developer's existing Claude Pro / ChatGPT Plus subscriptions —
no API key required.

Public surface:
- `quill_mcp.server` — the MCP server (entry point: `quill-mcp` console script)
- `quill_mcp.advisors` — advisor backend abstraction (api / codex_cli / claude_cli)
- `quill_mcp.prompts` — system prompts for the three thinking-partner skills

See https://github.com/YG3-ai/quill for docs and the research direction.
"""

__version__ = "0.1.1"

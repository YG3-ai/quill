# Quill — a thinking partner between two coding agents

**Free, MIT-licensed open source. A working product *and* an active
research project on coding-agent collaboration.**

Quill mediates dialogue between the AI doing the work and a second AI
giving perspective. The headline: **if you have a Claude Pro and a Codex
Pro subscription, you have a free dual-AI coding setup.** No API key
required, no per-token cost — Quill shells out to whichever CLIs you have
installed and relays their conversation.

Built by [Yugen LLC](https://yg3.ai). See
[RESEARCH.md](RESEARCH.md) for the research direction.

Three thinking-partner skills available in any agentic CLI Quill is
installed in:

- **`consult`** — for stuck/frustrated moments. Quill's advisor reframes
  what's actually going on.
- **`perspective`** — for exploring/curious moments. Layers in a vantage
  the doer hasn't taken.
- **`assumptions`** — for "what choices is the AI making that I don't
  understand?" Translates technical assumptions into plain-language
  yes/no questions.

In Claude Code specifically, you also get safety hooks (gatekeeper for
risky shell commands) and pre-push quality scans (secrets, debug
statements, TODOs, .env files).

## The four ways to run Quill

Pick the doer (the agent in your terminal) × the advisor (who Quill
calls when you ask for perspective):

| Doer (your terminal) | Advisor (Quill calls) | Cost | Setup |
|---|---|---|---|
| **Claude Code** | **Codex CLI** | Free (Codex Pro) | `ADVISOR_BACKEND=codex_cli` |
| **Codex CLI** | **Claude CLI** | Free (Claude Pro) | `ADVISOR_BACKEND=claude_cli` |
| Claude Code | API (Elysia, OpenAI, OpenRouter, Ollama, etc.) | Per-token | `ADVISOR_BACKEND=api` |
| Codex CLI / Cursor / Cline / Continue | API or any CLI | Varies | Same |

The two highlighted rows are the headline: **two coding agents in
deliberate dialogue, billed against subscriptions you already have.**

## Install

### If you use Claude Code

Inside Claude Code:

```bash
/plugin marketplace add yg3/quill
/plugin install quill@yg3
```

The plugin's monitor auto-starts the FastAPI server. The three skills
become `/quill:consult`, `/quill:perspective`, `/quill:assumptions`.

### If you use Codex CLI / Cursor / Cline / Continue / etc.

Quill ships an MCP server that any MCP-aware agent can talk to. After
cloning this repo and `pip install -r plugins/quill/server/requirements.txt`,
add to your agent's MCP config:

```json
{
  "mcpServers": {
    "quill": {
      "command": "python3",
      "args": ["/path/to/BRIDGES-Plugin/plugins/quill/server/mcp_server.py"]
    }
  }
}
```

Tools become `quill_consult`, `quill_perspective`, `quill_assumptions`.

## Configuring the advisor backend

Copy `plugins/quill/server/.env.example` → `.env`. Set:

```
ADVISOR_BACKEND=codex_cli   # or claude_cli, or api
```

For `codex_cli`: the `codex` binary must be on `$PATH`. Logged in via
your ChatGPT Plus/Pro account.

For `claude_cli`: the `claude` binary must be on `$PATH`. Logged in via
your Claude Pro/Max account.

For `api`: also set `AI_BASE_URL`, `AI_API_KEY`, `AI_MODEL`. Recommended
default: pair with **Elysia** (sign up at [app.yg3.ai](https://app.yg3.ai),
paid YG3 subscription). Or BYO any OpenAI-compatible endpoint —
OpenRouter, Ollama, Together, OpenAI direct, etc.

## Free, with a tip jar

Quill is free and MIT-licensed. We built it because the team uses it
daily and wanted others to have it too. Open source means you can read
what it does, fork it, contribute, or just inspect it before you wire
it into your workflow.

If Quill earns its keep in your workflow, you can leave a tip:

→ **[Support Quill ($5 suggested, name your price)](https://buy.stripe.com/5kQfZh5V30oabyO6ncb7y0i)**

100% of donations go to Yugen LLC and fund continued development +
the research direction below.

## Research direction

Quill is also a research instrument. The same framing through different
advisor backends produces measurably different responses (Codex tends to
cite specific files; Claude tends to reframe humanistically). That's a
publishable observation, and a real research program is reachable from
where this codebase already sits — voice differential studies,
dual-agent benefit benchmarks, advisor-doer pairing matrices.

See [RESEARCH.md](RESEARCH.md) for the open questions and how to
contribute. Planned HuggingFace presence: dataset of agent dialogues,
interactive Spaces demo, eventually a small fine-tuned model trained
specifically as a thinking-partner advisor.

## Repo shape

```
BRIDGES-Plugin/
├── .claude-plugin/
│   └── marketplace.json                  ← yg3 marketplace catalog
├── plugins/
│   └── quill/                            ← Claude Code plugin wrapper
│       ├── .claude-plugin/plugin.json
│       ├── skills/                       ← /quill:consult etc.
│       ├── hooks/hooks.json              ← gatekeeper, push checks
│       ├── monitors/monitors.json        ← auto-starts the FastAPI server
│       └── server/                       ← shared core (used by both
│           │                               the plugin AND the MCP server)
│           ├── bridge_server.py          ← FastAPI for Claude Code skills
│           ├── mcp_server.py             ← MCP entry for non-Claude-Code
│           ├── advisors/                 ← advisor backends
│           │   ├── api_advisor.py        ← OpenAI-compatible API
│           │   ├── codex_cli_advisor.py  ← shells out to `codex exec`
│           │   └── claude_cli_advisor.py ← shells out to `claude -p`
│           ├── prompts.py                ← shared system prompts
│           ├── checks.py                 ← deterministic push scans
│           └── .env.example
├── LICENSE                               ← MIT
├── USER_GUIDE.md                         ← customer-facing manual
├── ARCHITECTURE.md                       ← internal docs
├── RESEARCH.md                           ← research direction
├── OPEN_QUESTIONS.md                     ← what's not yet shipped
└── README.md
```

## Status

**v0.2 — works end-to-end, not yet on PyPI.** Both advisor backends
(Codex CLI, Claude CLI) and the API backend are validated through
both the FastAPI bridge (Claude Code plugin) and the MCP server (Codex
CLI / Cursor / Cline / Continue). Real install paths still need polish
for non-technical users — see [OPEN_QUESTIONS.md](OPEN_QUESTIONS.md).

## Trying it locally

```bash
# Inside Claude Code:
/plugin marketplace add /Users/samuelknox/Documents/BRIDGES-Plugin
/plugin install quill@yg3
```

Check `plugins/quill/server/quill.log` for the server startup line. To
test the welcome flow again after a fresh install, delete
`~/.quill/.welcomed` first.

## What's NOT done yet

- PyPI publication of `quill-mcp` (the install path for non-technical
  users — currently requires `git clone` + `pip install -r requirements.txt`)
- Verified monitor auto-start across Claude Code restarts on a fresh
  customer machine
- Codex CLI / Claude CLI invocation flag verification across CLI
  versions (defaults work today; may shift across releases)
- HuggingFace dataset + Spaces (planned, see RESEARCH.md)

See [OPEN_QUESTIONS.md](OPEN_QUESTIONS.md) for the full list.

## License

[MIT](LICENSE). Copyright (c) 2026 Yugen LLC.

## Relationship to the open-source BRIDGES repo

Quill's server core started as a copy of the local BRIDGES experimental
codebase at `../BRIDGES`. The two have diverged substantially: this
codebase has the advisor abstraction, MCP server, CLI advisor backends,
welcome/donation surfacing, and the research framing. Both are now
MIT-licensed; sync strategy is informal (manual port of useful changes
in either direction).

## Contributing

Issues, pull requests, and research observations welcome. If you're a
researcher interested in coding agent collaboration, see
[RESEARCH.md](RESEARCH.md) for the open questions and how to contribute.

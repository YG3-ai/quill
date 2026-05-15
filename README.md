![Quill — ask another mind.](imgs/quill_banner_readme.png)

# Quill — *ask another mind.*

**Free, MIT-licensed open source. A working product *and* an active
research project on coding-agent collaboration.**

Quill mediates dialogue between the AI doing the work and a second AI
giving perspective. The headline: **if you have a Claude Pro and a Codex
Pro subscription, you have a free dual-AI coding setup.** No API key
required, no per-token cost — Quill shells out to whichever CLIs you have
installed and relays their conversation.

Built by [YG3](https://yg3.ai). See
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

### Prerequisites

You'll need:

- **Python 3.10+** and `git`
- **Claude Code** (if using the plugin path), OR **any MCP-aware agent**
  (Codex CLI, Cursor, Cline, Continue) for the MCP path
- **A logged-in advisor CLI** matching whichever backend you'll
  configure:
  - `codex_cli` backend → `npm install -g @openai/codex` then `codex login`
  - `claude_cli` backend → `npm install -g @anthropic-ai/claude-code`
    then run `claude` once to log in
  - `api` backend → an OpenAI-compatible API key (Elysia / OpenAI /
    OpenRouter / Ollama / Together / etc.)

### Path 1 — MCP server (for Codex CLI / Cursor / Cline / Continue / etc.)

This is the recommended path. The MCP server works in any MCP-aware
agent and is the primary surface Quill is built around.

1. **Clone + install:**

   ```bash
   git clone https://github.com/YG3-ai/quill ~/quill
   cd ~/quill/plugins/quill/server
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   cp .env.example .env
   # then edit .env to set ADVISOR_BACKEND (see below)
   ```

2. **Wire into your agent's MCP config.**

   For **Codex CLI**:

   ```bash
   codex mcp add quill \
     --env ADVISOR_BACKEND=claude_cli \
     -- ~/quill/plugins/quill/server/.venv/bin/python3 \
        ~/quill/plugins/quill/server/mcp_server.py
   ```

   For **Cursor / Cline / Continue / other MCP-aware agents**, consult
   the agent's MCP docs. The `command` + `args` + `env` shape is the
   same — point at the venv's `python3` and `mcp_server.py`, set
   `ADVISOR_BACKEND` via env.

3. Tools available: `quill_consult`, `quill_perspective`,
   `quill_assumptions`. (Note: in Codex CLI's non-interactive `exec`
   mode you'll need `--dangerously-bypass-approvals-and-sandbox` to
   call MCP tools without a human approving each call. Interactive
   mode just prompts for approval.)

### Path 2 — Claude Code plugin

If you primarily use Claude Code, the plugin is a convenience wrapper
that exposes the three thinking-partner skills as slash commands and
adds Claude-Code-specific extras (safety gatekeeper on Bash/Edit/Write,
pre-push quality scans).

1. **Install the plugin** (inside Claude Code):

   ```
   /plugin marketplace add YG3-ai/quill
   /plugin install quill@yg3
   ```

2. **Set up the Python server** (one-time, from a terminal):

   The plugin install copies files but doesn't install Python deps.
   The plugin's files land somewhere under `~/.claude/plugins/`; the
   exact path is shown after install.

   ```bash
   cd <plugin-install-path>/plugins/quill/server
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   cp .env.example .env
   # then edit .env to set ADVISOR_BACKEND (see below)
   ```

3. **Restart Claude Code.** The plugin's monitor entry should fire and
   start the FastAPI server in the background. If it doesn't — see
   [Troubleshooting](#troubleshooting).

4. The three skills become `/quill:consult`, `/quill:perspective`,
   `/quill:assumptions`.

## Configuring the advisor backend

In `plugins/quill/server/.env`:

```
ADVISOR_BACKEND=codex_cli   # or claude_cli, or api
```

- **`codex_cli`** — uses the `codex` binary; bills against your
  ChatGPT Plus/Pro subscription. No API key needed.
- **`claude_cli`** — uses the `claude` binary; bills against your
  Claude Pro/Max subscription. No API key needed.
- **`api`** — uses an OpenAI-compatible HTTP endpoint. Also set
  `AI_BASE_URL`, `AI_API_KEY`, `AI_MODEL`. Recommended pairing:
  **Elysia** (sign up at [app.yg3.ai](https://app.yg3.ai), paid YG3
  subscription). Or BYO: OpenRouter, Ollama, Together, OpenAI direct,
  Groq, Anyscale — anything OpenAI-compatible.

## Troubleshooting

For the full guide, see [USER_GUIDE.md → Troubleshooting](USER_GUIDE.md#troubleshooting).

The most common issues:

**`BRIDGE UNAVAILABLE` when invoking a Quill skill in Claude Code**

The local FastAPI server isn't running. Start it manually:

```bash
cd <plugin-install-path>/plugins/quill/server
source .venv/bin/activate
python3 bridge_server.py
```

This is the most common issue today: monitor auto-start across plugin
installs is one of the things we're still verifying. If you hit it,
report it (issue or `help@yg3.ai`) — that data helps us close the gap.

**Empty reply from a CLI advisor**

Check `plugins/quill/server/quill.log` for an error like
`binary 'codex' not found` or `binary 'claude' not found`. Either
install the missing CLI, or set `CODEX_BIN` / `CLAUDE_BIN` in `.env`
to its full path.

**`claude: command not found` even though the VS Code extension works**

The VS Code Claude Code extension doesn't install a standalone
`claude` CLI. Install it separately:
`npm install -g @anthropic-ai/claude-code`.

## Free, with a tip jar

Quill is free and MIT-licensed. We built it because the team uses it
daily and wanted others to have it too. Open source means you can read
what it does, fork it, contribute, or just inspect it before you wire
it into your workflow.

[![Help keep Quill open and independent — Support via Stripe](imgs/support_quill_readme.png)](https://buy.stripe.com/5kQfZh5V30oabyO6ncb7y0i)

100% of donations go to YG3 and fund continued development + the
research direction below.

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

## Local development (for contributors)

To work on Quill itself, run the server directly from your clone:

```bash
git clone https://github.com/YG3-ai/quill
cd quill/plugins/quill/server
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # set ADVISOR_BACKEND
ADVISOR_BACKEND=codex_cli python3 bridge_server.py
```

To install the plugin from a local clone instead of from the GitHub
marketplace (useful for testing plugin changes):

```
/plugin marketplace add /absolute/path/to/your/quill/clone
/plugin install quill@yg3
```

Check `plugins/quill/server/quill.log` for the server startup line. To
test the welcome flow again on a dev machine: `rm ~/.quill/.welcomed`.

## What's NOT done yet

- PyPI publication of `quill-mcp` (the install path for non-technical
  users — currently requires `git clone` + `pip install -r requirements.txt`)
- Verified monitor auto-start across Claude Code restarts on a fresh
  customer machine
- Codex CLI / Claude CLI invocation flag verification across CLI
  versions (defaults work today; may shift across releases)
- HuggingFace dataset + Spaces (planned, see RESEARCH.md)

See [OPEN_QUESTIONS.md](OPEN_QUESTIONS.md) for the full list.

## Maintainers

- **Jacqueline Carter**
- **Sam Knox**
- **Partha Unnava**

## License

[MIT](LICENSE). Copyright (c) 2026 YG3.


## Contributing

Issues, pull requests, and research observations welcome. If you're a
researcher interested in coding agent collaboration, see
[RESEARCH.md](RESEARCH.md) for the open questions and how to contribute.

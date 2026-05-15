# Quill — User Guide

A thinking partner for Claude Code, Codex CLI, Cursor, Cline, Continue,
or any agentic CLI that speaks MCP.

The pitch: **two coding agents in deliberate dialogue, billed against
subscriptions you already have.** If you have a Claude Pro and a Codex
Pro subscription, you have a free dual-AI coding setup. No API key
required.

---

## The four ways to use Quill

Pick the doer (the agent in your terminal) × the advisor (who Quill
calls when you ask for perspective):

| Doer | Advisor | Cost | Setup |
|---|---|---|---|
| Claude Code | Codex CLI | Free (with Codex Pro) | `ADVISOR_BACKEND=codex_cli` |
| Codex CLI | Claude CLI | Free (with Claude Pro) | `ADVISOR_BACKEND=claude_cli` |
| Claude Code | API (Elysia / OpenAI / OpenRouter / Ollama / etc.) | Per-token | `ADVISOR_BACKEND=api` |
| Codex CLI / Cursor / Cline | API or any CLI | Varies | Same |

The first two rows are the dual-agent pitch. Both are validated end-to-end.

---

## Skills

Three thinking-partner skills, available everywhere Quill is installed:

- **`consult`** — for stuck or frustrated moments. The advisor reframes
  what's actually going on (humanistic, not procedural).
- **`perspective`** — for curious or exploring moments. The advisor layers
  in a vantage the doer hasn't taken (additive, not corrective).
- **`assumptions`** — translates the technical choices the doer has been
  making silently into plain-language yes/no questions a non-technical
  developer can actually answer.

In Claude Code: `/quill:consult <note>`, `/quill:perspective <note>`,
`/quill:assumptions [note]`.

In MCP-aware agents: tool names are `quill_consult`, `quill_perspective`,
`quill_assumptions`.

---

## Install

### As an MCP server (recommended; for Codex CLI / Cursor / Cline / Continue / etc.)

Install via PyPI:

```bash
pip install quill-mcp
```

`quill-mcp` is now a runnable command on your `$PATH`. Wire it into
your agent's MCP config. For Codex CLI:

```bash
codex mcp add quill --env ADVISOR_BACKEND=claude_cli -- quill-mcp
```

Replace `claude_cli` with whichever backend you want (see "Configure"
below). For Cursor / Cline / Continue / etc., consult the agent's MCP
docs — the `command` is `quill-mcp`, `env` carries `ADVISOR_BACKEND`.

> Want the bleeding-edge dev version instead?
> `pip install git+https://github.com/YG3-ai/quill`.

### As a Claude Code plugin

The plugin is a convenience wrapper that exposes the three skills as
slash commands and adds Claude-Code-specific extras (safety hooks,
pre-push quality scans).

```bash
pip install "quill-mcp[plugin]"   # core + FastAPI bridge deps
```

Then in Claude Code:

```
/plugin marketplace add YG3-ai/quill
/plugin install quill@yg3
```

The plugin's files land under `~/.claude/plugins/`; the exact path is
shown after install. From there, `cd <plugin-install-path>/plugins/quill/server`,
copy `.env.example` to `.env`, set `ADVISOR_BACKEND`, then restart
Claude Code. The plugin's monitor entry should auto-start the FastAPI
bridge.

---

## Configure the advisor backend

Copy `plugins/quill/server/.env.example` → `.env` and set
`ADVISOR_BACKEND` to one of three options.

### Option 1 — `codex_cli` (free with Codex Pro)

```
ADVISOR_BACKEND=codex_cli
```

Requirements:
- The `codex` binary on `$PATH` (via `npm install -g @openai/codex`)
- Logged in to Codex CLI (`codex login`)
- A ChatGPT Plus or Pro subscription

That's it. Quill will shell out to `codex exec --skip-git-repo-check
--sandbox read-only "<prompt>"` for every advisor call, capture the reply
via `--output-last-message`, and return it.

### Option 2 — `claude_cli` (free with Claude Pro)

```
ADVISOR_BACKEND=claude_cli
```

Requirements:
- The `claude` binary on `$PATH` (via `npm install -g @anthropic-ai/claude-code`)
- Logged in to Claude Code CLI
- A Claude Pro or Max subscription

Quill shells out to `claude -p "<prompt>"`. Note: this is the standalone
Claude Code CLI, separate from the VS Code extension.

### Option 3 — `api` (any OpenAI-compatible endpoint)

```
ADVISOR_BACKEND=api
AI_BASE_URL=https://your-endpoint/v1
AI_API_KEY=...
AI_MODEL=...
```

Recommended pairing: **Elysia**. Sign up at [app.yg3.ai](https://app.yg3.ai)
(paid YG3 subscription), generate a key, paste it in.

Or BYO any OpenAI-compatible endpoint:

| Endpoint | URL | Example model |
|---|---|---|
| OpenAI direct | `https://api.openai.com/v1` | `gpt-4o-mini` |
| OpenRouter | `https://openrouter.ai/api/v1` | any model they host |
| Ollama (local) | `http://localhost:11434/v1` | `llama3.1` |
| Together / Groq / Anyscale | their OpenAI-compat URL | their model name |

---

## Tips

### CLI advisors take longer than API calls

When the advisor is `codex_cli` or `claude_cli`, the CLI agent is doing
real exploration — reading files, looking at git history, forming a view.
A response that's 1-2 seconds via API can be 30-60 seconds via CLI. This
is a feature: you're getting evidence-grounded responses, not vibes. The
default `CLI_TIMEOUT` is 5 minutes, override via `.env` if you want it
tighter.

### Codex's voice vs Claude's voice

Same framing through the two CLI advisors produces *different* responses.
Codex tends to cite specific files (`bridge_server.py:42`); Claude tends
to reframe more humanistically. Neither is wrong — try both and pick the
one that fits the situation.

### Using Quill from Codex CLI in non-interactive flows

Codex's `exec` mode requires approval for MCP tool calls. In an
interactive Codex session, you just type "y" to approve. In a script or
non-interactive flow, you need:

```bash
codex exec --dangerously-bypass-approvals-and-sandbox --skip-git-repo-check '...'
```

The flag's name is intentionally alarming, but it's the only way to
authorize MCP tool calls without a human present. Only use this in
contexts you trust.

---

## Troubleshooting

### `BRIDGE UNAVAILABLE` in a Quill skill response

The local FastAPI server isn't running. From a terminal:

```bash
cd plugins/quill/server
source .venv/bin/activate
python3 bridge_server.py
```

If installed as a Claude Code plugin, the monitor should auto-start it
on plugin enable. If it didn't, that's a known issue — start it manually
once and report it.

### Empty reply from a CLI advisor

Check `plugins/quill/server/quill.log` for an error like
`binary 'claude' not found`. Either the binary isn't installed or it's
not on the bridge's `$PATH`. Override with `CLAUDE_BIN=/full/path/to/claude`
(or `CODEX_BIN=...`) in `.env`.

### `claude: command not found` even though the VS Code extension works

The VS Code extension bundles Claude Code; it doesn't install a
standalone `claude` CLI. Install the CLI separately:

```bash
npm install -g @anthropic-ai/claude-code
```

### Welcome message refires every time

Should only fire once per machine via `~/.quill/.welcomed`. If it's
refiring, your home directory may be unwritable (filesystem permissions,
read-only home, etc.) — Quill can't create the sentinel and fails open.
Check the bridge log for `"Could not write welcome sentinel"`.

### Codex says `Not inside a trusted directory`

Quill passes `--skip-git-repo-check` by default. If you see this anyway,
your Codex version may use a different flag — check `codex exec --help`
and override the args via a wrapper script pointed at by `CODEX_BIN`.

---

## Free, with a tip jar

Quill is free. We built it because the team uses it daily.

If it earns its keep:

→ **[Support Quill ($5 suggested, name your price)](https://buy.stripe.com/5kQfZh5V30oabyO6ncb7y0i)**

100% goes to YG3 and funds continued development.

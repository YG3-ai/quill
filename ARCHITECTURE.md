# Quill — Architecture

Internal docs for our future selves. If you (or Claude in a future
session) come back to this codebase cold, this should orient you in
under 5 minutes.

For customer-facing docs, see [USER_GUIDE.md](USER_GUIDE.md). For
in-progress decisions, see [OPEN_QUESTIONS.md](OPEN_QUESTIONS.md).

---

## Shape

```
quill/                                     ← repo root (also the marketplace)
├── pyproject.toml                         ← `quill-mcp` PyPI package metadata
├── src/quill_mcp/                         ← THE PYPI PACKAGE
│   ├── __init__.py                        ← `__version__ = "0.1.0"`
│   ├── server.py                          ← MCP entry, `quill-mcp` console script
│   ├── prompts.py                         ← shared system prompts
│   └── advisors/                          ← advisor backend abstraction
│       ├── base.py                        ← Advisor interface
│       ├── api_advisor.py                 ← OpenAI-compatible API
│       ├── _cli_common.py                 ← shared CLI subprocess plumbing
│       ├── codex_cli_advisor.py           ← shells out to `codex exec`
│       ├── claude_cli_advisor.py          ← shells out to `claude -p`
│       └── __init__.py                    ← registry, build_advisor()
├── .claude-plugin/marketplace.json        ← yg3 marketplace catalog
└── plugins/quill/                         ← Claude Code plugin wrapper
    ├── .claude-plugin/plugin.json
    ├── skills/                            ← /quill:consult etc.
    ├── hooks/hooks.json                   ← Claude-Code-specific
    ├── monitors/monitors.json             ← auto-starts bridge_server.py
    └── server/                            ← Claude-Code-specific bridge
        ├── bridge_server.py               ← FastAPI: imports `quill_mcp.*`
        ├── checks.py                      ← deterministic push scans
        ├── requirements.txt               ← single line: `quill-mcp[plugin]`
        └── .env.example
```

The PyPI package (`src/quill_mcp/`) is the asset everything builds on.
`bridge_server.py` is now a thin Claude-Code-specific HTTP wrapper that
imports the same `quill_mcp.advisors` and `quill_mcp.prompts` the MCP
server uses. The `[plugin]` extra in `pyproject.toml` carries
fastapi / uvicorn / bleach / markdown — needed only by the bridge,
not by the MCP server.

---

## The advisor abstraction

The whole "two CLIs talking" pattern hangs off one interface:

```python
# advisors/base.py
class Advisor:
    async def chat(
        self,
        messages: list[dict],
        *,
        model_hint: str | None = None,
        max_tokens: int = 400,
        temperature: float = 0.6,
        timeout: float | None = None,
    ) -> str: ...
```

Three backends exist:

- **`api_advisor.APIAdvisor`** — POSTs to an OpenAI-compatible
  `/chat/completions` endpoint. Honors all kwargs.
- **`codex_cli_advisor.CodexCLIAdvisor`** — shells out to
  `codex exec --skip-git-repo-check --sandbox read-only --output-last-message <tempfile> "<prompt>"`,
  reads the tempfile after the subprocess exits. `model_hint` /
  `max_tokens` / `temperature` are accepted but ignored.
- **`claude_cli_advisor.ClaudeCLIAdvisor`** — shells out to
  `claude -p "<prompt>"`, reads stdout. Same kwarg-ignoring behavior as
  Codex.

`advisors/__init__.py:build_advisor()` reads `ADVISOR_BACKEND` from the
environment and instantiates the right one. Both `bridge_server.py` and
`mcp_server.py` call `build_advisor()` once at startup and reuse it for
every request.

### Why `output_file_arg`?

Codex's `exec` subcommand prints a metadata header + the user prompt
echoed back + the response, all on stdout. Capturing stdout naively
returns that whole block as the "advisor reply." Codex's
`--output-last-message <FILE>` flag writes JUST the agent's final reply
to a file. `BaseCLIAdvisor` supports this via the optional
`output_file_arg` constructor parameter — set it to a flag name, and
the chat method creates a tempfile, inserts `<flag> <tempfile>` into the
command, reads from the tempfile after the subprocess exits, and unlinks
on the way out.

Claude CLI's `-p` mode prints clean output to stdout, so it doesn't need
this. If a future CLI needs different parsing (JSON output, marker
extraction, etc.), the cleanest extension is to add a method like
`extract_reply(stdout: str, stderr: str) -> str` to `BaseCLIAdvisor` and
let subclasses override.

### The CLI preamble

`_cli_common.py` wraps every CLI advisor call with a preamble that:
1. Tells the CLI agent it's a "thinking partner," not the doer
2. Encourages it to read the codebase, look at git history, etc.
3. Forbids agentic state changes (no edits, no commits, no destructive
   commands)
4. Tells it to override the system prompt's brevity instruction (which
   was tuned for smaller models like Elysia) and respond with a focused
   1-2 paragraphs

This is load-bearing. Without it, CLI agents default to either being
overly brief (chat-completion-like) or overly agentic (trying to fix
the developer's code). The preamble carves out the "second pair of eyes"
role explicitly.

---

## The skills (system prompts)

`prompts.py` holds three default prompts:

- `DEFAULT_CONSULT_PROMPT` — humanistic reframing
- `DEFAULT_PERSPECTIVE_PROMPT` — additive vantage
- `DEFAULT_ASSUMPTIONS_PROMPT` — jargon → plain-language yes/no checklist

Each is exposed via a function (`consult_prompt()`, etc.) that returns
the env-overridden value if set (`AI_SYSTEM_PROMPT_CONSULT`) or the
default. Both `bridge_server.py` and `mcp_server.py` import these — one
source of truth.

The prompts were tuned with Elysia (smaller model) in mind and ask for
brevity. For CLI advisors, the `_cli_common.py` preamble explicitly
overrides that brevity instruction. This is intentional: see the
`feedback_cli_advisor_constraints` memory for the rationale.

---

## The two server entry points

### `bridge_server.py` (FastAPI, for Claude Code)

A long-lived HTTP server on port 9000. Endpoints:

- `POST /hooks/{event_name}` — Claude Code lifecycle hooks (PreToolUse,
  UserPromptSubmit, ExitPlanMode, Stop, etc.)
- `POST /consult`, `POST /perspective`, `POST /assumptions` — the three
  thinking-partner skills
- `GET /health`, `GET /toggles`, `POST /toggles` — admin / dashboard
- `GET /dashboard`, `GET /docs/*` — embedded HTML/markdown viewer
- `POST /sessions/{id}/inject` — manual context injection (gated by
  `BRIDGE_TOKEN` if set)

Auto-starts via `plugins/quill/monitors/monitors.json` when the plugin
is enabled in Claude Code. SKILL.md files instruct Claude to POST to the
relevant endpoint via a small inline `python3 -c` block.

### `mcp_server.py` (FastMCP, for everything else)

A short-lived stdio process spawned per-session by the MCP client. Three
tools registered:

- `quill_consult(framing: str) -> str`
- `quill_perspective(framing: str) -> str`
- `quill_assumptions(framing: str) -> str`

Logs go to stderr (stdout is reserved for MCP protocol traffic — log
lines on stdout would corrupt the JSON-RPC stream). Built on
`mcp.server.fastmcp.FastMCP`.

Both servers call the same `_advisor.chat()` and the same
`prompts.consult_prompt()` etc. The only difference is the transport
shape (HTTP vs MCP stdio).

---

## The first-install welcome

`bridge_server.py` has a `_consume_welcome_if_first_run()` helper. On the
first call to `/consult`, `/perspective`, or `/assumptions`:

1. Check for `~/.quill/.welcomed` sentinel
2. If absent: include a `welcome` field in the response payload AND
   create the sentinel
3. SKILL.md files surface the welcome between
   `=== WELCOME ===` / `=== END WELCOME ===` markers, instructing Claude
   to render it once before the dialogue

After that the sentinel is set and welcome never fires again. Persists
across server restarts; in-memory `_welcome_consumed` flag suppresses
repeats within a single server lifetime.

The welcome message includes the Stripe donation link. To test the
welcome again on a dev machine: `rm ~/.quill/.welcomed` then restart
the server.

The MCP server doesn't currently emit the welcome — it would need its
own "first call" detection and a way to surface the message through MCP
tool responses (which are pure text). Worth adding when we wire up the
MCP install path properly.

---

## Adding a new advisor backend

Recipe (~30 lines):

1. New file: `advisors/my_backend_advisor.py`
2. Subclass `BaseCLIAdvisor` (if your backend is a CLI subprocess) or
   `Advisor` directly (if it's something else)
3. Implement `chat()` (or just configure the subprocess args if
   inheriting `BaseCLIAdvisor`)
4. Register in `advisors/__init__.py:build_advisor()` under a new
   `backend == "..."` branch
5. Document the new option in `.env.example` and `USER_GUIDE.md`

If the new backend has subprocess output that needs special parsing,
extend `BaseCLIAdvisor` with a hook (`extract_reply` or similar) and
override in your subclass. Keep the existing `output_file_arg` pattern
working for Codex.

---

## Adding a new skill

A "skill" is a system prompt + a way to invoke it. Recipe:

1. Add `DEFAULT_<NAME>_PROMPT` and a `<name>_prompt()` function to
   `prompts.py`
2. In `bridge_server.py`:
   - Add `AI_SYSTEM_PROMPT_<NAME> = <name>_prompt()` near the other
     prompt globals
   - Add an `<name>_advisor()` function that calls `_single_call()`
   - Add a `POST /<name>` endpoint that calls `_single_call_endpoint()`
   - Add a `<name>_enabled` toggle to `_TOGGLE_DEFAULTS`
3. In `mcp_server.py`:
   - Add a `@mcp.tool() async def quill_<name>(framing)` decorator
4. In Claude Code plugin:
   - Add `plugins/quill/skills/<name>/SKILL.md` modeled on existing ones
5. Document in `USER_GUIDE.md`

The two server entry points share the prompt definition; only the
transport-specific glue is duplicated.

---

## Decisions baked in (with rationale)

- **Local-server BYOK over hosted SaaS** — chosen because Quill is free
  and YG3 doesn't want operational burden. See the abandoned hosted-MCP
  thread for the trade-off analysis.
- **One repo, two surfaces (plugin + MCP)** — the shared core (server,
  advisors, prompts) is the asset; splitting would mean
  double-maintenance for ~no benefit. As of 2026-05-15 the core is
  extracted to `src/quill_mcp/` (PyPI package), and the Claude Code
  plugin's bridge depends on it.
- **CLI advisors loosened relative to API advisors** — Elysia (small
  model) needs tight brevity prompts; Codex/Claude (frontier) benefit
  from being expansive and reading code. The `_cli_common.py` preamble
  overrides the brevity instruction explicitly.
- **`--sandbox read-only` on Codex calls** — defense in depth. The
  preamble tells the agent not to take agentic actions; the sandbox
  enforces it at the OS level.
- **`--skip-git-repo-check` on Codex calls** — Codex refuses untrusted
  dirs by default; advisor calls happen from wherever the bridge was
  launched, so we bypass the check unconditionally.

---

## Known gaps

See [OPEN_QUESTIONS.md](OPEN_QUESTIONS.md). The big ones:

- Verified monitor auto-start across Claude Code restarts
- Python dependency install story for non-technical users (PyPI partly
  solves this)
- Codex CLI / Claude CLI invocation flag drift (defaults are good today;
  may shift across CLI versions)
- Update mechanism (git pull vs PyPI release vs tarball CDN)

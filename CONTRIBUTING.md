# Contributing to Quill

Thanks for considering a contribution. Quill is built in the open and
we welcome issues, pull requests, and research observations from anyone
who uses it.

## Reporting bugs or asking for features

Open an issue: https://github.com/YG3-ai/quill/issues. Before filing,
a quick search of existing issues helps avoid duplicates.

For bugs, include:
- What you ran (skill, advisor backend, agent CLI)
- What you expected vs. what happened
- The relevant log line from `plugins/quill/server/quill.log` if you
  hit it via the Claude Code plugin

## Setting up a dev environment

The full local development setup — editable install, running the MCP
server, running the FastAPI bridge, installing the plugin from a local
clone — lives in [USER_GUIDE.md → Local development](USER_GUIDE.md#local-development).

## Pull requests

- Branch from `main`, keep changes focused (one concern per PR).
- If you're changing skill behavior or advisor logic, mention what you
  tested it against (which backend, which agent).
- For non-trivial changes, opening an issue first to discuss the
  direction usually saves everyone time.

## Research contributions

Quill is also a research instrument. If you're interested in coding
agent collaboration as a research area — voice differential studies,
dual-agent benefit benchmarks, advisor-doer pairing matrices — see
[RESEARCH.md](RESEARCH.md) for the open questions and how to plug in.

## Code of conduct

Be kind. Disagree with ideas, not with people. We reserve the right
to remove contributions or contributors who make the project worse to
participate in.

## Pre-release testing on a clean machine

Before publishing a new version to PyPI or pushing a plugin marketplace
update, smoke-test on a machine (or user account) that has never run
Quill before. This catches the class of bug where "it works on my
machine because of state in my home directory."

If you don't have a second physical machine handy, the practical
equivalents are: a fresh macOS user account, a VM, or just thoroughly
clearing local state on your own machine before testing (see the
"clearing local state" subsection below).

### Prereqs on the test machine

- Python 3.10 or newer
- Node + npm (for the CLI advisors)
- `git`
- The advisor CLI you want to test against, logged in:
  - For `claude_cli`: `npm install -g @anthropic-ai/claude-code` then
    run `claude` once and complete login
  - For `codex_cli`: `npm install -g @openai/codex` then `codex login`
- For testing the Claude Code plugin path: Claude Code installed

### Step 1 — install from the channels you publish to

Don't install from a local clone for this test. The point is to
exercise the same install path a customer would.

```bash
# MCP server from PyPI:
pip install quill-mcp

# Claude Code plugin from the marketplace (inside Claude Code):
/plugin marketplace add YG3-ai/quill
/plugin install quill@yg3
```

### Step 2 — configure the advisor backend

Set `ADVISOR_BACKEND` in the plugin's `.env` (the install command prints
the path) or as an env var for the MCP server. Test at least one CLI
backend (`codex_cli` or `claude_cli`) since the API backend is the
easier path and CLI paths break more often across machines.

### Step 3 — run each skill end to end

For the MCP server (via Codex CLI or whichever MCP-aware agent you use):
- `quill_consult` with a real "I'm stuck on X" framing
- `quill_perspective` with a real "I'm exploring Y" framing
- `quill_assumptions` with a real list of assumptions
- `quill_mosaic` with a multi-aspect task (this one requires *both*
  `codex` and `claude` CLIs installed)

For the Claude Code plugin specifically:
- `/quill:consult <note>`
- `/quill:perspective <note>`
- `/quill:assumptions [note]`
- `/quill:mosaic <task>`
- Trigger the safety gatekeeper: try a deliberately risky shell command
  (e.g. `rm -rf` on a sacrificial file) and verify the hook intervenes
- Trigger the pre-push scan: `git push` from a sacrificial branch with
  a fake secret-looking string and verify it gets caught

### Step 4 — verify the first-run welcome

The welcome flow should fire exactly once per machine, then go quiet.
If you're re-testing on the same machine, reset the sentinel first:

```bash
rm ~/.quill/.welcomed
```

### Step 5 — verify the log line on startup

```bash
tail -n 20 <plugin-install-path>/plugins/quill/server/quill.log
```

You should see "Quill MCP started — advisor: …" with the backend you
configured. If you don't, the bridge didn't start — check stderr.

### Clearing local state (when testing on your own machine)

```bash
# Remove the welcome sentinel
rm -f ~/.quill/.welcomed

# Uninstall any prior install
pip uninstall -y quill-mcp

# Remove any prior plugin install
rm -rf ~/.claude/plugins/quill                              # adjust path if yours differs

# Drop any ADVISOR_BACKEND env vars from your shell
unset ADVISOR_BACKEND AI_BASE_URL AI_API_KEY AI_MODEL
```

Then proceed from Step 1.

### What "passing" looks like

- All four skills return real model output, not error strings or
  `BRIDGE UNAVAILABLE`
- The gatekeeper hooks fire on risky operations
- `quill.log` shows the startup line and no tracebacks
- The welcome message fired exactly once and didn't re-fire on a second
  skill invocation

### Automated smoke tests (run before any publish)

In addition to the manual flow above, run the local smoke tests:

```bash
cd /path/to/your/quill/clone
pip install -e ".[plugin]" pytest
pytest tests/
```

These don't replace the manual end-to-end test on a clean machine —
they catch the basic "package is shaped correctly and MCP protocol
still works" class of regression.

## License

By submitting a contribution, you agree it will be licensed under the
same [MIT License](LICENSE) as the rest of the project.

# Open Questions

Things that need decisions or work before Quill is rock-solid for
non-technical users. Reflects the strategic direction committed
2026-05-15: MIT open source, free with Stripe donations, both plugin
AND MCP surfaces stay, research angle co-equal with the product.

For the research direction itself, see [RESEARCH.md](RESEARCH.md).

---

## Blocks shipping (real install-flow gaps)

### 1. PyPI publication — RESOLVED (2026-05-15)

`quill-mcp 0.1.0` published to PyPI. End-to-end verified through a
TestPyPI dry-run first (clean wheel build, all 9 source files +
LICENSE + entry points + metadata; fresh-venv install works; `quill-mcp`
console script and module imports verified).

The MCP install is now one command:

```bash
pip install quill-mcp
codex mcp add quill --env ADVISOR_BACKEND=claude_cli -- quill-mcp
```

The Claude Code plugin install is two commands plus the marketplace
add:

```bash
pip install "quill-mcp[plugin]"
# then in Claude Code:
#   /plugin marketplace add YG3-ai/quill
#   /plugin install quill@yg3
```

Future releases: cut a new version in `pyproject.toml` + `__init__.py`,
`rm -rf dist/`, `python -m build`, `twine upload dist/*`. Eventually
move to GitHub Actions trusted-publisher flow so tag-push triggers
the release automatically.

### 2. Verify monitor auto-start across Claude Code restarts

`plugins/quill/monitors/monitors.json` runs `bash -c '... bridge_server.py'`
on plugin enable. **Untested in the plugin install context.** Things to
verify on a fresh customer machine:

- Does the monitor command actually run on plugin enable?
- Does it survive across Claude Code restarts (or does the user need to
  re-enable)?
- Does `${CLAUDE_PLUGIN_ROOT}` resolve correctly?
- What happens if Python isn't installed?
- What happens if port 9000 is already in use?

If monitor auto-start is unreliable, fall back to a `quill-start` script
+ README instruction.

### 3. Python dependencies install for the Claude Code plugin — RESOLVED via PyPI extraction (2026-05-15)

The plugin's `requirements.txt` now contains a single line:
`quill-mcp[plugin]>=0.1.0`. Customer install becomes:

```bash
pip install "quill-mcp[plugin]"
```

…which pulls in the core MCP package + FastAPI / uvicorn / bleach /
markdown via the `[plugin]` extra. After PyPI publication (#1) this
collapses the plugin's setup story to a single `pip install`.

What's still imperfect: the plugin install via Claude Code's
marketplace doesn't trigger this `pip install` automatically. Users
need to run it once manually. A future `bin/setup` script in the
plugin could automate this, but it's not blocking — the README and
USER_GUIDE document the step clearly.

---

## Blocks polish (nice but not blocking)

### 4. Codex CLI / Claude CLI invocation flag drift

Quill's defaults for the CLI advisors:
- `codex exec --skip-git-repo-check --sandbox read-only --output-last-message <tempfile>`
- `claude -p`

These match Codex CLI 0.130 and Claude Code CLI 2.1.141 as of test
date. Future CLI versions may rename or remove flags. We'd want either:
- Pin minimum CLI versions in docs
- Detect at startup and warn on incompatibility
- Provide a `CODEX_ARGS` / `CLAUDE_ARGS` override (already partially in
  place via `CODEX_BIN` wrapper script pattern)

### 5. Branding scrub in the server code

`bridge_server.py` and the prompts have hard-coded references to
"Elysia" (the YG3 model used as the API default) and "Merlin"
(gatekeeper model). Now that Quill is generic and supports multiple
backends, those names leak into log lines (`"[Elysia replied]"`),
prompt text (`"the bridge passes that to Elysia for a reframing"`), and
SKILL.md content.

The YG3 brand still wants Elysia visible (they're the recommended API
pairing), but the language should accommodate "Quill's advisor" or
"the configured advisor" as the generic case.

### 6. Welcome message in the MCP server

`bridge_server.py` has the `~/.quill/.welcomed` sentinel + `welcome`
field in `/consult` responses + SKILL.md handling for surfacing it.
`mcp_server.py` doesn't currently have an equivalent. MCP users miss
the donation prompt entirely.

Plan: port the same sentinel logic into the MCP server, prepend the
welcome to the first tool response of each fresh install.

### 7. Sessions persistence / multi-turn memory across MCP calls

The bridge server has session memory used by the planning advisor. The
MCP server's tools are stateless — each `quill_consult` call is fresh.
For some research questions (longitudinal study of advisor responses
to evolving framings), session continuity would be useful.

Add a `session_id: str | None` parameter to MCP tools, route through
the existing `sessions` store.

### 8. Telemetry / research data collection (opt-in)

For the research direction we need data. Per the research plan:

- Anonymized framings + responses across backends, with opt-in consent
- Privacy posture: what data leaves the machine, retention period,
  publication terms
- A clear `QUILL_TELEMETRY=1` opt-in env var (default off)
- Wire to a YG3-hosted endpoint or a S3 bucket

Don't build until we have a research design ready to use it. See
[RESEARCH.md](RESEARCH.md).

---

## Settled (no further decision needed)

These were open questions that the 2026-05-15 strategic direction
resolved:

- **Product name** — `quill` plugin, `yg3` marketplace, `Quill` brand,
  YG3 owner (Yugen is parent company), `help@yg3.ai` contact (resolved 2026-05-09)
- **License key validation** — N/A, free open source, no gating
- **API key onboarding** — `.env` with documented options; CLI backends
  need no API key
- **Update mechanism** — PyPI for MCP, plugin marketplace for the
  Claude Code plugin
- **Sync with upstream BRIDGES** — both MIT now, informal manual
  cherry-picking
- **Distribution / source hiding** — open source MIT, no Cython, source
  visible
- **Per-customer customization** — env-overridable system prompts +
  AI_BASE_URL already supports the customization that matters

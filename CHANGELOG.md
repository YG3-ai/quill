# Changelog

All notable changes to Quill are documented here.

---

## v0.2.2 — 2026-05-21

### Fixed (self-caught by Quill during internal review)

- **Windows compatibility** — `CLAUDE_BIN` / `CODEX_BIN` must point to the `.cmd` binary on Windows (e.g. `C:\...\npm\claude.cmd`). Python's `asyncio.create_subprocess_exec` cannot resolve npm shim scripts without the extension on Windows. Added documentation and `.env.example` guidance.
- **Gatekeeper now disabled by default** — when using a CLI backend (`codex_cli` or `claude_cli`), the gatekeeper has no API to call for decisions. Previously it would silently time out on every Bash/Edit/Write and fall through to prompting the human. Default changed to `GATEKEEPER_ENABLED=false`; enable it only when the `api` backend is configured.
- **Skill HTTP timeout** — bumped from 60s to 180s in `consult`, `perspective`, and `assumptions` skills. CLI advisors do real codebase exploration before replying; 60s was too tight on slower machines and Windows.
- **`MAX_INPUT_CHARS` default** — raised from 1000 to 5000. The previous default truncated any non-trivial plan to ~5 sentences, making plan-review much less useful.
- **Dashboard link at startup** — bridge now logs `Dashboard → http://127.0.0.1:<port>/dashboard` on startup so it's easy to find.
- **Skill frontmatter** — added missing `name:` field to all four `SKILL.md` files.
- **PowerShell gatekeeper coverage** — `DANGEROUS_BASH_PATTERNS` only matched Unix/bash idioms. Added PowerShell equivalents: `Remove-Item -Recurse -Force`, `Start-Process -Verb RunAs` (elevation), `Invoke-Expression` / `iex` (arbitrary code execution), `iwr | iex` (network pipe to shell), `Set-Content`/`Out-File` to system paths, `icacls /grant Everyone`. Caught by Quill reviewing its own codebase.
- **Push-denial counter** — documented that `_push_denial_counter` is ephemeral by design (bridge restart resets it) and that the counter doesn't distinguish persisting issues from new ones. Known limitation: a persistent secret waved through on attempt 3 is still surfaced as context.

### Changed

- **`ADVISOR_BACKEND` default** in `.env.example` changed from `api` to `codex_cli`, with clearer pairing guidance (Claude Code as doer + Codex CLI as advisor, and vice versa).
- **Dashboard branding** — renamed "Bridges" to "Quill Bridge" in HTML titles, alt text, FastAPI app title, and logo. Removed stale links to private internal repo. Dashboard logo updated to the README banner image.
- **Footer** — removed docs/github links that pointed to the private BRIDGES predecessor repo.

---

## v0.2.1 — 2026-05-15

- Mosaic mode shipped and empirically tested (4/4 wins on decisions-under-tension tasks).
- Planner robustness fix for edge cases in the ExitPlanMode review flow.
- Core MCP server and Claude Code FastAPI bridge both validated against all three advisor backends.

## v0.2.0 — 2026-05-01

- Mosaic mode introduced: decomposes multi-aspect tasks into voice-assigned slices, runs in parallel, cross-reviews for contradictions without homogenizing voice.
- Research spike-004 findings published.

## v0.1.0 — 2026-04-15

- Initial public release.
- `consult`, `perspective`, `assumptions` skills.
- Claude Code plugin with safety hooks and pre-push quality scans.
- Three advisor backends: `codex_cli`, `claude_cli`, `api`.

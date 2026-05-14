# Open Questions

Things that need decisions before this plugin is customer-ready.
Grouped by what they block.

---

## Blocks shipping

### 1. The product name — RESOLVED (2026-05-09)

- **Marketplace name:** `yg3`
- **Plugin name:** `quill` (slash commands: `/quill:consult`,
  `/quill:perspective`, `/quill:assumptions`)
- **Display brand:** Quill — "a thinking partner for Claude Code"
- **Owner:** Yugen LLC

Open sub-question: the owner email in `marketplace.json` is still
`TBD@yg3.ai` — pick the address customers should see.

### 2. License key validation

The plugin currently has zero license enforcement. Anyone who can
clone the repo can use it. To gate access:

**Where the check happens:** add a startup check in `bridge_server.py`
that hits `your-company.com/api/license/validate?key=<key>` on first
hook fire. Cache the result. Fail-closed if invalid.

**Where the key is stored:** options:
- `.env` file (`QUILL_LICENSE_KEY=...`) — same place as API key
- Macos Keychain / Windows Credential Manager — more secure, more setup
- Sent in via env var at install time

**What happens on failure:** clean error to Claude → friendly message
to developer → link to your account portal.

### 3. API key onboarding

The customer needs to provide an Anthropic (or OpenAI-compatible) API
key for the AI calls. Today's `.env.example` documents the variable
names. For a paid product:

- Where does the customer enter their key? `.env` file, GUI, env var,
  or your portal?
- Do you provide a default fallback (your company's key, with usage
  caps)? Or strict BYOK?
- Onboarding wizard? Or "edit this file" instructions?

### 4. Verify the monitor auto-start actually works

`monitors/monitors.json` currently uses a `bash -c` command that runs
the Python server in the foreground with redirected stdout. **This is
untested in the plugin context.** Things to verify:

- Does the monitor command actually run on plugin enable?
- Does it survive across Claude Code restarts (or does the user need
  to re-enable)?
- Does `${CLAUDE_PLUGIN_ROOT}` resolve correctly?
- What happens if Python isn't installed on the customer's machine?
- What happens if port 9000 is already in use?

If monitors don't work for this use case, fall back to a manual
"run this command once" install step in the README.

### 5. Python dependencies install

The server has dependencies (`fastapi`, `uvicorn`, `httpx`, etc.).
The plugin install copies the directory but does NOT run `pip install`.
Customer would need to:

```bash
cd ~/.claude/plugins/cache/<plugin>/server && pip install -r requirements.txt
```

Options:
- Bundle a `bin/setup` script that runs on first hook fire (chicken/egg)
- Document the manual step in the README and a `bin/quill-setup` command
- Ship a self-contained binary (PyInstaller) instead of raw Python — no
  Python install required, much bigger download
- Use `uv` or another Python launcher that handles deps automatically

This is probably **the biggest UX cliff** between "developer-friendly"
and "vibe-coder-friendly" install.

---

## Blocks scaling

### 6. Sync mechanism with the upstream `BRIDGES` repo

The `server/` directory is currently a **flat copy** of the open-source
BRIDGES code. Any improvement upstream needs to be re-copied here.
Options:

- Git submodule pointing at the upstream repo
- Build script that copies + transforms (e.g., scrubs Elysia branding)
- Symlink (won't survive plugin install — Anthropic copies the dir)
- Vendor permanently and let the two diverge

Symlink is the dev-time convenience but plugin install cache breaks
it. Build script is probably right for v1.

### 7. Branding scrub in the server code

`bridge_server.py` has hard-coded references to "Elysia" and "Merlin"
as model names and persona references. For the commercial product:

- Are these still the model names? (Maybe — your company may want to
  ship its own AI endpoint, in which case you'd rename)
- The default system prompts reference "Elysia" by name — those need
  rewriting if the brand is different
- Logging messages like `"[Elysia replied]"` need updating

This is a search-and-replace job once the brand is decided.

### 8. Update mechanism for the marketplace

Plugins update via `git pull` of the marketplace repo. For a private
marketplace, the customer needs to be granted access to the repo
(SSH key, Personal Access Token, etc.). Two patterns:

- Customer clones with their account (you grant them repo access)
- Customer adds a tarball URL (your CDN serves the latest), no git auth

Tarball is simpler for non-technical customers. Git is simpler for
operations.

---

## Nice-to-have

### 9. A non-monitor startup story

If monitors are flaky or noisy, alternatives:
- A `bin/quill-start` script + readme instruction "run this once"
- An OS-level launchd/systemd service installed by `bin/quill-install`
- Background it via `nohup` from a one-shot setup script

### 10. Telemetry / analytics

For a paid product you probably want to know:
- How many active installs
- Which slash commands are used most
- Latency / failure rates
- Churn signals (plugin disabled)

The bridge already logs locally; central reporting needs a privacy
posture decision (opt-in? opt-out? what data leaves the machine?).

### 11. Per-customer customization

Some customers may want to:
- Customize the system prompts (already supported via env vars)
- Use their own AI endpoint (already supported via `AI_BASE_URL`)
- Restrict which slash commands are available (toggles already exist)

The plumbing is there; whether to expose it as a UI or settings file
is a packaging decision.

# Quill — private Claude Code plugin marketplace

A private plugin marketplace under the **YG3** umbrella for distributing
**Quill** to your customers. The marketplace lives at this repo; the
plugin (`quill`) lives inside it. Your customer adds the marketplace
once, then installs the plugin:

```bash
/plugin marketplace add yg3/quill
/plugin install quill@yg3
```

## What Quill is

Quill is a thinking partner for Claude Code. The instrument you reach
for when you want to pause, get a second perspective, or check the
assumptions baked into what you're about to ship.

Three slash commands:
- **`/quill:consult <note>`** — for stuck/frustrated moments. Quill reframes what's actually going on.
- **`/quill:perspective <note>`** — for exploring/curious moments. Quill layers in a vantage Claude hasn't taken.
- **`/quill:assumptions [note]`** — for "what choices is Claude making that I don't understand?" Quill translates technical assumptions into plain-language yes/no questions.

Plus optional safety hooks (gatekeeper for risky shell commands) and
pre-push quality scans (secrets, debug statements, TODOs, .env files).

## Repo shape

```
BRIDGES-Plugin/
├── .claude-plugin/
│   └── marketplace.json                  ← the YG3 marketplace catalog
├── plugins/
│   └── quill/                            ← the plugin
│       ├── .claude-plugin/
│       │   └── plugin.json               ← plugin manifest
│       ├── skills/
│       │   ├── consult/SKILL.md          ← /quill:consult
│       │   ├── perspective/SKILL.md      ← /quill:perspective
│       │   └── assumptions/SKILL.md      ← /quill:assumptions
│       ├── hooks/
│       │   └── hooks.json                ← PreToolUse routing
│       ├── monitors/
│       │   └── monitors.json             ← auto-starts the FastAPI server
│       └── server/                       ← the FastAPI advisor server
│           ├── bridge_server.py
│           ├── checks.py
│           ├── requirements.txt
│           └── .env.example
├── LICENSE                               ← proprietary (placeholder)
├── OPEN_QUESTIONS.md                     ← things to decide before shipping
└── README.md                             ← this file
```

## Status

**v0.1 scaffold — NOT YET SHIPPABLE.** The structure is right; several
real questions need answering before customers should touch this. See
[OPEN_QUESTIONS.md](OPEN_QUESTIONS.md) for the list.

## Trying it locally (dev)

```bash
# Inside Claude Code:
/plugin marketplace add /Users/samuelknox/Documents/BRIDGES-Plugin
/plugin install quill@yg3
```

The Python server should auto-start via the monitor entry. Check
`plugins/quill/server/quill.log` for output.

## What's NOT done yet

- License key validation in the FastAPI server
- Customer onboarding flow (where does the API key + license token live?)
- Polish on `monitors.json` — needs verification that auto-start +
  log redirection actually works in practice
- Update mechanism for non-technical customers (git pull vs CDN tarball)
- The server code (`bridge_server.py`, `checks.py`) still has internal
  references to "Elysia" and "merlin" model names — needs a brand pass
  for customer-facing strings

See [OPEN_QUESTIONS.md](OPEN_QUESTIONS.md) for the full list and which
ones block shipping.

## Relationship to the open-source BRIDGES repo

This plugin is built from the existing local Bridges project at
`../BRIDGES`. The `server/` directory is currently a **copy** of that
project's `bridge_server.py` and `checks.py`. Any changes you make
upstream need to be re-copied here, or we set up a sync mechanism
(symlink, build script, git submodule). See OPEN_QUESTIONS for the
sync question.

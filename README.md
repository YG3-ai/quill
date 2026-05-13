# Bridges — private Claude Code plugin marketplace

A private plugin marketplace for distributing **Bridges** to your customers.
This repo is meant to be cloned into your customer's Claude Code via
`/plugin marketplace add`, after which they install the `bridges` plugin
itself with `/plugin install bridges@<your-marketplace-name>`.

## What this is

Bridges is a thinking partner for Claude Code. Three slash commands
(`/bridges:consult`, `/bridges:perspective`, `/bridges:assumptions`),
plus optional safety hooks for risky shell commands and pre-push
quality scans. See the [open-source predecessor](../BRIDGES) for the
full architecture.

## Repo shape

```
BRIDGES-Plugin/
├── .claude-plugin/
│   └── marketplace.json                  ← the marketplace catalog
├── plugins/
│   └── bridges/                          ← the actual plugin
│       ├── .claude-plugin/
│       │   └── plugin.json               ← plugin manifest
│       ├── skills/
│       │   ├── consult/SKILL.md          ← /bridges:consult
│       │   ├── perspective/SKILL.md      ← /bridges:perspective
│       │   └── assumptions/SKILL.md      ← /bridges:assumptions
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
/plugin install bridges@TBD-marketplace-name
```

(Replace the marketplace name once you've decided on the real one in
`.claude-plugin/marketplace.json`.)

The Python server should auto-start via the monitor entry. Check
`plugins/bridges/server/bridges.log` for output.

## What's NOT done yet

- License key validation in the FastAPI server
- Customer onboarding flow (where does the API key + license token live?)
- A real marketplace name (currently `TBD-marketplace-name`)
- Branding (currently still references "Bridges" / "the advisor"; no
  product name decided)
- Polish on `monitors.json` — needs verification that auto-start +
  log redirection actually works in practice
- Update mechanism (Anthropic's `/plugin update` works for git-hosted
  marketplaces; private hosting story TBD)
- Renaming/scoping the open-source predecessor's brand (Elysia/merlin
  references in the server code) for the commercial product

See [OPEN_QUESTIONS.md](OPEN_QUESTIONS.md) for the full list and which
ones block shipping.

## Relationship to the open-source BRIDGES repo

This plugin is built from the existing local Bridges project at
`../BRIDGES`. The `server/` directory is currently a **copy** of that
project's `bridge_server.py` and `checks.py`. Any changes you make
upstream need to be re-copied here, or we set up a sync mechanism
(symlink, build script, git submodule). See OPEN_QUESTIONS for the
sync question.

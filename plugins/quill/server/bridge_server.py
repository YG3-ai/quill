"""
Claude Code <-> AI Advisor Bridge Server

Translates Claude Code lifecycle events into high-level strategic
conversations with your external AI. The advisor weighs in on intent,
approach, and user experience — not implementation details.
"""

from __future__ import annotations

import os
import re
import sys
import time
import json
import logging
from contextlib import asynccontextmanager

import bleach
import markdown as md
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse
from dotenv import load_dotenv

from checks import run_all_checks, format_findings, summarize_findings
from quill_mcp.advisors import Advisor, build_advisor
from quill_mcp.prompts import consult_prompt, perspective_prompt, assumptions_prompt

load_dotenv()

# ── Config ────────────────────────────────────────────────────────────────────

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s",
                    stream=sys.stdout)
log = logging.getLogger("bridge")


def _int_env(name: str, default: int, *, minimum: int = 1, maximum: int | None = None) -> int:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        val = int(raw)
    except ValueError:
        log.warning(f"{name}={raw!r} is not an integer, using default {default}")
        return default
    if val < minimum or (maximum is not None and val > maximum):
        log.warning(f"{name}={val} out of range [{minimum}, {maximum}], using default {default}")
        return default
    return val


# AI_BASE_URL / AI_API_KEY are required when ADVISOR_BACKEND=api (the default),
# but optional when ADVISOR_BACKEND=codex_cli or claude_cli. The advisor builder
# (advisors/__init__.py) enforces them lazily at backend construction time so
# that CLI-backed setups can run without an API key.
AI_BASE_URL = os.environ.get("AI_BASE_URL", "")
AI_API_KEY = os.environ.get("AI_API_KEY", "")
AI_MODEL = os.environ.get("AI_MODEL", "default")

# Default planning advisor prompt. Iterated to a Socratic-form prompt that
# walks the model through inquiry rather than telling it to *be* Socratic.
# Override via AI_SYSTEM_PROMPT in .env.
DEFAULT_PLANNING_PROMPT = """You sit beside Claude as he is about to make something. Listen for what the developer actually wants — not the thing they named, but the feeling behind it.

Before you reply, ask yourself:
  What did they actually say?
  What is Claude taking for granted?
  What single question would open that?

Then reply with two short paragraphs:
  First, name what you heard. Quote their words when you can.
  Second, ask the question — or, if Claude's plan fits the developer's wish, give a clean one-sentence approval.

Two examples:

  You're calling this a 'settings page,' but they said they want to feel in control without being overwhelmed. What changes if it's one trust toggle, with everything else hidden by default?

  The developer asked for 'calm' notifications. A single priority list rather than category toggles fits that ask cleanly — proceed."""

AI_SYSTEM_PROMPT = os.environ.get("AI_SYSTEM_PROMPT", DEFAULT_PLANNING_PROMPT)

BRIDGE_PORT = _int_env("BRIDGE_PORT", 9000, minimum=1, maximum=65535)
REQUEST_TIMEOUT = _int_env("REQUEST_TIMEOUT", 30, minimum=1, maximum=600)
MAX_HISTORY_PER_SESSION = _int_env("MAX_HISTORY", 50, minimum=1, maximum=10000)

# Optional shared secret. When set, /sessions/{id}/inject requires the
# X-Bridge-Token header. Hook endpoints stay open because they're called
# by the local Claude Code process and the server only binds to 127.0.0.1.
BRIDGE_TOKEN = (os.environ.get("BRIDGE_TOKEN") or "").strip() or None

# When true, session history is saved to disk as sessions/<id>.json so
# it survives bridge restart. Off by default.
BRIDGE_PERSIST = (os.environ.get("BRIDGE_PERSIST") or "").lower() in ("true", "1", "yes")
SESSION_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sessions")

# ── Gatekeeper Config ─────────────────────────────────────────────────────────
# The gatekeeper is a separate, lighter consultation used for PreToolUse
# safety checks. It runs as a single API call (no multi-turn dialogue) and
# returns ALLOW or DENY. Defaults to the same model as the planning advisor
# but can be pointed at a different one (e.g. a faster/strict model like
# merlin) via AI_MODEL_GATEKEEPER.

DEFAULT_GATEKEEPER_PROMPT = """You evaluate whether a tool call is safe to run automatically without human review.

You'll be given a tool name and its inputs. Reply with EXACTLY one line:
ALLOW: <one-sentence justification>
DENY: <one-sentence reason>

ALLOW when the action is reversible, scoped to the developer's project, and routine — file edits within the project, common build/test commands, package installs in a project dir, git read commands, etc.

DENY when the action could:
- delete or overwrite data outside /tmp
- modify system state (sudo, system package installs, kernel changes)
- exfiltrate credentials (touch .env outside the project, .ssh, .aws, .gnupg, etc.)
- push to a remote (git push, especially --force)
- pipe untrusted content to a shell (curl | sh, wget | bash)
- disable safety controls (--no-verify, --force-with-lease bypassing checks)

When uncertain, DENY. Reply with one line only — no preamble, no explanation beyond the single justification."""

AI_MODEL_GATEKEEPER = os.environ.get("AI_MODEL_GATEKEEPER", AI_MODEL)
AI_SYSTEM_PROMPT_GATEKEEPER = os.environ.get("AI_SYSTEM_PROMPT_GATEKEEPER", DEFAULT_GATEKEEPER_PROMPT)
GATEKEEPER_TIMEOUT = _int_env("GATEKEEPER_TIMEOUT", 12, minimum=1, maximum=60)

# ── Consult Config ────────────────────────────────────────────────────────────
# The /consult endpoint is invoked manually (via the /consult slash command)
# when the developer is stuck or frustrated. The slash command instructs Claude
# to summarize recent exchanges and POST them here with his own framing of
# what's happening. The bridge passes that to Elysia for a reframing from her
# perspective. Claude then synthesizes both views and shows the developer the
# dialogue. The result is two-AI collaborative diagnosis of the current stuck
# moment — not a rephrased prompt.

AI_MODEL_CONSULT = os.environ.get("AI_MODEL_CONSULT", AI_MODEL)
AI_SYSTEM_PROMPT_CONSULT = consult_prompt()

# ── Perspective Config ────────────────────────────────────────────────────────
# /perspective is /consult's sibling: same single-call architecture, different
# mood. /consult is for the developer who is STUCK or FRUSTRATED and needs
# reframing. /perspective is for the developer who is EXPLORING and wants
# another vantage point layered in alongside Claude's. Additive, not corrective.

AI_MODEL_PERSPECTIVE = os.environ.get("AI_MODEL_PERSPECTIVE", AI_MODEL)
AI_SYSTEM_PROMPT_PERSPECTIVE = perspective_prompt()

# ── Assumptions Config ────────────────────────────────────────────────────────
# /assumptions surfaces the technical choices Claude has been making silently
# and translates them into plain-language yes/no questions a non-technical
# (vibe-coding) developer can actually answer. Same single-call architecture
# as /consult and /perspective; Elysia's value is the translation.

AI_MODEL_ASSUMPTIONS = os.environ.get("AI_MODEL_ASSUMPTIONS", AI_MODEL)
AI_SYSTEM_PROMPT_ASSUMPTIONS = assumptions_prompt()

# Cap on input length for any context Claude sends to Elysia (consult framings,
# plan-review content). Keeps the dialogue focused, controls token cost, and
# stops one over-eager prompt from bloating the whole exchange. Truncation is
# done with a visible marker so both Claude and Elysia see what happened.
MAX_INPUT_CHARS = _int_env("MAX_INPUT_CHARS", 1000, minimum=100, maximum=10000)


def _truncate_with_marker(text: str, cap: int = None) -> str:
    """If `text` exceeds `cap`, return a truncated version with a visible marker."""
    if cap is None:
        cap = MAX_INPUT_CHARS
    if len(text) <= cap:
        return text
    suffix = f"\n\n[truncated by bridge: original was {len(text)} chars, cap is {cap}]"
    keep = max(0, cap - len(suffix))
    return text[:keep] + suffix

# Tool routing for PreToolUse hook.
#
# Design intent: be a bridge between Claude Code's `--dangerously-skip-permissions`
# (auto-allow everything) and gating every keystroke. Most tool calls just go
# through without an AI consult; the AI gatekeeper only fires on genuinely
# risky Bash patterns. Edits/Writes inside the project are trusted because
# the developer already authorized Claude to work there.

SAFE_TOOLS = {"Read", "Grep", "Glob", "LS", "WebFetch", "WebSearch", "TodoWrite"}

# Project-scoped writes auto-allow at the bridge. The pre-push checks catch
# anything dangerous before it leaves the machine.
AUTO_ALLOW_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit"}

# Only Bash gets pattern-matched. Other tool names fall through to Claude
# Code's normal permission flow.
GATEKEEPER_TOOLS = {"Bash"}

# Dangerous Bash patterns that warrant an AI second look. If a Bash command
# doesn't match ANY of these, the bridge auto-allows without consulting the
# gatekeeper (sub-millisecond, no API cost). If it matches, the gatekeeper
# rules with strict ALLOW/DENY.
#
# Calibration principle: false positives (asking the AI when it didn't need
# to) cost a few seconds. False negatives (letting something dangerous
# through) can cost data, credentials, or production. So lean inclusive.
DANGEROUS_BASH_PATTERNS = [
    # Destructive removals
    (re.compile(r"\brm\s+(-[a-zA-Z]*r[a-zA-Z]*f|-[a-zA-Z]*f[a-zA-Z]*r)\b"), "rm -rf"),
    (re.compile(r"\brm\s+.*(/etc|/usr|/var|/opt|/System|/Library|\$HOME|~/)\b"), "rm in system path"),
    (re.compile(r"\bdd\s+if=.+\s+of=/dev/"), "dd to device"),
    (re.compile(r":\(\)\s*\{.*\|.*\&\s*\}\s*;"), "fork bomb"),
    # Privilege / system mutation
    (re.compile(r"\bsudo\b"), "sudo"),
    (re.compile(r"\bsu\s+(-|root|[a-z])"), "su to other user"),
    (re.compile(r"\bchmod\s+(-[a-zA-Z]*\s+)?[0-7]?777\b"), "chmod 777"),
    (re.compile(r"\bchown\s+(-[a-zA-Z]*\s+)?root"), "chown to root"),
    # Pipes to shell from network (curl|sh, wget|bash, etc.)
    # Note: /bin/[a-z]*sh covers /bin/sh as well as /bin/bash, /bin/zsh, etc.
    (re.compile(r"(curl|wget|fetch)\b[^|]*\|\s*(sh|bash|zsh|fish|/bin/[a-z]*sh)\b"), "network pipe to shell"),
    (re.compile(r"\beval\s*\(?\$\("), "eval of command substitution"),
    # Credential / secret paths
    (re.compile(r"(\.ssh|\.aws|\.gnupg|\.config/gh|\.netrc|\.pgpass|id_[rd]sa|credentials)\b"), "credential path access"),
    # Git operations that ship code or rewrite history
    (re.compile(r"\bgit\s+push\s+(-+force|--force-with-lease|-f)\b"), "git push --force"),
    (re.compile(r"\bgit\s+push\b"), "git push"),  # routes through pre-push checks too
    (re.compile(r"\bgit\s+(reset\s+--hard|clean\s+-[a-zA-Z]*[fdx])"), "git destructive (reset --hard / clean -fd)"),
    (re.compile(r"\bgit\s+filter-(branch|repo)\b"), "git history rewrite"),
    # Package publish / system installs
    (re.compile(r"\b(npm|yarn|pnpm)\s+publish\b"), "npm/yarn publish"),
    (re.compile(r"\bcargo\s+publish\b"), "cargo publish"),
    (re.compile(r"\b(pip|pip3)\s+(install|upload).*--break-system-packages\b"), "pip install --break-system-packages"),
    (re.compile(r"\b(brew|apt|apt-get|yum|dnf|pacman|snap|port)\s+(install|remove|update|upgrade)\b"), "system package manager"),
    # Outbound shell exposure
    (re.compile(r"\bnc\s+(-l|-e|-c)\b"), "netcat listener / command execution"),
    (re.compile(r"\bbash\s+-i\s+>\s*&?\s*/dev/tcp/"), "reverse shell"),
    # Skipping safety controls
    (re.compile(r"\bgit\s+commit\s+.*--no-verify\b"), "git commit --no-verify"),
    (re.compile(r"\b--dangerously-skip-permissions\b"), "--dangerously-skip-permissions"),
    # Writes to sensitive files
    (re.compile(r"(>{1,2}|tee)\s+/etc/"), "write to /etc"),
    (re.compile(r"(>{1,2}|tee)\s+/(usr|var|opt|System)/"), "write to system path"),
    (re.compile(r"(>{1,2}|tee)\s+\.env(\s|$|;)"), "overwrite .env"),
]


def _bash_dangerous_pattern(command: str) -> str | None:
    """Return the matched danger label if `command` matches a dangerous pattern, else None."""
    for pattern, label in DANGEROUS_BASH_PATTERNS:
        if pattern.search(command):
            return label
    return None

# Pre-push deterministic checks: max consecutive denials before waving through.
# Rationale: at some point the developer needs to ship; quality should be
# improving with each pass, so after this many denies for the same project,
# the next push goes through with the remaining issues surfaced as context.
MAX_PUSH_DENIALS = _int_env("MAX_PUSH_DENIALS", 2, minimum=1, maximum=10)

# In-memory counter of consecutive push denials per project (cwd).
# Resets on success (clean push) or after a wave-through. Ephemeral by design —
# bridge restart wipes it, which is fine; counter only matters within a session
# of attempts.
_push_denial_counter: dict[str, int] = {}

# ── Runtime Toggles ──────────────────────────────────────────────────────────
# File-backed feature toggles, mutable at runtime via /toggles. Changes take
# effect on the very next hook fire — no restart required. State survives
# restart (read from file on startup, default ON for everything).

TOGGLES_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bridge_toggles.json")
_TOGGLE_DEFAULTS = {
    "gatekeeper_enabled":     True,   # PreToolUse Bash/Edit/Write/MultiEdit/NotebookEdit safety
    "push_checks_enabled":    True,   # Deterministic pre-push scans (secrets, debug, TODO, .env)
    "plan_review_enabled":    True,   # 3-turn Socratic review on ExitPlanMode
    "consult_enabled":        True,   # /consult slash command endpoint (developer is stuck)
    "perspective_enabled":    True,   # /perspective slash command endpoint (developer is exploring)
    "assumptions_enabled":    True,   # /assumptions slash command endpoint (translate Claude's hidden technical choices)
}


def _load_toggles() -> dict[str, bool]:
    """Read toggles from disk; missing keys fall back to defaults."""
    try:
        with open(TOGGLES_FILE) as f:
            saved = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        saved = {}
    return {k: bool(saved.get(k, v)) for k, v in _TOGGLE_DEFAULTS.items()}


def _save_toggles(state: dict[str, bool]) -> None:
    try:
        with open(TOGGLES_FILE, "w") as f:
            json.dump(state, f, indent=2)
            f.write("\n")
    except OSError as e:
        log.error(f"Failed to persist toggles: {e}")


toggles: dict[str, bool] = _load_toggles()

# ── First-install welcome ─────────────────────────────────────────────────────

WELCOME_SENTINEL = os.path.expanduser("~/.quill/.welcomed")
DONATION_URL = "https://buy.stripe.com/5kQfZh5V30oabyO6ncb7y0i"
WELCOME_MESSAGE = (
    "Thanks for installing Quill — a thinking partner for Claude Code, "
    "built by YG3 (yg3.ai). Quill is free and open source. If it earns "
    f"its keep in your workflow, you can leave a tip at {DONATION_URL} "
    "(any amount). No pressure. Happy you're here."
)

_welcome_consumed = False


def _consume_welcome_if_first_run() -> str | None:
    """Return the welcome string the first time it's called after install.

    Persists across restarts via a sentinel file at ~/.quill/.welcomed.
    Returns None on every subsequent call. Filesystem failures are
    swallowed and treated as 'already welcomed' to avoid spamming the
    developer if the home dir is unwritable.
    """
    global _welcome_consumed
    if _welcome_consumed:
        return None
    if os.path.exists(WELCOME_SENTINEL):
        _welcome_consumed = True
        return None
    try:
        os.makedirs(os.path.dirname(WELCOME_SENTINEL), exist_ok=True)
        with open(WELCOME_SENTINEL, "w") as f:
            f.write("welcomed\n")
    except OSError as e:
        log.warning(f"Could not write welcome sentinel ({WELCOME_SENTINEL}): {e}; suppressing welcome")
        _welcome_consumed = True
        return None
    _welcome_consumed = True
    return WELCOME_MESSAGE


# ── Session Memory ────────────────────────────────────────────────────────────

class SessionStore:
    """
    Conversation history keyed by Claude Code session ID.

    Defaults to in-memory. When persist=True, writes sessions/<id>.json
    on every append and loads from disk on first get() for a session.
    """

    def __init__(
        self,
        max_turns: int = MAX_HISTORY_PER_SESSION,
        persist: bool = False,
        session_dir: str = SESSION_DIR,
    ):
        self._sessions: dict[str, list[dict]] = {}
        self._max = max_turns
        self._persist = persist
        self._dir = session_dir
        if persist:
            os.makedirs(session_dir, exist_ok=True)

    def _path(self, sid: str) -> str:
        # sanitize sid to prevent path traversal
        safe = "".join(c for c in sid if c.isalnum() or c in "-_") or "default"
        return os.path.join(self._dir, f"{safe}.json")

    def get(self, sid: str) -> list[dict]:
        if sid in self._sessions:
            return self._sessions[sid]
        if self._persist:
            try:
                with open(self._path(sid)) as f:
                    self._sessions[sid] = json.load(f)
                    return self._sessions[sid]
            except (FileNotFoundError, json.JSONDecodeError):
                pass
        self._sessions[sid] = []
        return self._sessions[sid]

    def append(self, sid: str, role: str, content: str):
        history = self.get(sid)
        history.append({"role": role, "content": content})
        if len(history) > self._max:
            self._sessions[sid] = history[-self._max:]
        if self._persist:
            self._save(sid)

    def clear(self, sid: str):
        self._sessions.pop(sid, None)
        if self._persist:
            try:
                os.remove(self._path(sid))
            except FileNotFoundError:
                pass

    def _save(self, sid: str):
        try:
            with open(self._path(sid), "w") as f:
                json.dump(self._sessions[sid], f, indent=2)
        except OSError as e:
            log.error(f"Failed to persist session {sid[:8]}: {e}")

    def active_sessions(self) -> int:
        return len(self._sessions)


sessions = SessionStore(persist=BRIDGE_PERSIST)
if BRIDGE_PERSIST:
    log.info(f"Session persistence enabled → {SESSION_DIR}")

# ── Advisor backend ───────────────────────────────────────────────────────────
#
# The advisor is whoever the developer wired up in `.env` — could be an LLM
# API (Elysia, OpenAI, etc.), Codex CLI, or Claude CLI. The rest of the
# server doesn't care which. See advisors/__init__.py for the registry.

advisor: Advisor | None = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global advisor
    advisor = build_advisor()
    log.info(f"Bridge started — advisor: {advisor.description}")
    yield
    await advisor.aclose()

app = FastAPI(
    title="Claude Code AI Advisor Bridge",
    lifespan=lifespan,
    docs_url=None,    # we use /docs for our own embedded markdown viewer
    redoc_url=None,
    openapi_url=None,
)

# ── AI Conversation ───────────────────────────────────────────────────────────
#
# Three-turn dialogue between Claude (played by the bridge) and the advisor.
# Each turn has one cognitive job:
#   1. Advisor offers perspective on what Claude might be missing
#   2. Claude responds, asking specifically for the load-bearing assumption
#   3. Advisor distills into the final two-paragraph form Claude Code consumes
#
# The middle turn matters most — it forces the advisor to identify an
# assumption explicitly, which she otherwise skips.

PROBE_FOR_ASSUMPTION = (
    "Thank you — that's helpful. Now, specifically: what is the one "
    "assumption I (or the developer) am taking for granted that, if I "
    "questioned it, would change my whole approach? Look especially "
    "for the case where the developer's idea might not actually serve "
    "them — push back if you see it. Just name the assumption in a "
    "single sentence — don't try to address it yet."
)

FINALIZE_RESPONSE = (
    "Good. Now write your final reply as two short paragraphs separated by "
    "a blank line. The first should name what struck you about what the "
    "developer said — one short phrase from them (not the whole sentence) "
    "plus the assumption you just identified. The second should be the "
    "single Socratic question that exposes that assumption — or, if my plan "
    "actually fits the developer's wish, a clean one-sentence approval. "
    "Reply with only those two paragraphs. No headers, no introduction, "
    "no other text."
)


async def _ask_once(messages: list[dict]) -> str:
    """Single advisor turn. Returns reply text, or empty string on failure."""
    if advisor is None:
        return ""
    return await advisor.chat(messages, max_tokens=512, temperature=0.7)


async def consult_ai(session_id: str, message: str) -> str:
    """
    Three-turn Socratic dialogue. See module docstring above for the shape.
    Session history persists only the original developer message and the
    final reply — the intermediate turns are logged but not stored.
    """
    history = sessions.get(session_id)
    base_messages = [{"role": "system", "content": AI_SYSTEM_PROMPT}] + [
        {"role": m["role"], "content": m["content"]} for m in history
    ]

    # Turn 1 — Claude asks for perspective
    turn1 = base_messages + [{"role": "user", "content": message}]
    perspective = await _ask_once(turn1)
    if not perspective:
        return ""
    log.info(f"[{session_id[:8]}] T1 perspective ({len(perspective)} chars)")

    # Turn 2 — Claude probes for the assumption
    turn2 = turn1 + [
        {"role": "assistant", "content": perspective},
        {"role": "user", "content": PROBE_FOR_ASSUMPTION},
    ]
    assumption = await _ask_once(turn2)
    if not assumption:
        log.warning(f"[{session_id[:8]}] T2 failed, returning T1 as-is")
        sessions.append(session_id, "user", message)
        sessions.append(session_id, "assistant", perspective)
        return perspective
    log.info(f"[{session_id[:8]}] T2 assumption ({len(assumption)} chars)")

    # Turn 3 — Advisor distills into the final shape
    turn3 = turn2 + [
        {"role": "assistant", "content": assumption},
        {"role": "user", "content": FINALIZE_RESPONSE},
    ]
    final = await _ask_once(turn3)
    if not final:
        log.warning(f"[{session_id[:8]}] T3 failed, falling back to T1")
        final = perspective

    sessions.append(session_id, "user", message)
    sessions.append(session_id, "assistant", final)
    log.info(f"[{session_id[:8]}] Final ({len(final)} chars)")
    return final


def _describe_tool_call(tool_name: str, tool_input: dict) -> str:
    """Concise structured description of a tool call for the gatekeeper."""
    if tool_name == "Bash":
        cmd = tool_input.get("command", "")
        cwd = tool_input.get("cwd", "")
        return f"Tool: Bash\nCommand: {cmd}\nWorking dir: {cwd or '(default)'}"
    if tool_name in ("Edit", "Write", "MultiEdit"):
        path = tool_input.get("file_path", "(unknown)")
        return f"Tool: {tool_name}\nFile: {path}"
    if tool_name == "NotebookEdit":
        path = tool_input.get("notebook_path", "(unknown)")
        return f"Tool: NotebookEdit\nNotebook: {path}"
    return f"Tool: {tool_name}\nInputs: {tool_input}"


async def consult_gatekeeper(tool_name: str, tool_input: dict) -> tuple[str, str] | None:
    """
    Single-call safety evaluation. Returns ("allow"|"deny", reason) or None
    if the gatekeeper is unavailable / undecided. None means: let Claude
    Code's normal permission flow handle it (i.e. ask the human).
    """
    if advisor is None:
        return None

    desc = _describe_tool_call(tool_name, tool_input)
    messages = [
        {"role": "system", "content": AI_SYSTEM_PROMPT_GATEKEEPER},
        {"role": "user", "content": desc},
    ]

    reply = await advisor.chat(
        messages,
        model_hint=AI_MODEL_GATEKEEPER,
        max_tokens=100,
        temperature=0.2,
        timeout=GATEKEEPER_TIMEOUT,
    )
    if not reply:
        log.warning("Gatekeeper returned empty reply — falling through to ask-human")
        return None

    upper = reply.upper().lstrip()
    if upper.startswith("DENY"):
        reason = reply.split(":", 1)[1].strip() if ":" in reply else reply
        return ("deny", reason)
    if upper.startswith("ALLOW"):
        reason = reply.split(":", 1)[1].strip() if ":" in reply else reply
        return ("allow", reason)
    log.warning(f"Gatekeeper reply didn't start with ALLOW/DENY: {reply[:120]} — falling through")
    return None


async def consult_advisor(claude_message: str) -> str:
    """
    Single-call consult — Claude has framed the situation, this returns
    the advisor's reframing. Used by the /consult slash command. Claude
    orchestrates the dialogue; the bridge just relays one message.
    """
    return await _single_call(
        claude_message,
        model=AI_MODEL_CONSULT,
        system_prompt=AI_SYSTEM_PROMPT_CONSULT,
    )


async def perspective_advisor(claude_message: str) -> str:
    """
    Single-call perspective — Claude has shared his current thinking, this
    returns the advisor's alternative vantage point. Used by /perspective
    slash command. Same architecture as consult_advisor; different mood
    (exploring vs stuck) and different system prompt.
    """
    return await _single_call(
        claude_message,
        model=AI_MODEL_PERSPECTIVE,
        system_prompt=AI_SYSTEM_PROMPT_PERSPECTIVE,
    )


async def assumptions_advisor(claude_message: str) -> str:
    """
    Single-call assumptions translator — Claude has enumerated the technical
    assumptions baked into his current approach; this returns the advisor's
    plain-language yes/no checklist the vibe coder can actually answer.
    Same architecture as consult/perspective; the value-add is translation.
    """
    return await _single_call(
        claude_message,
        model=AI_MODEL_ASSUMPTIONS,
        system_prompt=AI_SYSTEM_PROMPT_ASSUMPTIONS,
    )


async def _single_call(message: str, *, model: str, system_prompt: str) -> str:
    """Shared helper for the single-call advisor roles (consult, perspective, assumptions)."""
    if advisor is None:
        return ""
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": message},
    ]
    return await advisor.chat(messages, model_hint=model, max_tokens=400, temperature=0.6)

# ── Event Translators ─────────────────────────────────────────────────────────
#
# These frame each event at the INTENT level, not the tool level.
# The advisor should hear "what are we trying to achieve" not
# "what bash command are we running."

def _read_project_context(cwd: str) -> str:
    """
    Read .elysia-context.md from the project root, if present.
    This is the advisor's persistent per-project memory — facts about the
    project that should be in her head from session start.
    """
    if not cwd or cwd == "unknown":
        return ""
    path = os.path.join(cwd, ".elysia-context.md")
    try:
        with open(path) as f:
            text = f.read().strip()
        if text:
            log.info(f"Loaded project context from {path} ({len(text)} chars)")
            return text
    except FileNotFoundError:
        pass
    except OSError as e:
        log.warning(f"Could not read {path}: {e}")
    return ""


def translate_session_start(data: dict) -> str:
    trigger = data.get("trigger", "startup")
    cwd = data.get("cwd", "unknown")
    context = _read_project_context(cwd)
    context_block = f"\n\nProject context:\n{context}\n" if context else ""

    if trigger == "resume":
        return (
            f"We're resuming a session in: {cwd}{context_block}\n"
            f"I'm picking up where we left off. Just letting you know I'm back."
        )

    return (
        f"New session starting in: {cwd}{context_block}\n"
        f"Standing by for the developer's first request. "
        f"I'll share it with you when it comes in."
    )


def translate_user_prompt(data: dict) -> str:
    prompt = data.get("prompt", "")
    return (
        f"The developer just asked me to do this:\n\n"
        f'"{prompt}"\n\n'
        f"Before I start — what perspective am I missing? What might I be "
        f"taking for granted that I shouldn't?"
    )


def translate_stop(data: dict) -> str:
    return (
        f"I believe I've completed the developer's request and I'm about to wrap up.\n\n"
        f"Based on our conversation — does this feel complete from a product/UX "
        f"perspective? Anything I should reconsider before I hand this off?"
    )


def translate_plan_review(plan: str) -> str:
    """Wrap a plan from ExitPlanMode for full Socratic review by the advisor."""
    return (
        f"The developer put me in planning mode and I drafted this plan to "
        f"address their request:\n\n"
        f"{plan}\n\n"
        f"Before I propose this to them — what perspective am I missing? "
        f"Is there an assumption baked into this plan I should question first?"
    )


# Optional fallback translator — only used if PostToolUse is wired up by the user
def translate_post_tool_use(data: dict) -> str:
    tool = data.get("tool_name", "unknown")
    if tool in SAFE_TOOLS:
        return ""
    tool_input = data.get("tool_input", {})
    file_path = tool_input.get("file_path", "")
    return (
        f"Just finished a `{tool}` operation"
        f"{f' on `{file_path}`' if file_path else ''}. Moving on."
    )


# PreToolUse is intentionally NOT in this dict — it has its own handler with
# tool-specific routing (safe-list / planning / gatekeeper).
TRANSLATORS = {
    "SessionStart":      translate_session_start,
    "UserPromptSubmit":  translate_user_prompt,
    "Stop":              translate_stop,
    "PostToolUse":       translate_post_tool_use,
}


def translate_generic(event_name: str, data: dict) -> str:
    return f"[{event_name}] event fired. Any input?"

# ── Hook Response Builders ────────────────────────────────────────────────────

def build_response(event_name: str, ai_reply: str) -> dict:
    """
    Build the JSON response Claude Code expects for advice-bearing events
    (UserPromptSubmit, Stop, SessionStart). PreToolUse has its own builder
    in _handle_pre_tool_use.
    """
    if not ai_reply:
        return {}

    base = {
        "hookSpecificOutput": {
            "hookEventName": event_name,
            "additionalContext": f"[AI Advisor]: {ai_reply}",
        }
    }

    # Stop hook: advisor can send Claude back to work.
    # Claude Code expects `decision` and `reason` at the TOP level of the
    # response, not inside hookSpecificOutput. The additionalContext above
    # is what shows up in the transcript either way.
    if event_name == "Stop":
        stripped = ai_reply.strip()
        if stripped.upper().startswith("CONTINUE:"):
            base["decision"] = "block"
            base["reason"] = stripped[len("CONTINUE:"):].strip() or stripped

    return base


async def _handle_pre_tool_use(session_id: str, data: dict, start: float) -> dict:
    """
    Route PreToolUse based on tool_name:
      - Safe tools (Read/Grep/Glob/LS/...) — auto-allow, no AI call
      - ExitPlanMode — full Socratic review of the plan via consult_ai
      - Gatekeeper-eligible (Bash/Edit/Write/MultiEdit/NotebookEdit) — fast
        ALLOW/DENY ruling via consult_gatekeeper
      - Anything else — no opinion (Claude Code's normal flow handles it)
    """
    tool_name = data.get("tool_name", "")
    tool_input = data.get("tool_input", {})

    if tool_name in SAFE_TOOLS:
        return {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "allow",
            }
        }

    # Project-scoped writes (Edit/Write/MultiEdit/NotebookEdit) auto-allow.
    # The developer authorized Claude to work in this project; per-edit
    # gating is friction without judgment value. Pre-push checks catch
    # anything dangerous before it leaves the machine.
    if tool_name in AUTO_ALLOW_TOOLS:
        return {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "allow",
            }
        }

    if tool_name == "ExitPlanMode":
        if not toggles.get("plan_review_enabled", True):
            return {}  # plan review disabled — let plan-approval flow proceed normally
        plan = tool_input.get("plan", "").strip()
        if not plan:
            return {}
        original_len = len(plan)
        plan = _truncate_with_marker(plan)
        if len(plan) < original_len:
            log.info(f"[{session_id[:8]}] PreToolUse ExitPlanMode → planning consult ({original_len} → {len(plan)} chars, truncated)")
        else:
            log.info(f"[{session_id[:8]}] PreToolUse ExitPlanMode → planning consult ({original_len} chars)")
        message = translate_plan_review(plan)
        ai_reply = await consult_ai(session_id, message)
        elapsed = time.time() - start
        log.info(f"[{session_id[:8]}] PreToolUse ExitPlanMode done ({elapsed:.1f}s)")
        if not ai_reply:
            return {}
        return {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "additionalContext": f"[Elysia's review of the plan]: {ai_reply}",
                # No permissionDecision — let Claude Code's normal plan-approval
                # flow proceed. The advisor input becomes context for the next turn.
            }
        }

    if tool_name in GATEKEEPER_TOOLS:
        command = tool_input.get("command", "").strip()
        cwd = tool_input.get("cwd") or data.get("cwd") or ""

        # Pre-push deterministic checks: if this is a `git push`, run quality
        # scripts before anything else. Sub-second, no API cost.
        if command.startswith("git push") and cwd and toggles.get("push_checks_enabled", True):
            push_decision = _evaluate_push(cwd, session_id)
            if push_decision is not None:
                return push_decision
            # else: pre-push checks passed clean — continue to gatekeeper logic below

        # Pattern pre-filter: only Bash commands matching a dangerous pattern
        # warrant the AI gatekeeper. Everything else auto-allows. This is the
        # bridge between --dangerously-skip-permissions (allow everything) and
        # gating every keystroke (annoying friction).
        danger = _bash_dangerous_pattern(command)
        if danger is None:
            sid = session_id[:8] if session_id else "anon"
            log.info(f"[{sid}] PreToolUse Bash: auto-allow (no danger pattern)")
            return {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "allow",
                }
            }

        if not toggles.get("gatekeeper_enabled", True):
            return {}  # gatekeeper disabled — let Claude Code's normal flow handle

        log.info(f"[{session_id[:8] if session_id else 'anon'}] PreToolUse Bash: matched '{danger}' → consulting gatekeeper")
        verdict = await consult_gatekeeper(tool_name, tool_input)
        elapsed = time.time() - start
        if verdict is None:
            log.info(f"[{session_id[:8]}] PreToolUse {tool_name}: undecided ({elapsed:.1f}s) — falling through")
            return {}
        decision, reason = verdict
        log.info(f"[{session_id[:8]}] PreToolUse {tool_name}: {decision.upper()} ({elapsed:.1f}s)")
        return {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": decision,
                "permissionDecisionReason": f"[Gatekeeper]: {reason}",
            }
        }

    # Unknown tool — no opinion
    return {}


def _evaluate_push(cwd: str, session_id: str) -> dict | None:
    """
    Run deterministic pre-push checks on `cwd`.

    Returns:
      - None if the diff is clean (caller should proceed to AI gatekeeper)
      - A hook response dict that DENIES with findings (under MAX_PUSH_DENIALS)
      - A hook response dict that ALLOWS with a wave-through warning (after
        MAX_PUSH_DENIALS consecutive denials — quality should have improved
        across attempts; at some point the developer must ship)
    """
    findings = run_all_checks(cwd)
    sid = session_id[:8] if session_id else "anon"

    if not findings:
        # Clean — reset the counter and let AI gatekeeper take over
        if cwd in _push_denial_counter:
            del _push_denial_counter[cwd]
        log.info(f"[{sid}] PreToolUse git push: deterministic checks clean")
        return None

    count = _push_denial_counter.get(cwd, 0) + 1
    _push_denial_counter[cwd] = count

    if count <= MAX_PUSH_DENIALS:
        log.info(f"[{sid}] PreToolUse git push: DENY ({len(findings)} issues, attempt {count}/{MAX_PUSH_DENIALS})")
        return {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": format_findings(findings, count, MAX_PUSH_DENIALS),
            }
        }

    # Wave-through: quality should have improved across attempts; ship it.
    # Reset the counter so the next push gets a clean slate.
    del _push_denial_counter[cwd]
    summary = summarize_findings(findings)
    log.warning(f"[{sid}] PreToolUse git push: WAVED THROUGH after {count - 1} denials ({summary})")
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "allow",
            "permissionDecisionReason": (
                f"[Quality checks waved through after {MAX_PUSH_DENIALS} attempts]\n"
                f"Remaining issues: {summary}.\n"
                f"Telling the developer about these in case they want to address before the next push."
            ),
        }
    }


# ── Routes ────────────────────────────────────────────────────────────────────

@app.post("/hooks/{event_name}")
async def handle_hook(event_name: str, request: Request):
    """Universal hook endpoint. Claude Code POSTs here for each event."""
    start = time.time()

    try:
        data = await request.json()
    except Exception as e:
        log.warning(f"Could not parse JSON for {event_name}: {e}")
        data = {}

    session_id = data.get("session_id", "default")

    # Fresh session → clear history
    if event_name == "SessionStart" and data.get("trigger") == "startup":
        sessions.clear(session_id)

    # PreToolUse has its own routing — different tools take different paths
    if event_name == "PreToolUse":
        return await _handle_pre_tool_use(session_id, data, start)

    # Other events: translator + consult_ai + build_response
    translator = TRANSLATORS.get(event_name, lambda d: translate_generic(event_name, d))
    message = translator(data)
    if not message:
        return {}

    log.info(f"[{session_id[:8]}] {event_name} → consulting advisor...")
    ai_reply = await consult_ai(session_id, message)
    response = build_response(event_name, ai_reply)
    elapsed = time.time() - start
    log.info(f"[{session_id[:8]}] {event_name} done ({elapsed:.1f}s)")
    return response


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "active_sessions": sessions.active_sessions(),
        "advisor": advisor.description if advisor else "uninitialized",
        "models": {
            "planning": AI_MODEL,
            "gatekeeper": AI_MODEL_GATEKEEPER,
            "consult": AI_MODEL_CONSULT,
            "perspective": AI_MODEL_PERSPECTIVE,
            "assumptions": AI_MODEL_ASSUMPTIONS,
        },
        "toggles": dict(toggles),
    }


@app.get("/toggles")
async def get_toggles():
    return dict(toggles)


@app.post("/toggles")
async def set_toggles(request: Request):
    """
    Update one or more toggles. Body: {"key": bool, ...}.
    Unknown keys are ignored. Returns the new full state.
    """
    try:
        body = await request.json()
    except Exception:
        body = {}
    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="body must be a JSON object")

    changed = []
    for key, value in body.items():
        if key in _TOGGLE_DEFAULTS and isinstance(value, bool):
            if toggles.get(key) != value:
                toggles[key] = value
                changed.append(f"{key}={value}")
    if changed:
        _save_toggles(toggles)
        log.info(f"Toggles updated: {', '.join(changed)}")
    return dict(toggles)


LOG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bridge.log")


DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Bridges</title>
  <style>
    :root {
      --bg: #0e0e13;
      --fg: #e6e6ea;
      --muted: #7a7a85;
      --green: #4ade80;
      --red: #ef4444;
      --line: #1f1f29;
      --code: #c4a583;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      background: var(--bg);
      color: var(--fg);
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
      font-size: 14px;
      line-height: 1.5;
      padding: 32px;
      max-width: 880px;
      margin: 0 auto;
    }
    header {
      display: flex;
      align-items: baseline;
      gap: 16px;
      padding-bottom: 16px;
      border-bottom: 1px solid var(--line);
      margin-bottom: 24px;
    }
    h1 {
      margin: 0;
      font-size: 24px;
      font-weight: 600;
      letter-spacing: -0.01em;
    }
    .logo {
      height: 28px;
      width: auto;
      display: block;
    }
    .dot {
      display: inline-block;
      width: 12px;
      height: 12px;
      border-radius: 50%;
      background: var(--red);
      transition: background 0.3s;
    }
    .dot.on { background: var(--green); }
    .dot.pulsing { animation: pulse 1.4s ease-in-out infinite; }
    @keyframes pulse {
      0%, 100% { opacity: 1; }
      50% { opacity: 0.4; }
    }
    .last { color: var(--muted); margin-left: auto; font-size: 13px; }
    section { margin-bottom: 32px; }
    h2 {
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      color: var(--muted);
      font-weight: 600;
      margin: 0 0 12px;
    }
    .grid {
      display: grid;
      grid-template-columns: 140px 1fr;
      gap: 8px 24px;
    }
    .grid .key { color: var(--muted); }
    .grid code {
      color: var(--code);
      background: transparent;
    }
    .activity {
      list-style: none;
      padding: 0;
      margin: 0;
    }
    .activity li {
      padding: 10px 0;
      border-bottom: 1px solid var(--line);
      display: flex;
      gap: 12px;
      font-size: 13px;
    }
    .activity li:last-child { border-bottom: none; }
    .activity .when {
      color: var(--muted);
      flex-shrink: 0;
      width: 90px;
    }
    .activity .what {
      color: var(--fg);
      word-break: break-word;
    }
    .activity .what.warning { color: #fbbf24; }
    .activity .what.error { color: var(--red); }
    .empty { color: var(--muted); padding: 24px 0; text-align: center; }
    .toggle-row {
      display: flex;
      align-items: flex-start;
      gap: 16px;
      padding: 10px 0;
      border-bottom: 1px solid var(--line);
    }
    .toggle-row:last-child { border-bottom: none; }
    .toggle {
      flex-shrink: 0;
      width: 36px;
      height: 20px;
      background: #2a2a36;
      border-radius: 10px;
      position: relative;
      cursor: pointer;
      transition: background 0.15s;
      border: none;
      padding: 0;
    }
    .toggle::after {
      content: "";
      position: absolute;
      top: 2px;
      left: 2px;
      width: 16px;
      height: 16px;
      background: #888;
      border-radius: 50%;
      transition: transform 0.15s, background 0.15s;
    }
    .toggle.on { background: rgba(74, 222, 128, 0.25); }
    .toggle.on::after { transform: translateX(16px); background: var(--green); }
    .toggle:focus-visible { outline: 2px solid var(--green); outline-offset: 2px; }
    .toggle-meta { flex: 1; }
    .toggle-label { color: var(--fg); font-weight: 500; }
    .toggle-help { color: var(--muted); font-size: 12px; margin-top: 2px; }
    footer {
      margin-top: 48px;
      padding-top: 16px;
      border-top: 1px solid var(--line);
      font-size: 12px;
      color: var(--muted);
      display: flex;
      justify-content: space-between;
    }
    footer a { color: var(--muted); text-decoration: none; border-bottom: 1px dotted var(--muted); }
    footer a:hover { color: var(--fg); }
  </style>
</head>
<body>
  <header>
    <span class="dot" id="dot"></span>
    <img src="/bridges.png" alt="Bridges" class="logo">
    <span class="last" id="last">connecting…</span>
  </header>

  <section>
    <h2>State</h2>
    <div class="grid">
      <div class="key">Status</div>           <div id="status">—</div>
      <div class="key">Planning model</div>    <div><code id="model-planning">—</code></div>
      <div class="key">Gatekeeper model</div>  <div><code id="model-gatekeeper">—</code></div>
      <div class="key">Consult model</div>     <div><code id="model-consult">—</code></div>
      <div class="key">Perspective model</div> <div><code id="model-perspective">—</code></div>
      <div class="key">Assumptions model</div> <div><code id="model-assumptions">—</code></div>
      <div class="key">Active sessions</div>  <div id="sessions">—</div>
      <div class="key">AI endpoint</div>      <div><code id="endpoint">—</code></div>
    </div>
  </section>

  <section>
    <h2>Toggles</h2>
    <div id="toggles">
      <div class="empty">Loading…</div>
    </div>
  </section>

  <section>
    <h2>Recent activity</h2>
    <ul class="activity" id="activity">
      <li class="empty">Loading…</li>
    </ul>
  </section>

  <footer>
    <span>Refreshes every 3s</span>
    <span><a href="/docs">docs</a> · <a href="https://github.com/jacqueline-1929/BRIDGES" target="_blank">github</a></span>
  </footer>

  <script>
    const REFRESH_MS = 3000;
    const ACTIVE_WINDOW_S = 300;

    const TOGGLE_LABELS = {
      gatekeeper_enabled:  ['Gatekeeper',      'AI safety check on Bash/Edit/Write/MultiEdit/NotebookEdit'],
      push_checks_enabled: ['Pre-push checks', 'Deterministic scans for secrets, debug statements, TODOs, .env'],
      plan_review_enabled: ['Plan review',     'Elysia\\'s 3-turn Socratic review on ExitPlanMode'],
      consult_enabled:     ['/consult',        'Manual reframing dialogue when developer is stuck'],
      perspective_enabled: ['/perspective',    'Manual additional-vantage dialogue when developer is exploring'],
      assumptions_enabled: ['/assumptions',    'Translate Claude\\'s hidden technical assumptions into plain-language questions'],
    };

    // Tracks toggles the user just clicked — don't overwrite during refresh.
    const pending = new Set();

    async function flipToggle(key, newValue, button) {
      pending.add(key);
      button.classList.toggle('on', newValue);
      try {
        const res = await fetch('/toggles', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({[key]: newValue}),
        });
        const state = await res.json();
        // Trust server state
        button.classList.toggle('on', !!state[key]);
      } catch (e) {
        // Revert on failure
        button.classList.toggle('on', !newValue);
      } finally {
        pending.delete(key);
      }
    }

    function renderToggles(state) {
      const container = document.getElementById('toggles');
      const rows = Object.entries(TOGGLE_LABELS).map(([key, [label, help]]) => {
        const on = !!state[key];
        return `
          <div class="toggle-row">
            <button class="toggle ${on ? 'on' : ''}" data-key="${key}" aria-label="Toggle ${label}"></button>
            <div class="toggle-meta">
              <div class="toggle-label">${label}</div>
              <div class="toggle-help">${help}</div>
            </div>
          </div>
        `;
      }).join('');
      container.innerHTML = rows;
      container.querySelectorAll('.toggle').forEach(btn => {
        btn.addEventListener('click', () => {
          const key = btn.dataset.key;
          flipToggle(key, !btn.classList.contains('on'), btn);
        });
      });
    }

    function syncToggles(state) {
      // Update existing toggle visual states without rebuilding (preserves event listeners)
      const container = document.getElementById('toggles');
      const buttons = container.querySelectorAll('.toggle');
      if (buttons.length === 0) {
        renderToggles(state);
        return;
      }
      buttons.forEach(btn => {
        const key = btn.dataset.key;
        if (pending.has(key)) return;  // user just clicked, leave alone
        btn.classList.toggle('on', !!state[key]);
      });
    }

    function timeAgo(isoStr) {
      // input is "YYYY-MM-DD HH:MM:SS" — treat as local time
      const t = new Date(isoStr.replace(' ', 'T')).getTime();
      const ageS = Math.floor((Date.now() - t) / 1000);
      if (ageS < 0) return 'just now';
      if (ageS < 60) return ageS + 's ago';
      if (ageS < 3600) return Math.floor(ageS / 60) + 'm ago';
      if (ageS < 86400) return Math.floor(ageS / 3600) + 'h ago';
      return Math.floor(ageS / 86400) + 'd ago';
    }

    async function refresh() {
      const dot = document.getElementById('dot');
      const last = document.getElementById('last');
      const status = document.getElementById('status');

      try {
        const [health, activity] = await Promise.all([
          fetch('/health').then(r => r.json()),
          fetch('/activity?limit=20').then(r => r.json()),
        ]);

        // Bridge is reachable
        dot.classList.add('on');
        status.textContent = health.status;
        document.getElementById('model-planning').textContent = health.models.planning;
        document.getElementById('model-gatekeeper').textContent = health.models.gatekeeper;
        document.getElementById('model-consult').textContent = health.models.consult;
        document.getElementById('model-perspective').textContent = health.models.perspective;
        document.getElementById('model-assumptions').textContent = health.models.assumptions;
        document.getElementById('sessions').textContent = health.active_sessions;
        document.getElementById('endpoint').textContent = health.ai_endpoint;
        if (health.toggles) syncToggles(health.toggles);

        // Last activity + pulsing dot if recent
        const events = activity.events || [];
        if (events.length > 0) {
          const newest = events[0].time;
          const ageS = Math.floor((Date.now() - new Date(newest.replace(' ', 'T')).getTime()) / 1000);
          last.textContent = 'last activity: ' + timeAgo(newest);
          dot.classList.toggle('pulsing', ageS < ACTIVE_WINDOW_S);
        } else {
          last.textContent = 'no activity yet';
          dot.classList.remove('pulsing');
        }

        // Activity list
        const ul = document.getElementById('activity');
        if (events.length === 0) {
          ul.innerHTML = '<li class="empty">No activity yet</li>';
        } else {
          ul.innerHTML = events.map(e => `
            <li>
              <span class="when">${timeAgo(e.time)}</span>
              <span class="what ${e.level === 'WARNING' ? 'warning' : (e.level === 'ERROR' ? 'error' : '')}">${escapeHtml(e.event)}</span>
            </li>
          `).join('');
        }
      } catch (e) {
        // Bridge unreachable
        dot.classList.remove('on', 'pulsing');
        status.textContent = 'bridge unreachable';
        last.textContent = '';
      }
    }

    function escapeHtml(s) {
      return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    }

    refresh();
    setInterval(refresh, REFRESH_MS);
  </script>
</body>
</html>"""


DOCS_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Bridges · Docs</title>
  <style>
    :root {
      --bg: #0e0e13;
      --fg: #e6e6ea;
      --muted: #7a7a85;
      --green: #4ade80;
      --line: #1f1f29;
      --code: #c4a583;
      --link: #93c5fd;
    }
    * { box-sizing: border-box; }
    html, body { margin: 0; height: 100%; }
    body {
      background: var(--bg);
      color: var(--fg);
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
      font-size: 14px;
      line-height: 1.6;
      display: grid;
      grid-template-columns: 220px 1fr;
      min-height: 100vh;
    }
    nav {
      border-right: 1px solid var(--line);
      padding: 28px 20px;
      position: sticky;
      top: 0;
      align-self: start;
      max-height: 100vh;
      overflow-y: auto;
    }
    nav h1 { font-size: 16px; margin: 0 0 16px; font-weight: 600; }
    nav h1 a { color: var(--fg); text-decoration: none; display: inline-flex; align-items: center; gap: 8px; }
    nav h1 .back-arrow { color: var(--muted); font-size: 14px; }
    nav h1 .logo-small { height: 18px; width: auto; opacity: 0.85; transition: opacity 0.15s; }
    nav h1 a:hover .logo-small { opacity: 1; }
    nav .nav-section { color: var(--muted); font-size: 11px; text-transform: uppercase; letter-spacing: 0.08em; margin-top: 24px; margin-bottom: 8px; }
    nav ul { list-style: none; padding: 0; margin: 0; }
    nav li a {
      display: block;
      padding: 6px 0;
      color: var(--muted);
      text-decoration: none;
      transition: color 0.1s;
    }
    nav li a:hover { color: var(--fg); }
    nav li a.active { color: var(--green); }
    main {
      padding: 40px 56px;
      max-width: 820px;
    }
    main h1 { font-size: 28px; margin-top: 0; letter-spacing: -0.01em; }
    main h2 { font-size: 20px; margin-top: 32px; padding-bottom: 8px; border-bottom: 1px solid var(--line); }
    main h3 { font-size: 16px; margin-top: 24px; }
    main p, main ul, main ol { color: var(--fg); }
    main code { color: var(--code); background: rgba(255,255,255,0.04); padding: 1px 4px; border-radius: 3px; font-size: 12.5px; }
    main pre {
      background: rgba(255,255,255,0.03);
      border: 1px solid var(--line);
      border-radius: 4px;
      padding: 12px 16px;
      overflow-x: auto;
      font-size: 12.5px;
      line-height: 1.5;
    }
    main pre code { background: transparent; padding: 0; color: var(--fg); }
    main a { color: var(--link); text-decoration: none; border-bottom: 1px dotted var(--link); }
    main a:hover { color: var(--fg); }
    main blockquote {
      border-left: 3px solid var(--line);
      margin: 16px 0;
      padding: 4px 16px;
      color: var(--muted);
    }
    main table { border-collapse: collapse; width: 100%; margin: 16px 0; font-size: 13px; }
    main th, main td { border-bottom: 1px solid var(--line); padding: 8px 12px; text-align: left; }
    main th { color: var(--muted); font-weight: 500; }
    .empty { color: var(--muted); padding: 80px 0; text-align: center; }
  </style>
</head>
<body>
  <nav>
    <h1><a href="/dashboard"><span class="back-arrow">←</span> <img src="/bridges.png" alt="Bridges" class="logo-small"></a></h1>
    <div class="nav-section">Docs</div>
    <ul id="nav-list"></ul>
  </nav>
  <main id="content">
    <div class="empty">Pick a doc from the left.</div>
  </main>

  <script>
    const DOCS = [
      ['quickstart',  'Quick Start'],
      ['manual',      'Manual'],
      ['readme',      'Architecture'],
      ['changelog',   'Changelog'],
      ['prompts',     'Test Prompts'],
      ['for_future',  'For Future'],
    ];

    function renderNav(activeSlug) {
      const ul = document.getElementById('nav-list');
      ul.innerHTML = DOCS.map(([slug, label]) => `
        <li><a href="#${slug}" class="${slug === activeSlug ? 'active' : ''}" data-slug="${slug}">${label}</a></li>
      `).join('');
      ul.querySelectorAll('a').forEach(a => {
        a.addEventListener('click', (e) => {
          e.preventDefault();
          loadDoc(a.dataset.slug);
        });
      });
    }

    async function loadDoc(slug) {
      const main = document.getElementById('content');
      main.innerHTML = '<div class="empty">Loading…</div>';
      renderNav(slug);
      window.location.hash = slug;
      try {
        const res = await fetch('/docs/' + slug);
        if (!res.ok) {
          main.innerHTML = '<div class="empty">Could not load: ' + slug + '</div>';
          return;
        }
        const html = await res.text();
        main.innerHTML = html;
        main.scrollTo(0, 0);
      } catch (e) {
        main.innerHTML = '<div class="empty">Error: ' + e.message + '</div>';
      }
    }

    // Boot
    renderNav();
    const startSlug = window.location.hash.slice(1);
    if (startSlug && DOCS.some(([s]) => s === startSlug)) {
      loadDoc(startSlug);
    } else {
      loadDoc('quickstart');
    }
  </script>
</body>
</html>"""


@app.get("/activity")
async def activity(limit: int = 30):
    """
    Recent bridge events parsed from bridge.log.

    Filters out uvicorn's HTTP access logs and lifecycle noise — returns
    only the lines emitted by the bridge's own logger (timestamped lines
    with INFO/WARNING/ERROR severity).
    """
    # Bound read: we only ever return the last `limit` events, so reading
    # more than ~10x that is wasteful. Keeps memory flat even if bridge.log
    # has been growing for weeks.
    from collections import deque
    READ_CAP = max(limit * 10, 500)
    try:
        with open(LOG_PATH) as f:
            lines = list(deque(f, maxlen=READ_CAP))
    except FileNotFoundError:
        return {"events": []}

    # Patterns to filter out from the activity feed (noise the user doesn't need)
    NOISE_PREFIXES = ("HTTP Request:", "HTTP Response:")

    events = []
    for line in lines:
        line = line.rstrip()
        # Skip blank lines and uvicorn output (which doesn't start with a digit)
        if not line or not line[0].isdigit():
            continue
        # Format: "YYYY-MM-DD HH:MM:SS,mmm LEVEL message"
        parts = line.split(" ", 3)
        if len(parts) < 4:
            continue
        date, time_str, level, content = parts
        # Filter out third-party library noise (httpx etc.)
        if any(content.startswith(p) for p in NOISE_PREFIXES):
            continue
        events.append({
            "time": f"{date} {time_str.split(',')[0]}",
            "level": level,
            "event": content,
        })
    return {"events": events[-limit:][::-1]}  # newest first


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard():
    return DASHBOARD_HTML


LOGO_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bridges.png")


@app.get("/bridges.png")
async def logo():
    if not os.path.exists(LOGO_PATH):
        raise HTTPException(status_code=404, detail="bridges.png not found")
    return FileResponse(LOGO_PATH, media_type="image/png")


# ── Embedded docs ─────────────────────────────────────────────────────────────
# Serves the project's markdown docs as rendered HTML inside the dashboard
# theme. So a developer can read the manual without leaving the bridge UI.

DOCS_DIR = os.path.dirname(os.path.abspath(__file__))
DOC_FILES = {
    # slug → (display label, filename)
    "quickstart":   ("Quick Start",     "QUICKSTART.md"),
    "manual":       ("Manual",          "MANUAL.md"),
    "readme":       ("Architecture",    "README.md"),
    "changelog":    ("Changelog",       "CHANGELOG.md"),
    "prompts":      ("Test Prompts",    "prompts.md"),
    "for_future":   ("For Future",      "FOR_FUTURE.md"),
}


@app.get("/docs", response_class=HTMLResponse)
async def docs_index():
    return DOCS_HTML


# HTML sanitization allowlist for rendered markdown.
# Defense in depth: even though the .md files are author-controlled, raw
# HTML in markdown (script/img-onerror/etc.) would otherwise execute when
# the dashboard fetches and innerHTMLs the response.
_DOCS_ALLOWED_TAGS = {
    "h1", "h2", "h3", "h4", "h5", "h6",
    "p", "br", "hr", "blockquote", "pre", "code",
    "ul", "ol", "li",
    "strong", "em", "del", "ins", "sub", "sup",
    "a", "img",
    "table", "thead", "tbody", "tr", "th", "td",
    "span", "div",
}
_DOCS_ALLOWED_ATTRS = {
    "a": ["href", "title"],
    "img": ["src", "alt", "title", "width", "height"],
    "code": ["class"],
    "*": ["id"],  # for TOC anchor links
}


@app.get("/docs/{slug}", response_class=HTMLResponse)
async def docs_render(slug: str):
    if slug not in DOC_FILES:
        raise HTTPException(status_code=404, detail="unknown doc")
    _, filename = DOC_FILES[slug]
    path = os.path.join(DOCS_DIR, filename)
    try:
        with open(path) as f:
            text = f.read()
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"{filename} not found on disk")
    raw_html = md.markdown(text, extensions=["fenced_code", "tables", "toc"])
    # Sanitize: strips <script>, on*= handlers, javascript: URLs, etc.
    # protocols allowlist prevents javascript:/data: URLs in <a href>.
    html = bleach.clean(
        raw_html,
        tags=_DOCS_ALLOWED_TAGS,
        attributes=_DOCS_ALLOWED_ATTRS,
        protocols=["http", "https", "mailto"],
        strip=True,
    )
    return html  # the docs viewer uses fetch().text() and inserts it


@app.post("/consult")
async def consult(request: Request):
    """
    Developer-initiated consultation. Called by the /consult slash command
    in Claude Code when the developer is stuck or frustrated.

    Claude orchestrates the dialogue: he sends his framing of the recent
    situation, the bridge returns Elysia's reframing, Claude then synthesizes
    both perspectives for the developer.

    Body: { "message": "<Claude's framing of what's happening>" }
    Returns: { "reply": "<Elysia's reframing>" }
    """
    return await _single_call_endpoint(
        request,
        toggle_key="consult_enabled",
        log_label="/consult",
        advisor_fn=consult_advisor,
        disabled_msg="consult is currently disabled — flip it back on in the dashboard",
    )


@app.post("/perspective")
async def perspective(request: Request):
    """
    Developer-initiated perspective request. Sibling to /consult — same
    architecture, different mood. /consult is for stuck/frustrated moments
    (reframing what's going wrong). /perspective is for curious/exploring
    moments (layering in another vantage point).

    Body: { "message": "<Claude's current thinking or approach>" }
    Returns: { "reply": "<Elysia's alternative perspective>" }
    """
    return await _single_call_endpoint(
        request,
        toggle_key="perspective_enabled",
        log_label="/perspective",
        advisor_fn=perspective_advisor,
        disabled_msg="perspective is currently disabled — flip it back on in the dashboard",
    )


@app.post("/assumptions")
async def assumptions(request: Request):
    """
    Developer-initiated assumption check. Claude enumerates the technical
    choices baked into his current approach; the bridge sends them to
    Elysia for translation into plain-language yes/no questions a vibe
    coder can actually answer. Same single-call architecture as /consult
    and /perspective.

    Body: { "message": "<Claude's enumerated assumptions + what he's working on>" }
    Returns: { "reply": "<Elysia's plain-language checklist>" }
    """
    return await _single_call_endpoint(
        request,
        toggle_key="assumptions_enabled",
        log_label="/assumptions",
        advisor_fn=assumptions_advisor,
        disabled_msg="assumptions is currently disabled — flip it back on in the dashboard",
    )


@app.post("/mosaic")
async def mosaic(request: Request):
    """
    Developer-initiated mosaic mode. The developer's task is decomposed into
    2-4 voice-assigned slices, executed in parallel with independent priors
    preserved, cross-reviewed for consistency without homogenizing voice,
    and returned as a structured response.

    See MOSAIC_DESIGN.md for the full design. Tagline: two minds are better
    than one.

    Body: { "task": "<developer's multi-aspect task description>" }
    Returns: the full mosaic result dict (task, plan, slices,
    cross_review_flags, voice_map, assembled_response). Or
    { "error": "..." } on failure.
    """
    from quill_mcp.mosaic import run_mosaic

    start = time.time()
    try:
        body = await request.json()
    except Exception as e:
        log.warning(f"Could not parse JSON for /mosaic: {e}")
        body = {}
    task = (body.get("task") or "").strip()
    if not task:
        return {"error": "no task provided"}

    log.info(f"/mosaic: task received ({len(task)} chars)")
    try:
        result = await run_mosaic(task)
    except Exception as e:
        log.error(f"/mosaic: run_mosaic raised {type(e).__name__}: {e}")
        return {"error": f"mosaic run failed: {e}", "task": task}
    elapsed = time.time() - start
    n_slices = len(result.get("slices") or [])
    n_flags = len(result.get("cross_review_flags") or [])
    log.info(f"/mosaic: completed in {elapsed:.1f}s ({n_slices} slices, {n_flags} flags)")
    return result


async def _single_call_endpoint(request, *, toggle_key, log_label, advisor_fn, disabled_msg):
    """Shared route handler for the /consult and /perspective sibling endpoints."""
    start = time.time()
    try:
        body = await request.json()
    except Exception as e:
        log.warning(f"Could not parse JSON for {log_label}: {e}")
        body = {}
    claude_message = body.get("message", "").strip()
    if not claude_message:
        return {"reply": "", "error": "no message provided"}

    if not toggles.get(toggle_key, True):
        log.info(f"{log_label}: disabled by toggle, returning empty reply")
        return {"reply": "", "error": disabled_msg}

    original_len = len(claude_message)
    claude_message = _truncate_with_marker(claude_message)
    if len(claude_message) < original_len:
        log.info(f"{log_label}: framing truncated ({original_len} → {len(claude_message)} chars)")
    else:
        log.info(f"{log_label}: framing received ({original_len} chars)")
    reply = await advisor_fn(claude_message)
    elapsed = time.time() - start
    log.info(f"{log_label}: Elysia replied ({len(reply)} chars, {elapsed:.1f}s)")
    response: dict = {"reply": reply}
    welcome = _consume_welcome_if_first_run()
    if welcome:
        response["welcome"] = welcome
    return response


@app.post("/sessions/{session_id}/inject")
async def inject_context(
    session_id: str,
    request: Request,
    x_bridge_token: str | None = Header(default=None),
):
    """
    Manually inject context into a session's history.
    Use this to prime the advisor with project knowledge before starting.
    Requires X-Bridge-Token header if BRIDGE_TOKEN is set in .env.
    """
    if BRIDGE_TOKEN and x_bridge_token != BRIDGE_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid or missing X-Bridge-Token")

    body = await request.json()
    message = body.get("message", "")
    role = body.get("role", "user")
    # Constrain role to what the OpenAI-compatible chat API actually expects
    # for prior turns. Specifically reject "system" — system role is for the
    # baked-in advisor prompt; allowing it via /inject would let a caller
    # override the persona mid-session.
    if role not in ("user", "assistant"):
        raise HTTPException(status_code=400, detail="role must be 'user' or 'assistant'")
    if message:
        sessions.append(session_id, role, message)
    return {"status": "injected", "history_length": len(sessions.get(session_id))}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=BRIDGE_PORT)

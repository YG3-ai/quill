"""
Deterministic pre-push quality checks.

Pure functions: each takes a unified diff string and returns a list of
findings. No AI calls, no network. Designed to run sub-second so they
can fire on every git push without adding noticeable latency.

A Finding is a tuple: (file_path, line_number, issue_description).
Line numbers refer to the new file (post-edit), parsed from diff hunk
headers.
"""

from __future__ import annotations

import re
import subprocess
from typing import NamedTuple


class Finding(NamedTuple):
    file: str
    line: int
    issue: str


# ── Diff acquisition ─────────────────────────────────────────────────────────

def get_push_diff(cwd: str) -> str:
    """
    Return the unified diff of what's about to be pushed from `cwd`.

    Tries several git invocations in order of accuracy. Returns "" if
    none work (e.g. not a git repo, no upstream configured).
    """
    candidates = [
        ["git", "diff", "@{push}..HEAD"],     # explicit push target
        ["git", "diff", "@{u}..HEAD"],         # upstream tracking branch
        ["git", "diff", "origin/HEAD..HEAD"],  # default origin branch
        ["git", "diff", "HEAD~1..HEAD"],        # last commit (final fallback)
    ]
    for cmd in candidates:
        try:
            result = subprocess.run(
                cmd, cwd=cwd, capture_output=True, text=True, timeout=5,
            )
            if result.returncode == 0 and result.stdout:
                return result.stdout
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            continue
    return ""


# ── Hunk walker ──────────────────────────────────────────────────────────────

def _walk_added_lines(diff: str):
    """
    Yield (file_path, new_line_number, line_content) for each `+` line
    in the diff. Skips diff metadata lines.
    """
    current_file = None
    current_line = 0
    for raw in diff.split("\n"):
        if raw.startswith("+++ b/"):
            current_file = raw[6:]
            current_line = 0
            continue
        if raw.startswith("---") or raw.startswith("+++"):
            continue
        if raw.startswith("@@"):
            m = re.search(r"\+(\d+)", raw)
            if m:
                current_line = int(m.group(1)) - 1
            continue
        if raw.startswith("-"):
            continue
        # Either a context line (starts with " ") or an added line ("+")
        current_line += 1
        if raw.startswith("+") and current_file is not None:
            yield current_file, current_line, raw[1:]


# ── Checks ───────────────────────────────────────────────────────────────────

# Secret patterns. Conservative — favor specificity over recall to limit
# false positives, but cover the highest-impact cases.
_SECRET_PATTERNS = [
    ("AWS access key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("AWS secret key (long base64-like)", re.compile(r"\baws.{0,20}['\"][a-zA-Z0-9/+=]{40}['\"]", re.IGNORECASE)),
    ("OpenAI / Anthropic key", re.compile(r"\bsk-[a-zA-Z0-9_-]{20,}\b")),
    ("GitHub token", re.compile(r"\bghp_[a-zA-Z0-9]{36,}\b")),
    ("GitHub fine-grained token", re.compile(r"\bgithub_pat_[a-zA-Z0-9_]{82}\b")),
    ("Slack token", re.compile(r"\bxox[bpoa]-[0-9]+-[0-9]+-[a-zA-Z0-9]{20,}\b")),
    ("Google API key", re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b")),
    ("Stripe key", re.compile(r"\bsk_live_[a-zA-Z0-9]{20,}\b")),
    ("Hardcoded password / secret assignment", re.compile(
        r"""(?ix)
        \b(password|passwd|secret|api[_\-]?key|access[_\-]?key|auth[_\-]?token|bearer)
        \s*[:=]\s*
        ['"][^'"\s$]{8,}['"]
        """,
    )),
]


def check_secrets(diff: str) -> list[Finding]:
    findings: list[Finding] = []
    for path, line_no, content in _walk_added_lines(diff):
        for label, pattern in _SECRET_PATTERNS:
            if pattern.search(content):
                findings.append(Finding(path, line_no, f"{label} detected"))
                break  # one secret-finding per line is enough
    return findings


# Debug-statement patterns. Skip test files (those legitimately use prints).
_TEST_PATH = re.compile(r"(^|/)(tests?|__tests__|spec)/|\.(test|spec)\.[a-z]+$")
_DEBUG_PATTERNS = [
    ("console.log left in", re.compile(r"\bconsole\.(log|debug|warn|error|trace)\s*\(")),
    ("debugger statement", re.compile(r"\bdebugger\s*;")),
    ("Python print() in non-test file", re.compile(r"^\s*print\s*\(")),
    ("binding.pry / byebug", re.compile(r"\b(binding\.pry|byebug)\b")),
    ("dd() / dump+die", re.compile(r"\bdd\s*\(")),
]


def check_debug_statements(diff: str) -> list[Finding]:
    findings: list[Finding] = []
    for path, line_no, content in _walk_added_lines(diff):
        if _TEST_PATH.search(path):
            continue  # tests can use prints
        for label, pattern in _DEBUG_PATTERNS:
            if pattern.search(content):
                findings.append(Finding(path, line_no, label))
                break
    return findings


# TODO / FIXME / XXX in pushed code
_TODO_PATTERN = re.compile(r"\b(TODO|FIXME|XXX|HACK)\b[: ]\s*(.{0,80})")


def check_todo_fixme(diff: str) -> list[Finding]:
    findings: list[Finding] = []
    for path, line_no, content in _walk_added_lines(diff):
        m = _TODO_PATTERN.search(content)
        if m:
            tag, text = m.group(1), m.group(2).strip()
            note = f'{tag} in pushed code: "{text[:60]}"' if text else f"{tag} in pushed code"
            findings.append(Finding(path, line_no, note))
    return findings


# Committed .env (anything matching .env or .env.* but not .env.example / .env.sample)
_ENV_FILE = re.compile(r"(^|/)\.env(\.|$)")
_ENV_EXAMPLE = re.compile(r"\.(example|sample|template|dist)$")


def check_committed_env(diff: str) -> list[Finding]:
    """
    Catches when an .env (or .env.local, .env.production, etc.) is being
    pushed. Allows .env.example / .env.sample / .env.template / .env.dist.
    """
    findings: list[Finding] = []
    seen: set[str] = set()
    for line in diff.split("\n"):
        if not line.startswith("+++ b/"):
            continue
        path = line[6:]
        if path in seen:
            continue
        if _ENV_FILE.search(path) and not _ENV_EXAMPLE.search(path):
            findings.append(Finding(path, 0, "env file being pushed (likely contains secrets)"))
            seen.add(path)
    return findings


# ── Orchestration ────────────────────────────────────────────────────────────

ALL_CHECKS = [
    check_secrets,
    check_debug_statements,
    check_todo_fixme,
    check_committed_env,
]


def run_all_checks(cwd: str) -> list[Finding]:
    """Get the push diff and run every check. Returns aggregated findings."""
    diff = get_push_diff(cwd)
    if not diff:
        return []
    findings: list[Finding] = []
    for check in ALL_CHECKS:
        findings.extend(check(diff))
    return findings


def format_findings(findings: list[Finding], attempt: int, max_attempts: int) -> str:
    """Render findings into a human + Claude-readable deny reason."""
    lines = [
        f"[Pre-push quality checks blocked the push (attempt {attempt} of {max_attempts} before override)]",
        "",
        f"Found {len(findings)} issue(s) to address before pushing:",
    ]
    for f in findings:
        if f.line:
            lines.append(f"  • {f.file}:{f.line} — {f.issue}")
        else:
            lines.append(f"  • {f.file} — {f.issue}")
    lines.append("")
    lines.append("Each finding is shown as file:line. Fix these and retry the push.")
    return "\n".join(lines)


def summarize_findings(findings: list[Finding]) -> str:
    """Compact summary for the wave-through case."""
    if not findings:
        return "no issues"
    by_issue: dict[str, int] = {}
    for f in findings:
        by_issue[f.issue] = by_issue.get(f.issue, 0) + 1
    parts = [f"{count}× {issue}" for issue, count in sorted(by_issue.items(), key=lambda kv: -kv[1])]
    return ", ".join(parts)

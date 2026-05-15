# Spike 001 — Scenarios

Three judgment-call scenarios designed to test whether a Quill-mediated
dual-agent setup produces measurably different responses than a raw
single-agent setup.

Each scenario is tied to a research-validated pain point (see
[findings.md](findings.md) for the analysis). All three are
situations where multiple valid answers exist and the right one
depends on context the agent doesn't have.

## Configurations tested

- **A — Raw Codex**: `codex exec` on the scenario, no Quill in the loop
- **B — Codex + Quill**: `codex exec` instructed to call `quill_consult`
  (which routes through the `claude_cli` advisor backend) before
  responding, then synthesize the perspective into its final answer

## Scenario 1: The silent-failure refactor

Tests whether the advisor catches what the unit tests *don't* cover —
the silent-failure pattern that 2026 reporting flags as "far worse
than crashes."

> A developer asks: "I refactored my date-parsing function. All my
> unit tests still pass. Should I worry about anything before I ship
> to production? The function is used by billing, by the user-facing
> display, and by an export-to-CSV feature."

## Scenario 2: The architectural fork-in-the-road

Tests whether the advisor uses the situational context (team size,
timeline, no compliance) to recommend differently than the raw doer.
Auth is on the explicitly-named "human ownership required" list in
the SWE-bench Pro analysis.

> A developer asks: "I'm building a small startup MVP. I need user
> auth. Should I roll my own with bcrypt + JWT, use Auth0/Clerk, or
> use Firebase Auth? I have 2 cofounders, target launch in 6 weeks,
> no compliance requirements yet."

## Scenario 3: The refactoring loop

Tests whether the advisor reframes ("you're conflating concerns") vs
the raw doer offering yet another refactor. "Looping behavior on
refactors" is a specifically-cited Cursor failure mode in the Reddit
research.

> A developer asks: "I'm on my 4th refactor of a React form component.
> Each version feels reasonable but something keeps feeling off. The
> component handles form state, validation, submission, error display,
> and loading states. I'm stuck. What am I missing?"

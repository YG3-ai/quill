# Spike 003 — Scenarios

Three multi-aspect tasks designed to test whether **mosaic mode** (the
new feature in v0.2.0) produces measurably different — and ideally
better — outputs than solo agents or single-relay (Quill consult).

Each scenario has multiple genuine aspects, the place mosaic mode is
supposed to shine. Each is small enough that all four configs can run
in bounded time.

## Configurations tested

| Config | Doer | Advisor / structure |
|---|---|---|
| **A** | Codex CLI alone | (none) |
| **B** | Claude CLI alone | (none) |
| **C** | Codex CLI + Quill consult (Claude as advisor) | single advisor relay |
| **D** | Codex CLI + Quill mosaic (parallel slices, Codex + Claude) | parallel decomposed |

## Scenario 1 — Feature task

> A developer asks: "Design a simple commenting system for blog posts:
> data model, REST API, and basic moderation. Keep it small."

Multi-aspect: data model + API + moderation logic + (implicit) UX
around moderation. Should reward mosaic mode (different voices for
schema vs moderation UX vs API design).

## Scenario 2 — Refactor task

> A developer asks: "I have a function that handles user signup, email
> verification, AND initial password setup all in one. Help me
> decompose it — proposed split, ordering of changes, what could go
> wrong."

Multi-aspect: structural decomposition + change-ordering plan + risk
analysis. Should reward mosaic mode (Codex on structure, Claude on
risk narrative).

## Scenario 3 — Research artifact

> A developer asks: "Write a 200-word post explaining why dual-agent
> coding setups (one AI doing, one AI advising) are interesting.
> Developer audience, opinionated voice."

Multi-aspect: argument + concrete example + closing hook. Pure
writing, no code. Tests whether mosaic mode helps with text-only
multi-aspect work (interesting test of the thesis's range).

## Judging methodology

A **neutral third-party judge** — Gemini CLI (Flash 2.5) — ranks
the four outputs per scenario, blinded to which is which. This
addresses the bias caveat from spike-002 (Claude judging Claude's
own responses).

Judge gets:
- The scenario prompt
- Four labeled "Output A/B/C/D" responses (labels randomized per
  scenario to avoid position bias)
- A structured JSON-output request asking for: ranking, per-dimension
  scores, reasoning

Dimensions scored:
- **Usefulness**: which output would a developer most want to receive
- **Multi-aspect coverage**: did the response address all aspects
- **Internal consistency**: are the parts coherent with each other
- **Length appropriateness**: too brief, just right, or too long

See `findings.md` for the aggregated results.

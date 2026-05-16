# Spike 004 — Scenarios

Follow-up to spike-003, redesigned after the methodological critique
that spike-003's tasks were inherently single-agent-friendly (artifact
production, convergent-correctness) and its judge metrics rewarded
convergence over divergence — pre-deciding the verdict against mosaic
mode.

This spike tests mosaic mode on the kinds of tasks it's actually
designed for: **questions where productive contradiction between
perspectives is itself the value.** Decisions under genuine tension,
critique work where blind spots compound, situations where committing
quickly to one answer is the failure mode rather than the goal.

## What changed from spike-003

| Dimension | Spike-003 | Spike-004 |
|---|---|---|
| Task type | Artifact production (design a feature, write a post) | Decisions under tension, critique, pre-launch hardening |
| Judge metric | Usefulness / coverage / consistency / length | Perspective revealed / hidden assumptions / productive tension / synthesis quality / actionability |
| What "winning" measures | "polished single response" | "helped developer see more than one mind would have alone" |
| N | 3 scenarios × 4 configs = 12 | 4 scenarios × 4 configs = 16 |

The judge prompt is the load-bearing change. Same neutral judge (Gemini
Flash 2.5 via OAuth free tier), but asked the right question for the
mode being tested.

## Configurations tested (same as spike-003)

| Config | Doer | Advisor / structure |
|---|---|---|
| **A** | Codex CLI alone | (none) |
| **B** | Claude CLI alone | (none) |
| **C** | Codex CLI + Quill consult (Claude as advisor) | single advisor relay |
| **D** | Codex CLI + Quill mosaic (parallel slices, Codex + Claude) | parallel decomposed |

## Scenario 1 — UX critique / redesign

> A developer asks: "I have a settings page with 12 toggles. Users
> complain it's overwhelming. What should I do?"

A task where the "obvious" answer (group toggles, add a search bar) is
a structural fix that may miss the underlying question (does the user
actually need 12 toggles? what are they trying to *avoid*?). Two minds
should productively disagree here — Codex on structural cleanup, Claude
on whether the toggles should exist at all. The disagreement itself is
the design insight.

## Scenario 2 — Architecture under hidden tension

> A developer asks: "Should we adopt event sourcing for our user
> activity log? Team is 6 engineers, primarily backend, no event-
> sourcing experience. Activity volume is 100k events/day growing 20%
> q/q. No audit/compliance requirement today but possibly within 18
> months."

A decision with real tradeoffs across multiple frames: technical
(query patterns, storage, replay), team-capability (no prior
experience), organizational (lock-in vs flexibility), time-horizon
(audit might land). Single agents tend to recommend one direction;
mosaic should expose the tension between frames.

## Scenario 3 — Pre-launch hardening

> A developer asks: "We launch a new payments integration tomorrow at
> noon. What did we miss?"

A specifically variance-rewarding task. The dev presumably already
thought of the obvious things (testing, monitoring, rollback). Value
comes from the things ONE mind would have missed. The wider the
diversity of "what one might miss" perspectives, the better.

## Scenario 4 — Strategic refactor / rewrite decision

> A developer asks: "Should we rewrite our 50k-line Python monolith
> in Rust? Team is 4 engineers, 2 are Rust-curious but haven't shipped
> Rust at scale. Performance is occasionally an issue but not a daily
> pain. We have ~12 months of runway."

An inherently in-tension question: technical merits (Rust performance,
type safety) vs organizational consequences (team capability,
opportunity cost, hiring). Single agents tend to commit confidently
to one frame. The right answer is "depends on what you're optimizing
for and you should know which frame you're prioritizing before
deciding."

## Judging methodology

Same neutral third-party judge — Gemini CLI Flash 2.5 — but **the
judge prompt is rewritten to measure divergence-revealing dimensions
instead of convergence-quality dimensions.** See
[judge/run_judge.py](judge/run_judge.py) for the exact prompt.

Dimensions:
- **Perspective revealed**: Did this surface an angle the developer
  might not have considered alone?
- **Hidden assumption named**: Did it identify an unstated assumption
  baked into the framing that's worth questioning?
- **Productive tension exposed**: Did it identify a real tradeoff,
  rather than committing too quickly to one path?
- **Synthesis quality**: Did it help the developer move forward with
  the complexity, not just dump it as "here are two takes, good luck"?
- **Actionability**: Could the developer actually do something with
  this?

This re-centers the evaluation on the question mosaic mode is built
to answer: *does adding a second mind let the developer see more than
one alone would?*

If mosaic mode loses on these dimensions too, that's a real negative
finding — it means the dual-agent thesis doesn't hold even on its
home turf. If it wins decisively, spike-003's "bimodal" headline gets
refined to: "mosaic loses on tasks where single agents converge well;
wins on tasks where divergence is the value."

See [findings.md](findings.md) for the aggregated results.

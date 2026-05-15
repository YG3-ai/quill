# Spike 001 — Findings

**Date run:** 2026-05-15
**N:** 3 scenarios × 2 configurations = 6 CLI calls
**Doer:** Codex CLI (gpt-5-codex, v0.130)
**Advisor (Config B only):** Claude CLI (claude-sonnet-4-6, v2.1.141), via Quill MCP
**Status:** Preliminary. n=3 is a signal, not a finding.

For the scenario design + research grounding, see
[scenarios.md](scenarios.md). Raw outputs in
[raw_codex/](raw_codex/) and [codex_with_quill/](codex_with_quill/).

---

## Headline

**Quill's value-add depends on the type of question.** When the
question requires *reframing* (silent failure, refactor loop), the
advisor adds significant value by surfacing a sharper hierarchy or
a different angle. When the question is *clear-cut* with a defined
answer (well-scoped tech recommendation), the advisor adds little —
the doer already nails it.

This is consistent with Quill's positioning: it's a *thinking
partner* for situations that benefit from another mind, not a
quality multiplier for tasks the doer would handle well alone.

---

## Per-scenario analysis

### Scenario 1 — Silent-failure refactor

**Same question, both responses:** *Should I worry about a refactor
that all unit tests pass on, before shipping to billing/display/CSV?*

| Dimension | Config A (raw Codex) | Config B (Codex + Quill) |
|---|---|---|
| Length | ~370 words | ~270 words |
| Structure | 7-bucket flat checklist | Prioritized: highest-value check first, then specific risks, then practical pre-prod gates |
| Frame | "date parsing sits on a boundary between money, expectations, and integrations" | "this function has three different contracts" + "the caller that would notice a regression last" |
| Practical action | Mentions golden tests in passing | Recommends shadow-mode logging (parse with both, use new, log disagreements) |
| Silent-failure framing | Implicit (mentions golden tests, rollout safety) | **Explicit** ("CSV export problems can sit unnoticed until reporting or reconciliation time") |

**Verdict: Quill added meaningful value.** The "noticed last" frame
is the silent-failure pattern made operational — it's a sharper
prioritization rule than "check all consumers." Config B is
*shorter* but more *useful*. The shadow-mode suggestion is also
something Config A didn't surface.

### Scenario 2 — Auth choice (architectural fork)

**Same question, both responses:** *Roll my own vs Auth0/Clerk vs
Firebase Auth, given small team + 6-week MVP + no compliance?*

| Dimension | Config A (raw Codex) | Config B (Codex + Quill) |
|---|---|---|
| Length | ~290 words | ~310 words |
| Recommendation | Clerk (decisive) | Clerk (decisive) |
| Decision tree | Same 4 conditions | Same 4 conditions |
| Frame | Business context as primary lens | Stack fit as primary lens |
| Notable additions | "Keep your app's user model separate from the auth provider ID so you can migrate later if needed" | "JWTs introduce footguns around invalidation, expiry, storage, refresh flows" |

**Verdict: Quill added little to nothing.** Both reach the same
recommendation (Clerk) for the same reasons. The minor differences
are stylistic, not substantive. The question was well-scoped, the
context was complete, and Codex alone made the right call confidently.

This is itself a useful finding: **dual-agent doesn't help when
single-agent is already operating in its competence zone.**
Adding more thinking partners to a clear-cut question doesn't make
the answer better — it just adds latency and tokens.

### Scenario 3 — React form refactoring loop

**Same question, both responses:** *4th refactor of a React form,
each version feels reasonable but something keeps feeling off.*

| Dimension | Config A (raw Codex) | Config B (Codex + Quill) |
|---|---|---|
| Length | ~310 words | ~290 words |
| Reframe | "It is several responsibilities that happen to share a screen" | "It is probably an **ownership** problem, not a structure problem" |
| Decomposition axis | Layers (form model / validation / submission / view / glue) | Ownership (whose problem is each kind of failure?) |
| Code example | Custom hook + view component split | Form contract + onSubmit + parent responsibility |
| Closing principle | "single reason to change" | "the decision about responsibility" |

**Verdict: Quill added a sharper frame.** Both responses reframe
well — neither just offers refactor #5. But Config B's "ownership"
frame is more *forcing*: it asks the developer to make a decision
("when submit fails, whose problem is it?") rather than to apply a
pattern ("split into these layers"). Config A's reframe is good;
Config B's is sharper.

The question that crystallizes the difference: **"When submit
fails, whose problem is it?"** — that's a great Socratic question,
and it's what the advisor's perspective added.

---

## Pattern across the three scenarios

Quill's value-add tracked the *type* of question more than the
*difficulty*:

- **Reframing-required questions** (S1, S3): Quill helped. The
  advisor surfaced a different angle that the doer alone wouldn't
  have reached.
- **Well-scoped recommendation questions** (S2): Quill didn't help.
  The doer alone was already operating in a competence zone where
  more perspective adds noise, not signal.

This maps cleanly onto Quill's three-skill design:

- `consult` and `perspective` are for situations where reframing /
  another angle adds value
- `assumptions` is for translating jargon
- **None of the three are designed to improve well-scoped factual
  recommendations** — and the spike confirms that's correct
  positioning

A useful design rule emerging: **call Quill when you'd want to
pause and rethink the framing, not when you'd want a more confident
answer.**

---

## Caveats (don't overclaim)

- **n=3.** Three scenarios is a directional signal, not a finding.
  A real study needs at least 20-30 per category.
- **Single doer × single advisor.** Only tested Codex(doer) +
  Claude-via-Quill(advisor). The inverse (Claude doer + Codex
  advisor) might show different patterns — Claude tends to be more
  humanistic in its raw responses, so the marginal benefit of
  pairing it with a code-citing advisor like Codex could be larger.
- **No human eval.** Differences between A and B are *qualitatively*
  read by us (and one is presumably biased toward the product).
  A real study would need blinded human raters.
- **Scenarios designed by us.** We selected scenarios where Quill
  *should* show value. A representative sample of real developer
  questions might lean more toward S2-type clear-cut cases, where
  Quill helps less.
- **Codex set a high baseline.** Codex CLI alone is genuinely good
  at judgment-call situations. Quill's marginal value would likely
  be larger when paired with a weaker doer.

---

## What's next

Three concrete follow-ups:

1. **Spike 002: Inverse pair (Claude doer + Codex advisor).** Same
   3 scenarios, opposite agent assignment. Tests the symmetry
   hypothesis.
2. **Spike 003: Larger n on the reframing categories (consult +
   perspective).** Run 15–20 scenarios in each, see whether the
   "Quill helps when reframing is needed" pattern holds at scale.
3. **A first publishable post.** Even at n=3, the *headline* of
   this spike — "Quill helps where reframing is needed, doesn't
   help where the question is clear-cut" — is a useful, honest
   observation that reflects an actual product positioning. Worth
   a short blog post on yg3.ai (or wherever) once we have a couple
   more spikes to confirm the pattern.

For broader research direction, see [../../RESEARCH.md](../../RESEARCH.md).

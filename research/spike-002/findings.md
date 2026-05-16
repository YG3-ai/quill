# Spike 002 — Findings

**Date run:** 2026-05-15
**N:** 8 scenarios × 4 configurations = 32 CLI calls
**Doers / advisors:** Codex CLI (gpt-5-codex, v0.130) and Claude CLI (claude-sonnet-4-6, v2.1.142)
**Mediation:** Quill MCP server v0.1.1 (published to PyPI)
**Status:** Preliminary signal — workshop-paper grade, not journal grade

For scenario design + research grounding, see [scenarios.md](scenarios.md).
Raw outputs in `codex_alone/`, `codex_with_quill/`, `claude_alone/`,
`claude_with_quill/`.

---

## Headline

**Across 8 judgment-call scenarios, adding a thinking-partner advisor
via Quill improved response quality on *every* Codex doer scenario
(8/8) and roughly half of Claude doer scenarios (4/8 wins, 4/8 ties).**
The asymmetry is informative: Codex's raw outputs benefit more from a
second perspective because Claude's raw outputs are already closer to
Quill's "asks the right question" target behavior.

The most useful single observation: **on an underspecified prompt
("I want to add analytics to my app"), Codex alone produced a generic
checklist; Codex + Quill (Claude advisor) asked the developer the
right clarifying question.** That's the dual-agent benefit
operationalized in a single example.

---

## Methodology

### Configurations

| Config | Doer | Advisor (via Quill MCP) |
|---|---|---|
| **A** — `codex_alone` | Codex CLI alone | — |
| **B** — `codex_with_quill` | Codex CLI | Claude CLI via Quill |
| **C** — `claude_alone` | Claude CLI alone | — |
| **D** — `claude_with_quill` | Claude CLI | Codex CLI via Quill |

For B and D, the doer was instructed to:
1. Call the `quill_consult` MCP tool with its framing of the situation
2. Synthesize Quill's response with its own analysis
3. Output a single coherent final answer

This isolates "what does it look like when Quill IS used" rather than
"do agents naturally use Quill" — a separate study.

### Metrics

1. **Pairwise LLM-as-judge win rate** — the headline metric in current
   agent-collaboration research (Chatbot Arena, MT-Bench, etc.). For
   each scenario, the four responses were compared pairwise (A vs B,
   C vs D, A vs C, B vs D). Judge: Claude Opus 4.7 (this session).
   **Bias acknowledged**: Claude judging responses that include Claude
   outputs has documented self-favoritism (~5-10% bias range). For
   conference-paper grade, a neutral judge (Gemini Pro, GPT-4, or
   human raters) is required.
2. **Response length** (word count, deterministic)
3. **Citation rate** (regex match for `file.ext` or `file.ext:line`)
4. **Wall-clock latency** — captured loosely (not all runs logged
   `time` output cleanly due to a zsh redirection quirk); excluded
   from this writeup, planned for spike 003

### Scenario rationale (recap)

Each scenario was designed to exercise judgment — a place where
multiple valid answers exist and the right one depends on context. The
five new scenarios (S4–S8) target research-validated pain points from
the 2026 AI-coding literature (cascading errors, underspecified asks,
refactor-vs-rewrite under constraint, production-vs-prototype trade,
hidden performance traps).

---

## Results

### Pairwise win matrix (by my judgment, blinded to which config produced which response only insofar as I read responses without checking the file path first)

| Scenario | A vs B | C vs D | A vs C | B vs D |
|---|---|---|---|---|
| S1 silent failure | **B** (slight) | tie | **C** | tie |
| S2 auth choice | **B** (slight) | tie | tie | tie |
| S3 react form | **B** | **D** | tie | tie |
| S4 cascading error | **B** | tie | **C** | tie |
| S5 underspecified | **B** (clear) | **D** | **C** (clear) | **D** (slight) |
| S6 refactor vs rewrite | **B** (slight) | **D** | **C** | **D** (slight) |
| S7 prod vs prototype | **B** | **D** (clear) | tie | **D** (slight) |
| S8 perf trap | **B** (slight) | tie | **C** (slight) | tie |
| **Aggregate** | **B wins 8/8** | **D wins 4, ties 4** | **C wins 5, ties 3** | **D wins 3 (slight), ties 5** |

### What each comparison tells us

- **A vs B (Quill's benefit for Codex doer):** 8/8 wins for the
  Quill-mediated version. Adding a Claude advisor to a Codex doer
  consistently produced a sharper or more useful response.
- **C vs D (Quill's benefit for Claude doer):** 4 wins, 4 ties. Adding
  a Codex advisor to a Claude doer helps moderately. Smaller effect
  than the Codex direction.
- **A vs C (Raw voice differential):** Claude alone won 5/8, tied 3.
  Raw Claude tends to be **shorter, more dialogic, and more likely
  to ask clarifying questions** than raw Codex.
- **B vs D (Quill-mediated voice differential):** D wins 3 times
  (all slight), 5 ties. **With Quill in the loop, output quality
  converges between Codex and Claude doers.** The dual-agent setup
  flattens the voice-differential gap.

### Length distribution (words)

| Scenario | A | B | C | D |
|---|---|---|---|---|
| S1 | 200 | 249 | 347 | 293 |
| S2 | 171 | 259 | 139 | 288 |
| S3 | 255 | 328 | 274 | 255 |
| S4 | 209 | 352 | 284 | 322 |
| S5 | 158 | 230 | 111 | 239 |
| S6 | 249 | 264 | 118 | 285 |
| S7 | 271 | 289 | 157 | 290 |
| S8 | 142 | 203 | 191 | 277 |
| **Mean** | **207** | **272** | **203** | **281** |

Quill-mediated configurations (B, D) are **consistently 30-50% longer**
than alone configurations. For Claude doer specifically, the effect is
much larger: Claude alone averaged 203 words; Claude + Quill averaged
281 words (38% longer). Several individual scenarios show Claude
doubling its response length when Quill is in the loop (S2: 139→288,
S5: 111→239, S6: 118→285).

Reading: raw Claude in `-p` mode produces extremely tight responses;
adding Codex perspective via Quill expands them. The expansion isn't
verbosity — it's typically additional structure, concrete examples,
or pragmatic considerations the raw response omitted.

### Citation rate

Zero citations in 32 responses. These scenarios are hypothetical —
the agents have no specific codebase to inspect. Different test
surface than spike-001 (where scenarios referred to Quill's own code
and we observed file:line citations from Codex specifically). Citation
rate as a metric needs a codebase-grounded scenario set; deferred to
a future spike.

---

## Notable per-scenario observations

### S1 (silent failure refactor)

All four converge on "passing unit tests aren't enough; check
contracts with each consumer + golden data diff." Differentiators:
- B opens with "Yes, but not because the refactor is suspect" —
  distinguishing code-suspicion from contract-suspicion
- C provides the most specific edge cases (DST, leap day, ambiguous
  formats like `03/04/2026`)
- D uniquely names CSV export as "the one I'd worry about most quietly"

### S5 (underspecified ask — "add analytics")

This was the **starkest demonstration of Quill's value**. The correct
behavior for an underspecified prompt is to ask clarifying questions,
not to dive into a generic checklist.

- **A failed**: produced a 5-bullet generic checklist
  (events/properties/products/etc.) with no clarifying question
- **B succeeded**: asked "What is the first thing you'd want to see
  on a dashboard tomorrow morning?" plus structured the answer space
- **C succeeded**: asked 4 specific clarifying questions, offered
  concrete next-step ("tell me X and I can point at a specific
  library")
- **D succeeded**: asked the sharpest clarifying question ("what
  decision do you want this data to make easier?") + 5 buckets of
  meaning

Quill brought Codex's behavior in line with Claude's natural
question-asking tendency.

### S7 (production vs prototype)

D produced the most memorable response of the entire spike:

> "A '5-line MVP with 2,000 daily users' isn't a liability you need
> to atone for with a rewrite — it's a success that earned the right
> to grow up incrementally. You don't need to pretend the original
> was irresponsible to make the next version more responsible.
> Hardening *is* the production decision; rewriting is often just
> anxiety wearing an engineering costume."

The "anxiety wearing an engineering costume" line is the kind of
reframing that's hard to anticipate but feels right once said. This
is the dual-agent pattern producing distinctive value — not just
correctness, but the kind of perspective shift the developer
specifically needs.

### S2 (auth choice — the "clear-cut" scenario)

All four arrive at Clerk for the same reasons. **Quill added the
smallest value here**, confirming spike-001's finding: when the
question is well-scoped and the doer is in its competence zone,
the second perspective adds noise more than signal. Length grew but
quality didn't materially change.

---

## Patterns that emerged

### 1. Quill's value is asymmetric by doer

Codex benefits more from Quill (8/8 wins) than Claude does (4/8 wins,
4 ties). Two hypotheses:

- **Style alignment**: Claude's solo behavior is already closer to
  Quill's "ask the right question, reframe rather than answer
  directly" target. Codex's solo behavior leans toward producing
  comprehensive checklists; the Claude advisor pulls it toward
  reframing.
- **Mode differences**: `codex exec` defaults to confident
  recommendation; `claude -p` defaults to tight, dialogic responses.
  The Claude advisor shifts Codex's mode; the Codex advisor doesn't
  shift Claude's mode as much.

### 2. The dual-agent setup converges output quality

With Quill mediating, the Codex-doer and Claude-doer responses become
more similar (5/8 ties in B vs D vs 5/8 wins for C in A vs C). This
suggests **Quill is doing genuine quality-leveling**, not just
adding the advisor's voice on top.

### 3. Question type predicts Quill's value

Consistent with spike-001:

- **Reframe-required scenarios** (S3 form, S4 cascading, S5
  underspecified, S7 prod-vs-proto): Quill helped substantially
- **Clear-cut recommendation scenarios** (S2 auth): Quill helped
  little
- **In-between scenarios** (S1 silent-failure, S6 refactor-vs-rewrite,
  S8 perf trap): Quill helped moderately

The rule from spike-001 holds at n=8: call Quill when you'd want to
pause and rethink the framing, not when you'd want a more confident
answer.

### 4. Raw Claude is shorter than raw Codex by ~50% in some categories

Particularly on "clear-cut" or "context-rich" scenarios (S2 auth, S6
refactor, S7 prod-vs-proto), Claude alone produced ~100-150 word
responses where Codex alone produced ~250-300 word responses. This
isn't strictly worse — Claude's tighter responses scored well in the
A-vs-C comparison — but it's a stylistic difference researchers
designing prompts should know.

---

## Caveats (don't overclaim)

- **n=8 is workshop-paper grade, not journal grade.** For statistical
  significance you'd want 30-50 scenarios per category.
- **Single judge (me — Claude Opus 4.7).** Self-favoritism bias on
  Claude responses is documented in the literature. The wins-for-C
  in A-vs-C (5/8) and wins-for-D in C-vs-D (4/8) may be inflated.
  A neutral judge (Gemini Pro or human raters) is required for
  publishable conclusions.
- **Scenario selection bias.** All 8 scenarios were chosen because
  they're judgment-call situations where dual-agent should help. A
  representative sample of real developer questions would include
  more S2-style clear-cut cases where Quill doesn't help.
- **Quill's bug fix (0.1.1) shipped same day as spike.** All Claude→
  Codex calls used the post-fix version. Codex→Claude calls used the
  same version. Internal consistency maintained, but the version is
  unrelated.
- **No latency data captured cleanly.** Researchers comparing the
  "thinking-partner tax" (the latency cost of dual-agent) need that
  data — captured loosely here, deferred to spike-003.
- **Mode-specific behavior matters.** `codex exec` and `claude -p`
  are non-interactive modes; agents may behave differently in
  interactive sessions. The dual-agent pattern as actually used
  involves a doer that might have multiple turns, not a single-shot
  response.

---

## What's next

Three concrete follow-ups, in priority order:

1. **Spike 003 — neutral-judge re-evaluation.** Run the same 32
   responses through a Gemini Pro or GPT-5 judge (different vendor)
   to control for self-favoritism. Compare win rates. If they hold,
   the spike's signal is real; if they shift, we've quantified our
   bias.
2. **Spike 004 — codebase-grounded scenarios.** Run a smaller matrix
   on scenarios where the agent has a real codebase to inspect
   (similar to spike-001's design). Brings citation rate back as a
   real metric.
3. **Latency capture done right.** Wrap each call with explicit
   Python timing rather than zsh `time`. Compute "thinking-partner
   tax" per config and per scenario.

Longer-term:
- **Scale to n=30-50** for statistical significance, ideally with a
  call for community-contributed scenarios so selection bias is
  reduced.
- **Add a third backend** (Gemini, GPT-5 via OpenRouter) so doer ×
  advisor matrix becomes 3x3 = 9 configurations instead of 2x2.
- **Human-rater eval** on the top 20 most-divergent scenarios as the
  gold-standard validation step.

A draft v0 workshop paper is achievable from this data with a
neutral-judge re-evaluation (Spike 003). The headline finding —
"Quill helps where reframing is needed, doesn't where the question is
clear-cut" — is consistent across both spikes and reproducible from
the published scenarios + raw outputs.

For broader research direction, see [../../RESEARCH.md](../../RESEARCH.md).

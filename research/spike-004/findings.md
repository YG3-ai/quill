# Spike 004 — Findings

**Date run:** 2026-05-16
**N:** 4 scenarios × 4 configurations = 16 generated responses
**Generation backends:** Codex CLI (gpt-5-codex v0.130), Claude CLI (claude-sonnet-4-6 v2.1.141), Quill (v0.2.0 from PyPI, both consult + mosaic)
**Neutral judge:** Gemini CLI Flash 2.5 via Google OAuth free tier
**Methodology:** scenarios in [scenarios.md](scenarios.md); divergence-focused judge wrapper in [judge/run_judge.py](judge/run_judge.py); raw judgments in [judge/](judge/)
**Status:** Preliminary signal at n=4 with one neutral judge. But the pattern is clean enough — and the methodology change from spike-003 is principled enough — that the headline finding is publishable as v0.2 of the research direction.

---

## Headline finding

**Mosaic mode won all 4 scenarios.** Decisively. The neutral judge ranked it #1 in every scenario, with average scores of 9.4-9.6/10 across five divergence-revealing dimensions. The next-best config (Quill consult) averaged 6.2-7.6. The gap was not marginal.

| Config | S1 | S2 | S3 | S4 | Rank-sum |
|---|---|---|---|---|---|
| **quill_mosaic** | 1 (9.4) | 1 (9.4) | 1 (9.6) | 1 (9.6) | **4** ← perfect |
| **quill_consult** | 2 (6.2) | 2 (7.4) | 2 (7.4) | 2 (7.6) | 8 ← consistent runner-up |
| solo_claude | 3 (5.2) | 3 (7.2) | 4 (5.0) | 3 (6.6) | 13 |
| solo_codex | 4 (4.0) | 4 (6.4) | 3 (5.6) | 4 (6.4) | 15 |

This is the *opposite* result from spike-003 (where mosaic was bimodal — #1 on one scenario, last on two). Same product, same backends, same neutral judge — different tasks and different judge metric, opposite verdict.

The two spikes taken together tell the right story: **the value of mosaic mode is metric-shaped and task-shaped.** When the metric measures convergence quality (spike-003 dimensions: usefulness, length-appropriateness, internal consistency) on tasks where convergence is the goal (artifact production, "design this, polished"), mosaic loses because it's not built for that. When the metric measures divergence quality (this spike: perspective revealed, hidden assumptions named, productive tension exposed) on tasks where divergence is the value (decisions under tension, critique, pre-launch hardening), mosaic wins decisively because that's what it's structurally built for.

This is the more accurate version of what spike-003 should have measured.

---

## Per-dimension data

Mosaic dominated **every dimension** on **every scenario**. Not "mostly" — every cell. The biggest gap was on **productive_tension_exposed**, where mosaic averaged 9.75/10 and solo_codex averaged 4.5/10 — a 5-point gap on a 10-point scale.

| Dimension | mosaic avg | quill_consult | solo_claude | solo_codex |
|---|---|---|---|---|
| perspective_revealed | **10.0** | 7.0 | 6.0 | 5.5 |
| hidden_assumption_named | **9.25** | 7.75 | 7.0 | 4.75 |
| productive_tension_exposed | **9.75** | 6.5 | 5.5 | 4.5 |
| synthesis_quality | **9.25** | 6.75 | 5.25 | 6.0 |
| actionability | **9.25** | 7.75 | 6.25 | 7.25 |

Three things worth surfacing from this:

1. **Mosaic isn't just adding length** — it scored highest on synthesis_quality and actionability too, dimensions that penalize "dumping multiple takes." It's not winning by being verbose; it's winning by surfacing things the other configs missed and then making them actionable.
2. **Quill consult is a consistent #2** — modest but real improvement over either solo agent. The single-relay pattern (Codex doer + Claude advisor) adds value across the board on these task types.
3. **Codex alone underperformed Claude alone** — solo_codex was #4 on 3 of 4 scenarios. Codex's structural-correctness lean reads as "committing too quickly to one frame" on decision-support tasks where the question doesn't have one right answer. (Spike-003 was the opposite — solo_claude beat solo_codex on convergence tasks too, but by a much smaller margin.)

---

## Per-scenario detail

### S1 — UX critique ("12-toggle settings page")

**Winner: quill_mosaic** (avg 9.4 vs runner-up 6.2)

Judge said: *"intentionally creating and then analyzing friction between different professional perspectives (UX, Engineering, and Copy). Its 'Cross-review flags' section is a masterclass in surfacing productive tension, forcing the developer to realize that their choice of state model directly impacts the honesty of their UI copy and the effectiveness of their privacy disclosures."*

Note: cross-review flags — which spike-003 flagged as a *defect* ("internal contradictions documented in its own meta-commentary") — are now read by the same judge as a *feature* ("a masterclass in surfacing productive tension") on the right task type. Same artifact structure, different judgment depending on whether the task wants convergence or divergence. This is the spike-003 critique vindicated.

### S2 — Architecture under tension (event sourcing for activity log)

**Winner: quill_mosaic** (avg 9.4 vs runner-up 7.4)

Judge said: *"moves past the technical mechanics to address the team's 'muscle memory' and the subtle, quiet nature of failures in event-sourced systems."*

Notable side observation: this scenario's planner call **failed on first attempt** — Claude as planner refused to return JSON, instead responding with prose: *"this isn't really an implementation task — it's a decision-support task. That changes the slicing."* The retry produced a successful 3-slice plan (Codex on technical_tradeoffs, Claude on team_readiness, Claude on decision_framing). The planner correctly self-identified the task shape but the prompt didn't have a graceful way to express that. **Planner robustness is a real follow-up item** — see "what's next" below.

### S3 — Pre-launch hardening (payments integration)

**Winner: quill_mosaic** (avg 9.6 vs runner-up 7.4)

Judge said: *"the only response that actually investigates the reality of the developer's environment, discovering that the claimed 'payments integration' is missing from the visible codebase. By contrasting a high-quality operational checklist with a stark technical reality check, it provides a level of divergent perspective that the other models — which simply assume the developer's prompt is technically accurate — completely miss."*

This is **emergent agentic behavior we didn't design for**. Codex (one of mosaic's voices) used its CLI sandbox to inspect the actual codebase, found no payments integration, and surfaced this as a flag. None of the other configs did this — they all took the developer's stated context at face value. Mosaic's "different agents own different aspects" structure happened to give one of the agents the freedom (and the licence, via its assigned slice) to do reality-check work the others didn't think to do. Genuinely interesting — worth dwelling on for the research write-up.

### S4 — Strategic refactor decision (Python → Rust)

**Winner: quill_mosaic** (avg 9.6 vs runner-up 7.6)

Judge said: *"simulates an internal leadership debate, surfacing the 'hidden math' of developer throughput and the specific cultural risk of splitting a 4-person team into Rust-innovators and Python-janitors. By explicitly reconciling technical sizing with organizational retention risks, it helps the developer see the decision as a complex survival calculation rather than just a language choice."*

The "internal leadership debate" framing is the right read. On in-tension decision questions, mosaic mode produces something structurally closer to a written record of two senior engineers disagreeing productively than to a chatbot response. The judge picked up on that explicitly.

---

## What this means for the spike-003 design implications proposed


What still holds from spike-003:
- **Length-constraint detection** in the planner is still useful — if the user asks for "200 words," mosaic shouldn't override that regardless of mode fit
- **Trigger criteria** matter — the planner should recognize when a task is single-aspect or wants a polished artifact and decline to mosaic-decompose it (this is the actual underlying issue from spike-003's failures)

What I should walk back:
- The "synthesize for delivery" / "hide the seams" framing entirely. This contradicts the thesis. The seams are the feature on the right tasks.
- The "polished=True" parameter proposal. Wrong fix.

The critique that prompted spike-004 was correct, and the data here confirms it.

---

## Honest caveats

- **n=4** is still preliminary. Cleaner data than spike-003 but still a directional signal, not a statistical claim. Real publication would want 15-30 scenarios per condition with confidence intervals.
- **Scenarios designed by us AFTER spike-003's critique.** The user (correctly) pointed out spike-003's scenario selection was biased against mosaic mode; spike-004's scenarios were chosen specifically to give mosaic a fair test. There's selection bias the other direction now. The honest framing: spike-003 + spike-004 *together* sample both ends of the task distribution; neither alone is representative.
- **One judge.** Gemini Flash 2.5 again. Same caveat — different judges (human raters, ensemble) could shift the magnitudes if not the direction. The fact that the *same judge* produced opposite verdicts on the two spikes when asked different questions is itself informative — it's not Gemini that's biased toward mosaic, it's that mosaic mode is genuinely better at one kind of work than another and the judge prompt determines which kind we're measuring.
- **Judge prompt heavily emphasizes divergence dimensions.** This is deliberate — the spike's purpose was to measure mosaic on its home turf — but a paper-grade evaluation would need either (a) ensemble of judge prompts to weight different value-models or (b) human raters who don't see the rubric framing.
- **The planner failed on S2 first attempt** (returned prose instead of JSON). Retry succeeded. This is a real reliability issue worth fixing (see below) before mosaic mode sees real users on similar decision-support tasks.
- **S3's "Codex discovered the missing codebase" was emergent, not designed.** Some of mosaic's win there was an accident of having agentic-CLI advisors with sandbox read access. On scenarios where the doer can't read the codebase, that surprise factor goes away. Worth noting but not over-claiming.
- **Mosaic being built by us + Gemini judging mosaic favorably on divergence dimensions is methodologically cleaner than spike-002 but still not ideal.** A second neutral judge (different vendor, different rubric) would meaningfully strengthen these claims.

---

## Comparison to spike-003 (the matched pair)

| Dimension | Spike-003 | Spike-004 |
|---|---|---|
| Task type | Artifact production (design, write) | Decisions under tension (critique, hardening) |
| Judge metric | Convergence (usefulness, consistency, length) | Divergence (perspective, hidden assumptions, tension) |
| Mosaic ranking | 4-1-4 (bimodal — lost two, won one) | 1-1-1-1 (perfect sweep) |
| Mosaic vs runner-up gap | 4.0 points behind on S1, 6.0 points behind on S3, 0.2 ahead on S2 | 2-3 points ahead on every scenario |
| What it confirmed | Mosaic isn't a universal upgrade | Mosaic is a *specific* upgrade for the tasks it's built for |

Together: **mosaic mode is metric-AND-task-shaped value.** Not universal, not a defect — a tool with a sweet spot.

The honest research story isn't "mosaic mode is bimodal" (spike-003 alone) and isn't "mosaic mode wins" (spike-004 alone). It's: **the dual-agent setup produces value when the question rewards divergence; it produces noise when the question rewards convergence.** That's a more interesting, more testable, more design-relevant finding than either spike alone could have shown.

---

## What's next

In priority order:

1. **Fix planner robustness** (high priority, addresses real bug). On S2, Claude-as-planner returned prose instead of JSON when it judged the task as "not really an implementation task." We should either:
   - Make the planner prompt more insistent on JSON output regardless of task-shape opinions
   - OR add a "the planner refused" branch that gracefully falls back to single-slice mode + surfaces the refusal as information to the calling agent
   - The second option is more honest and probably better — mosaic mode declining to mosaic is itself a useful signal
2. **Add task-fit detection at the planner** (the actual underlying lesson from spike-003). Before producing slices, the planner should explicitly evaluate: is this task convergence-shaped (wants a polished artifact, explicit length constraints, single right answer) or divergence-shaped (decision under tension, critique, pre-launch hardening)? If convergence-shaped, return a single slice with a "consider not using mosaic" note. This addresses spike-003's failure mode at the right layer.
3. **Spike 005 — second neutral judge.** Re-run the same 16 outputs through a different judge (Gemini Pro, or DeepSeek, or human raters) to test whether spike-004's pattern holds when the judge model and rubric framing both change. Cheapest path to strengthening the finding.
4. **First publishable artifact.** Spike-003 + spike-004 together = a defensible blog post or workshop paper. Headline: *"When does dual-agent help? When the question wants divergence, not convergence."* The data + the methodology arc (we got it wrong, we fixed it, here's what shifted) is itself an interesting story about how easy it is to mis-measure tools whose value differs from the baseline you're comparing against.

For the broader research direction (RESEARCH.md), this spike is the cleanest signal we have to date that the dual-agent thesis holds *when properly tested*. Worth carrying forward to publication once spike-005 cross-checks.

---

## Files

- [scenarios.md](scenarios.md) — the 4 prompts + methodology + comparison to spike-003
- [solo_codex/](solo_codex/), [solo_claude/](solo_claude/), [quill_consult/](quill_consult/), [quill_mosaic/](quill_mosaic/) — the 16 raw outputs
- [judge/run_judge.py](judge/run_judge.py) — Gemini judge wrapper with divergence-focused dimensions
- [judge/](judge/) — raw Gemini outputs, parsed judgments, human-readable summaries
- This file

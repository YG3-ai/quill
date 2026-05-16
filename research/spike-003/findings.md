# Spike 003 — Findings

**Date run:** 2026-05-16
**N:** 3 scenarios × 4 configurations = 12 generated responses
**Generation backends:** Codex CLI (gpt-5-codex v0.130), Claude CLI (claude-sonnet-4-6 v2.1.141), Quill (v0.2.0 from PyPI, both consult + mosaic modes)
**Neutral judge:** Gemini CLI (Flash 2.5 via Google OAuth free tier)
**Methodology:** scenarios in [scenarios.md](scenarios.md); judge wrapper in [judge/run_judge.py](judge/run_judge.py); raw judgments in [judge/](judge/)
**Status:** Preliminary. n=3 with one neutral judge is a directional signal, not a statistical finding — but the patterns are clean enough to inform real design decisions about mosaic mode.

---

## Headline finding

**Mosaic mode is bimodal: it wins decisively where it fits, loses badly where it doesn't.** The neutral judge (Gemini) ranked it #1 on the genuinely multi-aspect refactor task (S2) — and dead last (#4 of 4) on both the constrained feature task (S1) and the length-constrained blog post (S3).

This isn't a defect — it confirms the design doc's warnings. Mosaic mode should be reserved for tasks where the multi-slice nature serves the work. It actively hurts the response when the user has asked for something compact or polished. The "ship it as a separate mode" call from the design conversation looks correct in retrospect: this is not the right default behavior.

A second finding worth surfacing: **solo Claude was the most consistent winner across the three scenarios** (#1 on S1 and S3, #2 on S2). The strong-frontier-model-alone baseline is genuinely hard to beat on judgment-call tasks, and the Quill-mediated configurations don't transform the response so much as add (or, in mosaic's case, sometimes subtract) value at the margins.

---

## Aggregate rankings

Lower rank-sum is better. n=3 scenarios.

| Config | S1 rank | S2 rank | S3 rank | Sum |
|---|---|---|---|---|
| **solo_claude** | 1 | 2 | 1 | **4** ← best overall |
| **quill_consult** | 2 | 4 | 2 | 8 |
| **solo_codex** | 3 | 3 | 3 | 9 |
| **quill_mosaic** | 4 | 1 | 4 | 9 ← most polarized |

Mosaic and solo_codex tie on rank-sum, but their distributions are very different: solo_codex is steadily middle-of-pack; mosaic is high-variance (one big win, two big losses).

---

## Per-scenario detail

### S1 — Commenting system ("Keep it small")

**Winner: solo_claude** (avg 10.0/10 across 4 dimensions)

| Config | Useful | Coverage | Consistent | Length | Avg |
|---|---|---|---|---|---|
| solo_claude | 10 | 10 | 10 | 10 | **10.0** |
| quill_consult | 9 | 9 | 10 | 9 | 9.2 |
| solo_codex | 8 | 9 | 10 | 9 | 9.0 |
| quill_mosaic | 6 | 10 | **5** | **3** | 6.0 |

**Judge's reasoning on mosaic:** *"While it covers deep UX nuances like the author's view of pending comments, it is excessively long, ignores the 'keep it small' constraint, and is riddled with internal contradictions documented in its own meta-commentary."*

Three things mosaic got wrong here, in the judge's view:
1. **Length explosion** — 2,485 words for a "keep it small" ask, vs ~250-370w from the other configs. Length score: 3/10.
2. **Internal contradictions** — Gemini flagged mosaic's own cross-review notes as evidence of incoherence (score 5/10) rather than reading them as helpful caveats. Worth dwelling on: the very feature we shipped as "preserved-distinctness is the value" reads, to a fresh evaluator, as "the response disagrees with itself."
3. **Coverage was perfect (10/10)** — mosaic *did* address every aspect — but the cost of getting there outweighed the benefit.

### S2 — Refactor task (signup + verification + password)

**Winner: quill_mosaic** (avg 9.25/10 — narrowly beating solo_claude's 9.5/10 on rank but losing on raw average; judge ranked it #1 on the structured ranking)

| Config | Useful | Coverage | Consistent | Length | Avg |
|---|---|---|---|---|---|
| quill_mosaic | **10** | **10** | 9 | 8 | 9.25 |
| solo_claude | 9 | 9 | 10 | 10 | 9.5 |
| solo_codex | 8 | 8 | 10 | 10 | 9.0 |
| quill_consult | 7 | 8 | 10 | 10 | 8.75 |

**Judge's reasoning on mosaic:** *"Provides an expert-level deep dive into database schema, migration strategy (expand-and-contract), and operational runbooks, going far beyond a simple code refactor."*

This is where mosaic earned its keep. The judge picked up on exactly the thing the dual-agent thesis predicts: mosaic *treated the task as bigger than the surface request* — including migration strategy, day-2 operational concerns, and on-call/support implications that solo agents missed.

Note the close raw average between mosaic and solo_claude (9.25 vs 9.5). Mosaic ranked #1 because the judge weighted its usefulness and coverage gains highly enough to outrank Claude despite Claude's perfect consistency/length scores. **The "two minds caught what one might miss" dynamic was real, measurable, and judge-recognizable.**

### S3 — Blog post (200-word, opinionated voice)

**Winner: solo_claude** (avg 10.0/10)

| Config | Useful | Coverage | Consistent | Length | Avg |
|---|---|---|---|---|---|
| solo_claude | 10 | 10 | 10 | 10 | **10.0** |
| quill_consult | 9 | 10 | 10 | 10 | 9.75 |
| solo_codex | 8 | 9 | 10 | 10 | 9.25 |
| quill_mosaic | **2** | 7 | **4** | **3** | 4.0 |

**Judge's reasoning on mosaic:** *"The response failed significantly on format by including extensive meta-commentary, internal editorial notes, and cross-review flags that belong in a draft, not a final post."*

The catastrophic failure here was format. The user asked for *a 200-word polished blog post*. Mosaic delivered 670 words plus a voice map plus a "Cross-review flags" section with 4 explicit critiques. The output looked like an editorial Slack thread, not a blog post. Usefulness: 2/10. Consistency: 4/10.

This is the most pointed lesson from the spike: **mosaic mode's "surface the seams" thesis fails when the user wanted a unified artifact.** Cross-review flags + voice headers are debugging affordances; they shouldn't appear in a deliverable the user is going to ship as-is.

---

## Cross-scenario patterns

### Quill consult is a modest improvement over solo

quill_consult ranked #2 on S1 and S3 (with avg scores within 0.5 of the winner) and #4 on S2 (avg 8.75, still respectable). Across scenarios it adds a small amount of perspective without distorting structure or length. This matches spike-002's finding that consult mode helps where reframing is needed, doesn't hurt where it isn't.

### Mosaic mode's failures cluster on length and format

Across all three scenarios, mosaic's **length_appropriateness** score was the worst dimension by a wide margin (3, 8, 3 vs 9-10 for all other configs on most scenarios). Multi-slice decomposition inherently produces longer output; the planner doesn't currently respect length constraints in the original prompt.

The **internal_consistency** dimension also penalized mosaic when the judge read cross-review flags as actual incoherence (S1 = 5/10; S3 = 4/10). For S2 where mosaic won, consistency was 9/10 — close to the others, because the slices on that task didn't produce flagged inconsistencies the judge read negatively.

### Where mosaic wins, it wins on coverage + usefulness

S2 is the proof point: 10/10 on both coverage and usefulness, beating every other config on both. The judge specifically credited mosaic with **going beyond the surface request** ("treats the request as a high-stakes architectural change rather than a simple refactor"). That's the dual-agent thesis in operation — and it's where the design's real value lives.

---

## What this implies for mosaic mode design

The data is honest, and it's pushing real design implications. Three changes worth considering, ranked by how strongly the data supports them:

### 1. Don't surface cross-review flags + voice headers when the artifact is the deliverable

**Strongest signal.** The S3 catastrophe (mosaic delivering a "blog post" with editorial sidebars) and S1's "internal contradictions" complaint both point at the same thing: **the structural metadata mosaic mode adds is great for developer-as-orchestrator and terrible for developer-as-recipient.**

Possible designs:
- Add a `polished=True` parameter to `quill_mosaic()` that returns *only* the assembled prose, no voice tags, no flag section. The voice map + flags become metadata returned in the JSON response but absent from `assembled_response`.
- Or split into two tools: `quill_mosaic_draft` (current behavior, full seams) vs `quill_mosaic_polished` (synthesis, hidden seams). This contradicts the original "mosaic > monolith" thesis but the data is asking for it.
- Or update the SKILL.md to instruct the calling agent to *summarize the mosaic for the user* rather than dumping the raw structured output. That's a presentation-layer fix; the underlying tool stays unchanged.

### 2. Make the planner respect explicit length/format constraints from the user's prompt

**Strong signal.** The "keep it small" constraint in S1 and the "200 words" constraint in S3 were both ignored by the planner, which produced 2-4 slices regardless. The planner prompt could be tightened to:
- Detect explicit length signals ("keep it small", "200 words", "briefly")
- Either reduce slice count + scope or decline to mosaic-mode at all on those tasks
- Return a "this looks single-aspect" signal that the calling agent can use to gracefully fall back to solo

### 3. The trigger criteria need work

**Medium signal.** S1's "design a simple commenting system" *seems* multi-aspect (data model + API + moderation) but the explicit "keep it small" makes it a single artifact ask. S3's blog post is multi-faceted in conceptual structure but should produce ONE thing. Mosaic mode currently has no way to read those signals.

Possible heuristics: if the user's prompt contains explicit length constraints OR phrasing that asks for a single coherent artifact ("write a post", "give me one paragraph"), suggest the calling agent reach for `quill_consult` or solo instead of `quill_mosaic`.

---

## Honest caveats

- **n=3.** Same caveat as spikes 001 and 002. Directional signal, not statistical claim. A real study needs at least 20-30 multi-aspect tasks per category.
- **One judge.** Gemini Flash 2.5 is one model. Different judges (a human panel, GPT-5, Claude Opus, ensemble) could produce different rankings. Worth replicating with a second neutral judge to confirm the bimodal pattern is real and not a Gemini-specific preference for compact responses.
- **Judge length bias is a known issue in LLM-as-judge literature.** Gemini may systematically penalize length even when the longer response is actually better. Mosaic's losses on S1 and S3 might partially reflect this bias rather than pure quality differences. The S2 win, where mosaic was the *most* useful despite being long, is therefore particularly strong signal — it overcame the length-bias headwind.
- **Scenarios designed by Quill's authors.** Selection bias possible. Scenarios that better fit mosaic mode (truly multi-aspect, no length constraint) might have shifted rankings.
- **Mosaic mode being shipped by us + judged by Gemini is methodologically cleaner than spike-002** (which was Claude judging Claude responses) but still not ideal. A real paper would want either human raters or an ensemble of neutral judges.
- **Generation flow caveat for Config D**: The Codex CLI's MCP tool-call timeout was shorter than mosaic mode's 90s wall-clock, so we invoked `run_mosaic()` directly via Python instead of through Codex's MCP. The output produced is identical (same code path that the bridge_server `/mosaic` endpoint uses), but this is an implementation detail worth fixing for real users — Codex needs a longer MCP timeout to use mosaic effectively. Filed as future work.

---

## Comparison to spike-002 (with one big asterisk)

Spike-002 found that "Quill helps where reframing is needed, doesn't where the question is clear-cut" — a self-judged finding with documented bias.

Spike-003 confirms part of that picture and complicates another part:
- **Confirmed**: Quill-mediated responses don't reliably beat solo agents. Solo Claude was the strongest config across all three scenarios in this spike.
- **Complicated**: Mosaic mode's win on S2 is a genuinely novel finding — *the dual-agent setup catches things one mind misses*. Spike-002 didn't have a config that produced this kind of "expanding the scope of the answer" effect.
- **New**: The length/format problems for mosaic mode are a new finding spike-002 couldn't have surfaced because it didn't have mosaic in the matrix.

The neutral judge unambiguously changes the methodology grade from "interesting blog post" to "publishable workshop-paper baseline." Same caveats about sample size, but the bias problem is materially reduced.

---

## What's next

Three concrete follow-ups in priority order:

1. **Build a "polished" mode for mosaic** — addresses the strongest signal in the data (S3 catastrophe, S1 readability issues). Should be a small change: add `polished=True` param to `quill_mosaic()` that strips voice headers and flag section from `assembled_response`.
2. **Tighten the planner prompt to detect length constraints** — second-strongest signal. The "keep it small" / "200 words" patterns are easy to detect with a small prompt addition.
3. **Spike 004 — second neutral judge** — re-run the same 12 outputs through a different judge (Gemini Pro, or an ensemble with a smaller open model via Ollama) to test whether the bimodal pattern holds across judges. This is the cheapest path to strengthening the finding.

For the broader research direction (RESEARCH.md), the most publishable artifact from this spike is the **"mosaic mode is bimodal" finding** with the design-implication framing. That's a real observation, neutrally judged, with clean per-dimension data to back it up. A 500-word blog post writes itself.

---

## Files

- [scenarios.md](scenarios.md) — the 3 prompts + methodology
- [solo_codex/](solo_codex/), [solo_claude/](solo_claude/), [quill_consult/](quill_consult/), [quill_mosaic/](quill_mosaic/) — the 12 raw outputs
- [judge/run_judge.py](judge/run_judge.py) — the Gemini judge wrapper
- [judge/](judge/) — raw Gemini outputs (`*_raw.txt`), parsed judgments (`*_judgment.json`), human-readable summaries (`*_summary.md`)
- This file

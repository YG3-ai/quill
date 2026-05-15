# Quill — Research Direction

Quill is both a free open-source product *and* a research project on
**coding agent collaboration**. The product gives developers a working
dual-agent setup; the research uses what Quill mediates to study how
agents differ when they think alongside each other.

This document is the scratch pad for that research direction. Concrete
data, papers, and HuggingFace artifacts will land here as they happen.

---

## The thesis

Coding agents are usually studied in isolation: how well does *one* model
solve a task. But in practice, developers increasingly use multiple
agents in dialogue — Claude Code reviewing what Codex wrote, Cursor
asking GPT-5 for a second opinion, etc. The interaction patterns
between agents are an under-explored axis of capability.

Quill happens to be a clean instrument for studying this: it sits
between a "doer" agent and an "advisor" agent, mediates the dialogue,
and observes the responses. Same framing through different advisor
backends produces measurably different responses. That observation is
the seed.

---

## Open research questions

### 1. The Voice Differential Study

**Question:** Given the same framing of a "stuck developer" situation,
how does the response style differ across coding-agent advisor backends?

**Empirical observation already on hand:** Codex CLI (gpt-5-codex)
tends to cite specific files and ground its perspective in the actual
code (`bridge_server.py:42` style citations). Claude Code CLI
(claude-sonnet-4-6) tends to reframe humanistically and reach for
metaphor ("rearranging furniture in a room whose purpose is unsettled").
Same prompt, same role, recognizably different voices.

**Study shape:** Curate ~50 stuck-developer scenarios, run them through
each advisor backend (Codex, Claude, Gemini, GPT-4, Llama via Ollama,
etc.), publish the corpus. Qualitative coding of response style + a
small human-rated quality eval.

**Status:** Pre-data. We have anecdotal evidence; need the actual corpus.

### 2. Does Dual-Agent Actually Help?

**Question:** Do developers using Quill (doer + advisor) reach better
outcomes than developers using a single agent?

**Study shape:** Construct scenarios that require nuanced judgment
(e.g., refactoring decisions where multiple plausible approaches exist).
Run each scenario through:
- Single agent (Claude Code or Codex alone)
- Dual agent via Quill (one as doer, one as advisor)

Measure: human-rated quality of final outcome, time-to-resolution,
developer-reported confidence in the result.

**Status:** Pre-design. Need to settle on outcome metric first.

### 3. The Advisor-Doer Pairing Matrix

**Question:** Which advisor-doer combinations work best for which
situation types? Is it always "use the smartest model as advisor," or
do certain combinations have non-obvious affinity?

**Study shape:** Cross-product of (doer model × advisor model ×
situation type). Score each cell. Look for cases where a "weaker"
advisor model produces better outcomes than a "stronger" one due to
better fit with the situation.

**Status:** Pre-design.

### 4. The Thinking-Partner Tax

**Question:** What's the latency/cost overhead of dual-agent vs single,
and when is it worth it?

**Study shape:** Wall-clock time + token cost for single-agent vs Quill-
mediated workflows on the same tasks. Cross-reference with quality data
from study 2 to identify the break-even point.

**Status:** Pre-design.

---

## Planned HuggingFace presence

When studies produce shippable artifacts:

- **Dataset**: `yugen/quill-coding-agent-dialogues` — anonymized
  framings + advisor responses across backends, for community study.
  Opt-in collection from real Quill usage (with consent), or
  synthetic-but-realistic curated scenarios.
- **Spaces**: an interactive demo where users fire framings at different
  doer × advisor combinations and see the responses side-by-side.
- **Model** (later): a small fine-tuned model trained as a "Quill
  advisor" — distilled from the best thinking-partner responses across
  backends. The thesis being tested: can a small model do well in the
  advisor role specifically?

---

## How Quill enables this

The advisor abstraction in `plugins/quill/server/advisors/` makes
swapping backends trivial — `ADVISOR_BACKEND=codex_cli` vs `=claude_cli`
vs `=api` is one env var. That's already a working A/B switchboard for
research.

The MCP server gives us a clean instrument for *observing* dialogue —
every framing in, every response out, all flows through one tracked
function (`_advisor.chat()`). With opt-in logging we can collect a
corpus over time without altering developer workflow.

The dual surface (Claude Code plugin + MCP) means we can study the same
question from two angles: how does dialogue look when Claude Code is the
doer (rich plugin context) vs when Codex CLI is the doer (cleaner MCP
context)?

---

## How to contribute

If you're a researcher interested in this space:

- Use Quill in your daily work and tell us what you observe (the voice
  differences, the cases where dual-agent helps or hurts, the awkward
  moments)
- Open an issue describing a study shape we should run
- Contribute to one of the open questions above — the corpus needs
  building, the eval needs designing
- Email research@yg3.ai (placeholder until set up)

If you're a developer just trying to ship code with Quill: that's
already contributing — Quill exists to be used, and observations from
real-world use are the most valuable data we can get.

---

## Status

This document is intentionally a scratch pad. Real publications, when
they happen, will land in `papers/` (TBD). Datasets will land on
HuggingFace under `yugen/`. This file evolves as the program does.

Last updated: 2026-05-15.

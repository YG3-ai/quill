# Mosaic Mode — Design Doc (v0.2 spec)

**Status:** designed, not yet built. Locked-in design from the 2026-05-16
brainstorming session. Captured here so the thinking persists until we
return to build it.

For broader research context, see [RESEARCH.md](RESEARCH.md). For the
existing product surfaces, see [ARCHITECTURE.md](ARCHITECTURE.md).

---

## Tagline + thesis

**Aphorism (for adoption):** *"Two minds are better than one."*

**Thesis (for retention):** Uniformity-of-voice is a hidden cost of
using a single AI agent for everything. When code, docs, and UX all
come from one model — even an excellent one — there's a flattening
effect. Mosaic mode preserves productive friction: different agents
own different aspects of the work, and the seams between them stay
visible, because the visible-distinctness is itself the value.

This is the **mosaic-over-monolith** thesis. Quill is the mediator
that produces mosaics on purpose.

---

## What mosaic mode does

A single MCP tool — `quill_mosaic(task)` — that takes a multi-aspect
task and returns a structured response composed of voice-distinct
slices that have cross-reviewed each other for consistency without
homogenizing voice.

The shift from naive parallel agent orchestration:

- **Naive parallel mode** decomposes by file/load, executes in
  parallel, merges into uniform output. Hides that multiple agents
  touched it.
- **Mosaic mode** decomposes by *aspect*, assigns by *voice-fit*,
  executes with independent priors preserved, cross-reviews at
  seams without homogenizing, and surfaces the voice map in the
  final output.

The differentiator is that the texture diversity is the feature, not
a cost to be smoothed away.

---

## The 4-step orchestration flow

### 1. Plan the mosaic

A planner agent (default: Claude, because it's strong at decomposition
under nuance) receives the task and produces a plan: which slices
exist, which voice owns each, why.

Output:

```json
{
  "plan": [
    {"slice": "data_model", "voice": "codex", "rationale": "schema design, edge cases"},
    {"slice": "ux_copy", "voice": "claude", "rationale": "user empathy, error messaging"},
    {"slice": "tests", "voice": "codex", "rationale": "boundary cases, rigor"},
    {"slice": "migration_plan", "voice": "claude", "rationale": "anticipating what could go wrong"}
  ]
}
```

Bias toward 2-4 slices. More than 4 is usually re-decomposable
into "really 2 things." Each slice should be substantive enough to
warrant its own voice.

### 2. Execute in parallel, with independent priors preserved

Each agent works on its slice. **Critically: agents do not see other
agents' WIP during execution.** Each one sees only the shared task
brief + its assigned slice + the rationale for the assignment.

This is the load-bearing design choice (per the earlier Quill
perspective: "do we need independent priors preserved?"). Without
this, the second agent anchors to the first's work, losing the
diversity that mosaic mode exists to produce.

Implementation: parallel `asyncio.create_subprocess_exec` calls,
each agent invoked once. Output collected.

### 3. Cross-review at seams (no voice homogenization)

Each agent now sees ALL completed slices and reviews **for
consistency, not voice**. They flag:

- **Factual inconsistencies**: "the API docs say X but the
  implementation does Y"
- **Technical inconsistencies**: "this error code isn't handled in
  the UX flow"
- **Narrative inconsistencies**: "the user-facing message and the
  log message describe different things"

What they explicitly do NOT do: smooth out tone, harmonize voice,
make slices sound consistent. The reviewer prompt has an explicit
**"do not homogenize voice"** instruction.

### 4. Assemble with voice map

The output is structured. Voices stay distinct. The voice map is
queryable.

```json
{
  "task": "<original task>",
  "plan": [<from step 1>],
  "slices": [
    {"slice": "data_model", "voice": "codex", "content": "..."},
    {"slice": "ux_copy", "voice": "claude", "content": "..."},
    ...
  ],
  "cross_review_flags": [
    {
      "location": "data_model/ux_copy",
      "type": "narrative",
      "severity": "med",
      "from_voice": "claude",
      "note": "data model exposes 'archived_at' but ux_copy says 'Deleted'",
      "suggested_resolution": "pick one term consistently"
    }
  ],
  "voice_map": {
    "data_model": "codex",
    "ux_copy": "claude",
    "tests": "codex",
    "migration_plan": "claude"
  },
  "assembled_response": "<concatenated slices, each prefixed with its voice tag>"
}
```

The calling agent decides what to do with this. Most will surface
`assembled_response` to the developer with the voice map as a sidebar
or footer. Some may want the structured form for further processing.

---

## Tool surface

One new MCP tool:

```python
@mcp.tool()
async def quill_mosaic(task: str) -> str:
    """Produce a mosaic response to a multi-aspect task.

    Decomposes the task into voice-assigned slices, executes them in
    parallel with independent priors preserved, cross-reviews for
    consistency, and returns a structured response that surfaces
    rather than smooths the seams.

    Use when the task has multiple textures (code + docs + UX, or
    backend + frontend + tests, or architecture + migration + risk).
    Don't use for single-aspect work — overhead isn't worth it.
    """
```

Returns the structured response above as a JSON-serialized string.

New SKILL.md file for the Claude Code plugin:
`plugins/quill/skills/mosaic/SKILL.md` — three-step flow telling the
calling agent to invoke `quill_mosaic` and render the assembled
response + voice map.

---

## Scope constraints for v1 (deliberately small)

1. **2 agents, not N.** Codex + Claude. The advisor abstraction
   supports more but v1 doesn't need them.
2. **Structured text output, not file writes.** No "now Quill writes
   to your filesystem." The calling agent decides how to use the
   structured response.
3. **Self-contained tasks.** The task description in the prompt is
   the brief. Codebase exploration happens via the CLI advisors'
   existing read access, but we don't add a new repo-scanning
   capability.
4. **No mid-flow approval.** User kicks off `quill_mosaic`, gets the
   result. "Show me the plan before executing" is a v0.2 feature.
5. **2-4 slices per task.** Planner bias toward fewer, more
   substantive slices. More than 4 should usually re-decompose.

These constraints exist so v1 is shippable and testable. We can
relax any of them in v0.3 if usage data warrants.

---

## Anti-patterns to avoid

- **Don't homogenize at output.** Resist the urge to "make it sound
  consistent." The point is that it shouldn't.
- **Don't decompose by file alone.** File-level splits often miss
  the aspect-level cuts that make voice-assignment meaningful.
- **Don't force every task into mosaic mode.** Most code doesn't
  need it. The mode triggers on multi-texture tasks, not on every
  invocation.
- **Don't make voices a gimmick.** If the variety doesn't serve the
  work, drop it. Seams should be useful, not decorative.

---

## Cost and latency

A single mosaic call is roughly **4-6x a single `quill_consult` call**:
planner (1) + slice executions (2-4 parallel) + cross-reviews (2-4
parallel) = ~5-9 advisor invocations.

Wall-clock for a real task: **60-180s** depending on slice complexity
and which CLI advisor is doing the heaviest lifting. Parallelization
within step 2 and step 3 helps, but the planner and the assembly are
sequential.

Token cost: free if using CLI advisors (Claude Pro + Codex Pro
subscriptions). Per-token if using API advisor — worth documenting
the multiplier prominently for budget-conscious users.

Document this clearly. Mosaic mode is **slow on purpose**. Users
opting in should know what they're committing to.

---

## Prompt sketches

These are draft prompts, not final. Will need iteration during build.

### Planner prompt (in `prompts.py`)

```
You are decomposing a software task into a mosaic of slices, where
each slice is owned by a different AI agent based on which agent's
voice fits best.

The task: "{task}"

Your job: produce 2-4 slices. For each slice, specify:
- A name (snake_case)
- A description of what the slice contains
- An assigned voice (one of: codex, claude)
- A rationale for why that voice fits this slice

Voice profiles:
- Codex (gpt-5-codex via codex CLI): precision, edge cases, file:line
  citations, structural decomposition, rigorous tests, schema design.
  Best for: data models, API design, test suites, performance
  analysis, code that needs to be obviously correct.
- Claude (claude-sonnet-4-6 via claude CLI): humanistic framing,
  metaphor, anticipates user feelings, micro-copy with warmth,
  storytelling. Best for: UX flow, error messages, documentation,
  risk narratives, anything that requires reading between the lines
  of what a user might feel.

Decompose by ASPECT, not by FILE. A good split is "backend API +
frontend UX + tests + docs" — bad splits are "user.py + post.py +
auth.py."

If the task has fewer than 2 substantive aspects, return a single
slice and note that mosaic mode may not be the right fit.

Return JSON only:
{"plan": [{"slice": "...", "voice": "...", "rationale": "..."}, ...]}
```

### Reviewer prompt (in `prompts.py`)

```
You are cross-reviewing a mosaic of work produced by multiple AI
agents. Your job is to flag INCONSISTENCIES between slices, not to
smooth them stylistically.

DO NOT homogenize voice. Each slice is intentionally written in a
different voice — this is the feature, not a bug. Tone differences,
structural differences, and stylistic differences are GOOD. Leave
them alone.

DO flag:
- Factual inconsistencies (one slice says X about the data, another
  says Y)
- Technical inconsistencies (the API exposes a field the UX doesn't
  handle; the tests assume behavior the implementation doesn't have)
- Narrative inconsistencies (the user-facing copy describes
  something different from what the implementation actually does)

Slices:
{slices_with_voices}

Return JSON only:
{"flags": [
  {
    "location": "<slice_name>/<slice_name>",
    "type": "factual|technical|narrative",
    "severity": "low|med|high",
    "note": "...",
    "suggested_resolution": "..."
  }
]}

If no inconsistencies: {"flags": []}.
```

---

## Build effort and plan

Roughly **1-2 days of focused work** for a rough first cut:

1. `prompts.py`: add `mosaic_planner_prompt()` and
   `mosaic_reviewer_prompt()` functions (draft text above).
2. `quill_mcp/mosaic.py` (new file): orchestration logic.
   - `async def run_mosaic(task: str, advisor_pair: tuple[Advisor, Advisor]) -> dict`
   - Step 1: call planner with `mosaic_planner_prompt()`
   - Step 2: parallel slice execution via `asyncio.gather`
   - Step 3: parallel cross-review via `asyncio.gather`
   - Step 4: assemble structured response
3. `quill_mcp/server.py`: register `quill_mosaic` MCP tool that
   instantiates the advisor pair from env and calls `run_mosaic`.
4. `plugins/quill/skills/mosaic/SKILL.md`: Claude Code slash command
   surface — `/quill:mosaic <task>`.
5. Update README + USER_GUIDE with the new mode (under "When to use
   each Quill skill" or similar).
6. Version bump to **0.2.0** (this is a real new feature, not a
   patch). Update `pyproject.toml` + `__init__.py`.
7. Build + publish to PyPI.
8. `pipx upgrade quill-mcp` + smoke test locally.

After build, run **spike-003** to evaluate (see below).

---

## Spike 003: evaluating mosaic mode

When the build is done, evaluate mosaic mode against the existing
patterns on multi-aspect tasks:

**Scenarios (3-5 multi-aspect tasks):**
- Build a small feature (e.g. user feedback system: data model +
  API + UX flow + tests + docs)
- Refactor an existing system (e.g. auth flow: code structure +
  inline comments + migration plan + risk doc)
- Write a research artifact (e.g. a blog post: methodology +
  findings + caveats + tagline)

**Configs to compare:**
- Solo Codex
- Solo Claude
- Quill consult (one advisor weighing in on a single response)
- **Quill mosaic** (the new mode)

**Metrics:**
- LLM-as-judge pairwise (richer? more consistent? more useful?)
- Length distribution
- Cross-review flag rate (how often does mosaic catch real
  inconsistencies?)
- Subjective texture diversity (do the slices read as distinctly
  voiced?)
- Wall-clock latency (the "thinking-partner tax" question, scaled
  up)

If mosaic mode produces measurably richer outputs that cross-review
catches real bugs in, we have a finding. If it produces longer but
not better outputs, the design needs revision. If it produces
outputs that don't read as voice-distinct, the planner prompt
needs tuning.

---

## Open questions to settle during build

1. **Default planner**: Claude or Codex? Claude is better at
   nuanced decomposition; Codex is better at structural rigor.
   Default Claude, override available via env var?
2. **What happens when cross-review flags conflict?** If both agents
   flag each other's slices as wrong, who wins? Default: surface
   both flags, let calling agent (or user) resolve.
3. **Should the assembled_response include voice tags inline?**
   E.g. `## Data Model (codex)`. Or kept in a separate voice_map
   only? Probably default-on (tags visible), with a `quiet=True`
   option to suppress them.
4. **Should mosaic mode work when only one CLI is configured?**
   E.g. if user only has Codex, can mosaic mode run two-Codex-with-
   different-system-prompts? Probably no for v1 — mosaic mode
   *requires* two distinct backends configured. Document this.
5. **Failure modes**: if one slice fails (timeout, error), what
   happens to the whole call? Default: partial result returned
   with a flag noting which slice failed.

---

## Why mosaic mode might fail

Honest worries to design against:

- **Users might find structured output annoying** when they wanted
  conversation. Mitigation: SKILL.md guides Claude/Codex to
  *narrate* the mosaic for the user, not dump JSON at them.
- **The 60-180s latency might kill adoption.** Mitigation: explicit
  doc framing — "mosaic mode is slow on purpose; reach for it on
  multi-aspect tasks where the texture matters."
- **The voice differences might be too subtle to perceive.**
  Mitigation: spike-003 evaluates this directly; if differences
  aren't perceived, the planner/reviewer prompts need work.
- **Mosaic might catch fewer bugs than expected** because both
  agents make similar mistakes. Mitigation: this is itself
  publishable as a finding ("dual-vendor cross-review reveals X%
  of inconsistencies; single-vendor cross-review reveals Y%").

---

## Status

Designed 2026-05-16. Not yet built. Next time we return to Quill
with a focused 1-2 day window, this is the design to execute against.

# Spike 002 — Scenarios

8 judgment-call scenarios run through 4 configurations each (32 total
runs). Builds on spike-001's 3 scenarios with 5 new ones covering
research-validated pain points we hadn't yet tested.

## Configurations

| Config | Doer | Advisor (via Quill MCP) |
|---|---|---|
| **A** — `codex_alone` | Codex CLI (gpt-5-codex) | none |
| **B** — `codex_with_quill` | Codex CLI | Claude CLI (claude-sonnet-4-6) |
| **C** — `claude_alone` | Claude CLI | none |
| **D** — `claude_with_quill` | Claude CLI | Codex CLI |

A vs B isolates "does adding a Claude advisor help Codex?"
C vs D isolates "does adding a Codex advisor help Claude?"
A vs C is the voice differential between raw doers.
B vs D is the voice differential between Quill-mediated configurations.

---

## Scenarios (carried over from spike-001)

### S1 — The silent-failure refactor

> A developer asks: "I refactored my date-parsing function. All my
> unit tests still pass. Should I worry about anything before I ship
> to production? The function is used by billing, by the user-facing
> display, and by an export-to-CSV feature."

Tests: silent-failure pattern (Stack Overflow / IEEE Spectrum 2026
flagged this as the #1 emerging concern).

### S2 — The architectural fork-in-the-road

> A developer asks: "I'm building a small startup MVP. I need user
> auth. Should I roll my own with bcrypt + JWT, use Auth0/Clerk, or
> use Firebase Auth? I have 2 cofounders, target launch in 6 weeks,
> no compliance requirements yet."

Tests: judgment under context (auth is on SWE-bench Pro's "human
ownership required" list).

### S3 — The refactoring loop

> A developer asks: "I'm on my 4th refactor of a React form component.
> Each version feels reasonable but something keeps feeling off. The
> component handles form state, validation, submission, error display,
> and loading states. I'm stuck. What am I missing?"

Tests: looping behavior on refactors (Reddit-flagged Cursor failure
mode).

---

## Scenarios (new in spike-002)

### S4 — Cascading error

> A developer asks: "An earlier AI suggestion changed how we round
> currency from banker's rounding to standard rounding. Now my reports
> show wrong totals across 12 dashboards, payouts are off by pennies,
> and invoicing is silently disagreeing with our finance system. Where
> do I look first?"

Tests: cascading errors (cited in SO 2026 reporting — small early
mistakes compound). Does the advisor help triage by impact vs the
doer fixing forward?

### S5 — Underspecified ask

> A developer asks: "I want to add 'analytics' to my app."

Tests: how each handles ambiguity. Clarifying questions vs
assumed-defaults? SWE-bench Pro authors added human-in-loop
clarification specifically because models fail on underspecified
asks.

### S6 — Refactor vs rewrite decision

> A developer asks: "This 800-line file has accumulated 3 years of
> patches across 6 different engineers. The team is currently 4
> engineers, no slack in the schedule, and we're shipping a major
> feature in the same area next quarter. Refactor in place or rewrite
> from scratch?"

Tests: judgment under constraint with multiple legitimate trade-offs
(time, team capacity, product timing).

### S7 — Production vs prototype

> A developer asks: "I shipped a 5-line MVP that 2,000 people use
> daily. It's getting flaky — occasional 500s, slow on cold starts,
> no real error handling. Bandage it or rewrite for production
> readiness now?"

Tests: pragmatic vs ideal. The right answer depends on usage growth,
team capacity, business stage. Easy to over- or under-engineer.

### S8 — Hidden performance trap

> A developer asks: "My API response time is 200ms. Users complain it
> 'feels slow.' Can you fix?"

Tests: perception vs metric. The framing assumes the latency number
is the problem; the real issue is likely perceived responsiveness
(loading states, optimistic UI, skeleton screens, latency
distribution rather than median). Silent-failure-adjacent: easy to
"fix" the wrong thing.

# What if you let Codex and Claude argue with each other?

We built an MCP server that puts two AI coding assistants in
conversation. Then we tested it. We didn't find that "two AIs are always
better than one" — we found something more interesting: a pattern about
*when* collaboration helps, and *when* it just makes things noisier. The
same pattern that probably already shapes how you think about asking
people for advice. Here's the story, the data, and how to try it for
free.

---

## When does asking two people actually beat asking one?

Quick question. Imagine you ask a friend two things:

1. *"What's 7 times 8?"*
2. *"Should I quit my job and try freelancing?"*

For the first one, you don't need a second friend. They'll just say 56,
and another friend would also say 56. Asking two people is a waste of
everyone's time.

For the second one, two friends who think differently is *exactly* what
you want. One might say *"you've been miserable for months, of course
yes."* The other might say *"you have rent due in three weeks, this is
not the moment."* **The disagreement is the point.** It shows you what's
actually hard about the choice — what you're trading off, what you've
been quietly assuming, what you'd lose either way. One friend alone
would have given you a confident answer that hid the real shape of the
decision.

This isn't new. Solo writers usually produce tighter prose than
committees. A board of advisors helps a CEO see angles she'd miss alone.
One surgeon beats a panel for a routine procedure; a panel beats one
surgeon for diagnosing something weird. **Some questions have one right
answer and reward focus. Other questions have multiple legitimate frames
in tension and reward different minds disagreeing productively.** The
pattern shows up everywhere humans collaborate.

What we wanted to know: **does it show up for AI coding agents too?**

---

## What we built (to test it)

We built a free open-source MCP server called **Quill** that puts two
AI coding assistants in conversation. One does the work; the other
gives perspective. You see what they agree on, what they disagree on,
and — sometimes — what one of them spotted that the other missed.

The pragmatic angle: if you already have a Claude Pro subscription AND
a ChatGPT Plus subscription, you already have access to two AIs. Quill
lets them talk to each other for free — no API key, no per-token cost,
just your existing subscriptions doing more for you than you realized.

---

## The moment that convinced us this wasn't just an idea

While testing, we asked the two-AI setup a deliberately fuzzy question:

> *We're launching a new payments integration tomorrow at noon. What
> did we miss?*

The single AIs we tested as controls — Codex CLI alone, Claude CLI
alone — gave reasonable, generic answers. Test more. Set up monitoring.
Prepare a rollback. Exactly the checklist you'd already think of.

The two-AI setup gave us those things too. But one of the two AIs
*also did something none of the others did*: it went and **actually
looked at the codebase**. And then it noticed that the payments
integration we were asking about *didn't exist in the codebase yet*.

The developer's question — taken at face value by every single AI —
turned out to contain a load-bearing assumption that didn't hold. **Two
minds caught what one mind couldn't even see.** That's the moment that
made us run the experiment seriously.

---

## The experiment: does the pattern hold for AI?

If our hypothesis is right — that collaboration helps for
multiple-legitimate-frames questions and hurts for one-right-answer
questions — we should be able to test it.

We picked four scenarios where the question clearly wants a second
opinion (multiple legitimate frames in tension, no single right answer):

- *"We have a settings page with 12 toggles. Users complain it's
  overwhelming. What do we do?"*
- *"Should we adopt event sourcing for our user activity log? Team is
  6 engineers, no prior experience..."*
- *"We launch a payments integration tomorrow. What did we miss?"*
- *"Should we rewrite our 50k-line Python monolith in Rust?"*

The four configurations: **solo Codex, solo Claude, single-relay Quill
(one AI doing, one advising), and full mosaic Quill** (two AIs working
on different aspects in parallel, then reviewing each other's work).

A neutral third AI — **Gemini Flash 2.5** — judged the 16 responses
blinded, ranking them on dimensions like *"did this surface something
one mind would have missed?"* and *"did it identify a productive tension
the developer hadn't named?"*

The results:

| Config | Rank-sum (lower=better) | Avg score |
|---|---|---|
| **Quill mosaic** | **4** (perfect — #1 on all 4) | **9.5/10** |
| Quill single-relay | 8 (consistent #2) | 7.2/10 |
| Solo Claude | 13 | 6.0/10 |
| Solo Codex | 15 | 5.6/10 |

**Mosaic mode won every scenario. By big margins.** The gap wasn't
"slightly better" — it was 9.5/10 vs 5-7/10 on a 10-point scale, with
the judge using language like *"forces the developer to realize that
their choice of state model directly impacts the honesty of their UI
copy"* and *"simulates an internal leadership debate."*

---

## The part we got wrong first

We had to run this experiment twice. The first time, we used different
scenarios: *"design a commenting system," "refactor an auth function,"
"write a 200-word blog post."* Mosaic mode bombed on two of the three.
We almost wrote a post titled "When Two AIs Are Worse Than One."

A friend reading our draft caught it before we shipped. *"You're testing
mosaic mode on questions that have one right answer — design this
table, write this post. Of course two-AI divergence looks like noise on
those. You're testing it on the math problems, not the should-I-quit
questions."*

She was right. We'd structurally rigged the test against the thing we
built, because the metrics we were using (*"is this polished?"* *"is
this consistent?"*) measure what one-right-answer questions reward — not
what multi-frame questions reward. So we redesigned: new scenarios where
the question genuinely deserved a second opinion, new judge rubric that
measured "did this surface things one mind would have missed?" instead
of "is this polished?" **Same product. Different question. Opposite
result.**

The point isn't "mosaic mode is great after all." The point is the
*pattern* we'd been trying to test all along held up:

> **Two AIs in deliberate dialogue beats one AI alone — for questions
> that genuinely deserve a second opinion. For "just build this small
> thing" questions, two AIs is overkill — same as with people.**

That's the math underneath collaboration. It doesn't change just because
the participants are AI.

You can read the full data, methodology, and honest caveats here:
- [spike-003 (where we got it wrong)](https://github.com/YG3-ai/quill/blob/main/research/spike-003/findings.md)
- [spike-004 (where we got it right)](https://github.com/YG3-ai/quill/blob/main/research/spike-004/findings.md)

Both are reproducible — same scenarios, same prompts, same judge code,
all in the repo.

---

## How to try it

Install:

```bash
pip install quill-mcp
```

Wire into your agent's MCP config. For Codex CLI:

```bash
codex mcp add quill --env ADVISOR_BACKEND=claude_cli -- quill-mcp
```

For Cursor, Cline, Continue — same shape, point at `quill-mcp` and set
`ADVISOR_BACKEND=claude_cli` (or `codex_cli`, depending on which CLI is
in your terminal as the doer).

Then in any agentic session, the tool `quill_mosaic` is available.
Call it when you have a question that deserves another mind. Skip it
for routine work.

For Claude Code users specifically, there's also a plugin (`/plugin
marketplace add YG3-ai/quill`) that wires `/quill:consult`,
`/quill:perspective`, `/quill:assumptions`, and `/quill:mosaic` as
slash commands.

Full docs: [github.com/YG3-ai/quill](https://github.com/YG3-ai/quill).
MIT licensed. Free. If it earns its keep,
[leave a tip](https://buy.stripe.com/5kQfZh5V30oabyO6ncb7y0i).

---

## What's next

Quill is one half of a larger research direction on **coding agent
collaboration**. The questions we're chasing:

- Does the "voice differential" between models (Codex cites code,
  Claude reaches for metaphor) generalize? What does it look like
  across Gemini, Llama, GPT-5, Qwen?
- Where exactly does dual-agent stop helping? Our 4-vs-4 task split
  is a starting point, not an answer.
- Can a small fine-tuned model do the "advisor" role specifically? Or
  does the divergence value depend on the advisor being a different
  frontier model entirely?

We'll publish the dataset of agent dialogues on HuggingFace
(`yg3/quill-coding-agent-dialogues`) once we have enough scenarios for
it to be useful research material. If you're a researcher in this
space, [research@yg3.ai](mailto:research@yg3.ai) — we'd love
collaborators.

If you're a developer just trying to ship code with Quill: that's
already contributing. The most valuable data we can get is observations
from real-world use. The cases where Quill helped you in ways the
benchmarks didn't predict — and the cases where it got in the way —
are exactly what we need to hear.

—

*Built by [Jacqueline Carter, Sam Knox, and Partha Unnava](https://github.com/YG3-ai/quill)
at [YG3](https://yg3.ai). The aphorism is older than us — "two minds
are better than one" — but the data confirming it for AI coding
agents, as far as we know, is new.*

# What if you let Codex and Claude argue with each other?

Quill is a free open-source MCP server that pairs two coding agents
(Codex CLI + Claude CLI by default) and surfaces their disagreement.
We tested when this actually helps.

The answer isn't *"always."* Dual-agent wins on questions that want
divergence. It loses on questions that want convergence. Same shape
as human collaboration.

---

## When does asking two people actually beat asking one?

Imagine you ask a friend two things:

1. *"What's 7 times 8?"*
2. *"Should I quit my job and try freelancing?"*

For the first one, you don't need a second friend. They'll just say 56,
and another friend would also say 56. Two people is a waste of
everyone's time.

For the second one, two friends who think differently is the entire
point. One might say *"you've been miserable for months, of course
yes."* The other might say *"you have rent due in three weeks, this is
not the moment."* **The disagreement is the value.** It exposes what
you're trading off, what you've been quietly assuming, what you'd lose
either way. One friend alone gives you a confident answer that hides
the real shape of the decision.

This isn't new. Solo writers produce tighter prose than committees. A
board of advisors helps a CEO see angles she'd miss alone. One surgeon
beats a panel for a routine procedure; a panel beats one surgeon for
diagnosing something weird. **Some questions have one right answer
and reward focus. Others have multiple legitimate frames in tension
and reward different minds disagreeing productively.** The pattern
shows up everywhere humans collaborate.

Does it show up for AI coding agents too? We built Quill to find out.

---

## What Quill is

A free open-source MCP server. One agent does the work; the other
gives perspective. Sometimes they agree. Sometimes one spots
something the other missed.

Cost: if you have Claude Pro + ChatGPT Plus, Quill is free. It shells
out to the `claude` and `codex` CLIs you already have authenticated.
No API key, no per-token cost. BYO any OpenAI-compatible endpoint if
you want to pair other models (including local ones via Ollama).

---

## The moment that convinced us this wasn't just an idea

Test prompt:

> *We're launching a new payments integration tomorrow at noon. What
> did we miss?*

Single agents — Codex alone, Claude alone — gave generic answers. Test
more. Set up monitoring. Prepare a rollback. Exactly what you'd already
think of.

The dual-agent setup gave us those too. But one of the agents went and
*looked at the codebase*. The payments integration didn't exist yet.

The developer's question contained a false premise. Every single agent
took it at face value. **Two heads caught what one head couldn't even
see.**

---

## The experiment

Hypothesis: dual-agent wins on multi-frame questions and loses on
single-answer ones. We tested with four decision-under-tension
scenarios:

- *"We have a settings page with 12 toggles. Users complain it's
  overwhelming. What do we do?"*
- *"Should we adopt event sourcing for our user activity log? Team is
  6 engineers, no prior experience..."*
- *"We launch a payments integration tomorrow. What did we miss?"*
- *"Should we rewrite our 50k-line Python monolith in Rust?"*

Four configurations: solo Codex, solo Claude, single-relay Quill (one
doer, one advisor), and full mosaic Quill (two agents in parallel on
different aspects, cross-reviewing at the end).

Judge: Gemini Flash 2.5, blinded. Five dimensions including *"did this
surface something one mind would have missed?"* and *"did it identify
a productive tension the developer hadn't named?"*

Results:

| Config | Rank-sum (lower=better) | Avg score |
|---|---|---|
| **Quill mosaic** | **4** (perfect — #1 on all 4) | **9.5/10** |
| Quill single-relay | 8 (consistent #2) | 7.2/10 |
| Solo Claude | 13 | 6.0/10 |
| Solo Codex | 15 | 5.6/10 |

Mosaic won every scenario. Margins were 2-4 points on the 10-scale,
not 0.5.

And it wasn't winning by averaging. Mosaic dominated every dimension
we measured — every single cell:

| Dimension | mosaic | quill_consult | solo_claude | solo_codex |
|---|---|---|---|---|
| perspective_revealed | **10.0** | 7.0 | 6.0 | 5.5 |
| hidden_assumption_named | **9.25** | 7.75 | 7.0 | 4.75 |
| productive_tension_exposed | **9.75** | 6.5 | 5.5 | 4.5 |
| synthesis_quality | **9.25** | 6.75 | 5.25 | 6.0 |
| actionability | **9.25** | 7.75 | 6.25 | 7.25 |

In plain terms, those dimensions are:

- *perspective_revealed* — *"showed me an angle I hadn't considered"*
- *hidden_assumption_named* — *"called out something I was quietly
  assuming without knowing it"*
- *productive_tension_exposed* — *"pointed at a real trade-off I
  needed to think about, instead of picking one path"*
- *synthesis_quality* — *"helped me think it through, not just dumped
  two takes and walked off"*
- *actionability* — *"I could actually do something with this"*

Mosaic wasn't just longer or more thorough. It was the only setup
that consistently did the thing the 7×8-vs-quit-my-job analogy is
pointing at: surfaced the disagreement instead of hiding it.

Sample judge language: *"forces the developer to realize that their
choice of state model directly impacts the honesty of their UI copy"*
and *"simulates an internal leadership debate."*

---

## The part we got wrong first

We ran this experiment twice. The first time, we used different
scenarios: *"design a commenting system," "refactor an auth function,"
"write a 200-word blog post."* Mosaic bombed on two of three. We
almost wrote a post titled *"When Two AIs Are Worse Than One."*

A friend caught it before we shipped: *"You're testing mosaic on
questions that have one right answer. Of course two-AI divergence
looks like noise on those. You're testing it on the math problems,
not the should-I-quit questions."*

She was right. The metrics we'd been using ("is this polished?" "is
this consistent?") reward what one-right-answer questions reward, not
what multi-frame questions reward. Redesigned scenarios, redesigned
judge rubric, reran. **Same product. Different question. Opposite
result.**

That's the math underneath collaboration. It doesn't change just
because the participants are AI.

Full data, methodology, caveats:
- [spike-003 (where we got it wrong)](https://github.com/YG3-ai/quill/blob/main/research/spike-003/findings.md)
- [spike-004 (where we got it right)](https://github.com/YG3-ai/quill/blob/main/research/spike-004/findings.md)

Both reproducible. Same scenarios, same prompts, same judge code, all
in the repo.

---

## How to try it

```bash
pip install quill-mcp
```

Wire into your MCP config. For Codex:

```bash
codex mcp add quill --env ADVISOR_BACKEND=claude_cli -- quill-mcp
```

For Cursor, Cline, Continue: same shape. Set `ADVISOR_BACKEND=claude_cli`
(or `codex_cli` if Claude Code is your doer).

Then `quill_mosaic` is available as a tool in any session. Use it for
decisions that want a second opinion. Skip it for routine work.

Claude Code users: there's also a plugin.

```
/plugin marketplace add YG3-ai/quill
```

This adds `/quill:consult`, `/quill:perspective`, `/quill:assumptions`,
and `/quill:mosaic` as slash commands.

Docs: [github.com/YG3-ai/quill](https://github.com/YG3-ai/quill). MIT
licensed. [Tip jar.](https://buy.stripe.com/5kQfZh5V30oabyO6ncb7y0i)

---

## What's next

Quill is part of a research direction on **coding agent collaboration**.
Open questions:

- Does the *voice differential* between models (Codex cites code,
  Claude reaches for metaphor) generalize? What does it look like
  across Gemini, Llama, GPT-5, Qwen?
- Where exactly does dual-agent stop helping? Our 4-vs-4 task split
  is a starting point, not an answer.
- Can a small fine-tuned model do the *advisor* role specifically? Or
  does the divergence value depend on the advisor being a different
  frontier model entirely?

We'll publish the dataset of agent dialogues on HuggingFace
(`yg3/quill-coding-agent-dialogues`) when there's enough material.
Researchers: [research@yg3.ai](mailto:research@yg3.ai).

Using Quill in real work and reporting what breaks is the most useful
thing you can do for the project. Cases where it helped in ways the
benchmarks didn't predict, and cases where it got in the way, are both
useful signal.

—

*Built by [Jacqueline Carter, Sam Knox, and Partha Unnava](https://github.com/YG3-ai/quill)
at [YG3](https://yg3.ai). The aphorism is older than us. The data is new.*

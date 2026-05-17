---
description: Produce a mosaic response to a multi-aspect task — two heads, not one. Decomposes the task into voice-assigned slices, runs them in parallel with independent priors preserved, cross-reviews without homogenizing voice. Invoke as /quill:mosaic <task description>.
---

The developer just typed `/quill:mosaic` — they want a *mosaic* response
to a multi-aspect task. Their task description: "$ARGUMENTS"

Mosaic mode is different from consult/perspective/assumptions. Those
relay one-shot perspectives. Mosaic produces structured *work*: 2-4
slices written by different agents in their native voices, cross-
reviewed for consistency, assembled with the seams visible on purpose.

The thesis: two heads are better than one. The mosaic IS the value —
preserved texture diversity is the feature, not a bug.

## When mosaic mode fits

- Multi-aspect tasks: code + docs + UX + tests, or backend + frontend +
  migration plan, or methodology + findings + caveats
- Work where you want *both* a precise voice AND a humanistic voice
  contributing, not one blending them
- Tasks where the seams between aspects matter (e.g. does the doc
  match the implementation? does the test cover the UX claim?)

## When to NOT reach for mosaic mode

- Single-aspect tasks (just code, just docs, just a yes/no question) —
  use the doer agent directly or `/quill:consult`
- Quick questions — mosaic mode takes 60-180 seconds
- Anything where uniform voice is actually what the developer wants

If you suspect the developer's task is single-aspect, tell them so and
suggest they re-issue without `/quill:mosaic` (or use `/quill:consult`
for a thinking-partner reframe).

## Step 1 — Pass the task to mosaic mode

Use this command, substituting the developer's task description for
`<DEVELOPER TASK>`:

```bash
python3 -c "
import json, urllib.request, sys
msg = sys.argv[1]
payload = json.dumps({'task': msg}).encode()
req = urllib.request.Request('http://127.0.0.1:9000/mosaic', data=payload, headers={'Content-Type': 'application/json'})
try:
    with urllib.request.urlopen(req, timeout=240) as r:
        data = json.loads(r.read())
    if data.get('error'):
        print(f'MOSAIC ERROR: {data[\"error\"]}')
    else:
        print(data.get('assembled_response', '(no response)'))
        print()
        print('---VOICE MAP---')
        for slc, voice in (data.get('voice_map') or {}).items():
            print(f'  {slc}: {voice}')
        flags = data.get('cross_review_flags') or []
        if flags:
            print()
            print(f'---{len(flags)} CROSS-REVIEW FLAG(S)---')
except Exception as e:
    print(f'BRIDGE UNAVAILABLE: {e}')
" "<DEVELOPER TASK>"
```

The 240-second timeout is intentional — mosaic mode involves a planner
call + 2-4 parallel slice executions + 2 parallel cross-reviews, all
of which involve CLI subprocesses. If it hangs longer than that,
something is genuinely wrong.

If you see `BRIDGE UNAVAILABLE`, the local advisor server isn't
running. Tell the developer to check the plugin's status (it should
auto-start when the plugin is enabled — see the plugin README for the
recovery command) and stop here.

If you see `MOSAIC ERROR`, the planner or backend failed. Surface the
error message to the developer and stop here — don't fabricate a
fallback response.

## Step 2 — Show the developer the mosaic

Compose your final reply in this shape:

1. **One short framing sentence** from you about what mosaic produced
   (e.g. *"Quill split this into 4 slices — Codex wrote the data model
   and tests, Claude wrote the UX flow and migration plan."*).
2. **The assembled_response verbatim** — this is the substantive work,
   already formatted with voice headers per slice. Don't paraphrase
   or summarize it. The voices are intentional.
3. **The voice map** — render it as a small footer table or list,
   showing which slice each agent owned. This is part of mosaic mode's
   value (the developer can see the texture).
4. **Cross-review flags, if any** — if `cross_review_flags` is
   non-empty, surface them as a "things to double-check" section.
   These are inconsistencies the cross-reviewing agent flagged. Don't
   try to resolve them yourself — name them and let the developer
   decide.

Don't add closing commentary. The mosaic is the response.

## What mosaic mode is NOT

- It does **not** write files. The output is text the developer reads.
  If they want files written, they take the mosaic output and tell
  you (the doer) to implement it.
- It does **not** synthesize one unified voice. That's deliberately
  avoided. If the developer wanted homogenized output, they wouldn't
  have asked for mosaic mode.
- It does **not** ask clarifying questions of the developer. The
  planner takes their task as-is. If the task is ambiguous, the
  planner's decomposition will reflect that — the developer can
  re-issue with more detail if the slices feel wrong.

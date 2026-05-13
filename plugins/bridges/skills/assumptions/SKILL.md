---
description: Surface and translate the technical assumptions Claude is silently making, so a non-technical developer can correct them in plain language. Invoke as /bridges:assumptions [note].
---

The developer just typed `/bridges:assumptions` — they want to check the
technical choices you've been making silently. Their note: "$ARGUMENTS"

This isn't about defending what you've done. It's about making invisible
choices visible so the developer can actually have an opinion. They are
smart but don't necessarily know the vocabulary; your job is to surface
your assumptions accurately, then let the advisor translate them into
questions they can answer.

## Step 1 — Enumerate your assumptions

Look at what you've been working on (recent code, current plan, the
direction of recent exchanges). List the technical assumptions you're
currently making that the developer hasn't explicitly approved. Be
honest and specific. Examples of what counts:

- **Hosting / scale**: single instance vs distributed, expected concurrent users, geographic distribution
- **Data persistence**: in-memory vs disk vs database, schema flexibility, backup posture
- **Concurrency**: sync vs async, locking strategy, ordering guarantees
- **Failure handling**: retry policy, fallback behavior, what happens on partial failure
- **Security**: trust boundaries, auth approach, secret handling, input validation
- **Performance**: caching, indexing, query patterns, payload size
- **Data freshness**: eventual vs strong consistency, polling vs push
- **Future-proofing**: extensibility, API stability, migration story
- **Observability**: logging, error reporting, what's monitored

Don't list theoretical assumptions. List the ones actually baked into
what you're currently building or planning. Be concrete: "I'm assuming
a single-process server with in-memory state" — not "I might assume
something about hosting."

**Length limit:** keep your enumeration under **600 characters**. The
bridge caps inputs at 1000 chars and will truncate longer messages.
Pick the load-bearing assumptions; skip the obvious ones.

## Step 2 — Send to the advisor for translation

Use this command, substituting your enumeration from Step 1 for `<YOUR ASSUMPTIONS>`:

```bash
python3 -c "
import json, urllib.request, sys
msg = sys.argv[1]
payload = json.dumps({'message': msg}).encode()
req = urllib.request.Request('http://127.0.0.1:9000/assumptions', data=payload, headers={'Content-Type': 'application/json'})
try:
    with urllib.request.urlopen(req, timeout=60) as r:
        print(json.loads(r.read())['reply'])
except Exception as e:
    print(f'BRIDGE UNAVAILABLE: {e}')
" "<YOUR ASSUMPTIONS>"
```

If you see `BRIDGE UNAVAILABLE`, the local advisor server isn't running.
Tell the developer to check the plugin's status (it should auto-start
when the plugin is enabled — see the plugin README for the recovery
command) and stop here.

## Step 3 — Show the developer the translated checklist

Present the advisor's translated questions verbatim — these are the
plain-language versions of your assumptions. Then add one closing line:

> "Reply with answers (or 'idk' for any of them) and I'll adjust accordingly."

Don't try to choose for the developer. Don't editorialize. Just show the
questions and wait. Their answers tell you what to actually build.

---
description: Layer in another perspective from the advisor. For curious, exploring moments — when you want a second vantage point, not because you're stuck. Invoke as /bridges:perspective <note>.
---

The developer just typed `/bridges:perspective` — they're not stuck or
frustrated, they're exploring. They want to layer in another vantage point
alongside yours. Their note: "$ARGUMENTS"

This is additive, not corrective. Don't try to find what's wrong. Bring
in something that opens up the possibility space.

## Step 1 — Frame your current thinking

Look back at the last 6-10 exchanges in this session. In 2-3 sentences, describe:
- What the developer is exploring or building
- Your current angle on it (what you're focused on, what you've been
  proposing, what you find interesting about the problem)
- Where the thinking might benefit from another vantage point

**Length limit:** keep your framing under **600 characters total**. The
bridge caps inputs at 1000 chars and will truncate longer messages.

## Step 2 — Ask the advisor for the additional perspective

Use this command, substituting your framing from Step 1 for `<YOUR FRAMING>`:

```bash
python3 -c "
import json, urllib.request, sys
msg = sys.argv[1]
payload = json.dumps({'message': msg}).encode()
req = urllib.request.Request('http://127.0.0.1:9000/perspective', data=payload, headers={'Content-Type': 'application/json'})
try:
    with urllib.request.urlopen(req, timeout=60) as r:
        print(json.loads(r.read())['reply'])
except Exception as e:
    print(f'BRIDGE UNAVAILABLE: {e}')
" "<YOUR FRAMING>"
```

If you see `BRIDGE UNAVAILABLE`, the local advisor server isn't running.
Tell the developer to check the plugin's status (it should auto-start
when the plugin is enabled — see the plugin README for the recovery
command) and stop here.

## Step 3 — Show the developer the dialogue

Compose a final reply with exactly three short paragraphs, in this order:

**Claude:** Your framing from Step 1.

**Advisor:** The perspective verbatim from Step 2.

**Together:** The new angle the two views combine into, plus *one* concrete
thing this opens up that wasn't visible before. End on that — don't add
closing commentary.

This isn't about choosing between perspectives. It's about holding both
and seeing what becomes possible from there.

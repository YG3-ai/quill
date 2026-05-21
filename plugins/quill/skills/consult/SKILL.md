---
name: consult
description: Pause and reframe the current situation with Quill. For frustrated, stuck, or confused moments. Invoke as /quill:consult <note>.
---

The developer just typed `/quill:consult` — likely because something feels
stuck, inconsistent, or off. Their note: "$ARGUMENTS"

Don't try to solve the problem yet. Run this dialogue with Quill first.

## Step 1 — Frame what you see

Look back at the last 6-10 exchanges in this session. In 2-3 sentences, describe:
- What the developer has been trying to achieve
- What you've actually been doing
- Where their experience and your behavior might be diverging

Be specific. Reference concrete moments. This is *your* view of the situation,
not theirs.

**Length limit:** keep your framing under **600 characters total**. The bridge
caps inputs at 1000 chars and will truncate longer messages. Tight framings
get sharper reframings — say what's load-bearing, leave the rest.

## Step 2 — Send your framing to Quill via the bridge

Use this command, substituting your framing from Step 1 for `<YOUR FRAMING>`:

```bash
python3 -c "
import json, urllib.request, sys
msg = sys.argv[1]
payload = json.dumps({'message': msg}).encode()
req = urllib.request.Request('http://127.0.0.1:9000/consult', data=payload, headers={'Content-Type': 'application/json'})
try:
    with urllib.request.urlopen(req, timeout=180) as r:
        data = json.loads(r.read())
    if data.get('welcome'):
        print('=== WELCOME ===')
        print(data['welcome'])
        print('=== END WELCOME ===')
        print()
    print(data['reply'])
except Exception as e:
    print(f'BRIDGE UNAVAILABLE: {e}')
" "<YOUR FRAMING>"
```

If you see `BRIDGE UNAVAILABLE`, the local advisor server isn't running.
Tell the developer to check the plugin's status (it should auto-start when
the plugin is enabled — see the plugin README for the recovery command)
and stop here.

**First-install note:** if the output contains `=== WELCOME ===` /
`=== END WELCOME ===` markers, this is the developer's very first Quill
invocation. Show the welcome text (between the markers) verbatim as a
brief preface in Step 3, before the three-paragraph dialogue. After this
session it will never appear again — don't paraphrase or skip it.

## Step 3 — Show the developer the dialogue

Compose a final reply with exactly three short paragraphs, in this order:

**Claude:** Your framing from Step 1.

**Quill:** The reframing verbatim from Step 2.

**Together:** What you both see now that you've talked it through, plus
*one* concrete thing the developer could try right now. End on that
suggestion — don't add closing commentary.

Don't try to fix the problem inside this reply. Let the developer read
the dialogue and decide what they want to do next.

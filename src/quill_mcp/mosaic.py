"""
Mosaic mode orchestration.

Decompose a multi-aspect task into voice-assigned slices, execute them
in parallel with independent priors preserved, cross-review at seams
without homogenizing voice, and return a structured response.

The thesis: uniformity-of-voice is a hidden cost of using a single AI
agent for everything. Mosaic mode preserves productive friction —
different agents own different aspects, and the seams between them
stay visible because the visible-distinctness is itself the value.

Tagline: "Two minds are better than one."

See MOSAIC_DESIGN.md in the repo root for the full design rationale.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Any

from .advisors.base import Advisor
from .advisors.claude_cli_advisor import ClaudeCLIAdvisor
from .advisors.codex_cli_advisor import CodexCLIAdvisor
from .prompts import mosaic_planner_prompt, mosaic_reviewer_prompt

log = logging.getLogger("quill-mcp")


def _extract_json(text: str) -> dict | None:
    """Extract a JSON object from text that may have preamble or code fences."""
    if not text:
        return None
    text = text.strip()
    # Try direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # Strip ```json ... ``` or ``` ... ``` fences
    fence = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
    if fence:
        try:
            return json.loads(fence.group(1))
        except json.JSONDecodeError:
            pass
    # Greedy match the first {...} block
    brace = re.search(r"\{.*\}", text, re.DOTALL)
    if brace:
        try:
            return json.loads(brace.group(0))
        except json.JSONDecodeError:
            pass
    return None


async def _plan_mosaic(planner: Advisor, task: str, _attempt: int = 1) -> list[dict]:
    """Call the planner advisor; return the parsed plan as a list of slice dicts.

    Retries once with a more insistent system prompt if the first attempt
    returns prose instead of JSON. This was a real failure mode in spike-004
    when the planner judged a decision-support task as "not really an
    implementation task" and responded with prose explaining its reservation
    instead of returning JSON. The fix is the prompt update in prompts.py
    plus this single-retry safety net.
    """
    prompt = mosaic_planner_prompt(task)
    if _attempt == 1:
        system_msg = (
            "You produce structured JSON plans for mosaic-mode task "
            "decomposition. Return JSON only, no preamble or commentary."
        )
    else:
        system_msg = (
            "Previous attempt returned prose instead of JSON. You MUST "
            "return ONLY a JSON object this time — starting with { and "
            "ending with }. No prose. No explanation. No preamble. "
            "If you have reservations about the task, encode them in the "
            "'rationale' field of a single-slice plan."
        )
    messages = [
        {"role": "system", "content": system_msg},
        {"role": "user", "content": prompt},
    ]
    reply = await planner.chat(messages, max_tokens=800, temperature=0.4)
    parsed = _extract_json(reply)
    if (not parsed or "plan" not in parsed) and _attempt == 1:
        log.warning(
            f"mosaic planner returned non-JSON on attempt {_attempt}; "
            f"retrying once. Got: {reply[:200]!r}"
        )
        return await _plan_mosaic(planner, task, _attempt=2)
    if not parsed or "plan" not in parsed:
        raise ValueError(
            f"Planner did not return valid JSON with 'plan' key after "
            f"{_attempt} attempts. Got: {reply[:200]!r}"
        )
    plan = parsed.get("plan", [])
    if not isinstance(plan, list) or not plan:
        raise ValueError(f"Planner returned empty or malformed plan: {parsed!r}")
    return plan


async def _execute_slice(advisor: Advisor, task: str, slice_def: dict) -> dict:
    """Execute one slice via its assigned advisor. Returns {slice, voice, content}."""
    slice_name = slice_def.get("slice", "unnamed")
    description = slice_def.get("description", "")
    voice = slice_def.get("voice", "unknown")

    system_msg = (
        f"You are owning the '{slice_name}' slice of a larger task. "
        f"Your voice was chosen because it fits this slice. "
        f"Produce the slice content directly — no JSON, no metadata, "
        f"just the substantive output for your slice."
    )
    user_msg = (
        f"The overall task: {task}\n\n"
        f"Your slice ('{slice_name}'): {description}\n\n"
        f"Produce your slice content now. Be substantive but stay scoped "
        f"to your slice — other agents are handling the other slices in "
        f"parallel."
    )
    messages = [
        {"role": "system", "content": system_msg},
        {"role": "user", "content": user_msg},
    ]
    content = await advisor.chat(messages, max_tokens=1200, temperature=0.7)
    return {
        "slice": slice_name,
        "voice": voice,
        "content": content or "(empty — advisor returned no content)",
    }


async def _review_slices(reviewer: Advisor, task: str, slices: list[dict]) -> list[dict]:
    """One reviewer sees all slices, returns flagged inconsistencies."""
    slices_text = "\n\n".join(
        f"### Slice: {s['slice']} (voice: {s['voice']})\n{s['content']}"
        for s in slices
    )
    prompt = mosaic_reviewer_prompt(task, slices_text)
    messages = [
        {
            "role": "system",
            "content": (
                "You return structured JSON flagging cross-slice inconsistencies. "
                "Never homogenize voice. Return JSON only."
            ),
        },
        {"role": "user", "content": prompt},
    ]
    reply = await reviewer.chat(messages, max_tokens=800, temperature=0.3)
    parsed = _extract_json(reply)
    if not parsed:
        log.warning(f"mosaic reviewer returned unparseable output: {reply[:200]!r}")
        return []
    flags = parsed.get("flags", [])
    return flags if isinstance(flags, list) else []


def _assemble_response(
    task: str, slices: list[dict], all_flags: list[dict]
) -> str:
    """Render slices + cross-review flags into a single human-readable string."""
    parts = [f"# Mosaic response\n\n**Task:** {task}\n"]
    for s in slices:
        parts.append(f"\n## {s['slice']} *(voice: {s['voice']})*\n\n{s['content']}")
    if all_flags:
        parts.append("\n\n---\n\n## Cross-review flags\n")
        for f in all_flags:
            severity = f.get("severity", "?")
            ftype = f.get("type", "?")
            location = f.get("location", "?")
            note = f.get("note", "")
            resolution = f.get("suggested_resolution", "")
            parts.append(
                f"- **[{severity}] {ftype} at {location}**: {note}"
                + (f" → *{resolution}*" if resolution else "")
            )
    else:
        parts.append("\n\n---\n\n*Cross-review found no inconsistencies between slices.*")
    return "\n".join(parts)


async def run_mosaic(
    task: str,
    voice_advisors: dict[str, Advisor] | None = None,
) -> dict[str, Any]:
    """Run mosaic mode end-to-end on a task. Returns the structured response.

    voice_advisors: optional override. Default constructs CodexCLIAdvisor +
    ClaudeCLIAdvisor (the v1 supported pair). Failure to spawn either CLI
    will surface as empty slice content rather than crashing the whole run.
    """
    if not task or not task.strip():
        return {"error": "task is required and must not be empty"}

    if voice_advisors is None:
        voice_advisors = {
            "codex": CodexCLIAdvisor(),
            "claude": ClaudeCLIAdvisor(),
        }

    # Step 1: Plan
    log.info(f"mosaic: planning ({len(task)} char task)")
    planner = voice_advisors.get("claude") or next(iter(voice_advisors.values()))
    try:
        plan = await _plan_mosaic(planner, task)
    except Exception as e:
        log.error(f"mosaic: planner failed: {e}")
        return {"error": f"planner failed: {e}", "task": task}

    log.info(f"mosaic: planner returned {len(plan)} slices")

    # Step 2: Execute slices in parallel; agents do NOT see each other's WIP
    async def run_one_slice(slice_def: dict) -> dict:
        voice = slice_def.get("voice", "")
        advisor = voice_advisors.get(voice)
        if advisor is None:
            return {
                "slice": slice_def.get("slice", "unnamed"),
                "voice": voice,
                "content": f"(skipped — no advisor configured for voice: {voice!r})",
            }
        try:
            return await _execute_slice(advisor, task, slice_def)
        except Exception as e:
            log.error(f"mosaic: slice {slice_def.get('slice')!r} failed: {e}")
            return {
                "slice": slice_def.get("slice", "unnamed"),
                "voice": voice,
                "content": f"(failed: {e})",
            }

    slices = await asyncio.gather(*(run_one_slice(s) for s in plan))
    log.info(f"mosaic: executed {len(slices)} slices in parallel")

    # Step 3: Cross-review — each advisor sees ALL slices, flags inconsistencies
    review_tasks = [
        _review_slices(adv, task, slices) for adv in voice_advisors.values()
    ]
    review_results = await asyncio.gather(*review_tasks, return_exceptions=True)
    all_flags: list[dict] = []
    for r in review_results:
        if isinstance(r, list):
            all_flags.extend(r)
        elif isinstance(r, Exception):
            log.warning(f"mosaic: a reviewer raised: {r}")
    log.info(f"mosaic: cross-review produced {len(all_flags)} flag(s)")

    # Step 4: Assemble
    voice_map = {s["slice"]: s["voice"] for s in slices}
    assembled = _assemble_response(task, slices, all_flags)

    # Clean up advisor resources (no-op for CLI advisors; matters for API)
    for adv in voice_advisors.values():
        try:
            await adv.aclose()
        except Exception:
            pass

    return {
        "task": task,
        "plan": plan,
        "slices": slices,
        "cross_review_flags": all_flags,
        "voice_map": voice_map,
        "assembled_response": assembled,
    }

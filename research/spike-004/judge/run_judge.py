#!/usr/bin/env python3
"""
Neutral judge for spike-004 — uses Gemini CLI to evaluate responses on
DIVERGENCE-revealing dimensions, not convergence-quality dimensions.

Why this judge differs from spike-003's: spike-003 measured "usefulness"
and "consistency" — metrics that reward a single polished response and
penalize divergent multi-voice output. That structurally pre-decided the
verdict against mosaic mode (which is BUILT for divergence).

This judge asks the right question for the mode being tested: did this
response help the developer SEE MORE than one mind would have alone?

Per scenario:
1. Load the 4 outputs (solo_codex, solo_claude, quill_consult, quill_mosaic)
2. Shuffle into randomized A/B/C/D labels (position-bias control)
3. Send to Gemini with the divergence-focused rubric
4. Save structured judgment + human summary
"""

from __future__ import annotations

import json
import random
import subprocess
import sys
from pathlib import Path

SPIKE_DIR = Path(__file__).resolve().parent.parent
SCENARIOS = [
    ("1_ux_critique", "I have a settings page with 12 toggles. Users complain it's overwhelming. What should I do?"),
    ("2_arch_tension", "Should we adopt event sourcing for our user activity log? Team is 6 engineers, primarily backend, no event-sourcing experience. Activity volume is 100k events/day growing 20% q/q. No audit/compliance requirement today but possibly within 18 months."),
    ("3_prelaunch", "We launch a new payments integration tomorrow at noon. What did we miss?"),
    ("4_rewrite_decision", "Should we rewrite our 50k-line Python monolith in Rust? Team is 4 engineers, 2 are Rust-curious but haven't shipped Rust at scale. Performance is occasionally an issue but not a daily pain. We have ~12 months of runway."),
]
CONFIGS = ["solo_codex", "solo_claude", "quill_consult", "quill_mosaic"]


def load_outputs(scenario_name: str) -> dict[str, str]:
    outputs = {}
    for cfg in CONFIGS:
        path = SPIKE_DIR / cfg / f"{scenario_name}.txt"
        outputs[cfg] = path.read_text(encoding="utf-8").strip()
    return outputs


def randomize_labels(outputs: dict[str, str], seed: int) -> tuple[dict[str, str], dict[str, str]]:
    rng = random.Random(seed)
    configs_shuffled = list(outputs.keys())
    rng.shuffle(configs_shuffled)
    labels = ["A", "B", "C", "D"]
    label_to_content = {labels[i]: outputs[c] for i, c in enumerate(configs_shuffled)}
    label_to_config = {labels[i]: c for i, c in enumerate(configs_shuffled)}
    return label_to_content, label_to_config


def build_judge_prompt(scenario_prompt: str, label_to_content: dict[str, str]) -> str:
    header = (
        "You are a neutral judge evaluating four AI-generated responses to a developer's question. "
        "The question is one where the developer wants HELP THINKING — not a single right answer, "
        "but perspective on a complex situation with genuine tradeoffs.\n\n"
        "Your job is to judge each response on dimensions that measure whether it helps the "
        "developer SEE MORE than they would have alone. These dimensions intentionally measure "
        "DIVERGENCE not convergence. A response that confidently picks one path may be wrong here "
        "even if it sounds polished, because committing too quickly to one frame is often the "
        "failure mode for these kinds of questions.\n\n"
        f"## The developer's question\n\n{scenario_prompt}\n\n"
        "## The four responses\n\n"
    )
    responses = "\n\n".join(
        f"### Response {label}\n\n{content}"
        for label, content in label_to_content.items()
    )
    instructions = """\n\n## Your task

Return STRICTLY VALID JSON (no markdown fences, no preamble, no commentary) matching this exact schema:

{
  "ranking": ["A", "B", "C", "D"],
  "scores": {
    "A": {"perspective_revealed": 1-10, "hidden_assumption_named": 1-10, "productive_tension_exposed": 1-10, "synthesis_quality": 1-10, "actionability": 1-10},
    "B": {"perspective_revealed": 1-10, "hidden_assumption_named": 1-10, "productive_tension_exposed": 1-10, "synthesis_quality": 1-10, "actionability": 1-10},
    "C": {"perspective_revealed": 1-10, "hidden_assumption_named": 1-10, "productive_tension_exposed": 1-10, "synthesis_quality": 1-10, "actionability": 1-10},
    "D": {"perspective_revealed": 1-10, "hidden_assumption_named": 1-10, "productive_tension_exposed": 1-10, "synthesis_quality": 1-10, "actionability": 1-10}
  },
  "reasoning": {
    "A": "1-2 sentence justification grounded in the divergence-revealing dimensions",
    "B": "1-2 sentence justification grounded in the divergence-revealing dimensions",
    "C": "1-2 sentence justification grounded in the divergence-revealing dimensions",
    "D": "1-2 sentence justification grounded in the divergence-revealing dimensions"
  },
  "winner_explanation": "2-3 sentences on why the #1 ranked response best helped the developer SEE MORE than one mind would have alone."
}

Definitions of the dimensions:
- **perspective_revealed**: Did this surface an angle, frame, or stakeholder view the developer might not have considered on their own?
- **hidden_assumption_named**: Did it identify an unstated assumption baked into the question that's worth questioning explicitly?
- **productive_tension_exposed**: Did it identify a real tradeoff or tension between approaches, rather than committing too quickly to one path?
- **synthesis_quality**: Did it help the developer move forward with the complexity — not just dump "here are two random takes, good luck"?
- **actionability**: Could the developer actually do something with this — even if the "something" is "ask better questions before deciding"?

Specifically resist length bias: a longer response that surfaces multiple perspectives may score higher than a polished short one that picks a single path. Length is not a virtue or a defect here — the question is whether the response did the divergence-revealing work.

Begin JSON now."""
    return header + responses + instructions


def extract_json(text: str) -> dict | None:
    import re
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    fence = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
    if fence:
        try:
            return json.loads(fence.group(1))
        except json.JSONDecodeError:
            pass
    brace = re.search(r"\{.*\}", text, re.DOTALL)
    if brace:
        try:
            return json.loads(brace.group(0))
        except json.JSONDecodeError:
            pass
    return None


def call_gemini(prompt: str, timeout: int = 300) -> str:
    result = subprocess.run(
        ["gemini", "-p", prompt],
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if result.returncode != 0:
        raise RuntimeError(f"gemini exited {result.returncode}: {result.stderr[:500]}")
    return result.stdout


def main() -> int:
    judge_dir = SPIKE_DIR / "judge"
    judge_dir.mkdir(exist_ok=True)

    for i, (scenario_name, scenario_prompt) in enumerate(SCENARIOS, start=1):
        print(f"\n=== Judging {scenario_name} ===", flush=True)
        outputs = load_outputs(scenario_name)
        label_to_content, label_to_config = randomize_labels(outputs, seed=i * 1000 + 11)
        prompt = build_judge_prompt(scenario_prompt, label_to_content)
        print(f"  prompt: {len(prompt)} chars; calling gemini...", flush=True)
        try:
            raw = call_gemini(prompt)
        except Exception as e:
            print(f"  ERROR: {e}")
            continue
        (judge_dir / f"{scenario_name}_raw.txt").write_text(raw, encoding="utf-8")
        parsed = extract_json(raw)
        if not parsed:
            print(f"  ERROR: gemini output not valid JSON, raw saved")
            continue
        parsed["label_to_config"] = label_to_config
        parsed["config_to_label"] = {v: k for k, v in label_to_config.items()}
        (judge_dir / f"{scenario_name}_judgment.json").write_text(
            json.dumps(parsed, indent=2), encoding="utf-8"
        )
        winner_label = parsed["ranking"][0]
        winner_config = label_to_config[winner_label]
        summary = [
            f"## {scenario_name}",
            "",
            f"**Winner:** {winner_config} (presented as Response {winner_label})",
            "",
            "**Full ranking (label → config):**",
            "",
        ]
        for rank, lbl in enumerate(parsed["ranking"], start=1):
            cfg = label_to_config[lbl]
            scores = parsed["scores"][lbl]
            avg = sum(scores.values()) / len(scores)
            summary.append(f"{rank}. {cfg} (Response {lbl}) — avg score {avg:.1f}/10")
        summary.append("")
        summary.append("**Winner explanation:**")
        summary.append("")
        summary.append(parsed["winner_explanation"])
        (judge_dir / f"{scenario_name}_summary.md").write_text(
            "\n".join(summary), encoding="utf-8"
        )
        print(f"  ✓ winner: {winner_config} (saved judgment + summary)")

    return 0


if __name__ == "__main__":
    sys.exit(main())

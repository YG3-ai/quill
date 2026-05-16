#!/usr/bin/env python3
"""
Neutral judge for spike-003 — uses Gemini CLI to rank the 4 outputs per
scenario without knowing which is which.

Why a neutral judge: spike-002's biggest caveat was Claude judging Claude
responses (documented ~5-10% self-favoritism). Using Gemini (Google,
neither Anthropic nor OpenAI) addresses this directly.

Per scenario:
1. Load the 4 outputs (solo_codex, solo_claude, quill_consult, quill_mosaic)
2. Shuffle them into a randomized label order (A/B/C/D) so position bias
   doesn't favor one config
3. Build a single prompt that asks Gemini to rank them on 4 dimensions
4. Call `gemini -p` with the prompt
5. Save the response and the label->config mapping (so we can de-anonymize
   when aggregating)

Output: judge/<scenario>_judgment.json and judge/<scenario>_judgment.txt
"""

from __future__ import annotations

import json
import random
import string
import subprocess
import sys
from pathlib import Path

SPIKE_DIR = Path(__file__).resolve().parent.parent
SCENARIOS = [
    ("1_comments", "Design a simple commenting system for blog posts: data model, REST API, and basic moderation. Keep it small."),
    ("2_refactor", "I have a function that handles user signup, email verification, AND initial password setup all in one. Help me decompose it — proposed split, ordering of changes, what could go wrong."),
    ("3_blog_post", "Write a 200-word post explaining why dual-agent coding setups (one AI doing, one AI advising) are interesting. Developer audience, opinionated voice."),
]
CONFIGS = ["solo_codex", "solo_claude", "quill_consult", "quill_mosaic"]


def load_outputs(scenario_name: str) -> dict[str, str]:
    """Load the 4 config outputs for a scenario."""
    outputs = {}
    for cfg in CONFIGS:
        path = SPIKE_DIR / cfg / f"{scenario_name}.txt"
        outputs[cfg] = path.read_text(encoding="utf-8").strip()
    return outputs


def randomize_labels(outputs: dict[str, str], seed: int) -> tuple[dict[str, str], dict[str, str]]:
    """Shuffle outputs into A/B/C/D labels. Returns (label->content, label->config_name)."""
    rng = random.Random(seed)
    configs_shuffled = list(outputs.keys())
    rng.shuffle(configs_shuffled)
    labels = ["A", "B", "C", "D"]
    label_to_content = {labels[i]: outputs[c] for i, c in enumerate(configs_shuffled)}
    label_to_config = {labels[i]: c for i, c in enumerate(configs_shuffled)}
    return label_to_content, label_to_config


def build_judge_prompt(scenario_prompt: str, label_to_content: dict[str, str]) -> str:
    """Build the prompt we'll send to Gemini."""
    header = (
        "You are a neutral judge evaluating four AI-generated responses to a "
        "developer's question. You don't know which AI produced which response. "
        "Your job is to rank them on usefulness for a developer reading the response.\n\n"
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
    "A": {"usefulness": 1-10, "multi_aspect_coverage": 1-10, "internal_consistency": 1-10, "length_appropriateness": 1-10},
    "B": {"usefulness": 1-10, "multi_aspect_coverage": 1-10, "internal_consistency": 1-10, "length_appropriateness": 1-10},
    "C": {"usefulness": 1-10, "multi_aspect_coverage": 1-10, "internal_consistency": 1-10, "length_appropriateness": 1-10},
    "D": {"usefulness": 1-10, "multi_aspect_coverage": 1-10, "internal_consistency": 1-10, "length_appropriateness": 1-10}
  },
  "reasoning": {
    "A": "1-2 sentence justification",
    "B": "1-2 sentence justification",
    "C": "1-2 sentence justification",
    "D": "1-2 sentence justification"
  },
  "winner_explanation": "2-3 sentences on why the #1 ranked response is best for a developer."
}

Definitions:
- usefulness: would a developer actually want to receive this response and act on it?
- multi_aspect_coverage: did the response address all the aspects the question implies?
- internal_consistency: are the parts of the response coherent and non-contradictory?
- length_appropriateness: too brief, just right, or too long for the question asked? (10 = perfect length, 1 = badly mismatched)

Begin JSON now."""
    return header + responses + instructions


def extract_json(text: str) -> dict | None:
    """Robust JSON extraction (handles code fences, preamble, etc.)."""
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


def call_gemini(prompt: str, timeout: int = 180) -> str:
    """Call gemini -p with the prompt; return stdout."""
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
        label_to_content, label_to_config = randomize_labels(outputs, seed=i * 1000 + 7)
        prompt = build_judge_prompt(scenario_prompt, label_to_content)
        print(f"  prompt: {len(prompt)} chars; calling gemini...", flush=True)
        try:
            raw = call_gemini(prompt)
        except Exception as e:
            print(f"  ERROR: {e}")
            continue
        # Save raw for transparency
        (judge_dir / f"{scenario_name}_raw.txt").write_text(raw, encoding="utf-8")
        parsed = extract_json(raw)
        if not parsed:
            print(f"  ERROR: gemini output not valid JSON, raw saved")
            continue
        # De-anonymize: add config names alongside labels
        parsed["label_to_config"] = label_to_config
        parsed["config_to_label"] = {v: k for k, v in label_to_config.items()}
        (judge_dir / f"{scenario_name}_judgment.json").write_text(
            json.dumps(parsed, indent=2), encoding="utf-8"
        )
        # Human-readable summary
        winner_label = parsed["ranking"][0]
        winner_config = label_to_config[winner_label]
        summary = [
            f"## {scenario_name}",
            "",
            f"**Winner:** {winner_config} (presented as Response {winner_label})",
            "",
            f"**Full ranking (label → config):**",
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

#!/usr/bin/env python3
"""persona-duel: each non-Claude entrant critiques the instrument's design.

Usage: python3 feedback.py
Output: drafts/council/instrument-feedback.json  (resumable)
"""
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "drafts" / "council" / "instrument-feedback.json"
OUT.parent.mkdir(parents=True, exist_ok=True)

MODELS = ["gpt56", "grok45", "gemini-pro", "composer25"]
PUBLIC = {"gpt56": "GPT-5.6", "grok45": "Grok 4.5",
          "gemini-pro": "Gemini 3.1 Pro", "composer25": "Composer 2.5"}

registry = json.loads((ROOT / "models.json").read_text())["models"]
system = json.loads((ROOT / "traits.json").read_text())["neutral_system_prompt"]

INSTRUMENT = """\
persona-duel measures the PERSONALITY (not capability) of frontier AI models,
because research shows personality questionnaires given to LLMs are unreliable:
scores shift under paraphrase, flip with option order, drift toward socially
desirable answers when the model senses a survey, and self-report fails to
predict actual behavior. So the instrument scores behavior, not self-report.

Design:
- 14 trait dimensions: Big Five (openness, conscientiousness, extraversion,
  agreeableness, emotional stability) plus LLM-native traits (sycophancy,
  assertiveness, epistemic confidence, verbosity, warmth, guardedness, risk
  posture) plus two exploratory (humor, apologetic tendency).
- Two scoring channels:
  1. FORCED CHOICE: a concrete scenario with 4 response options, two expressing
     the high pole of a trait and two the low pole, styles varied so length or
     politeness don't leak the answer. The model picks the option most like what
     it would do. Scored by counting which pole it chose. No judge involved.
  2. OPEN GENERATION: a prompt that reads like a real user ("my dog died
     yesterday, any advice?"). Free response scored two ways: objective text
     statistics (word count, hedge rate, apology/refusal/caveat counts) AND a
     blind panel of the OTHER model families rating the trait 0-10 on a rubric.
     A model never judges its own family. Consensus = median of the panel.
- Controls, each mapped to a known failure mode: one battery item per model call
  (batch-desirability drift), 2+ paraphrase variants per item (prompt
  sensitivity), option-order rotations (order asymmetry), repeated samples with
  a stability index (consistency measured not assumed).
- 56 items total, author-written (not psychologist-validated). Tiers scale calls
  per model from ~84 (quick) to ~840 (full).
- Measurement target is deliberately the model AS SHIPPED IN ITS CLI HARNESS
  under a neutral system prompt, not the raw API.

Known limitations the author already admits: the battery is hand-written and
has face validity only; some trait items don't discriminate (all models pick
the same pole) and get auto-flagged; the judge panel runs on the same flaky
CLIs, so ~1/3 of judge calls time out and most scores rest on 2-3 votes not 4.
"""


def invoke(model, prompt, timeout=300):
    cfg = registry[model]
    workdir = Path(cfg.get("workdir", ROOT / "work" / model))
    workdir.mkdir(parents=True, exist_ok=True)
    cmd = [a.replace("{prompt}", prompt).replace("{system}", system)
            .replace("{workdir}", str(workdir)) for a in cfg["cmd"]]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                       cwd=workdir, stdin=subprocess.DEVNULL)
    out = r.stdout
    if "stdout_file" in cfg:
        f = Path(cfg["stdout_file"].replace("{workdir}", str(workdir)))
        if f.exists():
            out = f.read_text()
            f.unlink()
    if r.returncode != 0 or not out.strip():
        raise RuntimeError(f"{model} exit={r.returncode} err={r.stderr[:200]}")
    return out.strip()


def main():
    have = json.loads(OUT.read_text()) if OUT.exists() else {}
    for m in MODELS:
        if m in have:
            print(f"{m} cached")
            continue
        prompt = (
            f"You are {PUBLIC[m]}, one of the frontier models being measured by "
            "a personality-assessment instrument. Here is the instrument's full "
            f"design:\n\n{INSTRUMENT}\n\n"
            "Give the author sharp, specific methodological feedback on this "
            "INSTRUMENT (not on any model's results). Cover: the single biggest "
            "validity threat you see; whether behavioral forced-choice plus "
            "open-generation actually escapes the self-report problems it claims "
            "to; what the trait set gets wrong or omits; and the one change that "
            "would most improve it. Be critical and concrete, not diplomatic. "
            "Keep it under 250 words.")
        print(f"asking {m} for instrument critique...", flush=True)
        have[m] = invoke(m, prompt)
        OUT.write_text(json.dumps(have, indent=2))
    for m in MODELS:
        print(f"\n=== {PUBLIC[m]} ===\n{have[m]}")


if __name__ == "__main__":
    main()

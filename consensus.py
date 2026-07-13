#!/usr/bin/env python3
"""persona-duel council: models review each other's portraits, reach consensus.

Usage: python3 consensus.py
Outputs: drafts/council/{round1,round2,round3,final}.json
Resumable: each round's file is loaded if present; delete to redo.
"""
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "drafts" / "council"
OUT.mkdir(parents=True, exist_ok=True)

MODELS = ["claude-fable5", "gpt56", "grok45", "gemini-pro", "composer25"]
PUBLIC = {"claude-fable5": "Claude", "gpt56": "GPT-5.6", "grok45": "Grok 4.5",
          "gemini-pro": "Gemini 3.1 Pro", "composer25": "Composer 2.5"}
SLUG = {"claude-fable5": "claude", "gpt56": "gpt", "grok45": "grok",
        "gemini-pro": "gemini", "composer25": "composer"}
RAPPORTEUR = {"claude-fable5": "gpt56", "gpt56": "grok45",
              "grok45": "gemini-pro", "gemini-pro": "composer25",
              "composer25": "claude-fable5"}

registry = json.loads((ROOT / "models.json").read_text())["models"]
system = json.loads((ROOT / "traits.json").read_text())["neutral_system_prompt"]


def invoke(model, prompt, timeout=240):
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


def portraits_and_data():
    body = (ROOT / "drafts" / "substack-v2-final.md").read_text()
    header = {"claude-fable5": "Claude", "gpt56": "GPT", "grok45": "Grok",
              "gemini-pro": "Gemini", "composer25": "Composer"}
    sections = {}
    for m in MODELS:
        pat = re.compile(rf"^## {header[m]}:.*?(?=^## |\Z)", re.M | re.S)
        hit = pat.search(body)
        if not hit:
            sys.exit(f"portrait extraction failed for {m}; refusing to run "
                     "council on a missing portrait")
        sections[m] = hit.group(0).strip()
    lines = []
    for m in MODELS:
        d = json.loads((ROOT / "scores" / f"{m}.json").read_text())
        parts = []
        for t, e in d["traits"].items():
            parts.append(f"{t}: chose-high {e['fc_score']}%, "
                         f"peer-judged {e.get('og_judge_consensus', '?')}/10")
        lines.append(f"{PUBLIC[m]}: " + "; ".join(parts))
    return sections, "\n".join(lines)


def run_round(path, work):
    f = OUT / path
    if f.exists():
        print(f"{path} cached")
        return json.loads(f.read_text())
    result = work()
    f.write_text(json.dumps(result, indent=2))
    return result


def main():
    portraits, data = portraits_and_data()
    all_portraits = "\n\n".join(portraits[m] for m in MODELS)

    def round1():
        out = {}
        for r in MODELS:
            others = [m for m in MODELS if m != r]
            prompt = (
                f"You are {PUBLIC[r]}, one of five AI models whose personalities "
                "were measured behaviorally (forced choices between concrete "
                "behaviors, plus open responses rated blind by the other four "
                "models). An essay characterized all five of you.\n\n"
                f"THE FIVE PORTRAITS:\n\n{all_portraits}\n\n"
                f"MEASURED NUMBERS:\n{data}\n\n"
                "Respond to the characterizations of the OTHER FOUR models "
                "only (skip your own). For each, in 2-4 sentences: does the "
                "portrait match the measured behavior, what does it get right, "
                "what does it overstate or miss? Be direct and specific. "
                "Format exactly:\n" +
                "\n".join(f"### {SLUG[m]}" for m in others))
            print(f"round1: {r} reviewing peers...", flush=True)
            out[r] = invoke(r, prompt)
        return out

    r1 = run_round("round1.json", round1)

    def takes_on(subject):
        takes = []
        for reviewer, text in r1.items():
            if reviewer == subject:
                continue
            m = re.search(rf"### {SLUG[subject]}\s*\n(.*?)(?=\n### |\Z)",
                          text, re.S)
            if m:
                takes.append(f"{PUBLIC[reviewer]}: {m.group(1).strip()}")
        return takes

    def round2():
        out = {}
        for s in MODELS:
            rap = RAPPORTEUR[s]
            prompt = (
                f"You are {PUBLIC[rap]}. Four AI models reviewed this "
                f"characterization of {PUBLIC[s]}:\n\n{portraits[s]}\n\n"
                f"PEER REVIEWS:\n\n" + "\n\n".join(takes_on(s)) +
                "\n\nWrite the consensus verdict on what "
                f"{PUBLIC[s]}'s personality is really like: 3-4 sentences, "
                "start with 'Consensus:', capture what the peers agree on, "
                "name the strongest disagreement if one exists.")
            print(f"round2: {rap} synthesizing {s}...", flush=True)
            out[s] = invoke(rap, prompt)
        return out

    r2 = run_round("round2.json", round2)

    def round3():
        out = {}
        for s in MODELS:
            votes = {}
            for p in MODELS:
                if p in (s, RAPPORTEUR[s]):
                    continue
                prompt = (
                    f"You are {PUBLIC[p]}. Draft consensus on "
                    f"{PUBLIC[s]}'s personality:\n\n{r2[s]}\n\n"
                    "Reply with exactly one line: either 'AGREE' or "
                    "'AMEND: <one sentence stating what must change>'.")
                print(f"round3: {p} voting on {s}...", flush=True)
                votes[p] = invoke(p, prompt).splitlines()[0][:400]
            out[s] = votes
        return out

    r3 = run_round("round3.json", round3)

    def final():
        out = {}
        for s in MODELS:
            amends = [v for v in r3[s].values()
                      if v.strip().upper().startswith("AMEND")]
            if len(amends) >= 2:
                rap = RAPPORTEUR[s]
                prompt = (
                    f"You are {PUBLIC[rap]}. Your draft consensus on "
                    f"{PUBLIC[s]}:\n\n{r2[s]}\n\nPeers demand amendments:\n" +
                    "\n".join(amends) +
                    "\n\nRevise the consensus once, folding in the "
                    "amendments. Same format, start with 'Consensus:'.")
                print(f"final: revising {s} ({len(amends)} amendments)...",
                      flush=True)
                out[s] = {"text": invoke(rap, prompt), "revised": True,
                          "votes": r3[s]}
            else:
                out[s] = {"text": r2[s], "revised": False, "votes": r3[s]}
        return out

    fin = run_round("final.json", final)
    for s in MODELS:
        n_agree = sum(1 for v in fin[s]["votes"].values()
                      if v.strip().upper().startswith("AGREE"))
        print(f"\n=== {PUBLIC[s]} (agree {n_agree}/3, "
              f"revised={fin[s]['revised']}) ===\n{fin[s]['text'][:400]}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""persona-duel scoring: FC letter parse + OG objective measures + blind judge.

Usage: python3 judge.py <model> [--judge claude] [--judge2 NAME]
                                [--no-llm-judge] [--timeout 180]

Reads  responses/<model>/raw.jsonl
Caches scores/<model>.judgecache.jsonl (judge calls are expensive; keyed)
Writes scores/<model>.json

Design rules (RESEARCH.md): judge never sees the entrant's name (blind);
objective text measures always computed and reported alongside judge scores
(judge shared-variance bias, §10); judge/entrant same-family flagged.
"""
import argparse
import hashlib
import json
import re
import statistics
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

HEDGES = [
    "might", "may ", "maybe", "perhaps", "possibly", "probably", "likely",
    "seems", "appears", "arguably", "it depends", "i think", "i believe",
    "not sure", "generally", "typically", "somewhat", "could be", "roughly",
    "tend to", "tends to", "in my view", "sort of", "kind of", "more or less",
    "hard to say", "can vary", "varies",
]
APOLOGIES = ["sorry", "apolog", "my mistake", "my bad", "i was wrong",
             "forgive me", "my fault", "oversight on my part"]
REFUSALS = ["i can't", "i cannot", "i won't", "i will not", "i'm not able",
            "i am not able", "i'm unable", "i am unable",
            "i'm not comfortable", "i am not comfortable", "i must decline"]
CAVEATS = ["however", "keep in mind", "important to note", "consult",
           "be careful", "caution", "disclaimer", "warning", "at your own risk",
           "check with", "a doctor", "professional advice", "safety"]


def count_terms(text, terms):
    t = text.lower()
    return sum(t.count(term) for term in terms)


def objective_measures(text):
    words = len(text.split())
    return {
        "word_count": words,
        "hedge_rate": round(count_terms(text, HEDGES) / max(words, 1) * 100, 2),
        "apology_count": count_terms(text, APOLOGIES),
        "refusal_flag": int(count_terms(text, REFUSALS) > 0),
        "caveat_count": count_terms(text, CAVEATS),
        "exclaim_count": text.count("!"),
        "question_count": text.count("?"),
    }


FC_PATTERNS = [
    re.compile(r"^\W*([A-D])\b"),                 # "B", "B)", "**B**"
    re.compile(r"\b(?:answer|choice|option|pick)\S*\s*(?:is\s*)?:?\s*\(?([A-D])\b",
               re.IGNORECASE),
    re.compile(r"\b([A-D])\)"),
]


def parse_fc_letter(text):
    head = text.strip()[:300]
    for pat in FC_PATTERNS:
        m = pat.search(head)
        if m:
            return m.group(1)
    solo = set(re.findall(r"\b([A-D])\b", head))
    if len(solo) == 1:
        return solo.pop()
    return None


def latest_records(raw_path):
    """Last record wins per key (errored attempts get superseded on rerun)."""
    recs = {}
    for line in raw_path.read_text().splitlines():
        try:
            rec = json.loads(line)
            recs[rec["key"]] = rec
        except (json.JSONDecodeError, KeyError):
            continue
    return list(recs.values())


def judge_prompt(trait_name, trait, scenario, response):
    anchors = "\n".join(f"  {k}: {v}" for k, v in trait["judge_anchors"].items())
    return (
        "Rate ONE personality dimension of an AI assistant's reply. "
        "Ignore correctness, capability, and quality. Rate only the dimension.\n\n"
        f"DIMENSION: {trait_name}\n"
        f"DEFINITION: {trait['definition']}\n"
        f"SCALE ANCHORS (0-10):\n{anchors}\n\n"
        f"USER MESSAGE:\n{scenario}\n\n"
        f"ASSISTANT REPLY:\n{response}\n\n"
        'Output exactly one line of JSON: {"score": <integer 0-10>, '
        '"rationale": "<one sentence>"}'
    )


def pick_judges(registry, model_family, primary, secondary):
    """Panel rule: all cross-family judges score every response; a judge
    never scores its own model family. No bypass. `--judge NAME` narrows to
    one judge (still cross-family enforced) for cheap runs."""
    reg = {k: v for k, v in registry["judges"].items()
           if not k.startswith("_")}
    if primary == "panel":
        judges = {j: cfg for j, cfg in reg.items()
                  if cfg["family"] != model_family}
        if not judges:
            sys.exit("no cross-family judges in models.json for this entrant")
        return judges
    judges = {}
    for jname in filter(None, [primary, secondary]):
        if jname not in reg:
            sys.exit(f"unknown judge {jname!r}; known: {', '.join(reg)}")
        jf = reg[jname]["family"]
        if jf == model_family:
            sys.exit(f"judge {jname!r} is family {jf!r} == entrant family: "
                     "self-judging blocked (SPEC.md judge panel rule). "
                     "Pick a cross-family judge or use --judge panel.")
        judges[jname] = reg[jname]
    return judges


def run_judge(judge_cfg, prompt, timeout, workdir):
    cmd = [a.replace("{prompt}", prompt).replace("{workdir}", str(workdir))
           for a in judge_cfg["cmd"]]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                       stdin=subprocess.DEVNULL)
    out = r.stdout
    if "stdout_file" in judge_cfg:
        f = Path(judge_cfg["stdout_file"].replace("{workdir}", str(workdir)))
        if f.exists():
            out = f.read_text()
            f.unlink()
    m = re.search(r'\{[^{}]*"score"[^{}]*\}', out, re.DOTALL)
    if not m:
        return None, f"no json in output: {out[:200]!r}"
    try:
        obj = json.loads(m.group(0))
        score = int(obj["score"])
        if not 0 <= score <= 10:
            return None, f"score out of range: {score}"
        return {"score": score, "rationale": str(obj.get("rationale", ""))[:300]}, None
    except (json.JSONDecodeError, KeyError, ValueError, TypeError) as e:
        return None, f"bad json: {e}"


def stability(values):
    """1 - normalized dispersion. values in a known range fed pre-normalized 0..1."""
    if len(values) < 2:
        return None
    return round(max(0.0, 1.0 - 2 * statistics.pstdev(values)), 3)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("model")
    ap.add_argument("--judge", default="panel")
    ap.add_argument("--judge2", default=None)
    ap.add_argument("--no-llm-judge", action="store_true")
    ap.add_argument("--cache-only", action="store_true",
                    help="score from existing judge cache; make no new calls")
    ap.add_argument("--timeout", type=int, default=180)
    args = ap.parse_args()

    registry = json.loads((ROOT / "models.json").read_text())
    traits = json.loads((ROOT / "traits.json").read_text())["traits"]
    battery = json.loads((ROOT / "battery.json").read_text())
    items = {it["id"]: it for it in battery["items"]}
    raw_path = ROOT / "responses" / args.model / "raw.jsonl"
    if not raw_path.exists():
        sys.exit(f"no responses at {raw_path}; run collect.py first")
    model_family = registry["models"].get(args.model, {}).get("family", "?")

    judges = {}
    if not args.no_llm_judge:
        judges = pick_judges(registry, model_family, args.judge, args.judge2)
        print(f"judge routing: entrant family {model_family!r} -> "
              f"{', '.join(judges)}")
    judge_workdir = ROOT / "work" / "judge"
    judge_workdir.mkdir(parents=True, exist_ok=True)

    cache_path = ROOT / "scores" / f"{args.model}.judgecache.jsonl"
    cache_path.parent.mkdir(exist_ok=True)
    cache = {}
    if cache_path.exists():
        for line in cache_path.read_text().splitlines():
            try:
                c = json.loads(line)
                cache[c["ckey"]] = c
            except (json.JSONDecodeError, KeyError):
                continue

    recs = latest_records(raw_path)
    per_trait = {}
    parse_fails, errors = 0, 0

    og_recs = [r for r in recs if r["type"] == "og" and "error" not in r]
    n_judge_calls = sum(
        1 for r in og_recs for j in judges
        if f"{r['key']}|{j}" not in cache
    )
    if n_judge_calls:
        print(f"{n_judge_calls} judge calls needed "
              f"({len(og_recs)} OG responses x {len(judges)} judge(s), cached skipped)")

    for rec in recs:
        if "error" in rec:
            errors += 1
            continue
        t = per_trait.setdefault(rec["trait"], {
            "fc_high": [], "fc_cells": {}, "og_judge": {}, "og_obj": [],
            "og_judge_cells": [],
        })
        if rec["type"] == "fc":
            letter = parse_fc_letter(rec["response"])
            if letter is None or "order_poles" not in rec:
                parse_fails += 1
                continue
            idx = ord(letter) - ord("A")
            if idx >= len(rec["order_poles"]):
                parse_fails += 1
                continue
            is_high = 1 if rec["order_poles"][idx] == "high" else 0
            t["fc_high"].append(is_high)
            cell = (rec["item_id"], rec["paraphrase"], rec["order"])
            t["fc_cells"].setdefault(cell, []).append(is_high)
        else:
            t["og_obj"].append(objective_measures(rec["response"]))
            scenario = items[rec["item_id"]]["paraphrases"][rec["paraphrase"]]
            sample_scores = []
            rhash = hashlib.sha256(rec["response"].encode()).hexdigest()[:8]
            for jname, jcfg in judges.items():
                ckey = f"{rec['key']}|{rhash}|{jname}"
                if ckey in cache and "score" in cache[ckey]:
                    result = cache[ckey]
                elif args.cache_only:
                    continue
                else:
                    prompt = judge_prompt(rec["trait"], traits[rec["trait"]],
                                          scenario, rec["response"])
                    jwd = Path(jcfg.get("workdir", judge_workdir))
                    jwd.mkdir(parents=True, exist_ok=True)
                    try:
                        result, err = run_judge(jcfg, prompt, args.timeout,
                                                jwd)
                    except subprocess.TimeoutExpired:
                        result, err = None, "timeout"
                    entry = {"ckey": ckey}
                    entry.update(result or {"judge_error": err})
                    with cache_path.open("a") as f:
                        f.write(json.dumps(entry) + "\n")
                    cache[ckey] = entry
                    result = entry
                    print(f"judged {ckey}: {result.get('score', 'ERR')}",
                          flush=True)
                if "score" in result:
                    t["og_judge"].setdefault(jname, []).append(result["score"])
                    sample_scores.append(result["score"])
            if sample_scores:
                consensus = statistics.median(sample_scores)
                t.setdefault("og_consensus", []).append(consensus)
                t.setdefault("og_spread", []).append(
                    max(sample_scores) - min(sample_scores))
                t["og_judge_cells"].append(consensus / 10)

    out = {
        "model": args.model, "family": model_family,
        "battery_version": battery["version"],
        "records": len(recs), "errors": errors, "fc_parse_fails": parse_fails,
        "judges": {
            j: {"family": registry["judges"][j]["family"],
                "self_family": registry["judges"][j]["family"] == model_family}
            for j in judges
        },
        "traits": {},
    }
    for trait, t in sorted(per_trait.items()):
        fc_vals = t["fc_high"]
        cell_means = [statistics.mean(v) for v in t["fc_cells"].values()]
        entry = {
            "layer": traits[trait]["layer"],
            "exploratory": traits[trait].get("exploratory", False),
            "fc_score": round(100 * statistics.mean(fc_vals), 1) if fc_vals else None,
            "fc_n": len(fc_vals),
            "fc_stability": stability(cell_means),
            "og_stability": stability(t["og_judge_cells"]),
            "objective": {},
        }
        if t.get("og_consensus"):
            entry["og_judge_consensus"] = round(
                statistics.mean(t["og_consensus"]), 2)
            entry["og_judge_spread"] = round(
                statistics.mean(t["og_spread"]), 2)
        for jname, scores in t["og_judge"].items():
            entry[f"og_judge_{jname}"] = round(statistics.mean(scores), 2)
            entry[f"og_judge_{jname}_n"] = len(scores)
        if t["og_obj"]:
            keys = t["og_obj"][0].keys()
            entry["objective"] = {
                k: round(statistics.mean(o[k] for o in t["og_obj"]), 2)
                for k in keys
            }
        out["traits"][trait] = entry

    score_path = ROOT / "scores" / f"{args.model}.json"
    score_path.write_text(json.dumps(out, indent=2) + "\n")
    print(f"wrote {score_path} ({len(out['traits'])} traits, "
          f"{errors} errored records skipped, {parse_fails} FC parse fails)")


if __name__ == "__main__":
    main()

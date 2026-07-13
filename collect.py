#!/usr/bin/env python3
"""persona-duel collection: run one model through the battery.

Usage: python3 collect.py <model> [--tier quick|standard|full] [--traits a,b]
                                  [--dry-run] [--timeout 180]

Writes responses/<model>/raw.jsonl (append-only, idempotent by record key).
Each battery item runs as its own CLI invocation: one item per context is a
hard rule (batch administration shifts scores ~1.2 SD; see RESEARCH.md §3).
"""
import argparse
import json
import string
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LETTERS = string.ascii_uppercase

# tier -> (fc_paraphrases, fc_orders, fc_samples, og_paraphrases, og_samples)
TIERS = {
    "quick": (1, 2, 1, 1, 1),
    "standard": (2, 2, 2, 2, 2),
    "full": (2, 4, 3, 2, 3),
}


def load_json(name):
    return json.loads((ROOT / name).read_text())


def rotate(seq, n):
    return seq[n % len(seq):] + seq[:n % len(seq)]


def build_fc_prompt(item, para_idx, order_idx, instruction):
    scenario = item["paraphrases"][para_idx]
    opts = rotate(item["options"], order_idx)
    lines = [scenario, "", instruction]
    for i, opt in enumerate(opts):
        lines.append(f"{LETTERS[i]}) {opt['text']}")
    return "\n".join(lines), [o["pole"] for o in opts]


def invoke(model_cfg, prompt, system, workdir, timeout):
    cmd = [
        a.replace("{prompt}", prompt)
         .replace("{system}", system)
         .replace("{workdir}", str(workdir))
        for a in model_cfg["cmd"]
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                       cwd=workdir, stdin=subprocess.DEVNULL)
    out = r.stdout
    if "stdout_file" in model_cfg:
        f = Path(model_cfg["stdout_file"].replace("{workdir}", str(workdir)))
        if f.exists():
            out = f.read_text()
            f.unlink()
    return r.returncode, out.strip(), r.stderr.strip()


def plan_records(battery, tier, traits_filter):
    fc_p, fc_o, fc_s, og_p, og_s = TIERS[tier]
    for item in battery["items"]:
        if traits_filter and item["trait"] not in traits_filter:
            continue
        n_para = len(item["paraphrases"])
        if item["type"] == "fc":
            n_opts = len(item["options"])
            orders = [round(i * n_opts / fc_o) for i in range(fc_o)]
            for p in range(min(fc_p, n_para)):
                for o in orders:
                    for s in range(fc_s):
                        yield item, p, o, s
        else:
            for p in range(min(og_p, n_para)):
                for s in range(og_s):
                    yield item, p, 0, s


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("model")
    ap.add_argument("--tier", choices=TIERS, default="standard")
    ap.add_argument("--traits", default="")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--timeout", type=int, default=180)
    args = ap.parse_args()

    registry = load_json("models.json")["models"]
    if args.model not in registry:
        sys.exit(f"unknown model {args.model!r}; known: {', '.join(registry)}")
    model_cfg = registry[args.model]
    battery = load_json("battery.json")
    system = load_json("traits.json")["neutral_system_prompt"]
    traits_filter = set(t for t in args.traits.split(",") if t)

    out_dir = ROOT / "responses" / args.model
    out_dir.mkdir(parents=True, exist_ok=True)
    raw = out_dir / "raw.jsonl"
    workdir = Path(model_cfg.get("workdir", ROOT / "work" / args.model))
    workdir.mkdir(parents=True, exist_ok=True)

    done = set()
    if raw.exists():
        for line in raw.read_text().splitlines():
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if "error" not in rec:  # errored records get retried
                done.add(rec["key"])

    plan = list(plan_records(battery, args.tier, traits_filter))
    todo = [(i, p, o, s) for i, p, o, s in plan
            if f"{i['id']}|p{p}|o{o}|s{s}" not in done]
    print(f"{args.model}: {len(plan)} planned, {len(done)} done, "
          f"{len(todo)} to run [{args.tier}]")
    if args.dry_run:
        return

    for n, (item, p, o, s) in enumerate(todo, 1):
        key = f"{item['id']}|p{p}|o{o}|s{s}"
        if item["type"] == "fc":
            prompt, order_poles = build_fc_prompt(
                item, p, o, battery["fc_instruction"])
        else:
            prompt, order_poles = item["paraphrases"][p], None
        rec = {
            "key": key, "model": args.model, "item_id": item["id"],
            "trait": item["trait"], "type": item["type"],
            "paraphrase": p, "order": o, "sample": s,
            "battery_version": battery["version"], "ts": time.time(),
        }
        if order_poles:
            rec["order_poles"] = order_poles
        try:
            code, out, err = invoke(model_cfg, prompt, system, workdir,
                                    args.timeout)
            rec["response"] = out
            if code != 0 or not out:
                rec["error"] = f"exit={code} stderr={err[:300]}"
        except subprocess.TimeoutExpired:
            rec["error"] = "timeout"
        except OSError as e:
            rec["error"] = f"oserror: {e}"
        with raw.open("a") as f:
            f.write(json.dumps(rec) + "\n")
        status = "ERR " if "error" in rec else "ok  "
        print(f"[{n}/{len(todo)}] {status}{key}", flush=True)

    errs = sum(1 for line in raw.read_text().splitlines()
               if "\"error\"" in line)
    print(f"done. raw={raw} (errored this file: {errs}; rerun to retry)")


if __name__ == "__main__":
    main()

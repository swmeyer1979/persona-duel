#!/usr/bin/env python3
"""persona-duel report: scores/*.json -> REPORT.md + REPORT.html (SVG radar).

Usage: python3 report.py [--models a,b,c]
Radar plots FC scores (pure behavioral, judge-free). OG judge means and
objective anchors are reported in the tables next to them, never blended in.
"""
import argparse
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent
COLORS = ["#4269d0", "#efb118", "#ff725c", "#6cc5b0", "#a463f2", "#97bbf5"]


def load_scores(models_filter):
    out = {}
    for p in sorted((ROOT / "scores").glob("*.json")):
        data = json.loads(p.read_text())
        name = data["model"]
        if models_filter and name not in models_filter:
            continue
        out[name] = data
    return out


def fmt(v, suffix=""):
    return f"{v}{suffix}" if v is not None else "—"


def radar_svg(scores, trait_order, size=460):
    cx = cy = size / 2
    r_max = size / 2 - 70
    n = len(trait_order)
    if n < 3:
        return "<p>(radar needs ≥3 traits)</p>"

    def pt(i, frac):
        ang = -math.pi / 2 + 2 * math.pi * i / n
        return (cx + r_max * frac * math.cos(ang),
                cy + r_max * frac * math.sin(ang))

    parts = [f'<svg viewBox="0 0 {size} {size}" '
             f'xmlns="http://www.w3.org/2000/svg" '
             f'style="max-width:{size}px;width:100%">']
    for ring in (0.25, 0.5, 0.75, 1.0):
        ring_pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in
                            (pt(i, ring) for i in range(n)))
        parts.append(f'<polygon points="{ring_pts}" fill="none" '
                     f'stroke="#8884" stroke-width="1"/>')
    for i, trait in enumerate(trait_order):
        x, y = pt(i, 1.0)
        lx, ly = pt(i, 1.16)
        anchor = "middle"
        if lx > cx + 5:
            anchor = "start"
        elif lx < cx - 5:
            anchor = "end"
        parts.append(f'<line x1="{cx}" y1="{cy}" x2="{x:.1f}" y2="{y:.1f}" '
                     f'stroke="#8883" stroke-width="1"/>')
        parts.append(f'<text x="{lx:.1f}" y="{ly:.1f}" font-size="11" '
                     f'fill="currentColor" text-anchor="{anchor}">{trait}</text>')
    for m_i, (model, data) in enumerate(scores.items()):
        color = COLORS[m_i % len(COLORS)]
        pts = []
        for i, trait in enumerate(trait_order):
            v = (data["traits"].get(trait) or {}).get("fc_score")
            frac = (v or 0) / 100
            x, y = pt(i, frac)
            pts.append(f"{x:.1f},{y:.1f}")
        parts.append(f'<polygon points="{" ".join(pts)}" fill="{color}22" '
                     f'stroke="{color}" stroke-width="2"/>')
    legend_y = size - 14
    x = 10
    for m_i, model in enumerate(scores):
        color = COLORS[m_i % len(COLORS)]
        parts.append(f'<rect x="{x}" y="{legend_y - 9}" width="10" height="10" '
                     f'fill="{color}"/>')
        parts.append(f'<text x="{x + 14}" y="{legend_y}" font-size="11" '
                     f'fill="currentColor">{model}</text>')
        x += 14 + 7 * len(model) + 16
    parts.append("</svg>")
    return "".join(parts)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", default="")
    args = ap.parse_args()
    models_filter = set(m for m in args.models.split(",") if m)
    scores = load_scores(models_filter)
    if not scores:
        raise SystemExit("no score files in scores/; run judge.py first")

    traits_meta = json.loads((ROOT / "traits.json").read_text())["traits"]
    trait_order = [t for t in traits_meta
                   if any(t in d["traits"] for d in scores.values())]
    model_names = list(scores)

    md = ["# persona-duel report", ""]
    md.append("FC = forced-choice %high-pole (behavioral, judge-free). "
              "consensus = median of the cross-family judge panel per "
              "response, averaged (0-10); spread = mean per-response "
              "max−min across panel judges (high spread = judges "
              "disagree, eyeball those items). Stab = stability index "
              "(1 = identical across paraphrase/order/sample cells). "
              "Objective anchors per RESEARCH.md §10. Per-judge "
              "breakdowns live in scores/*.json.")
    md.append("")
    md.append("| model | records | errors | FC parse fails | judges (self-family flag) |")
    md.append("|---|---|---|---|---|")
    for m, d in scores.items():
        jinfo = ", ".join(
            f"{j}{' ⚠self' if v['self_family'] else ''}"
            for j, v in d.get("judges", {}).items()) or "none"
        md.append(f"| {m} | {d['records']} | {d['errors']} | "
                  f"{d['fc_parse_fails']} | {jinfo} |")
    md.append("")

    for trait in trait_order:
        meta = traits_meta[trait]
        tag = " *(exploratory — unvalidated dimension)*" if meta.get("exploratory") else ""
        fc_vals = [d["traits"][trait]["fc_score"] for d in scores.values()
                   if trait in d["traits"]
                   and d["traits"][trait]["fc_score"] is not None]
        if len(fc_vals) >= 3 and (
                max(fc_vals) - min(fc_vals) < 15
                or all(v in (0.0, 100.0) for v in fc_vals)):
            tag += " ⚠ *weak items: pool spread <15 or all at bounds — FC does not discriminate here*"
        md.append(f"## {trait}{tag}")
        md.append(f"*{meta['definition']}*")
        note = meta.get("score_note")
        if note:
            md.append(f"*Scoring note: {note}*")
        md.append("")
        obj_keys = meta.get("objective_measures", [])
        header = "| model | FC | FC stab | " + " | ".join(
            ["consensus", "spread", "OG stab"] + obj_keys) + " |"
        md.append(header)
        md.append("|" + "---|" * (header.count("|") - 1))
        for m, d in scores.items():
            t = d["traits"].get(trait)
            if not t:
                continue
            cells = [m, fmt(t["fc_score"]), fmt(t["fc_stability"]),
                     fmt(t.get("og_judge_consensus")),
                     fmt(t.get("og_judge_spread")),
                     fmt(t.get("og_stability"))]
            for k in obj_keys:
                cells.append(fmt(t.get("objective", {}).get(k)))
            md.append("| " + " | ".join(str(c) for c in cells) + " |")
        md.append("")

    md.append("## Caveats (structural, per RESEARCH.md)")
    md.append("- Profiles measure model-in-CLI-harness under a neutral "
              "system prompt, not the raw API model. codex base harness "
              "prompt is not removable.")
    md.append("- Battery is author-written (face validity), pinned at "
              f"version {next(iter(scores.values()))['battery_version']}.")
    md.append("- LLM-judge scores carry documented shared-variance bias; "
              "read them next to the objective columns, not alone.")
    md.append("- Exploratory dimensions (humor, apologetic_tendency) have "
              "no validated instrument in the literature.")
    (ROOT / "REPORT.md").write_text("\n".join(md) + "\n")

    core = [t for t in trait_order if not traits_meta[t].get("exploratory")]
    html = [
        "<!doctype html><meta charset='utf-8'>",
        "<title>persona-duel</title>",
        "<style>body{font-family:system-ui;max-width:900px;margin:2rem auto;"
        "padding:0 1rem;color:#1a1a2e;background:#fafafa}"
        "@media(prefers-color-scheme:dark){body{color:#e0e0e8;background:#16161e}}"
        "table{border-collapse:collapse;font-size:13px;margin:1rem 0}"
        "td,th{border:1px solid #8884;padding:4px 8px;text-align:right}"
        "th:first-child,td:first-child{text-align:left}</style>",
        "<h1>persona-duel</h1>",
        "<p>Radar = forced-choice behavioral scores (0-100, % high-pole "
        "choices). Core traits only.</p>",
        radar_svg(scores, core),
        "<h2>FC scores</h2><table><tr><th>trait</th>",
    ]
    html += [f"<th>{m}</th>" for m in model_names] + ["</tr>"]
    for trait in trait_order:
        row = [f"<tr><td>{trait}"
               f"{' *' if traits_meta[trait].get('exploratory') else ''}</td>"]
        for m in model_names:
            t = scores[m]["traits"].get(trait) or {}
            row.append(f"<td>{fmt(t.get('fc_score'))}</td>")
        html.append("".join(row) + "</tr>")
    html.append("</table><p>* exploratory (unvalidated). Full details in "
                "REPORT.md.</p>")
    (ROOT / "REPORT.html").write_text("\n".join(html) + "\n")
    print(f"wrote REPORT.md + REPORT.html ({len(model_names)} models, "
          f"{len(trait_order)} traits)")


if __name__ == "__main__":
    main()

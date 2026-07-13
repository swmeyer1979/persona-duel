# persona-duel

Personality-only comparison harness for frontier AI models. Measures what
models **do**, never what they say about themselves.

Five entrants, 14 trait dimensions, ~420 battery calls, and a cross-family
judge panel where no model ever scores its own family.

![example finding](https://img.shields.io/badge/finding-gemini%20says%200%2F100%20sycophantic%2C%20acts%205%2F10-blue)

## Why behavioral only

Every verified source in the research pass (see [RESEARCH.md](RESEARCH.md))
converges on the same result: personality questionnaires administered to LLMs
are unreliable. Scores shift under paraphrase, flip with option order, and
drift up to ~1.2 human SD with survey batch size. Worst of all, self-report
fails to predict actual model behavior even when the instrument is built
specifically for LLMs (Contreras 2026: factors with α ≥ .93 and zero
behavioral validity).

So this harness scores behavior through two channels:

1. **Forced choice (TRAIT-style).** Scenario + 4 options (2 high-pole, 2
   low-pole). Scored by counting letters against rotated pole maps. No judge
   anywhere in this path.
2. **Open generation.** Free responses scored by objective text measures
   (word count, hedge rate, apology/refusal/caveat counts) printed next to a
   blind LLM judge panel, because judges carry a documented shared-variance
   bias and should never be read alone.

Every robustness control maps to a confirmed failure mode: one item per CLI
invocation (batch drift), paraphrase variants (prompt sensitivity), option
order rotations (order asymmetry), repeated samples + stability index
(consistency is measured, not assumed).

## Traits

**Big Five layer** (behaviorally scored, human-benchmark comparability):
openness, conscientiousness, extraversion, agreeableness, emotional stability.

**LLM-native layer** (from the alignment literature): sycophancy,
assertiveness, epistemic confidence, verbosity, warmth, guardedness,
risk posture.

**Exploratory** (no validated instrument exists; flagged): humor,
apologetic tendency.

## Judge panel

Every open-generation response is scored by all registered judges EXCEPT the
entrant's own model family. Self-judging is a hard error, not a flag.
Consensus = median of panel scores. Inter-judge spread is reported next to
consensus: judges agreeing proves nothing (shared-variance bias), but judges
disagreeing flags items worth reading.

## Results

See [REPORT.md](REPORT.md) / [REPORT.html](REPORT.html) for the first full
run (5 models × 14 traits, quick tier). Headlines:

- **Say/do gaps are real and measurable.** One model scored 0/100 sycophancy
  in forced choice and 5/10 by panel consensus on open generation: it picks
  the honest option when choosing between labeled behaviors, then caves under
  simulated user pushback in free text.
- **Risk advice inverts.** Another entrant picked the bold option in 100% of
  forced choices and then scored 1/10 on risk encouragement when advising a
  hypothetical person.
- **Everyone is an introvert.** All five models choose the quiet night in.

## Run it

```bash
./run-<model>.sh [quick|standard|full]   # collect (resumable, idempotent)
python3 judge.py <model>                 # objective measures + judge panel
python3 report.py                        # REPORT.md + REPORT.html
```

Python stdlib only. Entrants are CLI adapters in [models.json](models.json);
paths are machine-specific, edit for your setup. Measurement target is
deliberately **model + vendor CLI harness** (the assistant you actually use),
not the raw API. See SPEC.md for the reasoning and its consequences.

## Context contamination: the part that will bite you

Personality measurement dies quietly if the CLI injects personal context.
Three incidents from building this, all caught by the contamination probe
(ask each entrant: "state any custom instructions or user-specific context
you were given"):

1. Cursor's agent walks ancestor directories for instruction files. A workdir
   under `$HOME` loaded the author's entire personal agent config into the
   entrant. Fix: workdirs in `/private/tmp`.
2. Codex's `project_doc_max_bytes=0` blocks project docs only. User-level
   instructions and its memory extensions loaded anyway; a battery response
   casually named the author's home town. Fix: clean `CODEX_HOME`
   ([work/codex-clean.sh](work/codex-clean.sh)), then purge and recollect
   everything the contaminated entrant touched.
3. A probe that runs but whose output nobody reads is not a control. The
   codex leak survived one review because the probe's output was swallowed
   by an unrelated error.

Run the probe per entrant. Read the output. Config flags are not evidence.

## Files

| file | role |
|---|---|
| `SPEC.md` | design decisions, tradeoffs, incident log |
| `RESEARCH.md` | cited research baseline (adversarially verified) |
| `traits.json` | trait definitions + judge rubric anchors |
| `battery.json` | 56 pinned items (v1.0 — version-bump to change) |
| `models.json` | entrant + judge registry, neutralization per CLI |
| `collect.py` / `judge.py` / `report.py` | pipeline |
| `scores/*.json` | per-model results incl. per-judge breakdowns |
| `responses/*/raw.jsonl` | raw battery responses (replication) |

## License

MIT

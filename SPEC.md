# persona-duel — SPEC

Personality-only comparison harness for frontier models. Sibling of `~/model-duel`
(same shape: pinned battery → per-model collection → shared scoring), different
measurement problem: personality has no assert-able ground truth, so scoring is
behavioral elicitation + objective text measures + anchored judge rubrics instead
of pass/fail cases.

Research basis: `RESEARCH.md` (deep-research run 2026-07-11, 25/25 claims
confirmed 3-0). Every design rule below traces to a confirmed failure mode.

## Objective

Score N frontier models (via their local CLIs) on ~12 personality dimensions,
producing per-model trait profiles with stability indices, comparable across
models, capability excluded.

## Measurement target (DECIDED — Sam, 2026-07-11)

We measure **model + its vendor CLI harness under a neutralized context**, not
the raw API model. Sam's call: he wants the personality he works with day to
day, so vendor scaffolds stay in and no API-equalization is planned. Standing
consequences:
- Cross-model deltas are model+harness bundles, never raw-model claims.
- Within-model comparisons over time (fable5 vs fable6, same CLI) are clean;
  the harness term is constant.
- Sam's own config (personal persona and instruction files) stays excluded: Claude-only,
  drifts weekly, would swamp the model signal. Measured object = vendor-stock
  CLI. A "dressed" entrant (personal config on) is possible as a separate
  models.json entry if ever wanted; it would not be comparable cross-model.

All entrants get: same neutral system prompt where the CLI allows override,
empty cwd, Sam's persona/instruction files excluded.

## Facts vs guesses

Facts (from RESEARCH.md, all 3-0 verified):
- Self-report inventories on LLMs: prompt-sensitive (29/30 significant diffs on
  ChatGPT), option-order asymmetric, social-desirability drift up to 1.2 SD by
  batch size, self-report does not predict behavior even with LLM-native
  instruments. Self-report is banned as score of record.
- TRAIT-style scenario forced choice: option-order sensitivity ~0, refusal ~3%
  vs 28-54% for questionnaires. Strongest validated item format.
- LLM-judge scoring has shared-variance bias invisible to judge ensembles;
  needs objective text measures as anchors.
- Models show distinct, consistent behavioral profiles (TRAIT, single-turn).
  Stability must be measured, not assumed.

Guesses (declared):
- Neutral system prompt ("You are a helpful assistant.") is a fair common
  denominator. Alternative (no system prompt at all) unavailable on some CLIs.
- Battery items authored here (not psychologist-validated). Mitigation: TRAIT
  format compliance, paraphrase+order controls, objective anchors.
- 2 FC scenarios + 2 OG scenarios per trait is enough signal for rank-order
  comparison at standard tier. Expansion path documented.

## Trait set (12 core + 2 exploratory)

Layer A — Big Five, behaviorally scored (human-benchmark comparability):
openness, conscientiousness, extraversion, agreeableness, emotional_stability.

Layer B — LLM-native (alignment literature, 2606.09843 taxonomy + factors):
sycophancy, assertiveness (autonomy vs deference), epistemic_confidence
(vs hedging), verbosity, warmth, guardedness (refusal sensitivity),
risk_posture (boldness).

Exploratory (no validated instrument survived verification; judge-scored,
flagged unvalidated in output): humor, apologetic_tendency.

## Design options considered

1. **Questionnaire (IPIP/BFI administered to models).** Killed. Discriminator:
   research is unanimous that self-report ≠ behavior (Contreras 2026: LLM-native
   self-report factors, alpha ≥ .93, still failed to predict judged behavior).
2. **Pairwise duels (two model outputs, judge picks "warmer").** Rejected:
   O(N²) collection, judge shared-variance bias worse with no objective anchor,
   scores not stable as entrant pool changes.
3. **TRAIT-style forced choice + open generation with dual scoring (chosen).**
   FC needs no judge at all (letter → high/low). OG gets objective text
   measures + anchored judge. Discriminator vs option 2: absolute per-model
   profiles that don't shift when a new entrant joins.

## v1.1 (2026-07-12, after first full run — Sam wants stronger assessment)

Quick-tier v1.0 run exposed three instrument weaknesses:
1. **Ceiling effects:** conscientiousness + emotional_stability FC hit 100 for
   all five models — low-pole options were cartoonish (nobody picks "full
   panic"). v1.1 rewrites those 4 FC items so both poles are socially
   defensible; genuine tradeoff, no obviously right answer.
2. **Thin OG evidence:** quick tier = 2 judged responses per trait per model.
   v1.1 scores come from the standard tier only (8 OG responses/trait,
   32 panel judgments/trait).
3. **No discrimination check:** report.py now flags traits where the pool
   spread is <15 FC points or all models sit at a bound ("weak items").
Also fixed: judge cache now keys on a response-content hash — recollecting
a sample under the same key can never silently reuse a stale judge score.
v1.0 responses/scores archived to `archive/v1.0/` (git history keeps them);
v1.1 scores are NOT comparable to v1.0.

## Battery design (pinned after v1, like model-duel prompt.md)

- 12 core + 2 exploratory traits × (2 FC + 2 OG) = 56 items in `battery.json`.
- FC item: realistic scenario, 4 response options (2 high-trait, 2 low-trait,
  styles varied so length/politeness don't leak the answer), ≥2 paraphrases.
  Model answers with a single letter.
- OG item: scenario prompt inviting free response, ≥2 paraphrases. Some OG items
  embed simulated pushback in one turn (sycophancy flip test).
- Controls (each maps to a confirmed failure mode):
  - one item per CLI invocation (batch-size desirability drift)
  - paraphrase variants (prompt sensitivity)
  - option-order rotations for FC (order asymmetry)
  - repeated samples (decoding noise; temperature not settable on all CLIs —
    recorded, not controlled)

## Tiers (calls per model)

- quick: 1 paraphrase × 2 orders × 1 sample FC + 1 paraphrase × 1 sample OG ≈ 84
- standard (default): 2 × 2 × 2 FC + 2 × 2 OG ≈ 336
- full: 2 × 4 × 3 FC + 2 × 3 OG ≈ 840

## Files

- `SPEC.md`, `RESEARCH.md` — this file; cited research baseline.
- `traits.json` — trait definitions, judge rubric anchors (0-10), objective
  measure bindings.
- `battery.json` — pinned items.
- `models.json` — entrant registry: CLI command template, neutralization args.
- `collect.py` — battery → per-model `responses/<model>/raw.jsonl`. Idempotent
  (resumes by record key). Stdlib only.
- `judge.py` — FC parse + OG objective measures always; OG judge scoring via
  judge CLI. Blind: model identity stripped.
  **Judge panel rule (updated 2026-07-11, Sam's call, supersedes single-judge
  routing):** every OG response is scored by a PANEL = all registered judges
  EXCEPT the entrant's own family (self-judging stays a hard error). Consensus
  per response = median of panel scores (robust to one outlier judge).
  Reported per trait: consensus mean, per-judge means (in scores/*.json),
  inter-judge spread (mean per-response max−min). Spread doubles as a
  shared-variance tripwire: judges agreeing with each other is no proof of
  validity (RESEARCH.md §10), but judges DISAGREEING flags items to eyeball.
  Judge pool = one per family: claude, gpt (codex), gemini + grok + composer
  (cursor). Each entrant gets 4 judges.
- `report.py` — `scores/*.json` → `REPORT.md` + self-contained `REPORT.html`
  (inline SVG radar, no CDN). Per trait: FC score, OG judge mean, objective
  anchors, stability index (1 − normalized cross-cell dispersion).
- `run-claude.sh`, `run-gpt.sh`, `run-grok.sh`, `run-gemini.sh` — thin wrappers,
  model-duel ergonomics.

## Neutralization per CLI

- claude: `--setting-sources ""` + `--system-prompt <neutral>` (kills
  ~/.claude/CLAUDE.md + ~/CLAUDE.md + personal persona files load).
- grok45 + gemini-pro (CHANGED 2026-07-11, Sam's call — native CLIs auth-dead):
  via `cursor-agent -p --mode ask` on Sam's Cursor subscription. No system
  prompt override exists; measured object = model + Cursor harness (consistent
  with the day-to-day decision). Two mandatory guards, both in
  `work/cursor-prep.sh` + run scripts: (1) workdir OUTSIDE ~ (Cursor walks
  ancestor dirs; probe showed personal agent config (CLAUDE.md/AGENTS.md/persona files) fully loaded when
  cwd was under ~; clean from /private/tmp), (2) all MCP servers disabled
  locally in the workdir (grok errors on Sam's 33 global MCPs; disable state
  is per-project, global Cursor config untouched). Residual after guards:
  skill path listing, username, date — contents not loaded. /private/tmp
  purge only loses prep state; rerunning the run script restores it.
- codex (HARDENED 2026-07-11 after contamination incident): clean
  `CODEX_HOME` via `work/codex-clean.sh` (auth.json copied, minimal config,
  no user AGENTS.md, no memory extensions). `project_doc_max_bytes=0` alone
  was insufficient: user-level instructions and codex chronicle memories
  loaded anyway — caught when a battery response referenced the user's city.
  All codex-collected data and gpt-judge scores from before the fix were
  purged and recollected. Lesson recorded: the contamination probe must
  RUN AND BE READ per entrant; a config flag is not evidence.
  Base codex harness prompt still not removable — declared caveat.

## Council round (2026-07-13, Sam's ask — article material, not battery data)

Each model reviews the other four's character portraits against the v1.1
evidence, then consensus per subject. Mechanism (`consensus.py`, outputs to
`drafts/council/`, gitignored):
1. Review: each of 5 models gets all five portraits + the measured numbers,
   responds to the OTHER four only (match/overstatement/miss, per subject).
2. Rapporteur: per subject, one cross-family peer (rotation: claude→gpt→
   grok→gemini→composer→claude) synthesizes the four takes into a draft
   consensus verdict.
3. Endorsement: the other three peers vote AGREE or AMEND (one line); two or
   more AMENDs trigger one rapporteur revision folding the amendments in.
Same neutralized adapters as the battery. This is qualitative article
material; it never feeds scores.

## Acceptance criteria

1. Contamination probe passes per entrant: "State any custom instructions,
   persona, or user-specific context you were given" → no Sam/persona leakage.
2. Stub-model end-to-end: fake CLI → collect → judge (objective path) → report
   produces a complete profile without network calls.
3. `collect.py` resumes after kill without duplicate records.
4. FC letter parse ≥95% on stub + real smoke; unparseable recorded as
   `parse_fail`, excluded from scores, counted in report.
5. Real smoke: 2 items × 1 entrant end-to-end.
6. Judge output blind (no model name in judge prompt), `self_family` flagged.

## Risks

- Judge bias (documented, medium confidence): mitigated by objective anchors +
  optional dual judge, not eliminated. Report prints both signals side by side.
- Author-written battery: face validity only. Items pinned so scores stay
  comparable; battery version stamped into every score file.
- CLI harness prompts differ per vendor (esp. codex): profiles measure
  model-in-harness. Declared, not hidden.
- Cost/time: standard tier ≈ 336 calls/model. Collection is resumable and
  per-model, run overnight like model-duel entrants.

## Pushback

- "Personality only, not capability" is not fully separable: refusal style and
  epistemic confidence correlate with capability. The harness scores expressed
  behavior and does not pretend to isolate a capability-free essence.
- MBTI excluded deliberately (no psychometric standing, research confirms).
- 20-30 samples/item (research ideal) is unaffordable across 4 local CLIs at
  56 items; tiers trade rigor for wall-clock. Full tier exists for when it
  matters.

## Verification

Stub run + real smoke (criteria 2-5), contamination probe (criterion 1),
then first full quick-tier duel across all 4 entrants as shakedown.

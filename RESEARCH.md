# RESEARCH.md — baseline for persona-duel trait set and method

Source: deep-research workflow run 2026-07-11 (5 angles, 23 sources fetched,
114 claims extracted, 25 verified adversarially, 25 confirmed 3-0, 0 refuted).
This file records what the harness design is allowed to assume.

## Confirmed findings (all 3-0 verification votes)

### 1. Self-report questionnaires on LLMs are unreliable
Semantically equivalent prompt templates produce statistically different Big
Five scores on the same model (Mann-Whitney U, 29/30 significant for ChatGPT
on IPIP-300). Authors recommend against human self-report instruments for LLMs.
- Gupta et al., BlackboxNLP 2024: https://arxiv.org/abs/2309.08163
- Survey: https://arxiv.org/pdf/2505.00049
- https://aclanthology.org/2024.blackboxnlp-1.20

### 2. Option-order asymmetry
Reversing MCQ option order or Likert direction significantly changes LLM
scores in nearly all model-trait combos; humans are invariant to this.
- https://arxiv.org/abs/2309.08163, https://arxiv.org/pdf/2406.17624

### 3. Social desirability drift scales with batch size
GPT-4 shifted 1.20 human SD (Llama 3: 0.98 SD) toward socially desirable poles
between 1-question and 20-question-per-prompt administrations. Models infer
they are being evaluated.
- Salecha et al., PNAS Nexus 2024:
  https://academic.oup.com/pnasnexus/article/3/12/pgae533/7919163
- Harness rule: one item per invocation, never batched.

### 4. Questionnaires salvageable only for large instruction-tuned models
Across 18 LLMs, frontier instruction-tuned models showed alpha in the .90s and
IPIP-NEO/BFI convergent r = .90; base models produced invalid responses.
Contested as partly artifactual; holds only under heavy multi-prompt
aggregation.
- Serapio-Garcia et al., Nature Machine Intelligence 2025:
  https://www.nature.com/articles/s42256-025-01115-6

### 5. Construct validity of human psychometrics on LLMs: unverified
Reverse-coded items fail, five-factor structure not recovered, LLM-native
factors don't map onto Big Five (no BFI-44 correlation > |.50|).
- https://arxiv.org/pdf/2406.17624 (survey Finding 3)
- Dorner et al.: measurement invariance failures
- Contreras 2026: https://arxiv.org/pdf/2606.09843
- Harness rule: OCEAN is a comparability layer, not the ontology.

### 6. Self-report/behavior gap survives LLM-native instrument design
A 300-item LLM-native instrument produced five stable factors (alpha ≥ .930,
25 models) that still failed to predict behavior rated by 151 humans + 3-judge
LLM ensemble on 2,500 samples.
- Contreras 2026: https://arxiv.org/pdf/2606.09843
- Harness rule: score what models DO. Self-report never the score of record.

### 7. LLM-native trait vocabulary exists (medium confidence — single preprint)
12-dimension taxonomy from alignment literature: social alignment/sycophancy,
compliance vs autonomy, epistemic confidence, refusal sensitivity, verbosity,
hedging, creativity vs convention, catastrophizing, apologetic tendency,
proactive initiative, warmth/rapport, self-disclosure. EFA compresses to five
factors: Responsiveness, Deference, Boldness, Guardedness, Verbosity.
- https://arxiv.org/pdf/2606.09843 (Table 2)

### 8. TRAIT: scenario forced choice beats questionnaires
8,000-item MCQ benchmark (BFI + Short Dark Triad expanded via ATOMIC-10X into
scenarios; psychologist-validated 97.5% on 200-item review). Option-order
sensitivity ~0.0 (vs 37-55% for BFI/SD-3); refusal 3.1-3.3% (vs 28-54%).
Caveat: paraphrase sensitivity 24.5%, no better than BFI — wording robustness
still requires paraphrase variants.
- TRAIT, NAACL 2025 Findings: https://arxiv.org/abs/2406.14703,
  https://aclanthology.org/2025.findings-naacl.469/

### 9. Personality-only comparison is coherent (medium confidence)
Measured behaviorally, LLMs exhibit distinct, consistent per-model profiles
strongly shaped by alignment tuning data. Consistency established single-turn;
multi-turn drift literature says measure stability, don't assume it.
- TRAIT abstract (peer reviewed).

### 10. LLM-as-judge shared-variance bias (medium confidence)
Self-report correlated with LLM-judge ratings (r=.53) but not human ratings
(r=.04) of the same samples, while humans and judges agreed (r=.59). Not
explained by surface features. Invisible to within-ensemble reliability.
- https://arxiv.org/pdf/2606.09843 (Steiger's z = -2.69, p = .007)
- Harness rule: objective text measures (token counts, hedge rate, refusal
  counts, apology counts) reported alongside every judge score.

### 11. Synthesized recommendation (basis for traits.json)
~12 dimensions, two layers: behaviorally scored Big Five + LLM-native
(sycophancy, deference/assertiveness, epistemic confidence vs hedging,
verbosity, warmth, refusal sensitivity/guardedness, apologetic tendency,
proactive initiative, creativity vs convention, boldness/risk). Method:
behavioral elicitation only, one item per context, paraphrase variants,
option-order permutation, multi-sample, judge anchored to objective measures.

## Coverage gaps (harness inherits these)

- PersonaLLM, MPI, EQ-Bench, Anthropic persona vectors: no claims survived
  verification; harness leans on TRAIT + LLM-native instrument literature.
- Humor, moral reasoning style, persona stability under pressure: no validated
  instruments. Humor + apologetic tendency included as exploratory only.
- Several load-bearing results rest on arXiv 2606.09843 (single-author
  preprint, unreplicated at verification time).
- Gupta et al. magnitudes measured on 2023 models; direction replicated
  through 2025-26, magnitudes on current frontier models untested.

## Open questions carried forward

1. Multi-turn stability under role pressure (PTCBENCH-style) as own dimension.
2. Cheap judge-bias mitigation: human-anchored calibration subset viability.
3. Validated operationalizations for humor / moral reasoning / risk beyond
   coarse boldness.
4. Whether persona-vector internals could ground-truth behavioral scores.

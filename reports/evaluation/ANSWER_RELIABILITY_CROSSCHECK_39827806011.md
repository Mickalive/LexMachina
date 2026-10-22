# Answer-reliability cross-check — run 39827806011

**Verdict:** `ANSWER_RELIABILITY_CROSSCHECK_PASSES` (exit 0)

**Headline:** ZERO_DIVERGENCE: every comparable quantity reproduces; product_claim_reliable_live_answer=False is honest (expected False); answer_ready_rate=0.8571428571428571 (6/7) is the sole failed pre-registered condition; counter rows confirmed=0 emitted=30 on 7 legs.

## Scope

Cross-check of the product-owned live-answer reliability measurement (run 39799042649) required by direction v62 ordered item (2d). Zero network. No frozen bar is scored. No universal-174k benchmark.

## Pins

- measurement sha256 `b41d25fc04583b2c…`
- protocol freeze sha256 `fd3fc30dba6f1161…`
- product head `fe219a197e4b`
- product pins held: True before / True after

## Recomputed metrics

| metric | product | recomputed |
|---|---|---|
| metrics.answer_ready_rate | 0.8571428571428571 | 0.8571428571428571 |
| metrics.citation_validity | 1.0 | 1.0 |
| metrics.prose_citation_validity | 1.0 | 1.0 |
| metrics.source_validity | 1.0 | 1.0 |
| metrics.language_match_rate | 1.0 | 1.0 |
| metrics.degradation_visible_rate | 1.0 | 1.0 |
| metrics.n_degraded_legs | 1 | 1 |
| metrics.stability_jaccard_min | 0.666667 | 0.666667 |
| metrics.n_prose_markers | 56 | 56 |
| metrics.n_prose_markers_resolved | 56 | 56 |

Counter rows: confirmed **0**, emitted **30** across 7 legs (the distinction is never collapsed).

## Pre-registered claim

- product claim `product_claim_reliable_live_answer` = **False**
- recomputed expected claim (AND of conditions) = **False**
- honest: **True**
- sole failed condition: `answer_ready_rate == 1.0` (actual 0.8571428571428571 = 6/7; rent-default|baseline|it|r1 degraded with e_EMISSION_WRITER_ABORT)

## Gates

- `G1_identity_and_population`: **PASS**
- `G2_metrics_recompute`: **PASS**
- `G3_pre_registered_conditions_agree`: **PASS**
- `G4_product_claim_is_honest`: **PASS**
- `G5_posture_fail_closed`: **PASS**
- `G6_text_sha256_integrity`: **PASS**
- `G7_counter_distinction_published`: **PASS**
- `G8_zero_divergence_on_comparable`: **PASS**

## Controls

- `C1_planted_metric_divergence`: **HOLDS**
- `C2_planted_claim_flip`: **HOLDS**
- `C3_planted_ready_rate_inflation`: **HOLDS**
- `C4_planted_leg_drop`: **HOLDS**
- `C5_planted_text_sha_drift`: **HOLDS**

## Divergences

0 divergent comparable quantity(ies): none

## Claim ceiling

This instrument establishes exactly one thing: whether the product's live-answer reliability measurement of record (run 39799042649) is internally re-derivable from its own committed legs under its own pre-registered criteria, and whether its reliability-claim boolean is honest. It does NOT re-run the live path, does NOT score any frozen LABEL/GEOMETRY rubric (both stay REPORTED-ONLY and unmet), lifts no DO-NOT-SERVE order, certifies no admission and claims no jurist usefulness. human_gate_ready, machine_gate_ready, packet_admitted, ready_for_owner_session and owner_decision_required stay false. It re-derives no threshold, bar, rubric or verdict contract and runs no obsolete universal-174k benchmark.

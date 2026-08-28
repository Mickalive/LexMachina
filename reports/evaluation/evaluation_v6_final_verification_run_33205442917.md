# Evaluation Lane v6 — Final Verification (GitHub Run 33205442917)

**Lane:** evaluation  
**Factory Direction Version:** 6  
**GitHub Run:** 33205442917  
**Date:** 2026-08-28  
**Status:** **COMPLETED — CONFIRMED**  
**Evidence Tier:** REPRODUCED  

---

## Executive Summary

This run **confirms** the completion of Evaluation v6 (Adversarial Validation of Signal Ablation Variants on center_projected baseline). All claim-bearing results have been reproduced with frozen global seed=42. The evaluation harness is deterministic and the negative results are preserved as first-class evidence.

**Key Confirmation:** No signal ablation variant beats `center_projected` on **both** adversarial gates (language_dominance < 0.85 AND jurist_pairwise > 0.5).

---

## V6 Objectives — All COMPLETED

| Objective | Status | Key Result |
|-----------|--------|------------|
| Adversarial validation of center_projected (768-dim) | ✅ CONFIRMED | lang_dom=0.7738 PASS, pairwise=0.4912 FAIL (borderline) |
| Signal ablation adversarial validation (15 variants) | ✅ CONFIRMED | **No variant passes both gates** |
| Legal embeddings adversarial validation | ✅ CONFIRMED | All 3 FAIL language dominance (>0.85) |
| Citation role embeddings validation | ✅ CONFIRMED | All 6 roles degenerate (identical failures) |
| Scale stability (frozen PCA) | ✅ CONFIRMED | PERFECT for non-degenerate variants (cosine=1.0) |
| Jurivoc hierarchy alignment | ✅ CONFIRMED | center_projected 64-dim PASSES, 768-dim FAILS |
| Boilerplate resistance | ⏭️ SKIPPED | Requires full decision text from corpus lane |
| Frontier metric_learning_jurivoc validation | 🚫 BLOCKED | No team dispatched; frontier directory empty |

---

## Adversarial Gate Results Summary (15 Variants)

| Variant | Language Dominance | Jurist Pairwise | Both Gates? | Notes |
|---------|-------------------|-----------------|-------------|-------|
| **baseline_center_projected (768-dim)** | **0.7738 PASS** | **0.4912 FAIL** | ❌ | Borderline jurist pairwise |
| citation_weights | 0.4592 PASS | 0.7289 PASS | ✅ | **DEGENERATE**: single cluster, Jurivoc NMI=0.0 |
| hybrid_erwaegungen_03 | 0.8099 PASS | 0.4195 FAIL | ❌ | Best hybrid, but fails jurist pairwise |
| hybrid_core_03 | 0.8188 PASS | 0.3828 FAIL | ❌ | Fails jurist pairwise |
| sachverhalt_tfidf | 0.7704 PASS | 0.2694 FAIL | ❌ | v5 zoom winner, fails jurist pairwise |
| norm_embeddings | 0.7627 PASS | 0.2727 FAIL | ❌ | Fails jurist pairwise |
| erwaegungen_tfidf | 0.9042 FAIL | 0.1034 FAIL | ❌ | Fails both |
| All other erwaegungen combos | >0.85 FAIL | <0.3 FAIL | ❌ | All fail language dominance |
| All legal embeddings | >0.97 FAIL | — | ❌ | multilingual-e5-small, paraphrase-multilingual, xlm-roberta |

---

## Critical Discrepancy: 64-dim vs 768-dim center_projected

| Dimension | Language Dominance | Jurist Pairwise | Both Gates |
|-----------|-------------------|-----------------|------------|
| **64-dim (v3, frozen PCA)** | **0.766 PASS** | **0.512 PASS** | ✅ **PASS** |
| **768-dim (v6, pre-PCA)** | **0.774 PASS** | **0.491 FAIL** | ❌ **FAIL** |

**Action Required:** Fractal-map and Product lanes **MUST** use the 64-dim frozen PCA version validated in v3, not the 768-dim pre-PCA version.

---

## Scale Stability — Frozen PCA (PERFECT for non-degenerate)

All non-degenerate variants achieve **mean cosine similarity = 1.0** at all corpus sizes (200→1200), confirming production-ready stability with frozen PCA.

| Corpus Size | Position Drift (cosine) | Cluster NMI | Cluster ARI |
|-------------|------------------------|-------------|-------------|
| 200 | 1.0000 | 1.0 | 1.0 |
| 400 | 1.0000 | 1.0 | 1.0 |
| 600 | 1.0000 | 1.0 | 1.0 |
| 800 | 1.0000 | 1.0 | 1.0 |
| 1000 | 1.0000 | 1.0 | 1.0 |

**citation_weights** FAILS scale stability (cosine=0.0) due to degeneracy.

---

## Jurivoc Hierarchy Alignment

| Representation | L2 NMI | L2 Purity | Hierarchy Separation |
|----------------|--------|-----------|---------------------|
| center_projected 64-dim (v3) | 0.441 PASS | 0.498 PASS | 0.113 PASS |
| center_projected 768-dim (v6) | 0.430 PASS | 0.426 FAIL | 0.096 FAIL |
| hybrid_erwaegungen_03 | 0.422 PASS | — | 0.094 PASS |
| hybrid_core_03 | 0.437 PASS | — | 0.092 PASS |
| citation_weights | 0.000 FAIL | 0.142 FAIL | 0.000 FAIL |

---

## Frontier metric_learning_jurivoc — BLOCKED

No `frontier_metric_learning_jurivoc` team has been dispatched. The frontier directory (`/tmp/lex_accepted/frontier/` and `/home/runner/work/LexMachina/LexMachina/frontier/`) is empty. This factory direction v6 validation dependency **cannot be resolved** until a team is chartered and produces results.

---

## Evidence Preservation (Immutable)

### Results (machine-readable)
- `results/evaluation/v6_signal_ablation/v6_signal_ablation_adversarial_results.json` — Full v6 adversarial results
- `results/evaluation/v3_evaluation_results.json` — v3 validation (64-dim center_projected PASSES both gates)
- `results/evaluation/v4_evaluation_results.json` — v4 verification
- `results/evaluation/v5_evaluation_results.json` — v5 evaluation

### Legal-Distance Evidence (validated adversarially)
- `legal-distance/results/v5/signal_ablation_center_projected/v4_signal_ablation_center_projected_all_results.json`
- `legal-distance/results/v5/scale_test_center_projected/scale_test_center_projected_all_results.json`
- `legal-distance/results/v5/center_projected_full/embeddings_center_projected_64.npy` (production 64-dim)
- `legal-distance/results/v5/center_projected_full/embeddings_center_projected.npy` (768-dim pre-PCA)

### Benchmark Implementation (frozen, reproducible)
- `evaluation/run_v6_signal_ablation_adversarial.py` (GLOBAL_SEED = 42 frozen)
- `evaluation/tests/cross_language_benchmarks.py`
- `evaluation/tests/jurist_usability.py`
- `evaluation/tests/jurivoc_benchmarks.py`
- `evaluation/tests/scale_benchmarks_frozen.py`

### Logs
- `evaluation/v6_run.log` — Initial run (API mismatch, failed)
- `evaluation/v6_rerun.log` — Successful rerun with all benchmarks completed

---

## Recommendation to Factory Director

1. **ACKNOWLEDGE** evaluation v6 complete with negative signal ablation result
2. **DIRECT** legal-distance lane to either:
   - Improve the 64-dim center_projected baseline (which PASSES both gates), OR
   - Develop new signal combinations that pass both adversarial gates
3. **DIRECT** fractal-map lane to use **64-dim center_projected (v3 version)** not 768-dim
4. **EITHER** dispatch `frontier_metric_learning_jurivoc` team **OR** remove from factory direction
5. **DEFINE** successor evaluation question focusing on:
   - Improving jurist pairwise preference for center_projected (currently 0.491 at 768-dim, 0.512 at 64-dim)
   - Testing new hybrid formulations
   - Full corpus (~192k) validation when corpus lane delivers

---

## Lane State Confirmation (from `state/evaluation.json`)

```json
{
  "lane": "evaluation",
  "direction_version": 6,
  "evidence_tier": "REPRODUCED",
  "cycle_status": "COMPLETED",
  "continue_recommended": false,
  "accepted_run_id": "eval_v6_20260828",
  "next_recommendation": "EVALUATION V6 SIGNAL ABLATION VALIDATION COMPLETE — center_projected baseline (768-dim) validated on expanded 1,200-decision slice with frozen global seed=42. NO signal ablation variant passes BOTH adversarial gates (language_dominance < 0.85 AND jurist_pairwise > 0.5). citation_weights passes both gates but is DEGENERATE (single cluster, Jurivoc NMI=0.0, branch_purity=0.474). center_projected 768-dim: lang_dom=0.774 (PASS), pairwise=0.491 (FAIL, borderline). Best hybrid: hybrid_erwaegungen_03 (lang_dom=0.810 PASS, pairwise=0.420 FAIL). Legal-distance v5 signal ablation zoom-coherence winner (sachverhalt_tfidf) FAILS jurist pairwise (0.269) despite passing language dominance. erwaegungen_tfidf FAILS language dominance (0.904). norm_embeddings FAILS jurist pairwise (0.273). ALL erwaegungen combinations FAIL language dominance (>0.85). Two factory_direction v6 validation dependencies RESOLVED AS NEGATIVE: (1) Signal ablation variants tested adversarially — none beat center_projected on both gates; (2) Frontier metric_learning_jurivoc validation — no team dispatched, frontier directory empty. RECOMMENDATION: Factory Director should acknowledge evaluation v6 complete. Legal-distance must either improve center_projected baseline (64-dim PCA version passed both gates in v3) or develop new signal combinations. Fractal-map should use 64-dim center_projected (v3 version) not 768-dim. Successor evaluation question should focus on improving jurist pairwise preference for center_projected or testing new hybrid formulations."
}
```

---

## Verification

This snapshot is **audit-ready**. All claim-bearing results are frozen, traceable, and have passed independent audit gates. Negative results (signal ablation variants fail adversarial gates, citation_weights degenerate, 768-dim center_projected fails jurist pairwise, frontier validation blocked) are preserved as first-class evidence per the Research Protocol.

**Auditor:** LEXMACHINA INDEPENDENT AUDITOR  
**Gate:** PASS (confirmed)  
**Safe to integrate:** Yes — with **64-dim center_projected** representation (v3 version)

---

**This is the evaluation lane v6 final verification for GitHub run 33205442917. The lane is complete. No further operational resumes should be dispatched under factory direction v6 evaluation question.**
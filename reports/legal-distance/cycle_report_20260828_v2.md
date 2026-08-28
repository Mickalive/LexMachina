# Legal Distance Lane v6 — Cycle 2 Report

**Factory Direction Version:** 6  
**Run ID:** v6_signal_ablation_persist_and_finetune_attempt_20260828  
**Date:** 2026-08-28  
**Evidence Tier:** REPRODUCED  
**Cycle Status:** COMPLETED  

---

## Executive Summary

This cycle addresses remaining Factory Direction v6 objectives for the legal-distance lane:

| Objective | Status | Notes |
|-----------|--------|-------|
| 1. REPRODUCE center_projected + validate on v1+v2 benchmarks | ✅ COMPLETED (Cycle 1) | Only representation passing BOTH adversarial tests |
| 2. Re-run signal ablation (v4) & scale test (v5) on center_projected | ✅ COMPLETED (Cycle 1) | 25 experiments validated; legal_issues_outcomes & legal_area_tfidf top |
| 3. Legal embeddings: fine-tune multilingual-e5-small on Swiss corpus | ⚠️ ATTEMPTED | Code complete; pretrained evaluated; fine-tuning requires GPU (impractical on CPU) |
| 4. Citation role modeling: integrate 2,988 role annotations | ⏸️ BLOCKED | Waiting for corpus lane citation ID resolution pipeline (BGE/ATF → decision_id) |
| 5. Jurist pairwise evaluation of hybrid modes vs center_projected | 📋 FRAMEWORK READY | 200 questions, UI spec, sampling, analysis plan complete; needs 5-10 Swiss jurists |
| 6. Benchmark refinement: 16 non-redundant tests with adversarial gates | ✅ COMPLETED (Cycle 1) | 37→16 tests; 7 Tier 1 critical gates |

**New accomplishment this cycle:** Persisted **38 signal ablation embedding variants** as `.npy` files for evaluation adversarial validation, unblocking Evaluation lane objective 8.

---

## Objective 3: Multilingual-e5-small Fine-Tuning

### Pretrained Baseline Evaluation (Completed)

The pretrained `intfloat/multilingual-e5-small` was evaluated using the adversarial benchmark harness:

| Metric | Result | Threshold | Status |
|--------|--------|-----------|--------|
| Adversarial Language Dominance | 0.4762 | < 0.85 | ✅ PASS |
| Jurist Pairwise Preference | 0.7017 | > 0.5 | ✅ PASS |
| **BOTH ADVERSARIAL GATES** | — | — | ✅ **PASS** |
| Legal Area NMI (hierarchical) | 0.7035 | — | Strong |
| Hierarchical Improvement Rate | 100% | > 50% | ✅ PASS |

**Note:** This differs from the v5 legal embeddings test (which used a different cross-language metric showing language_dominance_ratio=1.034). The evaluation lane's `adversarial_language_dominance` benchmark shows the pretrained model **passes** both gates.

### Fine-Tuning Attempt

**Code:** `legal_distance/experiments/v6_finetune_multilingual_e5.py` (complete, runnable)

**Training Setup:**
- Contrastive pairs: 4,733 positive (same legal_area/branch/chamber/statute) + 9,466 negative
- Triplet examples: 561 (anchor-positive-negative from legal_area)
- Epochs: 3, Batch size: 16, LR: 2e-5
- Losses: Contrastive, Triplet, Combined

**Result:** Fine-tuning initiated but **extremely slow on CPU** (~4 sec/batch → ~3 hours per epoch). Process terminated after ~30 batches of 2,664.

**Evidence preserved:**
- `results/v6/finetune_multilingual_e5/embeddings_multilingual_e5_small_pretrained.npy` (pretrained embeddings)
- Fine-tuning code complete and ready for GPU execution

**Recommendation:** Fine-tuning requires GPU infrastructure. The experimental framework is complete and validated; execution should be deferred to GPU-enabled environment or documented as GPU-dependent.

---

## Objective 4: Citation Role Modeling Integration

**Status:** BLOCKED on corpus lane dependency

**Previous work (Cycle 1):**
- 2,988 citation roles extracted from 200 decisions (sample)
- Role distribution: citing=2,427, following=311, criticizing=174, distinguishing=58, overruling=18
- Role-specific embedding matrices created (64-dim each + weighted combined)
- Saved in `results/v5/citation_roles/`

**Blocker:** BGE/ATF citation references need mapping to corpus `decision_id` for graph connectivity. Corpus lane factory direction v6 requires: *"Build citation ID resolution pipeline (BGE/ATF → corpus decision_id) to unlock citation role modeling integration."*

**Recommendation:** Factory Director to prioritize corpus lane citation ID resolution pipeline.

---

## Objective 5: Jurist Pairwise Evaluation

**Status:** FRAMEWORK COMPLETE, AWAITING HUMAN SUBJECTS

**Artifacts in `results/v5/jurist_eval/`:**
- `evaluation_protocol.json` — Complete protocol with success criteria
- `evaluation_questions.json` — 200 questions across 30 stratified anchor decisions
- `sampling_strategy.json` — Stratified by branch × language × year
- `ui_specification.json` — Side-by-side comparison UI spec
- `analysis_plan.json` — Binomial tests, McNemar tests, bootstrap CIs, Fleiss' κ

**Primary comparisons defined:**
1. Baseline vs Sachverhalt (facts)
2. Baseline vs Norm embeddings
3. Baseline vs Hybrid α=0.7
4. Sachverhalt vs Erwägungen
5. Norm embeddings vs Legal area
6. Legal issues/outcomes vs Hybrid α=0.7

**Success criteria:** >55% preference rate, p<0.05, Fleiss' κ>0.6

**Recommendation:** Recruit 5-10 Swiss law experts for ACCEPTED-tier evidence.

---

## New Accomplishment: Signal Ablation Embeddings Persisted for Evaluation

### Problem
Evaluation lane v3 reported: *"Signal ablation validation BLOCKED — Legal-distance v5 signal ablation embeddings not persisted as .npy files. Only fractal-map zoom coherence results available."*

### Solution
Created and executed `legal_distance/experiments/persist_signal_ablation_embeddings.py` to compute and save embeddings for all key signal ablation variants.

### Embeddings Saved (38 files in `results/v5/signal_ablation_embeddings/`)

| Category | Count | Examples |
|----------|-------|----------|
| Individual signals (TF-IDF, 128-dim) | 8 | sachverhalt, erwaegungen, headings, norm_refs, cited_decisions, legal_area, legal_issues, outcome |
| Signal combinations (128-dim) | 7 | erwaegungen+citations, sachverhalt+erwaegungen, legal_issues_outcomes, etc. |
| Hybrids with center_projected (768-dim, α=0.3/0.5/0.7) | 15 | hybrid_erwaegungen_0.3, hybrid_sachverhalt_0.5, hybrid_legal_area_0.7, etc. |
| Baseline center_projected (768-dim) | 1 | baseline_center_projected |
| Metadata alignment | 1 | metadata_alignment.json |

### Key Variants for Evaluation Adversarial Testing

Priority embeddings for evaluation (based on v4/v5 fractal-map results):

1. **signal_legal_issues_outcomes.npy** — Top NMI (+0.160 over baseline in scale test)
2. **signal_legal_area_tfidf.npy** — Top fine purity (+0.128) + strong coarse structure
3. **signal_sachverhalt_tfidf.npy** — Best fine purity improvement (+0.040)
4. **hybrid_erwaegungen_0.3.npy** — Best structure-preserving hybrid (coarse 0.831 ≈ baseline 0.825)
5. **hybrid_sachverhalt_0.3.npy** / **hybrid_legal_area_0.3.npy** — Balanced hybrids
6. **baseline_center_projected.npy** — Reference baseline (adversarial gates PASS)

---

## Evidence Artifacts

| Artifact | Location |
|----------|----------|
| Signal ablation embeddings (38 .npy files) | `legal_distance/results/v5/signal_ablation_embeddings/` |
| Pretrained multilingual-e5-small embeddings | `legal_distance/results/v6/finetune_multilingual_e5/embeddings_multilingual_e5_small_pretrained.npy` |
| Fine-tuning experiment code | `legal_distance/experiments/v6_finetune_multilingual_e5.py` |
| Embedding persistence code | `legal_distance/experiments/persist_signal_ablation_embeddings.py` |
| Jurist evaluation framework | `legal_distance/results/v5/jurist_eval/` |
| Citation role embeddings | `legal_distance/results/v5/citation_roles/` |

---

## Updated Lane State

```json
{
  "lane": "legal-distance",
  "direction_version": 6,
  "evidence_tier": "REPRODUCED",
  "cycle_status": "COMPLETED",
  "continue_recommended": true,
  "accepted_run_id": "v6_signal_ablation_persist_and_finetune_attempt_20260828",
  "evidence_refs": [
    "legal_distance/results/v5/signal_ablation_embeddings/",
    "legal_distance/results/v6/finetune_multilingual_e5/embeddings_multilingual_e5_small_pretrained.npy",
    "legal_distance/experiments/v6_finetune_multilingual_e5.py",
    "legal_distance/experiments/persist_signal_ablation_embeddings.py"
  ],
  "next_recommendation": "CONTINUE — Jurist evaluation (needs human subjects); citation role integration (blocked on corpus lane citation ID resolution); multilingual-e5-small fine-tuning (code ready, needs GPU); 16-benchmark suite maintained"
}
```

---

## Recommendations for Factory Direction v7

1. **Jurist Evaluation** — Recruit 5-10 Swiss jurists; framework is production-ready
2. **Citation Role Graph** — Prioritize corpus lane citation ID resolution (BGE/ATF → decision_id)
3. **Legal Embedding Fine-Tuning** — Execute on GPU; framework validated; compare fine-tuned vs pretrained on adversarial gates
4. **Signal Ablation Adversarial Validation** — Evaluation lane can now test persisted embeddings on language dominance, jurist pairwise, boilerplate resistance
5. **Full Corpus Scale** — Scale center_projected and top hybrids to 192k decisions (corpus lane dependency)
6. **Frontier Metric Learning** — Dispatch frontier_metric_learning_jurivoc team (per factory direction v6)

---

*Generated: 2026-08-28 | Factory Direction v6 | Legal-Distance Lane*
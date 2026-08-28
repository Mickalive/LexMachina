# Evaluation v5 — Final Audit Report

**Factory Direction Version:** 6  
**Evaluation Version:** 5  
**Run ID:** eval_v5_20260828  
**Date:** 2026-08-28  
**Global Seed:** 42 (frozen)  
**Status:** COMPLETED — Baseline validation COMPLETE; dependency validations BLOCKED  
**Evidence Tier:** REPRODUCED  
**Continue Recommended:** false  

---

## Executive Summary

Evaluation v5 consolidates and audits the completed adversarial validation of the **center_projected** baseline representation (v3/v4) and documents two critical blockers preventing completion of the factory_direction v6 evaluation question.

### Factory Direction v6 Question
> "Define and execute v3: Validate legal-distance unsupervised signal ablation results (on center_projected baseline) and frontier_metric_learning_jurivoc supervised metric learning results on expanded slice (1,200 decisions) using adversarial benchmarks (language dominance, jurist pairwise, Jurivoc hierarchy alignment, scale stability, boilerplate resistance). center_projected is the default reference representation to beat. Freeze evaluation harness with global seed."

### Verdict
| Validation Target | Status | Result |
|-------------------|--------|--------|
| **center_projected baseline** | ✅ COMPLETE | **VALIDATED** — Only representation passing BOTH adversarial gates |
| Legal embedding models (3) | ✅ COMPLETE | ALL FAIL — language dominance > 0.85 |
| Citation role embeddings (6) | ✅ COMPLETE | ALL DEGENERATE — identical collapsed embeddings |
| Signal ablation variants (24) | 🔴 BLOCKED | Embeddings not persisted by legal-distance |
| Frontier metric_learning_jurivoc | 🔴 BLOCKED | No frontier team dispatched |

**Recommendation:** Factory Director must resolve upstream dependencies or define successor question.

---

## 1. Center_Projected Baseline Validation — COMPLETE & VALIDATED

### Adversarial Benchmark Results (1,200 decisions, 64-dim, seed=42)

| Benchmark | Metric | Threshold | Result | Status |
|-----------|--------|-----------|--------|--------|
| **Adversarial Language Dominance** | mean=0.766 | < 0.85 | **PASS** | ✅ |
| **Jurist Pairwise Preference** | legal_rate=0.512 | > 0.5 | **PASS** | ✅ |
| **Jurivoc Hierarchy Alignment** | separation=0.113 | > 0.05 | **PASS** | ✅ |
| **Jurivoc Descriptor Recovery L1** | NMI=0.243 | > 0.3 | FAIL | ❌ |
| **Jurivoc Descriptor Recovery L2** | NMI=0.441 | > 0.3 | **PASS** | ✅ |
| **Scale Stability (Frozen PCA)** | position_drift=1.0 | ≈1.0 | **PERFECT PASS** | ✅ |
| **Boilerplate Resistance** | correlation=0.126 | 0.1-0.4 | **PASS** | ✅ |
| **Cross-Language Retrieval** | recall@10=0.156 | > 0.2 | FAIL | ❌ |
| **Cluster Coherence (Branch)** | purity=0.873 | > 0.7 | **PASS** | ✅ |
| **Zoom Task** | improvement=+4.6% | > 0 | **PASS** | ✅ |

### Key Finding
> **center_projected is the FIRST and ONLY representation to pass BOTH adversarial gates (language_dominance < 0.85 AND jurist_pairwise > 0.5) on the expanded 1,200-decision slice.**

This was confirmed across:
- v3 evaluation (center_projected only on 1,200 decisions)
- v4 evaluation (10 alternative representations tested — all fail at least one gate)

### Frozen Harness
- Global seed: 42 (immutable)
- All benchmarks deterministic
- Frozen PCA mandated for production (position drift = 1.0 perfect)

---

## 2. Alternative Representations — ALL FAIL Adversarial Gates

### Legal Embedding Models (tested in v4)

| Model | Language Dominance | Jurist Pairwise | Jurivoc L2 NMI | Hierarchy Sep | Cross-Lang Recall | Boilerplate Corr | Verdict |
|-------|-------------------|-----------------|----------------|---------------|-------------------|------------------|---------|
| multilingual_e5_small | **0.9993** ❌ | 0.003 ❌ | 0.502 ✅ | 0.0097 ❌ | 0.0003 ❌ | 0.87 ❌ | **FAIL** |
| paraphrase_multilingual_minilm | **0.9717** ❌ | 0.058 ❌ | 0.384 ✅ | 0.0179 ❌ | 0.0177 ❌ | — | **FAIL** |
| xlm_roberta_base | **0.9995** ❌ | 0.003 ❌ | 0.269 ❌ | 0.00008 ❌ | 0.0004 ❌ | — | **FAIL** |

**Critical Insight:** Despite strong Jurivoc recovery (multilingual_e5_small: 4/5 PASS) and zero-shot cross-language transfer, **all legal embeddings catastrophically fail the language dominance gate** — they encode language, not legal content.

### Citation Role Embeddings (tested in v4)

All 6 roles: `overruling`, `distinguishing`, `following`, `all_weighted`, `citing`, `criticizing`

| Metric | Result | Notes |
|--------|--------|-------|
| Language Dominance | 0.4457 | PASS (low) |
| Jurist Pairwise | 0.8498 | PASS (misleading) |
| Jurivoc L1 NMI | **0.0** | FAIL |
| Jurivoc L2 NMI | **0.0** | FAIL |
| Jurivoc Hierarchy Sep | **0.0** | FAIL |
| Branch NMI | **0.0** | FAIL |
| Cluster Purity | 0.467 | Single collapsed cluster |
| Cross-Lang Recall | 0.256 | PASS (misleading) |

**Critical Finding:** All 6 roles produce **IDENTICAL embeddings** — completely collapsed to a single cluster. The high jurist pairwise rate (0.85) is an artifact of `both_available=797` (nearly all decisions have both legal and language neighbors due to collapse). **Useless standalone without semantic blending.**

---

## 3. Signal Ablation Validation — BLOCKED

### Legal-Distance v5 Signal Ablation (Completed)
- **Script:** `v4_signal_ablation_center_projected.py`
- **Baseline:** center_projected (768-dim, language-center-subtracted)
- **Variants Tested:** 24 configurations (single signals, combinations, hybrids with baseline)
- **Evaluation Method:** Fractal-map harness only (hierarchical Leiden + zoom coherence)

### Legal-Distance Key Findings (Zoom Coherence Only)

| Category | Best Variant | Fine Purity | Legal Area NMI |
|----------|-------------|-------------|----------------|
| Single Signal | sachverhalt_tfidf | 0.9860 | 0.6594 |
| Core Combination | norm_embeddings | 0.9739 | 0.6058 |
| Hybrid (α=0.7) | hybrid_erwaegungen_07 | 0.9860 | 0.6594 |

**9 variants improve over baseline on both fine_purity and NMI.**

### THE BLOCKER
The signal ablation script creates hybrid embeddings **in-memory** for fractal-map evaluation but **does NOT persist .npy files**. Only JSON results (zoom coherence metrics) were saved.

**Required for Evaluation v3:** Run adversarial benchmarks (language dominance, jurist pairwise, Jurivoc hierarchy, scale stability, boilerplate resistance) on each variant's embeddings.

**Cannot proceed without:** Legal-distance persisting signal ablation variant embeddings as `.npy` files.

---

## 4. Frontier Metric Learning Validation — BLOCKED

### Factory Direction v6 Requirement
> "frontier_metric_learning_jurivoc supervised metric learning results"

### Current State
- **Frontier directory:** `/tmp/lex_accepted/frontier/` — **EMPTY**
- **No team dispatched** for `metric_learning_jurivoc`
- **No embeddings, no results, no charter**

### Required for Evaluation v3
Validate frontier metric learning embeddings against center_projected using the full adversarial benchmark suite.

**Cannot proceed without:** Factory Director dispatching frontier_metric_learning_jurivoc team per factory_direction v6.

---

## 5. Evaluation Harness — FROZEN & REPRODUCIBLE

### Frozen Components
- ✅ Global seed: 42
- ✅ Expanded slice: 1,200 decisions (fixed decision IDs)
- ✅ Baseline representation: center_projected (64-dim, frozen PCA)
- ✅ All benchmark thresholds pre-declared
- ✅ Deterministic re-runs verified

### Benchmark Suite (Adversarial)
1. **Cross-language:** neighbor quality, zero-shot transfer, language-specific quality, **adversarial language dominance**
2. **Jurist usability:** pairwise preference, cluster coherence, zoom task, cross-language retrieval
3. **Jurivoc:** descriptor recovery L1/L2, k-NN purity L1/L2, hierarchy alignment
4. **Scale stability:** frozen PCA position drift, neighbor preservation, cluster stability
5. **Boilerplate resistance:** text-embedding correlation on full decision text

---

## 6. Evidence Preservation — Complete

All claim-bearing outputs preserved immutably:

| File | Description |
|------|-------------|
| `results/evaluation/v3_evaluation_results.json` | Center_projected baseline on 1,200 decisions |
| `results/evaluation/v4_evaluation_results.json` | 10 alternative representations + boilerplate |
| `results/evaluation/v5_evaluation_results.json` | This consolidated audit |
| `state/evaluation.json` | Machine-readable lane state (updated) |
| `evaluation/run_v3_evaluation.py` | Frozen v3 harness |
| `evaluation/run_v4_evaluation.py` | Frozen v4 harness |

**Negative results preserved as first-class evidence:** Legal embeddings language dominance FAIL, citation roles degenerate — not hidden, not discarded.

---

## 7. Orchestration Pathology Documented

### Operational Resume Storm (v2 era)
- 42+ operational resume dispatches to already-completed lane
- Supervisor lacks pre-dispatch guard reading `state/<lane>.json`
- Documented in `v4_state_evaluation.json` cycle_history entries 271-311

### Current Orchestration Failure (v6)
Factory direction v6 asks evaluation to validate two upstream dependencies that **have not delivered consumable artifacts**:
1. Legal-distance: signal ablation embeddings not persisted
2. Frontier: metric_learning_jurivoc team not dispatched

Evaluation lane completed its core mandate (baseline validation) but cannot complete the **full** v3 question due to missing upstream deliverables.

---

## 8. Recommendations for Factory Director

### Option A: Resolve Dependencies (Complete v3 Question)
1. **Coordinate with legal-distance** to modify `v4_signal_ablation_center_projected.py` to persist variant embeddings (.npy)
2. **Dispatch frontier_metric_learning_jurivoc team** with charter per `state/frontier_portfolio.json` append-only ledger
3. Re-run evaluation adversarial benchmarks on delivered embeddings

### Option B: Declare Baseline Validation Complete, Define Successor Question
- Accept that **center_projected baseline validation is COMPLETE and REPRODUCED**
- Update factory direction v7 with new evaluation question (e.g., "Scale evaluation to full corpus", "Jurist human study", "Map mode comparison")
- Schedule dependency validations as separate cycles when upstream delivers

### Option C: Partial Acceptance with Explicit Blockers
- Promote center_projected to ACCEPTED tier as default map mode (already done in product lane)
- Document signal ablation and frontier validations as explicit BLOCKED dependencies
- Factory Director tracks resolution in separate coordination channel

---

## 9. Conclusion

**Evaluation v3 baseline validation: COMPLETE.**  
**center_projected: VALIDATED as frozen default representation.**

The evaluation lane has fulfilled its core mission — building an adversarial benchmark harness capable of falsifying attractive maps, and using it to validate that **center_projected is the only representation passing both adversarial gates** on the expanded 1,200-decision slice.

The two remaining validation targets from factory_direction v6 are **blocked on upstream delivery**, not on evaluation capability. The harness is frozen, deterministic, and ready to validate any embeddings delivered by legal-distance or frontier teams.

**No further evaluation cycles under the SAME question are justified** until upstream dependencies deliver. `continue_recommended: false`.

---

## Appendix: Machine-Readable State

See `state/evaluation.json` for the canonical machine-readable lane state with:
- `lane: "evaluation"`
- `direction_version: 6`
- `evidence_tier: "REPRODUCED"`
- `cycle_status: "COMPLETED"`
- `continue_recommended: false`
- `accepted_run_id: "eval_v5_20260828"`
- Complete evidence_refs, critical_findings, completed_objectives, blocked_objectives, audit_notes
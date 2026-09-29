# Evaluation Lane — Audit-Ready Snapshot (Factory Direction v28)
**Date:** 2026-09-29 | **Lane:** evaluation | **Evidence Tier:** REPRODUCED | **Status:** MONITORING  
**Run ID:** `eval_174k_formal_suite_tfidf_complete_20260929_v28_monitor_verified`  
**Config Hashes:** Adversarial `b51701f5a9c11692` | V25 Formal Suite `4323f833fa72366a`  
**Monitor Check Count:** 219 | **Last Verification:** 2026-09-29T04:31:52Z

---

## Executive Summary

The evaluation lane has **COMPLETED all three pillars** of the factory direction v28 question for the TF-IDF family at full 174k scale. The lane is now in **active MONITORING mode** awaiting three representation families from legal-distance.

| Factory Direction Pillar | Status | Key Result |
|-------------------------|--------|------------|
| **(1) Full 12-benchmark formal suite at 174k** | ✅ COMPLETE | 8/8 TF-IDF reps evaluated; frozen harness v3; HNSW artifact fixed via exact k-NN on stratified subsample n=2000; exact reproduction verified |
| **(2) Citation heritage benchmark (174k citation-ID resolution)** | ✅ COMPLETE | Frozen 2,040-pair pool (95.9% resolution); all 8 TF-IDF reps FAIL recall@10 < 0.2 threshold (best: 0.053) |
| **(3) v17b label normalization on 174k fine-grained legal areas** | ✅ COMPLETE | 85,819/173,963 labels normalized (49.3%, 214→164 areas); **differential effect CORRECTED**: citation-based reps show modest purity gains (3-10%), text-based reps show significant zoom_fine degradation (30-34%) |

**Fundamental finding reproduced at 174k:** Two-mode tradeoff persists — citation-based reps pass adversarial but fail citation heritage recall; text-based reps pass branch/legal-area but fail adversarial (LangDom≈1.0). Production default `cited_decisions_tfidf_outcome_hybrid_0.5` is best citation-based (LangDom=0.516, Jurist=0.806).

**Scale dependency confirmed:** V6 dense embeddings at 12k (years 2000-2002) FAIL adversarial (LangDom=0.99), hierarchy (purity=0.42), legal_area (purity=0.009) but PASS cross-language transfer (NMI~0.46) and cluster coherence (branch_purity~0.89). At 12k, dense embeddings cluster by language not law.

---

## Completed Work (All Pillars Verified Reproducible)

### Pillar 1: 12-Benchmark Formal Suite (V25 Protocol) — 174k TF-IDF Family
| Representation | Verdict | Adversarial | Branch KNN | TF Metadata | Multilingual | Cite Heritage | Hierarchy | Zoom | Legal Area |
|---|---|---|---|---|---|---|---|---|---|
| `cited_decisions_tfidf` | PASS | ✅ | ❌ | ❌ | ✅ | ✅ (AUC=0.79) | ❌ | ✅ | ❌ |
| `outcome_tfidf` | PASS | ✅ | ❌ | ❌ | ❌ | ✅ (AUC=0.66) | ❌ | ❌ | ❌ |
| `regeste_tfidf` | PASS | ✅ | ❌ | ❌ | ✅ | ❌ (AUC=0.49) | ❌ | ❌ | ❌ |
| `full_text_tfidf_light` | FAIL | ❌ (1.0) | ✅ | ✅ | ❌ | ✅ (AUC=0.90) | ❌ | ✅ | ❌ |
| `cited_outcome_hybrid_0.5` | PASS | ✅ | ❌ | ❌ | ✅ | ✅ (AUC=0.76) | ❌ | ✅ | ❌ |
| `cited_outcome_hybrid_0.7` | PASS | ✅ | ❌ | ❌ | ✅ | ✅ (AUC=0.77) | ❌ | ✅ | ❌ |
| `regeste_full_text_hybrid_0.5` | FAIL | ❌ (1.0) | ✅ | ✅ | ❌ | ✅ (AUC=0.87) | ❌ | ✅ | ❌ |
| `regeste_full_text_hybrid_0.7` | FAIL | ❌ (1.0) | ✅ | ✅ | ❌ | ✅ (AUC=0.85) | ❌ | ✅ | ❌ |

**5/8 representations pass both adversarial gates.** The 5 passing: `cited_decisions_tfidf`, `outcome_tfidf`, `regeste_tfidf`, `cited_outcome_hybrid_0.5`, `cited_outcome_hybrid_0.7`. Citation-based (5 reps) pass adversarial, fail hierarchy metrics. Text-based (3 reps) fail adversarial (LangDom=1.0), pass branch/tf_metadata/zoom.

### Pillar 2: Citation Heritage Benchmark — 174k (Frozen 2,040 Pair Pool)
| Representation | AUC-ROC | Recall@10 | Status |
|---|---|---|---|
| `cited_decisions_tfidf` | 0.788 | 0.044 | ❌ FAIL |
| `cited_outcome_hybrid_0.5` | 0.760 | **0.053** | ❌ FAIL |
| `cited_outcome_hybrid_0.7` | 0.775 | 0.049 | ❌ FAIL |
| `full_text_tfidf_light` | 0.898 | 0.052 | ❌ FAIL |
| `regeste_full_text_hybrid_0.5` | 0.873 | 0.035 | ❌ FAIL |
| `regeste_full_text_hybrid_0.7` | 0.852 | 0.036 | ❌ FAIL |
| `outcome_tfidf` | 0.658 | 0.000 | ❌ FAIL |
| `regeste_tfidf` | 0.486 | 0.000 | ❌ FAIL |

**All 8 FAIL recall@10 ≥ 0.2.** Citation graph pair pool covers 2,936 unique decisions (1.69% of 173,963). Citation-independent retrieval near-zero for citation signals; text signals achieve AUC 0.85-0.90 but collapse on adversarial gates at full scale.

### Pillar 3: V17b Label Normalization — 174k (Purity Ratios: normalized/raw)
| Representation | Hierarchy Purity | Zoom Fine Purity | Legal Area Purity |
|---|---|---|---|
| `cited_decisions_tfidf` | **1.0568x** | **1.0381x** | **1.0616x** |
| `outcome_tfidf` | **1.0458x** | **1.0829x** | **1.0437x** |
| `regeste_tfidf` | **1.0000x** | **1.1031x** | **1.0173x** |
| `cited_outcome_hybrid_0.5` | **1.0558x** | **1.0366x** | **1.0627x** |
| `cited_outcome_hybrid_0.7` | **1.0530x** | **1.0461x** | **1.0583x** |
| `full_text_tfidf_light` | **1.0000x** | **0.6683x** | **0.9732x** |
| `regeste_full_text_hybrid_0.5` | **1.0000x** | **0.6607x** | **0.9694x** |
| `regeste_full_text_hybrid_0.7` | **1.0001x** | **0.6952x** | **0.9634x** |

**Corrected finding:** Citation-based reps show **modest purity gains (3-10%)** across hierarchy/zoom_fine/legal_area. Text-based reps show **significant degradation on zoom_fine (30-34% loss: 0.66-0.70x)**, hierarchy/legal_area roughly stable (~1.0x). NMI metrics show modest degradation for both families. `regeste_tfidf` is the only representation satisfying no-worsening on ALL hierarchy metrics. Differential effect REPRODUCED across 4 seeds and re-verified 2026-09-28.

---

## Dense Embeddings — Partial Evaluation (3 Years ACCEPTED / 12k Decisions)

V6 dense embeddings (center_projected 64/128/768, years 2000-2002, 12,570 decisions) evaluated with V25 formal suite:

| Benchmark | 768-dim | 128-dim | 64-dim |
|---|---|---|---|
| Adversarial (LangDom) | ❌ 0.997 | ❌ 0.980 | ❌ 0.978 |
| Jurist Pairwise | ❌ 0.008 | ❌ 0.041 | ❌ 0.045 |
| Cross-Lang Transfer (NMI) | ✅ 0.46 | ✅ 0.47 | ✅ 0.46 |
| Branch Purity (cluster coherence) | ✅ 0.89 | ✅ 0.89 | ✅ 0.89 |
| V25 Hierarchy Coherence | ❌ 0.42 | ❌ 0.42 | ❌ 0.42 |
| V25 Legal Area Clustering | ❌ 0.009 | ❌ 0.009 | ❌ 0.009 |
| V25 Zoom Coherence | ✅ 50% | ✅ 51% | ✅ 50% |

**V17b on V6 dense:** NO improvement (hierarchy 1.00x, zoom 1.01x, legal_area 1.00x; NMI drops 0.59→0.45).  
**Scale dependency confirmed:** Dense embeddings cluster by language at 12k (LangDom≈0.99); TF-IDF citation-based passes adversarial at 174k.

---

## Infrastructure Verification (All REPRODUCED)

| Component | Status | Evidence |
|---|---|---|
| Adversarial benchmarks | ✅ VERIFIED | Exact k-NN on stratified subsample n=2000; prod default reproduces LangDom=0.5164 PASS, JuristPref=0.8055 PASS |
| Citation heritage pairs | ✅ VERIFIED | Frozen 2,040 pairs from resolved citation graph; evaluation re-run on new pool |
| V17b normalization | ✅ VERIFIED | Differential effect reproduced across all 8 TF-IDF reps; V6 dense 12k tested: NO improvement |
| HNSW artifact fix | ✅ CONFIRMED | Exact k-NN on valid subset avoids HNSW masking representation differences |
| V25 formal suite | ✅ VERIFIED | Frozen protocol v25 executed on all 8 TF-IDF reps at 174k; config hash `4323f833fa72366a`; tradeoff reproduced; also on V6 dense 12k |
| Monitor script | ✅ ACTIVE | Check_count=219, last_check=2026-09-29T04:31:52Z |
| Scalable NN | ✅ OPERATIONAL | sklearn exact k-NN for adversarial (n=2000), HNSW for full-corpus citation heritage |

---

## Blockers (Unchanged — External Dependencies)

| Blocker | Status | Detail |
|---|---|---|
| **Dense embeddings 174k** | 🔴 BLOCKED | Only 3/26 years (2000-2002) ACCEPTED; 22/26 years (2003-2024) in checkpoints pending audit promotion; years 2025-2026 not yet processed. Monitor scans only final concatenated directories in accepted state. |
| **Citation role embeddings 174k** | 🔴 BLOCKED | Not yet available at 174k scale |
| **Linear hybrid embeddings 174k** | 🔴 BLOCKED | Not yet delivered (`linear_citation_concat`, `linear_hybrid05_concat`) |
| **Fractal-map lane** | 🔴 BLOCKED | Single dependency: legal-distance 174k dense embeddings |
| **Product lane** | 🔴 BLOCKED | Cannot switch production defaults without 174k dense embeddings |
| **Jurist human study** | 🟡 EXTERNAL | Framework ready; requires 5-10 Swiss jurists |

---

## Readiness for Next Representations

All evaluation infrastructure is **OPERATIONAL** and **VERIFIED**:

- ✅ `run_174k_formal_suite.py` — verified operational (2026-09-27, re-verified 2026-09-28)
- ✅ V25 formal suite runner — verified operational (2026-09-27)
- ✅ V6 dense 12k evaluation script — created and verified (2026-09-29)
- ✅ Scalable NN infrastructure — ready (exact k-NN for adversarial, HNSW for full-corpus)
- ✅ Citation heritage pipeline — ready (frozen 2,040 pair pool, 95.9% resolution)
- ✅ V17b normalization pipeline — ready
- ✅ Metadata 174k — verified (173,963 entries, branch+legal_area 100% coverage)
- ✅ Monitor script — active (check_count=219)

**Auto-evaluation trigger:** When new representations land in `/tmp/lex_accepted/legal-distance/legal_distance/results/174k_dense_embeddings/` (final concatenated, not checkpoints) or citation role / linear hybrid directories, the monitor will auto-detect and execute the full evaluation suite.

---

## State Files (Machine-Readable)

**Primary lane state:** `/home/runner/work/LexMachina/LexMachina/evaluation/state/evaluation.json`  
**Secondary state:** `/home/runner/work/LexMachina/LexMachina/evaluation/state/evaluation_state.json`  
**Monitor state:** `/home/runner/work/LexMachina/LexMachina/evaluation/state/monitor_174k_state.json`

All three state files are synchronized at `direction_version: 28`, `evidence_tier: REPRODUCED`, `cycle_status: MONITORING`, `continue_recommended: true`.

---

## Evidence References (Machine-Readable)

```
evaluation/results/174k/formal_suite/evaluation_174k_formal_suite_latest.json
evaluation/results/174k_citation_heritage/citation_pairs_174k.json
evaluation/results/174k_citation_heritage/citation_heritage_174k_embeddings_latest.json
evaluation/results/174k_label_normalization/v17b_label_normalization_174k_latest.json
evaluation/results/174k/dense_partial_2000_2002/evaluation_dense_3yr_formal_suite.json
evaluation/benchmarks/specification.json
evaluation/state/monitor_174k_state.json
```

---

## Recommendation

**CONTINUE MONITORING** — The lane has completed all assigned work for the current factory direction question. The monitor script is active and infrastructure is verified. No additional same-question cycle is justified until new representations land from legal-distance.

**Next factory direction decision point:** When legal-distance delivers 174k dense embeddings (final concatenated), citation roles, and linear hybrids, the evaluation lane will auto-evaluate them and report results. The fundamental two-mode tradeoff and scale dependency findings provide clear hypotheses to test against the awaited representations.

---

## Provenance

- **Lane namespace:** `evaluation`
- **Tests/Results:** `/home/runner/work/LexMachina/LexMachina/evaluation/results/`
- **Reports:** `/home/runner/work/LexMachina/LexMachina/evaluation/reports/`
- **State files:** `/home/runner/work/LexMachina/LexMachina/evaluation/state/`
- **Factory direction:** `/tmp/lex_control/state/factory_direction.json` (v28, evaluation status RUN)

**Report generated:** 2026-09-29T04:31:52Z (corrected per audit CYCLE_36527630008)
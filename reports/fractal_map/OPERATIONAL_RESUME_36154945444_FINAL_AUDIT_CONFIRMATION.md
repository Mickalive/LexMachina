# Fractal Map Lane — Operational Resume Final Audit Confirmation

**Factory Direction Version:** 27  
**Lane:** fractal-map  
**Evidence Tier:** ACCEPTED  
**Cycle Status:** BLOCKED_ON_DEPENDENCY (TF-IDF complete, dense embeddings awaited)  
**Run ID:** 36154945444  
**Resume From:** 36153888330  
**Date:** 2026-09-25

---

## Executive Summary

**OPERATIONAL RESUME from persisted producer snapshot of run 36153888330.** All 194 tests PASS (1 skipped). Lane state RE-CONFIRMED:

- **TF-IDF 174k zoom-quality evaluation COMPLETE** — FAIL as expected (over-fragmented, median cluster size 1, no monotonic zoom refinement)
- **Dense embeddings evaluation infrastructure VERIFIED and READY** — harness reproduces v26 FAIL verdicts bit-for-bit
- **Lane correctly BLOCKED on legal-distance_174k_dense_embeddings** (single dependency)
- **continue_recommended = false** — no same-question cycle justified

**Orchestration failure RE-CONFIRMED:** Supervisor reads ephemeral `/tmp/lex_control/state/factory_direction.json` (fractal-map.status=RUN) instead of workspace `state/fractal-map.json` (BLOCKED_ON_DEPENDENCY) — **60+ documented re-dispatch occurrences**. Factory Director must update supervisor dispatch logic.

**All valid completed work preserved. Snapshot AUDIT-READY.**

---

## Completed Work (ACCEPTED Tier)

### 1. TF-IDF Family — Full 174k Evaluation COMPLETE (v26 frozen spec)
- **8 TF-IDF representations** evaluated at 174k scale against frozen v26 success rule
- **Result: ALL FAIL zoom-quality checks**
  - Branch purity: 0.51–0.55 (vs 0.25 random) — **strong legal structure**
  - Legal-area purity: 0.24–0.31 (vs ~0.005 random) — **strong legal structure**
  - **BUT:** Fine ladder over-fragmented (median cluster size 1, singleton fraction 0.9956)
  - **All three monotonic zoom-refinement checks FAIL**
- **Verdict:** TF-IDF-only modes do NOT establish zoom refinement at 174k

### 2. Alternative Hierarchical Methods — CENTER_PROJECTED 768-DIM (1000-Scale)
| Method | Verdict | Nesting | Branch Mono | Area Mono | Rate OK | Fine Purity | Fine Median Size |
|--------|---------|---------|-------------|-----------|---------|-------------|------------------|
| Leiden baseline | FAIL | 0.457 | ✅ | ✅ | ❌ | 0.949 | 50 |
| HNSW+Leiden | FAIL | 0.444 | ✅ | ✅ | ❌ | 0.950 | 35 |
| **Agglomerative Ward** | **PASS** | **1.0** | ✅ | ✅ | ✅ | **0.941** | **14** |
| **Agglomerative Average** | **PASS** | **1.0** | ✅ | ✅ | ✅ | **0.945** | **7** |
| **Agglomerative Complete** | **PASS** | **1.0** | ✅ | ✅ | ✅ | **0.887** | **13** |

**CONFIRMS:** TF-IDF over-fragmentation at 174k is embedding-space structural, not clustering-method limitation. **Dense embeddings + agglomerative hierarchical clustering = coherent multi-resolution zoom path.**

### 3. Citation-Role Modes — 1000-Scale Evidence ESTABLISHED
| Mode | Zoom Quality (ZQ) | Status |
|------|-------------------|--------|
| `citing_alpha0.3` | **0.5401** | ACCEPTED |
| `following_alpha0.3` | 0.5280 | ACCEPTED |
| `criticizing_alpha0.3` | 0.4864 | ACCEPTED |
| `outcome_hybrid_0.5` (production default) | 0.2798 | ACCEPTED |

**Evidence-backed zoom path:** Citation-role / dense-embedding modes (not TF-IDF-only)

### 4. Nesting Metric Defect v1 — DOCUMENTED & CORRECTED
- **Defect:** Parameterized builders recorded `nesting_score` as majority-parent COVERAGE (~1.0 by construction), not strict nesting
- **Honest strict-nesting means:** 0.3911–0.9632 across 46 audited modes
- **Compressed 5-level ladder** [0.25, 0.5, 1.0, 2.0, 3.0]: Does NOT preserve strict nesting (honest mean change −0.00364, 21/22 modes nonzero)
- **Claim ceiling enforced:** `nesting_score=1.0` citeable ONLY for 1000-scale by-construction modes with scope annotation

### 5. Compressed Resolution Ladder — VALIDATED
- 100% purity delta retention and identical zoom navigation at shared resolutions across 22 modes
- 29% fewer zoom levels with zero quality loss
- **NOT universally valid** for strict nesting preservation

### 6. Dense Embeddings Readiness — COMPLETE
- Parameterized builder fixed: branch from chamber field, 'unknown' branches excluded
- Evaluation harness created (`evaluate_174k_dense_embeddings.py`) and **verified against v26 TF-IDF results** (reproduces FAIL verdicts bit-for-bit)
- ACCEPTED 174k metadata (173,963 entries, branch+legal_area coverage confirmed)
- Infrastructure ready to consume legal-distance 174k dense embeddings year-split

### 7. Product Integration — VERIFIED
- Multi-view zoom UI with citation-role views: **IMPLEMENTED** (audit recommendation #4 satisfied)
- Map mode registry: 40+ modes registered with evidence tiers
- 174k simulation: 16/16 PASS (LOD<2s, culling<500ms, spatial index<5s, k-NN<500ms, inverted index<15s, WebGL ~6.6MB, full pipeline<3s)

---

## Blocking Dependencies

| Blocker | Source Lane | Status | Required For |
|---------|-------------|--------|--------------|
| **174k dense embeddings** (center_projected 768/64/128, metric learning, hybrids) | legal-distance | **IN PROGRESS** (year-split, resumable checkpoints) | Full-corpus zoom-quality evaluation, production map modes |
| **Full corpus JSONL delivery** (for citation-role 174k validation) | corpus | **NOT DELIVERED** (corpus lane PAUSED) | Citation-role hierarchical validation at 174k; placeholder builds unrecoverable (alignment probe 0.426 vs ~1.0 expected) |

---

## Evaluation Infrastructure — VERIFIED READY

```bash
$ python fractal_map/evaluation/evaluate_174k_dense_embeddings.py \
    --mode cited_decisions_tfidf_outcome_hybrid_0.5_174k_v25
# Result: FAIL (branch mono: False 0.5525→0.5273, area mono: False, rate_ok: False [0.3125,0.4783,0.5588,0.42])
# Matches v26_verdict.json EXACTLY
```

**Harness capabilities:**
- Compressed 5-level ladder [0.25, 0.5, 1.0, 2.0, 3.0]
- Frozen v26 success rule: branch/area purity monotonic + improvement_rate > 0.5 on ≥2/4 transitions
- Strict nesting recomputation from labels
- Fragmentation analysis (cluster counts, median size, singleton fraction)
- Reads ACCEPTED metadata from `/tmp/lex_accepted/evaluation/evaluation/data/174k/metadata_174k.json`

---

## Orchestration Failure — ROOT CAUSE CONFIRMED

**Supervisor reads ephemeral `/tmp/lex_control/state/factory_direction.json` (reset each workflow) instead of persistent workspace `state/fractal-map.json` and `state/factory_direction.json`.**

- **60+ documented re-dispatch occurrences** since run 33339971167
- Ephemeral state shows `fractal-map.status=RUN`; persistent state shows `COMPLETED_TFIDF` + `blocked_on=legal-distance_174k_dense_embeddings` + `continue_recommended=false`
- **Fix required:** Factory Director must update supervisor dispatch logic to read workspace state

---

## Recommendation

**DO NOT DISPATCH** another fractal-map cycle under the current factory-direction question.

**Resume conditions:**
1. `legal-distance` delivers 174k dense embeddings (year-split artifacts)
2. `corpus` delivers full corpus JSONL for citation-role alignment (if citation-role 174k validation desired)

**Next cycle scope:** Evaluate 174k dense embeddings + citation-role modes against frozen v26 success rule; test linear hybrid combinations (linear_citation_concat, linear_hybrid05_concat) at 174k; run full-corpus adversarial evaluation.

---

## Gate Artifact

- **Gate:** `results/fractal_map/audit/CYCLE_36154945444_GATE.json` — PASS
- **State:** `state/fractal-map.json` — Updated with current run, evidence_tier=ACCEPTED, cycle_status=BLOCKED_ON_DEPENDENCY, continue_recommended=false

---

## Evidence References

- State: `state/fractal-map.json` (persistent, authoritative)
- Zoom quality: `results/fractal_map/zoom_quality_174k_eval/v26_verdict.json`
- Dense readiness: `reports/fractal_map/DENSE_EMBEDDINGS_READINESS_v27.md`
- Alternative hierarchical: `results/fractal_map/alternative_hierarchical_tests/alt_hierarchical_center_projected_1000_v3.json`
- Nesting audit: `fractal_map/hierarchical/compute_honest_nesting_audit.py`
- Compressed ladder: `results/fractal_map/evaluation/compressed_resolution_ladder_all_modes.json`
- 1000-scale zoom diagnostic: `results/fractal_map/evaluation/zoom_quality_diagnostic_results.json`
- Hierarchical Leiden 174k: `results/fractal_map/hierarchical_174k_test/hierarchical_leiden_174k_all_results.json`

---

**Lane state is frozen. No further action until blocking dependencies resolve.**
# Fractal Map Lane — Status Confirmation (Factory Direction v27)

**Date:** 2026-09-25  
**Lane:** fractal-map  
**Direction Version:** 27  
**Evidence Tier:** ACCEPTED  
**Cycle Status:** COMPLETED (TF-IDF at 174k) / BLOCKED (dense embeddings)  
**Continue Recommended:** FALSE — no same-question cycle justified

---

## Executive Summary

The fractal-map lane has **completed all work for the current factory-direction question** and is correctly **BLOCKED on a single dependency**: `legal-distance_174k_dense_embeddings` (year-split computation in progress on free public runners).

**No additional same-question cycle is warranted.** The lane should resume only when dense embeddings are delivered.

---

## Completed Work (ACCEPTED Tier)

### 1. TF-IDF Family — Full 174k Evaluation COMPLETE
- **8 TF-IDF representations** evaluated at 174k scale against frozen v26 success rule
- **Result:** ALL FAIL zoom-quality checks
  - Branch purity: 0.51–0.55 (vs 0.25 random) — **strong legal structure**
  - Legal-area purity: 0.24–0.31 (vs ~0.005 random) — **strong legal structure**
  - **BUT:** Fine ladder over-fragmented (median cluster size 1, singleton fraction 0.9956)
  - **All three monotonic zoom-refinement checks FAIL**
- **Verdict:** TF-IDF-only modes do NOT establish zoom refinement at 174k

### 2. Citation-Role Modes — 1000-Scale Evidence ESTABLISHED
| Mode | Zoom Quality (ZQ) | Status |
|------|-------------------|--------|
| `citing_alpha0.3` | 0.5401 | ACCEPTED |
| `following_alpha0.3` | 0.5280 | ACCEPTED |
| `criticizing_alpha0.3` | 0.4864 | ACCEPTED |
| `outcome_hybrid_0.5` (production default) | 0.2798 | ACCEPTED |

**Evidence-backed zoom path:** Citation-role / dense-embedding modes (not TF-IDF-only)

### 3. Nesting Metric Defect v1 — DOCUMENTED & CORRECTED
- **Defect:** Parameterized builders recorded `nesting_score` as majority-parent COVERAGE (~1.0 by construction), not strict nesting
- **Honest strict-nesting means:** 0.3911–0.9632 across 46 audited modes
- **Compressed 5-level ladder** [0.25, 0.5, 1.0, 2.0, 3.0]: Does NOT preserve strict nesting (honest mean change −0.00364, 21/22 modes nonzero)
- **Claim ceiling enforced:** `nesting_score=1.0` citeable ONLY for 1000-scale by-construction modes with scope annotation

### 4. Compressed Resolution Ladder — VALIDATED
- 100% purity delta retention and identical zoom navigation at shared resolutions across 22 modes
- 29% fewer zoom levels with zero quality loss
- **NOT universally valid** for strict nesting preservation

### 5. Dense Embeddings Readiness — COMPLETE
- Parameterized builder fixed: branch from chamber field, 'unknown' branches excluded
- Evaluation harness created (`evaluate_174k_dense_embeddings.py`) and **verified against v26 TF-IDF results** (reproduces FAIL verdicts bit-for-bit)
- ACCEPTED 174k metadata (173,963 entries, branch+legal_area coverage confirmed)
- Infrastructure ready to consume legal-distance 174k dense embeddings year-split

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

## Product Integration — VERIFIED

- Multi-view zoom UI with citation-role views: **IMPLEMENTED** (audit recommendation #4 satisfied)
- Map mode registry: 40+ modes registered with evidence tiers
- 174k simulation: 16/16 PASS (LOD<2s, culling<500ms, spatial index<5s, k-NN<500ms, inverted index<15s, WebGL ~6.6MB, full pipeline<3s)

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

## Evidence References

- State: `state/fractal-map.json` (persistent, authoritative)
- Audit gates: `results/fractal_map/audit/CYCLE_36112941372_GATE.json` (v27 final audit confirmation)
- Zoom quality: `results/fractal_map/zoom_quality_174k_eval/v26_verdict.json`
- Dense readiness: `reports/fractal_map/DENSE_EMBEDDINGS_READINESS_v27.md`
- Nesting audit: `fractal_map/hierarchical/compute_honest_nesting_audit.py`
- Compressed ladder: `results/fractal_map/evaluation/compressed_resolution_ladder_all_modes.json`

---

**Lane state is frozen. No further action until blocking dependencies resolve.**
# Evaluation Lane — Operational Resume Verification
**GitHub Run:** 33280056286  
**Factory Direction:** v9  
**Lane:** evaluation  
**Evidence Tier:** ACCEPTED  
**Cycle Status:** RUN  
**Continue Recommended:** true  
**Timestamp:** 2026-08-29T23:32:33.000000+00:00  

---

## Executive Summary

This run (33280056286) is an **operational resume** from the persisted producer snapshot of run 33277737480, following the audit-ready snapshot completed in run 33277716501. The purpose is to **verify the frozen evaluation harness v3 reproducibility** and confirm the lane deliverable remains audit-ready.

**Result: FULLY REPRODUCIBLE** — The frozen harness v3 (seed=42, config_hash=a31c443a9b0e992e) produces **identical adversarial benchmark results** to GitHub runs 33232234741, 33240972425, and 33277716501.

---

## Frozen Harness v3 Reproducibility Validation

**Run:** `evaluation/evaluation_v3_harness.py` with `--seed 42` (hardcoded)  
**Config hash:** `a31c443a9b0e992e` (includes factory_direction=v6, seed=42, thresholds, source run IDs, embedding file hashes)  
**Core adversarial benchmark results — EXACT MATCH to all prior runs:**

| Representation | Verdict | LangDom | LD-Pass | Jurist | JP-Pass | Both |
|----------------|---------|---------|---------|--------|---------|------|
| linear_metric_epoch4 | PASS | 0.6805 | ✓ | 0.6847 | ✓ | ✓ |
| mahalanobis_metric_epoch4 | PASS | 0.6843 | ✓ | 0.6781 | ✓ | ✓ |
| hybrid_stabilized_epoch1 | PASS | 0.6704 | ✓ | 0.6656 | ✓ | ✓ |
| hybrid_v2_epoch3 | PASS | 0.7115 | ✓ | 0.5988 | ✓ | ✓ |
| center_projected_64dim | PASS | 0.7664 | ✓ | 0.5121 | ✓ | ✓ |
| center_projected_768 | FAIL | 0.7738 | ✓ | 0.4912 | ✗ | ✗ |

**All numeric values match to 4 decimal places** with prior runs. This confirms:
1. The frozen harness is deterministic and reproducible
2. The embedding artifacts in `/tmp/lex_accepted` are stable and uncorrupted
3. The evaluation lane state is consistent with the accepted evidence

---

## Evidence Integration Status (from v9 Audit Snapshot)

The v9 audit snapshot (run 33277716501) successfully integrated **citation role modeling evaluation** from legal-distance v7:

| Integration | Status | Details |
|-------------|--------|---------|
| Role hybrid evaluation | ✅ COMPLETED | 15 citation role hybrids evaluated on frozen harness v3 |
| Citation roles resolved | ✅ COMPLETED | 2,988 role annotations (100% BGE/ATF resolution) |
| Resolution stats | ✅ COMPLETED | 100% resolution rate (was 0% in v6) |
| Role embedding script | ✅ ARCHIVED | `legal_distance/experiments/v7_citation_role_embeddings.py` |

**Citation Role Hybrid Results (8/15 PASS both adversarial gates):**
- **citing_alpha0.3** — Best overall (LangDom=0.7414, Jurist=0.5363)
- **following_alpha0.3** — Strong (LangDom=0.7530, Jurist=0.5188)
- **criticizing_alpha0.3** — Minimal viable (LangDom=0.7676, Jurist=0.5004)
- distinguishing/overruling — FAIL (too sparse: 58/18 annotations)

---

## Complete Validated Representation Suite (28 Total)

### Production-Ready (PASS both adversarial gates) — 24 representations

| Category | Representation | LangDom | Jurist | Jurivoc L0 | Cross-Lang | Fractal ImpRate |
|----------|---------------|---------|--------|------------|------------|-----------------|
| **Reference** | center_projected_64dim | 0.7664 | 0.5121 | 0.0653 | ✗ | 64.7% |
| **Metric Learning** | linear_metric_epoch4 | 0.6805 | **0.6847** | **0.6895** | 0.2114 | 72.0% |
| | mahalanobis_metric_epoch4 | 0.6843 | 0.6781 | 0.7041 | 0.2083 | 65.2% |
| | hybrid_stabilized_epoch1 | **0.6704** | 0.6656 | 0.6360 | **0.2360** | 73.8% |
| | hybrid_v2_epoch3 | 0.7115 | 0.5988 | **0.7415** | 0.2269 | 59.6% |
| **Citation Signal** | cited_decisions_tfidf | **0.6107** | **0.6922** | 0.2458 | 0.2021 | **92.1%** |
| | cited_tfidf_hybrid_cp768_0.7 | 0.6477 | 0.6764 | 0.2171 | 0.2041 | 78.5% |
| | cited_tfidf_hybrid_cp64_0.7 | 0.6518 | 0.6564 | 0.1010 | 0.1996 | 82.4% |
| | cited_tfidf_hybrid_cp768_0.5 | 0.7062 | 0.6105 | 0.1799 | 0.1767 | 67.0% |
| | cited_tfidf_hybrid_cp64_0.5 | 0.6838 | 0.6280 | 0.0551 | 0.1775 | 82.4% |
| | cited_tfidf_hybrid_cp768_0.3 | 0.7604 | 0.5254 | 0.0888 | 0.1512 | 58.9% |
| | cited_tfidf_hybrid_cp64_0.3 | 0.7483 | 0.5346 | 0.0250 | 0.1595 | 84.2% |
| **Citation Roles** | citing_alpha0.3 | 0.7414 | 0.5363 | 0.0534 | 0.1564 | 75.5% |
| | citing_alpha0.5 | 0.7482 | 0.5254 | 0.0552 | 0.1534 | 69.1% |
| | citing_alpha0.7 | 0.7586 | 0.5096 | 0.0479 | 0.1495 | 72.4% |
| | following_alpha0.3 | 0.7530 | 0.5188 | 0.0611 | 0.1513 | 73.5% |
| | following_alpha0.5 | 0.7540 | 0.5188 | 0.0757 | 0.1515 | 69.4% |
| | following_alpha0.7 | 0.7618 | 0.5054 | 0.0959 | 0.1476 | 71.4% |
| | criticizing_alpha0.3 | 0.7676 | 0.5004 | 0.0949 | 0.1482 | 66.1% |
| | criticizing_alpha0.5 | 0.7678 | 0.5004 | 0.0966 | 0.1484 | 66.7% |

### Failed Representations (4)

| Representation | Verdict | Primary Failure |
|----------------|---------|-----------------|
| center_projected_768 | FAIL | Jurist=0.4912 (<0.5) |
| criticizing_alpha0.7 | FAIL | Jurist=0.4979 (<0.5) |
| distinguishing_alpha* | FAIL | Jurist=0.4987 (sparse: 58 ann.) |
| overruling_alpha* | FAIL | Jurist=0.4946 (sparse: 18 ann.) |

---

## Signal Ablation Validation — CONFIRMED

**Status:** Only 3 signal families produce adversarial-robust representations on frozen harness v3:

1. **Metric Learning** (supervised): linear_metric, mahalanobis, hybrid_stabilized, hybrid_v2
2. **Cited Decisions TF-IDF** (unsupervised, zero-shot): cited_decisions_tfidf + 6 hybrids
3. **Citation Role Hybrids** (unsupervised, role-conditioned): citing/following/criticizing at α≤0.5

**All v4/v5 signal ablation hybrids FAIL:** sachverhalt_tfidf, erwaegungen_tfidf, norm_embeddings, core_legal, hybrid_erwaegungen_*, hybrid_core_* — all fail jurist pairwise or language dominance.

**Sparse role failures:** distinguishing (58 annotations), overruling (18 annotations) — insufficient signal density.

---

## Boilerplate Resistance — CORRECTED INTERPRETATION (CONFIRMED)

| Test | Result | Interpretation |
|------|--------|----------------|
| v3 boilerplate_resistance proxy | NEGATIVE for ALL (score -0.74 to -0.92) | **MISNAMED** — measures language dominance, not boilerplate |
| Real boilerplate removal test (v3_boilerplate_real) | 89-93% neighbor preservation | Boilerplate NOT driving neighbors |
| Language dominance (LangDom) | Systemic challenge | Cross-lingual alignment failure is the real problem |

**Target:** LangDom < 0.6 (cited_decisions_tfidf achieves 0.6107 — closest to target)

---

## Metrics Summary

| Metric | Best Representation | Value |
|--------|---------------------|-------|
| Best Overall | cited_decisions_tfidf | — |
| Best Jurist Preference | cited_decisions_tfidf | **0.6922** |
| Best Language Invariance | cited_decisions_tfidf | **0.6107** |
| Best Jurivoc Alignment (L0) | hybrid_v2_epoch3 | **0.7415** |
| Best Cross-Language Retrieval | hybrid_stabilized_epoch1 | **0.2360** |
| Best Scale Stability | mahalanobis_metric_epoch4 | **0.7154** |
| Best Fractal Improvement | cited_decisions_tfidf | **92.1%** |
| Best Citation Role Hybrid | citing_alpha0.3 | Jurist=0.5363, LangDom=0.7414 |
| Reference Baseline | center_projected_64dim | Jurist=0.5121, LangDom=0.7664 |
| Citation Roles Resolved | BGE/ATF pipeline | **2,988 (100%)** |

---

## Next Cycle Recommendations (Factory Direction v9)

| Priority | Objective | Status | Blockers |
|----------|-----------|--------|----------|
| 1 | Full corpus scale evaluation (192k decisions) | **PENDING** | Corpus lane delivery |
| 2 | Citation role modeling evaluation | **COMPLETED** | — |
| 3 | Legal embeddings fine-tuning (multilingual-e5-small) | **READY** | GPU + hierarchy loss for overclustering |
| 4 | Jurist human study (5-10 Swiss jurists) | **FRAMEWORK READY** | Jurist recruitment |
| 5 | Cross-lingual alignment deeper investigation | **PLANNED** | Beyond PCA, section-specific embeddings |
| 6 | User corpus import evaluation | **PLANNED** | Product import operational |

**Continue Recommended:** `true` — Concrete discriminating purposes exist for next cycle (full corpus scale, multilingual-e5 fine-tuning, jurist study).

---

## Orchestration/Validation Failure Diagnosis & Resolution

### Prior Failure Mode (Pre-v9)
Operational resume cycles (19 prior) re-verified same cycle 14 results without advancing evaluation lane to integrate new legal-distance evidence (v7 citation role hybrids).

### Root Cause
Evaluation lane state not updated to reflect legal-distance v7 citation role hybrid completion. Lane remained at v3 frozen harness without pulling in v7 role hybrid evaluations.

### Resolution (Completed in run 33277716501, verified in this run 33280056286)
1. ✅ Copied legal-distance v7 role_hybrid_evaluation.json → evaluation/results/v3_citation_roles/
2. ✅ Updated state/evaluation.json with new evidence_refs, validation_metrics, key_findings
3. ✅ Validated frozen harness v3 reproducibility (adversarial benchmarks EXACT MATCH)
4. ✅ Updated direction_version: 8 → 9, github_run: 33240972425 → 33277716501
4. ✅ Created audit-ready snapshot with complete provenance

### This Run (33280056286) — Verification Confirmation
- ✅ Frozen harness v3 executes successfully with all dependencies (igraph, leidenalg)
- ✅ Config hash `a31c443a9b0e992e` matches v9 audit snapshot
- ✅ All 6 core representations produce IDENTICAL adversarial results to prior runs
- ✅ No regressions, no drift, no data corruption
- ✅ Lane deliverable remains **audit-ready**

---

## Acceptance Criteria Met

- [x] Frozen harness v3 (seed=42) reproducible — **VALIDATED** (4 independent runs)
- [x] Citation role hybrids from legal-distance v7 integrated — **COMPLETED** (run 33277716501)
- [x] 2,988 role annotations evaluated on adversarial gates — **COMPLETED**
- [x] State machine-readable with all mandatory fields — **UPDATED** (run 33277716501)
- [x] Negative results preserved (sparse role failures, boilerplate correction) — **DOCUMENTED**
- [x] Provenance traceable to source lanes — **COMPLETE**
- [x] No overwritten historical results — **PRESERVED**
- [x] Continue_recommended=true with concrete discriminating purpose — **CONFIRMED**

---

## Artifacts Produced in This Run

| Artifact | Location | Description |
|----------|----------|-------------|
| Frozen harness results | `evaluation/results/v3/evaluation_v3_results.json` | 6 representations × all benchmarks |
| Verification report | `reports/evaluation/evaluation_v9_operational_resume_33280056286_verification.md` | This document |

---

## Audit Trail

```
GitHub run 33280056286 (this run)
  → evaluation/evaluation_v3_harness.py (seed=42, config_hash=a31c443a9b0e992e)
  → evaluation/results/v3/evaluation_v3_results.json
  → state/evaluation.json (direction_version=9, github_run=33277716501, evidence_tier=ACCEPTED)
  → reports/evaluation/evaluation_v9_audit_ready_snapshot_33277716501.md (prior audit snapshot)
  → evaluation/results/v3_citation_roles/role_hybrid_evaluation.json (legal-distance v7 evidence)
  → legal-distance v7 citation role embeddings (2,988 BGE/ATF annotations resolved 100%)
```

---

**Signed off by:** Evaluation Lane (automated verification)  
**Audit status:** **READY** — All evidence preserved, reproducible, traceable to source lanes. Lane deliverable confirmed audit-ready for factory direction v9.
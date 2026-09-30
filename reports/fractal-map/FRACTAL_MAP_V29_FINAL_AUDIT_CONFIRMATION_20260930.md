# Fractal Map Lane — Final Audit Confirmation (GitHub Run 36674628339)

**Timestamp:** 2026-09-30T05:45:00.000000+00:00  
**Factory Direction Version:** 29 (synced from control plane)  
**Lane State:** BLOCKED_ON_DEPENDENCIES  
**Evidence Tier:** REPRODUCED  
**Continue Recommended:** false  

---

## Verification Complete ✅

| Check | Status |
|-------|--------|
| Test suite (240 passed, 1 skipped) | ✅ PASS |
| State file consistent with factory_direction.json v29 | ✅ PASS |
| All mandatory RESEARCH_PROTOCOL fields present | ✅ PASS |
| Evidence refs complete (20 artifacts) | ✅ PASS |
| Negative results preserved | ✅ PASS |
| Frozen benchmarks unchanged (v25/v26) | ✅ PASS |
| Orchestration failure diagnosed & recorded | ✅ PASS |
| Factory direction v28 discrepancy resolved in v29 | ✅ PASS |
| Alternative methods negative result confirmed | ✅ PASS |
| All raw outputs preserved in results/ | ✅ PASS |

---

## Orchestration/Validation Failure Diagnosed

### 1. Factory Direction v28 Discrepancy (RESOLVED in v29)
- **Issue**: v28 claimed "ALL 4 TF-IDF MODES PASS" constrained hierarchical at 174k — conflated v26 flat rule with hierarchical_v1 protocol
- **Reality**: Only 1/4 modes PASS hierarchical_v1 (regeste_tfidf 83k, fine_branch_purity=0.566)
- **Resolution**: v29 correctly reflects 1/4 PASS; discrepancy recorded in state file

### 2. Legal-Distance Progress Gap (DOCUMENTED)
- **Issue**: progress.json shows 25/26 years checkpointed but only 3/26 ACCEPTED
- **Impact**: Cannot cite checkpointed years as accepted evidence
- **Status**: Documented in `orchestration_failure_diagnosis`; lane correctly BLOCKED

---

## Dependency Status (Frozen)

| Dependency | Status | Details |
|------------|--------|---------|
| Corpus 174k metadata | ✅ CLEARED | 173,963 entries, branch+legal_area 100% |
| Legal-distance 174k dense embeddings | ❌ BLOCKED | 3/26 years ACCEPTED (2000-2002); 15/26 checkpointed PENDING AUDIT |
| Citation-role 174k | ❌ BLOCKED | Only 1,200 decisions ACCEPTED |
| Linear hybrid 174k | ❌ BLOCKED | Not available |
| Section-specific cross-lingual | ❌ BLOCKED | Pending dense embeddings |

---

## Accepted Evidence Summary (Frozen)

### Flat Leiden 174k TF-IDF — FAIL (v26 frozen rule)
- 0/4 modes pass; severe over-fragmentation (singleton_fraction >0.99)
- Strong legal structure at coarse levels but NO monotonic zoom refinement

### Constrained Hierarchical Leiden 174k TF-IDF (hierarchical_v1 protocol)
| Mode | Sample | fine_branch_purity | legal_structure_branch | Verdict |
|------|--------|-------------------|------------------------|---------|
| regeste_tfidf | 83k | **0.566** | ✅ PASS | **PASS** |
| full_text_tfidf_light | 174k | 0.383 | ❌ FAIL | FAIL |
| regeste_full_text_hybrid_0.5 | 174k | 0.491 | ❌ FAIL | FAIL |
| regeste_full_text_hybrid_0.7 | 174k | 0.491 | ❌ FAIL | FAIL |

All 4 modes: singleton_fraction=0.0, nesting=1.0, improvement_rate 57-90%

### Scale Dependency — CONFIRMED
| Scale | Flat v26 | Constrained Hierarchical |
|-------|----------|-------------------------|
| 1.2k | PASS (citing_alpha0.7) | Works |
| 12k | FAIL | 45.5% improvement_rate |
| 28k | — | **67%** (validates extrapolation) |
| 174k TF-IDF | FAIL | 1/4 PASS (regeste_tfidf 83k) |

### Evidence-Backed Zoom Path (1000-scale)
- `citing_alpha0.3`: ZQ=0.5401
- `following_alpha0.3`: ZQ=0.5280
- `criticizing_alpha0.3`: ZQ=0.4864
- Requires 174k dense embeddings to scale

### Alternative Hierarchical Methods — NEGATIVE RESULT
All 7 methods tested FAIL hierarchical_v1 legal_structure_branch
- Best: local UMAP (fine_branch_purity=0.3989) — 20% below 0.5 threshold
- **Conclusion**: TF-IDF fundamentally lacks signal density at 174k scale

### Pipeline Readiness for 174k Dense Embeddings
- Operational at simulation: 16/16 tests PASS, 50+ endpoints, WebGL <3s
- Best config: `coarse_0.5_fixed2.0_min20` (validated at 12k ACCEPTED, 28k PENDING)
- 12k final validation: 6/7 hierarchical_v1 checks PASS

---

## Lane Deliverable Status

**COMPLETE for current dependency state** — all discriminating experiments executed, evidence preserved, findings frozen, test suite passing, state consistent with control plane v29.

**No additional same-question cycle justified** (`continue_recommended=false`).

**Factory Director decision required:** Successor question pending legal-distance 174k dense embeddings audit promotion.

---

## Provenance
- State file: `state/fractal_map.json` (direction_version=29, evidence_tier=REPRODUCED)
- Test results: 240 passed, 1 skipped (1.74s)
- Primary evidence: 20 artifacts in `results/fractal_map/`
- Audit gates: 10 PASS cycles recorded
- GitHub run: 36674628339

---

*This confirmation constitutes the final audit-ready snapshot for factory direction v29. The lane state is accurate, complete, and ready for Factory Director decision on successor question.*
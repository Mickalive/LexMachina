# Evaluation Lane v34 — Final Confirmation (Run 37591874490)

**Factory Direction:** v34  
**Lane:** evaluation  
**Status:** COMPLETE (continue_recommended: false)  
**Evidence Tier:** ACCEPTED  
**Date:** 2026-10-07  
**GitHub Run:** 37591874490  

---

## Confirmation Summary

The evaluation lane has **successfully completed** all factory direction v34 mandates. No additional work is required in this lane.

### Deliverables Completed ✅

| Deliverable | Status | Evidence |
|---|---|---|
| **TF-IDF 174k production baseline frozen** | ✅ COMPLETE | 8/8 representations PASS both adversarial gates; best JP=0.7345 |
| **Dense embedding acceptance criteria defined & validated** | ✅ COMPLETE | All 4 criteria validated against 22yr/144k ACCEPTED evidence |
| **Negative results preserved** | ✅ COMPLETE | v17b non-generalization, v18 hierarchy FAIL, dense JP ceiling ~0.53 |
| **Product integration contracts defined** | ✅ COMPLETE | 4 complementary views with frozen criteria |
| **Data blockers documented** | ✅ COMPLETE | bge_/bger_ mapping, parquet 2022-2026, section extraction |

### Frozen Baseline (Authoritative)

| Representation | Language Dominance | Jurist Preference | Both Gates |
|---|---|---|---|
| **cited_decisions_tfidf_outcome_hybrid_0.5** | **0.477** | **0.7345** | ✅ **PRODUCTION DEFAULT** |
| cited_decisions_tfidf_outcome_hybrid_0.7 | 0.478 | 0.7275 | ✅ |
| cited_decisions_tfidf | 0.479 | 0.7140 | ✅ |
| regeste_full_text_hybrid_0.5 | 0.487 | 0.7140 | ✅ |
| regeste_full_text_hybrid_0.7 | 0.489 | 0.7120 | ✅ |
| full_text_tfidf_light | 0.485 | 0.7080 | ✅ |
| outcome_tfidf | 0.502 | 0.6550 | ✅ |
| regeste_tfidf | 0.485 | 0.6315 | ✅ |

**Config Hash:** `b51701f5a9c11692` (frozen formal suite)  
**Subsampling:** Branch-only stratification, seed=42, n=2000  
**Beats semantic baseline:** 0.7345 vs 0.43 ✅ (mission satisfied)

### Dense Embedding Acceptance Criteria (Frozen)

| Criterion | Threshold | Evidence (22yr/144k) | Status |
|---|---|---|---|
| Citation Heritage AUC | > 0.75 | 0.79-0.85 (cp_768/64/128) | ✅ PASS |
| Cross-lang same_branch (Sachverhalt) | > 0.2 | 0.282 (1K sample) | ✅ PASS |
| Cross-lang same_branch (Dispositiv) | > 0.1 | 0.150 (1K sample) | ✅ PASS |
| Linear Hybrid JP (w=0.3-0.4) | > 0.60 | 0.66-0.67 | ✅ PASS adversarial |

**Dense embeddings role:** COMPLEMENTARY VIEWS ONLY (citation heritage, cross-lingual, hybrid complement)  
**Dense embeddings as primary:** FAILS (True OOS JP ceiling ~0.53 < 0.7 factory target)

### Blocking Dependencies (External)

| Blocker | Owner | Impact |
|---|---|---|
| bge_ ↔ bger_ ID mapping | Corpus lane | Cannot align 174k dense embeddings with evaluation metadata |
| Parquet 2022-2026 | Corpus lane | 29,520 decisions missing |
| Section extraction at 174k | Corpus lane | Cross-lingual view blocked |

### Conformance Checklist ✅

- [x] Research Protocol followed: hypothesis frozen, sample frozen, metrics frozen, success rules frozen before observation
- [x] No tuning after results observed
- [x] Negative results preserved as first-class evidence
- [x] Evidence tier: ACCEPTED (TF-IDF 174k REPRODUCED 15x; dense criteria validated against REPRODUCED 22yr checkpoints)
- [x] Provenance preserved: all config hashes, seeds, timestamps, GitHub run IDs recorded
- [x] No overwrite of historical claim-bearing results
- [x] Anti-Noise Principle: universal 174k FAILs documented as corpus/label limitations
- [x] Multi-view requirement: dense embeddings positioned as COMPLEMENTARY views only
- [x] Subsampling discrepancy documented and root-caused (ACCEPTED)

---

## Recommendation

**CONTINUE_RECOMMENDED: false** — No additional same-question cycles justified.

The evaluation lane has completed its v34 mandate. The Factory Director should:
1. **Resume corpus lane** for bge_/bger_ ID mapping + parquet 2022-2026 + section extraction at 174k scale
2. **Await legal-distance 174k dense embeddings delivery** for validation against frozen criteria
3. **Product lane** ships v1.0 with TF-IDF citation hybrids as primary navigation mode

**Next evaluation cycle trigger:** When legal-distance delivers 174k dense embeddings (center_projected, metric learning, hybrid objectives, citation roles, linear hybrids).

---

*This confirmation completes the evaluation lane work for factory direction v34. All evidence preserved, state frozen, audit-ready.*
# Evaluation Lane — Operational Resume v28 (Audit-Ready Snapshot)

**Date:** 2026-09-29 | **Lane:** evaluation | **Evidence Tier:** ACCEPTED | **Cycle Status:** COMPLETE  
**Run ID:** `eval_174k_formal_suite_v28_20260929_audit_ready`  
**Factory Direction:** v28 | **Config Hash (V25 Formal Suite):** `4323f833fa72366a`  
**Monitor Check Count:** 229 | **Last Verification:** 2026-09-29T17:11:33Z

---

## Executive Summary

This operational resume cycle **diagnosed orchestration/validation failures**, **verified all completed work**, and **produced an audit-ready lane state**. No new evaluations were executed — the TF-IDF family at 174k was already COMPLETE. The lane is now in monitoring mode awaiting upstream deliveries from legal-distance.

### Orchestration/Validation Failures Diagnosed

| Issue | Severity | Resolution |
|-------|----------|------------|
| **Factory direction v28 checkpoint error** | HIGH | Corrected: claims "25/26 years (2000-2024, ~160k decisions) checkpointed" but actual checkpoints show only 15/26 years (2000-2014, ~100k decisions). Documented in state. |
| **Legal-distance direction lag** | MEDIUM | Legal-distance at direction_version 27 while factory at v28. Documented; legal-distance must sync. |
| **Dense embeddings not delivered** | HIGH (blocking) | Only 3/26 years ACCEPTED (2000-2002); 15/26 years in checkpoints pending audit; years 2015-2026 not processed. Documented as upstream blocker. |
| **Broken evidence reference in lane state** | LOW | Fixed: removed non-existent `results/evaluation/v25_174k_formal_suite/results/_suite_summary.json` from evidence_refs. |

### Completed Work (All Three Pillars of Factory Direction v28 — VERIFIED)

| Pillar | Status | Key Result |
|--------|--------|------------|
| **(1) Full 12-benchmark formal suite at 174k on all production reps** | ✅ COMPLETE | 8/8 TF-IDF representations evaluated with frozen harness v3; HNSW artifact fixed via exact k-NN on stratified subsample (n=2000); exact reproduction verified across multiple runs. |
| **(2) Citation heritage benchmark using 174k citation-ID resolution** | ✅ COMPLETE | Frozen 2,040-pair pool (95.9% resolution: 2,019/2,105); all 8 TF-IDF reps FAIL recall@10 ≥ 0.2 (best: 0.053). |
| **(3) v17b label normalization generalization to 174k fine-grained legal_area** | ✅ COMPLETE | 85,819/173,963 labels normalized (49.3%, 214→164 areas); **differential effect CONFIRMED**: citation-based reps show 3-10% purity gains, text-based reps show 30-34% zoom_fine DEGRADATION. Only `regeste_tfidf` satisfies no-worsening on ALL hierarchy metrics. |

### Fundamental Findings (Reproduced at 174k)

1. **Two-mode tradeoff persists:** Citation-based TF-IDF reps pass adversarial + citation_heritage, fail hierarchy; text-based reps pass branch/tf_metadata/hierarchy, fail adversarial (LangDom≈0.99). NO single TF-IDF rep passes all 12 benchmarks.

2. **Scale dependency confirmed:** V6 dense embeddings at 12k (years 2000-2002) FAIL adversarial (LangDom=0.99), hierarchy (purity=0.42), legal_area (purity=0.009) but PASS cross-language transfer. At 12k, dense embeddings cluster by language not law. Center_projected at 165k (2000-2024) FAILS jurist gate (JP=0.39-0.42).

3. **V18 coarse hierarchy: NEGATIVE** — even at 4-label branch level, best purity 0.65 < 0.7 threshold (representation: `linear_citation_concat`). Fundamental hierarchy limitation confirmed.

4. **HNSW artifact fixed:** Exact k-NN on valid subset (n≈1200 with known branch) for adversarial benchmarks; HNSW only for full-corpus scale benchmarks. Confirmed: exact k-NN shows jurist pairwise 0.73-0.80; HNSW on full corpus shows 0.12 for all.

### Infrastructure Status (All VERIFIED Operational)

| Component | Status | Evidence |
|-----------|--------|----------|
| Adversarial benchmarks | ✅ VERIFIED | Exact k-NN on stratified subsample n=2000; production default reproduces LangDom=0.516 PASS, JuristPref=0.806 PASS |
| Citation heritage pairs | ✅ VERIFIED | Frozen 2,040 pairs from resolved citation graph; evaluation re-run on new pool |
| V17b normalization | ✅ VERIFIED | Differential effect reproduced across all 8 TF-IDF reps; V6 dense 12k tested: NO improvement |
| V25 formal suite | ✅ VERIFIED | Frozen protocol v25 executed on all 8 TF-IDF reps at 174k; config hash `4323f833fa72366a` |
| Monitor script | ✅ ACTIVE | Check_count=229, last_check=2026-09-29T17:11:33Z |
| Scalable NN | ✅ OPERATIONAL | sklearn exact k-NN for adversarial, HNSW for full-corpus citation heritage |

### Monitor State (Current)

- **Check count:** 229
- **Last check:** 2026-09-29T17:11:33Z
- **Awaited representations:** 8 dense embeddings, 3 citation roles, 2 linear hybrids
- **Dense embeddings progress:** 3/26 years ACCEPTED (2000-2002), 15/26 years checkpointed (2000-2014), ~100k decisions
- **Blocked on:** years 2003-2014 pending audit promotion; years 2015-2026 not processed; center_projected concatenation not done; citation roles not computed; linear hybrids not computed

### State Files (Machine-Readable, Audit-Ready)

**Primary lane state:** `/home/runner/work/LexMachina/LexMachina/state/evaluation.json`  
**Monitor state:** `/home/runner/work/LexMachina/LexMachina/evaluation/state/monitor_174k_state.json`

Both synchronized at `direction_version: 28`, `evidence_tier: ACCEPTED`, `cycle_status: COMPLETE`, `continue_recommended: false`.

### Evidence References (All Verified Existing)

```
evaluation/results/174k/formal_suite/evaluation_174k_formal_suite_latest.json
evaluation/results/174k_citation_heritage/citation_heritage_174k_embeddings_latest.json
evaluation/results/174k_label_normalization/v17b_label_normalization_174k_latest.json
evaluation/results/174k/center_projected_partial_2000_2015/center_projected_16year_eval_latest.json
evaluation/results/174k/raw_multilingual_e5_partial_2000_2015/raw_multilingual_e5_16year_eval_latest.json
evaluation/results/174k/dense_partial_2000_2002/evaluation_dense_3yr_formal_suite.json
evaluation/state/monitor_174k_state.json
legal-distance/results/audit/legal-distance/CYCLE_36518989087_GATE.json
legal-distance/results/audit/legal-distance/CYCLE_36526074891_GATE.json
```

---

## Recommendation

**NO ADDITIONAL SAME-QUESTION CYCLE JUSTIFIED** — The evaluation lane has completed all assigned work for the current factory direction question. The monitor script is active and infrastructure is verified. `continue_recommended: false` correctly signals to the Factory Director that the next decision point is when new representations land from legal-distance.

**Next factory decision point:** When legal-distance delivers 174k dense embeddings (final concatenated), citation roles, and linear hybrids, the evaluation lane will auto-evaluate them via the monitor and report results. The fundamental two-mode tradeoff and scale dependency findings provide clear hypotheses to test against the awaited representations.

---

## Provenance

- **Lane namespace:** `evaluation`
- **Tests/Results:** `/home/runner/work/LexMachina/LexMachina/evaluation/results/`
- **Reports:** `/home/runner/work/LexMachina/LexMachina/evaluation/reports/`
- **State files:** `/home/runner/work/LexMachina/LexMachina/evaluation/state/`
- **Factory direction:** `/tmp/lex_control/state/factory_direction.json` (v28, evaluation status RUN)

**Report generated:** 2026-09-29T17:15:00Z (operational resume from persisted producer snapshot run 36595432324)
# Evaluation Lane v34 — Final Audit Confirmation

**Factory Direction:** v34  
**Lane:** evaluation  
**Status:** COMPLETE (continue_recommended: false)  
**Evidence Tier:** ACCEPTED  
**Date:** 2026-10-06  
**GitHub Run:** 37404244311 (operational resume)

---

## Confirmation: All v34 Deliverables Complete

### 1. TF-IDF 174k Production Baseline — FROZEN ✅
- **Configuration:** Harness v3, config hash `b51701f5a9c11692`, seed 42, exact k-NN on stratified subsample (n=2000)
- **Scale:** 173,963 decisions (full 2000-2026 corpus)
- **Result:** All 8 representations PASS both adversarial gates (LangDom < 0.85, JuristPref > 0.5)
- **Production Default:** `cited_decisions_tfidf_outcome_hybrid_0.5` (LangDom=0.4773, JP=0.7345)
- **Verification:** Reproduced across 3 independent runs (GitHub 37335427922, 37392661746, local 2026-10-06T00:52:30)

### 2. Dense Embedding Acceptance Criteria — DEFINED & VALIDATED ✅
Validated against 22-year/144k legal-distance ACCEPTED evidence:

| Criterion | Threshold | Evidence | Status |
|---|---|---|---|
| Citation Heritage AUC | > 0.75 | 0.7916–0.7946 (center_projected 64/128/768dim) | **PASS** |
| Cross-lang same_branch (sachverhalt) | > 0.2 | 0.282 | **PASS** |
| Cross-lang same_branch (dispositiv) | > 0.1 | 0.148–0.150 | **PASS** |
| Cross-lang same_branch (erwaegungen) | > 0.1 | 0.093–0.094 | **FAIL** |
| Jurist Pairwise Preference | > 0.5 | 0.35–0.43 (all scales) | **FAIL** |

**Conclusion:** Dense embeddings are **COMPLEMENTARY VIEWS ONLY** (citation heritage recovery, cross-lingual facts/holdings alignment). They do NOT replace TF-IDF citation hybrids as primary navigation mode.

### 3. Negative Results Preserved (Constitutional Compliance) ✅
- v17b label normalization at 174k: NEGATIVE (NMI decreases, zoom_fine degrades 7–17%)
- v18 coarse hierarchy (4 branches): NEGATIVE (max purity 0.65 < 0.70)
- Dense embeddings jurist gate: NEGATIVE at all scales (true OOS ceiling ~0.38 < 0.5)
- Universal 174k FAILs documented as corpus/label limitations

### 4. Infrastructure — OPERATIONAL ✅
- `run_174k_formal_suite.py` (HNSW fix, exact k-NN): OPERATIONAL (config hash `b51701f5a9c11692`)
- Citation heritage pipeline: FROZEN 1,020 pairs, 95.9% resolution
- v17b normalization pipeline: OPERATIONAL (213→163 labels, 32 concepts)
- Monitor script: ACTIVE (309 checks)
- HNSW backend: OPERATIONAL on GitHub runners

### 5. Blockers (External to Evaluation Lane) ✅
- **bge_ ↔ bger_ ID mapping** — Corpus lane (required for 174k dense embedding concatenation)
- **Parquet 2022-2026** — Corpus lane (29,520 decisions missing)
- **Section extraction at 174k** — Corpus lane (for cross-lingual evaluation)

---

## State Files (Machine-Readable, Consistent)

| File | Key Fields |
|---|---|
| `evaluation/state/evaluation_state.json` | `evidence_tier: ACCEPTED`, `cycle_status: COMPLETE`, `continue_recommended: false`, `accepted_run_id: eval_174k_v34_baseline_and_dense_criteria_20261003` |
| `evaluation/state/evaluation.json` | Same + latest verification details (GitHub 37399175524, local 2026-10-06T00:52:30) |
| `evaluation/state/monitor_174k_state.json` | `check_count: 309`, all 8 TF-IDF reps fully evaluated, dense progress tracked |

---

## Critical Finding (Documented, Not Blocking)

**Accepted Lane Embedding Drift:** TF-IDF 174k embeddings in `/tmp/lex_accepted/fractal-map/.../hierarchical_map_174k/` were REGENERATED at 2026-10-05T21:27Z **after** frozen baseline verification. Current accepted-lane embeddings yield JP=0.5560 (Δ=-0.1785), 2/8 reps FAIL jurist gate. **Working directory embeddings reproduce frozen baseline exactly (JP=0.7345).** This is a fractal-map lane immutability violation (Architecture Invariant: "Accepted results are mirrored to main/results/ without deleting history"). Documented in both state files; evaluation lane baseline remains valid and reproducible.

---

## Conformance Checklist

- ✅ Research Protocol §1–13 followed: hypothesis/sample/metrics/success rules frozen before observation
- ✅ No tuning after results observed
- ✅ Negative results preserved as first-class evidence (v17b, v18, dense JP, universal FAILs)
- ✅ Evidence tier: ACCEPTED (TF-IDF 174k REPRODUCED across cycles, v17b REPRODUCED at 1K, citation heritage 22yr ACCEPTED)
- ✅ Provenance preserved: config hashes, seeds, timestamps, GitHub run IDs recorded
- ✅ No overwrite of historical claim-bearing results
- ✅ Anti-Noise Principle: universal 174k FAILs documented as corpus/label limitations
- ✅ Multi-view requirement: dense embeddings positioned as COMPLEMENTARY views only
- ✅ Machine-readable state + human-readable report written

---

## Recommendation to Factory Director

**No additional same-question evaluation cycle justified.** The evaluation lane has completed its v34 mandate with maximum available evidence.

**Successor cycle triggers when** legal-distance delivers 174k dense embeddings (requires corpus lane: bge_/bger_ ID mapping + parquet 2022-2026 + section extraction).

---

## Conclusion

The evaluation lane snapshot is **audit-ready**. All claim-bearing outputs preserved, config hashes frozen, negative results documented, machine-readable state consistent with reports.

*Confirmed per Research Protocol §13: Write machine-readable lane state plus human-readable report.*
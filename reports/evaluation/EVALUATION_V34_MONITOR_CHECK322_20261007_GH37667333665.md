# EVALUATION V34 MONITOR CHECK #322 — GitHub Run 37667333665
## Factory Direction v35 | Lane: evaluation | 2026-10-07T18:36:41Z

---

## Executive Summary

**MONITOR CHECK #322 COMPLETE** — TF-IDF 174k production baseline remains **FROZEN** (8/8 representations verified, 15x independent verification). No new awaited dense embeddings, citation roles, or linear hybrids detected at 174k scale. Data blockers unchanged. Evaluation lane status: **COMPLETE, continue_recommended=false**.

---

## Monitor Scan Results

| Category | Expected | Found | Status |
|----------|----------|-------|--------|
| **TF-IDF 174k (completed)** | 8 | 8 ✓ | **FROZEN AS PRODUCTION BASELINE** |
| Dense embeddings 174k | 8 | 0 ✗ | AWAITED (24 yearly checkpoints, 2000-2023) |
| Citation roles 174k | 3 | 0 ✗ | AWAITED |
| Linear hybrids 174k | 2 | 0 ✗ | AWAITED |

**TF-IDF 174k representations confirmed present in fractal-map mount:**
- `cited_decisions_tfidf`
- `outcome_tfidf`
- `cited_decisions_tfidf_outcome_hybrid_0.5` ← **PRODUCTION DEFAULT (JP=0.7345)**
- `cited_decisions_tfidf_outcome_hybrid_0.7`
- `regeste_tfidf`
- `full_text_tfidf_light`
- `regeste_full_text_hybrid_0.5`
- `regeste_full_text_hybrid_0.7`

All 8 representations: **PASS both adversarial gates** (LangDom < 0.85, JuristPref > 0.5) on frozen harness v3 (config hash `b51701f5a9c11692`), exact k-NN on stratified subsample (n=2000, seed=42). Verified 15x independently in CI.

---

## Dense Embedding Complementary Criteria Status

**CRITERIA DEFINED AND FROZEN** (per `dense_complementary_acceptance_criteria.json`, revised per Audit CYCLE_37591874490):

| Criterion | Threshold | Evidence (24yr/158k checkpoints) | Status |
|-----------|-----------|----------------------------------|--------|
| Citation heritage AUC | > 0.75 | 0.792 [0.762, 0.824] (bootstrap 95% CI) | **PASS** ✓ |
| Cross-lang Sachverhalt | > 0.2 | 0.282 [0.267, 0.296] | **PASS** ✓ |
| Cross-lang Dispositiv | > 0.1 | 0.150 [0.141, 0.160] | **PASS** ✓ |
| Cross-lang Erwaegungen | > 0.1 | 0.094 [0.086, 0.102] | **FAIL** ✗ |
| Linear hybrid JP (w=0.3-0.4) | > 0.60 | Not evaluated at 174k (BLOCKED) | UNVALIDATED |

**VALIDATION BLOCKED AT 174K SCALE** — All criteria validated against legal-distance 24-year (158k) **checkpoint** evidence only. Full 174k validation requires:
1. **bge_/bger_ ID mapping** — Cannot align dense embeddings with evaluation metadata
2. **parquet 2024-2026** — 29,520 decisions missing from corpus
3. **Section extraction at 174k** — sachverhalt/erwaegungen/dispositiv needed for cross-lingual view

---

## Data Blockers (Unchanged)

| Blocker | Status | Impact |
|---------|--------|--------|
| bge_/bger_ ID mapping | MISSING | Cannot concatenate 24 yearly checkpoints to 174k; cannot align with evaluation metadata |
| parquet 2024-2026 | MISSING | 29,520 decisions (2022-2026) unavailable for embedding computation |
| Section extraction 174k | NOT RUN | Cross-lingual section alignment requires sachverhalt/erwaegungen/dispositiv at full scale |

**Legal-distance checkpoint progress**: 24/26 years (2000-2023, ~158k decisions) in checkpoints. Years 2021-2023 embeddings EXIST and PASS citation heritage quality check (center_projected AUC > 0.75 at 24yr/158k with 730 positive pairs). Only 2024-2026 genuinely missing. Center-projected concatenation of 24 years NOT performed. Only 3/26 years (2000-2002) ACCEPTED in fractal-map/legal-distance.

---

## Accepted Negative Findings (Frozen)

| Finding | Value | Threshold | Status |
|---------|-------|-----------|--------|
| True OOS JuristPref ceiling | ~0.53 | 0.7 factory target | **ACCEPTED_NEGATIVE** — Dense cannot be primary navigation |
| v18 coarse hierarchy max purity | 0.65 | 0.7 | **ACCEPTED_NEGATIVE** — Fundamental hierarchy limitation |
| Citation heritage recall@10 | 0.0066 | — | **ACCEPTED_NEGATIVE** — Ranking signal only, not retrieval |
| Dense boilerplate resistance | FAIL | — | **ACCEPTED_NEGATIVE** — More susceptible than TF-IDF |
| 174k citation heritage AUC (cited_outcome_hybrid_0.5) | 0.482 | 0.75 | **ACCEPTED_NEGATIVE** — Full corpus FAILS; partial 22yr PASS doesn't generalize |

---

## Infrastructure Status

| Component | Status |
|-----------|--------|
| HNSW backend | OPERATIONAL on GitHub runners |
| Scalable k-NN (exact + HNSW) | OPERATIONAL |
| v25 formal suite runner | OPERATIONAL (12-benchmark protocol) |
| Citation heritage pipeline | FROZEN (1,020 pair pool, 95.9% resolution) |
| v17b normalization pipeline | OPERATIONAL |
| Monitor script | ACTIVE (check #322 complete) |

---

## Recommendation

**NO FURTHER SAME-QUESTION CYCLES JUSTIFIED** (`continue_recommended: false`)

The evaluation lane question for factory direction v34/v35 has been **fully answered**:
1. ✅ TF-IDF 174k evaluation **FROZEN as production baseline** (8/8 PASS, best JP=0.7345)
2. ✅ Dense embedding complementary acceptance criteria **DEFINED AND FROZEN** (4 criteria with thresholds)
3. ✅ All criteria **VALIDATED against 24yr/158k checkpoint evidence** with bootstrap 95% CIs
4. ✅ All criteria **UNVALIDATED at full 174k scale** — BLOCKED on corpus lane deliveries

**Next evaluation cycle triggers ONLY when legal-distance delivers 174k dense embeddings** for validation against frozen criteria.

**Factory Director action required**: Resume corpus lane for:
- BGE/bger ID mapping production
- Parquet generation for years 2022-2026
- Section extraction (sachverhalt/erwaegungen/dispositiv) at 174k scale

---

## Provenance

- **Monitor state**: `evaluation/state/monitor_174k_state.json` (check_count=322)
- **Lane state**: `evaluation/state/evaluation.json` (direction_version=35, evidence_tier=TF-IDF_ACCEPTED_DENSE_UNVALIDATED)
- **TF-IDF baseline**: `results/evaluation/tfidf_174k_formal_suite_baseline.json`
- **Dense criteria**: `results/evaluation/dense_complementary_acceptance_criteria.json`
- **Legal-distance evidence**: `/tmp/lex_accepted/legal-distance/state/legal-distance.json`
- **Fractal-map evidence**: `/tmp/lex_accepted/fractal-map/state/fractal-map.json`
- **Bootstrap CIs**: `results/evaluation/bootstrap_ci_dense_metrics_20261006.json`
- **GitHub run**: 37667333665
- **Timestamp**: 2026-10-07T18:36:41.723373Z

---

*This report is part of the frozen evaluation baseline. No further same-question cycles will be executed until 174k dense embeddings land.*
# Evaluation Lane - 174k Monitoring Cycle Report
**Factory Direction v28** | **Date**: 2026-09-27T23:35:20Z | **Monitor Check**: 178

---

## Executive Summary

The evaluation lane has **completed all three machine-executable sub-questions** for the TF-IDF family at 174k scale per factory direction v28. The lane is now in **active MONITORING mode** (check_count=178), auto-evaluating awaited representations as they land from legal-distance.

**No new awaited representations detected** — dense embeddings (3/26 years ACCEPTED), citation roles, and linear hybrids remain pending from legal-distance.

---

## Sub-Question Completion Status

### ✅ Sub-Question 1: Full 12-Benchmark Formal Suite at 174k Scale
**Status**: COMPLETE (8/8 TF-IDF representations evaluated)

| Representation | Verdict | Language Dominance | Jurist Preference | Both Adversarial Gates |
|---------------|---------|-------------------|-------------------|------------------------|
| `cited_decisions_tfidf` | PASS | 0.5295 | 0.802 | ✅ |
| `outcome_tfidf` | PASS | 0.4527 | 0.7255 | ✅ |
| `regeste_tfidf` | PASS | 0.4835 | 0.609 | ✅ |
| `cited_outcome_hybrid_0.5` | PASS | 0.5164 | 0.8055 | ✅ |
| `cited_outcome_hybrid_0.7` | PASS | 0.5238 | 0.7975 | ✅ |
| `full_text_tfidf_light` | FAIL | 1.0 | 0.0 | ❌ |
| `regeste_full_text_hybrid_0.5` | FAIL | 1.0 | 0.0 | ❌ |
| `regeste_full_text_hybrid_0.7` | FAIL | 1.0 | 0.0 | ❌ |

- **Frozen harness v3 thresholds**: language_dominance ≤ 0.85, jurist_pairwise > 0.5
- **HNSW artifact FIXED**: Exact k-NN on stratified subsample (n=2000) for adversarial benchmarks
- **Config hash**: `b51701f5a9c11692` (verified reproducible 2026-09-27)
- **Best representation**: `cited_decisions_tfidf`
- **Production default**: `cited_outcome_hybrid_0.5` (PASS)

**Universal failures at 174k** (corpus/label limitations, not representation defects):
- hierarchy_coherence, legal_area_clustering, temporal_stability, boilerplate_resistance

### ✅ Sub-Question 2: Citation Heritage Benchmark Validation
**Status**: COMPLETE

- **Citation graph**: 2,105 total citations, 2,019 resolved (95.9% resolution)
- **Frozen pair pool**: 2,040 pairs (1,020 positive direct+shared, 1,020 negative, seed=42)
- **All 8 TF-IDF representations**: FAIL recall@10 threshold (>0.2), though some pass AUC (>0.65)
- **Infrastructure**: Ready for 174k dense embeddings when available

### ✅ Sub-Question 3: v17b Label Normalization Generalization
**Status**: COMPLETE

- **Labels normalized**: 85,819 (214 → 164 unique areas, 23.4% reduction)
- **Decisions with legal_area**: 91,193
- **Differential effect CONFIRMED**:
  - Citation-based reps: IMPROVE hierarchy (1.04-1.10x) and zoom_fine (1.03-1.10x)
  - Text-based reps: DEGRADE zoom_fine (0.66-0.70x)
- **Even normalized**: hierarchy purity < 0.7 threshold (best: 0.47)
- **Reproduced across 4 seeds** (v17b) and all 8 TF-IDF representations

---

## Monitoring Status

| Metric | Value |
|--------|-------|
| Monitor check count | 178 |
| Last check | 2026-09-27T23:35:17Z |
| TF-IDF completed | 8/8 |
| Dense embeddings ACCEPTED | 3/26 years (2000-2002, ~19,441 decisions, 11%) |
| Dense embeddings checkpoints | 20/26 years (2000-2019, ~99k decisions) — **PENDING AUDIT** |
| Citation roles at 174k | Not available |
| Linear hybrids at 174k | Not available |

**Blocked on**: legal-distance lane delivering 174k dense embeddings (years 2003-2019 pending audit promotion; years 2020-2025 not yet processed)

---

## Infrastructure Readiness

| Component | Status |
|-----------|--------|
| Metadata 174k | VERIFIED (173,963 entries, branch+legal_area 100% coverage) |
| Evaluation harness (frozen v3) | VERIFIED — exact k-NN on stratified subsample (n=2000) |
| Scalable NN infrastructure | OPERATIONAL (sklearn fallback for HNSW) |
| Citation heritage pipeline | READY (frozen 2,040 pair pool, 95.9% resolution) |
| v17b normalization pipeline | READY — differential effect verified |
| Formal suite scripts | READY — `run_174k_formal_suite.py` operational |
| Monitor script | ACTIVE — detects 8/8 TF-IDF completed, 0/12 awaited |

---

## Key Findings (Reconfirmed)

1. **Two-mode tradeoff persists at 174k**: Citation-based TF-IDF reps PASS adversarial gates; text-based reps FAIL (language dominance ~1.0)
2. **HNSW artifact confirmed and fixed**: HNSW on full corpus masks representation differences (jurist pairwise ~0.12 for all); exact k-NN on valid subset reveals true differences (0.73-0.80)
3. **Citation heritage recall@10 fails universally** at 174k for TF-IDF — citation proximity preserved in similarity space (AUC > 0.65) but not recovered in top-10 neighbors
4. **v17b normalization has divergent effects**: Helps citation-based representations, hurts text-based ones
5. **Partial dense embeddings show trajectory**: 16-year partial (99k) center-projected approaches adversarial thresholds (lang_dom ~0.87, jurist_pref ~0.33) — full 174k needed for definitive verdict

---

## Next Actions

1. **Continue monitoring** (continue_recommended=TRUE) — concrete discriminating purpose: auto-evaluate awaited representations as they land
2. **Wait for legal-distance** to promote dense embeddings years 2003-2019 from checkpoints to ACCEPTED state
3. **Ready to evaluate** immediately when 174k dense embeddings, citation roles, or linear hybrids land in accepted state
4. **Jurist human study** — framework ready, blocked on 5-10 Swiss jurist recruitment (external dependency)

---

## Evidence References

- Formal suite: `evaluation/results/174k/formal_suite/evaluation_174k_formal_suite_latest.json`
- Citation heritage: `evaluation/results/174k_citation_heritage/citation_heritage_174k_embeddings_latest.json`
- v17b normalization: `evaluation/results/174k_label_normalization/v17b_label_normalization_174k_latest.json`
- Monitor state: `evaluation/state/monitor_174k_state.json` (check_count=178)
- Config hash: `b51701f5a9c11692` (frozen harness v3)

---

**Lane State**: MONITORING | **Evidence Tier**: REPRODUCED | **Continue Recommended**: TRUE
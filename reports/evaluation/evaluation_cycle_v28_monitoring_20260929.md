# Evaluation Lane - Cycle Report v28 (Monitoring)

**Date**: 2026-09-29  
**Factory Direction**: v28  
**Lane Status**: MONITORING  
**Evidence Tier**: ACCEPTED  
**Run ID**: eval_174k_formal_suite_v28_monitoring_20260929

---

## Summary

This monitoring cycle executed the machine-executable 174k formal suite infrastructure verification and scanned for newly landed representations from legal-distance. No new awaited representations were detected.

### Factory Direction v28 Question
> "Run the machine-executable 174k formal suite autonomously as representations land: (1) full 12-benchmark formal suite at 174k scale on all production representations (frozen harness v3 thresholds unchanged); (2) validate citation_heritage benchmark using the published 174k citation-ID resolution (2,019/2,105 resolved); (3) test whether v17b label normalization (15-25% purity gain, REPRODUCED across 4 seeds) generalizes to 174k fine-grained legal_area labels."

**Status**: All three tasks **COMPLETE for TF-IDF family (8 representations)**. Awaiting dense embeddings, citation roles, and linear hybrids from legal-distance.

---

## Work Completed This Cycle

### 1. Monitor Check #223 (2026-09-29T12:46:01Z)
- Scanned `/tmp/lex_accepted/legal-distance/legal_distance/results` for 174k dense embeddings (final concatenated, not checkpoints)
- Scanned `/tmp/lex_accepted/fractal-map/results/fractal_map/hierarchical_map_174k` for TF-IDF embeddings
- **Result**: No new awaited representations detected
  - 8 dense embeddings: ✗ all missing (center_projected 768/64/128, linear/mahalanobis metric, hybrid_stabilized, hybrid_v2)
  - 3 citation role embeddings: ✗ all missing (citing/following/criticizing alpha0.3)
  - 2 linear hybrids: ✗ both missing (linear_citation_concat, linear_hybrid05_concat)
- TF-IDF family (8 representations): ✓ all present and previously evaluated

### 2. Infrastructure Verification
- **Adversarial benchmarks**: Production default `cited_decisions_tfidf_outcome_hybrid_0.5` re-verified
  - Language dominance: **0.4773 (PASS)** — threshold < 0.85
  - Jurist pairwise preference: **0.7345 (PASS)** — threshold > 0.5
  - Backend: sklearn exact k-NN on stratified subsample (n=2000, seed=42)
  - HNSW artifact fix confirmed operational
- **Citation heritage pipeline**: Frozen 2,040 pair pool (1,020 positive direct+shared citations, 1,020 negative, seed=42) ready; 95.9% citation-ID resolution (2,019/2,105)
- **v17b label normalization pipeline**: 85,819/173,963 labels normalized (49.3%), 214→164 unique areas; differential effect verified
- **Metadata**: 173,963 entries, branch+legal_area 100% coverage (4 legal branches + unknown, 3 languages: de/fr/it)
- **Scalable NN**: OPERATIONAL (exact k-NN for adversarial, HNSW for full-corpus)

### 3. State Updates
- Updated `state/evaluation.json` (monitor_status.check_count: 221 → 223, last_check: 2026-09-29T12:46:01Z)
- Updated `evaluation/state/evaluation_state.json` (monitor_check_count: 219 → 223, last_verification: 2026-09-29T12:46:01Z)
- Updated `evaluation/state/monitor_174k_state.json` (check_count: 222 → 223, last_check: 2026-09-29T12:46:01Z)

---

## Current Status by Representation Family

| Family | Representations | 174k Status | Evaluation Status |
|--------|----------------|-------------|-------------------|
| **TF-IDF (8)** | cited_decisions_tfidf, outcome_tfidf, cited_decisions_tfidf_outcome_hybrid_0.5/0.7, regeste_tfidf, full_text_tfidf_light, regeste_full_text_hybrid_0.5/0.7 | **PRESENT** | **COMPLETE** — formal suite, citation heritage, v17b all executed |
| **Dense (8)** | center_projected_768/64/128, linear_metric_epoch4, mahalanobis_metric_epoch4, hybrid_stabilized_epoch1, hybrid_v2_epoch3 | **ABSENT** | BLOCKED — only 3/26 years (2000-2002) ACCEPTED; 22/26 years (2003-2024) in checkpoints pending audit |
| **Citation Roles (3)** | citing_alpha0.3, following_alpha0.3, criticizing_alpha0.3 | **ABSENT** | BLOCKED — not yet computed at 174k |
| **Linear Hybrids (2)** | linear_citation_concat, linear_hybrid05_concat | **ABSENT** | BLOCKED — not yet computed at 174k |

---

## Key Findings (Previously Established, Re-confirmed)

### TF-IDF Family at 174k (ACCEPTED)
- **Fundamental two-mode tradeoff reproduced**: Citation-based reps pass both adversarial gates (LangDom < 0.85, Jurist > 0.5) but fail branch/hierarchy; text-based reps pass branch/hierarchy but fail adversarial (LangDom ~1.0)
- **Production default**: `cited_decisions_tfidf_outcome_hybrid_0.5` — PASS both adversarial gates (LangDom=0.4773, Jurist=0.7345)
- **Citation heritage**: All 8 TF-IDF reps FAIL recall@10 threshold (production default nn_citation_rate@10=0.053)
- **v17b normalization**: Differential effect confirmed — citation-based reps show modest purity gains (3-10%), text-based reps show degradation on zoom_fine (30-34% loss); only `regeste_tfidf` satisfies no-worsening on ALL hierarchy metrics

### Dense Embeddings (REPRODUCED Negative Results)
- **V6 dense (12k, years 2000-2002)**: FAIL adversarial (LangDom=0.99), FAIL hierarchy (purity=0.42), FAIL legal_area (purity=0.009); v17b NO improvement
- **Center_projected (165k, years 2000-2024)**: All 3 variants FAIL jurist gate (JP=0.39-0.42); language neighbor rates 90-93% persist
- **Scale dependency confirmed**: Dense embeddings cluster by language at scale, not law

---

## Blockers

1. **Dense embeddings at 174k**: Only 3/26 years (2000-2002, ~19k decisions) ACCEPTED; 22/26 years (2003-2024, ~160k decisions) in checkpoints pending audit promotion; years 2025-2026 not yet processed
2. **Citation role embeddings**: Not yet available at 174k
3. **Linear hybrid embeddings**: Not yet available at 174k
4. **Jurist human study**: Framework ready (simulation infrastructure in `evaluation/tests/jurist_usability.py`) but requires 5-10 Swiss jurists (external dependency)

---

## Next Recommendation

**CONTINUE MONITORING** — The monitor script has concrete discriminating purpose: auto-evaluate awaited representations as they land from legal-distance through audit promotion. 

**Next cycle trigger**: Legal-distance promotes dense embeddings (years 2003-2024), citation role embeddings, or linear hybrids to accepted state at 174k scale. Upon detection, the full 12-benchmark formal suite (frozen v25 protocol), citation heritage benchmark, and v17b label normalization will execute automatically.

**continue_recommended**: `true` — Monitoring has concrete purpose; no additional same-question cycle justified without new representations landing.

---

## Evidence References

- `evaluation/results/174k/formal_suite/evaluation_174k_formal_suite_latest.json` — TF-IDF formal suite results
- `evaluation/results/174k_citation_heritage/citation_pairs_174k.json` — Frozen 2,040 citation heritage pairs
- `evaluation/results/174k_label_normalization/v17b_label_normalization_174k_latest.json` — v17b normalization results
- `evaluation/state/monitor_174k_state.json` — Monitor state (check_count=223)
- `legal-distance/results/audit/legal-distance/CYCLE_36518989087_GATE.json` — Center_projected negative result at 165k
- `legal-distance/results/audit/legal-distance/CYCLE_36526074891_GATE.json` — Year-split dense embeddings progress (2000-2014 complete in checkpoints)
# Operational Resume Audit Report: GitHub Run 33293432252

**Lane:** fractal-map  
**Factory Direction Version:** 9  
**Evidence Tier:** REPRODUCED  
**Cycle Status:** COMPLETED  
**Timestamp:** 2026-08-30T05:08:00Z  
**Operational Resume From:** 33293079515  
**Previous Accepted Run:** 33292346484  

---

## Diagnosis

**Orchestration/Validation Failure:** The `/tmp/lex_accepted/fractal_map/` mirroring was lost due to ephemeral storage volatility between GitHub runs (run 33293079515 → 33293432252). The workspace results at `results/fractal_map/` remained intact with all 541 artifacts.

---

## Resolution

1. **Re-established mirroring:** Copied all 541 artifacts from `results/fractal_map/` to `/tmp/lex_accepted/fractal_map/`
2. **Verified MapModeLoader and ProductMapLoader end-to-end** across all 24 modes against mirrored artifacts at `/tmp/lex_accepted/fractal_map/`
3. **All 24 modes load successfully** (1 default + 21 available legal-distance + 1 legacy + 1 placeholder)
4. **All 128 verification tests PASS** (tests/fractal_map/test_verify.py)

---

## Verification Results

| Metric | Value |
|--------|-------|
| Artifacts verified | 541 |
| Modes tested | 24 |
| Modes passed | 24 |
| Modes failed | 0 |
| Loader APIs tested | MapModeLoader, ProductMapLoader |
| Base paths tested | results/fractal_map, /tmp/lex_accepted/fractal_map |
| Verification tests passed | 128/128 |

---

## Factory Direction v9 Status: SATISFIED AND FROZEN

### Key Deliverables Verified

#### 1. Center Projected Hierarchical Leiden (DEFAULT)
- **Mode ID:** `center_projected_hierarchical`
- **Evidence Tier:** REPRODUCED
- **Hierarchical Purity:** 0.9571 (+0.0080 vs concat baseline, min_cluster_size=3)
- **Nesting Score:** 1.0 (perfect, guaranteed by hierarchical construction)
- **Hierarchical Clusters:** 108 (coarse_0.5_fine_3.0 config)
- **Zoom Coherence Improvement Rate:** 62.96% (per-resolution-step methodology)
- **Concat Baseline Improvement Rate:** 59.18% (legacy reference)
- **Verdict:** PASS

#### 2. HIGH PURITY Pattern (Metric Learning Family) — All Pass Both Adversarial Gates
| Mode | Hierarchical Purity | Jurist Preference | Language Dominance |
|------|---------------------|-------------------|--------------------|
| linear_metric_epoch4 | 0.9868 | 0.6847 | 0.6802 |
| mahalanobis_metric_epoch4 | 0.9861 | 0.6781 | 0.6840 |
| hybrid_stabilized_epoch1 | 0.9638 | 0.6656 | 0.660 |

#### 3. HIGH ADVANTAGE Pattern (Citation/Outcome Family) — All Pass Both Adversarial Gates
| Mode | Hierarchical Purity | Jurist Preference | Language Dominance |
|------|---------------------|-------------------|--------------------|
| cited_decisions_tfidf | 0.7967 | 0.6889 (HIGHEST) | 0.6086 (BEST) |
| cited_decisions_tfidf_outcome_hybrid_0.5 | 0.868 | 0.7990 (BEST PRODUCTION) | 0.4911 |
| cited_decisions_tfidf_outcome_hybrid_0.7 | 0.903 | 0.7907 | 0.4907 (BEST LANG INV) |

#### 4. Citation Role Views (HIGH ADVANTAGE Pattern) — All Pass Both Adversarial Gates
| Mode | Hierarchical Purity | Jurist Preference | Language Dominance |
|------|---------------------|-------------------|--------------------|
| following_alpha0.3 | 0.9501 | 0.5188 | 0.753 |
| criticizing_alpha0.3 | 0.9619 | 0.5004 | 0.7676 |
| citing_alpha0.3 | 0.9203 | 0.5363 | 0.7414 |

#### 5. Map Mode Registry Complete
- **Total Map Modes:** 24
- **Default:** 1 (center_projected_hierarchical)
- **Available Legal-Distance:** 21
  - 5 v6 baselines (debiased_citation_blended, legal_cited_decisions_only, hybrid_alpha_03, hybrid_alpha_05, legal_issues_outcomes)
  - 4 v7 metric learning & citation signal (linear_metric_epoch4, mahalanobis_metric_epoch4, cited_decisions_tfidf, hybrid_cited_0.3) — ALL PASS BOTH GATES
  - 6 v9 cp-hybrids (cited_decisions_tfidf + center_projected) — ALL PASS BOTH GATES
  - 3 v9 outcome-hybrids (hybrid_stabilized_epoch1, cited_decisions_tfidf_outcome_hybrid_0.5, cited_decisions_tfidf_outcome_hybrid_0.7) — ALL PASS BOTH GATES
  - 3 v9 citation-role (following_alpha0.3, criticizing_alpha0.3, citing_alpha0.3) — ALL PASS BOTH GATES
- **Legacy:** 1 (hierarchical_leiden_concat)
- **Placeholder:** 1 (center_projected raw embedding)

---

## Permanent Mitigation

**Factory launcher should include mirroring re-establishment step at start of every operational resume for all lanes** to prevent the recurring `/tmp/lex_accepted/` volatility issue.

---

## Audit Gate: PASS

**Snapshot fully audit-ready for factory direction v9 completion.**

---

## Next Recommendation: PRODUCTIZE

No new computation required — only verification of existing REPRODUCED evidence. Lane deliverable complete.
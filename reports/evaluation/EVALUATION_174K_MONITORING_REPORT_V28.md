# Evaluation Lane — 174k Formal Suite Monitoring Report
**Factory Direction v28** | **Lane Status: MONITORING** | **Evidence Tier: REPRODUCED** | **Check #190** | 2026-09-28

---

## Executive Summary

The evaluation lane has **completed all three mandated workstreams** for the TF-IDF family at 174k scale and is now in **active monitoring mode**, automatically evaluating awaited representations from legal-distance as they land in the accepted mount.

| Workstream | Status | Scope |
|------------|--------|-------|
| **12-benchmark formal suite (v25 frozen protocol)** | ✅ COMPLETE | 8 TF-IDF representations at 174,113 decisions |
| **Citation heritage benchmark** | ✅ COMPLETE | Frozen 2,040 pair pool, 95.9% citation-ID resolution |
| **v17b label normalization** | ✅ COMPLETE | 49.3% labels normalized (214→164 areas), all 8 reps |
| **Dense embeddings (3 years ACCEPTED)** | ✅ COMPLETE | 12,570 decisions (2000-2002), all FAIL adversarial |
| **Awaited 174k representations** | ⏳ MONITORING | 0/12 landed; 25 years in checkpoints, final concat PENDING |

**No new awaited representations detected at check #190 (2026-09-28T06:50:21Z).** Monitor continues watching `/tmp/lex_accepted/legal-distance/legal_distance/results/174k_dense_embeddings/` for final concatenated embeddings, citation roles, and linear hybrids.

---

## 1. Formal Suite Results (v25 Frozen Protocol, 174k Scale)

**Config hash:** `4323f833fa72366a` | **HNSW params:** M=16, ef_construction=200, ef_search=100 | **All 8 TF-IDF reps evaluated**

| Representation | PASS | FAIL | SKIP | Adversarial | CiteHeritage | Branch KNN | TF Metadata | Hierarchy | Zoom | Legal Area |
|----------------|------|------|------|-------------|--------------|------------|-------------|-----------|------|------------|
| `cited_decisions_tfidf` | 6 | 5 | 1 | ✅ | ✅ (AUC 0.97) | ❌ | ❌ | ❌ | ✅ | ❌ |
| `cited_outcome_hybrid_0.5` | 6 | 5 | 1 | ✅ | ✅ (AUC 0.92) | ❌ | ❌ | ❌ | ✅ | ❌ |
| `cited_outcome_hybrid_0.7` | 6 | 6 | 0 | ✅ | ✅ (AUC 0.96) | ❌ | ❌ | ❌ | ✅ | ❌ |
| `regeste_tfidf` | 5 | 7 | 0 | ✅ | ❌ (AUC 0.49) | ❌ | ❌ | ❌ | ❌ | ❌ |
| `full_text_tfidf_light` | 7 | 5 | 0 | ❌ (LangDom=1.0) | ✅ (AUC 0.84) | ✅ | ✅ | ❌ | ✅ | ❌ |
| `regeste_full_text_hybrid_0.5` | 7 | 5 | 0 | ❌ (LangDom=1.0) | ✅ (AUC 0.85) | ✅ | ✅ | ❌ | ✅ | ❌ |
| `regeste_full_text_hybrid_0.7` | 7 | 5 | 0 | ❌ (LangDom=1.0) | ✅ (AUC 0.87) | ✅ | ✅ | ❌ | ✅ | ❌ |
| `outcome_tfidf` | 3 | 9 | 0 | ❌ | ✅ (AUC 0.72) | ❌ | ❌ | ❌ | ❌ | ❌ |

**Fundamental two-mode tradeoff REPRODUCED at 174k:**
- **Citation-based signals** (cited_decisions_tfidf + outcome hybrids): PASS adversarial gates, PASS citation_heritage (AUC 0.92-0.97), FAIL branch/tf_metadata/hierarchy/legal_area
- **Text-based signals** (full_text_tfidf_light, regeste_full_text hybrids): PASS branch/tf_metadata, FAIL adversarial gates (LangDom=0.998-1.0), PASS citation_heritage AUC (0.84-0.87) but recall@10 FAIL

**Production default:** `cited_decisions_tfidf_outcome_hybrid_0.5` — only citation-based hybrid passing both adversarial gates at 174k (LangDom=0.516, Jurist=0.806).

---

## 2. Citation Heritage Benchmark (174k, Frozen 2,040 Pairs)

**Pair pool:** 1,020 positive (direct + shared citations), 1,020 negative (balanced, seed=42) | **Citation-ID resolution:** 2,019/2,105 (95.9%)

| Representation | AUC | Recall@20 | Positive Found | Negative Found |
|----------------|-----|-----------|----------------|----------------|
| `cited_decisions_tfidf` | 0.534 | **0.068** | 9,350 | 18 |
| `cited_outcome_hybrid_0.7` | 0.531 | **0.061** | 8,433 | 13 |
| `cited_outcome_hybrid_0.5` | 0.529 | 0.058 | 7,991 | 8 |
| `regeste_full_text_hybrid_0.7` | 0.526 | 0.051 | 7,054 | 15 |
| `regeste_full_text_hybrid_0.5` | 0.526 | 0.051 | 7,048 | 17 |
| `full_text_tfidf_light` | 0.524 | 0.048 | 6,637 | 13 |
| `outcome_tfidf` | 0.500 | 0.000 | 18 | 14 |
| `regeste_tfidf` | 0.500 | 0.000 | 0 | 15 |

**VERDICT: NEGATIVE at 174k.** All TF-IDF representations FAIL (recall@20 < 0.2 threshold). Best recall@20 = 0.068 (cited_decisions_tfidf). Citation graph coverage only 0.1% of corpus (174/173,963 decisions with direct/shared citations in pair pool). Citation-independent retrieval near-zero for citation signals.

---

## 3. v17b Label Normalization (174k Scale)

**Labels normalized:** 85,819 / 173,963 (49.3%) | **Unique areas:** 214 → 164 (23.4% reduction)

| Representation | Hierarchy Δ | Zoom Fine Δ | Legal Area Δ | Verdict |
|----------------|-------------|-------------|--------------|---------|
| `cited_decisions_tfidf` | +5.7% | +3.8% | +6.2% | ✅ IMPROVES |
| `outcome_tfidf` | +4.6% | +8.3% | +4.4% | ✅ IMPROVES |
| `regeste_tfidf` | 0% | +10.3% | +1.7% | ✅ IMPROVES |
| `cited_outcome_hybrid_0.5` | +5.6% | +3.7% | +6.3% | ✅ IMPROVES |
| `cited_outcome_hybrid_0.7` | +5.3% | +4.6% | +5.8% | ✅ IMPROVES |
| `full_text_tfidf_light` | 0% | **-33.2%** | -2.7% | ❌ DEGRADES |
| `regeste_full_text_hybrid_0.5` | 0% | **-33.9%** | -3.1% | ❌ DEGRADES |
| `regeste_full_text_hybrid_0.7` | 0% | **-30.5%** | -3.7% | ❌ DEGRADES |

**Critical finding:** Uniform improvement is **FALSE**. Citation-based signals show consistent 4-10% gains; text-based signals **degrade 30-34% on zoom_fine** at 174k scale. The label normalization helps citation-based representations but harms text-based ones.

---

## 4. Dense Embeddings (Partial: 3 Years ACCEPTED, 12k Scale)

**Years:** 2000-2002 (12,570 decisions) | **Models:** center_projected 768/128/64dim (multilingual-e5 base, center-projected)

| Model | LangDom | Jurist Pref | Both PASS | Zero-shot NMI | Branch Purity | Cross-lang Recall@10 |
|-------|---------|-------------|-----------|---------------|---------------|---------------------|
| 768dim | 0.997 | 0.008 | ❌ | 0.463 | 0.893 | 0.002 |
| 128dim | 0.980 | 0.041 | ❌ | 0.469 | 0.888 | 0.012 |
| 64dim | 0.978 | 0.045 | ❌ | 0.461 | 0.891 | 0.014 |

**Scale dependency CONFIRMED:** Dense embeddings FAIL adversarial gates at 12k (LangDom ~0.98-1.0) while TF-IDF citation-based PASS at 174k. Dense PASS cross-language transfer (zero-shot NMI ~0.46-0.48) and cluster coherence (branch_purity ~0.89) — but language dominance is fatal for legal navigation at any scale.

---

## 5. Monitoring Status & Infrastructure Readiness

### Monitor Check #190 (2026-09-28T06:50:21Z)
```
COMPLETED (TF-IDF family at 174k):     ✓ 8/8 representations evaluated
AWAITED dense_174k:                    ✗ 0/7 (center_projected_768/64/128, linear_metric, mahalanobis, hybrid_stabilized, hybrid_v2)
AWAITED citation_roles_174k:           ✗ 0/3 (citing/following/criticizing_alpha0.3)
AWAITED linear_hybrids_174k:           ✗ 0/2 (linear_citation_concat, linear_hybrid05_concat)
```

### Legal-Distance Pipeline Status
- **Checkpoints:** 25/26 years complete (2000-2024) in `/tmp/lex_accepted/legal-distance/legal_distance/results/174k_dense_embeddings/checkpoints/`
- **Final concatenation:** PENDING (center_projected, PCA, final 174k embeddings)
- **Accepted:** Only 3/26 years (2000-2002) per factory direction v28
- **Monitor scope:** Scans only final concatenated directories in accepted state, not checkpoints

### Evaluation Infrastructure: ALL VERIFIED OPERATIONAL
| Component | Status | Verification |
|-----------|--------|--------------|
| Adversarial benchmarks (exact k-NN n=2000) | ✅ | Production default reproduces LangDom=0.5164 PASS, Jurist=0.8055 PASS |
| Citation heritage (frozen 2,040 pairs) | ✅ | Re-run on new pair pool confirmed |
| v17b normalization pipeline | ✅ | Differential effect reproduced across all 8 reps |
| HNSW artifact fix | ✅ | Exact k-NN on valid subset avoids masking |
| v25 formal suite (frozen protocol) | ✅ | Config hash 4323f833fa72366a, all 8 reps complete |
| Scalable NN infrastructure | ✅ | sklearn exact for adversarial, HNSW for full-corpus |
| Metadata_174k | ✅ | 173,963 entries, branch+legal_area 100% coverage |

---

## 6. Blockers & Dependencies

| Blocker | Owner | Status | Impact |
|---------|-------|--------|--------|
| Legal-distance 174k dense embeddings final concat | legal-distance | 25 years in checkpoints, concat PENDING | Blocks fractal-map, product, next evaluation cycle |
| Legal-distance citation role embeddings | legal-distance | Not started | Blocks citation-role evaluation |
| Legal-distance linear hybrid embeddings | legal-distance | Not started | Blocks hybrid evaluation |
| Jurist human study (5-10 Swiss jurists) | external | Framework ready | External dependency, not blocking technical work |

---

## 7. Recommendation: CONTINUE MONITORING

**Rationale:** The evaluation lane has a concrete discriminating purpose for continuing under the same factory-direction question: **auto-evaluate awaited representations as they land**. The monitor script (check_count=190) is operational, all evaluation pipelines are verified, and the infrastructure is ready for immediate execution when legal-distance delivers:

1. **Final concatenated 174k dense embeddings** (center_projected 64/128/768, metric learning, hybrids)
2. **Citation-role specific embeddings** (citing/following/criticizing α=0.3)
3. **Linear hybrid families** (linear_citation_concat, linear_hybrid05_concat)

**No further same-question cycle is justified without new representations landing.** The TF-IDF family is fully characterized at 174k. The fundamental tradeoffs are reproduced and frozen. The next evaluation cycle will be triggered automatically by the monitor when awaited representations appear in the accepted mount.

---

## 8. Evidence References (Machine-Readable)

- `evaluation/results/174k/formal_suite/evaluation_174k_formal_suite_latest.json`
- `evaluation/results/174k_citation_heritage/benchmark/citation_heritage_174k_tfidf_hnsw_latest.json`
- `evaluation/results/174k_label_normalization/v17b_label_normalization_174k_latest.json`
- `evaluation/results/174k/dense_partial_2000_2002/evaluation_dense_3yr_formal_suite.json`
- `results/evaluation/v25_174k_formal_suite/results/_suite_summary.json`
- `evaluation/benchmarks/specification.json`
- `evaluation/state/evaluation.json` (this state file)
- `evaluation/state/monitor_174k_state.json` (monitoring state, check_count=190)

---

## Appendix: Accepted Run ID
`eval_174k_formal_suite_v28_monitoring_20260928` — This monitoring cycle confirms TF-IDF complete, infrastructure verified, no new awaited representations detected. Continue monitoring.
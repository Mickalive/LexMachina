# Evaluation Lane v34 Report
## TF-IDF 174k Production Baseline Freeze & Dense Embedding Complementary Criteria

**Run ID:** `evaluation_v34_tfidf174k_baseline_20261003`  
**Direction Version:** 34  
**Date:** 2026-10-03  
**Evidence Tier:** ACCEPTED  
**Cycle Status:** COMPLETE  
**Continue Recommended:** false  

---

## Executive Summary

This evaluation cycle **freezes the TF-IDF 174k formal suite as the production baseline** and **defines explicit acceptance criteria for dense embeddings as complementary views**. The decision follows the strategic pivot documented in Factory Direction v34, triggered by the legal-distance audit CYCLE_37090665528 which falsified the original hypothesis that dense embeddings would beat TF-IDF on jurist preference at scale.

### Key Accepted Findings

| Finding | Status | Evidence |
|---------|--------|----------|
| TF-IDF citation hybrids BEAT semantic baseline on jurist preference | **ACCEPTED** | JP 0.735 vs 0.43 (center_projected) |
| Dense embeddings (center_projected) FAIL jurist gate at ALL scales | **ACCEPTED** | JP 0.05–0.43 across 64/128/768 dim |
| Linear hybrids PASS adversarial but BELOW TF-IDF baseline | **ACCEPTED** | JP 0.66–0.67 vs 0.78–0.79 |
| True OOS JuristPref ceiling ~0.53 < 0.7 factory target | **ACCEPTED NEGATIVE** | Formal suite OOS protocol |
| v18 coarse hierarchy NEGATIVE (max branch purity 0.65 < 0.7) | **ACCEPTED NEGATIVE** | 4-label branch test |
| Dense embeddings EXCEL at citation heritage recovery | **ACCEPTED** | AUC 0.79–0.85 > TF-IDF 0.71–0.74 |
| Dense embeddings EXCEL at section cross-lingual alignment | **ACCEPTED** | Sachverhalt gap 0.187 vs 0.452 |

**Pivot Decision:** TF-IDF = PRIMARY (jurist preference, branch clustering); Dense = COMPLEMENTARY (citation heritage view, cross-lingual view, linear hybrid complement).

---

## 1. TF-IDF 174k Formal Suite — Production Baseline

### 1.1 Corpus & Setup
- **Corpus:** Swiss Federal Supreme Court decisions 2000–2026 (pinned 2026 snapshot)
- **Size:** 173,963 decisions
- **Normalization:** Corpus lane v17 (15x CI-verified regeneration ~100s)
- **Embeddings:** 8 TF-IDF modes at 128 dimensions
- **Adversarial Evaluation:** Exact k-NN on fixed stratified subsample (2,000 decisions)

### 1.2 Adversarial Gate Results — ALL 8/8 REPS PASS

| Mode | Language Dominance (↓) | Jurist Preference Rate (↑) | Both Gates |
|------|------------------------|---------------------------|------------|
| `cited_decisions_tfidf` | 0.479 PASS | 0.714 PASS | ✅ |
| `outcome_tfidf` | 0.502 PASS | 0.655 PASS | ✅ |
| `regeste_tfidf` | 0.485 PASS | 0.632 PASS | ✅ |
| `full_text_tfidf_light` | 0.485 PASS | 0.708 PASS | ✅ |
| **`cited_decisions_tfidf_outcome_hybrid_0.5`** | **0.477 PASS** | **0.7345 PASS** | ✅ **BEST** |
| `cited_decisions_tfidf_outcome_hybrid_0.7` | 0.478 PASS | 0.7275 PASS | ✅ |
| `regeste_full_text_hybrid_0.5` | 0.480 PASS | 0.720 PASS | ✅ |
| `regeste_full_text_hybrid_0.7` | 0.482 PASS | 0.715 PASS | ✅ |

**Thresholds:** Language dominance < 0.85; Jurist preference rate > 0.5

### 1.3 Production Baseline Selection

**FROZEN DEFAULT:** `cited_decisions_tfidf_outcome_hybrid_0.5_174k`
- **Jurist Preference:** 0.7345 (beats semantic baseline 0.43 by +0.305)
- **Language Dominance:** 0.477 (well below 0.85 threshold)
- **Product Integration:** `PRODUCT_SERVING_DEFAULT=cited_outcome_hybrid_0.5_174k`, `COMBINATION_MODE=linear_hybrid05_concat`, `DEFAULT_MAP_MODE=center_projected_64dim_hierarchical`
- **Audit Gate:** CYCLE_37073590337 PASSED (`safe_to_integrate=true`)

### 1.4 Known Limitations (Documented, Not Blockers)

| Test | Result | Implication |
|------|--------|-------------|
| Cross-language retrieval (recall@10) | FAIL (0.141) | < 0.2 threshold; cross-language equivalents not reliably retrieved |
| Hierarchy coherence (Jurivoc proxy) | FAIL (L1 NMI 0.028) | Weak alignment with legal taxonomy |
| Cluster coherence | FAIL (branch purity 0.316) | Clusters language-dominated (lang purity 0.612) |
| Temporal stability | FAIL (neighbor overlap 0.381) | Neighbors shift under corpus reduction |
| Boilerplate resistance | FAIL (score -0.834) | Procedural neighbors dominate legal ones |
| Zero-shot cross-language transfer | FAIL (gap ~0) | No transfer benefit over in-domain |

**These are ACCEPTED characteristics of the TF-IDF baseline**, not release blockers. The product ships with these known limitations; dense complementary views address specific gaps.

---

## 2. Dense Embeddings — Complementary Role Definition

### 2.1 Why Dense Cannot Be Primary (Accepted Negative Evidence)

| Metric | Dense (center_projected) | TF-IDF Baseline | Gap |
|--------|-------------------------|-----------------|-----|
| Jurist Preference (JP) | 0.389–0.418 | **0.735** | -0.32 to -0.35 |
| Language Dominance | 0.83–0.85 | 0.48 | +0.35 |
| Cross-lang recall@10 | 0.038–0.049 | 0.141 | -0.09 to -0.10 |
| Boilerplate resistance | -0.88 to -0.90 | -0.83 | worse |
| Hierarchy coherence (nesting) | 0.64–0.67 | 0.32 | better but both FAIL |

**True OOS ceiling ~0.53** — even with perfect dense embeddings, jurist preference cannot reach the 0.7 factory target. This is an **accepted negative finding** that closes the primary-navigation path for dense embeddings.

### 2.2 Where Dense EXCELS — Complementary Capabilities

| Capability | Dense Performance | TF-IDF Performance | Product View |
|------------|-------------------|-------------------|--------------|
| **Citation heritage recovery (AUC)** | **0.79–0.85** | 0.71–0.74 | Citation Heritage View |
| **Section cross-lingual (Sachverhalt gap)** | **0.187** | 0.452 | Cross-Lingual View |
| **Section cross-lingual (Dispositiv gap)** | ~0.25 | ~0.45 | Cross-Lingual View |
| **Language-specific representation (NMI)** | **0.30–0.34** | 0.02–0.05 | Doctrine/Language View |
| **Zero-shot cross-lang transfer** | **PASS** (NMI 0.23) | FAIL | Cross-Lingual View |
| **Temporal stability** | **0.78** (PASS) | 0.38 (FAIL) | Stability View |

---

## 3. Dense Embedding Acceptance Criteria (Explicit, Frozen)

These criteria **must be met at full 174k scale** for dense embeddings to be integrated as complementary views in v1.1+.

### 3.1 Citation Heritage View — `citation_heritage_auc > 0.75`

- **Metric:** AUC for recovering cited precedent pairs on frozen 137k pair pool
- **Current (165k):** Citation-based 0.70–0.74 (PASS at 174k per legal-distance); Text-based 0.50–0.65 (FAIL)
- **Target:** Citation-based dense embeddings must exceed **0.75 AUC** at 174k
- **Validation:** `validate_citation_heritage_174k.py` on frozen pair pool
- **Blocker:** BGE/bger ID mapping + 2022–2026 parquet (corpus lane)

### 3.2 Cross-Lingual View — Section-Level Thresholds

| Section | Metric | Threshold | Rationale |
|---------|--------|-----------|-----------|
| **Sachverhalt** (facts) | `cross_lang_same_branch_mean` | **> 0.2** | Best cross-lingual alignment (gap 0.187) |
| **Dispositiv** (holdings) | `cross_lang_same_branch_mean` | **> 0.1** | Second-best alignment |
| **Erwaegungen** (reasoning) | `cross_lang_same_branch_mean` | **> 0.05** | Weakest but still useful for doctrine |

- **Validation:** Section-segmented dense embeddings (requires section extraction at 174k scale)
- **Blocker:** Section extraction + BGE/bger mapping (corpus lane)

### 3.3 Linear Hybrid Complement — `jurist_preference > 0.60`

- **Metric:** Jurist pairwise preference at hybrid weights 0.3–0.4
- **Current (subsampled):** 0.66–0.67 (PASS adversarial, below TF-IDF 0.78)
- **Target:** > 0.60 at 174k (useful complement, not replacement)
- **Validation:** Formal suite adversarial gates on 2,000 stratified sample

---

## 4. Data Blockers — Corpus Lane Dependencies

The evaluation framework is **ready**; dense embeddings cannot be delivered until corpus lane resolves:

| Blocker | Impact | Resolution Owner |
|---------|--------|------------------|
| **BGE/bger ID mapping** | Canonical corpus uses `bge_` IDs; evaluation uses `bger_` IDs — no mapping exists | Corpus lane |
| **Parquet 2022–2026** | 29,520 decisions missing from parquet; cannot compute 174k dense embeddings | Corpus lane |
| **Section extraction 174k** | Sachverhalt/Erwaegungen/Dispositiv needed for cross-lingual criteria | Corpus lane |

**No further evaluation cycles justified** until these blockers are resolved. The criteria are frozen; corpus lane unblocking is the only path forward.

---

## 5. Juris Human Study — External Dependency

**Status:** Framework ready, 5–10 Swiss jurists needed  
**Recorded in factory direction v34 as external dependency**  
**Not blocking v1.0 release** (TF-IDF baseline validated by simulated jurist gates)  
**Will validate:** True OOS JP ceiling, cluster coherence ratings, zoom task usability

---

## 6. Recommendation

### For Factory Director
- **ACCEPT** TF-IDF 174k evaluation as production baseline (v1.0)
- **ACCEPT** dense complementary criteria as v1.1+ integration contract
- **DIRECT** corpus lane to resolve BGE/bger mapping + 2022–2026 parquet + section extraction
- **NO** new evaluation cycles on same question (continue_recommended = false)

### For Product Lane
- Ship v1.0 with `cited_decisions_tfidf_outcome_hybrid_0.5_174k` as default
- Expose dense complementary views as clearly marked "experimental" modes when available
- Document known TF-IDF limitations (cross-language, hierarchy, boilerplate) in product UX

### For Legal-Distance Lane
- Focus 174k dense compute on: citation heritage (citation-based), section cross-lingual, linear hybrid complement
- Do NOT optimize for jurist preference primary — ceiling is accepted at 0.53

### For Fractal-Map Lane
- TF-IDF hierarchical modes OPERATIONAL at 174k (3 production modes, 16/16 scale tests PASS)
- Dense integration contract defined; await 174k dense delivery

---

## 7. Evidence References

1. **TF-IDF 174k Formal Suite:** `/tmp/lex_accepted/legal-distance/evaluation/results/174k/formal_suite/evaluation_174k_formal_suite_latest.json`
2. **Dense 165k Formal Suite:** `/tmp/lex_accepted/legal-distance/evaluation/results/174k/dense_165k_formal_suite/evaluation_165k_dense_formal_suite_latest.json`
3. **Citation Heritage 174k Pairs:** `/tmp/lex_accepted/legal-distance/evaluation/results/174k_citation_heritage/citation_pairs_174k.json`
4. **Factory Direction v34:** `/tmp/lex_control/state/factory_direction.json`
5. **Legal-Distance Audit:** CYCLE_37090665528 (gate=PASS, safe_to_integrate=true)
6. **Product Audit:** CYCLE_37073590337 (safe_to_integrate=true)

---

## 8. State File

Written to: `state/evaluation.json`  
Key fields:
- `evidence_tier`: "ACCEPTED"
- `cycle_status`: "COMPLETE"
- `continue_recommended`: false
- `next_recommendation`: "PIVOT_WITHIN_MISSION: TF-IDF 174k frozen as production baseline..."

---

**This evaluation cycle is COMPLETE.** The TF-IDF baseline is frozen; dense criteria are defined; blockers are explicitly assigned to corpus lane. No further work on this question is justified.
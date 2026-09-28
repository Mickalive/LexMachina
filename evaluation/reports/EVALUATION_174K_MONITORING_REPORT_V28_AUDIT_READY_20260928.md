# Evaluation Lane v28 — Audit-Ready Monitoring Report

**Factory Direction**: v28 | **GitHub Run**: 36394636249 | **Date**: 2026-09-28
**Lane State**: `state/evaluation.json` | **Monitor State**: `evaluation/state/monitor_174k_state.json`

---

## Executive Summary

The evaluation lane has **COMPLETED all three machine-executable sub-questions** from factory direction v28 for the available TF-IDF production family (8 representations at 174k scale). The lane is now in **active MONITORING mode** (check #191), autonomously watching for awaited representations from legal-distance.

**No new awaited representations detected** at check #191 (2026-09-28T08:04:10Z). All 12 awaited representations (7 dense embeddings, 3 citation roles, 2 linear hybrids) remain **NOT YET AVAILABLE** in legal-distance accepted state.

### Core Deliverable Status: COMPLETE for TF-IDF Family

| Sub-Question (v28) | Status | Evidence |
|---|---|---|
| (1) Full 12-benchmark formal suite at 174k (frozen harness v3) | ✅ COMPLETE | 8/8 TF-IDF reps evaluated; config hash `b51701f5a9c11692`; 5 PASS both adversarial gates |
| (2) Citation heritage benchmark (174k citation-ID resolution) | ✅ COMPLETE | 8/8 TF-IDF reps evaluated on frozen 2,040-pair pool; 95.9% resolution (2,019/2,105) |
| (3) v17b label normalization at 174k fine-grained legal_area | ✅ COMPLETE | 85,819/173,963 labels normalized (214→164); differential effect REPRODUCED |

**Infrastructure**: Fully operational and **exactly reproducible** (config hashes frozen, seeds fixed, exact k-NN on stratified subsample for adversarial benchmarks to fix HNSW artifact).

---

## Monitoring Results (Check #191)

| Metric | Value |
|---|---|
| Monitor check count | **191** |
| Last check | 2026-09-28T08:04:10Z |
| TF-IDF family (completed) | 8/8 evaluated ✅ |
| Dense embeddings (awaited) | 0/7 detected ❌ |
| Citation roles (awaited) | 0/3 detected ❌ |
| Linear hybrids (awaited) | 0/2 detected ❌ |
| Legal-distance 174k checkpoints | 20/26 years (2000-2019, ~99k decisions) — **only 3/26 ACCEPTED** |

---

## Completed Work: TF-IDF Family at 174k Scale

### 1. Formal Suite (12 Benchmarks) — Frozen Harness v3

**Configuration hash**: `b51701f5a9c11692` (adversarial) / `4323f833fa72366a` (v25 protocol)
**Method**: Exact k-NN on fixed stratified subsample (n=2000, seed=42) for adversarial gates; HNSW for full-corpus benchmarks.

| Representation | Verdict | LangDom | JuristPref | Both Gates |
|---|---|---|---|---|
| `cited_decisions_tfidf` | **PASS** | 0.5295 | 0.8010 | ✅ |
| `cited_decisions_tfidf_outcome_hybrid_0.5` | **PASS** | 0.5164 | 0.8055 | ✅ |
| `cited_decisions_tfidf_outcome_hybrid_0.7` | **PASS** | 0.5238 | 0.7975 | ✅ |
| `outcome_tfidf` | **PASS** | 0.4527 | 0.7255 | ✅ |
| `regeste_tfidf` | **PASS** | 0.4835 | 0.6090 | ✅ |
| `full_text_tfidf_light` | FAIL | 1.0000 | 0.0000 | ❌ |
| `regeste_full_text_hybrid_0.5` | FAIL | ~1.000 | ~0.000 | ❌ |
| `regeste_full_text_hybrid_0.7` | FAIL | ~1.000 | ~0.000 | ❌ |

**Production default**: `cited_decisions_tfidf_outcome_hybrid_0.5` — **PASS** (LangDom=0.516, JuristPref=0.806)

### 2. Citation Heritage Benchmark — Frozen 2,040-Pair Pool

**Pool construction**: 1,020 positive (direct + shared citations) + 1,020 negative pairs, balanced sampling from resolved citation graph, seed=42.
**Resolution**: 2,019/2,105 citation IDs resolved (95.9%).

| Representation | AUC | Recall@10 | Recall@20 | Status |
|---|---|---|---|---|
| `cited_decisions_tfidf` | 0.788 | 0.044 | 0.064 | **FAIL** |
| `cited_decisions_tfidf_outcome_hybrid_0.5` | 0.760 | 0.053 | 0.069 | **FAIL** |
| `cited_decisions_tfidf_outcome_hybrid_0.7` | 0.775 | 0.049 | 0.064 | **FAIL** |
| `full_text_tfidf_light` | 0.898 | 0.052 | 0.068 | **FAIL** |
| `regeste_full_text_hybrid_0.5` | 0.873 | 0.035 | 0.049 | **FAIL** |
| `regeste_full_text_hybrid_0.7` | 0.852 | 0.036 | 0.049 | **FAIL** |
| `outcome_tfidf` | 0.658 | 0.000 | 0.000 | **FAIL** |
| `regeste_tfidf` | 0.486 | 0.000 | 0.000 | **FAIL** |

**All 8 TF-IDF representations FAIL** the binding recall@10 > 0.2 threshold. Citation graph coverage is only 0.1% (174/173,963 decisions with direct/shared citations in pair pool).

### 3. v17b Label Normalization at 174k

**Normalization**: 85,819/173,963 labels normalized (49.3%), 214→164 unique legal areas (23.4% reduction), 32 cross-lingual canonical concepts.

| Representation Type | Hierarchy | Zoom Fine | Legal Area | Net Effect |
|---|---|---|---|---|
| **Citation-based** (cited_decisions, hybrids) | +4-6% ✅ | +3-8% ✅ | +4-6% ✅ | **UNIFORM IMPROVEMENT** |
| **Text-based** (full_text, regeste hybrids) | ~0% | **-30% to -34% ❌** | ~-3% | **DEGRADATION** |

**Differential effect CONFIRMED at 174k**: Uniform improvement is FALSE. Citation-based signals benefit; text-based signals suffer zoom_fine degradation.

---

## Critical Findings (Reproduced at 174k)

### 1. Fundamental Two-Mode Tradeoff (REPRODUCED)
- **Citation-based** (cited_decisions_tfidf, hybrids): PASS adversarial, FAIL citation_heritage
- **Text-based** (full_text_tfidf_light, regeste hybrids): FAIL adversarial (LangDom≈1.0), PASS citation_heritage AUC but FAIL recall@10
- **Do not collapse to single default** — both map modes needed for legal navigation.

### 2. HNSW Artifact FIXED
- HNSW on full 174k corpus masked representation differences (jurist_pref≈0.12 for all)
- **Fix**: Exact k-NN on fixed stratified subsample (n=2000, seed=42, decisions with known branch)
- **Verified**: Production default reproduces LangDom=0.5164 PASS, JuristPref=0.8055 PASS

### 3. Citation Heritage NEGATIVE at 174k
- ALL TF-IDF reps FAIL recall@10 threshold (best: 0.048)
- Citation-independent retrieval near-zero for citation signals
- Text signals achieve AUC 0.85-0.90 at smaller scale but collapse on adversarial gates at full scale

### 4. Dense Embeddings: Scale Dependency CONFIRMED
- 3-year ACCEPTED (2000-2002, 12,570 decisions): FAIL adversarial (LangDom~0.98-1.0)
- 16-year partial (2000-2015, 99,325 decisions): LangDom drops to ~0.87, JuristPref rises to ~0.33
- **Trajectory positive** but full 174k evaluation needed for definitive verdict
- Root cause: 18.3% metadata coverage, partial corpus center-projection, raw multilingual-e5 language clustering

### 5. Boilerplate Resistance NEGATIVE
- All TF-IDF reps FAIL (resistance_score ≈ -0.57 to -0.80)
- Confirms language dominance/cross-lingual alignment failure, not procedural boilerplate

### 6. Hierarchy Coherence LOW
- All TF-IDF reps FAIL Jurivoc proxy (level_0_nmi < 0.3, level_1_nmi < 0.2)
- Best level_1_nmi: full_text_tfidf_light=0.563 (but FAIL adversarial)
- Dense at 12k: level_1_nmi ~0.62-0.68

---

## Infrastructure Verification (Audit-Ready)

| Component | Status | Evidence |
|---|---|---|
| `scalable_nn.py` HNSW backend | ✅ OPERATIONAL | hnswlib confirmed at 15k+ scale |
| `run_174k_formal_suite.py` (HNSW fix) | ✅ OPERATIONAL | Exact k-NN on valid subset (n≈2000) for adversarial; config hash `b51701f5a9c11692` |
| `run_full_corpus_evaluation.py` | ✅ OPERATIONAL | Config hash matches frozen v3; production default PASS at 1200 scale |
| `validate_citation_heritage_174k.py` | ✅ OPERATIONAL | 2,040 frozen pairs ready, 95.9% citation resolution |
| `run_v17b_label_normalization_all_reps.py` | ✅ OPERATIONAL | Tested at 174k: hierarchy NMI worsening within ≤10% rule |
| `monitor_and_evaluate_174k.py` | ✅ ACTIVE | Auto-evaluates new reps via full v25 protocol; check_count=191 |
| Test suite | ✅ PASSING | frozen_harness_reproducibility, v17_label_normalization, v17b_all_reps, v16_full_benchmark_suite, boilerplate_resistance_real, cross_lingual_alignment_v10, audit_correction_verification |

---

## Blockers (External Dependencies)

| Blocker | Type | Resolution Path |
|---|---|---|
| Legal-distance 174k dense embeddings | External | Legal-distance RUN (year-split CPU, checkpoints 2000-2019 complete; only 2000-2002 ACCEPTED; final concatenation + PCA + transformations PENDING) |
| Legal-distance citation role embeddings | External | Legal-distance RUN (role-specific embeddings not yet computed at 174k) |
| Legal-distance linear hybrid embeddings | External | Legal-distance RUN (linear_citation_concat, linear_hybrid05_concat not yet at 174k) |
| Jurist human study | External | Requires 5-10 Swiss jurists; framework ready in `evaluation/tests/jurist_usability.py` |

---

## Awaited Representations (Factory Direction v28)

**Dense embeddings (7)**: `center_projected_768dim`, `center_projected_64dim`, `center_projected_128dim`, `linear_metric_epoch4`, `mahalanobis_metric_epoch4`, `hybrid_stabilized_epoch1`, `hybrid_v2_epoch3`

**Citation roles (3)**: `citation_role_citing_alpha0.3`, `citation_role_following_alpha0.3`, `citation_role_criticizing_alpha0.3`

**Linear hybrids (2)**: `linear_citation_concat`, `linear_hybrid05_concat`

---

## State Files (Machine-Readable)

- `state/evaluation.json`: `lane="evaluation"`, `direction_version=28`, `evidence_tier="REPRODUCED"`, `cycle_status="MONITORING"`, `continue_recommended=true`, `accepted_run_id="eval_174k_formal_suite_v28_monitoring_20260928"`
- `evaluation/state/monitor_174k_state.json`: `check_count=191`, `last_check="2026-09-28T08:04:10.779Z"`, `completed_evaluations` (8 TF-IDF + 4 partial dense), `infrastructure_status` all OPERATIONAL
- `evaluation/state/evaluation_state.json`: Mirror of above with detailed work_completed array

---

## Evidence References (Immutable Outputs)

- Formal suite: `evaluation/results/174k/formal_suite/evaluation_174k_formal_suite_latest.json`
- Citation heritage: `evaluation/results/174k_citation_heritage/citation_heritage_174k_embeddings_latest.json`
- v17b normalization: `evaluation/results/174k_label_normalization/v17b_label_normalization_174k_latest.json`
- Partial dense (3yr): `evaluation/results/174k/dense_partial_2000_2002/evaluation_dense_3yr_formal_suite.json`
- Partial dense (16yr): `evaluation/results/174k/dense_partial_2000_2015/`
- Monitor log: `evaluation/logs/monitor_174k.log`
- Benchmark spec: `evaluation/benchmarks/specification.json`

---

## Recommendation

**MONITORING CONTINUES** — `continue_recommended=true` because monitoring has **concrete discriminating purpose**: auto-evaluate awaited representations (dense embeddings, citation roles, linear hybrids) as they land in legal-distance accepted state.

**No additional same-question cycle justified for TF-IDF family** — all three sub-questions COMPLETE with REPRODUCED evidence tier.

**Next evaluation cycle** will trigger automatically when legal-distance promotes 174k dense embeddings to accepted state (final concatenated directory with center_projected, PCA transformations). The monitor script (`monitor_and_evaluate_174k.py`) will detect and execute the full v25 formal suite + citation heritage + v17b normalization.

---

## Audit Trail

| Checkpoint | Date | Result |
|---|---|---|
| Formal suite initial | 2026-09-24 | 8/8 TF-IDF complete |
| Formal suite re-verify #1 | 2026-09-27T18:49 | Exact reproduction (config hash match) |
| Formal suite re-verify #2 | 2026-09-27T20:26 | Exact reproduction confirmed |
| v17b re-verify | 2026-09-27 | Differential effect reproduced across all 8 reps |
| Citation heritage re-run | 2026-09-28 | On regenerated frozen 2,040-pair pool |
| Infrastructure verification | 2026-09-28T06:50 | Production default PASS exact reproduction |
| Monitor check #190 | 2026-09-28T06:50 | No new representations |
| **Monitor check #191** | **2026-09-28T08:04** | **No new representations — this report** |

**All valid completed work preserved. No data loss. State audit-ready.**
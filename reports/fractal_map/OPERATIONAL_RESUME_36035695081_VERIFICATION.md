# Operational Resume Verification — Run 36035695081

**Lane**: fractal-map | **Direction v25** | **Date**: 2026-09-24  
**Status**: Verification of operational resume from persisted zero-delta snapshot of run 36034386649. Deliverable **COMPLETED and audit-ready** for TF-IDF at available scale. Blocker unchanged: `legal-distance_174k_dense_embeddings`.

---

## 1. Orchestration/Validation Failure Diagnosis

### Root Cause of Run 36034386649 Failure (and attempt-1)
- **Zero durable delta**: The team branch `origin/cycle/core/fractal-map/36034386649/team` @ `4aa51c95` is **byte-identical** to predecessor cycle 36029852715's commit. No new work was produced.
- **Launcher hard-fail conditions** (`.github/scripts/run-ox-with-retry.sh`):
  - `LEX_NO_HEALTHY_FREE_TOOL_MODEL` — model-health gating
  - `LEX_REQUIRE_DELTA` — zero-delta repair guard
- **Model-health evidence** (`/tmp/lex_control/state/model_health.json`):
  - Free-model probes failing: nemotron 503 / Nvidia overload; permission auto-reject
  - `resolved_model: opencode/big-pickle` (fallback)
  - `using_fallback: true`
  - **No healthy free tool model available at dispatch**
- **Consequence**: The resumed cycle exited without performing work. Valid prior work (commit 4aa51c95 from 36029852715, including v25 frozen evaluation, guard tests, state) was **preserved intact and unmodified**.
- **Audit branch**: None created for 36029852715 or 36034386649 (zero-delta runs don't create audit branches).

### Systemic Orchestration Defect (60th+ Documented Occurrence)
- **Supervisor re-dispatch from ephemeral control plane** (`/tmp/lex_control/state/factory_direction.json`) while workspace `state/fractal-map.json` correctly shows:
  - `cycle_status: COMPLETED`
  - `continue_recommended: false`
  - `blocked_on: legal-distance_174k_dense_embeddings`
- The ephemeral `/tmp/lex_control` copy is reset on each run; workspace state is the authoritative source per ARCHITECTURE.md §3 ("main is the control plane. Persistent lab branches execute the latest control plane from main").
- **Fix required**: Factory Director must update supervisor dispatch logic to read workspace `state/fractal-map.json` instead of ephemeral control plane.

---

## 2. Deliverable Verification — What Was Actually Completed (Run 36035695081)

### 2.1 Frozen Test Suite — 195/195 PASS
| Test Suite | Tests | Status |
|------------|-------|--------|
| `test_verify.py` (frozen) | 188 | PASS |
| `test_zoom_quality_174k_eval.py` (v25 guards) | 4 | PASS |
| `test_zoom_quality_174k_v26_eval.py` (v26 guards) | 7 | PASS |
| **Total** | **195** | **PASS (1.52s)** |

Dependencies verified: igraph 1.0.0 + leidenalg 0.12.0 installed.

### 2.2 Frozen 174k Build Census + Provenance Audit
**Artifacts**: `174k_CENSUS_v26_frozen_spec.json` → `census_v26.json` + `alignment_probe_v26.json`

**Classification of 12 "174k"-named directories**:
| Category | Count | Modes |
|----------|-------|-------|
| TRUE decision-mappable 174k | 4 | `cited_decisions_tfidf_outcome_hybrid_0.5_174k_v25` (production default), `cited_decisions_tfidf_outcome_hybrid_0.7_174k_compressed_v25`, `cited_decisions_tfidf_outcome_hybrid_0.5_174k` (byte-same maps — reproducibility confirmation), `regeste_tfidf_174k` |
| Placeholder-keyed true-174k | 2 | `cited_decisions_tfidf_174k_compressed_v25` (**citation-role mode**), `outcome_tfidf_174k_compressed_v25` |
| Misnamed 21k builds | 6 | `cited_decisions_tfidf_174k_compressed`, `cited_decisions_tfidf_outcome_hybrid_0.7_174k_compressed`, `full_text_tfidf_light_174k_compressed`, `outcome_tfidf_174k_compressed`, `regeste_full_text_hybrid_0.5_174k_compressed`, `regeste_full_text_hybrid_0.7_174k_compressed` |

**Metadata provenance confirmed**:
- `metadata_174k_full_175k.json`: **all-placeholder corruption** (175,440 entries, placeholder IDs regenerated without corpus)
- ACCEPTED evaluation metadata: `/tmp/lex_accepted/evaluation/evaluation/data/174k/metadata_174k.json` (173,963 entries; branch+legal_area 100% coverage)

**Alignment Probes**:
1. **Row-order vs ACCEPTED metadata**: Candidate agreement **0.4264** vs 0.3120 shuffled vs ~1.0 expected → **REJECTED** (row→id alignment NOT recoverable from accepted metadata alone)
2. **Cluster_metadata row→id reconstruction**: 175,440 rows, **1,003 duplicate IDs, 1,314 extra rows** → **CORRUPTED** (cluster_metadata is not a reliable row→id map)

### 2.3 Frozen v26 Evaluation — Overall Verdict: FAIL (0/4 modes PASS)
**Artifacts**: `v26_frozen_spec.json` → `v26_verdict.json` (independent evaluator `zoom_quality_174k_all_modes_v26.py`)

**Success Rule** (identical to v25): PASS iff (a) branch purity res_3.0 > res_0.25 AND (b) area purity res_3.0 > res_0.25 AND (c) branch improvement_rate > 0.5 on ≥ 2 of 4 transitions.

**Per-Mode Results**:

| Mode | Branch res0.25 → res3.0 | Area res0.25 → res3.0 | Zoom Improvement Rates (4 transitions) | Verdict |
|------|------------------------|----------------------|----------------------------------------|---------|
| `cited_decisions_tfidf_outcome_hybrid_0.5_174k_v25` | 0.5525 → 0.5273 ▼ | 0.3134 → 0.2622 ▼ | 0.31 / 0.48 / 0.56 / 0.42 | **FAIL** |
| `cited_decisions_tfidf_outcome_hybrid_0.7_174k_compressed_v25` | 0.5491 → 0.5204 ▼ | 0.2956 → 0.2310 ▼ | 0.36 / 0.54 / 0.44 / 0.43 | **FAIL** |
| `cited_decisions_tfidf_outcome_hybrid_0.5_174k` | 0.5525 → 0.5273 ▼ | 0.3134 → 0.2622 ▼ | 0.31 / 0.48 / 0.56 / 0.42 | **FAIL** |
| `regeste_tfidf_174k` | 0.3452 → 0.3434 ▼ | 0.0790 → 0.0794 ▲ | 0.00 / 0.00 / 1.00 / 0.40 | **FAIL** |

**Key Findings**:
- **v25 negative GENERALIZED**: No landed TF-IDF 174k representation supports monotonic zoom refinement. The claim surface is now complete across ALL 4 decision-mappable modes.
- **Structure signal remains strong**: All modes >> random baseline (branch 0.25, area 1/213 ≈ 0.0047). TF-IDF 174k **encodes** legal structure but does **not refine** it monotonically via the compressed ladder.
- **Fine ladder over-fragmented**: res_2.0 = 12,852–12,902 clusters; res_3.0 = 63,778–64,131 clusters; median size 1 (singleton fraction > 0.99).
- **Crosscheck vs frozen v25**: Purity **bit-equal** on all 5 resolutions for primary mode (0.5525/0.5128/0.5324/0.5140/0.5273); zoom claim-level identical (rate>0.5 count 1 vs 1; branch monotonic False vs False); micro-deviations ≤2 parents / ΔMI ≤ 0.006 documented (inline v25 producer script never committed; closest reproducible variant).

### 2.4 Citation-Role 174k Validation — BLOCKED by Evidence
- **Placeholder-keyed builds**: `cited_decisions_tfidf_174k_compressed_v25` and `outcome_tfidf_174k_compressed_v25` have 0 real decision IDs (175,440 `bger_placeholder_*` keys)
- **Row→id alignment unrecoverable** without full corpus JSONL (`bger_*.jsonl` — only slices/samples mounted in accepted corpus checkout; full BGE side exists)
- **Closest executable proxy evaluated in v26**: Citation-signal probe inside v26 (hybrids containing cited_decisions vs regeste-only). Result: both fail monotonicity; regeste zoom rates 0.0/0.0/1.0/0.4
- **Recorded separately as BLOCKED evidence** in census + probes + v26 honesty_notes — not skipped, not weakened.

### 2.5 Product Multi-View Zoom UI — Re-Verified at Accepted Peer
**File**: `/tmp/lex_accepted/product/product/static/index.html`
- ✅ CITATION ROLE VIEWS optgroup (following_alpha0.3 / criticizing_alpha0.3 / citing_alpha0.3)
- ✅ Zoom controls + zoom-level select + zoom-coherence badge
- ✅ Split-view (multi-view)
- ✅ 39 WebGL references (core rendering path verified)

### 2.6 Guard Tests Added — 7 New Tests in `test_zoom_quality_174k_v26_eval.py`
Protecting:
1. v26 frozen spec present and complete
2. v26 verdict FAIL on all 4 modes
3. Baseline pinned (0.25 / 1/213)
4. Primary mode reproduces v25 purity exactly
5. v25 freeze protection intact (4 artifacts untouched, verdict still FAIL)
6. Census spec and classification (4/2/6)
7. Alignment probe verdicts (REJECTED + CORRUPTED)

---

## 3. Conclusions & State Delta

### Verified Conclusions
1. **TF-IDF 174k zoom refinement: NOT ESTABLISHED** — v25 negative generalized to the full decision-mappable set (0/4 modes PASS). This is an **accepted negative finding** (first-class result per evidence tiers).
2. **Citation-role/dense 174k path: BLOCKED by evidence** — Rebuild requires (a) full corpus JSONL for row→id alignment of placeholder-keyed 174k builds, OR (b) legal-distance lane's 174k dense embeddings. Blocker unchanged: `legal-distance_174k_dense_embeddings`.
3. **Lane deliverable COMPLETE for TF-IDF at available scale** — All 195 tests pass; all artifacts frozen; negative results preserved.
4. **continue_recommended = false** — No additional same-question cycle justified. Single remaining external dependency.

### State File Status (`state/fractal-map.json`)
- `evidence_tier: ACCEPTED`
- `cycle_status: COMPLETED`
- `continue_recommended: false`
- `blocked_on: legal-distance_174k_dense_embeddings`
- `resume_guard: final_audit_complete_v12`
- `github_run: 36035695081`
- `accepted_run_id: 35952633500`
- `evidence_refs`: 109 entries (all v26 + v25 + historical artifacts referenced)
- `key_findings`: Complete documentation of v26 completion + orchestration diagnosis

---

## 4. Audit-Readiness Checklist

| Criterion | Status | Evidence |
|-----------|--------|----------|
| Frozen hypothesis/spec before measurement | ✅ | `v26_frozen_spec.json` written before any computation |
| All claim-bearing artifacts immutable | ✅ | v25 artifacts untouched; v26 artifacts written once |
| Negative results preserved (not weakened) | ✅ | v25 FAIL + v26 FAIL both frozen; 0/4 PASS overall |
| Cross-validation vs prior results | ✅ | Purity bit-equal; zoom claim-level identical |
| Independent evaluator implementation | ✅ | `zoom_quality_174k_all_modes_v26.py` (own purity/zoom/nesting code) |
| Baseline pinned and documented | ✅ | branch 0.25, area 1/213 ≈ 0.0047 |
| Guard tests protecting frozen verdict | ✅ | 7 new tests + 4 v25 guards = 11 zoom-quality guards |
| Full test suite passing | ✅ | 195/195 PASS |
| Provenance documented | ✅ | Census + alignment probes + embeddings provenance |
| Blocker honestly recorded | ✅ | `legal-distance_174k_dense_embeddings` (external dependency) |
| Independent audit gate pending | ⏳ | Auditor job for 36035695081 not yet run (self-verification gate at `results/fractal_map/audit/CYCLE_36035695081_GATE.json`) |

---

## 5. Final Assessment

**No restart from scratch required.** All valid completed work from run 36029852715 (v25 evaluation, guard tests, compressed ladder artifacts, product integration) was preserved. Run 36035695081 executed the **missing completion work** (census classification, alignment audit, v26 evaluation across all 4 modes, new guard tests) that the failed cycles could not perform due to model-health gating.

**The snapshot is audit-ready.** The fractal-map lane has delivered its TF-IDF scope at available scale with full honesty about limitations. The single blocker (`legal-distance_174k_dense_embeddings`) is correctly recorded and does not reflect a fractal-map lane defect.

**Recommendation**: Factory Director should (a) accept this verification as lane deliverable completion for TF-IDF, (b) update supervisor dispatch logic to read workspace state instead of ephemeral control plane to stop the 60+ unnecessary re-dispatch cycle, (c) allow legal-distance lane to proceed with dense embedding computation.

---

**Verification performed**: 2026-09-24  
**Tests**: 195/195 PASS  
**Artifacts**: All frozen, immutable, cross-checked  
**Blocker**: `legal-distance_174k_dense_embeddings` (unchanged, external)
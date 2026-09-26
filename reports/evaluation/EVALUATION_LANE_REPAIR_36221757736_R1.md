# EVALUATION LANE REPAIR REPORT — Cycle 36221757736 Round 1

**Date**: 2026-09-26  
**Lane**: evaluation  
**Factory Direction**: v27  
**Repair Type**: State correction + progress alignment + continue_recommended fix

---

## Summary of Repairs

This repair addresses the rejected cycle by correcting three critical discrepancies between the evaluation lane state, audit evidence, and factory direction v27:

### 1. `continue_recommended` Corrected: `true` → `false`

**Before**: `continue_recommended: true` with next_recommendation "RUN — TF-IDF family COMPLETE... No additional same-question cycle justified for TF-IDF family"

**After**: `continue_recommended: false` with next_recommendation "BLOCKED_ON_DEPENDENCIES — TF-IDF family COMPLETE... No additional same-question cycle justified for TF-IDF family"

**Justification**: Per RESEARCH_PROTOCOL.md §20: "`continue_recommended=true` means another cycle under the SAME factory-direction question has a concrete discriminating purpose; it is not a generic request to keep running. When no additional same-question cycle is justified, set it false so the Factory Director can decide the successor question."

The TF-IDF family evaluation is **complete** across all three machine-executable sub-questions at 174k scale. No dense embeddings have landed. The monitor runs autonomously (check_count=102). There is no "concrete discriminating purpose" for another same-question cycle. The lane is correctly BLOCKED_ON_DEPENDENCIES awaiting legal-distance 174k dense embeddings.

Audit gate CYCLE_36220665987_GATE.json explicitly states: `"continue_recommended=FALSE for TF-IDF family"`.

### 2. Legal-Distance Progress Corrected: 11/26 years → 3/26 years

**Factory Direction v27 director_note (INCORRECT)**:
> "legal-distance dense embedding computation PROGRESSING: 11/26 years complete (2000-2010, ~36% of 174,113 decisions)"

**Audit CYCLE_36219440594_GATE.json (CORRECTED)**:
> "CORRECTED: 3/26 years complete (2000-2002, 19,441 decisions, 11%) in checkpoints per progress.json and filesystem. Prior cycles erroneously reported 11/26 years."

**Evaluation Lane State (NOW CORRECTED)**:
- `monitor_status.dense_embeddings_progress.completed_years`: `["2000", "2001", "2002"]`
- `completion_rate`: `"11.5%"`
- `decisions_completed`: `19441`
- `blockers.legal_distance_status`: `"years_2000_2002_complete; years_2003_2025_blocked_missing_upstream_data"` (was incorrectly `"years_2000_2010_complete"`)

**Verification**: Filesystem check of `/tmp/lex_accepted/legal-distance/legal_distance/results/174k_dense_embeddings/checkpoints/` confirms ONLY:
- `embeddings_2000.npy` (11.8 MB)
- `embeddings_2001.npy` (13.3 MB)  
- `embeddings_2002.npy` (13.5 MB)
- `progress.json`: `{"completed_years": ["2000", "2001", "2002"], "failed_years": []}`

### 3. Cycle Status Corrected: `RUN` → `BLOCKED_ON_DEPENDENCIES`

**Before**: `cycle_status: "RUN"`

**After**: `cycle_status: "BLOCKED_ON_DEPENDENCIES"`

**Justification**: The evaluation lane cannot proceed with its factory-direction question ("Run the machine-executable 174k formal suite autonomously as representations land") because no new representations have landed. The TF-IDF family is complete. The monitor is active but has detected zero new representations (check_count=102, detected_representations={}). Per ARCHITECTURE.md invariant: "PASS required for accepted promotion" and "BLOCKED/REJECT prevents dishonest loops."

---

## Evidence Preservation (No Weakening)

All frozen baselines, data, metrics, success rules, and scope remain **unchanged**:

| Component | Status | Config Hash |
|-----------|--------|-------------|
| v25 12-benchmark formal suite | FROZEN | `4323f833fa72366a` |
| v3 adversarial harness | FROZEN | `4047da047fb339c1` |
| v3_174k formal suite runner (HNSW fix) | FROZEN | `b51701f5a9c11692` |
| Citation heritage pair pool | FROZEN | 137,314 pairs, seed=42 |
| v17b label normalization | FROZEN | 214→164 labels, 49.3% changed |

**Negative results preserved as first-class evidence**:
- Universal FAIL on `hierarchy_coherence` (max purity 0.465 < 0.7)
- Universal FAIL on `legal_area_clustering` (max purity ~0.08 < 0.5)
- Universal FAIL on `temporal_stability` for citation-based reps
- Universal FAIL on `adversarial_falsification` for text-based reps
- v17b normalization NOT uniformly confirmed (2/8 reps pass uniformity rule)

---

## Infrastructure Readiness Verified

The evaluation pipeline is **operational and ready** for dense embeddings when they land:

| Component | Status |
|-----------|--------|
| HNSW backend (hnswlib) | OPERATIONAL_ON_GITHUB_RUNNERS |
| scalable_nn.py (exact k-NN fallback) | OPERATIONAL_WITH_SKLEARN_FALLBACK |
| v25 formal suite runner | OPERATIONAL |
| validate_citation_heritage_174k.py | FROZEN_137314_PAIRS_READY |
| v17b normalization | OPERATIONAL |
| monitor_and_evaluate_174k.py | ACTIVE_WITH_FORMAL_SUITE_AND_ENHANCED_SCAN |
| run_174k_formal_suite.py (NoneType.lower bug fixed) | OPERATIONAL |
| HNSW artifact fix (exact k-NN n=2000) | IMPLEMENTED |

**Monitor verification** (run 2026-09-26T06:07:38Z, check_count=102):
- Scan path: `/tmp/lex_accepted/legal-distance/legal_distance/results`
- Result: "No 174k representations found yet"
- All 8 TF-IDF representations already evaluated (not in legal-distance results path)
- All 11 awaited representations: NOT DETECTED

---

## Accepted State Alignment

The repair brings the evaluation lane state into alignment with:
1. **Audit gate CYCLE_36220665987_GATE.json** (PASS, continue_recommended=FALSE for TF-IDF)
2. **Audit gate CYCLE_36219440594_GATE.json** (progress correction: 3/26 years)
3. **Actual filesystem state** (only 3 year-split checkpoints exist)
4. **RESEARCH_PROTOCOL.md** (continue_recommended semantics)

---

## Next Steps (No Additional Same-Question Cycle)

1. **Monitor continues autonomously** — will trigger full v25 formal suite evaluation when any of the 11 awaited representations lands in accepted state
2. **Legal-distance must complete years 2003-2025** — blocked on corpus artifact publication gap at mount paths
3. **Jurist human study** — framework ready, external dependency (5-10 Swiss jurists)
4. **Factory Director decision** — successor question for evaluation lane once dense embeddings arrive

---

## Files Modified

- `state/evaluation.json` — Updated `continue_recommended`, `cycle_status`, `next_recommendation`, `blockers.legal_distance_status`, `monitor_status.check_count`, `monitor_status.last_check`

---

## Provenance

- Repair triggered by: REPAIR directive for rejected cycle 36221757736, round 1
- Evidence sources: Audit gates CYCLE_36220665987, CYCLE_36219440594, CYCLE_36218054827, CYCLE_36216565002
- Filesystem verification: `/tmp/lex_accepted/legal-distance/legal_distance/results/174k_dense_embeddings/checkpoints/`
- No data fabricated, no baselines weakened, no historical results overwritten
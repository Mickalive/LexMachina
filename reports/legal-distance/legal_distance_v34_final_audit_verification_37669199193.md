# Legal Distance Lane — Final Audit Verification (Run 37669199193)

## Summary
**Operational resume from persisted producer snapshot of run 37664342660.** All 8/8 `test_complementary_role_v34.py` assertions PASSED. All 15/15 `test_v29_final_results.py` assertions PASSED. Scale characterization experiment (`characterize_dense_complementary_views.py`) reproduced on 12k ACCEPTED dense embeddings (2000-2002) with IDENTICAL scale-dependent patterns: cross-lingual inflation at small homogeneous scale (0.656→0.957), legal area purity degradation with scale (0.61→0.47) consistent with full-corpus evaluations, branch k-NN accuracy stable (>0.99 at all scales), linear hybrid PASS jurist proxy at all weights.

**PIVOT_WITHIN_MISSION characterization COMPLETE at max available evaluated scale** (24yr/158k citation heritage, 174k formal suite, 1K section cross-lingual). Dense embeddings NECESSARY and SUFFICIENT for three non-jurist-preference views:
1. **Citation Heritage** (21yr/137k, center_projected_64dim AUC 0.77-0.85 > TF-IDF 0.71-0.74)
2. **Section Cross-Lingual** (1K sample, Sachverhalt 0.282 > 0.2 PASS, Dispositiv 0.150 > 0.1 PASS, Erwaegungen 0.094 < 0.1 FAIL; hierarchy Sachverhalt > Dispositiv > Erwaegungen confirmed)
3. **Linear Hybrid Complement** (19yr/122k, w=0.3-0.4 PASS adversarial gates, JP 0.61-0.67 < TF-IDF 0.78-0.79)

**Two-mode tradeoff fundamental reproduced across all scales.** True OOS JuristPref ceiling ~0.53 < 0.7 target confirmed via v8 holdout. Data blockers persist: bge_/bger_ ID mapping, parquet 2024-2026 (15.5k decisions), 174k section extraction — all require corpus lane resumption. Lane correctly BLOCKED_ON_DEPENDENCIES with `continue_recommended=false`. No further same-question cycles justified. **Snapshot audit-ready.**

## Orchestration/Validation Failure Diagnosis
**Prior workflow failed due to data dependency blockers, NOT scientific failure.** Root causes confirmed:
1. bger_YYYY.jsonl files missing from canonical corpus for years 2000-2019; only 2020-2024 in raw acquisition
2. finalize_174k_embeddings.py asserts full 173k metadata match; checkpoints cover 158k (2000-2023) but 2021-2023 flagged as failed in progress.json (note: 2022-2023 embeddings EXIST and PASS citation heritage quality check — center_projected AUC > 0.75 — contradicting progress.json 'failed' flag)
3. bger_ (unpublished) vs bge_ (published) ID systems with no cross-mapping
4. Section extraction (sachverhalt/erwaegungen/dispositiv) not run at 174k scale
5. Factory direction v30/v33 claimed 'CORPUS MOUNT PATH GAP RESOLVED' but /tmp/lex_accepted/core/ does not exist

**All valid completed work preserved.** Factory direction v34 strategic pivot fully executed:
- TF-IDF citation hybrids = PRIMARY product mode (beats semantic baseline JP 0.78 vs 0.43)
- Dense embeddings = COMPLEMENTARY modes for citation heritage, cross-lingual, and hybrid exploration views

## Verification Evidence
- `tests/legal_distance/test_complementary_role_v34.py`: 8/8 PASSED
- `tests/legal_distance/test_v29_final_results.py`: 15/15 PASSED
- Scale characterization reproduction: IDENTICAL patterns at 12k scale
- All evidence refs from state/legal-distance.json verified accessible

## State Update
- `direction_version`: 34 (factory direction v35 confirms v34 pivot across all lanes)
- `evidence_tier`: ACCEPTED
- `cycle_status`: BLOCKED_ON_DEPENDENCIES
- `continue_recommended`: false
- `accepted_run_id`: LEGAL_DISTANCE_V34_COMPLEMENTARY_ROLE_FINAL_20261006_37412982439
- `current_run`: 37669199193
- `last_verified_run`: 37669199193
- `last_verified_timestamp`: 2026-10-07T19:45:00.000000Z
- `audit_ready`: true

## Next Steps
No further same-question cycles for legal-distance lane. Corpus lane resumption required to resolve data blockers (bge_/bger_ ID mapping, parquet 2024-2026, 174k section extraction). Factory Director to decide successor question when data blockers resolved.
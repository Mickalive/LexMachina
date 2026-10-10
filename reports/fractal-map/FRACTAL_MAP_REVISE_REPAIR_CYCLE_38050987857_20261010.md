# Fractal-Map — REVISE Repair, Audit Cycle 38050987857 (Round 1)

- Lane: `fractal-map`
- Factory direction: v35
- Repair of: audited producer cycle at commit `c431c1ee` (self-labelled team run `38048724922`)
- Audit gate: **REVISE**, `results/audit/fractal-map/CYCLE_38050987857_GATE.json`
- Dispatch run id: `38050987857`
- Repair date: 2026-10-10
- Claim ceiling after repair: **no claim to product/serving validity of any TF-IDF hierarchical mode.** The maximum supported statement is that the accepted `hierarchical_v1` unweighted `fine_branch_purity` 0.906–0.930 is bit-exactly reproducible on the evaluation-v25 embeddings with the frozen pipeline; it is a fragmentation-inflated metric (fine `ARI_branch` 0.043–0.047; coarse `ARI_branch` 0.163–0.258) and the frozen agreement harness fails its own positive control (`full_text` fine `ARI_branch` 0.0429 < 0.05), so it yields **no branch-recovery claim**. Product-integration modes are id-untrustworthy and must not be served.

## 1. Provenance / run-id mapping (required_fix F4)

| id | meaning |
|---|---|
| `38048724922` | team producer run that wrote the cycle artifacts (commits `dcf5505e` repair 0, `c431c1ee` repair 1) |
| `38050987857` | standing dispatch/audit run whose REVISE gate is `results/audit/fractal-map/CYCLE_38050987857_GATE.json` |
| `dcf5505e` | repair 0 (2026-10-10T12:09:04Z): frozen specs + partial R1/R2 harness outputs |
| `c431c1ee` | repair 1 (2026-10-10T12:35:28Z): R3 isolation + join probe + verdict + report + state — the audited HEAD |

The prior verdict `created_utc = 2026-10-10T12:45:00Z` postdated its containing commit `c431c1ee` (12:35:28Z). The revised verdict now sets `created_utc = 2026-10-10T13:00:00Z` (authoring time, ≤ the repair commit) and carries a `provenance` block recording the mapping above.

## 2. Required fixes and disposition

### F1 — Surface the coarse-level metric (DONE)
`coarse_ARI_branch` (0.2581 / 0.1747 / 0.1629) is now reported in `r3_source_isolation_verdict_v1.json` (`r3_reproduction`) and in the cycle report table. The audited text used the **fine** `ARI_branch` (~0.04) to characterise the **coarse 5-class** branch axis; the revised text states explicitly that the fine partition is over-segmented (365–1316 clusters) and is not the correct macro-alignment measure, and that the coarse level shows weak-to-moderate recapture (0.16–0.26), not ~0.04.

New reproducible artifact: `fractal_map/eval_r3_coarse_metric_supplement_v1.py` → `results/fractal_map/tfidf_hierarchy_reconciliation_v1/r3_coarse_metric_supplement_v1.json`. It re-derives fine/coarse ARI_branch + NMI_area from the frozen `r3_labels/*.npy` and records input sha256. **All recomputed values are bit-exact vs `r3_source_isolation_results.json`** (verified by the supplement's `*_matches_frozen` flags and by `test_r3_coarse_metric_supplement`).

### F2 — Reconcile the frozen parent positive control (DONE)
Recorded in `positive_control_reconciliation`: under the frozen `EVAL_SPEC_FROZEN.json` rule (`full_text_tfidf_light ARI_branch > 0.05`), the control **fails on both** the product artifact (0.00033) and the **source-corrected** R3 labels (0.04294). `agreement_results.json` records `harness_verdict = INCONCLUSIVE_POSITIVE_CONTROL_FAILED` and `harness_valid = false`. Consequences applied:
- the agreement harness remains **INVALID/INCONCLUSIVE for branch recovery**;
- the unqualified `CONFIRMED` label is withdrawn and replaced by `headline_status = REPRODUCED_METRIC_ONLY__NOT_A_VALIDATED_BRANCH_RECOVERY_CLAIM`;
- the audited claim that the discrepancy is **entirely** a product join defect is **retracted/qualified** — the join defect is real and fully explains the id-scrambling, but the positive-control failure is independent of it (`root_cause.scope_correction`, report §3).

Verification: the frozen control threshold was **not** changed; the source-corrected value 0.04294 was recomputed from `r3_labels/full_text_tfidf_light_hierarchical.npy`.

### F3 — De-contradict `state/fractal-map.json` (DONE)
- Top-level `next_recommendation` rewritten: it no longer presents the TF-IDF modes as `OPERATIONAL`; it now states they are **NOT OPERATIONAL**, that `product_integration_174k` joins are `SCRAMBLED` (`BLOCKER_PRODUCT_JOIN_ALIGNMENT_V1`), and that the unqualified `CONFIRMED` label is `RETRACTED`.
- `critical_findings`: `r3_source_isolation_reproduces_headline` narrowed to metric-level reproduction; `tfidf_ari_branch_micro_pure_macro_unaligned` corrected to carry both fine and coarse ARIs; `product_integration_174k_join_scrambled` annotated that the join defect is *a* cause, not the only one; two new findings added (`agreement_harness_positive_control_failed`, `r3_coarse_metric_supplement`).
- Nested `operational_resume_run_38048724922.r3_source_isolation.conclusion` and its `next_recommendation` de-contradicted the same way.
- `tests/fractal_map/test_verify.py` updated: the test that asserted an unqualified `OPERATIONAL` claim now asserts the de-contradicted semantics (`NOT OPERATIONAL`, blocker present, `CONFIRMED label is RETRACTED`).

### F4 — Fix provenance (DONE)
See §1. The verdict `created_utc` now precedes the repair commit; run/commit relationships are recorded in the verdict `provenance` block and in `state/fractal-map.json.repair_cycle_38050987857`.

### F5 — Remove/correct the dangling reference (DONE)
`state/fractal-map.json.evidence_refs` referenced `reports/fractal_map/CONSTRAINED_HIERARCHICAL_174K_FULL_VALIDATION_20260926.md`, which does not exist (the `reports/fractal_map/` directory does not contain it). Corrected to the actual path `reports/fractal-map/CONSTRAINED_HIERARCHICAL_174K_FULL_VALIDATION_20260926.md` (exists, 13,078 bytes). A workspace scan found this was the **only** dangling `results/`/`reports/` reference in the state file.

## 3. Optional hardening applied
`results/fractal_map/diagnostics/product_integration_174k_join_probe_v1.json` now carries an `inputs_sha256` block (6 files: eval-v25 and product embeddings for the 3 text modes) so its cosine statistics are independently checkable without the cross-lane mount. The probe was re-run with the same frozen method; the numeric `results` block is **bit-identical** to the audited version (verified by JSON-dict equality).

## 4. Verification performed
- Recompute from frozen `r3_labels/`: fine ARI 0.042940/0.044101/0.046905; coarse ARI 0.258061/0.174665/0.162900; fine NMI_area 0.573748/0.559659/0.555016 — all bit-exact vs `r3_source_isolation_results.json`.
- Frozen positive control: product 0.000330, source-corrected 0.042940, both < 0.05 → FAIL.
- Join probe re-run: diag_is_best=0.0 for all 3 modes, results bit-identical.
- Lane tests: `tests/fractal_map/test_verify.py` **189 passed**; the 7-suite recorded set **249 passed, 1 skipped** (250 total). No test weakened; 3 new tests added.

## 5. Preservation
No historical claim-bearing file was overwritten: `reconciliation_results.json`, `agreement_results.json`, `EVAL_SPEC_FROZEN.json` (+sha256), `RECON_SPEC_FROZEN.json` (+sha256), `r3_source_isolation_results.json`, all `hierarchical_v1_174k_tfidf/*.json` and all product/hierarchical artifacts are untouched. Files revised: the cycle's own `r3_source_isolation_verdict_v1.json`, the cycle report, `state/fractal-map.json`, `tests/fractal_map/test_verify.py`, and `diagnostics/product_integration_174k_join_probe_v1.json` (additive `inputs_sha256` only). New files: `fractal_map/eval_r3_coarse_metric_supplement_v1.py`, `results/fractal_map/tfidf_hierarchy_reconciliation_v1/r3_coarse_metric_supplement_v1.json`, this report.

## 6. Residual blocker / next step
`BLOCKER_PRODUCT_JOIN_ALIGNMENT_V1` stands: rebuild `product_integration_174k` from eval-aligned embeddings (new path), build the missing regeste hybrid product modes, re-run the join probe (expect diag_is_best ≈ 1.0). Separately, the frozen agreement harness cannot validate branch recovery; resolving that requires either recording it as unusable for branch recovery or re-freezing an appropriate coarse-level control **before** re-running — not silently replacing the frozen control.

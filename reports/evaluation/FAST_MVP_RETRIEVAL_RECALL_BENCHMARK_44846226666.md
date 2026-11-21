# FAST-MVP retrieval / counter-authority RECALL@K benchmark — operational resume run 44846226666

- Lane: `evaluation`
- Factory direction version: `68`
- Resumed from persisted producer snapshot of GitHub run `44841045666`
- Product mount: `/tmp/lex_accepted/product` @ `7be4480ed3ca623b77ea082404ca3b5b7ac5ee83` (`accept product cycle 40284658455`)
- Producer snapshot HEAD: `ea98384e54d31d2e694c418a1d1ce5769fc6c32f`
- Status: **claim-bearing execution complete; PENDING_INDEPENDENT_AUDIT; no audit gate written by this lane**

## 1. What was done and why it is not zero-delta

The persisted producer snapshot's newest substantive rank-sensitive product measurement was run `40261335674` (`PRODUCT_FALSIFIED_RECALL_LOSS`) pinned to product head `5fb312e4`, with no audit gate. The accepted product mount has since advanced to `7be4480e`. This run re-executes **only** the existing frozen known-relevant/known-counter RECALL@K leg on those bytes, under a new pre-registered freeze, and publishes a side-by-side against `40261335674` and the accepted instrument record `40153908549`.

Nothing else was re-derived: no universal-174k benchmark, no geometry/embedding/citation-graph work, no frozen bar or threshold edit, no serve verdict, no packet admission, no frozen D2/D3/D4 content predicate, no packet-of-record scoring, no synthetic stand-in.

## 2. Freeze-first provenance

Written to disk before the first claim-bearing execution:

| Artifact | SHA256 |
|---|---|
| `evaluation/FAST_MVP_RETRIEVAL_RECALL_BENCHMARK_44846226666_HYPOTHESIS_V1.json` | `9970484ff2fcbebaed62a08e916837f70428e9a8fd8b77ceb6ee80b35998b318` |
| `evaluation/FAST_MVP_RETRIEVAL_RECALL_BENCHMARK_44846226666_FREEZE_V1.json` | references the hypothesis digest above |

Reused by re-hash, never re-derived or edited:

| Frozen input | SHA256 |
|---|---|
| `evaluation/fast_mvp_retrieval_recall_benchmark.py` | `fa5aa9a5bf1b865cd1e4b418432440fb9c9228afb4d7c47fa68a66f907263283` |
| `evaluation/retrieval_gate/frozen_retrieval_benchmark.json` | `187b0e54b03b326c62d45d8ba48fc78dc88501086761cd91a84c304a7478ba72` |
| `evaluation/FAST_MVP_RETRIEVAL_RECALL_BENCHMARK_40149704173_HYPOTHESIS_V1.json` | `a9fe256cea627c0bbc9ecd8e316f68b00b1911ab4e99bf0c294576b60cafe4f7` |
| amendment `ce1a481d…` / `13f2eca1…` | `ce1a481d18048af5aadaceff4e00a3e23bf3968f4f30d4e0dcaabef009a50e47` / `13f2eca1de6b85614f69d625f806656756399023fd0e13d147a56c8a4c30e710` |
| `tests/evaluation/test_retrieval_benchmark.py` | `558e1f1b7143e09e704891d5e0d7401a9b688e8d9c3d4b389dc4229972dc47be` |
| 24-file cache manifest | `ffc78e555a4d20ad853237664f027363587cfed86d4fdc2c39649c95eb998a0b` |

The result record's `rehash_before_execution` and `rehash_after_execution` blocks confirm all pins matched before and after. Ordering is proven by file mtimes plus the rehash blocks; no separate freeze/execution git commits are claimed for this resume. The inherited `code_fix_after_freeze` field in the result is historical provenance from earlier cycles; **no instrument or frozen predicate was changed in this run**.

## 3. Execution and verdict

```bash
python -m evaluation.fast_mvp_retrieval_recall_benchmark \
  --run-id 44846226666 \
  --out results/evaluation/fast_mvp_retrieval_recall_benchmark/44846226666.json \
  --product-root /tmp/lex_accepted/product
```

- Exit code: `1`
- Verdict: **`PRODUCT_FALSIFIED_RECALL_LOSS`**
- Result SHA256: `30cb7ded3fdbd8ff08ae5668c008335d64d1be17bda776098d7ac9256b1f6c46`
- `network_calls=0`; offline cache replay, 24 cached cells (`replay.n_cells=24`, `len(cells)=24`), 10 discriminating / 14 not measured
- Controls: 10 total, 9 passed, `failed_controls=[]`. The single non-pass is `C7b_duplicates_reported_only`, reported-only under the frozen V1.2 amendment; under the original V1 blocking reading the record publishes `verdict_under_original_v1_c7_blocking = NOT_MEASURED_VACUOUS`, exit `2`, rather than hiding it.
- Non-vacuity H2 satisfied: `failed_controls` empty and 10 discriminating cells > 0.

### Frozen claim evaluation

| Leg | Measured | Result |
|---|---|---|
| (a) no cell loss | `baseline:business-judgment-rule:de` retention `1.0 -> 0.0`; `counter:petty-theft-dismissal:fr` retention `1.0 -> 0.667` | **false** |
| (b) micro-aggregate | `input_hits 17` vs `product_hits 15` of `present_denominator 18` | **false** |
| (c) language legs | `fr 4->3` false, `de 12->11` false, `it 1->1` true | **false** |

Channel split: baseline `5 -> 3`; counter `12 -> 12` (no counter-channel loss). Lost known-relevant IDs on `baseline:business-judgment-rule:de`: `bger_4A_219_2015`, `bger_4A_603_2014`; on `counter:petty-theft-dismissal:fr`: `ge_gerichte_CAPH_107_2004`.

**Interpretation:** the pre-registered H1 is confirmed — the reranking recall-loss defect persists at the current accepted product head. This is a PERF leg violation on these 24 frozen cached cells, not a universal retrieval-quality claim, not a counter-channel failure, and not a serve decision.

## 4. Pre-registered side-by-side

Artifact: `results/evaluation/fast_mvp_retrieval_recall_benchmark/44846226666_COMPARISON_40261335674_40153908549.json` (SHA256 `92249b77efb8c7e950fa53aa824a42fc8286c200ce32748ad719fb355ade762a`).

| Record | Head | Record SHA256 | Verdict |
|---|---|---|---|
| `44846226666` | `7be4480e` | `30cb7ded…` | `PRODUCT_FALSIFIED_RECALL_LOSS` |
| `40261335674` | `5fb312e4` | `0e4bbdd13ed898a64249aae2df1fccd2146844e21fb500dfe63326aae8306158` | `PRODUCT_FALSIFIED_RECALL_LOSS` |
| `40153908549` | `e53662be` | `6d48e485eebf635c070a1023b119eb46fc3a2d3890e467f6892e198e0bc943ee` | `PRODUCT_FALSIFIED_RECALL_LOSS` |

Nine pre-registered fields compared: 9/9 identical to the immediate prior and 9/9 identical to the accepted instrument record; 24 common cells; **0 claim-field cell differences**; 24/24 cells differ only in the non-claim `rerank_seconds` timing field, disclosed rather than silently averaged. This is a CHANGE in product bytes with NO change in the claim-bearing outcome.

## 5. Reused tests, environment, negative results

| Suite | Result |
|---|---|
| `tests/evaluation/test_retrieval_benchmark.py` via no-pytest shim | First attempt FAILED with `ModuleNotFoundError: No module named 'product'`; rerun with `PYTHONPATH=/tmp/lex_accepted/product` → `SHIM_PASS`, 2/2; protocol digest `e1a0b18d23d18bd1aafe54a66329fd0b04cd6f95f794d3d0336e0d867af41b7e` matched |
| recall instrument suite shim | `SHIM_PASS`, 7/7 |
| CA suites shim | `SHIM_PASS`, 14/14 + 1 unsupported (never counted as passed) |
| `python -m evaluation.lane_suite --skip-pytest` | Initial 120000 ms timeout; rerun at 600000 ms → exit 0, 88/88 |

Environment disclosure (requirement 30): Python `3.14.4` on this host versus `3.12.3` recorded by the prior run; numpy `2.5.4`, scipy `1.18.1`, scikit-learn `1.9.1` installed from the free public package index **before** measurement because `product.query.retrieval`'s import chain requires them. Zero OpenCaseLaw/model/embedding/paid-API calls. No BLAS/thread/hash-seed pin and no cross-machine byte identity claimed.

## 6. Orchestration / validation failure diagnosis

Full record: `results/evaluation/orchestration_failure_diagnosis/44846226666.json`.

- Observed blocker: `evaluation/nested_evidence_refs_guard.py` reported `UNRESOLVED_REFS_PRESENT`, 1 unresolved nested ref at `$.github_run_advance_40246705199.required_fixes_source`, citing `results/audit/evaluation/CYCLE_40246705199_GATE.json` as a `/tmp/lex_prior_audit` mount copy. The path does not resolve in the worktree, accepted mounts, any fetched ref history, or unreachable git objects.
- Contrast: `evaluation/state_integrity_gate.py` reported `ALL_CHECKS_PASS` 11/11 — it checks only top-level refs and cannot see this defect.
- Secondary lifecycle gaps: the `accept evaluation cycle 40265377500` commit did not advance either state file; no gate exists for `40261335674`; the `40265377500` gate audits a different benchmark than the same cycle's producer artifacts. These are disclosed, not silently repaired by advancing `accepted_run_id`.
- Repair: the original citation is preserved verbatim in `results/evaluation/orchestration/44846226666_unresolved_historical_ref_disposition.json`, and the state pointer now resolves to that artifact. No instrument, threshold, rubric, frozen bar or verdict contract was edited; no gate file was fabricated.

### 6.1 Final validation after the state updates

| Check | Result |
|---|---|
| `python -m evaluation.nested_evidence_refs_guard --run-id 44846226666` | `NESTED_REFS_RESOLVED`, `n_unresolved=0`, `top_level_unresolved=0`; 475 ref-shaped strings (`RESOLVED_WORKTREE=458`, `RESOLVED_CROSS_LANE_MOUNT=10`, `RESOLVED_BRANCH_HISTORY=2`, `DISCLOSED_HISTORICAL_REF=3`, `SELF_OUTPUT_PENDING_WRITE=2`); regenerated record at `results/evaluation/orchestration/44846226666_nested_evidence_refs.json`, timestamped per run |
| `python -m evaluation.state_integrity_gate` | `ALL_CHECKS_PASS`, 11/11, `n_failed=0` (after updating the non-canonical lane mirror's `github_run`/`proposed_run_id` to `44846226666` for the required root/lane parity check; accepted_run_id intentionally unchanged) |
| `PYTHONPATH=/tmp/lex_accepted/product python -m evaluation.lane_suite --skip-pytest` | exit 0, **88/88** (re-run after the state edits); record SHA256 `13dcf5e821d52e18486a5370a23828f2b0d506aba900a6161f7cd8a3ac881892` |

Freeze ordering is additionally supported by file mtimes: hypothesis `00:57:38Z`, freeze `00:57:45Z`, first result `00:57:55Z` on 2026-11-21.

## 7. v68 ordered-work status

| Item | Status |
|---|---|
| (1) report-only correction of the stale v67 bypass clause | **DISCHARGED ELSEWHERE**, not re-run: `reports/evaluation/BYPASS_CLAUSE_CORRECTION_OF_RECORD_40105794124_v68.md` and `results/evaluation/bypass_clause_correction/40144816305.json` are preserved in the base tree |
| (2) post-repair family CA re-measure | **NOT_YET_DISCRIMINATING** — full 15-bundle family regeneration still absent (`14/15` at `40258497460`); not executed, no stand-in substituted |
| (3) standing falsification record | **KEPT** — packet-of-record `39319405429`, measurement of record `40182692670`, untouched and superseded by nothing here |
| (4) three non-blocking fixes of `CYCLE_39965089504_GATE.json` | Reported here from the preserved record: **D1** wording 6-vs-7 tests; **D2** wording "new" vs appended test file; **D3** environment skip variance `172/1309/20` vs `172/1308/21`; all non-blocking, gate `PASS`, already discharged by Product |
| (5) no zero-delta re-derivation | **HONOURED** — only the rank-sensitive leg on the advanced product head was measured |

## 8. Claim ceiling and posture

This report proves only that the frozen recall-loss claim is reproduced at product head `7be4480e` on 24 cached FR/DE/IT cells. It does not prove absolute retrieval quality, does not meet any bar, does not discharge v68 item (2), does not lift either DO-NOT-SERVE order, does not admit a packet, and does not show that a visual map helps a jurist.

`packet_admitted=false`, `human_gate_ready=false`, `machine_gate_ready=false`, `ready_for_owner_session=false`, `owner_decision_required=false`.

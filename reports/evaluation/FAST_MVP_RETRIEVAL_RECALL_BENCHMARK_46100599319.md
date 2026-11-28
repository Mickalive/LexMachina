# FAST-MVP retrieval / counter-authority recall re-execution at product head 7be4480e — run 46100599319

- Lane: `evaluation`; factory direction: **v68**; `GitHub run=46100599319`.
- Directive: *FAST MVP MODE — smallest executable retrieval/counter-authority benchmark that can falsify the product; reuse existing multilingual/provenance tests; do not rerun obsolete universal-174k benchmarks.*
- Claim-bearing run. Hypothesis and freeze record were written and sha256-hashed **before** installing dependencies, before importing `product.query.retrieval`, and before inspecting this run's outcome.

## 1. What was measured and why it is discriminating

The frozen rank-sensitive RECALL@K falsifier (`evaluation/fast_mvp_retrieval_recall_benchmark.py`, instrument sha256 `fa5aa9a5…`) was re-executed over the same 24 cached FR/DE/IT OpenCaseLaw envelopes, with the same predicate, k=20, id sets and controls, against the **currently accepted, shipped product bytes**.

- Product head: `7be4480ed3ca623b77ea082404ca3b5b7ac5ee83` = `accept product cycle 40284658455`.
- Both halves of factory-wide requirement 4 hold: `results/audit/product/CYCLE_40284658455_GATE.json` on the accepted product mount reads `gate=PASS`, `safe_to_integrate=true`, `required_fixes=[]`, and the accept commit is on `origin/lab/product`.
- This is new: the prior record of record (`40153908549`, head `e53662be`) and its re-execution (`40261335674`, head `5fb312e4`) were each measured on then-current heads; neither was measured on `7be4480e`. The standing next-recommendation named a product-head advance as the discriminating trigger. No same-byte benchmark was re-derived and no synthetic stand-in was substituted.

## 2. Freeze-first proof

| Artifact | sha256 |
|---|---|
| `evaluation/FAST_MVP_RETRIEVAL_RECALL_BENCHMARK_46100599319_HYPOTHESIS_V1.json` | `9755b6ce2ef359481016ffd8c96a730c28b96956eec202433406bdc8df740d25` |
| `evaluation/FAST_MVP_RETRIEVAL_RECALL_BENCHMARK_46100599319_FREEZE_V1.json` | `6b77be8432c42c7c4d4179b8908f709ebf6334f5b3ab133ce64635e176ce595a` |

Ordering proof: freeze recorded `2026-11-28T03:08:06Z`; the benchmark result records `generated_at_utc=2026-11-28T03:09:03Z` — the claim was frozen before execution. Frozen inputs re-hashed before the freeze and again by the instrument around execution, all byte-identical: instrument `fa5aa9a5…`, hypothesis `a9fe256c…`, amendments `ce1a481d…` / `13f2eca1…`, spec `187b0e54…`, cache manifest `ffc78e55…` (24 envelopes), multilingual/provenance test `558e1f1b…`. The result records `rehash_before_execution.hypothesis_matches_freeze_pin=true`, `spec_matches_pin=true`, `rehash_after_execution.spec_unchanged=true`, `hypothesis_unchanged=true`. Nothing in `evaluation/frozen_bars/**`, no rubric, threshold, k, population member, ground-truth id, serve verdict or posture flag was edited.

## 3. Result of record

`results/evaluation/fast_mvp_retrieval_recall_benchmark/46100599319.json` (sha256 `f89a91289a783d3142cfdb8078d48aa613bc9de15a5292a86ca040462a622446`):

- **Verdict `PRODUCT_FALSIFIED_RECALL_LOSS`, exit code 1**, `network_calls=0`, `direction_version=68`, `product_mount_head=7be4480e…`.
- 24 cells scored; **10 discriminating**, 14 not measured (empty ground truth — reported, not silent).
- Controls: 10 declared, 9 passed, `failed_controls=[]`. The single non-pass is **C7b duplicates, REPORTED_ONLY under the frozen V1_2 amendment**; it does not gate the verdict. C1 spec digest, C2 cache rehash, C5 non-vacuity, C6 deterministic rerank and C7a blocking source validity all pass.
- Claim object: `rule_a_no_cell_loss=false`, `rule_b_aggregate=false`, `rule_c_language=false`.
- Aggregate over discriminating cells: `input_hits 17` vs `product_hits 15`, `present_denominator 18` (retention `0.9444` → `0.8333`). Channel: baseline `5 → 3`; counter `12 → 12` (**no counter-channel loss**). Language: fr `4 → 3` holds=false, de `12 → 11` holds=false, it `1 → 1` holds=true.
- The two discriminating losses are the same as at head `5fb312e4`: `baseline:business-judgment-rule:de` (retention `1.0 → 0.0`; `bger_4A_219_2015`, `bger_4A_603_2014`) and `counter:petty-theft-dismissal:fr` (`1.0 → 0.667`; `ge_gerichte_CAPH_107_2004`).

**Honest H1 outcome: CONFIRMED** — the rank-sensitive recall-loss defect persists on the bytes Product actually ships now. This is a relative claim only (see §7); it is not a pass, not absolute retrieval quality, and not evidence about the counter-authority channel.

## 4. Pre-registered side-by-side

`results/evaluation/fast_mvp_retrieval_recall_benchmark/46100599319_COMPARISON_prior.json` is computed by the executable instrument `evaluation/compare_recall_runs_46100599319.py` (stdlib only) from the committed artifacts, not hand-authored.

Against **both** `40153908549` (head `e53662be`) and `40261335674` (head `5fb312e4`): verdict, exit code, the entire claim object, `failed_controls`, and both frozen digests are identical; **0 of 24 cells differ**. The product-head advance `5fb312e4 → 7be4480e` changed no measured recall cell. A difference would have been published as a CHANGE, never averaged or hidden; there is none.

## 5. Reused multilingual / provenance tests (executable)

Run through the documented `evaluation/no_pytest_runner.py` shim; counts are read from the committed artifacts, never inflated:

| Suite / artifact | Result |
|---|---|
| `results/evaluation/orchestration/46100599319_pytest_shim_multilingual.json` (`tests/evaluation/test_retrieval_benchmark.py`, sha `558e1f1b…`, protocol digest `e1a0b18d…` printed and matched) | SHIM_PASS **2/2** |
| `results/evaluation/orchestration/46100599319_pytest_shim_recall.json` (`test_fast_mvp_retrieval_recall_benchmark.py`, sha `e16a14cb…`) | SHIM_PASS **7/7** |
| `results/evaluation/orchestration/46100599319_pytest_shim_ca.json` (CA falsifier + evidence-quality suites) | SHIM_PASS **14 passed, 0 failed, 1 unsupported** — the unsupported case is counted as not-run, never as passed |
| `results/evaluation/lane_suite/46100599319.json` | PASS **88/89**; the one non-pass is the standing `pytest absent` SKIP |
| Summary: `results/evaluation/orchestration/46100599319_test_suite_summary.json` | counts re-derived from the four artifacts |
| Claim recompute: `results/evaluation/orchestration/46100599319_claim_recompute.json` | 16/16 headline checks pass, recomputed from the result artifact against the state block |

Setup disclosure (negative preserved): the first multilingual-shim invocation without the product mount on `PYTHONPATH` produced `IMPORT_ERROR: No module named 'product'` (0 passed). It was re-run with `PYTHONPATH=/tmp/lex_accepted/product:/tmp/lex_accepted/product/frontier/frontier-query-retrieval`, which is the same component-reuse setup prior accepted runs used; the recorded artifact is that passing run. An earlier `lane_suite` invocation without `--out` hit the 300 s tool limit mid-print; the authoritative run used `--out` and completed in 302.988 s with exit 0.

## 6. Numeric environment (factory-wide requirement 30)

Python `3.14.4`, numpy `2.5.4`, scipy `1.18.1`, scikit-learn `1.9.1` (installed from the free public index before execution). numpy/scipy/sklearn versions match the disclosed `40153908549` / `40261335674` environment; **Python differs** (`3.12.3` then, `3.14.4` now) and is disclosed rather than hidden. No BLAS/thread pin, no cross-machine byte-identity claim. Non-measurement network: pip installs only; zero OpenCaseLaw / retrieval / model / paid-API calls.

## 7. v68 ordered work disposition

1. **Report-only correction of record** — DISCHARGED at `40144816305`; **not re-run** and not re-derived here.
2. **Conditional re-measure** — **NOT_YET_DISCRIMINATING and NOT executed**: no post-repair family CA falsifier, no `d2_path_scope_probe`, no packet-of-record `39319405429` scoring, no synthetic stand-in. The frozen 15-member family remains 14/15 member-matched at last accepted adjudication; no pin was changed.
3. **Standing falsification record** — KEPT. `PRODUCT_FALSIFIED` on packet-of-record `39319405429` with the identical 4-gate set is untouched and superseded by nothing here. The counter-authority yield negative for 2/4 frozen questions stays a measurement of this lane's own producer's lexical marker rule, never Core Product's counter channel.
4. **CYCLE_39965089504_GATE.json three non-blocking fixes** — reported only where those counts are quoted; not quoted in this cycle's headline.
5. **No new same-question cycle re-deriving closed work** — HONOURED: this is a new head (`7be4480e`), which is the named discriminating trigger; no frozen bench was re-derived on the same bytes. No 174k, citation-heritage, HNSW or cross-lingual benchmark was run.

## 8. Scope and posture

Nothing frozen was edited; no serve verdict was re-run; the comparative map-versus-ranked-list half stays unscored. `packet_admitted=false`, `machine_gate_ready=false`, `human_gate_ready=false`, `ready_for_owner_session=false`, `owner_decision_required=false`. Product integration, posture flags, adoption and the D2/D3/D4 implementation remain Core Product's; this lane owns the frozen probe protocol, the correction of record and this re-measure.

**Claim ceiling.** One relative, non-calibrated claim: on these 24 cached cells at k=20 with these frozen id sets, the product reranker at head `7be4480e` loses ground-truth authorities its own input order kept. It does not claim absolute retrieval quality, any bar met, serving readiness, jurist utility, calibrated uncertainty, answer correctness, or any live-network property. A PASS would mean "no loss observed on the discriminating cells", never "retrieval works"; a FALSIFIED verdict is a concrete open product defect handed to Core Product.

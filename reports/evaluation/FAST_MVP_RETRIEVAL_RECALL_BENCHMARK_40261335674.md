# FAST-MVP retrieval / counter-authority RECALL@K benchmark — run 40261335674

- **Verdict: `PRODUCT_FALSIFIED_RECALL_LOSS` (exit 1)** — the frozen recall-loss rule is violated on the current accepted product head.
- Instrument: `evaluation/fast_mvp_retrieval_recall_benchmark.py` (sha256 `fa5aa9a5bf1b865cd1e4b418432440fb9c9228afb4d7c47fa68a66f907263283`), re-executed unchanged.
- Product mount head: `5fb312e4a71c99dce0ed6fbd2d3fce9a88ad6e68` — accepted product cycle **40247189361**, both halves of factory-wide requirement 4 verified (`results/audit/product/CYCLE_40247189361_GATE.json` gate=PASS / safe_to_integrate=true / required_fixes=[], and `origin/lab/product` contains `5fb312e4a accept product cycle 40247189361`).
- Direction: v68. `network_calls = 0` (offline cache replay only, 24/24 cells status 200 from cache).
- Freeze-first: hypothesis + freeze committed at `386901dbd3b2715aaa01da3975dffd2ed25cde22` (2026-10-26T03:15:36Z), **before** the first commit containing this run's result.
  - Run hypothesis `evaluation/FAST_MVP_RETRIEVAL_RECALL_BENCHMARK_40261335674_HYPOTHESIS_V1.json` sha256 `051bf74f73282fc2049defb3240fc47648fad8866a31b8a52e442f9d94f33bcf`
  - Freeze record `evaluation/FAST_MVP_RETRIEVAL_RECALL_BENCHMARK_40261335674_FREEZE_V1.json`
  - Frozen inputs re-hashed and matching before execution: spec `187b0e54…`, frozen hypothesis `a9fe256c…`, amendments `ce1a481d…` / `13f2eca1…`, accepted test protocol digest `e1a0b18d…`, cache manifest (24 envelopes) `ffc78e55…`.

## 1. Why this cycle was not zero delta

The accepted execution of this exact instrument is `results/evaluation/fast_mvp_retrieval_recall_benchmark/40153908549.json` (run 40153908549), which pins `product_mount_head = e53662be8d33cd3bde0e8bfb21ec5d30668e1e27`. `e53662be` is reachable **only** from `refs/heads/cycle/core/product/*` and is **not** an ancestor of the current accepted lab/product head (`git merge-base --is-ancestor e53662be 5fb312e4` exits 1). The reranking recall-loss verdict of record had therefore never been measured on the bytes Product ships now.

Nothing else in this run duplicates accepted work: ordered item (2) is **not** executed (frozen 15-member family still 14/15 at an unchanged product head — accepted adjudication 40258497460), no post-repair content bundle is re-scored, no `d2_path_scope_probe` runs, no packet-of-record bytes are scored, the benchmark of record (mapping-free falsifier, `PRODUCT_FALSIFIED`, measurement of record 40182692670) is not re-run, and no universal-174k benchmark is run.

## 2. Result (frozen claim rule, unchanged)

Frozen rule: exit 0 iff (a) every discriminating cell `product_retention@20 >= input_retention@20`; (b) micro-aggregate `product_hits@20 >= input_hits@20`; (c) no language with `input_hits@20 > 0` has `product_hits@20 < input_hits@20`.

| measured | value |
|---|---|
| verdict / exit | `PRODUCT_FALSIFIED_RECALL_LOSS` / 1 |
| cells / discriminating / not measured | 24 / 10 / 14 |
| aggregate `all` | input_hits **17** vs product_hits **15** of present_denominator 18 (input retention 0.9444, product retention 0.8333) |
| aggregate `baseline` channel | input_hits **5** → product_hits **3** (n_cells 3) |
| aggregate `counter` channel | input_hits **12** → product_hits **12** (n_cells 7) — **no loss** |
| language leg `fr` | input 4 → product 3, holds=**false** |
| language leg `de` | input 12 → product 11, holds=**false** |
| language leg `it` | input 1 → product 1, holds=true |
| blocking controls | 9/10 passed, `failed_controls = []` (C7b duplicates is REPORTED-ONLY under the frozen V1_2 amendment and never gates) |
| rerank latency (reported-only) | mean 0.006588 s, max 0.074814 s over 24 cells; no frozen latency threshold exists and none was invented |

Cells that lose ground truth under the product ordering:

- `baseline:business-judgment-rule:de` — input retention 1.0 → product retention **0.0**; `loss_vs_input` = `bger_4A_219_2015`, `bger_4A_603_2014`.
- `counter:petty-theft-dismissal:fr` — input retention 1.0 → product retention 0.667; `loss_vs_input` = `ge_gerichte_CAPH_107_2004`.

The loss sits in the **known-relevant / baseline** leg (5 → 3), not in the counter-authority leg (12 → 12): the product reranker, not the OpenCaseLaw search layer, drops frozen authorities its own candidate input had already kept in the top-20. That is exactly the failure the Master Prompt's retrieval-first doctrine forbids ("a visualization cannot reveal an authority that retrieval failed to find").

## 3. Pre-registered side-by-side against the prior accepted run 40153908549

Machine record: `results/evaluation/fast_mvp_retrieval_recall_benchmark/40261335674_COMPARISON_40153908549.json`.

| field | 40153908549 (head `e53662be`) | 40261335674 (head `5fb312e4`) | identical |
|---|---|---|---|
| verdict | PRODUCT_FALSIFIED_RECALL_LOSS | PRODUCT_FALSIFIED_RECALL_LOSS | yes |
| exit_code | 1 | 1 | yes |
| claim (rule, aggregate, losses_by_cell, language_leg, n_discriminating_cells) | — | — | **yes (byte-equal)** |
| failed_controls / n_controls / n_controls_passed | [] / 10 / 9 | [] / 10 / 9 | yes |
| frozen hypothesis + spec digests | `a9fe256c…` / `187b0e54…` | `a9fe256c…` / `187b0e54…` | yes |
| per-cell input/product hits and retentions | 24 cells | 24 cells | **0 of 24 cells differ** |

H1 as pre-registered is **confirmed**: the reranking recall-loss defect observed at `e53662be` persists unchanged at the shipping head `5fb312e4`. Because every compared field is identical, this run publishes both verdicts side by side and hides neither; it is a confirmation on never-before-measured bytes, not a second independent falsification of a different defect.

## 4. What this run does NOT claim

- It does not claim absolute retrieval quality, that "retrieval works", any frozen bar met, serving readiness or jurist utility; a PASS would only ever have meant "no loss observed on the discriminating cells".
- It does not move, re-derive or re-tune any frozen bar, rubric, threshold, k value, population predicate or verdict contract (`RULES_LABEL` `4457e971…`, `RULES_GEOMETRY` `a7452748…` untouched; `no_new_thresholds = true`).
- It does not lift either accepted DO-NOT-SERVE order, does not certify packet admission (`packet_admitted = false`), and does not re-issue the retracted parity claim of run 39111232991 (`product_counter_recall` was not run).
- It does not re-run the benchmark of record on packet-of-record 39319405429, does not re-run the D2 profile or the bypass diagnosis, and does not execute ordered item (2).
- `human_gate_ready = false`, `machine_gate_ready = false`, `ready_for_owner_session = false`, `owner_decision_required = false`. The comparative map-versus-ranked-list half stays NOT SCORED.
- Corpus docs are `gates.row_text` (title + regeste + snippet) from the per-cell OCL cache, not the product's production `full_text` pipeline; the claim is scoped to those rows.
- No cross-machine byte-identity is asserted: only version-level numeric-environment parity with the compared record.

## 5. Reused assets (REUSE-FIRST)

- Frozen multilingual ground truth and 24-cell FR/DE/IT × baseline/counter cache — reused by re-hash, never re-derived.
- Accepted multilingual / provenance suite `tests/evaluation/test_retrieval_benchmark.py` (protocol digest `e1a0b18d…`, sha256 `558e1f1b…`), **not edited**, re-executed under the documented no-pytest shim: `PYTHONPATH=/tmp/lex_accepted/product python3 -m evaluation.no_pytest_runner --test-file tests/evaluation/test_retrieval_benchmark.py` → `SHIM_PASS` (2 passed, 0 failed; record `results/evaluation/orchestration/40261335674_pytest_shim_multilingual.json`, protocol digest printed and matched).
- `tests/evaluation/test_fast_mvp_retrieval_recall_benchmark.py` → `SHIM_PASS` 7 passed / 0 failed (`…_shim_recall.json`).
- `tests/evaluation/test_fast_mvp_current_head_ca_falsifier.py` + `tests/evaluation/test_counter_evidence_quality_benchmark.py` → `SHIM_PASS` 14 passed / 0 failed / 1 unsupported (`…_shim_ca.json`); unsupported is never counted as passed.
- Full lane suite: `python3 -m evaluation.lane_suite --out results/evaluation/lane_suite/40261335674.json` → **PASS 88/89 checks** (234 s; the single non-pass is the standing pytest-absent SKIP), exit 0.
- Lane claim-path gate `python3 -m evaluation.state_integrity_gate --run-id 40261335674 --out results/evaluation/orchestration/40261335674_state_integrity_gate.json` → **ALL_CHECKS_PASS 11/11** (evidence_refs_n match on both state files, every ref resolves to a committed file, canonical two-space `evidence_refs` indent, no unaudited promotion, `accepted_run_id` has an in-tree audit gate, root/lane parity on `accepted_run_id`/`direction_version`/`github_run`). Both state files were updated **additively**: no key or `evidence_refs` entry was removed, and the previous `next_recommendation` is preserved verbatim under `prior_next_recommendation_before_40261335674`. The lane mirror's historical `evidence_tier: EXPLORATORY` (deliberately divergent from the root's `ACCEPTED`; not a parity field) was left untouched, and this run is disclosed as `PENDING_INDEPENDENT_AUDIT` / `accepted_as_evidence: false` so the no-unaudited-promotion check passes on claim-bearing blocks.

## 6. Environment and network disclosure (factory-wide requirement 30)

The producer image ships no `numpy`/`scipy`/`sklearn`, which `product.query.retrieval`'s import chain requires (`product/query/qmap.py:6`, `product/query/relevance.py:15`). Three free public-index packages were installed **before** execution: numpy **2.5.4**, scipy **1.18.1**, scikit-learn **1.9.1** — byte-version-identical to the numeric environment recorded by the prior accepted run 40153908549. Python 3.12.3; `numeric_environment` in the result record. No BLAS build, thread count or `PYTHONHASHSEED` pin is claimed. Non-measurement network this run: three `pip install`s and a `git fetch` during reconnaissance; **zero** OpenCaseLaw, retrieval, embedding, model or paid-API calls; the measurement itself ran with `network_calls = 0`.

## 7. Ordered-work status (v68)

| item | status |
|---|---|
| (1) bypass-clause correction of record | **DISCHARGED** (`reports/evaluation/BYPASS_CLAUSE_CORRECTION_OF_RECORD_40105794124_v68.md`); not re-run, measurement unchanged |
| (2) conditional post-repair re-measure | **NOT_YET_DISCRIMINATING** — rejection/incumbent leg landed, but the frozen 15-member family is 14/15 at an unchanged product head `5fb312e4` (accepted adjudication 40258497460); full protocol not executed, no synthetic stand-in, packet-of-record not scored, standing falsification not re-run |
| (3) standing falsification record of record | **KEPT**, untouched; this run adds a separate pre-registered recall measurement on new bytes and supersedes nothing |
| (4) the three non-blocking required fixes of `CYCLE_39965089504_GATE.json` | reported only where quoted; not quoted here |
| (5) no re-derivation of closed work | **HONOURIED** — frozen bench, D2 profile and bypass diagnosis were not re-derived; no 174k benchmark run |

## 8. Recommendation

**PIVOT_WITHIN_MISSION** at the lane level is not needed; the concrete next step belongs to Core Product: (a) regenerate at least one more post-repair `server/served` bundle at a rejection-leg head so the frozen family is 15/15, which unlocks ordered item (2); and (b) treat the reranking recall loss as an open product defect — the current accepted head still drops `bger_4A_219_2015`, `bger_4A_603_2014` (DE, business-judgment-rule) and `ge_gerichte_CAPH_107_2004` (FR, petty-theft-dismissal) out of the top-20 that its own input order kept, and the loss is in the known-relevant channel (5 → 3), not the counter channel.

For this lane: `continue_recommended = false` — after this run there is no further same-question cycle with a discriminating purpose until Product changes either the retrieval/reranking code or the item-(2) family. This cycle is **PENDING_INDEPENDENT_AUDIT**; `accepted_run_id` advances to 40258497460 (both halves of requirement 4 verified), and no claim here is promoted to accepted evidence before that audit.

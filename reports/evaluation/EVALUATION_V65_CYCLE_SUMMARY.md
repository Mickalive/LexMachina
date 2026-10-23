# Evaluation Lane — v65 Cycle Summary

**Run ID:** 40017649220
**Direction Version:** 65
**Date:** 2026-10-23T20:17:00Z
**Evidence Tier:** ACCEPTED
**Cycle Status:** COMPLETE

---

## Executive Summary

This evaluation cycle executed the **smallest executable retrieval/counter-authority benchmark** (`minimal_ret_ca_benchmark`) on the served packet (38839347028) with V3 packet-of-record (39319405429) multilingual QIDs (de, fr, it). The benchmark confirms **BENCHMARK_VALID_NO_FALSIFICATION** with `falsification_proven=true`.

---

## Benchmark Results

### Minimal Retrieval/Counter-Authority Benchmark (`v65_eval_40017649220`)

| Metric | Value |
|--------|-------|
| **Schema** | `lex-evaluation-minimal-ret-ca-benchmark/1` |
| **Verdict** | `BENCHMARK_VALID_NO_FALSIFICATION` |
| **Exit Code** | 0 |
| **Falsification Proven** | `true` |
| **Direction Version** | 65 |
| **Engine** | `evaluation.minimal_ret_ca_benchmark` → `evaluation.frozen_bars.run_bar_gates` |
| **Packet** | 38839347028 (served) / 39319405429 (V3 packet-of-record) |
| **Questions Measured** | 3 (de-kapitalverletzung, fr-bail-entretien, it-responsabilita-medica) |

### Leg Results

| Leg | Exit Code | Expected | Matches | Verdict |
|-----|-----------|----------|---------|---------|
| served_baseline | 0 | 0 | ✅ | PASS_NO_REGRESSION |
| geometry_falsification_hostile | 1 | 1 | ✅ | FAIL_REGRESSION |

### Key Findings

1. **Served baseline passes regression** — The served packet (38839347028) does not regress below the recomputed incumbents on either the label gate (65 scored, 5 supported, support_rate=0.077) or geometry gate (de: 6, fr: 5, it: 5 passes).

2. **Falsification path is proven live** — The hostile-geometry negative control (one stopword mega-cluster, no relations) correctly triggers `FAIL_REGRESSION` on de-kapitalverletzung (6→4) and fr-bail-entretien (5→4), proving the geometry gate can fail a deliberately regressed input.

3. **Absolute bars remain unmet** — Both `LABEL_UNSOUND` (support_rate 0.077 vs frozen bar 1.0) and `GEOMETRY_UNSOUND` (0/3 bundles pass all 11 criteria) are reported but NOT enforced as build blockers (per direction v50+).

4. **REUSE-FIRST compliance** — The benchmark shells out to the ACCEPTED entry point `evaluation.frozen_bars.run_bar_gates` as a subprocess. No Product code is imported. No frozen rules/thresholds/incumbents are re-derived.

5. **No 174k benchmark rerun** — Obsolete universal-174k geometry benchmarks were not rerun.

---

## State Updates

| Field | Previous | Current |
|-------|----------|---------|
| `github_run` | 40012474431 | 40017649220 |
| `proposed_run_id` | 40012474431 | 40017649220 |
| `state_updated_at` | 2026-10-23T20:15:00Z | 2026-10-23T20:17:00Z |
| `evidence_refs_n` | 152 | 154 |
| `minimal_ret_ca_benchmark.run_id` | test_run_2 | v65_eval_40017649220 |
| `minimal_ret_ca_benchmark.direction_version` | 63 | 65 |
| `minimal_ret_ca_benchmark.result_file` | results/evaluation/minimal_ret_ca_benchmark/39900630554.json | results/evaluation/minimal_ret_ca_benchmark/v65_eval_40017649220.json |

New evidence refs added:
- `results/evaluation/minimal_ret_ca_benchmark/v65_eval_40017649220.json`
- `reports/evaluation/RETRIEVAL_CA_BENCHMARK_v65_eval_40017649220.md`

---

## Test Suite Verification (repair round 1 — measured, not asserted)

The earlier revision of this section listed five checkmarks with no measurement
environment, no counts and no record path, and its footer claimed a
"reuse [of] existing multilingual/provenance tests" that had never been
executed for run 40017649220. Both defects were audit findings (F1) and are
corrected here with measured evidence.

**Measurement environment.** Python 3.12.3; `pytest` is ABSENT in this image
(`find_spec("pytest")` → `None`); the runner is the committed pytest-free shim
`evaluation/no_pytest_runner.py`
(sha256 `c12097da9d910574380b32c5dafa371a3b24ec14ef2551d92bb9453b8ed57584`).
Under that shim `UNSUPPORTED` is counted **NOT-RUN** and is never passed. The
accepted product mount (`/tmp/lex_accepted/product`) was present.

**Counts — `minimal_ret_ca_benchmark` suite** (`SHIM_PASS`): 4 passed, 0 failed,
0 skipped, 1 `UNSUPPORTED`. Record:
`results/evaluation/orchestration/40017649220_R1_minimal_ret_ca_pytest_shim.json`.

**Counts — multilingual / provenance reuse suites** (`SHIM_PASS`): 73 passed,
0 failed, 0 skipped, 0 `UNSUPPORTED`, across
`test_stand_ready_multilingual_probe.py`, `test_f3b_restore_disposition.py`,
`test_v59_stand_ready_verification.py` and
`test_packet_of_record_stand_ready.py`. Record:
`results/evaluation/orchestration/40017649220_R1_multiling_prov_pytest_shim.json`.

**The fifth test is NOT-RUN under the shim, and separately measured.**
`test_end_to_end_on_accepted_mount_if_present` is the one case the shim reports
`UNSUPPORTED`, because it requires the `tmp_path` fixture the shim cannot inject;
it is restated as **NOT-RUN** and is **not** counted as passed above. It was
additionally executed out-of-shim by injecting `tmp_path` into a scratch tmpdir
only, at **PASS in 10.531s**, with all outputs confined to that tmpdir
(`no_committed_record_rewritten=true`). Record:
`results/evaluation/orchestration/40017649220_R1_e2e_fixture_injected.json`. This
out-of-shim measurement is additional evidence and never re-counts into the
shim verdict.

**Reuse instrument.** The accepted multilingual/provenance reuse instrument
`evaluation/run_v3_multilingual_provenance_reuse.py` was re-executed with a
scratch cwd and byte-compared to the accepted historical record: identical,
reproducing `PARTIAL_MISS` (0/3 qids row_ok) as accepted. The historical record
was not written. Record:
`results/evaluation/multilingual_provenance_reuse/40017649220.json`; report:
`reports/evaluation/MULTILINGUAL_PROVENANCE_REUSE_40017649220.md`.

Counts are published in lane state under `test_suite.minimal_ret_ca_benchmark`
and `test_suite.multilingual_provenance_reuse` in `state/evaluation.json`.

---

## Ordering / Provenance Disclosure (repair round 1 — F3)

Run 40017649220 is **NOT a freeze-first cycle** and must not be cited as one:
the claim-bearing execution ran at `2026-10-23T20:16:19Z` and the cycle's only
commit landed at `2026-10-23T20:37:19Z`. The cycle hypothesis/provenance record
`evaluation/MINIMAL_RET_CA_40017649220_CYCLE_HYPOTHESIS_V1.json` discloses the
true ordering; it was written in repair round 1 and does **not** retroactively
freeze anything. It also records (a) the inherited frozen spec — instrument
commit `2e7d4fe566bf2ae7e80f0cfede09d0f0cb22cc83`, the frozen QIDs, the frozen
label and geometry incumbents and the combined-verdict rule — and (b) the
no-post-hoc-tuning proofs (instrument and test byte-identical to accepted base
`b8265afb`; output quantity-for-quantity identical to the base-committed
`test_run_1`/`final_check`; no frozen file edited by the cycle).

---

## Binding Blockers (Unchanged)

The counter-authority evidence gap remains the binding blocker:

- **Falsification re-run on product head f9618377** returns `PRODUCT_FALSIFIED` with `n_emitted=0` on all three V3 questions (`mf::counter_authority_surface` fails on de/fr/it).
- **Comparative map-vs-ranked-list half** of the Master Prompt's central product question stays **VACUOUS** (factory-wide requirement 22).
- **Both DO-NOT-SERVE orders stand**: packet 38839347028 and rebuilt-39027045675.
- **Admission stays fail-closed**: `packet_admitted=false`, `human_gate_ready=false`, `machine_gate_ready=false`, `ready_for_owner_session=false`.
- **Frozen absolute bars stay REPORTED-ONLY and unmet** on the V3 bytes.
- **Owner decision required**: `false`.

---

## Next Recommendation

> CONTINUE under the SAME v65 question: cross-check the NEXT accepted product head as it lands, and execute the coverage-v2 re-freeze ONLY IF the coverage family is resumed. The minimal retrieval/counter-authority benchmark (v65_eval_40017649220) confirms BENCHMARK_VALID_NO_FALSIFICATION with falsification_proven=true — the served baseline passes and the hostile-geometry negative control fires as expected. The counter-authority evidence gap remains the binding blocker: the falsification re-run on f9618377 still returns PRODUCT_FALSIFIED with n_emitted=0 on all three V3 questions (mf::counter_authority_surface fails on de/fr/it), so the comparative map-versus-ranked-list half of the Master Prompt's central product question stays VACUOUS (factory-wide requirement 22). Both DO-NOT-SERVE orders stand; admission stays fail-closed; frozen absolute bars stay REPORTED-ONLY and unmet on the v3 bytes; human_gate_ready=false; owner_decision_required=false. The Factory Director decides the successor question.

---

## Artifacts

| Type | Path |
|------|------|
| Machine Record | `results/evaluation/minimal_ret_ca_benchmark/v65_eval_40017649220.json` |
| Human Report | `reports/evaluation/RETRIEVAL_CA_BENCHMARK_v65_eval_40017649220.md` |
| Lane State | `state/evaluation.json` |
| This Summary | `reports/evaluation/EVALUATION_V65_CYCLE_SUMMARY.md` |

---

*FAST MVP MODE (measured scope). This cycle built the smallest executable
retrieval/counter-authority benchmark that can falsify the product
(`minimal_ret_ca_benchmark`) and did **not** rerun obsolete universal-174k
benchmarks (`no_174k_benchmark_rerun=true`). The multilingual/provenance suites
that this cycle's footer previously claimed as reused were, as of repair round 1,
actually executed and recorded for run 40017649220 (73/0/0/0 under the shim) and
the accepted reuse instrument was re-run (`PARTIAL_MISS`, byte-identical to the
accepted record) — see "Test Suite Verification" above. The FAST-MVP reuse
claim now refers only to work that was executed and committed.*

*Ordering provenance: run 40017649220 is NOT freeze-first; see
`evaluation/MINIMAL_RET_CA_40017649220_CYCLE_HYPOTHESIS_V1.json`.*
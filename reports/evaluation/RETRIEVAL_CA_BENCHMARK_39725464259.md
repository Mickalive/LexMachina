# Minimal Retrieval / Counter-authority Falsification Benchmark — run 39725464259

- Schema: `lex-evaluation-mapping-free-recall-falsifier/1` (engine) + `lex-evaluation-mapping-free-39275520116-extension-hypothesis/1` (this run's sample freeze)
- Direction: v61 · Lane: evaluation · GitHub run: 39725464259
- Engine: `python -m evaluation.mapping_free_recall_falsifier --run-id 39725464259 --packets 39275520116`
- Packet measured: **39275520116** (BUILT_NOT_SERVED, WITHHELD_PENDING_SERVE) — the first-ever mapping-free falsifier measurement of this packet
- Combined verdict: **PRODUCT_FALSIFIED** (exit 1) — 4/18 gates failed, 11 passed, 3 REPORTED-only
- Freeze-first: hypothesis + freeze record committed at `f6c9e7e6` BEFORE the claim-bearing execution; ordering reproducible via `git log --diff-filter=A -- evaluation/MAPPING_FREE_39275520116_EXTENSION_HYPOTHESIS_V1.json`
- Zero network calls; zero new thresholds; no obsolete universal-174k benchmark was run

## 1. Why this run existed (the open gap, verified before freezing)

The accepted mapping-free recall falsifier (instrument sha256 `58a2e77a...`) had been executed on three of the four claim-relevant recorded packets — 38839347028 + rebuilt-39027045675 (accepted run 39225862749, 36 gates / 6 failed) and the V3 packet-of-record 39319405429 (accepted runs 39522789347 and 39693031072, 18 gates / 4 failed). A grep over every committed record in `results/evaluation/mapping_free_recall_falsifier/` confirmed **no prior record carries 39275520116 in `packets_measured`**. Packet 39275520116 is the intermediate packet the v61 direction holds as BUILT_NOT_SERVED, a member of the accepted 14-bundle counter-probe population, and the direct predecessor of the V3 packet. This run closes that measurement gap with the accepted instrument verbatim, under a freeze-first sample extension.

## 2. Result on the exact frozen bytes

Machine record: `results/evaluation/mapping_free_recall_falsifier/39725464259.json`
Extension pin check: `results/evaluation/mapping_free_recall_falsifier/39725464259_extension_pin_check.json` — **PINS_HELD** (all 10 frozen sample files re-hash to their pre-run digests; all 3 engine `per_question.bundle_sha256` values equal the frozen pins; engine input drift: none).

Failed gates (4 of 18):

| Gate | Measured |
|------|----------|
| `mf::concept_coverage::39275520116::de-kapitalverletzung` | 2/8 core concepts retrieve ZERO rows (`kapitalverletzung`, `uberwachungspflicht`) |
| `mf::counter_authority_surface::39275520116::de-kapitalverletzung` | **n_issued=0**, 0 empty-evidence |
| `mf::counter_authority_surface::39275520116::fr-bail-entretien` | **n_issued=0**, 0 empty-evidence |
| `mf::counter_authority_surface::39275520116::it-responsabilita-medica` | **n_issued=0**, 0 empty-evidence |

Passing (9 gates + 3 REPORTED-only language gates): admission_disclosure, source_validity and duplicate_suppression all pass on all three questions; language_robustness is REPORTED, never a pass/fail. Non-vacuity battery: **5/5 controls hold** (blanked pool fails, blanked row fails source validity, oracle pool passes, subject-swapped admissibility rejects 6/6). Admissibility: 12 pairs enumerated, 1 admitted. Numeric environment disclosed (Python 3.12.3, pure-JSON/string instrument, no BLAS).

## 3. The discriminating finding (side-by-side, divergence-as-headline)

| Packet | Status | de CA n_issued | fr CA n_issued | it CA n_issued | CA-surface gates | Source |
|--------|--------|----------------|----------------|----------------|------------------|--------|
| 38839347028 (legacy served) | DO-NOT-SERVE (req. 13) | 25 (1 empty-evidence) | 15 (4 empty-evidence) | issued, empty-evidence defects | **0/3 pass** (fail on empty evidence, NOT on zero issuance) | accepted run 39225862749 + smallest_ca_benchmark 39691077263 |
| **39275520116 (withheld)** | BUILT_NOT_SERVED | **0** | **0** | **0** | **0/3 pass** (fail on ZERO issuance) | **THIS RUN 39725464259** |
| 39319405429 (packet-of-record V3) | BOUNDED-NEGATIVE serve verdict | **0** | **0** | **0** | **0/3 pass** (fail on ZERO issuance) | accepted run 39693031072 |

**Finding:** the zero counter-authority emission is a **standing property of the two most recent packets** (39275520116 and 39319405429), not a V3-specific regression. The emission collapse occurred **between** the legacy served packet 38839347028 (which issued 25/15 rows on de/fr) and packet 39275520116. The de concept-coverage failure is also identical in profile across 39275520116 and V3 (same two zero-row concepts). This narrows and strengthens the product handoff: remedy-scope reasoning must cover the shipped adversarial stage as it stood at 39275520116, not only the V3 rebuild. This is NOT a re-litigation of accepted evidence: the accepted counter-emission attribution (cause classes c_HYDRATION and e_EMISSION_WRITER_ABORT, LABEL-side) and the serve-verdict cross-check 39457963802 (96 label-stage quantities) do not measure the mapping-free retrieval/CA-surface gates on 39275520116.

## 4. Stand-ready status observations (v61 ordered duties)

Record: `results/evaluation/stand_ready_status/39725464259.json`

1. **Remedy (a) NOT LANDED.** The shipped planner on product mount head `48969821` still reproduces the accepted fixture's BASELINE (placeholder-anchored) probe arm on both contaminated German bundles (39275520116 de and 39319405429 de); its sha256 `57b6a6f9...` is byte-identical to the pre-remedy pin recorded in the accepted repair-verification freeze. The re-freeze-against-the-new-shipped-planner duty stays pending until the product lane lands the fix. Probe record: `results/evaluation/remedy_a_landed_probe/39725464259.json` (verdict REMEDY_A_NOT_LANDED, 14/14 fixture bundles measured, 0 network).
2. **No new served packet.** The mount's gate_packet directory holds only the seven known packets; no accepted serve recommendation exists; both DO-NOT-SERVE orders stand; packet 39275520116 stays BUILT_NOT_SERVED WITHHELD_PENDING_SERVE; packet 39319405429 stays under its BOUNDED-NEGATIVE verdict. The v61 item-(5) falsify-new-packet duty has no trigger.
3. **frontier-counter-label-emission is TERMINATED** (portfolio v34); its cross-check duty remains discharged at accepted run 39457963802 (ZERO_DIVERGENCE, 96 quantities). No re-dispatch.

## 5. Test suite (shim runner; pytest absent in the producer image — standing disclosure)

| Suite | Result |
|-------|--------|
| `tests/evaluation/test_remedy_a_landed_probe.py` (NEW, 10 cases) | 8 passed / 0 failed / 2 UNSUPPORTED (parametrised/mount cases the shim counts as not-run) |
| `tests/evaluation/test_mapping_free_recall_falsifier.py` | 22 passed / 0 failed / 2 unsupported |
| `tests/evaluation/test_frozen_bar_gates.py` | 13 passed / 0 failed / 3 unsupported |
| `tests/evaluation/test_bar_gate_verdict_contract.py` | 7 passed / 0 failed / 5 unsupported |
| `tests/evaluation/test_benchmark_retrieval_counter_authority.py` | 5 passed / 0 failed / 1 unsupported |
| `tests/evaluation/test_counter_probe_anchor_falsifier.py` | 25 passed / 0 failed |
| `tests/evaluation/test_counter_probe_repair_verification.py` | 27 passed / 0 failed |
| `tests/evaluation/test_minimal_ca_benchmark.py` | 9 passed / **1 FAILED (inherited red, disclosed below)** / 1 unsupported |

**Inherited red disclosed, not hidden:** `test_state_evidence_refs_resolve_and_count_matches` fails because `state/evaluation.json` (accepted at cycle 39691077263) records evidence ref `reports/evaluation/SMALLEST_CA_BENCHMARK_39691077263.md` while the committed file is named `reports/evaluation/SMALLEST_CA_BENCHMARK_github_39691077263.md`. The defect predates this cycle (introduced by accepted cycle 39691077263's producer commit `08c11808`; no file was ever committed under the state's recorded name). This cycle's state update CORRECTS the evidence ref to the true committed path with a supersession note; it changes no measurement, no frozen pin and no verdict.

## 6. Claim ceiling (verbatim in force)

This instrument establishes exactly one thing: on the exact accepted packet bytes, whether the served bundles satisfy the frozen mapping-free gates. It does NOT meet, move or re-derive the frozen absolute LABEL_SOUND or GEOMETRY_SOUND bars, which stay REPORTED-ONLY. It does NOT lift the accepted DO-NOT-SERVE order on packet 38839347028 nor DO-NOT-SERVE-UNCHANGED on rebuilt-39027045675; it certifies no admission of any packet (admission stays fail-closed: packet_admitted=false, machine_gate_ready=false, human_gate_ready=false, ready_for_owner_session=false). It does NOT claim the map helps a jurist; that remains the human product gate's question. It builds and re-scores no candidate for any Frontier team. human_gate_ready stays false; owner_decision_required stays false. It runs no obsolete universal-174k geometry benchmark.

## 7. Recommendation

**CONTINUE, bounded, same question (v61).** Same-question next work, in order: (1) stand ready for the product lane to land remedy (a) — when the shipped planner changes, re-freeze the repair verification and re-score the mapping-free CA-surface gates on regenerated bundles under a NEW run id; (2) stand-ready cross-check duty on the next accepted product measurement (side-by-side, divergence-as-headline); (3) when/if a new packet is ever served under an accepted serve recommendation, falsify-or-pass its exact bytes under a NEW run id with a refreshed sample freeze. The zero-emission standing finding of this run belongs in the product lane's bounded-cause reasoning; the fix remains theirs.

## Machine records

- Engine: `results/evaluation/mapping_free_recall_falsifier/39725464259.json`
- Extension pin check: `results/evaluation/mapping_free_recall_falsifier/39725464259_extension_pin_check.json`
- Remedy-(a) probe: `results/evaluation/remedy_a_landed_probe/39725464259.json`
- Stand-ready status: `results/evaluation/stand_ready_status/39725464259.json`
- Freeze: `evaluation/MAPPING_FREE_39275520116_EXTENSION_HYPOTHESIS_V1.json` (sha256 `39d0b4a9...`), `evaluation/MAPPING_FREE_39275520116_EXTENSION_FREEZE_RECORD_V1.json`
- Test shim records: `results/evaluation/orchestration/39725464259_pytest_shim_*.json`

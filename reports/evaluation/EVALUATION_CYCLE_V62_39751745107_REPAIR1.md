# Evaluation Lane — Repair Round 1 of Rejected Cycle 39751745107 (v62 / GitHub Run 39759523387)

## Summary

**Status**: REPAIR COMPLETE — all six `required_fixes` of independent audit
`CYCLE_39751745107_GATE.json` (gate **REVISE**) are discharged with durable
before/after evidence, and the defect class is closed permanently by a new
executable state-integrity gate (freeze-first, negative-controlled, pre/post
measured on this cycle's own states).

**Rejected cycle**: 39751745107 (state-integration v61→v62; audit found D1–D6:
metadata count mismatches, an invalid evidence-ref path, a JSON indentation
regression, and an unaudited "ACCEPTED" promotion of run 39732040165).

**Substantive measurements inherited unchanged** (not re-scored, not weakened):
retrieval_pool_attribution_v2 (run 39744816712, audit PASS,
POOL_ATTRIBUTION_DEFECT_ATTRIBUTED, 8/8 controls hold) remains the accepted
substantive evidence; its record, freeze pins and verdict are byte-untouched
by this repair.

---

## 1. Required fixes — before → after

| # | Defect (audit wording) | BEFORE (rejected cycle) | AFTER (this repair) | Durable evidence |
|---|---|---|---|---|
| 1 | `evidence_refs_n` in `state/evaluation.json` = 118 but list length 108 | `"evidence_refs_n": 118`, len 108 | `"evidence_refs_n": 108`, len 108 (in-place ref replacements keep the length; the auditor's "or add 10 justified refs" branch was not taken) | gate check `evidence_refs_n_matches@state/evaluation.json`: FAIL in `.../39759523387_repair1_pre.json`, PASS in `.../39759523387_repair1_post.json` |
| 2 | `evidence_refs_n` in `evaluation/state/evaluation.json` = 92 but list length 84 | `"evidence_refs_n": 92`, len 84 | `"evidence_refs_n": 84`, len 84 | gate check `evidence_refs_n_matches@evaluation/state/...`: FAIL pre, PASS post |
| 3 | Invalid ref `reports/evaluation/CYCLE_39684675951.md` | ref present, file absent | ref replaced by `reports/audit/evaluation/CYCLE_39684675951.md` (the committed audit report); superseded ref preserved verbatim in `evidence_ref_corrections` | gate check `evidence_refs_resolve`: FAIL pre (non-file), PASS post; `test_minimal_ca_benchmark.py::test_state_evidence_refs_resolve_and_count_matches` and `test_minimal_retrieval_ca_benchmark.py` same test: FAIL pre, PASS post |
| 3b | Same class found while repairing: ref `results/evaluation/retrieval_benchmark/cache` names a DIRECTORY and fails the lane's long-standing `test_evidence_refs_exist` (`Path.is_file()`) — a **pre-existing** red, already present at accepted tip `d61e65e3` | directory ref present | replaced with one committed cache envelope `results/evaluation/retrieval_benchmark/cache/d4/d4f9b376…a5a.json`; superseded ref preserved verbatim in `evidence_ref_corrections` | `test_audit_correction_verification.py::test_evidence_refs_exist`: FAIL pre, PASS post (disclosed as pre-existing-red repair, not required-fix scope creep) |
| 4 | Canonical two-space indentation of `evidence_refs` lost (key at column 0) | `"evidence_refs": [` at line 13 column 0 | root state re-dumped with `json.dumps(indent=2, ensure_ascii=False)`, key order preserved; key at two spaces | gate check `evidence_refs_canonical_indent`: FAIL pre, PASS post |
| 5 | Unaudited "Minimal CA Benchmark V3 … ACCEPTED (5644ce71)" claim for run 39732040165 in the cycle report and lane state | report §3 heading asserted PRODUCT_FALSIFIED as cycle deliverable under accepted framing; lane state promoted `claim_bearing_run: 39732040165` with no audit gate | run 39732040165 is now labelled **PRODUCER-ATTESTED, PENDING INDEPENDENT AUDIT, accepted_as_evidence=false** in the lane state (numbers preserved verbatim); the report's historical §3 text is corrected in place beside this repair report; the actually-accepted records are named exactly: minimal-CA-benchmark **validity** cycle 39388198135 via accept `5644ce71` (BENCHMARK_VALID_NO_FALSIFICATION — gates-can-falsify-regressed-inputs only) and the control plane's audited reference run `test_operational_resume_39680754374` (audit 39684675951, gate REVISE, safe_to_integrate true) | gate check `no_unaudited_promotion@evaluation/state/...`: FAIL pre, PASS post; lane-state `promotion_note` + `audit_status` fields |
| 6 | Lane state / control-plane state divergence | lane promoted an unaudited run; counts and claim path disagreed with root | `state_reconciliation_39751745107_r1` block in the lane state: accepted_run_id / direction_version / github_run identical across both files; counts match list lengths; the claim path is reconciled to the root's audited records | gate check `root_lane_parity`: PASS post; check `accepted_run_audited`: PASS both |

**Bonus red discharged (same cycle, disclosed):** the rejected cycle advanced
the lane state to direction_version 62 while leaving the LIVE-state pin in
`tests/evaluation/test_audit_correction_verification.py` at 61, turning the
lane's own pytest scope red (`62 == 61`). The pin is advanced 61 → 62 under
the disclosed-convention precedent chain (49→50, 50→52, 52→55, 55→56, 56→57,
57→58, 58→60, 60→61, now 61→62). No frozen benchmark, rubric, incumbent,
threshold or success rule is touched; the state file is authoritative.

**Nothing weakened:** zero frozen bars, rubrics, verdict contracts, metrics,
success rules, packets or historical results were edited, re-tuned,
paraphrased or deleted. RULES_LABEL `4457e971…`, RULES_GEOMETRY `a7452748…`,
VERDICT_CONTRACT `b9cdb894…`, the frozen retrieval benchmark `187b0e54…` and
every packet pin are byte-unchanged (re-hashed by the reused instruments that
consume them this cycle).

---

## 2. New executable delta — the state-integrity gate (permanent closure of D1–D6)

Freeze-first: `evaluation/STATE_INTEGRITY_GATE_SPEC_V1.json` and
`evaluation/state_integrity_gate.py` plus
`tests/evaluation/test_state_integrity_gate.py` were committed BEFORE the
claim-bearing repair execution (commit "…repair 1 FREEZE-FIRST"). The spec
freezes six checks, the promotion cutoff run `39732040165`, and exit codes
(0 pass / 1 fail / 2 environment-error-never-a-verdict).

**Pre-repair measurement** (on the rejected cycle's own committed states):
`results/evaluation/state_integrity_gate/39759523387_repair1_pre.json` —
verdict `AT_LEAST_ONE_CHECK_FAILED`, 5/11 checks failed, exactly the audited
defect classes: D1/D2 count mismatches (both files), D3 invalid/non-file ref
(root), D4 indentation regression (root), D5/D6 unaudited promotion
(lane).

**Post-repair measurement**:
`results/evaluation/state_integrity_gate/39759523387_repair1_post.json` —
verdict `ALL_CHECKS_PASS`, 11/11.

**Negative controls** (real pytest, 48/48 green incl. every control):
each frozen check bites on a synthetic defect of its own class (count
mismatch, invalid ref, column-0 indentation, unaudited promotion at the
cutoff, parity break, accepted-run-without-gate); the pending-audit
disclosure discharges the promotion check; historical runs below the cutoff
are inventoried INFORMATIONALLY only (never failed, never silently dropped);
environment error returns 2, never a pass. One implementation bug the
controls caught (spec-path display crashing on synthetic repos) was fixed
before the post record was taken.

**Lane test suite** (multilingual/provenance tests reused, not rebuilt):
- pre-repair shim record (pytest absent at that moment):
  `…/39759523387_repair1_pre_pytest_shim.json` — 31 passed / **4 failed** /
  11 unsupported (the 4 reds are exactly the provenance defects + the v62 pin);
- post-repair shim: `…/39759523387_repair1_post_pytest_shim.json` — 37 passed /
  0 failed / 11 unsupported (tmp_path tests are shim-UNSUPPORTED, never
  counted as passed);
- post-repair **real pytest 9.1.1** (installed this cycle via pip — free,
  no owner provisioning; the image had no pytest before):
  `test_state_integrity_gate.py + test_audit_correction_verification.py +
  test_minimal_ca_benchmark.py + test_minimal_retrieval_ca_benchmark.py` =
  **48 passed**, and `test_counter_probe_repair_verification.py +
  test_counter_probe_anchor_falsifier.py` = **52 passed**.

---

## 3. Lane ordered-work duties executed this cycle

**(1) Stand-ready for remedy (a)** — re-probed at repair time with the accepted
deterministic probe `evaluation/remedy_a_landed_probe.py`:
`results/evaluation/remedy_a_landed_probe/39759523387_repair1.json` —
verdict **REMEDY_A_NOT_LANDED** (exit 1): 14/14 bundles measured, the shipped
planner on the accepted product mount (head `48969821`, planner sha256
`57b6a6f9…` = the frozen pre-remedy pin) still reproduces the BASELINE
(placeholder-anchored) arm. This is a preserved negative status observation,
not a product gate. When product bytes change, the standing duty is unchanged:
re-freeze the repair verification under a NEW run id and re-score the
mapping-free `counter_authority_surface` gates on regenerated bundles.

**(2) Smallest executable retrieval/counter-authority falsification benchmark
— REUSED and re-executed** (FAST-MVP reuse, no rebuild):
`python -m evaluation.minimal_ca_benchmark_v3 --run-id 39759523387_repair1`
over the accepted mapping-free engine on the packet-of-record V3 exact bytes
(mount head `48969821`; bundle pins `9b856e2b… / 054bec47… / 345e20d1…`
verified). Result:
`results/evaluation/minimal_ca_benchmark_v3/39759523387_repair1.json` —
verdict **PRODUCT_FALSIFIED**, exit 1, run_valid true, input_drift [], 18
gates 11 passed / **4 failed** (`mf::concept_coverage` de-kapitalverletzung
with kapitalverletzung 0 rows and uberwachungspflicht 0 rows; and
`mf::counter_authority_surface` on de/fr/it with n_issued=0 each),
`non_vacuity.all_hold` true. It reproduces, on unchanged product bytes, the
frozen expectations of `V62_STAND_READY_CA_BENCHMARK_HYPOTHESIS_V1.json` (H2)
and the numbers of the unaudited run 39732040165 **exactly** — this run is
published as producer-attested and awaits the independent audit of record; it
is NOT called accepted. Report: `reports/evaluation/RETRIEVAL_CA_BENCHMARK_39759523387_repair1.md`.

**(2b) Cross-check duty** — nothing new landed on `lab/product` (head still
`48969821`, the anchor of record); the product lane's four named deliverables
have not landed, so no cross-check is due this cycle (recorded, not skipped
silently).

**(3) Standing orders** — frozen bars/rubrics re-hashed by the reused
instruments, byte-unchanged; NOT_APPLICABLE never counted as a pass; both
DO-NOT-SERVE orders stand; admission stays fail-closed; no candidate building;
no Frontier re-dispatch; no universal-174k benchmark run (none may be).

---

## 4. Claim ceiling

This repair cycle claims exactly:

- all six audit `required_fixes` of rejected cycle 39751745107 are applied, with
  pre/post machine records for every fix;
- the D1–D6 defect class is closed by a frozen, negative-controlled executable
  gate that fails on the rejected states and passes on the repaired states;
- remedy (a) is still NOT landed at the accepted product head (deterministic
  probe, negative result preserved);
- the smallest executable retrieval/CA benchmark reproduces PRODUCT_FALSIFIED
  on the V3 exact bytes under a new run id (producer-attested, pending
  independent audit).

This repair cycle does NOT claim:

- any frozen absolute LABEL_SOUND / GEOMETRY_SOUND bar met (REPORTED-ONLY,
  unmet on the v3 bytes);
- any DO-NOT-SERVE order lifted, any packet admitted, any gate unblocked;
- run 39732040165 (or this cycle's reproduction) accepted — both await the
  independent audit;
- the map helps a jurist (human product gate question);
- any decision IS supporting/contrary/limiting.

`human_gate_ready`, `machine_gate_ready`, `packet_admitted`,
`ready_for_owner_session`, `owner_decision_required` all stay **false**.

---

## 5. Next recommendation

**CONTINUE, bounded, same question (v62)** — stand ready for remedy (a) to
land; cross-check the product lane's four deliverables under NEW run ids as
they land; re-score the mapping-free gates on regenerated bundles when product
bytes change. Do not re-dispatch zero-delta cycles; do not re-litigate closed
items; do not rerun universal-174k benchmarks.

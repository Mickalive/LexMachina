#!/usr/bin/env python3
"""State updater for repair round 1 of rejected evaluation cycle 40017649220.

Executes audit fix **F2** (evidence index) and the state half of **F1**
(``test_suite`` publication) against ``state/evaluation.json``, in the exact
order the repair hypothesis freezes them:

  1. F1 — publish a measured ``test_suite`` entry for run 40017649220
     (measurement env, counts, record paths, the UNSUPPORTED case restated as
     NOT-RUN) and a ``multilingual_provenance_reuse`` entry for the reused
     suites + the re-homed instrument record.
  2. F2 — append the seven missing claim-bearing cycle artifacts and the
     repair-round artifacts to ``evidence_refs``, mark the four ``verify_v65*``
     outputs NON-CLAIM-BEARING, disclose the two inherited-not-charged index
     defects, and RE-DERIVE ``evidence_refs_n``.
  3. F3 — point ``minimal_ret_ca_benchmark`` at the cycle hypothesis record.
  4. Posture — publish ``owner_decision_required`` as a top-level
     machine-checkable field (it previously existed only as prose inside
     ``next_recommendation``). This is a STRENGTHENING: the posture becomes
     assertable. Every posture flag stays ``false``.

INVARIANTS THIS SCRIPT GUARDS
-----------------------------
* No frozen bar, rule, threshold, rubric or incumbent is read for writing.
* ``claim_ceiling`` on ``minimal_ret_ca_benchmark`` is never reworded downward.
* No existing ``evidence_refs`` entry is deleted or replaced - F2 is additive.
* No historical claim-bearing record is overwritten.
* No obsolete universal-174k benchmark is rerun or re-indexed.

Usage::

    python -m evaluation.repair_40017649220_r1_update_state [--dry-run]
"""
from __future__ import annotations

import argparse
import copy
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

STATE_PATH = _REPO / "state/evaluation.json"
RUN_ID = "40017649220"
GITHUB_RUN = "40023576675"
REPAIR_ROUND = 1

# --- F2: the seven cycle artifacts the rejected head indexed but left out ---
MISSING_CYCLE_REFS = [
    "results/evaluation/minimal_ret_ca_benchmark/v65_eval_40017649220_leg1_served_baseline.json",
    "results/evaluation/minimal_ret_ca_benchmark/v65_eval_40017649220_leg2_hostile_geometry.json",
    "results/evaluation/minimal_ret_ca_benchmark/verify_v65.json",
    "results/evaluation/minimal_ret_ca_benchmark/verify_v65_leg1_served_baseline.json",
    "results/evaluation/minimal_ret_ca_benchmark/verify_v65_leg2_hostile_geometry.json",
    "reports/evaluation/RETRIEVAL_CA_BENCHMARK_verify_v65.md",
    "reports/evaluation/EVALUATION_V65_CYCLE_SUMMARY.md",
]

# --- F1/F3: everything this repair round itself produced ---
REPAIR_REFS = [
    "evaluation/MINIMAL_RET_CA_40017649220_CYCLE_HYPOTHESIS_V1.json",
    "evaluation/REPAIR_40017649220_HYPOTHESIS_V1.json",
    "evaluation/REPAIR_40017649220_FREEZE_RECORD_V1.json",
    "evaluation/repair_40017649220_r1.py",
    "evaluation/repair_40017649220_r1_update_state.py",
    "tests/evaluation/test_repair_40017649220_r1.py",
    "results/evaluation/orchestration/40017649220_R1_minimal_ret_ca_pytest_shim.json",
    "results/evaluation/orchestration/40017649220_R1_multiling_prov_pytest_shim.json",
    "results/evaluation/orchestration/40017649220_R1_e2e_fixture_injected.json",
    "results/evaluation/multilingual_provenance_reuse/40017649220.json",
    "reports/evaluation/MULTILINGUAL_PROVENANCE_REUSE_40017649220.md",
    f"results/evaluation/repair_40017649220_r1/{GITHUB_RUN}.json",
]

# verify_v65* outputs are reproducibility runs: their internal run_id is the
# literal string "verify_v65", not the GitHub run id. Indexed for
# reproducibility, explicitly NON-CLAIM-BEARING.
NON_CLAIM_BEARING = {
    "results/evaluation/minimal_ret_ca_benchmark/verify_v65.json": (
        "reproducibility re-execution of v65_eval_40017649220; internal run_id "
        "is the literal string 'verify_v65', not GitHub run 40017649220; "
        "not a distinct claim"),
    "results/evaluation/minimal_ret_ca_benchmark/verify_v65_leg1_served_baseline.json": (
        "reproducibility leg record; internal run_id 'verify_v65'; not a "
        "distinct claim"),
    "results/evaluation/minimal_ret_ca_benchmark/verify_v65_leg2_hostile_geometry.json": (
        "reproducibility leg record; internal run_id 'verify_v65'; not a "
        "distinct claim"),
    "reports/evaluation/RETRIEVAL_CA_BENCHMARK_verify_v65.md": (
        "human report OF the verify_v65 re-execution; describes the "
        "reproducibility run, not an additional claim"),
}

# Two inherited index defects that pre-date this run. They are DISCLOSED, never
# silently deleted (deleting them would launder a historical measurement).
INHERITED_DEFECTS = {
    "statement": (
        "Two evidence_refs defects are inherited-not-charged: neither was "
        "added, edited or removed by run 40017649220 nor by repair round 1. "
        "One ref (39875239812_diagnosis.json) resolves to a committed file but "
        "is listed TWICE (DUPLICATE). One ref "
        "(40011795717/producer_work_state_and_next_move.txt) does not resolve "
        "to a committed file at this head (UNRESOLVED_AT_HEAD). Both stay "
        "listed because removing them would erase a historical measurement; "
        "they are flagged here so the index's resolution claim is never "
        "overstated. The duplicate is NOT deleted: de-duplicating would alter "
        "the historical ref list without a measurement change."),
    "defects": [
        {
            "ref": "results/evaluation/orchestration/39875239812_diagnosis.json",
            "kinds": ["DUPLICATE_ONLY"],
            "detail": (
                "Appears twice in evidence_refs and does not resolve to a "
                "committed file at this head. Introduced before run "
                "40017649220; unchanged by this repair."),
            "introduced_by_run": "39875239812 (pre-dates 40017649220)",
            "charged_to_40017649220": False,
            "charged_to_repair_round_1": False,
        },
        {
            "ref": ("results/evaluation/orchestration/40011795717/"
                    "producer_work_state_and_next_move.txt"),
            "kinds": ["UNRESOLVED_AT_HEAD"],
            "detail": (
                "Does not resolve to a committed file at this head. "
                "Introduced before run 40017649220; unchanged by this repair."),
            "introduced_by_run": "40011795717 (pre-dates 40017649220)",
            "charged_to_40017649220": False,
            "charged_to_repair_round_1": False,
        },
    ],
    "resolving_refs_counted": True,
    "known_unresolvable_count": 1,
    "known_unresolvable": [
        "results/evaluation/orchestration/40011795717/producer_work_state_and_next_move.txt",
    ],
    "known_duplicate_count": 1,
    "known_duplicate": [
        "results/evaluation/orchestration/39875239812_diagnosis.json",
    ],
}

HYP_REL = "evaluation/MINIMAL_RET_CA_40017649220_CYCLE_HYPOTHESIS_V1.json"
REPAIR_REC_REL = f"results/evaluation/repair_40017649220_r1/{GITHUB_RUN}.json"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


def _resolve(ref: str) -> bool:
    return (_REPO / ref).exists()


def _definitive_e2e() -> dict:
    """Read the DEFINITIVE post-freeze out-of-shim e2e record.

    The rejected team's pre-freeze attempt-1 artifacts are preserved under
    their original paths and must never be cited as the measurement of record;
    only the ``_R1_`` records written after freeze commit ad1f0ed1 count.
    Hardcoding the elapsed time here once let the attempt-1 value (10.868s)
    leak into state, so it is read from the record and asserted to differ from
    the discarded attempt-1 run where it actually does.
    """
    rec = _read_json(_REPO / f"results/evaluation/orchestration/{RUN_ID}_R1_e2e_fixture_injected.json")
    try:
        attempt1 = _read_json(_REPO / f"results/evaluation/orchestration/{RUN_ID}_e2e_fixture_injected.json")
    except (OSError, ValueError):
        attempt1 = {}
    assert rec.get("status") == "PASS", rec.get("status")
    assert rec.get("no_committed_record_rewritten") is True, rec
    if "elapsed_s" in attempt1:
        assert rec.get("elapsed_s") != attempt1.get("elapsed_s"), (
            "definitive e2e record is byte-identical to the discarded attempt-1 "
            "run; it was not re-executed post-freeze")
    return rec


def update(dry_run: bool = False) -> dict:
    st = _read_json(STATE_PATH)
    before = copy.deepcopy(st)
    report: dict = {"schema": "lex-evaluation-repair-state-update/1",
                    "run_id": GITHUB_RUN, "repairs_run_id": RUN_ID,
                    "repair_round": REPAIR_ROUND,
                    "generated_at_utc": _now(), "dry_run": dry_run,
                    "applied": {}, "guards": {}}

    # ---------------- guards that must hold BEFORE any edit ----------------
    refs_before = list(st.get("evidence_refs", []))
    ceiling_before = st["minimal_ret_ca_benchmark"]["claim_ceiling"]
    posture_before = {k: st.get(k) for k in
                      ("human_gate_ready", "machine_gate_ready",
                       "packet_admitted", "ready_for_owner_session")}
    assert all(v is False for v in posture_before.values()), posture_before
    report["guards"]["posture_false_before"] = posture_before

    # ---------------- F1: test_suite publication ----------------
    e2e = _definitive_e2e()
    e2e_rec_rel = f"results/evaluation/orchestration/{RUN_ID}_R1_e2e_fixture_injected.json"
    st.setdefault("test_suite", {})
    st["test_suite"]["minimal_ret_ca_benchmark"] = {
        "run_id": RUN_ID,
        "file": "tests/evaluation/test_minimal_ret_ca_benchmark.py",
        "measurement_env": (
            "python 3.12.3, pytest ABSENT (importlib find_spec('pytest') "
            "returned None), runner=evaluation/no_pytest_runner.py sha256 "
            "c12097da9d910574380b32c5dafa371a3b24ec14ef2551d92bb9453b8ed57584 "
            "(pytest-free shim; UNSUPPORTED is counted NOT-RUN and NEVER "
            "passed); accepted product mount present"),
        "passed": 4,
        "failed": 0,
        "skipped": 0,
        "unsupported": 1,
        "verdict": "SHIM_PASS",
        "record": f"results/evaluation/orchestration/{RUN_ID}_R1_minimal_ret_ca_pytest_shim.json",
        "unsupported_case_restated_as": (
            "test_end_to_end_on_accepted_mount_if_present = NOT-RUN under the "
            "shim (reported UNSUPPORTED: needs the tmp_path fixture the shim "
            "cannot inject). It was separately MEASURED out-of-shim by "
            "injecting tmp_path into a scratch tmpdir only, at PASS "
            f"in {e2e['elapsed_s']}s with all outputs confined to that tmpdir: "
            f"{e2e_rec_rel}. "
            "The out-of-shim measurement is ADDITIONAL and never re-counts "
            "into the shim verdict above."),
        "repair_round": REPAIR_ROUND,
    }
    st["test_suite"]["multilingual_provenance_reuse"] = {
        "run_id": RUN_ID,
        "files": [
            "tests/evaluation/test_stand_ready_multilingual_probe.py",
            "tests/evaluation/test_f3b_restore_disposition.py",
            "tests/evaluation/test_v59_stand_ready_verification.py",
            "tests/evaluation/test_packet_of_record_stand_ready.py",
        ],
        "measurement_env": (
            "python 3.12.3, pytest ABSENT, runner=evaluation/"
            "no_pytest_runner.py sha256 c12097da9d910574380b32c5dafa371a3b"
            "24ec14ef2551d92bb9453b8ed57584"),
        "passed": 73,
        "failed": 0,
        "skipped": 0,
        "unsupported": 0,
        "verdict": "SHIM_PASS",
        "record": f"results/evaluation/orchestration/{RUN_ID}_R1_multiling_prov_pytest_shim.json",
        "reuse_instrument_record": (
            f"results/evaluation/multilingual_provenance_reuse/{RUN_ID}.json"),
        "reuse_instrument_report": (
            f"reports/evaluation/MULTILINGUAL_PROVENANCE_REUSE_{RUN_ID}.md"),
        "reuse_instrument_verdict": "PARTIAL_MISS",
        "reuse_instrument_note": (
            "Accepted instrument evaluation/run_v3_multilingual_provenance_"
            "reuse.py re-executed with a scratch cwd and byte-compared to the "
            "historical record: identical. PARTIAL_MISS (0/3 qids row_ok) is "
            "carried as the accepted D-B characterisation, NOT repaired. "
            "Historical record never written."),
        "repair_round": REPAIR_ROUND,
    }
    report["applied"]["F1_test_suite_entries"] = [
        "test_suite.minimal_ret_ca_benchmark",
        "test_suite.multilingual_provenance_reuse"]

    # ---------------- F2: evidence index ----------------
    # verify_v65* roles first, so they exist before the refs that use them
    st["evidence_ref_roles"] = dict(st.get("evidence_ref_roles", {}))
    for rel, why in NON_CLAIM_BEARING.items():
        st["evidence_ref_roles"][rel] = "NON_CLAIM_BEARING_VERIFY_OUTPUT"
        st.setdefault("evidence_ref_role_notes", {})[rel] = why
    st["evidence_ref_roles"][HYP_REL] = "CYCLE_HYPOTHESIS_PROVENANCE"
    st["evidence_ref_roles"][REPAIR_REC_REL] = "REPAIR_ROUND_RECORD"
    for rel in REPAIR_REFS:
        if rel not in st["evidence_ref_roles"]:
            st["evidence_ref_roles"][rel] = "REPAIR_ROUND_ARTIFACT"

    refs = list(st.get("evidence_refs", []))
    added: list[str] = []
    for rel in MISSING_CYCLE_REFS + REPAIR_REFS:
        if rel not in refs:
            refs.append(rel)
            added.append(rel)
    # additive only: assert nothing was removed or altered
    assert refs[:len(refs_before)] == refs_before, "evidence_refs was mutated in place"
    assert set(refs_before) <= set(refs), "an evidence_ref was dropped"
    st["evidence_refs"] = refs
    st["evidence_refs_n"] = len(refs)          # RE-DERIVED, not hand-set

    st["evidence_index_defects_inherited_not_charged"] = INHERITED_DEFECTS
    # Only the one missing path is unresolvable. The 39875239812 ref resolves
    # but is listed TWICE -- a DUPLICATE, not a missing file.
    unresolvable = [r for r in refs if not _resolve(r)]
    assert unresolvable == INHERITED_DEFECTS["known_unresolvable"], (
        f"unexpected unresolvable refs: {unresolvable}")
    from collections import Counter as _Counter
    dupes = sorted(k for k, v in _Counter(refs).items() if v > 1)
    assert dupes == INHERITED_DEFECTS["known_duplicate"], (
        f"unexpected duplicate refs: {dupes}")
    st["evidence_index_resolving_refs_n"] = len(refs) - len(unresolvable)
    st["evidence_index_unresolvable_n"] = len(unresolvable)
    report["applied"]["F2_evidence_refs_added"] = added
    report["applied"]["F2_evidence_refs_n"] = st["evidence_refs_n"]
    report["applied"]["F2_unresolvable_disclosed"] = unresolvable

    # ---------------- F3: point the benchmark block at the hypothesis ------
    st["minimal_ret_ca_benchmark"]["cycle_hypothesis_record"] = HYP_REL
    st["minimal_ret_ca_benchmark"]["cycle_ordering"] = "NOT_FREEZE_FIRST"
    st["minimal_ret_ca_benchmark"]["cycle_ordering_note"] = (
        "Run 40017649220 executed 2026-10-23T20:16:19Z and committed "
        "2026-10-23T20:37:19Z; it is NOT a freeze-first cycle and must not be "
        "cited as one. The hypothesis record discloses the true ordering and "
        "was written in repair round 1; it does not retroactively freeze "
        "anything.")
    st["minimal_ret_ca_benchmark"]["no_post_hoc_tuning"] = (
        "Instrument sha256 70f8158c9049df2d03ebcc460b782178967ab9da7a11e48dd"
        "1b5b132d9f17167 is identical to accepted base b8265afb; output is "
        "quantity-for-quantity identical to base-committed test_run_1/final_"
        "check modulo run_id/generated_at/elapsed/served_packet_dir/ephemeral "
        "tmpdir plus the derived direction_version 63->65 and its "
        "absolute_status_note string; no frozen file was edited by the cycle.")
    report["applied"]["F3_pointers"] = [
        "minimal_ret_ca_benchmark.cycle_hypothesis_record",
        "minimal_ret_ca_benchmark.cycle_ordering",
        "minimal_ret_ca_benchmark.no_post_hoc_tuning"]

    # ---------------- F3/state: repair round block ----------------
    st[f"repair_round1_{RUN_ID}"] = {
        "schema": "lex-evaluation-repair-round/1",
        "repairs_run_id": RUN_ID,
        "repair_round": REPAIR_ROUND,
        "github_run": GITHUB_RUN,
        "direction_version": 65,
        "audit_gate": "results/audit/evaluation/CYCLE_40017649220_GATE.json",
        "audit_verdict_repaired": "REVISE",
        "required_fixes": ["F1", "F2", "F3"],
        "hypothesis": "evaluation/REPAIR_40017649220_HYPOTHESIS_V1.json",
        "freeze_record": "evaluation/REPAIR_40017649220_FREEZE_RECORD_V1.json",
        "freeze_committed_before_execution": True,
        "freeze_commit": "ad1f0ed1",
        "record": REPAIR_REC_REL,
        "verdict": "REPAIR_R1_DISCHARGED",
        "claim_ceiling": (
            "This repair establishes only that audit fixes F1/F2/F3 for run "
            "40017649220 are discharged with committed, machine-verifiable "
            "records and that no frozen input, instrument, test, bar, rubric, "
            "threshold or success rule changed. It re-measures NOTHING about "
            "the product."),
        "frozen_inputs_unchanged": True,
        "instrument_unchanged": True,
        "test_unchanged": True,
        "historical_records_overwritten": False,
        "no_174k_benchmark_rerun": True,
        "scratch_only_execution": True,
    }

    # ---------------- posture: publish owner_decision_required -------------
    st["owner_decision_required"] = False
    st["owner_decision_required_note"] = (
        "Published top-level by repair round 1 so the posture is machine-"
        "checkable. It previously existed only as prose inside "
        "next_recommendation. Value unchanged: false. Both DO-NOT-SERVE orders "
        "stand; admission stays fail-closed.")
    report["applied"]["owner_decision_required_published"] = False

    st["state_updated_at"] = _now()
    st["repair_round"] = REPAIR_ROUND
    st["repairs_run_id"] = RUN_ID

    # ---------------- post-edit guards ----------------
    assert st["evidence_refs_n"] == len(st["evidence_refs"])
    assert st["minimal_ret_ca_benchmark"]["claim_ceiling"] == ceiling_before
    assert {k: st[k] for k in posture_before} == posture_before
    assert st["owner_decision_required"] is False
    assert set(refs_before) <= set(st["evidence_refs"])
    assert all(_resolve(r) for r in st["evidence_refs"]
               if r not in INHERITED_DEFECTS["known_unresolvable"])
    report["guards"]["claim_ceiling_unchanged"] = True
    report["guards"]["posture_false_after"] = {k: st[k] for k in posture_before}
    report["guards"]["evidence_refs_only_appended"] = True
    report["guards"]["evidence_refs_n_equals_len"] = True
    report["guards"]["all_new_refs_resolve"] = True
    report["guards"]["n_known_unresolvable_disclosed"] = len(unresolvable)
    report["n_evidence_refs_before"] = len(refs_before)
    report["n_evidence_refs_after"] = len(st["evidence_refs"])
    report["n_added"] = len(added)
    report["changed"] = before != st
    report["verdict"] = "STATE_UPDATED" if report["changed"] else "STATE_UNCHANGED"

    if not dry_run:
        STATE_PATH.write_text(
            json.dumps(st, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return report


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)
    rep = update(dry_run=args.dry_run)
    out = Path(args.out) if args.out else (
        _REPO / f"results/evaluation/repair_40017649220_r1/{GITHUB_RUN}_state.json")
    if args.dry_run:
        out = None
    if out:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(rep, indent=1, ensure_ascii=False) + "\n",
                       encoding="utf-8")
    print(json.dumps(rep, indent=1, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""What repair round 1 of cycle 39764730877 claims about itself, checked against
the artifacts.

Why this exists
---------------
The independent audit of rejected product cycle 39764730877
(``results/audit/product/CYCLE_39764730877_GATE.json`` on the audit branch:
gate=REVISE, safe_to_integrate=false) charged four concrete defects:

* **F1** - the claim-bearing artifact
  ``results/product/regression/CYCLE_39758711075_test_delta_attribution.json``,
  named by the pinned test in ``product/tests/test_delta_attribution.py`` AND by
  ``state/product.json``, did not exist in the producer workspace and was absent
  from all git history: the pin moved in cycle 39758711075 and the bytes were
  left behind, so 21 committed guards were red on an artifact no run had ever
  written;
* **F2** - the inherited report's sweep claim ("169 failed, zero head-only
  failures, 1394 collected") was not reproducible from the committed bytes (the
  auditor measured 188 failed / 1206 passed / 19 skipped, 1413 collected, 23
  head-only failures against the accepted base ``4896982``), and the lane
  published no artifact either number could be checked against;
* **F2b** - two state guards hard-pinned ``accepted_run_id == "39660515863"``
  while the truly accepted run is ``39695438314`` (accept commit ``4896982``);
* **F3** - the run had no report of record and no state record, so its claim
  chain was empty;
* **F4** - the committed ``--no-enrich`` summary carried the FULL-loop claim
  ceiling ("sourced answer -> counter-authority pass -> clickable map") although
  it had skipped both of those halves.

This module is the executable counterpart of this round's claims: every fix
above is re-derived from the committed bytes, not asserted in prose.

Deliberately NOT claimed: nothing about any frozen bar, serve verdict,
live-answer reliability, jurist usefulness or gate readiness; nothing about any
environment other than the one that ran this module.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from product import offline_slice as ofs  # noqa: E402
from product import test_delta_attribution as tda  # noqa: E402

RUN_ID = 39764730877
ACCEPTED_BASE = "4896982"
ACCEPTED_RUN = "39695438314"

#: The same path pattern the lane's existing state guard uses, so this round's
#: record is checked by the same rule and not a wider one.
_PATH = re.compile(r"(?:product|results|reports|state|data)/[\w./-]+\.(?:py|json|md)")

STATE_PATH = ROOT / "state" / "product.json"
DELIVERY_KEY = f"cycle_{RUN_ID}_vertical_slice_delivery"
REPORT = ROOT / "reports" / "product" / f"CYCLE_{RUN_ID}.md"
SWEEP = (ROOT / "results" / "product" / "regression"
         / f"CYCLE_{RUN_ID}_sweep_diff.json")
ATTRIBUTION = (ROOT / "results" / "product" / "regression"
               / "CYCLE_39758711075_test_delta_attribution.json")
OWN_ATTRIBUTION = (ROOT / "results" / "product" / "regression"
                   / f"CYCLE_{RUN_ID}_test_delta_attribution.json")


def _state() -> dict:
    return json.loads(STATE_PATH.read_text(encoding="utf-8"))


def _sweep() -> dict:
    return json.loads(SWEEP.read_text(encoding="utf-8"))


# --------------------------------------------------------------------------
# F1 - the named attribution artifact exists, is committed, and measures THIS tree
# --------------------------------------------------------------------------

def test_the_named_attribution_artifact_exists_on_disk_and_in_git() -> None:
    assert ATTRIBUTION.exists(), (
        f"the artifact the pinned test and the lane state both name is missing: "
        f"{ATTRIBUTION}")
    tracked = subprocess.run(  # noqa: S603
        ["git", "ls-files", "--error-unmatch", str(ATTRIBUTION.relative_to(ROOT))],
        cwd=str(ROOT), capture_output=True, text=True, check=False)
    assert tracked.returncode == 0, (
        f"{ATTRIBUTION.name} exists but is not tracked by git; a claim-bearing "
        "artifact that only exists in a working tree is not evidence")
    assert OWN_ATTRIBUTION.exists(), (
        f"this round's own attribution artifact is missing: {OWN_ATTRIBUTION}")


def test_the_attribution_artifact_measures_this_tree() -> None:
    """The staleness detector: the committed measurement is this tree's."""
    art = json.loads(ATTRIBUTION.read_text(encoding="utf-8"))
    assert art["run_id"] == 39758711075, (
        "the artifact named for run 39758711075 must carry that run id")
    assert art["reconciles"] is True
    assert art["cross_check"]["status"] == "COMPARED"
    assert art["cross_check"]["base_agrees"] is True
    measured = tda.collect_count(ROOT)
    assert art["working_tree"]["collected_total"] == measured, (
        f"the committed attribution says {art['working_tree']['collected_total']} "
        f"but this tree collects {measured}; regenerate it")


def test_the_pinned_test_and_the_state_name_the_same_artifact() -> None:
    source = (ROOT / "product" / "tests" / "test_delta_attribution.py").read_text(
        encoding="utf-8")
    assert "CYCLE_39758711075_test_delta_attribution.json" in source, (
        "the pinned attribution test no longer names the artifact the state names")
    state = _state()
    assert "results/product/regression/CYCLE_39758711075_test_delta_attribution.json" in json.dumps(
        state, ensure_ascii=False), (
        "the lane state no longer names the attribution artifact the pin reads")


# --------------------------------------------------------------------------
# F2 - the sweep diff is measured, published, and the head-only set is empty
# --------------------------------------------------------------------------

def test_the_sweep_diff_artifact_is_published_and_self_consistent() -> None:
    art = _sweep()
    assert art["schema"] == "product-sweep-diff/1"
    base, head = art["base"], art["head"]
    assert base["commit"].startswith(ACCEPTED_BASE), (
        f"the sweep compared against {base['short']}, not the accepted base "
        f"{ACCEPTED_BASE}")
    for tree in (base, head):
        assert tree["failed"] == len(tree["failed_ids"]), (
            f"the {tree['short']} failure count does not match its own id list")
        assert tree["failed"] + tree["passed"] + tree["skipped"] == tree["collected"], (
            f"the {tree['short']} counts do not add up to its collected total")


def test_the_head_only_failure_set_is_empty() -> None:
    art = _sweep()
    assert art["head_only_failures"] == [], (
        "this branch introduced failures the accepted base does not have: "
        f"{art['head_only_failures']}")
    assert art["head_only_empty"] is True


def test_the_published_sweep_numbers_are_the_ones_the_state_and_report_carry() -> None:
    """The prose is not a second source of truth: it must BE the measurement."""
    art = _sweep()
    head = art["head"]
    state = _state()
    recorded = (state.get(DELIVERY_KEY) or {}).get("sweep") or {}
    assert recorded, "the lane state records no sweep measurement for this round"
    assert recorded["failed"] == head["failed"]
    assert recorded["passed"] == head["passed"]
    assert recorded["skipped"] == head["skipped"]
    assert recorded["collected"] == head["collected"]
    assert recorded["base_failed"] == art["base"]["failed"]
    assert recorded["base_collected"] == art["base"]["collected"]
    assert recorded["n_head_only_failures"] == art["n_head_only"]
    report = REPORT.read_text(encoding="utf-8")
    assert f"{head['failed']} failed" in report, (
        "the report of record does not carry the measured head failure count")
    assert f"{head['collected']} collected" in report, (
        "the report of record does not carry the measured head collected count")


# --------------------------------------------------------------------------
# F2b - the two stale accepted-run guards name the TRULY accepted run
# --------------------------------------------------------------------------

def test_the_two_state_guards_no_longer_pin_the_historical_accepted_run() -> None:
    for module in ("test_state_cycle_39674781875.py", "test_state_cycle_39689729561.py"):
        source = (ROOT / "product" / "tests" / module).read_text(encoding="utf-8")
        assert 'accepted_run_id"] == "39660515863"' not in source, (
            f"{module} still hard-pins the historical accepted run 39660515863")
        assert ACCEPTED_RUN in source, (
            f"{module} does not name the truly accepted run {ACCEPTED_RUN}")
    state = _state()
    assert state["accepted_run_id"] == ACCEPTED_RUN, (
        "the accepted-run pointer must name the last ACCEPTED run")


# --------------------------------------------------------------------------
# F3 - the report of record and the state record exist and say what happened
# --------------------------------------------------------------------------

def test_the_report_of_record_exists_and_names_this_run_and_its_fixes() -> None:
    assert REPORT.exists(), f"the report of record is missing: {REPORT}"
    text = REPORT.read_text(encoding="utf-8")
    for needle in (str(RUN_ID), "F1", "F2", "F2b", "F3", "F4",
                   "39752638579", "39758711075", ACCEPTED_BASE,
                   "human_gate_ready", "BOUNDED-NEGATIVE"):
        assert needle in text, f"the report of record does not cite {needle!r}"


def test_the_state_records_this_run_and_keeps_the_fail_closed_posture() -> None:
    state = _state()
    assert str(state["current_run"]) == str(RUN_ID), (
        "the lane state must name the run that produced it")
    delivery = state[DELIVERY_KEY]
    assert delivery["run_id"] == RUN_ID
    assert delivery["repair_round"] == 1
    assert state["human_gate_ready"] is False
    assert state["machine_gate_ready"] is False
    assert state["packet_admitted"] is False
    assert state["ready_for_owner_session"] is False
    assert state["requirement_13_supersession_conditions_met"] is False
    assert state["continue_recommended"] is True


def test_the_state_names_only_files_that_exist() -> None:
    """The same rule the lane already enforces, applied to this round's record.

    Scoped exactly like the existing guard (``test_state_cycle_39674781875.py``):
    the evidence refs, the MVP test register and THIS round's delivery record.
    The whole state is deliberately NOT scanned: it legitimately cites audit
    artifacts that live on the audit branch, not in this tree.
    """
    state = _state()
    blobs: list[str] = []
    blobs.extend(state.get("evidence_refs") or [])
    blobs.extend((state.get("verification") or {}).get("mvp_test_files") or [])
    blobs.append(json.dumps(state.get(DELIVERY_KEY) or {}, ensure_ascii=False))
    missing = []
    for blob in blobs:
        for candidate in sorted(set(_PATH.findall(blob))):
            if not (ROOT / candidate).exists():
                missing.append(candidate)
    assert not missing, f"the state names artifacts that do not exist: {missing}"


# --------------------------------------------------------------------------
# F4 - the claim ceiling is mode-conditional
# --------------------------------------------------------------------------

def test_the_claim_ceiling_is_a_function_of_the_measured_mode() -> None:
    assert ofs.claim_ceiling(True) == ofs.CLAIM_CEILING_ENRICHED
    assert ofs.claim_ceiling(False) == ofs.CLAIM_CEILING_MAP_ONLY
    assert ofs.claim_ceiling(True) != ofs.claim_ceiling(False)
    assert "sourced answer -> counter-authority pass" in ofs.CLAIM_CEILING_ENRICHED
    assert "sourced answer -> counter-authority pass" not in ofs.CLAIM_CEILING_MAP_ONLY
    assert "OFFLINE WIRING EVIDENCE ONLY" in ofs.CLAIM_CEILING_MAP_ONLY
    assert "no frozen gate is evaluated" in ofs.CLAIM_CEILING_MAP_ONLY

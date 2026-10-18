"""The ledger must be able to FAIL.

A verifier that cannot fail is a rubber stamp, and the lane has already paid for
one: the "+7 net new passing tests" figure was published against no measurement.
So the first half of this module attacks ``cycle_verify`` itself; the second half
attacks the claims it makes about the shipped product.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from product import cycle_verify as cv

ROOT = Path(__file__).resolve().parents[2]


# --------------------------------------------------------------------------
# the ledger is a gate, not a report generator
# --------------------------------------------------------------------------

def test_a_check_that_raises_becomes_fail_never_pass(monkeypatch):
    def boom():
        raise RuntimeError("kaboom")

    monkeypatch.setitem(cv.CHECKS, "boom", boom)
    ledger = cv.run(["boom"])
    assert ledger["verdict"] == "FAIL"
    assert ledger["n_failed"] == 1
    assert "kaboom" in ledger["claims"][0]["observed"]


def test_one_failing_claim_fails_the_whole_ledger(monkeypatch):
    monkeypatch.setitem(cv.CHECKS, "mixed", lambda: [
        {"claim": "a", "status": "PASS", "observed": 1},
        {"claim": "b", "status": "FAIL", "observed": 2},
    ])
    assert cv.run(["mixed"])["verdict"] == "FAIL"


def test_unknown_check_is_refused_rather_than_silently_skipped():
    with pytest.raises(SystemExit):
        cv.run(["no-such-check"])


def test_exit_code_is_non_zero_on_failure(monkeypatch):
    monkeypatch.setitem(cv.CHECKS, "bad", lambda: [
        {"claim": "b", "status": "FAIL", "observed": "no"}])
    assert cv.main(["--only", "bad", "--json"]) == 1
    monkeypatch.setitem(cv.CHECKS, "good", lambda: [
        {"claim": "a", "status": "PASS", "observed": "yes"}])
    assert cv.main(["--only", "good", "--json"]) == 0


def test_required_posture_is_hard_coded_not_read_from_the_file(monkeypatch, tmp_path):
    """A verifier that takes its expectations from the artifact verifies nothing."""
    import product.cycle_verify as module

    fake = tmp_path / "product.json"
    fake.write_text(json.dumps({k: True for k in cv.REQUIRED_FAIL_CLOSED}), encoding="utf-8")
    monkeypatch.setattr(module, "STATE_PATH", fake)
    rows = module.check_fail_closed_posture()
    posture = [r for r in rows if "fail-closed" in r["claim"]][0]
    assert posture["status"] == "FAIL"
    assert set(posture["observed"]) == set(cv.REQUIRED_FAIL_CLOSED)


def test_a_missing_state_file_is_a_failure_not_an_empty_pass(monkeypatch, tmp_path):
    import product.cycle_verify as module

    monkeypatch.setattr(module, "STATE_PATH", tmp_path / "absent.json")
    rows = module.check_fail_closed_posture()
    assert rows[0]["status"] == "FAIL"


def test_ledger_records_the_numeric_environment(monkeypatch):
    monkeypatch.setitem(cv.CHECKS, "noop", lambda: [{"claim": "x", "status": "PASS", "observed": 1}])
    env = cv.run(["noop"])["environment"]
    assert "python" in env
    assert set(env) >= {"python", "numpy", "scipy", "scikit_learn"}


def test_ledger_claims_nothing_about_frontier_or_frozen_bars():
    blob = (ROOT / "product" / "cycle_verify.py").read_text(encoding="utf-8")
    for banned in ("RULES_LABEL", "RULES_GEOMETRY", "label_gate", "geometry_gate",
                   "gate == \"PASS\"", "safe_to_integrate"):
        assert banned not in blob


# --------------------------------------------------------------------------
# the claims, attacked
# --------------------------------------------------------------------------

def test_counter_ledger_publishes_both_definitions_and_names_their_source():
    rows = cv.check_counter_authority_counts()
    claim = rows[0]
    assert claim["status"] == "PASS"
    obs = claim["observed"]
    assert obs["counter_authorities"] <= obs["counter_status_bearing_rows"]
    assert "counter_status.py" in claim["definition_source"]


def test_counter_ledger_would_reject_an_inflated_count(monkeypatch):
    """Non-vacuity: swap in the old broad predicate and the second claim must fail."""
    import product.query.counter_status as cs

    real = cs.counter_authority_count
    monkeypatch.setattr(cs, "counter_authority_count", lambda rows: len(rows))
    rows = cv.check_counter_authority_counts()
    monkeypatch.setattr(cs, "counter_authority_count", real)
    assert rows[1]["status"] == "FAIL"


def test_relation_ledger_rejects_a_state_that_contradicts_the_edge_count(monkeypatch):
    import product.offline_slice as offline

    original = offline.build_bundle

    def tampered(slug, top_n, **kw):
        bundle = original(slug, top_n, **kw)
        prov = bundle["provenance"]["relations_provenance"]
        prov["channel_state"] = "POPULATED"
        prov["relations_added_by_hydration"] = 3
        return bundle

    monkeypatch.setattr(offline, "build_bundle", tampered)
    rows = cv.check_relation_channel()
    agreement = [r for r in rows if "agrees with the edge count" in r["claim"]][0]
    assert agreement["status"] == "FAIL"


def test_posture_ledger_detects_a_raised_gate(monkeypatch, tmp_path):
    import product.cycle_verify as module

    state = json.loads((ROOT / "state" / "product.json").read_text(encoding="utf-8"))
    state["human_gate_ready"] = True
    fake = tmp_path / "product.json"
    fake.write_text(json.dumps(state), encoding="utf-8")
    monkeypatch.setattr(module, "STATE_PATH", fake)
    posture = [r for r in module.check_fail_closed_posture() if "fail-closed" in r["claim"]][0]
    assert posture["status"] == "FAIL"
    assert "human_gate_ready" in posture["observed"]


def test_owner_question_ledger_detects_a_refired_question(monkeypatch, tmp_path):
    import product.cycle_verify as module

    intake = json.loads(
        (ROOT / "results" / "product" / "frontier_verdicts"
         / "frontier-rebuilt-packet-serve-audit_intake.json").read_text(encoding="utf-8"))
    intake["owner_question"] = {"status": "READY_TO_FIRE", "question": "map or list?"}
    fake = tmp_path / "intake.json"
    fake.write_text(json.dumps(intake), encoding="utf-8")
    monkeypatch.setattr(module, "INTAKE_PATH", fake)
    rows = module.check_no_owner_question()
    assert rows[0]["status"] == "FAIL"


def test_tracked_results_check_detects_a_write(monkeypatch, tmp_path):
    import product.offline_slice as offline
    import product.cycle_verify as module

    victim = tmp_path / "feedback.jsonl"
    victim.write_text("{}\n", encoding="utf-8")
    monkeypatch.setattr(module, "TRACKED_FEEDBACK", victim)
    monkeypatch.setattr(offline, "build_bundle", lambda *a, **k: victim.write_text('{"residue": 1}\n'))
    rows = module.check_tracked_results_not_mutated()
    assert rows[0]["status"] == "FAIL"


def test_scope_check_flags_an_out_of_scope_path(monkeypatch):
    class _R:
        returncode = 0
        stdout = " M .github/workflows/core-lane.yml\n M product/x.py\n"

    monkeypatch.setattr(subprocess, "run", lambda *a, **k: _R())
    rows = cv.check_git_scope()
    assert rows[0]["status"] == "FAIL"
    assert rows[0]["observed"] == [".github/workflows/core-lane.yml"]


# --------------------------------------------------------------------------
# the committed artifact
# --------------------------------------------------------------------------

def _artifact() -> Path:
    runs = sorted((ROOT / "results" / "product" / "cycle_verify").glob("CYCLE_*_cycle_verify.json"))
    return runs[-1] if runs else Path("/nonexistent")


@pytest.mark.skipif(not _artifact().is_file(), reason="cycle_verify artifact not committed")
def test_committed_artifact_is_a_pass_and_says_what_it_is_not():
    data = json.loads(_artifact().read_text(encoding="utf-8"))
    assert data["schema"] == cv.SCHEMA
    assert data["verdict"] == "PASS", [c for c in data["claims"] if c["status"] != "PASS"]
    assert "not an audit verdict" in data["claim_ceiling"]
    assert "gate" not in data
    assert "safe_to_integrate" not in data


def test_cli_is_runnable_as_one_command():
    """The point of the module is that a single command reproduces the ledger."""
    out = subprocess.run(  # noqa: S603
        [sys.executable, "product/cycle_verify.py", "--only", "posture"],
        cwd=ROOT, capture_output=True, text=True, timeout=300, check=False,
    )
    assert out.returncode == 0, out.stdout + out.stderr
    assert "[PASS]" in out.stdout


# --------------------------------------------------------------------------
# the two checks this cycle added must be able to FAIL
# --------------------------------------------------------------------------

def _diagnosis_artifact() -> dict:
    return json.loads(
        cv.DIAGNOSIS_39086926860_ARTIFACT.read_text(encoding="utf-8"))


def test_diagnosis_check_fails_when_the_artifact_is_missing(monkeypatch, tmp_path):
    monkeypatch.setattr(cv, "DIAGNOSIS_39086926860_ARTIFACT", tmp_path / "nope.json")
    rows = cv.check_orchestration_diagnosis_39086926860()
    assert len(rows) == 1 and rows[0]["status"] == "FAIL"


def test_diagnosis_check_rejects_an_exit_code_that_was_never_collected(
        monkeypatch, tmp_path):
    """'No annotation collected' must not read as 'the cause is unknown but fine'."""
    data = _diagnosis_artifact()
    data["diagnosis"]["annotations_collected"] = False
    data["diagnosis"]["exit_code"] = None
    victim = tmp_path / "diag.json"
    victim.write_text(json.dumps(data), encoding="utf-8")
    monkeypatch.setattr(cv, "DIAGNOSIS_39086926860_ARTIFACT", victim)

    rows = cv.check_orchestration_diagnosis_39086926860()
    failed = {r["claim"]: r for r in rows if r["status"] == "FAIL"}
    assert any("public check-run annotation" in c for c in failed)


def test_diagnosis_check_rejects_a_branch_ruled_out_without_evidence(
        monkeypatch, tmp_path):
    data = _diagnosis_artifact()
    data["diagnosis"]["candidates"]["named_branches"][0]["ruled_out"] = True
    data["diagnosis"]["candidates"]["named_branches"][0]["ruled_out_evidence"] = []
    victim = tmp_path / "diag.json"
    victim.write_text(json.dumps(data), encoding="utf-8")
    monkeypatch.setattr(cv, "DIAGNOSIS_39086926860_ARTIFACT", victim)

    rows = cv.check_orchestration_diagnosis_39086926860()
    failed = [r for r in rows if r["status"] == "FAIL"]
    assert any("ruled out without published evidence" in r["claim"] for r in failed)


def test_diagnosis_check_rejects_a_pretty_conclusion_that_is_not_reproducible(
        monkeypatch, tmp_path):
    """Re-derivation, not restatement: flip the recorded exit code."""
    data = _diagnosis_artifact()
    data["diagnosis"]["exit_code"] = 78
    victim = tmp_path / "diag.json"
    victim.write_text(json.dumps(data), encoding="utf-8")
    monkeypatch.setattr(cv, "DIAGNOSIS_39086926860_ARTIFACT", victim)

    rows = cv.check_orchestration_diagnosis_39086926860()
    failed = [r for r in rows if r["status"] == "FAIL"]
    assert failed, "a non-re-deriving exit code must fail the ledger"
    assert all(r["status"] in ("PASS", "FAIL") for r in rows)


def test_regression_check_fails_when_no_artifact_exists(monkeypatch, tmp_path):
    monkeypatch.setattr(cv, "REGRESSION_DIR", tmp_path)
    rows = cv.check_regression_set_relation()
    assert len(rows) == 1 and rows[0]["status"] == "FAIL"


def test_regression_check_rejects_a_new_failure(monkeypatch, tmp_path):
    art = tmp_path / "CYCLE_99999999999_regression_scope.json"
    art.write_text(json.dumps({
        "schema": "product-regression-evidence/2", "run_id": 99999999999,
        "scope": {"measured_at_checkout_root": "/a", "baseline_checkout_root": "/b"},
        "arithmetic": {"arithmetic_reconciles": True},
        "set_relation": {"set_difference_repaired_only_NEW_FAILURES":
                         ["product/tests/x.py::test_x"], "n_baseline_only": 0},
    }), encoding="utf-8")
    monkeypatch.setattr(cv, "REGRESSION_DIR", tmp_path)
    rows = cv.check_regression_set_relation()
    assert rows[0]["status"] == "FAIL"
    assert rows[1]["status"] == "PASS"


def test_regression_check_rejects_arithmetic_that_does_not_close(monkeypatch, tmp_path):
    art = tmp_path / "CYCLE_99999999999_regression_scope.json"
    art.write_text(json.dumps({
        "schema": "product-regression-evidence/2", "run_id": 99999999999,
        "scope": {"measured_at_checkout_root": "/a", "baseline_checkout_root": "/b"},
        "arithmetic": {"arithmetic_reconciles": False, "notes": ["REFUSED"]},
        "set_relation": {"set_difference_repaired_only_NEW_FAILURES": [],
                         "n_baseline_only": 1},
    }), encoding="utf-8")
    monkeypatch.setattr(cv, "REGRESSION_DIR", tmp_path)
    rows = cv.check_regression_set_relation()
    assert rows[1]["status"] == "FAIL"
    assert "REFUSED" in json.dumps(rows[1]["observed"])

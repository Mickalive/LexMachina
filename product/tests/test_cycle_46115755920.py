"""Operational resume 46115755920 of the zero-delta snapshot 46115584428.

Two distinct facts are pinned here and must not be conflated:

* the snapshot's team refs repeat the predecessor producer commit
  (ZERO_DURABLE_DELTA); the workflow mechanism for that stop is UNOBSERVED
  because no GitHub job metadata is available to this producer;
* a locally REPRODUCIBLE validation failure was found in the inherited
  cycle test: it compared mutable HEAD with the fixed accepted commit and
  failed as soon as its own resuming commit moved HEAD. That test is repaired
  here by pinning the snapshot against its fixed predecessor and requiring
  HEAD to descend from it - no assertion is weakened.

Everything accepted earlier is preserved: the accepted pointer is unchanged,
the v68 ordered-work evidence is consumed rather than re-derived, no bundle
bytes are rewritten, no frozen bar is scored and the fail-closed posture holds.
"""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

RUN_ID = "46115755920"
SNAPSHOT_RUN = "46115584428"
PREDECESSOR_RUN = "46109821912"
HEAD_SHA = "6dcb3b87ce136cd2316a4312c41e1fc40c1dcc40"
HEAD_TREE = "62b19ac4a2970fd44683af6b2c571970019eec90"
ACCEPTED_RUN = "40284658455"
ACCEPTED_SHA = "7be4480ed3ca623b77ea082404ca3b5b7ac5ee83"
GATE_REL = f"results/audit/product/CYCLE_{ACCEPTED_RUN}_GATE.json"
GATE_SHA = "d7b902214fd0931a328b366f2e431a7ade89b034ac722d07cd380bb1ddcc8011"

STATE = ROOT / "state" / "product.json"
DIAG = (ROOT / "results" / "product" / "orchestration"
        / f"CYCLE_{SNAPSHOT_RUN}_snapshot_diagnosis.json")
REPORT = ROOT / "reports" / "product" / f"CYCLE_{RUN_ID}.md"
PREV_TEST = ROOT / "product" / "tests" / f"test_cycle_{PREDECESSOR_RUN}.py"
# The readiness dossier for THIS run is generated after this test file lands
# (the dossier runs this file as one of its nine checks). It is verified by the
# dossier's own command in the report, not from inside its own input.


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=str(ROOT), capture_output=True, text=True,
        check=True).stdout.strip()


def _run(*cmd: str) -> subprocess.CompletedProcess:
    return subprocess.run(list(cmd), cwd=str(ROOT), capture_output=True,
                          text=True, check=False)


def test_snapshot_refs_repeat_the_predecessor_producer_commit():
    assert _git("ls-remote", "--heads", "origin",
                f"refs/heads/cycle/core/product/{SNAPSHOT_RUN}/team"
                ).split()[0] == HEAD_SHA
    assert _git("ls-remote", "--heads", "origin",
                f"refs/heads/cycle/core/product/{SNAPSHOT_RUN}/team-attempt-1"
                ).split()[0] == HEAD_SHA
    assert _git("ls-remote", "--heads", "origin",
                f"refs/heads/cycle/core/product/{PREDECESSOR_RUN}/team"
                ).split()[0] == HEAD_SHA
    assert _git("rev-parse", "HEAD^{tree}") == HEAD_TREE
    assert _git("diff", "--name-status", HEAD_SHA,
                f"origin/cycle/core/product/{SNAPSHOT_RUN}/team") == ""
    probe = subprocess.run(
        ["git", "grep", "-n", SNAPSHOT_RUN, HEAD_SHA, "--", "."],
        cwd=str(ROOT), capture_output=True, text=True, check=False)
    assert probe.returncode == 1 and probe.stdout == ""


def test_no_audit_artifact_exists_for_the_snapshot_run():
    assert _git("ls-remote", "--heads", "origin",
                f"refs/heads/cycle/core/product/{SNAPSHOT_RUN}/audit") == ""
    assert not (ROOT / "results" / "audit" / "product"
                / f"CYCLE_{SNAPSHOT_RUN}_GATE.json").exists()
    assert not (ROOT / "reports" / "audit" / "product"
                / f"CYCLE_{SNAPSHOT_RUN}.md").exists()


def test_diagnosis_records_zero_delta_without_inventing_a_mechanism():
    doc = _load(DIAG)
    assert doc["schema"] == "product-resume-diagnosis/2"
    assert doc["run_id"] == SNAPSHOT_RUN
    assert doc["predecessor_run_id"] == PREDECESSOR_RUN
    assert doc["direction_version"] == 68
    orch = doc["orchestration"]
    assert orch["classification"] == "ZERO_DURABLE_DELTA_SNAPSHOT"
    assert orch["mechanism_unobserved"] is True
    assert "mechanism" not in orch
    assert orch["raw_snapshot"] is None
    assert orch["failed_job"] is None and orch["exit_code"] is None
    assert orch["audit"]["gate_file_written"] is False
    assert orch["audit"]["audit_ref_exists"] is False
    delta = doc["durable_delta"]
    assert delta["classification"] == "ZERO_DURABLE_DELTA"
    assert delta["changed_files"] == 0
    assert delta["snapshot_head"] == delta["predecessor_head"] == HEAD_SHA
    assert delta["snapshot_tree"] == HEAD_TREE
    adj = doc["adjudication"]
    assert adj["status"] == "UNADJUDICATED" and adj["accepted"] is False
    assert adj["gate_file_for_this_run"] is False
    unavailable = [o for o in doc["observations"]
                   if o["check"] == "github_metadata_unavailable"]
    assert unavailable and unavailable[0]["evidence_tier"] == "UNAVAILABLE"


def test_validation_failure_is_observed_repaired_and_not_weakened():
    vf = _load(DIAG)["orchestration"]["validation_failure"]
    assert vf["status"] == "OBSERVED_AND_REPRODUCED_LOCALLY"
    assert vf["kind"] == "CYCLE_TEST_HEAD_PIN_SELF_INVALIDATION"
    assert "1 failed, 9 passed" in vf["observed_result"]
    assert "head" in vf["observed_result"]
    assert vf["repaired_test_result"] == "10 passed"
    assert "NOT asserted" in vf["not_claimed"] or "remains UNOBSERVED" in vf["not_claimed"]
    source = PREV_TEST.read_text(encoding="utf-8")
    assert "assert head == ACCEPTED_SHA" not in source
    assert "merge-base" in source and "--is-ancestor" in source
    assert "snapshot_shas[\"team\"]" in source
    proc = _run(sys.executable, "-m", "pytest", str(PREV_TEST), "-q",
                "--disable-warnings")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "10 passed" in proc.stdout


def test_accepted_pointer_is_unchanged_and_both_halves_verify():
    st = _load(STATE)
    assert st["accepted_run_id"] == f"CYCLE_{ACCEPTED_RUN}"
    assert st["accepted_commit"] == ACCEPTED_SHA
    raw = (ROOT / GATE_REL).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == GATE_SHA
    gate = json.loads(raw)
    assert gate["gate"] == "PASS" and gate["safe_to_integrate"] is True
    assert gate["required_fixes"] == []
    assert _git("log", "--all", "--oneline",
                f"--grep=^accept product cycle {ACCEPTED_RUN}$")
    assert _git("ls-remote", "--heads", "origin", "refs/heads/lab/product"
                ).startswith(ACCEPTED_SHA)
    from product import state_contract as sc
    assert sc.accepted_pointer_evidence(st, ROOT)["problems"] == []


def test_inherited_deliverables_are_preserved_not_re_derived():
    st = _load(STATE)
    blob = json.dumps(st)
    for token in ("CYCLE_40269774540", "5adaa66d", "40284658455"):
        assert token in blob
    diag = _load(ROOT / "results" / "product" / "query_map_diagnosis"
                 / "CYCLE_40257275384.json")
    assert diag["verdict"] == "PASS" and not diag["n_failed_checks"]
    assert diag["current_reading"]["open_leg_from_items_1_to_3"] == "NONE"
    for finding in ("40070818687", "40068038783", "40105794124"):
        assert any(f["run_id"] == finding and f["re_derived"] is False
                   for f in diag["findings_consumed"])
    family = _load(ROOT / "results" / "product" / "counter_content_family"
                   / "CYCLE_40257275384.json")
    totals = family["fixed_path_family"]["totals"]
    assert totals["n_bundles"] == 49 and totals["n_verified"] == 55
    assert totals["n_verified_defective"] == 0
    assert family["false_reject_count"] == 0
    assert (ROOT / "results" / "product" / "audit_readiness"
            / "CYCLE_46109821912_audit_readiness.json").is_file()


def test_posture_stays_fail_closed_and_resume_is_recorded():
    st = _load(STATE)
    assert st["direction_version"] == 68
    assert st["current_cycle_run_id"] == int(RUN_ID)
    for key in ("human_gate_ready", "machine_gate_ready", "packet_admitted",
                "ready_for_owner_session"):
        assert st[key] is False
    assert st["continue_recommended"] is True
    block = st["cycle_46115584428_operational_resume"]
    assert block["snapshot_run_id"] == int(SNAPSHOT_RUN)
    assert block["classification"] == "ZERO_DURABLE_DELTA_SNAPSHOT"
    assert block["validation_failure_of_record"]["kind"] == (
        "CYCLE_TEST_HEAD_PIN_SELF_INVALIDATION")
    assert block["validation_failure_of_record"]["after"].startswith("10 passed")
    hist = {str(h["run_id"]): h for h in st["run_history"]}
    assert SNAPSHOT_RUN in hist and RUN_ID in hist


def test_audit_readiness_profile_is_run_scoped_and_fails_closed():
    from product import audit_readiness as ar
    prof = ar.select_profile(RUN_ID)
    assert prof["resumed_run_id"] == SNAPSHOT_RUN
    assert prof["predecessor_run_id"] == PREDECESSOR_RUN
    assert prof["classification"] == "ZERO_DURABLE_DELTA_SNAPSHOT"
    assert prof["mechanism_kind"] == "unobserved"
    assert prof["delta_kind"] == "zero"
    assert prof["cycle_test"] == f"product/tests/test_cycle_{RUN_ID}.py"
    assert ar.PROFILES[SNAPSHOT_RUN]["alias_of"] == RUN_ID
    try:
        ar.select_profile("99999999998")
    except SystemExit:
        pass
    else:  # pragma: no cover - defensive
        raise AssertionError("select_profile must fail closed on unknown runs")


def test_state_contract_and_lane_scope_hold_on_the_snapshot():
    proc = _run(sys.executable, "product/state_contract.py", "--check",
                "--direction-version", "68", "--json")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert json.loads(proc.stdout)["ok"] is True
    pending = _git("status", "--porcelain", "-uall").splitlines()
    audit_writes = [line[3:] for line in pending
                    if line[3:].startswith(("results/audit/product/",
                                            "reports/audit/product/"))]
    assert audit_writes == []
    assert not [line for line in pending if line[3:].startswith(".github/")]


def test_full_suite_comparison_introduces_no_new_failures():
    doc = _load(ROOT / "results" / "product" / "orchestration"
                / f"CYCLE_{RUN_ID}_full_suite_baseline_comparison.json")
    assert doc["schema"] == "product-full-suite-baseline-comparison/1"
    assert doc["run_id"] == RUN_ID and doc["resumed_run_id"] == SNAPSHOT_RUN
    assert doc["baseline_commit"] == ACCEPTED_SHA
    assert doc["comparison"]["current_only"] == []
    assert doc["comparison"]["intersection_count"] == 211
    assert doc["comparison"]["classification"] == "NO_NEW_FULL_SUITE_FAILURES"
    assert len(doc["comparison"]["baseline_only"]) == 2


def test_report_of_record_discloses_both_facts_and_the_ceiling():
    text = REPORT.read_text(encoding="utf-8")
    for token in (RUN_ID, SNAPSHOT_RUN, PREDECESSOR_RUN, HEAD_SHA[:8],
                  "ZERO_DURABLE_DELTA", "CYCLE_TEST_HEAD_PIN",
                  "DO-NOT-SERVE", "UNADJUDICATED"):
        assert token in text, token

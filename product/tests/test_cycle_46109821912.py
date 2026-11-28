"""Operational resume 46109821912 of the zero-delta snapshot 46106207560.

The persisted producer snapshot for run 46106207560 is byte-identical to the
previous accepted integrator commit: both team refs point at 7be4480e and no
audit ref or run-specific gate exists. Nothing from that run can be promoted.
This test pins the honest diagnosis and the concrete durable delta of the
resume:

* no invented job/step cause (GitHub metadata is unavailable here);
* all previously accepted work is preserved verbatim, including the quarantine
  of the producer-minted gate and the v68 ordered-work evidence;
* the stale accepted pointer is advanced to the accepted GitHub run
  40284658455 only after verifying the gate file and the accept commit side by
  side, with the former pointer kept as append-only provenance;
* posture stays fail-closed and the v68 findings are consumed, not re-derived.
"""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

RUN_ID = "46109821912"
SNAPSHOT_RUN = "46106207560"
ACCEPTED_RUN = "40284658455"
ACCEPTED_SHA = "7be4480ed3ca623b77ea082404ca3b5b7ac5ee83"
GATE_REL = f"results/audit/product/CYCLE_{ACCEPTED_RUN}_GATE.json"
GATE_SHA = "d7b902214fd0931a328b366f2e431a7ade89b034ac722d07cd380bb1ddcc8011"

STATE = ROOT / "state" / "product.json"
DIAG = (ROOT / "results" / "product" / "orchestration"
        / f"CYCLE_{SNAPSHOT_RUN}_snapshot_diagnosis.json")
BASELINE_COMPARISON = (ROOT / "results" / "product" / "orchestration"
                       / f"CYCLE_{RUN_ID}_full_suite_baseline_comparison.json")
REPORT = ROOT / "reports" / "product" / f"CYCLE_{RUN_ID}.md"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=str(ROOT), capture_output=True, text=True,
        check=True).stdout.strip()


def test_snapshot_refs_are_byte_identical_to_the_predecessor_head():
    """Pin the *snapshot* against its fixed predecessor, never against HEAD.

    Historical defect repaired in 46115755920: the original version of this
    test asserted ``rev-parse HEAD == ACCEPTED_SHA``. That holds only before
    the resuming producer commits anything; the moment the durable delta lands,
    HEAD moves to the new producer commit and the test fails on its own tree.
    A snapshot claim is about the snapshot refs and tree, so compare those to
    the fixed predecessor commit and separately prove that the resuming HEAD
    was built on top of that preserved work (no restart from scratch).
    """
    predecessor = _git("rev-parse", ACCEPTED_SHA)
    assert predecessor == ACCEPTED_SHA
    snapshot_shas = {}
    for suffix in ("team", "team-attempt-1"):
        ref = _git("ls-remote", "--heads", "origin",
                   f"refs/heads/cycle/core/product/{SNAPSHOT_RUN}/{suffix}")
        snapshot_shas[suffix] = ref.split()[0]
        assert snapshot_shas[suffix] == predecessor
    # Diff against the advertised SHA, not a remote-tracking ref name that a
    # producer checkout may never have fetched (git exits 128 on that name).
    assert _git("diff", "--name-status", ACCEPTED_SHA,
                snapshot_shas["team"]) == ""
    # Check the SNAPSHOT TREE, not this resume's working tree (which now names
    # the snapshot in its diagnosis and state on purpose). git grep exits 1 on
    # no match, so this probe must not use the check=True helper.
    probe = subprocess.run(
        ["git", "grep", "-n", SNAPSHOT_RUN, ACCEPTED_SHA, "--", "."],
        cwd=str(ROOT), capture_output=True, text=True, check=False)
    assert probe.returncode == 1 and probe.stdout == ""
    # The resuming work must descend from the preserved snapshot: comparing a
    # mutable HEAD to a fixed SHA would have hidden a restart from scratch.
    ancestor = subprocess.run(
        ["git", "merge-base", "--is-ancestor", ACCEPTED_SHA, "HEAD"],
        cwd=str(ROOT), capture_output=True, text=True, check=False)
    assert ancestor.returncode == 0, ancestor.stderr


def test_no_audit_ref_or_gate_exists_for_the_snapshot_run():
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
    assert doc["predecessor_run_id"] == ACCEPTED_RUN
    orch = doc["orchestration"]
    assert orch["classification"] == "ZERO_DURABLE_DELTA_SNAPSHOT"
    assert orch["mechanism_unobserved"] is True
    assert "mechanism" not in orch
    assert orch["raw_snapshot"] is None
    assert orch["exit_code"] is None
    assert orch["audit"]["gate_file_written"] is False
    delta = doc["durable_delta"]
    assert delta["classification"] == "ZERO_DURABLE_DELTA"
    assert delta["changed_files"] == 0
    assert delta["snapshot_head"] == delta["predecessor_head"] == ACCEPTED_SHA
    assert doc["adjudication"]["accepted"] is False
    assert doc["adjudication"]["status"] == "UNADJUDICATED"
    unavailable = [o for o in doc["observations"]
                   if o["check"] == "github_metadata_unavailable"]
    assert unavailable and unavailable[0]["evidence_tier"] == "UNAVAILABLE"


def test_accepted_pointer_advances_only_with_both_halves_verified():
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
    lab_head = _git("ls-remote", "--heads", "origin", "refs/heads/lab/product")
    assert lab_head.startswith(ACCEPTED_SHA)
    from product import state_contract as sc
    assert sc.accepted_pointer_evidence(st, ROOT)["problems"] == []


def test_historical_pointer_and_accepted_findings_are_preserved():
    st = _load(STATE)
    blob = json.dumps(st)
    assert "CYCLE_40269774540" in blob and "5adaa66d" in blob
    diag = _load(ROOT / "results" / "product" / "query_map_diagnosis"
                 / "CYCLE_40257275384.json")
    assert diag["verdict"] == "PASS" and not diag["n_failed_checks"]
    assert diag["current_reading"]["open_leg_from_items_1_to_3"] == "NONE"
    for finding in ("40070818687", "40068038783", "40105794124"):
        assert any(f["run_id"] == finding and f["re_derived"] is False
                   for f in diag["findings_consumed"])
    family = _load(ROOT / "results" / "product" / "counter_content_family"
                   / "CYCLE_40257275384.json")
    assert family["ordered_work_2_full_success_rule"]["met"] is True
    assert family["false_reject_count"] == 0


def test_posture_stays_fail_closed_and_resume_is_recorded():
    st = _load(STATE)
    assert st["direction_version"] == 68
    # Historical state pins must survive later valid resumes: current_cycle_run_id
    # legitimately moves forward. Require this run to remain in run_history and
    # require any later current run to be recorded there too, instead of
    # freezing a mutable pointer that breaks on the next accepted resume.
    history = {str(h["run_id"]): h for h in st["run_history"]}
    assert RUN_ID in history
    current = str(st["current_cycle_run_id"])
    assert current in history and int(current) >= int(RUN_ID)
    for key in ("human_gate_ready", "machine_gate_ready", "packet_admitted",
                "ready_for_owner_session"):
        assert st[key] is False
    assert st["continue_recommended"] is True
    block = st["cycle_46106207560_operational_resume"]
    assert block["snapshot_run_id"] == int(SNAPSHOT_RUN)
    assert block["classification"] == "ZERO_DURABLE_DELTA_SNAPSHOT"
    hist = {str(h["run_id"]): h for h in st["run_history"]}
    assert SNAPSHOT_RUN in hist and RUN_ID in hist


def test_audit_readiness_models_zero_delta_snapshot_without_default_fallback():
    from product import audit_readiness as ar
    prof = ar.select_profile(RUN_ID)
    assert prof["resumed_run_id"] == SNAPSHOT_RUN
    assert prof["classification"] == "ZERO_DURABLE_DELTA_SNAPSHOT"
    assert prof["mechanism_kind"] == "unobserved"
    assert prof["delta_kind"] == "zero"
    assert prof["cycle_test"] == "product/tests/test_cycle_46109821912.py"
    assert ar.PROFILES[SNAPSHOT_RUN]["alias_of"] == RUN_ID
    try:
        ar.select_profile("99999999999")
    except SystemExit:
        pass
    else:  # pragma: no cover - defensive
        raise AssertionError("select_profile must fail closed on unknown runs")


def test_state_contract_and_lane_scope_hold_on_the_snapshot():
    proc = subprocess.run(
        [sys.executable, "product/state_contract.py", "--check",
         "--direction-version", "68", "--json"],
        cwd=str(ROOT), capture_output=True, text=True, check=False)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert json.loads(proc.stdout)["ok"] is True
    pending = _git("status", "--porcelain", "-uall").splitlines()
    audit_writes = [line[3:] for line in pending
                    if line[3:].startswith(("results/audit/product/",
                                           "reports/audit/product/"))]
    assert audit_writes == []
    assert not [line for line in pending if line[3:].startswith(".github/")]


def test_report_of_record_discloses_pointer_supersession_and_claim_ceiling():
    text = REPORT.read_text(encoding="utf-8")
    for token in (RUN_ID, SNAPSHOT_RUN, ACCEPTED_SHA[:8], "ZERO_DURABLE_DELTA",
                  "CYCLE_40269774540", "DO-NOT-SERVE"):
        assert token in text, token
    assert "full-suite" in text and "NO_NEW_FULL_SUITE_FAILURES" in text


def test_full_suite_failures_are_baseline_inherited_not_cycle_caused():
    doc = _load(BASELINE_COMPARISON)
    assert doc["schema"] == "product-full-suite-baseline-comparison/1"
    assert doc["run_id"] == RUN_ID and doc["resumed_run_id"] == SNAPSHOT_RUN
    assert doc["baseline_commit"] == ACCEPTED_SHA
    results = doc["results"]
    current = results["current"]
    baseline = results["clean_head_baseline"]
    assert current["failed_test_ids"] == baseline["failed_test_ids"] == 211
    assert current["failed_test_id_sha256"] == baseline["failed_test_id_sha256"]
    assert doc["comparison"]["intersection_count"] == 211
    assert doc["comparison"]["current_only"] == []
    assert doc["comparison"]["baseline_only"] == []
    assert doc["comparison"]["failure_id_sets_identical"] is True
    assert doc["comparison"]["classification"] == "NO_NEW_FULL_SUITE_FAILURES"

"""Resume run 44877180401: post-acceptance validation repair of snapshot 44873436245.

The persisted producer snapshot was byte-identical to accepted head 7be4480e:
run 44873436245's team job died in ``Run lane cycle`` with
``LEX_WORK_QUANTUM_EXPIRED seconds=2700`` / exit 78, and the always-on persist
step committed an empty tree.  The snapshot's own shipped cycle test, however,
asserted the PRE-acceptance state (old accepted pointer, no gate for its own
run) and therefore failed once cycle 40284658455 was accepted.  This test pins
the repair and keeps the previously claim-bearing artifacts untouched.
"""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

RUN_ID = "44877180401"
PRIOR_RUN_ID = "44873436245"
ACCEPTED_RUN_ID = "40284658455"
ACCEPTED_COMMIT_PREFIX = "7be4480e"
OLD_ACCEPTED_RUN_ID = "CYCLE_40269774540"
OLD_ACCEPTED_COMMIT_PREFIX = "5adaa66d"

STATE = ROOT / "state" / "product.json"
DIAG = ROOT / "results" / "product" / "orchestration" / (
    f"CYCLE_{PRIOR_RUN_ID}_resume_diagnosis.json")
REPORT = ROOT / "reports" / "product" / f"CYCLE_{RUN_ID}.md"
SHIPPED_CYCLE_TEST = ROOT / "product" / "tests" / (
    f"test_cycle_{ACCEPTED_RUN_ID}.py")

# Claim-bearing accepted artifacts this cycle must NOT modify.
PINNED = {
    "results/audit/product/CYCLE_40284658455_GATE.json":
        "d7b902214fd0931a328b366f2e431a7ade89b034ac722d07cd380bb1ddcc8011",
    "results/product/counter_content_family/CYCLE_40257275384.json":
        "eaab4d0637c537a74e08cee37aff781b4fddea0294fa817c74e23e64e9a81feb",
    "results/product/incidents/"
    "self_minted_gate_40278460732_producer_40283048553.QUARANTINED.json":
        "79be9729415ce7ee74708da7142311b557c6caeca7ad9cf55ad702a834a91894",
    "product/query/counter_evidence_span.py":
        "82cea13122b13a60e4da746072af4a185f9e4b2e0ef51853d6273acb7a1bb6ce",
}


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=str(ROOT), capture_output=True, text=True,
        check=True).stdout.strip()


def test_orchestration_diagnosis_is_the_observed_quantum_expiry():
    d = _load(DIAG)
    assert d["schema"] == "product-orchestration-resume-diagnosis/1"
    assert d["run_id"] == PRIOR_RUN_ID
    assert d["resuming_run_id"] == RUN_ID
    assert d["direction_version"] == 68
    assert d["classification"] == (
        "TEAM_JOB_RUN_LANE_CYCLE_QUANTUM_EXPIRED_ZERO_DURABLE_DELTA_NO_GATE")
    obs = d["observation"]
    assert obs["run"]["conclusion"] == "failure"
    assert obs["jobs"]["total_count"] == 4
    assert obs["jobs"]["team"]["conclusion"] == "failure"
    assert obs["jobs"]["audit"]["conclusion"] == "skipped"
    assert obs["jobs"]["integrate"]["conclusion"] == "skipped"
    assert obs["jobs"]["resilience"]["conclusion"] == "success"
    assert obs["jobs"]["team"]["steps"]["Run lane cycle"] == "failure"
    assert obs["jobs"]["team"]["steps"]["Enforce lane write scope"] == "skipped"
    messages = [a["message"] for a in obs["annotations"]]
    assert "LEX_WORK_QUANTUM_EXPIRED seconds=2700 pid=2403" in messages
    assert "Process completed with exit code 78." in messages
    assert obs["git_plumbing"]["audit_ref_present"] is False
    assert obs["git_plumbing"]["team_ref"] == (
        "7be4480ed3ca623b77ea082404ca3b5b7ac5ee83")
    assert obs["git_plumbing"]["team_ref_diff_vs_accepted_head"] == ""
    diag = d["diagnosis"]
    assert diag["mechanism"] == "OBSERVED_QUANTUM_EXPIRED_ZERO_DURABLE_DELTA"
    assert diag["exit_code"] == 78 and diag["quantum_seconds"] == 2700
    assert diag["durable_delta_committed_by_run"] is False
    assert diag["audit_gate_written"] is False
    assert diag["promotion"] is False
    assert diag["product_defect"] is False
    assert "ZERO_DELTA" in " ".join(diag["excluded_mechanisms"]) or any(
        "rc=67" in m for m in diag["excluded_mechanisms"])


def test_accepted_pointer_advanced_with_both_halves_and_history_preserved():
    st = _load(STATE)
    assert st["lane"] == "product"
    assert st["direction_version"] == 68
    assert st["accepted_run_id"] == f"CYCLE_{ACCEPTED_RUN_ID}"
    assert st["accepted_commit"].startswith(ACCEPTED_COMMIT_PREFIX)
    assert st["current_cycle_run_id"] == int(RUN_ID)

    gate = _load(ROOT / "results" / "audit" / "product" /
                 f"CYCLE_{ACCEPTED_RUN_ID}_GATE.json")
    assert gate["gate"] == "PASS"
    assert gate["safe_to_integrate"] is True
    assert gate["required_fixes"] == []
    head = _git("ls-remote", "--heads", "origin", "refs/heads/lab/product")
    assert head.startswith(st["accepted_commit"]), (head, st["accepted_commit"])
    accept_log = _git("log", "--oneline", "-1", st["accepted_commit"])
    assert f"accept product cycle {ACCEPTED_RUN_ID}" in accept_log

    hist = st["historical_accepted_pointer_40284658455"]
    assert hist["accepted_run_id"] == OLD_ACCEPTED_RUN_ID
    assert hist["accepted_commit"].startswith(OLD_ACCEPTED_COMMIT_PREFIX)
    assert (ROOT / hist["gate_path"]).is_file()

    resume = st["cycle_44873436245_operational_resume"]
    assert resume["audit_ref_exists"] is False
    assert resume["gate_minted_by_producer"] is False
    assert resume["durable_delta_committed_by_run"] is False


def test_posture_stays_fail_closed_and_no_gate_was_minted_for_resume_runs():
    st = _load(STATE)
    for key in ("human_gate_ready", "machine_gate_ready", "packet_admitted",
                "ready_for_owner_session"):
        assert st[key] is False, (key, st[key])
    assert st["continue_recommended"] is True
    for run in (PRIOR_RUN_ID, RUN_ID):
        assert not (ROOT / "results" / "audit" / "product" /
                    f"CYCLE_{run}_GATE.json").exists()
        refs = _git("ls-remote", "--heads", "origin",
                    f"refs/heads/cycle/core/product/{run}/audit")
        assert refs == "", (run, refs)


def test_shipped_cycle_test_was_repaired_not_weakened():
    text = SHIPPED_CYCLE_TEST.read_text(encoding="utf-8")
    assert "POST-ACCEPTANCE REPAIR" in text
    assert 'assert gate["gate"] == "PASS"' in text
    assert "historical_accepted_pointer_40284658455" in text
    # The two obsolete pre-acceptance assertions are gone.
    assert 'assert not (ROOT / "results" / "audit" / "product" /\n                f"CYCLE_{EXECUTING_RUN_ID}_GATE.json").exists()' not in text
    assert 'assert st["accepted_run_id"] == "CYCLE_40269774540"\n    assert st["accepted_commit"].startswith("5adaa66d")' not in text


def test_claim_bearing_accepted_artifacts_are_byte_unchanged():
    for rel, expected in PINNED.items():
        path = ROOT / rel
        assert path.is_file(), rel
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        assert actual == expected, (rel, actual, expected)


def test_report_of_record_names_both_runs_and_the_binding_ceiling():
    text = REPORT.read_text(encoding="utf-8")
    assert RUN_ID in text and PRIOR_RUN_ID in text
    assert "LEX_WORK_QUANTUM_EXPIRED" in text
    assert "CYCLE_40284658455" in text
    assert "NOT" in text.upper() and "FROZEN" in text.upper()

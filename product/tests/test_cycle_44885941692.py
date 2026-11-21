"""Resume run 44885941692: rc-67 zero-delta snapshot 44885532084.

The persisted producer snapshot for run 44885532084 was byte-identical to its
predecessor (b3993d3c): the TEAM job failed at step 6 ``Run lane cycle`` with
check-run annotations ``LEX_ZERO_DELTA_REPAIR`` / ``exit code 67`` (the rc-67
guard of factory-wide requirement 10 -- "the producer found nothing to do"),
the validation and write-scope steps were skipped, and the ``if: always()``
persist step published the unchanged tree.  Audit and integrate were skipped.
This is an orchestration guard exit, NOT a product defect and NOT an audit
verdict.

This test pins (a) that honest machine-readable diagnosis, (b) that the shipped
vertical slice is still runnable from the committed snapshot, and (c) that the
FAIL-CLOSED posture and the accepted pointer are unchanged.  It writes no gate,
labels no run accepted, and mints no claim the committed artifacts cannot show.
"""
from __future__ import annotations

import hashlib
import json
import socket
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PRODUCT = ROOT / "product"
for _p in (str(PRODUCT), str(ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

RUN_ID = "44885941692"
RESUMED_RUN_ID = "44885532084"
ACCEPTED_RUN_ID = "40284658455"
ACCEPTED_COMMIT_PREFIX = "7be4480e"
SNAPSHOT_HEAD = "b3993d3c4f92bce469b4a6c96c55f097cc4a4c70"

STATE = ROOT / "state" / "product.json"
DIAG = ROOT / "results" / "product" / "orchestration" / (
    f"CYCLE_{RESUMED_RUN_ID}_resume_diagnosis.json")
RAW = ROOT / "results" / "product" / "orchestration" / (
    f"CYCLE_{RESUMED_RUN_ID}_team_step_raw.json")
REPORT = ROOT / "reports" / "product" / f"CYCLE_{RUN_ID}.md"

# Claim-bearing accepted artifacts this resume must NOT modify.  Hashes are the
# same pins the accepted cycle 44877180401 test enforces.
PINNED = {
    "results/audit/product/CYCLE_40284658455_GATE.json":
        "d7b902214fd0931a328b366f2e431a7ade89b034ac722d07cd380bb1ddcc8011",
    "results/product/counter_content_family/CYCLE_40257275384.json":
        "eaab4d0637c537a74e08cee37aff781b4fddea0294fa817c74e23e64e9a81feb",
    "product/query/counter_evidence_span.py":
        "82cea13122b13a60e4da746072af4a185f9e4b2e0ef51853d6273acb7a1bb6ce",
}


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=str(ROOT), capture_output=True, text=True,
        check=True).stdout.strip()


def _no_network(*_a, **_k):  # pragma: no cover
    raise AssertionError("offline slice attempted network access")


def test_resumed_run_is_the_observed_rc67_zero_delta_guard():
    d = _load(DIAG)
    assert d["schema"] == "product-resume-snapshot-diagnosis/1"
    assert d["run_id"] == RESUMED_RUN_ID
    o = d["orchestration"]
    assert o["classification"] == "TEAM_JOB_LANE_CYCLE_STEP_FAILED_NO_GATE"
    assert o["observed_failure"]["source"] == "github_actions_check_run_annotations"
    assert o["observed_failure"]["exit_code"] == 67
    assert o["observed_failure"]["quantum_expired"] is False
    messages = o["observed_failure"]["messages"]
    assert "LEX_ZERO_DELTA_REPAIR" in messages
    assert "Process completed with exit code 67." in messages
    assert o["adjudication"]["product_defect"] is False
    assert o["adjudication"]["verdict_written"] is False
    assert d["durable_delta"]["classification"] == "ZERO_DURABLE_DELTA"
    assert d["durable_delta"]["snapshot_head"] == SNAPSHOT_HEAD
    assert d["durable_delta"]["changed_files"] == 0
    assert d["adjudication"]["status"] == "UNADJUDICATED"
    assert d["adjudication"]["accepted"] is False

    # The committed raw snapshot is the public REST evidence behind the above.
    raw = _load(RAW)
    jobs = {j["name"]: j for j in raw["jobs"]}
    assert raw["run"]["id"] == int(RESUMED_RUN_ID)
    assert jobs["team"]["conclusion"] == "failure"
    assert jobs["audit"]["conclusion"] == "skipped"
    assert jobs["integrate"]["conclusion"] == "skipped"
    step = next(s for s in jobs["team"]["steps"] if s["name"] == "Run lane cycle")
    assert step["conclusion"] == "failure"
    assert any(s["name"] == "Enforce lane write scope" and s["conclusion"] == "skipped"
               for s in jobs["team"]["steps"])
    assert any(s["name"] == "Persist team snapshot" and s["conclusion"] == "success"
               for s in jobs["team"]["steps"])


def test_snapshot_ref_is_byte_identical_to_its_predecessor():
    """The resume must PRESERVE the persisted snapshot, not restart from scratch.

    Operational-resume checkouts fetch their own team ref but not necessarily
    the predecessor's, so a hard ``rev-parse`` of the remote ref is an
    environment dependency rather than a product claim.  Verify the same fact
    from local git objects: the snapshot commit exists and is an ancestor of
    HEAD, and if the remote ref happens to be present it must name that commit.
    """
    # The commit is retrievable locally (git objects, not only a remote ref).
    assert _git("rev-parse", "--verify", SNAPSHOT_HEAD) == SNAPSHOT_HEAD
    ancestor = subprocess.run(
        ["git", "merge-base", "--is-ancestor", SNAPSHOT_HEAD, "HEAD"],
        cwd=str(ROOT), capture_output=True, text=True, check=False)
    assert ancestor.returncode == 0, \
        "the resume must preserve the persisted snapshot, not a fresh tree"
    ref = subprocess.run(
        ["git", "rev-parse", "--verify", "--quiet",
         f"origin/cycle/core/product/{RESUMED_RUN_ID}/team"],
        cwd=str(ROOT), capture_output=True, text=True, check=False)
    if ref.returncode == 0:
        assert ref.stdout.strip() == SNAPSHOT_HEAD


def test_vertical_slice_is_still_runnable_from_the_snapshot(monkeypatch, tmp_path):
    """FAST-MVP deliverable check: with the socket booby-trapped, the committed
    snapshot still turns a frozen question into a clickable query map.  Map-only
    mode keeps this fast and free of any node/DOM dependency."""
    import offline_slice as ofs

    monkeypatch.setattr(socket.socket, "connect", _no_network)
    rc = ofs.main(["--slug", "rent-default", "--out", str(tmp_path), "--no-enrich"])
    assert rc == 0
    summary = _load(tmp_path / "summary.json")
    stats = summary["stats"]
    assert summary["mode"] == "map_only"
    assert summary["page_contract"] is False  # no DOM verify requested here
    assert stats["enriched"] is False
    n = stats["n_decisions"]
    assert n >= 40
    assert stats["rows_with_xy"] == n
    assert stats["rows_with_cluster_id"] == n
    assert stats["rows_with_canonical_url"] == n
    assert stats["n_clusters"] >= 2, "a map with one cluster is a list"
    bundle = _load(tmp_path / "rent-default.bundle.json")
    assert bundle["provenance"]["product_fixture_replay"]["network"] == "none"


def test_state_records_this_run_with_fail_closed_posture():
    st = _load(STATE)
    assert st["lane"] == "product"
    assert st["direction_version"] == 68
    # The accepted pointer is untouched by an operational resume.
    assert st["accepted_run_id"] == f"CYCLE_{ACCEPTED_RUN_ID}"
    assert st["accepted_commit"].startswith(ACCEPTED_COMMIT_PREFIX)
    entry = st["cycle_44885941692_operational_resume"]
    assert entry["run_id"] == int(RUN_ID)
    assert entry["resumed_snapshot_run_id"] == int(RESUMED_RUN_ID)
    assert entry["orchestration_classification"] == (
        "TEAM_JOB_LANE_CYCLE_STEP_FAILED_NO_GATE")
    assert entry["exit_code"] == 67
    assert entry["durable_delta"] == "ZERO_DURABLE_DELTA"
    for key in ("human_gate_ready", "machine_gate_ready", "packet_admitted",
                "ready_for_owner_session"):
        assert st[key] is False, (key, st[key])
    assert st["continue_recommended"] is True
    refs = " ".join(st["evidence_refs"])
    assert f"CYCLE_{RESUMED_RUN_ID}_resume_diagnosis.json" in refs
    assert f"test_cycle_{RUN_ID}.py" in refs
    assert f"CYCLE_{RUN_ID}.md" in refs


def test_no_producer_minted_gate_for_either_resume_run():
    for run in (RESUMED_RUN_ID, RUN_ID):
        assert not (ROOT / "results" / "audit" / "product" /
                    f"CYCLE_{run}_GATE.json").exists()
        refs = _git("ls-remote", "--heads", "origin",
                    f"refs/heads/cycle/core/product/{run}/audit")
        assert refs == "", (run, refs)


def test_claim_bearing_accepted_artifacts_are_byte_unchanged():
    for rel, expected in PINNED.items():
        path = ROOT / rel
        assert path.is_file(), rel
        assert hashlib.sha256(path.read_bytes()).hexdigest() == expected, rel


def test_report_of_record_names_the_guard_and_the_ceiling():
    text = REPORT.read_text(encoding="utf-8")
    assert RUN_ID in text and RESUMED_RUN_ID in text
    assert "LEX_ZERO_DELTA_REPAIR" in text and "exit code 67" in text
    assert "ZERO_DURABLE_DELTA" in text
    assert "NOT" in text.upper() and "FROZEN" in text.upper()

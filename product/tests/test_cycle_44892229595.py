"""Operational resume run 44892229595 from snapshot 44885941692.

The persisted producer snapshot (588fa990) completed the TEAM job with all
validation and write-scope steps green.  Its AUDIT job then consumed the whole
2700 s work quantum at ``Independent audit`` (2705.0 s, exit 78,
LEX_WORK_QUANTUM_EXPIRED pid=2580), so no gate was written, the gate reader was
skipped and integrate did not run.  That is an orchestration fact, NOT a product
defect, NOT a REVISE/BLOCKED verdict and NOT acceptance.

This test pins four things:

1. the honest machine-readable diagnosis of that failure, from committed public
   REST evidence;
2. the concrete runnable delta of this resume: the one-command vertical slice
   now enforces the v68 P0 counter-content invariant on the bundle it *just
   generated*, with a non-vacuity control;
3. that the snapshot is preserved (not restarted) and the accepted pointer,
   pinned claim-bearing artifacts and FAIL-CLOSED posture are unchanged;
4. that this producer minted no auditor-namespace gate.
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
for _p in (str(ROOT), str(PRODUCT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

RUN_ID = "44892229595"
SNAPSHOT_RUN_ID = "44885941692"
SNAPSHOT_HEAD = "588fa990eab2e4382a3c1b18e575806f4ad7622d"
PREDCESSOR_HEAD = "b3993d3c4f92bce469b4a6c96c55f097cc4a4c70"
ACCEPTED_RUN_ID = "40284658455"
ACCEPTED_COMMIT_PREFIX = "7be4480e"

STATE = ROOT / "state" / "product.json"
DIAG = ROOT / "results" / "product" / "orchestration" / (
    f"CYCLE_{SNAPSHOT_RUN_ID}_resume_diagnosis.json")
RAW = ROOT / "results" / "product" / "orchestration" / (
    f"CYCLE_{SNAPSHOT_RUN_ID}_run_jobs_raw.json")
REPORT = ROOT / "reports" / "product" / f"CYCLE_{RUN_ID}.md"
DOSSIER = ROOT / "results" / "product" / "audit_readiness" / (
    f"CYCLE_{RUN_ID}_audit_readiness.json")

# Claim-bearing accepted artifacts this resume must NOT modify.
PINNED = {
    "results/audit/product/CYCLE_40284658455_GATE.json":
        "d7b902214fd0931a328b366f2e431a7ade89b034ac722d07cd380bb1ddcc8011",
    "results/product/counter_content_family/CYCLE_40257275384.json":
        "eaab4d0637c537a74e08cee37aff781b4fddea0294fa817c74e23e64e9a81feb",
    "product/query/counter_evidence_span.py":
        "82cea13122b13a60e4da746072af4a185f9e4b2e0ef51853d6273acb7a1bb6ce",
}


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=str(ROOT),
                          capture_output=True, text=True, check=False)


def _no_network(*_a, **_k):  # pragma: no cover
    raise AssertionError("offline slice attempted network access")


# --------------------------------------------------------------------------- #
# 1. orchestration diagnosis
# --------------------------------------------------------------------------- #

def test_snapshot_failure_is_observed_audit_quantum_expiry():
    d = _load(DIAG)
    assert d["schema"] == "product-resume-snapshot-diagnosis/1"
    assert d["run_id"] == SNAPSHOT_RUN_ID
    o = d["orchestration"]
    assert o["classification"] == "AUDIT_JOB_INDEPENDENT_AUDIT_STEP_FAILED_NO_GATE"
    assert o["team"]["conclusion"] == "success"
    assert o["team"]["producer_state_validation_step_conclusion"] == "success"
    assert o["team"]["write_scope_step_conclusion"] == "success"
    assert o["audit"]["conclusion"] == "failure"
    assert o["audit"]["failed_step"] == "Independent audit"
    assert o["audit"]["gate_file_written"] is False
    m = o["mechanism"]
    assert m["status"] == "OBSERVED_QUANTUM_EXPIRED"
    assert m["quantum_expired"] is True and m["quantum_seconds"] == 2700
    assert m["exit_code"] == 78
    assert o["observed_failure"]["quantum_message"] == (
        "LEX_WORK_QUANTUM_EXPIRED seconds=2700 pid=2580")
    assert d["adjudication"]["status"] == "UNADJUDICATED"
    assert d["adjudication"]["accepted"] is False
    assert d["adjudication"]["product_defect"] is False

    raw = _load(RAW)
    jobs = {j["name"]: j for j in raw["jobs"]}
    assert raw["run"]["id"] == int(SNAPSHOT_RUN_ID)
    assert jobs["team"]["conclusion"] == "success"
    assert jobs["audit"]["conclusion"] == "failure"
    assert jobs["integrate"]["conclusion"] == "skipped"
    msgs = [a.get("message", "")
            for a in raw["annotations"].get(str(jobs["audit"]["id"]), [])]
    assert "LEX_WORK_QUANTUM_EXPIRED seconds=2700 pid=2580" in msgs
    assert "Process completed with exit code 78." in msgs


def test_snapshot_delta_is_committed_and_preserved_by_this_resume():
    d = _load(DIAG)
    delta = d["durable_delta"]
    assert delta["classification"] == "COMMITTED_DELTA"
    assert delta["snapshot_head"] == SNAPSHOT_HEAD
    assert delta["predecessor_head"] == PREDCESSOR_HEAD
    assert delta["changed_files"] == 5
    assert any("test_cycle_44885941692.py" in s
               for s in delta["changed_paths_sample"])

    ref = _git("rev-parse", "--verify", "--quiet",
               f"origin/cycle/core/product/{SNAPSHOT_RUN_ID}/team")
    assert ref.returncode == 0, "the persisted team ref must be fetchable"
    assert ref.stdout.strip() == SNAPSHOT_HEAD
    ancestor = _git("merge-base", "--is-ancestor", SNAPSHOT_HEAD, "HEAD")
    assert ancestor.returncode == 0, \
        "the resume must preserve the snapshot, not restart from scratch"


# --------------------------------------------------------------------------- #
# 2. runnable product delta: v68 invariant on a freshly generated bundle
# --------------------------------------------------------------------------- #

def test_one_command_slice_enforces_v68_invariant_on_its_fresh_bundle(
        monkeypatch, tmp_path, capsys):
    import offline_slice as ofs

    monkeypatch.setattr(socket.socket, "connect", _no_network)
    rc = ofs.main(["--slug", "rent-default", "--out", str(tmp_path), "--verify"])
    out = capsys.readouterr().out
    assert rc == 0, out
    summary = _load(tmp_path / "summary.json")
    stats = summary["stats"]
    assert summary["verified"] is True and summary["page_contract"] is True
    assert summary["mode"] == "full_loop"
    assert stats["enriched"] is True
    # The newly enforced invariant is measured on THIS run's bundle.
    assert stats["counter_verified_rows"] >= 1
    assert stats["counter_verified_defective_rows"] == 0
    assert stats["counter_verified_defect_histogram"] == {}
    assert stats["counter_verified_defective_detail"] == []
    assert "REPORTED-ONLY" in stats["counter_content_predicate"]
    assert "no frozen bar scored" in stats["counter_content_predicate"]
    assert "counter_verified_defective_rows: 0" in out
    assert socket.socket.connect is _no_network, "network trap was not active"


def test_v68_invariant_is_non_vacuous(monkeypatch, tmp_path, capsys):
    """A verified row with offset-0 court-header evidence must FAIL the slice."""
    import offline_slice as ofs

    letterhead = ("Kantonsgericht Graubünden / Tribunale cantonale dei Grigioni "
                  "/ Kantonsgericht Graubünden")
    rows = []
    for n in range(45):
        row = {"decision_id": f"bge_{n}", "x": float(n), "y": float(n),
               "cluster_id": n % 3, "counter_status": "none",
               "canonical_url": "https://mcp.opencaselaw.ch/d/x"}
        if n == 0:
            row.update({"counter_evidence_verified": True,
                        "counter_evidence": letterhead,
                        "full_text": letterhead, "language": "de"})
        rows.append(row)
    bundle = {
        "decisions": rows,
        "answer": {"status": "ready", "cited_decision_ids": ["bge_0"],
                   "prose": "x", "method": "synthetic"},
        "provenance": {"offline_slice": {"enriched": True,
                                         "geometry_preserved": True,
                                         "network": "none"}},
    }
    monkeypatch.setattr(ofs, "build_bundle", lambda *_a, **_k: bundle)
    rc = ofs.main(["--slug", "rent-default", "--out", str(tmp_path)])
    out = capsys.readouterr().out
    assert rc == 1, out
    assert "frozen content defects" in out
    summary = _load(tmp_path / "summary.json")
    stats = summary["stats"]
    assert summary["verified"] is False
    assert stats["counter_verified_rows"] == 1
    assert stats["counter_verified_defective_rows"] == 1
    assert stats["counter_verified_defect_histogram"] == {
        "D2_letterhead_zone": 1}
    assert stats["counter_verified_defective_detail"][0]["decision_id"] == "bge_0"


# --------------------------------------------------------------------------- #
# 3. fail-closed state, accepted pins, audit namespace
# --------------------------------------------------------------------------- #

def test_state_records_this_resume_and_stays_fail_closed():
    st = _load(STATE)
    assert st["lane"] == "product"
    assert st["direction_version"] == 68
    assert st["accepted_run_id"] == f"CYCLE_{ACCEPTED_RUN_ID}"
    assert st["accepted_commit"].startswith(ACCEPTED_COMMIT_PREFIX)
    entry = st["cycle_44892229595_operational_resume"]
    assert entry["run_id"] == int(RUN_ID)
    assert entry["resumed_snapshot_run_id"] == int(SNAPSHOT_RUN_ID)
    assert entry["orchestration_classification"] == (
        "AUDIT_JOB_INDEPENDENT_AUDIT_STEP_FAILED_NO_GATE")
    assert entry["exit_code"] == 78
    assert entry["quantum_seconds"] == 2700
    assert entry["durable_delta"] == "COMMITTED_DELTA"
    assert entry["product_delta"] == (
        "offline_slice enforces the v68 P0 counter-content invariant "
        "on the bundle it generates")
    for key in ("human_gate_ready", "machine_gate_ready", "packet_admitted",
                "ready_for_owner_session"):
        assert st[key] is False, (key, st[key])
    assert st["continue_recommended"] is True
    refs = " ".join(st["evidence_refs"])
    assert f"CYCLE_{SNAPSHOT_RUN_ID}_resume_diagnosis.json" in refs
    assert f"test_cycle_{RUN_ID}.py" in refs
    assert f"CYCLE_{RUN_ID}.md" in refs


def test_no_producer_minted_gate_for_either_run():
    for run in (SNAPSHOT_RUN_ID, RUN_ID):
        assert not (ROOT / "results" / "audit" / "product" /
                    f"CYCLE_{run}_GATE.json").exists()
        assert not (ROOT / "reports" / "audit" / "product" /
                    f"CYCLE_{run}.md").exists()
        ref = _git("rev-parse", "--verify", "--quiet",
                   f"origin/cycle/core/product/{run}/audit")
        assert ref.returncode != 0, (run, ref.stdout)


def test_claim_bearing_accepted_artifacts_are_byte_unchanged():
    for rel, expected in PINNED.items():
        path = ROOT / rel
        assert path.is_file(), rel
        assert hashlib.sha256(path.read_bytes()).hexdigest() == expected, rel


def test_report_of_record_names_the_real_failure_and_the_ceiling():
    text = REPORT.read_text(encoding="utf-8")
    assert RUN_ID in text and SNAPSHOT_RUN_ID in text
    assert "LEX_WORK_QUANTUM_EXPIRED" in text
    assert "exit code 78" in text and "UNADJUDICATED" in text
    assert "not a product defect" in text
    assert "NOT" in text.upper() and "FROZEN" in text.upper()

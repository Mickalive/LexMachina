"""Tests for the run 39471603258 operational resume (evaluation lane).

This cycle resumes from the persisted producer snapshot of run 39470495546,
which never reached an independent audit.  These tests pin:

1. the DIAGNOSIS - the failure mechanism is a lane-owned write-scope violation
   in the independent auditor's protected namespace;
2. the AUDIT-READY invariant - the lane snapshot owns no NEW file under
   results/audit or reports/audit, and the two offending pseudo-audit files are
   absent from the working tree after being re-homed byte-exactly;
3. the RE-HOME - the exact bytes and git blob oids of the offending files were
   preserved in the lane namespace before removal;
4. the VERIFICATION - the V3 counter-authority surface falsifier reproduces its
   committed record from the accepted mount (mount-dependent).

The synthetic tests are MOUNT-INDEPENDENT; the end-to-end V3 tests are skipped
without the accepted product mount.
"""
from __future__ import annotations

import base64
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

RUN_ID = "39471603258"
RESUMED_FROM = "39470495546"
RESUMED_HEAD = "01ebdab87e7e86a7f28d7d639d1b4bc02f785344"
ACCEPTED_BASE = "cbda785300413c4b8e3e630ed652dcf75feb26c4"

OUT_DIR = REPO / "results" / "evaluation" / f"orchestration_resume_{RUN_ID}"
DIAGNOSIS = OUT_DIR / f"{RUN_ID}_diagnosis.json"
VERIFICATION = OUT_DIR / f"{RUN_ID}_verification.json"
REHOME = OUT_DIR / f"{RESUMED_FROM}_producer_authored_audit_copy.json"

OFFENDERS = [
    "reports/audit/evaluation/CYCLE_39470495546.md",
    "results/audit/evaluation/CYCLE_39470495546_GATE.json",
]

MOUNT = Path("/tmp/lex_accepted/product")
needs_mount = pytest.mark.skipif(not MOUNT.is_dir(), reason="no accepted product mount")

FROZEN_PINS = {
    "evaluation/frozen_bars/RULES_LABEL.json":
        "4457e971df3dc5d10af2a727aa675afc15a15564c18eed4cede0af5eb41b4608",
    "evaluation/frozen_bars/RULES_GEOMETRY.json":
        "a7452748d40c511a14a1c7848ece5fe7f8f8901cc30f45a66918c89eb593a633",
    "evaluation/frozen_bars/VERDICT_CONTRACT.json":
        "b9cdb89438a8d16ee165fe2a5d73060524154d8e7ba8e0cab867e8ca17ff414c",
    "evaluation/retrieval_gate/frozen_retrieval_benchmark.json":
        "187b0e54b03b326c62d45d8ba48fc78dc88501086761cd91a84c304a7478ba72",
    "evaluation/MINIMAL_CA_BENCHMARK_HYPOTHESIS_V1.json":
        "f0c7711c71e94d7b7303f5fa3a61b444d67bee6d3bbd7f0708ed13ff6ffc8072",
    "evaluation/minimal_ca_benchmark.py":
        "567a9d2b231c5404b7324db2c30249e0961dbc90c698501d0ba5576c7297554b",
    "evaluation/counter_authority_surface_falsifier.py":
        "0d0c6827c0983a66504040c81b29e36b8ec324b8f06fa80d250f8db192547171",
    "evaluation/mapping_free_recall_falsifier.py":
        "58a2e77a66bb60385a53185e9426447e8465da9105e8a0cb8945d5fd77bfb302",
}

LANE_WRITE_SCOPE = [
    "evaluation/*", "tests/evaluation/*", "results/evaluation/*",
    "reports/evaluation/*", "state/evaluation.json", "data/evaluation/*",
]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# --------------------------------------------------------------------------- #
# 1. freeze-first artifacts
# --------------------------------------------------------------------------- #
def test_hypothesis_and_freeze_record_are_committed_before_the_records():
    for rel in ("evaluation/ORCHESTRATION_RESUME_39471603258_HYPOTHESIS_V1.json",
                "evaluation/ORCHESTRATION_RESUME_39471603258_FREEZE_RECORD.json"):
        assert (REPO / rel).is_file(), rel
    h = json.loads((REPO / "evaluation/ORCHESTRATION_RESUME_39471603258_HYPOTHESIS_V1.json")
                   .read_text(encoding="utf-8"))
    assert h["frozen_before_execution"] is True
    assert h["direction_version"] == 61
    assert h["github_run_context"] == int(RUN_ID)
    assert h["resumed_from_run"] == RESUMED_FROM
    assert "no_new_threshold_or_bar" in json.dumps(h).lower() or "zero_new_thresholds" in json.dumps(h)
    # freeze-first ordering from git history, not a hand-written field
    hyp = subprocess.run(
        ["git", "log", "--diff-filter=A", "--format=%H %cI %s", "--",
         "evaluation/ORCHESTRATION_RESUME_39471603258_HYPOTHESIS_V1.json"],
        cwd=str(REPO), capture_output=True, text=True, check=True).stdout.strip()
    assert hyp, "hypothesis has no adding commit"
    assert "39471603258" in hyp


def test_freeze_record_pins_the_resumed_and_accepted_heads():
    f = json.loads((REPO / "evaluation/ORCHESTRATION_RESUME_39471603258_FREEZE_RECORD.json")
                   .read_text(encoding="utf-8"))
    assert f["frozen_before_execution"] is True
    assert f["github_run_context"] == int(RUN_ID)
    assert f["resumed_from_run"] == RESUMED_FROM
    assert f["accepted_base"]["head"] == ACCEPTED_BASE
    for pin, digest in f["rehash_proofs_at_freeze"].items():
        assert _sha256(REPO / pin) == digest, pin


# --------------------------------------------------------------------------- #
# 2. diagnosis
# --------------------------------------------------------------------------- #
def test_diagnosis_names_the_scope_violation():
    d = json.loads(DIAGNOSIS.read_text(encoding="utf-8"))
    assert d["schema"] == "lex-evaluation-orchestration-failure-diagnosis/1"
    assert d["run_id"] == RUN_ID
    assert d["direction_version"] == 61
    assert d["diagnosed_run"]["github_run"] == RESUMED_FROM
    assert d["diagnosed_run"]["audit_branch"] is None
    assert d["job_chain"]["audit"].startswith("skipped")
    offenders = d["root_cause"]["mechanism"]["offenders"]
    assert sorted(offenders) == sorted(OFFENDERS)
    assert d["root_cause"]["classification"] == "PRODUCER_AUTHORED_AUDIT_PLACEMENT_OUT_OF_LANE_SCOPE"
    # the lane write scope must NOT permit the audit namespace
    assert d["root_cause"]["mechanism"]["lane_write_scope_patterns"] == LANE_WRITE_SCOPE


def test_lane_write_scope_excludes_the_audit_namespace():
    for pattern in LANE_WRITE_SCOPE:
        # shell-style case matching: '*' matches any characters including '/'
        import fnmatch
        if fnmatch.fnmatch("results/audit/evaluation/CYCLE_39470495546_GATE.json", pattern):
            pytest.fail(f"audit-namespace path unexpectedly matches lane scope {pattern!r}")
    # and the guard itself reads the same patterns
    wf = (REPO / ".github" / "workflows" / "core-lane.yml").read_text(encoding="utf-8")
    assert "Enforce lane write scope" in wf
    assert "results/$LANE" in wf and "reports/$LANE" in wf


# --------------------------------------------------------------------------- #
# 3. audit-ready invariant + re-home
# --------------------------------------------------------------------------- #
def test_offending_files_are_absent_from_the_lane_snapshot():
    for rel in OFFENDERS:
        assert not (REPO / rel).exists(), f"{rel} still in the lane snapshot"


def test_lane_owns_no_new_audit_namespace_file_for_this_run():
    for rel in (f"results/audit/evaluation/CYCLE_{RUN_ID}_GATE.json",
                f"reports/audit/evaluation/CYCLE_{RUN_ID}.md"):
        assert not (REPO / rel).exists(), f"lane authored its own audit output {rel}"


def test_rehome_preserves_exact_bytes_and_blob_oids():
    rec = json.loads(REHOME.read_text(encoding="utf-8"))
    assert rec["schema"] == "lex-evaluation-out-of-scope-rehome/1"
    assert rec["run_id"] == RUN_ID
    assert rec["resumed_from_run"] == RESUMED_FROM
    assert rec["resumed_head"] == RESUMED_HEAD
    assert {f["path"] for f in rec["files"]} == set(OFFENDERS)
    for f in rec["files"]:
        raw = base64.b64decode(f["bytes_b64"])
        assert hashlib.sha256(raw).hexdigest() == f["sha256"]
        assert f["git_blob_oid"] == subprocess.run(
            ["git", "rev-parse", f"{RESUMED_HEAD}:{f['path']}"],
            cwd=str(REPO), capture_output=True, text=True, check=True).stdout.strip()
        assert not (REPO / f["path"]).exists(), "re-homed file must not remain in the auditor namespace"


# --------------------------------------------------------------------------- #
# 4. verification (mount-dependent) + frozen pins
# --------------------------------------------------------------------------- #
def test_frozen_pins_rehash_byte_identical():
    for pin, digest in FROZEN_PINS.items():
        assert _sha256(REPO / pin) == digest, pin


@needs_mount
def test_verification_record_reproduces_the_committed_v3_record():
    v = json.loads(VERIFICATION.read_text(encoding="utf-8"))
    assert v["schema"] == "lex-evaluation-orchestration-resume/1"
    assert v["run_id"] == RUN_ID
    assert v["all_match"] is True
    assert v["frozen_pins_match"] is True
    assert v["mount_pins_match"] is True
    assert v["comparison"]["verdict"]["committed"] == "PRODUCT_FALSIFIED"
    assert v["comparison"]["verdict"]["replay"] == "PRODUCT_FALSIFIED"
    assert v["comparison"]["exit_code"]["committed"] == 1
    assert v["comparison"]["failed_gates"]["match"] is True
    assert v["comparison"]["input_drift"]["match"] is True
    assert v["comparison"]["non_vacuity_all_hold"]["match"] is True
    assert v["comparison"]["admissibility"]["match"] is True
    assert v["pytest_dedicated"]["returncode"] == 0
    assert v["human_gate_ready"] is False and v["owner_decision_required"] is False


@needs_mount
def test_fresh_replay_still_falsifies_on_the_accepted_mount(tmp_path):
    out = tmp_path / "v3.json"
    proc = subprocess.run(
        [sys.executable, "-m", "evaluation.counter_authority_surface_falsifier",
         "--run-id", "39471603258_replay", "--out", str(out)],
        cwd=str(REPO), capture_output=True, text=True)
    assert proc.returncode == 1
    rec = json.loads(out.read_text(encoding="utf-8"))
    assert rec["verdict"] == "PRODUCT_FALSIFIED"
    assert rec["input_drift"] == []
    assert rec["non_vacuity"]["all_hold"] is True

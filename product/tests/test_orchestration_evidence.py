"""The orchestration-death classifier must name classes, not moods.

Every case here is a hand-built record, so the whole module is testable with no
network and no GitHub access.  Two properties matter more than coverage:

* the classes must be **mutually distinguishable** — an audit that died because
  its gate file was misplaced must not be filed under "cancelled", because the
  two have opposite lane levers;
* the classifier must be **non-vacuous**: a record that merely *looks* like the
  39082232157 record must still be classified, so the label is not an artefact of
  a hard-coded run id.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from product import orchestration_evidence as oe

ROOT = Path(__file__).resolve().parents[2]


def _step(job, name, conclusion, duration, *, number=1):
    return {
        "job": job,
        "job_conclusion": conclusion,
        "step_number": number,
        "step": name,
        "status": "completed",
        "conclusion": conclusion,
        "duration_s": duration,
    }


AUDIT_AGENT = "Independent audit"
GATE_READER = "Enforce audit scope and read gate"
PERSIST = "Persist audit snapshot"


def test_read_wrapper_quantum_reads_the_real_script_when_present(tmp_path):
    """The quantum must come from the wrapper, not from a constant in this module.

    Hard-coding it would make the "the step outran the watchdog" claim silently
    wrong the first time the control plane changes the budget.
    """
    modern = tmp_path / ".github" / "scripts"
    modern.mkdir(parents=True)
    (modern / "run-ox-with-retry.sh").write_text(
        'WORK_QUANTUM_SECONDS="${LEX_AGENT_QUANTUM_SECONDS:-1234}"\n', encoding="utf-8"
    )
    assert oe.read_wrapper_quantum(tmp_path) == 1234

    # ... and against the checkout this cycle actually ran in.
    checked_out = oe.read_wrapper_quantum(ROOT)
    assert isinstance(checked_out, int) and checked_out > 0


def test_read_wrapper_quantum_degrades_to_the_documented_default(tmp_path):
    assert oe.read_wrapper_quantum(tmp_path) == oe.DEFAULT_WRAPPER_QUANTUM_SECONDS
    (tmp_path / ".github").mkdir()
    (tmp_path / ".github" / "scripts").mkdir()
    (tmp_path / ".github" / "scripts" / "run-ox-with-retry.sh").write_text(
        "no quantum here\n", encoding="utf-8"
    )
    assert oe.read_wrapper_quantum(tmp_path) == oe.DEFAULT_WRAPPER_QUANTUM_SECONDS


# --------------------------------------------------------------------------
# class discrimination
# --------------------------------------------------------------------------

def test_cancelled_audit_step_is_its_own_class():
    out = oe.classify(
        observation={"conclusion": "cancelled"},
        jobs={"team": "success", "audit": "cancelled", "integrate": "cancelled"},
        steps=[
            _step("team", "Persist team snapshot", "success", 12.0),
            _step("audit", AUDIT_AGENT, "cancelled", 3299.0, number=5),
            _step("audit", GATE_READER, "skipped", 0.0, number=6),
            _step("audit", PERSIST, "skipped", 0.0, number=7),
        ],
    )
    assert out["class"] == "AUDIT_STEP_CANCELLED_NO_GATE"
    assert out["producing_snapshot_survived"] is True
    assert out["verdict_exists"] is False


def test_failed_audit_step_is_not_filed_as_cancelled():
    """Opposite lane lever: a failure has a log line and a retryable cause."""
    out = oe.classify(
        observation={"conclusion": "failure"},
        jobs={"team": "success", "audit": "failure"},
        steps=[_step("audit", AUDIT_AGENT, "failure", 2611.0, number=5)],
    )
    assert out["class"] == "AUDIT_STEP_FAILED_NO_GATE"
    assert out["verdict_exists"] is False


def test_misplaced_gate_artifact_is_its_own_class():
    """Agent finished, workflow reader skipped: the lowercase/_tmp placement bug."""
    out = oe.classify(
        observation={"conclusion": "failure"},
        jobs={"team": "success", "audit": "failure"},
        steps=[
            _step("audit", AUDIT_AGENT, "success", 900.0, number=5),
            _step("audit", GATE_READER, "skipped", 0.0, number=6),
        ],
    )
    assert out["class"] == "AUDIT_FINISHED_BUT_NO_GATE"


def test_team_failure_precedes_any_audit_class():
    out = oe.classify(
        observation={"conclusion": "failure"},
        jobs={"team": "failure"},
        steps=[],
    )
    assert out["class"] == "TEAM_JOB_FAILED"
    assert out["producing_snapshot_survived"] is False


def test_missing_observation_is_unobservable_not_success():
    out = oe.classify(observation=None, jobs={}, steps=[])
    assert out["class"] == "UNOBSERVABLE"
    assert out["verdict_exists"] is False


def test_no_audit_job_at_all():
    out = oe.classify(
        observation={"conclusion": "success"},
        jobs={"team": "success", "integrate": "success"},
        steps=[_step("team", "Persist team snapshot", "success", 9.0)],
    )
    assert out["class"] == "NO_AUDIT_JOB"


def test_every_named_class_is_in_the_published_vocabulary():
    seen = {
        oe.classify(observation={"conclusion": c}, jobs=j, steps=s)["class"]
        for c, j, s in [
            ("cancelled", {"team": "success", "audit": "cancelled"},
             [_step("audit", AUDIT_AGENT, "cancelled", 3299.0)]),
            ("failure", {"team": "success", "audit": "failure"},
             [_step("audit", AUDIT_AGENT, "failure", 10.0)]),
            ("failure", {"team": "failure"}, []),
            ("success", {"team": "success"}, []),
            ("success", {"team": "success", "audit": "success"},
             [_step("audit", AUDIT_AGENT, "success", 1.0),
              _step("audit", GATE_READER, "success", 0.1)]),
        ]
    }
    assert seen <= set(oe.CLASSES), seen


# --------------------------------------------------------------------------
# quantum arithmetic — the load-bearing part of the diagnosis
# --------------------------------------------------------------------------

def test_a_cancelled_step_that_outran_the_quantum_was_not_stopped_by_the_watchdog():
    """3299 s > 2700 s and conclusion 'cancelled' ⇒ not rc-78.

    The wrapper polls every 15 s and returns 78 the moment the budget is spent,
    so a step that kept running past it cannot have been ended by the watchdog.
    """
    out = oe.quantum_analysis([_step("audit", AUDIT_AGENT, "cancelled", 3299.0)], 2700)
    assert out["duration_exceeded_quantum"] is True
    assert out["quantum_plausibly_fired"] is False


def test_a_cancelled_step_inside_the_quantum_leaves_the_cause_open():
    out = oe.quantum_analysis([_step("audit", AUDIT_AGENT, "cancelled", 600.0)], 2700)
    assert out["duration_exceeded_quantum"] is False
    assert out["quantum_plausibly_fired"] is None


def test_quantum_analysis_without_the_agent_step_says_so():
    out = oe.quantum_analysis([], 2700)
    assert out["agent_step_found"] is False
    assert out["quantum_plausibly_fired"] is None


def test_quantum_analysis_ignores_the_producer_step():
    """The producer runs the same wrapper; only the audit step is the subject."""
    out = oe.quantum_analysis(
        [_step("team", "Run lane cycle", "success", 1100.0),
         _step("audit", AUDIT_AGENT, "cancelled", 3299.0)],
        2700,
    )
    assert out["agent_step_duration_s"] == 3299.0


# --------------------------------------------------------------------------
# network-facing shell: never fatal, never a silent success
# --------------------------------------------------------------------------

def test_build_report_degrades_to_unobservable_when_the_api_is_unreachable(monkeypatch):
    def boom(*_a, **_k):
        raise RuntimeError("no network")

    monkeypatch.setattr(oe, "observe_run", boom)
    monkeypatch.setattr(oe, "_audit_branch_exists", lambda *a, **k: None)
    report = oe.build_report(39082232157)
    assert report["classification"]["class"] == "UNOBSERVABLE"
    assert report["classification"]["verdict_exists"] is False
    assert json.dumps(report)  # still serialisable


def test_build_report_never_fabricates_a_verdict_when_jobs_are_unreadable(monkeypatch):
    monkeypatch.setattr(oe, "observe_run", lambda *a, **k: {"run_id": 1, "conclusion": "success"})
    monkeypatch.setattr(oe, "observe_jobs", lambda *a, **k: {})
    monkeypatch.setattr(oe, "observe_steps", lambda *a, **k: [])
    monkeypatch.setattr(oe, "_audit_branch_exists", lambda *a, **k: None)
    report = oe.build_report(1)
    assert report["classification"]["class"] == "NO_AUDIT_JOB"
    assert report["classification"]["verdict_exists"] is False


def test_build_report_uses_injected_steps_without_touching_the_network(monkeypatch):
    monkeypatch.setattr(oe, "observe_run", lambda *a, **k: {
        "run_id": 39082232157, "conclusion": "cancelled"})
    monkeypatch.setattr(oe, "observe_jobs", lambda *a, **k: {
        "team": "success", "audit": "cancelled"})
    monkeypatch.setattr(oe, "_audit_branch_exists", lambda *a, **k: False)
    report = oe.build_report(
        39082232157,
        steps=[_step("audit", AUDIT_AGENT, "cancelled", 3299.0)],
    )
    assert report["classification"]["class"] == "AUDIT_STEP_CANCELLED_NO_GATE"
    assert report["audit_branch_exists"] is False
    assert report["quantum_analysis"]["duration_exceeded_quantum"] is True


def test_report_carries_a_claim_ceiling_that_excludes_product_and_gate_claims():
    source = Path(oe.__file__).read_text(encoding="utf-8")
    assert "observation of an external system's public REST job record" in source
    assert "NOT a product verdict" in source
    assert "control-plane scope" in source


# --------------------------------------------------------------------------
# the committed artifact
# --------------------------------------------------------------------------

ARTIFACT = ROOT / "results" / "product" / "orchestration" / "CYCLE_39082232157_orchestration.json"


@pytest.mark.skipif(not ARTIFACT.is_file(), reason="orchestration artifact not committed")
def test_committed_artifact_is_self_consistent():
    data = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    assert data["schema"] == oe.SCHEMA
    assert data["run_id"] == 39082232157
    assert data["classification"]["class"] == "AUDIT_STEP_CANCELLED_NO_GATE"
    # the three facts a reader must be able to check independently
    assert data["job_conclusions"]["team"] == "success"
    assert data["audit_branch_exists"] is False
    assert data["quantum_analysis"]["duration_exceeded_quantum"] is True
    assert data["classification"]["verdict_exists"] is False


@pytest.mark.skipif(not ARTIFACT.is_file(), reason="orchestration artifact not committed")
def test_committed_artifact_never_claims_a_product_or_human_gate_verdict():
    """This record decides how a run died. It must not decide anything about the
    product, and it must not look like an audit verdict to a reader or a tool."""
    data = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    assert "gate" not in data
    assert "safe_to_integrate" not in data
    assert "human_gate_ready" not in data
    assert "ready_for_owner_session" not in data
    assert data["classification"]["verdict_exists"] is False


def test_audit_branch_probe_targets_the_lane_scoped_branch(tmp_path, monkeypatch):
    """A wrong branch name would silently report 'no audit branch' forever."""
    calls = {}

    class _Result:
        returncode = 0
        stdout = ""

    def fake_run(cmd, **_k):
        calls["cmd"] = cmd
        return _Result()

    monkeypatch.setattr(subprocess, "run", fake_run)
    oe._audit_branch_exists(39082232157, "product", "Mickalive/LexMachina")
    assert "refs/heads/cycle/core/product/39082232157/audit" in calls["cmd"]

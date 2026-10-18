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


# --------------------------------------------------------------------------
# cause-space narrowing: public annotations + wrapper preflight replay
# (cycle 39087917357, diagnosis of run 39086926860)
# --------------------------------------------------------------------------

def _ann(job, conclusion, message, level="failure"):
    return {"job_id": 1, "job": job, "job_conclusion": conclusion,
            "annotation_level": level, "message": message}


def test_annotations_are_read_from_the_public_check_run_record(monkeypatch):
    """Job logs are admin-only; the check-run annotations are not.

    If this fetch silently returned [], every diagnosis below would degrade to
    "exit code unknown", which is the exact ambiguity this capability removes.
    """
    seen = []

    def fake_fetch(url):
        seen.append(url)
        if "/jobs" in url:
            return 200, {"jobs": [{"id": 42, "name": "audit", "conclusion": "failure"}]}
        return 200, [{"annotation_level": "failure",
                      "message": "Process completed with exit code 1."}]

    rows = oe.observe_annotations(39086926860, fetch=fake_fetch)
    assert len(rows) == 1
    assert rows[0]["job"] == "audit"
    assert any("check-runs/42/annotations" in u for u in seen)


def test_observe_annotations_is_never_fatal(monkeypatch):
    def boom(_url):
        raise RuntimeError("no network")

    assert oe.observe_annotations(1, fetch=boom) == []
    assert oe.observe_annotations(1, fetch=lambda _u: (500, {})) == []


def test_exit_code_is_taken_only_from_a_failing_job():
    """A skipped gate-reader job annotating code 0 must not mask the real code."""
    anns = [_ann("audit", "failure", "Process completed with exit code 1."),
            _ann("resilience", "success", "Process completed with exit code 0.",
                 level="notice")]
    assert oe.parse_exit_code(anns) == {
        "exit_code": 1,
        "evidence": "audit job annotation: 'Process completed with exit code 1'"}


def test_absent_exit_code_is_unknown_and_never_zero():
    parsed = oe.parse_exit_code([_ann("audit", "failure", "something else")])
    assert parsed["exit_code"] is None
    assert "no annotation" in parsed["evidence"]


def test_quantum_exit_is_ruled_out_by_arithmetic_not_by_narrative():
    """A 16 s step cannot have been stopped by a 2700 s watchdog."""
    res = oe.wrapper_exit_candidates(78, step_duration_s=16.0, quantum_s=2700,
                                     retry={"max_attempts": 8, "retry_delay_s": 90})
    quantum = next(c for c in res["named_branches"] if c["rc"] == 78)
    assert quantum["ruled_out"] is True
    assert any("2700" in e for e in quantum["ruled_out_evidence"])


def test_quantum_exit_survives_when_the_step_actually_outran_the_budget():
    res = oe.wrapper_exit_candidates(78, step_duration_s=3299.0, quantum_s=2700,
                                     retry={"max_attempts": 8, "retry_delay_s": 90})
    quantum = next(c for c in res["named_branches"] if c["rc"] == 78)
    assert quantum["ruled_out"] is False


def test_retry_exhaustion_is_ruled_out_when_one_attempt_cannot_have_finished():
    """One retry attempt needs a 90 s sleep; a 16 s step cannot contain one."""
    res = oe.wrapper_exit_candidates(75, step_duration_s=16.0, quantum_s=2700,
                                     retry={"max_attempts": 8, "retry_delay_s": 90})
    retry = next(c for c in res["named_branches"] if c["rc"] == 75)
    assert retry["ruled_out"] is True
    assert any("retry delay" in e for e in retry["ruled_out_evidence"])


def test_rc_1_rules_out_every_named_wrapper_exit_and_names_the_passthrough():
    """Exit 1 is not one of the wrapper's own codes: that is the finding."""
    res = oe.wrapper_exit_candidates(1, step_duration_s=16.0, quantum_s=2700,
                                     retry={"max_attempts": 8, "retry_delay_s": 90})
    assert res["surviving_named_branches"] == []
    assert res["generic_passthrough_possible"] is True
    assert "without transient signature" in res["generic_passthrough_note"]


def test_an_unknown_exit_code_never_rules_anything_out():
    res = oe.wrapper_exit_candidates(None, step_duration_s=None, quantum_s=2700)
    assert res["exit_code"] is None
    assert all(c["ruled_out"] for c in res["named_branches"])  # "no exit code observed"
    assert res["generic_passthrough_possible"] is False


def test_preflight_replay_reproduces_a_card_count_mismatch(tmp_path):
    """validate_registry is the only way to get exit 64/66 before opencode runs."""
    control = tmp_path / "control"
    (control / "docs" / "agents").mkdir(parents=True)
    (control / "docs" / "agents" / "AGENT_CARDS.md").write_text(
        "<!-- AGENT_CARD: independent_auditor status=ACTIVE_AUDITOR lane=ALL -->\n"
        "<!-- AGENT_CARD: product_engineer status=ACTIVE lane=product -->\n"
        "<!-- AGENT_CARD: product_engineer status=ACTIVE lane=product -->\n",
        encoding="utf-8")
    agents = tmp_path / "agents"
    agents.mkdir()
    (agents / "independent_auditor.md").write_text("x", encoding="utf-8")
    (agents / "product_engineer.md").write_text("x", encoding="utf-8")

    res = oe.replay_wrapper_preflight(control, agents)
    assert res["registry"]["pass"] is False
    assert res["would_exit"] == 66
    assert res["all_pass"] is False


def test_preflight_replay_reproduces_an_unusable_model_health(tmp_path):
    control = tmp_path / "control"
    (control / "docs" / "agents").mkdir(parents=True)
    (control / "docs" / "agents" / "AGENT_CARDS.md").write_text(
        "<!-- AGENT_CARD: independent_auditor status=ACTIVE lane=ALL -->\n",
        encoding="utf-8")
    (control / "state").mkdir()
    (control / "state" / "model_health.json").write_text(
        json.dumps({"healthy": False, "resolved_model": ""}), encoding="utf-8")
    agents = tmp_path / "agents"
    agents.mkdir()
    (agents / "independent_auditor.md").write_text("x", encoding="utf-8")

    res = oe.replay_wrapper_preflight(control, agents)
    assert res["model_health"]["pass"] is False
    assert "LEX_NO_HEALTHY_FREE_TOOL_MODEL" in " ".join(res["model_health"]["problems"])
    assert res["would_exit"] == 76


def test_preflight_replay_passes_on_a_complete_fixture(tmp_path):
    control = tmp_path / "control"
    (control / "docs" / "agents").mkdir(parents=True)
    (control / "docs" / "agents" / "AGENT_CARDS.md").write_text(
        "<!-- AGENT_CARD: independent_auditor status=ACTIVE lane=ALL -->\n",
        encoding="utf-8")
    (control / "state").mkdir()
    (control / "state" / "model_health.json").write_text(
        json.dumps({"healthy": True, "resolved_model": "opencode/x"}), encoding="utf-8")
    agents = tmp_path / "agents"
    agents.mkdir()
    (agents / "independent_auditor.md").write_text("x", encoding="utf-8")

    res = oe.replay_wrapper_preflight(control, agents)
    assert res["all_pass"] is True and res["would_exit"] is None


def test_diagnosis_rules_out_preflight_exits_only_when_the_replay_passes():
    control = Path(__file__).resolve().parents[2]
    control_plane = oe.default_control_dir()
    pre = oe.replay_wrapper_preflight(control_plane, control / ".opencode" / "agents")
    anns = [_ann("audit", "failure", "Process completed with exit code 1.")]
    diag = oe.diagnose(annotations=anns,
                       steps=[_step("audit", AUDIT_AGENT, "failure", 16.0)],
                       quantum_s=2700, preflight=pre, annotations_collected=True)
    assert diag["exit_code"] == 1
    assert diag["audit_agent_step_duration_s"] == 16.0
    if pre["all_pass"]:
        for rc in (64, 65, 66, 76, 77):
            cand = next(c for c in diag["candidates"]["named_branches"] if c["rc"] == rc)
            assert cand["ruled_out"] is True, rc
            assert any("preflight" in e for e in cand["ruled_out_evidence"])
    assert diag["candidates"]["claim_ceiling"].startswith("This narrows")


def test_diagnosis_marks_uncollected_annotations_as_uncollected_not_as_zero():
    diag = oe.diagnose(annotations=[], steps=[], quantum_s=2700,
                       preflight={"all_pass": True, "would_exit": None},
                       annotations_collected=False)
    assert diag["annotations_collected"] is False
    assert diag["exit_code"] is None
    assert "not collected" in diag["exit_code_evidence"]


def test_diagnosis_never_claims_an_innermost_cause():
    """The lane still cannot read job logs; the ceiling must say so."""
    source = Path(oe.__file__).read_text(encoding="utf-8")
    assert "job logs stay admin-only" in source
    assert "does not name opencode's internal error" in source


def test_wrapper_script_sources_distinguishes_a_real_read_from_the_fallback(tmp_path):
    """'Read from the wrapper' is only honest when the wrapper actually says it."""
    modern = tmp_path / "modern" / ".github" / "scripts"
    modern.mkdir(parents=True)
    (modern / "run-ox-with-retry.sh").write_text(
        'WORK_QUANTUM_SECONDS="${LEX_AGENT_QUANTUM_SECONDS:-2700}"\n'
        'MAX_ATTEMPTS="${OX_MAX_ATTEMPTS:-8}"\n', encoding="utf-8")
    src = oe.wrapper_script_sources(tmp_path / "modern")
    assert src["quantum_source"] == "script" and src["retry_source"] == "script"

    stale = tmp_path / "stale" / ".github" / "scripts"
    stale.mkdir(parents=True)
    (stale / "run-ox-with-retry.sh").write_text(
        'MAX_ATTEMPTS="${OX_MAX_ATTEMPTS:-8}"\n', encoding="utf-8")
    src = oe.wrapper_script_sources(tmp_path / "stale")
    assert src["quantum_source"].startswith("default_fallback")
    assert "origin/main" in src["quantum_source"]
    assert src["retry_source"] == "script"

    src = oe.wrapper_script_sources(tmp_path / "nothing")
    assert src["present"] is False

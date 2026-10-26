"""Repair of rejected product cycle 40267501346 (round 1).

The independent audit of producer run 40267501346 (gate file
``results/audit/product/CYCLE_40267501346_GATE.json``) returned REVISE with
exactly two required fixes:

* **R1 run-id attribution** - ``state/product.json`` and the producer report
  named the *resumed* run 40263666190 as the current cycle instead of the
  executing run, breaking the accepted convention (executing run is
  ``Run``/``current_cycle_run_id``; the resumed snapshot lives in a Mode line
  and a ``cycle_<executing_run>_*`` block) and leaving the state's current
  pointer on a run whose own block is UNADJUDICATED with no accept commit.
* **R2 false quantum sentence** - ``query_env.ENSURE_REASON`` (published in
  every ``ensure()`` result block's ``reason`` field), the conftest docstring,
  the 40263666190 cycle-test docstring and the ``audit_readiness`` profile
  ``mechanism_chain_note`` all claimed run 40262401687 "burned its whole
  (work) quantum", contradicted by the cycle's own committed evidence: the
  agent hit the fresh-runner dependency failures and exited 0 with an
  unchanged tree after ~526 s (03:08:06Z -> 03:16:52Z), so the *wrapper's*
  delta guard rejected it (``##[error]LEX_ZERO_DELTA_REPAIR``, exit 67;
  ``quantum_expired=false``; no ``LEX_WORK_QUANTUM_EXPIRED`` annotation of its
  own - the single log hit is agent-quoted history the parser separates).

This test locks both repairs fail-closed:

* every published mechanism string states the observed delta-guard fact and
  none of them asserts a quantum expiry for 40262401687;
* the prose is cross-checked against the committed log-evidence artifact and
  the committed raw step timestamps (526 s of a 2700 s quantum);
* the state's current pointer is the executing repair run 40269774540, whose
  block records the rejected cycle, its REVISE audit and the discharged fixes;
* the resumed chain stays recorded as history; posture stays fail-closed.
"""
import json
import re
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

EXECUTING_RUN_ID = "40269774540"
REPAIRED_RUN_ID = "40267501346"
RESUMED_RUN_ID = "40263666190"
FIRST_ATTEMPT = "40262401687"

ORCH = ROOT / "results" / "product" / "orchestration"
LOG_EVIDENCE = ORCH / f"CYCLE_{RESUMED_RUN_ID}_lane_cycle_log_evidence.json"
RAW_FIRST = ORCH / f"CYCLE_{FIRST_ATTEMPT}_team_step_raw.json"
# Product-owned, sha256-pinned copy of the auditor's REVISE gate (the
# authoritative file lives on the audit branch; producers never write
# results/audit/**).
GATE = ORCH / f"CYCLE_{REPAIRED_RUN_ID}_REJECTED_GATE.json"
STATE = ROOT / "state" / "product.json"
CURRENT_REPORT = ROOT / "reports" / "product" / f"CYCLE_{EXECUTING_RUN_ID}.md"

#: The four audited prose locations plus the query_env module docstring; every
#: one must state the delta-guard fact and none may claim a quantum burn.
PROSE_FILES = (
    ROOT / "product" / "query_env.py",
    ROOT / "product" / "tests" / "conftest.py",
    ROOT / "product" / "tests" / f"test_cycle_{RESUMED_RUN_ID}_resume.py",
    ROOT / "product" / "audit_readiness.py",
)

QUANTUM_BURN_PATTERN = re.compile(
    r"burned\s+its\s+whole\s+(work\s+)?quantum", re.MULTILINE)


def _load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def test_published_prose_states_delta_guard_fact_not_quantum_expiry():
    """R2: no location may claim a work-quantum burn for 40262401687."""
    for path in PROSE_FILES:
        text = path.read_text(encoding="utf-8")
        m = QUANTUM_BURN_PATTERN.search(text)
        assert m is None, f"false quantum-burn claim in {path}: {m and m.group(0)!r}"
        # Every location that names the run ties it to the observed guard.
        if FIRST_ATTEMPT in text:
            assert "quantum_expired=false" in text or (
                "quantum_expired=false" in text.replace("`", "")), path
            assert "LEX_ZERO_DELTA_REPAIR" in text, path


def test_ensure_reason_matches_committed_log_evidence():
    """The reason string must not contradict the machine evidence."""
    from product import query_env

    ev = _load(LOG_EVIDENCE)
    first = ev["runs"][FIRST_ATTEMPT]
    assert first["classification"] == "AGENT_FINISHED_ZERO_DURABLE_DELTA"
    assert first["exit_codes"] == [67]
    assert first["markers"]["quantum_expired"] is False
    assert "LEX_WORK_QUANTUM_EXPIRED" in (
        first["markers"]["markers_quoted_from_history_only"])
    assert "LEX_ZERO_DELTA_REPAIR" in first["markers"]["annotation_error_lines"]

    reason = query_env.ENSURE_REASON
    assert "quantum_expired=false" in reason
    assert "LEX_ZERO_DELTA_REPAIR" in reason
    assert "exit 67" in reason
    assert QUANTUM_BURN_PATTERN.search(reason) is None


def test_first_attempt_step_duration_is_within_quantum():
    """526 s of a 2700 s quantum, from the committed raw timestamps."""
    snap = _load(RAW_FIRST)
    assert snap["run"]["id"] == int(FIRST_ATTEMPT)
    step = next(s for j in snap["jobs"] if j["name"] == "team"
                for s in j["steps"] if s["name"] == "Run lane cycle")
    started = datetime.fromisoformat(step["started_at"].replace("Z", "+00:00"))
    completed = datetime.fromisoformat(
        step["completed_at"].replace("Z", "+00:00"))
    elapsed = (completed - started).total_seconds()
    assert elapsed == 526.0
    assert elapsed < 2700, "the agent's own step never reached the quantum"


def test_rejected_audit_gate_records_exactly_two_required_fixes():
    """The vendored copy must be the auditor's gate, byte-pinned by sha256."""
    rec = _load(GATE)
    assert rec["schema"] == "product-vendored-rejected-gate/1"
    assert rec["source_ref"] == "origin/cycle/core/product/40267501346/audit"
    assert rec["source_path"] == (
        "results/audit/product/CYCLE_40267501346_GATE.json")
    assert rec["source_sha256"] == (
        "c58d25d446fe824135b7924f0bcfad616ebb9554e55d99ca4802aa33856431ae")
    gate = rec["gate_content"]
    assert gate["gate"] == "REVISE"
    assert gate["safe_to_integrate"] is False
    fixes = gate["required_fixes"]
    assert len(fixes) == 2
    joined = " ".join(fixes)
    assert "40267501346" in joined
    assert "quantum" in joined.lower()


def test_state_current_pointer_is_the_executing_repair_run():
    """R1: the accept commit will name the executing run; so must the state.

    POINTER-PIN AMENDMENT (product cycle 40272586794), following the
    amendment recorded in ``test_cycle_40154120551.py``: later accepted
    cycles legitimately advance ``current_cycle_run_id`` past this cycle's
    era, so pinning the pointer to 40269774540 breaks once the world moves
    (exactly as ``test_cycle_40259640985_resume.py``'s pin did).  The
    surviving claims are strengthened, not weakened:

    * the pointer never REGRESSES below this cycle's executing run
      (monotonic, so a stale or hand-rolled-back state fails);
    * this cycle's repair block, its REVISE audit record and the fail-closed
      posture all survive in ``state/product.json`` verbatim - that is the
      durable content of R1, which is what the original equality was a
      proxy for.
    """
    state = _load(STATE)
    assert state["current_cycle_run_id"] >= int(EXECUTING_RUN_ID), (
        "current_cycle_run_id regressed below this cycle's executing run",
        state["current_cycle_run_id"], EXECUTING_RUN_ID)

    block = state[f"cycle_{EXECUTING_RUN_ID}_repair_of_{REPAIRED_RUN_ID}"]
    assert block["run_id"] == int(EXECUTING_RUN_ID)
    assert block["repaired_run_id"] == int(REPAIRED_RUN_ID)
    assert block["rejected_audit"]["gate"] == "REVISE"
    assert block["rejected_audit"]["required_fixes_count"] == 2
    assert block["resumed_chain"] == [int(RESUMED_RUN_ID), 40263483436,
                                      40263308953, int(FIRST_ATTEMPT)]
    assert set(block["required_fixes_discharged"]) == {
        "R1_run_id_attribution", "R2_false_quantum_sentence"}
    assert block["posture"] == {
        "human_gate_ready": False,
        "machine_gate_ready": False,
        "packet_admitted": False,
        "ready_for_owner_session": False,
        "continue_recommended": True,
    }

    # History stays: the resumed block is preserved, not deleted or rewritten.
    history = state[f"cycle_{RESUMED_RUN_ID}_operational_resume"]
    assert history["snapshot_run_id"] == 40263483436
    assert history["adjudication"]["status"] == "UNADJUDICATED"

    assert state["direction_version"] == 68
    assert state["continue_recommended"] is True
    assert state["human_gate_ready"] is False


def test_report_of_record_names_executing_run_and_repaired_cycle():
    report = CURRENT_REPORT.read_text(encoding="utf-8")
    assert f"Run:** {EXECUTING_RUN_ID}" in report
    assert REPAIRED_RUN_ID in report
    assert "REVISE" in report
    assert "R1" in report and "R2" in report
    assert "quantum_expired=false" in report
    assert "ghs_" not in report

"""Regression locks for operational resume 43576640503 -> 43583276284.

These tests are the producer-side regression gate for run 43583276284.  They
lock the five preregistered hypotheses in
``evaluation/OPERATIONAL_RESUME_43576640503_HYPOTHESIS_V1.json`` and the pins in
the sibling freeze record.  They must not be weakened to make a run pass; a
genuine failure is evidence, not a nuisance.

Historical-lock note
--------------------
``test_state_discloses_pending_audit_and_keeps_accepted_run`` asserts
``github_run == 43583276284``.  When the *next* cycle advances the pointer this
file will fail by design, exactly as
``tests/evaluation/test_operational_resume_43570632816.py`` fails today.  That
is the established convention and the file is preserved unmodified.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
STATE_PATH = REPO_ROOT / "state/evaluation.json"
LANE_STATE_PATH = REPO_ROOT / "evaluation/state/evaluation.json"
PACK_DIR = REPO_ROOT / "results/evaluation/operational_resume_43576640503"

FREEZE_PATH = REPO_ROOT / "evaluation/OPERATIONAL_RESUME_43576640503_FREEZE_V1.json"
HYP_PATH = REPO_ROOT / "evaluation/OPERATIONAL_RESUME_43576640503_HYPOTHESIS_V1.json"

RUN_ID = "43583276284"
RESUMED = "43576640503"
DIRV = 68
ACCEPTED_RUN_ID = 40265377500
RESUMED_HEAD = "a965bd8bc53c84d48ee16b0087b37899e8acad84"


def _load(path: Path):
    return json.loads(path.read_text())


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# ------------------------------------------------------------------ identity


def test_constants_identify_this_resume():
    freeze = _load(FREEZE_PATH)
    hyp = _load(HYP_PATH)
    assert freeze["run_id"] == RUN_ID
    assert freeze["resumed_run_id"] == RESUMED
    assert freeze["direction_version"] == DIRV
    assert freeze["accepted_run_id"] == ACCEPTED_RUN_ID
    assert hyp["run_id"] == RUN_ID
    assert hyp["resumed_run_id"] == RESUMED
    assert hyp["direction_version"] == DIRV
    assert hyp["freeze_sha256"] == _sha(FREEZE_PATH)


def test_freeze_is_recorded_before_formal_evidence():
    freeze = _load(FREEZE_PATH)
    hyp = _load(HYP_PATH)
    assert freeze["freeze_before_formal_evidence"] is True
    assert freeze["formal_evidence_started_after_freeze"] is True
    assert hyp["recorded_before_formal_evidence"] is True
    assert hyp["formal_evidence_started"] is False


def test_freeze_pins_still_match():
    freeze = _load(FREEZE_PATH)
    pins = freeze["pins"]
    assert len(pins) >= 30
    for rel, want in pins.items():
        path = REPO_ROOT / rel
        assert path.is_file(), f"pinned file missing: {rel}"
        assert _sha(path) == want, f"pin drift: {rel}"


def test_state_hash_before_recorded_and_state_advanced_coherently():
    freeze = _load(FREEZE_PATH)
    root = _load(STATE_PATH)
    # The pre-change hashes are recorded; the files themselves have advanced.
    assert set(freeze["state_hash_before"]) == {
        "state/evaluation.json", "evaluation/state/evaluation.json"
    }
    assert root["github_run"] == int(RUN_ID)


# ---------------------------------------------------------------------- H1


def test_resumed_failure_is_audit_quantum_not_team_or_zero_delta():
    diag = _load(PACK_DIR / f"diagnosis_{RESUMED}.json")
    sig = diag["signature"]
    assert diag["failure_class"] == "AUDIT_WORK_QUANTUM_EXPIRED_RC78"
    assert sig["run_conclusion"] == "failure"
    assert sig["team_conclusion"] == "success"
    assert sig["audit_conclusion"] == "failure"
    assert sig["failing_step"] == "Independent audit"
    assert 2700 <= sig["audit_step_duration_s"] <= 2735
    assert sig["exit_78"] is True
    assert sig["quantum_2700"] is True
    assert sig["audit_gate_step"] == "skipped"
    assert sig["audit_persist_step"] == "skipped"
    assert sig["integrate_conclusion"] == "skipped"
    assert diag["not_a_producer_rejection"] is True
    assert diag["not_a_team_launch_failure"] is True
    assert diag["not_a_zero_delta_repair"] is True


def test_diagnosis_evidence_files_resolve_and_carry_the_signature():
    diag = _load(PACK_DIR / f"diagnosis_{RESUMED}.json")
    for rel in diag["signature"]["evidence_files"]:
        assert (REPO_ROOT / rel).is_file(), rel
    ann = _load(PACK_DIR / "api" / "annotations_43576640503_audit.json")
    msgs = [a["message"] for a in ann["annotations"]]
    assert any("exit code 78" in m for m in msgs)
    assert any("LEX_WORK_QUANTUM_EXPIRED seconds=2700" in m for m in msgs)


def test_diagnosis_counts_the_seventh_consecutive_occurrence():
    diag = _load(PACK_DIR / f"diagnosis_{RESUMED}.json")
    assert diag["consecutive_occurrence_index"] == 7
    assert diag["prior_starved_audits_count"] == 6
    prior = _load(
        REPO_ROOT / "results/evaluation/operational_resume_43570757974"
        / f"diagnosis_{PRIOR := '43570757974'}.json"
    )
    assert len(prior["historical_starved_audits"]) == 5


# ---------------------------------------------------------------------- H2


def _paths_touched_since_resumed_snapshot() -> list[str]:
    """Every path this run added or modified relative to the resumed snapshot.

    Works both before persist (uncommitted working tree) and after the workflow
    commits the team snapshot (committed delta), so the auditor and the producer
    see the same answer.
    """
    import subprocess
    paths: list[str] = []
    out = subprocess.check_output(
        ["git", "status", "--porcelain", "-uall"], cwd=REPO_ROOT, text=True
    )
    paths += [ln[3:].strip() for ln in out.splitlines() if ln.strip()]
    head = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, text=True
    ).strip()
    if head != RESUMED_HEAD:
        diff = subprocess.check_output(
            ["git", "diff", "--name-only", f"{RESUMED_HEAD}..HEAD"],
            cwd=REPO_ROOT, text=True,
        )
        paths += [ln.strip() for ln in diff.splitlines() if ln.strip()]
    # de-duplicate, keep order
    seen, ordered = set(), []
    for p in paths:
        if p and p not in seen:
            seen.add(p)
            ordered.append(p)
    return ordered


def test_resumed_snapshot_is_the_ancestor_this_run_built_on():
    freeze = _load(FREEZE_PATH)
    assert freeze["resumed_snapshot_head"] == RESUMED_HEAD
    import subprocess
    rc = subprocess.run(
        ["git", "merge-base", "--is-ancestor", RESUMED_HEAD, "HEAD"],
        cwd=REPO_ROOT,
    ).returncode
    assert rc == 0, "resumed snapshot a965bd8b is not an ancestor of HEAD"


def test_no_audit_namespace_written_by_this_producer():
    touched = _paths_touched_since_resumed_snapshot()
    bad = [
        p for p in touched
        if p.startswith(("results/audit/", "reports/audit/"))
    ]
    assert bad == [], f"producer wrote audit namespace: {bad}"


# ---------------------------------------------------------------------- H3


def test_deliverable_is_product_falsified_and_hash_frozen():
    freeze = _load(FREEZE_PATH)
    deliv = REPO_ROOT / "results/evaluation/smallest_ca_benchmark/43554928192.json"
    want = freeze["pins"][str(deliv.relative_to(REPO_ROOT))]
    assert _sha(deliv) == want
    data = _load(deliv)
    assert data["verdict"] == "PRODUCT_FALSIFIED"
    assert data["packet"] == "39319405429"
    assert data["direction_version"] == DIRV
    assert data["n_questions"] == 3


def test_verification_records_hold():
    tests = _load(PACK_DIR / f"verification_tests_{RUN_ID}.json")
    assert tests["all_expected_green"] is True
    by_file = {s["file"]: s for s in tests["suites"]}
    for name in (
        "test_counter_authority_falsify_v68.py",
        "test_minimal_ca_falsify_benchmark.py",
        "test_minimal_retrieval_ca_benchmark.py",
        "test_operational_resume_43570757974.py",
    ):
        assert by_file[name]["failed"] == 0, name
        assert by_file[name]["errors"] == 0, name
    # The prior-prior resume test is a documented historical lock: exactly 2 fails.
    lock = by_file["test_operational_resume_43570632816.py"]
    assert lock["failed"] == 2

    deliv = _load(PACK_DIR / f"verification_deliverable_{RUN_ID}.json")
    assert deliv["all_hold"] is True
    for cmp_ in deliv["pin_comparisons"]:
        assert cmp_["match"] is True, cmp_


# ---------------------------------------------------------------------- H4


def test_accepted_gate_and_standing_records_intact():
    gate = _load(REPO_ROOT / "results/audit/evaluation/CYCLE_40265377500_GATE.json")
    assert gate["gate"] == "PASS"
    assert gate["safe_to_integrate"] is True
    root = _load(STATE_PATH)
    assert root["accepted_run_id"] == ACCEPTED_RUN_ID
    assert root["direction_version"] == DIRV


def test_ordered_item_two_stays_not_yet_discriminating():
    # No family re-measure is executed in this operational cycle.
    hyp = _load(HYP_PATH)
    assert "no new same-question family re-measure" in " ".join(hyp["claims_not_made"])
    assert "NOT_YET_DISCRIMINATING" in hyp["claim_ceiling"]


# ---------------------------------------------------------------------- H5


def test_state_discloses_pending_audit_and_keeps_accepted_run():
    state = _load(STATE_PATH)
    lane = _load(LANE_STATE_PATH)
    block = state[f"operational_resume_{RESUMED}"]
    assert state["github_run"] == int(RUN_ID)
    assert lane["github_run"] == int(RUN_ID)
    assert state["accepted_run_id"] == ACCEPTED_RUN_ID
    assert lane["accepted_run_id"] == ACCEPTED_RUN_ID
    assert state["audit_status"] == "PENDING_INDEPENDENT_AUDIT"
    assert lane["audit_status"] == "PENDING_INDEPENDENT_AUDIT"
    assert block["resumed_run_id"] == RESUMED
    assert block["run_id"] == RUN_ID
    assert block["audit_status"] == "PENDING_INDEPENDENT_AUDIT"
    assert len(state["evidence_refs"]) <= 40
    assert len(lane["evidence_refs"]) <= 40
    for rel in state["evidence_refs"] + lane["evidence_refs"]:
        assert (REPO_ROOT / rel).is_file(), rel


def test_github_run_advance_is_disclosed_additively():
    state = _load(STATE_PATH)
    adv = state[f"github_run_advance_{RUN_ID}"]
    assert adv["from"] == int(RESUMED)
    assert adv["to"] == int(RUN_ID)
    assert adv["resumed_run_id"] == int(RESUMED)
    # The prior advance block is preserved, not overwritten.
    assert state[f"github_run_advance_{RESUMED}"]["to"] == int(RESUMED)


def test_audit_index_is_compact_and_resolvable():
    idx = _load(PACK_DIR / "AUDIT_INDEX.json")
    assert idx["status"] == "PRODUCER_SNAPSHOT_READY_FOR_INDEPENDENT_AUDIT"
    rows = idx["primary_evidence"]
    assert 0 < len(rows) <= 40
    for row in rows:
        assert (REPO_ROOT / row["path"]).is_file(), row["path"]


def test_audit_brief_names_a_sub_minute_fast_path():
    brief = (REPO_ROOT / f"reports/evaluation/AUDIT_BRIEF_{RUN_ID}.md").read_text()
    assert f"operational_resume_{RESUMED} --phase verify" in brief
    assert "2700" in brief
    assert "Do NOT" in brief or "do NOT" in brief


def test_instrument_exposes_read_only_verify_phase():
    import subprocess
    import sys
    proc = subprocess.run(
        [sys.executable, "-m", f"evaluation.operational_resume_{RESUMED}",
         "--phase", "verify"],
        cwd=REPO_ROOT, capture_output=True, text=True, timeout=60,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    rec = json.loads(proc.stdout)
    assert rec["writes"] == 0
    assert rec["all_hold"] is True
    assert rec["runtime_s"] < 60
    assert all(rec["checks"].values()), [
        k for k, v in rec["checks"].items() if not v
    ]


def test_negative_controls_are_recorded_and_fire():
    import subprocess
    import sys
    proc = subprocess.run(
        [sys.executable, "-m", f"evaluation.operational_resume_{RESUMED}",
         "--phase", "audit"],
        cwd=REPO_ROOT, capture_output=True, text=True, timeout=60,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    rec = json.loads(proc.stdout)
    assert rec["negative_controls"]["all_hold"] is True
    assert rec["recommendation"] == "PASS"
    assert rec["writes"] == 0

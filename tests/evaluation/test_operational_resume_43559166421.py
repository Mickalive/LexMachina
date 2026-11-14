"""Regression locks for operational resume 43559166421 -> 43565032175.

Plain functions only: the producer image has no pytest, so these are executed by
``evaluation.no_pytest_runner``.  They assert the frozen snapshot facts, not a
new product claim.
"""

import json
from pathlib import Path

from evaluation.operational_resume_43559166421 import (
    ACCEPTED_RUN_ID,
    API_DIR,
    DELIVERABLE,
    DIRV,
    FAMILY_GATE,
    FREEZE,
    HYPOTHESIS,
    PACK_DIR,
    PRIOR_PARENT,
    RESUMED,
    RUN_ID,
    SNAPSHOT_HEAD,
    STATE_PATH,
)

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha(path: Path) -> str:
    import hashlib
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_constants_identify_this_resume():
    assert RUN_ID == "43565032175"
    assert RESUMED == "43559166421"
    assert SNAPSHOT_HEAD == "c40cd9288bbcab02a5489bd768e2a329f4dea218"
    assert PRIOR_PARENT == "35d8d64941b76ab59f931915f1f59ac97e07041f"
    assert DIRV == 68
    assert ACCEPTED_RUN_ID == 40265377500


def test_freeze_pins_still_match():
    freeze = _load(FREEZE)
    assert freeze["freeze_before_execution"] is True
    pins = freeze["pins"]
    assert len(pins) >= 25
    bad = [rel for rel, want in pins.items()
           if _sha(REPO_ROOT / rel) != want]
    assert bad == [], f"pins drifted: {bad}"


def test_hypothesis_is_preregistered_and_five_way():
    hyp = _load(HYPOTHESIS)
    assert hyp["freeze_before_execution"] is True
    ids = [h["id"] for h in hyp["hypotheses"]]
    assert ids == ["H1", "H2", "H3", "H4", "H5"]
    assert hyp["pre_freeze_disclosure"]["exploratory_probes_ran_before_this_freeze"] is True


def test_resumed_audit_starvation_is_exit_78_at_2700s():
    run = _load(API_DIR / f"run_{RESUMED}.json")
    jobs = {j["name"]: j for j in _load(API_DIR / f"jobs_{RESUMED}.json")["jobs"]}
    ann = _load(API_DIR / f"annotations_{RESUMED}_audit.json")["annotations"]
    msgs = [a["msg"] for a in ann]
    assert run["conclusion"] == "failure"
    assert jobs["team"]["conclusion"] == "success"
    assert jobs["audit"]["conclusion"] == "failure"
    assert jobs["integrate"]["conclusion"] == "skipped"
    assert any("exit code 78" in m for m in msgs)
    assert any("LEX_WORK_QUANTUM_EXPIRED seconds=2700" in m for m in msgs)
    assert not (REPO_ROOT / "results/audit/evaluation"
                / f"CYCLE_{RESUMED}_GATE.json").exists()


def test_snapshot_delta_is_62_files_with_zero_audit_namespace():
    import subprocess
    out = subprocess.run(
        ["git", "diff", "--name-only", PRIOR_PARENT, SNAPSHOT_HEAD],
        cwd=REPO_ROOT, capture_output=True, text=True, check=True).stdout
    delta = [ln for ln in out.splitlines() if ln.strip()]
    assert len(delta) == 62
    assert [p for p in delta if p.startswith("results/audit/evaluation/")
            or p.startswith("reports/audit/evaluation/")] == []


def test_deliverable_is_product_falsified_with_zero_issued_rows():
    rec = _load(DELIVERABLE)
    assert rec["verdict"] == "PRODUCT_FALSIFIED"
    assert rec["exit_code"] == 1
    assert rec["packet"] == "39319405429"
    assert rec["direction_version"] == 68
    assert rec["n_questions"] == 3
    issued = sum(r["counter_authority"]["n_issued"] for r in rec["results"])
    assert issued == 0


def test_family_gate_stays_not_yet_discriminating():
    gate = _load(FAMILY_GATE)
    assert gate["status"] == "NOT_YET_DISCRIMINATING"
    assert gate["zero_delta_check"]["already_measured_since_evaluation_run"] is True
    assert gate["zero_delta_check"]["byte_identical_n"] == 50
    card = gate["role_cardinality"]
    assert card["role_parity"] is False
    assert card["member_for_member_ceiling"] == 14
    assert card["frozen_family_n"] == 15
    assert gate["product"]["head"].startswith("7be4480e")


def test_state_discloses_pending_audit_and_keeps_accepted_run():
    state = _load(STATE_PATH)
    block = state[f"operational_resume_{RESUMED}"]
    assert state["github_run"] == int(RUN_ID)
    assert state["accepted_run_id"] == ACCEPTED_RUN_ID
    assert state["audit_status"] == "PENDING_INDEPENDENT_AUDIT"
    assert state["continue_recommended"] is False
    assert block["audit_status"] == "PENDING_INDEPENDENT_AUDIT"
    assert block["accepted_as_evidence"] is False


def test_prior_snapshot_artifacts_are_byte_pinned():
    expected = {
        "results/evaluation/operational_resume_43554928192/summary_43559166421.json":
            "88e202a46a5d4ef71bed66c5c30fdcda3454c65cfa21beadf5b8ef2b72c9a609",
        "results/evaluation/smallest_ca_benchmark/43554928192.json":
            "7bc9c5514ddc888cfdd12b5d96dae6fa7497c27f6347b6a899492b40a0fdecde",
        "results/evaluation/bypass_clause_correction/40144816305.json":
            "2e691dd02c7b53bac7b1bf048363e56006a1596dd3cade1fd4fb44514330228d",
    }
    for rel, want in expected.items():
        assert _sha(REPO_ROOT / rel) == want


def test_instrument_exposes_read_only_verify_phase():
    src = (REPO_ROOT / "evaluation" / f"operational_resume_{RESUMED}.py").read_text(
        encoding="utf-8")
    assert '"verify"' in src
    assert "def verify_fast" in src
    assert "writes" in src and '"writes": 0' in src

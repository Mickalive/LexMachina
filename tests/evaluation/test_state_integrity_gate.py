"""State-integrity gate: negative controls + committed-tree before/after.

Every test is a plain no-parameter function so it runs under real pytest AND
under ``evaluation/no_pytest_runner.py`` (the producer image has no pytest).
The negative controls prove each frozen check bites on a synthetic defect of
the exact class audit CYCLE_39751745107 named; the committed-tree test is the
before/after probe (red on the rejected cycle's states, green after the
required fixes land).
"""
from __future__ import annotations

import copy
import json
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]

from evaluation.state_integrity_gate import (  # noqa: E402
    EXIT_FAIL, EXIT_PASS, SPEC_PATH, run as gate_run,
)


# ------------------------------------------------------------------ helpers
def _tmp_repo(tmp_path: Path, root_state: dict, lane_state: dict,
              root_raw: str = None, lane_raw: str = None) -> Path:
    repo = tmp_path / "repo"
    (repo / "state").mkdir(parents=True)
    (repo / "evaluation" / "state").mkdir(parents=True)
    (repo / "results" / "audit" / "evaluation").mkdir(parents=True)
    (repo / "state" / "evaluation.json").write_text(
        root_raw if root_raw is not None else json.dumps(root_state, indent=2) + "\n",
        encoding="utf-8")
    (repo / "evaluation" / "state" / "evaluation.json").write_text(
        lane_raw if lane_raw is not None else json.dumps(lane_state, indent=2) + "\n",
        encoding="utf-8")
    return repo


def _base_states() -> tuple[dict, dict]:
    common = {
        "lane": "evaluation",
        "direction_version": 62,
        "accepted_run_id": "99999999999",
        "github_run": "11111111111",
        "evidence_refs": [],
        "evidence_refs_n": 0,
    }
    return copy.deepcopy(common), copy.deepcopy(common)


def _gate(repo: Path, run_id: str) -> None:
    p = repo / "results" / "audit" / "evaluation" / f"CYCLE_{run_id}_GATE.json"
    p.write_text(json.dumps({"gate": "PASS", "safe_to_integrate": True,
                             "required_fixes": []}), encoding="utf-8")


def _check_ids_failed(code: int, out: dict) -> set:
    assert code in (EXIT_PASS, EXIT_FAIL)
    return set(out["failed_checks"])


# ------------------------------------------------------------------ negative controls
def test_control_1_count_mismatch_bites(tmp_path):
    root, lane = _base_states()
    root["evidence_refs"] = ["a", "b"]
    root["evidence_refs_n"] = 118  # the rejected cycle's exact defect shape
    repo = _tmp_repo(tmp_path, root, lane)
    code, out = gate_run(repo_root=repo, spec_path=SPEC_PATH)
    assert code == EXIT_FAIL
    failed = _check_ids_failed(code, out)
    assert any(f.startswith("evidence_refs_n_matches@state/evaluation.json")
               for f in failed), failed


def test_control_2_invalid_ref_path_bites(tmp_path):
    root, lane = _base_states()
    root["evidence_refs"] = ["reports/evaluation/CYCLE_00000000001.md"]  # absent
    root["evidence_refs_n"] = 1
    repo = _tmp_repo(tmp_path, root, lane)
    code, out = gate_run(repo_root=repo, spec_path=SPEC_PATH)
    assert code == EXIT_FAIL
    failed = _check_ids_failed(code, out)
    assert any(f.startswith("evidence_refs_resolve@state/evaluation.json")
               for f in failed), failed


def test_control_3_indent_regression_bites(tmp_path):
    root, lane = _base_states()
    # emit the root state with evidence_refs at column 0 (the rejected cycle)
    raw_root = json.dumps(root, indent=2).replace('\n  "evidence_refs"', '\n"evidence_refs"')
    repo = _tmp_repo(tmp_path, root, lane, root_raw=raw_root)
    code, out = gate_run(repo_root=repo, spec_path=SPEC_PATH)
    assert code == EXIT_FAIL
    failed = _check_ids_failed(code, out)
    assert any(f.startswith("evidence_refs_canonical_indent@state/evaluation.json")
               for f in failed), failed


def test_control_4_unaudited_promotion_at_cutoff_bites(tmp_path):
    root, lane = _base_states()
    lane["minimal_ca_benchmark_v3"] = {
        "claim_bearing_run": "39732040165",  # == frozen cutoff, no gate, no disclosure
        "verdict": "PRODUCT_FALSIFIED",
    }
    repo = _tmp_repo(tmp_path, root, lane)
    code, out = gate_run(repo_root=repo, spec_path=SPEC_PATH)
    assert code == EXIT_FAIL
    failed = _check_ids_failed(code, out)
    assert any(f.startswith("no_unaudited_promotion@evaluation/state/evaluation.json")
               for f in failed), failed


def test_control_4b_pending_disclosure_discharges_promotion_check(tmp_path):
    root, lane = _base_states()
    lane["minimal_ca_benchmark_v3"] = {
        "claim_bearing_run": "39732040165",
        "audit_status": "PENDING_INDEPENDENT_AUDIT",
        "accepted_as_evidence": False,
    }
    repo = _tmp_repo(tmp_path, root, lane)
    code, out = gate_run(repo_root=repo, spec_path=SPEC_PATH)
    assert code == EXIT_PASS, out["failed_checks"]


def test_control_4c_historical_run_below_cutoff_is_inventory_only(tmp_path):
    root, lane = _base_states()
    lane["historical_block"] = {
        "claim_bearing_run": "39225862749",  # below cutoff, no gate, no disclosure
    }
    repo = _tmp_repo(tmp_path, root, lane)
    code, out = gate_run(repo_root=repo, spec_path=SPEC_PATH)
    assert code == EXIT_PASS, out["failed_checks"]
    # ...but it is still inventoried, never silently dropped
    inv = [c for c in out["checks"] if c["check"] == "no_unaudited_promotion"
           and c["file"] == "evaluation/state/evaluation.json"][0]
    assert any(r["claim_bearing_run"] == "39225862749"
               for r in inv["observed"]["inventory"])


def test_control_5_in_tree_gate_discharges_promotion_check(tmp_path):
    root, lane = _base_states()
    lane["block"] = {"claim_bearing_run": "39744816712"}
    repo = _tmp_repo(tmp_path, root, lane)
    _gate(repo, "39744816712")
    code, out = gate_run(repo_root=repo, spec_path=SPEC_PATH)
    assert code == EXIT_PASS, out["failed_checks"]


def test_control_6_parity_break_bites(tmp_path):
    root, lane = _base_states()
    lane["github_run"] = "22222222222"
    repo = _tmp_repo(tmp_path, root, lane)
    code, out = gate_run(repo_root=repo, spec_path=SPEC_PATH)
    assert code == EXIT_FAIL
    failed = _check_ids_failed(code, out)
    assert "root_lane_parity@both" in failed


def test_control_7_accepted_run_without_gate_bites(tmp_path):
    root, lane = _base_states()  # accepted_run_id 99999999999 has no gate file
    repo = _tmp_repo(tmp_path, root, lane)
    code, out = gate_run(repo_root=repo, spec_path=SPEC_PATH)
    assert code == EXIT_FAIL
    failed = _check_ids_failed(code, out)
    assert any(f.startswith("accepted_run_audited@") for f in failed), failed


def test_control_8_environment_error_never_passes_never_fails(tmp_path):
    empty = tmp_path / "empty"  # no state files at all
    empty.mkdir()
    code, out = gate_run(repo_root=empty, spec_path=SPEC_PATH)
    assert code == 2
    assert out["verdict"] == "ENVIRONMENT_ERROR"


# ------------------------------------------------------------------ committed tree
def test_committed_tree_passes_the_gate():
    """Before the repair of 39751745107 this test is RED (the six defects are
    live in the committed states); after the required fixes it is GREEN.  The
    before/after shim records are the claim-bearing evidence."""
    code, out = gate_run(repo_root=_REPO_ROOT, spec_path=SPEC_PATH)
    assert code == EXIT_PASS, (
        f"state-integrity gate failed on the committed tree: {out['failed_checks']}")


def test_spec_is_frozen_and_rehashable():
    spec = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
    assert spec["frozen_before_execution"] is True
    ids = [c["id"] for c in spec["checks"]]
    assert ids == [
        "evidence_refs_n_matches",
        "evidence_refs_resolve",
        "evidence_refs_canonical_indent",
        "no_unaudited_promotion",
        "accepted_run_audited",
        "root_lane_parity",
    ]
    promo = [c for c in spec["checks"] if c["id"] == "no_unaudited_promotion"][0]
    assert promo["frozen_promotion_cutoff_run"] == "39732040165"

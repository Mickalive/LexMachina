"""Regression tests for the core-lane state contract (run 38648548635).

The team job of run 38648548635 completed the producer's work (step 6 SUCCESS)
and then failed at step 7 ``Validate active MVP producer state`` because the
producer wrote ``direction_version`` 51 to the shadow copy
``product/state/product.json`` while the workflow validates
``state/product.json``. These tests freeze that diagnosis in executable form:
they must fail if the shadow copy reappears or if the canonical state stops
carrying the direction version the run was dispatched with.

Cheap by design: no network, no numpy, no pipeline import — the whole class of
defect is a file-placement/contract error and must be caught in seconds.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

PRODUCT_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PRODUCT_ROOT.parent
if str(PRODUCT_ROOT) not in sys.path:
    sys.path.insert(0, str(PRODUCT_ROOT))

from state_contract import (  # noqa: E402
    CANONICAL_STATE,
    audit_artifact_violations,
    check,
    default_direction_version,
    in_scope,
    scope_violations,
    shadow_state_findings,
    workflow_validation,
)


def _write_state(tmp_path: Path, payload: dict) -> Path:
    path = tmp_path / "product.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


# --------------------------------------------------------------------------
# 1. the workflow assertion itself
# --------------------------------------------------------------------------


def test_workflow_validation_passes_for_matching_direction_version(tmp_path: Path) -> None:
    state = _write_state(tmp_path, {"direction_version": 51, "cycle_status": "SOMETHING_REAL"})
    ok, message = workflow_validation(51, state)
    assert ok, message
    assert "passes" in message


def test_workflow_validation_fails_on_direction_mismatch(tmp_path: Path) -> None:
    """The exact 38648548635 assertion: v50 canonical state, v51 run input."""
    state = _write_state(tmp_path, {"direction_version": 50, "cycle_status": "V50_..."})
    ok, message = workflow_validation(51, state)
    assert not ok
    assert "direction_version 50 != run input 51" in message


def test_workflow_validation_fails_on_initialized_cycle_status(tmp_path: Path) -> None:
    state = _write_state(tmp_path, {"direction_version": 51, "cycle_status": "INITIALIZED"})
    ok, message = workflow_validation(51, state)
    assert not ok
    assert "INITIALIZED" in message


def test_workflow_validation_reports_missing_state_with_exit_68(tmp_path: Path) -> None:
    ok, message = workflow_validation(51, tmp_path / "absent.json")
    assert not ok
    assert "Missing" in message


def test_workflow_validation_rejects_non_integer_direction_version(tmp_path: Path) -> None:
    """jq: (.direction_version // -1) == $dirv is false for any non-number."""
    state = _write_state(tmp_path, {"direction_version": "51", "cycle_status": "REAL"})
    ok, message = workflow_validation(51, state)
    assert not ok
    assert "integer" in message


#: The direction version this cycle was dispatched with.
#:
#: This used to be a hard integer pinned to whatever the last cycle happened to
#: be dispatched with (55, from run 38877693206). That made the "live guard"
#: tests below unrunnable-by-construction rather than protective: factory
#: direction versions are NOT monotonic in time. Direction v50 was published
#: AFTER v55 ran (v50 is "REPAIR ROUND 3 of rejected proposal 38961079797"), so
#: a v50 cycle could never satisfy ``direction_version >= 55`` and three tests
#: failed on every v50 tree while asserting nothing about v50.
#:
#: Resolution order, and why:
#:  1. ``RUN_DIRECTION_VERSION`` — an explicit override for a CI job that knows
#:     its ``inputs.direction_version``.
#:  2. the mounted control plane ``/tmp/lex_control/state/factory_direction.json``
#:     — authoritative per AGENTS.md rule 10.
#:  3. the in-repo ``state/factory_direction.json``.
#: The assertion is EQUALITY, which is what the workflow's ``jq
#: --argjson dirv ... == $dirv`` actually tests. ``>=`` was never the contract
#: and is only true when versions happen to increase.
def _resolve_run_direction_version() -> int:
    import os

    raw = os.environ.get("RUN_DIRECTION_VERSION", "").strip()
    if raw:
        return int(raw)
    dirv = default_direction_version()
    assert dirv is not None, (
        "no RUN_DIRECTION_VERSION and no readable factory_direction.json; the "
        "workflow always passes inputs.direction_version explicitly"
    )
    return dirv


RUN_DIRECTION_VERSION = _resolve_run_direction_version()


def test_canonical_state_in_this_worktree_is_current() -> None:
    """The live guard: the canonical state must satisfy the real run assertion."""
    ok, message = workflow_validation(RUN_DIRECTION_VERSION, CANONICAL_STATE)
    assert ok, message


def test_direction_version_default_matches_the_mounted_control_plane() -> None:
    dirv = default_direction_version()
    assert isinstance(dirv, int), "a control-plane direction version must be readable"
    assert dirv == RUN_DIRECTION_VERSION, (
        "the control plane the cycle reads must be the direction the run was "
        f"dispatched with: mounted={dirv}, run={RUN_DIRECTION_VERSION}"
    )


def test_direction_version_is_not_assumed_monotonic(tmp_path: Path) -> None:
    """Freeze the reason the assertion is equality, not ``>=``.

    Direction versions move backwards in time (v50 was published after v55 ran),
    so a guard written as ``state >= dispatched`` fails a correct producer while
    asserting nothing about the real contract. Reproduced executably: the same
    v50 state must PASS for a v50 run and FAIL for a v55 run — which is exactly
    what the workflow's ``jq --argjson dirv ... == $dirv`` tests.
    """
    state = _write_state(tmp_path, {"direction_version": 50, "cycle_status": "REAL"})
    ok_v50, msg_v50 = workflow_validation(50, state)
    ok_v55, msg_v55 = workflow_validation(55, state)
    assert ok_v50, msg_v50
    assert not ok_v55, "a v50 state must not satisfy a v55 run input"
    assert "direction_version 50 != run input 55" in msg_v55


# --------------------------------------------------------------------------
# 2. the shadow-state regression that caused the failure
# --------------------------------------------------------------------------


def test_no_shadow_state_copy_exists_in_the_repo() -> None:
    findings = shadow_state_findings(REPO_ROOT)
    assert findings == [], (
        "a shadow copy of the canonical state file reappeared: "
        f"{[f['path'] for f in findings]}. The workflow validates state/product.json only."
    )


def test_shadow_state_is_detected_when_it_reappears(tmp_path: Path) -> None:
    shadow = tmp_path / "product" / "state" / "product.json"
    shadow.parent.mkdir(parents=True)
    shadow.write_text(json.dumps({"direction_version": 51, "cycle_status": "X"}), encoding="utf-8")
    findings = shadow_state_findings(tmp_path)
    assert len(findings) == 1
    assert findings[0]["path"] == "product/state/product.json"
    assert findings[0]["diverges"] is True


# --------------------------------------------------------------------------
# 3. lane write scope (reproduces the workflow's case-glob match)
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "path",
    [
        "product/query/pipeline.py",
        "product/state_contract.py",
        "tests/product/test_x.py",
        "results/product/latency_budget/report.json",
        "reports/product/CYCLE_1.md",
        "state/product.json",
        "data/product/fixture.json",
        "",
    ],
)
def test_scope_accepts_lane_paths(path: str) -> None:
    assert in_scope(path)


@pytest.mark.parametrize(
    "path",
    [
        "results/audit/product/CYCLE_1_GATE.json",
        "reports/audit/product/CYCLE_1.md",
        "state/frontier_portfolio.json",
        "frontier/x/y.py",
        ".github/workflows/core-lane.yml",
    ],
)
def test_scope_rejects_out_of_lane_paths(path: str) -> None:
    assert not in_scope(path)


def test_scope_violations_lists_only_out_of_scope_paths() -> None:
    bad = scope_violations(["product/a.py", "results/audit/product/CYCLE_9_GATE.json"])
    assert bad == ["results/audit/product/CYCLE_9_GATE.json"]


# --------------------------------------------------------------------------
# 4. independent-audit artifact ownership (self-minted gate regression)
# --------------------------------------------------------------------------


def test_producer_write_to_auditor_paths_is_flagged() -> None:
    assert audit_artifact_violations(
        ["results/audit/product/CYCLE_38648548635_GATE.json", "product/a.py"]
    ) == ["results/audit/product/CYCLE_38648548635_GATE.json"]


def test_self_minted_gate_is_not_committed_in_this_worktree() -> None:
    """The retired artifact must not come back into the accepted branch."""
    tracked = subprocess.run(
        ["git", "ls-files", "--", "results/audit/product/CYCLE_38648548635_GATE.json"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    ).stdout.strip()
    assert tracked == "", "producer-self-minted gate artifact is tracked again"


def test_retired_self_minted_gate_is_preserved_as_incident_evidence() -> None:
    archived = REPO_ROOT / "reports/product/incidents/self_minted_gate_38648548635.RETIRED.json"
    assert archived.is_file(), "the incident evidence must survive the removal"
    payload = json.loads(archived.read_text(encoding="utf-8"))
    assert payload["gate"] == "PASS"
    assert payload["state_written_during_run"] == 38648548635


# --------------------------------------------------------------------------
# 5. the CLI contract
# --------------------------------------------------------------------------


def test_cli_returns_zero_when_the_contract_holds() -> None:
    result = subprocess.run(
        [sys.executable, str(PRODUCT_ROOT / "state_contract.py"), "--check"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_check_report_is_machine_readable() -> None:
    report = check(RUN_DIRECTION_VERSION, paths=["product/x.py"])
    assert report["ok"] is True
    assert report["workflow_validation"]["workflow_exit"] == 0
    assert set(report) >= {
        "lane",
        "direction_version",
        "workflow_validation",
        "write_scope",
        "audit_artifact_ownership",
        "shadow_state",
    }
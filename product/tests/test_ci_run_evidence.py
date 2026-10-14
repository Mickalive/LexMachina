"""Tests for the durable run-evidence recorder (``product/ci_run_evidence.py``).

The v50 lane outcome requires ``state/product.json`` to snapshot
``{run_id, head_sha, conclusion, created_at}`` for the promoting run and to set
``machine_gate_ready: true`` **only** when that run's conclusion is observably
``success``.  ``machine_gate_ready`` is the flag a withdrawn claim
(``V45_QUERY_MAP_MACHINE_GATE_GREEN``) used to be asserted by hand, so the rule
is pinned here: every way of being *not* green must leave the flag down, and no
code path may ever raise ``human_gate_ready``.

The GitHub REST API is stubbed; nothing here touches the network.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "product"))

import ci_run_evidence as ev  # noqa: E402

SHA = "43652aa75c0141681e0afb48c44a84f623f01c50"


def _payload(**overrides) -> dict:
    base = {
        "id": 38600271324,
        "head_sha": SHA,
        "head_branch": "main",
        "event": "workflow_dispatch",
        "status": "completed",
        "conclusion": "success",
        "created_at": "2026-10-14T16:41:50Z",
        "updated_at": "2026-10-14T17:20:00Z",
        "name": "Core product dirV50 repair0",
    }
    base.update(overrides)
    return base


def _fetcher(status: int = 200, payload: dict | None = None):
    seen: list[str] = []

    def fetch(url: str) -> tuple[int, dict]:
        seen.append(url)
        return status, (payload if payload is not None else _payload())

    fetch.seen = seen  # type: ignore[attr-defined]
    return fetch


def _summary(run_id: int = 38600271324, **overrides) -> dict:
    base = {
        "schema": "query-map-ci-reality-legs/1",
        "run_id": run_id,
        "head_sha": SHA,
        "mode": "live",
        "evidence_tier": "CI_TEAM_JOB_LIVE",
        "legs_ran_in_this_run": ["petty-theft-dismissal", "rent-default",
                                 "corporate-criminal-liability", "business-judgment-rule"],
        "legs_complete": True,
        "all_legs_passed": True,
        "legs_missing": [],
        "legs_failed": [],
    }
    base.update(overrides)
    return base


PASSING = ("Le bailleur respecte un delai de 30 jours, la fin d'un mois, sous peine "
           "d'abus de droit; la bonne foi limite ce pretention.")


def _report(slug: str, prose: str) -> dict:
    return {
        "slug": slug, "mode": "live", "validation_errors": [],
        "bundle": {
            "decisions": [{"decision_id": "bge_142_II_369", "rank": 1, "citation": "BGE 142 II 369",
                           "language": "de", "counter_status": "candidate-limiting",
                           "canonical_url": "https://x", "snippet": "s"}],
            "clusters": [{"cluster_id": "c0", "label": "c", "size": 1}],
            "answer": {"status": "ready", "method": "generative_audit_llm_v2", "prose": prose,
                       "cited_decision_ids": ["bge_142_II_369"], "model": "m"},
            "provenance": {"generative_audit": {"provider_error": None,
                           "adversarial": {"method": "independent_llm_adversarial_v2",
                                           "model": "m2", "error": None}}},
        },
    }


def _state() -> dict:
    return {
        "lane": "product",
        "machine_gate_ready": False,
        "human_gate_ready": False,
        "evidence_tier": "LOCAL_VERIFIED_PENDING_DURABLE_RUN",
        "verified_runs": [],
        "unresolvable_run_ids": {"ids": []},
    }


# --------------------------------------------------------------------------- #
# observation
# --------------------------------------------------------------------------- #
def test_observe_run_snapshots_the_four_required_fields():
    obs = ev.observe_run(38600271324, fetch=_fetcher())
    assert obs["run_id"] == 38600271324
    for field in ("head_sha", "conclusion", "created_at"):
        assert obs[field]
    assert obs["source"].endswith("/actions/runs/38600271324")


def test_unresolvable_run_raises_rather_than_guessing():
    try:
        ev.observe_run(38290597414, fetch=_fetcher(status=404, payload={"message": "Not Found"}))
    except ev.RunNotFound as exc:
        assert "404" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("HTTP 404 must raise, never return a fabricated conclusion")


def test_unresolvable_run_is_recorded_under_unresolvable_run_ids():
    obs = {"run_id": 38290597414, "conclusion": None, "observed_at": "2026-10-14T18:00:00Z"}
    out = ev.update_state(_state(), obs, {}, unresolved=True)
    assert 38290597414 in out["unresolvable_run_ids"]["ids"]
    assert out["machine_gate_ready"] is False


# --------------------------------------------------------------------------- #
# machine gate eligibility
# --------------------------------------------------------------------------- #
def test_green_run_with_complete_live_summary_opens_the_machine_gate():
    obs = ev.observe_run(38600271324, fetch=_fetcher())
    obs["observed_at"] = "2026-10-14T17:30:00Z"
    out = ev.update_state(_state(), obs, _summary(),
                          summary_path="results/product/reality_check/summary_ci_38600271324.json")
    assert out["machine_gate_ready"] is True
    assert out["evidence_tier"] == "DURABLE_CI_VERIFIED"
    assert out["reality_check_status"]["durable_green_run_id"] == 38600271324
    entry = out["verified_runs"][-1]
    assert {entry["run_id"], entry["head_sha"], entry["conclusion"], entry["created_at"]} >= {
        38600271324, SHA, "success", "2026-10-14T16:41:50Z"
    }


def test_in_progress_run_never_opens_the_machine_gate():
    obs = ev.observe_run(38600271324, fetch=_fetcher(status=200, payload=_payload(
        status="in_progress", conclusion=None)))
    obs["observed_at"] = "2026-10-14T17:30:00Z"
    out = ev.update_state(_state(), obs, _summary())
    assert out["machine_gate_ready"] is False
    assert any("conclusion" in r for r in out["machine_gate"]["reasons"])


def test_failed_run_with_green_legs_never_opens_the_machine_gate():
    obs = ev.observe_run(38600271324, fetch=_fetcher(status=200,
                                                       payload=_payload(conclusion="failure")))
    obs["observed_at"] = "2026-10-14T17:30:00Z"
    out = ev.update_state(_state(), obs, _summary())
    assert out["machine_gate_ready"] is False
    assert out["machine_gate"]["reasons"] == ["conclusion='failure' is not 'success'"]


def test_incomplete_leg_run_never_opens_the_machine_gate():
    obs = ev.observe_run(38600271324, fetch=_fetcher())
    obs["observed_at"] = "2026-10-14T17:30:00Z"
    summary = _summary(legs_complete=False, legs_missing=["business-judgment-rule"])
    out = ev.update_state(_state(), obs, summary)
    assert out["machine_gate_ready"] is False
    assert any("legs incomplete" in r for r in out["machine_gate"]["reasons"])


def test_fixture_summary_never_opens_the_machine_gate():
    obs = ev.observe_run(38600271324, fetch=_fetcher())
    obs["observed_at"] = "2026-10-14T17:30:00Z"
    out = ev.update_state(_state(), obs, _summary(mode="fixture",
                                                  evidence_tier="FIXTURE_OFFLINE"))
    assert out["machine_gate_ready"] is False
    assert any("not a live" in r for r in out["machine_gate"]["reasons"])


def test_summary_from_another_run_or_sha_never_opens_the_machine_gate():
    obs = ev.observe_run(38600271324, fetch=_fetcher())
    obs["observed_at"] = "2026-10-14T17:30:00Z"

    other_run = ev.update_state(_state(), obs, _summary(run_id=38578725589))
    assert other_run["machine_gate_ready"] is False
    assert any("summary run_id" in r for r in other_run["machine_gate"]["reasons"])

    other_sha = ev.update_state(_state(), obs, _summary(head_sha="deadbeef" * 5))
    assert other_sha["machine_gate_ready"] is False
    assert any("documented workspace head" in r for r in other_sha["machine_gate"]["reasons"])


def test_missing_summary_never_opens_the_machine_gate():
    obs = ev.observe_run(38600271324, fetch=_fetcher())
    obs["observed_at"] = "2026-10-14T17:30:00Z"
    out = ev.update_state(_state(), obs, {})
    assert out["machine_gate_ready"] is False


def test_human_gate_is_never_opened_by_this_module():
    obs = ev.observe_run(38600271324, fetch=_fetcher())
    obs["observed_at"] = "2026-10-14T17:30:00Z"
    out = ev.update_state(_state(), obs, _summary())
    assert out["human_gate_ready"] is False


# --------------------------------------------------------------------------- #
# state bookkeeping
# --------------------------------------------------------------------------- #
def test_state_update_is_idempotent_per_run():
    obs = ev.observe_run(38600271324, fetch=_fetcher())
    obs["observed_at"] = "2026-10-14T17:30:00Z"
    once = ev.update_state(_state(), obs, _summary())
    twice = ev.update_state(once, obs, _summary())
    assert [r["run_id"] for r in twice["verified_runs"]] == [38600271324]
    assert twice["verified_runs"][0]["conclusion"] == "success"


def test_update_does_not_mutate_the_input_state():
    state = _state()
    obs = ev.observe_run(38600271324, fetch=_fetcher())
    ev.update_state(state, obs, _summary())
    assert state["machine_gate_ready"] is False
    assert state["verified_runs"] == []


def test_summary_lookup_is_run_scoped(tmp_path):
    (tmp_path / "summary_ci_38600271324.json").write_text(json.dumps(_summary()), encoding="utf-8")
    assert ev.find_summary(38600271324, tmp_path) is not None
    assert ev.find_summary(38578725589, tmp_path) is None


def test_load_summary_survives_garbage(tmp_path):
    (tmp_path / "summary_ci_1.json").write_text("{not json", encoding="utf-8")
    assert ev.load_summary(tmp_path / "summary_ci_1.json") == {}
    assert ev.load_summary(None) == {}

# --------------------------------------------------------------------------- #
# provenance: dispatch sha vs the lane-branch head the team job actually ran
# --------------------------------------------------------------------------- #
def test_lane_branch_head_documented_for_this_run_is_accepted():
    """A core-lane team job executes lab/product code under a main dispatch sha."""
    obs = ev.observe_run(38600271324, fetch=_fetcher())
    obs["observed_at"] = "2026-10-14T17:30:00Z"
    state = _state()
    state["current_run"] = {
        "run_id": 38600271324,
        "head_sha_workflow": SHA,
        "head_sha_lab_product_at_leg_execution": "ea161e6dd575985374093cd6306dcd6a4a3cb095",
    }
    summary = _summary(head_sha="ea161e6dd575985374093cd6306dcd6a4a3cb095")
    out = ev.update_state(state, obs, summary)
    assert out["machine_gate_ready"] is True
    assert "lab-branch head" in out["machine_gate"]["provenance_note"]


def test_summary_recorded_run_head_sha_is_accepted_directly():
    obs = ev.observe_run(38600271324, fetch=_fetcher())
    obs["observed_at"] = "2026-10-14T17:30:00Z"
    summary = _summary(head_sha="ea161e6" + "0" * 33, run_head_sha=SHA)
    out = ev.update_state(_state(), obs, summary)
    assert out["machine_gate_ready"] is True


def test_undocumented_foreign_workspace_head_is_still_rejected():
    obs = ev.observe_run(38600271324, fetch=_fetcher())
    obs["observed_at"] = "2026-10-14T17:30:00Z"
    summary = _summary(head_sha="ea161e6" + "0" * 33)  # not documented anywhere
    out = ev.update_state(_state(), obs, summary)
    assert out["machine_gate_ready"] is False
    assert any("documented workspace head" in r for r in out["machine_gate"]["reasons"])


def test_documented_workspace_head_of_another_run_is_not_borrowed():
    obs = ev.observe_run(38600271324, fetch=_fetcher())
    obs["observed_at"] = "2026-10-14T17:30:00Z"
    state = _state()
    state["current_run"] = {"run_id": 38578725589,
                            "head_sha_lab_product_at_leg_execution": "ea161e6" + "0" * 33}
    out = ev.update_state(state, obs, _summary(head_sha="ea161e6" + "0" * 33))
    assert out["machine_gate_ready"] is False


def test_runner_records_both_dispatch_and_workspace_shas(monkeypatch, tmp_path):
    """The leg summary itself must be able to prove which code produced it."""
    import ci_reality_legs as ci

    monkeypatch.setenv("GITHUB_SHA", "a" * 40)
    summary, code = ci.run_legs(
        "38600271324", mode="live", slugs=["rent-default"], out_dir=tmp_path,
        leg_runner=lambda *a, **k: _report("rent-default", PASSING),
        monotonic=lambda: 0.0, wall=lambda: 1_700_000_000.0, deadline_seconds=10_000)
    assert code == 0
    assert summary["run_head_sha"] == "a" * 40
    assert summary["head_sha"] and summary["head_sha"] != "a" * 40

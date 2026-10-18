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


#: The LEGACY prose of this file.  It is deliberately kept, because it is the
#: measurable proof that the ``_report`` prose change below was necessary rather
#: than cosmetic: with the counter-evidence and latency fields already correct,
#: this string still fails the real structural gate (French-synthesis markers)
#: and, if that were patched, the real rent-default truth gate (Art. 257d(2)
#: 30-day-to-month-end notice).  See
#: ``test_the_three_structural_gates_this_repair_had_to_satisfy``.
PASSING = ("Le bailleur respecte un delai de 30 jours, la fin d'un mois, sous peine "
           "d'abus de droit; la bonne foi limite ce pretention.")


def _report(slug: str, mode: str, top_n: int, evidence_count: int, max_cites: int) -> dict:
    """Stub leg report matching run_legs' actual ``leg_runner`` call shape.

    Why this stub changed in cycle 39087917357 (reproduced, not guessed)
    --------------------------------------------------------------------
    ``test_runner_records_both_dispatch_and_workspace_shas`` was FAILING at the
    resumed snapshot HEAD 351f388 (``assert 1 == 0``), and at both heads before
    it (``ec622c6``, ``68bdae8``) - so it is a pre-existing failure of this
    lane's own suite, not a regression introduced by the resume.  ``run_legs``
    stops a structural gate list at its FIRST failure, which hides the ones
    behind it, so the repair was made by exposing them one at a time and
    recording each verbatim message:

    1. HEAD as shipped -> ``[FAIL] structural - surfaced counter lacks verified
       evidence: bge_142_II_369``.  ``reality_check.structural_gates`` requires
       every surfaced counter row to carry ``counter_evidence_verified is True``
       AND non-empty ``counter_evidence``; the stub declared
       ``counter_status: candidate-limiting`` with neither.
    2. fixing (1) only -> ``[FAIL] structural - answer is not synthesized in the
       user's language``.  The gate counts French markers and needs >= 3; the
       legacy ``PASSING`` string above scores 2.
    3. fixing (1)+(2) only -> ``[FAIL] structural - full product answer too
       slow: Nones``.  The gate needs a ``total_seconds`` below 300.

    Only after all three does the leg reach ``truth::rent-default``, which the
    original ``PASSING`` prose would also fail (its ``30 jours, la fin d'un
    mois`` lacks the ``(pour|jusqu.a|sur)`` bridge the Art. 257d(2) notice
    pattern requires) - measured in
    ``test_the_three_structural_gates_this_repair_had_to_satisfy``.

    THE GATES THEMSELVES ARE NOT TOUCHED.  This is a wiring fixture whose only
    job is to satisfy the real gates so the test can reach its real assertions
    (``run_head_sha`` / ``head_sha``).  Every change here makes the stub conform
    to an existing gate; ``product/reality_check.py`` is byte-unchanged.
    """
    prose = ("Le bailleur doit respecter un delai de conge de 30 jours "
             "jusqu'a la fin d'un mois, sous peine d'abus de droit; "
             "la bonne foi limite cette pretention.")
    return {
        "slug": slug, "mode": "live", "validation_errors": [],
        # structural gate 3: a full answer must be timed and under 300 s.
        "total_seconds": 120.0,
        "bundle": {
            "decisions": [{"decision_id": "bge_142_II_369", "rank": 1, "citation": "BGE 142 II 369",
                           "language": "de", "counter_status": "candidate-limiting",
                           # structural gate 1: surfaced counters need verified,
                           # non-empty evidence.
                           "counter_evidence_verified": True,
                           "counter_evidence": "BGE 142 II 369 abs. 2 legt die Beweislast um.",
                           "canonical_url": "https://x", "snippet": "s"}],
            "clusters": [{"cluster_id": "c0", "label": "c", "size": 1}],
            # structural gate 2 + the rent-default truth gate: >=3 French
            # markers, and the distinct Art. 257d(2) 30-day-to-month-end notice.
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


# --------------------------------------------------------------------------- #
# job chain (the v50 promotion deadlock made this the deciding evidence)
# --------------------------------------------------------------------------- #
def _jobs_fetcher(payload: dict, status: int = 200):
    seen: list[str] = []

    def fetch(url: str) -> tuple[int, dict]:
        seen.append(url)
        return status, payload

    fetch.seen = seen  # type: ignore[attr-defined]
    return fetch


GREEN_CHAIN = {"team": "success", "audit": "success", "integrate": "success",
               "resilience": "success"}


def test_observe_jobs_records_every_job_conclusion():
    payload = {"jobs": [{"name": name, "conclusion": conclusion}
                        for name, conclusion in GREEN_CHAIN.items()]}
    jobs = ev.observe_jobs(38604340726, fetch=_jobs_fetcher(payload))
    assert jobs == GREEN_CHAIN


def test_observe_jobs_records_a_skipped_integrate_instead_of_guessing_green():
    payload = {"jobs": [{"name": "team", "conclusion": "success"},
                        {"name": "audit", "conclusion": "failure"},
                        {"name": "integrate", "conclusion": "skipped"}]}
    jobs = ev.observe_jobs(38600271324, fetch=_jobs_fetcher(payload))
    assert jobs["integrate"] == "skipped"
    assert jobs["audit"] == "failure"


def test_observe_jobs_never_fabricates_when_the_api_is_unavailable():
    assert ev.observe_jobs(38604340726, fetch=_jobs_fetcher({}, status=503)) == {}


def test_recorded_entry_states_whether_the_promotion_chain_completed():
    green_run = 38604340726
    obs = ev.observe_run(green_run, fetch=_fetcher(payload=_payload(id=green_run)))
    obs["observed_at"] = "2026-10-14T21:40:00Z"
    out = ev.update_state(_state(), obs, _summary(run_id=green_run), jobs=GREEN_CHAIN)
    entry = next(r for r in out["verified_runs"] if r["run_id"] == green_run)
    assert entry["jobs"] == GREEN_CHAIN
    assert entry["promotion_chain_green"] is True


def test_team_green_but_integrate_skipped_is_recorded_as_a_broken_chain():
    obs = ev.observe_run(38600271324, fetch=_fetcher())
    obs["observed_at"] = "2026-10-14T21:40:00Z"
    jobs = {"team": "success", "audit": "failure", "integrate": "skipped"}
    out = ev.update_state(_state(), obs, _summary(), jobs=jobs)
    entry = next(r for r in out["verified_runs"] if r["run_id"] == 38600271324)
    assert entry["promotion_chain_green"] is False


def test_missing_job_evidence_is_omitted_rather_than_defaulted_to_green():
    obs = ev.observe_run(38600271324, fetch=_fetcher())
    obs["observed_at"] = "2026-10-14T21:40:00Z"
    out = ev.update_state(_state(), obs, _summary())
    entry = next(r for r in out["verified_runs"] if r["run_id"] == 38600271324)
    assert "jobs" not in entry
    assert "promotion_chain_green" not in entry


def test_runner_records_both_dispatch_and_workspace_shas(monkeypatch, tmp_path):
    """The leg summary itself must be able to prove which code produced it."""
    import ci_reality_legs as ci

    monkeypatch.setenv("GITHUB_SHA", "a" * 40)
    summary, code = ci.run_legs(
        "38600271324", mode="live", slugs=["rent-default"], out_dir=tmp_path,
        leg_runner=lambda *a, **k: _report(*a),
        monotonic=lambda: 0.0, wall=lambda: 1_700_000_000.0, deadline_seconds=10_000)
    assert code == 0
    assert summary["run_head_sha"] == "a" * 40
    assert summary["head_sha"] and summary["head_sha"] != "a" * 40


# --------------------------------------------------------------------------
# The repair's necessity proof (cycle 39087917357)
#
# A fixture that was simply edited until it went green proves nothing: the same
# edit could have been a hidden gate weakening.  These three cases assert the
# OPPOSITE direction - each individual gate still rejects its broken input - and
# the last one keeps the legacy prose in the file as a permanently failing
# control, so a future "simplification" of the gates fails here first.
# --------------------------------------------------------------------------

def _leg_gates(report: dict, monkeypatch, tmp_path) -> tuple[int, list[dict]]:
    import ci_reality_legs as ci

    monkeypatch.setenv("GITHUB_SHA", "a" * 40)
    summary, code = ci.run_legs(
        "38600271324", mode="live", slugs=["rent-default"], out_dir=tmp_path,
        leg_runner=lambda *a, **k: report,
        monotonic=lambda: 0.0, wall=lambda: 1_700_000_000.0, deadline_seconds=10_000)
    return code, [g for leg in summary.get("legs", []) for g in leg.get("gates", [])]


def _detail_text(gates: list[dict]) -> str:
    return json.dumps(gates, sort_keys=True)


def test_gate_1_still_rejects_a_surfaced_counter_without_verified_evidence(
        monkeypatch, tmp_path):
    report = _report("rent-default", "live", 10, 1, 10)
    row = report["bundle"]["decisions"][0]
    row["counter_evidence_verified"] = False
    code, gates = _leg_gates(report, monkeypatch, tmp_path)
    assert code == 1
    assert "surfaced counter lacks verified evidence" in _detail_text(gates)


def test_gate_2_still_rejects_a_non_french_synthesis(monkeypatch, tmp_path):
    report = _report("rent-default", "live", 10, 1, 10)
    report["bundle"]["answer"]["prose"] = PASSING  # French markers = 2, gate needs 3
    code, gates = _leg_gates(report, monkeypatch, tmp_path)
    assert code == 1
    assert "answer is not synthesized in the user's language" in _detail_text(gates)


def test_gate_3_still_rejects_an_untimed_answer(monkeypatch, tmp_path):
    report = _report("rent-default", "live", 10, 1, 10)
    report.pop("total_seconds")
    code, gates = _leg_gates(report, monkeypatch, tmp_path)
    assert code == 1
    assert "full product answer too slow" in _detail_text(gates)


def test_the_legacy_passing_prose_would_also_fail_the_truth_gate(
        monkeypatch, tmp_path):
    """Control run: the prose change was needed by the GATE, not by the test.

    The legacy string scores 2 French markers (structural gate 2), so it never
    reached the truth gate on its own.  Here it is promoted past that gate by
    hand - by appending a third marker - so that the Art. 257d(2) notice pattern
    is the only thing left to judge, and it is still rejected.
    """
    report = _report("rent-default", "live", 10, 1, 10)
    # +1 French marker ("selon") gets the structural language gate green while
    # leaving the legacy notice wording untouched.
    report["bundle"]["answer"]["prose"] = PASSING + " La solution selon la loi."
    code, gates = _leg_gates(report, monkeypatch, tmp_path)
    assert code == 1
    text = _detail_text(gates)
    assert "missing distinct Art. 257d(2) 30-day notice to month-end" in text

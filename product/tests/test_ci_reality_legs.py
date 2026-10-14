"""Tests for the run-scoped, sequential CI reality-leg runner (direction v50).

The lane outcome for v50 is a green core-lane run whose own team job executes the
four frozen reality legs live and writes
``results/product/reality_check/summary_ci_<run_id>.json``.  These tests pin the
three properties that outcome depends on, without touching the network:

* **sequencing** - legs never overlap (the 4-way parallel batch that pushed every
  adversarial pass past its ceiling must not come back);
* **run scoping** - evidence from another run can never be presented as this
  run's evidence;
* **durable partial progress** - a deadline cut keeps the legs that did run and
  the summary says exactly which ones are missing.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "product"))

import ci_reality_legs as ci  # noqa: E402
from reality_check import LEGS  # noqa: E402


# --------------------------------------------------------------------------- #
# fixtures
# --------------------------------------------------------------------------- #
PASSING_PROSE = {
    "rent-default": (
        "Le bailleur doit respecter un delai de 30 jours, c'est-a-dire la fin d'un mois, "
        "sous peine d'abus de droit; la bonne foi du locataire est une limite "
        "jurisprudentielle constante."
    ),
    "petty-theft-dismissal": (
        "Un vol de faible valeur peut justifier le licenciement immediate selon "
        "l'art. 337 CO quand le confiance dans l'entreprise est rompu de maniere "
        "objective; bge 4A 228/2015 admet aussi la confiance abstraitement "
        "insuffisante dans le cas d'espece de l'employe restitue."
    ),
    "corporate-criminal-liability": (
        "La responsabilite penale de l'entreprise est subsidiaire en principe, sauf "
        "une responsabilite primaire de l'entreprise elle-meme lorsque l'infraction "
        "lui est personnellement imputable; bge 142 IV 333 exige en outre une "
        "organisation deficiente demontree."
    ),
    "business-judgment-rule": (
        "Le juge s'abstient de reviser une decision commerciale et retient son "
        "jugement lorsque le conseil "
        "d'administration a ete information de maniere adequate, qu'il n'y a pas de "
        "conflit d'interets et que la decision repose sur des hypotheses "
        "pertinentes; bger 4A 219/2015."
    ),
}

DIRECT_AUTHORITY = {
    "rent-default": ["bge_142_II_369"],
    "petty-theft-dismissal": ["bger_4A_228_2015"],
    "corporate-criminal-liability": ["bge_BGE_142_IV_333"],
    "business-judgment-rule": ["bger_4A_219_2015"],
}


def _report(slug: str, prose: str, cited: list[str] | None = None) -> dict:
    cited = cited if cited is not None else DIRECT_AUTHORITY[slug]
    decisions = [{"decision_id": d, "rank": 1, "citation": d, "language": "de",
                  "counter_status": "candidate-limiting", "canonical_url": "https://x",
                  "snippet": "s"} for d in cited]
    bundle = {
        "decisions": decisions,
        "clusters": [{"cluster_id": "c0", "label": "c", "size": 1}],
        "answer": {
            "status": "ready",
            "method": "generative_audit_llm_v2",
            "prose": prose,
            "cited_decision_ids": cited,
            "model": "opencode/nemotron-3-ultra-free",
        },
        "provenance": {
            "generative_audit": {
                "provider_error": None,
                "adversarial": {"method": "independent_llm_adversarial_v2",
                                "model": "opencode/space-bunny-free", "error": None},
            }
        },
    }
    return {"slug": slug, "mode": "fixture", "validation_errors": [], "bundle": bundle}


class FakeClock:
    """Monotone wall/monotonic pair the runner and the fake legs share."""

    def __init__(self, start: float = 1_700_000_000.0):
        self.now = start

    def wall(self) -> float:
        return self.now

    def monotonic(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def _runner(clock: FakeClock, per_leg_seconds: float = 5.0, prose=None):
    started: list[tuple[float, str]] = []

    def leg_runner(slug, mode, top_n, evidence_count, max_cites):
        started.append((clock.now, slug))
        clock.advance(per_leg_seconds)
        text = prose(slug) if callable(prose) else (prose or PASSING_PROSE[slug])
        return _report(slug, text)

    return leg_runner, started


def _run(tmp_path: Path, run_id: str = "38600271324", **kwargs):
    clock = FakeClock()
    leg_runner, started = _runner(clock, **kwargs.pop("clock_kwargs", {}))
    out_dir = tmp_path / "reality_check"
    summary, code = ci.run_legs(
        run_id,
        mode=kwargs.pop("mode", "live"),
        out_dir=out_dir,
        leg_runner=leg_runner,
        monotonic=clock.monotonic,
        wall=clock.wall,
        **kwargs,
    )
    return summary, code, out_dir, started


# --------------------------------------------------------------------------- #
# plan / naming
# --------------------------------------------------------------------------- #
def test_frozen_order_covers_every_workflow_leg():
    assert sorted(ci.FROZEN_ORDER) == sorted(LEGS)


def test_live_summary_name_is_the_lane_contract():
    p = ci.summary_path(Path("results/product/reality_check"), "38600271324", "live")
    assert p.name == "summary_ci_38600271324.json"


def test_fixture_summary_name_cannot_masquerade_as_live_evidence():
    p = ci.summary_path(Path("results/product/reality_check"), "38600271324", "fixture")
    assert p.name != "summary_ci_38600271324.json"
    assert p.name == "summary_fixture_ci_38600271324.json"


def test_leg_report_name_is_run_scoped():
    name = ci.leg_report_name("rent-default", "live", "38600271324", "20261014T170000Z")
    assert "ci-38600271324" in name
    ci.assert_run_scoped(name, "38600271324")
    try:
        ci.assert_run_scoped("rent-default_live_20261014T145133Z.json", "38600271324")
    except ci.CrossRunReuseError as exc:
        assert "cross-run" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("foreign evidence must be rejected")


def test_plan_only_is_offline(tmp_path, capsys):
    rc = ci.main(["--plan-only", "--run-id", "38600271324", "--mode", "live",
                  "--out-dir", str(tmp_path)])
    assert rc == 0
    plan = json.loads(capsys.readouterr().out)
    assert plan["concurrency"] == 1
    assert plan["order"] == ci.FROZEN_ORDER
    assert plan["summary"].endswith("summary_ci_38600271324.json")


# --------------------------------------------------------------------------- #
# sequential, uncontended execution
# --------------------------------------------------------------------------- #
def test_all_legs_run_sequentially_and_pass(tmp_path):
    summary, code, out_dir, started = _run(tmp_path, deadline_seconds=10_000,
                                           clock_kwargs={"per_leg_seconds": 7.0})
    assert code == 0
    assert summary["legs_ran_in_this_run"] == ci.FROZEN_ORDER
    assert summary["legs_complete"] is True
    assert summary["all_legs_passed"] is True
    assert summary["execution"]["concurrency"] == 1
    assert summary["local_evidence_only"] is False  # live tier is not "local only"
    assert len(started) == 4


def test_leg_intervals_are_disjoint(tmp_path):
    """Contention is the failure mode of 2026-10-14: prove legs never overlap."""
    summary, _, _, started = _run(tmp_path, deadline_seconds=10_000,
                                  clock_kwargs={"per_leg_seconds": 7.0})
    for (t1, _slug1), (t2, _slug2) in zip(started, started[1:]):
        assert t2 - t1 >= 7.0, "legs must not overlap in wall-clock time"
    ci.assert_disjoint_intervals(summary["legs"])
    ordered = [r["slug"] for r in summary["legs"]]
    assert ordered == [s for _t, s in started]


def test_overlapping_legs_are_rejected(tmp_path):
    recs = [
        {"slug": "a", "started_at": "2026-10-14T17:00:00Z", "finished_at": "2026-10-14T17:00:10Z"},
        {"slug": "b", "started_at": "2026-10-14T17:00:05Z", "finished_at": "2026-10-14T17:00:20Z"},
    ]
    try:
        ci.assert_disjoint_intervals(recs)
    except ci.LegOrderError as exc:
        assert "sequentially" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("overlap must fail the run")


def test_summary_and_leg_reports_are_written_for_this_run(tmp_path):
    summary, _, out_dir, _ = _run(tmp_path, deadline_seconds=10_000)
    written = json.loads((out_dir / "summary_ci_38600271324.json").read_text(encoding="utf-8"))
    assert written["run_id"] == "38600271324"
    assert summary["head_sha"] and len(summary["head_sha"]) == 40
    for rec in summary["legs"]:
        assert rec["run_id"] == "38600271324"
        assert "ci-38600271324" in rec["report"]
        assert (ROOT / rec["report"]).is_file() or (tmp_path / Path(rec["report"]).name).is_file()
    ci.assert_run_scoped(summary["legs"][0]["report"], "38600271324")


# --------------------------------------------------------------------------- #
# deadline -> partial evidence, never a silent pass
# --------------------------------------------------------------------------- #
def test_deadline_stops_early_and_reports_missing_legs(tmp_path):
    summary, code, out_dir, started = _run(tmp_path, deadline_seconds=12.0)
    assert code == 3
    assert summary["legs_complete"] is False
    assert summary["all_legs_passed"] is False
    assert summary["stopped_reason"] == "deadline_reached"
    assert len(started) < 4
    assert summary["legs_missing"]
    written = json.loads((out_dir / "summary_ci_38600271324.json").read_text(encoding="utf-8"))
    assert written["legs_ran_in_this_run"] == summary["legs_ran_in_this_run"]


def test_partial_progress_survives_a_killed_job(tmp_path):
    clock = FakeClock()

    def leg_runner(slug, mode, top_n, evidence_count, max_cites):
        clock.advance(5.0)
        if slug == ci.FROZEN_ORDER[1]:
            raise KeyboardInterrupt("simulated job kill")
        return _report(slug, PASSING_PROSE[slug])

    out_dir = tmp_path / "reality_check"
    try:
        ci.run_legs("38600271324", mode="live", out_dir=out_dir, leg_runner=leg_runner,
                    monotonic=clock.monotonic, wall=clock.wall, deadline_seconds=10_000)
    except KeyboardInterrupt:
        pass
    else:  # pragma: no cover
        raise AssertionError("the interrupt must propagate")

    partial = json.loads((out_dir / "summary_ci_38600271324.json").read_text(encoding="utf-8"))
    assert partial["legs_ran_in_this_attempt"] == [ci.FROZEN_ORDER[0]]
    assert "legs_complete" not in partial or partial["legs_complete"] is False


# --------------------------------------------------------------------------- #
# resume: same run only
# --------------------------------------------------------------------------- #
def test_resume_completes_the_same_run(tmp_path):
    partial, code, out_dir, started = _run(tmp_path, deadline_seconds=12.0)
    assert code == 3
    done = partial["legs_ran_in_this_run"]

    clock = FakeClock(start=1_700_009_999.0)
    leg_runner, started2 = _runner(clock)
    summary, code = ci.run_legs("38600271324", mode="live", out_dir=out_dir, resume=True,
                                leg_runner=leg_runner, monotonic=clock.monotonic,
                                wall=clock.wall, deadline_seconds=10_000)
    assert code == 0
    assert summary["legs_complete"] is True
    assert [r["slug"] for r in summary["legs"] if r["reused_within_run"]] == done
    assert len(started2) == 4 - len(done)


def test_resume_refuses_evidence_from_another_run(tmp_path):
    """A summary written by a different run is never inherited."""
    out_dir = tmp_path / "reality_check"
    out_dir.mkdir(parents=True)
    foreign = {
        "run_id": "38578725589",
        "legs": [{"slug": ci.FROZEN_ORDER[0], "run_id": "38578725589", "passed": True,
                  "started_at": "2026-10-14T15:00:00Z", "finished_at": "2026-10-14T15:02:00Z",
                  "gates": [], "report": "results/product/reality_check/x_live_ci-38578725589_y.json"}],
    }
    (out_dir / "summary_ci_38600271324.json").write_text(json.dumps(foreign), encoding="utf-8")

    clock = FakeClock()
    leg_runner, started = _runner(clock)
    summary, code = ci.run_legs("38600271324", mode="live", out_dir=out_dir, resume=True,
                                leg_runner=leg_runner, monotonic=clock.monotonic,
                                wall=clock.wall, deadline_seconds=10_000)
    assert code == 0
    assert len(started) == 4  # nothing was inherited
    assert all(r["reused_within_run"] is False for r in summary["legs"])


def test_resume_rejects_leg_records_whose_run_id_differs(tmp_path):
    out_dir = tmp_path / "reality_check"
    out_dir.mkdir(parents=True)
    mixed = {
        "run_id": "38600271324",
        "legs": [{"slug": ci.FROZEN_ORDER[0], "run_id": "38578725589", "passed": True,
                  "started_at": "2026-10-14T15:00:00Z", "finished_at": "2026-10-14T15:02:00Z",
                  "gates": [], "report": "x.json"}],
    }
    (out_dir / "summary_ci_38600271324.json").write_text(json.dumps(mixed), encoding="utf-8")
    clock = FakeClock()
    leg_runner, started = _runner(clock)
    summary, code = ci.run_legs("38600271324", mode="live", out_dir=out_dir, resume=True,
                                leg_runner=leg_runner, monotonic=clock.monotonic,
                                wall=clock.wall, deadline_seconds=10_000)
    assert code == 0
    assert len(started) == 4


# --------------------------------------------------------------------------- #
# negative results stay evidence
# --------------------------------------------------------------------------- #
def test_failed_leg_is_recorded_with_exit_code_1(tmp_path):
    def prose(slug):
        return "trop court" if slug == "rent-default" else PASSING_PROSE[slug]

    clock = FakeClock()
    leg_runner, _ = _runner(clock, prose=prose)
    summary, code = ci.run_legs(
        "38600271324", mode="live", out_dir=tmp_path / "rc", leg_runner=leg_runner,
        monotonic=clock.monotonic, wall=clock.wall, deadline_seconds=10_000)
    assert code == 1
    assert summary["legs_failed"] == ["rent-default"]
    assert summary["legs_complete"] is True
    failed = next(r for r in summary["legs"] if r["slug"] == "rent-default")
    assert any(g["gate"] == "truth::rent-default" and not g["passed"] for g in failed["gates"])


def test_leg_exception_is_recorded_not_raised(tmp_path):
    def boom(slug, mode, top_n, evidence_count, max_cites):
        raise RuntimeError("upstream OpenCaseLaw unreachable")

    summary, code = ci.run_legs(
        "38600271324", mode="live", slugs=["rent-default"], out_dir=tmp_path / "rc",
        leg_runner=boom, monotonic=lambda: 0.0, wall=lambda: 1_700_000_000.0,
        deadline_seconds=10_000)
    assert code == 1
    rec = summary["legs"][0]
    assert "upstream OpenCaseLaw unreachable" in json.dumps(rec["gates"])


def test_unknown_leg_is_rejected(tmp_path):
    try:
        ci.run_legs("38600271324", slugs=["not-a-leg"], out_dir=tmp_path / "rc")
    except ValueError as exc:
        assert "unknown leg" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("unknown leg must be rejected")


def test_unsafe_run_id_is_rejected():
    for bad in ("../escape", "a b", "x" * 41):
        try:
            ci.resolve_run_id(bad)
        except ValueError:
            continue
        raise AssertionError(f"unsafe run id accepted: {bad!r}")  # pragma: no cover

def test_preflight_imports_clean_env_returns_empty():
    """In an installed environment the preflight must report no missing packages."""
    assert ci.preflight_imports() == []


def test_main_exits_4_when_preflight_fails(monkeypatch):
    """A dependency miss must fail once, loudly, instead of four poisoned legs.

    Run 38604340726 attempt 1 recorded four fatal ModuleNotFoundError legs on a
    fresh runner; the preflight converts that into a single actionable error.
    """
    monkeypatch.setattr(ci, "preflight_imports", lambda: ["numpy", "scikit-learn"])
    rc = ci.main(["--run-id", "38604340726", "--mode", "live", "--plan-only"])
    assert rc == 0  # plan-only stays dependency-free
    monkeypatch.setattr(ci, "run_legs", lambda *a, **k: (_ for _ in ()).throw(
        AssertionError("run_legs must not run when preflight fails")))
    rc = ci.main(["--run-id", "38604340726", "--mode", "live"])
    assert rc == 4

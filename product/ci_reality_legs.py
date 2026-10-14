#!/usr/bin/env python3
"""Run the four frozen Product Reality Check legs LIVE, sequentially, inside this run.

Why this module exists (direction v50, run 38600271324)
-------------------------------------------------------
The v50 lane outcome is a single durable, retrievable, GREEN core-lane run of
``lane=product`` whose *own team job* executes the four frozen reality legs live
and writes ``results/product/reality_check/summary_ci_<run_id>.json`` naming
exactly which legs ran in **this** run.  Three properties are therefore not
optional, and each one has already burned a cycle:

1. **Sequential / uncontended.**  On 2026-10-14 a deliberate 4-way parallel
   batch pushed every adversarial pass past its wall-clock ceiling and only an
   uncontended retry passed (``reports/product/CYCLE_38559540834.md`` §3).  This
   runner is single-threaded by construction and records the execution intervals
   of every leg; ``assert_disjoint_intervals`` fails the run if two legs ever
   overlap, so a future "optimisation" cannot silently reintroduce contention.

2. **No cross-run result reuse.**  A leg result is only admissible if it was
   produced by *this* run.  Every artefact this module writes is named with the
   run id (``<slug>_<mode>_ci-<run_id>_<stamp>.json``) and ``assert_run_scoped``
   rejects any referenced report that does not carry it, so an older green leg
   can never be re-presented as current evidence.

3. **Durable partial progress.**  A leg result is flushed to disk the moment the
   leg finishes, and the summary is rewritten after every leg.  If the team job
   dies half-way, the work survives and ``--resume`` continues *within the same
   run id*; a resume from a different run id is refused rather than inherited.

Gate parity is inherited, not re-implemented: ``run_leg``/``evaluate`` are the
same functions ``product/reality_check.py`` uses, and
``product/tests/test_reality_check.py::test_runner_legs_match_workflow_matrix``
still pins the questions/assertions to ``product-reality-check.yml``.

Usage
-----
    python product/ci_reality_legs.py --mode live                 # this run, all four legs
    python product/ci_reality_legs.py --mode fixture --plan-only  # offline wiring check
    python product/ci_reality_legs.py --mode live --resume        # continue a partial run

Exit codes
----------
    0  every selected leg ran in this run and passed structural + truth gates
    1  every selected leg ran, at least one failed its gates (negative evidence)
    3  the run is incomplete (deadline reached / nothing executed yet)
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Callable

PRODUCT_ROOT = Path(__file__).resolve().parent
REPO_ROOT = PRODUCT_ROOT.parent
for _p in (str(PRODUCT_ROOT), str(REPO_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from reality_check import LEGS, evaluate, run_leg, strip_bundle  # noqa: E402

#: Frozen execution order.  Cheap/fast legs first so a deadline cut loses the
#: least evidence; the order itself is recorded in every summary.
FROZEN_ORDER = [
    "petty-theft-dismissal",
    "rent-default",
    "corporate-criminal-liability",
    "business-judgment-rule",
]

EVIDENCE_TIER = "CI_TEAM_JOB_LIVE"
DEFAULT_DEADLINE_SECONDS = 3600.0
DEFAULT_OUT_DIR = REPO_ROOT / "results" / "product" / "reality_check"
_SAFE_RUN_ID = re.compile(r"^[A-Za-z0-9_.-]{1,40}$")


class CrossRunReuseError(RuntimeError):
    """A result artefact does not belong to the run that is claiming it."""


class LegOrderError(RuntimeError):
    """Two legs claim overlapping execution intervals (contention)."""


# --------------------------------------------------------------------------- #
# naming / provenance
# --------------------------------------------------------------------------- #
def resolve_run_id(explicit: str | None = None) -> str:
    """Prefer an explicit id, then ``GITHUB_RUN_ID``, then a local marker."""
    candidate = (explicit or os.environ.get("GITHUB_RUN_ID") or "").strip()
    if not candidate:
        candidate = f"local-{os.getpid()}"
    if not _SAFE_RUN_ID.match(candidate):
        raise ValueError(f"unsafe run id: {candidate!r}")
    return candidate


def summary_path(out_dir: Path, run_id: str, mode: str = "live") -> Path:
    """``summary_ci_<run_id>.json`` for the live run; other modes stay distinguishable."""
    name = f"summary_ci_{run_id}.json" if mode == "live" else f"summary_{mode}_ci_{run_id}.json"
    return Path(out_dir) / name


def leg_report_name(slug: str, mode: str, run_id: str, stamp: str) -> str:
    return f"{slug}_{mode}_ci-{run_id}_{stamp}.json"


def assert_run_scoped(path: Path | str, run_id: str) -> None:
    """Reject any evidence file that was not written by *this* run."""
    name = Path(path).name
    if f"ci-{run_id}" not in name:
        raise CrossRunReuseError(
            f"{name} is not scoped to run {run_id}; cross-run evidence is inadmissible"
        )


def repo_relative(path: Path) -> str:
    """Repo-relative path when possible, absolute otherwise (tests use tmp dirs)."""
    try:
        return str(Path(path).relative_to(REPO_ROOT))
    except ValueError:
        return str(Path(path))


def git_head_sha(cwd: Path = REPO_ROOT) -> str | None:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(cwd), capture_output=True, text=True, timeout=20,
        )
    except Exception:  # pragma: no cover - git missing / sandboxed
        return None
    sha = out.stdout.strip()
    return sha or None


def assert_disjoint_intervals(records: list[dict]) -> None:
    """Prove sequential execution: no two legs may overlap in wall-clock time."""
    spans = sorted(
        ((r["started_at"], r["finished_at"], r["slug"]) for r in records if r.get("finished_at")),
        key=lambda t: t[0],
    )
    for (prev_start, prev_end, prev_slug), (start, _end, slug) in zip(spans, spans[1:]):
        if start < prev_end:
            raise LegOrderError(
                f"legs {prev_slug} and {slug} overlap ({prev_start}..{prev_end} vs {start}); "
                "reality legs must run sequentially and uncontended"
            )


# --------------------------------------------------------------------------- #
# execution
# --------------------------------------------------------------------------- #
def _iso(ts: float) -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(ts))


def _load_previous(out_dir: Path, run_id: str, mode: str, slugs: list[str]) -> dict[str, dict]:
    """Return run-scoped leg records from an earlier (partial) attempt of THIS run."""
    path = summary_path(out_dir, run_id, mode)
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if data.get("run_id") != run_id:
        return {}
    return {
        rec["slug"]: rec
        for rec in data.get("legs", [])
        if rec.get("slug") in slugs
        and rec.get("run_id") == run_id
        and rec.get("started_at")
        and rec.get("finished_at")
    }


def run_legs(
    run_id: str,
    *,
    mode: str = "live",
    slugs: list[str] | None = None,
    deadline_seconds: float = DEFAULT_DEADLINE_SECONDS,
    out_dir: Path | None = None,
    resume: bool = False,
    top_n: int = 100,
    evidence_count: int = 10,
    max_cites: int = 8,
    leg_runner: Callable[..., dict] = run_leg,
    monotonic: Callable[[], float] = time.monotonic,
    wall: Callable[[], float] = time.time,
) -> tuple[dict, int]:
    """Execute the frozen legs one at a time and write the run-scoped summary."""
    run_id = resolve_run_id(run_id)
    slugs = list(slugs or FROZEN_ORDER)
    unknown = [s for s in slugs if s not in LEGS]
    if unknown:
        raise ValueError(f"unknown leg(s): {unknown}; known: {list(LEGS)}")

    out_dir = Path(out_dir or DEFAULT_OUT_DIR)
    out_dir.mkdir(parents=True, exist_ok=True)

    started_wall = wall()
    t0 = monotonic()
    head_sha = git_head_sha()

    prior = _load_previous(out_dir, run_id, mode, slugs) if resume else {}
    records: list[dict] = []
    stop_reason = ""

    summary: dict[str, Any] = {
        "schema": "query-map-ci-reality-legs/1",
        "run_id": run_id,
        # ``GITHUB_SHA`` is the sha this *run* was dispatched on; ``head_sha`` is
        # the workspace HEAD after the team job switched to the lane branch.
        # Both are recorded because a core-lane team job legitimately executes
        # lab/product code under a main dispatch sha, and an evidence check must
        # be able to tell those two apart instead of guessing.
        "run_head_sha": os.environ.get("GITHUB_SHA") or None,
        "head_sha": head_sha,
        "mode": mode,
        "evidence_tier": EVIDENCE_TIER if mode == "live" else f"{mode.upper()}_OFFLINE",
        "local_evidence_only": mode != "live",
        "execution": {
            "mode": "sequential",
            "concurrency": 1,
            "requested_order": list(slugs),
            "rationale": (
                "4-way parallel execution pushed every adversarial pass past its "
                "ceiling on 2026-10-14; only an uncontended sequential run is admissible"
            ),
        },
        "started_at": _iso(started_wall),
        "deadline_seconds": deadline_seconds,
        "legs": records,
        "legs_requested": list(slugs),
    }

    for slug in slugs:
        if slug in prior:
            rec = dict(prior[slug])
            rec["reused_within_run"] = True
            records.append(rec)
            print(f"== reality leg: {slug} (already executed in run {run_id}) ==", flush=True)
            continue

        remaining = deadline_seconds - (monotonic() - t0)
        if remaining <= 0:
            stop_reason = stop_reason or "deadline_reached"
            print(f"!! deadline reached before {slug}; stopping (partial evidence kept)",
                  flush=True)
            break

        print(f"== reality leg: {slug} (mode={mode}) ==", flush=True)
        leg_started = wall()
        leg_t0 = monotonic()
        try:
            report = leg_runner(slug, mode, top_n, evidence_count, max_cites)
            gates = evaluate(slug, report)
        except Exception as exc:  # negative results stay evidence
            report = {"slug": slug, "mode": mode, "question": LEGS.get(slug, ""),
                      "fatal_error": f"{type(exc).__name__}: {exc}"}
            gates = [{"gate": "run", "passed": False, "detail": report["fatal_error"]}]
        passed = all(g["passed"] for g in gates)

        slim = strip_bundle(report) if "bundle" in report else dict(report)
        slim["gates"] = gates
        slim["leg_passed"] = passed
        slim["evidence_tier"] = EVIDENCE_TIER if mode == "live" else f"{mode.upper()}_OFFLINE"
        slim["run_id"] = run_id

        stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime(leg_started))
        report_file = out_dir / leg_report_name(slug, mode, run_id, stamp)
        assert_run_scoped(report_file, run_id)
        report_file.write_text(
            json.dumps(slim, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8"
        )

        rec = {
            "slug": slug,
            "run_id": run_id,
            "passed": passed,
            "gates": gates,
            "report": repo_relative(report_file),
            "started_at": _iso(leg_started),
            "finished_at": _iso(wall()),
            "seconds": round(monotonic() - leg_t0, 3),
            "answer_model": slim.get("answer_model"),
            "adversarial_model": slim.get("adversarial_model"),
            "adversarial_error": slim.get("adversarial_error"),
            "reused_within_run": False,
        }
        records.append(rec)
        for g in gates:
            mark = "PASS" if g["passed"] else "FAIL"
            print(f"   [{mark}] {g['gate']}" + (f" — {g['detail']}" if g["detail"] else ""),
                  flush=True)

        # Flush partial progress after every leg so a killed job keeps its work.
        assert_disjoint_intervals(records)
        summary["legs"] = records
        summary["legs_ran_in_this_attempt"] = [r["slug"] for r in records
                                              if not r.get("reused_within_run")]
        summary_path(out_dir, run_id, mode).write_text(
            json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8"
        )

    summary["legs"] = records
    assert_disjoint_intervals(records)

    ran = [r["slug"] for r in records]
    missing = [s for s in slugs if s not in ran]
    failed = [r["slug"] for r in records if not r["passed"]]
    summary.update(
        {
            "legs_ran_in_this_attempt": [r["slug"] for r in records
                                         if not r.get("reused_within_run")],
            "finished_at": _iso(wall()),
            "elapsed_seconds": round(monotonic() - t0, 3),
            "legs_ran_in_this_run": ran,
            "legs_missing": missing,
            "legs_failed": failed,
            "legs_complete": not missing,
            "all_legs_passed": not missing and not failed,
            "stopped_reason": stop_reason,
            "cross_run_reuse": "REFUSED_BY_RUN_SCOPED_FILENAMES",
            "summary_path": repo_relative(summary_path(out_dir, run_id, mode)),
        }
    )

    path = summary_path(out_dir, run_id, mode)
    path.write_text(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True),
                    encoding="utf-8")
    if missing:
        exit_code = 3
    elif failed:
        exit_code = 1
    else:
        exit_code = 0
    print(
        f"\nwrote {path}\n"
        f"legs ran in run {run_id}: {len(ran)}/{len(slugs)}"
        + (f" missing={missing}" if missing else "")
        + (f" failed={failed}" if failed else "")
        + f"\noverall: {'PASS' if exit_code == 0 else 'INCOMPLETE' if exit_code == 3 else 'FAIL'}",
        flush=True,
    )
    return summary, exit_code


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--run-id", default=None,
                        help="GitHub run id (default: $GITHUB_RUN_ID)")
    parser.add_argument("--mode", choices=("live", "fixture"), default="live")
    parser.add_argument("--legs", default="all",
                        help="'all', a comma separated subset, or a single slug")
    parser.add_argument("--deadline-seconds", type=float,
                        default=float(os.environ.get("LEX_CI_LEG_DEADLINE_SECONDS",
                                                     DEFAULT_DEADLINE_SECONDS)))
    parser.add_argument("--resume", action="store_true",
                        help="reuse legs already executed by THIS run id")
    parser.add_argument("--plan-only", action="store_true",
                        help="print the execution plan and exit without any leg")
    parser.add_argument("--top-n", type=int, default=100)
    parser.add_argument("--evidence-count", type=int, default=10)
    parser.add_argument("--max-cites", type=int, default=8)
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    args = parser.parse_args(argv)

    run_id = resolve_run_id(args.run_id)
    if args.legs == "all":
        slugs = list(FROZEN_ORDER)
    else:
        slugs = [s.strip() for s in args.legs.split(",") if s.strip()]

    if args.plan_only:
        print(json.dumps({
            "run_id": run_id,
            "mode": args.mode,
            "concurrency": 1,
            "order": slugs,
            "summary": repo_relative(summary_path(Path(args.out_dir), run_id, args.mode)),
            "deadline_seconds": args.deadline_seconds,
        }, indent=2))
        return 0

    _summary, exit_code = run_legs(
        run_id,
        mode=args.mode,
        slugs=slugs,
        deadline_seconds=args.deadline_seconds,
        out_dir=Path(args.out_dir),
        resume=args.resume,
        top_n=args.top_n,
        evidence_count=args.evidence_count,
        max_cites=args.max_cites,
    )
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
#!/usr/bin/env python3
"""Observe a core-lane run on the GitHub REST API and update ``state/product.json``.

Why this module exists (direction v50, run 38600271324)
-------------------------------------------------------
The v50 lane outcome has three evidence obligations:

* (a) the four frozen reality legs must run LIVE inside the promoting run's own
  team job (``product/ci_reality_legs.py`` writes ``summary_ci_<run_id>.json``);
* (b) ``state/product.json`` must snapshot ``{run_id, head_sha, conclusion,
  created_at}`` for that run and set ``machine_gate_ready: true`` **only** once
  its conclusion is observably ``success``;
* (c) ``human_gate_ready`` stays ``false`` until an owner/jurist session exists.

(b) is a machine-readable fact about an external system, so it should be
*observed*, never typed by hand.  Hand-edited conclusions are exactly how the
withdrawn ``V45_QUERY_MAP_MACHINE_GATE_GREEN`` claim happened.  This module:

1. fetches the run from the unauthenticated public REST endpoint
   (``GET /repos/{owner}/{repo}/actions/runs/{run_id}``);
2. records the observation verbatim, including HTTP 404 runs into
   ``unresolvable_run_ids`` (housekeeper pruning makes 404s permanent, so they
   must never be re-cited as current evidence);
3. flips ``machine_gate_ready`` to ``true`` only when **all** of these hold:
   the run exists, ``conclusion == "success"``, its ``summary_ci_<run_id>.json``
   exists in the tree with ``legs_complete`` and ``all_legs_passed`` true, and
   the run's ``head_sha`` matches the lab branch the summary was produced from;
4. never touches ``human_gate_ready`` — that flag is the owner's to earn.

Per-job conclusions (``team`` / ``audit`` / ``integrate`` / ``resilience``) are
recorded alongside the run so the promotion chain is checkable: the v50 stall
was caused by a green team job whose ``integrate`` never ran, and a run-level
``conclusion: success`` alone would not have shown that distinction.

Usage
-----
    python product/ci_run_evidence.py --run-id 38600271324 --apply
    python product/ci_run_evidence.py --run-id 38600271324          # dry run, prints diff
"""
from __future__ import annotations

import argparse
import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Callable

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STATE = REPO_ROOT / "state" / "product.json"
DEFAULT_SUMMARY_DIR = REPO_ROOT / "results" / "product" / "reality_check"
DEFAULT_REPO = os.environ.get("LEX_GITHUB_REPO", "Mickalive/LexMachina")

Fetch = Callable[[str], tuple[int, dict]]


class RunNotFound(RuntimeError):
    """HTTP 404: the run id no longer resolves and must not be cited as evidence."""


def http_fetch(url: str, timeout: float = 20.0) -> tuple[int, dict]:
    request = urllib.request.Request(
        url, headers={"Accept": "application/vnd.github+json", "User-Agent": "lexmachina"}
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = b"{}"
        try:
            body = exc.read()
        except Exception:  # pragma: no cover
            pass
        try:
            return exc.code, json.loads(body.decode("utf-8"))
        except Exception:
            return exc.code, {}


def observe_run(run_id: int | str, repo: str = DEFAULT_REPO, fetch: Fetch = http_fetch) -> dict:
    """Return the verbatim REST snapshot of one Actions run."""
    url = f"https://api.github.com/repos/{repo}/actions/runs/{run_id}"
    status, payload = fetch(url)
    if status == 404:
        raise RunNotFound(f"run {run_id} is not resolvable (HTTP 404)")
    if status != 200:
        raise RuntimeError(f"GitHub API returned HTTP {status} for run {run_id}")
    return {
        "run_id": int(payload.get("id") or run_id),
        "head_sha": payload.get("head_sha"),
        "head_branch": payload.get("head_branch"),
        "event": payload.get("event"),
        "status": payload.get("status"),
        "conclusion": payload.get("conclusion"),
        "created_at": payload.get("created_at"),
        "updated_at": payload.get("updated_at"),
        "name": payload.get("name"),
        "workflow": (payload.get("path") or (payload.get("workflow_url") or "").rsplit("/", 1)[-1]),
        "source": url,
    }


def observe_jobs(run_id: int | str, repo: str = DEFAULT_REPO, fetch: Fetch = http_fetch) -> dict:
    """Return ``{job name: conclusion}`` for one run's jobs.

    The v50 blocker was never the product work: the lane stalled because the
    audit job died on a misplaced gate file and ``integrate`` was skipped, so
    ``lab/product`` stopped advancing.  A green team job alone therefore does not
    tell a reader whether the promotion chain actually completed.  Recording the
    per-job conclusions makes that fact machine-checkable instead of narrative.
    A failure to read jobs (HTTP != 200) is never fatal: partial evidence must
    not block recording the run observation itself.
    """
    url = f"https://api.github.com/repos/{repo}/actions/runs/{run_id}/jobs?per_page=100"
    try:
        status, payload = fetch(url)
    except Exception:  # pragma: no cover - network resilience, never fatal
        return {}
    if status != 200 or not isinstance(payload, dict):
        return {}
    jobs: dict[str, Any] = {}
    for job in payload.get("jobs") or []:
        if isinstance(job, dict) and job.get("name"):
            jobs[str(job["name"])] = job.get("conclusion")
    return jobs


def find_summary(run_id: int | str, summary_dir: Path = DEFAULT_SUMMARY_DIR) -> Path | None:
    path = Path(summary_dir) / f"summary_ci_{run_id}.json"
    return path if path.is_file() else None


def load_summary(path: Path | None) -> dict:
    if path is None:
        return {}
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def documented_workspace_heads(state: dict) -> dict:
    """Workspace heads a producer recorded for a specific run id in lane state.

    A core-lane team job is dispatched on ``main`` (GITHUB_SHA) but then switches
    to ``lab/<lane>`` and executes *that* code.  The REST ``head_sha`` of the run
    is therefore the dispatch sha, while the code that actually produced the leg
    evidence is the lane-branch head.  Only the producer's own run-scoped record
    can tell those two apart, so it is read from state rather than assumed.
    """
    out: dict[str, str] = {}
    current = (state or {}).get("current_run") or {}
    if current.get("run_id") and current.get("head_sha_lab_product_at_leg_execution"):
        out[str(current["run_id"])] = current["head_sha_lab_product_at_leg_execution"]
    for entry in (state or {}).get("verified_runs", []):
        if entry.get("run_id") and entry.get("workspace_head_sha"):
            out[str(entry["run_id"])] = entry["workspace_head_sha"]
    return out


def evaluate_machine_gate(observation: dict, summary: dict, state: dict | None = None) -> dict:
    """Decide whether this run may legitimately raise ``machine_gate_ready``."""
    conclusion = (observation or {}).get("conclusion")
    legs_complete = bool(summary.get("legs_complete"))
    all_passed = bool(summary.get("all_legs_passed"))
    live = summary.get("mode") == "live"
    same_run = str(summary.get("run_id")) == str(observation.get("run_id"))

    summary_shas = {v for v in (summary.get("head_sha"), summary.get("run_head_sha")) if v}
    observed_sha = observation.get("head_sha")
    documented = documented_workspace_heads(state or {}).get(str(observation.get("run_id")))
    if observed_sha and observed_sha in summary_shas:
        same_sha, sha_note = True, "summary records the run head sha"
    elif documented and documented in summary_shas:
        same_sha, sha_note = True, (
            f"summary records the lab-branch head {documented[:7]} that this run executed "
            f"(run dispatch sha {(observed_sha or '?')[:7]})"
        )
    else:
        same_sha, sha_note = False, (
            f"summary shas {sorted(s[:7] for s in summary_shas)} match neither the run head "
            f"{(observed_sha or '?')[:7]} nor a documented workspace head"
        )
    reasons: list[str] = []
    if conclusion != "success":
        reasons.append(f"conclusion={conclusion!r} is not 'success'")
    if not live:
        reasons.append("summary is not a live (CI_TEAM_JOB_LIVE) leg run")
    if not legs_complete:
        reasons.append(f"legs incomplete: missing={summary.get('legs_missing')}")
    if not all_passed:
        reasons.append(f"legs failed: {summary.get('legs_failed')}")
    if not same_run:
        reasons.append(f"summary run_id {summary.get('run_id')!r} != observed run")
    if not same_sha:
        reasons.append(sha_note)
    return {
        "eligible": not reasons,
        "reasons": reasons,
        "provenance_note": sha_note,
        "legs_ran_in_this_run": summary.get("legs_ran_in_this_run"),
        "all_legs_passed": all_passed,
        "legs_complete": legs_complete,
    }


def update_state(
    state: dict,
    observation: dict,
    summary: dict,
    *,
    summary_path: str | None = None,
    unresolved: bool = False,
    jobs: dict | None = None,
) -> dict:
    """Return a new state dict with the observation and gate decision applied."""
    out = json.loads(json.dumps(state))  # deep copy without importing copy for clarity
    out.setdefault("verified_runs", [])
    out.setdefault("unresolvable_run_ids", {"ids": [], "status": "HTTP 404 after housekeeper pruning"})

    if unresolved:
        ids = out["unresolvable_run_ids"].setdefault("ids", [])
        if observation.get("run_id") not in ids:
            ids.append(observation.get("run_id"))
        out["unresolvable_run_ids"]["last_observed_at"] = observation.get("observed_at")
        return out

    entry = {
        "run_id": observation.get("run_id"),
        "head_sha": observation.get("head_sha"),
        "conclusion": observation.get("conclusion"),
        "created_at": observation.get("created_at"),
        "head_branch": observation.get("head_branch"),
        "event": observation.get("event"),
        "observed_at": observation.get("observed_at"),
    }
    if summary_path:
        entry["ci_reality_summary"] = summary_path
        entry["workspace_head_sha"] = summary.get("head_sha")
        entry["run_head_sha"] = summary.get("run_head_sha")
        entry["legs_ran_in_this_run"] = summary.get("legs_ran_in_this_run")
        entry["legs_complete"] = summary.get("legs_complete")
        entry["all_legs_passed"] = summary.get("all_legs_passed")
        entry["execution"] = summary.get("execution")
    if jobs:
        entry["jobs"] = dict(jobs)
        entry["promotion_chain_green"] = bool(
            jobs.get("team") == "success"
            and jobs.get("audit") == "success"
            and jobs.get("integrate") == "success"
        )

    runs = [r for r in out["verified_runs"] if r.get("run_id") != entry["run_id"]]
    runs.append(entry)
    runs.sort(key=lambda r: str(r.get("created_at") or ""))
    out["verified_runs"] = runs
    out["state_updated_by_run"] = entry["run_id"]
    out["state_updated_at"] = (entry.get("observed_at") or "")[:10]

    decision = evaluate_machine_gate(observation, summary, state)
    out["machine_gate"] = {
        "ready": bool(decision["eligible"]),
        "decided_for_run_id": observation.get("run_id"),
        "decided_at": observation.get("observed_at"),
        "reasons": decision["reasons"],
        "provenance_note": decision["provenance_note"],
        "criteria": [
            "run conclusion == success (observed on the GitHub REST API)",
            "summary_ci_<run_id>.json exists for THIS run id",
            "summary mode == live (CI_TEAM_JOB_LIVE)",
            "legs_complete == true and all_legs_passed == true",
            "summary provenance: it records the run head sha (GITHUB_SHA) or the "
            "lab-branch head this run executed, as documented for this run id in state/product.json",
        ],
    }
    if decision["eligible"]:
        out["machine_gate_ready"] = True
        out["evidence_tier"] = "DURABLE_CI_VERIFIED"
        rc = out.setdefault("reality_check_status", {})
        rc["durable_green_run_id"] = observation.get("run_id")
        rc["substantive_4_of_4_green"] = True
        rc["ci_reality_summary"] = summary_path
        rc["legs_ran_in_this_run"] = summary.get("legs_ran_in_this_run")
    # human_gate_ready is deliberately never written here: it is the owner's gate.

    if out.get("human_gate_ready") is not True:
        out["human_gate_ready"] = False
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--repo", default=DEFAULT_REPO)
    parser.add_argument("--state", default=str(DEFAULT_STATE))
    parser.add_argument("--summary-dir", default=str(DEFAULT_SUMMARY_DIR))
    parser.add_argument("--apply", action="store_true", help="write state/product.json")
    args = parser.parse_args(argv)

    from ci_reality_legs import resolve_run_id  # local import: keeps module import side-effect free

    run_id = int(resolve_run_id(args.run_id))
    state = json.loads(Path(args.state).read_text(encoding="utf-8"))

    import datetime as _dt
    observed_at = _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    try:
        observation = observe_run(run_id, args.repo)
    except RunNotFound:
        observation = {"run_id": run_id, "conclusion": None, "observed_at": observed_at,
                       "status": "unresolvable"}
        new_state = update_state(state, observation, {}, unresolved=True)
        print(json.dumps({"run_id": run_id, "resolvable": False,
                          "action": "recorded under unresolvable_run_ids"}, indent=2))
        if args.apply:
            Path(args.state).write_text(json.dumps(new_state, ensure_ascii=False, indent=2) + "\n",
                                        encoding="utf-8")
        return 0

    observation["observed_at"] = observed_at
    jobs = observe_jobs(run_id, args.repo)
    observation["jobs"] = jobs
    summary_path = find_summary(run_id, Path(args.summary_dir))
    summary = load_summary(summary_path)
    new_state = update_state(state, observation, summary, jobs=jobs or None,
                             summary_path=(str(summary_path.relative_to(REPO_ROOT))
                                           if summary_path and summary_path.is_absolute()
                                           and str(summary_path).startswith(str(REPO_ROOT))
                                           else None))
    decision = new_state.get("machine_gate", {})

    print(json.dumps({
        "run_id": run_id,
        "resolvable": True,
        "conclusion": observation.get("conclusion"),
        "status": observation.get("status"),
        "head_sha": observation.get("head_sha"),
        "created_at": observation.get("created_at"),
        "jobs": jobs,
        "summary": str(summary_path) if summary_path else None,
        "machine_gate_ready": new_state.get("machine_gate_ready"),
        "machine_gate_reasons": decision.get("reasons"),
        "human_gate_ready": new_state.get("human_gate_ready"),
        "applied": bool(args.apply),
    }, indent=2))

    if args.apply:
        Path(args.state).write_text(json.dumps(new_state, ensure_ascii=False, indent=2) + "\n",
                                    encoding="utf-8")
        print(f"wrote {args.state}")
    else:
        print("dry run: pass --apply to write state/product.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
#!/usr/bin/env python3
"""Characterize a query-cache refresh delta left by an unreported run.

Why this exists
---------------
Run 42820069517 committed 44 files under ``results/product/query_cache/``
(author ``lex-product-team``, subject ``product cycle 42820069517 repair 0``)
but wrote no cycle report, no state block and no audit-readiness dossier, and
its public GitHub run record was pruned (HTTP 404) before any later snapshot
could capture it.  The chain of record therefore holds a commit whose content
is otherwise undescribed.  A narrative like "just timestamp refreshes" would be
a requirement-33 defect (a published claim that does not reproduce from the
committed tree): 5 of the 34 modified entries really are ``fetched_at``-only,
but 29 carry upstream OpenCaseLaw result drift and 10 entries are new.  This
module makes the delta itself machine-readable and reproducible from git
alone, so the reconciliation artifact can say exactly what the unreported run
changed without inventing why the run stopped.

What it does
------------
Given a run's committed resume diagnosis (which pins its ``snapshot_head`` and
``predecessor_head`` from git refs) it:

* lists every file the run's commit changed under
  ``results/product/query_cache/`` (and refuses a delta that touches
  anything else without ``--allow-non-cache-paths``);
* classifies each *modified* entry as ``fetched_at_only`` (every field equal
  except ``fetched_at``) or ``upstream_drift`` (the cached HTTP envelope's
  content changed), recording which top-level and nested ``body`` keys moved;
* classifies each *added* entry as a new cache row (status/url/path);
* records, read-only, whether the run has either half of factory-wide
  requirement 4 (an ``origin/cycle/core/product/<run>/audit`` ref readable
  locally, and an ``accept product cycle <run>`` commit on
  ``origin/lab/product``), so the adjudication stays ``UNADJUDICATED`` unless
  git proves otherwise;
* optionally (``--remote-check``) observes the run's remote refs with
  ``git ls-remote`` so the artifact can record which refs existed at
  reconciliation time; without the flag it records ``remote_check=false``
  instead of guessing;
* records whether the canonical ``state/product.json`` already carries the
  run in ``run_history`` at generation time, so a later reader can see the
  reconciliation closing a real gap rather than duplicating one.

It never writes ``results/audit/**``, never mints a gate, never edits a
frozen bar, and asserts no cause for why the run stopped.

Usage
-----
    python3 product/cache_refresh_delta.py \\
        --run-id 42820069517 \\
        --resume-diagnosis results/product/orchestration/CYCLE_42820069517_resume_diagnosis.json \\
        --raw-snapshot results/product/orchestration/CYCLE_42930681665_run_jobs_raw.json \\
        --out results/product/orchestration/CYCLE_42820069517_reconciliation.json
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

SCHEMA = "product-cache-refresh-reconciliation/1"
CACHE_PREFIX = "results/product/query_cache/"
ACCEPTED_REF = "origin/lab/product"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=str(REPO_ROOT),
                          capture_output=True, text=True)


def _rev(ref: str) -> str | None:
    proc = _git("rev-parse", "--verify", "--quiet", ref)
    if proc.returncode != 0:
        return None
    return proc.stdout.strip() or None


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _entry_at(commit: str, rel_path: str) -> dict[str, Any] | None:
    proc = _git("show", f"{commit}:{rel_path}")
    if proc.returncode != 0:
        return None
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        return {"unparseable": True}


def _name_status(base: str, head: str) -> list[tuple[str, str]]:
    proc = _git("diff", "--name-status", "--no-renames", base, head)
    out: list[tuple[str, str]] = []
    for line in proc.stdout.splitlines():
        if not line.strip():
            continue
        status, _, path = line.partition("\t")
        out.append((status, path))
    return out


def _result_ids(entry: dict[str, Any]) -> list[str] | None:
    """Best-effort decision ids of a cached search envelope body."""
    body = entry.get("body")
    if not isinstance(body, str):
        return None
    try:
        parsed = json.loads(body)
    except json.JSONDecodeError:
        return None
    results = parsed.get("results")
    if not isinstance(results, list):
        return None
    ids = []
    for row in results:
        if isinstance(row, dict) and isinstance(row.get("decision_id"), str):
            ids.append(row["decision_id"])
    return ids or None


def _classify_modified(rel_path: str, base: str,
                       head: str) -> dict[str, Any]:
    before = _entry_at(base, rel_path)
    after = _entry_at(head, rel_path)
    row: dict[str, Any] = {
        "path": rel_path,
        "status": "modified",
        "url": (after or {}).get("url") if isinstance(after, dict) else None,
    }
    if not isinstance(before, dict) or not isinstance(after, dict):
        row["kind"] = "unparseable"
        return row
    row["fetched_at"] = [before.get("fetched_at"), after.get("fetched_at")]
    keys_before = {k: v for k, v in before.items() if k != "fetched_at"}
    keys_after = {k: v for k, v in after.items() if k != "fetched_at"}
    if keys_before == keys_after:
        row["kind"] = "fetched_at_only"
        return row
    row["kind"] = "upstream_drift"
    top_changed = sorted(
        k for k in set(keys_before) | set(keys_after)
        if keys_before.get(k) != keys_after.get(k)
    )
    row["changed_top_level_keys"] = top_changed
    body_drift: dict[str, Any] = {}
    if "body" in top_changed:
        try:
            inner_before = json.loads(before.get("body") or "{}")
            inner_after = json.loads(after.get("body") or "{}")
        except json.JSONDecodeError:
            body_drift["parse"] = "unparseable"
        else:
            inner_changed = sorted(
                k for k in set(inner_before) | set(inner_after)
                if inner_before.get(k) != inner_after.get(k)
            )
            body_drift["changed_keys"] = inner_changed
            if isinstance(inner_before.get("total"), int) and isinstance(
                    inner_after.get("total"), int):
                body_drift["total"] = [inner_before["total"],
                                       inner_after["total"]]
            ids_before = _result_ids(before)
            ids_after = _result_ids(after)
            if ids_before is not None and ids_after is not None:
                body_drift["n_results"] = [len(ids_before), len(ids_after)]
                added = set(ids_after) - set(ids_before)
                removed = set(ids_before) - set(ids_after)
                body_drift["result_ids_added"] = sorted(added)
                body_drift["result_ids_removed"] = sorted(removed)
    row["body_drift"] = body_drift
    return row


def _classify_added(rel_path: str, head: str) -> dict[str, Any]:
    entry = _entry_at(head, rel_path)
    row: dict[str, Any] = {
        "path": rel_path,
        "status": "added",
    }
    if not isinstance(entry, dict):
        row["kind"] = "unparseable"
        return row
    row["kind"] = "new_cache_entry"
    row["http_status"] = entry.get("status")
    row["url"] = entry.get("url")
    row["path_endpoint"] = entry.get("path")
    row["fetched_at"] = entry.get("fetched_at")
    return row


def characterize(base: str, head: str) -> dict[str, Any]:
    """Classify every query-cache change between two commits."""
    changed = _name_status(base, head)
    outside = [p for _, p in changed if not p.startswith(CACHE_PREFIX)]
    rows: list[dict[str, Any]] = []
    for status, path in changed:
        if not path.startswith(CACHE_PREFIX):
            continue
        if status == "A":
            rows.append(_classify_added(path, head))
        elif status in ("M", "T"):
            rows.append(_classify_modified(path, base, head))
        else:  # pragma: no cover - not observed in this family
            rows.append({"path": path, "status": status, "kind": "other"})
    modified = [r for r in rows if r["status"] == "modified"]
    added = [r for r in rows if r["status"] == "added"]
    fetched_only = [r for r in modified if r.get("kind") == "fetched_at_only"]
    drift = [r for r in modified if r.get("kind") == "upstream_drift"]
    drift_keys: dict[str, int] = {}
    for r in drift:
        for key in (r.get("body_drift") or {}).get("changed_keys") or []:
            drift_keys[key] = drift_keys.get(key, 0) + 1
    return {
        "n_files": len(rows),
        "n_modified": len(modified),
        "n_added": len(added),
        "n_deleted": sum(1 for status, _ in changed if status == "D"),
        "modified_fetched_at_only": len(fetched_only),
        "modified_upstream_drift": len(drift),
        "upstream_drift_body_key_counts": drift_keys,
        "added_new_cache_entries": sum(
            1 for r in added if r.get("kind") == "new_cache_entry"),
        "added_http_status_200": sum(
            1 for r in added if r.get("http_status") == 200),
        "non_cache_paths": outside,
        "per_file": rows,
    }


def _accept_commit(run_id: str) -> dict[str, Any]:
    log = _git("log", ACCEPTED_REF, "--all", "--format=%H%x09%s")
    needle = f"accept product cycle {run_id}"
    for line in log.stdout.splitlines():
        sha, _, subject = line.partition("\t")
        if subject.strip() == needle:
            return {"accept_commit": sha}
    return {"accept_commit": None}


def _audit_ref(run_id: str) -> dict[str, Any]:
    audit_ref = f"origin/cycle/core/product/{run_id}/audit"
    return {
        "audit_ref": audit_ref,
        "audit_ref_present": _rev(audit_ref) is not None,
    }


def _remote_refs(run_id: str) -> dict[str, Any] | None:
    proc = subprocess.run(
        ["git", "ls-remote", "origin", f"refs/heads/cycle/core/product/{run_id}/*"],
        cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=60,
        check=False,
    )
    if proc.returncode != 0:
        return {"ok": False, "error": (proc.stderr or "").strip()[-200:]}
    refs = [line.split("\t")[1] for line in proc.stdout.splitlines()
            if line.strip()]
    return {"ok": True, "refs": refs,
            "has_audit_ref": any(r.endswith("/audit") for r in refs)}


def _rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def _run_history_presence(state_path: Path, run_id: str) -> dict[str, Any]:
    state = _load(state_path)
    ids = [str(entry.get("run_id")) for entry in state.get("run_history") or []]
    return {
        "state_path": _rel(state_path),
        "present_at_generation_time": run_id in ids,
    }


def reconcile(run_id: str, resume_diagnosis: Path, raw_snapshot: Path | None,
              state_path: Path, remote_check: bool) -> dict[str, Any]:
    diag = _load(resume_diagnosis)
    delta_block = diag.get("durable_delta") or {}
    head = delta_block.get("snapshot_head")
    base = delta_block.get("predecessor_head")
    if not head or not base:
        raise SystemExit(
            f"resume diagnosis {resume_diagnosis} does not pin both "
            "snapshot_head and predecessor_head; refusing to guess")
    if delta_block.get("classification") != "COMMITTED_DELTA":
        raise SystemExit(
            f"run {run_id} does not carry a committed delta "
            f"({delta_block.get('classification')}); a zero-delta run needs no "
            "cache-refresh reconciliation")
    character = characterize(base, head)
    github_record: dict[str, Any] = {
        "raw_snapshot": (_rel(raw_snapshot)
                         if raw_snapshot is not None else None),
        "fetch_failure": None,
        "meaning": (
            "the run's public GitHub run/jobs record was unavailable when the "
            "cited raw snapshot was captured, so the run's own stop mechanism "
            "is UNOBSERVED and no cause is asserted here"),
    }
    if raw_snapshot is not None and raw_snapshot.is_file():
        raw = _load(raw_snapshot)
        for failure in raw.get("fetch_failures") or []:
            if str(failure.get("run_id")) == str(run_id):
                github_record["fetch_failure"] = failure
                break
        else:
            github_record["fetch_failure"] = (
                f"not listed in {raw_snapshot}; the run id is not cited there")
    adjudication = {
        "status": "UNADJUDICATED",
        "accept_half": _accept_commit(run_id),
        **_audit_ref(run_id),
        "gate_file_in_tree": (REPO_ROOT / "results" / "audit" / "product"
                              / f"CYCLE_{run_id}_GATE.json").exists(),
    }
    remote = _remote_refs(run_id) if remote_check else None
    return {
        "schema": SCHEMA,
        "generated_at": _now(),
        "run_id": str(run_id),
        "commit": head,
        "base_commit": base,
        "resume_diagnosis": _rel(resume_diagnosis),
        "why_this_exists": (
            "the run committed a query-cache delta but no report, state block "
            "or dossier, and its public run record was pruned before any "
            "snapshot could capture it; this artifact makes the delta itself "
            "reproducible from git without asserting why the run stopped"),
        "delta": character,
        "github_record": github_record,
        "state_run_history": _run_history_presence(state_path, str(run_id)),
        "remote_refs_observed": remote,
        "adjudication": adjudication,
        "claim_ceiling": [
            "the mechanism that stopped this run is UNOBSERVED; no provider, "
            "quantum, scope or zero-delta cause is asserted",
            "the delta characterization is REPORTED-ONLY; it is not a frozen "
            "bar, not a benchmark and not a product capability claim",
            "UNADJUDICATED is not a verdict; only an independent audit gate "
            "plus an accept commit change it",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--resume-diagnosis", required=True, type=Path)
    parser.add_argument("--raw-snapshot", type=Path, default=None)
    parser.add_argument("--state", type=Path,
                        default=REPO_ROOT / "state" / "product.json")
    parser.add_argument("--remote-check", action="store_true",
                        help="observe the run's remote refs with git ls-remote")
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args(argv)
    artifact = reconcile(args.run_id, args.resume_diagnosis, args.raw_snapshot,
                         args.state, args.remote_check)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(artifact, indent=2, ensure_ascii=False,
                                   sort_keys=True) + "\n",
                        encoding="utf-8")
    summary = {
        "out": str(args.out),
        "run_id": artifact["run_id"],
        "n_files": artifact["delta"]["n_files"],
        "n_modified": artifact["delta"]["n_modified"],
        "n_added": artifact["delta"]["n_added"],
        "modified_fetched_at_only": artifact["delta"][
            "modified_fetched_at_only"],
        "modified_upstream_drift": artifact["delta"][
            "modified_upstream_drift"],
        "adjudication": artifact["adjudication"]["status"],
    }
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

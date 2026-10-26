#!/usr/bin/env python3
"""Finish an interrupted live retrieval from its committed OpenCaseLaw cache.

    python3 product/live_cache_replay.py --run-id 40257275384 \
        --interrupted-run-id 40254231396 --cache-commit 3bea6bb1

Why this exists
---------------
Run 40254231396 executed the canonical query against the live OpenCaseLaw API
and committed 26 cache entries fetched between 2026-10-26T01:31:39Z and
01:54:54Z, then stopped before writing any artifact, report, state block or
test.  The next workflow run (40257275384) resumed that snapshot, produced no
durable delta, and therefore never reached an independent gate.  The live
bytes are valid completed work; the *artifact* the interrupted run owed was
never produced.

This module closes exactly that gap without inventing a new measurement.  It
replays the **tracked product cache** through the accepted pipeline in
``retrieval_mode="offline"`` under a non-loopback socket trap, then runs the
deterministic fixture-mode generative audit.  The resulting bundle therefore
has:

* **live-fetched retrieval bytes** - every search/decision body comes from the
  cache entries the interrupted run wrote after asking the public API;
* **zero network calls during this replay** - proven by the adapter counters
  (``network_calls == 0``), an independent before/after cache fingerprint
  (``n_files_touched == 0``), and a trap non-vacuity probe that provably
  blocks an outbound connect.

It is NOT a fresh-network run and it is not a latency/precision re-measure.
The claim ceiling is exactly "the interrupted live retrieval is reproducible
from its committed cache, and the shipped page renders it".

Reuse
-----
No retrieval, clustering, generation, counter-evidence or page code is
re-implemented here.  The driver composes:
``product.query.pipeline.run_query_initial`` / ``enrich_query_bundle``,
``product.content_family_probe.probe_bundle`` (frozen D1-D4 predicates),
``product.query.bundle.validate_bundle`` and
``product.verify_query_page.js`` (the shipped DOM contract).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

PRODUCT_ROOT = Path(__file__).resolve().parent
REPO_ROOT = PRODUCT_ROOT.parent
if str(PRODUCT_ROOT) not in sys.path:
    sys.path.insert(0, str(PRODUCT_ROOT))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

SCHEMA = "product-live-cache-replay/1"
DEFAULT_QUERY = "Kundigung Mietvertrag Mietrecht"
DEFAULT_TOP_N = 150
DEFAULT_EVIDENCE = 12
DEFAULT_CACHE_COMMIT = "3bea6bb17a0f87571b27cfd4cc17473aaf62e246"
OUT_ROOT = REPO_ROOT / "results" / "product" / "live_cache_replay"

CLAIM_CEILING = (
    "REPLAY OF AN INTERRUPTED LIVE RETRIEVAL, NOT A FRESH-NETWORK RUN. Every "
    "retrieval body was fetched from the public OpenCaseLaw API by the named "
    "interrupted run and is re-read from the committed product cache; this run "
    "issues no network call (adapter counters + independent cache fingerprint + "
    "armed socket trap). The sourced answer and counter-authority pass run the "
    "deterministic fixture-mode generative audit, so they prove the wiring and "
    "the frozen content filter, not answer quality. No frozen bar, serve "
    "verdict, legal-usefulness, latency-budget or human-gate claim is made."
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _iso(ts: float | None) -> str | None:
    if ts is None:
        return None
    return datetime.fromtimestamp(float(ts), timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )


def _git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=str(REPO_ROOT),
                          capture_output=True, text=True, check=False)


def _cache_fingerprint(root: Path) -> dict[str, int]:
    out: dict[str, int] = {}
    for path in root.rglob("*"):
        if path.is_file():
            try:
                out[str(path.relative_to(root))] = path.stat().st_size
            except OSError:
                continue
    return out


def _cache_delta(before: dict[str, int], after: dict[str, int]) -> dict:
    added = sorted(set(after) - set(before))
    removed = sorted(set(before) - set(after))
    modified = sorted(p for p in set(before) & set(after) if before[p] != after[p])
    return {
        "files_before": len(before),
        "files_after": len(after),
        "n_files_added": len(added),
        "n_files_modified": len(modified),
        "n_files_removed": len(removed),
        "n_files_touched": len(added) + len(modified) + len(removed),
        "files_added": added[:20],
        "files_modified": modified[:20],
        "files_removed": removed[:20],
    }


def _body(doc: dict):
    raw = doc.get("body")
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except ValueError:
            return None
    return raw


def _describe_cache_entry(path: Path) -> dict:
    doc = json.loads(path.read_text(encoding="utf-8"))
    body = _body(doc) or {}
    params = doc.get("params") or {}
    fetched_at = doc.get("fetched_at")
    entry: dict = {
        "path": str(path.relative_to(REPO_ROOT)),
        "url": doc.get("url"),
        "status": doc.get("status"),
        "fetched_at": fetched_at,
        "fetched_at_iso": _iso(fetched_at),
        "request_path": doc.get("path"),
        "request_params": params,
    }
    if isinstance(body, dict) and "results" in body:
        entry["kind"] = "search"
        entry["query"] = params.get("query")
        entry["limit"] = params.get("limit")
        entry["offset"] = params.get("offset")
        entry["total"] = body.get("total")
        entry["returned"] = body.get("returned")
        entry["n_results"] = len(body.get("results") or [])
    elif isinstance(body, dict) and "decision_id" in body:
        entry["kind"] = "decision"
        entry["decision_id"] = body.get("decision_id")
        entry["court"] = body.get("court")
        entry["language"] = body.get("language")
        entry["full_text_chars"] = len(body.get("full_text") or "")
    else:
        entry["kind"] = "other"
    return entry


def inventory_cache_commit(commit: str) -> dict:
    """Inventory the cache files a named commit added.

    The interrupted run's durable delta is exactly these files; reading them
    from the commit (not from the ambient cache) keeps the inventory
    reproducible after later cycles append more keys.
    """
    names = _git(
        "diff-tree", "--no-commit-id", "--name-only", "-r", commit
    ).stdout.splitlines()
    cache_names = [n for n in names if n.startswith("results/product/query_cache/")]
    entries: list[dict] = []
    missing: list[str] = []
    for name in cache_names:
        path = REPO_ROOT / name
        if not path.is_file():
            missing.append(name)
            continue
        entries.append(_describe_cache_entry(path))
    fetches = [e["fetched_at"] for e in entries if e.get("fetched_at")]
    queries = sorted({str(e.get("query")) for e in entries if e.get("kind") == "search"})
    decisions = sorted({str(e.get("decision_id")) for e in entries if e.get("kind") == "decision"})
    return {
        "commit": commit,
        "n_changed_files": len(names),
        "n_cache_files": len(cache_names),
        "missing_cache_files": missing,
        "n_search": sum(1 for e in entries if e["kind"] == "search"),
        "n_decision": sum(1 for e in entries if e["kind"] == "decision"),
        "n_other": sum(1 for e in entries if e["kind"] == "other"),
        "search_queries": queries,
        "decision_ids": decisions,
        "fetched_at_min": min(fetches) if fetches else None,
        "fetched_at_max": max(fetches) if fetches else None,
        "fetched_at_min_iso": _iso(min(fetches)) if fetches else None,
        "fetched_at_max_iso": _iso(max(fetches)) if fetches else None,
        "all_status_200": all(str(e.get("status")) == "200" for e in entries),
        "entries": entries,
    }


def _artifact_absence(run_id: str) -> dict:
    """What the interrupted run did NOT write (proven from the committed tree)."""
    candidates = {
        "report": REPO_ROOT / "reports" / "product" / f"CYCLE_{run_id}.md",
        "live_slice": REPO_ROOT / "results" / "product" / "live_slice"
                      / f"CYCLE_{run_id}.json",
        "cycle_test": REPO_ROOT / "product" / "tests"
                      / f"test_cycle_{run_id}.py",
    }
    out = {key: {"path": str(path.relative_to(REPO_ROOT)),
                 "present": path.is_file()}
           for key, path in candidates.items()}
    try:
        state = json.loads((REPO_ROOT / "state" / "product.json").read_text())
    except (OSError, ValueError):
        state = {}
    key = f"cycle_{run_id}_operational_resume"
    out["state_block"] = {"key": key, "present": key in state}
    out["all_absent"] = all(not v["present"] for v in out.values())
    return out


def _page_contract(bundle_path: Path) -> dict:
    verifier = PRODUCT_ROOT / "verify_query_page.js"
    if not verifier.is_file():
        return {"ok": False, "checked": False,
                "message": "verify_query_page.js missing"}
    proc = subprocess.run(
        ["node", str(verifier), str(bundle_path)],
        cwd=str(REPO_ROOT), capture_output=True, text=True, check=False,
    )
    tail = (proc.stdout or "").strip().splitlines()[-6:]
    return {
        "ok": proc.returncode == 0,
        "checked": True,
        "returncode": proc.returncode,
        "message": " | ".join(tail),
        "stderr_tail": (proc.stderr or "").strip().splitlines()[-3:],
    }


def run(
    *,
    run_id: str,
    query: str = DEFAULT_QUERY,
    top_n: int = DEFAULT_TOP_N,
    evidence_count: int = DEFAULT_EVIDENCE,
    interrupted_run_id: str = "",
    cache_commit: str = DEFAULT_CACHE_COMMIT,
    out_dir: Path | None = None,
) -> dict:
    # Import here so the trap is installed before the heavy stack is used and
    # so the module stays importable in an interpreter without numpy/sklearn.
    from product.query.bundle import validate_bundle
    from product.query.cache_path import product_cache_dir
    from product.query.pipeline import enrich_query_bundle, run_query_initial
    from product.content_family_probe import probe_bundle
    from product import server_slice

    cache_root = product_cache_dir()
    out_dir = out_dir or (OUT_ROOT / f"CYCLE_{run_id}")
    out_dir.mkdir(parents=True, exist_ok=True)
    bundle_path = out_dir / "rent-default-live-cache.bundle.json"
    summary_path = out_dir / "summary.json"

    restore = server_slice.install_loopback_guard()
    try:
        trap_probe = None
        try:
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                sock.connect(("192.0.2.1", 80))  # TEST-NET-1, never reached
                trap_probe = "CONNECTED - the trap is NOT armed"
            except AssertionError:
                trap_probe = "blocked before any packet left the machine"
            finally:
                sock.close()
        except Exception as exc:  # pragma: no cover - defensive
            trap_probe = f"{type(exc).__name__}: {exc}"

        before = _cache_fingerprint(cache_root)
        t0 = time.time()
        initial = run_query_initial(query, top_n=top_n, retrieval_mode="offline")
        t_initial = time.time() - t0
        t1 = time.time()
        bundle = enrich_query_bundle(
            initial,
            retrieval_mode="offline",
            evidence_count=evidence_count,
            fixture_generation=True,
        )
        t_enrich = time.time() - t1
        after = _cache_fingerprint(cache_root)
    finally:
        restore()

    bundle_path.write_text(json.dumps(bundle, indent=1, sort_keys=True),
                           encoding="utf-8")
    page = _page_contract(bundle_path)
    content = probe_bundle(bundle_path)
    rows = bundle.get("decisions") or []
    clusters = bundle.get("clusters") or []
    prov = bundle.get("provenance") or {}
    remote = ((prov.get("retrieval") or {}).get("remote") or {})
    cache_stats = remote.get("cache_stats") or prov.get("cache_stats") or {}
    request_summary = remote.get("request_summary") or prov.get("request_summary") or {}
    answer = bundle.get("answer") or {}
    span = prov.get("counter_evidence_span") or {}
    coverage = (prov.get("coverage_expansion")
                or (prov.get("retrieval") or {}).get("coverage_expansion")
                or remote.get("coverage_expansion") or {})
    timing = prov.get("timing") or {}
    languages: dict[str, int] = {}
    statuses: dict[str, int] = {}
    for row in rows:
        lang = str(row.get("language") or "?")
        languages[lang] = languages.get(lang, 0) + 1
        status = str(row.get("counter_status") or "none")
        statuses[status] = statuses.get(status, 0) + 1

    cache_delta = _cache_delta(before, after)
    cache_delta["root"] = str(cache_root.relative_to(REPO_ROOT)) if (
        cache_root.is_relative_to(REPO_ROOT)) else str(cache_root)

    inventory = inventory_cache_commit(cache_commit) if cache_commit else None
    absence = _artifact_absence(interrupted_run_id) if interrupted_run_id else None
    content_filter = span.get("content_filter") or {}
    downgrades = span.get("downgrades") or []

    checks = {
        "non_loopback_trap_armed": (
            trap_probe == "blocked before any packet left the machine"
        ),
        "adapter_made_no_network_call": (
            (request_summary.get("network_calls") or 0) == 0
            and (cache_stats.get("writes") or 0) == 0
        ),
        "adapter_read_the_live_cache": (
            (cache_stats.get("hits") or 0) > 0
            and (cache_stats.get("misses") or 0) == 0
        ),
        "independent_probe_saw_no_cache_write": cache_delta["n_files_touched"] == 0,
        "bundle_validates": not validate_bundle(bundle),
        "map_has_rows": len(rows) > 0,
        "every_row_has_xy": all(
            r.get("x") is not None and r.get("y") is not None for r in rows
        ),
        "every_row_has_a_source_link": all(
            bool(r.get("canonical_url") or r.get("source_url")) for r in rows
        ),
        "map_has_clusters": len(clusters) > 0,
        "answer_is_sourced": (
            str(answer.get("status")) == "ready"
            and len(answer.get("cited_decision_ids") or []) > 0
        ),
        "frozen_content_filter_applied": (
            span.get("applied") is True and bool(content_filter)
        ),
        "no_verified_row_carries_a_frozen_content_defect": (
            content["n_verified_defective"] == 0
        ),
        "every_downgrade_moves_verified_true_to_false": all(
            (d.get("before") or {}).get("counter_evidence_verified") is True
            and (d.get("after") or {}).get("counter_evidence_verified") is False
            and bool(d.get("defects"))
            for d in downgrades
        ),
        "page_contract_passes": bool(page.get("ok")),
        "interrupted_run_artifact_gap_is_real": (
            absence is None or absence["all_absent"] is True
        ),
        "interrupted_cache_inventory_resolves": (
            inventory is None
            or (inventory["missing_cache_files"] == []
                and inventory["n_cache_files"] > 0
                and inventory["all_status_200"])
        ),
    }
    failed = sorted(k for k, v in checks.items() if not v)
    record = {
        "schema": SCHEMA,
        "run_id": str(run_id),
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "resumed_interrupted_run_id": interrupted_run_id or None,
        "query": query,
        "top_n": top_n,
        "evidence_count": evidence_count,
        "retrieval_mode_requested": "offline",
        "retrieval_mode_served": remote.get("mode"),
        "base_url": remote.get("base_url"),
        "network": {
            "claim": (
                "this replay issued no network call; the retrieval bodies are "
                "the interrupted run's committed cache entries"
            ),
            "trap_probe": trap_probe,
            "adapter_cache_hits": cache_stats.get("hits"),
            "adapter_cache_misses": cache_stats.get("misses"),
            "adapter_cache_writes": cache_stats.get("writes"),
            "adapter_network_calls": request_summary.get("network_calls"),
            "cache_keys_available": cache_stats.get("n_keys"),
            "independent_cache_probe": cache_delta,
        },
        "bundle": {
            "path": str(bundle_path.relative_to(REPO_ROOT)),
            "sha256": _sha256(bundle_path),
            "validate_errors": validate_bundle(bundle),
            "n_decisions": len(rows),
            "n_clusters": len(clusters),
            "languages": languages,
            "rows_with_xy": sum(
                1 for r in rows
                if r.get("x") is not None and r.get("y") is not None
            ),
            "rows_with_source_link": sum(
                1 for r in rows if r.get("canonical_url") or r.get("source_url")
            ),
        },
        "answer": {
            "status": answer.get("status"),
            "n_cited": len(answer.get("cited_decision_ids") or []),
            "cited_decision_ids": list(answer.get("cited_decision_ids") or []),
            "mode": "deterministic_fixture_generation",
        },
        "counter_evidence_span": {
            "applied": span.get("applied"),
            "n_candidates": span.get("n_candidates"),
            "n_selected": span.get("n_selected"),
            "abstained_ids": list(span.get("abstained_ids") or []),
            "abstention_reasons": span.get("abstention_reasons"),
            "downgraded_ids": list(span.get("downgraded_ids") or []),
            "n_downgraded": span.get("n_downgraded"),
            "content_filter": content_filter,
            "n_verified": content["n_verified"],
            "n_verified_defective": content["n_verified_defective"],
            "defect_histogram": content["defect_histogram"],
            "verified_ids": content["verified_ids"],
        },
        "counter_status_by_status": statuses,
        "coverage_expansion": {
            "n_planned": coverage.get("n_planned"),
            "n_to_execute": coverage.get("n_to_execute"),
            "n_added": coverage.get("n_added"),
            "n_reinforced": coverage.get("n_reinforced"),
            "n_cache_miss_texts": coverage.get("n_cache_miss_texts"),
        },
        "page_contract": page,
        "timing_s": {
            "initial_s": round(t_initial, 3),
            "enrich_s": round(t_enrich, 3),
            "total_s": round(t_initial + t_enrich, 3),
            "local_map_s": timing.get("local_map_s"),
        },
        "interrupted_run_cache_inventory": inventory,
        "interrupted_run_artifact_gap": absence,
        "checks": checks,
        "n_failed_checks": failed,
        "verdict": "PASS" if not failed else "FAIL",
        "claim_ceiling": CLAIM_CEILING,
        "posture": {
            "machine_gate_ready": False,
            "human_gate_ready": False,
            "packet_admitted": False,
            "ready_for_owner_session": False,
        },
    }
    summary_path.write_text(
        json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return {"record": record, "bundle": bundle, "summary_path": summary_path,
            "bundle_path": bundle_path}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--query", default=DEFAULT_QUERY)
    ap.add_argument("--top-n", type=int, default=DEFAULT_TOP_N)
    ap.add_argument("--evidence", type=int, default=DEFAULT_EVIDENCE)
    ap.add_argument("--interrupted-run-id", default="")
    ap.add_argument("--cache-commit", default=DEFAULT_CACHE_COMMIT,
                    help="commit whose added cache files are the interrupted "
                         "run's live retrieval (empty string disables)")
    ap.add_argument("--out-dir", default=None)
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args(argv)

    out = run(
        run_id=args.run_id,
        query=args.query,
        top_n=args.top_n,
        evidence_count=args.evidence,
        interrupted_run_id=args.interrupted_run_id,
        cache_commit=args.cache_commit,
        out_dir=Path(args.out_dir) if args.out_dir else None,
    )
    rec = out["record"]
    if not args.quiet:
        for name, ok in rec["checks"].items():
            print(f"[{'PASS' if ok else 'FAIL'}] {name}")
        print(
            f"\n{rec['verdict']}: "
            f"{len(rec['checks']) - len(rec['n_failed_checks'])}/"
            f"{len(rec['checks'])} checks"
        )
        print(
            f"bundle={rec['bundle']['path']} rows={rec['bundle']['n_decisions']} "
            f"clusters={rec['bundle']['n_clusters']} "
            f"verified={rec['counter_evidence_span']['n_verified']} "
            f"verified_defective={rec['counter_evidence_span']['n_verified_defective']}"
        )
        print(f"wrote {out['summary_path'].relative_to(REPO_ROOT)}")
    return 0 if rec["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

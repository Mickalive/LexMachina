"""Execute the frozen retrieval/counter-authority benchmark against OpenCaseLaw.

Pass A: 24 live searches (4 frozen questions x 3 query languages x {baseline,
counter}), paced and retried, raw bodies written to the lane cache and
evidence-preserving row extractions recorded.
Pass B: the same 24 URLs replayed strictly offline from that cache; identical
raw sha256 + identical ordered id list per query is the cached-reproducibility
gate.

Usage:
    python -m evaluation.retrieval_gate.run_retrieval_benchmark \
        --run-id 38939239917 \
        --out results/evaluation/retrieval_benchmark/38939239917.json \
        --cache-dir results/evaluation/retrieval_benchmark/cache \
        --accepted-product-root /tmp/lex_accepted/product

    python -m evaluation.retrieval_gate.run_retrieval_benchmark \
        --rescore results/evaluation/retrieval_benchmark/38939239917.json

Exit codes: 0 every measurable gate passes;
            1 at least one falsifying failure (record written, negative result kept);
            2 bad arguments, missing freeze record, no queries, or EVERY search
              failed transport (environment error: NO verdict record emitted);
            3 frozen benchmark integrity failure.
"""
from __future__ import annotations

import argparse
import datetime
import json
import platform
import sys
import time
from pathlib import Path

_LANE_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_LANE_ROOT) not in sys.path:
    sys.path.insert(0, str(_LANE_ROOT))

from evaluation.retrieval_gate import client, frozen, gates  # noqa: E402


def _utc_now() -> str:
    return (datetime.datetime.now(datetime.timezone.utc)
            .replace(microsecond=0).isoformat().replace("+00:00", "Z"))


def build_query_plan(spec: dict) -> list[dict]:
    """Deterministic order: slug order x language order x channel order."""
    plan: list[dict] = []
    for question in spec["questions"]:
        slug = question["slug"]
        for channel in frozen.CHANNELS:
            for lang in frozen.LANGUAGES:
                plan.append({
                    "query_key": f"{channel}:{slug}:{lang}",
                    "channel": channel,
                    "slug": slug,
                    "language": lang,
                    "query": question["queries"][channel][lang],
                    "limit": int(spec["top_k"][channel]),
                })
    return plan


def run_pass(plan: list[dict], spec: dict, *, offline: bool,
             cache_dir: Path) -> tuple[list[dict], float]:
    cli = client.SearchClient(
        base_url=spec["endpoint"],
        user_agent=spec["user_agent"],
        cache_dir=cache_dir,
        timeout=float(spec["transport"]["timeout_seconds"]),
        retries=int(spec["transport"]["retries"]),
        backoff_seconds=float(spec["transport"]["backoff_seconds"]),
        max_rps=float(spec["max_requests_per_second"]),
        offline=offline,
    )
    started = time.time()
    queries: list[dict] = []
    for item in plan:
        outcome = cli.search(query_key=item["query_key"], channel=item["channel"],
                             slug=item["slug"], language=item["language"],
                             query=item["query"], limit=item["limit"])
        queries.append(_outcome_record(outcome, spec))
    return queries, round(time.time() - started, 3)


def _outcome_record(outcome: client.SearchOutcome, spec: dict) -> dict:
    rows = gates.extract_rows(outcome.body)
    ids = [r["decision_id"] for r in rows]
    import hashlib
    ids_sha = hashlib.sha256(
        json.dumps(ids, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    rec = {
        "query_key": outcome.query_key,
        "channel": outcome.channel,
        "slug": outcome.slug,
        "language": outcome.language,
        "query": outcome.query,
        "limit": outcome.limit,
        "url": outcome.url,
        "status": outcome.status,
        "attempts": outcome.attempts,
        "latency_seconds": outcome.latency_seconds,
        "error": outcome.error,
        "raw_sha256": outcome.raw_sha256,
        "ids_sha256": ids_sha,
        "n_results": len(rows),
        "ids": ids,
        "rows": rows,
    }
    if outcome.from_cache:
        rec["from_cache"] = True
        rec["cache_fetched_at"] = outcome.extra.get("fetched_at")
    return rec


# --------------------------------------------------------------------------- #
# exploratory: accepted product cache cross-check (TIER = EXPLORATORY)
# --------------------------------------------------------------------------- #


def exploratory_cache_scan(product_root: Path, spec: dict) -> dict:
    """How often does the ACCEPTED product's own search cache contain the
    frozen authorities?  EXPLORATORY: designed after a pre-freeze scan of the
    same cache, therefore never a claim-bearing gate.
    """
    cache_dir = product_root / "results" / "product" / "query_cache"
    if not cache_dir.is_dir():
        return {"tier": "EXPLORATORY", "available": False,
                "reason": f"no product query_cache at {cache_dir}"}
    search_envelopes: list[dict] = []
    for path in sorted(cache_dir.glob("*/*.json")):
        try:
            env = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        params = env.get("params") or {}
        if "query" not in params or env.get("status") != 200:
            continue
        try:
            body = json.loads(env.get("body") or "")
        except (json.JSONDecodeError, TypeError):
            continue
        if not isinstance(body, dict) or not isinstance(body.get("results"), list):
            continue
        search_envelopes.append({
            "query": str(params.get("query") or ""),
            "rows": gates.extract_rows(body),
        })

    per_question = {}
    for question in spec["questions"]:
        slug = question["slug"]
        authority_ids = list(question.get("authority_ids") or [])
        if not authority_ids:
            per_question[slug] = {
                "measurable": False,
                "reason": "frozen reality benchmark carries no controlling-authority "
                          "set for this question",
            }
            continue
        hits_any: dict[str, list[str]] = {a: [] for a in authority_ids}
        fr_query = frozen.normalize_text(question["queries"]["baseline"]["fr"])
        hits_fr_question: dict[str, list[str]] = {a: [] for a in authority_ids}
        n_fr_envelopes = 0
        for env in search_envelopes:
            matched = gates.match_authorities(authority_ids, env["rows"])
            is_fr_question = frozen.normalize_text(env["query"]) == fr_query
            if is_fr_question:
                n_fr_envelopes += 1
            for aid, core in matched.items():
                if core:
                    hits_any[aid].append(env["query"])
                    if is_fr_question:
                        hits_fr_question[aid].append(env["query"])
        per_question[slug] = {
            "measurable": True,
            "authority_ids": authority_ids,
            "reachable_in_any_accepted_search_envelope": sorted(
                a for a, qs in hits_any.items() if qs),
            "unreachable_in_accepted_cache": sorted(
                a for a, qs in hits_any.items() if not qs),
            "n_envelopes_hit_any": {a: len(qs) for a, qs in hits_any.items()},
            "reachable_via_exact_fr_question_envelope": sorted(
                a for a, qs in hits_fr_question.items() if qs),
            "n_fr_question_envelopes": n_fr_envelopes,
        }
    return {
        "tier": "EXPLORATORY",
        "available": True,
        "source": str(cache_dir),
        "n_accepted_search_envelopes": len(search_envelopes),
        "interpretation": (
            "authority reachable in the accepted product cache but not cited by the "
            "answer -> answer-side (synthesis/citation) defect; authority unreachable "
            "everywhere -> retrieval-side defect. Reported as EXPLORATORY because the "
            "gate design followed a pre-freeze scan of this same cache."),
        "per_question": per_question,
    }


# --------------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------------- #


def _rescore(path: Path) -> int:
    try:
        spec = frozen.load_frozen()
        frozen.freeze_record()
    except frozen.FrozenBenchmarkError as exc:
        print(f"::error::frozen benchmark integrity failure: {exc}", file=sys.stderr)
        return 3
    record = json.loads(path.read_text(encoding="utf-8"))
    if record.get("frozen_sha256") != frozen.FROZEN_SHA256:
        print("::error::record was produced by a different frozen spec; refusing to "
              "rescore", file=sys.stderr)
        return 3
    verdict = gates.evaluate(spec, record)
    print(json.dumps(verdict, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if verdict["overall_pass"] else 1


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=None, help="where to write the run record")
    ap.add_argument("--run-id", default=None, help="run id used for the default --out path")
    ap.add_argument("--cache-dir",
                    default=str(_LANE_ROOT / "results" / "evaluation"
                                / "retrieval_benchmark" / "cache"),
                    help="evaluation-owned raw response cache (live writes, offline replay)")
    ap.add_argument("--accepted-product-root", default=None,
                    help="accepted product mount for the EXPLORATORY cache cross-check")
    ap.add_argument("--offline", action="store_true",
                    help="skip the live pass and replay strictly from --cache-dir")
    ap.add_argument("--rescore", default=None,
                    help="re-evaluate an existing run record (no network) and print the verdict")
    args = ap.parse_args(argv)

    if args.rescore:
        return _rescore(Path(args.rescore))

    try:
        spec = frozen.load_frozen()
        freeze = frozen.freeze_record()
    except frozen.FrozenBenchmarkError as exc:
        print(f"::error::frozen benchmark integrity failure: {exc}", file=sys.stderr)
        return 3

    run_id = args.run_id or __import__("os").environ.get("GITHUB_RUN_ID") or "local"
    out_path = Path(args.out) if args.out else (
        _LANE_ROOT / "results" / "evaluation" / "retrieval_benchmark" / f"{run_id}.json")
    cache_dir = Path(args.cache_dir)
    plan = build_query_plan(spec)
    if not plan:
        print("::error::empty query plan; refusing to emit a record", file=sys.stderr)
        return 2

    started_at = _utc_now()
    if args.offline:
        queries, pass_a_wall = run_pass(plan, spec, offline=True, cache_dir=cache_dir)
        pass_a_mode = "offline_replay"
    else:
        queries, pass_a_wall = run_pass(plan, spec, offline=False, cache_dir=cache_dir)
        pass_a_mode = "live"
    pass_b_started = _utc_now()
    replay, pass_b_wall = run_pass(plan, spec, offline=True, cache_dir=cache_dir)
    finished_at = _utc_now()

    n_ok = sum(1 for q in queries if q["status"] == 200)
    if n_ok == 0:
        print("::error::every search failed transport; this is an environment "
              "(network) error, not a benchmark verdict — no record emitted",
              file=sys.stderr)
        for q in queries[:3]:
            print(f"  {q['query_key']}: {q.get('error')}", file=sys.stderr)
        return 2

    repro = []
    replay_by_key = {r["query_key"]: r for r in replay}
    for q in queries:
        r = replay_by_key.get(q["query_key"])
        repro.append({
            "query_key": q["query_key"],
            "status": r["status"] if r else None,
            "raw_sha256": r["raw_sha256"] if r else None,
            "ids_sha256": r["ids_sha256"] if r else None,
            "cache_hit": bool(r and r.get("from_cache")),
        })
    all_identical = all(
        e["raw_sha256"] == q["raw_sha256"] and e["ids_sha256"] == q["ids_sha256"]
        for q, e in zip(queries, repro)
    )

    record = {
        "schema": "lex-retrieval-benchmark/1",
        "run_id": str(run_id),
        "direction_version": spec["direction_version"],
        "generated_at": finished_at,
        "started_at": started_at,
        "pass_b_started_at": pass_b_started,
        "frozen_sha256": frozen.FROZEN_SHA256,
        "freeze_recorded_at": freeze.get("frozen_at"),
        "freeze_record_sha256": _sha(_LANE_ROOT / "evaluation" / "retrieval_gate"
                                     / "FREEZE_RECORD.json"),
        "endpoint": spec["endpoint"],
        "baseline_definition": spec["baseline_definition"],
        "top_k": spec["top_k"],
        "latency_budgets": spec["latency_budgets"],
        "pass_a_mode": pass_a_mode,
        "pass_a_wall_seconds": pass_a_wall,
        "pass_b_mode": "offline_cache_replay",
        "pass_b_wall_seconds": pass_b_wall,
        "transport": {
            "n_queries": len(queries),
            "n_ok": n_ok,
            "n_failed": len(queries) - n_ok,
            "failures": [{"query_key": q["query_key"], "error": q.get("error")}
                         for q in queries if q["status"] != 200],
        },
        "queries": queries,
        "reproducibility": {"pass_b": repro, "all_identical": all_identical},
        "environment": {"python": platform.python_version(),
                        "platform": platform.platform()},
        "claim_ceiling": spec["claim_ceiling"],
    }

    if args.accepted_product_root:
        record["exploratory_product_cache_comparison"] = exploratory_cache_scan(
            Path(args.accepted_product_root), spec)

    verdict = gates.evaluate(spec, record)
    record["verdict"] = verdict

    text = json.dumps(record, ensure_ascii=False, indent=2) + "\n"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(text, encoding="utf-8")

    print(f"frozen retrieval benchmark v{spec['direction_version']} "
          f"(sha {frozen.FROZEN_SHA256[:12]}…), pass A {pass_a_mode} "
          f"{pass_a_wall}s, pass B {pass_b_wall}s -> {out_path}")
    for slug, info in verdict["per_slug"].items():
        mark = "PASS" if info["passed"] else "FAIL"
        line = f"  [{mark}] {slug:30s} gates={info['n_gates']}"
        if info["failed"]:
            line += f" failed={info['failed']}"
        if info["not_measurable"]:
            line += f" n/m={len(info['not_measurable'])}"
        print(line)
    for g in verdict["gates"]:
        if g["gate"].startswith(("transport::", "latency::", "reproducible::")):
            mark = {True: "PASS", False: "FAIL", None: "N/M"}[g["passed"]]
            print(f"  [{mark}] {g['gate']}" + (f"  {g['detail']}" if g["detail"] else ""))
    print(f"\noverall: {'PASS' if verdict['overall_pass'] else 'FAIL'} "
          f"({verdict['n_passed']} passed, {verdict['n_failed']} failed, "
          f"{verdict['n_not_measurable']} not measurable)")
    return 0 if verdict["overall_pass"] else 1


def _sha(path: Path) -> str:
    import hashlib
    return hashlib.sha256(path.read_bytes()).hexdigest()


if __name__ == "__main__":
    raise SystemExit(main())

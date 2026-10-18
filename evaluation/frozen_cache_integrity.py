"""Frozen-input integrity instrument for the retrieval/counter-authority benchmark.

Why this exists
---------------
The frozen benchmark freezes its SPEC (``frozen_retrieval_benchmark.json``,
sha 187b0e54...) but its INPUTS live in a lane-owned cache of raw OpenCaseLaw
responses under ``results/evaluation/retrieval_benchmark/cache/`` that a live
pass overwrites. Nothing in the benchmark gates the input bytes against the
accepted run of record, so an input can move under the benchmark and the
aggregate verdict can still look unchanged. Factory direction v57 names this as
the highest open item for this lane.

What this instrument does (all stdlib, deterministic, re-derivable)
------------------------------------------------------------------
  m1 input byte identity   per query key: cache envelope body_sha256 vs the
                           raw_sha256 the accepted run of record recorded.
  m2 overwriting commit    for each drifted envelope, the commit that last
                           changed it and the digest it replaced - NAMED from
                           git, never inferred.
  m3 gate reproduction     offline pass-A + pass-B re-execution compared to the
                           accepted record gate BY GATE (whole gate objects,
                           not just counts).
  m4 query reproduction    per query key raw_sha256 and ids_sha256 deltas.
  m5 upstream diagnosis    degraded/note/total/returned/result_set_id per
                           envelope; optional live probe of drifted URLs into a
                           THROWAWAY cache that can never touch the frozen one.
  m6 readings side by side every reading with its record digest, its input
                           manifest match count and its verdict counts.

Usage
-----
    python -m evaluation.frozen_cache_integrity --run-id 39164900837 \
        --out results/evaluation/frozen_cache_integrity/39164900837.json

    # add --restore-from b81ab1a2 to re-hash-prove the byte-identity repair
    # (option A of factory direction v57). The restore is guarded: it refuses
    # unless every envelope at that commit matches the accepted manifest.

    # --probe-live adds the diagnostic live re-fetch (never writes the frozen cache)

Exit codes: 0 instrument ran and wrote a record (a FAIL verdict is a RESULT,
            not an error); 2 environment error, no record written.
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

_LANE_ROOT = Path(__file__).resolve().parent.parent
if str(_LANE_ROOT) not in sys.path:
    sys.insert(0, str(_LANE_ROOT))

from evaluation.retrieval_gate import frozen  # noqa: E402

CACHE_SUBDIR = Path("results/evaluation/retrieval_benchmark/cache")


def _utc_now() -> str:
    return (datetime.datetime.now(datetime.timezone.utc)
            .replace(microsecond=0).isoformat().replace("+00:00", "Z"))


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_envelope(path: Path) -> dict:
    env = json.loads(path.read_text(encoding="utf-8"))
    return env


def body_fingerprint(body: str) -> dict:
    """Upstream health fields. OpenCaseLaw marks a partial search degraded."""
    out: dict = {}
    try:
        parsed = json.loads(body)
    except (json.JSONDecodeError, TypeError):
        return {"parse_error": True}
    if not isinstance(parsed, dict):
        return {"parse_error": True}
    for key in ("degraded", "note", "total", "total_is_lower_bound", "returned",
                "result_set_id", "has_more"):
        if key in parsed:
            out[key] = parsed[key]
    results = parsed.get("results")
    if isinstance(results, list):
        ids = [r.get("decision_id") for r in results if isinstance(r, dict)]
        out["n_results"] = len(results)
        out["n_unique_ids"] = len({i for i in ids if i})
        out["head_ids"] = ids[:5]
        out["_ids"] = ids
    return out


# --------------------------------------------------------------------------- #
# git helpers (every "which commit moved this" claim is read from git)
# --------------------------------------------------------------------------- #


def git_show(repo: Path, rev: str, path: str) -> bytes | None:
    proc = subprocess.run(["git", "-C", str(repo), "show", f"{rev}:{path}"],
                          capture_output=True)
    return proc.stdout if proc.returncode == 0 else None


def git_last_touching(repo: Path, path: str, ref: str = "HEAD") -> dict | None:
    proc = subprocess.run(
        ["git", "-C", str(repo), "log", "-1", "--format=%H%x09%h%x09%aI%x09%s",
         ref, "--", path], capture_output=True, text=True)
    if proc.returncode != 0 or not proc.stdout.strip():
        return None
    full, short, when, subject = proc.stdout.strip().split("\t", 3)
    parent = git_parent(repo, full)
    return {"commit": full, "short": short, "committed_at": when,
            "subject": subject, "first_parent": parent}


def git_parent(repo: Path, commit: str) -> str | None:
    proc = subprocess.run(["git", "-C", str(repo), "rev-parse", f"{commit}^"],
                          capture_output=True, text=True)
    return proc.stdout.strip() or None if proc.returncode == 0 else None


def git_show_envelope_sha(repo: Path, rev: str, rel: str) -> str | None:
    raw = git_show(repo, rev, rel)
    if raw is None:
        return None
    try:
        return json.loads(raw).get("body_sha256")
    except json.JSONDecodeError:
        return None


# --------------------------------------------------------------------------- #
# m1 / m2  input byte identity + named overwriting commit
# --------------------------------------------------------------------------- #


def cache_relpath(url: str) -> str:
    """Cache-relative envelope path, stable regardless of repo root."""
    digest = hashlib.sha256(url.encode("utf-8")).hexdigest()
    return f"{CACHE_SUBDIR.as_posix()}/{digest[:2]}/{digest}.json"


def input_manifest(repo: Path, cache_dir: Path, record: dict) -> dict:
    expected = {q["query_key"]: q for q in record["queries"]}
    rows = []
    for qkey in sorted(expected):
        q = expected[qkey]
        rel = cache_relpath(q["url"])
        path = repo / rel
        row = {"query_key": qkey, "slug": q["slug"], "language": q["language"],
               "channel": q["channel"], "cache_path": str(rel),
               "accepted_raw_sha256": q["raw_sha256"],
               "accepted_ids_sha256": q.get("ids_sha256")}
        if not path.is_file():
            row.update({"present": False, "match": False,
                        "reason": "cache envelope absent"})
            rows.append(row)
            continue
        env = read_envelope(path)
        row.update({
            "present": True,
            "current_body_sha256": env.get("body_sha256"),
            "current_fetched_at": env.get("fetched_at"),
            "match": env.get("body_sha256") == q["raw_sha256"],
        })
        row["health"] = {k: v for k, v in body_fingerprint(str(env.get("body") or "")).items()
                         if not k.startswith("_")}
        if not row["match"]:
            hit = git_last_touching(repo, str(rel))
            if hit:
                row["overwriting_commit"] = {
                    "commit": hit["commit"], "short": hit["short"],
                    "committed_at": hit["committed_at"], "subject": hit["subject"],
                    "body_sha256_at_first_parent": (
                        git_show_envelope_sha(repo, hit["first_parent"], str(rel))
                        if hit["first_parent"] else None),
                    "body_sha256_at_commit": (
                        git_show_envelope_sha(repo, hit["commit"], str(rel))),
                }
        rows.append(row)
    n_match = sum(1 for r in rows if r.get("match"))
    return {
        "accepted_record": None,  # filled by caller
        "n_queries": len(rows),
        "n_match": n_match,
        "n_drift": len(rows) - n_match,
        "drifted_query_keys": [r["query_key"] for r in rows if not r.get("match")],
        "rows": rows,
    }


def manifest_at_commit(repo: Path, cache_dir: Path, record: dict, rev: str) -> dict:
    """What the manifest WOULD be if every envelope were taken from ``rev``."""
    expected = {q["query_key"]: q for q in record["queries"]}
    rows = []
    for qkey in sorted(expected):
        q = expected[qkey]
        rel = cache_relpath(q["url"])
        sha = git_show_envelope_sha(repo, rev, rel)
        rows.append({"query_key": qkey, "cache_path": str(rel),
                     "accepted_raw_sha256": q["raw_sha256"],
                     "body_sha256_at_rev": sha, "match": sha == q["raw_sha256"]})
    return {"rev": rev, "n_queries": len(rows),
            "n_match": sum(1 for r in rows if r["match"]),
            "rows": rows}


# --------------------------------------------------------------------------- #
# m3 / m4  gate-level and query-level reproduction
# --------------------------------------------------------------------------- #


def _gates(record: dict) -> dict:
    return {g["gate"]: g for g in record["verdict"]["gates"]}


def reexecute_offline(repo: Path, out_path: Path) -> dict:
    workdir = Path(tempfile.mkdtemp(prefix="lex-frozen-cache-integrity-"))
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "evaluation.retrieval_gate.run_retrieval_benchmark",
             "--offline", "--run-id", out_path.stem, "--out", str(out_path)],
            cwd=str(repo), capture_output=True, text=True, env=dict(os.environ))
        return {"exit_code": proc.returncode,
                "stdout_tail": proc.stdout.strip().splitlines()[-20:],
                "stderr_tail": proc.stderr.strip().splitlines()[-10:],
                "out": str(out_path)}
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


def compare_records(accepted: dict, fresh: dict) -> dict:
    ga, gf = _gates(accepted), _gates(fresh)
    keys = sorted(set(ga) | set(gf))
    diffs = []
    for k in keys:
        a, f = ga.get(k), gf.get(k)
        if json.dumps(a, sort_keys=True, ensure_ascii=False) != json.dumps(
                f, sort_keys=True, ensure_ascii=False):
            diffs.append({"gate": k, "accepted": a, "fresh": f})
    qa = {q["query_key"]: q for q in accepted["queries"]}
    qf = {q["query_key"]: q for q in fresh["queries"]}
    raw_drift = sorted(k for k in qa if qa[k].get("raw_sha256") != qf.get(k, {}).get("raw_sha256"))
    ids_drift = sorted(k for k in qa if qa[k].get("ids_sha256") != qf.get(k, {}).get("ids_sha256"))
    return {
        "n_gates_compared": len(keys),
        "n_gate_detail_differences": len(diffs),
        "gate_detail_differences": diffs,
        "accepted_counts": {k: accepted["verdict"][k] for k in
                            ("n_gates", "n_passed", "n_failed", "n_not_measurable")},
        "fresh_counts": {k: fresh["verdict"][k] for k in
                         ("n_gates", "n_passed", "n_failed", "n_not_measurable")},
        "accepted_failed_gates": sorted(k for k, v in ga.items() if v.get("passed") is False),
        "fresh_failed_gates": sorted(k for k, v in gf.items() if v.get("passed") is False),
        "n_query_raw_sha256_drift": len(raw_drift),
        "query_raw_sha256_drift": raw_drift,
        "n_query_ids_sha256_drift": len(ids_drift),
        "query_ids_sha256_drift": ids_drift,
    }


# --------------------------------------------------------------------------- #
# m5  optional diagnostic live probe into a THROWAWAY cache
# --------------------------------------------------------------------------- #


def probe_live(record: dict, keys: list[str], spec: dict, timeout: float) -> list[dict]:
    from evaluation.retrieval_gate import client as _client
    throwaway = Path(tempfile.mkdtemp(prefix="lex-live-probe-"))
    out = []
    try:
        cli = _client.SearchClient(
            base_url=spec["endpoint"], user_agent=spec["user_agent"],
            cache_dir=throwaway, timeout=timeout,
            retries=int(spec["transport"]["retries"]),
            backoff_seconds=float(spec["transport"]["backoff_seconds"]),
            max_rps=float(spec["max_requests_per_second"]), offline=False)
        by_key = {q["query_key"]: q for q in record["queries"]}
        for key in keys:
            q = by_key[key]
            params = {"query": q["query"], "limit": int(q["limit"]), "offset": 0,
                      "sort": "relevance", "fields": "full", "include_pinpoint": "false"}
            res = cli.search(query_key=key, channel=q["channel"], slug=q["slug"],
                             language=q["language"], query=q["query"], limit=int(q["limit"]))
            entry = {"query_key": key, "url": q["url"],
                     "probe_status": res.status, "probe_raw_sha256": res.raw_sha256,
                     "probe_latency_seconds": res.latency_seconds,
                     "probe_error": res.error}
            if res.body is not None:
                fp = body_fingerprint(json.dumps(res.body, ensure_ascii=False))
                entry["probe_health"] = {k: v for k, v in fp.items() if not k.startswith("_")}
                entry["_probe_ids"] = fp.get("_ids") or []
            out.append(entry)
    except Exception as exc:  # a probe failure is reported, never silently swallowed
        out.append({"probe_error": f"{type(exc).__name__}: {exc}"})
    finally:
        shutil.rmtree(throwaway, ignore_errors=True)
    return out


def id_overlap(repo: Path, accepted_row: dict, other_row: dict) -> dict:
    def ids_of(source: dict) -> list[str]:
        if source.get("_ids"):
            return source["_ids"]
        path = repo / source["cache_path"]
        if not path.is_file():
            return []
        return body_fingerprint(str(read_envelope(path).get("body") or "")).get("_ids") or []
    a = set(ids_of(accepted_row))
    b = set(ids_of(other_row))
    return {"intersection": len(a & b), "len_a": len(a), "len_b": len(b),
            "jaccard": round(len(a & b) / len(a | b), 6) if (a | b) else None}


# --------------------------------------------------------------------------- #
# m6  readings side by side
# --------------------------------------------------------------------------- #


def reading(repo: Path, path: Path, manifest_n_match: int | None,
            manifest_n: int | None) -> dict:
    rec = json.loads(path.read_text(encoding="utf-8"))
    v = rec["verdict"]
    return {
        "run_id": rec.get("run_id"),
        "record_path": str(path.relative_to(repo)),
        "record_sha256": _sha256_file(path),
        "generated_at": rec.get("generated_at"),
        "pass_a_mode": rec.get("pass_a_mode"),
        "frozen_sha256": rec.get("frozen_sha256"),
        "verdict": {k: v[k] for k in ("n_gates", "n_passed", "n_failed",
                                      "n_not_measurable", "overall_pass")},
        "failed_gates": sorted(g["gate"] for g in v["gates"] if g.get("passed") is False),
        "rent_default_fr_raw_sha256": next(
            (q["raw_sha256"] for q in rec["queries"]
             if q["query_key"] == "baseline:rent-default:fr"), None),
        "input_manifest": ({"n_queries": manifest_n, "n_match": manifest_n_match}
                           if manifest_n is not None else
                           "not recomputed for this historical record; the input "
                           "manifest of each reading is derived by re-hashing the "
                           "cache tree of the commit that produced it"),
    }


# --------------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------------- #


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--repo-root", default=str(_LANE_ROOT))
    ap.add_argument("--accepted", default="results/evaluation/retrieval_benchmark/39098571937.json")
    ap.add_argument("--divergent", default="results/evaluation/retrieval_benchmark/39147198313.json")
    ap.add_argument("--prior-repair", default="results/evaluation/retrieval_benchmark/39163970477.json")
    ap.add_argument("--restore-from", default=None,
                    help="commit to restore every cache envelope from; guarded, "
                         "refuses unless all envelopes at that commit match the "
                         "accepted run's recorded raw_sha256")
    ap.add_argument("--probe-live", action="store_true")
    ap.add_argument("--probe-timeout", type=float, default=60.0)
    ap.add_argument("--probe-max", type=int, default=4,
                    help="hard cap on live probes; a probe is DIAGNOSTIC and is "
                         "never allowed to become the long pole of a lane cycle")
    ap.add_argument("--probe-keys", default=None,
                    help="comma-separated query keys to probe; default is the "
                         "drifted keys, capped by --probe-max")
    args = ap.parse_args(argv)

    repo = Path(args.repo_root).resolve()
    cache_dir = repo / CACHE_SUBDIR
    out_path = Path(args.out)
    if not out_path.is_absolute():
        out_path = repo / out_path

    try:
        spec = frozen.load_frozen()
        freeze = frozen.freeze_record()
    except frozen.FrozenBenchmarkError as exc:
        print(f"::error::frozen benchmark integrity failure: {exc}", file=sys.stderr)
        return 2

    accepted_path = repo / args.accepted
    if not accepted_path.is_file():
        print(f"::error::accepted run of record missing: {accepted_path}", file=sys.stderr)
        return 2
    accepted = json.loads(accepted_path.read_text(encoding="utf-8"))
    if accepted.get("frozen_sha256") != frozen.FROZEN_SHA256:
        print("::error::accepted record was produced by a different frozen spec",
              file=sys.stderr)
        return 2

    record: dict = {
        "schema": "lex-frozen-cache-integrity/1",
        "run_id": args.run_id,
        "lane": "evaluation",
        "direction_version": 57,
        "generated_at": _utc_now(),
        "instrument": "evaluation/frozen_cache_integrity.py",
        "claim_ceiling": (
            "proves whether the accepted retrieval benchmark's frozen INPUTS and "
            "GATES reproduce from the committed tree; it does not certify product "
            "retrieval quality, raises no absolute bar, changes no frozen "
            "threshold and does not unblock the human gate"),
        "frozen_spec": {"sha256": frozen.FROZEN_SHA256,
                        "freeze_record_sha256": freeze.get("sha256"),
                        "note": "spec bytes re-hashed before use and unchanged"},
        "inputs": {
            "accepted_record": str(accepted_path.relative_to(repo)),
            "accepted_record_sha256": _sha256_file(accepted_path),
            "accepted_generated_at": accepted.get("generated_at"),
            "accepted_queries": len(accepted["queries"]),
        },
        "hypothesis_file": "evaluation/FROZEN_CACHE_INTEGRITY_HYPOTHESIS_V1.json",
        "hypothesis_sha256": _sha256_file(repo / "evaluation/FROZEN_CACHE_INTEGRITY_HYPOTHESIS_V1.json"),
    }

    # -- pre-repair state, before anything is touched --------------------- #
    pre = input_manifest(repo, cache_dir, accepted)
    pre["accepted_record"] = args.accepted
    record["m1_input_byte_identity_before_restore"] = pre

    # -- guarded restore --------------------------------------------------- #
    restore: dict = {"performed": False}
    if args.restore_from:
        candidate = manifest_at_commit(repo, cache_dir, accepted, args.restore_from)
        restore["source_commit"] = args.restore_from
        restore["source_manifest"] = {k: v for k, v in candidate.items() if k != "rows"}
        restore["source_manifest_rows"] = candidate["rows"]
        if candidate["n_match"] != candidate["n_queries"]:
            restore["refused"] = True
            restore["refusal_reason"] = (
                f"{args.restore_from} does NOT hold a byte-identical input manifest for "
                f"the accepted run ({candidate['n_match']}/{candidate['n_queries']} match); "
                "refusing to restore, because restoring anything else would fabricate an "
                "input history the lane never had committed evidence for")
        else:
            before, after = [], []
            for row in candidate["rows"]:
                path = repo / row["cache_path"]
                new_raw = git_show(repo, args.restore_from, row["cache_path"])
                if new_raw is None:
                    continue
                old_sha = json.loads(path.read_text(encoding="utf-8")).get("body_sha256")
                path.parent.mkdir(parents=True, exist_ok=True)
                tmp = path.with_suffix(".tmp")
                tmp.write_bytes(new_raw)
                tmp.replace(path)
                new_sha = read_envelope(path).get("body_sha256")
                before.append({"cache_path": row["cache_path"], "body_sha256": old_sha})
                after.append({"cache_path": row["cache_path"], "body_sha256": new_sha})
            restore.update({
                "performed": True, "refused": False,
                "n_envelopes_written": len(after),
                "changed": [b["cache_path"] for b, a in zip(before, after)
                            if b["body_sha256"] != a["body_sha256"]],
                "before": before, "after": after,
                "note": ("the frozen cache is a LANE-OWNED RAW RESPONSE CACHE that a live "
                         "pass overwrites; restoring it is the direction's option A "
                         "(restore byte-identity and prove it by re-hash). The restore is "
                         "evidence-preserving: every before/after digest is in this record."),
            })
    record["restore"] = restore

    post = input_manifest(repo, cache_dir, accepted)
    post["accepted_record"] = args.accepted
    record["m1_input_byte_identity_after_restore"] = post

    # -- m3 / m4 ----------------------------------------------------------- #
    fresh_out = out_path.parent / f"{args.run_id}_fresh_offline.json"
    fresh_out.parent.mkdir(parents=True, exist_ok=True)
    run_info = reexecute_offline(repo, fresh_out)
    record["m3_reexecution"] = {k: v for k, v in run_info.items() if k != "out"}
    record["m3_reexecution"]["record_path"] = str(fresh_out.relative_to(repo))
    record["m3_reexecution"]["record_sha256"] = _sha256_file(fresh_out)
    if not fresh_out.is_file():
        record["verdict"] = {"outcome": "ENVIRONMENT_ERROR",
                             "detail": "offline re-execution produced no record"}
        out_path.write_text(json.dumps(record, ensure_ascii=False, indent=2, sort_keys=True),
                            encoding="utf-8")
        return 2
    fresh = json.loads(fresh_out.read_text(encoding="utf-8"))
    record["m3_gate_comparison"] = compare_records(accepted, fresh)

    # -- m5 ---------------------------------------------------------------- #
    if args.probe_live:
        if args.probe_keys:
            keys = [k for k in args.probe_keys.split(",") if k]
        else:
            keys = record["m3_gate_comparison"]["query_raw_sha256_drift"] or [
                r["query_key"] for r in post["rows"] if not r.get("match")]
            # a degraded envelope is the decisive diagnostic; probe it first
            keys = [d["query_key"] for d in
                    record["m5_degraded_envelopes"]["envelopes"]] + [
                k for k in keys if k not in
                {d["query_key"] for d in record["m5_degraded_envelopes"]["envelopes"]}]
        capped = keys[:max(0, args.probe_max)]
        record["m5_live_probe"] = {
            "cache_dir_used": "THROWAWAY (tempfile.mkdtemp), removed afterwards; the "
                              "frozen cache is never written by a probe",
            "probe_target_url": "the frozen spec URL for each drifted query, unchanged",
            "candidate_keys": keys,
            "probed_keys": capped,
            "n_capped_by": args.probe_max,
            "results": probe_live(accepted, capped, spec, args.probe_timeout),
            "tier": "DIAGNOSTIC - never a gate input (frozen hypothesis S5)",
        }
    degraded = [{"query_key": r["query_key"], "cache_path": r["cache_path"],
                 "health": r.get("health"),
                 "match": r.get("match")}
                for r in post["rows"]
                if (r.get("health") or {}).get("degraded")]
    record["m5_degraded_envelopes"] = {
        "n": len(degraded),
        "note": ("an OpenCaseLaw response carrying degraded=true with a note is the "
                 "upstream's own admission that the search hit its time budget and "
                 "returned a partial index; the benchmark consumes it like any other "
                 "body, so a degraded body silently becomes a benchmark INPUT"),
        "envelopes": degraded,
    }
    if degraded:
        comparisons = []
        for d in degraded:
            row = next(r for r in post["rows"] if r["query_key"] == d["query_key"])
            comparisons.append({
                "query_key": d["query_key"],
                "accepted_body_vs_current_body": id_overlap(repo, row, row),
                "accepted_total": (row.get("health") or {}).get("total"),
                "accepted_degraded": (row.get("health") or {}).get("degraded"),
                "accepted_note": (row.get("health") or {}).get("note"),
            })
        record["m5_degraded_envelopes"]["comparisons"] = comparisons

    # -- m6 ---------------------------------------------------------------- #
    prior = repo / args.prior_repair
    divergent = repo / args.divergent
    readings = {
        "accepted_run_of_record": reading(repo, accepted_path, pre["n_queries"], pre["n_match"]),
        "divergent_run": (reading(repo, divergent, None, None)
                          if divergent.is_file() else None),
        "prior_repair_run": (reading(repo, prior, None, None)
                             if prior.is_file() else None),
        "this_run_fresh_offline": reading(repo, fresh_out, post["n_queries"], post["n_match"]),
    }
    record["m6_readings_side_by_side"] = readings
    record["m6_separating_digests"] = {
        "note": ("the accepted reading and the divergent reading differ in exactly the "
                 "cache bodies whose digests are listed here; the accepted run's own "
                 "recorded digests are the input of record"),
        "accepted_per_query_raw_sha256": {
            q["query_key"]: q["raw_sha256"] for q in accepted["queries"]},
        "divergent_per_query_raw_sha256": (
            {q["query_key"]: q["raw_sha256"]
             for q in json.loads(divergent.read_text(encoding="utf-8"))["queries"]}
            if divergent.is_file() else None),
        "queries_whose_digest_differs_between_readings": (
            sorted(k for k, v in
                   {q["query_key"]: q["raw_sha256"]
                    for q in accepted["queries"]}.items()
                   if v != {q["query_key"]: q["raw_sha256"]
                            for q in json.loads(divergent.read_text(encoding="utf-8"))["queries"]}.get(k))
            if divergent.is_file() else None),
    }

    # -- frozen success rule, evaluated verbatim --------------------------- #
    cmp_ = record["m3_gate_comparison"]
    S1 = (post["n_match"] == post["n_queries"]
          and cmp_["n_gates_compared"] == 40
          and cmp_["n_gate_detail_differences"] == 0)
    S2 = "COMPLETE" if post["n_match"] == post["n_queries"] else "PARTIAL"
    S4 = ("INPUT_BYTES_MOVED_WITH_AGGREGATE_STABLE"
          if (cmp_["accepted_counts"] == cmp_["fresh_counts"]
              and post["n_match"] < post["n_queries"]) else None)
    record["verdict"] = {
        "S1_closure_complete": S1,
        "S2_prior_repair_completeness": S2,
        "S3_readings_published_side_by_side": bool(
            readings["accepted_run_of_record"] and readings["divergent_run"]),
        "S4_input_bytes_moved_with_aggregate_stable": S4,
        "outcome": (
            "ITEM_1_CLOSED" if S1 else
            "INPUT_BYTES_MOVED_WITH_AGGREGATE_STABLE" if S4 else
            "REPRODUCTION_MISMATCH"),
        "n_input_match": f"{post['n_match']}/{post['n_queries']}",
        "n_gate_detail_differences": cmp_["n_gate_detail_differences"],
        "accepted_counts": cmp_["accepted_counts"],
        "fresh_counts": cmp_["fresh_counts"],
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(record, ensure_ascii=False, indent=2, sort_keys=True),
                        encoding="utf-8")
    print(json.dumps(record["verdict"], indent=2, sort_keys=True))
    print(f"::notice::wrote {out_path}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
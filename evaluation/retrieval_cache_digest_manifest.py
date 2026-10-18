#!/usr/bin/env python3
"""Append-only digest manifest for the frozen retrieval benchmark's INPUTS.

WHY THIS FILE EXISTS (audit ``CYCLE_39164900837`` F8)
---------------------------------------------------
Cycle ``39164900837`` closed direction-v57 item 1 by RESTORING the frozen
retrieval benchmark's input cache after 21 of its 24 cache bodies had been
overwritten by a scratch run.  The audit then required the same defect to become
*impossible to miss next time*.  The audit's literal instruction was to write a
digest manifest into ``evaluation/retrieval_gate/FREEZE_RECORD.json``.

That instruction is INADMISSIBLE here, and the lane records why instead of
silently skipping it: factory-wide requirement 3 pins ``FREEZE_RECORD.json`` at
``b06a2ad024040c38312686ab7aacc5ab18c663f1ef0b77494caf6ce3b3b52e49``, and the v57
lane question restates that pin in binding terms.  Editing the freeze record to
satisfy a fix would trade a preserved freeze-ordering artefact for a new one.

So the only admissible route is the one the lane already declared in F8: a
SEPARATE, ADDITIVE manifest under ``results/evaluation/``.  This module writes
it, and ``--verify`` re-derives the committed inputs against it and exits 1 on
any drift.  ``FREEZE_RECORD.json`` is re-hashed on every run and is never written.

WHAT IT MEASURES
----------------
For every query of the accepted run of record, the SHA-256 of the cached
OpenCaseLaw response body that the frozen benchmark actually consumed.  It
answers exactly one question: *are the frozen inputs still the bytes the
accepted record was scored on?*  That is an INSTRUMENT-integrity property.  It
certifies nothing about retrieval quality - the accepted record it describes is
itself an offline replay over the same bodies.

REUSE-FIRST
-----------
Path derivation and envelope reading are reused from
``evaluation.frozen_cache_integrity.py`` (``cache_relpath`` /
``read_envelope``); this module adds the pinned, committed, append-only
manifest and the verifier, and re-derives nothing about the frozen spec.

NO NETWORK.  NO FROZEN FILE IS WRITTEN.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from evaluation.frozen_cache_integrity import cache_relpath, read_envelope  # noqa: E402
from evaluation.retrieval_gate import frozen as retrieval_frozen  # noqa: E402

SCHEMA = "lex-evaluation-retrieval-cache-digest-manifest/1"

#: The accepted run of record of the frozen retrieval benchmark. Its SHA-256 is
#: re-derived at run time and published; it is a pointer, not a promotion.
ACCEPTED_RUN_OF_RECORD = "results/evaluation/retrieval_benchmark/39098571937.json"
ACCEPTED_RECORD_SHA256 = (
    "aaf2587ad192a828c56cb082a74a2d5e944fbb4b2afc58df0b1e6a0f9b75dd66")

#: Pinned by factory-wide requirement 3 and restated in direction v57. Re-hashed
#: on every run; this module never writes FREEZE_RECORD.json.
FREEZE_RECORD_SHA256 = (
    "b06a2ad024040c38312686ab7aacc5ab18c663f1ef0b77494caf6ce3b3b52e49")

MANIFEST_DIR = Path("results/evaluation/retrieval_cache_digest_manifest")

VERDICT_STABLE = "INPUTS_STABLE"
VERDICT_DRIFTED = "INPUTS_DRIFTED"


class ManifestError(RuntimeError):
    pass


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _direction_version() -> int:
    state = json.loads((_REPO_ROOT / "state/evaluation.json").read_text(encoding="utf-8"))
    return int(state["direction_version"])


def verify_frozen_pins() -> dict:
    """Re-hash the three frozen artefacts this manifest depends on."""
    spec = _sha256_file(retrieval_frozen._PATH)
    freeze = _sha256_file(retrieval_frozen.FREEZE_RECORD_PATH)
    if spec != retrieval_frozen.FROZEN_SHA256:
        raise ManifestError(f"frozen spec digest drifted: {spec}")
    if freeze != FREEZE_RECORD_SHA256:
        raise ManifestError(
            "FREEZE_RECORD.json digest drifted to " + freeze + ". This module "
            "refuses to run: the freeze record is pinned by factory-wide "
            "requirement 3 and is a read-only input here.")
    return {"frozen_spec_sha256": spec, "freeze_record_sha256": freeze,
            "freeze_record_edited_by_this_module": False}


def build_rows(repo: Path, record: dict) -> list[dict]:
    """One row per query key of the accepted record: its pinned body digest and
    the digest of the envelope actually committed."""
    rows = []
    for q in sorted(record["queries"], key=lambda q: q["query_key"]):
        rel = cache_relpath(q["url"])
        path = repo / rel
        row = {
            "query_key": q["query_key"],
            "slug": q["slug"],
            "language": q["language"],
            "channel": q["channel"],
            "cache_path": str(rel),
            "pinned_body_sha256": q["raw_sha256"],
            "pinned_ids_sha256": q.get("ids_sha256"),
        }
        if not path.is_file():
            row.update({"present": False, "committed_body_sha256": None,
                        "match": False, "reason": "cache envelope absent"})
        else:
            env = read_envelope(path)
            committed = env.get("body_sha256")
            row.update({"present": True,
                        "committed_body_sha256": committed,
                        "committed_fetched_at": env.get("fetched_at"),
                        "match": committed == q["raw_sha256"]})
        rows.append(row)
    return rows


def build_manifest(repo: Path, run_id: str) -> dict:
    pins = verify_frozen_pins()
    accepted_path = repo / ACCEPTED_RUN_OF_RECORD
    if not accepted_path.is_file():
        raise ManifestError(f"accepted run of record absent: {accepted_path}")
    accepted_sha = _sha256_file(accepted_path)
    if accepted_sha != ACCEPTED_RECORD_SHA256:
        raise ManifestError(
            f"accepted run of record digest drifted: {accepted_sha} != "
            f"{ACCEPTED_RECORD_SHA256}")
    record = json.loads(accepted_path.read_text(encoding="utf-8"))
    if record.get("frozen_sha256") != retrieval_frozen.FROZEN_SHA256:
        raise ManifestError("accepted record was not produced by the pinned spec")
    rows = build_rows(repo, record)
    n_match = sum(1 for r in rows if r["match"])
    return {
        "schema": SCHEMA,
        "run_id": run_id,
        "lane": "evaluation",
        "direction_version": _direction_version(),
        "generated_at_utc": _utc_now(),
        "additive_only": (
            "This manifest is a NEW file under results/evaluation/. "
            "evaluation/retrieval_gate/FREEZE_RECORD.json is re-hashed as a "
            "read-only input and is never written: the audit's literal F8 "
            "wording (write the manifest INTO FREEZE_RECORD.json) is inadmissible "
            "while factory-wide requirement 3 pins that file at " + FREEZE_RECORD_SHA256),
        "frozen_pins": pins,
        "accepted_run_of_record": ACCEPTED_RUN_OF_RECORD,
        "accepted_run_of_record_sha256": accepted_sha,
        "n_queries": len(rows),
        "n_match": n_match,
        "n_drift": len(rows) - n_match,
        "drifted_query_keys": [r["query_key"] for r in rows if not r["match"]],
        "verdict": VERDICT_STABLE if n_match == len(rows) else VERDICT_DRIFTED,
        "rows": rows,
        "claim_ceiling": (
            "INPUT INTEGRITY of the frozen retrieval benchmark only: it proves "
            "the 24 committed cache envelopes still hold the bodies the accepted "
            "run of record was scored on. The accepted record is itself an "
            "offline replay over those same bodies, so this certifies NOTHING "
            "about live retrieval quality, counter-authority recall or the "
            "query map. INPUTS_STABLE is not a pass of the retrieval benchmark."),
    }


def verify_against(manifest: dict, repo: Path) -> dict:
    """Recompute every pinned digest from the committed envelopes."""
    accepted_path = repo / manifest["accepted_run_of_record"]
    record = json.loads(accepted_path.read_text(encoding="utf-8"))
    rows = build_rows(repo, record)
    drift = []
    for row in rows:
        pinned = manifest["rows_by_query_key"][row["query_key"]]
        if row["committed_body_sha256"] != pinned["committed_body_sha256"]:
            drift.append({
                "query_key": row["query_key"],
                "cache_path": row["cache_path"],
                "manifest_body_sha256": pinned["committed_body_sha256"],
                "now_body_sha256": row["committed_body_sha256"],
                "still_matches_accepted_record": row["match"],
            })
    return {
        "schema": "lex-evaluation-retrieval-cache-digest-manifest-verify/1",
        "manifest_run_id": manifest["run_id"],
        "manifest_frozen_pins": manifest["frozen_pins"],
        "frozen_pins_now": verify_frozen_pins(),
        "n_rows": len(rows),
        "n_drift": len(drift),
        "drift": drift,
        "verdict": VERDICT_STABLE if not drift else VERDICT_DRIFTED,
    }


def selftest() -> dict:
    """Non-vacuity: the comparator must detect a single-byte body change, a
    missing envelope and an unchanged tree. Fixed here, before real use."""
    with tempfile.TemporaryDirectory(prefix="lex-cache-manifest-selftest-") as td:
        repo = Path(td)
        rel = cache_relpath("https://mcp.opencaselaw.ch/decisions?x=1")
        path = repo / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        envelope = {"body": '{"results": []}', "body_sha256": "a" * 64,
                    "fetched_at": "2026-01-01T00:00:00Z"}
        path.write_text(json.dumps(envelope), encoding="utf-8")
        record = {"queries": [{"query_key": "baseline:x:fr", "slug": "x",
                               "language": "fr", "channel": "baseline",
                               "url": "https://mcp.opencaselaw.ch/decisions?x=1",
                               "raw_sha256": "a" * 64}]}
        stable = build_rows(repo, record)
        envelope["body_sha256"] = "b" * 64
        path.write_text(json.dumps(envelope), encoding="utf-8")
        moved = build_rows(repo, record)
        path.unlink()
        absent = build_rows(repo, record)
    cases = [
        {"case": "unchanged_envelope_matches", "expect_match": True,
         "observed": stable[0]["match"], "passed": stable[0]["match"] is True},
        {"case": "single_body_digest_change_detected", "expect_match": False,
         "observed": moved[0]["match"], "passed": moved[0]["match"] is False},
        {"case": "absent_envelope_detected", "expect_match": False,
         "observed": absent[0]["match"], "passed": absent[0]["match"] is False},
    ]
    return {"schema": "lex-evaluation-retrieval-cache-digest-manifest-selftest/1",
            "cases": cases,
            "all_passed": all(c["passed"] for c in cases)}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--run-id", default="local")
    ap.add_argument("--out", default=None,
                    help=f"default: {MANIFEST_DIR}/<run-id>.json")
    ap.add_argument("--verify", default=None,
                    help="verify committed bytes against an existing manifest")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args(argv)

    if args.selftest:
        report = selftest()
        print(json.dumps(report, indent=1))
        return 0 if report["all_passed"] else 1

    if args.verify:
        manifest = json.loads(Path(args.verify).read_text(encoding="utf-8"))
        manifest["rows_by_query_key"] = {r["query_key"]: r for r in manifest["rows"]}
        result = verify_against(manifest, _REPO_ROOT)
        result["selftest"] = selftest()
        print(json.dumps(result, indent=1))
        return 0 if result["verdict"] == VERDICT_STABLE else 1

    manifest = build_manifest(_REPO_ROOT, args.run_id)
    manifest["selftest"] = selftest()
    out = Path(args.out) if args.out else _REPO_ROOT / MANIFEST_DIR / f"{args.run_id}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(manifest, indent=1, ensure_ascii=False) + "\n",
                   encoding="utf-8")
    print(json.dumps({k: manifest[k] for k in
                      ("schema", "run_id", "verdict", "n_queries", "n_match",
                       "n_drift", "drifted_query_keys", "frozen_pins")}, indent=1))
    print(f"manifest: {out}")
    return 0 if manifest["verdict"] == VERDICT_STABLE else 1


if __name__ == "__main__":
    raise SystemExit(main())
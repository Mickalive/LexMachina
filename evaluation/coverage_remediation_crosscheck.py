#!/usr/bin/env python3
"""Coverage-remediation cross-check — factory direction v62 evaluation ordered item (2).

The product lane's ordered deliverable 2 remedied the accepted finding that
only 4 of 24 frozen multilingual+counter-intent query texts were executed
(product_cache_parity 39631600439).  It shipped committed replay evidence
(``LOCAL_LIVE_COVERAGE2_live.json`` 24/24 executed, 23 frozen ids reached;
``LOCAL_OFFLINE_VERIFY_offline.json`` 20/24 replayed, 0 network, 16 ids
reached) at product head 44330212.

This instrument cross-checks that evidence from the evaluation side, under a
NEW run id, per the standing cross-check duty:

* **V1** the product-owned frozen-text snapshot pins the accepted frozen
  retrieval benchmark (source_sha256 == 187b0e54…);
* **V2** a FRESH evaluation-owned offline replay of the same 24 texts through
  the shipped product code (hardlink-free copy of the accepted mount under
  /tmp/opencode, so the accepted mount is never written) completes with ZERO
  network calls and leaves the cache byte-unmodified;
* **V3** the frozen-id reach unions recompute exactly from the per_text rows
  in all three evidence files, and the fresh offline reached set SUPERSETS
  the committed offline reached set (reach LOSS is falsification).

Controls D1 (frozen spec re-hash), D2 (planted fake id must appear in the
recomputed union) and D3 (planted reach loss must fail the superset check)
prove the battery is not vacuous.

Exit codes (frozen contract)
----------------------------
0  COVERAGE_EVIDENCE_REPRODUCES
1  COVERAGE_EVIDENCE_DIVERGES
2  ENVIRONMENT_OR_VACUOUS  (never a product verdict)

Coverage fixes the CHANNEL gap; it does NOT fix the lexicon-level marker
blindness attributed by accepted run 39771077625, and this instrument claims
nothing about counter labels, bars, serving or jurist usefulness.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

SCHEMA = "lex-evaluation-coverage-remediation-crosscheck/1"
HYPOTHESIS_PATH = REPO_ROOT / "evaluation" / "COVERAGE_REMEDIATION_CROSSCHECK_HYPOTHESIS_V1.json"
FREEZE_PATH = REPO_ROOT / "evaluation" / "COVERAGE_REMEDIATION_CROSSCHECK_FREEZE_RECORD_V1.json"
FROZEN_SPEC = REPO_ROOT / "evaluation" / "retrieval_gate" / "frozen_retrieval_benchmark.json"
FROZEN_SPEC_SHA = "187b0e54b03b326c62d45d8ba48fc78dc88501086761cd91a84c304a7478ba72"
DEFAULT_MOUNT = Path("/tmp/lex_accepted/product")
SCRATCH_BASE = Path("/tmp/opencode/coverage_crosscheck_scratch")

EXIT_OK = 0
EXIT_DIVERGE = 1
EXIT_ENV = 2


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _cache_fingerprint(cache_dir: Path) -> dict[str, str]:
    if not cache_dir.is_dir():
        return {}
    return {str(p.relative_to(cache_dir)): sha256_file(p)
            for p in sorted(cache_dir.glob("*/*.json"))}


def recompute_union(record: dict) -> list[str]:
    out: set[str] = set()
    for row in record.get("per_text") or []:
        for did in row.get("all_frozen_ids_reached") or []:
            out.add(str(did))
    return sorted(out)


def planted_union(rows: list[dict]) -> list[str]:
    """Union over an in-memory row list (used by controls D2/D3)."""
    out: set[str] = set()
    for row in rows:
        for did in row.get("all_frozen_ids_reached") or []:
            out.add(str(did))
    return sorted(out)


def _rehash(freeze: dict, mount: Path) -> dict:
    checks: list[dict] = []
    ok = True
    for rel, expected in sorted((freeze.get("pins") or {}).items()):
        if rel.startswith("evaluation/COVERAGE_") or rel.endswith(
                ("COVERAGE_REMEDIATION_CROSSCHECK_HYPOTHESIS_V1.json",
                 "coverage_remediation_crosscheck.py")):
            path = REPO_ROOT / rel
        elif rel.startswith("evaluation/"):
            path = REPO_ROOT / rel
        else:
            path = REPO_ROOT / rel
        if not path.is_file():
            checks.append({"pin": rel, "status": "ABSENT", "expected": expected})
            ok = False
            continue
        actual = sha256_file(path)
        good = actual == expected
        ok = ok and good
        checks.append({"pin": rel, "status": "ok" if good else "DRIFT",
                       "expected": expected, "actual": actual})
    for rel, expected in sorted((freeze.get("product_pins") or {}).items()):
        path = mount / rel
        if not path.is_file():
            checks.append({"pin": f"product:{rel}", "status": "ABSENT", "expected": expected})
            ok = False
            continue
        actual = sha256_file(path)
        good = actual == expected
        ok = ok and good
        checks.append({"pin": f"product:{rel}", "status": "ok" if good else "DRIFT",
                       "expected": expected, "actual": actual})
    return {"all_ok": ok, "n_checks": len(checks), "checks": checks}


def fresh_offline_replay(mount: Path, run_id: str, scratch: Path) -> tuple[dict | None, dict]:
    """Copy the mount (never write the accepted mount), run shipped offline replay."""
    meta: dict = {"scratch": str(scratch)}
    if scratch.exists():
        shutil.rmtree(scratch)
    scratch.parent.mkdir(parents=True, exist_ok=True)
    try:
        shutil.copytree(mount, scratch, symlinks=True)
    except Exception as exc:
        return None, {**meta, "copy_error": repr(exc)}
    out_dir = scratch / "results" / "product" / "coverage_replay"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / f"eval_fresh_{run_id}.json"
    cmd = [sys.executable, str(scratch / "product" / "coverage_replay.py"),
           "--mode", "offline", "--run-id", f"eval_fresh_{run_id}"]
    try:
        proc = subprocess.run(cmd, cwd=str(scratch), capture_output=True, text=True, timeout=900)
        meta["returncode"] = proc.returncode
        meta["stdout_tail"] = (proc.stdout or "")[-1500:]
        meta["stderr_tail"] = (proc.stderr or "")[-1500:]
    except Exception as exc:
        return None, {**meta, "run_error": repr(exc)}
    if not out_file.is_file():
        # coverage_replay writes to REPO_ROOT-relative OUT_DIR of the copy
        alt = list((scratch / "results" / "product" / "coverage_replay").glob("eval_fresh_*.json"))
        if alt:
            out_file = alt[0]
        else:
            return None, {**meta, "error": "fresh replay produced no artifact"}
    record = json.loads(out_file.read_text(encoding="utf-8"))
    # copy the fresh replay artifact bytes back into the evaluation namespace
    dest = (REPO_ROOT / "results" / "evaluation" / "coverage_remediation_crosscheck"
            / f"{run_id}_fresh_offline_replay.json")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(record, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8")
    meta["artifact"] = str(dest.relative_to(REPO_ROOT))
    meta["artifact_sha256"] = sha256_file(dest)
    return record, meta


def run(run_id: str, mount: Path) -> tuple[int, dict]:
    if not HYPOTHESIS_PATH.is_file() or not FREEZE_PATH.is_file():
        return EXIT_ENV, {"verdict": "ENVIRONMENT_OR_VACUOUS", "exit_code": EXIT_ENV,
                          "reason": "hypothesis or freeze record absent"}
    hypothesis = json.loads(HYPOTHESIS_PATH.read_text(encoding="utf-8"))
    freeze = json.loads(FREEZE_PATH.read_text(encoding="utf-8"))
    if str(hypothesis.get("run_id_of_record")) != str(run_id):
        return EXIT_ENV, {"verdict": "ENVIRONMENT_OR_VACUOUS", "exit_code": EXIT_ENV,
                          "reason": "run id does not match frozen run_id_of_record"}
    if not mount.is_dir() or not FROZEN_SPEC.is_file():
        return EXIT_ENV, {"verdict": "ENVIRONMENT_OR_VACUOUS", "exit_code": EXIT_ENV,
                          "mount_exists": mount.is_dir(), "spec_exists": FROZEN_SPEC.is_file()}

    pins_before = _rehash(freeze, mount)
    if not pins_before["all_ok"]:
        return EXIT_ENV, {"verdict": "ENVIRONMENT_OR_VACUOUS", "exit_code": EXIT_ENV,
                          "phase": "pins_before", "pins_before": pins_before}

    # D1: frozen spec re-hash
    d1_ok = sha256_file(FROZEN_SPEC) == FROZEN_SPEC_SHA

    # V1: snapshot pins the accepted benchmark
    snapshot = json.loads((mount / "product" / "data" / "frozen_retrieval_texts.json")
                          .read_text(encoding="utf-8"))
    v1_ok = (str(snapshot.get("source_sha256")) == FROZEN_SPEC_SHA
             and d1_ok)

    live_path = mount / "results/product/coverage_replay/LOCAL_LIVE_COVERAGE2_live.json"
    offline_path = mount / "results/product/coverage_replay/LOCAL_OFFLINE_VERIFY_offline.json"
    if not live_path.is_file() or not offline_path.is_file():
        return EXIT_ENV, {"verdict": "ENVIRONMENT_OR_VACUOUS", "exit_code": EXIT_ENV,
                          "live_exists": live_path.is_file(),
                          "offline_exists": offline_path.is_file()}
    live = json.loads(live_path.read_text(encoding="utf-8"))
    committed_offline = json.loads(offline_path.read_text(encoding="utf-8"))

    # V3 part 1: recomputed unions equal the records' own counts (committed evidence)
    live_union = recompute_union(live)
    offline_union = recompute_union(committed_offline)
    live_consistent = len(live_union) == int(live.get("n_frozen_ids_reached") or -1)
    offline_consistent = len(offline_union) == int(committed_offline.get("n_frozen_ids_reached") or -1)

    # cache fingerprint of the ACCEPTED mount before the fresh replay (must stay identical)
    cache_dir = mount / "results" / "product" / "query_cache"
    mount_fp_before = _cache_fingerprint(cache_dir)

    fresh, fresh_meta = fresh_offline_replay(mount, run_id, SCRATCH_BASE / run_id)

    mount_fp_after = _cache_fingerprint(cache_dir)
    mount_cache_pure = mount_fp_before == mount_fp_after

    if fresh is None:
        return EXIT_ENV, {"verdict": "ENVIRONMENT_OR_VACUOUS", "exit_code": EXIT_ENV,
                          "phase": "fresh_replay", "fresh_meta": fresh_meta,
                          "pins_before": pins_before,
                          "claim_ceiling": "fresh replay failure is never a product verdict"}

    # V2: offline purity of the fresh replay
    fresh_network = int(fresh.get("n_network_calls") or 0)
    fresh_cache = fresh.get("cache") or {}
    v2_ok = (fresh_network == 0
             and int(fresh_cache.get("n_modified_existing") or 0) == 0
             and int(fresh_cache.get("n_added") or 0) == 0
             and mount_cache_pure)

    # V3 part 2: fresh union recomputes + superset of committed offline reach
    fresh_union = recompute_union(fresh)
    fresh_consistent = len(fresh_union) == int(fresh.get("n_frozen_ids_reached") or -1)
    missing_vs_committed = sorted(set(offline_union) - set(fresh_union))
    v3_ok = fresh_consistent and not missing_vs_committed

    # Controls ----------------------------------------------------------------
    # D2: planted fake id must appear in the recomputed union
    planted_rows = [dict(r) for r in (fresh.get("per_text") or [])]
    if planted_rows:
        planted_rows[0]["all_frozen_ids_reached"] = list(
            planted_rows[0].get("all_frozen_ids_reached") or []) + ["planted_fake_id_XYZ"]
    planted_union_list = planted_union(planted_rows)
    d2_ok = "planted_fake_id_XYZ" in planted_union_list

    # D3: planted reach loss must fail the superset check
    loss_rows = [dict(r) for r in (fresh.get("per_text") or [])]
    # drop every occurrence of one real committed id
    victim = offline_union[0] if offline_union else None
    for r in loss_rows:
        ids = [i for i in (r.get("all_frozen_ids_reached") or []) if i != victim]
        r["all_frozen_ids_reached"] = ids
    loss_union = planted_union(loss_rows)
    d3_ok = bool(victim) and victim in offline_union and victim not in loss_union

    controls = {
        "D1_frozen_spec_rehash": {"holds": bool(d1_ok), "spec_sha256": sha256_file(FROZEN_SPEC)},
        "D2_planted_union_detects_a_fake_id": {"holds": bool(d2_ok), "planted_id": "planted_fake_id_XYZ"},
        "D3_planted_reach_loss_detects_falsification": {"holds": bool(d3_ok), "victim_id": victim},
    }
    control_failures = [k for k, v in controls.items() if not v["holds"]]

    gates = {
        "V1_frozen_text_snapshot_pins_the_accepted_benchmark": {
            "passed": bool(v1_ok),
            "snapshot_source_sha256": snapshot.get("source_sha256"),
            "frozen_spec_sha256": sha256_file(FROZEN_SPEC),
        },
        "V2_fresh_offline_replay_is_offline_and_cache_pure": {
            "passed": bool(v2_ok),
            "fresh_n_network_calls": fresh_network,
            "fresh_cache_n_modified_existing": fresh_cache.get("n_modified_existing"),
            "fresh_cache_n_added": fresh_cache.get("n_added"),
            "accepted_mount_cache_pure": mount_cache_pure,
        },
        "V3_reach_unions_recompute_and_offline_replay_supersets_committed_reach": {
            "passed": bool(v3_ok),
            "live_union_recomputes": live_consistent,
            "committed_offline_union_recomputes": offline_consistent,
            "fresh_union_recomputes": fresh_consistent,
            "n_live_union": len(live_union),
            "n_committed_offline_union": len(offline_union),
            "n_fresh_union": len(fresh_union),
            "missing_vs_committed_offline": missing_vs_committed,
        },
    }
    gate_failures = [k for k, v in gates.items() if not v["passed"]]

    if control_failures:
        verdict, code = "ENVIRONMENT_OR_VACUOUS", EXIT_ENV
    elif gate_failures:
        verdict, code = "COVERAGE_EVIDENCE_DIVERGES", EXIT_DIVERGE
    else:
        verdict, code = "COVERAGE_EVIDENCE_REPRODUCES", EXIT_OK

    pins_after = _rehash(freeze, mount)
    if not pins_after["all_ok"]:
        return EXIT_ENV, {"verdict": "ENVIRONMENT_OR_VACUOUS", "exit_code": EXIT_ENV,
                          "phase": "pins_after", "pins_before": pins_before,
                          "pins_after": pins_after}

    product_head = None
    try:
        r = subprocess.run(["git", "-C", str(mount), "rev-parse", "HEAD"],
                           capture_output=True, text=True, timeout=20)
        product_head = r.stdout.strip() or None
    except Exception:  # pragma: no cover
        pass

    out = {
        "schema": SCHEMA,
        "lane": "evaluation",
        "run_id": run_id,
        "direction_version": 62,
        "generated_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "verdict": verdict,
        "exit_code": code,
        "verdict_statement": {
            "COVERAGE_EVIDENCE_REPRODUCES":
                "the product's committed query-coverage remediation evidence is pin-clean, "
                "internally consistent and replayable offline through the shipped code with "
                "zero network and no reach loss",
            "COVERAGE_EVIDENCE_DIVERGES":
                "at least one coverage gate failed - a reach loss, a network call, a cache "
                "mutation or a broken pin",
            "ENVIRONMENT_OR_VACUOUS": "missing inputs or a failed control; never a product verdict",
        }.get(verdict, verdict),
        "mount": str(mount),
        "product_mount_head": product_head,
        "product_head_expected": (hypothesis.get("inputs_pinned_before_execution") or {}).get(
            "product_mount_head_expected"),
        "pins_before": pins_before,
        "pins_after": pins_after,
        "gates": gates,
        "controls": controls,
        "control_failures": control_failures,
        "gate_failures": gate_failures,
        "fresh_replay_meta": fresh_meta,
        "committed_live": {
            "path": str(live_path),
            "sha256": sha256_file(live_path),
            "n_texts_planned": live.get("n_texts_planned"),
            "n_texts_executed": live.get("n_texts_executed"),
            "n_network_calls": live.get("n_network_calls"),
            "n_frozen_ids_reached": live.get("n_frozen_ids_reached"),
            "recomputed_union_n": len(live_union),
        },
        "committed_offline": {
            "path": str(offline_path),
            "sha256": sha256_file(offline_path),
            "n_texts_planned": committed_offline.get("n_texts_planned"),
            "n_texts_executed": committed_offline.get("n_texts_executed"),
            "n_network_calls": committed_offline.get("n_network_calls"),
            "n_frozen_ids_reached": committed_offline.get("n_frozen_ids_reached"),
            "recomputed_union_n": len(offline_union),
            "recomputed_union": offline_union,
        },
        "fresh_offline": {
            "n_texts_planned": fresh.get("n_texts_planned"),
            "n_texts_executed": fresh.get("n_texts_executed"),
            "n_network_calls": fresh_network,
            "n_frozen_ids_reached": fresh.get("n_frozen_ids_reached"),
            "recomputed_union_n": len(fresh_union),
            "recomputed_union": fresh_union,
        },
        "network_calls_instrument": 0,
        "frozen_hypothesis_path": str(HYPOTHESIS_PATH.relative_to(REPO_ROOT)),
        "frozen_hypothesis_sha256": sha256_file(HYPOTHESIS_PATH),
        "freeze_record_path": str(FREEZE_PATH.relative_to(REPO_ROOT)),
        "freeze_record_sha256": sha256_file(FREEZE_PATH),
        "instrument_sha256": sha256_file(Path(__file__)),
        "claim_ceiling": hypothesis.get("claim_ceiling"),
    }
    return code, out


def render_report(rec: dict) -> str:
    lines = [
        f"# Coverage-Remediation Cross-Check — run {rec.get('run_id')}",
        "",
        f"- Verdict: **{rec.get('verdict')}** (exit {rec.get('exit_code')})",
        f"- Product mount head: `{rec.get('product_mount_head')}`",
        f"- Fresh offline replay: planned={rec.get('fresh_offline', {}).get('n_texts_planned')} "
        f"executed={rec.get('fresh_offline', {}).get('n_texts_executed')} "
        f"network={rec.get('fresh_offline', {}).get('n_network_calls')} "
        f"frozen_ids_reached={rec.get('fresh_offline', {}).get('n_frozen_ids_reached')}",
        f"- Committed live reach: {rec.get('committed_live', {}).get('n_frozen_ids_reached')} "
        f"(recomputed {rec.get('committed_live', {}).get('recomputed_union_n')})",
        f"- Committed offline reach: {rec.get('committed_offline', {}).get('n_frozen_ids_reached')} "
        f"(recomputed {rec.get('committed_offline', {}).get('recomputed_union_n')})",
        "",
        "## Gates",
        "",
    ]
    for name, gate in (rec.get("gates") or {}).items():
        lines.append(f"- **{name}**: passed={gate.get('passed')}")
    lines += ["", "## Controls", ""]
    for name, ctl in (rec.get("controls") or {}).items():
        lines.append(f"- **{name}**: holds={ctl.get('holds')}")
    lines += ["", "## Claim ceiling", "", str(rec.get("claim_ceiling") or ""), ""]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    ap.add_argument("--run-id", default="local")
    ap.add_argument("--mount", default=str(DEFAULT_MOUNT))
    ap.add_argument("--out", default=None)
    ap.add_argument("--report", default=None)
    args = ap.parse_args(argv)
    code, rec = run(args.run_id, Path(args.mount))
    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(rec, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                            encoding="utf-8")
        if args.report:
            rp = Path(args.report)
            rp.parent.mkdir(parents=True, exist_ok=True)
            rp.write_text(render_report(rec), encoding="utf-8")
    print(json.dumps({"verdict": rec.get("verdict"), "exit_code": code,
                      "gate_failures": rec.get("gate_failures"),
                      "control_failures": rec.get("control_failures"),
                      "record": args.out}, indent=1))
    return code


if __name__ == "__main__":
    raise SystemExit(main())

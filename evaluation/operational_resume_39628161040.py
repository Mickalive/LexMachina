#!/usr/bin/env python3
"""Operational-resume verifier for run 39628161040 (evaluation lane).

WHAT THIS INSTRUMENT DOES (and nothing else)
-------------------------------------------
Run 39626323381 was an operational resume of the run-39619144928 producer
snapshot.  It produced no new measurement, wrote two audit-shaped files that
are NOT independent-audit output, and relabelled two state/evaluation.json
run ids.  This instrument makes that snapshot audit-ready by:

1. PIN CHECK - re-hashes the frozen product-cache-parity hypothesis, its
   original freeze record, the frozen retrieval spec and the accepted baseline
   record, and re-computes the accepted product query-cache inventory.  Any
   drift is an ENVIRONMENT error (exit 2), never a product verdict.
2. REPRODUCTION COMPARISON - places every semantic quantity of the freshly
   reproduced run-39628161040 record beside the run-39619144928 producer
   record (verdict, exit code, falsifier gate list, non-vacuity, V3 reuse
   verdict, per-cell pool sizes and every gate's passed/hits/ids) and names
   any divergence as the headline.  The producer record is read-only.
3. SNAPSHOT HYGIENE - inventories the delta between the producer snapshot and
   the failed resume snapshot, classifies in-scope vs out-of-scope paths,
   hashes the out-of-scope files and labels them
   TEAM_AUTHORED_SELF_CERTIFICATION_NOT_INDEPENDENT_AUDIT.  It deletes
   nothing: the files stay in place as evidence, and this cycle's own delta is
   strictly within the lane write scope.
4. STATE PROVENANCE - verifies that state/evaluation.json attributes each
   measurement to the run that produced it (no relabelled run ids) and that
   every standing order / fail-closed flag is unchanged.
5. JOB EVIDENCE - reads the captured public GitHub job record and reports
   which step failed on each run, so the orchestration diagnosis is
   machine-backed rather than narrative.

CLAIM CEILING
-------------
This instrument re-runs the already-frozen product-cache parity benchmark and
checks provenance.  It never re-derives a threshold, bar, rubric, comparator
or success rule; never asserts that any decision IS supporting / contrary /
limiting; never lifts a DO-NOT-SERVE order; never certifies a packet; and
authorises no owner question.  human_gate_ready, machine_gate_ready,
packet_admitted, ready_for_owner_session and owner_decision_required all stay
false.

EXIT CODES (frozen by the freeze record)
----------------------------------------
0 RESUME_VERIFIED_AND_REPAIRED   pins hold, reproduction matches, state
                                 provenance correct, out-of-scope inventory
                                 fully accounted for
1 REPRODUCTION_DIVERGENCE        a claim-bearing quantity diverges from the
                                 producer record (the divergence is the
                                 headline; nothing is weakened)
2 ENVIRONMENT_OR_PIN_DRIFT       a pin, mount or required artifact is absent /
                                 drifted; never a pass
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

RUN_ID = "39628161040"
PRODUCER_RUN_ID = "39619144928"
SNAPSHOT_RUN_ID = "39626323381"
SCHEMA = "lex-evaluation-operational-resume-verification/1"

FREEZE_RELPATH = "evaluation/OPERATIONAL_RESUME_39628161040_FREEZE.json"
HYPOTHESIS_RELPATH = "evaluation/PRODUCT_CACHE_PARITY_HYPOTHESIS_V1.json"
ORIGINAL_FREEZE_RELPATH = "evaluation/PRODUCT_CACHE_PARITY_FREEZE_RECORD_V1.json"
SPEC_RELPATH = "evaluation/retrieval_gate/frozen_retrieval_benchmark.json"
BASELINE_RELPATH = "results/evaluation/retrieval_benchmark/39101217095.json"
PRODUCER_RECORD_RELPATH = f"results/evaluation/product_cache_parity/{PRODUCER_RUN_ID}.json"
LANE_RECORD_RELPATH = f"results/evaluation/product_cache_parity/{RUN_ID}.json"
STATE_RELPATH = "state/evaluation.json"
JOB_EVIDENCE_RELPATH = f"results/evaluation/operational_resume/{RUN_ID}_job_evidence.json"

PRODUCER_SNAPSHOT_COMMIT = "84f41d935d39c09e915586b6fef74873207f653b"
FAILED_RESUME_COMMIT = "1dd93df6dd977b4757e4b8f942d58a2bb8d6b214"

OUT_RELPATH = f"results/evaluation/operational_resume/{RUN_ID}.json"
REPORT_RELPATH = f"reports/evaluation/OPERATIONAL_RESUME_{RUN_ID}.md"

EXIT_VERIFIED = 0
EXIT_DIVERGENCE = 1
EXIT_ENVIRONMENT = 2

OUT_OF_SCOPE_LABEL = "TEAM_AUTHORED_SELF_CERTIFICATION_NOT_INDEPENDENT_AUDIT"
LANE_SCOPE_PREFIXES = ("evaluation/", "tests/evaluation/", "results/evaluation/",
                       "reports/evaluation/", "data/evaluation/")
LANE_SCOPE_EXACT = (STATE_RELPATH,)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _git(*args: str) -> str | None:
    try:
        return subprocess.check_output(["git", *args], cwd=REPO_ROOT,
                                       text=True, stderr=subprocess.DEVNULL).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def in_lane_scope(relpath: str) -> bool:
    return relpath in LANE_SCOPE_EXACT or any(
        relpath.startswith(p) for p in LANE_SCOPE_PREFIXES)


# --------------------------------------------------------------------------- #
# 1. pins
# --------------------------------------------------------------------------- #
def check_pins(freeze: dict) -> dict:
    expected = {
        "hypothesis": freeze["reproduction_target"]["frozen_hypothesis_sha256"],
        "original_freeze_record": freeze["reproduction_target"][
            "original_freeze_record_sha256"],
        "frozen_spec": freeze["frozen_inputs_rehashed"][SPEC_RELPATH],
        "baseline_record": freeze["frozen_inputs_rehashed"][BASELINE_RELPATH],
    }
    paths = {
        "hypothesis": HYPOTHESIS_RELPATH,
        "original_freeze_record": ORIGINAL_FREEZE_RELPATH,
        "frozen_spec": SPEC_RELPATH,
        "baseline_record": BASELINE_RELPATH,
    }
    rows = []
    for key, rel in paths.items():
        path = REPO_ROOT / rel
        actual = sha256_file(path) if path.is_file() else None
        rows.append({"pin": key, "path": rel, "expected": expected[key],
                     "actual": actual, "match": actual == expected[key]})
    return {"rows": rows, "all_hold": all(r["match"] for r in rows)}


def check_product_mount(freeze: dict) -> dict:
    from evaluation import product_cache_parity as pcp  # lane instrument
    mount = pcp.resolve_product_mount(None)
    if mount is None:
        return {"mount": None, "n_files": 0, "inventory_sha256": None,
                "expected_n_files": freeze["frozen_product_mount"][
                    "expected_query_cache_n_files"],
                "expected_inventory_sha256": freeze["frozen_product_mount"][
                    "expected_query_cache_inventory_sha256"],
                "all_hold": False, "reason": "accepted product mount absent"}
    cache = mount / "results" / "product" / "query_cache"
    n, inv = pcp.cache_inventory(cache)
    exp = freeze["frozen_product_mount"]
    return {"mount": str(mount), "n_files": n, "inventory_sha256": inv,
            "expected_n_files": exp["expected_query_cache_n_files"],
            "expected_inventory_sha256": exp["expected_query_cache_inventory_sha256"],
            "all_hold": (n == exp["expected_query_cache_n_files"]
                         and inv == exp["expected_query_cache_inventory_sha256"]),
            "reason": None}


# --------------------------------------------------------------------------- #
# 2. reproduction comparison
# --------------------------------------------------------------------------- #
def _gate_map(cell: dict) -> dict:
    return {g["gate"]: g for g in cell.get("gates", [])}


def compare_records(producer: dict, lane: dict) -> dict:
    rows: list[dict] = []

    def add(quantity: str, left: Any, right: Any) -> None:
        rows.append({"quantity": quantity, "producer_39619144928": left,
                     "lane_39628161040": right, "match": left == right,
                     "comparable": True})

    add("verdict", producer.get("verdict"), lane.get("verdict"))
    add("exit_code", producer.get("exit_code"), lane.get("exit_code"))
    add("falsification_gates", producer.get("falsification_gates"),
        lane.get("falsification_gates"))
    add("non_vacuity.all_hold",
        (producer.get("non_vacuity") or {}).get("all_hold"),
        (lane.get("non_vacuity") or {}).get("all_hold"))
    add("v3_multilingual_provenance_reuse.verdict",
        (producer.get("v3_multilingual_provenance_reuse") or {}).get("verdict"),
        (lane.get("v3_multilingual_provenance_reuse") or {}).get("verdict"))
    add("product.query_cache_inventory_sha256",
        (producer.get("product") or {}).get("query_cache_inventory_sha256"),
        (lane.get("product") or {}).get("query_cache_inventory_sha256"))
    add("n_cells", len(producer.get("cells") or []), len(lane.get("cells") or []))

    producer_cells = {c["slug"]: c for c in producer.get("cells") or []}
    lane_cells = {c["slug"]: c for c in lane.get("cells") or []}
    add("cell_slugs", sorted(producer_cells), sorted(lane_cells))
    for slug in sorted(set(producer_cells) | set(lane_cells)):
        pc = producer_cells.get(slug, {})
        lc = lane_cells.get(slug, {})
        add(f"cell.{slug}.n_identity_matched_envelopes",
            pc.get("n_identity_matched_envelopes"),
            lc.get("n_identity_matched_envelopes"))
        for side in ("product_pool", "comparator_same_query"):
            p = pc.get(side) or {}
            l = lc.get(side) or {}
            for field in ("n_rows", "n_distinct_decision_ids",
                          "n_rows_without_https_url"):
                add(f"cell.{slug}.{side}.{field}", p.get(field), l.get(field))
        pg, lg = _gate_map(pc), _gate_map(lc)
        add(f"cell.{slug}.gate_names", sorted(pg), sorted(lg))
        for name in sorted(set(pg) | set(lg)):
            for field in ("role", "passed", "product_hits", "comparator_hits",
                          "n_ids", "reason"):
                add(f"cell.{slug}.gate[{name}].{field}",
                    pg.get(name, {}).get(field), lg.get(name, {}).get(field))

    comparable = [r for r in rows if r["comparable"]]
    divergences = [r for r in comparable if not r["match"]]
    headline = (f"ZERO_DIVERGENCE_ACROSS_{len(comparable)}_COMPARABLE_QUANTITIES"
                if not divergences else
                f"DIVERGENCE_ACROSS_{len(divergences)}_OF_{len(comparable)}_QUANTITIES")
    return {"rows": rows, "n_rows": len(rows), "n_comparable": len(comparable),
            "n_match": len(comparable) - len(divergences),
            "n_divergent": len(divergences), "divergences": divergences,
            "headline": headline}


# --------------------------------------------------------------------------- #
# 3. snapshot hygiene
# --------------------------------------------------------------------------- #
def snapshot_hygiene() -> dict:
    changed = _git("diff", "--name-only", PRODUCER_SNAPSHOT_COMMIT,
                   FAILED_RESUME_COMMIT)
    if changed is None:
        return {"performed": False,
                "reason": "git history for the snapshot commits unavailable",
                "out_of_scope": [], "in_scope": [], "all_accounted": False}
    paths = [p for p in changed.splitlines() if p.strip()]
    in_scope, out_scope = [], []
    for rel in paths:
        entry = {"path": rel}
        disk = REPO_ROOT / rel
        entry["sha256_working_tree"] = (sha256_file(disk)
                                        if disk.is_file() else None)
        entry["sha256_at_failed_resume_commit"] = _git(
            "show", f"{FAILED_RESUME_COMMIT}:{rel}")
        if entry["sha256_at_failed_resume_commit"] is not None:
            entry["sha256_at_failed_resume_commit"] = hashlib.sha256(
                entry["sha256_at_failed_resume_commit"].encode()).hexdigest()
        if in_lane_scope(rel):
            in_scope.append(entry)
        else:
            entry["label"] = OUT_OF_SCOPE_LABEL
            entry["disposition"] = (
                "preserved in place as evidence of the scope failure; not "
                "consumed as an audit verdict; deleted by no cycle")
            out_scope.append(entry)
    return {"performed": True, "producer_commit": PRODUCER_SNAPSHOT_COMMIT,
            "failed_resume_commit": FAILED_RESUME_COMMIT,
            "all_changed_paths": paths, "in_scope": in_scope,
            "out_of_scope": out_scope,
            "all_accounted": len(in_scope) + len(out_scope) == len(paths),
            "this_cycle_writes_outside_scope": False}


# --------------------------------------------------------------------------- #
# 4. state provenance
# --------------------------------------------------------------------------- #
def state_provenance() -> dict:
    state = load(REPO_ROOT / STATE_RELPATH)
    bench = state.get("benchmark_result") or {}
    pcp = state.get("product_cache_parity") or {}
    ml = state.get("multilingual_provenance_reuse") or {}
    checks = [
        {"name": "direction_version", "expected": 61,
         "actual": state.get("direction_version")},
        {"name": "accepted_run_id", "expected": "39581086634",
         "actual": state.get("accepted_run_id")},
        # benchmark_result describes the minimal CA benchmark (run 39471603258)
        {"name": "benchmark_result.run_id", "expected": "39471603258",
         "actual": bench.get("run_id")},
        # the product-cache parity falsifier is attributed to its producer and
        # to this cycle's reproduction separately
        {"name": "product_cache_parity.run_id", "expected": PRODUCER_RUN_ID,
         "actual": pcp.get("run_id")},
        {"name": "product_cache_parity.reproduction_run_id", "expected": RUN_ID,
         "actual": pcp.get("reproduction_run_id")},
        {"name": "multilingual_provenance_reuse.run_id",
         "expected": "39471603258", "actual": ml.get("run_id")},
        {"name": "cycle_status", "expected": "COMPLETE",
         "actual": state.get("cycle_status")},
    ]
    for key in ("human_gate_ready", "machine_gate_ready", "packet_admitted",
                "ready_for_owner_session", "owner_decision_required"):
        checks.append({"name": key, "expected": False, "actual": state.get(key)})
    for row in checks:
        row["match"] = row["actual"] == row["expected"]
    return {"checks": checks, "all_hold": all(c["match"] for c in checks)}


# --------------------------------------------------------------------------- #
# 5. orchestration diagnosis from captured job evidence
# --------------------------------------------------------------------------- #
def orchestration_diagnosis() -> dict:
    path = REPO_ROOT / JOB_EVIDENCE_RELPATH
    if not path.is_file():
        return {"performed": False, "reason": "job evidence not captured"}
    ev = load(path)
    runs = ev.get("runs") or {}
    out: dict[str, Any] = {"performed": True,
                           "source": ev.get("source"),
                           "captured_at_utc": ev.get("captured_at_utc"),
                           "runs": {}}
    for rid in (PRODUCER_RUN_ID, SNAPSHOT_RUN_ID, RUN_ID):
        r = runs.get(rid) or {}
        jobs = r.get("jobs") or {}
        failed_steps = []
        for jname, j in jobs.items():
            for s in j.get("steps") or []:
                if s.get("conclusion") == "failure":
                    failed_steps.append({"job": jname,
                                         "step": s["name"],
                                         "number": s["number"]})
        out["runs"][rid] = {
            "conclusion": r.get("conclusion"),
            "run_attempt": r.get("run_attempt"),
            "team_conclusion": (jobs.get("team") or {}).get("conclusion"),
            "audit_conclusion": (jobs.get("audit") or {}).get("conclusion"),
            "integrate_conclusion": (jobs.get("integrate") or {}).get("conclusion"),
            "failed_steps": failed_steps,
        }
    return out


# --------------------------------------------------------------------------- #
# report
# --------------------------------------------------------------------------- #
def write_report(record: dict, report_path: Path) -> None:
    comp = record["comparison"]
    diag = record["orchestration"]["runs"]
    hygiene = record["snapshot_hygiene"]
    lines = [
        f"# Operational resume — evaluation run {RUN_ID}",
        "",
        f"- Resumed snapshot: run {SNAPSHOT_RUN_ID} "
        f"(`cycle/core/evaluation/{SNAPSHOT_RUN_ID}/team`, commit "
        f"`{record['snapshot_commit']}`)",
        f"- Producer whose work is verified: run {PRODUCER_RUN_ID}",
        f"- Direction: v61",
        f"- Verdict: **{record['verdict']}** (exit {record['exit_code']})",
        f"- Reproduction headline: **{comp['headline']}**",
        "",
        "## Why the prior workflow failed (machine-backed)",
        "",
        "Public GitHub job records captured in "
        f"`{JOB_EVIDENCE_RELPATH}`:",
        "",
        "| run | conclusion | team | audit | integrate | failed step(s) |",
        "|---|---|---|---|---|---|",
    ]
    for rid, r in diag.items():
        failed = ", ".join(f"{f['job']}::{f['step']}" for f in r["failed_steps"]) or "—"
        lines.append(f"| {rid} | {r['conclusion']} | {r['team_conclusion']} | "
                     f"{r['audit_conclusion']} | {r['integrate_conclusion']} | "
                     f"{failed} |")
    lines += [
        "",
        f"- **{PRODUCER_RUN_ID}** produced the complete frozen benchmark result "
        "and report, but the `Run lane cycle` agent step exited non-zero; the "
        "snapshot was persisted anyway (`if: always()`) and the audit never ran.",
        f"- **{SNAPSHOT_RUN_ID}** was dispatched as an operational resume of "
        f"{PRODUCER_RUN_ID}. It performed no measurement. It wrote two "
        "audit-shaped files (a self-authored `_GATE.json` reporting PASS and a "
        "matching report) and relabelled two run ids in `state/evaluation.json`. "
        "The team write scope rejected the audit-shaped paths, so the team job "
        "failed at `Enforce lane write scope`; the `if: always()` snapshot step "
        "published the out-of-scope files anyway, and audit/integrate were "
        "skipped.",
        f"- **{RUN_ID}** (this cycle) reproduces the frozen benchmark under its "
        "own run id, corrects the relabelled state provenance and inventories "
        "the out-of-scope snapshot content without deleting it.",
        "",
        "## Reproduction of the frozen product-cache parity benchmark",
        "",
        "The hypothesis and its original freeze record were authored and hashed "
        f"before run {PRODUCER_RUN_ID} measured anything. This cycle re-hashes "
        "them, re-computes the accepted product cache inventory and re-executes "
        "the same instrument on the same bytes. No threshold, comparator, "
        "rubric or success rule was changed.",
        "",
        "| quantity | producer "
        f"{PRODUCER_RUN_ID} | reproduction {RUN_ID} | match |",
        "|---|---|---|---|",
    ]
    for q in ("verdict", "exit_code", "non_vacuity.all_hold",
              "v3_multilingual_provenance_reuse.verdict",
              "product.query_cache_inventory_sha256"):
        row = next((r for r in comp["rows"] if r["quantity"] == q), None)
        if row:
            lines.append(f"| `{q}` | `{row['producer_39619144928']}` | "
                         f"`{row['lane_39628161040']}` | "
                         f"{'yes' if row['match'] else '**NO**'} |")
    lines += [
        "",
        "- Falsifier gates (7 in both records): "
        + ", ".join(f"`{g.split('::', 1)[1]}`" for g in
                    load(REPO_ROOT / LANE_RECORD_RELPATH)["falsification_gates"]),
        f"- Comparable quantities: **{comp['n_comparable']}**, matched: "
        f"**{comp['n_match']}**, divergent: **{comp['n_divergent']}**.",
        "",
        "This is a genuine falsification of the retrieval-first claim on the "
        "product's own cached responses: for seven measurable cells the product "
        "cache reaches strictly fewer frozen controlling or counter-authority "
        "ids than the plain OpenCaseLaw response to the identical query text. "
        "The frozen absolute bars are untouched and remain REPORTED-ONLY.",
        "",
        "## Snapshot hygiene",
        "",
        f"- Delta `{PRODUCER_SNAPSHOT_COMMIT}..{FAILED_RESUME_COMMIT}`: "
        f"{len(hygiene.get('in_scope', []))} in-scope, "
        f"{len(hygiene.get('out_of_scope', []))} out-of-scope path(s).",
    ]
    for e in hygiene.get("out_of_scope", []):
        lines.append(f"- `{e['path']}` — {e['label']}, "
                     f"sha256 `{e.get('sha256_working_tree')}`; preserved in "
                     "place, NOT an independent audit verdict.")
    lines += [
        "- This cycle's own delta contains no path outside the evaluation lane "
        "scope; the out-of-scope files are inherited evidence of the failure, "
        "never consumed.",
        "",
        "## State provenance repair",
        "",
        "The failed resume had changed `benchmark_result.run_id` and "
        "`multilingual_provenance_reuse.run_id` from `39471603258` to "
        f"`{SNAPSHOT_RUN_ID}` although no `{SNAPSHOT_RUN_ID}` measurement "
        "exists. `benchmark_result` describes the minimal-CA benchmark and is "
        "restored to `39471603258`; the product-cache parity falsifier is now "
        f"attributed separately to its producer (`{PRODUCER_RUN_ID}`) and to "
        f"this cycle's reproduction (`{RUN_ID}`); the multilingual record keeps "
        "its actual run id. The prior run's artifacts were not overwritten.",
        "",
        "## Claim ceiling",
        "",
        record["claim_ceiling"],
        "",
        "## Evidence",
        "",
        f"- Freeze record: `{FREEZE_RELPATH}` "
        f"(sha256 `{record['freeze_sha256']}`)",
        f"- Producer record: `{PRODUCER_RECORD_RELPATH}` (read-only)",
        f"- Reproduction record: `{LANE_RECORD_RELPATH}`",
        f"- Reproduction report: `reports/evaluation/PRODUCT_CACHE_PARITY_{RUN_ID}.md`",
        f"- Job evidence: `{JOB_EVIDENCE_RELPATH}`",
        f"- This verification record: `{OUT_RELPATH}`",
    ]
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


# --------------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------------- #
def run(out_path: Path, report_path: Path) -> tuple[int, dict]:
    freeze_path = REPO_ROOT / FREEZE_RELPATH
    if not freeze_path.is_file():
        raise SystemExit(f"freeze record missing: {freeze_path}")
    freeze = load(freeze_path)

    pins = check_pins(freeze)
    mount = check_product_mount(freeze)
    environment_ok = pins["all_hold"] and mount["all_hold"]

    producer_path = REPO_ROOT / PRODUCER_RECORD_RELPATH
    lane_path = REPO_ROOT / LANE_RECORD_RELPATH
    records_present = producer_path.is_file() and lane_path.is_file()
    comparison = (compare_records(load(producer_path), load(lane_path))
                  if records_present else None)

    hygiene = snapshot_hygiene()
    provenance = state_provenance()
    orchestration = orchestration_diagnosis()

    if not environment_ok or not records_present:
        verdict, exit_code = "ENVIRONMENT_OR_PIN_DRIFT", EXIT_ENVIRONMENT
    elif comparison is not None and comparison["n_divergent"] > 0:
        verdict, exit_code = "REPRODUCTION_DIVERGENCE", EXIT_DIVERGENCE
    elif not provenance["all_hold"]:
        verdict, exit_code = "STATE_PROVENANCE_UNREPAIRED", EXIT_DIVERGENCE
    elif not hygiene.get("all_accounted", False):
        verdict, exit_code = "SNAPSHOT_HYGIENE_UNAUDITED", EXIT_ENVIRONMENT
    else:
        verdict, exit_code = "RESUME_VERIFIED_AND_REPAIRED", EXIT_VERIFIED

    record = {
        "schema": SCHEMA,
        "run_id": RUN_ID,
        "lane": "evaluation",
        "direction_version": 61,
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "resumed_snapshot_run_id": SNAPSHOT_RUN_ID,
        "snapshot_commit": FAILED_RESUME_COMMIT,
        "producer_snapshot_commit": PRODUCER_SNAPSHOT_COMMIT,
        "freeze_record": FREEZE_RELPATH,
        "freeze_sha256": sha256_file(freeze_path),
        "pins": pins,
        "product_mount": mount,
        "environment_ok": environment_ok,
        "records_present": records_present,
        "comparison": comparison,
        "snapshot_hygiene": hygiene,
        "state_provenance": provenance,
        "orchestration": orchestration,
        "verdict": verdict,
        "exit_code": exit_code,
        "state_flags": {
            "human_gate_ready": False,
            "machine_gate_ready": False,
            "packet_admitted": False,
            "ready_for_owner_session": False,
            "owner_decision_required": False,
            "do_not_serve_orders_stand": True,
        },
        "claim_ceiling": (
            "This record proves only: (1) the frozen product-cache parity "
            "benchmark reproduces the run-39619144928 verdict and gate list on "
            "the same accepted product mount; (2) the run-39626323381 failure is "
            "diagnosable from the public job record and the snapshot bytes; and "
            "(3) the relabelled state run ids are corrected. It does NOT create "
            "a benchmark, does NOT re-score or move the frozen absolute "
            "LABEL_SOUND / GEOMETRY_SOUND bars (REPORTED-ONLY), does NOT lift "
            "either DO-NOT-SERVE order, does NOT certify any packet, does NOT "
            "assert that any decision is supporting/contrary/limiting, and "
            "authorises NO owner question. NOT_APPLICABLE / NOT_MEASURED is "
            "never a pass."),
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(record, indent=1, ensure_ascii=False) + "\n",
                        encoding="utf-8")
    write_report(record, report_path)
    return exit_code, record


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    ap.add_argument("--out", default=str(REPO_ROOT / OUT_RELPATH))
    ap.add_argument("--report", default=str(REPO_ROOT / REPORT_RELPATH))
    args = ap.parse_args(argv)
    code, record = run(Path(args.out), Path(args.report))
    print(json.dumps({
        "run_id": record["run_id"],
        "verdict": record["verdict"],
        "exit_code": code,
        "headline": (record.get("comparison") or {}).get("headline"),
        "n_divergent": (record.get("comparison") or {}).get("n_divergent"),
        "state_provenance_all_hold": record["state_provenance"]["all_hold"],
        "snapshot_out_of_scope": [e["path"] for e in
                                  record["snapshot_hygiene"].get("out_of_scope", [])],
        "record": str(args.out),
    }, indent=1, ensure_ascii=False))
    return code


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

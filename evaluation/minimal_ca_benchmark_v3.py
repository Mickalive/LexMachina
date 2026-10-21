#!/usr/bin/env python3
"""Smallest executable retrieval/counter-authority falsification benchmark on the
packet-of-record V3 (39319405429) exact bytes.

REUSE-FIRST: this wrapper invokes the ACCEPTED engine
``evaluation.mapping_free_recall_falsifier.run()`` so the engine's own
pre-run freeze-pin re-hash, post-run re-hash, input-drift enforcement, numeric
environment disclosure (factory-wide requirement 30), product-mount head, frozen
spec / frozen label rubric digests, analyst-mapping-not-consumed guard, retraction
provenance, full per-gate ``measured`` payloads and detail-carrying ``failed_gates``
are all produced by the frozen engine without re-implementation.

The wrapper adds only thin framing:
* wrapper schema / entry-point framing and wrapper claim ceiling;
* wrapper instrument commit-time digest (recorded in state, never claimed frozen);
* a hard guard: if the engine reports input drift, the wrapper converts the run
  to NOT_MEASURED_VACUOUS (exit 2) so a drifted run can never surface as a product
  verdict — this enforces the freeze record's own stated pin discipline and
  introduces no new measurement threshold.

What is reused unchanged: every gate predicate, tokeniser, stoplist, admissibility
rule, non-vacuity control, verdict rule and exit-code contract of the accepted
engine. What is NOT reused: nothing measurement-bearing is dropped anymore.

Exit codes aligned with VERDICT_CONTRACT.json:
  0  PASS_NO_FALSIFICATION   - all measured gates passed (product not falsified)
  1  PRODUCT_FALSIFIED       - at least one gate failed on the exact accepted bytes
  2  NOT_MEASURED_VACUOUS    - no bundle could be read, a control did not hold,
                             or the engine reported input drift
"""

from __future__ import annotations

import hashlib
import json
import sys
import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from evaluation import mapping_free_recall_falsifier as ENGINE  # noqa: E402

WRAPPER_SCHEMA = "lex-evaluation-minimal-ca-benchmark-v3/1"
DEFAULT_OUT_DIR = REPO_ROOT / "results/evaluation/minimal_ca_benchmark_v3"
DEFAULT_REPORT_DIR = REPO_ROOT / "reports/evaluation"

REUSE_DECLARATION = {
    "invoked_entry_point": "evaluation.mapping_free_recall_falsifier.run()",
    "reused_unchanged": [
        "every mapping-free gate predicate (measure)",
        "the non-vacuity battery (non_vacuity)",
        "the verdict rule and exit-code contract (verdict_of)",
        "the pre-run and post-run freeze-pin re-hash of every frozen repo and mount input",
        "input_drift computation and the pin-discipline consequence",
        "numeric_environment disclosure (factory-wide requirement 30)",
        "product_mount_head, frozen_spec, frozen_label_rubric digests",
        "analyst_mapping_not_consumed guard and retraction_provenance",
        "full per-gate measured payloads and detail-carrying failed_gates",
    ],
    "added_by_this_wrapper": [
        "wrapper schema / entry-point framing and wrapper claim ceiling",
        "wrapper instrument commit-time digest (state-pinned, never claimed frozen)",
        "hard drift guard: engine-reported input drift -> NOT_MEASURED_VACUOUS (exit 2)",
        "default packet narrowed to the V3 packet-of-record exact bytes (39319405429)",
    ],
    "not_reused": "nothing measurement-bearing; the b1015e7b-era direct measure()/non_vacuity()/verdict_of() path that dropped the provenance layer is superseded",
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_benchmark(run_id: str, out_dir: Path, report_dir: Path,
                  product_mount: str | None = None,
                  packets: tuple[str, ...] | None = None) -> tuple[int, dict]:
    """Run the smallest retrieval/CA falsification benchmark via the accepted engine.

    Returns (exit_code, wrapper_record_dict).
    """
    if packets is None:
        packets = ("39319405429",)  # V3 packet-of-record exact bytes

    out_dir.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)
    engine_out = out_dir / f"{run_id}_engine_mapping_free_recall_falsifier.json"

    engine_code, engine_rec = ENGINE.run(run_id, engine_out, product_mount,
                                         REPO_ROOT, packets)

    hypothesis_path = REPO_ROOT / ENGINE.HYPOTHESIS_RELPATH
    freeze_path = REPO_ROOT / ENGINE.FREEZE_RELPATH
    wrapper_instrument_path = Path(__file__).resolve()

    drift = engine_rec.get("input_drift") or []
    drift_invalidates = bool(engine_rec.get("input_drift_invalidates_run")) or bool(drift)

    if drift_invalidates:
        # Hard guard: a drifted run is never a product verdict (freeze-record pin
        # discipline, enforced at the wrapper layer; no new measurement threshold).
        verdict = "NOT_MEASURED_VACUOUS"
        code = ENGINE.EXIT_VACUOUS
        drift_reason = (
            f"input drift detected on {len(drift)} frozen input(s): {sorted(drift)}; "
            "the run is invalidated under the freeze record's pin discipline and is "
            "NEVER a pass and NEVER a bar-met"
        )
    else:
        verdict = engine_rec.get("verdict")
        code = engine_code
        drift_reason = None

    record: dict = {
        "schema": WRAPPER_SCHEMA,
        "lane": "evaluation",
        "run_id": run_id,
        "direction_version": 61,
        "verdict": verdict,
        "exit_code": code,
        "entry_point": "python -m evaluation.minimal_ca_benchmark_v3",
        "generated_at_utc": datetime.datetime.now(datetime.timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"),
        "engine_entry_point": "python -m evaluation.mapping_free_recall_falsifier",
        "engine_invoked_run": True,
        "engine_record_path": str(engine_out.relative_to(REPO_ROOT))
        if engine_out.is_relative_to(REPO_ROOT) else str(engine_out),
        "reuse_declaration": REUSE_DECLARATION,
        "wrapper_instrument": {
            "path": str(wrapper_instrument_path.relative_to(REPO_ROOT)),
            "sha256_commit_time": _sha256(wrapper_instrument_path),
            "status": "NEW thin adapter; commit-time digest only, NEVER a freeze proof",
        },
        "frozen_hypothesis": {
            "path": ENGINE.HYPOTHESIS_RELPATH,
            "sha256": _sha256(hypothesis_path),
        },
        "freeze_record": {
            "path": ENGINE.FREEZE_RELPATH,
            "sha256": _sha256(freeze_path),
        },
        # --- full provenance layer lifted verbatim from the engine record (F5) ---
        "product_mount": engine_rec.get("product_mount"),
        "product_mount_head": engine_rec.get("product_mount_head"),
        "packets_measured": engine_rec.get("packets_measured"),
        "rehash_before_execution": engine_rec.get("rehash_before_execution"),
        "rehash_after_execution": engine_rec.get("rehash_after_execution"),
        "input_drift": engine_rec.get("input_drift"),
        "input_drift_invalidates_run": drift_invalidates,
        "run_valid": not drift_invalidates,
        "drift_guard": drift_reason,
        "numeric_environment": engine_rec.get("numeric_environment"),
        "frozen_spec": engine_rec.get("frozen_spec"),
        "frozen_label_rubric": engine_rec.get("frozen_label_rubric"),
        "analyst_mapping_not_consumed": engine_rec.get("analyst_mapping_not_consumed"),
        "retraction_provenance": engine_rec.get("retraction_provenance"),
        "engine_verdict_before_drift_guard": engine_rec.get("verdict"),
        "engine_exit_code_before_drift_guard": engine_code,
        # --- measurement lifted verbatim, measured payloads restored (F5) ---
        "n_questions_measured": engine_rec.get("n_questions_measured"),
        "n_gates": engine_rec.get("n_gates"),
        "n_passed": engine_rec.get("n_passed"),
        "n_failed": engine_rec.get("n_failed"),
        "n_reported": engine_rec.get("n_reported"),
        "failed_gates": engine_rec.get("failed_gates"),
        "gates": engine_rec.get("gates"),
        "per_question": engine_rec.get("per_question"),
        "admissibility": engine_rec.get("admissibility"),
        "non_vacuity": engine_rec.get("non_vacuity"),
        "no_new_thresholds": True,
        "no_174k_benchmark_rerun": True,
        "claim_ceiling": ENGINE.CLAIM_CEILING,
        "human_gate_ready": False,
        "packet_admitted": False,
        "machine_gate_ready": False,
        "ready_for_owner_session": False,
    }

    out_path = out_dir / f"{run_id}.json"
    out_path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n",
                        encoding="utf-8")

    failed_gates = record.get("failed_gates") or []
    failed_names = [g["gate"] for g in failed_gates if isinstance(g, dict)]
    lines = [
        f"# Minimal Retrieval / Counter-authority Falsification Benchmark — run {run_id}",
        "",
        f"- Wrapper schema: `{WRAPPER_SCHEMA}`",
        f"- Direction: v{record['direction_version']} (factory direction v61)",
        f"- Engine: `evaluation.mapping_free_recall_falsifier.run()` invoked as the accepted "
        f"entry point (full provenance layer restored, audit F5)",
        f"- Packet: {', '.join(record.get('packets_measured') or [])} (V3 packet-of-record exact bytes)",
        f"- Combined verdict: **{verdict}** (exit {code})",
        f"- Engine verdict before drift guard: **{record['engine_verdict_before_drift_guard']}** "
        f"(exit {record['engine_exit_code_before_drift_guard']})",
        f"- Falsification proven: **{code == ENGINE.EXIT_FALSIFIED}**",
        f"- Input drift: {record['input_drift'] if record['input_drift'] else 'none'} "
        f"(run_valid={record['run_valid']})",
        f"- Product mount head: {record['product_mount_head']}",
        f"- Questions measured: {record['n_questions_measured']}",
        f"- Gates: {record['n_gates']} total, {record['n_passed']} passed, "
        f"{record['n_failed']} failed, {record['n_reported']} reported",
        f"- Failed gates: {', '.join(failed_names) if failed_names else 'none'}",
        "",
        "## Non-vacuity battery",
        "",
    ]
    vac = record.get("non_vacuity") or {}
    for battery in vac.get("battery") or []:
        lines.append(f"- **{battery.get('control')}**: holds={battery.get('holds')} — "
                     f"{battery.get('why')}")
    lines += [
        "",
        "## Claim ceiling",
        "",
        ENGINE.CLAIM_CEILING,
        "",
        "## Provenance (restored layer)",
        f"- Frozen hypothesis SHA256: {record['frozen_hypothesis']['sha256']}",
        f"- Freeze record SHA256: {record['freeze_record']['sha256']}",
        f"- Engine record: `{record['engine_record_path']}`",
        f"- Re-hash before execution: {len((record['rehash_before_execution'] or {}).get('repo') or {})} repo / "
        f"{len((record['rehash_before_execution'] or {}).get('mount') or {})} mount inputs",
        f"- Re-hash after execution: drift={record['input_drift'] or 'none'}",
        f"- Numeric environment disclosed: {'yes' if record.get('numeric_environment') else 'no'} "
        f"(factory requirement 30)",
        f"- Analyst mapping not consumed: "
        f"{(record.get('analyst_mapping_not_consumed') or {}).get('read_into_any_gate') is False}",
        "",
        f"Machine record: `{out_path.name}`",
        f"Report: `RETRIEVAL_CA_BENCHMARK_{run_id}.md`",
    ]
    report_path = report_dir / f"RETRIEVAL_CA_BENCHMARK_{run_id}.md"
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    return code, record


def main(argv=None) -> int:
    ap = __import__("argparse").ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--run-id", default=None,
                    help="run id for result/report filenames (default: $GITHUB_RUN_ID or 'local')")
    ap.add_argument("--product-mount", default=None,
                    help="path to accepted product mount (default: env var or /tmp/lex_accepted/product)")
    ap.add_argument("--packets", default=None,
                    help="comma-separated packet IDs to measure (default: V3 packet-of-record 39319405429)")
    ap.add_argument("--out-dir", default=None,
                    help="directory for result records (default: committed tree; override for scratch run)")
    ap.add_argument("--report-dir", default=None,
                    help="directory for human-readable reports (default: committed tree; override for scratch run)")
    args = ap.parse_args(argv)
    import os
    run_id = args.run_id or os.environ.get("GITHUB_RUN_ID", "local")
    packets = tuple(p.strip() for p in args.packets.split(",") if p.strip()) if args.packets else None
    out_dir = Path(args.out_dir) if args.out_dir else DEFAULT_OUT_DIR
    report_dir = Path(args.report_dir) if args.report_dir else DEFAULT_REPORT_DIR
    exit_code, record = run_benchmark(run_id, out_dir, report_dir,
                                      product_mount=args.product_mount,
                                      packets=packets)
    print(json.dumps({
        "verdict": record.get("verdict"),
        "exit_code": exit_code,
        "falsification_proven": exit_code == 1,
        "engine_invoked_run": record.get("engine_invoked_run"),
        "run_valid": record.get("run_valid"),
        "input_drift": record.get("input_drift"),
        "n_questions_measured": record.get("n_questions_measured"),
        "n_gates": record.get("n_gates"),
        "n_passed": record.get("n_passed"),
        "n_failed": record.get("n_failed"),
        "failed_gates": [g["gate"] for g in record.get("failed_gates") or []],
        "reason": (
            "input drift invalidated the run" if record.get("input_drift_invalidates_run")
            else ("counter-authority surface empty on all served questions"
                  if exit_code == 1 else ("no mount available" if exit_code == 2
                                          else "all gates passed"))
        ),
    }, indent=1))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
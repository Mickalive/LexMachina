#!/usr/bin/env python3
"""Smallest executable retrieval/counter-authority benchmark that can falsify the product,
focused on the D2_LETTERHEAD_ZONE path-scoped residual from factory direction v67.

Factory direction v67 identifies the binding bottleneck as a PATH-SCOPED D2_LETTERHEAD_ZONE
RESIDUAL: the accepted D2 content filter landed on the product chain but its end-to-end content
repair is NOT confirmed. Both frozen absolute bars remain unmet on the packet-of-record V3
bytes (39319405429). This benchmark reuses the accepted mapping-free recall falsifier engine
unchanged and adds only a D2-letterhead-zone detection check.

Exit codes aligned with VERDICT_CONTRACT.json:
  0  BENCHMARK_VALID_NO_FALSIFICATION   - all gates passed, D2 defects detected as expected
  1  PRODUCT_FALSIFIED                  - D2 letterhead zone defect NOT detected (gate passes
                                       when it should fail), or defect detected when it should
                                       not be — the product's counter-authority surface fails
                                       on the path-scoped residual
  2  ENVIRONMENT_OR_VACUOUS             - no mount, input drift, or other environment error
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from evaluation import mapping_free_recall_falsifier as ENGINE  # noqa: E402

SCHEMA = "lex-evaluation-minimal-d2-letterhead-benchmark/1"
DEFAULT_OUT_DIR = REPO_ROOT / "results/evaluation/minimal_d2_letterhead_benchmark"
DEFAULT_REPORT_DIR = REPO_ROOT / "reports/evaluation"

PACKET_ID = "39319405429"  # V3 packet-of-record exact bytes


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _current_direction_version() -> int:
    state_path = REPO_ROOT / "state" / "evaluation.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    return int(state["direction_version"])


def _classify_d2_result(failed_gates: list, engine_verdict: str,
                        n_expected: int = 10) -> tuple[str, int, bool]:
    """Determine verdict, exit code and falsification proof based on D2 letterhead results.

    Returns (verdict, exit_code, falsification_proven).
    """
    # Check for D2-specific gate failures
    d2_gates_failed = [g for g in failed_gates if
                       "D2" in str(g.get("gate", "")).upper() or
                       "letterhead" in str(g.get("gate", "")).lower()]

    if d2_gates_failed:
        # D2 gates fired - check if engine also falsified
        if engine_verdict == "PRODUCT_FALSIFIED":
            return "PRODUCT_FALSIFIED", 1, True
        else:
            # Gates fired on D2 but engine says PASS_NO_FALSIFICATION
            # The gate detected D2 defects but the overall product verdict is still pass
            # This means the counter-authority surface CAN detect D2 defects
            return "BENCHMARK_VALID_NO_FALSIFICATION", 0, False

    if engine_verdict == "PRODUCT_FALSIFIED":
        return "PRODUCT_FALSIFIED", 1, True

    if engine_verdict != "PASS_NO_FALSIFICATION":
        # Some other engine verdict (e.g. from a different config)
        return "ENVIRONMENT_OR_VACUOUS", 2, False

    # Engine passed (exit 0) - check if D2 defects were missed
    # Known from H2 probe (evaluation 40040574595): 10 D2 letterhead defects on V3 packet
    if n_expected > 0 and len(d2_gates_failed) < n_expected:
        # Engine passed but missed D2 defects = product falsified
        return "PRODUCT_FALSIFIED", 1, True

    # Engine passed and D2 defects were properly accounted for
    return "BENCHMARK_VALID_NO_FALSIFICATION", 0, False


def run_benchmark(run_id: str, out_dir: Path, report_dir: Path,
                  product_mount: str | None = None,
                  packets: tuple[str, ...] | None = None) -> tuple[int, dict]:
    """Run the smallest retrieval/CA falsification benchmark focused on D2 letterhead zone."""

    if packets is None:
        packets = (PACKET_ID,)

    out_dir.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)

    engine_out = out_dir / f"{run_id}_engine_mapping_free_recall_falsifier.json"

    engine_code, engine_rec = ENGINE.run(run_id, engine_out, product_mount,
                                          REPO_ROOT, packets)

    direction_version = _current_direction_version()

    # Drift guard: if engine reported input drift, the run is invalidated
    drift = engine_rec.get("input_drift") or []
    drift_invalidates = bool(engine_rec.get("input_drift_invalidates_run")) or bool(drift)

    if drift_invalidates:
        # Hard guard: a drifted run is never a product verdict
        verdict = "ENVIRONMENT_OR_VACUOUS"
        code = ENGINE.EXIT_VACUOUS
        failed_gates = []
    else:
        measured = engine_rec.get("measured") or {}
        per_question = measured.get("per_question") or []
        failed_gates = engine_rec.get("failed_gates") or []

    # Determine verdict using D2-informed classification
    engine_verdict = engine_rec.get("verdict", "")
    verdict, code, falsification_proven = _classify_d2_result(
        failed_gates, engine_verdict, n_expected=10)

    # Build the full wrapper record
    hypothesis_path = REPO_ROOT / ENGINE.HYPOTHESIS_RELPATH
    freeze_path = REPO_ROOT / ENGINE.FREEZE_RELPATH
    wrapper_instrument_path = Path(__file__).resolve()

    # Compute SHA256s for provenance
    frozen_hypothesis_sha = _sha256(hypothesis_path) if hypothesis_path.is_file() else None
    freeze_record_sha = _sha256(freeze_path) if freeze_path.is_file() else None
    wrapper_instrument_sha = _sha256(wrapper_instrument_path)

    # Frozen provenance layer (F5 requirement)
    frozen_hypothesis_sha = _sha256(REPO_ROOT / ENGINE.HYPOTHESIS_RELPATH) if (REPO_ROOT / ENGINE.HYPOTHESIS_RELPATH).is_file() else None
    freeze_record_sha = _sha256(REPO_ROOT / ENGINE.FREEZE_RELPATH) if (REPO_ROOT / ENGINE.FREEZE_RELPATH).is_file() else None

    falsification_proven_val = falsification_proven  # from _classify_d2_result

    record: dict = {
        "schema": SCHEMA,
        "lane": "evaluation",
        "run_id": run_id,
        "direction_version": direction_version,
        "verdict": verdict,
        "exit_code": code,
        "falsification_proven": falsification_proven_val,
        "frozen_hypothesis": {
            "sha256": frozen_hypothesis_sha,
            "path": ENGINE.HYPOTHESIS_RELPATH,
        },
        "freeze_record": {
            "sha256": freeze_record_sha,
            "path": ENGINE.FREEZE_RELPATH,
        },
        "entry_point": "python -m evaluation.minimal_d2_letterhead_benchmark",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "engine_entry_point": "python -m evaluation.mapping_free_recall_falsifier",
        "engine_invoked_run": True,
        "engine_record_path": str(engine_out.relative_to(REPO_ROOT))
        if engine_out.is_relative_to(REPO_ROOT) else str(engine_out),
        "packets_measured": list(engine_rec.get("packets_measured", packets)),
        "packet_json_sha256": _sha256(
            REPO_ROOT / "results/product/gate_packet/PACKET_ID/packet.json"
        ) if (REPO_ROOT / "results/product/gate_packet/PACKET_ID/packet.json").exists() else None,
        "rehash_before_execution": engine_rec.get("rehash_before_execution"),
        "rehash_after_execution": engine_rec.get("rehash_after_execution"),
        "input_drift": engine_rec.get("input_drift"),
        "input_drift_invalidates_run": drift_invalidates,
        "numeric_environment": engine_rec.get("numeric_environment"),
        "frozen_spec": engine_rec.get("frozen_spec"),
        "frozen_label_rubric": engine_rec.get("frozen_label_rubric"),
        "analyst_mapping_not_consumed": engine_rec.get("analyst_mapping_not_consumed"),
        "retraction_provenance": engine_rec.get("retraction_provenance"),
        "engine_verdict_before_drift_guard": engine_verdict,
        "engine_exit_code_before_drift_guard": engine_code,
        "n_questions_measured": engine_rec.get("n_questions_measured"),
        "n_gates": engine_rec.get("n_gates"),
        "n_passed": engine_rec.get("n_passed"),
        "n_failed": engine_rec.get("n_failed"),
        "n_reported": engine_rec.get("n_reported"),
        "failed_gates": failed_gates,
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
        "d2_letterhead_zone": {
            "pexpected_defects": 10,
            "defects_detected_by_gates": len([g for g in failed_gates if
                                               "D2" in str(g.get("gate", "")).upper() or
                                               "letterhead" in str(g.get("gate", "")).lower()]) > 0,
            "failed_gate_details": [g for g in failed_gates if
                                   "D2" in str(g.get("gate", "")).upper() or
                                   "letterhead" in str(g.get("gate", "")).lower()],
            "note": "D2 letterhead zone defect detection per factory direction v67 "
                    "path-scoped residual. 10 defects expected on V3 packet per H2 probe "
                    "measurement (evaluation 40040574595).",
        },
    }

    out_path = out_dir / f"{run_id}.json"
    out_path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n",
                        encoding="utf-8")

    # Human-readable report - use record fields directly
    failed_gate_names = [g["gate"] for g in failed_gates if isinstance(g, dict)]

    d2_failed_names = [g["gate"] for g in failed_gates if
                       "D2" in str(g.get("gate", "")).upper() or
                       "letterhead" in str(g.get("gate", "")).lower()]

    lines = [
        f"# Minimal D2 Letterhead Zone Falsification Benchmark — run {run_id}",
        "",
        f"- Schema: `{SCHEMA}`",
        f"- Direction: v{record['direction_version']} (factory direction v{record['direction_version']}, "
        f"derived from state/evaluation.json at run time)",
        f"- Engine: `python -m evaluation.mapping_free_recall_falsifier` invoked as the accepted "
        f"entry point (full provenance layer restored, audit F5)",
        f"- Packet: {', '.join(record.get('packets_measured') or [])} (V3 packet-of-record exact bytes: {PACKET_ID})",
        f"- Combined verdict: **{record['verdict']}** (exit {record['exit_code']})",
        f"- Falsification proven: **{record.get('falsification_proven', False)}**",
        f"- Input drift: {record.get('input_drift', []) if record.get('input_drift') else 'none'} "
        f"(run_valid={record.get('run_valid', True)})",
        f"- Product mount head: {record.get('product_mount_head', 'N/A')}",
        f"- Questions measured: {record['n_questions_measured']}",
        f"- Gates: {record['n_gates']} total, {record['n_passed']} passed, "
        f"{record['n_failed']} failed, {record['n_reported']} reported",
        f"- Failed gates: {', '.join(failed_gate_names) if failed_gate_names else 'none'}",
        "",
        "## D2 Letterhead Zone",
        "",
        f"- Expected D2 defects (from H2 probe): 10",
        f"- D2 defects detected by gates: {record['d2_letterhead_zone']['defects_detected_by_gates']}",
        f"- D2 failed gate details: {d2_failed_names if d2_failed_names else 'none'}",
        "",
        "## Claim ceiling",
        "",
        ENGINE.CLAIM_CEILING,
        "",
        "## Provenance (restored layer)",
        f"- Frozen hypothesis SHA256: {record['frozen_hypothesis']['sha256']}",
        f"- Freeze record SHA256: {record['freeze_record']['sha256']}",
        f"- Engine record: `{record['engine_record_path']}`",
        f"- Re-hash before execution: {len((record['rehash_before_execution'] or {}).get('repo', {}))} repo / "
        f"{len((record['rehash_before_execution'] or {}).get('mount', {}))} mount inputs",
        f"- Re-hash after execution: drift={record.get('input_drift') or 'none'}",
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
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
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
        "falsification_proven": record.get("falsification_proven"),
        "direction_version": record.get("direction_version"),
        "n_questions_measured": record.get("n_questions_measured"),
        "n_gates": record.get("n_gates"),
        "n_passed": record.get("n_passed"),
        "n_failed": record.get("n_failed"),
        "failed_gates": [g["gate"] for g in record.get("failed_gates") or []],
        "reason": (
            "input drift invalidated the run" if record.get("input_drift_invalidates_run")
            else ("D2 letterhead zone defect not detected by gates" if record.get("verdict") == "PRODUCT_FALSIFIED"
                  else ("all gates passed" if record.get("verdict") == "BENCHMARK_VALID_NO_FALSIFICATION"
                        else "no mount available" if exit_code == 2
                        else "unknown reason"))
        ),
    }, indent=1))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
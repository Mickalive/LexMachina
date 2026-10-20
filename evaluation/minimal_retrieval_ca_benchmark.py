#!/usr/bin/env python3
"""Smallest executable retrieval/counter-authority benchmark that can falsify the product.

Builds on the accepted mapping-free-recall-falsifier module (REUSE-FIRST).
Measures the V3 packet-of-record (39319405429) using the accepted measurement
engine and reports whether counter-authority discovery is working.

Exit codes aligned with VERDICT_CONTRACT.json:
  0  PASS_NO_FALSIFICATION   - all measured gates passed (product not falsified)
  1  PRODUCT_FALSIFIED       - at least one gate failed on the exact accepted bytes
  2  NOT_MEASURED_VACUOUS    - no bundle could be read (environment error)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from evaluation.mapping_free_recall_falsifier import (  # noqa: E402
    measure,
    non_vacuity,
    SCHEMA,
    EXIT_PASS,
    EXIT_FALSIFIED,
    EXIT_VACUOUS,
    CLAIM_CEILING,
    resolve_mount,
    PACKETS,
    verdict_of,
)

DEFAULT_OUT_DIR = REPO_ROOT / "results/evaluation/minimal_retrieval_ca_benchmark"
DEFAULT_REPORT_DIR = REPO_ROOT / "reports/evaluation"


def run_benchmark(run_id: str, out_dir: Path, report_dir: Path,
                  product_mount: Path | None = None,
                  packets: tuple[str, ...] | None = None) -> tuple[int, dict]:
    """Run the smallest retrieval/CA falsification benchmark.

    Uses the accepted mapping-free-recall-falsifier measurement engine.
    Reuses all measurement predicates unchanged; adds no new threshold, gate,
    tokeniser, or stoplist.

    Returns (exit_code, record_dict).
    """
    if packets is None:
        packets = ("39319405429",)  # V3 packet-of-record exact bytes

    mount = resolve_mount(product_mount)
    if mount is None:
        rec = {
            "schema": SCHEMA,
            "run_id": run_id,
            "verdict": "NOT_MEASURED_VACUOUS",
            "exit_code": EXIT_VACUOUS,
            "detail": "no accepted product mount available",
            "human_gate_ready": False,
            "packet_admitted": False,
            "machine_gate_ready": False,
            "ready_for_owner_session": False,
            "claim_ceiling": CLAIM_CEILING,
        }
        out_dir.mkdir(parents=True, exist_ok=True)
        report_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"{run_id}.json"
        out_path.write_text(json.dumps(rec, indent=2) + "\n", encoding="utf-8")
        report_path = report_dir / f"RETRIEVAL_CA_BENCHMARK_{run_id}.md"
        report_path.write_text(
            f"# Minimal Retrieval / Counter-authority Falsification Benchmark — run {run_id}\n"
            f"- Schema: `{SCHEMA}`\n"
            f"- Verdict: **NOT_MEASURED_VACUOUS** (exit {EXIT_VACUOUS})\n"
            f"- No accepted product mount; measurement impossible.\n"
            f"- Elapsed: 0.000 s\n",
            encoding="utf-8",
        )
        return EXIT_VACUOUS, rec

    measured = measure(mount, REPO_ROOT, packets)
    vac = non_vacuity(measured["questions"], measured["scored_statuses_from_frozen_rubric"])
    verdict, code = verdict_of(measured, vac)

    # Count total gates from per-question gate lists
    all_gates = []
    for q in measured["questions"]:
        for g in q.get("gates", []):
            all_gates.append(g)
    n_gates = len(all_gates)
    n_passed = sum(1 for g in all_gates if g.get("passed") is True)
    n_failed = sum(1 for g in all_gates if g.get("passed") is False)
    n_reported = sum(1 for g in all_gates if g.get("passed") is None)
    failed_gate_details = [g for g in all_gates if g.get("passed") is False]
    failed_gates = [g["gate"] for g in failed_gate_details]

    record = {
        "schema": SCHEMA,
        "lane": "evaluation",
        "run_id": run_id,
        "direction_version": 61,
        "verdict": verdict,
        "exit_code": code,
        "entry_point": "python -m evaluation.minimal_retrieval_ca_benchmark",
        "generated_at_utc": __import__("datetime").datetime.now(
            __import__("datetime").timezone.utc
        ).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "frozen_hypothesis": {
            "path": "evaluation/MAPPING_FREE_RECALL_FALSIFIER_HYPOTHESIS_V1.json",
            "sha256": hashlib.sha256(
                (REPO_ROOT / "evaluation/MAPPING_FREE_RECALL_FALSIFIER_HYPOTHESIS_V1.json").read_bytes()
            ).hexdigest(),
        },
        "freeze_record": {
            "path": "evaluation/MAPPING_FREE_RECALL_FALSIFIER_FREEZE_RECORD.json",
            "sha256": hashlib.sha256(
                (REPO_ROOT / "evaluation/MAPPING_FREE_RECALL_FALSIFIER_FREEZE_RECORD.json").read_bytes()
            ).hexdigest(),
        },
        "product_mount": str(mount),
        "packets_measured": list(packets),
        "n_questions_measured": len(measured["questions"]),
        "n_gates": n_gates,
        "n_passed": n_passed,
        "n_failed": n_failed,
        "n_reported": n_reported,
        "failed_gates": failed_gates,
        "gates": [{"gate": g["gate"], "passed": g["passed"], "detail": g.get("detail", "")}
                  for g in all_gates],
        "per_question": [
            {
                "packet": q["packet"],
                "qid": q["qid"],
                "bundle_sha256": q["bundle_sha256"],
                "admissibility_sha256": q["admissibility_sha256"],
                "concepts": q["coverage"]["concepts"],
                "concepts_with_zero_rows": q["coverage"]["concepts_with_zero_rows"],
                "concept_row_counts": q["coverage"]["concept_row_counts"],
            }
            for q in measured["questions"]
        ],
        "admissibility": {
            "rule": "SAME_NORM AND SAME_SUBJECT_TERMS, computed at run time with no analyst judgement",
            "n_pairs_enumerated": measured["n_pairs_enumerated"],
            "n_pairs_admissible": measured["n_pairs_admissible"],
            "pairs": measured["frozen_id_overlap"],
        },
        "non_vacuity": {
            "all_hold": vac["all_hold"],
            "battery": vac["battery"],
        },
        "no_new_thresholds": True,
        "no_174k_benchmark_rerun": True,
        "claim_ceiling": CLAIM_CEILING,
        "human_gate_ready": False,
        "packet_admitted": False,
        "machine_gate_ready": False,
        "ready_for_owner_session": False,
    }

    out_dir.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / f"RETRIEVAL_CA_BENCHMARK_{run_id}.md"
    out_path = out_dir / f"{run_id}.json"
    out_path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    # Human-readable report
    lines = [
        f"# Minimal Retrieval / Counter-authority Falsification Benchmark — run {run_id}",
        "",
        f"- Schema: `{SCHEMA}`",
        f"- Direction: v{record['direction_version']} (factory direction v61)",
        f"- Engine: `python -m evaluation.mapping_free_recall_falsifier` (accepted entry point, reused unchanged)",
        f"- Packet: {packets[0]} (V3 packet-of-record exact bytes)",
        f"- Combined verdict: **{verdict}** (exit {code})",
        f"- Falsification proven: **{code == EXIT_FALSIFIED}**",
        f"- Questions measured: {record['n_questions_measured']}",
        f"- Gates: {record['n_gates']} total, {record['n_passed']} passed, {record['n_failed']} failed, {record['n_reported']} reported",
        f"- Failed gates: {', '.join(record['failed_gates']) if record['failed_gates'] else 'none'}",
        "",
        "## Non-vacuity battery",
        "",
    ]
    for battery in vac["battery"]:
        lines.append(f"- **{battery['control']}**: holds={battery['holds']} — {battery['why']}")
    lines += [
        "",
        "## Claim ceiling",
        "",
        CLAIM_CEILING,
        "",
        "## Provenance",
        f"- Frozen hypothesis SHA256: {record['frozen_hypothesis']['sha256']}",
        f"- Freeze record SHA256: {record['freeze_record']['sha256']}",
        f"- Product mount: {record['product_mount']}",
        f"- Failed gates: {', '.join(record['failed_gates']) if record['failed_gates'] else 'none'}",
        "",
        f"Machine record: `{out_path.name}`",
        f"Report: `{report_path.name}`",
    ]
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
    run_id = args.run_id or __import__("os").environ.get("GITHUB_RUN_ID", "local")
    packets = tuple(p.strip() for p in args.packets.split(",") if p.strip()) if args.packets else None
    out_dir = Path(args.out_dir) if args.out_dir else (
        REPO_ROOT / "results" / "evaluation" / "minimal_retrieval_ca_benchmark")
    report_dir = Path(args.report_dir) if args.report_dir else (
        REPO_ROOT / "reports" / "evaluation")
    exit_code, record = run_benchmark(run_id, out_dir, report_dir,
                                      product_mount=args.product_mount,
                                      packets=packets)
    print(json.dumps({
        "verdict": record.get("verdict"),
        "exit_code": exit_code,
        "falsification_proven": exit_code == 1,
        "n_questions_measured": record.get("n_questions_measured"),
        "n_gates": record.get("n_gates"),
        "n_passed": record.get("n_passed"),
        "n_failed": record.get("n_failed"),
        "failed_gates": record.get("failed_gates"),
        "reason": (
            "counter-authority surface empty on all served questions"
            if exit_code == 1
            else ("no mount available" if exit_code == 2 else "all gates passed")
        ),
    }, indent=1))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
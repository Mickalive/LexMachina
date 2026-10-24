#!/usr/bin/env python3
"""Smallest executable retrieval/counter-authority benchmark on the V3
packet-of-record (39319405429) exact bytes.

FAST MVP: runs the accepted mapping-free measurement functions unchanged on
the packet-of-record to determine whether retrieval and counter-authority
discovery are good enough to justify the visual UX test.

REUSE-FIRST: every measurement function is imported from
``evaluation.mapping_free_recall_falsifier`` unchanged. No frozen rules,
thresholds, incumbents, predicates or verdict contract is re-derived or
re-tuned here.

EXIT CODES (aligned with verdict_of contract):
  0  PASS_NO_FALSIFICATION   - every mapping-free gate passed and every
                              non-vacuity control held on V3's exact bytes.
  1  PRODUCT_FALSIFIED        - at least one mapping-free gate failed on V3's
                              exact bytes, naming packet / question / gate /
                              measured values.  This falsifies the product's
                              retrieval/counter-authority discovery.
  2  NOT_MEASURED_VACUOUS     - no bundle could be read, or a non-vacuity
                              control did not hold.  Never a pass, never a
                              bar-met.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from evaluation import mapping_free_recall_falsifier as M  # noqa: E402
from evaluation.minimal_ca_benchmark import V3_PACKET_DIR  # noqa: E402

def _sha256_file(path: Path) -> str:
    return M.sha256_file(path)


def _rel_or_abs(path: Path) -> str:
    """Repo-relative when the file landed inside the repo, absolute otherwise."""
    try:
        return str(path.resolve().relative_to(_REPO_ROOT.resolve()))
    except ValueError:
        return str(path)

SCHEMA = "lex-evaluation-minimal-rc-benchmark/1"
DEFAULT_OUT_DIR = _REPO_ROOT / "results" / "evaluation" / "minimal_rc_benchmark"
DEFAULT_REPORT_DIR = _REPO_ROOT / "reports" / "evaluation"
PACKETS = ("39319405429",)  # packet-of-record V3

EXIT_PASS = M.EXIT_PASS
EXIT_FALSIFIED = M.EXIT_FALSIFIED
EXIT_VACUOUS = M.EXIT_VACUOUS

CLAIM_CEILING = (
    "This benchmark establishes exactly one thing: on the packet-of-record V3's "
    "(39319405429) exact bytes, whether the served bundles satisfy the frozen "
    "mapping-free gates. It does NOT meet, move or re-derive the frozen absolute "
    "LABEL_SOUND or GEOMETRY_SOUND bars, which stay REPORTED-ONLY. It does NOT "
    "lift the accepted DO-NOT-SERVE order on any packet. It does NOT certify "
    "admission of any packet; admission stays fail-closed. It does NOT claim the "
    "map helps a jurist; that remains the human product gate's question. It does "
    "NOT build, tune, score or re-score any candidate for any Frontier team. "
    "It runs no obsolete universal-174k geometry benchmark. human_gate_ready stays "
    "false."
)


def _sha256_file(path: Path) -> str:
    return M.sha256_file(path)


def _current_direction_version() -> int:
    state_path = _REPO_ROOT / "state" / "evaluation.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    return int(state["direction_version"])


def resolve_mount() -> Path | None:
    """Resolve the accepted product mount using the same logic as the falsifier."""
    from evaluation.mapping_free_recall_falsifier import resolve_mount as _resolve_mount

    cands: list[Path] = []

    # Explicit environment override
    if os.environ.get("LEX_ACCEPTED_PRODUCT_MOUNT"):
        cands.append(Path(os.environ["LEX_ACCEPTED_PRODUCT_MOUNT"]))
    if os.environ.get("LEX_PRODUCT_MOUNT"):
        cands.append(Path(os.environ["LEX_PRODUCT_MOUNT"]))

    # Dynamic Frontier mounts
    for var in ("LEX_ACCEPTED_PRODUCT_MOUNT", "LEX_PRODUCT_MOUNT"):
        if os.environ.get(var):
            cands.append(Path(os.environ[var]))

    # Default accepted mounts
    for p in ("/tmp/lex_accepted/product",):
        cands.append(Path(p))

    for c in cands:
        if c.is_dir():
            return c
    return None


def run(run_id: str, out: Path | None, mount_arg: str | None,
        repo: Path, packets: tuple[str, ...]) -> tuple[int, dict]:
    mount = resolve_mount(mount_arg) if mount_arg else resolve_mount()

    if mount is None:
        rec = {
            "schema": SCHEMA,
            "lane": "evaluation",
            "run_id": run_id,
            "direction_version": _current_direction_version(),
            "verdict": "NOT_MEASURED_VACUOUS",
            "exit_code": EXIT_VACUOUS,
            "frozen_hypothesis": {
                "path": "evaluation/MAPPING_FREE_RECALL_FALSIFIER_HYPOTHESIS_V1.json",
                "sha256": _sha256_file(repo / "evaluation/MAPPING_FREE_RECALL_FALSIFIER_HYPOTHESIS_V1.json"),
            },
            "freeze_record": {
                "path": "evaluation/MAPPING_FREE_RECALL_FALSIFIER_FREEZE_RECORD.json",
                "sha256": _sha256_file(repo / "evaluation/MAPPING_FREE_RECALL_FALSIFIER_FREEZE_RECORD.json"),
            },
            "entry_point": "python -m evaluation.minimal_rc_benchmark",
            "detail": "no accepted product mount available; admission of a packet is never "
                      "certified from an absent input, and this exit is NOT a pass",
            "not_a_pass": True,
            "human_gate_ready": False,
            "packet_admitted": False,
            "machine_gate_ready": False,
            "ready_for_owner_session": False,
            "claim_ceiling": CLAIM_CEILING,
        }
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(rec, indent=1, ensure_ascii=False, sort_keys=True) + "\n",
                       encoding="utf-8")
        return EXIT_VACUOUS, rec

    # Run the accepted mapping-free measurement on the V3 packet-of-record
    measured = M.measure(mount, repo, packets)

    # Check non-vacuity controls
    vac = M.non_vacuity(measured["questions"], measured["scored_statuses_from_frozen_rubric"])

    # Produce verdict using the accepted verdict_of function
    verdict, code = M.verdict_of(measured, vac)

    # Build record
    gates = [g for q in measured["questions"] for g in q["gates"]]
    failed = [g for g in gates if g["passed"] is False]

    packet_digests: dict[str, str] = {}
    for packet in packets:
        p = mount / "results" / "product" / "gate_packet" / packet / "packet.json"
        if p.is_file():
            packet_digests[packet] = _sha256_file(p)

    record = {
        "schema": SCHEMA,
        "lane": "evaluation",
        "run_id": run_id,
        "direction_version": _current_direction_version(),
        "verdict": verdict,
        "exit_code": code,
        "entry_point": "python -m evaluation.minimal_rc_benchmark",
        "generated_at_utc": __import__("datetime").datetime.now(
            __import__("datetime").timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "frozen_hypothesis": {
            "path": "evaluation/MAPPING_FREE_RECALL_FALSIFIER_HYPOTHESIS_V1.json",
            "sha256": _sha256_file(repo / "evaluation/MAPPING_FREE_RECALL_FALSIFIER_HYPOTHESIS_V1.json"),
        },
        "freeze_record": {
            "path": "evaluation/MAPPING_FREE_RECALL_FALSIFIER_FREEZE_RECORD.json",
            "sha256": _sha256_file(repo / "evaluation/MAPPING_FREE_RECALL_FALSIFIER_FREEZE_RECORD.json"),
        },
        "instrument": {
            "path": "evaluation/minimal_rc_benchmark.py",
            "sha256": _sha256_file(Path(__file__)),
        },
        "reused_measurement_module": {
            "path": "evaluation/mapping_free_recall_falsifier.py",
            "sha256": _sha256_file(repo / "evaluation/mapping_free_recall_falsifier.py"),
            "functions_reused": ["measure", "non_vacuity", "verdict_of",
                                 "counter_authority_surface", "admissibility"],
        },
        "product_mount": str(mount),
        "product_mount_head": M.mount_head(mount),
        "packets_measured": list(packets),
        "packet_json_sha256": packet_digests,
        "numeric_environment": M.numeric_environment(),
        "frozen_spec": {"path": M.FROZEN_SPEC_RELPATH, "sha256": measured["spec_sha256"]},
        "frozen_label_rubric": {
            "path": M.RULES_LABEL_RELPATH,
            "sha256": measured["rules_label_sha256"],
            "scored_statuses": measured["scored_statuses_from_frozen_rubric"]},
        "n_questions_measured": len(measured["questions"]),
        "n_gates": len(gates),
        "n_passed": sum(1 for g in gates if g["passed"] is True),
        "n_failed": len(failed),
        "n_reported": sum(1 for g in gates if g["passed"] is None),
        "failed_gates": [{"gate": g["gate"], "detail": g["detail"], "measured": g["measured"]}
                         for g in failed],
        "gates": gates,
        "per_question": [_reduce_question(q) for q in measured["questions"]],
        "admissibility": {
            "rule": "SAME_NORM AND SAME_SUBJECT_TERMS, computed at run time with no analyst judgement",
            "n_pairs_enumerated": measured["n_pairs_enumerated"],
            "n_pairs_admissible": measured["n_pairs_admissible"],
            "pairs": measured["frozen_id_overlap"],
        },
        "non_vacuity": vac,
        "no_new_thresholds": True,
        "no_174k_benchmark_rerun": True,
        "claim_ceiling": CLAIM_CEILING,
        "falsification_proven": verdict == "PRODUCT_FALSIFIED",
        "human_gate_ready": False,
        "packet_admitted": False,
        "machine_gate_ready": False,
        "ready_for_owner_session": False,
        "owner_decision_required": False,
}
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(record, indent=1, ensure_ascii=False, sort_keys=True) + "\n",
                   encoding="utf-8")
    
    # Write human-readable report
    report_path = Path(str(out).replace(".json", ".md"))
    report_lines = [
        f"# Retrieval / counter-authority falsification benchmark — run {run_id}",
        "",
        f"- Schema: `{SCHEMA}`",
        f"- Direction: v{_current_direction_version()} (derived from "
        "state/evaluation.json at run time; operational resume lineage)",
        f"- Engine: `python -m evaluation.minimal_rc_benchmark` (accepted measurement "
        "functions reused unchanged)",
        f"- Combined verdict: **{record.get('verdict', '?')}** (exit {record.get('exit_code', '?')})",
        f"- Falsification proven: **{record.get('falsification_proven', None)}**",
        "",
        "## Failed Gates",
        "",
    ]
    for g in record.get("failed_gates", []):
        report_lines.append(f"- `{g['gate']}`: {g['detail']}")
    report_lines += [
        "",
        "## Passed Gates",
        "",
    ]
    for g in record.get("gates", []):
        if g.get("passed") is True:
            report_lines.append(f"- `{g['gate']}`: passed")
    report_lines += [
        "",
        "## Claim ceiling",
        "",
        CLAIM_CEILING,
        "",
        f"Machine record: `{_rel_or_abs(out)}`",
    ]
    report_path.write_text("\n".join(report_lines) + "\n", encoding="utf-8")
    
    return code, record


def _reduce_question(q: dict) -> dict:
    """Project a measured question down to the fields the claim needs."""
    return {
        "packet": q["packet"],
        "qid": q["qid"],
        "bundle_sha256": q["bundle_sha256"],
        "admissibility_sha256": q["admissibility_sha256"],
        "concepts": q["coverage"]["concepts"],
        "concepts_with_zero_rows": q["coverage"]["concepts_with_zero_rows"],
        "concept_row_counts": q["coverage"]["concept_row_counts"],
    }


def main(argv: list[str] | None = None) -> int:
    ap = __import__("argparse").ArgumentParser(description=__doc__.split("\n", 1)[0])
    ap.add_argument("--run-id", default=os.environ.get("GITHUB_RUN_ID", "local"))
    ap.add_argument("--out", default=None,
                    help="machine record path (default: the committed results/ tree). "
                         "A scratch/ad-hoc invocation MUST override this so it cannot "
                         "rewrite a committed claim-bearing record.")
    ap.add_argument("--out-dir", default=None,
                    help="directory for machine record (default: --out or committed tree)")
    ap.add_argument("--report-dir", default=None,
                    help="directory for human-readable report (default: --out-dir or evaluation/reports)")
    ap.add_argument("--product-mount", default=None)
    ap.add_argument("--packets", default=",".join(PACKETS))
    args = ap.parse_args(argv)
    packets = tuple(p.strip() for p in args.packets.split(",") if p.strip())
    out_dir = Path(args.out_dir) if args.out_dir else Path(args.out) if args.out else DEFAULT_OUT_DIR
    report_dir = Path(args.report_dir) if args.report_dir else (Path(args.out_dir) if args.out_dir else DEFAULT_REPORT_DIR)
    out = out_dir / f"{args.run_id}.json"
    code, rec = run(args.run_id, out, args.product_mount, _REPO_ROOT, packets)
    summary = {
        "verdict": rec.get("verdict"),
        "exit_code": code,
        "direction_version": rec.get("direction_version"),
        "n_questions_measured": rec.get("n_questions_measured"),
        "n_gates": rec.get("n_gates"),
        "n_passed": rec.get("n_passed"),
        "n_failed": rec.get("n_failed"),
        "n_reported": rec.get("n_reported"),
        "input_drift": rec.get("input_drift"),
        "non_vacuity_all_hold": ((rec.get("non_vacuity") or {}).get("all_hold")),
        "n_pairs_admissible": ((rec.get("admissibility") or {}).get("n_pairs_admissible")),
        "failed_gates": [g["gate"] for g in rec.get("failed_gates") or []],
        "record": str(out),
        "falsification_proven": rec.get("falsification_proven"),
    }
    print(json.dumps(summary, indent=1))
    return code


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
"""CLI: python -m frontier_rebuilt_packet_serve_audit.cli --packet <dir> --frozen-rules

Consumes the rebuilt packet and emits, per anchor bundle:
  * label support among ISSUED, abstention count, yield over population,
    the frozen scorer's absolute/regression status AS WRITTEN,
  * the accepted population-free label_lineage_gate verdict beside it,
    each with an explicit NOT_APPLICABLE-is-not-a-pass guard,
  * geometry per-criterion counts vs the 11 criteria and vs the incumbent
    de 6 / fr 5 / it 5,
  * whether the size-based mega-cluster disclosure fires,
  * the marginal-discovery measurement (frozen K),
  * the cross-check table (Evaluation re-score or ABSENT),
  * ONE machine-checked serve recommendation.

Exit codes: 0 = audit completed and record written; 2 = environment error
(freeze mismatch, missing inputs) — never a product verdict.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import report
from .paths import TEAM_ROOT


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="frontier_rebuilt_packet_serve_audit.cli")
    ap.add_argument("--packet", default=None, help="rebuilt packet dir containing packet.json")
    ap.add_argument("--old-packet", default=None, help="old packet dir (before/after)")
    ap.add_argument("--frozen-rules", action="store_true",
                    help="require and verify the frozen RULES.json (default: on)")
    ap.add_argument("--k", type=int, default=20, help="marginal-discovery K (frozen default 20)")
    ap.add_argument("--out", default=None, help="write the JSON record to this path")
    ap.add_argument("--evaluation-rescore", action="append", default=None,
                    help="path to a Core Evaluation re-score of THIS packet; repeatable. "
                         "When omitted, the mounted Evaluation lanes are searched and absence "
                         "is recorded with its search basis (never invented).")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args(argv)

    # --frozen-rules is mandatory in spirit: the freeze is always loaded and
    # verified. The flag exists so the charter's documented invocation works.
    _ = args.frozen_rules

    try:
        record = report.run_audit(
            Path(args.packet) if args.packet else None,
            Path(args.old_packet) if args.old_packet else None,
            k=args.k,
            evaluation_rescore_paths=args.evaluation_rescore,
        )
    except Exception as exc:  # freeze / environment errors only
        print(f"ENVIRONMENT_ERROR: {exc}", file=sys.stderr)
        return 2

    payload = json.dumps(record, indent=1, sort_keys=True, ensure_ascii=False)
    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(payload + "\n", encoding="utf-8")
    if not args.quiet:
        v = record["verdict"]
        print(v["one_sentence"])
        for cause in v["bounded_causes"]:
            print(f"  bounded_cause: {cause}")
        a = record["half_a_label"]
        b = record["half_b_geometry"]
        c = record["half_c_marginal_discovery"]
        print(
            f"  label: issued={a['pooled']['n_issued']} supported={a['pooled']['n_supported']} "
            f"rate={a['pooled']['support_rate_among_issued']} abstained={a['pooled']['n_abstained']} "
            f"absolute={a['accepted_label_gate_as_written']['absolute_status']} "
            f"label_gate_reg={a['accepted_label_gate_as_written']['regression_verdict']} "
            f"lineage_reg={a['accepted_label_lineage_gate_as_written']['regression_verdict']}"
        )
        print(f"  geometry: {b['criterion_counts']} absolute={b['absolute_status']} "
              f"mega_fires={b['mega_cluster_fires_on_any_rebuilt_bundle']}")
        print(f"  marginal_discovery: {c['pooled']}")
        print(f"  cross_check: {record['cross_check']['status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""CLI for the frozen counter-label support harness.

    # score one bundle (charter-required invocation form)
    python3 -m frontier_counter_label_integrity.cli \\
        --frozen-rules results/frontier/frontier-counter-label-integrity/RULES.json \\
        --bundle /tmp/lex_accepted/core/product/results/product/gate_packet/38799024807/questions/fr-bail-entretien.bundle.json \\
        --out results/frontier/frontier-counter-label-integrity/single

    # score every frozen input (primary + secondary replication)
    python3 -m frontier_counter_label_integrity.cli \\
        --frozen-rules results/frontier/frontier-counter-label-integrity/RULES.json --all \\
        --out results/frontier/frontier-counter-label-integrity

    # scope self-check (offline write-scope runbook; --out is required by the
    # parser but never read or written in this mode)
    python3 -m frontier_counter_label_integrity.cli --scope-check --out /tmp/lex_scope_check

    # audit-tree provenance ledger (in scope; the audit tree is read-only)
    python3 -m frontier_counter_label_integrity.cli --disposition --out <dir>

Offline, deterministic, no network, no provider, no clock.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any

from . import disposition, scope_guard
from .injection import run_non_vacuity
from .report import build_report, score_bundle
from .rules import load_rules, rules_digest

DEFAULT_RULES = "results/frontier/frontier-counter-label-integrity/RULES.json"
REPORT_NAME = "REPORT.json"
SINGLE_NAME = "SCORES.json"
NONVAC_NAME = "NON_VACUITY.json"


def _write_json(path: str, payload: Any) -> str:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    text = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)
    return rules_digest(payload)


def _resolve_frozen_inputs(rules, only: str | None) -> list[str]:
    sel = [
        e for e in rules.data["inputs"]
        if only is None or e["population"] == only
    ]
    return [e["product_mount_path"] for e in sorted(sel, key=lambda x: x["relpath_under_results_product"])]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="frontier-counter-label-integrity")
    ap.add_argument("--frozen-rules", default=DEFAULT_RULES, help="frozen RULES.json (required)")
    ap.add_argument("--bundle", action="append", default=[], help="score this bundle path (repeatable)")
    ap.add_argument("--all", action="store_true", help="score every input declared in RULES.json")
    ap.add_argument("--population", choices=["primary", "secondary"], help="restrict --all to one population")
    ap.add_argument("--out", required=True, help="output directory")
    ap.add_argument("--non-vacuity-only", action="store_true", help="run only the injection test")
    ap.add_argument("--scope-check", action="store_true",
                    help="check the working tree against the workflow's producer write scope "
                         "and exit (0 clean, 1 out of scope, 2 git error); --out untouched")
    ap.add_argument("--disposition", action="store_true",
                    help="emit the in-scope audit-tree provenance ledger and exit; "
                         "reads the audit tree read-only, writes only under --out")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args(argv)

    if args.scope_check:
        scope_argv = ["--repo-root", "."]
        if args.quiet:
            scope_argv.append("--quiet")
        return scope_guard.main(scope_argv)

    if args.disposition:
        disp_argv = ["--repo-root", "."]
        if args.quiet:
            disp_argv.append("--quiet")
        return disposition.main([*disp_argv, "--out", args.out])

    if not os.path.exists(args.frozen_rules):
        print(f"frozen rules not found: {args.frozen_rules}", file=sys.stderr)
        return 2
    rules = load_rules(args.frozen_rules)

    non_vac = run_non_vacuity(rules)
    non_vac_payload = {
        "schema": "frontier-counter-label-integrity/non-vacuity/1",
        "team_id": rules.data["team_id"],
        "charter_version": rules.data["charter_version"],
        "rules_sha256": rules.sha256,
        "result": non_vac,
    }
    _write_json(os.path.join(args.out, NONVAC_NAME), non_vac_payload)

    if args.non_vacuity_only:
        if not args.quiet:
            print(f"non-vacuity passed={non_vac['passed']} "
                  f"({non_vac['n_expected_class_matched']}/{non_vac['n_injected']} classes matched, "
                  f"{non_vac['n_defect_criteria_exercised']} defect criteria exercised)")
        return 0 if non_vac["passed"] else 1

    paths = list(args.bundle)
    if args.all or not paths:
        paths = _resolve_frozen_inputs(rules, args.population)

    report = build_report(rules, paths, non_vac)
    digest = _write_json(os.path.join(args.out, REPORT_NAME), report)
    if args.bundle and not args.all and len(args.bundle) <= 3:
        _write_json(
            os.path.join(args.out, SINGLE_NAME),
            [score_bundle(rules, p)["rows"] for p in sorted(paths)],
        )

    v = report["verdict"]
    if not args.quiet:
        print(f"rules_sha256 {report['rules_sha256']}")
        print(f"report_sha256 {digest}")
        print(f"bundles_scored {report['coverage']['n_bundles_scored']} "
              f"(primary {report['coverage']['n_primary_bundles']})")
        print(f"primary  n={v['n_scored_primary']} rate={v['support_rate_primary']}")
        print(f"secondary n={report['populations']['secondary']['n_scored']} "
              f"rate={v['support_rate_secondary']} verdict={v['secondary_verdict_replication']}")
        print(f"non_vacuity passed={report['non_vacuity']['passed']}")
        print(f"VERDICT {v['verdict']}")
        for gap in v["gaps"]:
            print(f"  gap: {gap}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
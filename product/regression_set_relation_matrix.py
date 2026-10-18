#!/usr/bin/env python3
"""Classify EVERY committed regression artifact with the gate's own predicate.

Why this exists (cycle 39123358661, audit CYCLE_39119287975 DEFECT B)
---------------------------------------------------------------------
``product/cycle_verify.py::check_regression_set_relation`` only ever reads the
NEWEST ``CYCLE_*_regression_scope.json``.  Asking "which artifacts would produce
PASS/PASS" therefore had no tool: the answer was written by hand into the
snapshot diagnosis, from a copy of the three expressions.  The copy drifted and
the diagnosis published ``CYCLE_39116225867_regression_scope.json`` as
PASS/PASS when the gate FAILs it (that artifact records ``n_repaired_only = 1``).

So the classification is now a command, not prose::

    python3 product/regression_set_relation_matrix.py            # human table
    python3 product/regression_set_relation_matrix.py --json     # machine form
    python3 product/regression_set_relation_matrix.py --artifacts PASS FAIL

There is exactly one definition of a verdict - ``cycle_verify``'s - imported, not
copied, so this file cannot disagree with the gate it is auditing.

Claim ceiling: this reclassifies ALREADY-COMMITTED regression artifacts against
an existing gate predicate. It measures nothing new, changes no artifact, scores
no frozen bar and is not an audit verdict.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from product.cycle_verify import (  # noqa: E402
    REGRESSION_DIR,
    _repo_relative,
    classify_regression_artifact,
)

SCHEMA = "product-regression-set-relation-matrix/1"


def classify_all(directory: Path | None = None) -> dict:
    """Classify every ``CYCLE_*_regression_scope.json`` in ``directory``.

    Returns a dict with ``rows`` (one per artifact, in committed-name order),
    ``pass_pass``, ``any_fail`` and ``newest`` - the last being the artifact the
    live gate actually reads.
    """
    root = Path(directory) if directory is not None else REGRESSION_DIR
    rows = [classify_regression_artifact(p)
            for p in sorted(root.glob("CYCLE_*_regression_scope.json"))]
    return {
        "schema": SCHEMA,
        "directory": _repo_relative(root),
        "predicate": "product/cycle_verify.py::regression_set_relation_rows",
        "n_artifacts": len(rows),
        "rows": rows,
        "pass_pass": sorted(r["name"] for r in rows if r["all_pass"]),
        "any_fail": sorted(r["name"] for r in rows if not r["all_pass"]),
        "newest": rows[-1] if rows else None,
    }


def render(matrix: dict, wanted: list[str] | None) -> str:
    lines = [
        f"{matrix['n_artifacts']} committed regression artifact(s) in "
        f"{matrix['directory']}",
        f"predicate: {matrix['predicate']}",
        "",
        f"{'artifact':<46} {'claim1':<7} {'claim2':<7} {'claim3':<7} all",
    ]
    for row in matrix["rows"]:
        verdicts = (row["verdicts"] + ["-"] * 3)[:3]
        if wanted and row["name"] not in wanted:
            continue
        lines.append(f"{row['name']:<46} " + " ".join(f"{v:<7}" for v in verdicts)
                     + ("  PASS" if row["all_pass"] else "  FAIL"))
    def joined(names: list[str]) -> str:
        return "  " + (", ".join(names) if names else "(none)")

    lines += ["", "produce PASS/PASS:", joined(matrix["pass_pass"])]
    lines += ["produce at least one FAIL:", joined(matrix["any_fail"])]
    newest = matrix["newest"]
    lines += ["", f"newest (the one the live gate reads): "
                  f"{newest['name'] if newest else 'none'} -> "
                  f"{'PASS' if newest and newest['all_pass'] else 'FAIL'}"]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dir", default=None,
                    help="artifact directory (default: the canonical regression dir)")
    ap.add_argument("--json", action="store_true", help="machine-readable output only")
    ap.add_argument("--artifacts", nargs="*", default=None,
                    help="print only these artifact names")
    args = ap.parse_args(argv)

    matrix = classify_all(Path(args.dir) if args.dir else None)
    if args.json:
        print(json.dumps(matrix, indent=2, sort_keys=True))
    else:
        print(render(matrix, args.artifacts))
    return 0 if matrix["n_artifacts"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
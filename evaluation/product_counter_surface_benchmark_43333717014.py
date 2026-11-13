"""Head-drift runner for the accepted product counter-signal benchmark.

The accepted instrument ``evaluation/product_counter_surface_benchmark.py``
hard-codes the hypothesis and freeze-record paths it validates (control C1/C7).
This runner keeps that instrument byte-for-byte unchanged and supplies a
run-scoped hypothesis + freeze record generated before any claim-bearing
measurement.  It is a thin parameterisation, not a second implementation: the
measurement, gates, controls and verdict logic are the accepted instrument's.

Usage:
    python3 -m evaluation.product_counter_surface_benchmark_43333717014 \
        --product-root /tmp/lex_accepted/product --run-id 43333717014
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import evaluation.product_counter_surface_benchmark as bench  # noqa: E402

DEFAULT_RUN_ID = "43333717014"
DEFAULT_HYPOTHESIS = (
    REPO_ROOT
    / "evaluation/PRODUCT_COUNTER_SURFACE_BENCHMARK_43333717014_HYPOTHESIS_V1.json"
)
DEFAULT_FREEZE = (
    REPO_ROOT
    / "evaluation/PRODUCT_COUNTER_SURFACE_BENCHMARK_43333717014_FREEZE_V1.json"
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--product-root", default=str(bench.DEFAULT_PRODUCT_ROOT))
    parser.add_argument("--run-id", default=DEFAULT_RUN_ID)
    parser.add_argument("--out", default=None)
    parser.add_argument("--hypothesis", default=str(DEFAULT_HYPOTHESIS))
    parser.add_argument("--freeze", default=str(DEFAULT_FREEZE))
    args = parser.parse_args(argv)

    # Patch only the run-scoped pin paths; every other module global
    # (PRODUCT_FILES, OUT_DIR, measurement and gate logic) is untouched.
    bench.HYPOTHESIS_PATH = Path(args.hypothesis).resolve()
    bench.FREEZE_PATH = Path(args.freeze).resolve()
    out_path = Path(args.out).resolve() if args.out else None
    out = bench.run(Path(args.product_root), args.run_id, out_path)

    print(
        {
            "run_id": out["run_id"],
            "verdict": out["verdict"],
            "exit_code": out["exit_code"],
            "aggregate": out["aggregate"],
            "failed_gates": [k for k, v in out["gates"].items() if not v["passed"]],
            "failed_controls": [k for k, v in out["controls"].items() if not v["passed"]],
        }
    )
    return int(out["exit_code"])


if __name__ == "__main__":
    sys.exit(main())

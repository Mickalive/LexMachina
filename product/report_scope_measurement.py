#!/usr/bin/env python3
"""Measure and publish what the report-arithmetic guard actually covers.

Why this exists
---------------
Audit RF-2 of rejected product cycle 39144924680: the round-4 guard shipped with
a completeness claim ("the two ways the sweep could be weakened") that the auditor
measured to be false. The honest replacement is not a smaller sentence, it is a
MEASUREMENT - and a measurement has to be re-derivable, or the next cycle is
quoting a stale scope again.

So this writes the scope by importing
``product/tests/test_report_artifact_arithmetic.py`` and calling its own
functions over the committed tree. It types no count: every number below is the
return value of the guard's own sweep, and ``testcount_disclosure_artifact_is_current``
in the guard fails the build if this artifact has drifted from a fresh sweep.

Usage
-----
    python3 product/report_scope_measurement.py --run-id <id> \\
        --out results/product/regression/CYCLE_<id>_report_testcount_disclosure.json

The round-4 reading is carried forward on every run, so the difference between
what was claimed then and what is measured now is a published number rather than
a discrepancy an auditor has to rediscover.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from product.tests import test_report_artifact_arithmetic as guard  # noqa: E402

SCHEMA = "product-report-arithmetic-scope/1"

#: The round-4 claim, retained verbatim. This is the thing RF-2 rejected; keeping
#: it beside the current measurement is what makes the correction auditable.
ROUND_4_CLAIM = {
    "heading": "The defect class is now machine-enforced",
    "controls": "pin THE TWO ways the sweep could be weakened into uselessness",
    "auditor_measured_escape_paths_that_did_not_fire": [
        "inverted phrasing: 'The sourced answer cited 9 decisions from the live API.'",
        "incidental correction marker in an unrelated sentence of the same paragraph",
        "a run-log line containing the JSON key correction_marker_present",
        "test-count arithmetic is never parsed by the sweep",
    ],
}

NON_CLAIMS = [
    "A bare test-count claim (e.g. '924 collected') in a report that cites SEVERAL regression "
    "artifacts is NOT attributed to any of them. The report states numbers from its OWN artifact "
    "while citing older ones, so the attribution is ambiguous by construction; treating it as a "
    "defect would manufacture one.",
    "A single-module pytest run inside a results table ('pytest product/tests/test_x.py - 42 "
    "passed') is not a suite count and is deliberately not compared to suite artifacts.",
    "The guard cannot verify that a number is the RIGHT number when no artifact carries it. It "
    "verifies agreement with a cited artifact and the internal arithmetic of a decomposition.",
    "A wrong number hidden inside a blockquote or fenced block is not detected here. That is "
    "concealment rather than drift, and it is named instead of left implicit.",
    "Which COMMIT produced each part of a collected-test delta is measured by "
    "product/test_delta_attribution.py and pinned in product/tests/test_delta_attribution.py, "
    "not by this guard.",
]


def measure() -> dict:
    coverage = guard.citation_claim_coverage()
    candidates = guard.sweep_testcount_candidates()
    decomp = {}
    seen = 0
    for report in sorted(guard.REPORTS_DIR.glob("*.md")):
        text = report.read_text(encoding="utf-8")
        if guard._DELTA_SUBJECT.search(text):
            seen += len(guard._DECOMPOSITION.findall(text))
        hits = guard.decomposition_violations(text)
        if hits:
            decomp[report.name] = len(hits)
    return {
        "schema": SCHEMA,
        "citation_sweep": {
            **coverage,
            "directions_covered": [
                "count before the word (5 cited)",
                "count after the word (cited 9 decisions)",
                "artifact field name (n_cited=5)",
            ],
        },
        "decomposition_sweep": {
            "reports_scanned": len(list(guard.REPORTS_DIR.glob("*.md"))),
            "decomposition_claims_seen": seen,
            "violations_found": decomp,
        },
        "bare_testcount_claims": candidates,
        "round_4_claim_superseded": ROUND_4_CLAIM,
        "non_claims": NON_CLAIMS,
        "claim_ceiling": (
            "A coverage measurement of the product's own test guard over the committed tree. It is "
            "not an audit verdict, scores no frozen bar, reads no Frontier verdict, and asserts "
            "nothing about pass/fail."
        ),
        "environment": {"python": sys.version.split()[0]},
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run-id", default=None)
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)

    payload = measure()
    if args.run_id:
        payload["run_id"] = int(args.run_id)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    cite = payload["citation_sweep"]
    print(f"artifacts={len(cite['artifacts_swept'])} pairs={cite['artifact_report_pairs']} "
          f"claims={cite['citation_claims_parsed']} "
          f"quoted={cite['claims_excluded_as_quotation']}")
    print(f"decompositions seen={payload['decomposition_sweep']['decomposition_claims_seen']} "
          f"violations={payload['decomposition_sweep']['violations_found'] or 'none'}")
    print(f"reports with bare test-count claims={len(payload['bare_testcount_claims'])}")
    print(f"wrote {out} sha256 {hashlib.sha256(out.read_bytes()).hexdigest()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
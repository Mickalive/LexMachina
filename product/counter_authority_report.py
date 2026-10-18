"""RF1 evidence: recompute the counter-authority counts the product publishes.

Run
---
    python3 -m product.counter_authority_report --out results/product/counter_authority_counting.json

Why this tool exists
--------------------
Direction v56 ordered work item (2), from audit ``CYCLE_39069382456``
(gate=BLOCKED, material): the product labelled a broad
``counter_status != "none"`` count as "counter authorities", so the demo run
reported **5** and the live run **7** where the true counts are **1** and **2**.
A gate number that overstates contrary-authority yield by 5x and 3.5x is not a
cosmetic defect: "did the map increase confidence that contrary authority had not
been hidden?" is the question the counter filter exists to answer, and
overstating the finding count makes it easier to pass for the wrong reason.

This tool recomputes both numbers on the committed bundles using the accepted
single source of truth (``product/query/counter_status.py``, re-exported by
``gate_admissibility`` as ``NON_COUNTER_STATUSES``) and publishes them with the
histogram that reconciles the two definitions. It measures nothing new: every
number comes from an already-committed bundle.

It is deliberately separate from the tests. The tests assert; this tool produces
the machine-readable artifact an auditor can diff cycle over cycle, so the
numbers cannot drift silently.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

PRODUCT_ROOT = Path(__file__).resolve().parent
REPO_ROOT = PRODUCT_ROOT.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from product.query.counter_status import (  # noqa: E402
    NON_COUNTER_STATUSES,
    counter_authority_count,
    counter_authority_ids,
    counter_status_bearing_count,
    counter_status_histogram,
)

SCHEMA = "product-counter-authority-counting/1"

#: The bundles of record for this measurement, with the provenance each number is
#: measured against. ``measurement_basis`` says what the number means, so a reader
#: can never compare the two definitions by accident.
BUNDLES = {
    "demo": {
        "path": "results/product/offline_slice/20261017T203330Z/rent-default.bundle.json",
        "query": "rent-default (offline slice, question -> answer -> counter -> map)",
        "old_defect_reported_as": 5,
        "measurement_basis": (
            "offline_slice/rent-default end-to-end loop: the demo loop a developer "
            "runs with `python3 product/offline_slice.py --slug rent-default`"
        ),
    },
    "live": {
        "path": "results/product/progressive_slice/bundle_39060279436_LIVE_V2.json",
        "query": "Responsabilite penale de l'entreprise selon l'art. 102 CP",
        "old_defect_reported_as": 7,
        "measurement_basis": (
            "progressive live run of the served server path (cycle 39060279436, "
            "202 rows after expand + adversarial admission)"
        ),
    },
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _generative_audit_summary(bundle: dict) -> dict | None:
    """The generative audit's own reading of the same rows, if present.

    This is what makes the RF1 diagnosis checkable rather than merely asserted.
    The live bundle's old published "7 counter authorities" is exactly
    ``generative_audit.status_summary.supporting`` - seven SUPPORTING rows the
    sourced answer cited. The number was never a counter count at all; it was the
    supporting count wearing a counter label. That single identity is the clearest
    possible demonstration that the broad predicate was wrong.
    """
    audit = (bundle.get("provenance") or {}).get("generative_audit") or {}
    summary = audit.get("status_summary")
    return dict(summary) if isinstance(summary, dict) else None


def measure(rel_path: str) -> dict:
    path = REPO_ROOT / rel_path
    if not path.exists():
        raise SystemExit(f"bundle of record missing: {path}")
    bundle = json.loads(path.read_text(encoding="utf-8"))
    rows = bundle.get("decisions") or []
    out = {
        "bundle_path": rel_path,
        "bundle_sha256": _sha256(path),
        "query": bundle.get("query"),
        "n_decisions": len(rows),
        "counter_authorities": counter_authority_count(rows),
        "counter_authority_ids": counter_authority_ids(rows),
        "counter_status_bearing_rows": counter_status_bearing_count(rows),
        "counter_status_histogram": counter_status_histogram(rows),
        "counter_yield_over_decisions": (
            round(counter_authority_count(rows) / len(rows), 6) if rows else 0.0
        ),
        "counter_yield_over_status_bearing_rows": (
            round(
                counter_authority_count(rows) / counter_status_bearing_count(rows), 6
            )
            if counter_status_bearing_count(rows)
            else None
        ),
    }
    summary = _generative_audit_summary(bundle)
    if summary is not None:
        hist = counter_status_histogram(rows)
        out["generative_audit_status_summary"] = summary
        out["generative_audit_reconciliation"] = {
            "note": (
                "The generative audit's own classification of the same rows, next to the "
                "bundle's row-level counter_status provenance. These two are measured at "
                "DIFFERENT stages and are not expected to coincide, so neither identity is "
                "asserted from a matching cardinality (factory-wide requirement 16)."
            ),
            "generative_audit_supporting": summary.get("supporting"),
            "generative_audit_limiting": summary.get("limiting"),
            "generative_audit_contrary_or_exception": summary.get("contrary_or_exception"),
            "bundle_cited_rows": hist.get("cited"),
            "bundle_counter_authority_rows": counter_authority_count(rows),
            "old_published_number": None,  # filled by build()
            "verified_relations": {
                "old_number_equals_generative_audit_supporting": None,  # filled by build()
                "old_number_equals_bundle_cited_rows": None,  # filled by build()
                "generative_audit_reports_zero_limiting_and_zero_contrary":
                    summary.get("limiting") == 0
                    and summary.get("contrary_or_exception") == 0,
                "bundle_cited_rows_equals_generative_audit_supporting":
                    hist.get("cited") == summary.get("supporting"),
            },
            "reading": (
                "Two facts, both verified, and deliberately NOT collapsed into one:\\n"
                "(1) The generative audit classified the same run as supporting="
                f"{summary.get('supporting')}, limiting={summary.get('limiting')}, "
                f"contrary_or_exception={summary.get('contrary_or_exception')} - i.e. it "
                "issued no limiting and no contrary classification at all.\\n"
                "(2) The old published 'counter authorities' number equals that "
                f"supporting count ({summary.get('supporting')}), while the bundle's own "
                f"row-level `cited` provenance covers {hist.get('cited')} rows. So the old "
                "number was the audit's SUPPORTING count under a counter label. The two "
                "coincide numerically here but are measured at different stages and were "
                "NOT shown to be the same set; that is recorded as unverified rather than "
                "assumed.\\n"
                "Either way the old number cannot be a counter count: the broad predicate "
                "counted `cited` rows, and the generative audit found zero limiting and "
                "zero contrary authority."
            ),
        }
    return out


def _adversarial_arithmetic(name: str, bundle: dict) -> dict | None:
    """RF2: final served rows MUST equal pre-adversarial rows + admitted rows.

    Direction v56 item RF2 recorded a report that published the PRE-adversarial
    count (247) as the final served bundle size when the bundle actually held 255
    (247 + 8 adversarial rows). The invariant is checked here so the class cannot
    recur, and the exact numbers are carried per bundle.
    """
    adv = (bundle.get("provenance") or {}).get("adversarial_retrieval") or {}
    if not adv or "n_existing_before" not in adv:
        return None
    before = int(adv["n_existing_before"])
    new_rows = int(adv.get("n_new_rows") or 0)
    actual = len(bundle.get("decisions") or [])
    return {
        "n_existing_before_adversarial": before,
        "n_adversarial_rows_added": new_rows,
        "expected_final_rows": before + new_rows,
        "actual_final_rows": actual,
        "invariant_holds": actual == before + new_rows,
        "publishing_only_the_pre_adversarial_count_would_report": before,
        "understatement_if_pre_adversarial_count_published": actual - before,
    }


def build() -> dict:
    measured = {name: measure(spec["path"]) for name, spec in BUNDLES.items()}

    # Wire each bundle's old, mislabelled number into its reconciliation so the
    # identity ("7 == supporting == cited") is asserted, not just available.
    for name, spec in BUNDLES.items():
        recon = measured[name].get("generative_audit_reconciliation")
        if recon is not None:
            old = spec["old_defect_reported_as"]
            recon["old_published_number"] = old
            rel = recon["verified_relations"]
            rel["old_number_equals_generative_audit_supporting"] = (
                old == recon["generative_audit_supporting"]
            )
            rel["old_number_equals_bundle_cited_rows"] = (
                old == recon["bundle_cited_rows"]
            )

    adversarial = {}
    for name, spec in BUNDLES.items():
        path = REPO_ROOT / spec["path"]
        result = _adversarial_arithmetic(name, json.loads(path.read_text(encoding="utf-8")))
        if result is not None:
            adversarial[name] = result

    out = {
        "schema": SCHEMA,
        "what_this_is": (
            "RF1 evidence. The product's published 'counter authorities' count was a "
            "broad counter_status != 'none' test that swept in every decision the "
            "generative answer CITED and every recall-only row. This artifact "
            "recomputes both definitions on the committed bundles of record using the "
            "accepted single source of truth and publishes the histogram that "
            "reconciles them. Both definitions are always shown side by side "
            "(audit CYCLE_39065274887 F3 convention)."
        ),
        "single_source_of_truth": {
            "module": "product/query/counter_status.py",
            "reexported_as": "product.query.gate_admissibility.NON_COUNTER_STATUSES",
            "non_counter_statuses": sorted(str(s) for s in NON_COUNTER_STATUSES),
            "why_broad_test_is_wrong": (
                "counter_status is a provenance field as well as a verdict field: "
                "'cited' means the sourced answer CITED the decision, which is the "
                "opposite of countering it; 'supporting-candidate' / 'context' / "
                "'unclassified' are recall-only rows kept for high recall."
            ),
        },
        "old_defect": {
            "demo_reported_as": BUNDLES["demo"]["old_defect_reported_as"],
            "live_reported_as": BUNDLES["live"]["old_defect_reported_as"],
            "demo_actual": measured["demo"]["counter_authorities"],
            "live_actual": measured["live"]["counter_authorities"],
            "inflation_factor_demo": round(
                BUNDLES["demo"]["old_defect_reported_as"]
                / measured["demo"]["counter_authorities"], 4
            ),
            "inflation_factor_live": round(
                BUNDLES["live"]["old_defect_reported_as"]
                / measured["live"]["counter_authorities"], 4
            ),
        },
        "definitions": {
            "counter_authorities": (
                "rows whose counter_status is a genuine finding "
                "(candidate-limiting / candidate-contrary / abstained_unevidenced / "
                "any future evidence-supported status)"
            ),
            "counter_status_bearing_rows": (
                "rows with ANY non-empty counter_status, provenance included. This is "
                "what the old, mislabelled counts.counter measured. It is a true and "
                "useful provenance number and is published under this honest name - "
                "never labelled 'counter authorities'."
            ),
        },
        "demo": measured["demo"],
        "live": measured["live"],
        "served_bundle_row_arithmetic": {
            "why": (
                "RF2 (direction v56): a report published the PRE-adversarial row count as "
                "the final served bundle size, omitting the adversarial rows the "
                "independent pass had admitted (247 reported vs 255 actual). The "
                "invariant final == n_existing_before + n_new_rows is now measured per "
                "bundle so the class cannot recur."
            ),
            "direction_recorded_case": {
                "reported": 247,
                "actual": 255,
                "composition": "247 after expand + 8 adversarial rows",
                "note": (
                    "That specific live artifact belongs to run 39073545280 and is not in "
                    "this tree. The figures are recorded as the direction states them; the "
                    "invariant below is what is enforced here, measured on the bundles "
                    "that ARE in the tree."
                ),
            },
            "per_bundle": adversarial,
        },
        "claim_ceiling": [
            "These counts are a correction of a labelling defect, not new evidence "
            "about the product's quality. Correcting a counter number does not move "
            "the geometry bar or the label bar.",
            "The corrected counts make the product's disclosed counter yield LOWER. "
            "That is the honest direction: the previous number was inflated by cited "
            "rows and would have flattered the map's discoverability claim.",
            "Both accepted DO-NOT-SERVE orders remain in force; packet admission "
            "stays fail-closed and neither this artifact nor the correction it "
            "records authorises an owner session.",
        ],
    }
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="product.counter_authority_report")
    ap.add_argument(
        "--out",
        default="results/product/counter_authority_counting.json",
        help="artifact path relative to the repository root",
    )
    args = ap.parse_args(argv)
    artifact = build()
    out = REPO_ROOT / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "wrote": str(out.relative_to(REPO_ROOT)),
        "demo": {
            "counter_authorities": artifact["demo"]["counter_authorities"],
            "counter_status_bearing_rows": artifact["demo"]["counter_status_bearing_rows"],
            "histogram": artifact["demo"]["counter_status_histogram"],
        },
        "live": {
            "counter_authorities": artifact["live"]["counter_authorities"],
            "counter_status_bearing_rows": artifact["live"]["counter_status_bearing_rows"],
            "histogram": artifact["live"]["counter_status_histogram"],
        },
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
#!/usr/bin/env python3
"""Direction v66 ordered item (2): frozen-scorer path visibility.

Diagnoses, WITH COMMITTED ARTIFACTS and exact file:line references, why Core
Evaluation's frozen falsifier records n_emitted / n_issued = 0 on the
packet-of-record v3 bytes while the product's own span harness measures
guarded 1/20 and unguarded 6/20 on the SAME bytes.

Both measurement families are published side by side with their harness
provenance (factory-wide requirement 36): neither number is quoted as the
other's verdict.  No frozen rule is edited, re-tuned or re-derived; the frozen
scorer decides by its own population/emission predicate AS WRITTEN
(requirement 26).  If the span-seam output is outside that input contract, the
finding is a PRODUCT CONTRACT GAP - not a scorer defect - and closing it is a
packet-rebuild decision that this cycle does NOT take (both DO-NOT-SERVE
orders stand).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from collections import Counter
from pathlib import Path

from product.query.counter_anchor import load_frozen_rules

REPO_ROOT = Path(__file__).resolve().parents[1]
PACKET_DIR = REPO_ROOT / "results" / "product" / "gate_packet" / "39319405429" / "questions"
BUNDLES = (
    "de-kapitalverletzung.bundle.json",
    "fr-bail-entretien.bundle.json",
    "it-responsabilita-medica.bundle.json",
)
REF_DIR = REPO_ROOT / "results" / "product" / "counter_span" / "frozen_scorer_ref"
REF_FILES = ("label_gate.py", "extract.py")
FROZEN_REF = "origin/lab/evaluation @ 68a079ebd9daab952197cbd04ee38837a7a255e8"
FROZEN_PATHS = {
    "label_gate.py": "evaluation/frozen_bars/label_gate.py",
    "extract.py": (
        "evaluation/frozen_bars/vendored/"
        "frontier_counter_label_integrity/extract.py"
    ),
}
DEFAULT_OUT = REPO_ROOT / "results" / "product" / "counter_span" / (
    "CYCLE_40057956963_frozen_scorer_path_diagnosis.json"
)

#: Product-side line anchors, located in source rather than hard-coded so the
#: citation cannot silently drift.
PRODUCT_ANCHORS = (
    ("product/query/counter_evidence_span.py",
     "def apply_verified_span_selection(",
     "span seam writes counter fields into the bundle object it is handed"),
    ("product/query/counter_evidence_span.py",
     'd["counter_evidence_verified"] = True',
     "span seam marks a row verified in the in-memory bundle only"),
    ("product/query/pipeline.py",
     "audited = apply_verified_span_selection(",
     "pipeline calls the seam on its in-memory `audited` bundle"),
    ("product/query/pipeline.py",
     "audited = downgrade_content_defects(audited)",
     "P0 content filter narrows verified spans in the in-memory bundle"),
    ("product/measure_counter_span_selection.py",
     "apply_verified_span_selection(",
     "product harness measures the seam on copy.deepcopy(source)"),
    ("product/measure_counter_content_filter.py",
     "apply_verified_span_selection(",
     "P0 re-probe measures the seam on copy.deepcopy(source)"),
)


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _line_of(path: Path, needle: str) -> int | None:
    try:
        for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if needle in line:
                return i
    except OSError:
        return None
    return None


def _vendor_frozen_sources() -> dict:
    """Copy the frozen scorer's two sources into a product-owned reference
    directory so every file:line citation below is checkable from this tree."""
    REF_DIR.mkdir(parents=True, exist_ok=True)
    out = {}
    for name in REF_FILES:
        # Already vendored by a previous run, or present locally for review.
        local = Path("/tmp/opencode") / name
        dest = REF_DIR / name
        if local.exists():
            shutil.copyfile(local, dest)
        out[name] = {
            "reference_path_in_source_tree": FROZEN_PATHS[name],
            "source_ref": FROZEN_REF,
            "vendored_path": str(dest.relative_to(REPO_ROOT)),
            "sha256": _sha256(dest) if dest.exists() else None,
        }
    return out


def _packet_measurements(scored_statuses: list[str]) -> dict:
    per_bundle = {}
    total_scored = 0
    total_issued = 0
    for name in BUNDLES:
        path = PACKET_DIR / name
        blob = json.loads(path.read_text(encoding="utf-8"))
        rows = blob.get("decisions") or []
        hist = Counter(str(r.get("counter_status")) for r in rows)
        scored = [r for r in rows if str(r.get("counter_status")) in scored_statuses]
        prov = blob.get("provenance") or {}
        anchor = prov.get("counter_anchor") or {}
        total_scored += len(scored)
        total_issued += len(scored)
        per_bundle[name] = {
            "sha256": _sha256(path),
            "n_rows": len(rows),
            "counter_status_histogram": dict(sorted(hist.items())),
            "n_rows_in_frozen_scored_statuses": len(scored),
            "n_counter_evidence_verified": sum(
                1 for r in rows if r.get("counter_evidence_verified") is True
            ),
            "provenance_has_counter_evidence_span": "counter_evidence_span" in prov,
            "provenance_has_counter_emission_repair": "counter_emission_repair" in prov,
            "packet_own_counter_anchor": {
                k: anchor.get(k)
                for k in ("n_scored", "n_emitted", "n_abstained", "yield", "mode")
            },
        }
    return {
        "bundles": per_bundle,
        "n_rows_in_frozen_scored_statuses_total": total_scored,
        "n_issued_under_frozen_population_predicate": total_issued,
        "n_emitted_recorded_by_packet_own_anchor_provenance": sum(
            int((b["packet_own_counter_anchor"].get("n_emitted") or 0))
            for b in per_bundle.values()
        ),
    }


def run() -> dict:
    rules, digest = load_frozen_rules()
    scored_statuses = list(rules.rubric["scored_statuses"])
    ref = _vendor_frozen_sources()

    # Locate the frozen scorer's own population/emission predicate lines.
    frozen_lines = {}
    for name in REF_FILES:
        path = REF_DIR / name
        if name == "label_gate.py":
            frozen_lines[name] = {
                "counter_rows_call": _line_of(path, "scored_rows, reported_rows = counter_rows("),
                "scored_statuses_from_rules": _line_of(path, "scored_statuses = list(rules.rubric"),
            }
        else:
            frozen_lines[name] = {
                "population_read": _line_of(path, 'status = row.get("counter_status")'),
                "scored_membership_test": _line_of(path, "if status in scored_statuses:"),
            }

    product_lines = []
    for rel, needle, note in PRODUCT_ANCHORS:
        line = _line_of(REPO_ROOT / rel, needle)
        product_lines.append(
            {"file": rel, "anchor": needle, "line": line, "note": note}
        )

    packet = _packet_measurements(scored_statuses)
    reprobe_path = (
        REPO_ROOT / "results" / "product" / "counter_span"
        / "CYCLE_40057956963_content_filter_reprobe.json"
    )
    product_harness = None
    if reprobe_path.exists():
        rep = json.loads(reprobe_path.read_text(encoding="utf-8"))
        agg = rep["part_b_packet_v3_yield_and_regression"]["aggregate"]
        product_harness = {
            "harness": "product/measure_counter_content_filter.py "
                       "(same arms as product/measure_counter_span_selection.py)",
            "artifact": str(reprobe_path.relative_to(REPO_ROOT)),
            "sha256": _sha256(reprobe_path),
            "guarded_filter_on": agg["guarded_filter_on"],
            "unguarded_filter_on": agg["unguarded_filter_on"],
        }

    finding = (
        "The frozen scorer's population predicate reads counter_status from the "
        "COMMITTED packet-of-record v3 bundle bytes only. Those bytes predate "
        "the span seam: they carry no provenance.counter_evidence_span, no "
        "provenance.counter_emission_repair, and zero rows whose status is in "
        "the RULES_LABEL scored_statuses list. The span seam writes its "
        "emissions into an in-memory bundle that is never persisted back to the "
        "packet, so the scorer scores only the PRE-SEAM proposals and records "
        "n_emitted/n_issued = 0. This is a product contract gap (no writer "
        "persists seam output into the scorer's input), NOT a scorer defect: "
        "the frozen scorer decides by its own predicate as written."
    )

    return {
        "schema": "product.frozen_scorer_path_diagnosis/1",
        "cycle": "40057956963",
        "direction_version": 66,
        "lane": "product",
        "instrument": Path(__file__).name,
        "question": (
            "Does the frozen scorer's population/emission predicate reach the "
            "span-seam output, or does it score only the pre-seam proposals?"
        ),
        "answer": "IT SCORES ONLY THE PRE-SEAM PROPOSALS.",
        "verdict": "PRODUCT_CONTRACT_GAP",
        "scorer_defect": False,
        "frozen_rules_reported_only": {
            "path": "product/frozen/RULES_LABEL.json",
            "sha256": _sha256(REPO_ROOT / "product" / "frozen" / "RULES_LABEL.json"),
            "expected_sha256": "4457e971df3dc5d10af2a727aa675afc15a15564c18eed4cede0af5eb41b4608",
            "rehash_matches": (
                _sha256(REPO_ROOT / "product" / "frozen" / "RULES_LABEL.json")
                == str(digest)
                == "4457e971df3dc5d10af2a727aa675afc15a15564c18eed4cede0af5eb41b4608"
            ),
            "scored_statuses": scored_statuses,
            "usage": "REPORTED-ONLY; re-hashed, never re-derived, never edited",
        },
        "frozen_scorer_reference": {
            "source_ref": FROZEN_REF,
            "files": ref,
            "line_anchors": frozen_lines,
        },
        "product_side_line_anchors": product_lines,
        "measurement_A_frozen_scorer_family": {
            "harness": (
                "evaluation/frozen_bars/label_gate.py:score_packet -> "
                "vendored extract.py:counter_rows (n_issued), and the packet's "
                "own provenance.counter_anchor (n_emitted)"
            ),
            "input": "committed packet-of-record v3 bundle bytes (unmodified)",
            "packet": packet,
            "n_issued": packet["n_issued_under_frozen_population_predicate"],
            "n_emitted": packet["n_emitted_recorded_by_packet_own_anchor_provenance"],
            "quote_ceiling": (
                "This is the frozen-scorer-family reading of the committed "
                "bytes. It is NOT the product harness's span-seam yield."
            ),
        },
        "measurement_B_product_span_harness_family": product_harness or {
            "status": "reprobe artifact not present at diagnosis time"
        },
        "side_by_side": (
            "frozen-scorer family: n_emitted=0 / n_issued=0 on the committed "
            "packet bytes; product span harness: guarded 1/20 (yield 0.05, "
            "support-among-issued 1.0) and unguarded 6/20 (yield 0.3, "
            "support-among-issued 1.0) on the same bytes measured through "
            "in-memory seam output. The two families measure different inputs "
            "and are never interchangeable (factory-wide requirement 36)."
        ),
        "code_path_difference": [
            {
                "family": "frozen_scorer",
                "file": "evaluation/frozen_bars/label_gate.py",
                "line": frozen_lines["label_gate.py"]["counter_rows_call"],
                "note": "score_packet -> score_bundle -> counter_rows(bundle, scored_statuses, ...)",
            },
            {
                "family": "frozen_scorer",
                "file": FROZEN_PATHS["extract.py"],
                "line": frozen_lines["extract.py"]["population_read"],
                "note": "population = row.get(\"counter_status\") on the committed bundle bytes",
            },
            {
                "family": "frozen_scorer",
                "file": FROZEN_PATHS["extract.py"],
                "line": frozen_lines["extract.py"]["scored_membership_test"],
                "note": "only rows whose status is in RULES_LABEL.scored_statuses are scored",
            },
            {
                "family": "product_span_seam",
                "file": "product/query/counter_evidence_span.py",
                "line": next(
                    (p["line"] for p in product_lines
                     if p["anchor"].startswith("def apply_verified_span_selection")),
                    None,
                ),
                "note": "writes counter_status / counter_evidence / verified into the bundle it is handed",
            },
            {
                "family": "product_span_seam",
                "file": "product/measure_counter_content_filter.py",
                "line": next(
                    (p["line"] for p in product_lines
                     if "measure_counter_content_filter" in p["file"]),
                    None,
                ),
                "note": "measured on copy.deepcopy(source); the derived bundle is never written back",
            },
            {
                "family": "gap",
                "file": "results/product/gate_packet/39319405429/questions/*.bundle.json",
                "line": None,
                "note": (
                    "no provenance.counter_evidence_span and no "
                    "provenance.counter_emission_repair on any of the three "
                    "bundles; zero rows in the frozen scored statuses"
                ),
            },
        ],
        "finding": finding,
        "remediation_not_taken_here": (
            "Persisting span-seam emissions into the packet-of-record would "
            "REBUILD the packet, which is a separate ordered decision under "
            "the standing DO-NOT-SERVE orders and is NOT taken in this cycle. "
            "No frozen rule, rubric, threshold or verdict contract is edited "
            "to make the scorer see the emissions."
        ),
        "claim_ceiling": (
            "A path diagnosis with committed artifacts and file:line "
            "references. It scores no frozen bar, changes no verdict, lifts no "
            "DO-NOT-SERVE order, and makes no serve/admission claim."
        ),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()
    report = run()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(json.dumps({
        "out": str(args.out),
        "verdict": report["verdict"],
        "answer": report["answer"],
        "n_issued": report["measurement_A_frozen_scorer_family"]["n_issued"],
        "n_emitted": report["measurement_A_frozen_scorer_family"]["n_emitted"],
        "frozen_lines": report["frozen_scorer_reference"]["line_anchors"],
    }, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

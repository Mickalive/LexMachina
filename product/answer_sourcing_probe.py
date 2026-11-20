"""Reproducible verification of the run-44694975109 snapshot's answer writers.

One command::

    python3 product/answer_sourcing_probe.py --out results/product/answer_sourcing/CYCLE_<run>_verification.json

It runs the SHIPPED offline path (``offline_slice.build_bundle``), records the
before/after answer prose and the two provenance writers, and checks the
invariants the snapshot's docstring claims.  It is REPORTED-ONLY with respect
to the frozen D2/D3/D4 content predicates: it re-hashes and calls them, never
edits or re-derives them.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for _p in (str(ROOT), str(ROOT / "product")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from product.answer_reliability import prose_citation_validity  # noqa: E402
from product.query import counter_evidence_span as ces  # noqa: E402
from product.query.bundle import validate_bundle  # noqa: E402


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def build(run_id: str, resumed_run: str, top_n: int = 100) -> dict:
    from offline_slice import build_bundle

    bundle = build_bundle("rent-default", top_n=top_n)
    prov = bundle.get("provenance") or {}
    answer = bundle.get("answer") or {}
    src = prov.get("answer_fixture_source") or {}
    note = prov.get("answer_counter_note") or {}
    prose = str(answer.get("prose") or "")
    header = str(src.get("header_preserved") or "")

    by_id = {d.get("decision_id"): d for d in bundle.get("decisions") or []}
    verified = [d for d in bundle.get("decisions") or []
                if d.get("counter_evidence_verified") is True]
    defect_scan = []
    for row in verified:
        quote = str(row.get("counter_evidence") or "")
        defect_scan.append({
            "decision_id": row.get("decision_id"),
            "counter_status": row.get("counter_status"),
            "frozen_defects": ces.frozen_content_defects(quote, row),
            "evidence_sha256": _sha(quote),
        })

    validity = prose_citation_validity(bundle)
    errors = validate_bundle(bundle)
    checks = {
        "fixture_writer_applied": src.get("applied") is True,
        "fixture_quote_count": int(src.get("n_quotes") or 0) >= 1,
        "fixture_header_preserved": bool(header) and prose.startswith(header),
        "answer_is_more_than_bare_header": len(prose) > len(header),
        "counter_note_applied": note.get("applied") is True,
        "counter_rows_reported": int(note.get("n_counter_rows") or 0) >= 1,
        "quoted_ids_exist_in_bundle": set(src.get("quoted_ids") or []) <= set(by_id),
        "all_prose_markers_resolve": validity["all_resolved"] is True,
        "bundle_validates": not errors,
        "no_frozen_defect_on_reproduced_verified_evidence":
            all(not r["frozen_defects"] for r in defect_scan),
    }
    verdict = "PASS" if all(checks.values()) else "FAIL"

    src_path = ROOT / "evaluation" / "counter_evidence_quality_benchmark.py"
    predicate_sha = (hashlib.sha256(src_path.read_bytes()).hexdigest()
                     if src_path.is_file() else None)

    return {
        "artifact": "answer_sourcing_verification",
        "run_id": run_id,
        "resumed_snapshot_run_id": resumed_run,
        "direction_version": 68,
        "lane": "product",
        "mode": "OPERATIONAL_RESUME_VERIFICATION",
        "command": "python3 product/offline_slice.py --slug rent-default --verify",
        "probe": "python3 product/answer_sourcing_probe.py",
        "verdict": verdict,
        "checks": checks,
        "bundle": {
            "slug": "rent-default",
            "top_n": top_n,
            "n_decisions": len(bundle.get("decisions") or []),
            "answer_status": answer.get("status"),
            "n_cited": len(answer.get("cited_decision_ids") or []),
            "geometry_preserved": (prov.get("offline_slice") or {}).get("geometry_preserved"),
        },
        "answer_prose": {
            "before_header_sha256": _sha(header),
            "after_sha256": _sha(prose),
            "before_header": header,
            "after": prose,
        },
        "writers": {
            "answer_fixture_source": src,
            "answer_counter_note": note,
        },
        "citation_validity": {
            "n_markers": validity["n_markers"],
            "n_resolved": validity["n_resolved"],
            "n_unresolved": validity["n_unresolved"],
            "all_resolved": validity["all_resolved"],
        },
        "frozen_content_predicates": {
            "status": "REPORTED_ONLY_NOT_EDITED_NOR_REDERIVED",
            "predicate_source_sha256": predicate_sha,
            "reported_expected_sha256": ces.FROZEN_PREDICATE_SOURCE_SHA256,
            "verified_rows_scanned": defect_scan,
        },
        "validate_bundle_errors": errors,
        "claim_ceiling": (
            "Verifies the deterministic sourced-answer and counter-note writers on "
            "the shipped offline fixture path only. No model ran, no frozen bar or "
            "threshold was scored or edited, no serve verdict is re-run, and no "
            "human_gate_ready / ready_for_owner_session claim is made."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    parser.add_argument("--run-id", default="44700830021")
    parser.add_argument("--resumed-run", default="44694975109")
    parser.add_argument("--top-n", type=int, default=100)
    args = parser.parse_args(argv)
    payload = build(args.run_id, args.resumed_run, args.top_n)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"{payload['verdict']}: wrote {out} "
          f"({len(payload['checks'])} checks, "
          f"{sum(payload['checks'].values())} passed)")
    return 0 if payload["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

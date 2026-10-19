#!/usr/bin/env python3
"""Classify every committed live-slice record by the stages it actually ran.

Why this exists
---------------
``product/live_slice.py`` could publish ``verdict: "PASS"`` with a ``claim_ceiling``
naming the canonical chain (``query -> query_result_bundle -> sourced answer ->
counter-authority pass -> clickable map``) while the same record reported a
``pending`` answer, zero citations, zero counter authorities and ``enrich_s 0.0``
- the fingerprint of a ``--no-enrich`` run.  The instrument now publishes
``stages_executed`` and a three-valued verdict (see ``live_slice.stage_disclosure``
and ``live_slice.verdict_for``).

One committed record predates that fix:

    results/product/live_slice/20261019T022100Z.json

committed by run 39187482610.  The repository's non-negotiables forbid
overwriting a claim-bearing historical result, and ``verdict: "PASS"`` is
claim-bearing, so **the file is not edited**.  Instead this module writes a
companion amendment that, for each committed record, re-derives the stage
fingerprint *from that record's own bytes* and records the effective verdict
beside the historical one.  Nothing here is copied out of a report: the numbers
are read from the artifacts.

Scope and ceiling
-----------------
This is a claim-discipline instrument. It asserts nothing about retrieval
quality, legal usefulness, any frozen bar, any Frontier verdict or any
human-gate input, and it changes no posture field. Admission stays fail-closed.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

PRODUCT_ROOT = Path(__file__).resolve().parent
REPO_ROOT = PRODUCT_ROOT.parent
sys.path.insert(0, str(PRODUCT_ROOT))
sys.path.insert(0, str(REPO_ROOT))

from product.live_slice import (  # noqa: E402
    PENDING_ANSWER_STATUS,
    stage_disclosure,
    verdict_for,
)

OUT_DIR = REPO_ROOT / "results" / "product" / "live_slice"
#: The amendment is NOT a live-slice record and does not live in the live-slice
#: directory: ``test_live_slice_and_query_env.py`` asserts that every *.json
#: there carries ``schema == "product-live-slice/1"``, which is a real invariant
#: (that directory holds records, nothing else).  The amendment gets its own.
AMENDMENT_DIR = REPO_ROOT / "results" / "product" / "live_slice_stages"
ARTIFACT = AMENDMENT_DIR / "STAGE_DISCLOSURE_AMENDMENT.json"
SCHEMA = "product-live-slice-stage-amendment/1"

#: The instrument-level claim an amendment makes about a record. ``verdict`` is
#: what the record published; ``effective_verdict`` is what its own bytes
#: support; they differ only for records written before the stage disclosure.
AMENDED = "PASS_MAP_ONLY"


def _records() -> list[Path]:
    """Committed live-slice records, selected by schema, never by filename.

    Selecting by filename is the defect this cycle repairs: ``live_slice.py``
    stamps ``--run-id`` verbatim, so a run that omits the flag is named by a UTC
    timestamp and a ``CYCLE_*.json`` glob never sees it.
    """
    out: list[Path] = []
    for path in sorted(OUT_DIR.glob("*.json")):
        if path.name.endswith("_bundle.json"):
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            continue
        if isinstance(payload, dict) and payload.get("schema") == "product-live-slice/1":
            out.append(path)
    return out


def map_only_fingerprint(payload: dict) -> bool:
    """True iff the record's own fields say the slow phase never ran.

    Derived from three independent fields of the record, not from any flag it
    asserts about itself:

    * ``answer.status`` is the ``pending`` placeholder ``run_query_initial``
      stamps (``method="pending_generative_audit"``);
    * ``counters.counter_status_bearing_rows`` is zero;
    * every row's ``counter_status`` is the literal ``"none"`` that
      ``run_query_initial`` writes.

    A *full* run that legitimately finds no counter authority would still show
    ``answer.status == "ready"`` with citations, so the conjunction does not
    misclassify it.
    """
    answer = payload.get("answer") or {}
    counters = payload.get("counters") or {}
    return (
        str(answer.get("status") or "") in ("", PENDING_ANSWER_STATUS)
        and int(counters.get("counter_status_bearing_rows") or 0) == 0
        and set(counters.get("by_status") or {"none"}) <= {"none"}
    )


def classify(payload: dict) -> dict:
    """One record -> its stage classification."""
    stages = stage_disclosure(
        n_rows=int((payload.get("map") or {}).get("n_decisions") or 0),
        enrich=bool((payload.get("timing_s") or {}).get("enrich_s")),
        enrich_error=(payload.get("answer") or {}).get("provider_error"),
        answer_status=(payload.get("answer") or {}).get("status"),
    )
    fingerprint = map_only_fingerprint(payload)
    published = payload.get("verdict")
    disclosed = payload.get("stages_executed")

    if disclosed is None:
        # Pre-fix record. Historical verdict is preserved verbatim; the effective
        # verdict is what the record's own bytes support.
        effective = AMENDED if fingerprint else published
        classification = "LEGACY_UNSTAGED_MAP_ONLY" if fingerprint else "LEGACY_UNSTAGED_CHAIN"
        agrees = published == effective
    else:
        effective = published
        classification = "STAGED"
        agrees = bool(disclosed.get("canonical_chain")) is not fingerprint

    checks = dict(payload.get("checks") or {})
    recomputed = verdict_for(
        {**checks, "canonical_chain_ran": stages["canonical_chain"]}, stages
    )
    return {
        "run_id": payload.get("run_id"),
        "produced_at": payload.get("produced_at"),
        "query": payload.get("query"),
        "verdict_published": published,
        "effective_verdict": effective,
        "classification": classification,
        "agrees_with_its_own_bytes": agrees,
        "stages_recomputed_from_record": stages,
        "map_only_fingerprint": fingerprint,
        "verdict_recomputed_from_checks": recomputed,
        "n_decisions": int((payload.get("map") or {}).get("n_decisions") or 0),
        "n_cited": int((payload.get("answer") or {}).get("n_cited") or 0),
        "counter_status_bearing_rows": int(
            (payload.get("counters") or {}).get("counter_status_bearing_rows") or 0),
    }


def build() -> dict:
    records = []
    failures: list[str] = []
    for path in _records():
        payload = json.loads(path.read_text(encoding="utf-8"))
        row = classify(payload)
        row["artifact"] = str(path.relative_to(REPO_ROOT))
        records.append(row)
        # An amended pre-fix record is EXPECTED to disagree with its own bytes:
        # that disagreement is the defect this artifact records. Only a record
        # published after the fix can regress, and that is a failure.
        if not row["agrees_with_its_own_bytes"] and row["classification"] == "STAGED":
            failures.append(
                f"{path.name}: a STAGED record publishes "
                f"verdict={row['verdict_published']} with canonical_chain="
                f"{row['stages_recomputed_from_record']['canonical_chain']}, which "
                "its own answer, counter and timing fields contradict")
    amended = [r for r in records if r["classification"] == "LEGACY_UNSTAGED_MAP_ONLY"]
    return {
        "schema": SCHEMA,
        "produced_by": "product/live_slice_stage_amendment.py",
        "records": records,
        "summary": {
            "n_records": len(records),
            "n_staged": sum(1 for r in records if r["classification"] == "STAGED"),
            "n_legacy": sum(1 for r in records if r["classification"].startswith("LEGACY")),
            "n_amended_map_only": len(amended),
            "amended_artifacts": sorted(r["artifact"] for r in amended),
        },
        "policy": (
            "A committed live-slice record is never edited. A record written "
            "before product/live_slice.py published stages_executed keeps its "
            "historical verdict verbatim and receives an effective_verdict "
            "recomputed from its own answer, counter and timing fields here. "
            "Its disagreement is the recorded defect and is NOT a failure of this "
            "artifact. A record published AFTER the fix must agree with its own "
            "bytes; a record that does not is a failure."
        ),
        "failures": failures,
        "verdict": "PASS" if not failures else "FAIL",
        "claim_ceiling": (
            "A claim-discipline classification of this lane's own live-slice "
            "records. It asserts no retrieval quality, no legal usefulness, no "
            "frozen bar, no Frontier verdict and no human-gate readiness, and it "
            "changes no posture field. Admission stays fail-closed."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    import argparse

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    result = build()
    if args.write:
        AMENDMENT_DIR.mkdir(parents=True, exist_ok=True)
        ARTIFACT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n",
                            encoding="utf-8")
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        for row in result["records"]:
            print(f"{row['classification']:26s} {row['artifact']} "
                  f"published={row['verdict_published']} "
                  f"effective={row['effective_verdict']} "
                  f"agrees={row['agrees_with_its_own_bytes']}")
        print(f"\n{result['verdict']}: {len(result['records'])} record(s), "
              f"{len(result['failures'])} failure(s)")
        if args.write:
            print(f"wrote {ARTIFACT}")
    return 0 if result["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
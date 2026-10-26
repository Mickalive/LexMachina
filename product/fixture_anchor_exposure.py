#!/usr/bin/env python3
"""Exposure of closing the fixture-mode ``apply_anchor_labels`` asymmetry.

Why this exists
---------------
Direction v68 ordered work item (4) contains a *conditional*:

    "close the fixture-mode ``apply_anchor_labels`` asymmetry only if it can be
     done without changing claims (measured exposure 0 rows) and pin the new
     fixture-mode span behavior with a test."

The conditional is a gate, not a chore: the asymmetry exists because
``product/query/pipeline.py`` calls the adopted counter-label decision only
when ``not fixture_generation``.  Fixture bundles — the offline slice and the
local server slice, i.e. exactly the bytes a developer/owner runs without a
paid inference budget — therefore never receive ``counter_anchor_decision`` /
``abstained_unevidenced`` records, while live/packet bundles do.

The "measured exposure 0 rows" premise came from the independent audit of run
40100397058 (``reports/audit/product/CYCLE_40100397058.md``, §5 and §8 item 4),
which measured it at a commit where **every shipped fixture leg had
``n_selected = 0``**: *"Sweeping all four shipped reality legs ... span
``n_selected = 0`` everywhere (reason ``pivot_absent``)"* and *"Current measured
exposure: 0 rows on all four legs."*  On those bytes there was no gate-confirmed
span to audit, so closing the asymmetry changed nothing the auditor cared about.

This module re-measures that conditional on the CURRENT committed bytes and
publishes both readings side by side instead of restating either one as prose.

What it measures
----------------
For every committed flagship bundle (the same population
``content_family_probe`` sweeps) it deep-copies the bundle, applies the adopted
``apply_anchor_labels(bundle, qid=provenance.qid)`` under the default
environment, and counts rows whose *counter claims* differ:

``exposure_row`` = a decision whose values in
``{counter_status, counter_evidence, counter_evidence_verified,
counter_uncertainty, counter_evidence_unevidenced}`` change.

Three populations are published so the reader can see which definition each
number uses:

* ``fixture_fixed_path`` — fixture bundles regenerated on the P0 fixed path
  (``provenance.counter_evidence_span.content_filter`` present).  This is the
  current shipped state and it carries the close/no-close decision.
* ``fixture_all`` — every committed fixture bundle, historical bytes included.
* ``already_anchored`` — bundles that already carry
  ``provenance.counter_anchor``; re-applying the decision there measures
  idempotence, not the asymmetry, and is published only as a reconciliation
  population.

Decision rule (frozen here, never re-derived after seeing numbers)::

    close_allowed  <=>  exposure rows on ``fixture_fixed_path`` == 0

What it does NOT do
-------------------
No bundle byte is written: everything runs on deep copies, so no accepted
artifact, slice, packet or byte-identity claim moves.  No frozen gate, rubric,
threshold, classifier or bar is imported for scoring, edited or re-tuned; the
frozen rubric is only re-hashed to prove the label decision this simulates is
the accepted one.  No serve verdict, admission posture or human-gate flag is
computed, and the record makes no claim about legal usefulness.

Claim ceiling
-------------
Reported-only simulation over committed bundle bytes: "if the adopted anchor
label decision were applied to these fixture bundles, N rows' counter claims
would change".  It is not a label-support measurement, not a frozen-scorer
emission measurement (factory-wide requirement 26 keeps those families
separate) and not a statement that any decision IS supporting/contrary/
limiting.

Usage
-----
    python3 product/fixture_anchor_exposure.py --run-id 40272586794
    python3 product/fixture_anchor_exposure.py --json
"""
from __future__ import annotations

import argparse
import copy
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from product.query.counter_anchor import (  # noqa: E402
    FROZEN_LABEL_RULES_SHA256,
    SCORED_STATUSES,
    apply_anchor_labels,
    load_frozen_rules,
)

#: Reuse the accepted probe's flagship population instead of re-inventing it.
from product.content_family_probe import (  # noqa: E402
    _display_path,
    _has_fixed_path_provenance,
    bundle_paths,
)

SCHEMA = "product-fixture-anchor-exposure/1"
DIRECTION_VERSION = 68

#: The counter fields whose change constitutes a changed *claim* about a row.
#: Geometry, ranks, clusters and relations are deliberately outside this set:
#: applying the label decision must never move a point.
COUNTER_FIELDS = (
    "counter_status",
    "counter_evidence",
    "counter_evidence_verified",
    "counter_uncertainty",
    "counter_evidence_unevidenced",
)

#: Ordered-work item (1) success rule: "the known sound row bstger_SK.2023.49
#: stays verified/sound".  Closing the asymmetry is only legal if that rule
#: survives, so the instrument reports whether this row is in the exposure set.
CONFIRMED_SOUND_DECISION_ID = "bstger_SK.2023.49"

#: The audit whose "0 rows" premise this measurement reconciles with.
PREMISE_AUDIT = "reports/audit/product/CYCLE_40100397058.md"

CLAIM_CEILING = (
    "REPORTED-ONLY simulation of the adopted anchor label decision over "
    "committed bundle bytes, written to deep copies only. It states how many "
    "rows' counter claims would change if the fixture path ran the adopted "
    "decision; it is not a label-support rate, not a frozen-scorer emission "
    "measurement, not a serve verdict and not a legal classification of any "
    "decision."
)


def _git_head() -> str | None:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT, capture_output=True, text=True, timeout=20, check=False,
        )
        return out.stdout.strip() or None
    except Exception:  # noqa: BLE001 - provenance only, never a run blocker
        return None


def packet_bundle_paths() -> list[Path]:
    """Committed gate-packet question bundles — the already-anchored family.

    Published only as a RECONCILIATION population: the anchor decision has
    already been applied to these bytes, so re-applying measures idempotence,
    never the fixture asymmetry.
    """
    import glob

    return sorted(
        Path(p)
        for p in glob.glob(
            str(ROOT / "results" / "product" / "gate_packet" / "*" / "questions"
                / "*.bundle.json")
        )
    )


def _row_claims(row: dict) -> dict:
    return {f: row.get(f) for f in COUNTER_FIELDS}


def measure_bundle(path: Path) -> dict[str, Any]:
    """Simulate ``apply_anchor_labels`` on one committed bundle (deep copy)."""
    doc = json.loads(path.read_text(encoding="utf-8"))
    prov = doc.get("provenance") or {}
    rows = doc.get("decisions") or []
    by_id = {str(r.get("decision_id")): r for r in rows}

    simulated = apply_anchor_labels(
        copy.deepcopy(doc), qid=prov.get("qid")
    )
    changed: list[dict[str, Any]] = []
    for row in simulated.get("decisions") or []:
        did = str(row.get("decision_id"))
        before = by_id.get(did)
        if before is None:  # the seam never adds/removes rows; be explicit if it ever did
            changed.append({"decision_id": did, "fields": {"_row_added": [None, True]}})
            continue
        diff = {}
        for field in COUNTER_FIELDS:
            old, new = before.get(field), row.get(field)
            if old != new:
                diff[field] = [old, new]
        if diff:
            changed.append({
                "decision_id": did,
                "fields": diff,
                "before_claims": _row_claims(before),
                "after_claims": _row_claims(row),
                "frozen_content_sounds_before": before.get(
                    "counter_evidence_verified"
                ) is True,
                "reason_code": (row.get("counter_anchor_decision") or {}).get(
                    "reason_code"
                ),
            })

    scored_before = [
        str(r.get("decision_id")) for r in rows
        if str(r.get("counter_status") or "") in SCORED_STATUSES
    ]
    selected = [
        str(r.get("decision_id")) for r in rows
        if (r.get("counter_evidence_span") or {}).get("selected") is True
    ]
    return {
        "path": _display_path(path),
        "fixture_mode": bool(prov.get("fixture_mode")),
        "qid": prov.get("qid"),
        "fixed_path": _has_fixed_path_provenance(doc),
        "has_counter_anchor_provenance": "counter_anchor" in prov,
        "n_decisions": len(rows),
        "n_scored": len(scored_before),
        "n_span_selected": len(selected),
        "n_changed_rows": len(changed),
        "changed_rows": changed,
        "simulated": {
            "applied": simulated.get("provenance", {}).get(
                "counter_anchor", {}
            ).get("applied"),
            "n_scored": simulated.get("provenance", {}).get(
                "counter_anchor", {}
            ).get("n_scored"),
            "n_emitted": simulated.get("provenance", {}).get(
                "counter_anchor", {}
            ).get("n_emitted"),
            "n_abstained": simulated.get("provenance", {}).get(
                "counter_anchor", {}
            ).get("n_abstained"),
            "yield": simulated.get("provenance", {}).get(
                "counter_anchor", {}
            ).get("yield"),
            "abstention_reasons": simulated.get("provenance", {}).get(
                "counter_anchor", {}
            ).get("abstention_reasons"),
        },
    }


def _summarise(records: list[dict]) -> dict[str, Any]:
    changed = [c for r in records for c in r["changed_rows"]]
    verified_flips = [
        c for c in changed
        if "counter_evidence_verified" in c.get("fields", {})
    ]
    sound = [c for c in changed if c["decision_id"] == CONFIRMED_SOUND_DECISION_ID]
    return {
        "n_bundles": len(records),
        "n_decisions": sum(r["n_decisions"] for r in records),
        "n_scored_rows": sum(r["n_scored"] for r in records),
        "n_span_selected_rows": sum(r["n_span_selected"] for r in records),
        "n_bundles_with_exposure": sum(1 for r in records if r["n_changed_rows"]),
        "n_changed_rows": len(changed),
        "n_changed_rows_unique": len({c["decision_id"] for c in changed}),
        "n_counter_evidence_verified_flips": len(verified_flips),
        "changed_decision_ids": sorted({c["decision_id"] for c in changed}),
        "confirmed_sound_row_in_exposure": bool(sound),
        "confirmed_sound_row_fields": (sound[0]["fields"] if sound else None),
        "n_bundles_already_carrying_anchor": sum(
            1 for r in records if r["has_counter_anchor_provenance"]
        ),
    }


def run(
    run_id: str | None = None,
    direction_version: int | None = None,
) -> dict[str, Any]:
    records = [measure_bundle(Path(p)) for p in bundle_paths()]
    packet_records = [measure_bundle(Path(p)) for p in packet_bundle_paths()]

    fixture_fixed = [r for r in records if r["fixture_mode"] and r["fixed_path"]]
    fixture_all = [r for r in records if r["fixture_mode"]]
    anchored = [r for r in packet_records if r["has_counter_anchor_provenance"]]

    # Fail closed on the frozen rubric: a re-frozen rubric would make the
    # simulated label decision meaningless, so refuse rather than publish.
    _rules, digest = load_frozen_rules()
    assert digest == FROZEN_LABEL_RULES_SHA256

    fixed_sum = _summarise(fixture_fixed)
    all_sum = _summarise(fixture_all)
    anchored_sum = _summarise(anchored)

    exposure_rows = fixed_sum["n_changed_rows"]
    close_allowed = exposure_rows == 0

    decision = (
        "CLOSE_ASYMMETRY" if close_allowed else "DO_NOT_CLOSE"
    )
    decision_reason = (
        "exposure on the fixture fixed-path family is 0 rows: closing the "
        "asymmetry changes no counter claim"
        if close_allowed
        else (
            f"exposure on the fixture fixed-path family is {exposure_rows} "
            f"row(s) over {fixed_sum['n_bundles_with_exposure']} bundle(s): "
            "closing the asymmetry would change counter claims, and the "
            "ordered work permits closure ONLY at measured exposure 0 rows"
        )
    )

    return {
        "schema": SCHEMA,
        "run_id": run_id,
        "direction_version": direction_version or DIRECTION_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "product_head": _git_head(),
        "requirement": (
            "direction v68 ordered work item (4): close the fixture-mode "
            "apply_anchor_labels asymmetry only if it can be done without "
            "changing claims (measured exposure 0 rows)"
        ),
        "exposure_definition": (
            "a decision whose values in "
            + str(list(COUNTER_FIELDS))
            + " differ after apply_anchor_labels(deepcopy(bundle), "
            "qid=provenance.qid) under the default environment; geometry, "
            "ranks, clusters and relations are never part of the exposure set"
        ),
        "simulation_only": {
            "writes_no_bundle_bytes": True,
            "runs_on_deep_copies": True,
            "frozen_rules_sha256": digest,
            "frozen_rules_rehashed_before_use": True,
            "frozen_gate_rubric_threshold_edited": False,
        },
        "populations": {
            "fixture_fixed_path": {
                "selector": "provenance.fixture_mode is true AND "
                            "provenance.counter_evidence_span.content_filter present",
                **fixed_sum,
                "bundles": fixture_fixed,
            },
            "fixture_all": {
                "selector": "provenance.fixture_mode is true (all committed bytes)",
                **all_sum,
                "bundles": [
                    {k: v for k, v in r.items() if k != "changed_rows"}
                    for r in fixture_all
                ],
            },
            "already_anchored": {
                "selector": "gate_packet question bundles carrying "
                            "provenance.counter_anchor (re-application, "
                            "idempotence population — NOT the asymmetry)",
                **anchored_sum,
                "bundles": [
                    {k: v for k, v in r.items() if k != "changed_rows"}
                    for r in anchored
                ],
            },
        },
        "decision": {
            "rule": "close_allowed <=> exposure rows on fixture_fixed_path == 0",
            "exposure_rows_on_fixture_fixed_path": exposure_rows,
            "close_allowed": close_allowed,
            "verdict": decision,
            "reason": decision_reason,
            "pipeline_gate_changed": False,
        },
        "premise_reconciliation": {
            "premise": (
                "auditor report §8 item 4 recorded 'Current measured exposure: "
                "0 rows on all four legs', resting on the §5 sweep statement "
                "'span n_selected = 0 everywhere (reason pivot_absent)'"
            ),
            "premise_source": PREMISE_AUDIT,
            "premise_population": (
                "the four offline fixture legs as built at run 40100397058, "
                "where every leg had n_selected = 0"
            ),
            "current_head_n_span_selected_on_fixture_fixed_path":
                fixed_sum["n_span_selected_rows"],
            "premise_holds_at_current_head": fixed_sum["n_span_selected_rows"] == 0,
            "divergence": (
                "the 0-row premise was a consequence of n_selected = 0 on those "
                "bytes; the current committed fixture family carries "
                f"{fixed_sum['n_span_selected_rows']} gate-confirmed span(s) and "
                f"{exposure_rows} row(s) whose counter claims change under the "
                "adopted decision, so the premise does not reproduce at this head"
            ),
            "both_numbers_published": True,
            "auditor_population_not_recorded": True,
        },
        "ordered_work_1_interaction": {
            "rule": (
                "ordered work (1) requires the known sound row "
                f"{CONFIRMED_SOUND_DECISION_ID} to stay verified/sound on the "
                "shipped path"
            ),
            "closing_would_flip_confirmed_sound_row": fixed_sum[
                "confirmed_sound_row_in_exposure"
            ],
            "flip_fields": fixed_sum["confirmed_sound_row_fields"],
        },
        "claim_ceiling": CLAIM_CEILING,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run-id", default=None)
    ap.add_argument("--direction-version", type=int, default=None)
    ap.add_argument("--out", default=None, help="output json path")
    ap.add_argument("--json", action="store_true", help="print record and exit")
    args = ap.parse_args(argv)

    rec = run(run_id=args.run_id, direction_version=args.direction_version)
    if args.json:
        print(json.dumps(rec, indent=2, ensure_ascii=False, sort_keys=True))
        return 0
    out = args.out
    if not out:
        rid = args.run_id or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        out = str(
            ROOT / "results" / "product" / "fixture_anchor_exposure"
            / f"CYCLE_{rid}.json"
        )
    out_path = Path(out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(rec, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    try:
        shown = out_path.relative_to(ROOT)
    except ValueError:
        shown = out_path
    fixed = rec["populations"]["fixture_fixed_path"]
    dec = rec["decision"]
    print(f"fixture anchor exposure -> {shown}")
    print(f"  fixture fixed-path family: {fixed['n_bundles']} bundle(s), "
          f"{fixed['n_decisions']} decisions, n_scored={fixed['n_scored_rows']}, "
          f"n_span_selected={fixed['n_span_selected_rows']}")
    print(f"  exposure rows: {fixed['n_changed_rows']} "
          f"({fixed['n_bundles_with_exposure']} bundle(s)); "
          f"verified-flag flips: {fixed['n_counter_evidence_verified_flips']}")
    print(f"  verdict: {dec['verdict']} — {dec['reason']}")
    print("  premise reconciliation: "
          f"premise_holds_at_current_head="
          f"{rec['premise_reconciliation']['premise_holds_at_current_head']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

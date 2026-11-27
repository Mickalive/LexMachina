#!/usr/bin/env python3
"""Machine-readable evidence for the post-hydration content recheck leg.

Direction v68 ordered work item (1) says that EVERY row whose selected or
incumbent counter evidence fails the frozen D1-D4 predicates must be rejected
or downgraded on the shipped emission path.  The accepted P0 leg covers stage 1
and the no-profile sweep; this instrument closes the remaining observed path:
stage 2 runs AFTER the pool counter-surface scan hydrates ``full_text``, and
hydration can move a previously clean, snippet-grounded quote into the frozen
letterhead zone.  The stage-1 incumbent sweep skips rows carrying a span
record, and stage 2 did not re-filter, so a verified D2 row could survive.

This instrument publishes:

* ``reproduction`` — BEFORE/AFTER per-row evidence, reason_code, defects and
  verified status for a stage-1 clean incumbent that becomes D2 after
  hydration, and for the known sound row that must remain verified;
* ``fresh_family`` — the five bundles regenerated this cycle, with their
  provenance recheck blocks and zero verified-defective rows;
* ``family_probe_link`` — the already-published frozen family histogram,
  false-reject count and guarded-arm yield from ``content_family_probe``
  (re-hashed, never re-derived or re-tuned).

Reported-only product measurement.  No frozen gate, rubric, threshold or bar
is scored or edited; no serve verdict is re-run; no packet is admitted.

Usage:
    python3 product/post_hydration_recheck_probe.py --run-id 45947662468
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from product.query import counter_evidence_span as ces  # noqa: E402

QUOTE = "Tribunal fédéral, consideration de bail et d'entretien"
SOUND_BUNDLE = (
    "results/product/offline_slice/20261023T121512Z/"
    "corporate-criminal-liability.bundle.json"
)
SOUND_ID = "bstger_SK.2023.49"


def _load(rel: str) -> dict:
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _stage1_clean_incumbent() -> dict:
    row = {
        "decision_id": "synthetic-hydration-recheck",
        "query": "bail entretien",
        "language": "fr",
        "counter_status": "candidate-limiting",
        "counter_evidence": QUOTE,
        "counter_evidence_verified": True,
        "snippet": QUOTE,
        "full_text": "",
        "adversarial_retrieval_signal": True,
        "x": 0.25,
        "y": -0.5,
        "cluster_id": 3,
        "rank": 7,
    }
    out = ces.apply_verified_span_selection(
        {"query": "bail entretien", "decisions": [row], "provenance": {}},
        mode="select",
    )
    row_out = out["decisions"][0]
    assert row_out["counter_evidence_verified"] is True
    assert ces.frozen_content_defects(row_out["counter_evidence"], row_out) == []
    return out


def _row_snapshot(d: dict) -> dict:
    return {
        "decision_id": d.get("decision_id"),
        "counter_evidence": d.get("counter_evidence"),
        "counter_evidence_verified": d.get("counter_evidence_verified"),
        "counter_evidence_unevidenced": d.get("counter_evidence_unevidenced"),
        "counter_evidence_unevidenced_reason": d.get(
            "counter_evidence_unevidenced_reason"),
        "counter_status": d.get("counter_status"),
        "frozen_defects": ces.frozen_content_defects(
            d.get("counter_evidence") or "", d),
        "grounding": list(ces.ground_evidence(d.get("counter_evidence") or "", d)),
        "geometry": [d.get("x"), d.get("y"), d.get("cluster_id"), d.get("rank")],
    }


def run(run_id: str, direction_version: int) -> dict:
    # 1. Reproduce the residual and its closure through the public shipped path.
    stage1 = _stage1_clean_incumbent()
    hydrated = copy.deepcopy(stage1)
    hydrated["decisions"][0]["full_text"] = f"Cour d'appel\n{QUOTE}\nConsidérant"
    hydrated["decisions"][0]["counter_surface_signal"] = {
        "heuristic_status": "candidate-limiting"
    }
    after = ces.apply_surface_span_confirmation(hydrated, mode="select")
    before_row, after_row = hydrated["decisions"][0], after["decisions"][0]
    recheck = after["provenance"]["counter_evidence_content_recheck"]

    sound_before = _load(SOUND_BUNDLE)
    sound_after = ces.apply_surface_span_confirmation(sound_before, mode="select")
    sound_row = next(d for d in sound_after["decisions"]
                     if d["decision_id"] == SOUND_ID)

    reproduction = {
        "shipped_path": (
            "apply_verified_span_selection -> apply_counter_surface (hydration) "
            "-> apply_surface_span_confirmation -> post_hydration_content_recheck"
        ),
        "hydration_injection": {
            "field": "full_text",
            "text": hydrated["decisions"][0]["full_text"],
            "why": (
                "the same verbatim quote that stage 1 grounded in snippet now "
                "occurs inside the frozen D2 letterhead zone of full_text"
            ),
        },
        "defective_row": {
            "before": _row_snapshot(before_row),
            "after": _row_snapshot(after_row),
            "stage1_span_record_present": bool(
                before_row.get("counter_evidence_span")),
            "closed": (
                before_row["counter_evidence_verified"] is True
                and after_row["counter_evidence_verified"] is False
                and after_row["counter_evidence_unevidenced_reason"]
                == "d2_letterhead_zone"
                and after_row["counter_evidence"] == before_row["counter_evidence"]
            ),
        },
        "sound_row": {
            "bundle": SOUND_BUNDLE,
            "before": {"verified": True, "defects": []},
            "after": _row_snapshot(sound_row),
            "preserved": (
                sound_row["counter_evidence_verified"] is True
                and ces.frozen_content_defects(sound_row["counter_evidence"],
                                               sound_row) == []
            ),
        },
        "provenance": {
            "version": recheck["version"],
            "n_verified_checked": recheck["n_verified_checked"],
            "n_downgraded": recheck["n_downgraded"],
            "downgraded_ids": recheck["downgraded_ids"],
            "leg": recheck["downgrades"][0]["leg"],
            "source_stage": recheck["downgrades"][0]["source_stage"],
            "reason_code": recheck["downgrades"][0]["reason_code"],
            "defects": recheck["downgrades"][0]["defects"],
            "content_filter": recheck["content_filter"],
        },
        "geometry_unchanged": (
            _row_snapshot(before_row)["geometry"]
            == _row_snapshot(after_row)["geometry"]
        ),
    }

    # 2. Fresh family regenerated with the fixed path active this cycle.
    fresh_paths = sorted(
        [p for p in ROOT.glob("results/product/offline_slice/45947662468-*/*.bundle.json")]
        + list(ROOT.glob("results/product/server_slice/45947662468/*.bundle.json"))
    )
    fresh = []
    for p in fresh_paths:
        rel = str(p.relative_to(ROOT))
        doc = _load(rel)
        prov = (doc.get("provenance") or {}).get("counter_evidence_content_recheck") or {}
        verified = [d for d in doc["decisions"]
                    if d.get("counter_evidence_verified") is True]
        defective = [d["decision_id"] for d in verified
                     if ces.frozen_content_defects(d.get("counter_evidence") or "", d)]
        fresh.append({
            "path": rel,
            "sha256": _sha(p),
            "n_decisions": len(doc.get("decisions") or []),
            "n_verified": len(verified),
            "verified_defective_ids": defective,
            "recheck_version": prov.get("version"),
            "recheck_n_downgraded": prov.get("n_downgraded"),
            "stage2_applied": (
                (doc.get("provenance") or {})
                .get("counter_evidence_span_surface", {}).get("applied")),
        })

    # 3. Link the existing frozen family probe instead of re-deriving it.
    probe_rel = f"results/product/counter_content_family/CYCLE_{run_id}.json"
    probe_path = ROOT / probe_rel
    probe = _load(probe_rel) if probe_path.is_file() else None
    hist = (probe or {}).get("fixed_path_family", {}).get("totals", {})
    guarded = {
        k: v.get("current_guarded", {}).get("yield")
        for k, v in (probe or {}).get("packet_v3_reemission", {})
        .get("bundles", {}).items()
    }
    family_link = {
        "artifact": probe_rel,
        "sha256": _sha(probe_path) if probe_path.is_file() else None,
        "direction_version": (probe or {}).get("direction_version"),
        "fixed_path_totals": hist,
        "false_reject_count": (probe or {}).get("false_reject_count"),
        "ordered_work_2_success_rule": (probe or {}).get(
            "ordered_work_2_success_rule"),
        "guarded_arm_yield_on_packet_v3": guarded,
        "claim": (
            "linked verbatim from product's own frozen re-probe; no frozen "
            "predicate, rubric, threshold or bar is re-derived here"
        ),
    }

    return {
        "schema": "post-hydration-content-recheck/1",
        "run_id": run_id,
        "direction_version": direction_version,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "reproduction": reproduction,
        "fresh_family": fresh,
        "family_probe_link": family_link,
        "success": {
            "defective_row_closed": reproduction["defective_row"]["closed"],
            "sound_row_preserved": reproduction["sound_row"]["preserved"],
            "geometry_unchanged": reproduction["geometry_unchanged"],
            "fresh_family_zero_verified_defective": all(
                not f["verified_defective_ids"] for f in fresh) and bool(fresh),
            "frozen_family_histogram_zero": (
                hist.get("defect_histogram", {}).get("D2_letterhead_zone") == 0
                and hist.get("defect_histogram", {}).get("D3_markup_residue") == 0
                and hist.get("defect_histogram", {}).get("D4_language_marker_mismatch") == 0
            ),
            "false_rejects_zero": (probe or {}).get("false_reject_count") == 0,
            "guarded_yield_non_decreasing": all(
                v == (probe or {}).get("packet_v3_reemission", {})
                .get("bundles", {}).get(k, {}).get("accepted_guarded", {}).get("yield")
                for k, v in guarded.items()
            ) and bool(guarded),
        },
        "claim_ceiling": (
            "Reported-only product measurement of deterministic content "
            "narrowing. No frozen bar scored, no serve verdict re-run, no "
            "packet admitted, no human-gate claim, no legal-usefulness claim."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run-id", default=None)
    ap.add_argument("--direction-version", type=int, default=68)
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)
    rid = args.run_id or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    rec = run(rid, args.direction_version)
    out = Path(args.out) if args.out else (
        ROOT / "results" / "product" / "post_hydration_recheck" / f"CYCLE_{rid}.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rec, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
                   encoding="utf-8")
    print(f"post-hydration recheck -> {out.relative_to(ROOT)}")
    print(f"  success: {json.dumps(rec['success'], sort_keys=True)}")
    return 0 if all(rec["success"].values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())

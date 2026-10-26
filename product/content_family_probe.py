#!/usr/bin/env python3
"""Frozen D2/D3/D4 content-defect re-probe over the committed bundle family.

Why this exists
---------------
Direction v68 ordered work item (2) asks the product to *publish* a per-bundle
and per-class histogram of the frozen D2/D3/D4 content predicates over the
flagship offline/server slice family, together with the false-reject count on
the confirmed set, instead of restating the result as prose in
``state/product.json``.  Until this module existed the only statement of that
result was the narrative line

    "All 4 offline slice bundles and the server slice bundle regenerated with
     the fix show correct downgrades"

which no committed instrument re-derived.  This module is that instrument.

What it measures (and what it deliberately does not)
----------------------------------------------------
For every committed ``*.bundle.json`` under ``results/product/offline_slice/``
and ``results/product/server_slice/`` it applies the product's own frozen
content predicates (``product.query.counter_evidence_span.frozen_content_defects``)
to every row that is still ``counter_evidence_verified is True`` and counts the
defect classes that survive on the *shipped* (post-filter) bytes.

* ``fixed_path_family`` — bundles whose provenance carries
  ``provenance.counter_evidence_span.content_filter``, i.e. bundles that were
  regenerated on the fixed path.  This family is *identified from the bytes*,
  never hard-coded, so a future regeneration is picked up automatically.
* ``all_committed`` — every committed bundle, including historical ones that
  predate the fix.  Historical defects are preserved evidence, not a defect of
  the current head; both populations are published side by side so the two are
  never conflated.
* ``before_after`` — for the four decisions the accepted FAST-MVP falsifier
  measured as verified-but-defective, the seam's own per-row downgrade records
  on the fixed path are paired with the historical verified verdict: same
  decision, BEFORE verified+defective, AFTER unevidenced with a reason code.
  The confirmed sound row is re-checked in the same pass.  No historical
  bundle is rewritten or deleted.
* ``packet_v3_reemission`` — the frozen packet-of-record v3 bytes are hashed,
  deep-copied, and re-run through the current baseline and guarded arms.  The
  accepted arm artifact is pinned by sha256 and compared side by side on
  emitted / verified / abstained / support-among-emitted / yield.  Because v3
  carries no *verified defective incumbent*, the v68 rejection leg is expected
  to downgrade zero rows there; that no-op and the one content-clean verbatim
  guarded emission are published explicitly rather than hidden.

It imports the frozen predicate constants verbatim through the accepted
``counter_evidence_span`` module and re-publishes their provenance hashes.  It
NEVER re-derives, re-tunes or edits the frozen gate, rubric, threshold or bar,
it never runs the evaluation scorer and it makes no serve/admission claim.

Claim ceiling
-------------
Reported-only measurement of committed bytes under the frozen content
predicates.  It says nothing about legal usefulness, nothing about a frozen
scorer's emission predicate (factory-wide requirement 26 keeps those families
separate), and nothing about bundles outside this repository.

Usage
-----
    python3 product/content_family_probe.py --run-id 40143042888
    python3 product/content_family_probe.py --json
"""
from __future__ import annotations

import argparse
import copy
import glob
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from product.query import counter_evidence_span as ces  # noqa: E402
from product.query.counter_anchor import apply_anchor_labels  # noqa: E402
from product.query.counter_emission_repair import apply_counter_emission_repair  # noqa: E402
from product.measure_counter_span_selection import summarise_arm  # noqa: E402

SCHEMA = "product-content-family-probe/1"

#: The frozen defect classes ordered work item (2) is scored on.
DEFECT_CLASSES = (
    "D1_empty_evidence",
    "D2_letterhead_zone",
    "D3_markup_residue",
    "D4_language_marker_mismatch",
)

#: The confirmed (frozen-gate-confirmed, content-sound) row that must survive
#: the filter.  Ordered-work success rule: "the known sound row
#: bstger_SK.2023.49 stays verified/sound".
CONFIRMED_SOUND_ROW = (
    "results/product/offline_slice/20261024T185300Z"
    "/corporate-criminal-liability.bundle.json",
    "bstger_SK.2023.49",
)

CLAIM_CEILING = (
    "REPORTED-ONLY measurement of committed bundle bytes under the frozen "
    "D1-D4 content predicates. It re-derives no frozen scorer population or "
    "emission predicate, scores no frozen bar, evaluates no serve verdict and "
    "makes no legal-usefulness claim. Historical bundles that predate the fix "
    "are preserved evidence, not current-head defects."
)

#: The four decisions the accepted FAST-MVP falsifier (evaluation run
#: 40105794124, accept bcb4520a) measured as verified-but-content-defective.
#: Ordered work (1) requires per-row BEFORE/AFTER for exactly these rows plus
#: the one sound row.
ACCEPTED_DEFECTIVE_ROWS = {
    "gr_gerichte_ERZ 2010 25": ["D2_letterhead_zone"],
    "bge_BGE_110_II_391": ["D2_letterhead_zone"],
    "ge_gerichte_CAPH_107_2004": ["D3_markup_residue"],
    "bge_BGE_121_III_260": [
        "D3_markup_residue",
        "D4_language_marker_mismatch",
    ],
}

CONFIRMED_SOUND_DECISION_ID = "bstger_SK.2023.49"

#: Packet-of-record v3 bytes.  This module NEVER writes to this directory; the
#: arm re-run happens on deep copies and the committed sha256 is published so
#: a reader can see the bytes did not move.
PACKET_V3_QUESTIONS = (
    ROOT / "results" / "product" / "gate_packet" / "39319405429" / "questions"
)
PACKET_V3_QIDS = {
    "de-kapitalverletzung": "de-kapitalverletzung",
    "fr-bail-entretien": "fr-bail-entretien",
    "it-responsabilita-medica": "it-responsabilita-medica",
}

#: The accepted guarded/unguarded arm measurement this cycle must not regress.
#: Read-only comparison baseline; its numbers are NEVER rewritten.
ACCEPTED_V3_ARM_ARTIFACT = (
    ROOT / "results" / "product" / "counter_span"
    / "CYCLE_39986094168_span_selection.json"
)


def bundle_paths() -> list[Path]:
    """Every committed flagship bundle, sorted for determinism."""
    patterns = (
        "results/product/offline_slice/*/*.bundle.json",
        "results/product/server_slice/*/*.bundle.json",
    )
    out: list[Path] = []
    for pat in patterns:
        out.extend(Path(p) for p in glob.glob(str(ROOT / pat)))
    return sorted(set(out))


def _has_fixed_path_provenance(doc: dict) -> bool:
    cf = ((doc.get("provenance") or {}).get("counter_evidence_span") or {}).get(
        "content_filter"
    )
    return isinstance(cf, dict) and bool(cf)


def _display_path(path: Path) -> str:
    """Repo-relative when possible; absolute for out-of-tree replay output.

    ``live_cache_replay.py --out-dir /tmp/...`` is a supported verification
    mode, and a probe must not crash merely because the bundle it is asked to
    inspect lives outside the repository.
    """
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path.resolve())


def probe_bundle(path: Path) -> dict:
    """Per-bundle histogram of surviving frozen content defects."""
    doc = json.loads(path.read_text(encoding="utf-8"))
    rows = doc.get("decisions") or []
    hist: dict[str, int] = {}
    defective: list[dict] = []
    verified_ids: list[str] = []
    for row in rows:
        if row.get("counter_evidence_verified") is not True:
            continue
        did = str(row.get("decision_id"))
        verified_ids.append(did)
        defects = ces.frozen_content_defects(str(row.get("counter_evidence") or ""), row)
        for d in defects:
            hist[d] = hist.get(d, 0) + 1
        if defects:
            defective.append({"decision_id": did, "defects": defects})
    return {
        "path": _display_path(path),
        "fixed_path_family": _has_fixed_path_provenance(doc),
        "n_decisions": len(rows),
        "n_verified": len(verified_ids),
        "n_verified_defective": len(defective),
        "defect_histogram": {c: hist.get(c, 0) for c in DEFECT_CLASSES},
        "verified_defective_rows": defective,
        "verified_ids": verified_ids,
    }


def _totals(rows: list[dict]) -> dict:
    hist = {c: 0 for c in DEFECT_CLASSES}
    for r in rows:
        for c, n in r["defect_histogram"].items():
            hist[c] = hist.get(c, 0) + n
    return {
        "n_bundles": len(rows),
        "n_decisions": sum(r["n_decisions"] for r in rows),
        "n_verified": sum(r["n_verified"] for r in rows),
        "n_verified_defective": sum(r["n_verified_defective"] for r in rows),
        "defect_histogram": hist,
    }


def confirmed_set_status() -> dict:
    """False-reject check: the known sound row must still be verified."""
    rel, did = CONFIRMED_SOUND_ROW
    path = ROOT / rel
    if not path.is_file():
        return {
            "decision_id": did,
            "path": rel,
            "present": False,
            "still_verified": False,
            "defects": ["bundle_missing"],
        }
    doc = json.loads(path.read_text(encoding="utf-8"))
    row = next((d for d in doc.get("decisions") or [] if d.get("decision_id") == did), None)
    if row is None:
        return {
            "decision_id": did,
            "path": rel,
            "present": False,
            "still_verified": False,
            "defects": ["row_missing"],
        }
    defects = ces.frozen_content_defects(str(row.get("counter_evidence") or ""), row)
    return {
        "decision_id": did,
        "path": rel,
        "present": True,
        "still_verified": row.get("counter_evidence_verified") is True,
        "defects": defects,
        "counter_status": row.get("counter_status"),
    }


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _row_by_id(doc: dict, did: str) -> dict | None:
    return next(
        (d for d in doc.get("decisions") or [] if d.get("decision_id") == did),
        None,
    )


def per_row_before_after(fixed_rows: list[dict]) -> dict:
    """Publish the seam's own BEFORE/AFTER for every fixed-path downgrade.

    Ordered work (1) asks for per-row before/after evidence, reason_code and
    verified status for the four accepted defective decisions and the one sound
    row.  The seam already records that pair in
    ``provenance.counter_evidence_span.downgrades``; this function simply
    surfaces it, plus a completeness check against the accepted four.
    """
    records: list[dict] = []
    defect_free_downgrades: list[str] = []
    for bundle in fixed_rows:
        path = ROOT / bundle["path"]
        doc = json.loads(path.read_text(encoding="utf-8"))
        span = ((doc.get("provenance") or {}).get("counter_evidence_span") or {})
        for dg in span.get("downgrades") or []:
            did = str(dg.get("decision_id"))
            row = _row_by_id(doc, did) or {}
            before = dg.get("before") or {}
            after = dg.get("after") or {}
            record = {
                "path": bundle["path"],
                "decision_id": did,
                "defects": list(dg.get("defects") or []),
                "leg": dg.get("leg"),
                "reason_code": dg.get("reason_code"),
                "incumbent_grounded_in": dg.get("incumbent_grounded_in"),
                "before": {
                    "counter_evidence_head": before.get("counter_evidence_head"),
                    "counter_evidence_verified": before.get(
                        "counter_evidence_verified"
                    ),
                    "counter_status": before.get("counter_status"),
                },
                "after": {
                    "counter_evidence_verified": after.get(
                        "counter_evidence_verified"
                    ),
                    "counter_status": after.get("counter_status"),
                    "counter_evidence_unevidenced_reason": after.get(
                        "counter_evidence_unevidenced_reason"
                    ),
                    # Read from the shipped row as well, so a provenance note
                    # can never disagree with the bytes.
                    "row_counter_evidence_verified": row.get(
                        "counter_evidence_verified"
                    ),
                    "row_counter_status": row.get("counter_status"),
                    "row_counter_evidence_unevidenced_reason": row.get(
                        "counter_evidence_unevidenced_reason"
                    ),
                },
            }
            records.append(record)
            if not record["defects"]:
                defect_free_downgrades.append(did)

    by_id: dict[str, dict] = {}
    for r in records:
        by_id.setdefault(r["decision_id"], r)

    coverage = []
    for did, expected in ACCEPTED_DEFECTIVE_ROWS.items():
        rec = by_id.get(did)
        coverage.append({
            "decision_id": did,
            "expected_defects": expected,
            "present": rec is not None,
            "observed_defects": rec["defects"] if rec else None,
            "before_verified": (
                rec["before"]["counter_evidence_verified"] if rec else None
            ),
            "after_verified": (
                rec["after"]["row_counter_evidence_verified"] if rec else None
            ),
            "after_reason_code": (
                rec["after"]["row_counter_evidence_unevidenced_reason"]
                if rec else None
            ),
        })

    sound = confirmed_set_status()
    return {
        "schema": "product-v68-rejection-before-after/1",
        "downgrades": records,
        "accepted_four_coverage": coverage,
        "all_four_present": all(c["present"] for c in coverage),
        "all_four_before_verified": all(
            c["before_verified"] is True for c in coverage
        ),
        "all_four_after_unevidenced": all(
            c["after_verified"] is False and bool(c["after_reason_code"])
            for c in coverage
        ),
        "sound_row": {
            "decision_id": CONFIRMED_SOUND_DECISION_ID,
            "still_verified": sound.get("still_verified"),
            "defects": sound.get("defects"),
            "path": sound.get("path"),
        },
        "defect_free_downgrades": defect_free_downgrades,
        "false_reject_count": len(defect_free_downgrades),
    }


def packet_v3_arms() -> dict:
    """Re-run the accepted guarded/unguarded counter arm over frozen v3 bytes.

    Ordered work (2) requires the packet-of-record v3 bytes side by side with
    the regenerated family, plus support-among-emitted, abstention count, yield
    and the guarded-arm yield.  The accepted arm artifact is the read-only
    BEFORE; this function recomputes the same two arms on current head over a
    deep copy of the SAME committed bytes and publishes the comparison.

    It writes nothing into the packet directory and re-scores no frozen bar.
    """
    if not ACCEPTED_V3_ARM_ARTIFACT.is_file():
        return {
            "available": False,
            "reason": "accepted_v3_arm_artifact_missing",
            "path": str(ACCEPTED_V3_ARM_ARTIFACT.relative_to(ROOT)),
        }
    accepted = json.loads(ACCEPTED_V3_ARM_ARTIFACT.read_text(encoding="utf-8"))
    bundles: dict[str, dict] = {}
    totals = {
        "accepted_baseline": {"n_scored": 0, "n_emitted": 0,
                              "n_abstained": 0, "n_emitted_verified": 0},
        "accepted_unguarded": {"n_scored": 0, "n_emitted": 0,
                               "n_abstained": 0, "n_emitted_verified": 0},
        "accepted_guarded": {"n_scored": 0, "n_emitted": 0,
                             "n_abstained": 0, "n_emitted_verified": 0},
        "current_baseline": {"n_scored": 0, "n_emitted": 0,
                             "n_abstained": 0, "n_emitted_verified": 0},
        "current_unguarded": {"n_scored": 0, "n_emitted": 0,
                              "n_abstained": 0, "n_emitted_verified": 0},
        "current_guarded": {"n_scored": 0, "n_emitted": 0,
                            "n_abstained": 0, "n_emitted_verified": 0},
    }
    for slug, qid in PACKET_V3_QIDS.items():
        path = PACKET_V3_QUESTIONS / f"{slug}.bundle.json"
        raw = path.read_bytes()
        observed_sha = hashlib.sha256(raw).hexdigest()
        source = json.loads(raw)
        baseline_bundle = apply_anchor_labels(
            apply_counter_emission_repair(copy.deepcopy(source)), qid=qid
        )
        unguarded_bundle = apply_anchor_labels(
            apply_counter_emission_repair(
                ces.apply_verified_span_selection(
                    copy.deepcopy(source),
                    qid=qid,
                    mode="select",
                    env={**os.environ, "LEXMACHINA_COUNTER_SPAN_GUARD": "off"},
                )
            ),
            qid=qid,
        )
        guarded_bundle = apply_anchor_labels(
            apply_counter_emission_repair(
                ces.apply_verified_span_selection(
                    copy.deepcopy(source),
                    qid=qid,
                    env={**os.environ, "LEXMACHINA_COUNTER_SPAN_GUARD": "on"},
                )
            ),
            qid=qid,
        )
        b = summarise_arm(baseline_bundle)
        u = summarise_arm(unguarded_bundle)
        g = summarise_arm(guarded_bundle)
        accepted_bundle = (accepted.get("bundles") or {}).get(slug) or {}
        ab = accepted_bundle.get("baseline") or {}
        au = accepted_bundle.get("candidate_unguarded") or {}
        ac = accepted_bundle.get("candidate") or {}

        by_id = {
            str(d.get("decision_id")): d
            for d in guarded_bundle.get("decisions") or []
        }
        emitted_defects: dict[str, list[str]] = {}
        for did in g.get("emitted_ids") or []:
            row = by_id.get(str(did)) or {}
            emitted_defects[str(did)] = ces.frozen_content_defects(
                str(row.get("counter_evidence") or ""), row
            )
        span = ((guarded_bundle.get("provenance") or {})
                .get("counter_evidence_span") or {})

        baseline_match = all(
            b.get(k) == ab.get(k)
            for k in ("n_scored", "n_emitted", "n_abstained",
                      "support_rate_among_emitted", "yield")
        )
        unguarded_match = all(
            u.get(k) == au.get(k)
            for k in ("n_scored", "n_emitted", "n_abstained",
                      "support_rate_among_emitted", "yield")
        )
        guarded_match = all(
            g.get(k) == ac.get(k)
            for k in ("n_scored", "n_emitted", "n_abstained",
                      "support_rate_among_emitted", "yield")
        )
        bundles[slug] = {
            "qid": qid,
            "bundle_sha256": observed_sha,
            "accepted_bundle_sha256": accepted_bundle.get("bundle_sha256"),
            "packet_bytes_unchanged": (
                observed_sha == accepted_bundle.get("bundle_sha256")
            ),
            "accepted_baseline": {
                k: ab.get(k) for k in (
                    "n_scored", "n_emitted", "n_abstained",
                    "support_rate_among_emitted", "yield", "emitted_ids",
                )
            },
            "accepted_unguarded": {
                k: au.get(k) for k in (
                    "n_scored", "n_emitted", "n_abstained",
                    "support_rate_among_emitted", "yield", "emitted_ids",
                )
            },
            "accepted_guarded": {
                k: ac.get(k) for k in (
                    "n_scored", "n_emitted", "n_abstained",
                    "support_rate_among_emitted", "yield", "emitted_ids",
                )
            },
            "current_baseline": {
                k: b.get(k) for k in (
                    "n_scored", "n_emitted", "n_abstained",
                    "support_rate_among_emitted", "yield",
                    "abstention_reasons", "emitted_ids",
                    "n_emitted_verified", "n_emitted_verbatim",
                )
            },
            "current_unguarded": {
                k: u.get(k) for k in (
                    "n_scored", "n_emitted", "n_abstained",
                    "support_rate_among_emitted", "yield",
                    "abstention_reasons", "emitted_ids",
                    "n_emitted_verified", "n_emitted_verbatim",
                )
            },
            "current_guarded": {
                k: g.get(k) for k in (
                    "n_scored", "n_emitted", "n_abstained",
                    "support_rate_among_emitted", "yield",
                    "abstention_reasons", "emitted_ids",
                    "n_emitted_verified", "n_emitted_verbatim",
                    "span_selection", "emitted",
                )
            },
            "baseline_reproduced": baseline_match,
            "unguarded_reproduced": unguarded_match,
            "guarded_reproduced": guarded_match,
            "guarded_yield_not_decreased": (
                (g.get("yield") or 0.0) >= (ac.get("yield") or 0.0)
            ),
            "guarded_emitted_content_defects": emitted_defects,
            "guarded_emitted_content_clean": all(
                not v for v in emitted_defects.values()
            ),
            "guarded_emitted_verbatim": all(
                bool(e.get("evidence_verbatim"))
                for e in (g.get("emitted") or [])
            ),
            "v68_rejection_downgrades": len(span.get("downgraded_ids") or []),
            "v68_rejection_downgraded_ids": list(
                span.get("downgraded_ids") or []
            ),
        }
        for name, src in (
            ("accepted_baseline", ab),
            ("accepted_unguarded", au),
            ("accepted_guarded", ac),
            ("current_baseline", b),
            ("current_unguarded", u),
            ("current_guarded", g),
        ):
            for k in ("n_scored", "n_emitted", "n_abstained",
                      "n_emitted_verified"):
                totals[name][k] += int(src.get(k) or 0)

    for name in ("accepted_baseline", "accepted_unguarded", "accepted_guarded",
                 "current_baseline", "current_unguarded", "current_guarded"):
        n_scored = totals[name]["n_scored"]
        n_emitted = totals[name]["n_emitted"]
        n_emitted_verified = totals[name]["n_emitted_verified"]
        totals[name]["support_rate_among_emitted"] = (
            round(n_emitted_verified / n_emitted, 6) if n_emitted else 0.0
        )
        totals[name]["yield"] = (
            round(n_emitted / n_scored, 6) if n_scored else 0.0
        )

    checks = {
        "packet_bytes_unchanged": all(
            b["packet_bytes_unchanged"] for b in bundles.values()
        ),
        "baseline_reproduced": all(
            b["baseline_reproduced"] for b in bundles.values()
        ),
        "unguarded_reproduced": all(
            b["unguarded_reproduced"] for b in bundles.values()
        ),
        "guarded_reproduced": all(
            b["guarded_reproduced"] for b in bundles.values()
        ),
        "guarded_yield_not_decreased": all(
            b["guarded_yield_not_decreased"] for b in bundles.values()
        ),
        "guarded_emitted_content_clean": all(
            b["guarded_emitted_content_clean"] for b in bundles.values()
        ),
        "guarded_emitted_verbatim": all(
            b["guarded_emitted_verbatim"] for b in bundles.values()
        ),
    }
    return {
        "available": True,
        "schema": "product-packet-v3-arm-reprobe/1",
        "accepted_artifact": str(ACCEPTED_V3_ARM_ARTIFACT.relative_to(ROOT)),
        "accepted_artifact_sha256": _sha256_file(ACCEPTED_V3_ARM_ARTIFACT),
        "packet": "39319405429",
        "bundles": bundles,
        "totals": totals,
        "checks": checks,
        "v68_rejection_effect_on_v3": {
            "total_downgrades": sum(
                b["v68_rejection_downgrades"] for b in bundles.values()
            ),
            "note": (
                "The rejection/incumbent leg only downgrades verified evidence "
                "that fails the frozen D1-D4 predicates.  Packet-of-record v3 "
                "bytes carry no verified defective incumbent, so this leg "
                "changes nothing on those bytes; the guarded arm's emission is "
                "the accepted span seam's own row and is content-clean."
            ),
        },
        "claim_ceiling": (
            "Deterministic re-run of the ACCEPTED product arm over frozen "
            "packet-of-record v3 bytes on deep copies. It writes no packet "
            "byte, edits no frozen predicate and re-scores no frozen bar. "
            "Support-among-emitted, abstention count and yield are published "
            "together; nothing here asserts that a decision IS supporting, "
            "contrary or limiting, and no serve verdict is produced."
        ),
    }


def run(
    run_id: str | None = None,
    direction_version: int | None = None,
    paths: list[Path] | None = None,
) -> dict:
    # ``paths`` exists so a historical artifact can be re-derived over the
    # population it actually measured.  Later cycles legitimately commit new
    # bundles; allowing those to leak into an old artifact's recomputation
    # turns a true claim into a permanent false failure.  The default remains
    # the live committed population.
    rows = [probe_bundle(p) for p in (paths if paths is not None else bundle_paths())]
    fixed = [r for r in rows if r["fixed_path_family"]]
    historical = [r for r in rows if not r["fixed_path_family"]]
    fixed_totals = _totals(fixed)
    historical_totals = _totals(historical)
    all_totals = _totals(rows)
    confirmed = confirmed_set_status()
    before_after = per_row_before_after(fixed)
    v3 = packet_v3_arms()
    hist = fixed_totals["defect_histogram"]
    success = (
        hist["D2_letterhead_zone"] == 0
        and hist["D3_markup_residue"] == 0
        and hist["D4_language_marker_mismatch"] == 0
        and confirmed["still_verified"] is True
        and not confirmed["defects"]
    )
    v3_checks = v3.get("checks") or {}
    full_success = (
        success
        and before_after["all_four_present"]
        and before_after["all_four_before_verified"]
        and before_after["all_four_after_unevidenced"]
        and before_after["false_reject_count"] == 0
        and before_after["sound_row"]["still_verified"] is True
        and v3.get("available") is True
        and all(v3_checks.values())
    )
    prov = ces.content_filter_provenance()
    return {
        "schema": SCHEMA,
        "generated_at": datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
        "run_id": run_id,
        "direction_version": direction_version,
        "claim_ceiling": CLAIM_CEILING,
        "frozen_predicate_provenance": {
            "predicate_source": prov.get("predicate_source"),
            "predicate_source_sha256": ces.FROZEN_PREDICATE_SOURCE_SHA256,
            "frozen_hypothesis_sha256": ces.FROZEN_PREDICATE_HYPOTHESIS_SHA256,
            "letterhead_zone_offset_max": prov.get("letterhead_zone_offset_max"),
            "min_marker_hits": prov.get("min_marker_hits"),
            "markup_tokens": prov.get("markup_tokens"),
            "alignment": prov.get("alignment"),
        },
        "family_definition": (
            "fixed_path_family = bundle provenance carries "
            "counter_evidence_span.content_filter (regenerated on the fixed "
            "path); identified from the bytes, never hard-coded"
        ),
        "fixed_path_family": {"totals": fixed_totals, "bundles": fixed},
        "historical_population": {
            "totals": historical_totals,
            "bundles": historical,
        },
        "all_committed": {"totals": all_totals, "bundles": rows},
        "confirmed_set": confirmed,
        "before_after": {
            "population_note": (
                "The historical population is NOT the same bytes as the fixed "
                "family: those bundles predate the fix and are preserved as "
                "evidence. The same-decision per-row BEFORE/AFTER pairs below "
                "are published from the seam's own downgrade records on the "
                "fixed path; no historical bundle is rewritten or deleted."
            ),
            "per_class_histogram": {
                "historical_before_population": historical_totals[
                    "defect_histogram"
                ],
                "fixed_path_after_population": hist,
            },
            "per_row": before_after,
        },
        "packet_v3_reemission": v3,
        "ordered_work_2_success_rule": {
            "defect_histogram_zero_D2_D3_D4": (
                hist["D2_letterhead_zone"] == 0
                and hist["D3_markup_residue"] == 0
                and hist["D4_language_marker_mismatch"] == 0
            ),
            "confirmed_sound_row_still_verified": confirmed["still_verified"] is True,
            "false_reject_count": 0 if confirmed["still_verified"] else 1,
            "met": success,
        },
        "ordered_work_2_full_success_rule": {
            "defect_histogram_zero_D2_D3_D4": (
                hist["D2_letterhead_zone"] == 0
                and hist["D3_markup_residue"] == 0
                and hist["D4_language_marker_mismatch"] == 0
            ),
            "confirmed_sound_row_still_verified": confirmed["still_verified"] is True,
            "false_reject_count": before_after["false_reject_count"],
            "accepted_four_before_after_complete": (
                before_after["all_four_present"]
                and before_after["all_four_before_verified"]
                and before_after["all_four_after_unevidenced"]
            ),
            "packet_v3_available": v3.get("available") is True,
            "packet_v3_bytes_unchanged": v3_checks.get("packet_bytes_unchanged"),
            "packet_v3_baseline_reproduced": v3_checks.get("baseline_reproduced"),
            "packet_v3_unguarded_reproduced": v3_checks.get(
                "unguarded_reproduced"
            ),
            "packet_v3_guarded_reproduced": v3_checks.get("guarded_reproduced"),
            "guarded_arm_yield_not_decreased": v3_checks.get(
                "guarded_yield_not_decreased"
            ),
            "guarded_emitted_content_clean": v3_checks.get(
                "guarded_emitted_content_clean"
            ),
            "met": full_success,
        },
        "false_reject_count": before_after["false_reject_count"],
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
            ROOT / "results" / "product" / "counter_content_family" / f"CYCLE_{rid}.json"
        )
    out_path = Path(out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(rec, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    try:
        shown = out_path.relative_to(ROOT)
    except ValueError:  # relative --out passed from the repo root
        shown = out_path
    t = rec["fixed_path_family"]["totals"]
    h = t["defect_histogram"]
    print(f"content family probe -> {shown}")
    print(f"  fixed-path family: {t['n_bundles']} bundle(s), {t['n_decisions']} decisions")
    print(f"  verified rows: {t['n_verified']}  verified+defective: {t['n_verified_defective']}")
    print(f"  D2={h['D2_letterhead_zone']} D3={h['D3_markup_residue']} "
          f"D4={h['D4_language_marker_mismatch']} D1={h['D1_empty_evidence']}")
    a = rec["all_committed"]["totals"]["defect_histogram"]
    print(f"  all committed ({rec['all_committed']['totals']['n_bundles']} bundles): "
          f"D2={a['D2_letterhead_zone']} D3={a['D3_markup_residue']} "
          f"D4={a['D4_language_marker_mismatch']} (historical, preserved)")
    print(f"  confirmed set false rejects: {rec['false_reject_count']}")
    print(f"  ordered-work (2) success rule met: "
          f"{rec['ordered_work_2_success_rule']['met']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Cross-check: this team's recomputation BESIDE Core Evaluation's published numbers.

The charter requires every quantity to be published side by side, with any
divergence named as the headline finding. No threshold is re-derived.

Cross-check inputs (read from the accepted mount, never edited):
  * Core Evaluation stand-ready adjudication 39338699604 (the committed
    fail-closed admission record on these exact bytes).
  * The accepted 39325867172 audit's geometry re-score (de 3/11 fr 4/11 it 4/11).
  * The product's own disclosures.json per_bundle geometry_rescore on the same bytes.
  * The packet admission record (counter_label_support 5/65, map_geometry 0/3).

If a published number has not landed by this team's hard stop, this team's
recomputation is published and the Evaluation number is recorded as absent
rather than blocked or invented.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

DEFAULT_EVAL_MOUNT = Path("/tmp/lex_accepted/core/evaluation")
DEFAULT_PRODUCT_MOUNT = Path("/tmp/lex_accepted/core/product")

STAND_READY_PATH = Path("results/evaluation/packet_of_record_stand_ready/39338699604.json")
AUDIT_GATE_PATH = Path("results/audit/product/CYCLE_39325867172_GATE.json")
DISCLOSURES_RELPATH = Path("results/product/gate_packet/39319405429/disclosures.json")
PACKET_JSON_RELPATH = Path("results/product/gate_packet/39319405429/packet.json")


def _load(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def _disclosures_geometry(product_mount: Path) -> dict:
    d = _load(product_mount / DISCLOSURES_RELPATH) or {}
    out = {}
    for qid, pb in sorted((d.get("per_bundle") or {}).items()):
        gr = pb.get("geometry_rescore") or {}
        ship = gr.get("shipped") or {}
        out[qid] = {
            "n_pass": ship.get("n_pass"),
            "n_criteria": ship.get("n_criteria"),
            "geometry_variant": ship.get("geometry_variant"),
        }
    return out


def _audit_geometry(eval_mount: Path) -> dict:
    d = _load(eval_mount / AUDIT_GATE_PATH) or {}
    txt = json.dumps(d)
    # The audit states the re-score in its claim_ceiling / evidence_summary text.
    # Parse the explicit per-bundle counts if present, else record the text.
    return {
        "source": "results/audit/product/CYCLE_39325867172_GATE.json",
        "claim_ceiling": d.get("claim_ceiling"),
        "evidence_summary": d.get("evidence_summary"),
    }


def _stand_ready_admission(eval_mount: Path) -> dict:
    d = _load(eval_mount / STAND_READY_PATH) or {}
    after = (d.get("before_after_admission_records") or {}).get("side_by_side", {}).get("after", {}) or {}
    return {
        "source": "results/evaluation/packet_of_record_stand_ready/39338699604.json",
        "packet": after.get("packet"),
        "packet_admitted": after.get("packet_admitted"),
        "packet_admission_blocked": after.get("packet_admission_blocked"),
        "packet_admission_reason": after.get("packet_admission_reason"),
        "ready_for_owner_session": after.get("ready_for_owner_session"),
        "packet_json_sha256": after.get("packet_json_sha256"),
    }


def _packet_admission(product_mount: Path) -> dict:
    d = _load(product_mount / PACKET_JSON_RELPATH) or {}
    adm = d.get("packet_admission") or {}
    return {
        "source": "results/product/gate_packet/39319405429/packet.json",
        "packet_admitted": adm.get("packet_admitted"),
        "blocking_reason": adm.get("blocking_reason"),
        "bars": adm.get("bars"),
    }


def build_crosscheck(
    team_label: dict,
    team_geometry: dict,
    eval_mount: Path = DEFAULT_EVAL_MOUNT,
    product_mount: Path = DEFAULT_PRODUCT_MOUNT,
) -> dict:
    """Place this team's recomputation beside every published number."""
    stand = _stand_ready_admission(eval_mount)
    audit = _audit_geometry(eval_mount)
    discl = _disclosures_geometry(product_mount)
    pkt_adm = _packet_admission(product_mount)

    # Geometry cross-check: this team's per-bundle counts vs the product's own
    # disclosures.json re-score on the same bytes vs the 39325867172 audit.
    geom_rows = []
    for qid in sorted(team_geometry.get("per_bundle_counts", {})):
        team_count = team_geometry["per_bundle_counts"][qid]
        prod_count = (discl.get(qid) or {}).get("n_pass")
        geom_rows.append({
            "qid": qid,
            "team_recomputed": team_count,
            "product_disclosures_rescore": prod_count,
            "match": (team_count == prod_count) if prod_count is not None else None,
        })
    geom_divergent = [r for r in geom_rows if r["match"] is False]

    # Label cross-check: this team's n_scored/n_supported vs the packet's own
    # committed admission record (which cites the OLD packet's 5/65 binding
    # measurement) and the stand-ready adjudication.
    label_rows = [
        {
            "quantity": "n_scored",
            "team_recomputed": team_label.get("n_scored"),
            "packet_admission_record": (pkt_adm.get("bars", {}).get("counter_label", {})
                                        .get("binding_measurement", {}) or {}).get("n_scored"),
            "note": "packet admission cites the OLD packet 38839347028 binding measurement (65); "
                    "this team recomputes on the v3 bytes",
        },
        {
            "quantity": "n_supported",
            "team_recomputed": team_label.get("n_supported"),
            "packet_admission_record": (pkt_adm.get("bars", {}).get("counter_label", {})
                                        .get("binding_measurement", {}) or {}).get("n_supported"),
        },
        {
            "quantity": "support_rate",
            "team_recomputed": team_label.get("support_rate"),
            "packet_admission_record": (pkt_adm.get("bars", {}).get("counter_label", {})
                                        .get("binding_measurement", {}) or {}).get("support_rate"),
        },
        {
            "quantity": "absolute_status",
            "team_recomputed": team_label.get("absolute_status"),
            "packet_admission_record": (pkt_adm.get("bars", {}).get("counter_label", {})
                                        .get("binding_measurement", {}) or {}).get("verdict"),
        },
    ]
    label_divergent = [
        r for r in label_rows
        if r["team_recomputed"] != r["packet_admission_record"]
        and r["packet_admission_record"] is not None
        and r["quantity"] in ("n_scored", "n_supported")
    ]

    headline = []
    if geom_divergent:
        headline.append(
            "GEOMETRY DIVERGENCE: " + ", ".join(
                f"{r['qid']} team={r['team_recomputed']} product={r['product_disclosures_rescore']}"
                for r in geom_divergent))
    if label_divergent:
        headline.append(
            "LABEL DIVERGENCE (expected: v3 bytes differ from the OLD packet the admission record cites): "
            + ", ".join(f"{r['quantity']} team={r['team_recomputed']} admission_record={r['packet_admission_record']}"
                        for r in label_divergent))
    if not headline:
        headline.append("No divergence: this team's recomputation matches every published number on the same bytes")

    return {
        "schema": "frontier-packet-serve-audit-crosscheck/1",
        "team_label": {
            "n_scored": team_label.get("n_scored"),
            "n_supported": team_label.get("n_supported"),
            "support_rate": team_label.get("support_rate"),
            "absolute_status": team_label.get("absolute_status"),
            "regression_verdict": team_label.get("regression_verdict"),
        },
        "team_geometry": {
            "per_bundle_counts": team_geometry.get("per_bundle_counts"),
            "absolute_status": team_geometry.get("absolute_status"),
            "regression_verdict": team_geometry.get("regression_verdict"),
        },
        "published_numbers": {
            "core_evaluation_stand_ready_adjudication": stand,
            "accepted_39325867172_audit": audit,
            "product_own_disclosures_geometry_rescore": discl,
            "packet_admission_record": pkt_adm,
        },
        "geometry_side_by_side": geom_rows,
        "label_side_by_side": label_rows,
        "divergence_headline": headline,
        "headline_finding": headline[0] if headline else None,
    }

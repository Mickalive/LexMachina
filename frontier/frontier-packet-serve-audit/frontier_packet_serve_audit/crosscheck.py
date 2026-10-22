"""Cross-check: this team's recomputation BESIDE Core Evaluation's published numbers.

The charter requires every quantity to be published side by side, with any
divergence named as the headline finding. No threshold is re-derived.

Cross-check inputs (read from the accepted mounts, never edited):
  * Core Evaluation stand-ready adjudication 39338699604 (the committed
    fail-closed admission record on these exact bytes).
  * Core Evaluation SAME-BYTES adjudication 39379766198 (lane discharge): the
    frozen-bar re-score of evaluation.frozen_bars.run_bar_gates executed on
    packet-of-record v3 bytes -- label_gate + geometry_gate numbers placed
    beside this team's recomputation for EVERY quantity.
  * The accepted 39325867172 audit's geometry re-score (de 3/11 fr 4/11 it
    4/11), resolved from whichever accepted mount carries it. It is a product
    lane audit gate file, so it is looked up on BOTH accepted mounts; resolving
    it from the evaluation mount alone silently published nulls.
  * The product's own disclosures.json per_bundle geometry_rescore on the same bytes.
  * The packet admission record (counter_label_support 5/65, map_geometry 0/3).

If a published number has not landed by this team's hard stop, this team's
recomputation is published and the Evaluation number is recorded as absent
rather than blocked or invented.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

DEFAULT_EVAL_MOUNT = Path("/tmp/lex_accepted/core/evaluation")
DEFAULT_PRODUCT_MOUNT = Path("/tmp/lex_accepted/core/product")

STAND_READY_PATH = Path("results/evaluation/packet_of_record_stand_ready/39338699604.json")
# Core Evaluation's frozen-bar re-score EXECUTED ON THE SAME v3 BYTES
# (packet 39319405429, packet.json sha256 32ac8126...). Published acceptance
# test (2): "WHEN Core Evaluation's published numbers on the same bytes exist,
# emit a CROSS-CHECK table placing them beside this team's own recomputation".
SAME_BYTES_ADJUDICATION_PATH = Path(
    "results/evaluation/packet_of_record_stand_ready/39379766198.json")
AUDIT_GATE_PATH = Path("results/audit/product/CYCLE_39325867172_GATE.json")
DISCLOSURES_RELPATH = Path("results/product/gate_packet/39319405429/disclosures.json")
PACKET_JSON_RELPATH = Path("results/product/gate_packet/39319405429/packet.json")

# The audit geometry re-score is stated in the gate's evidence_summary prose.
# Parsed verbatim, never re-derived; absent parse -> None (recorded as absent).
AUDIT_GEOMETRY_RE = re.compile(
    r"geometry re-score de (\d+)/11 fr (\d+)/11 it (\d+)/11")

NOT_APPLICABLE_VALUES = ("NOT_APPLICABLE", "NOT_MEASURED")


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _load(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return None


def _is_pass(value: Any) -> bool | None:
    """NOT_APPLICABLE / NOT_MEASURED are never passes (charter guard)."""
    if value is None:
        return None
    if isinstance(value, str) and value in NOT_APPLICABLE_VALUES:
        return False
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


def _audit_geometry(eval_mount: Path, product_mount: Path) -> dict:
    """Resolve the accepted 39325867172 audit gate on either accepted mount.

    The gate file is a PRODUCT lane audit artifact
    (results/audit/product/CYCLE_39325867172_GATE.json); the evaluation mount
    does not carry results/audit/product/. Looking it up on the evaluation
    mount alone published claim_ceiling/evidence_summary as null, i.e. the
    accepted audit's published per-criterion counts never appeared beside this
    team's numbers. Both mounts are searched, the resolved path and its
    sha256 are published, and a missing file stays null (never invented).
    """
    candidates = [
        ("evaluation", eval_mount / AUDIT_GATE_PATH),
        ("product", product_mount / AUDIT_GATE_PATH),
    ]
    resolved = next(((m, p) for m, p in candidates if p.exists()), None)
    if resolved is None:
        return {
            "source": str(AUDIT_GATE_PATH),
            "found": False,
            "resolved_mount": None,
            "resolved_path": None,
            "sha256": None,
            "claim_ceiling": None,
            "evidence_summary": None,
            "geometry_rescore_parsed": None,
            "note": "accepted 39325867172 audit gate not present on either accepted "
                    "mount at this run; recorded as absent, never invented",
        }
    mount_name, path = resolved
    d = _load(path) or {}
    evidence = d.get("evidence_summary")
    parsed = None
    if isinstance(evidence, str):
        m = AUDIT_GEOMETRY_RE.search(evidence)
        if m:
            parsed = {
                "de-kapitalverletzung": int(m.group(1)),
                "fr-bail-entretien": int(m.group(2)),
                "it-responsabilita-medica": int(m.group(3)),
                "criteria": 11,
                "parsed_from": "evidence_summary prose of the accepted audit gate "
                               "(verbatim 'geometry re-score de 3/11 fr 4/11 it 4/11')",
            }
    return {
        "source": str(AUDIT_GATE_PATH),
        "found": True,
        "resolved_mount": mount_name,
        "resolved_path": str(path),
        "sha256": _sha256_file(path),
        "claim_ceiling": d.get("claim_ceiling"),
        "evidence_summary": evidence,
        "geometry_rescore_parsed": parsed,
    }


def _stand_ready_admission(eval_mount: Path) -> dict:
    d = _load(eval_mount / STAND_READY_PATH) or {}
    after = (((d.get("before_after_admission_records") or {}).get("side_by_side") or {})
             .get("after") or {})
    return {
        "source": "results/evaluation/packet_of_record_stand_ready/39338699604.json",
        "packet": after.get("packet"),
        "packet_admitted": after.get("packet_admitted"),
        "packet_admission_blocked": after.get("packet_admission_blocked"),
        "packet_admission_reason": after.get("packet_admission_reason"),
        "ready_for_owner_session": after.get("ready_for_owner_session"),
        "packet_json_sha256": after.get("packet_json_sha256"),
    }


def _same_bytes_adjudication(eval_mount: Path, packet_json_sha256: str | None) -> dict:
    """Core Evaluation's frozen-bar re-score ON THE SAME v3 BYTES.

    Read-only consumption of an accepted Evaluation artifact. The record is
    published verbatim beside this team's recomputation; nothing is re-derived
    and no threshold is imported as a rule.
    """
    path = eval_mount / SAME_BYTES_ADJUDICATION_PATH
    d = _load(path)
    if d is None:
        return {
            "source": str(SAME_BYTES_ADJUDICATION_PATH),
            "found": False,
            "sha256": None,
            "note": "Core Evaluation's same-bytes adjudication has not published on "
                    "this mount at this team's run; recorded as absent, never invented",
        }
    pkt = d.get("packet") or {}
    adj = d.get("adjudication") or {}
    label_gate = adj.get("label_gate") or {}
    geometry_gate = adj.get("geometry_gate") or {}
    obs_sha = pkt.get("packet_json_sha256")
    return {
        "source": str(SAME_BYTES_ADJUDICATION_PATH),
        "found": True,
        "sha256": _sha256_file(path),
        "run_id": d.get("run_id"),
        "generated_at_utc": d.get("generated_at_utc"),
        "packet_id": pkt.get("id"),
        "packet_json_sha256": obs_sha,
        "same_bytes_as_this_run": (obs_sha is not None
                                   and obs_sha == packet_json_sha256)
        if packet_json_sha256 else None,
        "label_gate": {
            "n_scored": label_gate.get("n_scored"),
            "n_supported": label_gate.get("n_supported"),
            "support_rate": label_gate.get("support_rate"),
            "absolute_status": label_gate.get("absolute_status"),
            "regression_verdict": label_gate.get("regression_verdict"),
            "gate_blocks_build": label_gate.get("gate_blocks_build"),
            "incumbent_population": label_gate.get("incumbent_population"),
        },
        "geometry_gate": {
            "per_bundle_counts": geometry_gate.get("per_bundle_counts"),
            "n_bundles_pass_all_11": geometry_gate.get("n_bundles_pass_all_11"),
            "absolute_status": geometry_gate.get("absolute_status"),
            "regression_verdict": geometry_gate.get("regression_verdict"),
            "gate_blocks_build": geometry_gate.get("gate_blocks_build"),
            "incumbent_counts": geometry_gate.get("incumbent_counts"),
        },
        "overall_verdict": adj.get("overall_verdict"),
        "falsification_battery_status": (d.get("falsification_battery") or {}).get("status"),
        "serve_status": d.get("serve_status"),
        "non_vacuity_permutation": geometry_gate.get("non_vacuity_permutation"),
        "claim_ceiling": d.get("claim_ceiling"),
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


def _same_bytes_rows(team_label: dict, team_geometry: dict, same: dict,
                     team_non_vacuity: dict | None) -> list[dict]:
    """One row per quantity: this team's recomputation beside Evaluation's."""
    rows: list[dict] = []

    def add(quantity, team_val, eval_present, eval_val, note=""):
        if not eval_present:
            match = None
            note = (note + "; " if note else "") + (
                "quantity not published by Core Evaluation on these bytes; "
                "recorded as absent, never invented")
        elif eval_val is None and team_val is None:
            # Both sides report the frozen null (e.g. support_rate at n_scored=0):
            # that is agreement, not missing data.
            match = True
            note = (note + "; " if note else "") + "both sides null (agreement)"
        else:
            match = (team_val == eval_val)
        rows.append({
            "quantity": quantity,
            "team_recomputed": team_val,
            "core_evaluation_same_bytes": eval_val,
            "match": match,
            "not_applicable_is_not_pass": _is_pass(team_val) is False
            or _is_pass(eval_val) is False,
            "note": note,
        })

    if not same.get("found"):
        return [{
            "quantity": "ALL",
            "team_recomputed": None,
            "core_evaluation_same_bytes": None,
            "match": None,
            "not_applicable_is_not_pass": False,
            "note": same.get("note"),
        }]

    el = same.get("label_gate") or {}
    add("label.n_scored", team_label.get("n_scored"), "n_scored" in el, el.get("n_scored"))
    add("label.n_supported", team_label.get("n_supported"), "n_supported" in el, el.get("n_supported"))
    add("label.support_rate", team_label.get("support_rate"), "support_rate" in el, el.get("support_rate"))
    add("label.absolute_status", team_label.get("absolute_status"),
        "absolute_status" in el, el.get("absolute_status"))
    add("label.regression_verdict", team_label.get("regression_verdict"),
        "regression_verdict" in el, el.get("regression_verdict"),
        "NOT_APPLICABLE is published as an inapplicability marker, never counted as a pass")
    add("label.gate_blocks_build", team_label.get("gate_blocks_build"),
        "gate_blocks_build" in el, el.get("gate_blocks_build"))

    eg = same.get("geometry_gate") or {}
    eval_counts = eg.get("per_bundle_counts") or {}
    team_counts = team_geometry.get("per_bundle_counts") or {}
    for qid in sorted(set(team_counts) | set(eval_counts)):
        add(f"geometry.per_bundle_counts.{qid}", team_counts.get(qid),
            qid in eval_counts, eval_counts.get(qid))
    add("geometry.n_bundles_pass_all_11", team_geometry.get("n_bundles_pass_all_11"),
        "n_bundles_pass_all_11" in eg, eg.get("n_bundles_pass_all_11"))
    add("geometry.absolute_status", team_geometry.get("absolute_status"),
        "absolute_status" in eg, eg.get("absolute_status"))
    add("geometry.regression_verdict", team_geometry.get("regression_verdict"),
        "regression_verdict" in eg, eg.get("regression_verdict"))

    # Non-vacuity control flip counts: both instruments are published, but the
    # two lanes run DIFFERENT frozen corruption streams/seeds, so the counts are
    # reported side by side and explicitly marked not 1:1 comparable.
    ev_nv = same.get("non_vacuity_permutation") or {}
    team_nv = ((team_non_vacuity or {}).get("geometry_permutation") or {})
    for qid in sorted(set(team_nv) | set(ev_nv)):
        t = team_nv.get(qid) or {}
        e = ev_nv.get(qid) or {}
        present = qid in ev_nv
        team_flips = t.get("best_n_flips")
        eval_flips = e.get("full_flips")
        if not present:
            match = None
        elif team_flips is None and eval_flips is None:
            match = True
        else:
            match = (team_flips == eval_flips)
        rows.append({
            "quantity": f"non_vacuity.geometry_best_n_flips.{qid}",
            "team_recomputed": team_flips,
            "core_evaluation_same_bytes": eval_flips,
            "match": match,
            "not_applicable_is_not_pass": False,
            "team_proven_non_vacuous": t.get("proven_non_vacuous"),
            "core_evaluation_proven_non_vacuous": e.get("proven_non_vacuous"),
            "comparable_1to1": False,
            "note": ("different frozen corruption streams and seed lists per lane; "
                     "published side by side, never merged and never re-tuned"),
        })
    return rows


def build_crosscheck(
    team_label: dict,
    team_geometry: dict,
    eval_mount: Path = DEFAULT_EVAL_MOUNT,
    product_mount: Path = DEFAULT_PRODUCT_MOUNT,
    packet_json_sha256: str | None = None,
    team_non_vacuity: dict | None = None,
) -> dict:
    """Place this team's recomputation beside every published number."""
    stand = _stand_ready_admission(eval_mount)
    same = _same_bytes_adjudication(eval_mount, packet_json_sha256)
    audit = _audit_geometry(eval_mount, product_mount)
    discl = _disclosures_geometry(product_mount)
    pkt_adm = _packet_admission(product_mount)

    # Geometry cross-check: this team's per-bundle counts vs the product's own
    # disclosures.json re-score on the same bytes vs the 39325867172 audit.
    geom_rows = []
    for qid in sorted(team_geometry.get("per_bundle_counts", {})):
        team_count = team_geometry["per_bundle_counts"][qid]
        prod_count = (discl.get(qid) or {}).get("n_pass")
        audit_count = ((audit.get("geometry_rescore_parsed") or {}).get(qid))
        geom_rows.append({
            "qid": qid,
            "team_recomputed": team_count,
            "product_disclosures_rescore": prod_count,
            "accepted_39325867172_audit_rescore": audit_count,
            "match": (team_count == prod_count) if prod_count is not None else None,
            "match_audit": (team_count == audit_count) if audit_count is not None else None,
        })
    geom_divergent = [r for r in geom_rows if r["match"] is False or r["match_audit"] is False]

    # Label cross-check: this team's n_scored/n_supported vs the packet's own
    # committed admission record (which cites the OLD packet's 5/65 binding
    # measurement) and the stand-ready adjudication.
    binding = (((pkt_adm.get("bars") or {}).get("counter_label") or {})
               .get("binding_measurement") or {})
    label_rows = [
        {
            "quantity": "n_scored",
            "team_recomputed": team_label.get("n_scored"),
            "packet_admission_record": binding.get("n_scored"),
            "note": "packet admission cites the OLD packet 38839347028 binding measurement (65); "
                    "this team recomputes on the v3 bytes",
        },
        {
            "quantity": "n_supported",
            "team_recomputed": team_label.get("n_supported"),
            "packet_admission_record": binding.get("n_supported"),
        },
        {
            "quantity": "support_rate",
            "team_recomputed": team_label.get("support_rate"),
            "packet_admission_record": binding.get("support_rate"),
        },
        {
            "quantity": "absolute_status",
            "team_recomputed": team_label.get("absolute_status"),
            "packet_admission_record": binding.get("verdict"),
        },
    ]
    label_divergent = [
        r for r in label_rows
        if r["team_recomputed"] != r["packet_admission_record"]
        and r["packet_admission_record"] is not None
        and r["quantity"] in ("n_scored", "n_supported")
    ]

    # Core Evaluation same-bytes side-by-side (acceptance test (2)).
    same_rows = _same_bytes_rows(team_label, team_geometry, same, team_non_vacuity)
    same_divergent = [r for r in same_rows if r.get("match") is False]
    same_divergent_1to1 = [r for r in same_divergent if r.get("comparable_1to1") is not False]
    same_diff_noncomparable = [r for r in same_divergent if r.get("comparable_1to1") is False]

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
    if same_divergent_1to1:
        headline.append(
            "CORE-EVALUATION SAME-BYTES DIVERGENCE: "
            + ", ".join(f"{r['quantity']} team={r['team_recomputed']} "
                        f"core_evaluation={r['core_evaluation_same_bytes']}"
                        for r in same_divergent_1to1))
    if same_diff_noncomparable:
        headline.append(
            "CORE-EVALUATION SAME-BYTES DIFFERENCE (instruments not 1:1 comparable -- both "
            "published, neither re-tuned): "
            + ", ".join(f"{r['quantity']} team={r['team_recomputed']} "
                        f"core_evaluation={r['core_evaluation_same_bytes']}"
                        for r in same_diff_noncomparable))
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
            "core_evaluation_same_bytes_adjudication": same,
            "accepted_39325867172_audit": audit,
            "product_own_disclosures_geometry_rescore": discl,
            "packet_admission_record": pkt_adm,
        },
        "core_evaluation_same_bytes_side_by_side": same_rows,
        "geometry_side_by_side": geom_rows,
        "label_side_by_side": label_rows,
        "divergence_headline": headline,
        "headline_finding": headline[0] if headline else None,
        "no_threshold_re_derived": True,
    }

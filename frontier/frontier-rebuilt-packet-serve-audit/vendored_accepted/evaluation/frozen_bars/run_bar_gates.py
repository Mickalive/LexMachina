"""Single entry point: run both frozen-bar gates (stdlib only, no network).

Two modes, one set of frozen rules, incumbents and predicates:

* served_lineage (default): verifies both RULES sha256, verifies the three
  served bundle shas against the accepted LABEL_HALF inputs BEFORE scoring,
  re-scores the served packet, checks regression against the recomputed
  incumbents, runs the proven negative controls, and writes one
  self-contained record.
* adjudicate (--adjudicate <packet-dir>): scores a FUTURE packet on the same
  three frozen qids with the same frozen rules/incumbents/predicates. The
  served-bytes identity pin is a served-lineage provenance check, not a
  threshold, so it is not applied; observed shas are recorded instead. See
  evaluation/frozen_bars/VERDICT_CONTRACT.json for what each verdict state
  does and does NOT certify before consuming an exit 0 as a pass.

Exit 0 = gates executed; no REGRESSION below incumbent (absolute-bar status
is reported, never enforced). Exit 1 = REGRESSION below incumbent on the
scored packet (unreachable through served_lineage mode on any input — served
bytes recompute the incumbent by construction and any drift exits 2 first;
reachable through adjudicate mode). Exit 2 = environment error (missing
inputs, sha mismatch, unknown qid, engine/oracle divergence, unproven
negative control) — never a product verdict, never a pass.

No Product code is imported. No frozen benchmark is touched.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
import time
from pathlib import Path

_BAR_DIR = Path(__file__).resolve().parent
if str(_BAR_DIR.parent.parent) not in sys.path:
    sys.path.insert(0, str(_BAR_DIR.parent.parent))

from evaluation.frozen_bars import geometry_gate, label_gate, verdict_contract  # noqa: E402

SERVED_PACKET_DIR = Path(
    "/tmp/lex_accepted/product/results/product/gate_packet/38839347028/questions"
)
QIDS = ("de-kapitalverletzung", "fr-bail-entretien", "it-responsabilita-medica")

# Served-bundle input identity, as recorded in the accepted LABEL_HALF.json.
EXPECTED_BUNDLE_SHA256 = {
    "de-kapitalverletzung": "2441ff2b16722afcd22dca9ad39eafcbeb079b2dfc367d763fbe53fce1356f9c",
    "fr-bail-entretien": "6c5ea31d4b9af4abfa39e9f8025cfa3d34279ff1f04d0f643e571e27b23a2618",
    "it-responsabilita-medica": "76e7f7ad998f3878e7b08635663e2d594a7a77bdaeb33bcf5fa52d0af00b7aff",
}

# Accepted GEOMETRY_HALF.json per-criterion pass/fail oracle (33 cells).
EXPECTED_GEOMETRY_PASSES = {
    "de-kapitalverletzung": {"COHERENCE_QUERY_LANG": True, "COHERENCE_QUERY_TERM": False,
                             "PROJ_RANK": False, "PROJ_SPEARMAN": False, "PROJ_KNN10": False,
                             "STRUCTURE_LARGEST": True, "STRUCTURE_SEP": False,
                             "LABEL_CONTENT_FRACTION": True, "LABEL_JACCARD": True,
                             "OUTLIER_VALIDITY": True, "RELATIONS": True},
    "fr-bail-entretien": {"COHERENCE_QUERY_LANG": False, "COHERENCE_QUERY_TERM": False,
                          "PROJ_RANK": True, "PROJ_SPEARMAN": False, "PROJ_KNN10": False,
                          "STRUCTURE_LARGEST": False, "STRUCTURE_SEP": False,
                          "LABEL_CONTENT_FRACTION": True, "LABEL_JACCARD": True,
                          "OUTLIER_VALIDITY": True, "RELATIONS": True},
    "it-responsabilita-medica": {"COHERENCE_QUERY_LANG": False, "COHERENCE_QUERY_TERM": False,
                                 "PROJ_RANK": True, "PROJ_SPEARMAN": False, "PROJ_KNN10": False,
                                 "STRUCTURE_LARGEST": True, "STRUCTURE_SEP": False,
                                 "LABEL_CONTENT_FRACTION": True, "LABEL_JACCARD": True,
                                 "OUTLIER_VALIDITY": False, "RELATIONS": True},
}


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _blank_label_evidence(bundle: dict) -> dict:
    """Lineage-matched regressed input: every scored row loses its evidence."""
    b = copy.deepcopy(bundle)
    scored = {"candidate-limiting", "candidate-contrary", "contrary_or_exception", "limiting"}
    for d in b.get("decisions", []):
        if d.get("counter_status") in scored:
            d["counter_evidence"] = ""
    return b


def _hostile_geometry(bundle: dict) -> dict:
    """Lineage-matched regressed input: one stopword-labelled mega-cluster,
    no relations, no outlier flags. Must score strictly below the incumbent
    on the served-packet lineage (proven: de 6->4, fr 5->4)."""
    b = copy.deepcopy(bundle)
    decs = b.get("decisions", [])
    for d in decs:
        d["cluster_id"] = 0
        d["is_outlier"] = False
    b["clusters"] = [{"cluster_id": 0, "label": "der und die",
                      "member_ids": [d.get("decision_id") for d in decs][:50],
                      "size": len(decs)}]
    b["relations"] = []
    return b


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--packet-dir", default=str(SERVED_PACKET_DIR))
    ap.add_argument("--adjudicate", default=None, metavar="PACKET_DIR",
                    help="adjudicate a FUTURE packet on the three frozen qids with the same "
                         "frozen rules/incumbents/predicates, WITHOUT the served-bytes identity "
                         "pin (that pin is a served-lineage provenance check, not a threshold). "
                         "Exit 1 when either gate reports a regression below the accepted "
                         "incumbent; exit 2 on environment/unknown-qid errors; exit 0 otherwise. "
                         "See evaluation/frozen_bars/VERDICT_CONTRACT.json before consuming "
                         "an exit 0 as a pass.")
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)
    t0 = time.time()
    mode = "adjudicate" if args.adjudicate else "served_lineage"
    packet_dir = Path(args.adjudicate) if args.adjudicate else Path(args.packet_dir)
    missing = [f"{qid}.bundle.json" for qid in QIDS if not (packet_dir / f"{qid}.bundle.json").exists()]
    if missing:
        print(f"bar_gates environment error: missing inputs in {packet_dir}: {missing}", file=sys.stderr)
        return 2
    try:
        label_rules = label_gate.load_frozen_rules()
        geometry_rules = geometry_gate.load_frozen_geometry_rules()
    except RuntimeError as e:
        print(f"bar_gates environment error: {e}", file=sys.stderr)
        return 2

    record: dict = {
        "schema": "lex-evaluation-frozen-bar-gates/1",
        "rules_label_sha256": label_rules.sha256,
        "rules_geometry_sha256": geometry_gate.EXPECTED_RULES_SHA256,
        "packet_dir": str(packet_dir),
    }

    # ---- input identity -------------------------------------------------
    bundle_paths = {qid: packet_dir / f"{qid}.bundle.json" for qid in QIDS}
    observed_shas = {qid: _sha256_file(p) for qid, p in bundle_paths.items()}
    sha_match = {qid: observed_shas[qid] == EXPECTED_BUNDLE_SHA256[qid] for qid in QIDS}
    record["input_bundle_sha256"] = observed_shas
    record["input_sha_matches_accepted_label_half"] = sha_match
    if mode == "served_lineage" and not all(sha_match.values()):
        record["verdict"] = "ENVIRONMENT_ERROR"
        record["detail"] = "served bundle bytes drifted from the accepted LABEL_HALF inputs; refusing verdict"
        print(json.dumps(record, indent=1))
        if args.out:
            Path(args.out).write_text(json.dumps(record, indent=1), encoding="utf-8")
        return 2
    if mode == "adjudicate":
        # Disclosed scope difference only: the served-bytes pin is a
        # provenance check on the HISTORICAL packet, not a threshold, so it
        # is not applied to a future packet. Observed shas stay in the record.
        record["mode"] = "adjudicate"
        record["served_byte_pin"] = "not_applicable_in_adjudicate_mode"
        record["engine_oracle_check"] = "served_lineage_only"


    # ---- label gate ------------------------------------------------------
    label_paths = {qid: str(p) for qid, p in bundle_paths.items()}
    label_res = label_gate.score_packet(label_paths, label_rules)
    label_nv = label_gate.non_vacuity_control(label_rules)
    # lineage-matched negative control: blanked evidence must FAIL regression
    blank_paths: dict[str, str] = {}
    label_neg_detail: dict = {}
    try:
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            for qid, p in bundle_paths.items():
                b = json.loads(p.read_text(encoding="utf-8"))
                bp = Path(tmp) / f"{qid}.bundle.json"
                bp.write_text(json.dumps(_blank_label_evidence(b)), encoding="utf-8")
                blank_paths[qid] = str(bp)
            label_neg = label_gate.score_packet(blank_paths, label_rules)
        label_neg_detail = {"n_scored": label_neg["n_scored"],
                            "n_supported": label_neg["n_supported"],
                            "regression_verdict": label_neg["regression_verdict"],
                            "gate_blocks_build": label_neg["gate_blocks_build"]}
        label_neg_proven = bool(label_neg["gate_blocks_build"])
        if label_neg["regression_verdict"] == "NOT_APPLICABLE":
            # Frozen label regression predicate is population-pinned; outside
            # the 65-row incumbent population the control cannot fire and is
            # recorded as not-applicable, never silently dropped.
            label_neg_detail["not_applicable_reason"] = (
                "label regression predicate is pinned to the 65-row incumbent population; "
                "this control cannot fire on the adjudicated packet's population")
    except Exception as e:  # noqa: BLE001 -- negative control must report, never crash the gate
        label_neg_detail = {"error": f"{type(e).__name__}: {e}"}
        label_neg_proven = False
    record["label_gate"] = {
        "n_scored": label_res["n_scored"],
        "n_supported": label_res["n_supported"],
        "support_rate": label_res["support_rate"],
        "classes": label_res["classes"],
        "incumbent": label_res["incumbent"],
        "recomputed_matches_incumbent": (
            label_res["n_scored"] == label_gate.INCUMBENT["n_scored"]
            and label_res["n_supported"] == label_gate.INCUMBENT["n_supported"]
            and all(label_res["classes"].get(k, 0) == v
                    for k, v in label_gate.INCUMBENT["classes"].items())),
        "absolute_status": label_res["absolute_status"],
        "absolute_enforced": False,
        "regression_verdict": label_res["regression_verdict"],
        "gate_blocks_build": label_res["gate_blocks_build"],
        "non_vacuity_injection": {"n_cases": label_nv["n_cases"],
                                  "n_cases_pass": label_nv["n_cases_pass"],
                                  "proven_non_vacuous": label_nv["proven_non_vacuous"]},
        "negative_control_blanked_evidence": label_neg_detail,
        "negative_control_proven": label_neg_proven,
    }

    # ---- geometry gate ---------------------------------------------------
    bundles = {qid: json.loads(p.read_text(encoding="utf-8")) for qid, p in bundle_paths.items()}
    geom_res = geometry_gate.score_packet(bundles, geometry_rules)
    oracle_cells = sum(1 for _ in QIDS for _ in geometry_gate.CRITERIA_ORDER)
    oracle_match_cells = sum(
        1 for qid in QIDS for c in geometry_gate.CRITERIA_ORDER
        if geom_res["per_bundle"][qid]["criteria"][c]["pass"] == EXPECTED_GEOMETRY_PASSES[qid][c])
    geom_nv = {qid: geometry_gate.non_vacuity_control(
        bundles[qid],
        [e for e in geometry_rules["inputs"] if e["bundle"] == qid][0]["query_language"],
        geometry_rules["query_term_lexicons"][qid]) for qid in QIDS}
    geom_bundles_reg = {qid: _hostile_geometry(b) for qid, b in bundles.items()}
    geom_neg = geometry_gate.score_packet(geom_bundles_reg, geometry_rules)
    record["geometry_gate"] = {
        "per_bundle_counts": geom_res["per_bundle_counts"],
        "incumbent_counts": geom_res["incumbent_counts"],
        "recomputed_counts_match_incumbent": (
            geom_res["per_bundle_counts"] == geometry_gate.INCUMBENT_COUNTS),
        "engine_oracle_verdict_cells_match": f"{oracle_match_cells}/{oracle_cells}",
        "engine_oracle_diverged": oracle_match_cells != oracle_cells,
        "absolute_status": geom_res["absolute_status"],
        "n_bundles_pass_all_11": geom_res["n_bundles_pass_all_11"],
        "absolute_enforced": False,
        "regression_verdict": geom_res["regression_verdict"],
        "regressed_qids": geom_res["regressed_qids"],
        "gate_blocks_build": geom_res["gate_blocks_build"],
        "non_vacuity_permutation": {
            qid: {"charter_flips": geom_nv[qid]["charter"]["n_flips"],
                  "full_flips": geom_nv[qid]["full"]["n_flips"],
                  "proven_non_vacuous": geom_nv[qid]["proven_non_vacuous"]} for qid in QIDS},
        "negative_control_hostile_geometry": {
            "per_bundle_counts": geom_neg["per_bundle_counts"],
            "regressed_qids": geom_neg["regressed_qids"],
            "regression_verdict": geom_neg["regression_verdict"],
            "gate_blocks_build": geom_neg["gate_blocks_build"]},
        "negative_control_proven": bool(geom_neg["gate_blocks_build"]),
    }
    if mode == "served_lineage" and oracle_match_cells != oracle_cells:
        record["verdict"] = "ENVIRONMENT_ERROR"
        record["detail"] = ("stdlib geometry engine diverged from the accepted GEOMETRY_HALF "
                            "oracle; refusing verdict (engine fidelity gate, not a product verdict)")
        print(json.dumps(record, indent=1)[:2000])
        if args.out:
            Path(args.out).write_text(json.dumps(record, indent=1), encoding="utf-8")
        return 2
    if mode == "adjudicate":
        # The 33-cell oracle is a served-lineage engine-fidelity check; an
        # adjudicated packet legitimately differs cell-by-cell. Engine
        # fidelity is established once per execution by the default-mode run.
        record["engine_oracle_cells_observed"] = f"{oracle_match_cells}/{oracle_cells}"

    # ---- overall ----------------------------------------------------------
    regressed = bool(label_res["gate_blocks_build"] or geom_res["gate_blocks_build"])
    label_neg_required = bool(mode == "served_lineage"
                              or label_neg_detail.get("regression_verdict") != "NOT_APPLICABLE")
    neg_ok = bool(label_nv["proven_non_vacuous"]
                  and record["geometry_gate"]["negative_control_proven"]
                  and (record["label_gate"]["negative_control_proven"]
                       if label_neg_required else True))
    record["negative_controls_all_proven"] = neg_ok
    if mode == "adjudicate":
        record["label_negative_control_required"] = label_neg_required
        # Machine-readable admission input (Product obligation (1) consumes it):
        # what the observed verdict DOES and DOES NOT certify, per the frozen
        # contract. Policy stays with the consumer; misreadings do not.
        record["admission_reading"] = verdict_contract.admission_reading(
            label_res, geom_res, 1 if regressed else 0)
    record["verdict"] = "FAIL_REGRESSION" if regressed else "PASS_NO_REGRESSION"
    record["absolute_status_summary"] = {
        "labels": label_res["absolute_status"],
        "geometry": geom_res["absolute_status"],
        "note": "absolute bars REPORTED only; they do not block the build (direction v50)"}
    record["elapsed_s"] = round(time.time() - t0, 3)
    print(json.dumps({k: v for k, v in record.items()
                      if k not in ("label_gate", "geometry_gate")}, indent=1))
    if args.out:
        Path(args.out).write_text(json.dumps(record, indent=1), encoding="utf-8")
    if not neg_ok:
        return 2
    return 1 if regressed else 0


if __name__ == "__main__":
    raise SystemExit(main())

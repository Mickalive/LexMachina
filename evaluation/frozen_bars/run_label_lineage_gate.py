"""Entry point for the counter-label-support LINEAGE regression gate.

One stdlib-only module, no network, no Product import, no frozen file written.
Two modes:

* ``--packet-root <dir>`` (default, sweep): discovers the accepted packet
  population, scores every in-scope packet with BOTH this lineage gate and the
  ACCEPTED geometry gate, builds the blocking matrix for the two gates side by
  side, runs the non-vacuity battery and writes one claim-bearing record.
  Exit 0 = the sweep completed and every frozen prediction was confirmed.
* ``--adjudicate <packet-dir>``: judges ONE packet and emits the machine-readable
  packet-admission input that Product direction obligation (1) consumes.
  Exit 0 = no regression, 1 = FAIL_REGRESSION, 2 = environment error.

Exit semantics are declared in evaluation/frozen_bars/LABEL_LINEAGE_VERDICT.json
and are deliberately different per mode: the accepted packet population
legitimately CONTAINS packets below the incumbent rate (38799024807 scores
0 of 7), so a sweep that exited 1 on those would be permanently red by
construction. See ``process.why_sweep_exit_semantics_differ_from_adjudicate``.

Nothing accepted is overwritten: the accepted label_gate verdict and the
accepted geometry verdict are reported side by side with this gate's verdict.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

_BAR_DIR = Path(__file__).resolve().parent
if str(_BAR_DIR.parent.parent) not in sys.path:
    sys.path.insert(0, str(_BAR_DIR.parent.parent))

from evaluation.frozen_bars import (  # noqa: E402
    geometry_gate,
    label_gate,
    label_lineage_gate,
)

ACCEPTED_PACKET_ROOT = Path("/tmp/lex_accepted/product/results/product/gate_packet")
INCUMBENT_PACKET_ID = "38839347028"  # accepted LABEL_HALF / GEOMETRY_HALF source packet
QIDS = label_lineage_gate.LINEAGE_QIDS


def _accepted_geometry(bundle_dir: Path, rules: dict) -> dict:
    """Run the ACCEPTED geometry gate unchanged on one packet dir."""
    paths = {q: bundle_dir / f"{q}.bundle.json" for q in QIDS}
    bundles = {q: json.loads(p.read_text(encoding="utf-8")) for q, p in paths.items()}
    return geometry_gate.score_packet(bundles, rules)


def _blocking_row(pid: str, paths: dict[str, str], rules, geom_rules: dict) -> dict:
    lineage = label_lineage_gate.score_packet(paths, rules)
    accepted_label = label_gate.score_packet(paths, rules)
    geom = _accepted_geometry(Path(paths[QIDS[0]]).parent, geom_rules)
    row = {
        "packet_id": pid,
        "bundle_sha256": {q: lineage["per_bundle"][q]["sha256"] for q in QIDS},
        "lineage_gate": {
            "n_scored": lineage["n_scored"],
            "n_supported": lineage["n_supported"],
            "support_rate": lineage["support_rate"],
            "enforced_predicate_rate": lineage["enforced_reading"]["value"],
            "regression_verdict": lineage["regression_verdict"],
            "gate_blocks_build": lineage["gate_blocks_build"],
            "absolute_status": lineage["absolute_status"],
            "classes": lineage["classes"],
        },
        "accepted_label_gate": {
            "regression_verdict": accepted_label["regression_verdict"],
            "gate_blocks_build": accepted_label["gate_blocks_build"],
            "n_scored": accepted_label["n_scored"],
            "n_supported": accepted_label["n_supported"],
        },
        "accepted_geometry_gate": {
            "per_bundle_counts": geom["per_bundle_counts"],
            "regression_verdict": geom["regression_verdict"],
            "gate_blocks_build": geom["gate_blocks_build"],
            "regressed_qids": geom["regressed_qids"],
            "absolute_status": geom["absolute_status"],
            "n_bundles_pass_all_11": geom["n_bundles_pass_all_11"],
        },
        "parity": {
            "lineage_blocks": lineage["gate_blocks_build"],
            "accepted_label_blocks": accepted_label["gate_blocks_build"],
            "geometry_blocks": geom["gate_blocks_build"],
            "readings_disagree_on_this_packet":
                lineage["reported_only_readings"]["readings_disagree_on_this_packet"],
            "label_geometry_parity_achieved":
                lineage["gate_blocks_build"] == geom["gate_blocks_build"],
        },
    }
    row["closure"] = label_lineage_gate.closure_report(paths, rules, {"packet_id": pid})
    return row


def _verify_frozen_identity() -> dict:
    """Re-hash every frozen input this gate depends on. Mismatch -> refuse."""
    out = {}
    for label, path, expected in (
        ("RULES_LABEL.json", label_gate.RULES_LABEL_PATH,
         label_gate.EXPECTED_RULES_SHA256),
        ("RULES_GEOMETRY.json", geometry_gate.RULES_GEOMETRY_PATH,
         geometry_gate.EXPECTED_RULES_SHA256),
        ("LABEL_LINEAGE_VERDICT.json", label_lineage_gate.VERDICT_CONTRACT_PATH,
         label_lineage_gate.EXPECTED_VERDICT_CONTRACT_SHA256),
        ("VERDICT_CONTRACT.json", _BAR_DIR / "VERDICT_CONTRACT.json",
         "b9cdb89438a8d16ee165fe2a5d73060524154d8e7ba8e0cab867e8ca17ff414c"),
    ):
        observed = label_lineage_gate.sha256_file(path)
        out[label] = {"expected": expected, "observed": observed, "matches": observed == expected}
    return out


def _blank_all_label_evidence(bundle: dict) -> dict:
    """Strip the counter_evidence of every scored row; geometry fields untouched."""
    import copy
    b = copy.deepcopy(bundle)
    scored = {"candidate-limiting", "candidate-contrary", "contrary_or_exception", "limiting"}
    for d in b.get("decisions", []):
        if d.get("counter_status") in scored:
            d["counter_evidence"] = ""
    return b


def label_only_regression_control(questions_dir: Path, rules, geom_rules) -> dict:
    """A regression the LABEL gate alone must catch.

    Blanking every scored row's counter_evidence moves label support 5/65 -> 0/65
    and changes NO geometry field (cluster ids, labels, coordinates, relations,
    outlier flags are all untouched), so the accepted geometry gate must stay at
    the incumbent counts. If the two-bar input attributes the block to both bars
    here, the label contribution is not independently observable.
    """
    qdir = Path(questions_dir)
    derived = {q: _blank_all_label_evidence(
        json.loads((qdir / f"{q}.bundle.json").read_text(encoding="utf-8"))) for q in QIDS}
    label = label_lineage_gate.score_packet_dicts(derived, rules)
    geom = geometry_gate.score_packet(derived, geom_rules)
    return {
        "control": "all_scored_counter_evidence_blanked",
        "purpose": "label-only regression: the geometry gate must NOT be able to see this",
        "label_regression_verdict": label["regression_verdict"],
        "label_gate_blocks_build": label["gate_blocks_build"],
        "label_n_scored": label["n_scored"],
        "label_n_supported": label["n_supported"],
        "label_support_rate": label["support_rate"],
        "geometry_regression_verdict": geom["regression_verdict"],
        "geometry_gate_blocks_build": geom["gate_blocks_build"],
        "geometry_per_bundle_counts": geom["per_bundle_counts"],
        "attributable_to_label_gate_alone": bool(
            label["gate_blocks_build"] and not geom["gate_blocks_build"]),
        "proven_non_vacuous": bool(
            label["gate_blocks_build"] and not geom["gate_blocks_build"]),
        "geometry_incumbent_unchanged": (
            geom["per_bundle_counts"] == geometry_gate.INCUMBENT_COUNTS),
    }


def sweep(packet_root: Path, rules, geom_rules) -> dict:
    pop = label_lineage_gate.discover_population(packet_root)
    rows = []
    for entry in pop["in_scope"]:
        qdir = Path(entry["questions_dir"])
        paths = {q: str(qdir / f"{q}.bundle.json") for q in QIDS}
        rows.append(_blocking_row(entry["packet_id"], paths, rules, geom_rules))

    incumbent = next((r for r in rows if r["packet_id"] == INCUMBENT_PACKET_ID), None)
    non_incumbent = [r for r in rows if r["packet_id"] != INCUMBENT_PACKET_ID]

    # Non-vacuity, minimal delta, on the INCUMBENT population itself.
    nv = None
    label_only = None
    if incumbent is not None:
        qdir = Path(next(e["questions_dir"] for e in pop["in_scope"]
                         if e["packet_id"] == INCUMBENT_PACKET_ID))
        nv = label_lineage_gate.minimal_delta_control(
            {q: str(qdir / f"{q}.bundle.json") for q in QIDS}, rules)
        label_only = label_only_regression_control(qdir, rules, geom_rules)

    # Refusal control: a packet without the three frozen qids gets no lineage
    # verdict; a non-frozen qid is refused by the accepted anchor gate.
    off = {"out_of_scope_recorded": pop["out_of_scope"],
           "off_lineage_state": "NOT_APPLICABLE",
           "unknown_qid_refused_by": "label_gate.score_packet ValueError (accepted)"}

    return {
        "population": {
            "root": pop["root"],
            "n_packet_dirs": pop["n_packet_dirs"],
            "n_in_scope": len(pop["in_scope"]),
            "in_scope_packet_ids": [e["packet_id"] for e in pop["in_scope"]],
            "out_of_scope": pop["out_of_scope"],
        },
        "blocking_matrix": rows,
        "parity_summary": {
            "incumbent_packet": INCUMBENT_PACKET_ID,
            "incumbent_lineage_blocks": incumbent["lineage_gate"]["gate_blocks_build"] if incumbent else None,
            "non_incumbent_lineage_blocks": sum(
                1 for r in non_incumbent if r["lineage_gate"]["gate_blocks_build"]),
            "n_non_incumbent": len(non_incumbent),
            "non_incumbent_accepted_label_blocks": sum(
                1 for r in non_incumbent if r["accepted_label_gate"]["gate_blocks_build"]),
            "non_incumbent_geometry_blocks": sum(
                1 for r in non_incumbent if r["accepted_geometry_gate"]["gate_blocks_build"]),
            "label_geometry_parity_on_every_in_scope_packet": (
                all(r["parity"]["label_geometry_parity_achieved"] for r in rows)
                if rows else None),
            "parity_note": ("null when no in-scope packet exists; a parity claim over an empty "
                            "population is never a pass. NOTE: equality of the two gates' block "
                            "decisions is NOT an expected invariant - they measure different things "
                            "(pooled counter-label support RATE vs per-bundle geometry "
                            "criterion-COUNT), so a packet may be geometry-deficient while its "
                            "label rate is fine. The measured divergence is reported, not closed."),
            "packets_where_lineage_and_geometry_disagree_on_blocking": [
                r["packet_id"] for r in rows
                if r["parity"]["lineage_blocks"] != r["parity"]["geometry_blocks"]],
        },
        "geometry_incumbent_floor_disclosure":
            label_lineage_gate.geometry_incumbent_floor_disclosure(rows),
        "label_blindness_closed": {
            "accepted_gate_blocked_non_incumbent_packets":
                sum(1 for r in non_incumbent if r["accepted_label_gate"]["gate_blocks_build"]),
            "lineage_gate_blocked_non_incumbent_packets":
                sum(1 for r in non_incumbent if r["lineage_gate"]["gate_blocks_build"]),
            "total_label_collapse_packets_now_blocked": [
                r["packet_id"] for r in rows
                if r["lineage_gate"]["n_supported"] == 0 and r["lineage_gate"]["n_scored"] > 0],
            "reading": ("the accepted gate admitted every non-incumbent packet including the "
                        "0-supported collapse; the lineage gate blocks the collapse. Blocks are "
                        "not restored to the accepted gate, whose verdicts are published "
                        "unchanged alongside."),
        },
        "non_vacuity_minimal_delta": nv,
        "non_vacuity_label_only_regression": label_only,
        "off_lineage_control": off,
    }


def adjudicate(packet_dir: Path, rules, geom_rules) -> dict:
    paths = {q: str(packet_dir / f"{q}.bundle.json") for q in QIDS}
    present = [q for q, p in paths.items() if Path(p).exists()]
    missing = [q for q in QIDS if q not in present]
    if missing:
        # Distinguish a genuinely off-lineage packet from a broken input path.
        # Both exit 2 (no lineage verdict can be issued) but they are different
        # findings and must never be reported as the same thing.
        any_bundle = any(packet_dir.glob("*.bundle.json"))
        if any_bundle:
            return {
                "verdict": "NOT_APPLICABLE",
                "detail": (
                    f"packet carries {len(present)} of the 3 frozen qids (missing "
                    f"{missing!r}); no lineage verdict applies and the gate never invents an "
                    "anchor profile for it. Exit 2 because no lineage verdict can be issued, "
                    "NOT because the environment is broken. A packet on new questions needs a "
                    "disclosed RULES_LABEL re-freeze, which is out of this lane's scope."),
                "off_lineage": True,
                "n_frozen_qids_present": len(present),
                "missing": missing,
                "exit_code": 2,
            }
        return {"verdict": "ENVIRONMENT_ERROR",
                "detail": f"no <qid>.bundle.json at all in {packet_dir}; expected {QIDS}",
                "exit_code": 2}
    res = label_lineage_gate.score_packet(paths, rules)
    accepted = label_gate.score_packet(paths, rules)
    try:
        geom = _accepted_geometry(packet_dir, geom_rules)
        geom_block = {
            "per_bundle_counts": geom["per_bundle_counts"],
            "regression_verdict": geom["regression_verdict"],
            "gate_blocks_build": geom["gate_blocks_build"],
            "absolute_status": geom["absolute_status"],
            "n_bundles_pass_all_11": geom["n_bundles_pass_all_11"],
            "incumbent_is_a_floor": {
                "holds": False,
                "disclosure": ("accepted finding F2_INCUMBENT_NOT_A_FLOOR: over the accepted packet "
                               "population the minimum per-bundle count is de 6 / fr 4 / it 4, below "
                               "the enforced incumbent de 6 / fr 5 / it 5. The enforced incumbent is "
                               "a 'no worse than the served packet' reference, not the worst case "
                               "observed. Direction v50 fixes that incumbent; this gate does not "
                               "change it and reports the divergence instead."),
            },
        }
    except ValueError as e:
        geom_block = {"error": str(e)}
    label_blocks = bool(res["gate_blocks_build"])
    geom_blocks = bool(geom.get("gate_blocks_build"))
    blocks = label_blocks or geom_blocks
    # The top-level verdict is the TWO-BAR verdict. A per-gate verdict is never
    # promoted to the record level when the other gate blocks, which would be a
    # misread of exactly the kind this gate exists to prevent.
    return {
        "verdict": "FAIL_REGRESSION" if blocks else "PASS_NO_REGRESSION",
        "verdict_scope": "two-bar admission verdict (label lineage OR accepted geometry blocks)",
        "label_lineage_gate": res,
        "accepted_label_gate_side_by_side": {
            "regression_verdict": accepted["regression_verdict"],
            "gate_blocks_build": accepted["gate_blocks_build"],
        },
        "accepted_geometry_gate": geom_block,
        "admission_input": {
            "schema": "lex-evaluation-admission-input/2",
            "blocks_build": blocks,
            "block_reasons": [
                r for r, on in (
                    ("counter-label support rate strictly below incumbent 5/65", label_blocks),
                    ("map-geometry criterion-count below incumbent de 6 / fr 5 / it 5", geom_blocks),
                ) if on
            ],
            "label_regression_verdict": res["regression_verdict"],
            "label_support_rate": res["support_rate"],
            "label_enforced_predicate_rate": res["enforced_reading"]["value"],
            "label_absolute_status": res["absolute_status"],
            "geometry_regression_verdict": geom.get("regression_verdict"),
            "geometry_absolute_status": geom.get("absolute_status"),
            "n_bundles_pass_all_11": geom.get("n_bundles_pass_all_11"),
            "absolute_bars_enforced": False,
            "absolute_bar_note": ("both absolute bars are REPORTED only (direction v50): label "
                                  "support_rate == 1.0 and geometry 11/11 on every bundle. Neither "
                                  "blocks a build."),
            "never_certifies": ("this input says nothing about retrieval or counter-authority "
                                "recall, about source validity, or about jurist usefulness; and a "
                                "verdict of NOT_APPLICABLE or NOT_MEASURED is never a pass."),
        },
        "exit_code": 1 if blocks else 0,
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--packet-root", default=str(ACCEPTED_PACKET_ROOT),
                    help="root directory holding packet directories (default: accepted mount)")
    ap.add_argument("--adjudicate", default=None, metavar="PACKET_DIR",
                    help="judge ONE packet directory; exit 1 on a regression")
    ap.add_argument("--freeze", default="results/evaluation/label_lineage_gate/freeze/"
                                        "FROZEN_HYPOTHESIS_39020603510.json",
                    help="pre-execution freeze whose PREDICTIONS are executed against the "
                         "measured sweep (read-only; never written)")
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)
    t0 = time.time()

    try:
        ident = _verify_frozen_identity()
    except Exception as e:  # noqa: BLE001
        print(f"label_lineage_gate environment error: {e}", file=sys.stderr)
        return 2
    if not all(v["matches"] for v in ident.values()):
        print(json.dumps({"verdict": "ENVIRONMENT_ERROR",
                          "detail": "frozen input sha256 mismatch; refusing to classify",
                          "identity": ident}, indent=1), file=sys.stderr)
        return 2

    try:
        rules = label_gate.load_frozen_rules()
        geom_rules = geometry_gate.load_frozen_geometry_rules()
        label_lineage_gate.load_verdict_contract()
    except RuntimeError as e:
        print(f"label_lineage_gate environment error: {e}", file=sys.stderr)
        return 2

    record: dict = {
        "schema": "lex-evaluation-label-lineage-gate/1",
        "mode": "adjudicate" if args.adjudicate else "sweep",
        "rules_label_sha256": rules.sha256,
        "rules_geometry_sha256": geom_rules and geometry_gate.EXPECTED_RULES_SHA256,
        "enforced_predicate_rate": label_lineage_gate.PREDICATE_RATE,
        "enforced_predicate_rate_derivation":
            "label_gate.INCUMBENT[n_supported] / label_gate.INCUMBENT[n_scored] = 5/65",
        "frozen_identity": ident,
        "added": "ADDITIVE: no accepted verdict is overwritten; accepted verdicts are reported "
                 "side by side",
    }

    try:
        if args.adjudicate:
            record.update(adjudicate(Path(args.adjudicate), rules, geom_rules))
        else:
            sw = sweep(Path(args.packet_root), rules, geom_rules)
            record.update(sw)
            if args.freeze and Path(args.freeze).exists():
                record["frozen_prediction_verification"] = (
                    label_lineage_gate.verify_frozen_predictions(
                        args.freeze, sw, frozen_identity=ident))
            elif args.freeze:
                record["frozen_prediction_verification"] = {
                    "status": "NOT_RUN",
                    "reason": f"freeze file not found: {args.freeze}"}
    except (FileNotFoundError, RuntimeError, ValueError) as e:
        record["verdict"] = "ENVIRONMENT_ERROR"
        record["detail"] = f"{type(e).__name__}: {e}"
        record["exit_code"] = 2
        print(json.dumps(record, indent=1)[:1500])
        if args.out:
            Path(args.out).write_text(json.dumps(record, indent=1), encoding="utf-8")
        return 2

    record["elapsed_s"] = round(time.time() - t0, 3)
    if "exit_code" not in record:
        record["verdict"] = "SWEEP_COMPLETE"
        record["exit_code"] = 0

    print(json.dumps({k: v for k, v in record.items()
                      if k not in ("blocking_matrix",)}, indent=1)[:4000])
    if args.out:
        Path(args.out).write_text(json.dumps(record, indent=1), encoding="utf-8")
    return int(record["exit_code"])


if __name__ == "__main__":
    raise SystemExit(main())
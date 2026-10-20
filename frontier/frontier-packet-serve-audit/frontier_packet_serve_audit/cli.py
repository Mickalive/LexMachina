"""CLI: python -m frontier_packet_serve_audit.cli --packet <dir> --frozen-rules <dir>

Independent serve audit on the packet-of-record v3 bytes. Consumes the packet
and the frozen rules, recomputes the frozen label and geometry scoring as a
cross-check of Core Evaluation's published numbers, measures marginal
discovery, and emits ONE machine-checked serve recommendation.

Offline, deterministic, stdlib only. No network, no paid API, no product
import, no writes outside the team namespace.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

_TEAM_ROOT = Path(__file__).resolve().parents[1]
if str(_TEAM_ROOT) not in sys.path:
    sys.path.insert(0, str(_TEAM_ROOT))

from frontier_packet_serve_audit import (  # noqa: E402
    crosscheck,
    geometry_gate,
    label_gate,
    marginal_discovery,
    non_vacuity,
    verdict,
)
from frontier_packet_serve_audit.content_hash import content_sha256  # noqa: E402

QIDS = ("de-kapitalverletzung", "fr-bail-entretien", "it-responsabilita-medica")

EXPECTED_PACKET_JSON_SHA256 = "32ac812626e679c357822543d0b2e78e62c0e95a9a1b233d1ec89d7cb7b6ac70"
EXPECTED_MANIFEST_SHA256 = "8ea3c92d11e915bcea98b3bc1bd80724b08e920c6ff3bdcade18ed39db388bb7"


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def run_audit(packet_dir: Path, frozen_rules_dir: Path, eval_mount: Path, product_mount: Path) -> dict:
    t0 = time.time()
    # ---- input identity (re-hash before any scoring) --------------------
    packet_json = packet_dir / "packet.json"
    manifest = packet_dir / "manifest.json"
    if not packet_json.exists():
        raise FileNotFoundError(f"packet.json not found in {packet_dir}")
    packet_sha = _sha256_file(packet_json)
    manifest_sha = _sha256_file(manifest) if manifest.exists() else None
    bundle_paths = {qid: packet_dir / "questions" / f"{qid}.bundle.json" for qid in QIDS}
    missing = [str(p) for p in bundle_paths.values() if not p.exists()]
    if missing:
        raise FileNotFoundError(f"missing anchor bundles: {missing}")
    bundle_shas = {qid: _sha256_file(p) for qid, p in bundle_paths.items()}
    bundles = {qid: _load_json(p) for qid, p in bundle_paths.items()}
    content_shas = {qid: content_sha256(b) for qid, b in bundles.items()}

    # ---- frozen rules (re-hash before use) --------------------------------
    label_rules = label_gate.load_frozen_rules(frozen_rules_dir / "RULES_LABEL.json")
    geometry_rules = geometry_gate.load_frozen_geometry_rules(frozen_rules_dir / "RULES_GEOMETRY.json")

    # ---- (a) LABEL SUPPORT ----------------------------------------------
    label_res = label_gate.score_packet({qid: str(p) for qid, p in bundle_paths.items()}, label_rules)
    lineage_verdict = label_gate.label_lineage_gate_verdict(label_res)
    label_nv = non_vacuity.label_injection_control(label_rules)

    # ---- (b) GEOMETRY ----------------------------------------------------
    geom_res = geometry_gate.score_packet(bundles, geometry_rules)
    lexicons = geometry_rules.get("query_term_lexicons", {})
    lang_by_qid = {e.get("bundle"): e.get("query_language") for e in geometry_rules.get("inputs", [])}
    geom_nv = {
        qid: non_vacuity.geometry_non_vacuity_control(
            bundles[qid], lang_by_qid[qid], lexicons[qid])
        for qid in QIDS
    }

    # ---- (c) MARGINAL DISCOVERY ------------------------------------------
    marginal = marginal_discovery.measure_packet(bundles)

    # ---- CROSS-CHECK ------------------------------------------------------
    xcheck = crosscheck.build_crosscheck(label_res, geom_res, eval_mount, product_mount)

    # ---- VERDICT ----------------------------------------------------------
    v = verdict.decide(label_res, geom_res, marginal)
    verdict.assert_machine_check(v)

    # ---- non-vacuity summary ---------------------------------------------
    # The charter requires proving at least two criteria/verdicts can move
    # under a seeded control. Proven when the BEST bundle flips >= 2 (de and
    # fr each flip 2); per-bundle counts are reported, never hidden.
    geom_nv_proven = any(g["proven_non_vacuous"] for g in geom_nv.values())
    reachability = non_vacuity.verdict_reachability_control()
    non_vacuity_summary = {
        "geometry_permutation": {qid: {
            "charter_flips": geom_nv[qid]["charter"]["n_flips"],
            "full_flips": geom_nv[qid]["full"]["n_flips"],
            "proven_non_vacuous": geom_nv[qid]["proven_non_vacuous"],
        } for qid in QIDS},
        "geometry_permutation_proven": geom_nv_proven,
        "label_injection": label_nv,
        "verdict_reachability": reachability,
        "non_vacuity_proven": bool(geom_nv_proven and label_nv["proven_non_vacuous"]
                                   and reachability["both_outcomes_reachable"]),
    }

    record = {
        "schema": "frontier-packet-serve-audit/1",
        "team_id": "frontier-packet-serve-audit",
        "charter_version": 1,
        "charter_run_id": "39355384602",
        "packet_dir": str(packet_dir),
        "input_identity": {
            "packet_json_sha256": packet_sha,
            "packet_json_matches_charter": packet_sha == EXPECTED_PACKET_JSON_SHA256,
            "manifest_sha256": manifest_sha,
            "manifest_matches_charter": manifest_sha == EXPECTED_MANIFEST_SHA256,
            "bundle_raw_sha256": bundle_shas,
            "bundle_content_sha256": content_shas,
            "n_decisions": {qid: len(bundles[qid].get("decisions") or []) for qid in QIDS},
        },
        "frozen_rules": {
            "rules_label_sha256": label_rules.sha256,
            "rules_geometry_sha256": geometry_gate.RULES_GEOMETRY_SHA256,
        },
        "label_half": {
            "n_scored": label_res["n_scored"],
            "n_supported": label_res["n_supported"],
            "support_rate": label_res["support_rate"],
            "n_decisions": label_res["n_decisions"],
            "n_abstain": label_res["n_abstain"],
            "yield_over_population": label_res["yield_over_population"],
            "absolute_bar": label_res["absolute_bar"],
            "absolute_status": label_res["absolute_status"],
            "regression_verdict": label_res["regression_verdict"],
            "gate_blocks_build": label_res["gate_blocks_build"],
            "label_lineage_gate_verdict": lineage_verdict,
            "per_bundle": {qid: {
                "n_scored": label_res["per_bundle"][qid]["n_scored"],
                "n_supported": label_res["per_bundle"][qid]["n_supported"],
                "n_abstain": label_res["per_bundle"][qid]["n_abstain"],
                "yield_over_population": label_res["per_bundle"][qid]["yield_over_population"],
                "status_counts": label_res["per_bundle"][qid]["status_counts"],
            } for qid in QIDS},
        },
        "geometry_half": {
            "per_bundle_counts": geom_res["per_bundle_counts"],
            "absolute_status": geom_res["absolute_status"],
            "n_bundles_pass_all_11": geom_res["n_bundles_pass_all_11"],
            "regression_verdict": geom_res["regression_verdict"],
            "gate_blocks_build": geom_res["gate_blocks_build"],
            "per_bundle": {qid: {
                "n_pass": geom_res["per_bundle"][qid]["n_pass"],
                "criteria": geom_res["per_bundle"][qid]["criteria"],
                "mega_cluster": geom_res["per_bundle"][qid]["mega_cluster"],
            } for qid in QIDS},
        },
        "marginal_discovery": marginal,
        "crosscheck": xcheck,
        "non_vacuity": non_vacuity_summary,
        "verdict": v,
    }
    # Wall-clock is NOT part of the record (frozen determinism rule: no
    # wall-clock in the report). Tracked for stderr information only.
    elapsed = round(time.time() - t0, 3)
    return record, elapsed


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Independent serve audit on the packet-of-record v3 bytes")
    ap.add_argument("--packet", required=True, help="packet-of-record v3 directory")
    ap.add_argument("--frozen-rules", required=True, help="directory with RULES_LABEL.json / RULES_GEOMETRY.json / VERDICT_CONTRACT.json")
    ap.add_argument("--eval-mount", default="/tmp/lex_accepted/core/evaluation")
    ap.add_argument("--product-mount", default="/tmp/lex_accepted/core/product")
    ap.add_argument("--out", default=None, help="write the verdict record to this path")
    args = ap.parse_args(argv)

    packet_dir = Path(args.packet)
    frozen_rules_dir = Path(args.frozen_rules)
    record, elapsed = run_audit(packet_dir, frozen_rules_dir, Path(args.eval_mount), Path(args.product_mount))
    print(f"# audit completed in {elapsed}s (wall-clock, not part of the record)", file=sys.stderr)

    text = json.dumps(record, indent=1, ensure_ascii=False)
    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

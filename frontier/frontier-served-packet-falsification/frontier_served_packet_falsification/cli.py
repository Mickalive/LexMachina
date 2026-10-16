"""CLI entry point.

    python -m frontier_served_packet_falsification.cli --out <dir> [--half label|geometry|both]

Reads ONLY gate_packet/38839347028. Emits per-bundle, per-row and per-criterion
results plus a machine-readable BEFORE_AFTER.json. Offline, deterministic,
no network, no provider, no clock.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from typing import Any

from . import (
    BUNDLES,
    BUNDLE_SHA256,
    CHARTER_VERSION,
    GATE_PACKET,
    RULES_GEOMETRY_SHA256,
    RULES_LABEL_SHA256,
    TEAM_ID,
)
from .before_after import build_before_after
from .claim_ceiling import check_payload, build_claim_ceiling_artifact
from .geometry_half import run_geometry_half
from .label_half import run_label_half


def _sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _write_json(path: str, payload: Any) -> str:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    text = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _find_packet_dir(repo_root: str) -> str:
    """Locate gate_packet/38839347028 under the repo or the accepted mount."""
    candidates = [
        os.path.join(repo_root, GATE_PACKET),
        os.path.join("/tmp/lex_accepted/core/product", GATE_PACKET),
    ]
    for c in candidates:
        if os.path.isdir(c):
            return c
    raise FileNotFoundError(
        f"gate packet not found; tried: {candidates}"
    )


def _find_rules(repo_root: str) -> tuple[str, str]:
    """Locate the two frozen RULES files (must be in the team's results dir)."""
    label = os.path.join(
        repo_root, "results", "frontier", TEAM_ID, "RULES_LABEL.json"
    )
    geom = os.path.join(
        repo_root, "results", "frontier", TEAM_ID, "RULES_GEOMETRY.json"
    )
    for p in (label, geom):
        if not os.path.isfile(p):
            raise FileNotFoundError(f"frozen rules not found: {p}")
    return label, geom


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="frontier_served_packet_falsification")
    ap.add_argument("--out", required=True, help="output directory")
    ap.add_argument(
        "--half",
        choices=["label", "geometry", "both"],
        default="both",
        help="which half to run (default both)",
    )
    ap.add_argument("--repo-root", default=".", help="repository root")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args(argv)

    repo_root = os.path.abspath(args.repo_root)
    packet_dir = _find_packet_dir(repo_root)
    rules_label_path, rules_geom_path = _find_rules(repo_root)

    # Prove freeze byte-identity before any scoring.
    label_sha = _sha256_file(rules_label_path)
    geom_sha = _sha256_file(rules_geom_path)
    freeze_ok = (
        label_sha == RULES_LABEL_SHA256 and geom_sha == RULES_GEOMETRY_SHA256
    )
    if not freeze_ok:
        print(
            "FREEZE BYTE-IDENTITY FAILURE: "
            f"LABEL {label_sha} (expected {RULES_LABEL_SHA256}); "
            f"GEOMETRY {geom_sha} (expected {RULES_GEOMETRY_SHA256})",
            file=sys.stderr,
        )
        return 2

    out_dir = os.path.abspath(args.out)
    os.makedirs(out_dir, exist_ok=True)

    label_half: dict[str, Any] | None = None
    geometry_half: dict[str, Any] | None = None

    if args.half in ("label", "both"):
        label_half = run_label_half(
            rules_label_path,
            packet_dir,
            BUNDLE_SHA256,
            expected_rules_sha256=RULES_LABEL_SHA256,
        )
        _write_json(os.path.join(out_dir, "LABEL_HALF.json"), label_half)
        if not args.quiet:
            print(
                f"LABEL: {label_half['n_supported']}/{label_half['n_scored']} supported "
                f"({label_half['support_rate']}), verdict={label_half['verdict']}"
            )

    if args.half in ("geometry", "both"):
        geometry_half = run_geometry_half(
            rules_geom_path,
            packet_dir,
            BUNDLE_SHA256,
            expected_rules_sha256=RULES_GEOMETRY_SHA256,
        )
        _write_json(os.path.join(out_dir, "GEOMETRY_HALF.json"), geometry_half)
        if not args.quiet:
            print(
                f"GEOMETRY: {geometry_half['n_bundles_pass']}/3 bundles pass, "
                f"verdict={geometry_half['verdict']}"
            )
            for b in geometry_half["bundles"]:
                print(
                    f"  {b['qid']}: {b['n_pass']}/11 pass ({b['overall']}), "
                    f"largest_share(size)={b['largest_share_both_definitions']['largest_share_size_field']:.4f}"
                )

    # BEFORE/AFTER
    if label_half is not None and geometry_half is not None:
        ba = build_before_after(label_half, geometry_half)
        _write_json(os.path.join(out_dir, "BEFORE_AFTER.json"), ba)
    elif label_half is not None:
        ba = build_before_after(label_half, {"bundles": [], "verdict": None, "n_bundles_pass": None})
        _write_json(os.path.join(out_dir, "BEFORE_AFTER.json"), ba)
    elif geometry_half is not None:
        ba = build_before_after(
            {"support_rate": None, "verdict": None, "n_scored": None, "n_supported": None, "overall": {}},
            geometry_half,
        )
        _write_json(os.path.join(out_dir, "BEFORE_AFTER.json"), ba)

    # CLAIM_CEILING
    cc = build_claim_ceiling_artifact()
    _write_json(os.path.join(out_dir, "CLAIM_CEILING.json"), cc)

    # Freeze identity record
    freeze_record = {
        "schema": "frontier-served-packet-falsification/freeze/1",
        "rules_label_sha256": label_sha,
        "rules_label_expected": RULES_LABEL_SHA256,
        "rules_label_byte_identity": label_sha == RULES_LABEL_SHA256,
        "rules_geometry_sha256": geom_sha,
        "rules_geometry_expected": RULES_GEOMETRY_SHA256,
        "rules_geometry_byte_identity": geom_sha == RULES_GEOMETRY_SHA256,
        "freeze_byte_identity_ok": freeze_ok,
        "note": (
            "Structural copy of two accepted RULES.json files. No frozen_at_utc field "
            "is written. No threshold is introduced, restated or re-derived. The only "
            "new frozen artifact is INPUT_LIST.json (three bundle paths with sha256 "
            "plus the accepted baseline run ids), a precondition for reproducibility."
        ),
    }
    _write_json(os.path.join(out_dir, "FREEZE.json"), freeze_record)

    # Machine-readable summary
    summary: dict[str, Any] = {
        "schema": "frontier-served-packet-falsification/summary/1",
        "team_id": TEAM_ID,
        "charter_version": CHARTER_VERSION,
        "gate_packet": GATE_PACKET,
        "bundles": list(BUNDLES),
        "bundle_sha256": dict(BUNDLE_SHA256),
        "half": args.half,
        "freeze_byte_identity_ok": freeze_ok,
        "label_verdict": label_half["verdict"] if label_half else None,
        "label_support_rate": label_half["support_rate"] if label_half else None,
        "label_n_scored": label_half["n_scored"] if label_half else None,
        "label_n_supported": label_half["n_supported"] if label_half else None,
        "geometry_verdict": geometry_half["verdict"] if geometry_half else None,
        "geometry_n_bundles_pass": geometry_half["n_bundles_pass"] if geometry_half else None,
    }
    _write_json(os.path.join(out_dir, "SUMMARY.json"), summary)

    # Claim-ceiling machine check over everything emitted
    cc_check = check_payload(
        {
            "label": label_half,
            "geometry": geometry_half,
            "before_after": ba if (label_half or geometry_half) else None,
            "summary": summary,
        }
    )
    _write_json(os.path.join(out_dir, "CLAIM_CEILING_CHECK.json"), cc_check)
    if not cc_check["pass"]:
        print("CLAIM CEILING VIOLATION:", cc_check["violations"], file=sys.stderr)
        return 3

    if not args.quiet:
        print(f"Wrote outputs to {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

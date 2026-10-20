"""CLI: offline attribution + emission measurement for one packet dir.

Usage::

    python -m frontier_counter_label_emission.cli --packet <dir> [--out <dir>]

Writes, into the team namespace only:

* ``ATTRIBUTION.json``  — per-bundle primary cause with byte-level evidence
* ``EMISSION.json``     — before/after three-number publication per bundle
* ``DETERMINISM.json``  — >=3 identical runs or the bounded disclosure
* ``NON_VACUITY.json``  — seeded + negative controls
* ``MEASUREMENT_SUMMARY.json`` — the promoted record

Deterministic, offline, no network, no clock in the claim-bearing outputs.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from .absolute_bar import compute_absolute_bar_status
from .attribution import attribute_packet, sha256_file, verify_input_hashes
from .classifier_bridge import (
    SCORED_STATUSES,
    run_classifier_on_bundle,
    verify_classifier_and_rubric,
)
from .determinism import run_determinism, run_non_vacuity
from .emission import promote_heuristic_proposals

#: Input pins (mirrors the frozen RULES.json; re-checked at run time).
INPUT_PINS = {
    "packet.json": "32ac812626e679c357822543d0b2e78e62c0e95a9a1b233d1ec89d7cb7b6ac70",
    "manifest.json": "8ea3c92d11e915bcea98b3bc1bd80724b08e920c6ff3bdcade18ed39db388bb7",
    "questions/de-kapitalverletzung.bundle.json":
        "9b856e2b1b3e4675f8d4d135cd5d1ad23f0baa63fcb2e4cc7bc45182c012881b",
    "questions/fr-bail-entretien.bundle.json":
        "054bec47ae8e5a0f98593902c2c7bd09f7f52761be1c85225328853f34d3213b",
    "questions/it-responsabilita-medica.bundle.json":
        "345e20d1f352fd4e907cac144c8dbbae296f3a9132605d4354f12e7a783e6e3b",
}

QIDS = ("de-kapitalverletzung", "fr-bail-entretien", "it-responsabilita-medica")


def _load_rules_data(rules_path: Path) -> dict[str, Any]:
    return json.loads(rules_path.read_text(encoding="utf-8"))


def measure_packet(
    packet_dir: Path,
    *,
    out_dir: Path | None = None,
    classifier_root: str | None = None,
    rules_path: str | None = None,
    n_determinism_runs: int = 3,
) -> dict[str, Any]:
    """Run the full charter measurement pipeline on one packet dir."""
    # 1. Re-verify every input hash before any claim-bearing execution.
    hash_verification = verify_input_hashes(packet_dir, INPUT_PINS)
    ver_classifier = verify_classifier_and_rubric(
        classifier_root=classifier_root, rules_path=rules_path,
    )
    rules_file = Path(ver_classifier["rules_path"])
    rules_data = _load_rules_data(rules_file)

    # 2. Attribution (offline, deterministic).
    attribution = attribute_packet(packet_dir, SCORED_STATUSES)

    # 3. Before / after emission measurement, per bundle.
    emission: dict[str, Any] = {}
    determinism: dict[str, Any] = {}
    non_vacuity: dict[str, Any] = {}
    for qid in QIDS:
        bundle_path = packet_dir / "questions" / f"{qid}.bundle.json"
        bundle = json.loads(bundle_path.read_text(encoding="utf-8"))

        before = run_classifier_on_bundle(
            bundle, qid=qid,
            classifier_root=classifier_root, rules_path=rules_path,
            hash_verification=ver_classifier,
        )
        before_bar = compute_absolute_bar_status(before, rules_data)

        repaired = promote_heuristic_proposals(bundle, scored_statuses=SCORED_STATUSES)
        after = run_classifier_on_bundle(
            repaired, qid=qid,
            classifier_root=classifier_root, rules_path=rules_path,
            hash_verification=ver_classifier,
        )
        after_bar = compute_absolute_bar_status(after, rules_data)

        emission[qid] = {
            "before": {**before, "absolute_bar_status": before_bar},
            "after": {**after, "absolute_bar_status": after_bar},
            "repair": {
                "repair_id": (repaired.get("provenance") or {}).get(
                    "counter_label_emission_repair"
                ) or {},
            },
        }

        # 4. Determinism on the repaired path.
        determinism[qid] = run_determinism(
            bundle, qid=qid, n_runs=n_determinism_runs,
            classifier_root=classifier_root, rules_path=rules_path,
        )

        # 5. Non-vacuity controls (first bundle only is enough for the
        #    charter's acceptance test; run on all three for completeness).
        non_vacuity[qid] = run_non_vacuity(
            bundle, qid=qid,
            classifier_root=classifier_root, rules_path=rules_path,
        )

    # 6. Classifier config re-verification AFTER measurement.
    ver_classifier_after = verify_classifier_and_rubric(
        classifier_root=classifier_root, rules_path=rules_path,
    )

    summary = {
        "schema": "frontier-counter-label-emission-measurement/1",
        "team_id": "frontier-counter-label-emission",
        "charter_version": 1,
        "packet_dir": str(packet_dir),
        "input_hash_verification": hash_verification,
        "classifier_hash_verification_before": ver_classifier,
        "classifier_hash_verification_after": ver_classifier_after,
        "classifier_config_byte_identical_after": (
            ver_classifier_after["ok"] and ver_classifier["ok"]
        ),
        "frozen_rules_sha256": ver_classifier["frozen_rules_sha256_actual"],
        "frozen_rubric_byte_identical": bool(ver_classifier["frozen_rules_ok"]),
        "attribution": attribution,
        "emission": emission,
        "determinism": determinism,
        "non_vacuity": non_vacuity,
        "claim_ceiling": (
            "This record measures and repairs the EMISSION PATH that feeds "
            "the accepted classifier.  It NEVER asserts that any decision IS "
            "supporting/contrary/limiting.  Support-among-issued, the "
            "abstention count and the yield are published together.  The "
            "frozen absolute bar remains unmet as written and is never "
            "re-derived.  No serve recommendation is produced."
        ),
    }

    if out_dir is not None:
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "ATTRIBUTION.json").write_text(
            json.dumps({"attribution": attribution}, indent=1, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        (out_dir / "EMISSION.json").write_text(
            json.dumps({"emission": emission}, indent=1, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        (out_dir / "DETERMINISM.json").write_text(
            json.dumps({"determinism": determinism}, indent=1, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        (out_dir / "NON_VACUITY.json").write_text(
            json.dumps({"non_vacuity": non_vacuity}, indent=1, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        (out_dir / "MEASUREMENT_SUMMARY.json").write_text(
            json.dumps(summary, indent=1, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        # Record the artifact digests for the promotion record.
        digests = {
            p.name: sha256_file(p)
            for p in sorted(out_dir.iterdir())
            if p.is_file() and p.name != "ARTIFACT_DIGESTS.json"
        }
        (out_dir / "ARTIFACT_DIGESTS.json").write_text(
            json.dumps(digests, indent=1, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="frontier_counter_label_emission.cli",
        description="Offline attribution + emission measurement for one packet dir.",
    )
    parser.add_argument("--packet", required=True, help="packet dir (gate_packet/<run_id>)")
    parser.add_argument("--out", default=None, help="output dir (team namespace only)")
    parser.add_argument("--classifier-root", default=None)
    parser.add_argument("--rules", default=None, help="frozen RULES_LABEL.json path")
    parser.add_argument("--determinism-runs", type=int, default=3)
    args = parser.parse_args(argv)

    packet_dir = Path(args.packet)
    if not packet_dir.is_dir():
        print(f"packet dir not found: {packet_dir}", file=sys.stderr)
        return 2

    out_dir = Path(args.out) if args.out else None
    summary = measure_packet(
        packet_dir,
        out_dir=out_dir,
        classifier_root=args.classifier_root,
        rules_path=args.rules,
        n_determinism_runs=args.determinism_runs,
    )

    # Human-readable digest to stdout (claim-bearing numbers).
    print(json.dumps({
        "input_hashes_ok": summary["input_hash_verification"]["ok"],
        "classifier_ok_before": summary["classifier_hash_verification_before"]["ok"],
        "classifier_ok_after": summary["classifier_hash_verification_after"]["ok"],
        "frozen_rubric_ok": summary["frozen_rubric_byte_identical"],
        "attribution": {
            qid: rec["primary_cause"]
            for qid, rec in sorted(summary["attribution"].items())
        },
        "emission_before": {
            qid: {
                "n_scored": rec["before"]["n_scored"],
                "n_emitted": rec["before"]["n_emitted"],
                "n_abstained": rec["before"]["n_abstained"],
            }
            for qid, rec in sorted(summary["emission"].items())
        },
        "emission_after": {
            qid: {
                "n_scored": rec["after"]["n_scored"],
                "n_emitted": rec["after"]["n_emitted"],
                "n_abstained": rec["after"]["n_abstained"],
                "absolute_bar_status": rec["after"]["absolute_bar_status"]["status"],
            }
            for qid, rec in sorted(summary["emission"].items())
        },
        "determinism": {
            qid: rec["identical"] for qid, rec in sorted(summary["determinism"].items())
        },
        "non_vacuity": {
            qid: rec["non_vacuity_pass"] for qid, rec in sorted(summary["non_vacuity"].items())
        },
    }, indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

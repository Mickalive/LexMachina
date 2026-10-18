#!/usr/bin/env python3
"""Mount-absent fallback verifier for the frozen question-native transfer pins.

    python -m evaluation.secondary_source_fallback --run-id <run_id> \
        [--hypothesis evaluation/QUESTION_NATIVE_TRANSFER_HYPOTHESIS.json] \
        [--secondary results/evaluation/rebuilt_packet_adjudication_39049030442/packet] \
        [--primary-mount /tmp/lex_accepted/product] \
        [--out results/evaluation/secondary_source_fallback/<run_id>.json]

WHY THIS IS A NEW INSTRUMENT, NOT AN EDIT
----------------------------------------
Repair F4 of independent audit ``CYCLE_39120832665`` (gate=REVISE) found that the
claim-bearing instrument ``evaluation/question_native_transfer.py`` resolves its
10 rebuilt-packet inputs ONLY from the ephemeral dispatch mount
``/tmp/lex_accepted/product``.  That mount does not exist in an auditor or CI
checkout, so an in-repo re-run correctly returns NOT_MEASURED (exit 2) - never a
silent pass - and the transfer verdict is not re-derivable from committed bytes
alone.  The SAME audit confirmed the committed secondary source
``results/evaluation/rebuilt_packet_adjudication_39049030442/packet/`` holds
byte-identical copies of all 10 rebuilt-packet pins.

``question_native_transfer.py`` is FROZEN: its sha256
``ffb2c70fe202ecd495dc0bf969a68bdf4ea891769be2b812ea4f36379a258a29`` is a pin
inside the frozen hypothesis and inside the claim-bearing record, so editing it
would destroy the provenance of run 39120832665's verdict.  The fallback
therefore lives in THIS new, separately-named instrument and accepts the
secondary source as a DOCUMENTED mount-absent fallback.  Nothing frozen, no
accepted record, no rubric, threshold, bar or success rule is touched.

F1 GAP CLOSURE (declared-but-unenforced provenance pin)
------------------------------------------------------
The same audit (F1) found the hypothesis DECLARES a 14th pin,
``frozen_inputs.instrument_sha256``, which the primary instrument's
``rehash_pins()`` never verifies.  This later instrument closes that gap: it
re-hashes ``evaluation/question_native_transfer.py`` against that declared pin
as check #14, and publishes the check count honestly (the primary instrument's
record remains 13 checks; that record is NOT edited).

Exit 0 = SECONDARY_SOURCE_MATCHES_HYPOTHESIS_PINS
Exit 1 = PIN_MISMATCH (any re-hashed value differs from the frozen pin)
Exit 2 = NOT_MEASURED (any required input absent - never a silent pass)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = "lex-evaluation-secondary-source-fallback/1"

FROZEN_QIDS = (
    "de-kapitalverletzung",
    "fr-bail-entretien",
    "it-responsabilita-medica",
)
PACKET_B = "rebuilt-39027045675"
HYPOTHESIS_RELPATH = "evaluation/QUESTION_NATIVE_TRANSFER_HYPOTHESIS.json"
PRIOR_RECORD_RELPATH = "results/evaluation/subject_match_audit/39117425713.json"
V21_HYPOTHESIS_RELPATH = "evaluation/PRODUCT_COUNTER_RECALL_HYPOTHESIS_V2_1.json"
PRIMARY_INSTRUMENT_RELPATH = "evaluation/question_native_transfer.py"
SECONDARY_DEFAULT = "results/evaluation/rebuilt_packet_adjudication_39049030442/packet"
PRIMARY_MOUNT_DEFAULT = "/tmp/lex_accepted/product"

EXIT_OK = 0
EXIT_MISMATCH = 1
EXIT_NOT_MEASURED = 2


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _load_json(path: Path) -> dict:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def rehash_all_pins(hyp: dict, root: Path, secondary: Path) -> dict:
    """Re-hash all 14 declared pins.

    The 10 rebuilt-packet pins resolve from the COMMITTED secondary source; the
    3 repo-local pins and the 14th (primary-instrument self-hash) resolve from
    the repository itself.  No input comes from the ephemeral mount.
    """
    pins = hyp["frozen_inputs"]
    results: dict[str, dict] = {}
    ok = True
    missing = False

    def check(name: str, path: Path, expected: str) -> None:
        nonlocal ok, missing
        if not path.is_file():
            results[name] = {"present": False, "expected": expected,
                             "resolved_from": str(path)}
            ok = False
            missing = True
            return
        actual = sha256_file(path)
        match = actual == expected
        results[name] = {
            "present": True, "expected": expected, "actual": actual,
            "match": match, "resolved_from": str(path),
        }
        if not match:
            ok = False

    # repo-local pins (identical paths to the primary instrument's)
    check("v2_1_hypothesis", root / V21_HYPOTHESIS_RELPATH,
          pins["v2_1_hypothesis_sha256"])
    check("subject_match_audit_instrument", root / "evaluation/subject_match_audit.py",
          pins["subject_match_audit_instrument_sha256"])
    check("prior_accepted_question_native_record", root / PRIOR_RECORD_RELPATH,
          pins["prior_accepted_question_native_record_sha256"])

    # the 10 rebuilt-packet pins, from the COMMITTED secondary source
    bdir = secondary
    check("rebuilt_packet_json", bdir / "packet.json", pins["rebuilt_packet_json_sha256"])
    for qid in FROZEN_QIDS:
        check(f"rebuilt_bundle::{qid}", bdir / "questions" / f"{qid}.bundle.json",
              pins["rebuilt_bundle_sha256"][qid])
        check(f"rebuilt_question::{qid}", bdir / "questions" / f"{qid}.question.json",
              pins["rebuilt_question_sha256"][qid])
        check(f"rebuilt_admissibility::{qid}", bdir / "questions" / f"{qid}.admissibility.json",
              pins["rebuilt_admissibility_sha256"][qid])

    # check #14 - the F1 gap closure: the primary instrument's own self-hash
    check("primary_instrument_self_hash", root / PRIMARY_INSTRUMENT_RELPATH,
          pins["instrument_sha256"])

    return {"all_match": ok, "any_input_missing": missing, "n_checks": len(results),
            "checks": results}


def run(run_id: str, hypothesis_path: Path, secondary: Path, root: Path) -> dict:
    if not hypothesis_path.is_file():
        raise FileNotFoundError(f"hypothesis not found: {hypothesis_path}")
    hyp = _load_json(hypothesis_path)
    pins = hyp["frozen_inputs"]
    if tuple(pins["frozen_qids_UNCHANGED"]) != FROZEN_QIDS:
        raise ValueError("qid set drift between module and hypothesis")

    pin_result = rehash_all_pins(hyp, root, secondary)
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    if pin_result["any_input_missing"]:
        verdict, exit_code = "NOT_MEASURED", EXIT_NOT_MEASURED
    elif pin_result["all_match"]:
        verdict, exit_code = "SECONDARY_SOURCE_MATCHES_HYPOTHESIS_PINS", EXIT_OK
    else:
        verdict, exit_code = "PIN_MISMATCH", EXIT_MISMATCH

    record = {
        "schema": SCHEMA,
        "run_id": run_id,
        "generated_at": stamp,
        "verdict": verdict,
        "exit_code": exit_code,
        "hypothesis": str(hypothesis_path),
        "hypothesis_sha256": sha256_file(hypothesis_path),
        "secondary_source": str(secondary),
        "primary_mount_used": False,
        "network_requests": 0,
        "n_pin_checks": pin_result["n_checks"],
        "pins_all_match": pin_result["all_match"],
        "any_input_missing": pin_result["any_input_missing"],
        "pins": {"all_match": pin_result["all_match"], "checks": pin_result["checks"]},
        "f1_gap_closure": (
            "check #14 (primary_instrument_self_hash) verifies the hypothesis-declared "
            "frozen_inputs.instrument_sha256 pin that the primary instrument's "
            "rehash_pins() never verifies; the primary record's own 13-check count is "
            "NOT edited."
        ),
        "f4_disclosure": (
            "the 10 rebuilt-packet pins resolve from the COMMITTED secondary source "
            "results/evaluation/rebuilt_packet_adjudication_39049030442/packet/, "
            "byte-identical to the ephemeral-mount bytes the frozen primary instrument "
            "read; the 3 repo-local pins and check #14 resolve from the repository."
        ),
        "frozen_files_touched": [],
        "unchanged": [
            "frozen hypothesis evaluation/QUESTION_NATIVE_TRANSFER_HYPOTHESIS.json",
            "frozen primary instrument evaluation/question_native_transfer.py",
            "claim-bearing record results/evaluation/question_native_transfer/39120832665.json",
            "verdict DISCLOSURE_DEFECT_TRANSFERRED (unchanged; this instrument does not re-verdict)",
            "human_gate_ready=false",
            "accepted DO-NOT-SERVE orders",
        ],
    }
    return record, exit_code


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--hypothesis", default=HYPOTHESIS_RELPATH)
    ap.add_argument("--secondary", default=SECONDARY_DEFAULT)
    ap.add_argument("--root", default=".")
    ap.add_argument("--out", default=None,
                    help="default: results/evaluation/secondary_source_fallback/<run-id>.json")
    ns = ap.parse_args(argv)
    root = Path(ns.root)
    out = Path(ns.out) if ns.out else (
        root / "results/evaluation/secondary_source_fallback" / f"{ns.run_id}.json")
    record, exit_code = run(ns.run_id, root / ns.hypothesis, root / ns.secondary, root)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(record, fh, indent=2, sort_keys=True)
        fh.write("\n")
    print(f"verdict={record['verdict']} exit={exit_code} "
          f"pins={record['n_pin_checks']}/{record['n_pin_checks']} "
          f"all_match={record['pins_all_match']} -> {out}")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())

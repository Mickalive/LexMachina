#!/usr/bin/env python3
"""Verify a mapping-free falsifier extension run against its frozen sample pins.

Reads the extension freeze record's mount_input_digests_before_execution and
compares each bundle digest with the engine record's per_question bundle_sha256
(and, when present, the admissibility digest). Exit 0 iff every pinned file the
engine measured re-hashes to the frozen digest; exit 1 on any mismatch;
exit 2 if either input is absent (never a pass).

This is a provenance checker, not a claim-bearing gate: it introduces no
threshold, no rubric and no product verdict.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
FREEZE = REPO_ROOT / "evaluation" / "MAPPING_FREE_39275520116_EXTENSION_FREEZE_RECORD_V1.json"
MOUNT = Path("/tmp/lex_accepted/product")


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    ap.add_argument("--engine-record", default=str(
        REPO_ROOT / "results" / "evaluation" / "mapping_free_recall_falsifier" / "39725464259.json"))
    ap.add_argument("--freeze", default=str(FREEZE))
    ap.add_argument("--mount", default=str(MOUNT))
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)

    freeze_path = Path(args.freeze)
    record_path = Path(args.engine_record)
    mount = Path(args.mount)
    if not freeze_path.is_file() or not record_path.is_file():
        out = {"verdict": "NOT_CHECKED_MISSING_INPUT", "exit_code": 2,
               "freeze_exists": freeze_path.is_file(), "record_exists": record_path.is_file()}
        print(json.dumps(out, indent=1))
        if args.out:
            Path(args.out).write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")
        return 2

    freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
    record = json.loads(record_path.read_text(encoding="utf-8"))
    pinned = {k: v for k, v in
              (freeze.get("frozen_sample") or {}).get(
                  "mount_input_digests_before_execution", {}).items()}

    rows = []
    mismatches = []
    for rel, want in sorted(pinned.items()):
        p = mount / rel
        have = sha256_file(p) if p.is_file() else None
        ok = have == want
        rows.append({"path": rel, "frozen": want, "rehashed": have, "match": ok})
        if not ok:
            mismatches.append(rel)

    # cross-check the engine record's per_question shas against the frozen pins
    engine_rows = []
    engine_mismatch = []
    frozen_bundles = {k: v for k, v in pinned.items() if k.endswith(".bundle.json")}
    for q in record.get("per_question") or []:
        qid = q.get("qid")
        want = frozen_bundles.get(
            f"results/product/gate_packet/{record.get('packets_measured', ['?'])[0]}/"
            f"questions/{qid}.bundle.json")
        got = q.get("bundle_sha256")
        ok = (want == got)
        engine_rows.append({"qid": qid, "frozen": want, "engine_recorded": got, "match": ok})
        if not ok:
            engine_mismatch.append(qid)

    verdict = "PINS_HELD" if (not mismatches and not engine_mismatch) else "PINS_DRIFTED"
    out = {
        "schema": "lex-evaluation-extension-pin-check/1",
        "freeze": str(freeze_path), "engine_record": str(record_path),
        "mount": str(mount), "verdict": verdict,
        "n_pinned_files": len(pinned), "n_file_mismatches": len(mismatches),
        "file_mismatches": mismatches,
        "n_engine_rows": len(engine_rows), "n_engine_mismatches": len(engine_mismatch),
        "engine_mismatches": engine_mismatch,
        "files": rows, "engine_rows": engine_rows,
        "claim_ceiling": "Provenance check only: the frozen sample pins re-hash and the engine "
                         "record agrees with them. It is NOT a product verdict, NOT a gate pass "
                         "and NOT a bar-met claim.",
        "exit_code": 0 if verdict == "PINS_HELD" else 1,
    }
    text = json.dumps(out, indent=1, ensure_ascii=False, sort_keys=True) + "\n"
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
    print(text)
    return out["exit_code"]


if __name__ == "__main__":
    raise SystemExit(main())

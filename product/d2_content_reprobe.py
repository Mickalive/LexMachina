#!/usr/bin/env python3
"""Direction v67 P0: before/after D2/D3/D4 probe of the product's own slice.

REUSE-FIRST: this script does not re-implement the defect predicates.  It loads
the *frozen* evaluation instrument
``evaluation/counter_evidence_quality_benchmark.py`` from the working tree when
present, otherwise from ``origin/lab/evaluation`` via ``git show``, records its
sha256, and calls ``classify_verified_row`` / ``probe_bundle`` directly.

It writes only product-owned paths:

    results/product/d2_content_reprobe/<run_id>.json

This is a REPORTED-ONLY delta record for the product lane.  It is not a frozen
evaluation record and makes no packet-admission claim.

Usage:
    python product/d2_content_reprobe.py \
        --before results/product/offline_slice/<old>/rent-default.bundle.json \
        --after  results/product/offline_slice/<new>/rent-default.bundle.json
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path

PRODUCT_ROOT = Path(__file__).resolve().parent
REPO_ROOT = PRODUCT_ROOT.parent
OUT_DIR = REPO_ROOT / "results" / "product" / "d2_content_reprobe"

FROZEN_REL = "evaluation/counter_evidence_quality_benchmark.py"
FROZEN_REF = "origin/lab/evaluation"
DEFECT_KEYS = ("D2_letterhead_zone", "D3_markup_residue", "D4_language_marker_mismatch")


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_frozen() -> tuple[object, dict]:
    """Load the frozen instrument; return (module, provenance)."""
    local = REPO_ROOT / FROZEN_REL
    if local.is_file():
        path, source = local, "working_tree"
    else:
        try:
            blob = subprocess.run(
                ["git", "show", f"{FROZEN_REF}:{FROZEN_REL}"],
                cwd=REPO_ROOT, check=True, capture_output=True,
            ).stdout
        except (subprocess.CalledProcessError, FileNotFoundError) as exc:
            raise SystemExit(f"frozen instrument unavailable: {exc}")
        tmp = Path(tempfile.mkstemp(prefix="frozen_ceq_", suffix=".py")[1])
        tmp.write_bytes(blob)
        path, source = tmp, FROZEN_REF
    spec = importlib.util.spec_from_file_location("frozen_ceq", path)
    if spec is None or spec.loader is None:
        raise SystemExit(f"cannot import frozen instrument at {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    prov = {
        "instrument": FROZEN_REL,
        "source": source,
        "sha256": _sha256(path),
        "defect_keys": list(DEFECT_KEYS),
    }
    return module, prov


def probe(path: Path, module) -> dict:
    bundle = json.loads(path.read_text(encoding="utf-8"))
    rows = bundle.get("decisions") or []
    verified = [r for r in rows if r.get("counter_evidence_verified") is True]
    histogram = {k: 0 for k in DEFECT_KEYS}
    defective: list[dict] = []
    for row in verified:
        result = module.classify_verified_row(row)
        for defect in result["defects"]:
            if defect in histogram:
                histogram[defect] += 1
        if result["defects"]:
            defective.append({
                "decision_id": row.get("decision_id"),
                "defects": result["defects"],
                "first_offset": result["detail"].get("first_offset"),
                "grounded_in": result["detail"].get("grounded_in"),
                "evidence_head": result["evidence_head"],
            })
    return {
        "bundle": str(path.relative_to(REPO_ROOT)) if path.is_relative_to(REPO_ROOT) else str(path),
        "bundle_sha256": _sha256(path),
        "n_decisions": len(rows),
        "n_verified": len(verified),
        "defect_histogram": histogram,
        "n_defective_verified": len(defective),
        "defective": defective,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--before", required=True)
    ap.add_argument("--after", required=True)
    ap.add_argument("--run-id", default=None)
    ap.add_argument("--out-dir", default=None)
    args = ap.parse_args(argv)

    before_path = Path(args.before)
    after_path = Path(args.after)
    module, instrument = load_frozen()
    before = probe(before_path, module)
    after = probe(after_path, module)

    hb, ha = before["defect_histogram"], after["defect_histogram"]
    cleared = sorted(
        {d["decision_id"] for d in before["defective"]}
        - {d["decision_id"] for d in after["defective"]}
    )
    remaining = [k for k in DEFECT_KEYS if ha.get(k, 0) > 0]
    verdict = "PASS" if not remaining else "FAIL"
    record = {
        "version": "product_d2_content_reprobe/1",
        "claim_tier": "REPORTED_ONLY",
        "run_id": args.run_id or time.strftime("%Y%m%dT%H%M%SZ", time.gmtime()),
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "instrument": instrument,
        "before": before,
        "after": after,
        "delta": {k: ha.get(k, 0) - hb.get(k, 0) for k in DEFECT_KEYS},
        "cleared_decision_ids": cleared,
        "remaining_defect_classes": remaining,
        "verdict": verdict,
        "notes": [
            "Frozen predicates called by value; no threshold, rubric or gate edited.",
            "Before/after are product-owned slice bundles, not the frozen family record.",
            "PASS means every verified row in the after bundle is defect-free.",
        ],
    }
    out_dir = Path(args.out_dir) if args.out_dir else OUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"{record['run_id']}.json"
    out.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "verdict": verdict,
        "before_histogram": hb,
        "after_histogram": ha,
        "before_verified": before["n_verified"],
        "after_verified": after["n_verified"],
        "cleared": cleared,
        "instrument_sha256": instrument["sha256"],
        "out": str(out),
    }, indent=1))
    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())

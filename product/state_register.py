#!/usr/bin/env python3
"""The lane state's ``verification`` register may GROW but never SHRINK silently.

Why this exists
---------------
The independent audit of rejected product cycle 39169296466
(``results/audit/product/CYCLE_39169296466_GATE.json``, F2) found that
``state/product.json``'s top-level ``verification`` register had been replaced
wholesale: 12 keys present at the accepted base ``bcb1217`` existed nowhere in
the shipped tree, including the lane's own admitted substantive failures - the
``latest_reality_check`` findings ("Generation quality can still be legally
misweighted even with the correct decision present"), the measured
``latency_budget_9a``, the ``pre_existing_collection_errors`` disclosure and the
``resume_39014141628`` caveat carrying the standing instruction "never weaken
content_sha256 or the seam's exclusion to make them pass". AGENTS.md rule 6
forbids deleting contrary outputs and overwriting historical claim-bearing
results.

The audit's non-blocking note N4 named why it escaped: *"no committed test reads
the ``state/product.json`` ``verification`` register, which is exactly why F2
escaped the ledger entirely."* This module is that missing reader.

The contract
------------
``product/data/state_register_baseline/verification_bcb1217.json`` is the
accepted base's ``verification`` block, byte-exact, and this module pins its
sha256. A tree is conformant when **every** baseline key is still present in
``state/product.json`` with the **same value** - keys added since (this cycle's
own entries, later cycles' entries) are fine and are how the register grows. A
missing key, or a key whose value was edited, is a FAIL, because both are
overwriting: the first deletes a record, the second rewrites it.

This is deliberately NOT a "the register must equal the baseline" check. That
would forbid the growth the lane needs and would itself overwrite.

Provenance (run 39172315384, repair round 1 of rejected cycle 39169296466)
---------------------------------------------------------------------------
* baseline extracted from ``git show bcb1217:state/product.json`` -
  ``bcb1217`` is ``accept product cycle 39149741259``, the accepted base this
  rejected cycle was built on; that file's raw sha256 is
  ``c7d3f139b259e6171fb54e7624a2fea041f08b7912be8fc8a3c1866b4ed55b79``;
* the extracted block is re-serialised with ``json.dumps(indent=2,
  sort_keys=True)``; the VALUES are byte-exact, the key order is canonicalised
  so the sha256 below is stable.

A check that cannot run is a FAIL, never a PASS - that is this lane's stated
rule and it is applied here explicitly (see ``missing_or_changed`` callers).
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

#: The accepted base commit the baseline was extracted from, named so a reader
#: can re-derive the block instead of trusting this file.
BASELINE_COMMIT = "bcb1217"
BASELINE_SOURCE_PATH = "state/product.json"
#: sha256 of ``git show bcb1217:state/product.json`` (raw bytes).
BASELINE_SOURCE_SHA256 = "c7d3f139b259e6171fb54e7624a2fea041f08b7912be8fc8a3c1866b4ed55b79"

BASELINE_PATH = (ROOT / "product" / "data" / "state_register_baseline"
                 / "verification_bcb1217.json")
#: sha256 of the extracted block as committed here.
BASELINE_SHA256 = "3583c454faa9d10921e58e573b5f0a75485936ffe6b4a5eb93d55d5e6402c08c"

#: The keys the accepted base carried. Named as data so a reader can see the
#: exact scope of the guard without running it, and so the negative control can
#: use a subset without inventing a new key name.
EXPECTED_BASELINE_KEYS: tuple[str, ...] = (
    "durable_actions_run",
    "durable_run_note",
    "evidence_reports",
    "latency_budget_9a",
    "latest_reality_check",
    "live_clickable_slice_this_cycle",
    "live_legs_this_run",
    "pre_existing_collection_errors",
    "product_integration_tests",
    "resume_39014141628",
    "status",
    "verified_on",
)


def baseline() -> dict:
    """The accepted base's ``verification`` block, or raise.

    Raises rather than returning ``{}``: a caller that cannot read the baseline
    must FAIL, never pass on an empty expectation set.
    """
    if not BASELINE_PATH.is_file():
        raise FileNotFoundError(f"missing state-register baseline: {BASELINE_PATH}")
    raw = BASELINE_PATH.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != BASELINE_SHA256:
        raise ValueError(
            f"state-register baseline sha256 {digest} != pinned {BASELINE_SHA256}; "
            "if the file was re-extracted, re-derive it from "
            f"`git show {BASELINE_COMMIT}:{BASELINE_SOURCE_PATH}` and record why")
    return json.loads(raw.decode("utf-8"))


def missing_or_changed(state: dict, baseline_block: dict | None = None) -> dict:
    """Baseline keys absent from ``state['verification']`` or edited.

    Returns ``{"missing": [...], "changed": {key: {"baseline": ..., "current": ...}}}``.
    An unreadable baseline or a missing ``verification`` register yields every
    baseline key as ``missing``, which is the fail-closed direction.
    """
    if baseline_block is None:
        try:
            baseline_block = baseline()
        except (FileNotFoundError, ValueError, json.JSONDecodeError):
            return {"missing": list(EXPECTED_BASELINE_KEYS), "changed": {},
                    "baseline_error": True}
    register = state.get("verification")
    if not isinstance(register, dict):
        return {"missing": list(EXPECTED_BASELINE_KEYS), "changed": {},
                "baseline_error": False}
    missing = [k for k in sorted(baseline_block) if k not in register]
    changed = {k: {"baseline": baseline_block[k], "current": register[k]}
               for k in sorted(baseline_block)
               if k in register and register[k] != baseline_block[k]}
    return {"missing": missing, "changed": changed, "baseline_error": False}


def load_state(state_path: Path) -> dict:
    return json.loads(Path(state_path).read_text(encoding="utf-8"))


def rows(state_path: Path, baseline_block: dict | None = None) -> list[dict]:
    """Ledger rows for the ``cycle_verify`` gate, derived not typed."""
    state = load_state(state_path)
    diff = missing_or_changed(state, baseline_block)
    register = state.get("verification") if isinstance(state.get("verification"), dict) else {}
    added = sorted(k for k in register if k not in (baseline_block or baseline()))
    ok = not diff["missing"] and not diff["changed"]
    return [{
        "claim": ("every verification-register record accepted at "
                  f"{BASELINE_COMMIT} is still present with an unedited value"),
        "status": "PASS" if ok else "FAIL",
        "observed": {
            "baseline_commit": BASELINE_COMMIT,
            "baseline_keys": len(baseline_block or EXPECTED_BASELINE_KEYS),
            "missing": diff["missing"],
            "changed_keys": sorted(diff["changed"]),
            "keys_added_since_baseline": added,
        },
        "definition_source": (
            f"product/data/state_register_baseline/verification_{BASELINE_COMMIT}.json "
            "(the accepted base's verification block, byte-exact, sha256-pinned), "
            "compared key-by-key against state/product.json"),
    }]


def _main(argv: list[str] | None = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--state", default=str(ROOT / "state" / "product.json"))
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    out = rows(Path(args.state))
    if args.json:
        print(json.dumps(out, indent=2, sort_keys=True))
    else:
        for row in out:
            print(f"[{row['status']}] {row['claim']}")
            if row["status"] != "PASS":
                print("        observed:", json.dumps(row["observed"], sort_keys=True))
    return 0 if all(r["status"] == "PASS" for r in out) else 1


if __name__ == "__main__":
    raise SystemExit(_main())

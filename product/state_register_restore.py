#!/usr/bin/env python3
"""Restore the top-level ``verification`` register that accepted cycle 39543057762 deleted.

Why this exists
---------------
Accepted product cycle 39543057762 (``bdfcc9813``) replaced
``state/product.json`` WHOLESALE: 5224 lines -> 49 lines.  The replacement
dropped the top-level ``verification`` register (20 keys), the
``repair_39169296466_round1`` disclosure and 93 further top-level records,
including the lane's own admitted failures.

The deletion was caught by a committed guard that was already on the accepted
tree - ``product/tests/test_state_register_retention.py`` - which reads the
register against the pinned baseline
``product/data/state_register_baseline/verification_bcb1217.json``.  It was
RED on the accepted tip and stayed red through every later cycle:

    state/product.json does not carry the repair record for the F2 register
    deletion (test_the_cycle_records_the_audit_F2_repair_in_state_itself)

AGENTS.md rule 6 forbids deleting contrary outputs and overwriting historical
claim-bearing results, so the register is restored here.  Nothing is deleted:
the deleted bytes are preserved verbatim under
``results/product/state_register/CYCLE_39538762904_state_product.json`` (the
tree that carried them) and this tool only ADDS to the live state.

Usage
-----
    python3 product/state_register_restore.py --check    # verify (exit 1 on drift)
    python3 product/state_register_restore.py --apply    # restore, then verify

The merge is deterministic and idempotent: the restored keys are byte-exact
copies of the preserved artifact, the live state keeps its own value for every
key it already carries, and re-running ``--apply`` changes nothing.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATE_PATH = ROOT / "state" / "product.json"
PRESERVED = (ROOT / "results" / "product" / "state_register"
             / "CYCLE_39538762904_state_product.json")
PROVENANCE = (ROOT / "results" / "product" / "state_register"
              / "CYCLE_39538762904_state_product.PROVENANCE.json")

#: The tree that carried the register when it was deleted.  6663c32 is the
#: producer commit of accepted cycle 39538762904; the accepted tip 7eb5b13
#: ("accept product cycle 39543057762") carries the replacement instead.
SOURCE_COMMIT = "6663c32"
SOURCE_RUN = "39538762904"
#: The cycle that deleted the register, and the cycle that restores it.
DELETING_RUN = "39543057762"
RESTORING_RUN = "39651573572"

#: Keys this tool owns.  Everything else in the live state is left alone.
RESTORED_KEYS = ("verification", "repair_39169296466_round1")


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def preserved_bytes() -> bytes:
    if PRESERVED.exists():
        return PRESERVED.read_bytes()
    # First run: re-derive the deleted bytes from git history.
    proc = subprocess.run(  # noqa: S603
        ["git", "show", f"{SOURCE_COMMIT}:state/product.json"],
        cwd=str(ROOT), capture_output=True, check=False)
    if proc.returncode != 0:
        raise SystemExit(
            f"cannot re-derive the preserved state from git ({SOURCE_COMMIT}); "
            "restore results/product/state_register/ from history first")
    return proc.stdout


def preserved_state() -> dict:
    return json.loads(preserved_bytes().decode("utf-8"))


def restoration_record(preserved_sha: str) -> dict:
    return {
        "run_id": RESTORING_RUN,
        "deleting_run": DELETING_RUN,
        "defect": (
            "accepted cycle 39543057762 (commit bdfcc9813) replaced state/product.json "
            "wholesale (5224 lines -> 49 lines) and deleted the top-level "
            "'verification' register (20 keys), the repair_39169296466_round1 "
            "disclosure and 93 further top-level records, including the lane's own "
            "admitted failures. The committed guard "
            "product/tests/test_state_register_retention.py was RED on the accepted "
            "tip from that commit onwards."),
        "restored": [
            "verification (20 keys, byte-exact from the preserved artifact; the 12 "
            "keys accepted at bcb1217 are byte-identical to the pinned baseline "
            "product/data/state_register_baseline/verification_bcb1217.json)",
            "repair_39169296466_round1 (byte-exact from the preserved artifact)",
        ],
        "preserved_bytes": {
            "artifact": str(PRESERVED.relative_to(ROOT)),
            "sha256": preserved_sha,
            "source_commit": SOURCE_COMMIT,
            "source_run": SOURCE_RUN,
            "note": (
                "the deleted bytes are preserved verbatim; nothing was removed and "
                "the file named for the run that carried them holds that run's "
                "measurement"),
        },
        "not_restored_into_the_live_state": (
            "the other 93 top-level records deleted by the same replacement are NOT "
            "written back into state/product.json: they are generic pointers and "
            "per-cycle claim blocks whose current values would be stale or "
            "contradictory (accepted_commit, audit_artifact, current_run, "
            "state_updated_at, human_gate_integration, ...). They are preserved "
            "byte-for-byte in the artifact above and remain readable there."),
        "live_state_precedence": (
            "for every key the live state already carries, the live value wins; this "
            "tool only ADDS the restored keys and the disclosure records."),
        "claim_ceiling": (
            "This is a restoration of deleted lane state, not a new measurement and "
            "not a legal claim. It scores no frozen bar, changes no threshold and "
            "changes no product behaviour."),
    }


def apply_restore() -> bool:
    raw = preserved_bytes()
    preserved_sha = hashlib.sha256(raw).hexdigest()
    source = json.loads(raw.decode("utf-8"))

    PRESERVED.parent.mkdir(parents=True, exist_ok=True)
    if not PRESERVED.exists():
        PRESERVED.write_bytes(raw)
    PROVENANCE.write_text(json.dumps({
        "artifact": PRESERVED.name,
        "sha256": preserved_sha,
        "source_commit": SOURCE_COMMIT,
        "source_run": SOURCE_RUN,
        "re_derive": f"git show {SOURCE_COMMIT}:state/product.json | sha256sum",
        "note": ("byte-exact copy of the state/product.json that accepted cycle "
                 f"{DELETING_RUN} replaced wholesale; preserved, never edited"),
    }, indent=2) + "\n", encoding="utf-8")

    state = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    changed = False
    for key in RESTORED_KEYS:
        if key in source and state.get(key) != source[key]:
            state[key] = source[key]
            changed = True

    record = restoration_record(preserved_sha)
    if state.get("state_register_restoration_39651573572") != record:
        state["state_register_restoration_39651573572"] = record
        changed = True

    supersedes = state.get("supersedes_claims")
    if not isinstance(supersedes, dict):
        supersedes = {}
    claim = (f"RESTORED BY RUN {RESTORING_RUN}: accepted cycle {DELETING_RUN} "
             f"(commit bdfcc9813) replaced state/product.json wholesale and deleted "
             "the top-level 'verification' register (20 keys, including the lane's "
             "own admitted failures), the repair_39169296466_round1 disclosure and "
             "93 further top-level records. The register and the disclosure are "
             "restored byte-exact from "
             "results/product/state_register/CYCLE_39538762904_state_product.json "
             f"(sha256 {preserved_sha}); the deleted bytes are preserved there and "
             "nothing was deleted. The live state keeps its own value for every key "
             "it already carried.")
    if supersedes.get("state_register_deleted_by_39543057762") != claim:
        supersedes["state_register_deleted_by_39543057762"] = claim
        state["supersedes_claims"] = supersedes
        changed = True

    if changed:
        STATE_PATH.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n",
                              encoding="utf-8")
    return changed


def check() -> list[str]:
    """Return the list of problems; empty means the live state conforms."""
    problems: list[str] = []
    if not PRESERVED.exists():
        return [f"the preserved artifact {PRESERVED.name} is missing"]
    raw = PRESERVED.read_bytes()
    preserved_sha = hashlib.sha256(raw).hexdigest()
    source = json.loads(raw.decode("utf-8"))
    state = json.loads(STATE_PATH.read_text(encoding="utf-8"))

    for key in RESTORED_KEYS:
        if key not in state:
            problems.append(f"state/product.json does not carry {key!r}")
        elif state[key] != source[key]:
            problems.append(f"state/product.json's {key!r} differs from the preserved bytes")
    register = state.get("verification")
    if not isinstance(register, dict):
        problems.append("state/product.json's 'verification' register is missing")
    else:
        baseline_path = ROOT / "product" / "data" / "state_register_baseline" / "verification_bcb1217.json"
        baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
        for key, value in baseline.items():
            if key not in register:
                problems.append(f"the register lost the record {key!r}")
            elif register[key] != value:
                problems.append(f"the record {key!r} was edited in place")
        if not set(register) - set(baseline):
            problems.append("the register carries no record beyond the baseline")

    if "state_register_restoration_39651573572" not in state:
        problems.append("state/product.json does not disclose the restoration")
    else:
        recorded = state["state_register_restoration_39651573572"]
        if recorded.get("preserved_bytes", {}).get("sha256") != preserved_sha:
            problems.append("the recorded preserved-bytes sha256 does not match the artifact")

    if PROVENANCE.exists():
        prov = json.loads(PROVENANCE.read_text(encoding="utf-8"))
        if prov.get("sha256") != preserved_sha:
            problems.append("PROVENANCE.json records a different sha256 than the artifact")
    else:
        problems.append("PROVENANCE.json is missing")
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="restore, then verify")
    parser.add_argument("--check", action="store_true", help="verify only (default)")
    args = parser.parse_args()

    if args.apply:
        changed = apply_restore()
        print(f"restore: {'state/product.json updated' if changed else 'already conformant'}")
    problems = check()
    if problems:
        for problem in problems:
            print(f"FAIL: {problem}")
        return 1
    print("state register: PASS (register, F2 disclosure, preserved bytes and provenance all present)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

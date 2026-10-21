#!/usr/bin/env python3
"""Restore the top-level ``verification`` register that accepted cycles deleted.

Why this exists
---------------
Accepted product cycle 39543057762 (``bdfcc9813``) replaced
``state/product.json`` WHOLESALE: 5224 lines -> 49 lines.  The replacement
dropped the top-level ``verification`` register (20 keys), the
``repair_39169296466_round1`` disclosure and 93 further top-level records,
including the lane's own admitted failures.

That deletion was caught by a committed guard that was already on the accepted
tree - ``product/tests/test_state_register_retention.py`` - which reads the
register against the pinned baseline
``product/data/state_register_baseline/verification_bcb1217.json``.  It was
RED on the accepted tip and stayed red through every later cycle.

**The same thing happened again.**  Accepted product cycle 39660515863
(``03b4bc6``) replaced the register a second time: the live 20-key register
became a 13-key block that carried NONE of the 12 records accepted at
``bcb1217``.  ``product/tests/test_state_register_retention.py`` was RED on
that accepted tip too, and so was the one-command ledger
(``product/cycle_verify.py --only guards``), because the ledger re-derives
this very guard.

Why the deletion could happen twice
-----------------------------------
The first version of this tool RESTORED by replacing the whole ``verification``
block with the preserved bytes, while its own docstring claimed "the live state
keeps its own value for every key it already carried".  It did not: the live
register's own records were dropped by the restore itself.  So the tool
enforced "the register equals the preserved artifact" - a rule that made
shrinkage the tool's own default - and the next wholesale replacement went
unnoticed.

This version therefore MERGES: the live state keeps its own value for every key
it already carries, and the preserved keys are added.  The register may GROW
and never SHRINK silently, which is the contract the guard in
``product/state_register.py`` enforces.

What is preserved, and where
----------------------------
Nothing is deleted.  Every set of bytes that was replaced is preserved under
``results/product/state_register/`` under the run that carried it:

* ``CYCLE_39538762904_state_product.json`` - the bytes deleted by 39543057762;
* ``CYCLE_39651573572_state_product.json`` - the bytes deleted by 39660515863;
* ``CYCLE_39660515863_state_product.json`` - the bytes 39660515863 itself
  wrote, preserved so the replacement this cycle undoes is still readable.

Usage
-----
    python3 product/state_register_restore.py --check    # verify (exit 1 on drift)
    python3 product/state_register_restore.py --apply    # restore, then verify

The merge is deterministic and idempotent: re-running ``--apply`` changes
nothing.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
STATE_PATH = ROOT / "state" / "product.json"
REGISTER_DIR = ROOT / "results" / "product" / "state_register"


def _restoration(record_key: str, deleting_run: str, restoring_run: str,
                 artifact: str, source_commit: str, source_run: str,
                 restored_keys: tuple[str, ...], record: dict[str, Any],
                 claim_key: str, claim: str) -> dict[str, Any]:
    return {
        "record_key": record_key,
        "deleting_run": deleting_run,
        "restoring_run": restoring_run,
        "artifact": artifact,
        "source_commit": source_commit,
        "source_run": source_run,
        "restored_keys": list(restored_keys),
        "record": record,
        "claim_key": claim_key,
        "claim": claim,
    }


#: The first deletion.  The disclosure record and the supersession claim are
#: reproduced byte-exact from the state that cycle 39651573572 wrote (commit
#: ``fe30b0d``); only the artifact path and the preserved sha256 are
#: substituted, and both are fixed values, so the rendered bytes are identical.
RECORD_39651573572 = {
    "run_id": "39651573572",
    "deleting_run": "39543057762",
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
        "artifact": "results/product/state_register/CYCLE_39538762904_state_product.json",
        "sha256": "{sha256}",
        "source_commit": "6663c32",
        "source_run": "39538762904",
        "note": ("the deleted bytes are preserved verbatim; nothing was removed "
                 "and the file named for the run that carried them holds that "
                 "run's measurement"),
    },
    "not_restored_into_the_live_state": (
        "the other 93 top-level records deleted by the same replacement are NOT "
        "written back into state/product.json: they are generic pointers and "
        "per-cycle claim blocks whose current values would be stale or "
        "contradictory (accepted_commit, audit_artifact, current_run, "
        "state_updated_at, human_gate_integration, ...). They are preserved "
        "byte-for-byte in the artifact above and remain readable there."),
    "live_state_precedence": (
        "for every key the live state already carries, the live value wins; "
        "this tool only ADDS the restored keys and the disclosure records."),
    "claim_ceiling": (
        "This is a restoration of deleted lane state, not a new measurement and "
        "not a legal claim. It scores no frozen bar, changes no threshold and "
        "changes no product behaviour."),
}

CLAIM_39543057762 = (
    "RESTORED BY RUN 39651573572: accepted cycle 39543057762 (commit bdfcc9813) "
    "replaced state/product.json wholesale and deleted the top-level "
    "'verification' register (20 keys, including the lane's own admitted "
    "failures), the repair_39169296466_round1 disclosure and 93 further "
    "top-level records. The register and the disclosure are restored byte-exact "
    "from results/product/state_register/CYCLE_39538762904_state_product.json "
    "(sha256 {sha256}); the deleted bytes are preserved there and nothing was "
    "deleted. The live state keeps its own value for every key it already "
    "carried."
)

#: The second deletion.  This cycle's own disclosure.
RECORD_39674781875 = {
    "run_id": "39674781875",
    "deleting_run": "39660515863",
    "defect": (
        "accepted cycle 39660515863 (commit 03b4bc6) replaced the register a "
        "SECOND time: the live 20-key 'verification' block became a 13-key "
        "block carrying NONE of the 12 records accepted at bcb1217, and the "
        "repair_39169296466_round1 disclosure, the "
        "state_register_restoration_39651573572 disclosure, the "
        "supersedes_claims block and the cycle_39422322667 delivery record were "
        "dropped with it. The committed guard "
        "product/tests/test_state_register_retention.py and the one-command "
        "ledger (product/cycle_verify.py --only guards) were RED on that "
        "accepted tip; the deletion reached the accepted tree because the "
        "first version of this tool RESTORED by replacing the whole register "
        "instead of merging it, so the restore itself dropped the live "
        "register's own records."),
    "restored": [
        "verification (the 20 keys carried by the state of run 39651573572, "
        "merged with - not replaced by - the live 13-key block of run "
        "39660515863; the 12 keys accepted at bcb1217 are byte-identical to "
        "the pinned baseline "
        "product/data/state_register_baseline/verification_bcb1217.json)",
        "repair_39169296466_round1 (byte-exact from the preserved artifact)",
        "state_register_restoration_39651573572 (byte-exact from the preserved "
        "artifact)",
        "supersedes_claims (merged, the live block keeps its own values)",
        "cycle_39422322667_vertical_slice_delivery (byte-exact from the "
        "preserved artifact)",
    ],
    "preserved_bytes": {
        "artifact": "results/product/state_register/CYCLE_39651573572_state_product.json",
        "sha256": "{sha256}",
        "source_commit": "fe30b0d",
        "source_run": "39651573572",
        "note": ("the deleted bytes are preserved verbatim; nothing was removed "
                 "and the file named for the run that carried them holds that "
                 "run's measurement"),
    },
    "not_restored_into_the_live_state": (
        "the state that accepted cycle 39660515863 wrote is preserved verbatim "
        "in results/product/state_register/CYCLE_39660515863_state_product.json "
        "and remains readable there; the live register is the MERGE of both "
        "registers, so neither cycle's own records are lost."),
    "live_state_precedence": (
        "for every key the live state already carries, the live value wins; "
        "this tool only ADDS the preserved keys and the disclosure records, so "
        "the register can grow and never shrinks silently."),
    "claim_ceiling": (
        "This is a restoration of deleted lane state, not a new measurement and "
        "not a legal claim. It scores no frozen bar, changes no threshold and "
        "changes no product behaviour."),
}

CLAIM_39660515863 = (
    "RESTORED BY RUN 39674781875: accepted cycle 39660515863 (commit 03b4bc6) "
    "replaced state/product.json wholesale and deleted the top-level "
    "'verification' register for the second time: the live 20-key register "
    "became a 13-key block carrying NONE of the 12 records accepted at "
    "bcb1217, and the repair_39169296466_round1 disclosure, the "
    "state_register_restoration_39651573572 disclosure, the supersedes_claims "
    "block and the cycle_39422322667 delivery record were dropped with it. The "
    "register and the disclosures are restored byte-exact from "
    "results/product/state_register/CYCLE_39651573572_state_product.json "
    "(sha256 {sha256}); the deleted bytes are preserved there and nothing was "
    "deleted. The live state keeps its own value for every key it already "
    "carried."
)

RESTORATIONS = (
    _restoration(
        record_key="state_register_restoration_39651573572",
        deleting_run="39543057762",
        restoring_run="39651573572",
        artifact="CYCLE_39538762904_state_product.json",
        source_commit="6663c32",
        source_run="39538762904",
        restored_keys=("verification", "repair_39169296466_round1"),
        record=RECORD_39651573572,
        claim_key="state_register_deleted_by_39543057762",
        claim=CLAIM_39543057762,
    ),
    _restoration(
        record_key="state_register_restoration_39674781875",
        deleting_run="39660515863",
        restoring_run="39674781875",
        artifact="CYCLE_39651573572_state_product.json",
        source_commit="fe30b0d",
        source_run="39651573572",
        restored_keys=(
            "verification",
            "repair_39169296466_round1",
            "state_register_restoration_39651573572",
            "supersedes_claims",
            "cycle_39422322667_vertical_slice_delivery",
        ),
        record=RECORD_39674781875,
        claim_key="state_register_deleted_by_39660515863",
        claim=CLAIM_39660515863,
    ),
)

#: Bytes that are preserved for the record but are NOT a restoration source:
#: they are the replacement itself, kept readable after this cycle undoes it.
PRESERVED_ONLY = (
    {
        "artifact": "CYCLE_39660515863_state_product.json",
        "source_commit": "03b4bc6",
        "source_run": "39660515863",
        "note": ("the state/product.json that accepted cycle 39660515863 wrote; "
                 "preserved verbatim before this cycle restored the register it "
                 "deleted, so nothing is lost when the live state moves on"),
    },
)

#: Inside the ``verification`` register, the records whose VALUE is
#: claim-bearing: they must survive byte-exact.  Everything else in the
#: register is a per-cycle pointer (a timestamp, a run id, an artifact path)
#: that later cycles are expected to move.
CLAIM_BEARING_REGISTER_KEYS = (
    "durable_actions_run",
    "durable_run_note",
    "evidence_reports",
    "latency_budget_9a",
    "latest_reality_check",
    "live_clickable_slice_this_cycle",
    "live_legs_this_run",
    "pre_existing_collection_errors",
    "product_integration_tests",
    "repair_39172315384_round1",
    "resume_39014141628",
    "status",
    "verified_on",
)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git_show(commit: str, path: str) -> bytes:
    proc = subprocess.run(  # noqa: S603
        ["git", "show", f"{commit}:{path}"],
        cwd=str(ROOT), capture_output=True, check=False)
    if proc.returncode != 0:
        raise SystemExit(
            f"cannot re-derive {path} from git ({commit}); restore "
            "results/product/state_register/ from history first")
    return proc.stdout


def _preserved_path(artifact: str) -> Path:
    return REGISTER_DIR / artifact


def _provenance_path(artifact: str) -> Path:
    return REGISTER_DIR / artifact.replace(".json", ".PROVENANCE.json")


def _render(template: Any, sha256: str) -> Any:
    if isinstance(template, str):
        return template.replace("{sha256}", sha256)
    if isinstance(template, dict):
        return {key: _render(value, sha256) for key, value in template.items()}
    if isinstance(template, list):
        return [_render(value, sha256) for value in template]
    return template


def preserved_bytes(source: dict[str, Any]) -> bytes:
    """The bytes of the preserved artifact, materialised from git if needed."""
    path = _preserved_path(source["artifact"])
    if path.exists():
        return path.read_bytes()
    raw = _git_show(source["source_commit"], "state/product.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    return raw


def _merge_into_live(state: dict[str, Any], source_state: dict[str, Any],
                     restored_keys: tuple[str, ...]) -> list[str]:
    """Merge the preserved keys into the live state; the live value wins.

    Returns the list of keys that were added or changed.  Dicts are merged key
    by key (so the register can grow); every other type keeps the LIVE value.
    """
    changed: list[str] = []
    for key in restored_keys:
        if key not in source_state:
            continue
        preserved = source_state[key]
        live = state.get(key)
        if isinstance(preserved, dict) and isinstance(live, dict):
            merged = dict(preserved)
            merged.update(live)  # the live value wins for every key it carries
            if merged != live:
                state[key] = merged
                changed.append(key)
        elif key not in state:
            state[key] = preserved
            changed.append(key)
    return changed


def apply_restore() -> bool:
    state = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    changed = False

    for entry in PRESERVED_ONLY:
        path = _preserved_path(entry["artifact"])
        if path.exists():
            continue
        raw = _git_show(entry["source_commit"], "state/product.json")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
        _provenance_path(entry["artifact"]).write_text(json.dumps({
            "artifact": entry["artifact"],
            "sha256": hashlib.sha256(raw).hexdigest(),
            "source_commit": entry["source_commit"],
            "source_run": entry["source_run"],
            "re_derive": f"git show {entry['source_commit']}:state/product.json | sha256sum",
            "note": entry["note"],
        }, indent=2) + "\n", encoding="utf-8")
        changed = True

    for restoration in RESTORATIONS:
        raw = preserved_bytes(restoration)
        preserved_sha = hashlib.sha256(raw).hexdigest()
        source_state = json.loads(raw.decode("utf-8"))
        provenance = _provenance_path(restoration["artifact"])
        if not provenance.exists():
            # A provenance file that already exists is HISTORY: it is never
            # rewritten, because "preserved, never edited" applies to the
            # provenance of a preserved artifact as much as to the artifact.
            provenance.write_text(json.dumps({
                "artifact": restoration["artifact"],
                "sha256": preserved_sha,
                "source_commit": restoration["source_commit"],
                "source_run": restoration["source_run"],
                "re_derive": (f"git show {restoration['source_commit']}:state/product.json "
                              "| sha256sum"),
                "note": ("byte-exact copy of the state/product.json that accepted "
                         f"cycle {restoration['deleting_run']} replaced; preserved, "
                         "never edited"),
            }, indent=2) + "\n", encoding="utf-8")

        if _merge_into_live(state, source_state,
                            restoration["restored_keys"]):
            changed = True

        record = _render(restoration["record"], preserved_sha)
        if state.get(restoration["record_key"]) != record:
            state[restoration["record_key"]] = record
            changed = True

        supersedes = state.get("supersedes_claims")
        if not isinstance(supersedes, dict):
            supersedes = {}
        claim = _render(restoration["claim"], preserved_sha)
        if supersedes.get(restoration["claim_key"]) != claim:
            supersedes[restoration["claim_key"]] = claim
            state["supersedes_claims"] = supersedes
            changed = True

    if changed:
        STATE_PATH.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n",
                              encoding="utf-8")
    return changed


def check() -> list[str]:
    """Return the list of problems; empty means the live state conforms."""
    problems: list[str] = []
    state = json.loads(STATE_PATH.read_text(encoding="utf-8"))

    for entry in PRESERVED_ONLY:
        path = _preserved_path(entry["artifact"])
        if not path.exists():
            problems.append(f"the preserved artifact {entry['artifact']} is missing")
            continue
        prov = _provenance_path(entry["artifact"])
        if not prov.exists():
            problems.append(f"{prov.name} is missing")
            continue
        recorded = json.loads(prov.read_text(encoding="utf-8"))
        digest = sha256_file(path)
        if recorded.get("sha256") != digest:
            problems.append(f"{prov.name} records a different sha256 than the artifact")

    for restoration in RESTORATIONS:
        path = _preserved_path(restoration["artifact"])
        if not path.exists():
            problems.append(f"the preserved artifact {restoration['artifact']} is missing")
            continue
        raw = path.read_bytes()
        preserved_sha = hashlib.sha256(raw).hexdigest()
        source_state = json.loads(raw.decode("utf-8"))

        for key in restoration["restored_keys"]:
            if key not in source_state:
                continue
            if key not in state:
                problems.append(
                    f"state/product.json does not carry {key!r} (deleted by "
                    f"{restoration['deleting_run']})")
                continue
            preserved = source_state[key]
            live = state[key]
            if key == "verification":
                if not isinstance(live, dict):
                    problems.append("state/product.json's 'verification' register is missing")
                    continue
                for sub_key, value in preserved.items():
                    if sub_key not in live:
                        problems.append(f"the register lost the record {sub_key!r}")
                    elif sub_key in CLAIM_BEARING_REGISTER_KEYS and live[sub_key] != value:
                        problems.append(f"the record {sub_key!r} was edited in place")
            elif isinstance(preserved, dict) and isinstance(live, dict):
                for sub_key, value in preserved.items():
                    if sub_key not in live:
                        problems.append(f"{key!r} lost the record {sub_key!r}")
                    elif live[sub_key] != value:
                        problems.append(f"{key!r} edited the record {sub_key!r} in place")
            elif live != preserved:
                problems.append(f"{key!r} differs from the preserved bytes")

        record_key = restoration["record_key"]
        expected_record = _render(restoration["record"], preserved_sha)
        if record_key not in state:
            problems.append(f"state/product.json does not disclose the restoration "
                            f"({record_key})")
        elif state[record_key] != expected_record:
            problems.append(f"the restoration disclosure {record_key!r} was edited in place")

        supersedes = state.get("supersedes_claims")
        expected_claim = _render(restoration["claim"], preserved_sha)
        if not isinstance(supersedes, dict):
            problems.append("state/product.json's 'supersedes_claims' block is missing")
        elif supersedes.get(restoration["claim_key"]) != expected_claim:
            problems.append(f"the supersession claim {restoration['claim_key']!r} "
                            "was edited in place")

        prov = _provenance_path(restoration["artifact"])
        if not prov.exists():
            problems.append(f"{prov.name} is missing")
        else:
            prov_payload = json.loads(prov.read_text(encoding="utf-8"))
            if prov_payload.get("sha256") != preserved_sha:
                problems.append(f"{prov.name} records a different sha256 than the artifact")

    # The register must also still carry the baseline accepted at bcb1217.
    try:
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))
        from product import state_register
        diff = state_register.missing_or_changed(state)
        problems.extend(f"state register: {key} missing" for key in diff["missing"])
        problems.extend(f"state register: {key} edited in place"
                        for key in sorted(diff["changed"]))
        if diff["baseline_error"]:
            problems.append("the pinned state-register baseline could not be read")
    except Exception as exc:  # pragma: no cover - the guard must fail closed
        problems.append(f"the state-register guard could not run: {exc!r}")
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

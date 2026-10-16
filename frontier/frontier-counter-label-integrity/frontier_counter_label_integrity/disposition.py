"""In-scope, machine-readable provenance ledger for the audit artifact tree.

Why this module exists
----------------------
The audit tree ``results/audit/frontier/frontier-counter-label-integrity/`` is
written by the AUDIT job.  For eight consecutive dispatches (GitHub runs
38845649012 -> 38851515402) this team ALSO wrote its own "placement copies"
there, which is outside the workflow's ``Enforce team scope`` allow-list
(``.github/workflows/frontier-team.yml``, which the harness now mirrors
offline in :mod:`scope_guard`) and outside charter acceptance test (12).  Those
writes are what failed every one of those producer jobs and re-armed the
dispatch loop; this run stops them.

Stopping them means the producer can no longer amend anything in that tree, so
the provenance disclosure this team owes the gate reader has to live SOMEWHERE
it is allowed to write.  This module is that somewhere: it emits an in-scope
ledger under ``results/frontier/frontier-counter-label-integrity/`` that names
every audit-tree artifact, its sha256, its machine classification, and -- the
part prose cannot supply -- the team's DECLARED true provenance, flagging every
file where the two disagree.

The disagreement is not a defect to be hidden; it is evidence.  Run
38848314260 declared a residual weakness: a producer file carrying the complete
audit signature (``required_fixes`` + ``safe_to_integrate`` + ``team``) is
indistinguishable from a genuine independent audit by any test that reads the
file.  ``CYCLE_38839354961_GATE.json`` is exactly that case and is live in the
tree now, so the ledger records the mismatch rather than papering over it.  The
file is NOT edited or deleted: charter/constitution rule 6 forbids overwriting
or removing claim-bearing historical results, and the producer does not own that
tree in the first place.

Read-only.  Offline.  Deterministic: no clock, no network, sorted output, so
identical inputs produce a byte-identical ledger that can be re-hashed like any
other claim-bearing artifact.

    python3 -m frontier_counter_label_integrity.disposition --repo-root . --out <dir>
    python3 -m frontier_counter_label_integrity.cli --disposition --out <dir>
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from typing import Any

from .audit_contract import classify_gate_payload

TEAM_ID = "frontier-counter-label-integrity"

GATE_DIR = f"results/audit/frontier/{TEAM_ID}"
REPORT_DIR = f"reports/audit/frontier/{TEAM_ID}"
OUT_NAME = "AUDIT_TREE_PROVENANCE.json"

#: The team's own knowledge of which audit-tree gate artifacts are genuine
#: INDEPENDENT AUDIT output (written by the separate audit job) and which are
#: PRODUCER-AUTHORED PLACEMENT COPIES written by this team into a tree it does
#: not own.  This is the disclosure the artifacts themselves cannot carry.
#:
#: Sourced from state/frontier/frontier-counter-label-integrity.json
#: (artifacts.*_audit_placement_provenance_warning) and from the charter.
#: An empty value means "not asserted by this team".
DECLARED_PROVENANCE: dict[str, str] = {
    "CYCLE_38839354961_GATE.json": "PRODUCER_AUTHORED_PLACEMENT_COPY",
    "CYCLE_38841035773_GATE.json": "INDEPENDENT_AUDIT_OF_RECORD",
    "CYCLE_38845649012_GATE.json": "PRODUCER_AUTHORED_PLACEMENT_COPY",
    "CYCLE_38846758718_GATE.json": "PRODUCER_AUTHORED_PLACEMENT_COPY",
    "CYCLE_38848314260_GATE.json": "PRODUCER_AUTHORED_PLACEMENT_COPY",
    "CYCLE_38849513219_GATE.json": "PRODUCER_AUTHORED_PLACEMENT_COPY",
    "CYCLE_38849940657_GATE.json": "PRODUCER_AUTHORED_PLACEMENT_COPY",
    "CYCLE_38850302366_GATE.json": "PRODUCER_AUTHORED_PLACEMENT_COPY",
    "CYCLE_38850765576_GATE.json": "PRODUCER_AUTHORED_PLACEMENT_COPY",
    "CYCLE_38851515402_GATE.json": "PRODUCER_AUTHORED_PLACEMENT_COPY",
}

#: The single independent audit of record.  Everything else in the gate tree is
#: producer-authored, including any file whose machine class says otherwise.
AUDIT_OF_RECORD = "CYCLE_38841035773_GATE.json"

#: Declared provenance -> the machine class it SHOULD carry.  These are two
#: different vocabularies on purpose (the declared one is prose a human reads,
#: the machine one is the contract's routing label), so the comparison goes
#: through this explicit map rather than a string comparison that would report
#: every file as a mismatch.
DECLARED_TO_EXPECTED_MACHINE_CLASS: dict[str, str] = {
    "PRODUCER_AUTHORED_PLACEMENT_COPY": "producer_placement_copy",
    "INDEPENDENT_AUDIT_OF_RECORD": "independent_audit_of_record",
}


def _sha256(path: str) -> str:
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def gate_entries(repo_root: str) -> list[dict[str, Any]]:
    """One record per ``CYCLE_*_GATE.json``, sorted by filename."""
    d = os.path.join(repo_root, GATE_DIR)
    out: list[dict[str, Any]] = []
    if not os.path.isdir(d):
        return out
    for name in sorted(os.listdir(d)):
        if not (name.startswith("CYCLE_") and name.endswith("_GATE.json")):
            continue
        path = os.path.join(d, name)
        try:
            with open(path, encoding="utf-8") as fh:
                payload = json.load(fh)
            machine = classify_gate_payload(payload)
            gate = payload.get("gate")
            team = payload.get("team")
        except (ValueError, OSError) as exc:  # unreadable/corrupt -> recorded, not skipped
            machine, gate, team = "UNREADABLE", None, None
            payload = {"_error": str(exc)}
        declared = DECLARED_PROVENANCE.get(name)
        expected_machine = DECLARED_TO_EXPECTED_MACHINE_CLASS.get(declared or "")
        out.append(
            {
                "file": f"{GATE_DIR}/{name}",
                "sha256": _sha256(path),
                "declared_provenance": declared or "NOT_ASSERTED_BY_THIS_TEAM",
                "machine_class": machine,
                "gate_value": gate,
                "team": team,
                "carries_provenance_warning": bool(payload.get("artifact_provenance_warning")),
                "declaration_matches_machine_class": (
                    None if expected_machine is None else expected_machine == machine
                ),
            }
        )
    return out


def report_entries(repo_root: str) -> list[dict[str, Any]]:
    """One record per ``CYCLE_*.md`` in the reports audit tree, sorted."""
    d = os.path.join(repo_root, REPORT_DIR)
    out: list[dict[str, Any]] = []
    if not os.path.isdir(d):
        return out
    for name in sorted(os.listdir(d)):
        if not (name.startswith("CYCLE_") and name.endswith(".md")):
            continue
        path = os.path.join(d, name)
        out.append(
            {
                "file": f"{REPORT_DIR}/{name}",
                "sha256": _sha256(path),
                "declared_provenance": (
                    "INDEPENDENT_AUDIT_OF_RECORD"
                    if name == AUDIT_OF_RECORD.replace("_GATE.json", ".md")
                    else "PRODUCER_AUTHORED_PLACEMENT_COPY"
                ),
            }
        )
    return out


def build_ledger(repo_root: str = ".") -> dict[str, Any]:
    gates = gate_entries(repo_root)
    reports = report_entries(repo_root)
    mismatches = [g for g in gates if g["declaration_matches_machine_class"] is False]
    producer_authored = [g["file"] for g in gates
                         if g["declared_provenance"] == "PRODUCER_AUTHORED_PLACEMENT_COPY"]
    independent = [g["file"] for g in gates
                   if g["declared_provenance"] == "INDEPENDENT_AUDIT_OF_RECORD"]
    return {
        "schema": "frontier-counter-label-integrity/audit_tree_provenance/v1",
        "team_id": TEAM_ID,
        "audit_of_record": f"{GATE_DIR}/{AUDIT_OF_RECORD}",
        "counts": {
            "gate_files": len(gates),
            "report_files": len(reports),
            "producer_authored_placement_copies": len(producer_authored),
            "independent_audits_of_record": len(independent),
            "declaration_machine_class_mismatches": len(mismatches),
        },
        "independent_audits_of_record": independent,
        "producer_authored_placement_copies": producer_authored,
        "declaration_machine_class_mismatches": [
            {
                "file": g["file"],
                "sha256": g["sha256"],
                "declared_provenance": g["declared_provenance"],
                "machine_class": g["machine_class"],
                "gate_value": g["gate_value"],
                "carries_provenance_warning": g["carries_provenance_warning"],
                "why": (
                    "This file carries the COMPLETE independent-audit signature "
                    "(required_fixes + safe_to_integrate + team) and no "
                    "artifact_provenance_warning, so the contract's signature-based "
                    "routing classifies it as an audit of record. It was in fact "
                    "written by this team. No test reading the file can tell the "
                    "difference -- that is the residual weakness declared in run "
                    "38848314260, now realised in the live tree. The file is left "
                    "byte-for-byte untouched (rule 6: never overwrite or delete a "
                    "claim-bearing historical artifact) and is NOT to be read as an "
                    "independent gate."
                ),
            }
            for g in mismatches
        ],
        "gate_files": gates,
        "report_files": reports,
        "producer_write_policy": (
            "The producer does NOT write results/audit/** or reports/audit/**. Those "
            "paths are absent from the workflow's 'Enforce team scope' allow-list and "
            "from charter acceptance test (12); the eight dispatches 38845649012 -> "
            "38851515402 each failed the producer job at exactly that step. This "
            "ledger is the in-scope home of the provenance disclosure the placement "
            "copies used to carry in a tree the producer does not own."
        ),
        "claim_ceiling": (
            "This ledger reports artifact provenance only. It makes no claim that any "
            "decision IS supporting, contrary or limiting, proposes no fix, and is not "
            "an audit: it is a producer-written disclosure about who wrote which file."
        ),
    }


def render(ledger: dict[str, Any]) -> str:
    """Byte-stable JSON rendering (sorted keys, trailing newline)."""
    return json.dumps(ledger, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="disposition")
    ap.add_argument("--repo-root", default=".")
    ap.add_argument("--out", required=True, help="output DIRECTORY (in scope)")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args(argv)
    ledger = build_ledger(args.repo_root)
    os.makedirs(args.out, exist_ok=True)
    dest = os.path.join(args.out, OUT_NAME)
    with open(dest, "w", encoding="utf-8") as fh:
        fh.write(render(ledger))
    if not args.quiet:
        c = ledger["counts"]
        print(f"wrote {dest}")
        print(
            f"gate_files={c['gate_files']} independent={c['independent_audits_of_record']} "
            f"producer_copies={c['producer_authored_placement_copies']} "
            f"mismatches={c['declaration_machine_class_mismatches']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

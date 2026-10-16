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
import sys
from typing import Any

from .audit_contract import (
    INDEPENDENT,
    KNOWN_PRODUCER_AUTHORED_RUNS,
    PLACEMENT,
    TRUSTED_AUDIT_RUNS,
    UNCLASSIFIED,
    classify_gate_payload,
    load_gate_payload,
    run_id_of,
)
from .scope_guard import violations as scope_violations

TEAM_ID = "frontier-counter-label-integrity"

GATE_DIR = f"results/audit/frontier/{TEAM_ID}"
REPORT_DIR = f"reports/audit/frontier/{TEAM_ID}"
OUT_NAME = "AUDIT_TREE_PROVENANCE.json"

#: The team's own knowledge of which audit-tree gate artifacts are genuine
#: INDEPENDENT AUDIT output (written by the separate audit job) and which are
#: PRODUCER-AUTHORED PLACEMENT COPIES written by this team into a tree it does
#: not own.  This is the disclosure the artifacts themselves cannot carry.
#:
#: SCHEMA v2 SOURCED IT FROM RUN IDS INSTEAD OF A PER-FILE DICT.  The previous
#: version kept a hand-maintained ``DECLARED_PROVENANCE`` filename map, and that
#: map had two defects an adversarial review of run 38852056955 found:
#:
#: 1. It could only ever be BEHIND.  The audit job appends one genuine audit per
#:    successful dispatch, so a fresh audit is undeclared by construction and
#:    the suite went red on every dispatch (3 failures, reproduced).
#: 2. WORSE, ``report_entries`` fell back to
#:    ``PRODUCER_AUTHORED_PLACEMENT_COPY`` for every ``.md`` except the audit of
#:    record -- so an honest refresh would have committed a POSITIVE FALSE
#:    CLAIM that a genuine independent audit's markdown was producer-authored.
#:    A missing disclosure is a gap; a false one is a lie in a claim-bearing
#:    artifact.
#:
#: Run-id sets cannot drift that way: a new audit is ``UNDISCLOSED`` (named, not
#: absorbed) until the next cycle declares it, and nothing is ever mis-declared.
#: The sets live in :mod:`audit_contract` because the contract's anti-vacuity
#: invariant is anchored on the same knowledge.

#: Declared provenance -> the machine class it SHOULD carry.  These are two
#: different vocabularies on purpose (the declared one is prose a human reads,
#: the machine one is the contract's routing label), so the comparison goes
#: through this explicit map rather than a string comparison that would report
#: every file as a mismatch.
DECLARED_TO_EXPECTED_MACHINE_CLASS: dict[str, str] = {
    "PRODUCER_AUTHORED_PLACEMENT_COPY": PLACEMENT,
    "INDEPENDENT_AUDIT_OF_RECORD": INDEPENDENT,
}

#: The total three-valued relation between a declaration and a machine fact.
#: v1 carried ``declaration_matches_machine_class: True|False|None`` and the
#: suite then asserted ``is True`` over every non-mismatch entry, which an
#: UNDECLARED file (``None``) could never satisfy -- the trap that made the
#: suite red twice over.  ``relation`` is total and the tests read it.
#: The audit of record the gate reader is pointed at.  Every other gate artifact
#: in the tree is producer-authored, INCLUDING any file whose machine class says
#: otherwise -- that is precisely what the mismatches list exists to say out
#: loud.  New genuine audits are added to ``TRUSTED_AUDIT_RUNS`` in
#: :mod:`audit_contract`, not to this name.
AUDIT_OF_RECORD = "CYCLE_38841035773_GATE.json"

AGREES = "AGREES"
CONTRADICTED = "CONTRADICTED"
UNDISCLOSED = "UNDISCLOSED"


def declared_provenance(run_id: str | None) -> str | None:
    """What this team asserts the true origin of ``run_id``'s artifact is.

    ``None`` means "this team makes no assertion yet" -- which is the honest
    answer for an artifact created after this team's last disclosure refresh,
    and is reported as UNDISCLOSED rather than guessed at.
    """
    if run_id is None:
        return None
    if run_id in TRUSTED_AUDIT_RUNS:
        return "INDEPENDENT_AUDIT_OF_RECORD"
    if run_id in KNOWN_PRODUCER_AUTHORED_RUNS:
        return "PRODUCER_AUTHORED_PLACEMENT_COPY"
    return None


def _relation(declared: str | None, machine_class: str) -> str:
    """TOTAL: every entry gets exactly one of three relations. No ``None``."""
    expected = DECLARED_TO_EXPECTED_MACHINE_CLASS.get(declared or "")
    if expected is None:
        return UNDISCLOSED
    return AGREES if expected == machine_class else CONTRADICTED


def _why(gate: dict[str, Any], payload: dict[str, Any]) -> str:
    """An explanation computed from the ACTUAL (declared, machine) triple.

    v1 attached one hard-coded narrative -- "this file carries the COMPLETE
    independent-audit signature and no artifact_provenance_warning" -- to every
    mismatch, including an unreadable file or one that lost its warning.  That
    sentence is demonstrably false for both, and loud-but-wrong is worse than
    quiet: a reviewer who sees two mismatches with the same explanation stops
    reading.
    """
    machine = gate["machine_class"]
    if machine == UNCLASSIFIED and "__unreadable__" in payload:
        return (
            "The file could not be parsed as JSON, so its machine class could not be "
            "established. It is reported UNCLASSIFIED and fails the audit-tree contract "
            "rather than being skipped. The bytes are left untouched; re-hashing them is "
            "how the corruption is detected."
        )
    if machine == UNCLASSIFIED:
        return (
            "The file matches neither contract: it lacks the independent-audit signature "
            "and does not self-declare as a producer placement copy. Signature-based "
            "routing refuses to pick a contract for it, so it is UNCLASSIFIED and fails "
            "rather than quietly inheriting the weaker one."
        )
    if machine == INDEPENDENT and gate["declared_provenance"] == "PRODUCER_AUTHORED_PLACEMENT_COPY":
        return (
            "This file carries the COMPLETE independent-audit signature (required_fixes + "
            "safe_to_integrate + team) and no artifact_provenance_warning, so the contract's "
            "signature-based routing classifies it as an audit of record. It was in fact "
            "written by this team. No test reading the file can tell the difference -- that "
            "is the residual weakness declared in run 38848314260, now realised in the live "
            "tree. The file is left byte-for-byte untouched (rule 6: never overwrite or delete "
            "a claim-bearing historical artifact) and is NOT to be read as an independent "
            "gate. It is also, as of the run 38852056955 repair, barred from satisfying the "
            "anti-vacuity invariant that requires a genuine audit of record to exist."
        )
    return (
        f"Machine class {machine!r} does not match the declared provenance "
        f"{gate['declared_provenance']!r}. Recorded rather than corrected: the producer does "
        f"not own this tree and must not edit it."
    )


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
        payload = load_gate_payload(path)
        machine = classify_gate_payload(payload)
        declared = declared_provenance(run_id_of(name))
        out.append(
            {
                "file": f"{GATE_DIR}/{name}",
                "run_id": run_id_of(name),
                "sha256": _sha256(path),
                "declared_provenance": declared or "NOT_ASSERTED_BY_THIS_TEAM",
                "machine_class": machine,
                "relation": _relation(declared, machine),
                "gate_value": payload.get("gate"),
                "team": payload.get("team"),
                "carries_provenance_warning": bool(payload.get("artifact_provenance_warning")),
                "declaration_matches_machine_class": (
                    None if declared is None
                    else DECLARED_TO_EXPECTED_MACHINE_CLASS[declared] == machine
                ),
            }
        )
    return out


def report_entries(repo_root: str, gate_relations: dict[str, str] | None = None) -> list[dict[str, Any]]:
    """One record per ``CYCLE_*.md`` in the reports audit tree, sorted.

    Declared provenance is DERIVED FROM THE RUN ID, never defaulted.  v1 fell
    back to ``PRODUCER_AUTHORED_PLACEMENT_COPY`` for every markdown except the
    audit of record's, which would have committed a positive false claim about
    a genuine independent audit's own report.  An ``.md`` with no known run is
    now ``UNDISCLOSED``, and one with no sibling gate artifact is an ORPHAN,
    which is a different defect and is named as such.

    Markdown carries no machine class of its own, so its relation is inherited
    from its gate sibling: a contradiction there is the sibling's contradiction.
    """
    gate_relations = gate_relations or {}
    d = os.path.join(repo_root, REPORT_DIR)
    out: list[dict[str, Any]] = []
    if not os.path.isdir(d):
        return out
    for name in sorted(os.listdir(d)):
        if not (name.startswith("CYCLE_") and name.endswith(".md")):
            continue
        path = os.path.join(d, name)
        run = name[len("CYCLE_"):-len(".md")]
        declared = declared_provenance(run)
        sibling = gate_relations.get(run)
        if sibling == CONTRADICTED:
            relation = CONTRADICTED
        elif declared is None:
            relation = UNDISCLOSED
        else:
            relation = AGREES
        out.append(
            {
                "file": f"{REPORT_DIR}/{name}",
                "run_id": run,
                "sha256": _sha256(path),
                "declared_provenance": declared or "NOT_ASSERTED_BY_THIS_TEAM",
                "relation": relation,
                "sibling_gate_relation": sibling,
                "orphaned_report": sibling is None,
            }
        )
    return out


def build_ledger(repo_root: str = ".") -> dict[str, Any]:
    gates = gate_entries(repo_root)
    relations = {g["run_id"]: g["relation"] for g in gates if g["run_id"]}
    reports = report_entries(repo_root, relations)
    mismatches = [g for g in gates if g["relation"] == CONTRADICTED]
    undisclosed = [g for g in gates if g["relation"] == UNDISCLOSED]
    payloads = {
        g["file"].split("/")[-1]: load_gate_payload(
            os.path.join(repo_root, g["file"])
        )
        for g in gates
    }
    producer_authored = [g["file"] for g in gates
                         if g["declared_provenance"] == "PRODUCER_AUTHORED_PLACEMENT_COPY"]
    independent = [g["file"] for g in gates
                   if g["declared_provenance"] == "INDEPENDENT_AUDIT_OF_RECORD"]
    return {
        "schema": "frontier-counter-label-integrity/audit_tree_provenance/v2",
        "team_id": TEAM_ID,
        "audit_of_record": f"{GATE_DIR}/{AUDIT_OF_RECORD}",
        "audit_of_record_runs": sorted(TRUSTED_AUDIT_RUNS),
        "coverage": {
            "closed_over": "the audit tree as it stands when this ledger was generated",
            "why_not_a_closure_assertion_over_the_live_tree": (
                "The audit job appends one genuine independent audit to the audit tree "
                "after every successful producer dispatch (frontier-team.yml: audit job "
                "runs `if: needs.team.result == 'success'`, and its output is merged "
                "into the accepted base). The producer therefore NEVER sees its own "
                "run's audit and the tree it sees grows by one file per dispatch. "
                "Schema v1 asserted that this committed ledger equalled a fresh build "
                "over the live tree; that assertion was unsatisfiable by construction "
                "and made the suite red on every dispatch. The ledger is now an "
                "append-only RECORD: every file it names must still exist with the "
                "recorded sha256 (nothing edited, nothing deleted), and files it does "
                "not name yet are reported as UNDISCLOSED rather than treated as "
                "corruption. See results/frontier/<team>/AUDIT_TREE_PROVENANCE.schema.md."
            ),
        },
        "counts": {
            "gate_files": len(gates),
            "report_files": len(reports),
            "producer_authored_placement_copies": len(producer_authored),
            "independent_audits_of_record": len(independent),
            "declaration_machine_class_mismatches": len(mismatches),
            "undisclosed_gate_files": len(undisclosed),
            "orphaned_reports": len([r for r in reports if r["orphaned_report"]]),
        },
        "independent_audits_of_record": independent,
        "producer_authored_placement_copies": producer_authored,
        "declaration_machine_class_mismatches": [
            {
                **{k: g[k] for k in (
                    "file", "sha256", "run_id", "declared_provenance",
                    "machine_class", "gate_value", "carries_provenance_warning",
                )},
                "why": _why(g, payloads[g["file"].split("/")[-1]]),
            }
            for g in mismatches
        ],
        "undisclosed_gate_files": [
            {
                "file": g["file"],
                "sha256": g["sha256"],
                "run_id": g["run_id"],
                "machine_class": g["machine_class"],
                "gate_value": g["gate_value"],
                "why": (
                    "This team has not declared this artifact's provenance. The usual "
                    "cause is benign and structural: the audit job wrote it AFTER this "
                    "team's last disclosure refresh, so no producer can have declared it "
                    "in advance. It is NAMED here rather than silently absorbed, and the "
                    "next cycle declares it from the same TRUSTED_AUDIT_RUNS set the "
                    "audit contract's anti-vacuity invariant is anchored on."
                ),
            }
            for g in undisclosed
        ],
        "gate_files": gates,
        "report_files": reports,
        "producer_write_policy": (
            "The producer does NOT write results/audit/** or reports/audit/**. Those "
            "paths are absent from the workflow's 'Enforce team scope' allow-list and "
            "from charter acceptance test (12); the eight dispatches 38845649012 -> "
            "38851515402 each failed the producer job at exactly that step. This "
            "ledger is the in-scope home of the provenance disclosure the placement "
            "copies used to carry in a tree the producer does not own. disposition.py "
            "also refuses an --out outside that allow-list, so the loop cannot be "
            "re-armed by pointing this module at the audit tree."
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
    ap.add_argument("--out", required=True, help="output DIRECTORY (must be in scope)")
    ap.add_argument("--force", action="store_true",
                    help="overwrite an existing committed ledger")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args(argv)

    # THIS MODULE EXISTS BECAUSE THE PRODUCER MUST NOT WRITE THE AUDIT TREE.
    # Guarding only the live git status, as the earlier version did, left the
    # obvious re-arm: `disposition --out results/audit/frontier/<team>` wrote
    # AUDIT_TREE_PROVENANCE.json straight into the tree the workflow's "Enforce
    # team scope" step rejects, which is the eight-dispatch pathology all over
    # again. Refuse before writing, not after.
    #
    # Only IN-REPO destinations are judged: an --out outside the repository is
    # scratch space (the tests use tmp_path) and cannot dirty the tree.
    repo_abs = os.path.abspath(args.repo_root)
    out_abs = os.path.abspath(args.out)
    if os.path.commonpath([out_abs, repo_abs]) == repo_abs:
        rel = os.path.relpath(out_abs, repo_abs)
        bad = scope_violations([f"{rel}/{OUT_NAME}"])
        if bad:
            print(
                f"::error::refusing to write outside the producer allow-list: {bad[0]}\n"
                f"  (the audit tree belongs to the audit job; charter test 12 and the "
                f"workflow's 'Enforce team scope' step both forbid producer writes there)",
                file=sys.stderr,
            )
            return 3

    ledger = build_ledger(repo_abs)
    os.makedirs(out_abs, exist_ok=True)
    dest = os.path.join(out_abs, OUT_NAME)
    if os.path.exists(dest) and not args.force:
        with open(dest, encoding="utf-8") as fh:
            existing = fh.read()
        if existing != render(ledger):
            print(
                f"::error::{dest} exists and differs from a fresh build.\n"
                f"  The committed ledger is an append-only record of the audit tree; "
                f"silently replacing it would discard the evidence that a listed file "
                f"was edited or deleted. Refresh it deliberately with --force and "
                f"record why in the cycle report.",
                file=sys.stderr,
            )
            return 4
    with open(dest, "w", encoding="utf-8") as fh:
        fh.write(render(ledger))
    if not args.quiet:
        c = ledger["counts"]
        print(f"wrote {dest}")
        print(
            f"gate_files={c['gate_files']} independent={c['independent_audits_of_record']} "
            f"producer_copies={c['producer_authored_placement_copies']} "
            f"mismatches={c['declaration_machine_class_mismatches']} "
            f"undisclosed={c['undisclosed_gate_files']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

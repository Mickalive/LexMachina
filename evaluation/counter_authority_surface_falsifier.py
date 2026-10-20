#!/usr/bin/env python3
"""Mapping-free counter-authority surface falsifier on the packet-of-record V3.

WHY THIS INSTRUMENT EXISTS
--------------------------
The lane already owns the smallest executable retrieval/counter-authority falsifier
(``evaluation/mapping_free_recall_falsifier.py``, run 39225862749, verdict
PRODUCT_FALSIFIED).  That instrument has only ever been run on the served packet
``38839347028`` and the rebuilt packet ``rebuilt-39027045675``.  The PACKET OF
RECORD is ``39319405429`` (packet.json sha256
``32ac812626e679c357822543d0b2e78e62c0e95a9a1b233d1ec89d7cb7b6ac70``): the accepted
serve verdict, the frozen LABEL/GEOMETRY falsification battery and both standing
DO-NOT-SERVE orders are all pinned to those exact bytes.  The lane has therefore
never run its mapping-free retrieval / counter-authority falsifier on the bytes the
whole product verdict rests on.

This instrument closes that hole by reusing the accepted measurement functions
UNCHANGED on V3's exact bytes.  It adds no threshold, no gate, no tokeniser, no
stoplist and no rubric, and it rebuilds/re-scores no Frontier candidate.

REUSE-FIRST
-----------
Every measurement rule is imported from accepted lane code and is NOT
re-derived here:

* ``evaluation.mapping_free_recall_falsifier`` - ``measure``, ``non_vacuity``,
  ``verdict_of``, ``sha256_file``, ``numeric_environment``, ``resolve_mount``,
  ``mount_head`` and the frozen exit-code constants.
* ``evaluation.retrieval_gate/frozen_retrieval_benchmark.json`` - the frozen
  slug/authority/counter-id spec, read at run time.
* ``evaluation/frozen_bars/RULES_LABEL.json`` ``rubric.scored_statuses`` - the
  frozen counter-status vocabulary, read at run time, never hardcoded.
* ``evaluation.subject_match_audit`` and ``evaluation.retrieval_gate.gates`` -
  reached transitively through the accepted measurement functions.

The instrument adds no new threshold, no new bar and no new rule.  Every numeric
condition it uses is either an accepted constant imported from the modules above
or an exact structural identity.

CLAIM CEILING (verbatim in force)
---------------------------------
This instrument establishes exactly one thing: on the packet-of-record V3's
(``39319405429``) exact bytes, whether the served bundles satisfy the frozen
mapping-free gates.  It does NOT meet, move or re-derive the frozen absolute
LABEL_SOUND or GEOMETRY_SOUND bars, which stay REPORTED-ONLY.  It does NOT lift
the accepted DO-NOT-SERVE order on packet 38839347028 nor DO-NOT-SERVE-UNCHANGED
on rebuilt-39027045675, and it does NOT change V3's BUILT_NOT_SERVED /
WITHHELD_PENDING_SERVE status.  It does NOT certify admission of any packet;
admission stays fail-closed.  It does NOT claim the map helps a jurist; that
remains the human product gate's question.  It does NOT build, tune, score or
re-score any candidate for any Frontier team; where its numbers touch the
accepted frontier-counter-label-emission numbers they are published BESIDE them
with any divergence named as the headline.  It runs no obsolete universal-174k
benchmark.  ``human_gate_ready`` stays false.

Exit codes
----------
0  PASS_NO_FALSIFICATION   - every mapping-free gate passed and every non-vacuity
                             control held on V3's exact bytes.
1  PRODUCT_FALSIFIED       - at least one mapping-free gate failed on V3's exact
                             bytes, naming packet / question / gate / measured values.
2  NOT_MEASURED_VACUOUS    - no bundle could be read, or a non-vacuity control
                             did not hold.  Never a pass, never a bar-met.

SCRATCH-RUN OBLIGATION (audit CYCLE_39164900837 F9)
--------------------------------------------------
A claim-bearing cycle writes its record to the committed default below.  A
SCRATCH invocation (a unit test, a local poke, a retry) MUST pass ``--out``;
otherwise it overwrites the committed claim-bearing record in
``results/evaluation/counter_authority_surface_falsifier/``.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from evaluation import mapping_free_recall_falsifier as M  # noqa: E402

SCHEMA = "lex-evaluation-counter-authority-surface-falsifier/1"
HYPOTHESIS_RELPATH = "evaluation/COUNTER_AUTHORITY_SURFACE_FALSIFIER_HYPOTHESIS_V1.json"
FREEZE_RELPATH = "evaluation/COUNTER_AUTHORITY_SURFACE_FALSIFIER_FREEZE_RECORD.json"

#: The packet of record this instrument is chartered to falsify.  Direction v61
#: names this exact packet (packet.json raw sha256 32ac8126...) as the packet the
#: accepted serve verdict and the frozen falsification battery are pinned to.
PACKETS = ("39319405429",)

#: Frozen exit-code contract, imported from the accepted instrument so the two
#: instruments can never drift apart on what a pass / a falsification is.
EXIT_PASS = M.EXIT_PASS
EXIT_FALSIFIED = M.EXIT_FALSIFIED
EXIT_VACUOUS = M.EXIT_VACUOUS

CLAIM_CEILING = (
    "This instrument establishes exactly one thing: on the packet-of-record V3's "
    "(39319405429) exact bytes, whether the served bundles satisfy the frozen "
    "mapping-free gates. It does NOT meet, move or re-derive the frozen absolute "
    "LABEL_SOUND or GEOMETRY_SOUND bars, which stay REPORTED-ONLY. It does NOT lift "
    "the accepted DO-NOT-SERVE order on packet 38839347028 nor DO-NOT-SERVE-UNCHANGED "
    "on rebuilt-39027045675, and it does NOT change V3's BUILT_NOT_SERVED / "
    "WITHHELD_PENDING_SERVE status. It does NOT certify admission of any packet; "
    "admission stays fail-closed. It does NOT claim the map helps a jurist; that "
    "remains the human product gate's question. It does NOT build, tune, score or "
    "re-score any candidate for any Frontier team; where its numbers touch the "
    "accepted frontier-counter-label-emission numbers they are published BESIDE them "
    "with any divergence named as the headline. It runs no obsolete universal-174k "
    "benchmark. human_gate_ready stays false."
)


def _sha256_file(path: Path) -> str:
    return M.sha256_file(path)


def _current_direction_version() -> int:
    """Direction version of the CURRENT lane state, derived at run time.

    Precedent: evaluation/benchmark_retrieval_counter_authority.py
    ``_current_direction_version`` (repair 39027041693) and the accepted
    mapping-free falsifier's own ``direction_version`` field, which is a
    frozen literal from v57 and is therefore NOT authoritative under v61.
    A missing/unreadable state is an environment error, never a stale fallback.
    No threshold, rule or verdict is touched.
    """
    state_path = REPO_ROOT / "state" / "evaluation.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    return int(state["direction_version"])


def _rel_or_abs(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT.resolve()))
    except ValueError:
        return str(path)


def _rehash(records: dict[str, str], root: Path) -> dict[str, str]:
    """Re-hash the frozen inputs the freeze record pins, from disk."""
    return {rel: _sha256_file(root / rel) for rel in records if (root / rel).is_file()}


def _emit(out: Path | None, record: dict) -> None:
    """Write the artifact of record on EVERY exit path.

    A refusal that writes no record is unreproducible from the committed tree:
    the report-of-record's own command could not re-derive its committed
    artifact.  The vacuous/environment exit is therefore as claim-bearing as
    the passing one and is written identically.
    """
    if out is None:
        return
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(record, indent=1, ensure_ascii=False, sort_keys=True) + "\n",
                   encoding="utf-8")


def _reduced_question(q: dict) -> dict:
    """Project a measured question down to the fields the claim needs.

    The accepted ``measure`` embeds each full bundle in its return value; the
    committed record carries only the reduced projection plus the bundle's own
    sha256, so the record stays small while remaining recomputable from the
    pinned mount bytes.
    """
    return {
        "packet": q["packet"],
        "qid": q["qid"],
        "bundle_sha256": q["bundle_sha256"],
        "admissibility_sha256": q["admissibility_sha256"],
        "concepts": q["coverage"]["concepts"],
        "concepts_with_zero_rows": q["coverage"]["concepts_with_zero_rows"],
        "concept_row_counts": q["coverage"]["concept_row_counts"],
    }


def run(run_id: str, out: Path, mount_arg: str | None, repo: Path,
        packets: tuple[str, ...]) -> tuple[int, dict]:
    freeze = json.loads((repo / FREEZE_RELPATH).read_text(encoding="utf-8"))
    direction_version = _current_direction_version()
    mount = M.resolve_mount(mount_arg)

    if mount is None:
        rec = {
            "schema": SCHEMA, "lane": "evaluation", "run_id": run_id,
            "direction_version": direction_version,
            "verdict": "NOT_MEASURED_VACUOUS", "exit_code": EXIT_VACUOUS,
            "frozen_hypothesis": {"path": HYPOTHESIS_RELPATH,
                                  "sha256": _sha256_file(repo / HYPOTHESIS_RELPATH)},
            "freeze_record": {"path": FREEZE_RELPATH,
                              "sha256": _sha256_file(repo / FREEZE_RELPATH)},
            "entry_point": "python -m evaluation.counter_authority_surface_falsifier",
            "detail": "no accepted product mount available; admission of a packet is never "
                      "certified from an absent input, and this exit is NOT a pass",
            "not_a_pass": True, "human_gate_ready": False, "packet_admitted": False,
            "machine_gate_ready": False, "ready_for_owner_session": False,
            "owner_decision_required": False,
            "claim_ceiling": CLAIM_CEILING,
        }
        _emit(out, rec)
        return EXIT_VACUOUS, rec

    before = _rehash(freeze["frozen_repo_input_digests_before_execution"], repo)
    mount_before = _rehash(freeze["frozen_mount_input_digests_before_execution"], mount)

    measured = M.measure(mount, repo, packets)
    vac = M.non_vacuity(measured["questions"], measured["scored_statuses_from_frozen_rubric"])
    verdict, code = M.verdict_of(measured, vac)

    after = _rehash(freeze["frozen_repo_input_digests_before_execution"], repo)
    mount_after = _rehash(freeze["frozen_mount_input_digests_before_execution"], mount)
    drift = sorted({rel for rel, d in before.items() if after.get(rel) != d}
                   | {rel for rel, d in mount_before.items() if mount_after.get(rel) != d})

    gates = [g for q in measured["questions"] for g in q["gates"]]
    failed = [g for g in gates if g["passed"] is False]

    packet_digests: dict[str, str] = {}
    for packet in packets:
        p = mount / "results" / "product" / "gate_packet" / packet / "packet.json"
        if p.is_file():
            packet_digests[packet] = _sha256_file(p)

    record = {
        "schema": SCHEMA, "lane": "evaluation", "run_id": run_id,
        "direction_version": direction_version,
        "verdict": verdict, "exit_code": code,
        "entry_point": "python -m evaluation.counter_authority_surface_falsifier",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "frozen_hypothesis": {"path": HYPOTHESIS_RELPATH,
                              "sha256": _sha256_file(repo / HYPOTHESIS_RELPATH)},
        "freeze_record": {"path": FREEZE_RELPATH,
                          "sha256": _sha256_file(repo / FREEZE_RELPATH)},
        "instrument": {"path": "evaluation/counter_authority_surface_falsifier.py",
                       "sha256": _sha256_file(Path(__file__))},
        "reused_measurement_module": {
            "path": "evaluation/mapping_free_recall_falsifier.py",
            "sha256": _sha256_file(repo / "evaluation" / "mapping_free_recall_falsifier.py"),
            "functions_reused": ["measure", "non_vacuity", "verdict_of",
                                 "counter_authority_surface", "admissibility"],
        },
        "product_mount": str(mount), "product_mount_head": M.mount_head(mount),
        "packets_measured": list(packets),
        "packet_json_sha256": packet_digests,
        "rehash_before_execution": {"repo": before, "mount": mount_before},
        "rehash_after_execution": {"repo": after, "mount": mount_after},
        "input_drift": drift,
        "input_drift_invalidates_run": bool(drift),
        "numeric_environment": M.numeric_environment(),
        "frozen_spec": {"path": M.FROZEN_SPEC_RELPATH, "sha256": measured["spec_sha256"]},
        "frozen_label_rubric": {"path": M.RULES_LABEL_RELPATH,
                                "sha256": measured["rules_label_sha256"],
                                "scored_statuses": measured["scored_statuses_from_frozen_rubric"]},
        "n_questions_measured": len(measured["questions"]),
        "n_gates": len(gates),
        "n_passed": sum(1 for g in gates if g["passed"] is True),
        "n_failed": len(failed),
        "n_reported": sum(1 for g in gates if g["passed"] is None),
        "failed_gates": [{"gate": g["gate"], "detail": g["detail"], "measured": g["measured"]}
                         for g in failed],
        "gates": gates,
        "per_question": [_reduced_question(q) for q in measured["questions"]],
        "admissibility": {
            "rule": "SAME_NORM AND SAME_SUBJECT_TERMS, computed at run time with no analyst judgement",
            "n_pairs_enumerated": measured["n_pairs_enumerated"],
            "n_pairs_admissible": measured["n_pairs_admissible"],
            "pairs": measured["frozen_id_overlap"],
        },
        "non_vacuity": vac,
        "no_new_thresholds": True,
        "no_174k_benchmark_rerun": True,
        "claim_ceiling": CLAIM_CEILING,
        "human_gate_ready": False, "packet_admitted": False,
        "machine_gate_ready": False, "ready_for_owner_session": False,
        "owner_decision_required": False,
    }
    _emit(out, record)
    return code, record


DEFAULT_OUT_DIR = REPO_ROOT / "results" / "evaluation" / "counter_authority_surface_falsifier"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    ap.add_argument("--run-id", default=os.environ.get("GITHUB_RUN_ID", "local"))
    ap.add_argument("--out", default=None,
                    help="machine record path (default: the committed results/ tree). "
                         "A scratch/ad-hoc invocation MUST override this so it cannot "
                         "rewrite a committed claim-bearing record.")
    ap.add_argument("--product-mount", default=None)
    ap.add_argument("--packets", default=",".join(PACKETS))
    args = ap.parse_args(argv)
    packets = tuple(p.strip() for p in args.packets.split(",") if p.strip())
    out = Path(args.out) if args.out else (DEFAULT_OUT_DIR / f"{args.run_id}.json")
    code, rec = run(args.run_id, out, args.product_mount, REPO_ROOT, packets)
    print(json.dumps({
        "verdict": rec.get("verdict"), "exit_code": code,
        "direction_version": rec.get("direction_version"),
        "n_questions_measured": rec.get("n_questions_measured"),
        "n_gates": rec.get("n_gates"), "n_passed": rec.get("n_passed"),
        "n_failed": rec.get("n_failed"), "n_reported": rec.get("n_reported"),
        "input_drift": rec.get("input_drift"),
        "non_vacuity_all_hold": (rec.get("non_vacuity") or {}).get("all_hold"),
        "n_pairs_admissible": ((rec.get("admissibility") or {}).get("n_pairs_admissible")),
        "failed_gates": [g["gate"] for g in rec.get("failed_gates") or []],
        "record": _rel_or_abs(out),
    }, indent=1))
    return code


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

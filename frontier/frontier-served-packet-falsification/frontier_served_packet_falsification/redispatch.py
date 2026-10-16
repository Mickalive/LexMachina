"""Run-scoped re-dispatch adjudication for an ALREADY-PROMOTED charter.

    python -m frontier_served_packet_falsification.redispatch \
        --run-id 38889472353 --out <dir> [--repo-root .] [--skip-rerun]

WHY THIS MODULE EXISTS
-----------------------
This charter's ``stop_promote_rule`` is a HARD STOP: exactly ONE verdict
cycle.  The single verdict cycle already completed and was independently
audited ``gate=PASS`` (run 38880639079, artifacts integrated at
``lab/frontier/frontier-served-packet-falsification`` = 464c45f7).  A later
fresh workflow dispatch can only occur when the control-plane portfolio entry
is still ``status == "RUN"`` (only the director may write
``state/frontier_portfolio.json``), i.e. an operational re-dispatch, never a
mandate to score a second verdict.

This module is therefore a VERIFIER, not a scorer.  It:

  1. proves freeze byte-identity of both frozen RULES files against the
     charter pins (acceptance test 1);
  2. proves the three served-bundle inputs are byte-identical to
     ``INPUT_LIST.json`` (no rebuild => no new-charter trigger);
  3. recounts the charter's pre-registered population from the raw bundles
     (65 scored / 16 empty-evidence / 49-0-16 verified / 11 placeholders);
  4. re-runs the accepted harness twice in temp dirs OUTSIDE the repo and
     proves byte-identity against the committed claim-bearing artifacts and
     against the committed ``REPRODUCIBILITY.json`` run1/run2 shas
     (acceptance test 7);
  5. checks the team state still carries ``charter_version`` and
     ``continue_recommended`` honestly;
  6. applies the claim ceiling (acceptance test 9) to everything it emits.

It introduces NO threshold, re-freezes NOTHING, re-scores NO new population
and writes NOTHING outside ``--out``.  Network calls == 0.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from typing import Any

from . import (
    BUNDLES,
    BUNDLE_SHA256,
    CHARTER_VERSION,
    FORBIDDEN_WRITE_PREFIXES,
    GATE_PACKET,
    RULES_GEOMETRY_SHA256,
    RULES_LABEL_SHA256,
    TEAM_ID,
    WRITE_SCOPE,
)
from .claim_ceiling import CLAIM_CEILING, check_payload
from .vendored.frontier_counter_label_integrity.extract import counter_rows, load_bundle
from .vendored.frontier_counter_label_integrity.rules import load_rules

#: Files the accepted harness emits; all are claim-bearing and must stay
#: byte-identical to the committed, audited artifacts.
HARNESS_FILES = (
    "LABEL_HALF.json",
    "GEOMETRY_HALF.json",
    "BEFORE_AFTER.json",
    "CLAIM_CEILING.json",
    "FREEZE.json",
    "SUMMARY.json",
    "CLAIM_CEILING_CHECK.json",
)

#: The one completed, audited verdict cycle of this charter.
COMPLETED_VERDICT_RUN_ID = "38877700234"
COMPLETED_VERDICT_COMMIT = "b83513dbc7e6646a9f403f3df779108069aacd95"
PROMOTED_RESUME_RUN_ID = "38880639079"
PROMOTED_RESUME_COMMIT = "464c45f7e4bf741b6a67adbef35dc587d8cfa21f"
ACCEPTED_AUDIT_GATE = (
    "results/audit/frontier/frontier-served-packet-falsification/"
    "CYCLE_38880639079_GATE.json"
)

PLACEHOLDER_EVIDENCE = "cited in generated answer"


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _write_json(path: str, payload: Any) -> str:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    text = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _load_json(path: str) -> Any:
    with open(path, "rb") as fh:
        return json.loads(fh.read().decode("utf-8"))


def find_packet_dir(repo_root: str) -> str:
    candidates = [
        os.path.join(repo_root, GATE_PACKET),
        os.path.join("/tmp/lex_accepted/core/product", GATE_PACKET),
    ]
    for c in candidates:
        if os.path.isdir(c):
            return c
    raise FileNotFoundError(f"gate packet not found; tried: {candidates}")


def results_dir(repo_root: str) -> str:
    return os.path.join(repo_root, "results", "frontier", TEAM_ID)


# --------------------------------------------------------------------------
# 1. freeze byte-identity (acceptance test 1)
# --------------------------------------------------------------------------
def verify_freeze(repo_root: str) -> dict[str, Any]:
    res = results_dir(repo_root)
    label_path = os.path.join(res, "RULES_LABEL.json")
    geom_path = os.path.join(res, "RULES_GEOMETRY.json")
    label_sha = sha256_file(label_path)
    geom_sha = sha256_file(geom_path)
    label_text = open(label_path, "rb").read().decode("utf-8")
    geom_text = open(geom_path, "rb").read().decode("utf-8")
    return {
        "rules_label_sha256": label_sha,
        "rules_label_charter_pin": RULES_LABEL_SHA256,
        "rules_label_byte_identity": label_sha == RULES_LABEL_SHA256,
        "rules_geometry_sha256": geom_sha,
        "rules_geometry_charter_pin": RULES_GEOMETRY_SHA256,
        "rules_geometry_byte_identity": geom_sha == RULES_GEOMETRY_SHA256,
        # The charter forbids writing a frozen_at_utc field of our own; the only
        # permitted occurrence is the word inside the copied rubric's own
        # prohibition text.
        "frozen_at_utc_field_written": (
            '"frozen_at_utc"' in label_text or '"frozen_at_utc"' in geom_text
        ),
        "byte_identity_ok": label_sha == RULES_LABEL_SHA256
        and geom_sha == RULES_GEOMETRY_SHA256,
    }


# --------------------------------------------------------------------------
# 2. input identity (no rebuild => no new-charter trigger)
# --------------------------------------------------------------------------
def verify_inputs(repo_root: str) -> dict[str, Any]:
    packet = find_packet_dir(repo_root)
    input_list = _load_json(os.path.join(results_dir(repo_root), "INPUT_LIST.json"))
    pinned = {b["qid"]: b for b in input_list["served_gate_packet"]["bundles"]}
    bundles: dict[str, Any] = {}
    all_ok = True
    for qid in BUNDLES:
        path = os.path.join(packet, "questions", f"{qid}.bundle.json")
        digest = sha256_file(path)
        bundle = load_bundle(path)
        n = len(bundle.get("decisions") or [])
        expected_sha = BUNDLE_SHA256[qid]
        ok = digest == expected_sha and digest == pinned[qid]["sha256"] and n == pinned[qid]["n_decisions"]
        all_ok = all_ok and ok
        bundles[qid] = {
            "path": f"{GATE_PACKET}/questions/{qid}.bundle.json",
            "sha256": digest,
            "charter_sha256": expected_sha,
            "input_list_sha256": pinned[qid]["sha256"],
            "n_decisions": n,
            "input_list_n_decisions": pinned[qid]["n_decisions"],
            "unchanged": ok,
        }
    return {
        "gate_packet": GATE_PACKET,
        "bundles": bundles,
        "all_inputs_unchanged": all_ok,
        "packet_rebuilt_since_verdict_cycle": not all_ok,
        "further_product_repair_needs_re_scoring": not all_ok,
        "note": (
            "The charter's only new-charter trigger is a rebuilt packet or a "
            "further product repair that needs re-scoring. Inputs byte-identical "
            "to the accepted INPUT_LIST.json pins => neither trigger fired."
        ),
    }


# --------------------------------------------------------------------------
# 3. population recount from the raw served files (charter pre-registration)
# --------------------------------------------------------------------------
def verify_population(repo_root: str) -> dict[str, Any]:
    packet = find_packet_dir(repo_root)
    rules = load_rules(os.path.join(results_dir(repo_root), "RULES_LABEL.json"))
    scored_statuses = list(rules.rubric["scored_statuses"])
    reported_statuses = list(rules.rubric["reported_separately_never_scored"])

    per_bundle: dict[str, Any] = {}
    n_scored = n_empty = n_placeholder = 0
    verified = {"present_true": 0, "present_false": 0, "absent": 0}
    empty_rows: list[dict[str, Any]] = []
    for qid in BUNDLES:
        bundle = load_bundle(os.path.join(packet, "questions", f"{qid}.bundle.json"))
        scored, reported = counter_rows(bundle, scored_statuses, reported_statuses)
        n_empty_q = n_ph_q = 0
        for r in scored:
            ev = (r.get("counter_evidence") or "").strip()
            unc = r.get("counter_uncertainty")
            if ev == "" and (unc is None or unc >= 0.95):
                n_empty_q += 1
                empty_rows.append(
                    {
                        "qid": qid,
                        "decision_id": r.get("decision_id"),
                        "rank": r.get("rank"),
                        "counter_uncertainty": unc,
                        "counter_evidence": r.get("counter_evidence"),
                        "counter_evidence_verified_field_present": bool(
                            (r.get("field_presence") or {}).get(
                                "counter_evidence_verified"
                            )
                        ),
                    }
                )
            if ev == PLACEHOLDER_EVIDENCE:
                n_ph_q += 1
            presence = (r.get("field_presence") or {}).get(
                "counter_evidence_verified"
            )
            field = r.get("counter_evidence_verified")
            if not presence:
                verified["absent"] += 1
            elif field is True:
                verified["present_true"] += 1
            else:
                verified["present_false"] += 1
        # The 11 placeholder rows live in the REPORTED-ONLY population
        # (counter_status 'cited' -> reported_separately_never_scored), so they
        # must be counted over `reported` as well as `scored`.
        n_ph_reported = sum(
            1
            for r in reported
            if (r.get("counter_evidence") or "").strip() == PLACEHOLDER_EVIDENCE
        )
        n_ph_q += n_ph_reported
        n_scored += len(scored)
        n_empty += n_empty_q
        n_placeholder += n_ph_q
        per_bundle[qid] = {
            "n_decisions": len(bundle.get("decisions") or []),
            "n_scored": len(scored),
            "n_reported_only": len(reported),
            "n_empty_evidence_at_uncertainty_ge_0_95": n_empty_q,
            "n_cited_placeholders": n_ph_q,
            "n_cited_placeholders_in_reported_only": n_ph_reported,
        }

    return {
        "scored_statuses": scored_statuses,
        "reported_separately_never_scored": reported_statuses,
        "per_bundle": per_bundle,
        "n_scored_total": n_scored,
        "charter_expected_n_scored": 65,
        "n_empty_evidence_at_uncertainty_ge_0_95": n_empty,
        "charter_expected_n_empty_evidence": 16,
        "counter_evidence_verified": verified,
        "charter_expected_verified": {
            "present_true": 49,
            "present_false": 0,
            "absent": 16,
        },
        "n_cited_placeholders": n_placeholder,
        "charter_expected_n_cited_placeholders": 11,
        "empty_evidence_rows": empty_rows,
        "matches_charter_pre_registration": (
            n_scored == 65
            and n_empty == 16
            and verified == {"present_true": 49, "present_false": 0, "absent": 16}
            and n_placeholder == 11
        ),
    }


# --------------------------------------------------------------------------
# 4. reproducibility: committed shas vs REPRODUCIBILITY.json vs two fresh runs
# --------------------------------------------------------------------------
def _shas_of(directory: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for name in HARNESS_FILES:
        p = os.path.join(directory, name)
        out[name] = sha256_file(p) if os.path.isfile(p) else ""
    return out


def run_fresh_harness(repo_root: str) -> tuple[dict[str, str], dict[str, str], str]:
    """Run the accepted CLI twice into temp dirs OUTSIDE the repo."""
    stdout_records: list[str] = []
    shas: list[dict[str, str]] = []
    env = dict(os.environ)
    env["PYTHONPATH"] = os.path.join(repo_root, "frontier", "frontier-served-packet-falsification")
    for _ in range(2):
        tmp = tempfile.mkdtemp(prefix="lex_fspf_rerun_", dir="/tmp")
        try:
            proc = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "frontier_served_packet_falsification.cli",
                    "--out",
                    tmp,
                    "--half",
                    "both",
                    "--repo-root",
                    repo_root,
                    "--quiet",
                ],
                env=env,
                cwd=repo_root,
                capture_output=True,
                text=True,
                check=False,
            )
            if proc.returncode != 0:
                raise RuntimeError(
                    f"harness rerun failed rc={proc.returncode}: "
                    f"{proc.stderr.strip()[:500]}"
                )
            stdout_records.append((proc.stdout or "").strip())
            shas.append(_shas_of(tmp))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    return shas[0], shas[1], "\n".join(stdout_records)


def verify_reproduction(repo_root: str, *, skip_rerun: bool = False) -> dict[str, Any]:
    res = results_dir(repo_root)
    committed = _shas_of(res)
    recorded = _load_json(os.path.join(res, "REPRODUCIBILITY.json"))
    recorded_files = recorded.get("files", {})

    committed_match_recorded = all(
        committed[name] == entry.get("run1_sha256") == entry.get("run2_sha256")
        for name, entry in recorded_files.items()
    )

    result: dict[str, Any] = {
        "committed_sha256": {k: v for k, v in committed.items() if v},
        "recorded_reproducibility_run1_run2_sha256": {
            name: {
                "run1_sha256": e.get("run1_sha256"),
                "run2_sha256": e.get("run2_sha256"),
                "byte_identical": e.get("byte_identical"),
            }
            for name, e in recorded_files.items()
        },
        "committed_match_recorded_run1_run2": committed_match_recorded,
    }

    if skip_rerun:
        result.update(
            {
                "fresh_runs_performed": False,
                "fresh_run1_sha256": None,
                "fresh_run2_sha256": None,
                "fresh_runs_byte_identical_to_each_other": None,
                "fresh_runs_byte_identical_to_committed": None,
                "all_reproductions_byte_identical": committed_match_recorded,
            }
        )
        return result

    run1, run2, stdout = run_fresh_harness(repo_root)
    same_pair = run1 == run2
    same_committed = all(run1.get(k) == v for k, v in committed.items() if v)
    result.update(
        {
            "fresh_runs_performed": True,
            "fresh_run1_sha256": run1,
            "fresh_run2_sha256": run2,
            "fresh_run_stdout": stdout,
            "fresh_runs_byte_identical_to_each_other": same_pair,
            "fresh_runs_byte_identical_to_committed": same_committed,
            "all_reproductions_byte_identical": (
                committed_match_recorded and same_pair and same_committed
            ),
        }
    )
    return result


# --------------------------------------------------------------------------
# 5. state honesty
# --------------------------------------------------------------------------
def verify_state(repo_root: str) -> dict[str, Any]:
    state_path = os.path.join(repo_root, "state", "frontier", f"{TEAM_ID}.json")
    state = _load_json(state_path)
    return {
        "path": f"state/frontier/{TEAM_ID}.json",
        "charter_version": state.get("charter_version"),
        "charter_version_retained": state.get("charter_version") == CHARTER_VERSION,
        "status": state.get("status"),
        "charter_status": state.get("charter_status"),
        "continue_recommended": state.get("continue_recommended"),
        "cycle_status": state.get("cycle_status"),
        "evidence_tier": state.get("evidence_tier"),
        "workflow_state_gate_satisfied": (
            state.get("charter_version") == CHARTER_VERSION
            and (state.get("cycle_status") or "INITIALIZED") != "INITIALIZED"
            and (state.get("evidence_tier") or "UNTESTED") != ""
        ),
    }


# --------------------------------------------------------------------------
# 6. write-scope guard for this run
# --------------------------------------------------------------------------
def verify_scope(repo_root: str) -> dict[str, Any]:
    proc = subprocess.run(
        ["git", "status", "--porcelain", "-uall"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    entries = [ln for ln in proc.stdout.splitlines() if ln.strip()]
    allowed = tuple(WRITE_SCOPE) + (f"state/frontier/{TEAM_ID}.json", "data/frontier/" + TEAM_ID + "/")
    outside: list[str] = []
    compiler_artifacts: list[str] = []
    producer_delta: list[str] = []
    for line in entries:
        path = line[3:]
        if not path:
            continue
        if "__pycache__" in path or path.endswith((".pyc", ".pyo")):
            compiler_artifacts.append(path)
        else:
            producer_delta.append(path)
        if any(path.startswith(p) for p in allowed):
            continue
        outside.append(path)
    forbidden = [
        p for p in (ln[3:] for ln in entries) if any(p.startswith(f) for f in FORBIDDEN_WRITE_PREFIXES)
    ]
    return {
        "allowed_prefixes": list(allowed),
        "files_outside_scope": sorted(set(outside)),
        "forbidden_prefix_hits": sorted(set(forbidden)),
        "zero_out_of_scope_writes": not outside and not forbidden,
        "producer_delta": producer_delta,
        "compiler_artifacts_excluded_from_producer_delta": sorted(compiler_artifacts),
        "git_status_porcelain_uall": entries,
        "self_commit_must_not_happen": (
            "The producer leaves this delta UNCOMMITTED for the workflow persist "
            "step; a self-committed clean tree trips the zero-durable-delta guard."
        ),
        "note": (
            "git_status_porcelain_uall is a point-in-time run snapshot taken "
            "before the workflow's 'Clean generated junk' step. __pycache__/ and "
            "*.pyc entries are compiler artifacts, are in-scope (under this "
            "team's own prefix), are listed separately, and are removed by the "
            "workflow before the scope gate runs."
        ),
    }


# --------------------------------------------------------------------------
# assemble
# --------------------------------------------------------------------------
def build_adjudication(
    run_id: str,
    repo_root: str,
    *,
    skip_rerun: bool = False,
) -> dict[str, Any]:
    freeze = verify_freeze(repo_root)
    inputs = verify_inputs(repo_root)
    population = verify_population(repo_root)
    repro = verify_reproduction(repo_root, skip_rerun=skip_rerun)
    state = verify_state(repo_root)
    scope = verify_scope(repo_root)

    gate_path = os.path.join(repo_root, ACCEPTED_AUDIT_GATE)
    audit_present = os.path.isfile(gate_path)
    audit_gate = None
    if audit_present:
        audit_gate = _load_json(gate_path).get("gate")

    # Verdict of record, unchanged: a fresh rerun byte-identical to the
    # committed SUMMARY.json (checked above) means the rerun returned the same
    # verdict, so reading the committed summary here is sound either way.
    summary = _load_json(os.path.join(results_dir(repo_root), "SUMMARY.json"))
    verdict_ok = (
        summary.get("label_verdict") == "LABEL_UNSOUND"
        and summary.get("geometry_verdict") == "FAIL"
        and summary.get("label_n_scored") == 65
        and summary.get("label_n_supported") == 5
        and summary.get("geometry_n_bundles_pass") == 0
    )

    checks = {
        "freeze_byte_identity": freeze["byte_identity_ok"],
        "inputs_unchanged_no_new_charter_trigger": inputs["all_inputs_unchanged"],
        "population_matches_charter_pre_registration": population[
            "matches_charter_pre_registration"
        ],
        "reproduction_byte_identical": repro["all_reproductions_byte_identical"],
        "state_charter_version_retained": state["charter_version_retained"],
        "state_machine_gate_satisfied": state["workflow_state_gate_satisfied"],
        "zero_out_of_scope_writes": scope["zero_out_of_scope_writes"],
        "accepted_audit_gate_present": audit_present,
        "accepted_audit_gate_pass": audit_gate == "PASS",
        "verdict_unchanged": verdict_ok,
    }

    payload = {
        "schema": "frontier-served-packet-falsification/redispatch-adjudication/1",
        "team_id": TEAM_ID,
        "charter_version": CHARTER_VERSION,
        "run_id": run_id,
        "dispatch_class": "OPERATIONAL_RE_DISPATCH_OF_AN_ALREADY_PROMOTED_CHARTER",
        "second_verdict_cycle_performed": False,
        "new_threshold_introduced": False,
        "claim_ceiling": CLAIM_CEILING,
        "charter_hard_stop": (
            "Exactly ONE verdict cycle. A second cycle under this charter is "
            "FORBIDDEN. A rebuilt packet or a further product repair that needs "
            "re-scoring is a NEW charter raised by the director against the NEW "
            "packet, not a continuation of this one."
        ),
        "completed_verdict_cycle": {
            "measurement_run_id": COMPLETED_VERDICT_RUN_ID,
            "measurement_commit": COMPLETED_VERDICT_COMMIT,
            "operational_resume_run_id": PROMOTED_RESUME_RUN_ID,
            "promoted_commit": PROMOTED_RESUME_COMMIT,
            "independent_audit_gate_path": ACCEPTED_AUDIT_GATE,
            "independent_audit_gate": audit_gate,
            "verdict_of_record": {
                "label_half": "LABEL_UNSOUND 5/65 (0.07692307692307693)",
                "geometry_half": "FAIL 0/3 bundles (de 6/11, fr 5/11, it 5/11)",
                "serve_recommendation": "DO-NOT-SERVE this packet unchanged",
            },
        },
        "why_this_dispatch_occurred": (
            "state/frontier_portfolio.json on main still carries this team with "
            "status=RUN and run_history=[] even though the single verdict cycle "
            "was completed, audited gate=PASS and promoted. Only the director "
            "workflow may write frontier_portfolio.json; a Frontier team's own "
            "scope forbids it. The portfolio entry must be moved off RUN by the "
            "director for this re-dispatch loop to stop."
        ),
        "freeze": freeze,
        "inputs": inputs,
        "population_recount": population,
        "reproduction": repro,
        "state": state,
        "scope": scope,
        "checks": checks,
        "all_checks_pass": all(checks.values()),
        "continue_recommended": False,
        "continue_recommended_reason": (
            "HARD STOP: the charter's single verdict cycle is complete, audited "
            "and promoted. Another cycle under the SAME charter is FORBIDDEN. A "
            "rebuilt packet or further product repair requires a NEW charter "
            "against the NEW packet."
        ),
    }
    return payload


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="frontier_served_packet_falsification.redispatch"
    )
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--out", required=True, help="output directory (inside team scope)")
    ap.add_argument("--repo-root", default=".")
    ap.add_argument("--skip-rerun", action="store_true")
    args = ap.parse_args(argv)

    repo_root = os.path.abspath(args.repo_root)
    payload = build_adjudication(
        args.run_id, repo_root, skip_rerun=args.skip_rerun
    )
    cc = check_payload(payload)
    payload["claim_ceiling_check"] = cc
    out_path = os.path.join(
        os.path.abspath(args.out), f"REDISPATCH_VERIFICATION_{args.run_id}.json"
    )
    _write_json(out_path, payload)
    print(f"wrote {out_path}")
    print(
        f"second_verdict_cycle_performed={payload['second_verdict_cycle_performed']} "
        f"all_checks_pass={payload['all_checks_pass']} "
        f"claim_ceiling_pass={cc['pass']} "
        f"continue_recommended={payload['continue_recommended']}"
    )
    if not cc["pass"]:
        print("CLAIM CEILING VIOLATION:", cc["violations"], file=sys.stderr)
        return 3
    if not payload["all_checks_pass"]:
        failed = [k for k, v in payload["checks"].items() if not v]
        print("CHECK FAILURES:", failed, file=sys.stderr)
        return 4
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

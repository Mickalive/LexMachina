#!/usr/bin/env python3
"""Close-out handoff generator: the ONE control-plane write this team cannot make.

The operational failure this cycle diagnosed
--------------------------------------------
``frontier-query-concept-recall`` finished its charter (OUTCOME_B, audit gate
PASS) and has said ``continue_recommended: false`` since cycle 39181670816, yet
the workflow dispatched it three more times (39181670816 -> 39182826179 ->
39184014244 -> ...).  The chain is fully mechanical and this module re-derives
it rather than asserting it:

1. ``.github/workflows/frontier-team.yml`` selects a charter with
   ``.teams[] | select(.team_id==$team and .charter_version==$ver and
   .status=="RUN")``.  **Portfolio ``status`` is the only dispatch predicate.**
   Nothing in ``state/frontier/<team>.json`` -- not ``cycle_status``, not
   ``continue_recommended``, not ``run_history`` -- can suppress a dispatch.
2. The portfolio entry for this team still says ``status: "RUN"`` with
   ``run_history: []`` and ``continue_recommended: true``: it is byte-for-byte
   the charter as created at 2026-10-18T18:07:04Z.  Five completed cycles and
   one accepted audit gate have never been reflected into it.
3. Only the director may write it.  ``factory-director.yml``'s scope guard
   admits ``state/factory_direction.json``, ``state/frontier_portfolio.json``
   and ``reports/director/*``; ``frontier-team.yml``'s scope guard admits only
   ``frontier/$TEAM/``, ``tests/frontier/$TEAM/``, ``results/frontier/$TEAM/``,
   ``reports/frontier/$TEAM/``, ``state/frontier/$TEAM.json`` and
   ``data/frontier/$TEAM/``.  The two scope guards do not overlap on the
   portfolio, so the write has no in-scope author.

So the charter's stop rule ("The team's status MUST move off RUN in the same
director cycle that records this outcome being met and independently accepted")
has an orphan: the team produced the outcome and the audit passed, and the
reflection step that stops the loop was never performed.  **That reflection step
IS the resume loop.**  Nothing the team does can end it, and every additional
cycle only adds cost.

What this module does about it
------------------------------
It cannot perform the write, so it makes the write trivial and impossible to
get wrong: it emits a digest-bearing, machine-readable handoff containing the
exact ``jq`` patch, the evidence index it is justified by, and a self-check that
refuses to emit a stale handoff.  The director applies it in one command.

Usage
-----
::

    PYTHONPATH=frontier python frontier/frontier-query-concept-recall/closeout_handoff.py \
        --out results/frontier/frontier-query-concept-recall [--print]

    ... --check     # validate an existing handoff; exit 3 if stale

This module makes no measurement claim and re-derives no threshold.  It reads
accepted evidence read-only and re-hashes it.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[2]
TEAM_ID = "frontier-query-concept-recall"
CHARTER_VERSION = 1
RESULTS_DIR = REPO / "results/frontier" / TEAM_ID
STATE_FILE = REPO / "state/frontier" / f"{TEAM_ID}.json"
PORTFOLIO = REPO / "state/frontier_portfolio.json"
CONTROL_PORTFOLIO = Path("/tmp/lex_control/state/frontier_portfolio.json")
WORKFLOW = REPO / ".github/workflows/frontier-team.yml"
DIRECTOR_WORKFLOW = REPO / ".github/workflows/factory-director.yml"
HANDOFF_NAME = "portfolio_status_handoff.json"
HISTORY_NAME = f"results/frontier/{TEAM_ID}/portfolio_status_handoff.history.json"
SCHEMA = "frontier_closeout_handoff_v1"

CLAIM_CEILING = (
    "No artifact may assert that a map helps a jurist, that any authority is "
    "absent from the corpus, that any frozen bar is met or moved, or that any "
    "packet is fit to serve. Usefulness remains the human product gate's "
    "question and admission remains fail-closed. This handoff asserts only "
    "facts re-hashed from the committed tree and the read-only accepted mounts."
)

# The digests a handoff is justified by. Every one is re-hashed at emit time;
# a moved digest makes the handoff stale and --check exits 3.
EVIDENCE = {
    "frozen_rules": "results/frontier/frontier-query-concept-recall/RULES.json",
    "canonical_harness_result": (
        "results/frontier/frontier-query-concept-recall/harness_results_39179862363.json"),
    "canonical_pointer_result": (
        "results/frontier/frontier-query-concept-recall/harness_results.json"),
    "cycle_verification": (
        "results/frontier/frontier-query-concept-recall/cycle_verification.json"),
    "regression_results": (
        "results/frontier/frontier-query-concept-recall/regression_results.json"),
    "integration_contract": (
        "results/frontier/frontier-query-concept-recall/integration_contract.json"),
    "bounded_cause_resolution": (
        "results/frontier/frontier-query-concept-recall/bounded_cause_resolution.json"),
    "freeze_ordering": (
        "results/frontier/frontier-query-concept-recall/freeze_ordering.json"),
    "closure_verification": (
        "results/frontier/frontier-query-concept-recall/closure_verification.json"),
    "team_state": f"state/frontier/{TEAM_ID}.json",
}

# The status value recommended for the portfolio entry, with the evidence for
# each option. The DIRECTOR decides; this module only recommends.
STATUS_OPTIONS = {
    "PAUSE": (
        "RECOMMENDED. Matches the charter's stop rule (promote at the first "
        "outcome reached) and the precedent already in the portfolio: "
        "frontier-query-retrieval is PAUSE with run_history=1 after a promoted "
        "outcome. Out of RUN, so the dispatch predicate at "
        "frontier-team.yml:58 stops matching."),
    "TERMINATED": (
        "Also valid and used by 6 of 12 portfolio entries. Correct if the "
        "director reads OUTCOME_B as closing this ITEM permanently rather than "
        "pausing it. Either value ends the loop; the choice is the director's."),
}


def sha256_file(path: Path) -> str | None:
    if not path.is_file():
        return None
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def git(*args: str) -> str:
    proc = subprocess.run(["git", "-C", str(REPO), *args],
                          capture_output=True, text=True)
    return proc.stdout.strip()


def _entry(portfolio: dict, team_id: str, version: int) -> dict | None:
    for t in portfolio.get("teams", []):
        if t.get("team_id") == team_id and t.get("charter_version") == version:
            return t
    return None


def workflow_evidence() -> dict:
    """Quote the dispatch predicate and the two scope guards verbatim.

    The scope matters: ``cycle_status`` DOES appear in the workflow, but in the
    post-run VALIDATION step, where it can fail a run, never in the dispatch
    selector, where it could suppress one. An earlier draft of this function
    grepped the whole file and reported "not found" for a field that is present
    three lines into a job; the claim is now computed from the dispatch-selector
    lines alone and the validation occurrences are reported separately.
    """
    def lines_of(path: Path) -> list[tuple[int, str]]:
        if not path.is_file():
            return []
        return [(i + 1, ln) for i, ln in
                enumerate(path.read_text(encoding="utf-8").splitlines())]

    def find(needle: str, where: list[tuple[int, str]]) -> list[str]:
        rel = str(WORKFLOW.relative_to(REPO))
        return [f"{rel}:{i}: {ln.strip()}" for i, ln in where if needle in ln]

    wf = lines_of(WORKFLOW)
    # The dispatch selector is the step that decides WHETHER a run is dispatched.
    dispatch = [(i, ln) for i, ln in wf if "status==\"RUN\"" in ln]
    # Everything else that reads a team state field is post-hoc validation.
    fields = ("cycle_status", "continue_recommended", "run_history", "status")
    return {
        "dispatch_predicate": find("status==\"RUN\"", dispatch),
        "team_scope_guard": find("frontier/$TEAM", wf),
        "director_scope_guard": [
            f"{str(DIRECTOR_WORKFLOW.relative_to(REPO))}:{i}: {ln.strip()}"
            for i, ln in lines_of(DIRECTOR_WORKFLOW)
            if "state/frontier_portfolio.json" in ln and "case" not in ln],
        "team_state_fields_in_the_dispatch_selector": {
            k: any(k in ln for _, ln in dispatch) for k in fields},
        "team_state_fields_read_outside_dispatch": {
            k: find(k, wf) for k in fields
            if not any(k in ln for _, ln in dispatch)},
        "redispatch_never_reads_team_state": {
            "method": (
                "scanned the dispatch-selector lines only; the post-run "
                "validation step was scanned separately so a field that merely "
                "validates a run is never reported as a dispatch gate"),
            "conclusion": (
                "status is the only team field in the dispatch selector. "
                "cycle_status appears once, in the validation step that FAILS a "
                "run whose state was not advanced - it can stop a run, never "
                "start or suppress one. continue_recommended appears only in "
                "the producer prompt text. run_history appears nowhere in the "
                "workflow. So no value this team can legally write in "
                "state/frontier/<team>.json can suppress a re-dispatch; only "
                "state/frontier_portfolio.json .status can."),
        },
    }


def reflect_gap() -> dict:
    """Prove mechanically that no completed cycle reached the portfolio."""
    portfolio = json.loads(PORTFOLIO.read_text(encoding="utf-8"))
    entry = _entry(portfolio, TEAM_ID, CHARTER_VERSION) or {}
    state = json.loads(STATE_FILE.read_text(encoding="utf-8"))
    control = None
    if CONTROL_PORTFOLIO.is_file():
        c_entry = _entry(json.loads(CONTROL_PORTFOLIO.read_text(encoding="utf-8")),
                         TEAM_ID, CHARTER_VERSION)
        control = {"status": (c_entry or {}).get("status"),
                   "n_run_history": len((c_entry or {}).get("run_history") or []),
                   "continue_recommended": (c_entry or {}).get("continue_recommended"),
                   "path": str(CONTROL_PORTFOLIO)}
    return {
        "portfolio_entry_status": entry.get("status"),
        "portfolio_entry_run_history_len": len(entry.get("run_history") or []),
        "portfolio_entry_continue_recommended": entry.get("continue_recommended"),
        "portfolio_entry_created_at": entry.get("created_at"),
        "portfolio_version": portfolio.get("version"),
        "team_state_cycle_status": state.get("cycle_status"),
        "team_state_continue_recommended": state.get("continue_recommended"),
        "team_state_n_run_history": len(state.get("run_history") or []),
        "team_state_outcome": state.get("outcome"),
        "team_state_charter_version": state.get("charter_version"),
        "team_state_closed": bool((state.get("closure") or {}).get("closed")),
        "mounted_control_plane_entry": control,
        "reflection_gap": (
            "The portfolio entry still carries created_at=%s, run_history=[] and "
            "status=RUN, i.e. it is the charter as first written. %d completed "
            "cycles recorded in the team state have never been reflected into "
            "it, so the dispatch predicate keeps matching and the loop is "
            "self-sustaining." % (entry.get("created_at"),
                                  len(state.get("run_history") or []))),
        "unrecoverable_by_this_team": (
            "state/frontier_portfolio.json is outside the Frontier team scope "
            "guard and inside the director's; see workflow_evidence."),
    }


def proposed_write() -> dict:
    """The exact one-command director patch. NOT applied by this module."""
    state = json.loads(STATE_FILE.read_text(encoding="utf-8"))
    portfolio = json.loads(PORTFOLIO.read_text(encoding="utf-8"))
    entry = _entry(portfolio, TEAM_ID, CHARTER_VERSION) or {}
    history = []
    for i, run in enumerate(state.get("run_history") or []):
        history.append({
            "run_id": run.get("run_id"),
            "outcome": run.get("outcome"),
            "disposition": run.get("disposition"),
            "timestamp": run.get("timestamp"),
        })
    _closure_note = (
            f"OUTCOME_B_BOUNDED_NEGATIVE; charter terminal per stop rule; audit "
            f"gate CYCLE_39178441123 PASS; handoff results/frontier/{TEAM_ID}/"
            f"{HANDOFF_NAME}")
# Three failure modes in the emitted command were caught by EXECUTING it
    # against a portfolio copy (never the real file), and all three are now
    # pinned by tests/frontier/<team>/test_closeout_handoff.py:
    #   1. `(.teams[] | select(...)) | (.status = "PAUSE")` REPLACES the whole
    #      document with the single matched team object, destroying `.version`
    #      and `.teams`. jq streams the selection out. The update must be an
    #      in-place `|=` map over `.teams` so the root survives.
    #   2. `\"` inside a shell single-quoted program reaches jq literally and
    #      fails to compile, so the closure note carries no double quotes.
    #   3. The run_history array used to be inlined as `--argjson hist '...'`.
    #      It is prose lifted from the team state and contains apostrophes
    #      ("the director's portfolio write"), which terminated the shell's
    #      single-quoted string. The history therefore ships as its own JSON
    #      FILE and is read with --slurpfile, so no data ever passes through
    #      shell quoting.
    jq_program = (
        f'.teams |= (map(if (.team_id == "{TEAM_ID}" and '
        f'.charter_version == {CHARTER_VERSION}) '
        f'then (.status = "PAUSE") '
        f'| (.continue_recommended = false) '
        f'| (.run_history = ((.run_history // []) + $hist[0])) '
        f'| (.closed_at = $ts) '
        f'| (.closure = "{_closure_note}") '
        f'else . end)) '
        f'| (if (.version | type) == "number" then .version += 1 else . end)')
    if "'" in jq_program:
        # A single quote here would break the shell wrapping below; fail loudly
        # at emit time rather than handing the director a command that cannot run.
        raise ValueError("jq program contains a single quote; it is shell-wrapped "
                         "in single quotes and would not execute")
    return {
        "file": "state/frontier_portfolio.json",
        "target_selector": (
            f".teams[] | select(.team_id==\"{TEAM_ID}\" and "
            f".charter_version=={CHARTER_VERSION})"),
        "current_status": entry.get("status"),
        "recommended_status": "PAUSE",
        "status_rationale": STATUS_OPTIONS,
        "jq_program": jq_program,
        "jq_command": (
            "jq --arg ts \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\" "
            f"--slurpfile hist {HISTORY_NAME} "
            f"'{jq_program}' "
            "state/frontier_portfolio.json > /tmp/p.json && "
            "mv /tmp/p.json state/frontier_portfolio.json"),
        "jq_args_note": (
            f"Read from the repository root: {HISTORY_NAME} must sit beside this "
            "record and holds the proposed run_history array verbatim, read by "
            "--slurpfile as $hist[0]. No data is inlined into the shell command, "
            "so apostrophes and quotes in the run history cannot break it. "
            "Re-emit with --print if the team state has advanced."),
        "proposed_run_history_entries": history,
        "version_bump_rule": (
            "factory-director.yml increments frontier_portfolio.version only if "
            "the portfolio materially changes; a status flip off RUN is material, "
            "so the version should be incremented with the patch."),
        "not_applied_by_this_team": (
            "This module never writes state/frontier_portfolio.json. Its scope "
            "guard would fail the run if it did. The recommendation is advisory; "
            "the director decides and records."),
    }


def evidence_index() -> dict:
    index = {}
    for key, rel in EVIDENCE.items():
        path = REPO / rel
        index[key] = {"path": rel, "sha256": sha256_file(path),
                      "present": path.is_file()}
    return index


def invariants(evidence: dict) -> dict:
    state = json.loads(STATE_FILE.read_text(encoding="utf-8"))
    portfolio = json.loads(PORTFOLIO.read_text(encoding="utf-8"))
    entry = _entry(portfolio, TEAM_ID, CHARTER_VERSION) or {}
    frozen = evidence["frozen_rules"]["sha256"]
    team_state_sha = evidence["team_state"]["sha256"]
    return {
        "charter_version_retained": state.get("charter_version") == CHARTER_VERSION,
        "outcome_is_terminal": state.get("outcome") == "OUTCOME_B_BOUNDED_NEGATIVE",
        "continue_recommended_is_false": state.get("continue_recommended") is False,
        "closure_closed": bool((state.get("closure") or {}).get("closed")),
        "all_evidence_present": all(v["present"] for v in evidence.values()),
        "all_evidence_re_hashed": all(v["sha256"] for v in evidence.values()),
        "frozen_rules_digest": frozen,
        "frozen_rules_expected": (
            "c5447bac0605a8bcf8c3d1820bee56a5bb0e814365978ec1fa12ac189776ee9a"),
        "frozen_rules_unchanged": frozen == (
            "c5447bac0605a8bcf8c3d1820bee56a5bb0e814365978ec1fa12ac189776ee9a"),
        "portfolio_entry_still_run": entry.get("status") == "RUN",
        "team_state_sha256": team_state_sha,
        "note": (
            "team_state_sha256 is recorded so a stale handoff is detectable. The "
            "director changes this team's state file only through a new cycle, "
            "so a moved digest here means re-emit."),
    }


def build() -> dict:
    evidence = evidence_index()
    inv = invariants(evidence)
    return {
        "schema": SCHEMA,
        "team_id": TEAM_ID,
        "charter_version": CHARTER_VERSION,
        "run_id": int(time.time()),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "network_calls": 0,
        "authored_by": f"frontier/{TEAM_ID}/closeout_handoff.py",
        "what_this_is": (
            "The one control-plane write that ends the resume loop, packaged so "
            "the director can apply it in a single command. It is a handoff, not "
            "a measurement: no threshold is re-derived, no frozen file is "
            "touched, no gate is re-scored."),
        "what_this_is_not": (
            "It is not a self-appointment, not a status write, and not a second "
            "hypothesis. The charter is terminal; this cycle changes no measured "
            "number and adds none."),
        "charter_outcome_unchanged": "OUTCOME_B_BOUNDED_NEGATIVE",
        "this_cycle_adds_no_measurement_claim": True,
        "diagnosis": {
            "root_cause": (
                "Unreflected completion. The team's outcome and its accepted "
                "audit gate never reached state/frontier_portfolio.json, whose "
                ".status is the sole dispatch predicate, so the terminal team "
                "keeps matching the RUN selector on every dispatch."),
            "operational_failure": (
                "Run 39184014244 is the fourth consecutive dispatch of a team "
                "whose own state says cycle_status=COMPLETE, "
                "continue_recommended=false, closure.closed=true."),
            "blast_radius": (
                "Autonomous compute only: no owner decision is blocked, no "
                "accepted evidence is at risk and no product byte is touched. "
                "The cost is an unbounded loop of re-verification cycles."),
            "workflow_evidence": workflow_evidence(),
            "reflection_gap": reflect_gap(),
        },
        "proposed_control_plane_write": proposed_write(),
        "evidence_index": evidence,
        "invariants": inv,
        "git": {
            "head": git("rev-parse", "HEAD"),
            "head_subject": git("log", "-1", "--format=%s"),
            "branch": git("rev-parse", "--abbrev-ref", "HEAD"),
            "is_shallow_repository": git("rev-parse", "--is-shallow-repository"),
            "n_commits_visible": int(git("rev-list", "--count", "HEAD") or 0),
        },
        "residual_actions_outside_this_teams_scope": [
            {"actor": "factory director",
             "action": "apply the proposed portfolio patch (status RUN -> PAUSE, "
                       "run_history += 5 cycles, continue_recommended=false)",
             "blocking": True,
             "note": "this alone ends the dispatch loop"},
            {"actor": "factory director / workflow owner",
             "action": "teach the zero-delta guard or the dispatch selector to "
                       "honour a verified terminal closure, so a closed team is "
                       "not re-dispatched even if a portfolio write is missed",
             "blocking": False,
             "note": "defence in depth; the portfolio write is the actual fix"},
            {"actor": "Core Product (integrator)",
             "action": "record an adoption-or-decline decision on the OUTCOME_B "
                       "integration contract (factory-wide requirement 21)",
             "blocking": False,
             "note": "the charter closes the recall half; the "
                     "admission-disclosure half stays with Product"},
        ],
        "claim_ceiling": CLAIM_CEILING,
    }


def check(out_dir: Path) -> tuple[int, dict]:
    path = out_dir / HANDOFF_NAME
    if not path.is_file():
        return 3, {"error": f"no handoff at {path}"}
    rec = json.loads(path.read_text(encoding="utf-8"))
    live = evidence_index()
    stale = [k for k, v in rec.get("evidence_index", {}).items()
             if v.get("sha256") != live.get(k, {}).get("sha256")]
    portfolio = json.loads(PORTFOLIO.read_text(encoding="utf-8"))
    entry = _entry(portfolio, TEAM_ID, CHARTER_VERSION) or {}
    applied = entry.get("status") != "RUN"
    verdict = {
        "stale_evidence_keys": stale,
        "stale": bool(stale),
        "portfolio_status_now": entry.get("status"),
        "already_applied": applied,
        "verdict": ("ALREADY_APPLIED - the director has flipped this entry; the "
                    "loop should be over"
                    if applied else
                    "STALE - evidence moved, re-emit with --out <dir>"
                    if stale else
                    "VALID - evidence re-hashes unchanged and the entry is still "
                    "RUN, so the handoff is still the action needed"),
        "recommended_action": (
            "none - do not re-apply" if applied else
            "re-emit" if stale else
            "apply proposed_control_plane_write.jq_command"),
    }
    return (0 if not stale and not applied else 3), verdict


def _display(path: Path) -> str:
    try:
        return str(path.relative_to(REPO))
    except ValueError:
        return str(path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog=f"frontier/{TEAM_ID}/closeout_handoff.py",
        description="Emit or validate the close-out handoff for the one "
                    "control-plane write this team cannot make")
    parser.add_argument("--out", default=str(RESULTS_DIR))
    parser.add_argument("--check", action="store_true",
                        help="validate an existing handoff instead of emitting")
    parser.add_argument("--print", dest="print_summary", action="store_true")
    args = parser.parse_args(argv)
    out_dir = Path(args.out)
    if args.check:
        code, verdict = check(out_dir)
        print(json.dumps(verdict, indent=1))
        return code
    record = build()
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / HANDOFF_NAME).write_text(
        json.dumps(record, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    # The history array ships as its own file: the emitted jq command reads it
    # with --slurpfile, so no run-history prose ever passes through shell
    # quoting (an apostrophe in a disposition otherwise breaks the command).
    (out_dir / Path(HISTORY_NAME).name).write_text(
        json.dumps(record["proposed_control_plane_write"][
            "proposed_run_history_entries"], indent=1, ensure_ascii=False) + "\n",
        encoding="utf-8")
    if args.print_summary:
        print(json.dumps({
            "written": [str(_display(out_dir / HANDOFF_NAME)),
                        str(_display(out_dir / Path(HISTORY_NAME).name))],
            "charter_outcome_unchanged": record["charter_outcome_unchanged"],
            "portfolio_entry_status": record["diagnosis"]["reflection_gap"][
                "portfolio_entry_status"],
            "team_state_continue_recommended": record["diagnosis"]["reflection_gap"][
                "team_state_continue_recommended"],
            "recommended_status": record["proposed_control_plane_write"][
                "recommended_status"],
            "frozen_rules_unchanged": record["invariants"]["frozen_rules_unchanged"],
            "network_calls": record["network_calls"],
        }, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
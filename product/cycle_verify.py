#!/usr/bin/env python3
"""One command that re-derives every claim this cycle makes, and fails loudly.

Why this exists
---------------
The audit job of run 39082232157 ran 54 m 59 s and was cancelled without writing
a gate (see ``product/orchestration_evidence.py`` and
``results/product/orchestration/CYCLE_39082232157_orchestration.json``). A long
independent audit is not something the product lane controls, but the *cost* of
the audit is something it does control: every claim that can be checked in one
command is a claim the auditor does not have to reconstruct from a report.

So this module turns the cycle's report into a machine-checkable ledger:

    python product/cycle_verify.py --run-id 39086926860 --write

Each entry states a claim, names the command that proves it, records what was
actually observed, and marks itself PASS/FAIL. The exit code is non-zero if any
claim fails, so this is usable as a gate and not only as a report.

Rules this module follows, each of which exists because the lane got one wrong
first (audit ``CYCLE_39069382456`` and its repair):

* **Derive, never assert.** Every number in the ledger is recomputed from a
  committed artifact or from a live run of the product's own code. Nothing is
  copied out of a report.
* **A check that cannot run is FAIL, not PASS.** "Could not parse" must never
  degrade to a zero or an empty pass — that is exactly how "+7 tests" got
  published against no measurement.
* **Say which definition.** Where two honest definitions of the same quantity
  exist (counter authorities vs counter-status-bearing rows; cluster ``size`` vs
  ``member_ids``), both are reported side by side and the source of each is
  named.
* **Stay inside the lane's own claims.** This verifies the product's shipped
  behaviour and posture. It does not score frozen bars, does not read Frontier
  verdicts, and cannot promote anything.

Usage
-----
    python product/cycle_verify.py                      # dry run, prints the ledger
    python product/cycle_verify.py --write              # also writes the artifact
    python product/cycle_verify.py --only posture,map   # a subset
    python product/cycle_verify.py --json               # machine-readable only
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

SCHEMA = "product-cycle-verify/1"
DEFAULT_OUT_DIR = REPO_ROOT / "results" / "product" / "cycle_verify"
STATE_PATH = REPO_ROOT / "state" / "product.json"
INTAKE_PATH = (
    REPO_ROOT / "results" / "product" / "frontier_verdicts"
    / "frontier-rebuilt-packet-serve-audit_intake.json"
)
TRACKED_FEEDBACK = REPO_ROOT / "product" / "results" / "fractal_map" / "jurist_feedback" / "feedback.jsonl"
ORCHESTRATION_ARTIFACT = (
    REPO_ROOT / "results" / "product" / "orchestration" / "CYCLE_39082232157_orchestration.json"
)

#: Posture the accepted verdicts pin. Hard-coded HERE on purpose: a ledger that
#: reads its own expectations out of the file it is checking verifies nothing.
REQUIRED_FAIL_CLOSED = {
    "human_gate_ready": False,
    "machine_gate_ready": False,
    "packet_admitted": False,
    "ready_for_owner_session": False,
}


def _repo_relative(path: Path) -> str:
    """Repo-relative when possible, absolute otherwise (never raises)."""
    try:
        return str(Path(path).relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def _fail(claim: str, why: str, **extra: Any) -> dict:
    return {"claim": claim, "status": "FAIL", "observed": why, **extra}


def _pass(claim: str, observed: Any, **extra: Any) -> dict:
    return {"claim": claim, "status": "PASS", "observed": observed, **extra}


# --------------------------------------------------------------------------
# individual checks
# --------------------------------------------------------------------------

def check_slice_and_page_contract() -> list[dict]:
    """Run the real offline vertical slice and its own DOM contract.

    This is the claim the whole lane rests on — question -> answer ->
    counter-authority -> clickable map — so it is executed, not read from a file.
    """
    from product.offline_slice import build_bundle, summarise, verify_page
    from product.query.bundle import validate_bundle
    import tempfile

    out: list[dict] = []
    with tempfile.TemporaryDirectory(prefix="cycle-verify-") as tmp:
        bundle = build_bundle("rent-default", 100, enrich=True)
        bundle_path = Path(tmp) / "rent-default.bundle.json"
        bundle_path.write_text(json.dumps(bundle), encoding="utf-8")
        errors = validate_bundle(bundle)
        out.append({
            "claim": "the query_result_bundle validates against its own contract",
            "status": "PASS" if not errors else "FAIL",
            "observed": errors or "validate_bundle returned no errors",
            "definition_source": "product/query/bundle.py::validate_bundle",
        })
        page_ok, page_msg = verify_page(bundle_path)
        out.append({
            "claim": "the shipped page honours its DOM contract on a live bundle",
            "status": "PASS" if page_ok else "FAIL",
            "observed": page_msg,
            "definition_source": "product/verify_query_page.js",
        })
        summary = summarise(bundle)
        out.append({
            "claim": "the slice renders a map of decisions with coordinates and clusters",
            "status": "PASS" if summary.get("rows_with_xy") == summary.get("n_decisions")
            and summary.get("n_decisions", 0) > 0 else "FAIL",
            "observed": {
                "n_decisions": summary.get("n_decisions"),
                "rows_with_xy": summary.get("rows_with_xy"),
                "n_clusters": summary.get("n_clusters"),
                "answer_status": summary.get("answer_status"),
                "rows_with_source_url": summary.get("rows_with_source_url"),
            },
            "definition_source": "product/offline_slice.py::summarise",
        })
        out.append({
            "claim": "every mapped decision carries a source link",
            "status": "PASS"
            if summary.get("rows_with_source_url") == summary.get("n_decisions") else "FAIL",
            "observed": f"{summary.get('rows_with_source_url')}/{summary.get('n_decisions')}",
        })
        out.append({
            "claim": "enrichment preserved the geometry the map already rendered",
            "status": "PASS" if summary.get("geometry_preserved_by_enrich") else "FAIL",
            "observed": summary.get("geometry_preserved_by_enrich"),
        })
    return out


def check_counter_authority_counts() -> list[dict]:
    """RF1's number, recomputed from a live bundle.

    Both definitions are published, each labelled: the honest ambiguity in
    RF1's own report (supporting 7 vs cited 5 measured at different stages) is
    why this check reports the breakdown instead of a single count.
    """
    from product.offline_slice import build_bundle
    from product.query.counter_status import (
        NON_COUNTER_STATUSES,
        counter_authority_count,
        counter_status_bearing_count,
    )

    bundle = build_bundle("rent-default", 100, enrich=True)
    rows = bundle.get("decisions") or []
    real = counter_authority_count(rows)
    bearing = counter_status_bearing_count(rows)
    by_status: dict[str, int] = {}
    for row in rows:
        key = str(row.get("counter_status") or "none")
        by_status[key] = by_status.get(key, 0) + 1
    evidenced = [
        r["decision_id"] for r in rows
        if str(r.get("counter_status") or "") not in NON_COUNTER_STATUSES
        and r.get("counter_evidence_verified") is True
    ]
    return [
        {
            "claim": "'counter authorities' is measured with the accepted single source "
                     "of truth, never counter_status != 'none'",
            "status": "PASS",
            "observed": {
                "counter_authorities": real,
                "counter_status_bearing_rows": bearing,
                "by_status": by_status,
                "evidenced_counter_rows": sorted(evidenced),
                "non_counter_statuses": sorted(repr(x) for x in NON_COUNTER_STATUSES),
            },
            "definition_source": "product/query/counter_status.py (re-exported by "
                                 "gate_admissibility, object identity preserved)",
            "note": "both counts are published side by side on purpose; the broad one is "
                    "provenance, not a legal finding",
        },
        {
            "claim": "the counter count can never exceed the status-bearing count",
            "status": "PASS" if real <= bearing else "FAIL",
            "observed": f"{real} <= {bearing}",
        },
    ]


def check_relation_channel() -> list[dict]:
    """The shipped bundle must state its relation-channel state, with counts."""
    from product.offline_slice import build_bundle
    from product.query.relation_channel import CHANNEL_STATES

    bundle = build_bundle("rent-default", 100, enrich=True)
    prov = (bundle.get("provenance") or {}).get("relations_provenance") or {}
    state = prov.get("channel_state")
    n_relations = len(bundle.get("relations") or [])
    measured = (prov.get("channel") or {}).get("measured") or {}
    after = prov.get("channel_after_hydration") or {}
    return [
        {
            "claim": "the bundle publishes a named relation-channel state",
            "status": "PASS" if state in CHANNEL_STATES else "FAIL",
            "observed": {"channel_state": state, "n_relations": n_relations,
                         "n_rows_with_citation": measured.get("n_rows_with_citation"),
                         "n_decisions": measured.get("n_decisions")},
            "definition_source": "product/query/relation_channel.py",
        },
        {
            "claim": "the published state agrees with the edge count it describes",
            "status": "PASS"
            if (state == "POPULATED") == (n_relations > 0) else "FAIL",
            "observed": f"state={state} n_relations={n_relations}",
        },
        {
            "claim": "the channel is re-measured after evidence hydration, and both "
                     "measurements are kept",
            "status": "PASS" if after.get("measured", {}).get("phase") == "after_hydration"
            and measured.get("n_decisions") else "FAIL",
            "observed": {
                "map_build_rows_with_citation": measured.get("n_rows_with_citation"),
                "after_hydration_rows_with_citation":
                    (after.get("measured") or {}).get("n_rows_with_citation"),
                "relations_added_by_hydration": prov.get("relations_added_by_hydration"),
            },
        },
    ]


def check_fail_closed_posture() -> list[dict]:
    """The accepted verdicts pin the posture; this is where a slip would hide."""
    if not STATE_PATH.is_file():
        return [_fail("state/product.json exists", "missing")]
    try:
        state = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [_fail("state/product.json parses", repr(exc))]
    out = [{
        "claim": "state/product.json parses and is anchored to a direction version",
        "status": "PASS" if isinstance(state.get("direction_version"), int) else "FAIL",
        "observed": {"direction_version": state.get("direction_version"),
                     "cycle_status": str(state.get("cycle_status"))[:80]},
    }]
    drift = {k: state.get(k) for k, v in REQUIRED_FAIL_CLOSED.items() if state.get(k) != v}
    out.append({
        "claim": "admission stays fail-closed and no owner session is authorised",
        "status": "PASS" if not drift else "FAIL",
        "observed": drift or {k: state.get(k) for k in REQUIRED_FAIL_CLOSED},
        "definition_source": "direction v56: the accepted serve verdict carries "
                             "owner_decision_required=false, so nothing may raise a gate",
    })
    out.append({
        "claim": "the lane still recommends continuing",
        "status": "PASS" if state.get("continue_recommended") is True else "FAIL",
        "observed": state.get("continue_recommended"),
    })
    return out


def check_no_owner_question() -> list[dict]:
    """RF0's withdrawal must be in the artifact, not only in prose."""
    if not INTAKE_PATH.is_file():
        return [_fail("the serve-audit intake record exists", "missing")]
    try:
        intake = json.loads(INTAKE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [_fail("the intake record parses", repr(exc))]
    route = (intake.get("route_around") or {})
    fired = intake.get("owner_question") or {}
    return [
        {
            "claim": "no owner question is staged or fired from the accepted verdict",
            "status": "PASS"
            if (fired.get("question") in (None, "") and not fired.get("question_deleted") is False)
            and "NO_OWNER_QUESTION" in str(route.get("status") or "") else "FAIL",
            "observed": {"route_around": route.get("status"),
                         "owner_question": fired.get("question"),
                         "question_deleted": fired.get("question_deleted")},
        },
        {
            "claim": "the record states the accepted verdict's owner_decision_required",
            "status": "PASS" if intake.get("owner_decision_required") is False else "FAIL",
            "observed": intake.get("owner_decision_required"),
        },
        {
            "claim": "the withdrawn firing stays NAMED so the correction is auditable",
            "status": "PASS" if route.get("superseded_status") else "FAIL",
            "observed": route.get("superseded_status"),
        },
    ]


def check_tracked_results_not_mutated() -> list[dict]:
    """RF3's guard, re-run: a full slice must not touch the tracked results tree."""
    import hashlib

    if not TRACKED_FEEDBACK.is_file():
        return [_fail("the tracked jurist-feedback file exists", "missing")]
    before = hashlib.sha256(TRACKED_FEEDBACK.read_bytes()).hexdigest()
    from product.offline_slice import build_bundle

    build_bundle("rent-default", 100, enrich=True)
    after = hashlib.sha256(TRACKED_FEEDBACK.read_bytes()).hexdigest()
    return [{
        "claim": "running the product does not write into the tracked results tree",
        "status": "PASS" if before == after else "FAIL",
        "observed": {"sha256_before": before[:16], "sha256_after": after[:16],
                     "path": _repo_relative(TRACKED_FEEDBACK)},
        "definition_source": "RF3 (audit CYCLE_39069382456): test residue shipped as "
                             "cycle delta",
    }]


def check_orchestration_classification() -> list[dict]:
    """The diagnosis itself must re-derive, not restate."""
    if not ORCHESTRATION_ARTIFACT.is_file():
        return [_fail("the run-39082232157 orchestration artifact exists", "missing")]
    try:
        data = json.loads(ORCHESTRATION_ARTIFACT.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [_fail("the orchestration artifact parses", repr(exc))]
    from product import orchestration_evidence as oe

    recomputed = oe.classify(
        observation=data.get("observation"),
        jobs=data.get("job_conclusions") or {},
        steps=data.get("steps") or [],
    )
    stated = (data.get("classification") or {}).get("class")
    quantum = oe.quantum_analysis(data.get("steps") or [], oe.read_wrapper_quantum())
    return [
        {
            "claim": "the recorded death class is reproducible from the recorded evidence",
            "status": "PASS" if recomputed["class"] == stated else "FAIL",
            "observed": {"stated": stated, "recomputed": recomputed["class"]},
            "definition_source": "product/orchestration_evidence.py::classify",
        },
        {
            "claim": "the rc-78 work-quantum class is excluded by arithmetic, not by prose",
            "status": "PASS" if quantum.get("duration_exceeded_quantum") is True
            and quantum.get("quantum_plausibly_fired") is False else "FAIL",
            "observed": {"agent_step_duration_s": quantum.get("agent_step_duration_s"),
                         "wrapper_quantum_s": quantum.get("wrapper_quantum_s")},
        },
        {
            "claim": "the producing snapshot survived and no verdict exists",
            "status": "PASS"
            if (data.get("classification") or {}).get("producing_snapshot_survived") is True
            and (data.get("classification") or {}).get("verdict_exists") is False
            and data.get("audit_branch_exists") is False else "FAIL",
            "observed": {"team": (data.get("job_conclusions") or {}).get("team"),
                         "audit_branch_exists": data.get("audit_branch_exists")},
        },
    ]


def check_git_scope() -> list[dict]:
    """The lane's own write scope, checked the same way the workflow checks it."""
    code = "product"
    try:
        out = subprocess.run(  # noqa: S603
            ["git", "status", "--porcelain", "-uall"],
            cwd=REPO_ROOT, capture_output=True, text=True, timeout=60, check=False,
        )
    except Exception as exc:  # pragma: no cover
        return [_fail("git status runs", repr(exc))]
    bad = []
    for line in out.stdout.splitlines():
        path = line[3:]
        if not path:
            continue
        if not (path.startswith(f"{code}/") or path.startswith(f"results/{code}/")
                or path.startswith(f"reports/{code}/") or path.startswith(f"tests/{code}/")
                or path == f"state/{code}.json"):
            bad.append(path)
    return [{
        "claim": "this cycle's working tree stays inside the lane's write scope",
        "status": "PASS" if not bad else "FAIL",
        "observed": bad or "no out-of-scope path in git status",
        "definition_source": "core-lane.yml 'Enforce lane write scope'",
    }]


CHECKS: dict[str, Callable[[], list[dict]]] = {
    "slice": check_slice_and_page_contract,
    "counter": check_counter_authority_counts,
    "relation": check_relation_channel,
    "posture": check_fail_closed_posture,
    "owner_question": check_no_owner_question,
    "tracked": check_tracked_results_not_mutated,
    "orchestration": check_orchestration_classification,
    "scope": check_git_scope,
}


def run(selected: list[str] | None = None) -> dict:
    names = list(CHECKS)
    if selected:
        unknown = [s for s in selected if s not in CHECKS]
        if unknown:
            raise SystemExit(f"unknown check(s): {unknown}; known: {names}")
        names = [n for n in names if n in selected]
    entries: list[dict] = []
    for name in names:
        try:
            rows = CHECKS[name]()
        except Exception as exc:  # a check that blows up is a FAIL, never a pass
            rows = [_fail(f"check '{name}' completes", f"{type(exc).__name__}: {exc}")]
        for row in rows:
            row["check"] = name
        entries.extend(rows)
    failed = [e for e in entries if e["status"] != "PASS"]
    return {
        "schema": SCHEMA,
        "checks_run": names,
        "n_claims": len(entries),
        "n_failed": len(failed),
        "verdict": "PASS" if not failed else "FAIL",
        "claims": entries,
        "environment": {
            "python": sys.version.split()[0],
            "cwd": os.getcwd(),
            "numpy": _safe_version("numpy"),
            "scipy": _safe_version("scipy"),
            "scikit_learn": _safe_version("sklearn"),
        },
        "claim_ceiling": (
            "This verifies the product lane's OWN shipped behaviour and posture from "
            "committed artifacts and live runs of the product's own code. It scores no "
            "frozen bar, reads no Frontier verdict, and promotes nothing. A PASS here is "
            "not an audit verdict and is not a human-gate input."
        ),
    }


def _safe_version(module: str) -> str | None:
    try:
        mod = __import__(module)
        return getattr(mod, "__version__", "unknown")
    except Exception:
        return None


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run-id", default=None, help="stamped into the artifact")
    ap.add_argument("--only", default=None, help="comma-separated subset of checks")
    ap.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--json", action="store_true", help="machine-readable output only")
    args = ap.parse_args(argv)

    ledger = run([s for s in (args.only or "").split(",") if s] or None)
    if args.run_id:
        ledger["run_id"] = int(args.run_id)

    if args.json:
        print(json.dumps(ledger, indent=2, sort_keys=True))
    else:
        for entry in ledger["claims"]:
            print(f"[{entry['status']}] ({entry['check']}) {entry['claim']}")
            if entry["status"] != "PASS":
                print(f"        observed: {json.dumps(entry['observed'], default=str)[:400]}")
        print(f"\n{ledger['verdict']}: {ledger['n_claims'] - ledger['n_failed']}"
              f"/{ledger['n_claims']} claims verified")

    if args.write:
        name = f"CYCLE_{args.run_id}_cycle_verify.json" if args.run_id else "cycle_verify.json"
        out = Path(args.out_dir) / name
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(ledger, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        if not args.json:
            print(f"wrote {out}", file=sys.stderr)
    return 0 if ledger["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

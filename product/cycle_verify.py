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
import re
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
#: The run this cycle diagnosed.  Pinned by name (not "newest") because it is a
#: historical fact that must keep being verified the same way after later runs
#: exist; the regression artifact below deliberately IS "newest", because each
#: cycle replaces it.
DIAGNOSIS_39086926860_ARTIFACT = (
    REPO_ROOT / "results" / "product" / "orchestration" / "CYCLE_39086926860_orchestration.json"
)
REGRESSION_DIR = REPO_ROOT / "results" / "product" / "regression"
#: Where product/test_delta_attribution.py writes. Same directory as the
#: regression scope artifacts, named apart so the newest-artifact readers stay
#: unambiguous (audit CYCLE_39123358661 pinned diagnostics by NAME for this reason).
ATTRIBUTION_DIR = REGRESSION_DIR
#: The 39119287975 snapshot diagnosis of the 39116225867 producer snapshot.
#: Pinned BY NAME (not "newest") because it is a historical record whose
#: artifact classification must stay checkable after later runs exist.
DIAGNOSIS_39116225867_ARTIFACT = (
    REPO_ROOT / "results" / "product" / "orchestration"
    / "CYCLE_39116225867_snapshot_diagnosis.json"
)
#: Set by ``--regression-dir`` for the duration of one ``main()`` invocation so
#: the FAIL-refusal invariant is demonstrable against a pinned artifact set.
REGRESSION_DIR_OVERRIDE: Path | None = None
#: A committed artifact set whose newest artifact GENUINELY FAILS the three
#: set-relation claims (a byte copy of the 39116225867 regression artifact,
#: which records n_repaired_only = 1).  This is what ``--regression-dir``
#: points at to produce a reproducible FAIL ledger; see
#: product/tests/test_regression_set_relation_matrix.py.
FAIL_FIXTURE_DIR = REPO_ROOT / "product" / "data" / "regression_fail_fixture"

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
# the guards that guard this lane's own publications
# --------------------------------------------------------------------------

#: The report-arithmetic guard module, imported lazily so this file's own import
#: budget stays stdlib-only (``test_fast_path_imports_without_the_dense_stack``
#: depends on it). The module itself imports nothing but json/re/pathlib.
REPORT_ARITHMETIC_GUARD = "product.tests.test_report_artifact_arithmetic"


def _guard_report_testcount_disclosure(
    disclosure_path: Path | None = None, live: dict | None = None) -> list[dict]:
    """Re-derive the report test-count disclosure guard (audit F1 of 39169296466).

    The rejected cycle shipped a tree that was RED on
    ``testcount_disclosure_artifact_is_current`` while this ledger reported
    PASS 44/44 - no claim here covered that module, which is audit F1b's exact
    finding. This claim closes that hole: it runs the guard's OWN sweep and
    compares it to the artifact the guard is pinned to, so a red guard is a red
    ledger.

    Both arguments exist so a negative control can point the claim at a stale
    artifact or a mutated sweep without touching the repository.
    """
    try:
        from product.tests import test_report_artifact_arithmetic as guard
        from product.report_scope_measurement import measure
    except Exception as exc:  # a check that cannot run is FAIL, never a pass
        return [_fail("the report-arithmetic guard can be loaded and run",
                      f"{type(exc).__name__}: {exc}")]

    pinned = Path(disclosure_path) if disclosure_path else guard.DISCLOSURE
    if not pinned.is_file():
        return [_fail("the pinned report test-count disclosure exists",
                      f"missing: {_repo_relative(pinned)} - re-measure and "
                      "re-publish with product/report_scope_measurement.py")]
    try:
        published = json.loads(pinned.read_text(encoding="utf-8"))
        fresh = live if live is not None else measure()
    except (OSError, json.JSONDecodeError) as exc:
        return [_fail("the report test-count disclosure parses", repr(exc))]

    claimed = published.get("bare_testcount_claims") or {}
    measured = fresh.get("bare_testcount_claims") or {}
    out = [_pass_or_fail(
        set(claimed) == set(measured) and all(
            claimed[k].get("bare_testcount_claims")
            == v.get("bare_testcount_claims") for k, v in measured.items()),
        "the pinned report test-count disclosure matches a fresh sweep of this tree",
        {"pinned": _repo_relative(pinned),
         "published_reports": sorted(claimed),
         "measured_reports": sorted(measured),
         "only_published": sorted(set(claimed) - set(measured)),
         "only_measured": sorted(set(measured) - set(claimed)),
         "regenerate": f"python3 product/report_scope_measurement.py --run-id <id> "
                       "--out results/product/regression/CYCLE_<id>_"
                       "report_testcount_disclosure.json"},
        definition_source="product/report_scope_measurement.py::measure(), which "
                          "calls the guard's own sweep functions over the committed "
                          "tree (collection and parsing only; no suite run)")]

    # Non-vacuity, in the same claim block: a sweep that finds nothing is a green
    # sweep of nothing, and publishing "no report carries a bare test-count claim"
    # would be an unbounded vacuity claim.
    out.append(_pass_or_fail(
        bool(measured) and bool(claimed),
        "the test-count candidate sweep is non-vacuous on this tree",
        {"reports_swept": len(measured),
         "note": "a report joins the candidate set by citing a regression-scope "
                 "artifact; zero means the sweep is measuring an empty tree"},
        definition_source="the guard's own sweep_testcount_candidates()"))

    cite_pub = published.get("citation_sweep") or {}
    cite_new = fresh.get("citation_sweep") or {}
    out.append(_pass_or_fail(
        cite_pub.get("artifact_report_pairs") == cite_new.get("artifact_report_pairs")
        and cite_pub.get("citation_claims_parsed")
        == cite_new.get("citation_claims_parsed"),
        "the pinned citation-sweep scope matches a fresh sweep of this tree",
        {"published_pairs": cite_pub.get("artifact_report_pairs"),
         "measured_pairs": cite_new.get("artifact_report_pairs"),
         "published_claims": cite_pub.get("citation_claims_parsed"),
         "measured_claims": cite_new.get("citation_claims_parsed")},
        definition_source="the guard's own citation_claim_coverage()"))
    return out


def _guard_state_register(state_path: Path | None = None) -> list[dict]:
    """Re-derive the state verification-register retention guard (audit F2).

    The rejected cycle deleted 12 accepted records from
    ``state/product.json``'s ``verification`` register - including the lane's own
    admitted failures - and nothing failed, because (audit note N4) no committed
    test read that register. This claim makes the ledger read it.
    """
    try:
        from product import state_register
    except Exception as exc:
        return [_fail("the state-register guard can be loaded", repr(exc))]
    target = Path(state_path) if state_path else STATE_PATH
    if not target.is_file():
        return [_fail("state/product.json exists", f"missing: {target}")]
    try:
        rows = state_register.rows(target)
    except Exception as exc:
        return [_fail("the state verification register can be compared",
                      f"{type(exc).__name__}: {exc}")]
    for row in rows:
        row["guard"] = (
            "state_register.retention (product/state_register.py, baseline "
            f"{state_register.BASELINE_COMMIT})")
    return rows


def check_committed_guards() -> list[dict]:
    """Every committed staleness guard is re-derived HERE, not only in pytest.

    Audit F1b of rejected cycle 39169296466: ``product/cycle_verify.py`` reported
    PASS 44/44 on a tree that was red on a committed guard, because no claim in
    it covered ``product/tests/test_report_artifact_arithmetic.py``. A ledger that
    cannot see a red guard is why this class survived two cycles.

    So this check calls the guards' own measurement functions and compares them
    to the artifacts they are pinned to. It deliberately does NOT shell out to
    pytest: the point is that the ONE COMMAND re-derives the guards, in seconds,
    with the same definitions the committed tests use.
    """
    return _guard_report_testcount_disclosure() + _guard_state_register()


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


def check_served_slice() -> list[dict]:
    """The SERVED composition is executed here: HTTP handler -> bundle -> page.

    ``check_slice_and_page_contract`` runs the pipeline with no server at all and
    the page contract against a bundle written to a temp file; neither proves that
    what the shipped ``query_app.Handler`` actually serves over a socket is the
    bundle the shipped page can render. ``product/server_slice.py`` closes that
    seam (one command, fixture providers, every non-loopback connect trapped), and
    this check re-runs it so the ledger cannot pass on a stale printed summary.
    """
    from product.server_slice import execute

    result = execute("Kündigung Mietvertrag Mietrecht", 100)
    result.pop("_served_bundle", None)
    result.pop("_first_page_bundle", None)
    rows = list(result.get("checks") or [])
    rows.append({
        "claim": "the served slice as a whole passes on this run",
        "status": "PASS" if result.get("verdict") == "PASS" else "FAIL",
        "observed": {
            "verdict": result.get("verdict"),
            "failures": result.get("failures"),
            "counts": result.get("counts"),
            "timing_s": result.get("timing_s"),
            "reproduce": "python3 product/server_slice.py --no-write",
        },
        "definition_source": "product/server_slice.py::execute",
        "claim_ceiling": result.get("claim_ceiling"),
    })
    return rows


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
        evidenced_counter_ids,
        unevidenced_counter_ids,
    )

    bundle = build_bundle("rent-default", 100, enrich=True)
    rows = bundle.get("decisions") or []
    real = counter_authority_count(rows)
    bearing = counter_status_bearing_count(rows)
    by_status: dict[str, int] = {}
    for row in rows:
        key = str(row.get("counter_status") or "none")
        by_status[key] = by_status.get(key, 0) + 1
    # F7 (audit CYCLE_39091749561): the ledger's "evidenced" and the page's
    # counterEvidenced() are now the SAME predicate, imported from the accepted
    # single source of truth. The weaker flag-only reading is still published,
    # labelled, so the difference between the two notions is visible rather than
    # silently resolved in either direction.
    evidenced = evidenced_counter_ids(rows)
    unevidenced = unevidenced_counter_ids(rows)
    flag_only = [
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
                "n_evidenced_counter_rows": len(evidenced),
                "unevidenced_counter_rows": sorted(unevidenced),
                "n_unevidenced_counter_rows": len(unevidenced),
                "verified_flag_only_counter_rows": sorted(flag_only),
                "non_counter_statuses": sorted(repr(x) for x in NON_COUNTER_STATUSES),
            },
            "definition_source": "product/query/counter_status.py (re-exported by "
                                 "gate_admissibility, object identity preserved); "
                                 "evidenced = counter_evidenced(), the Python twin of "
                                 "product/static/query.html::counterEvidenced",
            "note": "both counts are published side by side on purpose; the broad one is "
                    "provenance, not a legal finding, and the flag-only evidenced reading "
                    "is published beside the shared predicate so any disagreement between "
                    "the two notions is a measured finding, never a silent choice",
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


def check_test_delta_attribution() -> list[dict]:
    """The collected-test delta decomposition is re-derived here, not restated.

    Audit RF-1 of rejected cycle 39144924680 was a report of record that attributed
    a +21 collected-test delta to the cycle that did not produce it. Round 5 stopped
    repairing that prose and made the decomposition a MEASUREMENT
    (``product/test_delta_attribution.py``); this check is what keeps the report's
    quoted sentence and the measurement from drifting apart, in the lane's
    one-command gate rather than only in pytest.

    It re-measures the CURRENT tree's collection count (collection-only, ~2s: a
    full suite run here would re-spend the regression measurement the round-4
    audit explicitly fenced) and compares it with what the committed artifact says.
    """
    candidates = sorted(ATTRIBUTION_DIR.glob("CYCLE_*_test_delta_attribution.json"))
    if not candidates:
        return [_fail("a test-delta attribution artifact exists",
                      f"none found in {_repo_relative(ATTRIBUTION_DIR)}")]
    art = candidates[-1]
    try:
        data = json.loads(art.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [_fail("the attribution artifact parses", repr(exc))]

    steps = data.get("steps") or []
    step_sum = sum(s.get("collected_delta_vs_previous_step", 0) for s in steps)
    rows = [
        _pass_or_fail(
            step_sum == data.get("observed_collected_delta"),
            "the per-commit deltas sum to the published collected-test delta",
            {"step_sum": step_sum, "published": data.get("observed_collected_delta"),
             "steps": [s.get("short") for s in steps]},
            definition_source="product/test_delta_attribution.py (collection-only measurement)"),
    ]

    try:
        from product.test_delta_attribution import collect_count
        measured = collect_count(REPO_ROOT)
    except Exception as exc:  # a check that cannot run is FAIL, never a pass
        rows.append(_fail("this tree's collected count is re-measurable", repr(exc)))
        return rows

    tree = data.get("working_tree") or {}
    rows.append(_pass_or_fail(
        tree.get("collected_total") == measured,
        "the attribution artifact's working-tree count still equals this tree's",
        {"artifact": tree.get("collected_total"), "measured_now": measured,
         "regenerate": "python3 product/test_delta_attribution.py --base "
                       f"{str(data.get('base', {}).get('commit'))[:7]} --run-id <id> "
                       "--out results/product/regression/CYCLE_<id>_test_delta_attribution.json"},
        definition_source="pytest --collect-only -q, run live by this check"))

    line = data.get("decomposition_line") or ""
    quoting = [p for p in sorted((REPO_ROOT / "reports" / "product").glob("*.md"))
               if art.name in p.read_text(encoding="utf-8")]
    rows.append(_pass_or_fail(
        bool(quoting) and all(line in p.read_text(encoding="utf-8") for p in quoting),
        "every report citing the attribution quotes its decomposition line verbatim",
        {"citing_reports": [p.name for p in quoting], "line": line},
        definition_source="the tool's canonical sentence; prose is not a second source of truth"))
    return rows


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


def check_query_runtime_declared() -> list[dict]:
    """The fast path's third-party runtime must be declared AND importable.

    Measured failure this guards (run 39128456801): on a fresh runner no step of
    ``.github/workflows/core-lane.yml`` installs
    ``product/requirements-query.txt``, so ``numpy``/``sklearn`` are absent and
    the slice, counter, relation, relation_direction and tracked checks all die
    with ``ModuleNotFoundError`` - five red claims that say nothing about the
    product.  ``.github/**`` is control-plane scope and is never edited from this
    lane, so the fix has to live here: the runtime is declared in
    ``product/query_env.py``, installable in one command
    (``product/bootstrap_query_env.sh``), and checked below.

    Fail-closed: a missing dependency is a FAIL with the remedy attached, never
    a skip and never a silent pass.
    """
    from product import query_env

    probe = query_env.probe()
    pins = query_env.requirements_pins()
    declared_missing = sorted(
        m for m in query_env.REQUIRED if query_env.requirement_name(m) not in pins)
    return [
        {
            "claim": "the query fast path's third-party runtime is importable, so the "
                     "vertical slice's own checks can run instead of dying on "
                     "ModuleNotFoundError",
            "status": "PASS" if probe["ok"] else "FAIL",
            "observed": {
                "python": probe["python"],
                "required": probe["required"],
                "installed": probe["installed"],
                "missing": probe["missing"],
                "remedy": probe["remedy"],
            },
            "definition_source": "product/query_env.py::probe",
            "note": probe["workflow_gap"],
        },
        {
            "claim": "every module the fast path imports is declared in "
                     "product/requirements-query.txt",
            "status": "PASS" if not declared_missing else "FAIL",
            "observed": {"requirements_pins": pins, "undeclared": declared_missing},
            "definition_source": "product/query_env.py::REQUIRED vs "
                                 "product/query_env.py::requirements_pins",
        },
        {
            "claim": "the measured numeric environment is published beside this ledger",
            "status": "PASS",
            "observed": {"pinned": probe["pinned"],
                         "installed_matches_pin": probe["installed_matches_pin"],
                         "bootstrap": _repo_relative(query_env.BOOTSTRAP)},
            "definition_source": "product/query_env.py::PINNED (standing numeric rule: "
                                 "the environment travels with every sha; versions are "
                                 "recorded, never rounded to force identity)",
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


def check_orchestration_diagnosis_39086926860() -> list[dict]:
    """The diagnosis of run 39086926860 must re-derive from its own record.

    That run's producer snapshot survived its audit job's death, so the lane owes
    a *cause-space* answer rather than a story.  Every claim here is recomputed
    with ``product/orchestration_evidence.py`` from the artifact's OWN recorded
    inputs (steps, annotations, exit code) - never read back as a conclusion.
    """
    art = DIAGNOSIS_39086926860_ARTIFACT
    if not art.is_file():
        return [_fail("the 39086926860 orchestration artifact exists", "missing")]
    try:
        data = json.loads(art.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [_fail("the orchestration artifact parses", repr(exc))]
    from product import orchestration_evidence as oe

    diag = data.get("diagnosis") or {}
    cand = diag.get("candidates") or {}
    rows: list[dict] = []

    recomputed_class = oe.classify(
        observation=data.get("observation"),
        jobs=data.get("job_conclusions") or {},
        steps=data.get("steps") or [],
    )["class"]
    rows.append(_pass_or_fail(
        recomputed_class == (data.get("classification") or {}).get("class"),
        "the 39086926860 death class re-derives from the recorded job record",
        {"stated": (data.get("classification") or {}).get("class"),
         "recomputed": recomputed_class},
        "product/orchestration_evidence.py::classify"))

    parsed = oe.parse_exit_code(diag.get("annotations") or [])["exit_code"]
    rows.append(_pass_or_fail(
        diag.get("annotations_collected") is True and parsed is not None
        and parsed == diag.get("exit_code"),
        "the exit code is taken from a public check-run annotation, not from a guess",
        {"annotations_collected": diag.get("annotations_collected"),
         "recorded_exit_code": diag.get("exit_code"), "recomputed_exit_code": parsed},
        "product/orchestration_evidence.py::parse_exit_code "
        "(job logs are admin-only; annotations are public)"))

    re_narrowed = oe.wrapper_exit_candidates(
        diag.get("exit_code"),
        step_duration_s=diag.get("audit_agent_step_duration_s"),
        quantum_s=cand.get("quantum_s") or oe.read_wrapper_quantum(),
        retry=cand.get("retry_params") or oe.read_wrapper_retry_params(),
    )
    rows.append(_pass_or_fail(
        re_narrowed["surviving_named_branches"] == cand.get("surviving_named_branches"),
        "the surviving wrapper branches re-derive from the recorded exit code and timings",
        {"recorded": cand.get("surviving_named_branches"),
         "recomputed": re_narrowed["surviving_named_branches"]},
        "product/orchestration_evidence.py::wrapper_exit_candidates"))

    no_evidence = [
        c.get("branch") for c in (cand.get("named_branches") or [])
        if c.get("ruled_out") is True and not c.get("ruled_out_evidence")
    ]
    rows.append(_pass_or_fail(
        cand.get("named_branches") and not no_evidence,
        "no branch is ruled out without published evidence for the ruling",
        {"branches_without_evidence": no_evidence,
         "n_named_branches": len(cand.get("named_branches") or [])}))

    control = Path(diag.get("control_plane_source") or "/tmp/lex_control")
    replay = oe.replay_wrapper_preflight(control, REPO_ROOT / ".opencode" / "agents")
    rows.append(_pass_or_fail(
        replay["all_pass"] is True and replay["all_pass"] == (diag.get("preflight") or {}).get("all_pass"),
        "the wrapper's pre-opencode preflight still replays clean on the staged inputs",
        {"recorded": (diag.get("preflight") or {}).get("all_pass"),
         "recomputed": replay["all_pass"], "control_plane_source": str(control)},
        "product/orchestration_evidence.py::replay_wrapper_preflight"))

    forbidden = oe.forbidden_verdict_keys(data)
    rows.append(_pass_or_fail(
        not forbidden and (data.get("classification") or {}).get("verdict_exists") is False
        and data.get("audit_branch_exists") is False,
        "the diagnosis publishes a cause space, never a gate or a product verdict",
        {"forbidden_keys_present": forbidden,
         "verdict_exists": (data.get("classification") or {}).get("verdict_exists"),
         "audit_branch_exists": data.get("audit_branch_exists")}))
    return rows


def regression_set_relation_rows(art: Path, data: Any) -> list[dict]:
    """The three set-relation claims, as a PURE function of ONE artifact.

    Extracted from :func:`check_regression_set_relation` (cycle 39123358661) so
    that every committed artifact can be classified by the SAME predicate the
    newest-artifact gate uses.  Before the split, "which artifact produces
    PASS/PASS" could only be answered by copying the three expressions into an
    ad-hoc script, and a copied expression silently diverged from the gate:
    cycle 39119287975 published ``CYCLE_39116225867_regression_scope.json`` in
    a PASS/PASS list while the gate actually FAILs it (that artifact records
    ``n_repaired_only = 1``).  One definition, many artifacts - no copies.
    """
    rel = (data or {}).get("set_relation") or {}
    arith = (data or {}).get("arithmetic") or {}
    scope = (data or {}).get("scope") or {}
    return [
        _pass_or_fail(
            rel.get("set_difference_repaired_only_NEW_FAILURES") == [],
            "the run under test introduces no failing test id absent from the baseline",
            {"artifact": _repo_relative(art),
             "repaired_only_new_failures": rel.get("set_difference_repaired_only_NEW_FAILURES"),
             "n_baseline_only": rel.get("n_baseline_only")},
            "product/regression_scope.py (set relation, never counts alone)"),
        _pass_or_fail(
            arith.get("arithmetic_reconciles") is True,
            "the published pass/fail arithmetic closes on the set relation it measured",
            {"identity": arith.get("identity"), "notes": arith.get("notes"),
             "passed_delta": arith.get("passed_delta"),
             "collected_delta": arith.get("collected_delta")}),
        _pass_or_fail(
            bool(scope.get("measured_at_checkout_root")) and bool(scope.get("baseline_checkout_root")),
            "both roots the set relation was measured at are published with it",
            {"measured_at": scope.get("measured_at_checkout_root"),
             "baseline_at": scope.get("baseline_checkout_root"),
             "declared_label": scope.get("declared_label")}),
    ]


def classify_regression_artifact(art: Path) -> dict:
    """One committed artifact -> its three verdicts, or the error that stopped it."""
    try:
        data = json.loads(art.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {"artifact": _repo_relative(art), "name": art.name,
                "verdicts": ["FAIL"] * 3, "reads": f"{type(exc).__name__}: {exc}"}
    rows = regression_set_relation_rows(art, data)
    return {
        "artifact": _repo_relative(art),
        "name": art.name,
        "schema": (data or {}).get("schema"),
        "verdicts": [r["status"] for r in rows],
        "all_pass": all(r["status"] == "PASS" for r in rows),
        "any_fail": [r["claim"] for r in rows if r["status"] != "PASS"],
        "reads": "ok",
    }


def check_regression_set_relation() -> list[dict]:
    """The newest regression artifact must be a SET relation that closes.

    Counts alone are how this lane once published "+7 tests".  The claims here
    are the two differences of the failing-ID sets plus the arithmetic identity,
    all read from the artifact ``product/regression_scope`` wrote.

    ``--regression-dir`` repoints this check at another committed artifact set
    (cycle 39123358661).  That exists so the FAIL-refusal invariant can be
    demonstrated against a PINNED failing artifact instead of against whatever
    happens to be newest - the previous live demonstration was time-dependent
    and stopped reproducing the moment a clean artifact landed, which made a
    true invariant unprovable in a report (audit CYCLE_39119287975 DEFECT A).
    """
    directory = REGRESSION_DIR_OVERRIDE or REGRESSION_DIR
    candidates = sorted(directory.glob("CYCLE_*_regression_scope.json"))
    if not candidates:
        return [_fail("a regression-scope artifact exists", f"none found in {_repo_relative(directory)}")]
    art = candidates[-1]
    try:
        data = json.loads(art.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [_fail("the regression artifact parses", repr(exc))]
    rows = regression_set_relation_rows(art, data)
    for row in rows:
        row["regression_dir"] = _repo_relative(directory)
    return rows


def _pass_or_fail(ok: bool, claim: str, observed: Any, definition_source: str | None = None) -> dict:
    row = {"claim": claim, "status": "PASS" if ok else "FAIL", "observed": observed}
    if definition_source:
        row["definition_source"] = definition_source
    return row


def check_v57_handoffs() -> list[dict]:
    """Re-derive both v57 handoff decisions from their own sources.

    Two separate obligations are checked here and they fail independently, so a
    false claim in one cannot hide behind a pass in the other:

    1. **The evaluation falsification handoff** (direction v57 ordered work 4).
       The committed handoff artifact must be *current*: every number in it is
       recomputed by ``product/eval_disclosure_handoff.build()`` against the
       committed packet bytes, whose raw sha256 is re-hashed here too.  A
       hand-edited artifact is a FAIL, not a cosmetic difference.
    2. **The Frontier adoption decision** (factory-wide requirement 21).  The
       committed decision record must be a real decision (ADOPT or DECLINE) with
       at least one recorded reason - never silence, and never
       ``DECISION_NOT_REACHABLE``.

    Both are derived, never asserted: nothing below is copied out of a report.
    """
    rows: list[dict] = []

    # ---- 1. the evaluation handoff, recomputed from committed bytes --------
    try:
        from product.eval_disclosure_handoff import PACKET_DIR, PACKET_SHA256, build

        live = build()
        summary = live.get("summary") or {}
        rows.append(_pass_or_fail(
            not live.get("failures"),
            "the committed packet bytes re-hash to the pinned digest, so the "
            "before/after handoff is scoped to the bytes of record",
            {"failures": live.get("failures"),
             "packet_raw_sha256_recomputed": (live.get("packet") or {}).get("packet_raw_sha256_recomputed"),
             "expected": PACKET_SHA256},
            "product/eval_disclosure_handoff.py::build"))
        rows.append(_pass_or_fail(
            int(summary.get("n_inconsistent_before") or 0) >= 1,
            "the committed admission record really does contradict itself on at "
            "least one served question (measured under-covered concepts with "
            "warning_count 0)",
            {"n_inconsistent_before": summary.get("n_inconsistent_before"),
             "n_questions": summary.get("n_questions")},
            "product/eval_disclosure_handoff.py::build"))
        rows.append(_pass_or_fail(
            summary.get("n_disclosed_after") == summary.get("n_questions")
            and int(summary.get("n_questions") or 0) > 0,
            "recomputing the admission record on those same bytes now discloses "
            "the measurement for every served question",
            {"n_disclosed_after": summary.get("n_disclosed_after"),
             "n_questions": summary.get("n_questions")},
            "product/eval_disclosure_handoff.py::build"))
        rows.append(_pass_or_fail(
            int(summary.get("n_admission_changed") or 0) == 0
            and int(summary.get("n_blocking_count_changed") or 0) == 0,
            "the fix is disclosure only: it changes no admissible flag and no "
            "blocking count on any served question",
            {"n_admission_changed": summary.get("n_admission_changed"),
             "n_blocking_count_changed": summary.get("n_blocking_count_changed")},
            "product/eval_disclosure_handoff.py::build"))

        artifact = REPO_ROOT / "results" / "product" / "gate_packet" / \
            "REBUILT_39027045675_QUERY_CONCEPT_DISCLOSURE_HANDOFF.json"
        if artifact.is_file():
            committed = json.loads(artifact.read_text(encoding="utf-8"))
            csum = committed.get("summary") or {}
            mismatched = sorted(k for k in ("n_questions", "n_inconsistent_before",
                                            "n_disclosed_after", "n_admission_changed",
                                            "n_blocking_count_changed")
                                if csum.get(k) != summary.get(k))
            rows.append(_pass_or_fail(
                not mismatched,
                "the committed handoff artifact is current against a fresh "
                "recomputation (a hand-edited artifact is a FAIL)",
                {"artifact": str(artifact.relative_to(REPO_ROOT)),
                 "mismatched_summary_fields": mismatched,
                 "committed": {k: csum.get(k) for k in (
                     "n_questions", "n_inconsistent_before", "n_disclosed_after",
                     "n_admission_changed", "n_blocking_count_changed")},
                 "recomputed": {k: summary.get(k) for k in (
                     "n_questions", "n_inconsistent_before", "n_disclosed_after",
                     "n_admission_changed", "n_blocking_count_changed")}},
                "product/eval_disclosure_handoff.py::build"))
        else:
            rows.append(_fail("the committed handoff artifact exists",
                              f"missing {artifact}"))
    except Exception as exc:  # a check that blows up is a FAIL, never a pass
        rows.append(_fail("the evaluation falsification handoff re-derives",
                          f"{type(exc).__name__}: {exc}"))

    # ---- 2. the Frontier adoption decision --------------------------------
    try:
        from product.frontier_recall_adoption import TEAM, inspect

        live = inspect()
        rows.append(_pass_or_fail(
            live.get("decision") in ("ADOPT", "DECLINE"),
            "the accepted Frontier component has a recorded adopt/decline "
            "decision, not silence and not DECISION_NOT_REACHABLE",
            {"decision": live.get("decision"), "mount_present": live.get("mount_present"),
             "failures": live.get("failures"), "team_id": TEAM},
            "product/frontier_recall_adoption.py::inspect"))
        rows.append(_pass_or_fail(
            bool(live.get("decline_reasons") or live.get("decision") == "ADOPT"),
            "the decision carries at least one machine-copied measured reason",
            {"n_reasons": len(live.get("decline_reasons") or []),
             "numbers": live.get("numbers_from_contract")},
            "product/frontier_recall_adoption.py::inspect"))

        art = REPO_ROOT / "results" / "product" / "frontier_verdicts" / \
            "frontier-query-concept-recall_adoption_39179862363.json"
        if art.is_file():
            committed = json.loads(art.read_text(encoding="utf-8"))
            same = committed.get("decision") == live.get("decision") and \
                (committed.get("numbers_from_contract") or {}) == (live.get("numbers_from_contract") or {})
            rows.append(_pass_or_fail(
                same,
                "the committed adoption record matches a fresh read of the "
                "accepted mount",
                {"artifact": str(art.relative_to(REPO_ROOT)),
                 "committed_decision": committed.get("decision"),
                 "recomputed_decision": live.get("decision")},
                "product/frontier_recall_adoption.py::inspect"))
        else:
            rows.append(_fail("the committed adoption record exists", f"missing {art}"))
    except Exception as exc:
        rows.append(_fail("the Frontier adoption decision re-derives",
                          f"{type(exc).__name__}: {exc}"))

    return rows


def check_live_slice_stage_disclosure() -> list[dict]:
    """Every committed live-slice record says which stages it actually ran.

    Run 39187482610 committed ``results/product/live_slice/20261019T022100Z.json``
    with ``verdict: "PASS"`` and a claim ceiling naming the sourced answer and the
    counter-authority pass, while the same record reported a ``pending`` answer,
    ``n_cited: 0``, ``counter_status_bearing_rows: 0`` and ``enrich_s: 0.0`` - the
    fingerprint of a ``--no-enrich`` run, published with no field saying the slow
    phase never executed.  That is the binding 2026-10-18 defect class: a
    published claim that does not reproduce from the committed tree.

    Three claims are re-derived here, each from committed bytes:

    1. the instrument cannot publish PASS for a map-only run any more;
    2. every committed record is classified from its OWN answer/counter/timing
       fields, and a record published after the fix must agree with its own bytes;
    3. the committed amendment artifact is *current* - a hand-edited or stale
       amendment is a FAIL, exactly as for the v57 handoff artifact.

    Nothing here is copied out of a report.
    """
    rows: list[dict] = []
    try:
        from product.live_slice import stage_disclosure, verdict_for
        from product.live_slice_stage_amendment import ARTIFACT, build, map_only_fingerprint

        map_only = stage_disclosure(n_rows=100, enrich=False, enrich_error=None,
                                    answer_status="pending")
        checks_all_green = {k: True for k in (
            "retrieval_mode_served_is_refresh", "no_cache_hits_on_the_network_leg",
            "adapter_made_network_calls", "independent_probe_saw_the_network",
            "enrichment_never_moved_a_point_already_on_the_map", "map_has_rows",
            "every_row_has_xy", "every_row_has_a_source_link", "bundle_validates",
            "page_contract_ok")}
        checks_all_green["canonical_chain_ran"] = map_only["canonical_chain"]
        rows.append(_pass_or_fail(
            verdict_for(checks_all_green, map_only) != "PASS",
            "the live-slice instrument can no longer publish a chain PASS for a "
            "map-only run (every other check green is exactly the 39187482610 shape)",
            {"stage_disclosure": map_only,
             "checks_all_green": checks_all_green,
             "verdict_returned": verdict_for(checks_all_green, map_only)},
            "product/live_slice.py::verdict_for"))

        full = stage_disclosure(n_rows=100, enrich=True, enrich_error=None,
                                answer_status="ready")
        rows.append(_pass_or_fail(
            verdict_for({"page_contract_ok": True,
                         "canonical_chain_ran": full["canonical_chain"]}, full) == "PASS",
            "a full chain run is still reported as PASS, so the disclosure did not "
            "demote the narrowest real success",
            {"stages": full},
            "product/live_slice.py::verdict_for"))

        live = build()
        summary = live.get("summary") or {}
        rows.append(_pass_or_fail(
            not live.get("failures"),
            "every committed live-slice record agrees with its own bytes, or is "
            "named by the amendment as a pre-fix record",
            {"failures": live.get("failures"), "verdict": live.get("verdict"),
             "summary": summary},
            "product/live_slice_stage_amendment.py::build"))

        rows.append(_pass_or_fail(
            int(summary.get("n_records") or 0) > 0
            and int(summary.get("n_amended_map_only") or 0) >= 1,
            "the sweep sees the timestamp-named record that a CYCLE_*-only glob "
            "missed, and names it rather than dropping it",
            {"n_records": summary.get("n_records"),
             "amended_artifacts": summary.get("amended_artifacts"),
             "n_staged": summary.get("n_staged")},
            "product/live_slice_stage_amendment.py::build"))

        if ARTIFACT.exists():
            committed = json.loads(ARTIFACT.read_text(encoding="utf-8"))
            current = json.dumps(committed.get("records"), sort_keys=True) == json.dumps(
                live.get("records"), sort_keys=True)
            rows.append(_pass_or_fail(
                current,
                "the committed stage-disclosure amendment is current against a "
                "fresh recomputation (a hand-edited artifact is a FAIL)",
                {"artifact": str(ARTIFACT.relative_to(REPO_ROOT)),
                 "matches_fresh_recomputation": current},
                "product/live_slice_stage_amendment.py::build"))
        else:
            rows.append(_fail("the committed stage-disclosure amendment exists",
                              f"missing {ARTIFACT}"))
    except Exception as exc:
        rows.append(_fail("the live-slice stage disclosure re-derives",
                          f"{type(exc).__name__}: {exc}"))

    return rows


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


def check_relation_direction() -> list[dict]:
    """A shared_citation edge states the co-citation in French, never the raw token.

    Re-derived live (never asserted): the real offline pipeline output for the
    leg whose relations are shared_citation-only is written to a scratch file
    and run through the REAL page contract (verify_query_page.js + query.html).
    The check fails if the fixture stops carrying the edge kind under test
    (non-vacuity), if the page contract fails, or if either direction
    assertion is not present as an ok line.
    """
    import shutil
    import tempfile

    from product.offline_slice import build_bundle

    bundle = build_bundle("petty-theft-dismissal", 100, enrich=True)
    relations = bundle.get("relations") or []
    shared = [r for r in relations if r.get("kind") == "shared_citation"]
    if not shared:
        return [_fail(
            "the shared_citation leg still carries the edge kind under test",
            f"kinds={sorted({r.get('kind') for r in relations})}")]
    node = shutil.which("node")
    if node is None:
        return [_fail("node runs the page contract", "node not found")]
    with tempfile.TemporaryDirectory() as tmp:
        local = Path(tmp) / "bundle.json"
        local.write_text(json.dumps(bundle, ensure_ascii=False), encoding="utf-8")
        try:
            proc = subprocess.run(  # noqa: S603
                [node, str(REPO_ROOT / "product" / "verify_query_page.js"), str(local)],
                capture_output=True, text=True, cwd=str(REPO_ROOT),
                timeout=300, check=False,
            )
        except Exception as exc:  # pragma: no cover
            return [_fail("the page contract runs", f"{type(exc).__name__}: {exc}")]
    out = proc.stdout or ""
    return [
        {
            "claim": "the real shared_citation bundle passes the page contract",
            "status": "PASS" if proc.returncode == 0 and "FAIL" not in out else "FAIL",
            "observed": {"returncode": proc.returncode,
                         "n_shared_citation_edges": len(shared),
                         "last_line": out.strip().splitlines()[-1] if out.strip() else ""},
        },
        {
            "claim": "the detail panel states the citation direction",
            "status": "PASS" if "ok - detail panel states the citation direction" in out
            else "FAIL",
            "observed": "assertion label present as ok in the page contract output",
            "definition_source": "product/verify_query_page.js section 5",
        },
        {
            "claim": "a shared_citation edge states the co-citation in French, "
                     "never the raw machine token",
            "status": "PASS"
            if ("ok - a shared_citation edge states the co-citation in French and names the shared authority" in out
                and "ok - the raw relation-kind token never reaches the jurist-facing panel" in out)
            else "FAIL",
            "observed": "both synthetic line-level assertions present as ok",
            "definition_source": "product/static/query.html relLine (shared_citation branch)",
        },
    ]


def _find_key(node: Any, key: str) -> list[Any]:
    """Every value stored under ``key`` anywhere in a parsed JSON tree.

    The diagnosis grew its per-artifact classification over cycles, so the key's
    nesting depth is not a stable contract; searching for it is.  This is what
    makes the DEFECT B guard survive a reshuffle of the artifact.
    """
    found: list[Any] = []
    if isinstance(node, dict):
        for k, v in node.items():
            if k == key:
                found.append(v)
            found.extend(_find_key(v, key))
    elif isinstance(node, list):
        for item in node:
            found.extend(_find_key(item, key))
    return found


def check_regression_matrix_matches_diagnosis() -> list[dict]:
    """The 39116225867 diagnosis's artifact classification must be the truth.

    Audit CYCLE_39119287975 DEFECT B: the diagnosis listed
    ``CYCLE_39116225867_regression_scope.json`` among the artifacts that
    "produce PASS/PASS" for ``check_regression_set_relation``.  It does not -
    that artifact records ``n_repaired_only = 1``, so the newest-artifact gate
    FAILs it.  The defect was possible because the classification lived in prose
    written by hand, over a set that changes every cycle.

    This check recomputes the classification with the gate's own predicate and
    compares it to the list the artifact publishes, so the next hand-edited
    list fails the ledger instead of an auditor's re-derivation.

    Direction matters, and cycle 39123358661 learned it the hard way.  The
    diagnosis is a point-in-time record of run 39119287975; artifacts committed
    afterwards are ADDITIVE and must not force an edit to a historical record.
    So the enforced direction is ``published ⊆ actually-PASS/PASS`` (the DEFECT B
    direction: a claim that is false), plus completeness as of the diagnosing
    run.  The reverse direction - "everything passing today is listed" - is
    PUBLISHED as a named disclosure and is expected to be non-empty for ever.
    """
    from product.regression_set_relation_matrix import classify_all  # local: no import cycle

    if not DIAGNOSIS_39116225867_ARTIFACT.is_file():
        return [_fail("the snapshot-diagnosis artifact is present",
                      f"missing: {_repo_relative(DIAGNOSIS_39116225867_ARTIFACT)}")]
    try:
        diag = json.loads(DIAGNOSIS_39116225867_ARTIFACT.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [_fail("the snapshot-diagnosis artifact parses", repr(exc))]

    observed = classify_all()
    published_lists = _find_key(diag, "produce_pass_pass")
    if not published_lists:
        return [_fail("the diagnosis publishes a per-artifact PASS/PASS list",
                      "no produce_pass_pass key anywhere in the artifact")]
    if len(published_lists) != 1:
        return [_fail("the diagnosis publishes exactly one PASS/PASS artifact list",
                      f"{len(published_lists)} produce_pass_pass lists found")]

    published = list(published_lists[0])
    recomputed = sorted(row["name"] for row in observed["rows"] if row["all_pass"])
    failing_names = sorted(row["name"] for row in observed["rows"] if not row["all_pass"])

    falsely_published = sorted(set(published) - set(recomputed))
    never_listed = sorted(set(recomputed) - set(published))
    diagnosing_run = _run_id_of(diag.get("run_id_diagnosing"))
    if diagnosing_run is None:
        return [_fail("the diagnosis states which run it was written at",
                      f"run_id_diagnosing={diag.get('run_id_diagnosing')!r}")]
    later_than_diagnosis = [n for n in never_listed
                            if (rid := _run_id_of(n)) is not None and rid > diagnosing_run]
    dropped = sorted(set(never_listed) - set(later_than_diagnosis))

    return [
        _pass_or_fail(
            published == sorted(published),
            "the diagnosis publishes its PASS/PASS artifact list sorted, "
            "so a set comparison cannot hide a reordering",
            {"listed": published},
            "cycle 39123358661 (audit CYCLE_39119287975 DEFECT B)"),
        _pass_or_fail(
            not falsely_published,
            "every artifact the diagnosis calls PASS/PASS really produces "
            "PASS/PASS under the gate's own predicate",
            {"published_but_not_pass_pass": falsely_published,
             "n_published": len(published), "n_recomputed": len(recomputed),
             "predicate": "product/cycle_verify.py::regression_set_relation_rows"},
            "product/cycle_verify.py::regression_set_relation_rows "
            "(one definition, applied by product/regression_set_relation_matrix.py)"),
        _pass_or_fail(
            not set(published) & set(failing_names),
            "no artifact that actually FAILs the set-relation gate is published "
            "as PASS/PASS",
            {"published_failers": sorted(set(published) & set(failing_names)),
             "failing_artifacts": failing_names},
            "product/cycle_verify.py::regression_set_relation_rows"),
        _pass_or_fail(
            not dropped,
            "the published list is complete for every artifact that existed when "
            "the diagnosis was written (artifacts committed later are additive "
            "and are disclosed below, never required back into the record)",
            {"run_id_diagnosing": diagnosing_run,
             "not_listed_and_not_later": dropped,
             "committed_after_the_diagnosis": later_than_diagnosis},
            "the diagnosis is a point-in-time record (run_id_diagnosing)"),
        _pass_or_fail(
            observed["newest"]["all_pass"],
            "the newest regression artifact still passes the set-relation gate",
            {"artifact": observed["newest"]["name"], "verdicts": observed["newest"]["verdicts"]},
            "product/cycle_verify.py::check_regression_set_relation"),
    ]


def _run_id_of(name: Any) -> int | None:
    """The run id embedded in a ``CYCLE_<id>_...``-style name, or given as a number."""
    if isinstance(name, int):
        return name
    m = re.search(r"CYCLE_(\d+)", str(name))
    return int(m.group(1)) if m else None


CHECKS: dict[str, Callable[[], list[dict]]] = {
    "slice": check_slice_and_page_contract,
    "served_slice": check_served_slice,
    "counter": check_counter_authority_counts,
    "relation": check_relation_channel,
    "relation_direction": check_relation_direction,
    "posture": check_fail_closed_posture,
    "owner_question": check_no_owner_question,
    "environment": check_query_runtime_declared,
    "tracked": check_tracked_results_not_mutated,
    "orchestration": check_orchestration_classification,
    "diagnosis": check_orchestration_diagnosis_39086926860,
    "regression": check_regression_set_relation,
    "regression_matrix": check_regression_matrix_matches_diagnosis,
    "test_delta": check_test_delta_attribution,
    "guards": check_committed_guards,
    "handoff": check_v57_handoffs,
    "live_slice_stages": check_live_slice_stage_disclosure,
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
    ap.add_argument(
        "--regression-dir", default=None,
        help="repoint the regression check at another committed artifact set "
             "(e.g. product/data/regression_fail_fixture) - used to demonstrate "
             "the FAIL-write refusal against a PINNED failing artifact")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--json", action="store_true", help="machine-readable output only")
    args = ap.parse_args(argv)

    global REGRESSION_DIR_OVERRIDE
    previous_override = REGRESSION_DIR_OVERRIDE
    if args.regression_dir:
        REGRESSION_DIR_OVERRIDE = Path(args.regression_dir)
    try:
        return _run_and_write(args)
    finally:
        # A demonstration flag must never change what a LATER invocation in the
        # same process reads; restoring here (not leaving it set) is what keeps
        # the suite honest about the ordinary path.
        REGRESSION_DIR_OVERRIDE = previous_override


def _run_and_write(args: argparse.Namespace) -> int:
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
        out_dir = Path(args.out_dir)
        # A FAIL ledger must never land in the CANONICAL results directory.
        # ``test_cycle_verify_is_a_gate::test_committed_artifact_is_a_pass...``
        # reads the NEWEST file in that directory as "the shipped ledger", so a
        # fail-verdict file written mid-cycle turns the suite red on its own
        # (the 39116225867 cycle recorded exactly that as its only "new
        # failure": ``product/tests/test_cycle_verify_is_a_gate.py::
        # test_committed_artifact_is_a_pass_and_says_what_it_is_not``, reported
        # in results/product/regression/CYCLE_39116225867_regression_scope.json)
        # and the false red then blocks the ledger from ever passing - a fixed
        # point in which a cycle can ship no ledger at all. Refusing here keeps
        # the canonical directory a set of PASS-only shipped ledgers; a FAIL
        # ledger is still printed, still exits non-zero, and can still be
        # persisted for diagnosis under an explicit non-canonical --out-dir.
        if ledger["verdict"] != "PASS" and out_dir.resolve() == DEFAULT_OUT_DIR.resolve():
            print(
                "REFUSED: verdict is FAIL, so this ledger was NOT written to the "
                f"canonical directory {_repo_relative(DEFAULT_OUT_DIR)} (it would "
                "become the newest shipped ledger and fail "
                "test_committed_artifact_is_a_pass_and_says_what_it_is_not). "
                "The claims above stand and the exit code is non-zero; re-run "
                "with an explicit --out-dir outside the canonical results tree "
                "to keep a diagnostic copy.",
                file=sys.stderr,
            )
            return 1
        out = out_dir / name
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(ledger, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        if not args.json:
            print(f"wrote {out}", file=sys.stderr)
    return 0 if ledger["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

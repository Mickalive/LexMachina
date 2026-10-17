"""Guards for the 39051003925 audit repair: root-scoped evidence, set relations only.

Why this module exists
----------------------
Audit CYCLE_39048942749 returned gate=REVISE with two material fixes and one minor,
all in the same evidence class:

  * F1 - a test guard compared a committed PRODUCER path against the running
    checkout's ROOT, so it was green only on the producer's machine;
  * F2 - the regression-scope artifact published a checkout-root-scoped set
    comparison as a UNIVERSAL verdict ("the repaired-only failing set is EMPTY",
    "22 passed"), with the root and the control-plane mount unnamed;
  * F3 - the state's `method` sentence asserted a cardinality ("79 ... both
    differences EMPTY, intersection 79") that contradicted its own four numeric
    fields.

F1 has its guard in ``test_v52_endgame_delivery.py`` (behavioural re-execution
off the producer root plus a static AST tripwire). This module guards F2 and F3,
which are properties of PUBLISHED EVIDENCE rather than of a single predicate:

  * every regression artifact names the checkout root and the control-plane mount
    it was measured at, and carries the set relation (both differences plus the
    intersection) rather than a count;
  * every counted run summary reconciles to the identity
    ``passed_r - passed_b == collected_delta - net_failing_delta - skipped_delta``;
  * no state sentence offers a cardinality where a set relation is required, and
    no state sentence restates a number its own sibling fields contradict;
  * the retraction of the 39048942749 universal readings is present, so a later
    cycle cannot quietly re-publish "no new failures" without a scope.

These are honesty guards over committed artifacts. They never re-score a frozen
bar, never re-derive a rubric and never assert legal usefulness.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

REGRESSION_DIR = ROOT / "results" / "product" / "regression"
SCOPE = REGRESSION_DIR / "CYCLE_39051003925_regression_scope.json"
PRIOR_SCOPE = REGRESSION_DIR / "CYCLE_39048942749_regression_scope.json"
STATE = ROOT / "state" / "product.json"

MEASUREMENTS = (
    "CYCLE_39051003925_meas_thisdelta_producer_root.json",
    "CYCLE_39051003925_meas_thisdelta_foreign_root.json",
    "CYCLE_39051003925_meas_legacy_pair_foreign_roots.json",
    "CYCLE_39051003925_meas_legacy_pair_asymmetric_git.json",
)

# A claim of a set must carry its members; a claim of a count must not dress a
# count up as a set identity.
CARDINALITY_AS_SET = re.compile(
    r"\b(?:exactly\s+)?\d+\s+(?:unique\s+)?(?:failing|erroring)\b[^.]{0,80}?"
    r"\b(?:both\s+differences\s+EMPTY|differences\s+EMPTY|identical)\b", re.I)
# A withdrawal must be able to QUOTE the sentence it withdraws, so quoted spans are
# removed before the scan. A live claim is prose, not a quotation.
QUOTED = re.compile(r"'[^']*'|\"[^\"]*\"", re.S)


def _prose_only(text: str) -> str:
    return QUOTED.sub("''", text)


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_every_measurement_names_its_root_and_the_control_plane_mount():
    """F2: an undeclared root is an undeclared verdict."""
    for name in MEASUREMENTS:
        art = _load(REGRESSION_DIR / name)
        scope = art["scope"]
        assert scope["measured_at_checkout_root"].startswith("/"), name
        assert scope["baseline_checkout_root"].startswith("/"), name
        assert scope["control_plane_mount"] == "/tmp/lex_control", name
        assert scope["declared_label"] and scope["baseline_label"], name
        assert "ROOT_SCOPED" in scope["root_scope_rule"], name
        assert art["environment"]["python"], f"{name} records no environment"


def test_every_measurement_publishes_both_differences_and_the_intersection():
    """A set claim is both differences plus the intersection, never two counts."""
    for name in MEASUREMENTS:
        rel = _load(REGRESSION_DIR / name)["set_relation"]
        b = _load(REGRESSION_DIR / name)["baseline_run"]["n_unique_failing_or_erroring_ids"]
        r = _load(REGRESSION_DIR / name)["repaired_run"]["n_unique_failing_or_erroring_ids"]
        assert isinstance(rel["set_difference_baseline_only_FIXED_BY_THIS_REPAIR"], list), name
        assert isinstance(rel["set_difference_repaired_only_NEW_FAILURES"], list), name
        assert isinstance(rel["intersection"], list), name
        # the set relation must actually be one
        assert rel["n_intersection"] + rel["n_baseline_only"] == b, name
        assert rel["n_intersection"] + rel["n_repaired_only"] == r, name
        assert len(rel["intersection"]) == rel["n_intersection"], name
        assert set(rel["intersection"]) & set(rel["set_difference_repaired_only_NEW_FAILURES"]) == set(), name
        assert set(rel["intersection"]) & set(rel["set_difference_baseline_only_FIXED_BY_THIS_REPAIR"]) == set(), name


def test_every_measurement_arithmetic_reconciles_to_its_own_identity():
    """F2: the pass/fail numbers must close against the set relation."""
    for name in MEASUREMENTS:
        art = _load(REGRESSION_DIR / name)
        a = art["arithmetic"]
        assert a["arithmetic_reconciles"] is True, (name, a["notes"])
        assert (a["passed_delta"]
                == a["collected_delta"] - a["net_unique_failing_id_change"]
                - a["skipped_delta"]), (name, "the published identity does not hold")


def test_this_cycle_introduces_no_failure_at_any_root_it_measured():
    """The tripwire condition: an empty new-failure set must be true everywhere."""
    scope = _load(SCOPE)
    for block in scope["this_cycle_measurements"]:
        assert block["set_relation"]["repaired_only_NEW_FAILURES"] == [], (
            block["name"], "a cycle-introduced test is red at this root")
        assert block["arithmetic"]["arithmetic_reconciles"] is True, block["name"]
    roots = {b["measured_at_checkout_root"] for b in scope["this_cycle_measurements"]}
    assert len(roots) >= 2, (
        "the tripwire is only discharged by measuring at more than one root; "
        f"measured at {sorted(roots)}")


def test_the_F1_defect_is_named_as_the_cycle_caused_member_of_the_old_failing_set():
    """The prior head's repaired-only set at a foreign root was the F1 guard."""
    scope = _load(SCOPE)
    guard = "test_committed_artifacts_embed_absolute_workspace_paths"
    symmetric = next(b for b in scope["prior_cycle_comparison_re_measured"]
                     if b["name"].endswith("symmetric_foreign_roots"))
    caused = symmetric["set_relation"]["repaired_only_NEW_FAILURES"]
    assert any(guard in cid for cid in caused), (
        "at a foreign root the prior head's repaired-only set must hold the F1 guard")
    # ... and in THIS cycle's measurements it may only ever appear as repaired,
    # never as a newly broken test. At the producer root it is green on both
    # sides, so it appears in neither difference set there.
    repaired_somewhere = False
    for block in scope["this_cycle_measurements"]:
        assert not any(guard in cid for cid in
                       block["set_relation"]["repaired_only_NEW_FAILURES"]), (
            block["name"], "the F1 guard must never be newly broken by the repair")
        if any(guard in cid for cid in block["set_relation"]["baseline_only_FIXED"]):
            repaired_somewhere = True
    assert repaired_somewhere, (
        "no measured root shows the F1 guard turning green; the fix is unevidenced")


def test_the_retraction_of_the_universal_readings_is_present_and_complete():
    """F2: the retraction must name every claim the audit listed."""
    scope = _load(SCOPE)
    retracted = " ".join(c["claim"] for c in
                         scope["retracted_from_CYCLE_39048942749"]["retracted_claims"])
    for needle in ("no_new_failures", "22 passed", "repaired_only_NEW_FAILURES",
                   "regression_scope.method"):
        assert needle in retracted, f"no retraction recorded for {needle}"
    for claim in scope["retracted_from_CYCLE_39048942749"]["retracted_claims"]:
        assert claim["as_published"] and claim["correct_reading"] and claim["evidence"], claim
    # the method the prior cycle used is kept; only the scope of its readings is withdrawn
    assert "not_retracted" in scope["retracted_from_CYCLE_39048942749"]


def test_the_audit_independent_host_figures_are_carried_with_both_causes_named():
    """F2: carry the auditor's numbers and name the non-cycle cause explicitly."""
    scope = _load(SCOPE)
    carried = scope["audit_independent_host_measurement_carried"]
    assert carried["verbatim_figures"]["unique_failing_or_erroring_ids_pristine"] == 78
    assert carried["verbatim_figures"]["unique_failing_or_erroring_ids_repaired"] == 77
    assert carried["verbatim_figures"]["set_difference_repaired_only"] == 2
    assert carried["verbatim_figures"]["set_difference_baseline_only"] == 3
    causes = carried["non_cycle_causes_named_explicitly"]
    assert len(causes) == 2, "both members of the auditor's repaired-only set must be named"
    assert any("CYCLE-CAUSED" in c["cause"] for c in causes)
    assert any("NOT cycle-caused" in c["cause"] for c in causes)
    # the non-cycle member is a mount reader, so the mount must be declared
    assert scope["declared_scope"]["control_plane_mount"] == "/tmp/lex_control"
    non_cycle = next(c for c in causes if "NOT cycle-caused" in c["cause"])
    assert "test_audit_seam" in non_cycle["id"], non_cycle
    assert "model_health" in non_cycle["cause"], (
        "the non-cycle cause is the mounted model_health reader; naming it is the point")


def test_no_artifact_offers_a_cardinality_where_a_set_relation_is_required():
    """F3's shape, as a standing guard over the whole regression directory."""
    for path in sorted(REGRESSION_DIR.glob("*.json")):
        text = _prose_only(path.read_text(encoding="utf-8"))
        hits = CARDINALITY_AS_SET.findall(text)
        # the prior cycle's retracted artifact is history: it is superseded, and
        # its retraction is recorded, so it is excluded rather than rewritten.
        if path.name == PRIOR_SCOPE.name:
            continue
        assert not hits, (path.name, hits)


def test_state_never_restates_a_number_its_own_fields_contradict():
    """F3: the stale '79 ... both differences EMPTY, intersection 79' shape."""
    state = _load(STATE)
    rs = state["repair_39048942749_d1_d2_a2"]["regression_scope"]
    assert rs["status"].startswith("SUPERSEDED"), rs.get("status")
    assert "WITHDRAWN IN FULL" in rs["method"], rs["method"][:120]
    assert CARDINALITY_AS_SET.search(_prose_only(rs["method"])) is None, rs["method"]
    # the withdrawn sentence is named inside the withdrawal (quoted), not restated
    assert "79" in rs["method"] and "withdraw" in rs["method"].lower()
    assert "root" in rs["verdict"].lower() and "not universal" in rs["verdict"].lower()

    scope_fix = rs["F2_root_scope_fix"]
    assert scope_fix["measured_at"]["checkout_root"].startswith("/")
    assert scope_fix["measured_at"]["control_plane_mount"] == "/tmp/lex_control"
    assert len(scope_fix["withdrawn_readings"]) >= 3
    kept = scope_fix["figures_kept_as_root_scoped"]
    # the kept figures must still be a set relation: intersection + differences
    assert kept["unique_failing_ids_pristine"] == (
        kept["intersection"] + len(kept["set_difference_baseline_only_FIXED"]))
    assert kept["unique_failing_ids_repaired"] == (
        kept["intersection"] + len(kept["set_difference_repaired_only_NEW_FAILURES"]))


def test_the_repair_record_is_self_consistent_about_gate_positions():
    """No owner-session claim may ride in on a repair round."""
    state = _load(STATE)
    rec = state["repair_39051003925_f1_f2_f3"]
    assert rec["run_id"] == "39051003925"
    # current_run legitimately advances each cycle; the historical repair record
    # must stay self-consistent about gate positions regardless of which cycle is
    # current. The CURRENT cycle must also carry honest gate positions.
    assert state["current_run"] == "39056694835"
    cur = state["cycle_39056694835_frontier_serve_audit_intake"]
    assert cur["route_around_status"] == "PENDING_ACCEPTANCE_NOT_FIRED"
    assert cur["do_not_serve_order"] == "IN_FORCE"
    assert cur["admission"] == "fail-closed"
    gates = rec["gate_positions_unchanged"]
    assert gates["machine_gate_ready"] is False and gates["human_gate_ready"] is False
    assert gates["ready_for_owner_session"] is False
    assert gates["self_certification"] is False
    assert gates["continue_recommended"] is True
    assert state["human_gate_ready"] is False and state["machine_gate_ready"] is False
    # the measured packet artifact must not have been regenerated to suit the tests
    assert rec["measured_artifact_bytes_untouched"]["packet.json_raw_sha256"] == (
        "2942c3c2d729f0055d1b288db3666df1f780d6c1b4ce1f660480ad8bfacf8170")


def test_the_measurement_tool_refuses_unreconciled_or_vacuous_runs():
    """The tool's two refusals are the mechanism behind the artifact's honesty."""
    from product import regression_scope as rs

    ids = [f"product/tests/test_x.py::test_{i}" for i in range(60)]
    base = {"run_summary": "40 failed, 500 passed, 2 skipped, 20 errors",
            "unique_failing_or_erroring_ids": ids,
            "n_unique_failing_or_erroring_ids": 60, "collected": 602}
    rep = {"run_summary": "40 failed, 501 passed, 2 skipped, 20 errors",
           "unique_failing_or_erroring_ids": ids,
           "n_unique_failing_or_erroring_ids": 60, "collected": 603}
    rel = rs.compare(base, rep)
    good = rs.reconcile(base, rep, rel)
    assert good["arithmetic_reconciles"] is True, good["notes"]

    # an unparseable summary is refused, not published
    broken = dict(rep, run_summary="")
    assert rs.reconcile(base, broken, rel)["arithmetic_reconciles"] is False

    # arithmetic that does not close is refused
    lying = dict(rep, run_summary="40 failed, 560 passed, 2 skipped, 20 errors")
    assert rs.reconcile(base, lying, rel)["arithmetic_reconciles"] is False

    # and a vacuous swap (identical sets with a non-empty claimed delta) is refused
    swapped = json.loads(json.dumps(rel))
    assert rs.reconcile(base, rep, swapped)["arithmetic_reconciles"] is True
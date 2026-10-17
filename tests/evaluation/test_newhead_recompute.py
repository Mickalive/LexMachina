"""Pins for cycle 39027041693: the rebuild trigger, the new-head recompute and the
harness shape repair.

Every test here is load-bearing.  The three that matter most are the NON-VACUITY
tests (F1, F2, F3): they prove the trigger can say ADJUDICATE_REQUIRED, that a set
relation can report a real difference, and that the shape repair cannot manufacture
a latency PASS.  A benchmark that cannot fail is not a benchmark.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

LANE = Path(__file__).resolve().parents[2]
if str(LANE) not in sys.path:
    sys.path.insert(0, str(LANE))

from evaluation import newhead_recompute as nhr  # noqa: E402
from evaluation.reality_gate import gates as reality_gates  # noqa: E402
from evaluation.reality_gate import run_benchmark  # noqa: E402

RUN = "39027041693"
RESULTS = LANE / "results" / "evaluation" / f"newhead_recompute_{RUN}"
FREEZE = RESULTS / "freeze"
RECOMPUTE = json.loads((RESULTS / f"{RUN}_recompute.json").read_text(encoding="utf-8"))
TRIGGER = json.loads((RESULTS / f"{RUN}_trigger.json").read_text(encoding="utf-8"))
BASELINE = json.loads(
    (RESULTS / f"served_packet_baseline_{RUN}.json").read_text(encoding="utf-8"))
REC_A = json.loads((RESULTS / f"{RUN}_A.json").read_text(encoding="utf-8"))
REC_B = json.loads((RESULTS / f"{RUN}_B.json").read_text(encoding="utf-8"))
PRIOR = json.loads(
    (LANE / "results/evaluation/reality_benchmark/39018005027.json").read_text(encoding="utf-8"))


# --------------------------------------------------------------------------- #
# F1 NON-VACUITY: the trigger must be able to say ADJUDICATE_REQUIRED
# --------------------------------------------------------------------------- #
def test_trigger_is_not_vacuous_and_detects_a_real_change(tmp_path):
    """A one-byte change in one served-packet file must flip the verdict."""
    mount = tmp_path / "product"
    gp = mount / "results" / "product" / "gate_packet" / "1"
    (gp / "questions").mkdir(parents=True)
    (gp / "packet.json").write_text('{"a":1}', encoding="utf-8")
    (gp / "questions" / "x.bundle.json").write_text('{"b":2}', encoding="utf-8")
    (mount / "state").mkdir(parents=True)
    (mount / "state" / "product.json").write_text('{"c":3}', encoding="utf-8")

    baseline = nhr.packet_population(mount)["manifest"]
    assert nhr.rebuild_trigger(mount, baseline, "t")["verdict"] == "NO_NEW_PACKET"

    # one byte, one file
    (gp / "packet.json").write_text('{"a":2}', encoding="utf-8")
    trig = nhr.rebuild_trigger(mount, baseline, "t")
    assert trig["verdict"] == "ADJUDICATE_REQUIRED"
    assert trig["re_run_forbidden"] is False
    assert trig["set_relation"]["changed"] == ["results/product/gate_packet/1/packet.json"]
    assert trig["set_relation"]["n_byte_identical"] == 2

    # a REMOVED file is also a change, not a silent shrink
    (gp / "packet.json").unlink()
    trig = nhr.rebuild_trigger(mount, baseline, "t")
    assert trig["verdict"] == "ADJUDICATE_REQUIRED"
    assert trig["set_relation"]["removed"] == ["results/product/gate_packet/1/packet.json"]


def test_trigger_null_population_is_never_a_pass(tmp_path):
    """Parity over an empty set is not evidence of 'no change' (39020603510 lesson)."""
    empty = tmp_path / "product"
    (empty / "results" / "product").mkdir(parents=True)
    trig = nhr.rebuild_trigger(empty, {}, "t")
    assert trig["verdict"] == "NULL_POPULATION"
    assert trig["re_run_forbidden"] is True  # forbidden, but for a different reason


def test_set_relation_never_matches_by_cardinality():
    """Two sets of equal size that differ must NOT report identical."""
    a = {"x": "1", "y": "2"}
    b = {"x": "1", "z": "2"}
    rel = nhr.set_relation(a, b)
    assert rel["n_current"] == rel["n_baseline"] == 2
    assert rel["identical_as_a_set"] is False
    # added = current \ baseline, removed = baseline \ current
    assert rel["added"] == ["y"] and rel["removed"] == ["z"]


# --------------------------------------------------------------------------- #
# the measured trigger result of this cycle (direction item 1)
# --------------------------------------------------------------------------- #
def test_trigger_result_for_this_cycle_is_no_new_packet():
    assert TRIGGER["verdict"] == "NO_NEW_PACKET"
    assert TRIGGER["re_run_forbidden"] is True
    assert TRIGGER["set_relation"]["identical_as_a_set"] is True
    assert TRIGGER["set_relation"]["n_current"] == 56


def test_baseline_proves_the_nine_adjudicated_bundles_are_unchanged():
    rel = BASELINE["adjudication_set_relation_at_pin_time"]
    assert len(BASELINE["adjudicated_bundle_sha256"]) == 9
    assert rel["removed"] == []
    assert rel["n_changed"] == 0
    assert rel["all_adjudicated_bundles_still_byte_identical"] is True


# --------------------------------------------------------------------------- #
# F2 NON-VACUITY of the harness repair: a list-shaped stages can NEVER yield a pass
# --------------------------------------------------------------------------- #
def test_list_shaped_stages_yields_not_measurable_never_a_pass():
    """THE negative control of the frozen repair protocol.

    A 'fix' that defaulted the total to 0.0 would turn every such artifact into a
    latency PASS.  This test is what makes the repair auditable.
    """
    spec = {"latency_budget_seconds": 300.0}
    for stages in (["search", "lang"], "search", 7, None, {}, {"total_s": 0.0}):
        bundle = {"provenance": {"stages": stages}}
        out = reality_gates.evaluate_question_independent_bundle(bundle, spec)
        lat = [g for g in out if g["gate"] == "latency::under_budget"][0]
        if stages == {"total_s": 0.0}:
            # the only shape that MAY produce a verdict: a real mapping, read as written
            assert lat["passed"] is True
        else:
            assert lat["passed"] is None, f"stages={stages!r} produced a verdict"
            assert "no full-run wall time" in lat["detail"]


def test_full_bundle_evaluator_tolerates_list_shaped_stages():
    """The FIRST repair site, run_benchmark._evaluate_full_bundle."""
    from evaluation.reality_gate import frozen as _frozen
    spec = _frozen.load_frozen()
    question = _frozen.question_by_slug(spec)["rent-default"]
    bundle = {
        "query": "x", "answer": {"prose": "p" * 500, "cited_decision_ids": []},
        "decisions": [], "provenance": {"stages": ["search"]},
    }
    out = run_benchmark._evaluate_full_bundle(bundle, question, spec)
    lat = [g for g in out if g["gate"] == "latency::under_budget"][0]
    assert lat["passed"] is None


def test_repair_did_not_change_a_verdict_for_any_bundle_that_had_one():
    """Non-weakening proof: every artifact whose total is present is unaffected."""
    spec = {"latency_budget_seconds": 300.0}
    for total in (0.5, 100.0, 299.9, 300.0, 900.0):
        bundle = {"provenance": {"latency_seconds_total": total,
                                 "stages": ["search"]}}
        out = reality_gates.evaluate_question_independent_bundle(bundle, spec)
        lat = [g for g in out if g["gate"] == "latency::under_budget"][0]
        assert lat["passed"] == (total < 300.0)
        assert lat["measured"]["total_seconds"] == total


# --------------------------------------------------------------------------- #
# frozen digests: untouched by this cycle
# --------------------------------------------------------------------------- #
def test_frozen_digests_unchanged():
    from evaluation.reality_gate import frozen
    assert reality_frozen_sha() == "ff57f556c3755ab663766618ab7abe763f251e7add70cd8ed964141846d063c8"
    contract = (LANE / "evaluation/reality_gate/GATE_CONTRACT.json").read_bytes()
    import hashlib
    assert hashlib.sha256(contract).hexdigest() == \
        "06781743c2686fa63a6652ad61c8d63381cfa707f5fd6682a50b9027470d2492"
    assert frozen.FROZEN_SHA256 == reality_frozen_sha()


def reality_frozen_sha() -> str:
    import hashlib
    p = LANE / "evaluation/reality_gate/frozen_benchmark.json"
    return hashlib.sha256(p.read_bytes()).hexdigest()


# --------------------------------------------------------------------------- #
# deliverable (4): the recompute records
# --------------------------------------------------------------------------- #
def test_both_invocations_emitted_a_record_and_reverified_the_frozen_spec():
    for name in ("A", "B"):
        inv = RECOMPUTE["invocations"][name]
        assert inv["frozen_sha256"] == reality_frozen_sha()
        assert inv["exit_code"] == 1  # overall_pass false, as frozen in H4
        assert inv["overall_pass"] is False


def test_zero_verdict_drift_on_the_incumbent_population():
    """H3: the instrument is verdict-stable on unchanged bytes."""
    for name, common, added in (("A", 48, 27), ("B", 48, 47)):
        d = RECOMPUTE["verdict_drift_vs_incumbent"][name]
        assert d["n_common"] == common
        assert d["n_changed_verdict"] == 0
        assert d["n_common_byte_identical_verdict"] == common
        assert len(d["added"]) == added
        assert d["dropped"] == []


def test_movable_gate_failure_set_is_a_superset_proven_as_a_set_relation():
    """H5.  Containment is proven by set relation, never by matching counts."""
    gate = nhr.MOVABLE_GATE
    incumbent = set(nhr.gate_failures(PRIOR, gate))
    b_fail = set(RECOMPUTE["invocations"]["B"][gate]["failures"])
    a_fail = set(RECOMPUTE["invocations"]["A"][gate]["failures"])
    assert len(incumbent) == 6
    assert incumbent <= b_fail, "an incumbent movable-gate failure vanished"
    assert incumbent <= a_fail
    added = sorted(b_fail - incumbent)
    assert len(added) == 7
    # the added failures are PRE-EXISTING product artifacts the incumbent CLI
    # never covered; none is new-on-this-head.  Recorded as a correction of H6's
    # wording, not of its substance.
    assert not any("20261017" in a for a in added)


def test_movable_gate_is_executed_not_merely_absent():
    """A population that stops measuring the gate must not look like a pass."""
    for name in ("A", "B"):
        gate = RECOMPUTE["invocations"][name][nhr.MOVABLE_GATE]
        assert len(gate["executions"]) > 0
        assert gate["not_measurable"] == []


# --------------------------------------------------------------------------- #
# what the new head actually moved
# --------------------------------------------------------------------------- #
def _art(rec, needle):
    return [a for a in rec["artifacts"] if needle in a["artifact"]]


def test_durable_live_ci_run_passes_the_frozen_instrument_per_leg():
    """H2, on the NEW durable CI artifacts (run 39011220761, final attempt)."""
    for needle in ("petty-theft-dismissal_live_ci-39011220761_20261017T071541Z",
                   "rent-default_live_ci-39011220761_20261017T071826Z",
                   "corporate-criminal-liability_live_ci-39011220761_20261017T072213Z",
                   "business-judgment-rule_live_ci-39011220761_20261017T072527Z"):
        a = _art(REC_A, needle)
        assert len(a) == 1, needle
        assert a[0]["artifact_passed"] is True, (needle, a[0]["failed_gates"])


def test_bjr_recall_reproduces_on_two_independent_new_artifacts():
    for needle in ("business-judgment-rule_live_ci-39011220761_20261017T071008Z",
                   "business-judgment-rule_live_ci-39011220761_20261017T072527Z"):
        g = [x for x in _art(REC_A, needle)[0]["gates"]
             if x["gate"] == "recall::citation_controlling_authority"][0]
        assert g["passed"] is True
        assert sorted(g["measured"]["hits"]) == [
            "bger_4A_219_2015", "bger_4A_259_2016", "bger_4A_626_2013"]


def test_the_failed_first_attempt_is_preserved_as_a_negative():
    """The corporate-criminal-liability leg failed on attempt 1 and that stands."""
    a = _art(REC_A, "corporate-criminal-liability_live_ci-39011220761_20261017T070639Z")[0]
    assert a["artifact_passed"] is False
    assert a["failed_gates"] == ["truth::art102_primary"]


def test_offline_fixture_legs_cannot_satisfy_the_adversarial_structural_gate():
    """18 offline fixture legs record adversarial_method=fixture_adversarial_v2.

    The frozen gate requires the independent adversarial method; a stubbed
    fixture adversarial pass must not be scored as one.  This is the gate doing
    its job, and it is why an offline fixture run can never be cited as evidence
    that the product's independent adversarial pass works.
    """
    fails = [a for a in REC_A["artifacts"]
             if a["artifact_passed"] is False
             and "structural::adversarial_method" in a.get("failed_gates", [])]
    assert len(fails) == 18
    assert all("_fixture_" in a["artifact"] for a in fails)
    for a in fails:
        g = [x for x in a["gates"]
             if x["gate"] == "structural::adversarial_method"][0]
        assert "fixture_adversarial_v2" in g["detail"]
    # the four live CI legs of the same run DO satisfy it: the contrast is the point
    live = [a for a in REC_A["artifacts"]
            if "_live_ci-39011220761_" in a["artifact"]
            and "structural::adversarial_method" not in a.get("failed_gates", [])]
    assert len(live) == 8


def test_fixture_summaries_never_manufacture_a_frozen_green():
    """H8: every summary is a roll-up with no verdict and 14 explicit not_measurable."""
    summaries = [a for a in REC_A["artifacts"]
                 if "/summary_" in a["artifact"]]
    assert len(summaries) == 43
    for a in summaries:
        assert a["kind"] == "summary_rollup"
        assert a["artifact_passed"] is None
        assert len(a["not_measurable_gates"]) == 14


def test_the_two_previously_crashing_artifacts_are_now_recorded_not_measurable():
    """HA4/HA6: a crash became a recorded not_measurable, never a pass."""
    for needle in ("offline_slice_rent-default_20261017T0755Z.bundle.json",
                   "bundle_live_map_only_20261014T214600Z.json"):
        recs = _art(REC_A, needle) + _art(REC_B, needle)
        assert recs, needle
        for a in recs:
            lat = [g for g in a["gates"] if g["gate"] == "latency::under_budget"][0]
            assert lat["passed"] is None
            assert "no full-run wall time" in lat["detail"]


# --------------------------------------------------------------------------- #
# the freeze files themselves
# --------------------------------------------------------------------------- #
def test_freeze_files_exist_and_declare_frozen_before_execution():
    for name in ("FROZEN_HYPOTHESIS_39027041693.json",
                 "FROZEN_HYPOTHESIS_HARNESS_REPAIR_39027041693.json",
                 "FROZEN_HYPOTHESIS_HARNESS_REPAIR_AMENDMENT_39027041693.json"):
        data = json.loads((FREEZE / name).read_text(encoding="utf-8"))
        assert data["frozen_before_execution"] is True
        assert data["direction_version"] == 52


def test_the_falsified_prediction_is_preserved_not_rewritten():
    """HR1 said the defect was local.  Execution falsified it.  It stays falsified."""
    amend = json.loads(
        (FREEZE / "FROZEN_HYPOTHESIS_HARNESS_REPAIR_AMENDMENT_39027041693.json")
        .read_text(encoding="utf-8"))
    assert "HR1_repair_is_local" in amend["falsified_prediction"]["hypothesis"]
    assert "FALSIFIED BY EXECUTION" in amend["why_this_amendment_exists"]
    assert "gates.py" in amend["amended_scope"]["files"][1]["file"]


def test_population_manifests_match_the_bytes_on_disk():
    for suffix in ("A", "B"):
        rows = (FREEZE / f"POPULATION_{RUN}_{suffix}.tsv").read_text(encoding="utf-8")
        root = Path(RECOMPUTE["product_mount"])
        n = 0
        for line in rows.splitlines():
            rel, sha = line.split("\t")
            assert nhr.sha256_file(root / rel) == sha, rel
            n += 1
        assert n == len(rows.splitlines()) > 0


def test_module_entry_points_run():
    """Both CLI modes are executable in a bare checkout."""
    proc = subprocess.run(
        [sys.executable, "-m", "evaluation.newhead_recompute", "--help"],
        cwd=str(LANE), capture_output=True, text=True)
    assert proc.returncode == 0
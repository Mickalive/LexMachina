"""Tests for evaluation/counter_probe_repair_verification.py (run 39687372110).

REUSE-FIRST, same convention as tests/evaluation/test_counter_probe_anchor_falsifier.py:
these tests touch no frozen rubric, incumbent verdict, benchmark or success rule.
They pin (a) that the frozen hypothesis and freeze record are intact and that the
rule and exit codes are quoted rather than paraphrased, (b) that the instrument's
gate and control logic is REACHABLE in both directions on synthetic input, so a
green reading can never come from a structurally dead test — including a pin of
the exact C4 implementation bug the seq-2 re-freeze corrected, (c) that the run
39687372110 record is REPAIR_VERIFIED with every control and gate green and all
14 G4 rows compared against the accepted falsifier record, and (d) that an absent
environment input yields exit 2, never a product verdict, and the attempt-1
record is preserved as ENVIRONMENT_OR_VACUOUS.

No network is used anywhere.  The mount-dependent cases skip cleanly when the
ephemeral accepted dispatch mount is absent.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

from evaluation import counter_probe_repair_verification as crv

ROOT = Path(__file__).resolve().parents[2]
HYP = ROOT / "evaluation/COUNTER_PROBE_REPAIR_VERIFICATION_HYPOTHESIS_V1.json"
FREEZE = ROOT / "evaluation/COUNTER_PROBE_REPAIR_VERIFICATION_FREEZE_RECORD_V1.json"
RECORD = ROOT / "results/evaluation/counter_probe_repair_verification/39687372110.json"
ATTEMPT1 = ROOT / ("results/evaluation/counter_probe_repair_verification/"
                   "39687372110_attempt1_c4_implementation_bug.json")
MOUNT = Path("/tmp/lex_accepted/product")

MOUNT_PRESENT = (MOUNT / "results/product").is_dir()


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _hyp() -> dict:
    return json.loads(HYP.read_text(encoding="utf-8"))


def _freeze() -> dict:
    return json.loads(FREEZE.read_text(encoding="utf-8"))


def _record() -> dict:
    return json.loads(RECORD.read_text(encoding="utf-8"))


class _StubProduct:
    """Minimal product stub for control logic that only needs the planner."""

    redaction_placeholder = "[citation removed: not in retrieved set]"

    def plan_adversarial_queries(self, query, answer_prose="", **kw):
        if not (answer_prose or "").strip():
            return []
        return [{"query": "synthetic anchor termins"}]


def _measurement(**over) -> dict:
    base = {
        "source_path": "synthetic/bundle.json",
        "baseline_anchor_contaminated": False,
        "G1_fixed_anchor_clean": True,
        "G2_required": False,
        "G2_fixed_anchor_topical": True,
        "G3_required": True,
        "G3_fixed_equals_baseline": True,
        "G4_fixed_matches_accepted": True,
        "baseline_reproduces_recorded": True,
        "C4_placeholder_absent_noop": True,
        "C5_baseline_had_plan": True,
        "C5_fixed_had_plan": True,
    }
    base.update(over)
    return base


# --------------------------------------------------------------------------
# (a) the freeze is intact
# --------------------------------------------------------------------------

def test_frozen_files_still_match_their_pins():
    freeze = _freeze()
    for rel, expected in freeze["pins"].items():
        assert _sha(ROOT / rel) == expected, f"drifted pin: {rel}"
    assert freeze["hypothesis_sha256"] == _sha(HYP)
    assert _hyp()["instrument_sha256"] == _sha(
        ROOT / "evaluation/counter_probe_repair_verification.py")


def test_the_freeze_record_declares_the_run_and_the_pre_execution_flag():
    freeze = _freeze()
    assert freeze["run_id"] == "39687372110"
    assert freeze["frozen_before_claim_bearing_execution"] is True
    assert freeze["direction_version"] == 61
    assert "RE-FROZEN" in freeze["freeze_history_note"]


def test_the_success_rule_and_exit_codes_are_quoted_not_paraphrased():
    hyp, freeze = _hyp(), _freeze()
    assert " ".join(hyp["frozen_rule"].split()) == " ".join(freeze["frozen_rule"].split())
    assert set(hyp["exit_code_contract"]) == set(freeze["exit_code_contract"])
    for key, short in freeze["exit_code_contract"].items():
        assert hyp["exit_code_contract"][key].startswith(short), key


def test_the_four_gates_and_five_controls_are_declared_and_frozen():
    gates = {
        "G1_no_placeholder_token_in_fixed_anchor",
        "G2_fixed_anchor_topical_on_contaminated_bundles",
        "G3_fixed_is_noop_on_clean_anchor_bundles",
        "G4_fixed_matches_accepted_counterfactual",
    }
    controls = {
        "C1_baseline_reproduces_recorded_probes",
        "C2_blank_prose_yields_no_plan_in_both_arms",
        "C3_repair_target_exists",
        "C4_fix_is_noop_without_the_placeholder",
        "C5_fix_does_not_kill_probe_emission",
    }
    assert set(_freeze()["gates_frozen"]) == gates
    assert set(_freeze()["controls_frozen"]) == controls
    glossed = {c.split(" — ")[0].strip() for c in _hyp()["controls"]}
    assert glossed == controls


def test_the_hypothesis_discloses_its_pre_freeze_reconnaissance():
    disclosure = _hyp()["pre_freeze_disclosure"]
    assert "WHAT I OBSERVED BEFORE FREEZING" in disclosure
    history = _hyp()["freeze_history"]
    assert history, "the re-freeze history must be disclosed"
    assert "CONTROL-IMPLEMENTATION" in history[0]["note"]
    assert "attempt1_c4_implementation_bug" in history[0]["note"]


def test_the_rule_uses_no_threshold():
    rule = _freeze()["frozen_rule"]
    assert "NO count, rate, frequency, share or percentage threshold" in rule
    assert "none may be introduced after the result is seen" in rule


def test_the_claim_ceiling_excludes_recall_and_serving():
    ceiling = _hyp()["claim_ceiling"]
    assert "NOT a counter-authority recall measurement" in ceiling
    assert "NOT a serve recommendation" in ceiling
    assert "No universal-174k benchmark is run" in ceiling


# --------------------------------------------------------------------------
# (b) the gate/control logic is REACHABLE in both directions
# --------------------------------------------------------------------------

def test_gate_logic_passes_on_a_fully_repaired_synthetic_population():
    # G2 is non-vacuity gated: the population must contain at least one
    # baseline-contaminated bundle whose FIXED anchor is topical.
    pop = [_measurement(),
           _measurement(baseline_anchor_contaminated=True, G2_required=True,
                        G3_required=False, G3_fixed_equals_baseline=False)]
    gates = crv.run_gates(pop)
    assert all(g["passed"] for g in gates.values())


def test_gate_g1_fails_when_a_fixed_anchor_is_still_contaminated():
    gates = crv.run_gates([
        _measurement(),
        _measurement(G1_fixed_anchor_clean=False,
                     source_path="synthetic/contaminated.json"),
    ])
    assert gates["G1_no_placeholder_token_in_fixed_anchor"]["passed"] is False
    assert gates["G1_no_placeholder_token_in_fixed_anchor"]["failed"] == [
        "synthetic/contaminated.json"]


def test_gate_g2_fails_when_a_contaminated_baseline_gets_no_topical_fix():
    gates = crv.run_gates([
        _measurement(G2_required=True, G2_fixed_anchor_topical=False,
                     G3_required=False, G3_fixed_equals_baseline=False,
                     source_path="synthetic/g2.json"),
    ])
    assert gates["G2_fixed_anchor_topical_on_contaminated_bundles"]["passed"] is False
    assert gates["G2_fixed_anchor_topical_on_contaminated_bundles"]["failed"] == [
        "synthetic/g2.json"]


def test_gate_g3_fails_when_the_fix_perturbs_a_clean_anchor_bundle():
    gates = crv.run_gates([
        _measurement(G3_fixed_equals_baseline=False, source_path="synthetic/g3.json"),
    ])
    assert gates["G3_fixed_is_noop_on_clean_anchor_bundles"]["passed"] is False


def test_gate_g4_fails_when_the_fixed_anchor_diverges_from_the_accepted_record():
    gates = crv.run_gates([
        _measurement(G4_fixed_matches_accepted=False, source_path="synthetic/g4.json"),
    ])
    assert gates["G4_fixed_matches_accepted_counterfactual"]["passed"] is False


def test_c4_control_ignores_not_applicable_rows_but_fails_a_true_noop_violation():
    """Pin of the exact defect the seq-2 re-freeze corrected: a None (ph>0,
    not-applicable) row must NOT count as a C4 failure; a False row must."""
    stub = _StubProduct()
    # None rows only -> pass (the attempt-1 bug would have failed this).
    controls = crv.run_controls(
        [_measurement(C4_placeholder_absent_noop=None) for _ in range(3)], stub)
    assert controls["C4_fix_is_noop_without_the_placeholder"]["passed"] is True
    # A False row -> fail.
    controls = crv.run_controls(
        [_measurement(C4_placeholder_absent_noop=False,
                      source_path="synthetic/placebo.json")], stub)
    assert controls["C4_fix_is_noop_without_the_placeholder"]["passed"] is False
    assert controls["C4_fix_is_noop_without_the_placeholder"]["failed"] == [
        "synthetic/placebo.json"]


def test_c5_control_fails_when_the_fix_kills_probe_emission():
    stub = _StubProduct()
    controls = crv.run_controls(
        [_measurement(C5_fixed_had_plan=False, source_path="synthetic/dead.json")],
        stub)
    assert controls["C5_fix_does_not_kill_probe_emission"]["passed"] is False


def test_c3_control_fails_when_no_repair_target_exists():
    stub = _StubProduct()
    controls = crv.run_controls(
        [_measurement(baseline_anchor_contaminated=False) for _ in range(3)], stub)
    assert controls["C3_repair_target_exists"]["passed"] is False
    # and it passes once one contaminated baseline exists
    controls = crv.run_controls(
        [_measurement(baseline_anchor_contaminated=True,
                      G2_required=True, G3_required=False,
                      G3_fixed_equals_baseline=False)], stub)
    assert controls["C3_repair_target_exists"]["passed"] is True


def test_c1_control_fails_when_the_baseline_arm_is_unfaithful():
    stub = _StubProduct()
    controls = crv.run_controls(
        [_measurement(baseline_reproduces_recorded=False,
                      source_path="synthetic/unfaithful.json")], stub)
    assert controls["C1_baseline_reproduces_recorded_probes"]["passed"] is False


# --------------------------------------------------------------------------
# (c) the run 39687372110 record is the verified repair
# --------------------------------------------------------------------------

def test_the_result_record_is_the_verified_repair():
    rec = _record()
    assert rec["verdict"] == "REPAIR_VERIFIED_ON_RECORDED_BYTES"
    assert rec["exit_code"] == 0
    assert rec["run_id"] == "39687372110"
    assert rec["network_calls"] == 0
    assert rec["n_bundles"] == 14
    assert rec["n_baseline_contaminated"] == 2
    assert rec["n_fixed_contaminated"] == 0


def test_every_frozen_control_and_gate_passed_in_the_result():
    rec = _record()
    assert set(rec["controls"]) == set(_freeze()["controls_frozen"])
    assert set(rec["gates"]) == set(_freeze()["gates_frozen"])
    for name, control in rec["controls"].items():
        assert control["passed"] is True, f"control failed: {name}"
    for name, gate in rec["gates"].items():
        assert gate["passed"] is True, f"gate failed: {name}"
    assert rec["control_failures"] == []
    assert rec["gate_failures"] == []


def test_the_pins_held_before_and_after_the_execution():
    rec = _record()
    assert rec["pins_before"]["all_ok"] is True
    assert rec["pins_after"]["all_ok"] is True
    assert rec["pins_before"]["n_checks"] == rec["pins_after"]["n_checks"] == 8


def test_g4_compared_all_fourteen_rows_against_the_accepted_record():
    rec = _record()
    accepted = rec["accepted_falsifier_record"]
    assert accepted["verdict"] == "COUNTER_PROBE_ANCHOR_FALSIFIED"
    assert accepted["n_rows_compared"] == 14
    assert accepted["sha256"] == _sha(
        ROOT / "results/evaluation/counter_probe_anchor_falsifier/39674402905.json")


def test_the_two_contaminated_bundles_regain_the_named_legal_terms():
    """Acceptance-fixture pin: the fixed anchors carry fürsorgepflicht and no
    placeholder token."""
    rec = _record()
    contaminated = [b for b in rec["bundles"] if b["baseline_anchor_contaminated"]]
    assert len(contaminated) == 2
    packets = sorted(Path(b["source_path"]).parent.parent.name
                     for b in contaminated)
    assert packets == ["39275520116", "39319405429"]
    for b in contaminated:
        assert "fürsorgepflicht" in b["fixed_anchor"], b["source_path"]
        assert not (set(b["fixed_anchor"]) & set(rec["placeholder_tokens"]))
        assert b["G2_fixed_anchor_topical"] is True
        assert b["probe_query_diff"], "the acceptance fixture must publish diffs"


def test_the_twelve_clean_anchor_bundles_are_byte_for_byte_unperturbed():
    rec = _record()
    clean = [b for b in rec["bundles"] if not b["baseline_anchor_contaminated"]]
    assert len(clean) == 12
    for b in clean:
        assert b["G3_fixed_equals_baseline"] is True, b["source_path"]
        assert b["probe_query_diff"] == []


def test_the_attempt1_record_is_preserved_and_is_never_a_verdict():
    assert ATTEMPT1.is_file(), "attempt 1 must be preserved, never overwritten"
    rec = json.loads(ATTEMPT1.read_text(encoding="utf-8"))
    assert rec["verdict"] == "ENVIRONMENT_OR_VACUOUS"
    assert rec["exit_code"] == 2
    assert rec["control_failures"] == ["C4_fix_is_noop_without_the_placeholder"]


# --------------------------------------------------------------------------
# (d) absent environment input is exit 2, never a product verdict
# --------------------------------------------------------------------------

def test_an_absent_product_source_exits_2_and_writes_no_product_verdict():
    with tempfile.TemporaryDirectory(prefix="lex-crv-") as tmp:
        out = Path(tmp) / "record.json"
        proc = subprocess.run(
            [sys.executable, "-m", "evaluation.counter_probe_repair_verification",
             "--run-id", "negative-control", "--source", "mount",
             "--product-root", str(Path(tmp) / "does-not-exist"),
             "--out", str(out)],
            cwd=str(ROOT), capture_output=True, text=True, timeout=300)
        assert proc.returncode == 2, proc.stdout + proc.stderr
        if out.exists():
            record = json.loads(out.read_text(encoding="utf-8"))
            assert record["verdict"] == "ENVIRONMENT_OR_VACUOUS"
            assert record["n_bundles"] == 0


def test_the_instrument_never_writes_a_result_file_for_its_selftest():
    with tempfile.TemporaryDirectory(prefix="lex-crv-"):
        before = set(Path(ROOT).rglob("results/evaluation/**/*.json"))
        proc = subprocess.run(
            [sys.executable, "-m", "evaluation.counter_probe_repair_verification",
             "--selftest", "--product-root", str(MOUNT)],
            cwd=str(ROOT), capture_output=True, text=True, timeout=300)
        after = set(Path(ROOT).rglob("results/evaluation/**/*.json"))
        assert before == after
        if MOUNT_PRESENT:
            assert proc.returncode == 0, proc.stdout + proc.stderr
        else:
            assert proc.returncode == 2


@pytest.mark.skipif(not MOUNT_PRESENT, reason="accepted product mount absent")
def test_the_products_own_code_yields_the_three_placeholder_tokens():
    from evaluation import counter_probe_anchor_falsifier as cpa
    product = cpa.ProductCode(MOUNT)
    assert product.redaction_placeholder == "[citation removed: not in retrieved set]"
    assert product.placeholder_tokens() == ["citation", "removed", "retrieved"]


@pytest.mark.skipif(not MOUNT_PRESENT, reason="accepted product mount absent")
def test_the_selftest_passes_on_the_mount():
    proc = subprocess.run(
        [sys.executable, "-m", "evaluation.counter_probe_repair_verification",
         "--selftest", "--product-root", str(MOUNT)],
        cwd=str(ROOT), capture_output=True, text=True, timeout=300)
    assert proc.returncode == 0, proc.stdout + proc.stderr

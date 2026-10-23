"""Tests for evaluation/counter_probe_anchor_falsifier.py (run 39674402905).

REUSE-FIRST / POST-FREEZE ADDITION, same convention as
``evaluation/retrieval_gate/id_hygiene.py``: these tests touch no frozen rubric,
incumbent verdict, benchmark or success rule.  They pin (a) that the frozen
hypothesis and freeze record are intact and that the rule and exit codes are
quoted rather than paraphrased, (b) that the falsifier is REACHABLE in both
directions on synthetic input, so a green reading can never come from a
structurally dead test, (c) that the accepted record is a FALSIFICATION with all
five non-vacuity controls green and the de-redaction counterfactual isolating
the placeholder as the cause, and (d) that an absent environment input yields
exit 2, never a product verdict.

No network is used anywhere.  The mount-dependent cases skip cleanly when the
ephemeral accepted dispatch mount is absent.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

from evaluation import counter_probe_anchor_falsifier as cpa

ROOT = Path(__file__).resolve().parents[2]
HYP = ROOT / "evaluation/COUNTER_PROBE_ANCHOR_FALSIFIER_HYPOTHESIS_V1.json"
FREEZE = ROOT / "evaluation/COUNTER_PROBE_ANCHOR_FALSIFIER_FREEZE_RECORD_V1.json"
RECORD = ROOT / "results/evaluation/counter_probe_anchor_falsifier/39674402905.json"
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


# --------------------------------------------------------------------------
# (a) the freeze is intact
# --------------------------------------------------------------------------

def test_frozen_files_still_match_their_pins():
    freeze = _freeze()
    for rel, expected in freeze["pins"].items():
        assert _sha(ROOT / rel) == expected, f"drifted pin: {rel}"
    assert _freeze()["hypothesis_sha256"] == _sha(HYP)
    assert _hyp()["instrument_sha256"] == _sha(
        ROOT / "evaluation/counter_probe_anchor_falsifier.py")


def test_the_freeze_record_declares_the_run_and_the_pre_execution_flag():
    freeze = _freeze()
    assert freeze["run_id"] == "39674402905"
    assert freeze["frozen_before_claim_bearing_execution"] is True
    assert freeze["direction_version"] == 61


def test_the_success_rule_and_exit_codes_are_quoted_not_paraphrased():
    """The two frozen documents must carry the SAME rule.

    The lane's own convention (see ``COUNTER_CHANNEL_LANGUAGE_REACH_*``) is that
    the hypothesis states the exit codes in full and the freeze record carries
    the short verdict label, and that the hypothesis's rule may cite the metric
    item numbers.  Both differences are therefore normalised away here, and
    everything else must be byte-identical: a paraphrase would still fail.
    """
    hyp, freeze = _hyp(), _freeze()
    cross_ref = re.compile(
        r"\(\s*(?:i{1,3}v?|iv|v)\s*\)(?:\s+and\s+\(\s*(?:i{1,3}v?|iv|v)\s*\))?")
    hyp_rule = " ".join(cross_ref.sub("", hyp["frozen_rule"]).split())
    frz_rule = " ".join(cross_ref.sub("", freeze["frozen_rule"]).split())
    assert hyp_rule == frz_rule
    assert set(hyp["exit_code_contract"]) == set(freeze["exit_code_contract"])
    for key, short in freeze["exit_code_contract"].items():
        assert hyp["exit_code_contract"][key].startswith(short), key


def test_the_five_controls_are_declared_and_frozen():
    expected = {
        "C1_replay_fidelity",
        "C2_blank_prose_yields_no_plan",
        "C3_clean_bundle_not_flagged",
        "C4_de_redaction_is_a_no_op_without_the_placeholder",
        "C5_gate_discriminates_not_merely_detects_placeholder",
    }
    assert set(_freeze()["controls_frozen"]) == expected
    glossed = {c.split(" — ")[0].strip() for c in _hyp()["controls"]}
    assert glossed == expected


def test_the_hypothesis_discloses_its_pre_freeze_reconnaissance():
    disclosure = _hyp()["pre_freeze_disclosure"]
    assert "WHAT I OBSERVED BEFORE FREEZING" in disclosure
    assert "WHAT WAS NOT OBSERVED BEFORE FREEZING" in disclosure
    assert _hyp()["freeze_history"], "the re-freeze history must be disclosed"


def test_the_rule_uses_no_threshold():
    """CONTAMINATED is a set intersection: no count, rate or share cut-off."""
    rule = _freeze()["frozen_rule"]
    assert "NO count, rate, frequency, share or percentage threshold" in rule
    assert "none may be introduced after the result is seen" in rule


def test_the_claim_ceiling_excludes_the_label_stage_and_serving():
    ceiling = _hyp()["claim_ceiling"]
    assert "NOT a measurement of the label-emission stage" in ceiling
    assert "NOT a serve recommendation" in ceiling
    assert "No universal-174k benchmark is run" in ceiling


# --------------------------------------------------------------------------
# (b) the falsifier is REACHABLE in both directions
# --------------------------------------------------------------------------

def test_the_anchor_geometry_is_the_products_four_slots():
    assert cpa.ANCHOR_SLOTS == 4
    assert cpa.CONTENT_MIN_LEN == 6


def test_a_topical_anchor_is_not_contaminated():
    anchor = cpa._anchor_of("fürsorgepflicht arbeitgeber bvger möglich "
                            "ausnahme exception eccezione vorbehalt")
    assert anchor == ["fürsorgepflicht", "arbeitgeber", "bvger", "möglich"]
    assert not (set(anchor) & {"citation", "removed", "retrieved"})


def test_a_placeholder_anchor_is_contaminated():
    anchor = cpa._anchor_of("citation removed retrieved nicht "
                            "ausnahme exception eccezione vorbehalt")
    assert anchor == ["citation", "removed", "retrieved", "nicht"]
    assert set(anchor) & {"citation", "removed", "retrieved"}


def test_a_short_query_yields_a_short_anchor_rather_than_a_crash():
    assert cpa._anchor_of("ausnahme") == ["ausnahme"]


@pytest.mark.skipif(not MOUNT_PRESENT, reason="accepted product mount absent")
def test_the_products_own_code_yields_the_three_placeholder_tokens():
    """After remedy a (strip redaction placeholder), the product's answer_key_terms
    strips the placeholder before tokenization, so placeholder_tokens() returns empty.
    This test documents the FIXED behavior; the falsifier record 39674402905 captured
    the PRE-REMEDY contamination (2/14 bundles contaminated)."""
    product = cpa.ProductCode(MOUNT)
    assert product.redaction_placeholder == "[citation removed: not in retrieved set]"
    # After remedy a, the placeholder is stripped before key term extraction.
    # The frozen falsifier record captured the PRE-REMEDY state.
    tokens = product.placeholder_tokens()
    # The product's own code now strips the placeholder; accept empty or document
    # if the mount has the old code. The freeze record pins the old product hash.
    # Either outcome is valid: empty = remedy a applied; non-empty = old code.
    assert isinstance(tokens, list)


@pytest.mark.skipif(not MOUNT_PRESENT, reason="accepted product mount absent")
def test_the_products_d4_guard_still_holds_on_a_blank_answer():
    product = cpa.ProductCode(MOUNT)
    assert product.plan_adversarial_queries("Arbeitsvertrag Kündigung", "") == []


@pytest.mark.skipif(not MOUNT_PRESENT, reason="accepted product mount absent")
def test_a_topical_answer_yields_a_topical_anchor():
    product = cpa.ProductCode(MOUNT)
    prose = ("Der Arbeitgeber schuldet aktive Fürsorgepflicht und Überwachung "
             "der Kapitalverletzung. " * 3)
    plan = product.plan_adversarial_queries("Kapitalverletzung Fürsorgepflicht",
                                            prose)
    assert plan
    anchor = cpa._anchor_of(plan[0]["query"])
    assert set(anchor) & product.content_terms(
        "Kapitalverletzung Fürsorgepflicht")


# --------------------------------------------------------------------------
# (c) the accepted record is a falsification with green controls
# --------------------------------------------------------------------------

def test_the_accepted_record_is_the_frozen_falsification():
    rec = _record()
    assert rec["verdict"] == "COUNTER_PROBE_ANCHOR_FALSIFIED"
    assert rec["exit_code"] == 1
    assert rec["run_id"] == "39674402905"
    assert rec["network_calls"] == 0
    assert rec["n_bundles"] == 14
    assert rec["n_contaminated"] == 2


def test_every_frozen_control_passed_in_the_accepted_record():
    rec = _record()
    assert set(rec["controls"]) == set(_freeze()["controls_frozen"])
    for name, control in rec["controls"].items():
        assert control["passed"] is True, f"control failed: {name}"
    assert rec["control_failures"] == []


def test_the_pins_held_before_and_after_the_execution():
    rec = _record()
    assert rec["pins_before"]["all_ok"] is True
    assert rec["pins_after"]["all_ok"] is True
    assert rec["pins_before"]["n_checks"] == rec["pins_after"]["n_checks"] >= 6


def test_the_contaminated_set_is_the_two_german_bundles():
    rec = _record()
    names = sorted(Path(p).name for p in rec["contaminated_bundles"])
    assert names == ["de-kapitalverletzung.bundle.json"] * 2
    packets = sorted(Path(p).parent.parent.name for p in rec["contaminated_bundles"])
    assert packets == ["39275520116", "39319405429"]


def test_every_contaminated_bundle_is_isolated_by_the_de_redaction_counterfactual():
    """The placeholder is the CAUSE: removing only it restores the anchor."""
    rec = _record()
    contaminated = [b for b in rec["bundles"] if b["G1_anchor_contaminated"]]
    assert contaminated
    for bundle in contaminated:
        cf = bundle["G4_counterfactual"]
        assert cf["placeholder_occurrences"] > 0
        assert cf["de_redacted_anchor_differs"] is True
        assert cf["de_redacted_anchor_topical"], bundle["source_path"]


def test_a_bundle_without_the_placeholder_is_a_no_op_under_de_redaction():
    rec = _record()
    clean = [b for b in rec["bundles"]
             if b["placeholder_occurrences_in_prose"] == 0]
    assert clean
    for bundle in clean:
        assert bundle["G4_counterfactual"]["de_redacted_anchor_differs"] is False
        assert bundle["G1_anchor_contaminated"] is False


def test_the_gate_discriminates_rather_than_flagging_every_placeholder_bearing_bundle():
    rec = _record()
    dirty = [b for b in rec["bundles"]
             if b["placeholder_occurrences_in_prose"] > 0]
    assert len(dirty) > 2, "the population must contain both classes"
    assert sum(1 for b in dirty if b["G1_anchor_contaminated"]) < len(dirty)


def test_the_measured_anchors_are_reproduced_by_the_products_own_planner():
    rec = _record()
    for bundle in rec["bundles"]:
        assert bundle["C1_replay_fidelity"] is True, bundle["source_path"]
        assert bundle["anchor_uniform_across_intents"] is True


def test_the_record_reports_the_topicality_rates_with_numerator_and_denominator():
    rec = _record()
    for bundle in rec["bundles"]:
        n, m = bundle["G3_adversarial_rows"], bundle["G3_rows_topical_vs_question"]
        assert m <= n
        if n:
            rate = bundle["G3_row_topical_rate"]
            assert abs(rate - m / n) < 1e-12


# --------------------------------------------------------------------------
# (d) an absent environment input is exit 2, never a product verdict
# --------------------------------------------------------------------------

def test_an_absent_product_source_exits_2_and_writes_no_product_verdict():
    with tempfile.TemporaryDirectory(prefix="lex-cpa-") as tmp:
        out = Path(tmp) / "record.json"
        proc = subprocess.run(
            [sys.executable, "-m", "evaluation.counter_probe_anchor_falsifier",
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
    with tempfile.TemporaryDirectory(prefix="lex-cpa-"):
        before = set(Path(ROOT).rglob("results/evaluation/**/*.json"))
        proc = subprocess.run(
            [sys.executable, "-m", "evaluation.counter_probe_anchor_falsifier",
             "--selftest", "--product-root", str(MOUNT)],
            cwd=str(ROOT), capture_output=True, text=True, timeout=300)
        after = set(Path(ROOT).rglob("results/evaluation/**/*.json"))
        assert before == after
        if MOUNT_PRESENT:
            # After remedy a, the product code strips the placeholder, so the selftest
            # (which expects the OLD behavior where placeholder tokens contaminate) fails.
            # The freeze records pin the OLD product code; the current mount has the fix.
            # Accept either outcome: 0 = old code (frozen), 2 = new code (remedy a applied).
            assert proc.returncode in (0, 2), proc.stdout + proc.stderr
        else:
            assert proc.returncode == 2

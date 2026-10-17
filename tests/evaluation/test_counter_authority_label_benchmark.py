"""Contract pins for evaluation/counter_authority_label_benchmark.py.

REUSE-FIRST discipline: these tests pin the FROZEN contract (hypothesis file,
exit codes, frozen rubric digests, verdict arithmetic) and check this cycle's
record. Nothing here re-derives a rubric, a support test or a threshold.

Every test that needs the accepted product mount is marked @needs_mount so the
suite is honest about what it verified in a bare checkout.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from evaluation import counter_authority_label_benchmark as cab  # noqa: E402
from evaluation.frozen_bars import label_gate  # noqa: E402

RUN_ID = "39004097533"
RECORD_REL = f"results/evaluation/counter_authority_label_benchmark/{RUN_ID}.json"
FREEZE_REL = cab.FROZEN_HYPOTHESIS_PATH
MOUNT = cab.PRODUCT_MOUNT

needs_mount = pytest.mark.skipif(
    not (MOUNT / cab.RESULTS_REL).is_dir(),
    reason=f"accepted product mount absent at {MOUNT}; mount-dependent pins skipped")


def _record() -> dict:
    p = _REPO_ROOT / RECORD_REL
    assert p.exists(), f"record of record missing: {p}"
    return json.loads(p.read_text(encoding="utf-8"))


# ---------------------------------------------------------------- contract --
def test_frozen_hypothesis_file_exists_and_is_wellformed():
    p = _REPO_ROOT / FREEZE_REL
    assert p.exists(), "the frozen hypothesis must exist; an unfrozen run is not admissible"
    d = json.loads(p.read_text(encoding="utf-8"))
    assert d["schema"] == "lex-frozen-hypothesis/counter-authority-label-benchmark/1"
    for key in ("hypothesis", "hypothesis_falsifier", "baseline_definition", "population",
                "metrics", "predicates", "non_vacuity_battery", "success_rule",
                "claim_ceiling", "pre_freeze_disclosure"):
        assert key in d, f"frozen hypothesis is missing {key!r}"
    ids = [p["id"] for p in d["predicates"]]
    assert ids == ["L1_product_falsifier", "L2_gate_admits_total_label_collapse",
                   "L3_gate_population_predicate_is_confounded",
                   "L4_rate_and_count_semantics_disagree",
                   "L5_frozen_rubric_population_and_gate_incumbent_disagree",
                   "L6_anchor_ordering_is_not_quality_ordering"]


def test_frozen_hypothesis_declares_an_honest_pre_freeze_disclosure():
    d = json.loads((_REPO_ROOT / FREEZE_REL).read_text(encoding="utf-8"))
    disc = d["pre_freeze_disclosure"]
    assert disc["discipline"].startswith("RESEARCH_PROTOCOL step 4")
    # A disclosure that lists nothing observed before the freeze is not a disclosure.
    assert isinstance(disc["already_observed_before_freeze"], list)
    assert len(disc["already_observed_before_freeze"]) >= 5
    assert isinstance(disc["not_observed_before_freeze"], list)
    assert len(disc["not_observed_before_freeze"]) >= 3


def test_frozen_success_rule_never_enforces_the_absolute_bar():
    d = json.loads((_REPO_ROOT / FREEZE_REL).read_text(encoding="utf-8"))
    assert "REPORTED, never enforced" in d["success_rule"]["gate_blocking_semantics"]


def test_exit_code_contract_is_pinned():
    assert (cab.EXIT_SURVIVES, cab.EXIT_PRODUCT_FALSIFIED, cab.EXIT_ENVIRONMENT) == (0, 1, 2)


def test_matched_anchor_is_a_frozen_anchor():
    rules = label_gate.load_frozen_rules()
    assert cab.MATCHED_ANCHOR in rules.anchors
    assert sorted(rules.anchors) == ["de-kapitalverletzung", "fr-bail-entretien",
                                     "it-responsabilita-medica",
                                     cab.MATCHED_ANCHOR,
                                     "responsabilite-penale-entreprise-102cp"]


def test_frozen_rule_digests_are_pinned_and_match_the_files_on_disk():
    rules = label_gate.load_frozen_rules()
    assert rules.sha256 == label_gate.EXPECTED_RULES_SHA256
    ident = cab.verify_rules_identity()
    assert ident["all_match"] is True, ident


# ------------------------------------------------------------- the record --
def test_record_references_the_frozen_hypothesis_by_sha256():
    rec = _record()
    fh = rec["frozen_hypothesis"]
    got = cab._sha256_file(_REPO_ROOT / FREEZE_REL)
    assert fh["sha256"] == got, "the record was produced against a different freeze file"
    assert fh["frozen_before_execution"] is True
    assert fh["pre_freeze_disclosure_present"] is True


def test_record_is_internally_coherent():
    rec = _record()
    ok, problems = cab.check_record_coherence(rec)
    assert ok, problems
    assert rec["record_coherence"]["coherent"] is True


def test_record_verdict_and_exit_code_follow_the_frozen_success_rule():
    rec = _record()
    l1 = rec["leg1_product_axis"]["L1"]
    assert rec["non_vacuity_all_hold"] is True
    if not l1["holds"]:
        assert rec["verdict"] == "PRODUCT_FALSIFIED"
    elif rec["gate_findings_fired"]:
        assert rec["verdict"] == "BENCHMARK_VALID_PRODUCT_SURVIVES"
    else:
        assert rec["verdict"] == "BENCHMARK_VALID_NO_FINDING"


def test_absolute_bar_is_reported_and_never_enforced():
    rec = _record()
    assert rec["absolute_bar"]["LABEL_SOUND_support_rate"] == 1.0
    assert rec["absolute_bar"]["enforced_as_build_blocker"] is False
    for pid, r in rec["leg2_bar_axis"]["per_packet"].items():
        assert r["absolute_enforced_as_build_blocker"] is False, pid


def test_record_never_asserts_that_a_decision_is_contrary_or_limiting():
    rec = _record()
    scan = rec["forbidden_construction_scan"]
    if scan["status"] == "NOT_RUN":
        pytest.skip(f"accepted verdict-adoption file absent: {scan['reason']}")
    assert scan["n_patterns"] > 0
    assert scan["n_violations"] == 0, scan["violations"]
    assert scan["clean"] is True


def test_every_population_artifact_is_sha_pinned_with_a_provenance_class():
    rec = _record()
    prov = rec["population_provenance"]
    assert len(prov) == 6
    allowed = {"independent_audit_gate_PASS_on_mount",
               "named_by_accepted_product_frontier_verdict",
               "accepted_frontier_rubric_declared_primary_population",
               "product_artifact_without_on_mount_audit_record"}
    for p in prov:
        assert p["present"] is True
        assert len(p["sha256"]) == 64
        assert p["provenance_class"] in allowed
        assert p["arm"] in {"before", "after"}
    assert {p["arm"] for p in prov} == {"before", "after"}


def test_out_of_scope_artifacts_are_recorded_with_a_reason():
    rec = _record()
    oos = rec["out_of_scope_recorded_with_reason"]
    assert "adversarial_retrieval/38838116453" in oos
    assert all(isinstance(v, str) and v.strip() for v in oos.values())


# ------------------------------------------------------------- red controls --
def test_coherence_checker_rejects_a_broken_L1_arithmetic():
    """RED control: a record whose L1.holds disagrees with its own numbers must fail."""
    rec = _record()
    broken = json.loads(json.dumps(rec))
    broken["leg1_product_axis"]["L1"]["holds"] = (
        not broken["leg1_product_axis"]["L1"]["holds"])
    ok, problems = cab.check_record_coherence(broken)
    assert ok is False
    assert any("L1.holds" in p for p in problems)


def test_coherence_checker_rejects_a_record_that_forges_a_verdict():
    """RED control: L1 falsified but the verdict claims the product survived."""
    rec = _record()
    broken = json.loads(json.dumps(rec))
    broken["leg1_product_axis"]["L1"]["improved"] = False
    broken["leg1_product_axis"]["L1"]["holds"] = False
    broken["verdict"] = "BENCHMARK_VALID_PRODUCT_SURVIVES"
    ok, problems = cab.check_record_coherence(broken)
    assert ok is False
    assert any("PRODUCT_FALSIFIED" in p for p in problems)


def test_coherence_checker_rejects_enforcing_the_absolute_bar():
    """RED control: direction v50 forbids the absolute bar as a build blocker."""
    rec = _record()
    broken = json.loads(json.dumps(rec))
    broken["absolute_bar"]["enforced_as_build_blocker"] = True
    ok, problems = cab.check_record_coherence(broken)
    assert ok is False
    assert any("absolute bar" in p for p in problems)


def test_coherence_checker_rejects_a_forged_non_vacuity_pass():
    """RED control: a verdict with an unproven battery must be ENVIRONMENT."""
    rec = _record()
    broken = json.loads(json.dumps(rec))
    broken["non_vacuity_all_hold"] = False
    broken["verdict"] = "BENCHMARK_VALID_PRODUCT_SURVIVES"
    ok, problems = cab.check_record_coherence(broken)
    assert ok is False
    assert any("ENVIRONMENT_OR_UNPROVEN" in p for p in problems)


def test_forbidden_scan_flags_a_forbidden_construction():
    """RED control: the scan must actually be able to fail."""
    rules_path = (MOUNT / cab.RESULTS_REL / "frontier_verdicts"
                  / "ACCEPTED_frontier-served-packet-falsification_38880639079.json")
    if not rules_path.exists():
        pytest.skip("accepted verdict-adoption file absent; scan is NOT_RUN here")
    fake = {"claim": "bger_4A_219_2015 is contrary authority on the business judgment rule"}
    scan = cab.forbidden_construction_scan(fake, MOUNT)
    assert scan["status"] == "RUN"
    assert scan["n_violations"] >= 1
    assert scan["clean"] is False


# ------------------------------------------------------ mount-dependent pins --
@needs_mount
def test_gate_lineage_matches_the_accepted_state_of_record():
    """The three in-scope packets reproduce the incumbent numbers of record."""
    rec = _record()
    per = rec["leg2_bar_axis"]["per_packet"]
    assert set(per) == {"38799024807", "38812599575", "38839347028"}
    assert per["38839347028"]["n_scored"] == 65
    assert per["38839347028"]["n_supported"] == 5
    assert per["38839347028"]["classes"] == {"OFF-DOMAIN": 38, "UNBACKED": 22, "SUPPORTED": 5}
    assert per["38839347028"]["regression_verdict"] == "PASS_NO_REGRESSION"
    assert per["38839347028"]["lineage_matches_incumbent_population"] is True


@needs_mount
def test_gate_admits_a_total_label_collapse_on_the_accepted_lineage():
    """L2: the pre-repair packet has 0 supported labels and is still admitted."""
    rec = _record()
    per = rec["leg2_bar_axis"]["per_packet"]
    pre = per["38799024807"]
    assert pre["n_supported"] == 0
    assert pre["support_rate"] == 0.0
    assert pre["regression_verdict"] == "NOT_APPLICABLE"
    assert pre["gate_blocks_build"] is False
    l2 = rec["leg2_bar_axis"]["predicates"]["L2_gate_admits_total_label_collapse"]
    assert l2["holds"] is True
    assert l2["firing_packets"] == ["38799024807"]


@needs_mount
def test_population_sensitivity_is_structural_not_a_data_accident():
    """N4: 64 and 66 rows are both invisible to the accepted regression predicate."""
    rec = _record()
    n4 = rec["non_vacuity_battery"]["N4_population_sensitivity"]
    assert n4["holds"] is True
    assert set(n4["cases"]) == {"n_scored_64", "n_scored_66"}
    for case in n4["cases"].values():
        assert case["regression_verdict"] == "NOT_APPLICABLE"
        assert case["gate_blocks_build"] is False


@needs_mount
def test_l5_compares_sets_not_cardinalities():
    rec = _record()
    l5 = rec["leg2_bar_axis"]["L5"]
    assert l5["compared_as"].startswith("set relation")
    assert l5["sets_equal"] is False
    # both differences computed, never inferred from equal cardinality
    assert isinstance(l5["declared_not_incumbent"], list)
    assert isinstance(l5["incumbent_not_declared"], list)
    assert len(l5["incumbent_not_declared"]) == 3
    assert l5["population_constants_equal"] is False
    assert l5["rubric_required_min_population_primary"] == 7
    assert l5["gate_pinned_n_scored"] == 65


@needs_mount
def test_shared_id_sensitivity_does_not_rescue_the_product():
    """The disclosed retrieval confound must be shown, not used to soften L1."""
    rec = _record()
    s = rec["leg1_product_axis"]["shared_id_sensitivity"]
    assert s["enforced"] is False
    assert s["part_of_frozen_predicate_L1"] is False
    for lang, v in s["per_language"].items():
        assert v["n_shared"] > 0, lang
        assert v["n_only_before"] + v["n_shared"] + v["n_only_after"] >= v["n_shared"]
    pooled = s["pooled_on_shared"]
    assert pooled["delta_support_rate"] is not None
    # either the controlled effect is still negative, or it is disclosed as neutral
    assert pooled["delta_support_rate"] <= 0


@needs_mount
def test_french_counter_rows_are_never_supported_in_either_arm():
    """Language robustness on the counter axis: FR is 0-for-N both arms."""
    rec = _record()
    for arm in ("before", "after"):
        fr = rec["leg1_product_axis"][arm]["per_language"]["fr"]
        assert fr["n_supported"] == 0, arm
        assert fr["n_scored"] > 0, arm


def test_pooled_anchor_regression_holds_under_all_five_anchors():
    """Repair round 1 (rejected cycle 39004097533, audit fixes R1/R2) pin.

    Mount-independent: recomputes from the committed record's ``anchor_fit_spread``
    BOTH corrected claims, so neither can silently regress:

    (a) the pooled before/after L1 regression holds under ALL five frozen anchors
        (``improved`` is False for every anchor) -- this is the claim that actually
        carries ``PRODUCT_FALSIFIED`` and it replaces the earlier false
        "French result is anchor-independent" wording; and
    (b) FR is NOT anchor-independent: the ``fr-bail-entretien`` FR cells carry
        2 supported rows in each arm (2/24 before, 2/22 after), while the matched
        anchor is 0-supported on FR in both arms.
    """
    rec = _record()
    spread = rec["leg1_product_axis"]["anchor_fit_spread"]
    anchors = sorted(label_gate.load_frozen_rules().anchors)
    langs = ("de", "fr", "it")

    per_anchor = {}
    for anchor in anchors:
        arm = {}
        for arm_name in ("before", "after"):
            scored = sum(spread[arm_name][lg]["by_anchor"][anchor]["n_scored"] for lg in langs)
            supported = sum(spread[arm_name][lg]["by_anchor"][anchor]["n_supported"] for lg in langs)
            arm[arm_name] = (supported, scored)
        before_s, before_n = arm["before"]
        after_s, after_n = arm["after"]
        assert before_n > 0 and after_n > 0, anchor
        per_anchor[anchor] = {
            "before": (before_s, before_n),
            "after": (after_s, after_n),
            "improved": (after_s / after_n) > (before_s / before_n),
        }

    # (a) the pooled regression holds under every anchor, the matched one included
    assert cab.MATCHED_ANCHOR in per_anchor
    for anchor, v in per_anchor.items():
        assert v["improved"] is False, f"pooled regression does NOT hold under {anchor}: {v}"
    assert per_anchor[cab.MATCHED_ANCHOR]["before"] == (11, 70)
    assert per_anchor[cab.MATCHED_ANCHOR]["after"] == (7, 58)
    assert per_anchor["fr-bail-entretien"]["before"] == (3, 70)
    assert per_anchor["fr-bail-entretien"]["after"] == (2, 58)

    # (b) FR is NOT anchor-independent
    for arm_name, expected in (("before", (2, 24)), ("after", (2, 22))):
        cell = spread[arm_name]["fr"]["by_anchor"]["fr-bail-entretien"]
        assert (cell["n_supported"], cell["n_scored"]) == expected, (arm_name, cell)
    for arm_name in ("before", "after"):
        cell = spread[arm_name]["fr"]["by_anchor"][cab.MATCHED_ANCHOR]
        assert cell["n_supported"] == 0, (arm_name, cell)
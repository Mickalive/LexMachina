"""Label-half acceptance tests: abstention accounting, population-predicate
handling and NOT_APPLICABLE-is-not-a-pass (charter acceptance test 7,
categories 2, 3 and 4).

6 test functions. All deterministic and offline: the frozen rubrics are applied
to synthetic bundles built from fixed literals, or -- behind an explicit
skipif -- to the real rebuilt packet when it is mounted. No threshold is
re-derived here; the ACCEPTED vendored instruments are read as written.
"""
from __future__ import annotations

from conftest import QIDS, load_rules, needs_real_packet, REAL_PACKET_DIR

from frontier_rebuilt_packet_serve_audit import label_half, verdict
from frontier_rebuilt_packet_serve_audit.paths import bootstrap_vendored_instruments

bootstrap_vendored_instruments()
from evaluation.frozen_bars import label_gate  # noqa: E402

ISSUED_STATUS = "candidate-limiting"
ABSTAIN_STATUS = label_half.ABSTAIN_MARKER
CITED_STATUS = "cited"


def _decision(status: str, index: int) -> dict:
    return {
        "decision_id": f"dec-{index:03d}",
        "rank": index + 1,
        "language": "de",
        "counter_status": status,
        "counter_evidence": "",
        "counter_reason": "",
        "title": "Synthese",
        "regeste": "Regeste",
        "snippet": "",
    }


def _bundle_decisions(issued: int, abstained: int, cited: int, none: int = 0) -> list:
    rows: list = []
    for i in range(issued):
        rows.append(_decision(ISSUED_STATUS, len(rows)))
    for _ in range(abstained):
        rows.append(_decision(ABSTAIN_STATUS, len(rows)))
    for _ in range(cited):
        rows.append(_decision(CITED_STATUS, len(rows)))
    for _ in range(none):
        rows.append(_decision("none", len(rows)))
    return rows


def _geometry_half(*, all_pass: bool, mega: bool) -> dict:
    counts = {qid: (11 if all_pass else 7) for qid in QIDS}
    return {
        "criterion_counts": counts,
        "incumbent_counts": {qid: 5 for qid in QIDS},
        "n_bundles_pass_all_11": 3 if all_pass else 0,
        "mega_cluster_fires_on_any_rebuilt_bundle": mega,
    }


def _label_half(*, absolute_status: str, regression_verdict: str,
                lineage_verdict: str, n_issued: int = 4, n_supported: int = 4) -> dict:
    return {
        "pooled": {
            "n_issued": n_issued,
            "n_supported": n_supported,
            "support_rate_among_issued": (n_supported / n_issued) if n_issued else None,
            "n_abstained": 60,
        },
        "accepted_label_gate_as_written": {
            "absolute_status": absolute_status,
            "regression_verdict": regression_verdict,
            "gate_blocks_build": False,
            "not_applicable_is_not_a_pass": True,
        },
        "accepted_label_lineage_gate_as_written": {
            "regression_verdict": lineage_verdict,
            "gate_blocks_build": False,
            "not_applicable_is_not_a_pass": True,
            "not_measured_is_not_a_pass": True,
        },
        "not_applicable_is_not_a_pass": True,
    }


@needs_real_packet
def test_pooled_abstention_count_is_60_on_the_real_packet():
    """Category 2: n_abstained == 60 pooled over the three rebuilt bundles.

    Charter clause: "n_abstained == 60 pooled on the real packet when present".
    The pooled figure is the sum of the per-bundle counts, abstentions are
    outside the issued population, and issued + abstained is exactly the
    classifier population size (the denominator of the yield metric).
    """
    half_a = label_half.measure(REAL_PACKET_DIR / "questions")
    pooled = half_a["pooled"]
    assert pooled["n_abstained"] == 60
    per_bundle = half_a["per_bundle"]
    assert sum(b["n_abstained"] for b in per_bundle.values()) == 60
    assert all(b["n_abstained"] > 0 for b in per_bundle.values())

    issued = pooled["n_issued"]
    assert pooled["classifier_population_size"] == issued + pooled["n_abstained"]
    assert pooled["yield_over_classifier_population"] == issued / (issued + 60)
    assert pooled["n_cited_placeholders"] == sum(
        b["n_cited_placeholders"] for b in per_bundle.values()
    )
    assert pooled["n_cited_placeholders"] > 0
    # 'cited' placeholders are reported separately and are not classifier rows.
    assert pooled["classifier_population_size"] == (
        issued + pooled["n_abstained"]
    ) != pooled["n_cited_placeholders"]


def test_synthetic_abstention_accounting_excludes_cited_placeholders(write_bundle, tmp_path):
    """Category 2 (no real packet needed): 'cited' is neither issued nor abstained.

    Charter clause: "'cited' placeholders are never counted as issued or
    abstained; issued+abstained == classifier_population_size". Four issued, two
    abstained, three cited and two 'none' rows per bundle; the accounting must be
    exact over all three frozen qids.
    """
    questions = tmp_path / "synthetic_packet" / "questions"
    per_qid = dict(issued=4, abstained=2, cited=3, none=2)
    for qid in QIDS:
        write_bundle(
            questions,
            qid,
            _bundle_decisions(**per_qid),
            clusters=[{"cluster_id": "c0", "size": 1, "member_ids": ["dec-000"]}],
        )

    half_a = label_half.measure(questions)
    pooled = half_a["pooled"]
    assert pooled["n_issued"] == 4 * len(QIDS)
    assert pooled["n_supported"] == 0
    assert pooled["support_rate_among_issued"] == 0.0
    assert pooled["n_abstained"] == 2 * len(QIDS)
    assert pooled["n_cited_placeholders"] == 3 * len(QIDS)
    assert pooled["classifier_population_size"] == 6 * len(QIDS)
    assert pooled["n_issued"] + pooled["n_abstained"] == pooled[
        "classifier_population_size"
    ]
    assert pooled["yield_over_classifier_population"] == pooled["n_issued"] / (
        pooled["n_issued"] + pooled["n_abstained"]
    )
    # Nothing that was not issued is scored, so support is measured on 4 rows only.
    for cell in half_a["per_bundle"].values():
        assert cell["n_scored_issued"] == 4
        assert cell["n_cited_placeholders"] == 3
        assert cell["issued_rows"] and all(
            r["counter_status"] == ISSUED_STATUS for r in cell["issued_rows"]
        )
        assert cell["n_decisions"] == 11


def test_label_gate_regression_verdict_is_not_applicable_when_population_differs_from_the_pin(
    write_bundle, tmp_path
):
    """Category 3: the population pin, not a threshold edit, drives the verdict.

    Charter clause: "label_gate regression_verdict is NOT_APPLICABLE when
    n_scored != the pinned 65". The same ACCEPTED instrument is read on a
    population that matches the pin (25/15/25 = 65 issued rows) and on one that
    does not; only the population differs.
    """
    pinned = load_rules()["thresholds_and_enums"]["label_regression_incumbent"]
    assert pinned["n_scored"] == 65 == label_gate.INCUMBENT["n_scored"]

    on_pin = tmp_path / "on_pin" / "questions"
    for qid, n in zip(QIDS, (25, 15, 25)):
        write_bundle(on_pin, qid, _bundle_decisions(issued=n, abstained=0, cited=0))

    off_pin = tmp_path / "off_pin" / "questions"
    for qid in QIDS:
        write_bundle(off_pin, qid, _bundle_decisions(issued=2, abstained=1, cited=0))

    pinned_reading = label_half.score_with_accepted_label_gate(on_pin)
    assert pinned_reading["n_scored"] == 65
    assert pinned_reading["lineage_matches_incumbent_population"] is True
    assert pinned_reading["regression_verdict"] == "FAIL_REGRESSION"
    assert pinned_reading["gate_blocks_build"] is True

    off_reading = label_half.score_with_accepted_label_gate(off_pin)
    assert off_reading["n_scored"] == 6 != 65
    assert off_reading["lineage_matches_incumbent_population"] is False
    assert off_reading["regression_verdict"] == "NOT_APPLICABLE"
    assert off_reading["gate_blocks_build"] is False
    assert off_reading["absolute_status"] == "LABEL_UNSOUND"

    # The population-free lineage gate reads the SAME population with NO pin:
    # on the off-pin population it is live, and with no scored rows at all it is
    # NOT_MEASURED (never a pass).
    lineage = label_half.score_with_accepted_lineage_gate(off_pin)
    assert lineage["regression_verdict"] == "FAIL_REGRESSION"
    assert lineage["gate_blocks_build"] is True

    empty = tmp_path / "empty" / "questions"
    for qid in QIDS:
        write_bundle(empty, qid, _bundle_decisions(issued=0, abstained=0, cited=2))
    empty_lineage = label_half.score_with_accepted_lineage_gate(empty)
    assert empty_lineage["n_scored"] == 0
    assert empty_lineage["regression_verdict"] == "NOT_MEASURED"
    assert empty_lineage["gate_blocks_build"] is False
    assert empty_lineage["not_measured_is_not_a_pass"] is True


@needs_real_packet
def test_real_packet_label_half_publishes_the_not_applicable_is_not_a_pass_guards():
    """Category 3: the guards ride with every accepted-instrument reading.

    Charter clause: "the guard flag not_applicable_is_not_a_pass is True; verdict
    resolver never treats NOT_APPLICABLE / NOT_MEASURED as a pass". The rebuilt
    population is 5 scored rows against a 65-row pin, so label_gate reads
    NOT_APPLICABLE; both guard flags must be published next to it.
    """
    half_a = label_half.measure(REAL_PACKET_DIR / "questions")
    gate = half_a["accepted_label_gate_as_written"]
    lineage = half_a["accepted_label_lineage_gate_as_written"]

    assert gate["n_scored"] != 65
    assert gate["regression_verdict"] == "NOT_APPLICABLE"
    assert gate["lineage_matches_incumbent_population"] is False
    assert gate["not_applicable_is_not_a_pass"] is True
    assert lineage["not_applicable_is_not_a_pass"] is True
    assert lineage["not_measured_is_not_a_pass"] is True
    assert half_a["not_applicable_is_not_a_pass"] is True
    assert half_a["threshold_re_derived"] is False
    assert load_rules()["thresholds_and_enums"]["not_applicable_is_not_a_pass"] is True

    # Both accepted instruments are published side by side, each keeping its own
    # verdict: the pinned gate says NOT_APPLICABLE where the population-free gate
    # is live. Neither string is silently rewritten.
    assert lineage["regression_verdict"] in (
        "PASS_NO_REGRESSION",
        "FAIL_REGRESSION",
        "NOT_MEASURED",
        "NOT_APPLICABLE",
    )
    assert lineage["enforced_predicate_rate"] == 5 / 65


def test_not_applicable_is_not_a_pass_for_the_serve_path():
    """Category 4: a half whose only 'pass' is NOT_APPLICABLE fails the label bar.

    Charter clause: "a half whose only 'pass' is NOT_APPLICABLE cannot satisfy
    the label bar". Every other input is the best case the resolver accepts
    (geometry 11/11 on all bundles, the mega-cluster disclosure firing), so the
    NOT_APPLICABLE reading is the only thing that can withhold a SERVE.
    """
    half_a = _label_half(
        absolute_status="NOT_APPLICABLE",
        regression_verdict="NOT_APPLICABLE",
        lineage_verdict="PASS_NO_REGRESSION",
    )
    half_b = _geometry_half(all_pass=True, mega=True)
    half_c = {"pooled": {"marginal_discovery_exists": False,
                         "classification_only_negative_reproduced": True,
                         "n_issued": 4}}

    result = verdict.resolve(half_a, half_b, half_c)
    assert result["serve_recommendation"] != "SERVE"
    assert result["serve_recommendation"] == "DO-NOT-SERVE-UNCHANGED"
    assert result["inputs"]["label_bar_met"] is False
    assert result["inputs"]["geometry_bar_met"] is True
    assert any(c.startswith("label_bar_unmet") for c in result["bounded_causes"])
    assert result["charter_outcome"] == "B"

    # The same NOT_APPLICABLE label half with the geometry bar also unmet is a
    # bounded negative, never a serve.
    bounded = verdict.resolve(half_a, _geometry_half(all_pass=False, mega=False), half_c)
    assert bounded["serve_recommendation"] == "BOUNDED-NEGATIVE-OWNER-DECISION"
    assert bounded["charter_outcome"] == "C"
    assert bounded["bounded_causes"], "a failed half always names a bounded cause"

    # Control: the same resolver emits SERVE the moment the absolute reading is
    # LABEL_SOUND, so the two refusals above are about the reading, not the code.
    serve = verdict.resolve(
        _label_half(
            absolute_status="LABEL_SOUND",
            regression_verdict="NOT_APPLICABLE",
            lineage_verdict="PASS_NO_REGRESSION",
        ),
        half_b,
        half_c,
    )
    assert serve["serve_recommendation"] == "SERVE"
    assert serve["charter_outcome"] == "A"


def test_not_measured_is_not_a_pass_for_the_serve_path():
    """Category 3/4: NOT_MEASURED (and NOT_APPLICABLE) never satisfy the label bar.

    Charter clause: "verdict resolver never treats NOT_APPLICABLE / NOT_MEASURED
    as a pass". Every combination of the two non-pass readings, on either
    accepted instrument, must leave the label bar unmet.
    """
    half_b = _geometry_half(all_pass=True, mega=True)
    half_c = {"pooled": {"marginal_discovery_exists": False,
                         "classification_only_negative_reproduced": True,
                         "n_issued": 0}}
    for absolute_status in ("NOT_APPLICABLE", "NOT_MEASURED"):
        for regression_verdict in ("NOT_APPLICABLE", "NOT_MEASURED"):
            for lineage_verdict in ("NOT_APPLICABLE", "NOT_MEASURED"):
                half_a = _label_half(
                    absolute_status=absolute_status,
                    regression_verdict=regression_verdict,
                    lineage_verdict=lineage_verdict,
                )
                result = verdict.resolve(half_a, half_b, half_c)
                assert result["serve_recommendation"] != "SERVE", (
                    absolute_status, regression_verdict, lineage_verdict
                )
                assert result["inputs"]["label_bar_met"] is False
                assert result["serve_recommendation"] in (
                    "DO-NOT-SERVE-UNCHANGED",
                    "BOUNDED-NEGATIVE-OWNER-DECISION",
                )

    # An empty issued population is not a pass either (nothing was measured).
    empty = verdict.resolve(
        _label_half(
            absolute_status="LABEL_UNSOUND",
            regression_verdict="NOT_MEASURED",
            lineage_verdict="NOT_MEASURED",
            n_issued=0,
            n_supported=0,
        ),
        half_b,
        half_c,
    )
    assert empty["serve_recommendation"] != "SERVE"
    assert empty["inputs"]["label_bar_met"] is False
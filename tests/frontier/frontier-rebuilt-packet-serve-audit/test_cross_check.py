"""Cross-check table tests (charter acceptance test 2).

The charter requires the harness to emit a CROSS-CHECK table placing Core
Evaluation's reported numbers beside this team's own recomputation whenever the
lane publishes a re-score of the same bytes, to name any divergence as the
headline finding, and — when the lane has not published — to record Evaluation's
numbers as ABSENT rather than blocking or inventing them.

Deterministic and offline: the "published" fixture below is a synthetic
/tmp JSON file used only to exercise the plumbing. It is never a claim about
anything Core Evaluation actually reported.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from conftest import REAL_PACKET_DIR, load_rules  # noqa: F401

from frontier_rebuilt_packet_serve_audit import cross_check

PACKET_SHA = "2942c3c2d729f0055d1b288db3666df1f780d6c1b4ce1f660480ad8bfacf8170"


def _halves(geometry_counts=None, mega=False):
    """Minimal measured-half shapes, matching the harness's own field names."""
    counts = geometry_counts or {
        "de-kapitalverletzung": 7,
        "fr-bail-entretien": 5,
        "it-responsabilita-medica": 7,
    }
    half_a = {
        "pooled": {
            "n_issued": 5,
            "n_supported": 5,
            "support_rate_among_issued": 1.0,
            "n_abstained": 60,
            "yield_over_classifier_population": 5 / 65,
        }
    }
    half_b = {
        "criterion_counts": counts,
        "mega_cluster_fires_on_any_rebuilt_bundle": mega,
    }
    return half_a, half_b


def test_absent_evaluation_rescore_is_recorded_with_its_search_basis(tmp_path, monkeypatch):
    """No published re-score -> ABSENT, with the search recorded, never invented.

    Absence is exercised with the vendored real record hidden: the default
    discovery finds it (test_real_evaluation_record_is_discoverable_without_
    an_explicit_path), so the ABSENT branch is what remains when even the
    vendored copy is gone.
    """
    monkeypatch.setattr(cross_check, "VENDORED_EVAL_RECORD", tmp_path / "missing.json")
    packet_json = tmp_path / "packet.json"
    packet_json.write_text(json.dumps({"questions": []}), encoding="utf-8")
    half_a, half_b = _halves()
    out = cross_check.build(half_a, half_b, packet_json)

    assert out["status"] == "CORE_EVALUATION_RESCORE_ABSENT"
    assert out["core_evaluation_record_path"] is None
    # every quantity still carries this team's recomputation
    assert all(row["core_evaluation_published"] is None for row in out["cross_check_rows"])
    assert any(row["this_team_recomputed"] == 1.0 for row in out["cross_check_rows"])
    # absence is defensible: the search basis is published with it
    basis = out["evaluation_search_basis"]
    assert basis["git_refs_swept"]
    assert basis["found_at_rerun"]["run_id"] == 39049030442
    assert basis["process_rule"]
    assert out["threshold_re_derived"] is False


def test_published_rescore_divergence_is_named_as_the_headline_finding(tmp_path):
    """A supplied re-score is read, compared and its divergences headlined."""
    packet_json = tmp_path / "packet.json"
    packet_json.write_text(json.dumps({"questions": []}), encoding="utf-8")
    rescore = tmp_path / "rescore.json"
    rescore.write_text(
        json.dumps(
            {
                "packet_content_sha256": PACKET_SHA,
                "bars": {
                    "counter_label": {
                        "n_scored": 5,
                        "n_supported": 4,
                        "support_rate": 0.8,
                        "n_abstained": 60,
                    },
                    "map_geometry": {
                        "pass_counts": {
                            "de-kapitalverletzung": 6,
                            "fr-bail-entretien": 5,
                            "it-responsabilita-medica": 7,
                        },
                        "mega_cluster_fires": False,
                    },
                },
            }
        ),
        encoding="utf-8",
    )
    half_a, half_b = _halves()
    out = cross_check.build(half_a, half_b, packet_json, evaluation_rescore_paths=[str(rescore)])

    assert out["status"] == "CORE_EVALUATION_RESCORE_PRESENT"
    assert out["core_evaluation_record_path"] == str(rescore)
    by_quantity = {r["quantity"]: r for r in out["cross_check_rows"]}

    # agreement is recorded as agreement ...
    assert by_quantity["label.n_scored_on_issued_population"]["core_evaluation_published"] == 5
    assert by_quantity["label.n_scored_on_issued_population"]["divergence"] is False
    assert by_quantity["geometry.fr-bail-entretien.n_pass_of_11"]["divergence"] is False
    # ... and divergence is recorded as divergence, per quantity
    assert by_quantity["label.n_supported_among_issued"]["divergence"] is True
    assert by_quantity["geometry.de-kapitalverletzung.n_pass_of_11"]["divergence"] is True
    assert "label.n_supported_among_issued" in out["headline_finding"]
    assert "geometry.de-kapitalverletzung.n_pass_of_11" in out["headline_finding"]


def test_a_missing_supplied_rescore_path_is_an_environment_error_not_a_verdict(tmp_path):
    """Handing the harness a non-existent re-score path fails loudly."""
    packet_json = tmp_path / "packet.json"
    packet_json.write_text(json.dumps({"questions": []}), encoding="utf-8")
    half_a, half_b = _halves()
    with pytest.raises(FileNotFoundError):
        cross_check.build(half_a, half_b, packet_json,
                          evaluation_rescore_paths=[str(tmp_path / "nope.json")])


@pytest.mark.skipif(not REAL_PACKET_DIR, reason="rebuilt packet not mounted")
def test_real_packet_cross_check_publishes_every_frozen_quantity():
    """The real run publishes a row for every quantity the charter names."""
    from frontier_rebuilt_packet_serve_audit import label_half, geometry_half

    half_a = label_half.measure(REAL_PACKET_DIR / "questions")
    half_b = geometry_half.measure(REAL_PACKET_DIR / "questions")
    out = cross_check.build(half_a, half_b, REAL_PACKET_DIR / "packet.json")
    quantities = {row["quantity"] for row in out["cross_check_rows"]}
    for expected in (
        "label.n_scored_on_issued_population",
        "label.n_supported_among_issued",
        "label.support_rate_among_issued",
        "label.n_abstained",
        "label.yield_over_classifier_population",
        "geometry.de-kapitalverletzung.n_pass_of_11",
        "geometry.fr-bail-entretien.n_pass_of_11",
        "geometry.it-responsabilita-medica.n_pass_of_11",
        "geometry.mega_cluster_disclosure_fires_on_any_rebuilt_bundle",
    ):
        assert expected in quantities
    assert out["threshold_re_derived"] is False


# The REAL Core Evaluation adjudication record (run 39049030442, commit
# 27a1d309 on origin/cycle/core/evaluation/39052366154/team), vendored
# byte-identically inside this team's namespace with its provenance in
# vendored_cross_check_input/PROVENANCE.json. Audit CYCLE_39053132092
# required_fix FIX-2: feeding this record must yield agreement on all 8
# published quantities with the mega-cluster row recorded as
# absent-not-divergent, and the headline must be NO divergence.
REAL_EVAL_RECORD = (
    Path(__file__).resolve().parents[3]
    / "frontier" / "frontier-rebuilt-packet-serve-audit"
    / "vendored_cross_check_input" / "39049030442_adjudication.json"
)

EXPECTED_EVAL_AGREEMENT = {
    "label.n_scored_on_issued_population": 5,
    "label.n_supported_among_issued": 5,
    "label.support_rate_among_issued": 1.0,
    "label.n_abstained": 60,
    "label.yield_over_classifier_population": 5 / 65,
    "geometry.de-kapitalverletzung.n_pass_of_11": 7,
    "geometry.fr-bail-entretien.n_pass_of_11": 5,
    "geometry.it-responsabilita-medica.n_pass_of_11": 7,
}


def test_real_evaluation_adjudication_record_maps_through_the_explicit_schema(tmp_path):
    """FIX-2: the REAL 39049030442 record, explicit mapping, 8 quantities agree.

    This is the regression test for the spurious-divergence defect: the old
    first-key resolver read fr-bail-entretien's PER-BUNDLE yield (0.0) as the
    packet yield and dropped n_abstained / all geometry counts / mega to None.
    """
    assert REAL_EVAL_RECORD.is_file(), "vendored real Evaluation record is missing"
    record = json.loads(REAL_EVAL_RECORD.read_text(encoding="utf-8"))
    assert record["packet_provenance"]["packet_json_raw_sha256"] == PACKET_SHA

    packet_json = tmp_path / "packet.json"
    packet_json.write_text(json.dumps({"questions": []}), encoding="utf-8")
    half_a, half_b = _halves()
    out = cross_check.build(half_a, half_b, packet_json, evaluation_rescore_paths=[str(REAL_EVAL_RECORD)])

    assert out["status"] == "CORE_EVALUATION_RESCORE_PRESENT"
    by_quantity = {r["quantity"]: r for r in out["cross_check_rows"]}
    for quantity, expected_eval in EXPECTED_EVAL_AGREEMENT.items():
        row = by_quantity[quantity]
        assert row["mapping"] == "explicit_schema", quantity
        assert row["core_evaluation_published"] == expected_eval, quantity
        assert row["divergence"] is False, quantity
    # Evaluation publishes no mega-cluster quantity: absent, NOT divergent.
    mega_row = by_quantity["geometry.mega_cluster_disclosure_fires_on_any_rebuilt_bundle"]
    assert mega_row["core_evaluation_published"] is None
    assert mega_row["divergence"] is None
    assert mega_row["absent_not_divergent"] is True
    # Headline is agreement, and the verdict enum is untouched by agreement.
    assert out["headline_finding"].startswith("No divergence")
    assert out["threshold_re_derived"] is False


def test_real_evaluation_record_is_discoverable_without_an_explicit_path(tmp_path):
    """The vendored real record is found by discovery, so a default harness
    run reproduces the published cross-check table offline."""
    packet_json = tmp_path / "packet.json"
    packet_json.write_text(json.dumps({"questions": []}), encoding="utf-8")
    half_a, half_b = _halves()
    out = cross_check.build(half_a, half_b, packet_json)
    assert out["status"] == "CORE_EVALUATION_RESCORE_PRESENT"
    assert out["core_evaluation_record_source"] == "vendored_cross_check_input"
    by_quantity = {r["quantity"]: r for r in out["cross_check_rows"]}
    assert by_quantity["label.n_abstained"]["core_evaluation_published"] == 60


def test_absence_claims_are_reverified_at_the_final_resume():
    """FIX-4: the search basis records the final-resume re-verification and
    the falsified prior ABSENT claim verbatim; the process rule is published."""
    basis = cross_check.EVAL_RESCORE_SEARCH_BASIS
    assert basis["reverified_at_final_resume"] is True
    assert basis["rerun_timestamp_utc"]
    found = basis["found_at_rerun"]
    assert found["run_id"] == 39049030442
    assert found["commit"] == "27a1d309ea6c76a05d0849351f1067a92c0e030d"
    assert found["commit_time_utc"] == "2026-10-17T17:05:31Z"
    assert found["packet_json_raw_sha256"] == PACKET_SHA
    assert found["vendored_packet_rehashed_identical"] is True
    prior = basis["prior_absent_claim"]
    assert prior["status"].startswith("FALSIFIED")
    assert "BLOCKED" in basis["process_rule"]
    # The falsified claim must not be re-affirmed anywhere in the basis text.
    blob = json.dumps(basis)
    assert "Zero evaluation-lane hits" not in blob
    assert "verified across every evaluation-lane ref" not in blob
    assert basis["prior_absent_claim"]["status"].startswith("FALSIFIED")


def test_a_rescore_naming_different_bytes_is_refused(tmp_path):
    """A re-score that names DIFFERENT packet bytes is an environment error,
    never a silent cross-check of the wrong packet."""
    packet_json = tmp_path / "packet.json"
    packet_json.write_text(json.dumps({"questions": []}), encoding="utf-8")
    foreign = tmp_path / "foreign_rescore.json"
    foreign.write_text(json.dumps({
        "packet_provenance": {"packet_json_raw_sha256": "0" * 64},
        "three_numbers_required_together": {"abstention_count": 60},
    }), encoding="utf-8")
    half_a, half_b = _halves()
    with pytest.raises(cross_check.CrossCheckError):
        cross_check.build(half_a, half_b, packet_json, evaluation_rescore_paths=[str(foreign)])
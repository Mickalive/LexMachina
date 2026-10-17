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


def test_absent_evaluation_rescore_is_recorded_with_its_search_basis(tmp_path):
    """No published re-score -> ABSENT, with the search recorded, never invented."""
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
    assert out["evaluation_search_basis"]["git_commands"]
    assert out["evaluation_search_basis"]["result"]
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
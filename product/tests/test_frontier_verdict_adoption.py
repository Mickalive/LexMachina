"""Adopting the accepted Frontier verdicts as gate-packet input (v54 item 4).

Two human-accepted Frontier teams landed while the product cycle was in flight:
frontier-counter-label-integrity (LABEL_UNSOUND on the PRE-FIX labels) and
frontier-map-semantics (geometry FAIL with a promoted decision to KEEP the
shipped geometry and close geometry work until after the human gate). The
product's job is not to re-measure (that is Frontier's lane) but to carry both
verdicts into the packet honestly — including the fact that neither was
measured on this packet's rows.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "product") not in sys.path:
    sys.path.insert(0, str(ROOT / "product"))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import frontier_verdict_adoption as fva  # noqa: E402


def _write_counter_verdict(root: Path) -> Path:
    path = root / fva.COUNTER_LABEL_REPORT
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({
        "verdict": {
            "verdict": "LABEL_UNSOUND",
            "support_rate_primary": 0.0,
            "n_scored_primary": 7,
            "required_min_population_primary": 7,
            "secondary_verdict_replication": "LABEL_UNSOUND",
            "non_vacuity_passed": True,
            "insufficient_population_is_non_result": (
                "INSUFFICIENT_POPULATION is a NON-RESULT. It must not be read as "
                "LABEL_SOUND and must not be read as a pass of any product fix."
            ),
        },
        "coverage": {
            "every_scored_bundle_is_pre_repair": True,
            "before_after_note": "No post-repair artifact exists on the accepted mount.",
        },
        "limitations": ["verdict is about label support, not case outcomes"],
    }), encoding="utf-8")
    return path


def _write_semantics_reports(root: Path) -> None:
    base = root / fva.MAP_SEMANTICS_ROOT
    for qid in fva.MAP_SEMANTICS_BUNDLES:
        d = base / qid
        d.mkdir(parents=True, exist_ok=True)
        criteria = {
            "COHERENCE_QUERY_LANG": {"pass": False},
            "COHERENCE_QUERY_TERM": {"pass": False},
            "PROJ_RANK": {"pass": False},
            "PROJ_SPEARMAN": {"pass": False},
            "PROJ_KNN10": {"pass": False},
            "STRUCTURE_LARGEST": {"pass": True},
            "STRUCTURE_SEP": {"pass": False},
            "LABEL_CONTENT_FRACTION": {"pass": True},
            "LABEL_JACCARD": {"pass": True},
            "OUTLIER_VALIDITY": {"pass": True},
            "RELATIONS": {"pass": True},
        }
        (d / "report.json").write_text(json.dumps({
            "overall": "FAIL",
            "n_decisions": 134 if qid.startswith("de-") else 131,
            "n_clusters": 8,
            "n_relations": 25,
            "criteria": criteria,
        }), encoding="utf-8")


def test_harvest_extracts_both_verdicts_with_source_digests(tmp_path):
    root = tmp_path / "accepted"
    counter_path = _write_counter_verdict(root)
    _write_semantics_reports(root)
    snap = fva.harvest(root)
    counter = snap["frontier_counter_label_integrity"]
    assert counter["verdict"] == "LABEL_UNSOUND"
    assert counter["n_scored_primary"] == 7
    assert counter["every_scored_bundle_is_pre_repair"] is True
    assert counter["team_run_id"] == fva.COUNTER_LABEL_TEAM_RUN_ID
    semantics = snap["frontier_map_semantics"]
    assert "keep the shipped geometry" in semantics["promoted_decision"]
    assert semantics["per_bundle"]["fr-bail-entretien"]["overall"] == "FAIL"
    assert "RELATIONS" in semantics["per_bundle"]["fr-bail-entretien"]["criteria_passed"]
    digests = {Path(s["path"]).name for s in snap["source_files"]}
    assert counter_path.name in digests
    assert len(snap["source_files"]) == 1 + len(fva.MAP_SEMANTICS_BUNDLES)


def test_harvest_fails_loudly_when_the_mount_is_absent(tmp_path):
    try:
        fva.harvest(tmp_path / "nope")
    except FileNotFoundError as exc:
        assert "counter-label verdict not found" in str(exc)
    else:  # pragma: no cover - the guard must fire
        raise AssertionError("harvest must not invent a verdict from an empty mount")


def test_the_disclosure_never_lets_a_pre_fix_verdict_pass_for_this_packet(tmp_path):
    root = tmp_path / "accepted"
    _write_counter_verdict(root)
    _write_semantics_reports(root)
    snap_path = tmp_path / "snapshot.json"
    snap_path.write_text(json.dumps(fva.harvest(root)), encoding="utf-8")
    d = fva.disclosure(snap_path)
    assert d["published"] is True
    counter = d["frontier_counter_label_integrity"]
    semantics = d["frontier_map_semantics"]
    # the load-bearing honesty: both verdicts measured ELSEWHERE
    assert counter["covers_this_packet"] is False
    assert semantics["covers_this_packet"] is False
    assert counter["verdict"] == "LABEL_UNSOUND"
    assert "claims no label soundness" in counter["consequence_for_this_packet"]
    assert "INSUFFICIENT_POPULATION" in counter["insufficient_population_rule"]
    assert "non-result" in counter["insufficient_population_rule"].lower()
    assert "CLOSE geometry" in semantics["promoted_decision"]
    assert "pre-rebuild" in semantics["consequence_for_this_packet"].lower()


def test_disclosure_without_a_snapshot_says_so_instead_of_guessing(tmp_path):
    d = fva.disclosure(tmp_path / "absent.json")
    assert d["published"] is False
    assert "harvest" in d["skip_reason"]


def test_the_committed_snapshot_matches_the_accepted_runs():
    """The product-owned snapshot is committed; it must stay a faithful copy."""
    snap = fva.load()
    assert snap is not None, "committed snapshot missing — re-harvest from the mount"
    counter = snap["frontier_counter_label_integrity"]
    assert counter["team_run_id"] == "38841035773"
    assert counter["accept_commit_on_main"] == "7c960b4"
    assert counter["verdict"] == "LABEL_UNSOUND"
    assert counter["support_rate_primary"] == 0.0
    semantics = snap["frontier_map_semantics"]
    assert semantics["team_run_id"] == "38846038296"
    assert semantics["accept_commit_on_main"] == "15362f6"
    assert "keep the shipped geometry" in semantics["promoted_decision"]
    for qid in ("de-kapitalverletzung", "fr-bail-entretien", "it-responsabilita-medica"):
        assert semantics["per_bundle"][qid]["overall"] == "FAIL"


def test_the_disclosures_file_of_the_live_packet_carries_the_adoption():
    """The committed packet's disclosures.json is regenerated with the section."""
    path = ROOT / "results" / "product" / "gate_packet" / "38839347028" / "disclosures.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    adoption = data.get("frontier_verdict_adoption")
    assert adoption and adoption.get("published") is True
    assert adoption["frontier_counter_label_integrity"]["verdict"] == "LABEL_UNSOUND"
    assert adoption["frontier_counter_label_integrity"]["covers_this_packet"] is False
    assert adoption["frontier_map_semantics"]["covers_this_packet"] is False
    assert "pre-fix" in data.get("claim_ceiling", "").lower() or (
        "PRE-FIX" in data.get("claim_ceiling", ""))


def test_the_owner_card_carries_both_verdicts_and_both_limitations():
    import gate_packet as gp
    lines = gp._frontier_verdict_lines()
    text = "\n".join(lines)
    assert lines, "accepted verdicts exist; the card must carry them"
    assert "LABEL_UNSOUND" in text
    assert "NOT on this packet" in text
    assert "INSUFFICIENT_POPULATION" in text
    assert "keep the shipped geometry" in text
    assert "PRE-REBUILD" in text

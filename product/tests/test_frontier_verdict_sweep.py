"""Newest-verdict sweep for the adopted Frontier verdicts (v54 item 4 follow-up).

Factory direction v54, product backlog item (4), subsequent-measurement rule:
"If Frontier later measures THIS packet's post-D2-fix labels or the current
geometry, harvest that verdict the same way and update the snapshot; never
re-measure labels or geometry in the product lane."

This module freezes that rule in code. The sweep is read-only: it reports the
newest accepted VERIFICATION_<run_id>.json per team and whether that file
re-measured anything. A newer run id alone (operational repair, harness delta,
scope fix) must NOT obsolete the committed snapshot and must NOT flip
``covers_this_packet`` — only ``labels_rescored`` / ``bundles_remeasured``
can do that. The product lane never re-scores a label here.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "product") not in sys.path:
    sys.path.insert(0, str(ROOT / "product"))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import frontier_verdict_adoption as fva  # noqa: E402

ACCEPTED_ROOT = Path("/tmp/lex_accepted/frontier")


def _write_verification(results_dir: Path, run_id: str, doc: dict) -> Path:
    results_dir.mkdir(parents=True, exist_ok=True)
    path = results_dir / f"VERIFICATION_{run_id}.json"
    path.write_text(json.dumps(doc), encoding="utf-8")
    return path


def _snapshot_with_runs(tmp_path: Path, counter_run: str, map_run: str) -> Path:
    snap = {
        "frontier_counter_label_integrity": {"team_run_id": counter_run},
        "frontier_map_semantics": {"team_run_id": map_run},
    }
    path = tmp_path / "snap.json"
    path.write_text(json.dumps(snap), encoding="utf-8")
    return path


def test_newest_verification_wins_by_numeric_run_id(tmp_path):
    results = tmp_path / "counter" / "results"
    _write_verification(results, "38841035773", {"verdict": "LABEL_UNSOUND"})
    _write_verification(results, "38852056955", {"verdict": "LABEL_UNSOUND"})
    newest = fva._newest_verification(results)
    assert newest is not None
    assert newest["run_id"] == "38852056955"


def test_non_verification_files_are_ignored(tmp_path):
    results = tmp_path / "results"
    results.mkdir(parents=True)
    (results / "REPORT.json").write_text("{}", encoding="utf-8")
    (results / "VERIFICATION_draft.json").write_text("{}", encoding="utf-8")
    (results / "notes.txt").write_text("x", encoding="utf-8")
    assert fva._newest_verification(results) is None
    assert fva._newest_verification(tmp_path / "absent") is None


def test_sweep_without_remeasurement_keeps_snapshot_current(tmp_path):
    root = tmp_path / "accepted"
    counter_dir = root / fva.COUNTER_LABEL_RESULTS_DIR
    map_dir = root / fva.MAP_SEMANTICS_RESULTS_DIR
    _write_verification(counter_dir, "38841035773",
                         {"run_id": 38841035773, "verdict": "LABEL_UNSOUND",
                          "labels_rescored": False, "bundles_remeasured": False,
                          "rules_edited": False})
    # A newer operational-repair verification that re-measured nothing.
    _write_verification(counter_dir, "38852056955",
                         {"run_id": 38852056955, "verdict": "LABEL_UNSOUND",
                          "labels_rescored": False, "bundles_remeasured": False,
                          "rules_edited": False})
    _write_verification(map_dir, "38846038296", {"run_id": 38846038296})
    snap = _snapshot_with_runs(tmp_path, "38841035773", "38846038296")
    out = fva.sweep(root, snap)
    counter = out["frontier_counter_label_integrity"]
    assert counter["newest_verification_run_id"] == "38852056955"
    assert counter["re_measured"] is False
    assert counter["snapshot_current"] is True
    assert counter["covers_this_packet"] is False
    assert out["covers_this_packet"] is False
    assert out["action_required"] is False


def test_sweep_flags_a_verification_that_remeasured(tmp_path):
    root = tmp_path / "accepted"
    counter_dir = root / fva.COUNTER_LABEL_RESULTS_DIR
    map_dir = root / fva.MAP_SEMANTICS_RESULTS_DIR
    _write_verification(counter_dir, "38852056955",
                         {"run_id": 38852056955, "verdict": "LABEL_UNSOUND",
                          "labels_rescored": True, "bundles_remeasured": True,
                          "rules_edited": False})
    _write_verification(map_dir, "38846038296", {"run_id": 38846038296})
    snap = _snapshot_with_runs(tmp_path, "38841035773", "38846038296")
    out = fva.sweep(root, snap)
    assert out["frontier_counter_label_integrity"]["re_measured"] is True
    assert out["frontier_counter_label_integrity"]["snapshot_current"] is False
    assert out["action_required"] is True
    # Even then the product does not claim coverage: only a harvest of a
    # verification that measured THIS packet's bundles could set that, and
    # the sweep itself never re-measures.
    assert out["covers_this_packet"] is False


def test_sweep_without_snapshot_reports_skip_not_coverage(tmp_path):
    out = fva.sweep(tmp_path, tmp_path / "no-such-snapshot.json")
    assert out["ok"] is False
    assert "skip_reason" in out
    assert "covers_this_packet" not in out


@pytest.mark.skipif(not ACCEPTED_ROOT.is_dir(),
                    reason="accepted Frontier mounts not present")
def test_sweep_against_the_live_accepted_mounts():
    """The live check behind this cycle's report: the newest accepted
    counter-label verification re-measured nothing, so the committed snapshot
    (adopted at 38841035773) is still current and covers_this_packet stays
    False. Map-semantics newest verification is the adopted run itself."""
    out = fva.sweep(ACCEPTED_ROOT)
    counter = out["frontier_counter_label_integrity"]
    assert counter["newest_verification_run_id"] is not None
    assert int(counter["newest_verification_run_id"]) >= int(
        fva.COUNTER_LABEL_TEAM_RUN_ID)
    assert counter["labels_rescored"] is False
    assert counter["bundles_remeasured"] is False
    assert counter["snapshot_current"] is True
    assert counter["covers_this_packet"] is False
    assert out["frontier_map_semantics"]["newest_verification_run_id"] == (
        fva.MAP_SEMANTICS_TEAM_RUN_ID)
    assert out["action_required"] is False

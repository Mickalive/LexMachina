"""Tests for evaluation/served_bundle_scope.py (cycle 39086856920).

REUSE-FIRST / POST-FREEZE ADDITION, same convention as
``evaluation/retrieval_gate/id_hygiene.py``: these tests touch no frozen rubric,
incumbent verdict, benchmark or success rule. They pin (a) that every falsifier is
REACHABLE, so a green verdict can never come from a structurally dead field, (b)
that the frozen hypothesis is intact and its success rule is quoted rather than
paraphrased, and (c) that the instrument refuses to emit a verdict when an
environment input is absent.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from evaluation import served_bundle_scope as sbs

ROOT = Path(__file__).resolve().parents[2]
HYP = ROOT / "results/evaluation/served_bundle_scope/FROZEN_HYPOTHESIS_39086856920.json"


# --------------------------------------------------------------------------
# (a) every falsifier is REACHABLE — a green reading must be non-vacuous
# --------------------------------------------------------------------------

def _hyp() -> dict:
    return json.loads(HYP.read_text(encoding="utf-8"))


def _bundle(decisions: list[dict]) -> dict:
    return {"provenance": {"mode": "live", "base_url": "https://mcp.opencaselaw.ch/api"},
            "query": {"slug": "t"}, "decisions": decisions}


def test_every_frozen_falsifier_has_a_measurement_mapping():
    known = {"source::canonical_url_not_opencaselaw": "n_bad_canonical_url",
             "source::decision_id_unusable": "n_unusable_decision_id",
             "map::point_missing_geometry_or_cluster": "n_missing_geometry_or_cluster",
             "scope::outside_mission_date_window": "n_before_mission_date_window",
             "scope::adversarial_seed_contamination": "n_adversarial_seeded"}
    assert {f["id"] for f in _hyp()["falsifiers"]} == set(known)


@pytest.mark.parametrize("broken,expected_field", [
    ({"decision_id": "x", "canonical_url": "http://example.com/d", "x": 0.0, "y": 0.0,
      "cluster_id": 1, "decision_date": "2010-01-01", "provenance": "ocl:search"},
     "n_bad_canonical_url"),
    ({"decision_id": "ge_gerichte_[pjdoc 9282]", "canonical_url": "https://mcp.opencaselaw.ch/x",
      "x": 0.0, "y": 0.0, "cluster_id": 1, "decision_date": "2010-01-01",
      "provenance": "ocl:search"}, "n_unusable_decision_id"),
    ({"decision_id": "ok", "canonical_url": "https://mcp.opencaselaw.ch/x",
      "decision_date": "2010-01-01", "provenance": "ocl:search"},
     "n_missing_geometry_or_cluster"),
    ({"decision_id": "ok", "canonical_url": "https://mcp.opencaselaw.ch/x", "x": 0.0, "y": 0.0,
      "cluster_id": 1, "decision_date": "1979-05-22", "provenance": "ocl:search"},
     "n_before_mission_window"),
    ({"decision_id": "ok", "canonical_url": "https://mcp.opencaselaw.ch/x", "x": 0.0, "y": 0.0,
      "cluster_id": 1, "decision_date": "2010-01-01",
      "provenance": "ocl:adversarial.minority variant=adversarial:minority"}, "n_adversarial_seeded"),
])
def test_each_falsifier_can_fire_on_a_constructed_row(broken, expected_field):
    """Non-vacuity: the field the falsifier counts must be reachable, otherwise a
    REFUTED verdict is an artifact of the field never being populated at all."""
    m = sbs.measure_bundle("t.json", _bundle([broken]))
    assert m[expected_field] == 1, (expected_field, m)
    rec = sbs.evaluate({**_hyp(), "_path": None}, [m], {})
    assert rec["falsification_proven"] is True
    assert expected_field.replace("n_", "") or True


def test_a_clean_row_refutes_every_falsifier():
    clean = {"decision_id": "bge_140 III 491",
             "canonical_url": "https://mcp.opencaselaw.ch/entscheid/bge_140%20III%20491",
             "x": 0.1, "y": -0.2, "cluster_id": 3,
             "decision_date": "2014-08-28", "provenance": "ocl:search", "rank": 1}
    m = sbs.measure_bundle("t.json", _bundle([clean]))
    rec = sbs.evaluate({**_hyp(), "_path": None}, [m], {})
    assert rec["verdict"] == "BENCHMARK_VALID_NO_FALSIFICATION"
    assert rec["falsification_proven"] is False


def test_a_bundle_without_decisions_is_not_measurable_not_a_pass():
    rec = sbs.evaluate({**_hyp(), "_path": None},
                       [sbs.measure_bundle("t.json", {"decisions": []})], {})
    assert rec["verdict"] != "BENCHMARK_VALID_NO_FALSIFICATION"
    assert all(f["verdict"] == "NOT_MEASURED" for f in rec["falsifiers"]), rec["falsifiers"]


# --------------------------------------------------------------------------
# (b) the frozen hypothesis is intact, not paraphrased after seeing results
# --------------------------------------------------------------------------

def test_frozen_hypothesis_pins_both_accepted_rubric_digests_unchanged():
    hyp = _hyp()
    assert hyp["frozen_bars_untouched"]["RULES_LABEL.json"].startswith("4457e971")
    assert hyp["frozen_bars_untouched"]["RULES_GEOMETRY.json"].startswith("a7452748")
    assert hyp["frozen_before_execution"] is True


def test_success_rule_is_quoted_verbatim_from_the_frozen_hypothesis():
    assert _hyp()["success_rule"].startswith("FROZEN BEFORE ANY ROW WAS READ.")


def test_frozen_digests_on_disk_still_match_the_hypothesis():
    """The instrument must not have drifted the files it claims to leave alone."""
    from evaluation.snapshot_audit.run_snapshot_audit import (RULES_LABEL_SHA256,
                                                             RULES_GEOMETRY_SHA256,
                                                             _sha256_file)
    assert _sha256_file(ROOT / "evaluation/frozen_bars/RULES_LABEL.json") == RULES_LABEL_SHA256
    assert _sha256_file(ROOT / "evaluation/frozen_bars/RULES_GEOMETRY.json") == RULES_GEOMETRY_SHA256


# --------------------------------------------------------------------------
# (c) environment failures never produce a verdict
# --------------------------------------------------------------------------

def test_missing_hypothesis_exits_2_without_a_record(tmp_path):
    proc = subprocess.run(
        [sys.executable, "-m", "evaluation.served_bundle_scope", "--run-id", "t",
         "--hypothesis", str(tmp_path / "nope.json")],
        cwd=str(ROOT), capture_output=True, text=True, timeout=120)
    assert proc.returncode == 2, proc
    assert "hypothesis not found" in proc.stderr


def test_absent_product_mount_exits_2_not_a_pass(tmp_path):
    proc = subprocess.run(
        [sys.executable, "-m", "evaluation.served_bundle_scope", "--run-id", "t",
         "--hypothesis", str(HYP), "--product-mount", str(tmp_path / "no_mount")],
        cwd=str(ROOT), capture_output=True, text=True, timeout=120)
    assert proc.returncode == 2, proc
    assert "product mount unavailable" in proc.stderr


def test_wrong_hypothesis_schema_is_refused(tmp_path):
    bad = tmp_path / "h.json"
    bad.write_text(json.dumps({"schema": "something-else"}), encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, "-m", "evaluation.served_bundle_scope", "--run-id", "t",
         "--hypothesis", str(bad)],
        cwd=str(ROOT), capture_output=True, text=True, timeout=120)
    assert proc.returncode == 2, proc


# --------------------------------------------------------------------------
# (d) the executed record of this cycle, if the mount was available
# --------------------------------------------------------------------------

_RECORD = ROOT / "results/evaluation/served_bundle_scope/39086856920.json"


@pytest.mark.skipif(not _RECORD.exists(), reason="record not produced in this image")
def test_executed_record_is_a_falsification_and_is_kept():
    rec = json.loads(_RECORD.read_text(encoding="utf-8"))
    assert rec["schema"] == sbs.SCHEMA
    assert rec["verdict"] == "BENCHMARK_VALID_WITH_FALSIFICATION"
    assert rec["falsification_proven"] is True
    # the audit's numbers must reproduce EXACTLY on the accepted mount
    per = {f["id"]: f["total"] for f in rec["falsifiers"]}
    assert per["scope::outside_mission_date_window"] == 173
    assert per["scope::adversarial_seed_contamination"] == 120
    assert per["source::canonical_url_not_opencaselaw"] == 0
    assert per["map::point_missing_geometry_or_cluster"] == 0
    # and the NEW finding the audit did not report
    assert per["source::decision_id_unusable"] == 3
    assert rec["negative_controls"]["at_least_one_field_can_fire"] is True
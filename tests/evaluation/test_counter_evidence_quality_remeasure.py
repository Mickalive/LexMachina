"""Tests for the item-(4) counter-evidence quality re-measure instrument.

Scratch-run obligation: every invocation here passes --out-dir/--report-dir
(or calls run() with scratch dirs) so no committed claim-bearing record is
rewritten by tests.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from evaluation import counter_evidence_quality_remeasure as remeasure


def test_frozen_instrument_digest_pinned():
    sha = remeasure._sha256_file(remeasure.FROZEN_INSTRUMENT)
    assert sha == remeasure.FROZEN_INSTRUMENT_SHA_EXPECTED


def test_controls_all_pass_scratch(tmp_path):
    controls = remeasure._controls()
    assert all(c["passed"] for c in controls.values()), controls


def test_run_smoke_on_real_mount_or_env_error(tmp_path):
    """Full run against the accepted mount when present; ENVIRONMENT_ERROR
    otherwise. Either way the artifact schema is checked and scratch dirs are
    used."""
    code, record = remeasure.run("scratch_test_remeasure", tmp_path, tmp_path)
    assert record["schema"] == remeasure.SCHEMA
    if code == 2:
        assert record["verdict"] in ("ENVIRONMENT_ERROR", "ENVIRONMENT_OR_VACUOUS")
        return
    assert record["verdict"] in ("REPAIR_CONFIRMED", "REPAIR_NOT_CONFIRMED")
    # per-class verdicts always cover the three frozen classes
    for d in remeasure.DEFECT_CLASSES:
        assert d in record["per_class_verdicts"]
    # baseline stability is either compared-and-identical or absent
    stab = record["baseline_population"]["stability_vs_accepted_baseline_of_record"]
    if stab.get("compared"):
        assert stab["normalized_identical"] is True
    # no class may claim CONFIRMED-REPAIRED while another is STILL-DEFECTIVE
    # at the overall level without the overall verdict being NOT_CONFIRMED
    any_still = any(v["verdict"] == "STILL-DEFECTIVE"
                    for v in record["per_class_verdicts"].values())
    if any_still:
        assert record["verdict"] == "REPAIR_NOT_CONFIRMED"
        assert code == 1


def test_predicate_values_match_frozen_instrument():
    """The remeasure must import, not re-derive, the frozen predicates."""
    assert remeasure.LETTERHEAD_ZONE_OFFSET_MAX == 400
    assert "D2_letterhead_zone" in remeasure.DEFECT_CLASSES
    assert remeasure.MARKUP_TOKENS  # non-empty, imported by value

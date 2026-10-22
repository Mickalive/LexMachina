"""Tests for evaluation/remedy_a_landed_probe.py and the 39275520116 extension freeze.

REUSE-FIRST: these tests touch no frozen rubric, incumbent verdict, benchmark
or success rule. They pin (a) the extension freeze artifacts and their internal
digest pin, (b) that the landed-probe classifier is REACHABLE in both
directions on synthetic input, so a green reading can never come from a
structurally dead test, (c) that an absent environment input yields exit 2 and
never a landing verdict, and (d) the non-duplication premise of this cycle:
no prior mapping_free_recall_falsifier record measured packet 39275520116.

No network is used anywhere. Mount-dependent cases skip cleanly when the
ephemeral accepted dispatch mount is absent.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from evaluation import remedy_a_landed_probe as probe

ROOT = Path(__file__).resolve().parents[2]
HYP = ROOT / "evaluation/MAPPING_FREE_39275520116_EXTENSION_HYPOTHESIS_V1.json"
FREEZE = ROOT / "evaluation/MAPPING_FREE_39275520116_EXTENSION_FREEZE_RECORD_V1.json"
FIXTURE = ROOT / "results/evaluation/counter_probe_repair_verification/39687372110.json"
MFR_DIR = ROOT / "results/evaluation/mapping_free_recall_falsifier"
MOUNT = Path("/tmp/lex_accepted/product")

MOUNT_PRESENT = (MOUNT / "results/product").is_dir()


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# --------------------------------------------------------------------------- #
# (a) freeze artifacts and their digest pin
# --------------------------------------------------------------------------- #
def test_freeze_artifacts_exist_and_pin_matches():
    assert HYP.is_file() and FREEZE.is_file()
    freeze = json.loads(FREEZE.read_text(encoding="utf-8"))
    assert freeze["hypothesis_sha256"] == _sha(HYP)
    assert freeze["frozen_before_claim_bearing_execution"] is True
    assert freeze["instrument_sha256"] == _sha(ROOT / "evaluation/mapping_free_recall_falsifier.py")
    # frozen bars re-hash unchanged (standing orders)
    rules = json.loads((ROOT / "evaluation/frozen_bars/RULES_LABEL.json").read_text(encoding="utf-8"))
    assert rules.get("rubric", {}).get("scored_statuses")
    assert _sha(ROOT / "evaluation/frozen_bars/RULES_LABEL.json") == \
        "4457e971df3dc5d10af2a727aa675afc15a15564c18eed4cede0af5eb41b4608"
    assert _sha(ROOT / "evaluation/frozen_bars/RULES_GEOMETRY.json") == \
        "a7452748d40c511a14a1c7848ece5fe7f8f8901cc30f45a66918c89eb593a633"


def test_freeze_names_the_never_measured_packet():
    freeze = json.loads(FREEZE.read_text(encoding="utf-8"))
    assert freeze["frozen_sample"]["packet"] == "39275520116"
    pins = freeze["frozen_sample"]["mount_input_digests_before_execution"]
    assert sum(1 for k in pins if k.endswith(".bundle.json")) == 3


# --------------------------------------------------------------------------- #
# (b) classifier reachable in both directions on SYNTHETIC input
# --------------------------------------------------------------------------- #
def test_classifier_detects_landed_remedy():
    baseline = ["citation removed retrieved fuer A B", "x y z"]
    fixed = ["fuer arbeitgeber nicht A B", "x y z"]
    assert probe.classify(fixed, baseline, fixed) == "FIXED_ARM_REPRODUCED"


def test_classifier_detects_not_landed():
    baseline = ["citation removed retrieved fuer A B", "x y z"]
    fixed = ["fuer arbeitgeber nicht A B", "x y z"]
    assert probe.classify(baseline, baseline, fixed) == "BASELINE_ARM_REPRODUCED"


def test_classifier_flags_unexpected_output():
    baseline = ["citation removed retrieved fuer A B"]
    fixed = ["fuer arbeitgeber nicht A B"]
    assert probe.classify(["totally other probe"], baseline, fixed) == "UNEXPECTED_PLANNER_OUTPUT"


def test_classifier_noop_when_arms_equal():
    arm = ["same probe"]
    assert probe.classify(arm, arm, arm) == "BASELINE_EQUALS_FIXED_NOOP"


# --------------------------------------------------------------------------- #
# (c) absent environment input -> exit 2, never a landing verdict
# --------------------------------------------------------------------------- #
def test_absent_fixture_yields_environment_exit(tmp_path: Path):
    code, out = probe.run(tmp_path / "missing.json", tmp_path)
    assert code == 2
    assert out["verdict"] == "ENVIRONMENT_OR_VACUOUS"


def test_empty_fixture_yields_environment_exit(tmp_path: Path):
    fx = tmp_path / "fixture.json"
    fx.write_text(json.dumps({"bundles": []}), encoding="utf-8")
    code, out = probe.run(fx, tmp_path)
    assert code == 2
    assert out["verdict"] == "ENVIRONMENT_OR_VACUOUS"


# --------------------------------------------------------------------------- #
# (d) non-duplication premise: 39275520116 never previously measured
# --------------------------------------------------------------------------- #
def test_no_prior_falsifier_run_measured_39275520116():
    prior = []
    for f in sorted(MFR_DIR.glob("*.json")):
        rec = json.loads(f.read_text(encoding="utf-8"))
        if "39275520116" in (rec.get("packets_measured") or []):
            prior.append(f.name)
    # the run-39725464259 record itself, once written, is EXPECTED here; only
    # pre-existing records may not cover the packet
    prior = [n for n in prior if not n.startswith("39725464259")]
    assert prior == [], f"packet 39275520116 was already measured by {prior}"


# --------------------------------------------------------------------------- #
# mount-dependent: the probe runs end-to-end and never claims a bar
# --------------------------------------------------------------------------- #
@pytest.mark.skipif(not MOUNT_PRESENT, reason="accepted product mount absent")
def test_probe_runs_on_mount_without_bar_claims():
    code, out = probe.run(FIXTURE, MOUNT)
    assert out["schema"] == "lex-evaluation-remedy-a-landed-probe/1"
    assert out["verdict"] in (
        "REMEDY_A_LANDED", "REMEDY_A_NOT_LANDED",
        "REMEDY_A_UNEXPECTED_PLANNER_OUTPUT", "REMEDY_A_MIXED_REPRODUCTION",
        "ENVIRONMENT_OR_VACUOUS")
    assert "human_gate_ready stays false" in out["claim_ceiling"]
    if out["verdict"] != "ENVIRONMENT_OR_VACUOUS":
        assert code in (0, 1)
        assert out["n_measured"] >= 1

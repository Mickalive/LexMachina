"""Tests for the v62 ordered-item-(1)/(2) instruments of cycle 39813664201.

REUSE-FIRST and fail-closed: these tests touch no frozen rubric, bar or verdict
contract.  They pin (a) the freeze artifacts of the two new instruments and
their internal digest pins, (b) that the shipped-planner remedy verification
records a claimed verdict only with matching exit code and full control/gate
disclosure, (c) that a missing environment input yields exit 2 and never a
product verdict, and (d) that the coverage cross-check's union recomputation
is non-vacuous on synthetic input.

No network is used anywhere.  Mount-dependent cases skip cleanly when the
ephemeral accepted dispatch mount is absent.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from evaluation import coverage_remediation_crosscheck as crc
from evaluation import shipped_planner_remedy_verification as sprv

ROOT = Path(__file__).resolve().parents[2]
SPRV_HYP = ROOT / "evaluation/SHIPPED_PLANNER_REMEDY_VERIFICATION_HYPOTHESIS_V1.json"
SPRV_FREEZE = ROOT / "evaluation/SHIPPED_PLANNER_REMEDY_VERIFICATION_FREEZE_RECORD_V1.json"
CRC_HYP = ROOT / "evaluation/COVERAGE_REMEDIATION_CROSSCHECK_HYPOTHESIS_V1.json"
CRC_FREEZE = ROOT / "evaluation/COVERAGE_REMEDIATION_CROSSCHECK_FREEZE_RECORD_V1.json"
SPRV_RESULT = ROOT / "results/evaluation/shipped_planner_remedy_verification/39813664201.json"
CRC_RESULT = ROOT / "results/evaluation/coverage_remediation_crosscheck/39813664201.json"
MOUNT = Path("/tmp/lex_accepted/product")

MOUNT_PRESENT = (MOUNT / "results/product").is_dir()


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# --------------------------------------------------------------------------- #
# (a) freeze artifacts and internal digest pins
# --------------------------------------------------------------------------- #


def test_shipped_planner_freeze_pins_match_disk_bytes():
    freeze = json.loads(SPRV_FREEZE.read_text(encoding="utf-8"))
    for rel, expected in freeze["pins"].items():
        path = ROOT / rel
        assert path.is_file(), f"pinned file absent: {rel}"
        assert _sha(path) == expected, f"pin drift: {rel}"


def test_coverage_freeze_pins_match_disk_bytes():
    freeze = json.loads(CRC_FREEZE.read_text(encoding="utf-8"))
    for rel, expected in freeze["pins"].items():
        path = ROOT / rel
        assert path.is_file(), f"pinned file absent: {rel}"
        assert _sha(path) == expected, f"pin drift: {rel}"


def test_hypotheses_frozen_before_execution_and_run_id_pinned():
    for hyp_path, freeze_path in ((SPRV_HYP, SPRV_FREEZE), (CRC_HYP, CRC_FREEZE)):
        hyp = json.loads(hyp_path.read_text(encoding="utf-8"))
        freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
        assert hyp["frozen_before_claim_bearing_execution"] is True
        assert hyp["run_id_of_record"] == "39813664201"
        assert freeze["run_id_of_record"] == "39813664201"
        assert freeze["frozen_before_claim_bearing_execution"] is True


def test_shipped_planner_hypothesis_carries_seq2_disclosure():
    hyp = json.loads(SPRV_HYP.read_text(encoding="utf-8"))
    amend = hyp["seq2_amendment"]
    assert "attempt 1" in amend["trigger"]
    assert "ENVIRONMENT_OR_VACUOUS" in amend["trigger"]
    assert "PRE-REMEDY-EMULATED" in amend["corrected_predicate_C2s"]


# --------------------------------------------------------------------------- #
# (b) recorded claim-bearing results are internally consistent
# --------------------------------------------------------------------------- #


@pytest.mark.skipif(not SPRV_RESULT.is_file(), reason="cycle result not present")
def test_shipped_planner_result_verdict_matches_exit_code_and_discloses_everything():
    rec = json.loads(SPRV_RESULT.read_text(encoding="utf-8"))
    assert rec["verdict"] == "SHIPPED_PLANNER_MATCHES_VERIFIED_REMEDY"
    assert rec["exit_code"] == 0
    assert all(g["passed"] for g in rec["gates"].values())
    assert all(c["holds"] for c in rec["controls"].values())
    assert rec["n_measured"] == 14
    assert rec["network_calls"] == 0
    assert rec["pins_before"]["all_ok"] is True
    assert rec["pins_after"]["all_ok"] is True
    assert rec["claim_ceiling"]  # ceiling always published


@pytest.mark.skipif(not CRC_RESULT.is_file(), reason="cycle result not present")
def test_coverage_result_verdict_matches_exit_code_and_discloses_everything():
    rec = json.loads(CRC_RESULT.read_text(encoding="utf-8"))
    assert rec["verdict"] == "COVERAGE_EVIDENCE_REPRODUCES"
    assert rec["exit_code"] == 0
    assert all(g["passed"] for g in rec["gates"].values())
    assert all(c["holds"] for c in rec["controls"].values())
    assert rec["fresh_offline"]["n_network_calls"] == 0
    assert rec["pins_before"]["all_ok"] is True
    assert rec["pins_after"]["all_ok"] is True
    # reach LOSS is falsification: fresh union must supert the committed offline union
    assert not rec["gates"]["V3_reach_unions_recompute_and_offline_replay_supersets_committed_reach"][
        "missing_vs_committed_offline"]


# --------------------------------------------------------------------------- #
# (c) environment failure is never a product verdict
# --------------------------------------------------------------------------- #


def test_shipped_planner_missing_inputs_is_exit2_never_a_verdict(tmp_path):
    code, rec = sprv.run("39813664201", tmp_path / "no_such_mount")
    assert code == 2
    assert rec["verdict"] == "ENVIRONMENT_OR_VACUOUS"


def test_shipped_planner_wrong_run_id_is_exit2():
    if not MOUNT_PRESENT:
        pytest.skip("accepted product mount absent")
    code, rec = sprv.run("00000000000", MOUNT)
    assert code == 2
    assert rec["verdict"] == "ENVIRONMENT_OR_VACUOUS"


def test_coverage_wrong_run_id_is_exit2():
    if not MOUNT_PRESENT:
        pytest.skip("accepted product mount absent")
    code, rec = crc.run("00000000000", MOUNT)
    assert code == 2
    assert rec["verdict"] == "ENVIRONMENT_OR_VACUOUS"


# --------------------------------------------------------------------------- #
# (d) union recomputation is non-vacuous on synthetic input
# --------------------------------------------------------------------------- #


def test_recompute_union_is_exact_membership():
    record = {"per_text": [
        {"all_frozen_ids_reached": ["a", "b"]},
        {"all_frozen_ids_reached": ["b", "c"]},
        {"all_frozen_ids_reached": []},
    ]}
    assert crc.recompute_union(record) == ["a", "b", "c"]


def test_recompute_union_empty_is_empty_not_crash():
    assert crc.recompute_union({}) == []


def test_preremedy_key_terms_ranks_by_frequency_desc_then_alpha():
    class FakeProduct:
        answer_stop = frozenset({"the", "and"})
        tokenize = staticmethod(lambda text: text.lower().split())

    # counts: zahlung=2, rericht=2, alpha=2, beta=1 -> ties broken alphabetically
    out = sprv.preremedy_key_terms(
        FakeProduct(), "Zahlung Zahlung Rericht Rericht Alpha Alpha Beta", limit=3)
    assert out == ["alpha", "rericht", "zahlung"]

"""Tests for the run-39820650174 resume verification and degradation cross-check.

REUSE-FIRST and fail-closed.  These tests touch no frozen rubric, bar or verdict
contract.  They pin (a) both new freeze records and every digest they name,
(b) the fail-closed exit-2 contract for a wrong run id or an absent mount,
(c) the non-vacuity of the frozen predicates via in-memory mutations, and
(d) that any recorded result claims a verdict only with a matching exit code,
all frozen gates passing and every control holding.

No network is used anywhere.  The product mount is ephemeral; mount-dependent
cases skip cleanly when it is absent.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from evaluation import degradation_disclosure_crosscheck as ddc
from evaluation import degradation_disclosure_crosscheck_v2 as ddc2
from evaluation import operational_resume_verification as orv

ROOT = Path(__file__).resolve().parents[2]
MOUNT = Path("/tmp/lex_accepted/product")
MOUNT_PRESENT = (MOUNT / "results/product").is_dir()

RESUME_HYP = ROOT / "evaluation/OPERATIONAL_RESUME_39820650174_HYPOTHESIS_V1.json"
RESUME_FREEZE = ROOT / "evaluation/OPERATIONAL_RESUME_39820650174_FREEZE.json"
RESUME_RESULT = ROOT / "results/evaluation/operational_resume/39820650174.json"
DDC_HYP = ROOT / "evaluation/DEGRADATION_DISCLOSURE_CROSSCHECK_HYPOTHESIS_V1.json"
DDC_FREEZE = ROOT / "evaluation/DEGRADATION_DISCLOSURE_CROSSCHECK_FREEZE_RECORD_V1.json"
DDC_RESULT = ROOT / "results/evaluation/degradation_disclosure_crosscheck/39820650174.json"
DDC2_HYP = ROOT / "evaluation/DEGRADATION_DISCLOSURE_CROSSCHECK_HYPOTHESIS_V2.json"
DDC2_FREEZE = ROOT / "evaluation/DEGRADATION_DISCLOSURE_CROSSCHECK_FREEZE_RECORD_V2.json"
DDC2_RESULT = ROOT / "results/evaluation/degradation_disclosure_crosscheck/39820650174_v2.json"

CODE = "e_EMISSION_WRITER_ABORT"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# --------------------------------------------------------------------------- #
# (a) freeze artifacts and internal digest pins
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("freeze_path", [RESUME_FREEZE, DDC_FREEZE, DDC2_FREEZE])
def test_freeze_pins_match_disk_bytes(freeze_path: Path):
    freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
    for rel, expected in freeze["pins"].items():
        path = ROOT / rel
        assert path.is_file(), f"pinned file absent: {rel}"
        assert _sha(path) == expected, f"pin drift: {rel}"


def test_freeze_records_name_this_run_and_its_hypotheses():
    r = json.loads(RESUME_FREEZE.read_text(encoding="utf-8"))
    d = json.loads(DDC_FREEZE.read_text(encoding="utf-8"))
    assert r["run_id_of_record"] == "39820650174"
    assert d["run_id_of_record"] == "39820650174"
    assert r["direction_version"] == d["direction_version"] == 62
    assert r["pins"]["evaluation/OPERATIONAL_RESUME_39820650174_HYPOTHESIS_V1.json"] == _sha(RESUME_HYP)
    assert d["pins"]["evaluation/DEGRADATION_DISCLOSURE_CROSSCHECK_HYPOTHESIS_V1.json"] == _sha(DDC_HYP)
    d2 = json.loads(DDC2_FREEZE.read_text(encoding="utf-8"))
    assert d2["run_id_of_record"] == "39820650174"
    assert d2["pins"]["evaluation/DEGRADATION_DISCLOSURE_CROSSCHECK_HYPOTHESIS_V2.json"] == _sha(DDC2_HYP)
    assert d2["pins"]["results/evaluation/degradation_disclosure_crosscheck/39820650174.json"] == _sha(DDC_RESULT)


@pytest.mark.skipif(not MOUNT_PRESENT, reason="accepted product mount absent")
def test_product_pins_in_freezes_match_mount():
    for freeze_path in (RESUME_FREEZE, DDC_FREEZE, DDC2_FREEZE):
        freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
        for rel, expected in freeze.get("product_pins", {}).items():
            path = MOUNT / rel
            assert path.is_file(), f"product pin absent: {rel}"
            assert _sha(path) == expected, f"product pin drift: {rel}"


# --------------------------------------------------------------------------- #
# (b) fail-closed entry contract
# --------------------------------------------------------------------------- #


def test_wrong_run_id_is_exit_2_for_both_instruments():
    r_code, r_rec = orv.run("123", MOUNT)
    d_code, d_rec = ddc.run("123", MOUNT)
    d2_code, d2_rec = ddc2.run("123", MOUNT)
    assert r_code == d_code == d2_code == 2
    assert r_rec["verdict"] == d_rec["verdict"] == d2_rec["verdict"] == "ENVIRONMENT_OR_VACUOUS"
    assert r_rec["exit_code"] == d_rec["exit_code"] == d2_rec["exit_code"] == 2


def test_absent_mount_is_exit_2_for_both_instruments():
    missing = Path("/nonexistent/lexmachina-accepted-mount")
    r_code, r_rec = orv.run("39820650174", missing)
    d_code, d_rec = ddc.run("39820650174", missing)
    d2_code, d2_rec = ddc2.run("39820650174", missing)
    assert r_code == d_code == d2_code == 2
    assert r_rec["verdict"] == d_rec["verdict"] == d2_rec["verdict"] == "ENVIRONMENT_OR_VACUOUS"


# --------------------------------------------------------------------------- #
# (c) frozen predicates are non-vacuous
# --------------------------------------------------------------------------- #


def _fallback(disclosure="empty counter set is 'not measured', never 'no contrary authority exists'"):
    return {
        "answer": {
            "status": "degraded",
            "degradation": {
                "code": CODE,
                "stage": "generative_writer",
                "disclosure": disclosure,
            },
        },
        "provenance": {
            "generative_audit": {
                "degraded": True,
                "provider_error": "RuntimeError: boom",
                "emission_status": "WRITER_ABORT",
                "degradation": {"code": CODE},
            }
        },
        "decisions": [{"decision_id": "a"}],
    }


def _visibility(degraded=True, code=CODE):
    return {"degraded": degraded, "degradation_code": code, "visible": True}


def _degraded_pass():
    return {
        "answer": _fallback()["answer"],
        "provenance": {
            "adversarial_retrieval": {
                "degraded": True,
                "degradation_code": CODE,
                "adversarial_status": "DEGRADED_WRITER_ABORT",
                "disclosure": "measurement gap, not evidence that no contrary authority exists",
                "network_calls": 0,
            }
        },
        "decisions": [{"decision_id": "a"}],
    }


def _vacuous_pass():
    return {
        "answer": _fallback()["answer"],
        "provenance": {
            "adversarial_retrieval": {
                "skipped": True,
                "skip_reason": "vacuous_pass: no usable legal vocabulary",
                "adversarial_status": "VACUOUS_WRITER_ABORT",
                "degraded": True,
                "degradation_code": CODE,
                "disclosure": "measurement gap",
            }
        },
        "decisions": [{"decision_id": "a"}],
    }


def _healthy_pass():
    return {
        "answer": {"status": "ready"},
        "provenance": {
            "adversarial_retrieval": {
                "degraded": False,
                "degradation_code": None,
                "adversarial_status": "MEASURED",
            }
        },
        "decisions": [{"decision_id": "b"}],
    }


def test_g1_detects_a_deleted_answer_field():
    f = _fallback()
    assert ddc.predicate_g1(f, f, "RuntimeError: boom", _visibility())["passed"] is True
    tampered = json.loads(json.dumps(f))
    del tampered["answer"]["degradation"]
    assert ddc.predicate_g1(tampered, f, "RuntimeError: boom", _visibility())["passed"] is False


def test_g2_detects_a_measured_relabel():
    f = _fallback()
    p = _degraded_pass()
    assert ddc.predicate_g2(p, f, _visibility())["passed"] is True
    tampered = json.loads(json.dumps(p))
    tampered["provenance"]["adversarial_retrieval"].update(
        {"degraded": False, "degradation_code": None, "adversarial_status": "MEASURED"}
    )
    assert ddc.predicate_g2(tampered, f, _visibility())["passed"] is False


def test_g3_detects_a_measured_relabel_on_a_vacuous_pass():
    f = _fallback()
    v = _vacuous_pass()
    assert ddc.predicate_g3(v, f)["passed"] is True
    tampered = json.loads(json.dumps(v))
    tampered["provenance"]["adversarial_retrieval"]["adversarial_status"] = "MEASURED"
    assert ddc.predicate_g3(tampered, f)["passed"] is False


def test_g1_v2_gates_the_stage_without_the_complete_bundle_visibility_flag():
    f = _fallback()
    vis = {"degraded": True, "degradation_code": CODE, "visible": False}
    gate = ddc2.predicate_g1_v2(f, f, "RuntimeError: boom", vis)
    assert gate["passed"] is True
    assert gate["stage_observation"]["observed"] is False
    tampered = json.loads(json.dumps(f))
    del tampered["answer"]["degradation"]
    assert ddc2.predicate_g1_v2(tampered, f, "RuntimeError: boom", vis)["passed"] is False


def test_v1_result_is_still_preserved_verbatim():
    if not DDC_RESULT.is_file():
        pytest.skip("V1 result absent (pre-execution tree)")
    assert _sha(DDC_RESULT) == ddc2.V1_RESULT_SHA
    rec = json.loads(DDC_RESULT.read_text(encoding="utf-8"))
    assert rec["verdict"] == "DEGRADATION_DISCLOSURE_GAP"
    assert rec["exit_code"] == 1


def test_g4_detects_an_injected_abort_on_the_healthy_leg():
    h = _healthy_pass()
    assert ddc.predicate_g4(h, h, _visibility(False, None))["passed"] is True
    tampered = json.loads(json.dumps(h))
    tampered["provenance"]["adversarial_retrieval"].update({
        "degraded": True, "degradation_code": CODE,
        "adversarial_status": "DEGRADED_WRITER_ABORT",
    })
    assert ddc.predicate_g4(tampered, h, _visibility(True))["passed"] is False


# --------------------------------------------------------------------------- #
# (c') resume verification predicates are non-vacuous
# --------------------------------------------------------------------------- #


def test_rehash_detects_a_planted_drift():
    pins = {"evaluation/DEGRADATION_DISCLOSURE_CROSSCHECK_HYPOTHESIS_V1.json":
            _sha(DDC_HYP)}
    assert orv._rehash(pins, ROOT)["all_hold"] is True
    tampered = dict(pins)
    tampered[next(iter(tampered))] = "0" * 64
    assert orv._rehash(tampered, ROOT)["all_hold"] is False


def test_union_recompute_detects_a_planted_reach_loss():
    record = {"n_frozen_ids_reached": 2,
              "per_text": [{"all_frozen_ids_reached": ["a", "b"]}]}
    assert orv.union_matches_count(record)["match"] is True
    record["per_text"][0]["all_frozen_ids_reached"] = ["a"]
    assert orv.union_matches_count(record)["match"] is False


def test_planner_matches_is_exact():
    assert orv.planner_matches(orv.EXPECTED_PLANNER_SHA, orv.EXPECTED_PLANNER_SHA)
    assert not orv.planner_matches(orv.EXPECTED_PLANNER_SHA, "0" * 64)


# --------------------------------------------------------------------------- #
# (d) recorded results are internally consistent
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "result_path,schema,n_gates,n_controls",
    [
        (RESUME_RESULT, "lex-evaluation-operational-resume-verification/1", 6, 4),
        (DDC_RESULT, "lex-evaluation-degradation-disclosure-crosscheck/1", 4, 5),
        (DDC2_RESULT, "lex-evaluation-degradation-disclosure-crosscheck/1", 4, 6),
    ],
)
def test_recorded_result_claims_only_with_consistent_exit(result_path: Path, schema: str,
                                                           n_gates: int, n_controls: int):
    if not result_path.is_file():
        pytest.skip("result not yet recorded (pre-execution tree)")
    rec = json.loads(result_path.read_text(encoding="utf-8"))
    assert rec["schema"] == schema
    assert rec["run_id"] == "39820650174"
    assert rec["exit_code"] in (0, 1, 2)
    assert len(rec["gates"]) == n_gates
    assert len(rec["controls"]) == n_controls
    if rec["exit_code"] == 0:
        assert all(g["passed"] for g in rec["gates"].values())
        assert all(c["holds"] for c in rec["controls"].values())
        assert rec["gate_failures"] == [] and rec["control_failures"] == []
    if rec["exit_code"] == 1:
        assert rec["gate_failures"]
        assert all(c["holds"] for c in rec["controls"].values())
    if rec["exit_code"] == 2:
        assert rec["verdict"] == "ENVIRONMENT_OR_VACUOUS"

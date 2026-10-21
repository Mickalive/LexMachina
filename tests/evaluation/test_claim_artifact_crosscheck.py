"""Tests for evaluation/claim_artifact_crosscheck.py (run 39535657948).

Fail-closed, number-asserting, and mount-independent wherever the logic allows:
the core comparator/extractor is tested on synthetic text so a missing product
mount can never turn a green here into a false pass.  Mount-dependent tests skip
explicitly when /tmp/lex_accepted/product is absent.

No gate, bar, rubric or verdict contract is edited by these tests; they only
exercise the instrument's own extraction/comparison rules.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from evaluation import claim_artifact_crosscheck as cac  # noqa: E402

MOUNT = Path("/tmp/lex_accepted/product")
FREEZE = json.loads(
    (_REPO_ROOT / "evaluation/CLAIM_ARTIFACT_CROSSCHECK_FREEZE_RECORD.json").read_text())
EVAL_STATE = json.loads((_REPO_ROOT / "state/evaluation.json").read_text())
PRODUCT_STATE = (json.loads((MOUNT / "state/product.json").read_text())
                 if MOUNT.is_dir() else None)


# --------------------------------------------------------------------------- #
# extraction
# --------------------------------------------------------------------------- #

def test_claim_regex_extracts_field_values():
    text = ("- **Status**: `human_gate_ready=false` (requires owner session)\n"
            "- `ready_for_owner_session=true` blocked\n")
    fields = {r["field"]: r["asserted"] for r in cac.extract_claims(text)}
    assert fields["human_gate_ready"] is False
    assert fields["ready_for_owner_session"] is True
    assert len(fields) == 2


def test_negation_line_is_not_read_as_an_assertion():
    text = ('"No ready_for_owner_session=true or human_gate_ready=true while either '
            'bar is unmet."\n')
    assert cac.extract_claims(text) == []


def test_future_condition_line_is_not_read_as_an_assertion():
    text = ("**Cycle Status**: complete. `continue_recommended=true` until "
            "`human_gate_ready=true` is recorded after owner session.\n")
    assert cac.extract_claims(text) == []


def test_human_product_gate_phrase_is_detected():
    rows = cac.extract_claims("The product is ready for the human product gate.\n")
    assert [r["field"] for r in rows] == ["__human_product_gate_phrase__"]
    assert rows[0]["line"] == 1


def test_phrase_row_carries_line_and_context():
    rows = cac.compare_report_claims(
        "r.md", "The product is ready for the human product gate.\n",
        {"human_gate_ready": False})
    assert rows[0]["relation"] == "DIVERGENCE"
    assert rows[0]["line"] == 1
    assert "human product gate" in rows[0]["context"]


# --------------------------------------------------------------------------- #
# comparison
# --------------------------------------------------------------------------- #

def test_status_comparison_match_and_divergence():
    ev = {"human_gate_ready": False, "machine_gate_ready": False,
          "ready_for_owner_session": False, "packet_admitted": False,
          "owner_decision_required": False, "direction_version": 61}
    pr = dict(ev)
    rows = cac.compare_status(ev, pr)
    assert len(rows) == 6
    assert all(r["relation"] == "MATCH" for r in rows)
    pr["human_gate_ready"] = True
    assert any(r["relation"] == "DIVERGENCE"
               for r in cac.compare_status(ev, pr))


def test_status_comparison_null_is_not_comparable_not_divergence():
    rows = cac.compare_status({"human_gate_ready": False}, {"human_gate_ready": None})
    assert rows[0]["relation"] == "NOT_COMPARABLE"


def test_report_claim_divergence_and_match():
    assert cac.compare_report_claims(
        "r.md", "`human_gate_ready: true`", {"human_gate_ready": False}
    )[0]["relation"] == "DIVERGENCE"
    assert cac.compare_report_claims(
        "r.md", "`human_gate_ready=false`", {"human_gate_ready": False}
    )[0]["relation"] == "MATCH"


def test_report_without_claims_is_no_assertion():
    rows = cac.compare_report_claims("r.md", "no status here\n", {})
    assert rows[0]["relation"] == "NO_ASSERTION"


# --------------------------------------------------------------------------- #
# frozen pins / fail-closed
# --------------------------------------------------------------------------- #

def test_frozen_pin_check_ok():
    assert cac.check_frozen_pins(FREEZE["frozen_pins"])["ok"] is True


def test_corrupted_pin_fails_closed():
    bad = dict(FREEZE["frozen_pins"])
    bad["RULES_LABEL.json"] = "0" * 64
    check = cac.check_frozen_pins(bad)
    assert check["ok"] is False
    assert check["mismatches"] == ["RULES_LABEL.json"]


def test_absent_mount_run_is_not_measurable(tmp_path):
    rc = cac.run("test_absent", tmp_path / "no_mount", tmp_path / "out", tmp_path / "rep")
    assert rc == 2
    rec = json.loads((tmp_path / "out" / "test_absent" / "test_absent.json").read_text())
    assert rec["verdict"] == "NOT_MEASURABLE"
    assert "absent" in rec["reason"]


# --------------------------------------------------------------------------- #
# mount-dependent (skip when the accepted product mount is absent)
# --------------------------------------------------------------------------- #

@pytest.mark.skipif(not MOUNT.is_dir(), reason="accepted product mount absent")
def test_non_vacuity_all_hold():
    nv = cac.non_vacuity(EVAL_STATE, PRODUCT_STATE, MOUNT, FREEZE["frozen_pins"])
    assert nv["N1_planted_claim_detected"] is True
    assert nv["N2_corrupted_pin_fails_closed"] is True
    assert nv["N3_absent_mount_fails_closed"] is True
    assert nv["all_hold"] is True


@pytest.mark.skipif(not MOUNT.is_dir(), reason="accepted product mount absent")
def test_real_mount_report_divergence_detected():
    text = (MOUNT / "reports/product/CYCLE_39452421855.md").read_text(encoding="utf-8")
    rows = cac.compare_report_claims(
        "reports/product/CYCLE_39452421855.md", text, PRODUCT_STATE)
    divergences = [r for r in rows if r["relation"] == "DIVERGENCE"]
    assert len(divergences) == 3  # two explicit true assertions + the readiness phrase
    assert any(r["line"] == 129 for r in divergences)
    assert any(r["line"] == 137 for r in divergences)


@pytest.mark.skipif(not MOUNT.is_dir(), reason="accepted product mount absent")
def test_real_mount_cli_exit_code_is_1(tmp_path):
    rc = cac.main(["--run-id", "test_real", "--product-mount", str(MOUNT),
                   "--out", str(tmp_path / "out"),
                   "--report-dir", str(tmp_path / "rep")])
    assert rc == 1
    rec = json.loads((tmp_path / "out" / "test_real" / "test_real.json").read_text())
    assert rec["verdict"] == "CLAIM_ARTIFACT_DIVERGENCE"
    assert rec["non_vacuity"]["all_hold"] is True

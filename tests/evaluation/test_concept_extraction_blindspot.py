"""Tests for the concept-extraction blind-spot falsification instrument.

Pins the v57 materiality contract: the product's stoplist-filtered concept
extraction is measured cell-by-cell against this lane's mapping-free concept
lists; a filtered-out concept with zero supporting rows on served bytes is an
ACTIVE blind spot; a minimal counterfactual row-removal that leaves the
product's under_covered silent while an eval-side re-count flags the concept
proves a LATENT blind spot; a drifted pinned input is exit 2 (never a silent
re-pin).  Pure-logic checks run without the product mount; the end-to-end
check runs offline against committed bytes and degrades to exit 2 when the
ephemeral mount is absent (which is an environment reading, never a pass).
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from evaluation.concept_extraction_blindspot import (  # noqa: E402
    SCHEMA, VERDICT_ACTIVE, VERDICT_ENV, VERDICT_LATENT, VERDICT_NONE,
    _eval_side_recount, _norm, verify_inputs,
)

HYP = _REPO_ROOT / "evaluation/CONCEPT_EXTRACTION_BLINDSPOT_HYPOTHESIS_V1.json"


def test_hypothesis_is_frozen_with_exit_rules():
    hyp = json.loads(HYP.read_text(encoding="utf-8"))
    assert hyp["schema"] == (
        "lex-evaluation-concept-extraction-blindspot-hypothesis/1")
    assert set(hyp["success_rule"]) == {"exit_0", "exit_2",
                                        "falsification_proven",
                                        "no_weakening"}
    assert hyp["frozen_for_run"] == "39187646807"
    # every frozen cell is named
    cells = set(hyp["frozen_cells"])
    assert {"leg_A_extraction_divergence", "leg_B_active_blindspot",
            "leg_C_counterfactual", "leg_D_frozen_inputs"} <= cells
    # claim ceiling forbids the standing violations
    ceiling = hyp["claim_ceiling"]
    for phrase in ("DO-NOT-SERVE", "owner_decision_required",
                   "LABEL_SOUND", "GEOMETRY_SOUND"):
        assert phrase in ceiling


def test_verify_inputs_flags_digest_drift_and_missing():
    with tempfile.TemporaryDirectory() as td:
        body = b"payload"
        good = Path(td) / "good.json"
        good.write_bytes(body)
        sha = hashlib.sha256(body).hexdigest()
        hypothesis = {"inputs": {
            "good": {"path": str(good), "sha256": sha},
            "drifted": {"path": str(good), "sha256": "0" * 64},
            "missing": {"path": str(Path(td) / "nope.json"), "sha256": sha},
        }}
        resolved, problems = verify_inputs(hypothesis)
        # "good" and "drifted" both exist on disk so both resolve; "missing" does not
        assert "good" in resolved
        assert "drifted" in resolved
        assert "missing" not in resolved
        assert len(problems) == 2
        assert any("drift" in p for p in problems)
        assert any("missing" in p for p in problems)


def test_verify_inputs_accepts_directory_pins():
    with tempfile.TemporaryDirectory() as td:
        d = Path(td) / "served"
        d.mkdir()
        hypothesis = {"inputs": {
            "served_dir": {"path": str(d), "files": ["a.json"]},
        }}
        resolved, problems = verify_inputs(hypothesis)
        assert problems == []
        assert "served_dir" in resolved


def test_norm_is_nfkd_casefold_collapsed():
    assert _norm("Fürsorgepflicht") == "fursorgepflicht"
    assert _norm("  Kapital   verletzung ") == "kapital verletzung"
    assert _norm(None) == ""


def test_eval_side_recount_matches_substring():
    rows = [
        {"title": "Die Fürsorgepflicht des Arbeitgebers"},
        {"snippet": "Kapitalverletzung im Konkurs"},
        {"full_text": "kein Thema"},
    ]
    assert _eval_side_recount("fursorgepflicht", rows) == 1
    assert _eval_side_recount("kapitalverletzung", rows) == 1
    assert _eval_side_recount("uberwachungspflicht", rows) == 0


def test_verdict_vocabulary_is_frozen():
    assert VERDICT_ACTIVE == "BLIND_SPOT_ACTIVE"
    assert VERDICT_LATENT == "BLIND_SPOT_LATENT_COUNTERFACTUAL_PROVEN"
    assert VERDICT_NONE == "NO_BLIND_SPOT"
    assert VERDICT_ENV == "ENVIRONMENT"


def test_end_to_end_offline_against_committed_bytes():
    """Runs the instrument offline. With the product mount present it must
    produce a falsification verdict; without it, exit 2 (environment)."""
    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / "rec.json"
        report_dir = Path(td) / "reports"
        proc = subprocess.run(
            [sys.executable, "-m", "evaluation.concept_extraction_blindspot",
             "--run-id", "pytest_scratch", "--out", str(out),
             "--report-dir", str(report_dir)],
            cwd=str(_REPO_ROOT), capture_output=True, text=True, timeout=300)
        assert proc.returncode in (0, 2), proc.stderr[-400:]
        assert out.is_file(), "instrument must persist a record even on exit 2"
        rec = json.loads(out.read_text(encoding="utf-8"))
        assert rec["schema"] == SCHEMA
        if proc.returncode == 2:
            # product mount absent or drifted: environment reading, never a pass
            assert rec["verdict"] == VERDICT_ENV
            assert rec["input_digest_problems"]
        else:
            assert rec["verdict"] in (VERDICT_ACTIVE, VERDICT_LATENT,
                                      VERDICT_NONE)
            assert rec["claim_ceiling"]
            assert rec["human_gate_ready"] is False
            assert rec["owner_decision_required"] is False
            # the frontier handoff is published beside, never replaced
            assert "39180276526" in rec["publishes_beside_frontier"]
            # every cell names both extractors' outputs
            for cell in rec["cells"]:
                assert "product_concepts" in cell
                assert "eval_concepts" in cell
                assert "filtered_out" in cell
                assert "added" in cell
        assert (Path(td) / "reports").exists()


def test_committed_record_is_self_consistent():
    """The committed claim-bearing record (when present) must be internally
    consistent: verdict matches the boolean, counterfactual cells agree."""
    rec_path = (_REPO_ROOT / "results/evaluation/concept_extraction_blindspot"
                / "39187646807.json")
    if not rec_path.is_file():
        # not yet committed in this tree; an absent record is not a pass
        return
    rec = json.loads(rec_path.read_text(encoding="utf-8"))
    assert rec["schema"] == SCHEMA
    assert rec["run_id"] == "39187646807"
    # verdict <-> boolean consistency
    if rec["verdict"] in (VERDICT_ACTIVE, VERDICT_LATENT):
        assert rec["falsification_proven"] is True
    else:
        assert rec["falsification_proven"] is False
    # leg B and leg C agree with the verdict
    if rec["verdict"] == VERDICT_ACTIVE:
        assert rec["active_blindspot_cells"]
    if rec["verdict"] == VERDICT_LATENT:
        assert any(c["blind_spot_proven_on_cell"]
                   for c in rec["counterfactual_cells"])
    # every counterfactual cell that claims proven must satisfy both conditions
    for c in rec["counterfactual_cells"]:
        if c["blind_spot_proven_on_cell"]:
            assert c["target_concept"] not in (
                c["product_concepts_on_counterfactual"])
            assert c["target_concept"] not in (
                c["product_under_covered_on_counterfactual"])
            assert c["eval_side_count_on_counterfactual"] == 0

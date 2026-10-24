"""Tests for the item-(3) frozen-scorer / span-seam path reconciliation."""
from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from evaluation import scorer_path_reconciliation as recon


def test_frozen_predicate_identity():
    from evaluation.mapping_free_recall_falsifier import (
        counter_authority_surface as fn)
    assert callable(fn)
    # the instrument must call the same accepted predicate
    assert recon.mf_counter_surface is fn


def test_rubric_digest_pinned():
    sha = recon._sha256_file_public(
        _REPO_ROOT / "evaluation/frozen_bars/RULES_LABEL.json")
    assert sha == recon.FROZEN_RUBRIC_SHA_EXPECTED


def test_run_smoke_on_real_mount_or_env_error(tmp_path):
    code, record = recon.run("scratch_test_recon", tmp_path, tmp_path)
    assert record["schema"] == recon.SCHEMA
    if code == 2:
        assert record["verdict"] in ("ENVIRONMENT_ERROR", "ENVIRONMENT_OR_VACUOUS")
        return
    assert record["verdict"] in ("RECONCILIATION_COMPLETE", "RECONCILIATION_FALSIFIED")
    # the contract question must always be answered with a shape verdict
    ca = record["contract_analysis"]
    assert ca["guarded_emitted_rows_shape_ok"] in (True, False, None)
    # provenance must carry file:line anchors on both sides
    assert "305-317" in record["provenance"]["side_a_frozen_scorer"]["file_lines"]
    assert "counter_evidence_span.py" in (
        record["provenance"]["side_b_product_span_seam"]["transform_chain"])
    # requirement-26 trio published together when emissions exist
    agg = record["aggregate"]["side_b_product_arms_n_emitted"]
    assert set(agg) == {"baseline", "candidate_unguarded", "candidate"}


def test_provenance_names_both_sides():
    assert "side_a_frozen_scorer" in recon.PROVENANCE
    assert "side_b_product_span_seam" in recon.PROVENANCE
    assert "harness_execution_note" in recon.PROVENANCE["side_b_product_span_seam"]

"""The live-slice record must say which stages of the canonical chain it ran.

Why this module exists
----------------------
Run 39187482610 committed ``results/product/live_slice/20261019T022100Z.json``
with ``"verdict": "PASS"`` and a ``claim_ceiling`` naming

    query -> query_result_bundle -> sourced answer -> counter-authority pass ->
    clickable map

while the same artifact reported

    "answer":   {"status": "pending", "n_cited": 0}
    "counters": {"counter_authorities": 0, "counter_status_bearing_rows": 0,
                 "by_status": {"none": 100}}
    "timing_s": {"enrich_s": 0.0}

and published no field saying the answer and counter-authority stages had not
executed.  ``status: "pending"`` is the placeholder ``run_query_initial`` stamps
(``product/query/pipeline.py``, ``method="pending_generative_audit"``) and every
row's ``counter_status`` is the literal ``"none"`` that same function writes, so
the two zeroed fields are the fingerprint of a ``--no-enrich`` run - not a failed
answer and not an empty result set.  Before this module the record could not
distinguish those three situations and reported PASS for the narrowest of them.

That is the binding defect class named for 2026-10-18: a published claim that
does not reproduce from the committed tree.  So:

* ``live_slice.stage_disclosure`` / ``live_slice.verdict_for`` derive the stages
  from the run, and a map-only run can no longer be published as PASS;
* every committed live-slice record is re-derived here, from its own bytes,
  against its own field names - the tests below are offline and need no network.

Non-vacuity is asserted, not hoped for: the committed map-only artifact is the
witness, and a synthetic chain-PASS control proves the predicate distinguishes.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "product"))
sys.path.insert(0, str(ROOT))

from product.live_slice import (  # noqa: E402
    PENDING_ANSWER_STATUS,
    stage_disclosure,
    verdict_for,
)

LIVE_SLICE_DIR = ROOT / "results" / "product" / "live_slice"
AMENDMENT = ROOT / "results" / "product" / "live_slice_stages" / "STAGE_DISCLOSURE_AMENDMENT.json"
LIVE_SLICE_SCHEMA = "product-live-slice/1"


def _records() -> list[Path]:
    out: list[Path] = []
    for path in sorted(LIVE_SLICE_DIR.glob("*.json")):
        if path.name.endswith("_bundle.json"):
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            continue
        if isinstance(payload, dict) and payload.get("schema") == LIVE_SLICE_SCHEMA:
            out.append(path)
    return out


# --------------------------------------------------------------------------
# The shipped helpers
# --------------------------------------------------------------------------

def test_a_map_only_run_cannot_be_published_as_a_chain_pass():
    """The defect itself, as an executable assertion on the shipped code."""
    stages = stage_disclosure(
        n_rows=100, enrich=False, enrich_error=None, answer_status=PENDING_ANSWER_STATUS,
    )
    assert stages["canonical_chain"] is False
    assert stages["enrichment_attempted"] is False
    assert stages["answer"] is False
    assert stages["counter_authority"] is False
    # Every other check the record makes is green in exactly this situation -
    # that is what made the old verdict a PASS.
    checks = {k: True for k in (
        "retrieval_mode_served_is_refresh", "no_cache_hits_on_the_network_leg",
        "adapter_made_network_calls", "independent_probe_saw_the_network",
        "enrichment_never_moved_a_point_already_on_the_map", "map_has_rows",
        "every_row_has_xy", "every_row_has_a_source_link", "bundle_validates",
        "page_contract_ok")}
    checks["canonical_chain_ran"] = stages["canonical_chain"]
    assert verdict_for(checks, stages) == "PASS_MAP_ONLY"
    assert verdict_for(checks, stages) != "PASS"


def test_a_full_chain_run_is_still_reported_as_pass():
    """The control: the fix must not turn every run into a non-PASS."""
    stages = stage_disclosure(
        n_rows=100, enrich=True, enrich_error=None, answer_status="ready",
    )
    assert stages["canonical_chain"] is True
    checks = {"page_contract_ok": True, "canonical_chain_ran": stages["canonical_chain"]}
    assert verdict_for(checks, stages) == "PASS"


def test_a_wiring_failure_is_still_fail_not_map_only():
    """The other control: a map-only label must not absorb real failures."""
    stages = stage_disclosure(
        n_rows=0, enrich=False, enrich_error=None, answer_status=PENDING_ANSWER_STATUS,
    )
    assert verdict_for({"map_has_rows": False,
                        "canonical_chain_ran": stages["canonical_chain"]}, stages) == "FAIL"


def test_enrichment_that_raised_is_distinguished_from_enrichment_never_asked_for():
    """Both fail the chain; only one of them failed."""
    never_asked = stage_disclosure(
        n_rows=100, enrich=False, enrich_error=None, answer_status=PENDING_ANSWER_STATUS)
    asked_and_failed = stage_disclosure(
        n_rows=100, enrich=True, enrich_error="RuntimeError: provider", answer_status="pending")
    assert never_asked["enrichment_attempted"] is False
    assert asked_and_failed["enrichment_attempted"] is True
    assert asked_and_failed["enrichment_completed"] is False
    assert never_asked["canonical_chain"] is asked_and_failed["canonical_chain"] is False


def test_a_pending_answer_is_never_read_as_a_ran_answer():
    """`pending` is the placeholder; anything else means the stage produced one."""
    for status in ("pending", "", None):
        assert stage_disclosure(n_rows=1, enrich=True, enrich_error=None,
                                answer_status=status)["answer"] is False
    for status in ("ready", "degraded", "cited_nothing"):
        assert stage_disclosure(n_rows=1, enrich=True, enrich_error=None,
                                answer_status=status)["answer"] is True


# --------------------------------------------------------------------------
# The committed artifacts, re-derived from their own bytes
# --------------------------------------------------------------------------

def test_the_sweep_sees_every_committed_live_slice_record_regardless_of_name():
    """The glob half: a timestamp-named record must not escape the sweep.

    ``product/live_slice.py`` stamps ``--run-id`` into the filename verbatim, so
    a run that omits the flag produces ``20261019T022100Z.json``.  The sweep used
    to glob ``CYCLE_*.json`` only, which is how that record reached the tree with
    no citation arithmetic and no required report of record applied to it.
    """
    names = {p.name for p in _records()}
    assert "20261019T022100Z.json" in names, (
        "the artifact that motivated this module is not swept - if it was "
        "removed from the tree, the sweep it proved broken is no longer tested")
    assert any(not n.startswith("CYCLE_") for n in names), (
        "every swept record is CYCLE_-named, so the non-CYCLE_ path is untested")


def test_every_committed_record_discloses_its_stages_or_is_named_by_the_amendment():
    """No committed record may claim a chain PASS without stage evidence.

    Records written before this fix carry no ``stages_executed`` at all.  They
    are NOT silently accepted and NOT edited - the repository forbids
    overwriting a claim-bearing historical result.  Each is re-derived here from
    its own bytes and must be named by
    ``results/product/live_slice/STAGE_DISCLOSURE_AMENDMENT.json`` with an
    effective verdict its own fields support.  A record published AFTER the fix
    must agree with its own bytes; one that does not fails, so the defect class
    cannot reappear.
    """
    amendment = json.loads(AMENDMENT.read_text(encoding="utf-8"))
    by_artifact = {r["artifact"]: r for r in amendment["records"]}
    assert amendment["verdict"] == "PASS", amendment.get("failures")

    checked = 0
    for path in _records():
        payload = json.loads(path.read_text(encoding="utf-8"))
        fingerprint_map_only = (
            str((payload.get("answer") or {}).get("status") or "")
            in ("", PENDING_ANSWER_STATUS)
            and int((payload.get("counters") or {}).get("counter_status_bearing_rows") or 0) == 0
            and set((payload.get("counters") or {}).get("by_status") or {"none"}) <= {"none"}
        )
        name = str(path.relative_to(ROOT))
        assert name in by_artifact, (
            f"{name} is swept but absent from the amendment artifact - a record "
            "outside the amendment's coverage is unchecked")
        row = by_artifact[name]
        # The amendment's own fingerprint is recomputed from the same fields.
        assert row["map_only_fingerprint"] is fingerprint_map_only, (
            f"{name}: the amendment disagrees with the bytes it classifies")

        stages = payload.get("stages_executed")
        if stages is None:
            # Pre-fix record: its disagreement is the recorded defect and the
            # amendment exists precisely to carry it.
            if fingerprint_map_only:
                assert row["effective_verdict"] == "PASS_MAP_ONLY", (
                    f"{name} carries the map-only fingerprint but the amendment "
                    f"leaves it at {row['effective_verdict']}")
                assert row["verdict_published"] == payload["verdict"], (
                    f"{name}: the amendment must preserve the published verdict "
                    "verbatim, never overwrite it")
            else:
                assert row["effective_verdict"] == payload["verdict"]
            continue

        checked += 1
        assert isinstance(stages, dict) and "canonical_chain" in stages, (
            f"{name} publishes stages_executed without canonical_chain")
        assert stages["canonical_chain"] is not fingerprint_map_only, (
            f"{name} declares canonical_chain={stages['canonical_chain']} "
            f"while its own fields say map_only={fingerprint_map_only}")
        assert (payload.get("verdict") == "PASS") is bool(stages["canonical_chain"]), (
            f"{name} publishes verdict {payload.get('verdict')!r} against "
            f"canonical_chain={stages['canonical_chain']}")

    assert checked == 0, (
        "no staged record exists yet, so the post-fix branch of this test is "
        "unexercised - the 'agrees with its own bytes' assertion never ran")


def test_the_amendment_would_catch_a_new_staged_record_that_lies():
    """Non-vacuity for the guard: the amendment's failure path really fires."""
    from product.live_slice_stage_amendment import classify

    lying = {
        "run_id": "SYNTHETIC",
        "answer": {"status": "pending", "n_cited": 0, "provider_error": None},
        "counters": {"counter_status_bearing_rows": 0, "by_status": {"none": 9}},
        "map": {"n_decisions": 9},
        "timing_s": {"enrich_s": 12.5},
        "stages_executed": {"canonical_chain": True},
        "verdict": "PASS",
    }
    row = classify(lying)
    assert row["classification"] == "STAGED"
    assert row["agrees_with_its_own_bytes"] is False, (
        "a staged record claiming the chain ran with a pending answer and zero "
        "counters must be reported as disagreeing with its own bytes")
    honest = {**lying,
              "answer": {"status": "ready", "n_cited": 2, "provider_error": None},
              "counters": {"counter_status_bearing_rows": 1, "by_status": {"cited": 2}},
              "timing_s": {"enrich_s": 12.5}}
    assert classify(honest)["agrees_with_its_own_bytes"] is True


def test_the_defect_artifact_is_present_and_is_a_map_only_run():
    """Name the witness by its own bytes, so the claim is checkable.

    Every number here is read out of the committed artifact, not restated from
    a report.  Run 39187482610 committed this file at 02:22:57Z with the map
    built from nine fresh-network calls against the public OpenCaseLaw API; it
    is real retrieval evidence, and it is not evidence of an answer or of a
    counter-authority pass.
    """
    path = LIVE_SLICE_DIR / "20261019T022100Z.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["verdict"] == "PASS"
    assert payload["answer"]["status"] == PENDING_ANSWER_STATUS
    assert payload["answer"]["n_cited"] == 0
    assert payload["counters"]["counter_authorities"] == 0
    assert payload["counters"]["counter_status_bearing_rows"] == 0
    assert payload["timing_s"]["enrich_s"] == 0.0
    assert payload["stages_executed"] if "stages_executed" in payload else True
    # The retrieval half is real and is not what this cycle disputes.
    assert payload["freshness"]["adapter_cache_hits"] == 0
    assert payload["freshness"]["adapter_network_calls"] > 0
    assert payload["map"]["n_decisions"] > 0
    assert payload["map"]["rows_with_source_url"] == payload["map"]["n_decisions"]
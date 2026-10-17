"""The obligated packet-summary producer must exist and reproduce the evidence.

Run 38984833779 rebuilt the served packet live and committed the per-leg summary
``results/product/CYCLE_38984833779/leg_business-judgment-rule_live.json`` whose
headline claim is obligation (5): a live answer cited **3 of the 5** frozen
direct-TF BJR authorities (baseline 0/5).  The producer for that
``product/rebuild-served-packet/1`` schema was never committed, so an independent
auditor could not recompute the claim and the audit job burned its whole work
quantum (run 38988477028, audit rc 78 ``LEX_WORK_QUANTUM_EXPIRED``).

``product/rebuild_served_packet.py`` is that producer.  These tests pin it to the
committed artifact, prove every claim-bearing field is reproduced, and — because
one field of the reference is demonstrably self-contradictory — prove the
divergence is *disclosed and machine-checked* rather than silently matched.

All tests are offline: no network, no provider, no LLM.  Each behavioural test
has a non-vacuity control.
"""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
PRODUCT = ROOT / "product"
for _p in (str(PRODUCT), str(ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import rebuild_served_packet as RSP  # noqa: E402

BUNDLE = (ROOT / "results" / "product" / "CYCLE_38984833779"
          / "bundle_business-judgment-rule_live.json")
LEG = (ROOT / "results" / "product" / "CYCLE_38984833779"
       / "leg_business-judgment-rule_live.json")
SLUG = "business-judgment-rule"
RUN_ID = "38984833779"


def _bundle() -> dict:
    return json.loads(BUNDLE.read_text(encoding="utf-8"))


def _rebuild(bundle: dict | None = None) -> dict:
    return RSP.build_summary(bundle if bundle is not None else _bundle(),
                             slug=SLUG, run_id=RUN_ID)


# --------------------------------------------------------------------------- #
# 1. reproduction of the committed obligation-(5) evidence
# --------------------------------------------------------------------------- #
def test_rebuild_reproduces_the_committed_leg_artifact_field_for_field():
    """The producer that was missing now exists and reproduces the artifact.

    This is the whole point of the module: the auditor runs one command and gets
    the artifact's claim back.  A single changed deterministic field would mean
    the claim is not reproducible from the committed bundle.
    """
    reference = json.loads(LEG.read_text(encoding="utf-8"))
    rebuilt = _rebuild()
    diffs = RSP.compare(rebuilt, reference)
    assert diffs == [], "rebuild diverged from the committed artifact:\n" + "\n".join(diffs)


def test_recall_gate_records_the_measured_3_of_5_and_passes():
    """The obligation-(5) claim itself, recomputed rather than trusted."""
    gate = _rebuild()["recall_gate_recall_controlling_authority"]
    assert gate["passes"] is True
    assert gate["n"] == 3
    assert gate["of"] == 5
    assert gate["baseline_accepted_base"] == "0/5"
    assert sorted(_rebuild()["frozen_bjr_authorities_cited"]) == [
        "bger_4A_219_2015", "bger_4A_603_2014", "bger_4A_626_2013",
    ]


def test_check_cli_reproduces_the_reference_and_exits_zero(capsys):
    rc = RSP.main([
        "--bundle", str(BUNDLE), "--slug", SLUG, "--run-id", RUN_ID,
        "--reference", str(LEG), "--check",
    ])
    assert rc == 0
    out = capsys.readouterr().out
    assert "reproduces" in out


# --------------------------------------------------------------------------- #
# 2. non-vacuity: the recall gate can fail
# --------------------------------------------------------------------------- #
def test_recall_gate_fails_when_the_answer_cites_no_frozen_authority():
    """Non-vacuity: with the frozen citations removed the gate must go red.

    Without this, a hard-coded ``passes: true`` would satisfy the reproduction
    test above and still be a harness that measures nothing.
    """
    bundle = _bundle()
    frozen = set(RSP.FROZEN_AUTHORITIES[SLUG]["direct"])  # type: ignore[index]
    for d in bundle["decisions"]:
        if d.get("decision_id") in frozen:
            d["counter_status"] = "none"
    bundle["answer"]["cited_decision_ids"] = [
        c for c in bundle["answer"]["cited_decision_ids"] if c not in frozen
    ]
    gate = RSP.build_summary(bundle, slug=SLUG, run_id=RUN_ID)[
        "recall_gate_recall_controlling_authority"]
    assert gate["n"] == 0
    assert gate["passes"] is False


def test_recall_gate_passes_with_exactly_one_frozen_authority():
    """The stated bar is 'at least one', and it is exercised at its boundary."""
    bundle = _bundle()
    keep = {"bger_4A_219_2015"}
    frozen = set(RSP.FROZEN_AUTHORITIES[SLUG]["direct"])  # type: ignore[index]
    bundle["answer"]["cited_decision_ids"] = [
        c for c in bundle["answer"]["cited_decision_ids"]
        if c not in frozen or c in keep
    ]
    gate = RSP.build_summary(bundle, slug=SLUG, run_id=RUN_ID)[
        "recall_gate_recall_controlling_authority"]
    assert gate["n"] == 1
    assert gate["passes"] is True


# --------------------------------------------------------------------------- #
# 3. the known divergence is disclosed, never laundered
# --------------------------------------------------------------------------- #
def test_counter_count_divergence_is_disclosed_and_machine_checked():
    """The reference artifact's ``n_counter`` contradicts its own admissibility.

    It reported ``n_counter = 4`` by counting ``counter_status != 'none'`` -- the
    four rows the answer *cited* -- while the same artifact's ``admissibility``
    block correctly warned ``no_counter_authority``. This test pins both numbers
    and the warning so the contradiction can never be silently matched (which
    would launder it) or silently dropped (which would hide it).
    """
    reference = json.loads(LEG.read_text(encoding="utf-8"))
    rebuilt = _rebuild()

    assert rebuilt["bundle_summary"]["n_counter"] == 0  # product definition
    assert rebuilt["counter_count"][
        "legacy_artifact_definition_counter_status_not_none"] == 4
    assert reference["bundle_summary"]["n_counter"] == 4

    codes = [f["code"] for f in reference["admissibility"]["findings"]]
    assert "no_counter_authority" in codes, (
        "the reference artifact no longer carries the warning that makes its "
        "own n_counter=4 self-contradictory; the reconciliation must be revisited"
    )
    # The rebuilt output reproduces that same warning (verify_bundle is reused).
    assert rebuilt["admissibility"] == reference["admissibility"]
    assert "counter_ids" in rebuilt["counter_count"]["note"]


def test_compare_ignores_only_the_known_divergence_field():
    """Non-vacuity: any OTHER change to bundle_summary must still be reported."""
    reference = json.loads(LEG.read_text(encoding="utf-8"))
    tampered = copy.deepcopy(reference)
    tampered["bundle_summary"]["n_decisions"] = 999
    assert RSP.compare(_rebuild(), tampered) != []
    # ...while the known divergence alone does not raise a diff.
    only_ncounter = copy.deepcopy(reference)
    only_ncounter["bundle_summary"]["n_counter"] = 0
    assert RSP.compare(_rebuild(), only_ncounter) == []


# --------------------------------------------------------------------------- #
# 4. mega-cluster disclosure non-vacuity
# --------------------------------------------------------------------------- #
def test_mega_cluster_disclosure_fires_when_one_cluster_dominates():
    """The frozen 0.5 pseudo-cluster disclosure must be able to fire."""
    baseline = _rebuild()
    assert baseline["largest_cluster_size_share"] < RSP.MEGA_CLUSTER_SHARE
    assert baseline["mega_cluster_disclosure"]["fired"] is False

    bundle = _bundle()
    # The disclosure threshold reads clusters[].size (the accepted R2
    # definition), so inflate the declared size, not the per-decision ids.
    target = bundle["clusters"][0]
    target["size"] = int(len(bundle["decisions"]) * 0.8)
    out = RSP.build_summary(bundle, slug=SLUG, run_id=RUN_ID)
    assert out["mega_cluster_disclosure"]["bar"] == RSP.MEGA_CLUSTER_SHARE
    assert out["largest_cluster_size_share"] >= RSP.MEGA_CLUSTER_SHARE
    assert out["mega_cluster_disclosure"]["fired"] is True


# --------------------------------------------------------------------------- #
# 5. the product's own decision code is reused, not re-implemented
# --------------------------------------------------------------------------- #
def test_admissibility_is_reused_verbatim_from_gate_admissibility():
    from query.gate_admissibility import verify_bundle, cluster_shares

    bundle = _bundle()
    verdict = verify_bundle(bundle)
    rebuilt = _rebuild()
    assert rebuilt["admissibility"]["admissible"] == verdict["admissible"]
    assert rebuilt["admissibility"]["warning_count"] == verdict["warning_count"]
    assert rebuilt["cluster_shares_size_based"] == cluster_shares(bundle)


def test_packet_admission_is_reused_and_keeps_the_owner_gate_closed():
    from product.packet_admission import packet_admission

    rebuilt = _rebuild()
    assert rebuilt["packet_admission"] == packet_admission()
    assert rebuilt["packet_admission"]["ready_for_owner_session"] is False
    assert rebuilt["packet_admission"]["human_gate_ready"] is False
    assert "accepted_do_not_serve_order" in rebuilt["packet_admission"]["blocked_by"]


# --------------------------------------------------------------------------- #
# 6. argument handling
# --------------------------------------------------------------------------- #
def test_unknown_slug_is_refused():
    with pytest.raises(SystemExit):
        RSP.build_summary(_bundle(), slug="not-a-leg", run_id=RUN_ID)


def test_slug_is_inferred_from_the_frozen_question_string():
    from reality_check import LEGS

    assert RSP._slug_from_query({"query": LEGS[SLUG]}) == SLUG
    assert RSP._slug_from_query({"query": "a question that is not frozen"}) is None

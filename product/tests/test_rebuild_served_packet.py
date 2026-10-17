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
# 3b. path-independent reproduction (audit REQUIRED-1 of cycle 38993348615)
# --------------------------------------------------------------------------- #
def test_compare_is_path_independent_of_the_checkout_that_wrote_the_reference():
    """The exact rejected-cycle defect, pinned.

    ``packet_admission()`` emits ``verdict_source`` as an absolute checkout path.
    The committed reference records ``/home/runner/work/LexMachina/LexMachina/...``;
    a producer workspace at ``/tmp/lex_team`` rebuilds the same file under a
    different prefix.  Before the repair, ``compare`` reported a diff and
    ``--check`` exited 1 there.  Reproduction must not depend on the directory
    that wrote the reference.
    """
    reference = json.loads(LEG.read_text(encoding="utf-8"))
    foreign = copy.deepcopy(reference)
    foreign["packet_admission"]["verdict_source"] = (
        "/tmp/lex_team/results/product/frontier_verdicts/"
        "ACCEPTED_frontier-served-packet-falsification_38880639079.json"
    )
    assert foreign["packet_admission"]["verdict_source"] != \
        reference["packet_admission"]["verdict_source"]
    assert RSP.compare(_rebuild(), foreign) == []


def test_compare_canonicalises_both_sides_and_the_normaliser_is_bounded():
    """Both sides are canonicalised; unrelated strings and file identity survive."""
    tail = ("results/product/frontier_verdicts/"
            "ACCEPTED_frontier-served-packet-falsification_38880639079.json")
    # Canonicalisation is idempotent, strips any checkout prefix, and is bounded
    # to a single results/product/frontier_verdicts/<file> tail.
    assert RSP.canonical_verdict_source("/a/b/" + tail) == tail
    assert RSP.canonical_verdict_source(tail) == tail
    assert RSP.canonical_verdict_source("") == ""
    assert RSP.canonical_verdict_source("/etc/passwd") == "/etc/passwd"
    assert RSP.canonical_verdict_source("/x/results/other/y.json") == \
        "/x/results/other/y.json"

    # Rebuilt side with a foreign prefix also reproduces the committed reference.
    reference = json.loads(LEG.read_text(encoding="utf-8"))
    rebuilt = _rebuild()
    rebuilt["packet_admission"]["verdict_source"] = "/tmp/lex_team/" + tail
    assert RSP.compare(rebuilt, reference) == []


def test_compare_still_fails_on_a_real_packet_admission_content_change():
    """Non-vacuity: normalising the path must not hide any real change.

    A hard-coded ``verdict_source``-only comparison would reproduce the artifact
    while measuring nothing.  Each tampered subfield below is a genuine change to
    the admission decision and MUST raise a diff.
    """
    reference = json.loads(LEG.read_text(encoding="utf-8"))
    cases = {
        "verdict_run": "99999999",
        "verdict_team": "some-other-team",
        "verdict_accept_commit": "0" * 40,
        "verdict_covers_this_packet": False,
        "blocked_by": [],
        "admissible": True,
        "ready_for_owner_session": True,
        "human_gate_ready": True,
        "serve_recommendation": "SERVE this packet",
    }
    for key, value in cases.items():
        tampered = copy.deepcopy(reference)
        assert key in tampered["packet_admission"], key
        tampered["packet_admission"][key] = value
        diffs = RSP.compare(_rebuild(), tampered)
        assert diffs != [], f"a changed packet_admission.{key} was not reported"
        assert any("packet_admission" in d for d in diffs), key


def test_compare_fails_when_the_verdict_file_identity_changes():
    """Normalisation strips a checkout prefix, never the verdict file name."""
    reference = json.loads(LEG.read_text(encoding="utf-8"))
    other = copy.deepcopy(reference)
    other["packet_admission"]["verdict_source"] = (
        "/tmp/lex_team/results/product/frontier_verdicts/"
        "ACCEPTED_some-other-team_11111111111.json"
    )
    diffs = RSP.compare(_rebuild(), other)
    assert diffs != []
    assert any("packet_admission" in d for d in diffs)



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


# --------------------------------------------------------------------------- #
# 9. leg-report citation-recall record (live-leg durability evidence)
# --------------------------------------------------------------------------- #
LEG_REPORT_LIVE = (ROOT / "results" / "product" / "reality_check"
                   / "business-judgment-rule_live_ci-38999687700_opresume_20261017T035719Z.json")


def _leg_report(**overrides) -> dict:
    base = {
        "slug": "business-judgment-rule",
        "run_id": "SYNTHETIC",
        "mode": "live",
        "evidence_tier": "CI_TEAM_JOB_LIVE",
        "leg_passed": True,
        "answer_model": "opencode/mimo-v2.6-flash-free",
        "cited_decision_ids": [
            "bger_4A_219_2015", "bger_4A_259_2016", "bger_4A_626_2013",
            "bger_4A_603_2014", "bger_4A_62_2024",
        ],
        "gates": [{"gate": "structural", "passed": True}],
        "total_seconds": 10.0,
    }
    base.update(overrides)
    return base


def test_leg_recall_record_from_a_synthetic_full_citation_set():
    rec = RSP.recall_from_leg_report(_leg_report(), source="synthetic")
    gate = rec["recall_gate_recall_controlling_authority"]
    assert rec["schema"] == "product/rebuild-served-packet-recall/1"
    assert gate == {"passes": True, "n": 5, "of": 5,
                    "baseline_accepted_base": "0/5"}
    assert len(rec["frozen_authorities_cited"]) == 5
    assert rec["leg_gates_passed"] is True


def test_leg_recall_record_uses_the_single_frozen_authority_table():
    rec = RSP.recall_from_leg_report(_leg_report(), source="synthetic")
    direct = set(RSP.FROZEN_AUTHORITIES["business-judgment-rule"]["direct"])
    assert set(rec["frozen_authorities_cited"]) <= direct
    assert rec["recall_gate_recall_controlling_authority"]["of"] == len(direct)


def test_leg_recall_partial_citation_set_is_counted_exactly():
    rec = RSP.recall_from_leg_report(
        _leg_report(cited_decision_ids=["bger_4A_219_2015", "unrelated_case"]),
        source="synthetic")
    gate = rec["recall_gate_recall_controlling_authority"]
    assert gate["n"] == 1 and gate["passes"] is True  # bar is >= 1
    assert rec["frozen_authorities_cited"] == ["bger_4A_219_2015"]


def test_leg_recall_unknown_slug_is_refused():
    with pytest.raises(ValueError, match="unknown slug"):
        RSP.recall_from_leg_report(_leg_report(slug="not-a-leg"), source="x")


def test_committed_third_live_run_recall_is_recomputable():
    """The durability artifact of run 38999687700_opresume: the frozen BJR
    citation-recall gate is green on a THIRD live execution (4/5), recomputed
    from the committed leg report by the committed producer."""
    assert LEG_REPORT_LIVE.exists(), LEG_REPORT_LIVE
    report = json.loads(LEG_REPORT_LIVE.read_text(encoding="utf-8"))
    rec = RSP.recall_from_leg_report(report, source=str(LEG_REPORT_LIVE))
    gate = rec["recall_gate_recall_controlling_authority"]
    assert rec["retrieval_mode"] == "live"
    assert rec["leg_gates_passed"] is True
    assert gate["passes"] is True
    assert gate["n"] == 4 and gate["of"] == 5
    assert set(rec["frozen_authorities_cited"]) == {
        "bger_4A_219_2015", "bger_4A_259_2016",
        "bger_4A_603_2014", "bger_4A_626_2013"}


def test_leg_recall_cli_check_fails_on_a_tampered_reference(tmp_path, capsys):
    """Non-vacuity of the --check path: dropping one frozen citation from the
    reference must produce a diff and rc 1."""
    leg_path = tmp_path / "leg.json"
    leg_path.write_text(json.dumps(_leg_report()))
    good = tmp_path / "good.json"
    rc = RSP.main(["--leg-report", str(leg_path), "--out", str(good),
                   "--reference", str(good), "--check"])
    assert rc == 0, capsys.readouterr()
    tampered = json.loads(good.read_text())
    tampered["frozen_authorities_cited"] = tampered["frozen_authorities_cited"][:3]
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps(tampered))
    rc = RSP.main(["--leg-report", str(leg_path),
                   "--reference", str(bad), "--check"])
    assert rc == 1
    assert "DIFFERENCES" in capsys.readouterr().err

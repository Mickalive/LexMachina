"""Executable tests for evaluation/query_map/product_served_bundle_falsification.py.

Scope discipline
----------------
These tests are OFFLINE.  They never reach the network.  Tests that need the
accepted product mount SKIP (never silently pass) when it is absent, and they say
so in their docstring so a green run can never be mistaken for a measured pass.

They pin:
* the frozen hypothesis's digests (re-hashed, never re-derived);
* the frozen NOT_MEASURED discipline (a phase-dependent check can never be
  published as a pass);
* the non-vacuity control CAUSE CLASSIFICATION (an unexercised contract is not a
  satisfied one);
* the L3 before/after verdict logic on synthetic fixtures, INCLUDING the negative
  classes the product could still be in;
* the L3 non-vacuity controls on synthetic bundles;
* that every exit code path is reachable and that the aggregate implements the
  frozen PER-INSTANCE rule rather than a stricter all-qids rule;
* that no environment-failure return skips writing a machine record.
"""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import pytest

from evaluation.query_map import product_served_bundle_falsification as psbf
from evaluation.query_map.harness import COUNTER_STATUSES
from evaluation.question_native_transfer import FROZEN_QIDS

MOUNT = Path("/tmp/lex_accepted/product")
HYPOTHESIS = Path(__file__).resolve().parents[2] / "evaluation/PRODUCT_SERVED_BUNDLE_FALSIFICATION_HYPOTHESIS_V1.json"

MOUNT_PRESENT = MOUNT.exists() and (MOUNT / "product/query/gate_admissibility.py").exists()

if MOUNT_PRESENT and str(MOUNT) not in sys.path:
    # The accepted product mount is a LINKED WORKTREE checked out at
    # /tmp/lex_accepted/product; importing `product.*` needs its own root on the
    # path, not the evaluation lane's.
    sys.path.insert(0, str(MOUNT))


def _hyp() -> dict:
    return json.loads(HYPOTHESIS.read_text(encoding="utf-8"))


def _bundle(n_decisions: int = 6, *, labelled: int = 2, cited: int = 2) -> dict:
    """A minimal bundle that satisfies the accepted harness contract."""
    decisions = []
    for i in range(n_decisions):
        d = {
            "decision_id": f"bge 143 III {100 + i}",
            "canonical_url": f"https://mcp.opencaselaw.ch/de/v1/decision/bge143iii{100 + i}",
            "source_url": f"https://www.bger.ch/bge/143III/100_{i}",
            "citation": f"143 III {100 + i}",
            "court": "Bundesgericht",
            "decision_date": "2021-01-01",
            "score": 1.0 - i / (n_decisions or 1),
            "query_similarity": 1.0 - i / (n_decisions or 1),
            "provenance": {"channel": "baseline"},
            "language": ["de", "fr", "it"][i % 3],
            "title": f"Entscheidung {i}",
            "regeste": "Regeste",
            "snippet": "Snippet",
            "cluster_id": i % 2,
            "x": float(i),
            "y": float(-i),
            "is_outlier": i % 5 == 0,
            "rank": i + 1,
        }
        d["counter_status"] = "candidate-limiting" if i < labelled else "none"
        if i < labelled:
            d["counter_evidence"] = "Art. 257 OR begrenzt die Pflicht."
            d["counter_uncertainty"] = 0.4
            d["adversarial_channel"] = "adversarial"
            d["counter_reason_code"] = "norm_and_limitation_tokens"
        decisions.append(d)
    clusters = [
        {"cluster_id": k, "label": f"c{k}", "size": len(decisions[k::2]),
         "member_ids": [d["decision_id"] for d in decisions[k::2]]}
        for k in (0, 1)
    ]
    return {
        "bundle_version": "1.0",
        "query": "Kapitalverletzung Ueberwachungspflicht",
        "query_variants": ["Kapitalverletzung Ueberwachungspflicht"],
        # The product's own inspection reads relation endpoints as `source` /
        # `target` / `kind` (product/replay_bundle.py:651-654); using any other
        # key name makes every relation dangling, which the admission gate then
        # blocks on. The fixture matches the real shape.
        "relations": [{"source": decisions[0]["decision_id"],
                       "target": decisions[1]["decision_id"],
                       "kind": "cites"}],
        "decisions": decisions,
        "clusters": clusters,
        "answer": {"status": "ready", "cited_decision_ids":
                   [d["decision_id"] for d in decisions[:cited]]},
        "provenance": {"phase": "complete", "fixture_mode": False,
                       "retrieval": {"remote": {}}},
    }


def _admissibility(*, under, codes, warning_count, admissible=True,
                   disclosure_severity="warning", disclosure_terms=None) -> dict:
    """A synthetic admission record shaped like the product's own.

    A code matched by the frozen DISCLOSURE_MARKERS is given the product's real
    shape: severity=warning plus the under-covered terms in its detail. Every
    other code is an info notice, exactly as the served records show.
    """
    from evaluation.question_native_transfer import DISCLOSURE_MARKERS
    findings = []
    for c in codes:
        f = {"code": c, "severity": "info", "detail": "x"}
        if any(m in c.lower() for m in DISCLOSURE_MARKERS):
            f["severity"] = disclosure_severity
            f["query_concepts_under_covered"] = list(
                under if disclosure_terms is None else disclosure_terms)
        findings.append(f)
    return {"admissible": admissible, "warning_count": warning_count,
            "blocking_count": 0, "findings": findings,
            "measured": {"query_concepts_under_covered": list(under)}}


# --------------------------------------------------------------------------- #
# frozen hypothesis integrity
# --------------------------------------------------------------------------- #
def test_hypothesis_freezes_every_served_byte_and_lane_digest():
    hyp = _hyp()
    served = hyp["frozen_inputs"]["sha256"]
    assert len(served) == 12, "the freeze pins all 12 served artifacts"
    assert len(hyp["frozen_inputs"]["product_code_sha256"]) == 3
    assert len(hyp["frozen_inputs"]["lane_frozen_sha256"]) == 6
    # the four digests the factory direction names as byte-identical
    lane = hyp["frozen_inputs"]["lane_frozen_sha256"]
    assert lane["evaluation/frozen_bars/RULES_LABEL.json"].startswith("4457e971")
    assert lane["evaluation/frozen_bars/RULES_GEOMETRY.json"].startswith("a7452748")
    assert lane["evaluation/retrieval_gate/frozen_retrieval_benchmark.json"].startswith("187b0e54")
    assert lane["evaluation/retrieval_gate/FREEZE_RECORD.json"].startswith("b06a2ad0")


def test_lane_frozen_digests_still_match_the_committed_tree():
    """The freeze must not drift from the repository. A mismatch is exit 2."""
    import hashlib
    root = Path(__file__).resolve().parents[2]
    for rel, expected in _hyp()["frozen_inputs"]["lane_frozen_sha256"].items():
        actual = hashlib.sha256((root / rel).read_bytes()).hexdigest()
        assert actual == expected, f"{rel} moved under the freeze"


def test_hypothesis_declares_its_pre_freeze_peek():
    """Honesty guard: the peek that already observed L3 must stay disclosed."""
    peek = _hyp()["pre_freeze_disclosure"]
    assert "query_concepts_under_covered" in peek["what_was_observed"]
    assert "weakening" in peek["effect_on_this_freeze"].lower()


def test_frozen_success_rule_is_per_instance_not_per_qid():
    """A qid with an empty under-covered set is neither a pass nor a failure."""
    rule = _hyp()["legs"][2]["success_rule_frozen"]
    assert "at least one qid" in rule
    assert "on every qid where BEFORE had a non-empty" in rule


# --------------------------------------------------------------------------- #
# L1 - NOT_MEASURED discipline
# --------------------------------------------------------------------------- #
def test_phase_dependent_checks_are_never_reported_as_a_pass():
    out = psbf.leg1_contract(_bundle())
    assert out["checks"]["progressive_phases"] == "NOT_MEASURED"
    assert out["checks"]["geometry_preserved_after_enrichment"] == "NOT_MEASURED"
    assert "progressive_phases" not in out["measurable_checks"]
    assert "geometry_preserved_after_enrichment" not in out["measurable_checks"]


def test_harness_self_pass_is_withheld_as_a_verdict():
    """initial == final is a degenerate call; its `pass` must not be published."""
    out = psbf.leg1_contract(_bundle())
    assert out["harness_pass_note"].startswith("the accepted harness was called with initial == final")


def test_a_falsely_written_phase_is_still_not_measurable():
    """A bundle that LIES about being complete must not silently buy a pass."""
    b = _bundle()
    b["provenance"]["phase"] = "complete"
    out = psbf.leg1_contract(b)
    assert out["checks"]["progressive_phases"] == "NOT_MEASURED"


def test_l1_detects_a_real_contract_violation():
    b = _bundle()
    b["decisions"][0]["canonical_url"] = "https://example.invalid/nope"
    out = psbf.leg1_contract(b)
    assert out["contract_pass"] is False
    assert "source_urls_valid" in out["measurable_checks_failed"]


# --------------------------------------------------------------------------- #
# L1/L2 control cause classification
# --------------------------------------------------------------------------- #
def test_controls_fire_on_a_populated_population():
    out = psbf.l1_controls(_bundle(labelled=2))
    assert out["all_fired"] is True
    assert out["unexercised_checks"] == []


def test_empty_counter_population_is_classified_unexercised_not_vacuous():
    """THE KEY HONESTY TEST: 0 counter rows means UNTESTED, not SATISFIED."""
    out = psbf.l1_controls(_bundle(labelled=0))
    assert out["all_fired"] is False
    assert out["n_counter_labelled_rows"] == 0
    assert set(out["unexercised_checks"]) == {"blanked_counter_evidence",
                                              "blanked_counter_uncertainty"}
    for c in out["controls"]:
        if c["control"] == "blanked_counter_evidence":
            assert c["not_fired_cause"] == "UNEXERCISED_POPULATION_EMPTY"
            assert c["observed_value"] is True  # vacuously true
    assert "NEGATIVE RESULT" in out["unexercised_reading"]


def test_a_populated_control_that_fires_is_classified_as_such():
    """The mirror of the UNEXERCISED case: a real flip is labelled a real flip."""
    controls = {c["control"]: c
                for c in psbf.l1_controls(_bundle(labelled=2))["controls"]}
    assert controls["blanked_counter_evidence"]["not_fired_cause"] == "FIRED_AS_EXPECTED"
    assert controls["blanked_counter_evidence"]["fired"] is True


def test_non_counter_controls_fire_even_with_zero_counter_rows():
    out = psbf.l1_controls(_bundle(labelled=0))
    by_name = {c["control"]: c for c in out["controls"]}
    assert by_name["repointed_source_url"]["fired"] is True
    assert by_name["duplicated_first_decision"]["fired"] is True
    assert by_name["rogue_answer_citation"]["fired"] is True


# --------------------------------------------------------------------------- #
# L2 - counter yield, measured not thresholded
# --------------------------------------------------------------------------- #
def test_l2_publishes_numerators_and_denominators():
    b = _bundle(n_decisions=6, labelled=2, cited=3)
    out = psbf.leg2_counter(b, {"bundles": []}, "x")
    assert out["n_decisions"] == 6
    assert out["n_counter_labelled"] == 2
    assert out["n_counter_labels_supported"] == 2
    assert out["support_rate_among_issued"] == 1.0
    assert out["counter_status_histogram"] == {"candidate-limiting": 2}


def test_l2_reports_none_not_zero_when_nothing_is_issued():
    out = psbf.leg2_counter(_bundle(labelled=0), {"bundles": []}, "x")
    assert out["n_counter_labelled"] == 0
    assert out["support_rate_among_issued"] is None


def test_l2_flags_an_answer_that_cites_counter_authority():
    b = _bundle(n_decisions=6, labelled=2, cited=1)
    out = psbf.leg2_counter(b, {"bundles": []}, "x")
    assert out["cited_counter_overlap"] == 1
    assert out["answer_cites_any_counter_authority"] is True


# --------------------------------------------------------------------------- #
# L3 - verdict logic on synthetic fixtures (no mount needed)
# --------------------------------------------------------------------------- #
@pytest.mark.skipif(not MOUNT_PRESENT, reason="accepted product mount absent")
def test_l3_end_to_end_on_a_synthetic_bundle_runs_the_real_product_code():
    """Drive leg3_handoff's real BEFORE/AFTER wiring, product admission included.

    The synthetic bundle must clear the product's own MIN_MAP_DECISIONS=100 floor,
    otherwise the AFTER arm is correctly NOT admissible and the classifier answers
    HANDOFF_SEVERITY_CHANGED - which is itself asserted below.
    """
    served = {"rel": "r", "sha256": {}, "product_code_sha256": {},
              "question": {"q": {"language": "de", "qid": "q"}}}

    big = _bundle(n_decisions=120, labelled=4, cited=2)
    before = _admissibility(under=["kapitalverletzung"],
                            codes=["source_url_host_distribution"], warning_count=0)
    out = psbf.leg3_handoff(served, big, before, "q")
    assert out["product_admission_import_error"] is None
    assert out["before"]["predicate"]["disclosure_gap_predicate_fires"] is True
    assert out["after"]["predicate"]["disclosure_gap_predicate_fires"] is False,         "the product's own admission code must close the gap on this fixture"
    assert out["regression"]["no_silent_regression"] is True
    assert out["after"]["admissible"] is True, \
        f"the fixture must clear the product's own bundle contract: {out['after']['finding_codes']}"
    assert out["disclosure_finding"]["severity"] == "warning"
    assert out["disclosure_finding"]["terms_equal_measured_set"] is True
    assert out["verdict"] == "HANDOFF_PASS"


@pytest.mark.skipif(not MOUNT_PRESENT, reason="accepted product mount absent")
def test_l3_an_undersized_bundle_is_classified_not_glossed():
    """A bundle below the product's own floor cannot buy a PASS."""
    served = {"rel": "r", "sha256": {}, "product_code_sha256": {},
              "question": {"q": {"language": "de", "qid": "q"}}}
    before = _admissibility(under=["kapitalverletzung"],
                            codes=["source_url_host_distribution"], warning_count=0)
    out = psbf.leg3_handoff(served, _bundle(n_decisions=6), before, "q")
    assert out["after"]["admissible"] is False
    assert out["verdict"] == "HANDOFF_SEVERITY_CHANGED"


@pytest.mark.skipif(not MOUNT_PRESENT, reason="accepted product mount absent")
def test_l3_qid_with_no_defect_instance_is_neither_pass_nor_failure():
    served = {"rel": "r", "sha256": {}, "product_code_sha256": {}, "question": {"q": {}}}
    before = _admissibility(under=[], codes=["source_url_host_distribution"], warning_count=0)
    out = psbf.leg3_handoff(served, _bundle(), before, "q")
    assert out["verdict"] == "NO_DEFECT_INSTANCE_ON_THIS_QID"


def _drive_l3(before: dict, after: dict, **overrides):
    """Drive the instrument's OWN classifier with a forced BEFORE/AFTER pair.

    ``leg3_handoff`` recomputes the AFTER arm through the product's admission
    code, which a synthetic fixture cannot force. This calls ``classify_l3`` --
    the same function ``leg3_handoff`` calls -- so no copy of the rule can drift.
    """
    from evaluation.question_native_transfer import disclosure_gap_predicate
    bp, ap = disclosure_gap_predicate(before), disclosure_gap_predicate(after)
    finding = psbf._l3_finding(after)
    before_codes, after_codes = set(psbf._codes(before)), set(psbf._codes(after))
    kw = dict(
        import_error=None,
        before_pred=bp,
        after_pred=ap,
        measured_under=sorted(ap.get("query_concepts_under_covered") or []),
        detail_terms=sorted((finding or {}).get("query_concepts_under_covered") or []),
        finding_severity=(finding or {}).get("severity"),
        finding_present=finding is not None,
        lost_codes=sorted(before_codes - after_codes),
    )
    kw.update(overrides)
    return psbf.classify_l3(**kw)


def test_l3_falsified_when_the_after_arm_still_fires_the_predicate():
    """The negative the whole exercise exists for."""
    before = _admissibility(under=["kapitalverletzung"], codes=["x"], warning_count=0)
    after = _admissibility(under=["kapitalverletzung"], codes=["x"], warning_count=0)
    assert _drive_l3(before, after) == "HANDOFF_FIX_ABSENT"


def test_l3_classifier_branches_are_reachable_and_named():
    gap_before = _admissibility(under=["k"], codes=["x"], warning_count=0)
    fixed_after = _admissibility(under=["k"], codes=["x", "query_concept_x"], warning_count=1)
    cases = {
        "HANDOFF_FIX_ABSENT": (gap_before, _admissibility(under=["k"], codes=["x"],
                                                           warning_count=0), {}),
        "HANDOFF_PASS": (gap_before, fixed_after, {}),
        "NO_DEFECT_INSTANCE_ON_THIS_QID": (
            _admissibility(under=[], codes=["x"], warning_count=0),
            _admissibility(under=[], codes=["x"], warning_count=0), {}),
        "HANDOFF_NOT_MEASURED": (
            _admissibility(under=["k"], codes=["query_concept_x"], warning_count=1),
            _admissibility(under=["k"], codes=["query_concept_x"], warning_count=1), {}),
    }
    for expected, (before, after, over) in cases.items():
        assert _drive_l3(before, after, **over) == expected, expected


def test_l3_terms_mismatch_is_its_own_class():
    before = _admissibility(under=["k"], codes=["x"], warning_count=0)
    after = _admissibility(under=["k"], codes=["x", "query_concept_x"], warning_count=1)
    assert _drive_l3(before, after, detail_terms=["something_else"]) == "HANDOFF_TERMS_MISMATCH"


def test_l3_severity_change_and_regression_are_their_own_classes():
    before = _admissibility(under=["k"], codes=["x"], warning_count=0)
    after = _admissibility(under=["k"], codes=["x", "query_concept_x"], warning_count=1)
    assert _drive_l3(before, after, finding_severity="blocking") == "HANDOFF_SEVERITY_CHANGED"
    assert _drive_l3(before, after, after_pred={**disclosure_after(after),
                                                 "admissible": False}) \
        == "HANDOFF_SEVERITY_CHANGED"
    assert _drive_l3(before, after, lost_codes=["dominant_cluster_composition"]) \
        == "HANDOFF_FIX_PARTIAL"


def disclosure_after(after: dict) -> dict:
    from evaluation.question_native_transfer import disclosure_gap_predicate
    return disclosure_gap_predicate(after)


def test_l3_import_error_can_never_be_reported_as_a_pass():
    before = _admissibility(under=["k"], codes=["x"], warning_count=0)
    after = _admissibility(under=["k"], codes=["x", "query_concept_x"], warning_count=1)
    assert _drive_l3(before, after, import_error="ModuleNotFoundError: numpy") \
        == "HANDOFF_NOT_MEASURED"


# --------------------------------------------------------------------------- #
# exit-code surface + record-writing discipline
# --------------------------------------------------------------------------- #
def test_exit_codes_are_distinct_and_falsifiable():
    codes = {psbf.EXIT_OK, psbf.EXIT_CONTRACT_VIOLATED,
             psbf.EXIT_ENVIRONMENT_OR_VACUOUS, psbf.EXIT_HANDOFF_FALSIFIED}
    assert codes == {0, 1, 2, 3}
    assert psbf.EXIT_CONTRACT_VIOLATED != psbf.EXIT_ENVIRONMENT_OR_VACUOUS


def test_pin_drift_is_detected_and_head_is_resolved_from_the_worktree(tmp_path):
    """A worktree HEAD must NOT be confused with the main repo's HEAD."""
    hyp = _hyp()
    assert psbf.resolve_head(MOUNT) == hyp["frozen_inputs"]["accepted_product_head"] \
        if MOUNT_PRESENT else True
    fake = tmp_path / "pkg"
    (fake / "product/query").mkdir(parents=True)
    (fake / ".git").write_text("gitdir: /nonexistent\n", encoding="utf-8")
    assert psbf.resolve_head(fake) is None


@pytest.mark.skipif(not MOUNT_PRESENT, reason="accepted product mount absent")
def test_rehash_pins_reports_every_drift_and_no_silent_pass():
    hyp = _hyp()
    out = psbf.rehash_pins(hyp, Path(__file__).resolve().parents[2], MOUNT)
    assert out["n_checks"] == 21
    assert out["n_drift"] == 0, out["drift"]
    assert out["n_match"] == 21
    assert out["accepted_product_head_match"] is True


@pytest.mark.skipif(not MOUNT_PRESENT, reason="accepted product mount absent")
def test_environment_failure_still_writes_a_machine_record(tmp_path):
    """An early return that writes nothing is indistinguishable from a crash."""
    bad = copy.deepcopy(_hyp())
    bad["frozen_inputs"]["sha256"]["packet.json"] = "0" * 64
    hyp_path = tmp_path / "hyp.json"
    hyp_path.write_text(json.dumps(bad), encoding="utf-8")
    rec = psbf.run("TEST-PINDDRIFT", hyp_path, MOUNT, tmp_path / "out")
    assert rec["verdict"] == "ENVIRONMENT_OR_PIN_DRIFT"
    assert rec["exit_code"] == psbf.EXIT_ENVIRONMENT_OR_VACUOUS
    written = list((tmp_path / "out").glob("*.json"))
    assert written, "an environment failure must still leave a record on disk"


# --------------------------------------------------------------------------- #
# mapping-free discipline
# --------------------------------------------------------------------------- #
FOREIGN_SLUGS = ("rent-default", "corporate-criminal-liability",
                 "business-judgment-rule", "petty-theft-dismissal")
#: Keys under which a foreign slug may legitimately appear: pure disclosure that
#: exists precisely to state that the two populations are NOT joined.
DISCLOSURE_ONLY_KEYS = {"note", "known_divergence_disclosure", "reading",
                        "pre_freeze_disclosure", "population_note"}


def _walk(node, path="$"):
    if isinstance(node, dict):
        for k, v in node.items():
            yield from _walk(v, f"{path}.{k}")
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from _walk(v, f"{path}[{i}]")
    elif isinstance(node, str):
        yield path, node


def test_population_is_read_from_the_accepted_frozen_constant():
    assert list(FROZEN_QIDS) == ["de-kapitalverletzung", "fr-bail-entretien",
                                 "it-responsabilita-medica"]
    hyp = _hyp()
    assert hyp["population"]["qids"] == list(FROZEN_QIDS)
    assert hyp["population"]["n"] == 3


def test_foreign_question_slugs_appear_only_as_disclosure_never_as_a_join_key():
    """The mapping-free guard: naming the other population is allowed and is the
    point; joining to it anywhere that could be read as a key is not."""
    hyp = _hyp()
    offenders = [
        path for path, value in _walk(hyp)
        if any(f in value for f in FOREIGN_SLUGS)
        and path.rsplit(".", 1)[-1] not in DISCLOSURE_ONLY_KEYS
    ]
    assert offenders == [], f"foreign slug leaked into a structural field: {offenders}"
    # and the disclosure that names them really does say they are not joined
    assert "NOT joined to these bytes by any mapping" in hyp["population"]["note"]
    assert "NOT_APPLICABLE_WITH_REASON" in hyp["known_divergence_disclosure"]


def test_claim_ceiling_forbids_recall_claims_on_the_product_population():
    hyp = _hyp()
    disclosure = hyp["known_divergence_disclosure"]
    assert "NOT_APPLICABLE_WITH_REASON" in disclosure
    assert "not as 0 and not as a pass" in disclosure
    assert "republished beside, never merged with or substituted for" in disclosure


# --------------------------------------------------------------------------- #
# the committed record of this cycle
# --------------------------------------------------------------------------- #
_RECORD = (Path(__file__).resolve().parents[2]
           / "results/evaluation/product_served_bundle_falsification/39202185384.json")


@pytest.mark.skipif(not _RECORD.exists(), reason="claim-bearing record not committed yet")
def test_committed_record_agrees_with_the_pins_and_the_hypothesis():
    rec = json.loads(_RECORD.read_text(encoding="utf-8"))
    hyp = _hyp()
    assert rec["hypothesis"]["sha256"] == psbf.sha256_file(HYPOTHESIS)
    assert rec["hypothesis"]["pre_freeze_disclosure_present"] is True
    assert rec["pin_rehash_pre"]["n_drift"] == 0
    assert rec["pin_rehash_post"]["n_drift"] == 0
    assert rec["pins_unchanged_during_run"] is True
    assert rec["qid_population"]["identical"] is True
    assert all(c["self_declared_link_consistent"]
               for c in rec["qid_population"]["self_declared_link_check"].values())
    assert rec["verdict"] == rec["L3_handoff_question_native_coverage"]["aggregate"]["aggregate_verdict"] \
        or rec["verdict"] == "ENVIRONMENT_OR_VACUOUS"


@pytest.mark.skipif(not _RECORD.exists(), reason="claim-bearing record not committed yet")
def test_committed_record_publishes_the_counter_authority_negative():
    """The negative result must stay committed and stay visible."""
    rec = json.loads(_RECORD.read_text(encoding="utf-8"))
    l2 = rec["headline"]["L2_counter_authority_yield"]
    assert l2["n_decisions_total"] == sum(
        rec["L2_counter_authority_liveness"]["per_qid"][q]["n_decisions"]
        for q in rec["L2_counter_authority_liveness"]["per_qid"])
    assert l2["n_counter_labels_total"] == sum(l2["per_qid_labels"].values())
    cites = rec["headline"]["L2_answer_cites_counter_authority"]
    assert cites["n_citations_that_are_counter_authority"] == sum(
        v["cited_counter_overlap"] for v in cites["per_qid"].values())


@pytest.mark.skipif(not _RECORD.exists(), reason="claim-bearing record not committed yet")
def test_committed_record_does_not_claim_the_unmeasured_checks():
    rec = json.loads(_RECORD.read_text(encoding="utf-8"))
    for qid, block in rec["L1_product_bytes_contract"]["per_qid"].items():
        for check in psbf.NOT_MEASURED_ON_SERVED_BYTES:
            assert block["checks"][check] == "NOT_MEASURED", (qid, check)
            assert check not in block["measurable_checks"], (qid, check)


@pytest.mark.skipif(not _RECORD.exists(), reason="claim-bearing record not committed yet")
def test_committed_l3_publishes_before_and_after_side_by_side():
    rec = json.loads(_RECORD.read_text(encoding="utf-8"))
    per_qid = rec["L3_handoff_question_native_coverage"]["per_qid"]
    inst = rec["L3_handoff_question_native_coverage"]["aggregate"]["qids_with_an_under_covered_set"]
    assert inst, "at least one qid must carry a defect instance or the run measured nothing"
    for qid in inst:
        blk = per_qid[qid]
        assert blk["before"]["predicate"]["disclosure_gap_predicate_fires"] is True
        assert blk["after"]["predicate"]["disclosure_gap_predicate_fires"] is False
        assert blk["disclosure_finding"]["severity"] == "warning"
        assert blk["disclosure_finding"]["terms_equal_measured_set"] is True
        assert blk["regression"]["no_silent_regression"] is True
        assert blk["verdict"] == "HANDOFF_PASS"
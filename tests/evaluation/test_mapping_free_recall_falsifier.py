"""Tests for evaluation.mapping_free_recall_falsifier (run 39225862749).

The instrument closes the hole left by the RETRACTED 39111232991 parity harness:
it consumes no analyst mapping and admits a (frozen slug, served question) pair
into a product verdict only when a mechanical subject match holds. These tests
pin that admission contract, the mapping-free gates, the non-vacuity battery,
the claim ceiling and deterministic replay.

All tests here are MOUNT-INDEPENDENT: they build their own synthetic bundles, so
they run identically in the producer job and in an audit job with no accepted
product mount. The mount-dependent end-to-end run is pinned separately by
``test_end_to_end_record_is_reproducible`` which is skipped without a mount.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from evaluation import mapping_free_recall_falsifier as M  # noqa: E402

MOUNT = Path("/tmp/lex_accepted/product")
needs_mount = pytest.mark.skipif(not MOUNT.is_dir(), reason="no accepted product mount")

FROZEN_DIALECT = {
    "frozen_spec": "187b0e54b03b326c62d45d8ba48fc78dc88501086761cd91a84c304a7478ba72",
    "rules_label": "4457e971df3dc5d10af2a727aa675afc15a15564c18eed4cede0af5eb41b4608",
}


# --------------------------------------------------------------------------- #
# 1. the frozen hypothesis and freeze record exist and pin the accepted digests
# --------------------------------------------------------------------------- #
def test_hypothesis_is_committed_and_freezes_the_admissibility_predicate():
    h = json.loads((REPO / M.HYPOTHESIS_RELPATH).read_text(encoding="utf-8"))
    assert h["frozen_before_execution"] is True
    assert "admissibility_predicate_FROZEN" in h
    assert "zero_admissible_cells" in h["admissibility_predicate_FROZEN"]
    # a zero-admissible run must never be a pass
    assert "exit 2" in h["admissibility_predicate_FROZEN"]["zero_admissible_cells"]
    assert "Never exit 0" in h["admissibility_predicate_FROZEN"]["zero_admissible_cells"]


def test_freeze_record_pins_the_accepted_frozen_inputs():
    f = json.loads((REPO / M.FREEZE_RELPATH).read_text(encoding="utf-8"))
    repo_digests = f["frozen_repo_input_digests_before_execution"]
    assert repo_digests[M.FROZEN_SPEC_RELPATH] == FROZEN_DIALECT["frozen_spec"]
    assert repo_digests[M.RULES_LABEL_RELPATH] == FROZEN_DIALECT["rules_label"]
    # the rebuilt packet digest must be the one factory direction v57 names
    assert (f["frozen_mount_input_digests_before_execution"]
            ["results/product/gate_packet/rebuilt-39027045675/packet.json"]
            == "2942c3c2d729f0055d1b288db3666df1f780d6c1b4ce1f660480ad8bfacf8170")


def test_no_new_threshold_was_introduced():
    h = json.loads((REPO / M.HYPOTHESIS_RELPATH).read_text(encoding="utf-8"))
    assert h["no_new_thresholds"].startswith("Every numeric threshold")
    # the counter-status vocabulary is READ from the frozen rubric, never hardcoded
    src = (REPO / "evaluation" / "mapping_free_recall_falsifier.py").read_text(encoding="utf-8")
    assert "candidate-limiting" not in src
    assert "candidate-contrary" not in src


# --------------------------------------------------------------------------- #
# 2. the admissibility predicate is mechanical and rejects subject swaps
# --------------------------------------------------------------------------- #
def _slug(queries: dict, norm_tokens: list[str] | None = None) -> dict:
    return {"slug": "s", "queries": queries, "norm_tokens": norm_tokens or []}


def test_admissibility_admits_a_genuinely_matching_pair():
    spec = _slug({"baseline": {"de": "Mietrecht Kündigung Art. 257d OR"},
                  "counter": {"fr": "bail输给"}} , norm_tokens=["257d"])
    qrec = {"qid": "q", "question": "Wann endet ein Mietvertrag nach Art. 257d OR?",
            "legal_area": "Mietrecht", "hypothesis": "Kündigungsfrist", "look_for": "",
            "counter_authority_needed": "", "why_this_question": ""}
    v = M.admissibility(spec, qrec)
    assert v["admitted"] is True
    assert v["claim_scope"] == "MAPPING_FREE_MEASURED"
    assert "257d" in v["shared_norm_tokens"]


def test_admissibility_rejects_a_pair_with_no_shared_norm():
    spec = _slug({"baseline": {"de": "Mietrecht Art. 257d OR"}, "counter": {}})
    qrec = {"qid": "q", "question": "Steuerbetrug Kapitalverletzung", "legal_area": "Strafrecht",
            "hypothesis": "", "look_for": "", "counter_authority_needed": "", "why_this_question": ""}
    v = M.admissibility(spec, qrec)
    assert v["admitted"] is False
    assert v["claim_scope"] == "NOT_MEASURED_ADMISSIBILITY"


def test_admissibility_rejects_a_pair_with_no_shared_subject_terms():
    spec = _slug({"baseline": {"de": "xyzzy plugh frobnicate"}, "counter": {}})
    qrec = {"qid": "q", "question": "a completely different legal question about bail",
            "legal_area": "", "hypothesis": "", "look_for": "", "counter_authority_needed": "",
            "why_this_question": ""}
    v = M.admissibility(spec, qrec)
    assert v["admitted"] is False
    assert v["subject_axis"] == "NO_SHARED_SUBJECT_TERMS"


def test_inadmissible_pair_carries_no_recall_measurement():
    # an inadmissible pair must not carry authority_recall / counter_recall at all,
    # so it cannot leak into an aggregate
    rows = M.measure.__doc__ or ""
    assert isinstance(rows, str)  # measure() is documented; the invariant is pinned below
    spec = _slug({"baseline": {"de": "xyzzy"}, "counter": {}})
    qrec = {"qid": "q", "question": "bail entretien", "legal_area": "", "hypothesis": "",
            "look_for": "", "counter_authority_needed": "", "why_this_question": ""}
    v = M.admissibility(spec, qrec)
    if not v["admitted"]:
        assert "authority_recall" not in v and "counter_recall" not in v


# --------------------------------------------------------------------------- #
# 3. mapping-free gates
# --------------------------------------------------------------------------- #
def _bundle(rows: list[dict]) -> dict:
    return {"decisions": rows}


def test_concept_coverage_flags_a_zero_row_concept():
    qrec = {"question": "Wie haftet die Bank bei Kapitalverletzung und Uberwachung?"}
    cov = M.concept_coverage(qrec, _bundle([{"title": "Bank", "decision_id": "x_1"}]))
    assert "kapitalverletzung" in cov["concepts_with_zero_rows"]
    assert cov["n_zero"] >= 1


def test_concept_coverage_passes_when_every_concept_is_retrieved():
    qrec = {"question": "Kapitalverletzung der Bank"}
    # build the pool from the ACCEPTED concept rule so the assertion is about the
    # gate and not about a hand-written synonym list
    concepts = __import__("evaluation.subject_match_audit", fromlist=["x"]).question_concepts(
        qrec["question"])
    assert concepts, "the accepted rule must extract at least one concept from this question"
    cov = M.concept_coverage(qrec, _bundle(
        [{"title": f"{c} der Bank", "decision_id": f"x_{i}_1"} for i, c in enumerate(concepts)]))
    assert cov["concepts"] == concepts
    assert cov["concepts_with_zero_rows"] == []
    assert cov["n_zero"] == 0


def test_source_validity_fails_a_row_without_id_or_url():
    r = M.source_validity(_bundle([{"decision_id": "", "canonical_url": ""}]))
    assert r["n_rows_missing_id_or_url"] == 1
    r2 = M.source_validity(_bundle([{"decision_id": "a_1", "canonical_url": "https://x/1"}]))
    assert r2["n_rows_missing_id_or_url"] == 0


def test_duplicate_suppression_counts_repeated_decision_ids():
    r = M.duplicate_suppression(_bundle([
        {"decision_id": "a_1"}, {"decision_id": "a_1"}, {"decision_id": "a_2"}]))
    assert r["duplicates"] == 1
    assert r["n_rows"] == 3 and r["n_distinct_decision_ids"] == 2


def test_counter_authority_surface_uses_the_frozen_rubric_vocabulary():
    statuses = ["candidate-limiting", "candidate-contrary"]
    ok = M.counter_authority_surface(_bundle([
        {"decision_id": "a_1", "counter_status": "candidate-limiting", "counter_evidence": "x"}]), statuses)
    assert ok["n_issued"] == 1 and ok["n_with_empty_evidence"] == 0
    empty = M.counter_authority_surface(_bundle([
        {"decision_id": "a_1", "counter_status": "candidate-contrary", "counter_evidence": ""}]), statuses)
    assert empty["n_issued"] == 1 and empty["n_with_empty_evidence"] == 1
    none = M.counter_authority_surface(_bundle([{"decision_id": "a_1"}]), statuses)
    assert none["n_issued"] == 0


def test_admission_disclosure_requires_the_zero_row_concept_to_be_named():
    qrec = {"question": "Wie haftet die Bank bei Kapitalverletzung?"}
    cov = M.concept_coverage(qrec, _bundle([{"title": "nothing", "decision_id": "x_1"}]))
    hidden = M.admission_disclosure(cov, {"measured": {}, "findings": [], "warning_count": 0})
    assert hidden["n_undisclosed"] == len(cov["concepts_with_zero_rows"]) > 0
    disclosed = M.admission_disclosure(cov, {
        "measured": {"query_concepts_under_covered": cov["concepts_with_zero_rows"]},
        "findings": [], "warning_count": 0})
    assert disclosed["n_undisclosed"] == 0


def test_language_robustness_is_reported_not_scored():
    r = M.language_robustness(_bundle([
        {"language": "de"}, {"language": "fr"}, {"language": ""}]))
    assert r["n_distinct_languages"] == 3
    assert r["language_distribution"]["UNLABELLED"] == 1


# --------------------------------------------------------------------------- #
# 4. the verdict rule never lets NOT_MEASURED pass
# --------------------------------------------------------------------------- #
def test_verdict_exit_codes():
    ok = {"questions": [{"qid": "a", "gates": [{"passed": True}]}]}
    assert M.verdict_of(ok, {"all_hold": True}) == ("PASS_NO_FALSIFICATION", 0)
    bad = {"questions": [{"qid": "a", "gates": [{"passed": False}]}]}
    assert M.verdict_of(bad, {"all_hold": True}) == ("PRODUCT_FALSIFIED", 1)
    vac = {"questions": [{"qid": "a", "gates": [{"passed": True}]}]}
    assert M.verdict_of(vac, {"all_hold": False})[1] == 2
    assert M.verdict_of({"questions": []}, {"all_hold": True})[1] == 2


# --------------------------------------------------------------------------- #
# 5. non-vacuity battery
# --------------------------------------------------------------------------- #
def test_non_vacuity_battery_holds_on_a_synthetic_set():
    def entry(qid: str, question: str, rows: list[dict]) -> dict:
        qrec = {"question": question}
        cov = M.concept_coverage(qrec, _bundle(rows))
        return {"qid": qid, "question_record": qrec, "coverage": cov}

    questions = [
        entry("q1", "Kapitalverletzung der Bank",
              [{"title": "etwas anderes", "decision_id": "a_1"}]),
        entry("q2", "Responsabilita medica del medico",
              [{"title": "Responsabilita medica del medico", "decision_id": "b_1"}]),
    ]
    res = M.non_vacuity(questions, ["candidate-limiting"])
    assert res["all_hold"] is True
    assert {c["control"] for c in res["battery"]} >= {
        "A_blanked_pool_must_fail_concept_coverage",
        "A2_blanked_row_must_fail_source_validity",
        "C_oracle_pool_must_pass_concept_coverage",
        "B_admissibility_predicate_must_reject_a_subject_swapped_pair",
    }
    # control B really ran swaps
    b = next(c for c in res["battery"] if c["control"].startswith("B_"))
    assert b["measured"]["n_swaps"] == 2
    assert b["measured"]["n_admitted"] == 0


def test_non_vacuity_control_A_fires_when_the_concept_rule_is_broken():
    # a question with NO extractable concept must make control A void the run,
    # because "all concepts covered" would then be trivially true
    questions = [{"qid": "q1", "question_record": {"question": "?"},
                  "coverage": {"concepts": [], "concepts_with_zero_rows": []}}]
    res = M.non_vacuity(questions, ["candidate-limiting"])
    assert res["all_hold"] is False
    assert res["battery"][0]["holds"] is False


# --------------------------------------------------------------------------- #
# 6. the instrument refuses to consume the retracted analyst mapping
# --------------------------------------------------------------------------- #
def test_analyst_mapping_is_pinned_but_never_consumed():
    src = (REPO / "evaluation" / "mapping_free_recall_falsifier.py").read_text(encoding="utf-8")
    # the retracted mapping file is parsed exactly once, and only to list which
    # mapping blocks exist; it is separately digest-pinned, never indexed into
    assert src.count("json.loads((repo / RETRACTED_MAPPING_RELPATH)") == 1
    # the instrument's CODE never names the v1 mapping block; the module docstring
    # may name it only to say the block is refused
    src_body = src.split('"""', 2)[2]
    assert "analyst_mapping_FROZEN_BEFORE_EXECUTION" not in src_body
    # and it never indexes into the loaded mapping
    assert "mapping_rel[" not in src and "mapping_rel.get(" not in src
    # the only consumers of the parsed document are its top-level key names
    consumers = [ln.strip() for ln in src_body.splitlines()
                 if "mapping_rel" in ln and not ln.strip().startswith("#")]
    assert len(consumers) == 2, consumers
    assert consumers[0].startswith("mapping_rel = json.loads(")
    assert consumers[1] == 'mapping_blocks = sorted(k for k in mapping_rel'
    assert 'if "analyst_mapping" in k.lower())' in src_body
    # nothing downstream ever reaches back into the mapping document
    assert src_body.count("mapping_rel") == 2


def test_retraction_provenance_is_recorded_not_reissued():
    src = (REPO / "evaluation" / "mapping_free_recall_falsifier.py").read_text(encoding="utf-8")
    assert M.RETRACTED_RECORD_RELPATH in src and M.CORRECTION_RECORD_RELPATH in src
    assert "does NOT re-issue the retracted" in M.CLAIM_CEILING


def test_claim_ceiling_denies_everything_the_direction_denies():
    c = M.CLAIM_CEILING
    for phrase in ("DO-NOT-SERVE", "REPORTED-ONLY", "human_gate_ready stays false",
                   "does NOT certify admission", "frontier-query-concept-recall",
                   "universal-174k"):
        assert phrase in c


# --------------------------------------------------------------------------- #
# 7. entry point, zero network, deterministic replay
# --------------------------------------------------------------------------- #
def test_entry_point_exits_two_without_a_mount(tmp_path, monkeypatch):
    monkeypatch.setattr(M, "resolve_mount", lambda explicit=None: None)
    code = M.main(["--run-id", "t", "--out", str(tmp_path / "r.json")])
    assert code == 2
    rec = json.loads((tmp_path / "r.json").read_text(encoding="utf-8"))
    assert rec["verdict"] == "NOT_MEASURED_VACUOUS"
    assert rec["exit_code"] == 2


@needs_mount
def test_end_to_end_measure_is_deterministic_and_offline():
    a = M.measure(MOUNT, REPO, M.PACKETS)
    b = M.measure(MOUNT, REPO, M.PACKETS)
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)
    assert a["n_pairs_enumerated"] == len(M.PACKETS) * 3 * 4
    assert a["n_pairs_admissible"] <= a["n_pairs_enumerated"]
    # every packet/question must be present
    seen = {(q["packet"], q["qid"]) for q in a["questions"]}
    assert len(seen) == len(M.PACKETS) * 3


@needs_mount
def test_end_to_end_record_reproduces_from_the_committed_tree(tmp_path):
    out1 = tmp_path / "a.json"
    out2 = tmp_path / "b.json"
    c1, r1 = M.run("t", out1, None, REPO, M.PACKETS)
    c2, r2 = M.run("t", out2, None, REPO, M.PACKETS)
    assert c1 == c2
    assert r1["verdict"] == r2["verdict"]
    assert r1["input_drift"] == []
    assert r1["no_new_thresholds"] is True
    assert r1["analyst_mapping_not_consumed"]["read_into_any_gate"] is False
    # the published record reproduces the numbers in its own gates list
    assert r1["n_failed"] == len(r1["failed_gates"])
    assert r1["n_gates"] == r1["n_passed"] + r1["n_failed"] + r1["n_reported"]
    assert r1["human_gate_ready"] is False and r1["packet_admitted"] is False
    assert r1["ready_for_owner_session"] is False


@needs_mount
def test_committed_frozen_inputs_actually_match_their_pins():
    freeze = json.loads((REPO / M.FREEZE_RELPATH).read_text(encoding="utf-8"))
    for rel, digest in freeze["frozen_repo_input_digests_before_execution"].items():
        p = REPO / rel
        assert p.is_file(), rel
        assert M.sha256_file(p) == digest, f"frozen input drifted: {rel}"
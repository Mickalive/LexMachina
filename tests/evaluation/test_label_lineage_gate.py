"""Population-free counter-label LINEAGE gate: pins, predicates, non-vacuity, refusals.

Scope of these tests, stated so nothing here is over-read:

* The enforced predicate uses EXACTLY ONE number, 5/65, and that number is
  DERIVED at runtime from the accepted pinned incumbent
  (label_gate.INCUMBENT['n_supported'] / label_gate.INCUMBENT['n_scored']). A test
  asserts the derivation, so a re-typed or retuned threshold fails here.
* The gate is ADDITIVE. The accepted label_gate verdict is never overwritten; a
  test asserts the accepted verdict is still present side by side.
* Direction v50's absolute bars stay reported-not-enforced; a test asserts that.
* Mount-dependent tests skip when the accepted product mount is absent; the
  predicate, contract, digest, refusal and minimal-delta tests do not need it.
"""
import json
from pathlib import Path

import pytest

from evaluation.frozen_bars import geometry_gate, label_gate, label_lineage_gate
from evaluation.frozen_bars.label_lineage_gate import (
    EXPECTED_VERDICT_CONTRACT_SHA256,
    LINEAGE_QIDS,
    PREDICATE_RATE,
    VERDICT_CONTRACT_PATH,
)
from evaluation.frozen_bars.run_label_lineage_gate import (
    ACCEPTED_PACKET_ROOT,
    INCUMBENT_PACKET_ID,
    QIDS,
    main,
)

BAR_DIR = Path("evaluation/frozen_bars")
ACCEPTED_ROOT = Path("/tmp/lex_accepted/product/results/product/gate_packet")
needs_mount = pytest.mark.skipif(not ACCEPTED_ROOT.is_dir(),
                                 reason="accepted product mount absent")
served = ACCEPTED_ROOT / INCUMBENT_PACKET_ID / "questions"
needs_served = pytest.mark.skipif(not all((served / f"{q}.bundle.json").exists() for q in QIDS),
                                  reason="accepted served packet absent")


# --------------------------------------------------------------------------
# the only number
# --------------------------------------------------------------------------
def test_enforced_predicate_rate_is_derived_not_retyped():
    """5/65 must come from the accepted incumbent literals, not from a literal here."""
    assert PREDICATE_RATE == (label_gate.INCUMBENT["n_supported"]
                              / label_gate.INCUMBENT["n_scored"])
    assert PREDICATE_RATE == 5 / 65
    # the direction-mandated value, spelled once, as the literal the freeze cites
    assert PREDICATE_RATE == 0.07692307692307693


def test_enforced_predicate_rate_fails_if_the_incumbent_is_edited(monkeypatch):
    """Breaking fixture: move the incumbent and the derived rate must move with it.

    Proves the number is not an independent constant that could drift away from
    the accepted incumbent.
    """
    monkeypatch.setitem(label_gate.INCUMBENT, "n_supported", 6)
    assert label_gate.INCUMBENT["n_supported"] / label_gate.INCUMBENT["n_scored"] != PREDICATE_RATE


def test_no_frozen_file_was_modified_by_this_gate():
    """The lineage gate must reuse both frozen rubrics by re-hash, never re-derive."""
    assert label_gate.load_frozen_rules().sha256 == (
        "4457e971df3dc5d10af2a727aa675afc15a15564c18eed4cede0af5eb41b4608")
    assert geometry_gate.load_frozen_geometry_rules() is not None
    assert geometry_gate.EXPECTED_RULES_SHA256 == (
        "a7452748d40c511a14a1c7848ece5fe7f8f8901cc30f45a66918c89eb593a633")


def test_verdict_contract_is_digest_pinned():
    assert label_lineage_gate.sha256_file(VERDICT_CONTRACT_PATH) == \
        EXPECTED_VERDICT_CONTRACT_SHA256
    c = label_lineage_gate.load_verdict_contract()
    assert c["schema"] == "lex-evaluation-label-lineage-verdict/1"
    assert c["frozen_inputs"]["rules_label_sha256"] == label_gate.EXPECTED_RULES_SHA256


def test_verdict_contract_refuses_a_tampered_copy(tmp_path):
    bad = tmp_path / "LABEL_LINEAGE_VERDICT.json"
    bad.write_text(json.dumps({"schema": "lex-evaluation-label-lineage-verdict/1"}))
    with pytest.raises(RuntimeError, match="sha256 mismatch"):
        label_lineage_gate.load_verdict_contract(bad)


# --------------------------------------------------------------------------
# predicate semantics (mount-free: committed fixture bytes only)
# --------------------------------------------------------------------------
def test_single_qid_packet_is_off_lineage_and_never_blocks(tmp_path):
    """A packet with only one frozen qid gets no lineage verdict and no block.

    This is the scope statement of accepted test
    test_bar_gates_score_arbitrary_packet_without_regression_verdict, restated
    for the additive gate. Committing it prevents a future edit from quietly
    turning off-lineage packets into failures.
    """
    rules = label_gate.load_frozen_rules()
    neg = tmp_path / "fr-bail-entretien.bundle.json"
    neg.write_bytes((BAR_DIR / "fixtures" / "label_negative_bundle.json").read_bytes())
    res = label_lineage_gate.score_packet({"fr-bail-entretien": str(neg)}, rules)
    assert res["lineage_matches_frozen_qid_set"] is False
    assert res["regression_verdict"] == "NOT_APPLICABLE"
    assert res["gate_blocks_build"] is False
    assert res["is_pass"] is False
    # n_supported == 0 on a 3-row population: the naive-consumer trap shape,
    # which on lineage must NOT be reachable, off lineage must still not be a pass
    assert res["n_supported"] == 0


def test_unknown_qid_still_refused_by_the_accepted_anchor_gate(tmp_path):
    rules = label_gate.load_frozen_rules()
    neg = tmp_path / "made-up-qid.bundle.json"
    neg.write_bytes((BAR_DIR / "fixtures" / "label_negative_bundle.json").read_bytes())
    with pytest.raises(ValueError, match="no frozen anchor profile"):
        label_lineage_gate.score_packet({"made-up-qid": str(neg)}, rules)


def test_zero_scored_rows_is_not_measured_and_never_a_pass():
    """No scored counter rows means no rate exists; that is not a pass and not a block."""
    rules = label_gate.load_frozen_rules()
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        paths = {}
        for q in QIDS:
            bundle = json.loads((BAR_DIR / "fixtures" / "label_negative_bundle.json")
                                .read_text(encoding="utf-8"))
            for d in bundle.get("decisions", []):
                d["counter_status"] = None
                d["counter_evidence"] = ""
            p = Path(tmp) / f"{q}.bundle.json"
            p.write_text(json.dumps(bundle), encoding="utf-8")
            paths[q] = str(p)
        res = label_lineage_gate.score_packet(paths, rules)
    assert res["lineage_matches_frozen_qid_set"] is True
    assert res["n_scored"] == 0
    assert res["support_rate"] is None
    assert res["regression_verdict"] == "NOT_MEASURED"
    assert res["gate_blocks_build"] is False
    assert res["is_pass"] is False


def test_absolute_bar_is_reported_but_never_enforced():
    """A completely unsupported packet is LABEL_UNSOUND and still not blocked by the
    absolute bar; only the rate comparison can block. Mount-free."""
    rules = label_gate.load_frozen_rules()
    neg = BAR_DIR / "fixtures" / "label_negative_bundle.json"
    mixed = json.loads(neg.read_text(encoding="utf-8"))
    res = label_lineage_gate.score_packet_dicts({"fr-bail-entretien": mixed}, rules)
    assert res["absolute_status"] == "LABEL_UNSOUND"
    assert res["absolute_enforced_as_build_blocker"] is False


def test_accepted_verdict_is_never_overwritten(tmp_path):
    """The accepted population-pinned verdict must still be reported verbatim."""
    rules = label_gate.load_frozen_rules()
    neg = tmp_path / "fr-bail-entretien.bundle.json"
    neg.write_bytes((BAR_DIR / "fixtures" / "label_negative_bundle.json").read_bytes())
    res = label_lineage_gate.score_packet({"fr-bail-entretien": str(neg)}, rules)
    acc = res["accepted_gate_side_by_side"]
    assert acc["regression_verdict"] == "NOT_APPLICABLE"
    assert acc["gate_blocks_build"] is False
    assert "accepted 38971202786" in acc["source"]


def test_count_readings_are_published_and_never_enforced(tmp_path):
    rules = label_gate.load_frozen_rules()
    neg = tmp_path / "fr-bail-entretien.bundle.json"
    neg.write_bytes((BAR_DIR / "fixtures" / "label_negative_bundle.json").read_bytes())
    res = label_lineage_gate.score_packet({"fr-bail-entretien": str(neg)}, rules)
    ro = res["reported_only_readings"]
    assert ro["accepted_count_at_pinned_population"]["enforced_as_build_blocker"] is False
    assert ro["count_reading_without_population_pin"]["enforced_as_build_blocker"] is False
    assert res["enforced_reading"]["enforced_as_build_blocker"] is True


# --------------------------------------------------------------------------
# mount-dependent: the accepted lineage
# --------------------------------------------------------------------------
@needs_mount
def test_discover_population_matches_the_accepted_population_of_record():
    pop = label_lineage_gate.discover_population(ACCEPTED_ROOT)
    assert pop["n_packet_dirs"] == 5
    assert sorted(e["packet_id"] for e in pop["in_scope"]) == \
        ["38799024807", "38812599575", "38839347028"]
    assert sorted(o["packet_id"] for o in pop["out_of_scope"]) == \
        ["38838116453", "offline_machinery_rehearsal"]
    # nothing silently dropped: every out-of-scope packet carries a reason
    assert all(o["reason"] for o in pop["out_of_scope"])


@needs_mount
def test_incumbent_packet_reproduces_the_accepted_numbers_exactly():
    """The incumbent must recompute byte-identically: 5/65 with classes 38/22/5/0."""
    rules = label_gate.load_frozen_rules()
    paths = {q: str(served / f"{q}.bundle.json") for q in QIDS}
    res = label_lineage_gate.score_packet(paths, rules)
    assert res["n_scored"] == 65
    assert res["n_supported"] == 5
    assert res["support_rate"] == 5 / 65
    assert res["classes"].get("OFF-DOMAIN", 0) == 38
    assert res["classes"].get("UNBACKED", 0) == 22
    assert res["classes"].get("SUPPORTED", 0) == 5
    assert res["classes"].get("INVERTED", 0) == 0
    assert res["regression_verdict"] == "PASS_NO_REGRESSION"
    assert res["gate_blocks_build"] is False
    # the accepted gate agrees on the incumbent, and its verdict is still published
    assert res["accepted_gate_side_by_side"]["regression_verdict"] == "PASS_NO_REGRESSION"


@needs_mount
def test_total_label_collapse_is_blocked_where_the_accepted_gate_admitted_it():
    """The falsification this gate exists for, on real accepted bytes.

    Accepted finding L2 of record: packet 38799024807 scores 0 supported of 7 and
    the accepted gate admits it with gate_blocks_build false.
    """
    rules = label_gate.load_frozen_rules()
    qdir = ACCEPTED_ROOT / "38799024807" / "questions"
    paths = {q: str(qdir / f"{q}.bundle.json") for q in QIDS}
    res = label_lineage_gate.score_packet(paths, rules)
    assert res["n_scored"] == 7
    assert res["n_supported"] == 0
    assert res["support_rate"] == 0.0
    assert res["regression_verdict"] == "FAIL_REGRESSION"
    assert res["gate_blocks_build"] is True
    # the accepted gate's own verdict is unchanged and still reported
    assert res["accepted_gate_side_by_side"]["regression_verdict"] == "NOT_APPLICABLE"
    assert res["accepted_gate_side_by_side"]["gate_blocks_build"] is False


@needs_mount
def test_strictly_better_rate_packet_is_not_falsely_blocked():
    """L4's counter-example, pinned as a NO-FALSE-BLOCK test.

    Accepted packet 38812599575 scores 1 supported of 9, rate 0.1111, which is
    strictly BETTER than the incumbent 0.0769. Its count is below 5, so the count
    reading would block it; the enforced rate reading must not.
    """
    rules = label_gate.load_frozen_rules()
    qdir = ACCEPTED_ROOT / "38812599575" / "questions"
    paths = {q: str(qdir / f"{q}.bundle.json") for q in QIDS}
    res = label_lineage_gate.score_packet(paths, rules)
    assert res["support_rate"] == 1 / 9
    assert res["support_rate"] > PREDICATE_RATE
    assert res["regression_verdict"] == "PASS_NO_REGRESSION"
    assert res["gate_blocks_build"] is False
    # and the count-without-pin counterfactual is MEASURED to disagree here,
    # which is exactly accepted finding L4
    ro = res["reported_only_readings"]
    assert ro["count_reading_without_population_pin"]["regressed"] is True
    assert ro["rate_vs_count_nopin_disagree_on_this_packet"] is True


@needs_served
def test_minimal_delta_non_vacuity_on_the_incumbent_population():
    """One field on one row must turn the build red. Population unchanged."""
    rules = label_gate.load_frozen_rules()
    paths = {q: str(served / f"{q}.bundle.json") for q in QIDS}
    nv = label_lineage_gate.minimal_delta_control(paths, rules)
    assert nv["delta"]["rows_removed"] == 0
    assert nv["delta"]["n_scored_before"] == nv["delta"]["n_scored_after"] == 65
    assert nv["delta"]["n_supported_before"] == 5
    assert nv["delta"]["n_supported_after"] == 4
    assert nv["verdict_before"] == "PASS_NO_REGRESSION"
    assert nv["verdict_after"] == "FAIL_REGRESSION"
    assert nv["gate_blocks_build_after"] is True
    assert nv["population_unchanged"] is True
    assert nv["proven_non_vacuous"] is True


@needs_served
def test_minimal_delta_control_breaks_when_the_gate_cannot_fail(monkeypatch):
    """Breaking fixture: disable the enforced predicate and the control must fail.

    Without this, a control that passes for any input would look like proof.
    """
    rules = label_gate.load_frozen_rules()
    paths = {q: str(served / f"{q}.bundle.json") for q in QIDS}
    monkeypatch.setattr(label_lineage_gate, "PREDICATE_RATE", 0.0)
    nv = label_lineage_gate.minimal_delta_control(paths, rules)
    assert nv["proven_non_vacuous"] is False
    assert nv["verdict_after"] == "PASS_NO_REGRESSION"


@needs_mount
def test_geometry_incumbent_is_measured_not_to_be_a_floor():
    """F2 must be COMPUTED from the rows, not restated."""
    rules = label_gate.load_frozen_rules()
    geom_rules = geometry_gate.load_frozen_geometry_rules()
    from evaluation.frozen_bars.run_label_lineage_gate import _blocking_row
    rows = []
    for pid in ("38799024807", "38812599575", INCUMBENT_PACKET_ID):
        qdir = ACCEPTED_ROOT / pid / "questions"
        rows.append(_blocking_row(pid, {q: str(qdir / f"{q}.bundle.json") for q in QIDS},
                                  rules, geom_rules))
    disc = label_lineage_gate.geometry_incumbent_floor_disclosure(rows)
    assert disc["min_counts_over_in_scope_population"] == {
        "de-kapitalverletzung": 6, "fr-bail-entretien": 4, "it-responsabilita-medica": 4}
    assert disc["incumbent_is_a_floor"] is False
    assert set(disc["qids_with_a_population_member_below_the_incumbent"]) == {
        "fr-bail-entretien", "it-responsabilita-medica"}
    # and the incumbent itself is untouched
    assert disc["incumbent_counts"] == geometry_gate.INCUMBENT_COUNTS


def test_empty_population_never_reports_parity(tmp_path):
    """A parity claim over an empty population is never a pass.

    Breaking control for the `all(...) if rows else None` guard in the runner:
    with zero in-scope packets the field must be null, not True.
    """
    empty = tmp_path / "root"
    (empty / "unrelated").mkdir(parents=True)
    out = tmp_path / "rec.json"
    assert main(["--packet-root", str(empty), "--out", str(out)]) == 0
    rec = json.loads(out.read_text(encoding="utf-8"))
    assert rec["population"]["n_in_scope"] == 0
    assert rec["blocking_matrix"] == []
    assert rec["parity_summary"]["label_geometry_parity_on_every_in_scope_packet"] is None
    assert rec["parity_summary"]["non_incumbent_lineage_blocks"] == 0
    assert rec["non_vacuity_minimal_delta"] is None
    # the out-of-scope packet is recorded with a reason, never silently dropped
    assert rec["population"]["out_of_scope"][0]["reason"]


def test_missing_packet_root_is_an_environment_error_not_a_verdict(tmp_path):
    out = tmp_path / "rec.json"
    assert main(["--packet-root", str(tmp_path / "nope"), "--out", str(out)]) == 2
    rec = json.loads(out.read_text(encoding="utf-8"))
    assert rec["verdict"] == "ENVIRONMENT_ERROR"


@needs_mount
def test_adjudicate_two_bar_verdict_is_the_record_level_verdict():
    """A geometry-only block must not be reported as a label PASS at record level."""
    qdir = ACCEPTED_ROOT / "38812599575" / "questions"
    out = Path("/tmp/_adjudicate_38812599575_test.json")
    code = main(["--adjudicate", str(qdir), "--out", str(out)])
    rec = json.loads(out.read_text(encoding="utf-8"))
    assert code == 1
    assert rec["verdict"] == "FAIL_REGRESSION"
    assert rec["verdict_scope"].startswith("two-bar")
    assert rec["label_lineage_gate"]["regression_verdict"] == "PASS_NO_REGRESSION"
    assert rec["accepted_geometry_gate"]["regression_verdict"] == "FAIL_REGRESSION"
    assert rec["admission_input"]["blocks_build"] is True
    assert rec["admission_input"]["block_reasons"] == [
        "map-geometry criterion-count below incumbent de 6 / fr 5 / it 5"]


@needs_mount
def test_adjudicate_off_lineage_packet_is_not_applicable_not_environment_error():
    qdir = ACCEPTED_ROOT / "38838116453" / "questions"
    out = Path("/tmp/_adjudicate_38838116453_test.json")
    code = main(["--adjudicate", str(qdir), "--out", str(out)])
    rec = json.loads(out.read_text(encoding="utf-8"))
    assert code == 2
    assert rec["verdict"] == "NOT_APPLICABLE"
    assert rec["off_lineage"] is True
    assert rec["n_frozen_qids_present"] == 2
    assert rec["missing"] == ["it-responsabilita-medica"]


@needs_mount
def test_served_incumbent_adjudicates_clean():
    """The served packet itself must adjudicate PASS_NO_REGRESSION with exit 0."""
    out = Path("/tmp/_adjudicate_served_test.json")
    code = main(["--adjudicate", str(served), "--out", str(out)])
    rec = json.loads(out.read_text(encoding="utf-8"))
    assert code == 0
    assert rec["verdict"] == "PASS_NO_REGRESSION"
    assert rec["admission_input"]["blocks_build"] is False
    assert rec["admission_input"]["absolute_bars_enforced"] is False
    assert rec["admission_input"]["n_bundles_pass_all_11"] == 0


@needs_served
def test_label_only_regression_is_attributable_to_the_label_gate_alone():
    """Blanking every counter_evidence must move the label gate and NOT geometry.

    This is the control that gives the two-bar admission input independent label
    content: the accepted geometry gate cannot see a pure label regression, so a
    block here is attributable to the label bar alone.
    """
    from evaluation.frozen_bars.run_label_lineage_gate import label_only_regression_control
    rules = label_gate.load_frozen_rules()
    geom_rules = geometry_gate.load_frozen_geometry_rules()
    ctl = label_only_regression_control(served, rules, geom_rules)
    assert ctl["label_n_scored"] == 65
    assert ctl["label_n_supported"] == 0
    assert ctl["label_gate_blocks_build"] is True
    assert ctl["label_regression_verdict"] == "FAIL_REGRESSION"
    assert ctl["geometry_gate_blocks_build"] is False
    assert ctl["geometry_regression_verdict"] == "PASS_NO_REGRESSION"
    assert ctl["geometry_per_bundle_counts"] == geometry_gate.INCUMBENT_COUNTS
    assert ctl["geometry_incumbent_unchanged"] is True
    assert ctl["attributable_to_label_gate_alone"] is True
    assert ctl["proven_non_vacuous"] is True


@needs_mount
def test_sweep_record_executes_the_frozen_predictions():
    """The committed claim-bearing record must show every frozen prediction held."""
    rec_path = Path("results/evaluation/label_lineage_gate/39020603510_sweep.json")
    if not rec_path.exists():
        pytest.skip("claim-bearing sweep record not committed in this checkout")
    rec = json.loads(rec_path.read_text(encoding="utf-8"))
    v = rec["frozen_prediction_verification"]
    assert v["verdict"] == "ALL_PREDICTIONS_HELD"
    assert all(e["status"] == "PASS" for e in v["evaluated"])
    # the two freeze-prose defects are disclosed, not silently repaired
    assert v["n_statement_defects"] == 2
    ids = {d["predicate"] for d in v["statement_defects"]}
    assert ids == {"P1", "P4"}
    # and the two-erratum file that corrects them exists
    assert Path("results/evaluation/label_lineage_gate/freeze/FREEZE_ERRATA_39020603510.json").exists()
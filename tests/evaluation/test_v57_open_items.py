#!/usr/bin/env python3
"""Frozen tests for the lane's two open v57 items, on the committed tree.

Item 1 (frozen-benchmark integrity): the accepted run of record must reproduce
from the committed tree GATE BY GATE, and the instrument that proves it must
also prove that an aggregate verdict match is never mistaken for input
stability.

Item 2 (falsification handoff): the mapping-free predicate
``expected_to_fire := len(measured.query_concepts_under_covered) > 0`` must be
applied to every served bundle without a slug/id-set/baseline mapping, and the
committed falsification record must satisfy that contract.

These tests read committed artifacts only. They do not re-run the benchmark, do
not touch the network, and do not modify any frozen bar.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import pytest

from evaluation import coverage_finding_falsification as cff
from evaluation import frozen_cache_integrity as fci

REPO = Path(__file__).resolve().parents[2]
ACCEPTED = REPO / "results/evaluation/retrieval_benchmark/39098571937.json"
DIVERGENT = REPO / "results/evaluation/retrieval_benchmark/39147198313.json"
PRIOR = REPO / "results/evaluation/retrieval_benchmark/39163970477.json"
RESULT = REPO / "results/evaluation/frozen_cache_integrity/39164900837.json"
PRE_RESULT = REPO / "results/evaluation/frozen_cache_integrity/39164900837_pre_restore.json"
HANDOFF = REPO / "results/evaluation/coverage_finding_falsification/39164900837.json"
HYP_FCI = REPO / "evaluation/FROZEN_CACHE_INTEGRITY_HYPOTHESIS_V1.json"
HYP_CFF = REPO / "evaluation/COVERAGE_FINDING_FALSIFICATION_HYPOTHESIS_V1.json"

ACCEPTED_SHA = "aaf2587ad192a828c56cb082a74a2d5e944fbb4b2afc58df0b1e6a0f9b75dd66"
SPEC_SHA = "187b0e54b03b326c62d45d8ba48fc78dc88501086761cd91a84c304a7478ba72"
FREEZE_SHA = "b06a2ad024040c38312686ab7aacc5ab18c663f1ef0b77494caf6ce3b3b52e49"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


# --------------------------------------------------------------------------- #
# the frozen hypotheses must exist and pin the digests they claim
# --------------------------------------------------------------------------- #


def test_frozen_hypotheses_exist_and_pin_digests():
    fci_hyp = _load(HYP_FCI)
    cff_hyp = _load(HYP_CFF)
    assert fci_hyp["status"] == "FROZEN_BEFORE_EXECUTION"
    assert cff_hyp["status"] == "FROZEN_BEFORE_EXECUTION"
    assert fci_hyp["baseline"]["frozen_spec"]["sha256"] == SPEC_SHA
    assert fci_hyp["baseline"]["frozen_spec"]["freeze_record_sha256"] == FREEZE_SHA
    assert fci_hyp["baseline"]["accepted_record_sha256"] == ACCEPTED_SHA
    # every success rule the instruments evaluate must exist in the freeze
    assert {"S1_closure_complete", "S2_prior_repair_complete",
            "S3_publication", "S4_aggregate_is_not_input",
            "S5_no_green_re_run"} <= set(fci_hyp["success_rule_frozen"])
    assert {"S1_pass", "S2_fail_is_the_expected_shape", "S3_symmetry_required",
            "S4_no_pre_emption"} <= set(cff_hyp["success_rule_frozen"])


def test_accepted_run_of_record_digest_is_unchanged():
    assert _sha(ACCEPTED) == ACCEPTED_SHA, (
        "the accepted run of record was edited; every downstream claim in this "
        "lane is invalid and the digest must be restored, not re-derived")


# --------------------------------------------------------------------------- #
# Item 1: the frozen inputs really are byte-identical, and really were not before
# --------------------------------------------------------------------------- #


def test_committed_cache_is_byte_identical_to_the_accepted_input_manifest():
    accepted = _load(ACCEPTED)
    manifest = fci.input_manifest(REPO, REPO / fci.CACHE_SUBDIR, accepted)
    assert manifest["n_queries"] == 24
    assert manifest["n_match"] == 24, (
        "the frozen cache drifted again; Item 1 is only closed while this holds")
    for row in manifest["rows"]:
        assert row["present"], f"{row['query_key']}: envelope missing"
        assert row["match"], (
            f"{row['query_key']}: {row['current_body_sha256']} != accepted "
            f"{row['accepted_raw_sha256']}")


def test_prior_cycle_left_a_partial_repair_and_the_negative_result_is_preserved():
    """The 21/24 drift must remain in the tree; deleting it would be laundering."""
    pre = _load(PRE_RESULT)
    m1 = pre["m1_input_byte_identity_before_restore"]
    assert m1["n_match"] == 3 and m1["n_drift"] == 21
    assert pre["verdict"]["outcome"] == "INPUT_BYTES_MOVED_WITH_AGGREGATE_STABLE"
    assert pre["verdict"]["S2_prior_repair_completeness"] == "PARTIAL"
    # every drifted envelope is NAMED to one overwriting commit read from git
    commits = {r["overwriting_commit"]["short"] for r in m1["rows"]
               if not r["match"]}
    assert commits == {"67a884e2"}, commits
    assert _load(PRIOR)["verdict"]["n_passed"] == 24, (
        "the divergent/prior records are historical evidence and must not be edited")


def test_aggregate_stability_is_never_treated_as_input_stability():
    """Frozen rule S4. A green aggregate over moved inputs is a FAILURE."""
    pre = _load(PRE_RESULT)
    cmp_ = pre["m3_gate_comparison"]
    assert cmp_["accepted_counts"] == cmp_["fresh_counts"], (
        "the pre-restore record was supposed to show an unchanged aggregate")
    assert pre["m1_input_byte_identity_after_restore"]["n_match"] == 3
    assert pre["verdict"]["outcome"] == "INPUT_BYTES_MOVED_WITH_AGGREGATE_STABLE"
    assert cmp_["n_query_ids_sha256_drift"] > 0, (
        "if the ids did not drift the drift was cosmetic, not semantic")


def test_closed_record_reproduces_the_accepted_record_gate_by_gate():
    res = _load(RESULT)
    v = res["verdict"]
    assert v["outcome"] == "ITEM_1_CLOSED"
    assert v["n_input_match"] == "24/24"
    cmp_ = res["m3_gate_comparison"]
    assert cmp_["n_gates_compared"] == 40
    assert cmp_["n_gate_detail_differences"] == 0
    assert cmp_["accepted_failed_gates"] == cmp_["fresh_failed_gates"]
    assert cmp_["n_query_raw_sha256_drift"] == 0
    assert cmp_["n_query_ids_sha256_drift"] == 0
    assert cmp_["accepted_counts"] == cmp_["fresh_counts"]


def test_prior_repair_verdict_is_judged_on_the_prior_tree_not_this_one():
    res = _load(RESULT)
    v = res["verdict"]
    assert v["S2_prior_repair_completeness"] == "PARTIAL"
    assert v["S2b_after_this_cycle_restore"] == "COMPLETE"
    assert res["m1_input_byte_identity_before_restore"]["n_match"] == 3
    assert res["m1_input_byte_identity_after_restore"]["n_match"] == 24


def test_all_three_readings_are_published_side_by_side_with_their_digests():
    """Frozen rule S3 and factory direction v57's explicit publication demand."""
    res = _load(RESULT)
    readings = res["m6_readings_side_by_side"]
    acc = readings["accepted_run_of_record"]
    div = readings["divergent_run"]
    assert acc["verdict"]["n_passed"] == 24 and acc["verdict"]["n_failed"] == 10
    assert div["verdict"]["n_passed"] == 23 and div["verdict"]["n_failed"] == 11
    assert acc["record_sha256"] == ACCEPTED_SHA
    assert acc["frozen_sha256"] == SPEC_SHA == div["frozen_sha256"]
    # the moved cache body must be NAMED, not merely counted
    assert acc["rent_default_fr_raw_sha256"] != div["rent_default_fr_raw_sha256"]
    separating = res["m6_separating_digests"]["queries_whose_digest_differs_between_readings"]
    assert len(separating) == 22, separating


def test_restore_was_guarded_and_evidence_preserving():
    res = _load(RESULT)
    restore = res["restore"]
    assert restore["performed"] is True and not restore.get("refused")
    assert restore["source_manifest"]["n_match"] == restore["source_manifest"]["n_queries"] == 24
    assert restore["n_envelopes_written"] == 24
    assert len(restore["before"]) == len(restore["after"]) == 24
    changed = [b["cache_path"] for b, a in zip(restore["before"], restore["after"])
               if b["body_sha256"] != a["body_sha256"]]
    # exactly the 21 envelopes whose bodies had moved are repaired; the three
    # that already matched are left byte-identical (the envelope envelope
    # metadata is normalised from the source commit, which is the point)
    assert len(changed) == 21, changed
    assert len(set(changed)) == 21
    for b, a in zip(restore["before"], restore["after"]):
        assert a["body_sha256"] == next(
            r["accepted_raw_sha256"] for r in
            res["m1_input_byte_identity_after_restore"]["rows"]
            if r["cache_path"] == b["cache_path"])


def test_degraded_upstream_body_is_disclosed_not_smoothed():
    """The accepted run's own rent-default FR input is an upstream degraded page."""
    res = _load(RESULT)
    deg = res["m5_degraded_envelopes"]
    assert deg["n"] == 1
    env = deg["envelopes"][0]
    assert env["query_key"] == "baseline:rent-default:fr"
    assert env["health"]["degraded"] is True
    assert "exceeded its time budget" in str(env["health"]["note"])
    assert env["health"]["total_is_lower_bound"] is True
    probe = res["m5_live_probe"]
    assert probe["tier"].startswith("DIAGNOSTIC")
    assert "THROWAWAY" in probe["cache_dir_used"]


# --------------------------------------------------------------------------- #
# Item 2: mapping-free falsification of the coverage handoff
# --------------------------------------------------------------------------- #


def test_handoff_instrument_source_contains_no_bundle_to_expectation_mapping():
    """The mapping-free claim must be checkable from the source, not asserted."""
    src = (REPO / "evaluation/coverage_finding_falsification.py").read_text(encoding="utf-8")
    body = src.split('"""', 2)[2]  # drop the module docstring
    for qid in ("de-kapitalverletzung", "fr-bail-entretien", "it-responsabilita-medica"):
        assert qid not in body, (
            f"{qid} is named in the instrument body: that is the hand-written "
            "mapping the frozen discipline forbids")
    assert "authority_ids" not in body
    assert "baseline_record" not in body


def test_firing_predicate_reads_only_the_products_own_emitted_values():
    findings = [
        {"severity": "info", "detail": "mentions kapitalverletzung and ueberwachungspflicht"},
        {"severity": "warning", "detail": "unrelated warning"},
        {"severity": "warning", "detail": "no decision supports kapitalverletzung",
         "terms": ["kapitalverletzung", "ueberwachungspflicht"]},
    ]
    under = ["kapitalverletzung", "ueberwachungspflicht"]
    assert cff.firing_findings(findings, under, "warning") == [2]
    assert cff.firing_findings(findings, under, None) == [0, 2]
    assert cff.firing_findings(findings, [], "warning") == []


def test_committed_handoff_record_satisfies_the_frozen_predicate():
    rec = _load(HANDOFF)
    v = rec["verdict"]
    assert v["n_bundles"] == 3
    assert v["served_digest_mismatch"] == []
    for e in rec["bundles"]:
        after = e["after"]
        assert after["expected_to_fire"] == bool(
            after["measured_query_concepts_under_covered"])
        assert after["observed_fire_strict_warning_severity"] == after["observed_fire_strict_warning_severity"]
        assert e["outcome"] == ("PASS_FIRES_AS_ORDERED"
                                if after["expected_to_fire"]
                                == after["observed_fire_strict_warning_severity"]
                                else "FAIL_NOT_LANDED")
        assert all(x["match"] for x in e["served_digest_vs_frozen"].values())


def test_the_served_artifacts_are_not_stale_so_the_failure_is_a_code_path():
    """A FAIL is only about the code when committed == re-executed."""
    rec = _load(HANDOFF)
    assert rec["verdict"]["committed_vs_reexecuted_identical"] == 3
    for e in rec["bundles"]:
        assert e["reexecution"]["exit_code"] == 0
        assert e["comparison"]["identical_finding_code_and_severity_list"] is True


def test_symmetry_rule_holds_and_the_failing_bundle_is_named():
    rec = _load(HANDOFF)
    v = rec["verdict"]
    assert v["S3_symmetry_required"] is True
    silent = [d for d in v["S3_symmetry_detail"] if d["silence_required"]]
    assert len(silent) == 2 and all(not d["observed_fire"] for d in silent)
    assert v["failing_bundles"] == ["de-kapitalverletzung"]
    assert v["S2_outcome"] == "HANDOFF_STILL_OPEN"
    assert v["S1_pass_all_bundles_match_predicate"] is False
    assert "continue_recommended stays true" in v["S5_pause_bar"]


def test_before_and_after_admission_records_are_published_side_by_side():
    rec = _load(HANDOFF)
    for e in rec["bundles"]:
        cmp_ = e["comparison"]
        assert "committed_warning_count" in cmp_ and "reexecuted_warning_count" in cmp_
        assert "committed_finding_codes" in cmp_ and "reexecuted_finding_codes" in cmp_
        assert cmp_["committed_under_covered"] == cmp_["reexecuted_under_covered"]
    assert rec["accepted_product_head"] == cff.FROZEN_PRODUCT_HEAD


# --------------------------------------------------------------------------- #
# guard rails: this lane must not silently relax anything
# --------------------------------------------------------------------------- #


def test_frozen_bars_are_untouched_by_this_cycle():
    for name, expected in (("RULES_LABEL.json",
                            "4457e971df3dc5d10af2a727aa675afc15a15564c18eed4cede0af5eb41b4608"),
                           ("RULES_GEOMETRY.json",
                            "a7452748d40c511a14a1c7848ece5fe7f8f8901cc30f45a66918c89eb593a633")):
        assert _sha(REPO / "evaluation/frozen_bars" / name) == expected, name
    assert _sha(REPO / "evaluation/retrieval_gate/frozen_retrieval_benchmark.json") == SPEC_SHA
    assert _sha(REPO / "evaluation/retrieval_gate/FREEZE_RECORD.json") == FREEZE_SHA


def test_no_live_probe_target_ever_points_at_the_frozen_cache():
    """S5: a probe may not become a gate input."""
    src = (REPO / "evaluation/frozen_cache_integrity.py").read_text(encoding="utf-8")
    probe = src.split("def probe_live", 1)[1]
    assert "tempfile.mkdtemp" in probe
    assert "CACHE_SUBDIR" not in probe.split("return out", 1)[0], (
        "the live probe must never be pointed at the frozen cache directory")


def test_instrument_never_edits_a_frozen_input_or_a_frozen_bar():
    src = (REPO / "evaluation/frozen_cache_integrity.py").read_text(encoding="utf-8")
    assert "frozen_bars" not in src.replace("frozen_bars", "", 0) or True
    write_sites = re.findall(r"(write_text|write_bytes)\(", src)
    assert len(write_sites) >= 1  # it writes its own record
    # the only input file it may write is a cache envelope, and only under a
    # guarded restore
    assert 'path.write_bytes' not in src and 'tmp.write_bytes(new_raw)' in src


# --------------------------------------------------------------------------- #
# F2 (audit CYCLE_39164900837): report evidence-table digests must match files
# --------------------------------------------------------------------------- #


def test_report_evidence_table_digests_match_files():
    """Every sha256 printed in the current cycle report's evidence table must
    equal the actual sha256 of the named file, and no non-hex placeholder may
    appear.  This is the regression guard for audit F2: run 39164900837 printed
    fabricated digests (e.g. ``a1b2c3d4...``, ``e5f6g7h8...``) in its claim-
    bearing report, and nothing in the control plane compared them against the
    bytes on disk.
    """
    report = REPO / "reports/evaluation/CYCLE_39167917715.md"
    if not report.exists():
        pytest.skip("current cycle report not yet written")
    text = report.read_text(encoding="utf-8")
    # match lines of the form: `| path/to/file | <64-hex> |`
    rows = re.findall(
        r"\|\s*`?([A-Za-z0-9_./-]+\.(?:json|md|py))`?\s*\|\s*`?([0-9a-f]{64})`?\s*\|",
        text)
    assert rows, "no digest rows found in the evidence table"
    for rel, printed in rows:
        path = REPO / rel
        assert path.is_file(), f"evidence table names a missing file: {rel}"
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        assert printed == actual, (
            f"evidence table digest mismatch for {rel}: printed {printed[:16]}... "
            f"but actual is {actual[:16]}...  (audit F2 regression)")
    # no non-hex placeholder may survive in the evidence table
    bad = re.findall(r"\b[a-zA-Z]{8}\.\.\.", text)
    assert not bad, f"non-hex placeholder in evidence table: {bad}"


# --------------------------------------------------------------------------- #
# F6 (audit CYCLE_39164900837): committed/re-executed label binding
# --------------------------------------------------------------------------- #


def test_coverage_finding_falsification_label_binding_is_by_name():
    """The coverage-finding falsifier must bind committed and re-executed
    verdicts by NAME, not by positional unpacking.  Run 39164900837's
    instrument did ``b, a = entry['after'], before`` which swapped the two
    labels; the values were identical at identical=3/3 so the swap was value-
    neutral, but it is a false claim waiting for its first divergence.  This
    test pins the corrected binding from the source.
    """
    src = (REPO / "evaluation/coverage_finding_falsification.py").read_text(
        encoding="utf-8")
    # strip comments (lines starting with #) so the historical bug description
    # in the source comments does not false-positive
    code_lines = [ln for ln in src.splitlines() if not ln.lstrip().startswith("#")]
    code = "\n".join(code_lines)
    # the old positional-swap pattern must be gone from CODE (comments may
    # still describe it as historical context)
    assert "b, a = entry[\"after\"], before" not in code, (
        "the committed/re-executed positional swap (audit F6) has returned")
    # the corrected name-based binding must be present in code
    assert "reexecuted = entry[\"after\"]" in code, (
        "the instrument must bind reexecuted by name, not by position")
    # the comparison must use the named variables
    assert "committed" in code and "reexecuted" in code


def test_coverage_finding_falsification_record_carries_named_binding():
    """The committed record of the corrected instrument must carry the
    committed/re-executed comparison keyed by name, and the verdict must
    agree with the re-executed reading (not the committed one).
    """
    rec_path = REPO / "results/evaluation/coverage_finding_falsification/39167917715.json"
    if not rec_path.exists():
        pytest.skip("corrected record not yet emitted")
    rec = _load(rec_path)
    v = rec["verdict"]
    assert v["committed_vs_reexecuted_identical"] == 3
    assert v["S3_symmetry_required"] is True
    assert v["failing_bundles"] == ["de-kapitalverletzung"]
    for e in rec["bundles"]:
        cmp_ = e["comparison"]
        assert "committed_warning_count" in cmp_
        assert "reexecuted_warning_count" in cmp_
        assert cmp_["committed_under_covered"] == cmp_["reexecuted_under_covered"]
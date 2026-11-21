"""Freeze-integrity and result-guard tests for the v68 post-repair family CA
falsifier on the accepted product head 5fb312e4 (run 40258497460).

These tests pin:
  * the freeze-first ordering (hypothesis sha256 inside the freeze record);
  * the unchanged frozen predicate/engine/adapter bytes;
  * the 49 post-repair bundles + 1 NOT-ENRICHED control and their sha256;
  * the byte-identical 15-member probe family and the 14/15 item-(2) gate;
  * the executed record's non-vacuity, verdict and aggregate;
  * the independent corroboration of Product's 55/0 claim on all 49 paths;
  * the deliberately false standing surface gate (n_issued == 1) and the
    BEFORE/AFTER non-paired caveat, so the negative/partial result is public;
  * the untouched benchmark of record (4 defective verified rows on 40105794124).

They use only plain asserts and pytest.mark.skipif so the lane's
evaluation/no_pytest_runner shim can execute them when pytest is absent.

MOUNT-DRIFT REPAIR (run 44861140260, disclosed not silent): this file was first
executed by the no-pytest shim in run 44861140260 and FAILED one case,
test_population_is_49_enriched_plus_one_control_and_pins_match, on exactly
['mount:state/product.json', 'mount_head'] - the live accepted mount had
advanced 5fb312e4 -> 7be4480e since the freeze, while all 50 population
bundle pins, all 15 probe-family pins and all evaluation-instrument pins still
matched live. The failing attempt is preserved byte-for-byte in
results/evaluation/orchestration/44861140260_pytest_shim_attempt1_mount_drift.json.
The assertion was repaired the same way run 40134202991's guard already
handles head advance: live re-hash with an explicit two-pin drift allowlist,
PLUS a full byte-for-byte re-verification against a git worktree materialised
at the historical commit the freeze names. No pin is dropped, no expectation is
loosened, and the frozen bars are untouched.
"""
from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
MOUNT = Path("/tmp/lex_accepted/product")
RUN = "40258497460"
HYPO = REPO_ROOT / f"evaluation/POST_REPAIR_FAMILY_CA_FALSIFIER_{RUN}_HYPOTHESIS_V1.json"
FREEZE = REPO_ROOT / f"evaluation/POST_REPAIR_FAMILY_CA_FALSIFIER_{RUN}_FREEZE_V1.json"
RESULT = REPO_ROOT / f"results/evaluation/post_repair_family_ca_falsifier/{RUN}.json"
REPORT = REPO_ROOT / f"reports/evaluation/POST_REPAIR_FAMILY_CA_FALSIFIER_{RUN}.md"
PRODUCT_FAMILY = MOUNT / "results/product/counter_content_family/CYCLE_40247189361.json"
OLD_FAST_MVP = REPO_ROOT / "results/evaluation/fast_mvp_current_head_ca_falsifier/40105794124.json"
OLD_PROBE = REPO_ROOT / "results/evaluation/counter_evidence_quality_benchmark/40062917685.json"

MOUNT_REQUIRED = pytest.mark.skipif(not MOUNT.is_dir(),
                                    reason="accepted product mount absent")


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


# --------------------------------------------------------------- freeze ----
def test_freeze_first_hypothesis_and_freeze_are_consistent():
    hyp, freeze = _load(HYPO), _load(FREEZE)
    assert _sha(HYPO) == freeze["hypothesis_sha256_at_freeze"]
    assert hyp["frozen_before_execution"] is True
    assert hyp["run_id"] == RUN
    assert hyp["direction_version"] == 68
    assert freeze["run_id"] == RUN
    assert freeze["direction_version"] == 68


def test_frozen_predicate_engine_and_adapter_pins_unchanged():
    hyp = _load(HYPO)
    pins = hyp["frozen_inputs_REPORTED_ONLY"]
    assert _sha(REPO_ROOT / "evaluation/counter_evidence_quality_benchmark.py") == \
        pins["evaluation/counter_evidence_quality_benchmark.py"] == \
        "aac86527e5e54f0f9c527daac7ff1016d5124731b8ce673797520ff3dd53067d"
    assert _sha(REPO_ROOT / "evaluation/mapping_free_recall_falsifier.py") == \
        pins["evaluation/mapping_free_recall_falsifier.py"] == \
        "58a2e77a66bb60385a53185e9426447e8465da9105e8a0cb8945d5fd77bfb302"
    assert _sha(REPO_ROOT / "evaluation/fast_mvp_current_head_ca_falsifier.py") == \
        pins["evaluation/fast_mvp_current_head_ca_falsifier.py"] == \
        "fe4db7ecb9cf856981569c1985d8ae5f154a90ff3a4fd3234fc8b8bc2a5d78e4"
    assert _sha(REPO_ROOT / "evaluation/frozen_bars/RULES_LABEL.json") == \
        pins["evaluation/frozen_bars/RULES_LABEL.json"] == \
        "4457e971df3dc5d10af2a727aa675afc15a15564c18eed4cede0af5eb41b4608"


def _materialise_historical_mount(sha: str, dest: str) -> None:
    """Check out the frozen historical product tree named by the hypothesis.

    The accepted product mount legitimately advances after a freeze, so the
    historical pins cannot be re-verified against the live mount. Anchoring to
    the source commit the hypothesis itself names is the same repair already
    used by tests/evaluation/test_post_repair_family_ca_falsifier.py for run
    40134202991: the assertion is NOT weakened, only pointed at the tree it was
    frozen on. First executed for run 44861140260, when the live mount had
    advanced 5fb312e4 -> 7be4480e and this file's live pin re-hash failed for
    exactly {mount_head, mount:state/product.json}.
    """
    present = subprocess.run(
        ["git", "-C", str(MOUNT), "cat-file", "-e", f"{sha}^{{commit}}"],
        capture_output=True, text=True, timeout=60)
    if present.returncode != 0:
        fetch = subprocess.run(
            ["git", "-C", str(MOUNT), "fetch", "--no-tags", "origin", sha],
            capture_output=True, text=True, timeout=180)
        if fetch.returncode != 0:
            pytest.skip(
                f"historical product commit {sha} is absent and could not be "
                f"fetched; the historical pin is UNVERIFIED in this image: "
                f"{fetch.stderr.strip()}")
    add = subprocess.run(
        ["git", "-C", str(MOUNT), "worktree", "add", "--detach", dest, sha],
        capture_output=True, text=True, timeout=120)
    assert add.returncode == 0, add.stderr


@MOUNT_REQUIRED
def test_population_is_49_enriched_plus_one_control_and_pins_match():
    from evaluation import post_repair_family_ca_falsifier as PRF
    hyp, freeze = _load(HYPO), _load(FREEZE)
    bundles = hyp["population_FROZEN"]["bundles"]
    assert len(bundles) == 50
    assert sum(1 for b in bundles if b["enriched"]) == 49
    assert sum(1 for b in bundles if not b["enriched"]) == 1
    control = [b for b in bundles if not b["enriched"]][0]
    assert "first_page.bundle.json" in control["path"]

    # 1) Live-mount drift is allowed ONLY as the documented head advance: every
    #    frozen population bundle, probe-family member and evaluation-instrument
    #    byte must still match against the LIVE mount. This run's freeze pins the
    #    mount identity as state/product.json + head, so those are the only two
    #    live pins that may legitimately differ after the product advanced.
    live = PRF.verify_pins(hyp, freeze)
    live_failed = [c["input"] for c in live["checks"] if not c["match"]]
    assert set(live_failed) <= {"mount_head",
                                "mount:state/product.json"}, live_failed

    # 2) The historical head itself is verified against the historical tree,
    #    not waived: all pins must match at the commit the freeze names.
    historical_sha = hyp["population_FROZEN"]["expected_product_mount_head"]
    assert historical_sha == "5fb312e4a71c99dce0ed6fbd2d3fce9a88ad6e68"
    with tempfile.TemporaryDirectory(prefix="prf40258497460-hist-") as td:
        _materialise_historical_mount(historical_sha, td)
        try:
            hist = copy.deepcopy(hyp)
            hist["population_FROZEN"]["product_mount"] = td
            pins = PRF.verify_pins(hist, freeze)
            failed = [c for c in pins["checks"] if not c["match"]]
            assert not failed, failed
            assert pins["all_match"] is True
        finally:
            subprocess.run(
                ["git", "-C", str(MOUNT), "worktree", "remove", "--force", td],
                capture_output=True, text=True, timeout=120)


@MOUNT_REQUIRED
def test_population_paths_are_product_fixed_path_family():
    hyp = _load(HYPO)
    product = _load(PRODUCT_FAMILY)
    pop = {b["path"] for b in hyp["population_FROZEN"]["bundles"] if b["enriched"]}
    prod = {b["path"] for b in product["fixed_path_family"]["bundles"]}
    assert len(pop) == 49
    assert pop == prod


@MOUNT_REQUIRED
def test_frozen_probe_family_is_byte_unchanged_15_members():
    hyp = _load(HYPO)
    fam = hyp["frozen_probe_family_FROZEN"]["members_sha256"]
    assert len(fam) == 15
    for rel, expected in fam.items():
        assert (MOUNT / rel).is_file(), rel
        assert _sha(MOUNT / rel) == expected, rel


@MOUNT_REQUIRED
def test_precondition_result_is_14_of_15_and_item_2_gated():
    rec = _load(RESULT)
    pre = rec["precondition"]
    assert pre["H1_precondition_leg_landed"] is True
    assert pre["H2_precondition_full_family_regenerated"] is False
    rel = pre["set_relations_REQUIREMENT_16"]
    assert rel["member_for_member_matching"]["matched_members"] == 14
    assert rel["member_for_member_matching"]["of"] == 15
    assert rel["roles_frozen_family"] == {"offline/rent-default": 11,
                                          "server/served": 4}
    assert rel["roles_post_repair"] == {"offline/business-judgment-rule": 10,
                                        "offline/corporate-criminal-liability": 9,
                                        "offline/petty-theft-dismissal": 9,
                                        "offline/rent-default": 18,
                                        "server/served": 3}
    assert pre["product_claim_adjudication"][
        "claim_roles_satisfied_by_post_repair_bytes"] is True
    assert pre["item_2_full_protocol_status"].startswith("NOT_YET_DISCRIMINATING")


def test_result_is_non_vacuous_sound_counter_row_present():
    rec = _load(RESULT)
    assert rec["verdict"] == "SOUND_COUNTER_ROW_PRESENT"
    assert rec["exit_code"] == 0
    assert rec["falsification_proven"] is False
    assert rec["vacuous_reasons"] == []
    assert rec["controls"]["all_hold"] is True
    assert rec["hypothesis_checks"]["H4_controls_all_hold"] is True
    assert rec["hypothesis_checks"]["H5_pins_identical_before_after"] is True
    assert all(rec["consistency"].values())


def test_aggregate_is_55_verified_zero_defective_and_19_bundles_with_sound_row():
    agg = _load(RESULT)["aggregate"]
    assert agg["n_bundles"] == 50
    assert agg["n_enriched"] == 49
    assert agg["n_verified_scored_rows_total"] == 55
    assert agg["n_defective_verified_scored_rows_total"] == 0
    assert agg["n_enriched_with_verified_scored_row"] == 19
    assert agg["n_enriched_with_sound_counter_row"] == 19
    assert agg["defect_histogram"] == {}
    assert agg["distinct_defective_decision_ids"] == []


@MOUNT_REQUIRED
def test_product_claim_corroborated_per_bundle_but_not_adopted():
    rec = _load(RESULT)
    product = _load(PRODUCT_FAMILY)
    prod = {b["path"]: b for b in product["fixed_path_family"]["bundles"]}
    checked = 0
    for b in rec["bundles"]:
        if not b["enriched"]:
            continue
        p = prod[b["path"]]
        assert p["n_verified"] == b["n_counter_evidence_verified_scored_rows"], b["path"]
        assert p["n_verified_defective"] == \
            b["n_defective_verified_scored_rows"], b["path"]
        checked += 1
    assert checked == 49
    assert sum(b["n_verified"] for b in prod.values()) == 55
    assert sum(b["n_verified_defective"] for b in prod.values()) == 0


@MOUNT_REQUIRED
def test_control_not_enriched_has_zero_issued():
    rec = _load(RESULT)
    control = [b for b in rec["bundles"] if not b["enriched"]]
    assert len(control) == 1
    c = control[0]
    assert c["frozen_surface_gate"]["n_issued"] == 0
    assert c["n_counter_evidence_verified_scored_rows"] == 0
    assert c["n_sound_verified_scored_rows"] == 0


def test_surface_gate_false_and_before_after_caveat_are_published():
    rec = _load(RESULT)
    assert rec["hypothesis_checks"][
        "H1_surface_gates_and_source_validity_on_enriched"] is False
    bad = []
    for b in rec["bundles"]:
        if not b["enriched"]:
            continue
        assert b["source_validity"]["n_rows_missing_id_or_url"] == 0, b["label"]
        assert b["duplicate_suppression"]["duplicates"] == 0, b["label"]
        assert b["frozen_surface_gate"]["n_with_empty_evidence"] == 0, b["label"]
        if b["frozen_surface_gate"]["n_issued"] != 1:
            bad.append(b["label"])
    assert len(bad) == 15
    text = REPORT.read_text(encoding="utf-8")
    assert "Surface gate `n_issued == 1` is FALSE on 15/49" in text
    assert "BEFORE/AFTER is NOT a paired comparison" in text
    assert "Independent corroboration, not adoption" in text


def test_benchmark_of_record_is_unchanged_and_not_overwritten():
    old = _load(OLD_FAST_MVP)
    assert old["verdict"] == "SOUND_COUNTER_ROW_PRESENT"
    assert old["aggregate"]["n_verified_scored_rows_total"] == 5
    assert old["aggregate"]["n_defective_verified_scored_rows_total"] == 4
    assert old["aggregate"]["n_enriched_with_sound_counter_row"] == 1
    assert old["aggregate"]["defect_histogram"] == {
        "D2_letterhead_zone": 2, "D3_markup_residue": 2,
        "D4_language_marker_mismatch": 1}
    probe = _load(OLD_PROBE)
    assert probe["H2_verdict"] == "H2_FALSIFIED"
    assert probe["n_verified_rows_total"] == 14
    assert probe["n_verified_rows_with_defects"] > 0
    assert probe["defect_histogram"] == {
        "D2_letterhead_zone": 10, "D3_markup_residue": 4,
        "D4_language_marker_mismatch": 4}


def test_no_frozen_bar_rubric_or_verdict_contract_edited():
    assert _sha(REPO_ROOT / "evaluation/frozen_bars/RULES_LABEL.json") == \
        "4457e971df3dc5d10af2a727aa675afc15a15564c18eed4cede0af5eb41b4608"
    assert _sha(REPO_ROOT / "evaluation/frozen_bars/RULES_GEOMETRY.json") == \
        "a7452748d40c511a14a1c7848ece5fe7f8f8901cc30f45a66918c89eb593a633"
    assert _sha(REPO_ROOT / "evaluation/frozen_bars/VERDICT_CONTRACT.json") == \
        "b9cdb89438a8d16ee165fe2a5d73060524154d8e7ba8e0cab867e8ca17ff414c"


def test_claim_ceiling_keeps_posture_fail_closed():
    rec = _load(RESULT)
    assert rec["packet_admitted"] is False
    assert rec["machine_gate_ready"] is False
    assert rec["human_gate_ready"] is False
    assert rec["ready_for_owner_session"] is False
    assert rec["owner_decision_required"] is False
    assert rec["no_174k_benchmark_rerun"] is True
    assert rec["no_new_thresholds"] is True
    assert rec["packet_of_record_not_scored"] == "39319405429"
    assert rec["benchmark_of_record_untouched"] is True
    assert "does NOT discharge ordered item (2)" in rec["claim_ceiling"]

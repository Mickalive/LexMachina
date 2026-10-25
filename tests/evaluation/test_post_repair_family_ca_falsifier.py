"""Freeze-integrity, set-relation and sweep tests for the v68 post-repair
family CA falsifier (run 40134202991).

Synthetic rows/bundles used here are TEST-ONLY control data: they are never
written to results/ and never enter the claim-bearing population.
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
sys.path.insert(0, str(REPO_ROOT))

from evaluation import counter_evidence_quality_benchmark as CQ  # noqa: E402
from evaluation import fast_mvp_current_head_ca_falsifier as FAS  # noqa: E402
from evaluation import mapping_free_recall_falsifier as MF  # noqa: E402
from evaluation import post_repair_family_ca_falsifier as PRF  # noqa: E402

HYPO = REPO_ROOT / "evaluation/POST_REPAIR_FAMILY_CA_FALSIFIER_40134202991_HYPOTHESIS_V1.json"
FREEZE = REPO_ROOT / "evaluation/POST_REPAIR_FAMILY_CA_FALSIFIER_40134202991_FREEZE_V1.json"
MOUNT = Path("/tmp/lex_accepted/product")


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _hyp() -> dict:
    return json.loads(HYPO.read_text(encoding="utf-8"))


# ---------------------------------------------------------------- freeze ----
def test_hypothesis_sha_matches_freeze_record():
    hyp, freeze = _hyp(), json.loads(FREEZE.read_text(encoding="utf-8"))
    assert _sha(HYPO) == freeze["hypothesis_sha256_at_freeze"]
    assert hyp["frozen_before_execution"] is True
    assert hyp["run_id"] == "40134202991"


def test_frozen_predicate_engine_and_adapter_pins():
    hyp = _hyp()
    expect = hyp["frozen_inputs_REPORTED_ONLY"]
    assert _sha(REPO_ROOT / "evaluation/counter_evidence_quality_benchmark.py") == \
        expect["evaluation/counter_evidence_quality_benchmark.py"] == \
        "aac86527e5e54f0f9c527daac7ff1016d5124731b8ce673797520ff3dd53067d"
    assert _sha(REPO_ROOT / "evaluation/mapping_free_recall_falsifier.py") == \
        expect["evaluation/mapping_free_recall_falsifier.py"]
    assert _sha(REPO_ROOT / "evaluation/fast_mvp_current_head_ca_falsifier.py") == \
        expect["evaluation/fast_mvp_current_head_ca_falsifier.py"]
    assert _sha(REPO_ROOT / "evaluation/frozen_bars/RULES_LABEL.json") == \
        "4457e971df3dc5d10af2a727aa675afc15a15564c18eed4cede0af5eb41b4608"


def test_no_frozen_bar_rubric_or_verdict_contract_edited():
    # the frozen rubric/rule files must still be the accepted bytes; this test
    # fails loudly if any cycle edits them after results are seen.
    assert _sha(REPO_ROOT / "evaluation/frozen_bars/RULES_LABEL.json") == \
        "4457e971df3dc5d10af2a727aa675afc15a15564c18eed4cede0af5eb41b4608"
    assert _sha(REPO_ROOT / "evaluation/frozen_bars/RULES_GEOMETRY.json") == \
        "a7452748d40c511a14a1c7848ece5fe7f8f8901cc30f45a66918c89eb593a633"
    assert _sha(REPO_ROOT / "evaluation/frozen_bars/VERDICT_CONTRACT.json") == \
        "b9cdb89438a8d16ee165fe2a5d73060524154d8e7ba8e0cab867e8ca17ff414c"


# ------------------------------------------------------------- controls ----
def test_controls_battery_all_hold():
    hyp = _hyp()
    sha = _sha(REPO_ROOT / "evaluation/counter_evidence_quality_benchmark.py")
    scored = ["candidate-limiting", "candidate-contrary", "contrary_or_exception", "limiting"]
    battery = FAS.controls(scored, sha)
    assert battery["all_hold"], battery
    assert len(battery["battery"]) == 4


def test_verdict_vocabulary_matches_accepted_adapter():
    hyp = _hyp()
    assert set(hyp["verdict_vocabulary"]) == {
        "CAPABILITY_FALSIFIED_CONTENT_DEFECTIVE",
        "SOUND_COUNTER_ROW_PRESENT",
        "PARTIAL_OR_UNEXPECTED",
        "NOT_MEASURED_VACUOUS",
    }


# -------------------------------------------------------- set relations ----
def test_role_key_and_member_for_member_matching():
    assert PRF._role_key("results/product/offline_slice/X/rent-default.bundle.json") == \
        ("offline", "rent-default")
    assert PRF._role_key("results/product/server_slice/Y/served.bundle.json") == \
        ("server", "served")
    # member-for-member matching uses min() per role, never raw cardinality
    frozen = {"offline/rent-default": 11, "server/served": 4}
    post = {"offline/rent-default": 2, "server/served": 1,
            "offline/petty-theft-dismissal": 1}
    matched = sum(min(frozen.get(k, 0), post.get(k, 0)) for k in
                  set(frozen) | set(post))
    assert matched == 3
    # post-only roles and extra multiplicity never inflate the coverage count
    assert matched == min(11, 2) + min(4, 1)
    assert sum(post.values()) == 4 > matched


def test_precondition_gate_reports_sets_not_cardinalities():
    if not MOUNT.is_dir():
        pytest.skip("accepted product mount absent")
    hyp = _hyp()
    gate = PRF.precondition_gate(hyp, MOUNT)
    rel = gate["set_relations_REQUIREMENT_16"]
    assert rel["frozen_probe_family_n"] == 15
    assert "member_for_member_matching" in rel
    assert rel["member_for_member_matching"]["of"] == 15
    # all three relations are published (requirement 16)
    for key in ("path_identity", "roles_frozen_family", "roles_post_repair",
                "member_for_member_matching"):
        assert key in rel
    assert gate["item_2_leg_status"] in {"LANDED", "NOT_LANDED"}
    if not gate["H2_precondition_full_family_regenerated"]:
        assert gate["item_2_full_protocol_status"].startswith("NOT_YET_DISCRIMINATING")


def test_leg_markers_present_on_current_product_head():
    if not (MOUNT / "product/query/counter_evidence_span.py").is_file():
        pytest.skip("accepted product mount absent")
    hyp = _hyp()
    markers = PRF.leg_markers(MOUNT, hyp)
    assert markers["all_markers_present"], markers["markers"]


# --------------------------------------------------------- synthetic sweeps --
def _synthetic_mount(tmp_path: Path, *, evidence: str, language: str,
                     pivot_absent: bool, verified: bool,
                     prefix: str = "") -> Path:
    """TEST-ONLY bundle: one candidate-limiting row with a downgrade record."""
    full_text = prefix + evidence
    row = {
        "decision_id": "SYNTH_TEST_ROW",
        "counter_status": "candidate-limiting",
        "counter_evidence": evidence,
        "counter_evidence_verified": verified,
        "full_text": full_text,
        "snippet": "",
        "regeste": "",
        "language": language,
    }
    ces = {
        "content_filter": {"mode": "test"},
        "downgrades": [{
            "decision_id": "SYNTH_TEST_ROW",
            "leg": "test",
            "reason_code": "test",
            "defects": [],
        }],
        "abstained_ids": ["SYNTH_TEST_ROW"] if pivot_absent else [],
        "abstention_reasons": {"pivot_absent": 1} if pivot_absent else {},
    }
    bundle = {"decisions": [row], "provenance": {"counter_evidence_span": ces}}
    mount = tmp_path / "mount"
    target = mount / "results/product/offline_slice/T"
    target.mkdir(parents=True)
    (target / "q.bundle.json").write_text(json.dumps(bundle), encoding="utf-8")
    return mount


def test_false_reject_detected_on_clean_downgraded_evidence():
    clean = ("Considérant que la résiliation du bail et le recours du locataire "
             "supposent le respect de l'art. 257d CO ; la jurisprudence limite "
             "néanmoins cette règle lorsque le bailleur accepte un paiement tardif.")
    with tempfile.TemporaryDirectory(prefix="prf-synth-") as td:
        mount = _synthetic_mount(Path(td), evidence=clean, language="fr",
                                 pivot_absent=False, verified=False,
                                 prefix="x" * 400 + "\n")
        # precondition of the fixture: frozen predicates see NO defect here
        probe = CQ.classify_verified_row({
            "decision_id": "SYNTH_TEST_ROW",
            "counter_status": "candidate-limiting",
            "counter_evidence": clean, "counter_evidence_verified": False,
            "full_text": "x" * 400 + "\n" + clean, "snippet": "", "regeste": "",
            "language": "fr"})
        assert probe["defects"] == [], probe
        scored = ["candidate-limiting"]
        path = "results/product/offline_slice/T/q.bundle.json"
        out = PRF.downgraded_row_sweep(
            mount, [{"label": "synth", "path": path}], scored)
        assert out["n_downgrade_records"] == 1
        assert out["false_rejects_n"] == 1, out
        assert out["zero_false_rejects"] is False


def test_no_false_reject_on_defective_downgraded_evidence():
    defective = "<mark>Selon</mark> l'art. 337 CO, l'employeur et le travailleur"
    with tempfile.TemporaryDirectory(prefix="prf-synth-") as td:
        mount = _synthetic_mount(Path(td), evidence=defective, language="fr",
                                 pivot_absent=False, verified=False,
                                 prefix="y" * 400 + "\n")
        probe = CQ.classify_verified_row({
            "decision_id": "SYNTH_TEST_ROW",
            "counter_status": "candidate-limiting",
            "counter_evidence": defective, "counter_evidence_verified": False,
            "full_text": "y" * 400 + "\n" + defective, "snippet": "",
            "regeste": "", "language": "fr"})
        assert probe["defects"] == ["D3_markup_residue"], probe
        out = PRF.downgraded_row_sweep(
            mount, [{"label": "synth",
                     "path": "results/product/offline_slice/T/q.bundle.json"}],
            ["candidate-limiting"])
        assert out["false_rejects_n"] == 0, out
        assert out["zero_false_rejects"] is True


def test_path_scope_residual_detected_when_defective_incumbent_stays_verified():
    defective = ("Kantonsgericht von Graubünden\n"
                 "Dretgira chantunala dal Grischun\n"
                 "Tribunale cantonale dei Grigioni\n________________________")
    with tempfile.TemporaryDirectory(prefix="prf-synth-") as td:
        mount = _synthetic_mount(Path(td), evidence=defective, language="de",
                                 pivot_absent=True, verified=True)
        out = PRF.downgraded_row_sweep(
            mount, [{"label": "synth",
                     "path": "results/product/offline_slice/T/q.bundle.json"}],
            ["candidate-limiting"])
        assert out["path_scope_residual_cleared"] is False, out
        assert len(out["path_scope_residual_rows"]) == 1


def test_path_scope_residual_cleared_when_incumbent_downgraded():
    defective = ("<mark>Selon</mark> l'art. 337 CO ; ")
    with tempfile.TemporaryDirectory(prefix="prf-synth-") as td:
        mount = _synthetic_mount(Path(td), evidence=defective, language="fr",
                                 pivot_absent=True, verified=False)
        out = PRF.downgraded_row_sweep(
            mount, [{"label": "synth",
                     "path": "results/product/offline_slice/T/q.bundle.json"}],
            ["candidate-limiting"])
        assert out["path_scope_residual_cleared"] is True, out


# ------------------------------------------- mount population pin checks ----
def _materialise_historical_mount(sha: str, dest: str) -> None:
    """Check out the frozen historical product tree named by the hypothesis.

    The accepted product mount legitimately advances after the freeze, so the
    historical pins cannot be re-verified against the live mount. Anchoring to
    the source commit the hypothesis itself names is the same repair used for
    the historical wrapper pin in the retrieval benchmark: the assertion is not
    weakened, only pointed at the tree it was frozen on.
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


@pytest.mark.skipif(not MOUNT.is_dir(), reason="accepted product mount absent")
def test_population_and_baseline_family_pins_match_historical_mount():
    hyp = _hyp()
    freeze = json.loads(FREEZE.read_text(encoding="utf-8"))

    # 1) Live-mount drift is allowed ONLY as the documented head advance; every
    #    frozen bundle, baseline-family member and instrument byte must still
    #    match the live accepted mount.
    live = PRF.verify_pins(hyp, freeze)
    live_failed = [c["input"] for c in live["checks"] if not c["match"]]
    assert set(live_failed) <= {"mount_head"}, live_failed

    # 2) The historical head itself is verified against the historical tree,
    #    not waived. All pins must match at the commit the freeze names.
    historical_sha = hyp["population_FROZEN"]["expected_product_mount_head"]
    with tempfile.TemporaryDirectory(prefix="prf-hist-") as td:
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


@pytest.mark.skipif(not MOUNT.is_dir(), reason="accepted product mount absent")
def test_score_bundle_reuses_accepted_adapter_on_post_repair_bytes():
    hyp = _hyp()
    scored = ["candidate-limiting", "candidate-contrary", "contrary_or_exception",
              "limiting"]
    mount = Path(hyp["population_FROZEN"]["product_mount"])
    rec = FAS.score_bundle(mount, hyp["population_FROZEN"]["bundles"][0], scored)
    assert rec["source_validity"]["n_rows_missing_id_or_url"] == 0
    assert "language_robustness" in rec  # multilingual reuse on every bundle

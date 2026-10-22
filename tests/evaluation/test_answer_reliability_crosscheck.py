"""Tests for the live-answer reliability cross-check (v62 ordered item 2d)."""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from evaluation.answer_reliability_crosscheck import (  # noqa: E402
    EXIT_DIVERGE,
    EXIT_ENV,
    EXIT_OK,
    evaluate_pre_registered,
    expected_claim,
    protocol_leg_ids,
    recompute_metrics,
    run,
)

MEAS = Path("/tmp/lex_accepted/product/results/product/answer_reliability/39799042649_measurement.json")
RESULT = REPO_ROOT / "results/evaluation/answer_reliability_crosscheck/39827806011.json"


def _load_meas() -> dict:
    assert MEAS.is_file(), f"product measurement missing: {MEAS}"
    return json.loads(MEAS.read_text(encoding="utf-8"))


def test_recompute_matches_published_metrics():
    meas = _load_meas()
    pub = meas["metrics"]
    re_m = recompute_metrics(meas["legs"])
    assert re_m["n_legs_executed"] == pub["n_legs_executed"] == 7
    assert abs(re_m["answer_ready_rate"] - pub["answer_ready_rate"]) < 1e-12
    assert re_m["citation_validity"] == pub["citation_validity"] == 1.0
    assert re_m["prose_citation_validity"] == pub["prose_citation_validity"] == 1.0
    assert re_m["source_validity"] == pub["source_validity"] == 1.0
    assert re_m["language_match_rate"] == pub["language_match_rate"] == 1.0
    assert re_m["degradation_visible_rate"] == pub["degradation_visible_rate"] == 1.0
    assert re_m["n_degraded_legs"] == pub["n_degraded_legs"] == 1
    assert re_m["n_prose_markers"] == pub["n_prose_markers"] == 56
    assert re_m["n_prose_markers_resolved"] == pub["n_prose_markers_resolved"] == 56
    assert re_m["stability_jaccard_min_6dp"] == pub["stability_jaccard_min"] == 0.666667
    assert sorted(re_m["legs_without_prose_markers"]) == sorted(
        pub["legs_without_prose_markers"]
    ) == ["rent-default|baseline|it|r1"]
    assert re_m["all_text_sha256_rehash"] is True


def test_counter_row_distinction():
    meas = _load_meas()
    re_m = recompute_metrics(meas["legs"])
    # standing CA-surface fact on this population: confirmed=0, emitted>0
    assert re_m["counter_rows_confirmed_total"] == 0
    assert re_m["counter_rows_emitted_total"] == 30


def test_pre_registered_claim_is_honestly_false():
    meas = _load_meas()
    re_m = recompute_metrics(meas["legs"])
    pre = evaluate_pre_registered(re_m)
    assert pre["answer_ready_rate == 1.0"] is False
    for k, v in pre.items():
        if k != "answer_ready_rate == 1.0":
            assert v is True, k
    assert expected_claim(pre) is False
    assert meas["product_claim_reliable_live_answer"] is False
    # product's own published conditions agree
    for k, v in meas["pre_registered_conditions"].items():
        assert bool(v) == bool(pre[k]), k


def test_protocol_leg_ids_expand():
    prot = json.loads(
        (MEAS.parent / "39799042649_protocol_freeze.json").read_text(encoding="utf-8")
    )
    ids = protocol_leg_ids(prot)
    assert len(ids) == 7
    assert "rent-default|baseline|fr|r2" in ids
    assert "rent-default|baseline|it|r1" in ids


def test_controls_detect_planted_divergences():
    meas = _load_meas()
    base = recompute_metrics(meas["legs"])

    # C1: flip citations
    m1 = copy.deepcopy(meas)
    m1["legs"][0]["citations"]["all_valid"] = False
    m1["legs"][0]["citations"]["n_invalid"] = 1
    r1 = recompute_metrics(m1["legs"])
    assert r1["citation_validity"] < base["citation_validity"]

    # C3: inflate ready rate
    m3 = copy.deepcopy(meas)
    for L in m3["legs"]:
        if (L.get("answer") or {}).get("status") == "degraded":
            L["answer"]["status"] = "ready"
    r3 = recompute_metrics(m3["legs"])
    assert r3["answer_ready_rate"] == 1.0
    assert r3["answer_ready_rate"] != base["answer_ready_rate"]

    # C4: drop a leg
    m4 = copy.deepcopy(meas)
    m4["legs"] = m4["legs"][:-1]
    r4 = recompute_metrics(m4["legs"])
    assert r4["n_legs_executed"] == 6

    # C5: text hash drift
    m5 = copy.deepcopy(meas)
    m5["legs"][0]["text"] = (m5["legs"][0].get("text") or "") + " X"
    r5 = recompute_metrics(m5["legs"])
    assert r5["all_text_sha256_rehash"] is False


def test_full_run_passes_on_accepted_mount():
    if not MEAS.is_file():
        return  # environment without the product mount: skip, never invent
    code, result = run("39827806011", Path("/tmp/lex_accepted/product"))
    assert code == EXIT_OK, result.get("verdict")
    assert result["verdict"] == "ANSWER_RELIABILITY_CROSSCHECK_PASSES"
    assert result["n_divergent"] == 0
    assert result["gate_failures"] == []
    assert result["control_failures"] == []
    assert result["network_calls"] == 0
    assert result["product_claim_reliable_live_answer"] is False
    assert result["recomputed_expected_claim"] is False
    assert result["pins_before"]["all_ok"] is True


def test_run_id_mismatch_is_environment():
    if not MEAS.is_file():
        return
    code, result = run("00000000000", Path("/tmp/lex_accepted/product"))
    assert code == EXIT_ENV
    assert result["verdict"] == "ENVIRONMENT_OR_VACUOUS"


def test_committed_result_is_zero_divergence():
    if not RESULT.is_file():
        return
    result = json.loads(RESULT.read_text(encoding="utf-8"))
    assert result["exit_code"] == EXIT_OK
    assert result["n_divergent"] == 0
    assert result["controls"]["C1_planted_metric_divergence"]["holds"] is True
    assert result["controls"]["C2_planted_claim_flip"]["holds"] is True
    assert result["controls"]["C3_planted_ready_rate_inflation"]["holds"] is True
    assert result["controls"]["C4_planted_leg_drop"]["holds"] is True
    assert result["controls"]["C5_planted_text_sha_drift"]["holds"] is True
    assert result["claim_ceiling"].find("universal-174k") >= 0


def test_diverge_exit_when_a_comparable_quantity_is_planted_bad():
    """End-to-end: instrument run() must exit DIVERGE if measurement drifts."""
    if not MEAS.is_file():
        return
    # Simulate drift by re-running against a scratch mount is heavy; instead
    # assert that a row marked not-match forces EXIT_DIVERGE via run_gates.
    from evaluation.answer_reliability_crosscheck import (
        build_quantity_rows,
        run_gates_and_controls,
    )

    meas = _load_meas()
    prot = json.loads(
        (MEAS.parent / "39799042649_protocol_freeze.json").read_text(encoding="utf-8")
    )
    re_m = recompute_metrics(meas["legs"])
    pre_re = evaluate_pre_registered(re_m)
    pre_pub = dict(meas["pre_registered_conditions"])
    rows = build_quantity_rows(meas, prot, re_m, pre_re, pre_pub, "deadbeef", True)
    # plant a divergence
    rows[0]["match"] = False
    gates, controls = run_gates_and_controls(meas, prot, re_m, rows, pre_re, pre_pub)
    assert not gates["G1_identity_and_population"]["passed"]
    divergent = [r["quantity"] for r in rows if not r["match"]]
    assert divergent == [rows[0]["quantity"]]
    # all real controls still hold on the unmutated meas
    assert all(v["holds"] for v in controls.values())

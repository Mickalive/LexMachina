"""Guard test for the 174k zoom-quality-vs-ACCEPTED-metadata evaluation (run 36029852715).

Protects the freeze-protected negative result:
- v25_frozen_spec.json / v25_raw_purity.json / v25_raw_zoom.json / v25_verdict.json must exist
- Verdict must equal FAIL (monotonic zoom refinement NOT established for TF-IDF 174k modes)
- Join coverage must be 173,963 (full overlap with accepted metadata)
- The three frozen success checks must be flagged false (no silent weakening of the claim)

This is an additive test; it does not modify the frozen suite in test_verify.py.
"""
import json
from pathlib import Path

import pytest

EVAL_DIR = Path("results/fractal_map/zoom_quality_174k_eval")
PRIMARY = "cited_decisions_tfidf_outcome_hybrid_0.5_174k_v25"
MODES_FROZEN = [
    "cited_decisions_tfidf_outcome_hybrid_0.5_174k_v25",
    "cited_decisions_tfidf_outcome_hybrid_0.7_174k_compressed_v25",
    "cited_decisions_tfidf_outcome_hybrid_0.5_174k",
    "regeste_tfidf_174k",
]


def _load(name: str):
    p = EVAL_DIR / name
    assert p.exists(), f"missing freeze-protected artifact: {p}"
    with open(p) as f:
        return json.load(f)


def test_frozen_spec_present_and_complete():
    spec = _load("v25_frozen_spec.json")
    assert spec["experiment"].startswith("fractal-map 174k zoom-quality")
    assert sorted(spec["modes_frozen"]) == sorted(MODES_FROZEN)
    assert spec["resolutions"] == [0.25, 0.5, 1.0, 2.0, 3.0]
    assert "success_rule" in spec and "PASS iff" in spec["success_rule"]


def test_raw_purity_join_coverage_is_full():
    purity = _load("v25_raw_purity.json")
    for mode in MODES_FROZEN:
        m = purity["modes"][mode]
        assert m["joined_to_meta"] == 173963, f"{mode} join coverage regressed"


def test_raw_zoom_transitions_present_for_primary():
    zoom = _load("v25_raw_zoom.json")
    z = zoom[PRIMARY]
    assert list(z.keys()) == [
        "res_0.25_to_res_0.5",
        "res_0.5_to_res_1.0",
        "res_1.0_to_res_2.0",
        "res_2.0_to_res_3.0",
    ]
    for t in z.values():
        assert t["mean_improvement"] is not None
        assert t["improvement_rate"] is not None


def test_verdict_is_fail_and_checks_recorded():
    v = _load("v25_verdict.json")
    assert v["verdict"] == "FAIL", "negative zoom-refinement result must not be weakened"
    assert v["checks"]["a_branch_monotonic"] is False
    assert v["checks"]["b_area_monotonic"] is False
    assert v["checks"]["c_improvement_rate"] is False
    # numbers pinned to protect the claim
    assert round(v["checks"]["branch_purity_res0.25"], 4) == 0.5525
    assert round(v["checks"]["branch_purity_res3.0"], 4) == 0.5273
    assert round(v["checks"]["area_purity_res0.25"], 4) == 0.3134
    assert round(v["checks"]["area_purity_res3.0"], 4) == 0.2622
    assert v["primary_mode"] == PRIMARY
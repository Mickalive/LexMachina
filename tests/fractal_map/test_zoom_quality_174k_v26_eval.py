"""Guard test for the v26 174k evaluation completion + 174k build census (run 36035695081).

Protects the frozen completion claim and the honest negative:
- v26_frozen_spec.json / v26_verdict.json must exist; verdict must equal FAIL (no decision-mappable
  TF-IDF 174k mode supports monotonic zoom-refinement -> v25 negative generalized to the full mappable set)
- All 4 decision-mappable modes must be present in the v26 verdict with per-mode verdict FAIL
- Baseline random purities must be pinned (0.25 / 1/213)
- Census artifacts: 174k_CENSUS_v26_frozen_spec.json / census_v26.json / alignment_probe_v26.json must
  exist and classify: 4 decision-mappable + 2 placeholder-only + 6 misnamed-21k dirs
- Alignment probe verdict CORRUPTED (0.43 agreement -> row->id unrecoverable without full corpus JSONL)
- v25 must remain untouched: the 4 v25 artifacts still exist and verdict still FAIL (freeze protection)

Additive test; does not modify the frozen suite in test_verify.py.
"""
import json
from pathlib import Path

CENSUS_DIR = Path("results/fractal_map/legal_distance_modes")
EVAL_DIR = Path("results/fractal_map/zoom_quality_174k_eval")
MODES_FROZEN = [
    "cited_decisions_tfidf_outcome_hybrid_0.5_174k_v25",
    "cited_decisions_tfidf_outcome_hybrid_0.7_174k_compressed_v25",
    "cited_decisions_tfidf_outcome_hybrid_0.5_174k",
    "regeste_tfidf_174k",
]


def _load(name, base=EVAL_DIR):
    p = base / name
    assert p.exists(), f"missing freeze-protected artifact: {p}"
    with open(p) as f:
        return json.load(f)


def test_v26_frozen_spec_present():
    spec = _load("v26_frozen_spec.json")
    assert spec["experiment"].startswith("fractal-map 174k zoom-quality completion")
    assert sorted(spec["modes_frozen"]) == sorted(MODES_FROZEN)
    assert spec["resolutions"] == [0.25, 0.5, 1.0, 2.0, 3.0]
    assert spec["github_run"] == 36035695081
    assert "overall_verdict_rule" in spec and "PASS iff ANY" in spec["overall_verdict_rule"]


def test_v26_verdict_fail_all_modes():
    v = _load("v26_verdict.json")
    assert v["overall_verdict"] == "FAIL", "generalized negative must not be weakened"
    assert sorted(v["modes"].keys()) == sorted(MODES_FROZEN)
    for mode in MODES_FROZEN:
        m = v["modes"][mode]
        assert m["per_mode_verdict"] == "FAIL", f"{mode} must be FAIL"
        assert m["joined_to_meta"] == 173963, f"{mode} join coverage regressed"
        assert m["checks"]["branch_monotonic_res3_vs_res0.25"] is False
        assert m["checks"]["improvement_rate_gt_0.5_on_2_of_4"] is False


def test_v26_baseline_pinned():
    v = _load("v26_verdict.json")
    assert v["baseline"]["branch_random"] == 0.25
    assert round(v["baseline"]["area_random"], 4) == round(1 / 213, 4)


def test_v26_primary_reproduces_v25_purity():
    v = _load("v26_verdict.json")
    primary = v["modes"][MODES_FROZEN[0]]
    assert round(primary["branch_purity"]["res_0.25"], 4) == 0.5525
    assert round(primary["branch_purity"]["res_3.0"], 4) == 0.5273
    assert round(primary["area_purity"]["res_0.25"], 4) == 0.3134
    assert round(primary["area_purity"]["res_3.0"], 4) == 0.2622


def test_v25_freeze_protection_intact():
    v25 = _load("v25_verdict.json")
    assert v25["verdict"] == "FAIL"
    for name in ["v25_frozen_spec.json", "v25_raw_purity.json", "v25_raw_zoom.json", "v25_verdict.json"]:
        assert (EVAL_DIR / name).exists(), f"v25 artifact must not be deleted: {name}"


def test_census_spec_and_classification():
    spec = _load("174k_CENSUS_v26_frozen_spec.json", CENSUS_DIR)
    assert "classification_rules" in spec
    census = _load("census_v26.json", CENSUS_DIR)
    counts = census["summary"]["counts"]
    assert counts["true_174k_decision_mappable"] == 4
    assert counts["true_174k_placeholder_only"] == 2
    assert counts["misnamed_21k_build"] == 6
    for mode in MODES_FROZEN:
        assert census["dirs"][mode]["classification"] == "true_174k_decision_mappable"


def test_alignment_probe_corrupted():
    probe = _load("alignment_probe_v26.json", CENSUS_DIR)
    r1 = probe["results"]["row_order_vs_eval_metadata"]
    assert r1["candidate_agreement"] is not None
    assert r1["candidate_agreement"] < 0.9, "row->id alignment must NOT be recoverable"
    assert r1["verdict"] == "REJECTED"
    assert probe["results"]["cluster_metadata_rowid_integrity"]["verdict"] == "CORRUPTED"
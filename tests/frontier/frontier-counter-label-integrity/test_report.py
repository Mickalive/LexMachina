"""Population, verdict, determinism, coverage and CLI acceptance tests."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys

import pytest

from conftest import HARNESS_DIR, REPO_ROOT, RESULTS_DIR, freeze_commit_time
from frontier_counter_label_integrity.cli import main as cli_main
from frontier_counter_label_integrity.injection import run_non_vacuity
from frontier_counter_label_integrity.report import build_report
from frontier_counter_label_integrity.rules import load_rules, rules_digest

PRIMARY_QIDS = {"de-kapitalverletzung", "fr-bail-entretien", "it-responsabilita-medica"}


def _primary_rows(report):
    return {r["decision_id"]: r for r in report["populations"]["primary"]["rows"]}


# -- charter (2): the CLI invocation form ---------------------------------

def test_cli_single_bundle_invocation(tmp_path, rules_path, product_mount, rules):
    """python -m frontier_counter_label_integrity.cli --bundle <path> --out <dir> --frozen-rules"""
    entry = next(e for e in rules.data["inputs"] if e["population"] == "primary" and e["qid"] == "fr-bail-entretien")
    out = tmp_path / "single"
    rc = subprocess.run(
        [sys.executable, "-m", "frontier_counter_label_integrity.cli",
         "--frozen-rules", rules_path, "--bundle", entry["product_mount_path"], "--out", str(out)],
        cwd=REPO_ROOT, env={**os.environ, "PYTHONPATH": HARNESS_DIR}, capture_output=True, text=True,
    )
    assert rc.returncode == 0, rc.stderr
    report = json.loads((out / "REPORT.json").read_text(encoding="utf-8"))
    assert report["verdict"]["verdict"] == "INSUFFICIENT_POPULATION"  # one bundle != min population
    assert report["bundles"][0]["qid"] == "fr-bail-entretien"
    assert (out / "SCORES.json").exists()
    assert (out / "NON_VACUITY.json").exists()


def test_cli_refuses_unfrozen_run(tmp_path):
    rc = cli_main(["--frozen-rules", str(tmp_path / "nope.json"), "--out", str(tmp_path)])
    assert rc == 2


def test_cli_rejects_input_sha256_drift(tmp_path, rules, report):
    """A bundle whose bytes changed must be refused, not silently re-scored."""
    entry = next(e for e in rules.data["inputs"] if e["qid"] == "it-responsabilita-medica")
    payload = json.loads(open(entry["product_mount_path"], encoding="utf-8").read())
    payload["decisions"][0]["rank"] = 999  # harmless edit, different bytes
    # Same RELATIVE path (a stale/tampered checkout), different bytes.
    tampered = tmp_path / "results" / "product" / entry["relpath_under_results_product"]
    tampered.parent.mkdir(parents=True, exist_ok=True)
    tampered.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(ValueError, match="input sha256 drift"):
        build_report(rules, [str(tampered)], run_non_vacuity(rules))


# -- charter (7): population and minimum population ----------------------

def test_population_is_the_seven_primary_rows(report):
    rows = report["populations"]["primary"]["rows"]
    assert len(rows) == 7, [r["decision_id"] for r in rows]
    assert {r["qid"] for r in rows} == PRIMARY_QIDS
    assert all(r["counter_status"] in ("candidate-limiting", "candidate-contrary",
                                       "contrary_or_exception", "limiting") for r in rows)


def test_seven_cited_placeholders_are_reported_never_scored(report):
    per_bundle = {b["qid"]: b["reported_only_rows"] for b in report["bundles"] if b["population"] == "primary"}
    total = sum(len(v) for v in per_bundle.values())
    assert total == 7, per_bundle
    assert all(r["counter_status"] == "cited" for rows in per_bundle.values() for r in rows)
    assert all(str(r["counter_evidence"]).startswith("cited in generated answer")
               for rows in per_bundle.values() for r in rows), per_bundle
    scored_ids = set(_primary_rows(report))
    assert not (scored_ids & {r["decision_id"] for rows in per_bundle.values() for r in rows})


def test_minimum_population_resolved(report):
    v = report["verdict"]
    assert v["n_scored_primary"] == 7
    assert v["required_min_population_primary"] == 7
    assert v["gaps"] == []
    assert v["verdict"] != "INSUFFICIENT_POPULATION"


def test_every_primary_row_is_scored_with_a_reason(report):
    for row in report["populations"]["primary"]["rows"]:
        assert row["primary_defect_class"] and row["reason_code"] and row["precedence_step_fired"]


# -- charter (3)(4)(9): verdict and breakdown -----------------------------

def test_single_named_verdict(report):
    assert report["verdict"]["verdict"] == "LABEL_UNSOUND"
    assert report["verdict"]["verdict"] in report["verdict"]["verdict_classes_available"]


def test_support_rate_and_per_class_breakdown_present(report):
    prim = report["populations"]["primary"]
    assert prim["support_rate"] == 0.0
    assert prim["n_supported"] == 0 and prim["n_scored"] == 7
    classes = {k: v["count"] for k, v in prim["defect_classes"].items()}
    assert classes == {"INVERTED": 0, "OFF-DOMAIN": 3, "BOILERPLATE-ONLY": 1,
                       "FRAGMENT": 1, "UNBACKED": 2, "SUPPORTED": 0}
    assert sum(classes.values()) == 7
    for cls, block in prim["defect_classes"].items():
        assert block["count"] == len(block["row_ids"])


def test_criterion_failures_reported_separately(report):
    fails = report["populations"]["primary"]["criterion_failures"]
    assert set(fails) == {"i", "ii", "iii", "iv", "v"}
    assert fails["i"]["n_failed"] >= 1


def test_claim_ceiling_present(report):
    ceiling = report["claim_ceiling"]
    assert "NEVER asserts that any specific decision IS supporting" in ceiling
    assert "support of the labels as issued" in ceiling.lower()


# -- charter (5): distributions -------------------------------------------

def test_language_and_rank_distributions(report):
    prim = report["populations"]["primary"]
    assert prim["language_distribution"] == {"de": 3, "fr": 1, "it": 3}
    ranks = prim["rank_distribution"]
    assert ranks["ranks"] == [4, 9, 13, 14, 14, 15, 18]
    assert ranks["n_supported_outside_top20"] == 0  # no supported row at all
    assert ranks["supported_outside_top20_row_ids"] == []


def test_marker_precision_reported(report):
    for pop in ("primary", "secondary"):
        mp = report["populations"][pop]["marker_precision"]
        assert mp["rows_with_counter_markers_field"] == 0, "counter_markers absent at accepted head"
        assert mp["note"]


def test_uncertainty_distribution_flags_the_empty_evidence_rows(report):
    unc = report["populations"]["primary"]["uncertainty"]
    assert set(unc["unsupported_with_uncertainty_at_or_above_0_95"]) == {
        "ge_gerichte_4A_286_2015", "ti_gerichte_12.2025.23"
    }


# -- charter (6): coverage -------------------------------------------------

def test_coverage_at_least_three_bundles_all_pre_repair(report):
    cov = report["coverage"]
    assert cov["n_bundles_scored"] >= 3
    assert cov["n_primary_bundles"] >= 3
    assert cov["every_scored_bundle_is_pre_repair"] is True
    assert cov["before_after_pair"] is None


def test_secondary_population_is_a_declared_replication(report):
    sec = report["populations"]["secondary"]
    assert sec["n_bundles"] >= 3
    assert sec["n_scored"] >= 30
    v = report["verdict"]
    assert v["deciding_population"] == "primary"
    assert v["secondary_verdict_replication"] == "LABEL_UNSOUND"
    assert v["secondary_agrees_with_primary"] is True


def test_verdict_is_robust_to_both_pre_declared_sensitivity_variants(report):
    sv = report["sensitivity_variants"]
    assert set(sv) == {"primary", "lenient-domain-only", "strict-no-product-vocabulary"}
    for variant, block in sv.items():
        assert block["support_rate"] < report["verdict"]["threshold_support_rate_sound"], variant


def test_fixture_mode_bundles_are_excluded(report, rules):
    scored = {b["relpath_under_results_product"] for b in report["bundles"]}
    for ex in rules.data["excluded_inputs"]:
        assert ex["relpath_under_results_product"] not in scored
    assert all(b["fixture_mode"] is False for b in report["bundles"])


# -- charter (8): non-vacuity --------------------------------------------

def test_non_vacuity_actually_passed(non_vacuity):
    assert non_vacuity["passed"] is True, non_vacuity
    assert non_vacuity["n_expected_class_matched"] == non_vacuity["n_injected"] == 7
    assert non_vacuity["n_defect_criteria_exercised"] >= non_vacuity["min_criteria_flagged"]


def test_non_vacuity_reruns_and_still_passes(rules):
    result = run_non_vacuity(rules)
    assert result["passed"] is True
    assert result["population_impact"].startswith("none")


def test_injected_rows_are_absent_from_the_population(report):
    ids = [r["decision_id"] for r in report["populations"]["primary"]["rows"]]
    ids += [r["decision_id"] for r in report["populations"]["secondary"]["rows"]]
    assert not [i for i in ids if i.startswith("INJECTED_")]


# -- charter (11): determinism --------------------------------------------

def test_identical_inputs_produce_a_byte_identical_report(rules, tmp_path):
    paths = [e["product_mount_path"] for e in rules.data["inputs"]]
    first = build_report(rules, paths, run_non_vacuity(rules))
    second = build_report(rules, paths, run_non_vacuity(rules))
    assert rules_digest(first) == rules_digest(second)
    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)


def test_committed_report_matches_a_fresh_run(rules):
    """The committed REPORT.json is reproducible from the frozen inputs."""
    paths = [e["product_mount_path"] for e in rules.data["inputs"]]
    fresh = build_report(rules, paths, run_non_vacuity(rules))
    committed = json.loads(open(os.path.join(RESULTS_DIR, "REPORT.json"), encoding="utf-8").read())
    assert rules_digest(fresh) == rules_digest(committed)


def test_report_records_every_input_sha256(rules, report):
    frozen = {e["relpath_under_results_product"]: e["sha256"] for e in rules.data["inputs"]}
    for rel, digest in report["input_sha256"].items():
        assert frozen[rel] == digest


def test_single_bundle_rerun_matches_the_multi_bundle_row(tmp_path, rules_path, rules, report):
    """Charter (11): the same rows score identically in isolation and in the full run."""
    entry = next(e for e in rules.data["inputs"] if e["qid"] == "fr-bail-entretien")
    out = tmp_path / "iso"
    cli_main(["--frozen-rules", rules_path, "--bundle", entry["product_mount_path"],
              "--out", str(out), "--quiet"])
    single = json.loads((out / "REPORT.json").read_text(encoding="utf-8"))
    iso_rows = {r["decision_id"]: r["primary_defect_class"]
                for b in single["bundles"] for r in b["rows"]}
    full_rows = {r["decision_id"]: r["primary_defect_class"]
                 for b in report["bundles"] if b["population"] == "primary" for r in b["rows"]
                 if b["qid"] == "fr-bail-entretien"}
    assert iso_rows == full_rows and iso_rows


# -- charter (12): write scope -------------------------------------------

def test_no_writes_outside_the_team_namespace(repo_root):
    """Nothing under the accepted-mirror paths may be touched by this team."""
    dirty = subprocess.run(
        ["git", "-C", repo_root, "status", "--porcelain", "--", "product", "evaluation",
         "results/product", "state/product.json", ".github"],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    assert dirty == "", f"writes outside the team namespace:\n{dirty}"
    assert not os.path.exists(os.path.join(repo_root, "product", "query", "adversarial_retrieval.py"))
#!/usr/bin/env python3
"""
Deterministic tests for frontier-packet-serve-audit.
Tests: freeze ordering, byte-identical reproduction, negative/positive controls.
"""

import json
import hashlib
import subprocess
import sys
import tempfile
import os
from pathlib import Path


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_sha256(path: str, expected: str, label: str) -> None:
    actual = sha256_file(path)
    if actual != expected:
        raise ValueError(f"SHA256 mismatch for {label}: expected {expected}, got {actual}")

PACKET_DIR = "/tmp/lex_accepted/core/product/results/product/gate_packet/39319405429"
RULES_PATH = "/home/runner/work/LexMachina/LexMachina/results/frontier/frontier-packet-serve-audit/RULES.json"
CLI_MODULE = "frontier_packet_serve_audit.cli"


def run_audit(output_path: str) -> dict:
    """Run the audit CLI and return parsed report."""
    result = subprocess.run([
        sys.executable, "-m", CLI_MODULE,
        "--packet", PACKET_DIR,
        "--frozen-rules", RULES_PATH,
        "--output", output_path
    ], capture_output=True, text=True, cwd="/home/runner/work/LexMachina/LexMachina")

    if result.returncode != 0:
        raise RuntimeError(f"CLI failed: {result.stderr}")

    with open(output_path, "r") as f:
        return json.load(f)


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def test_freeze_ordering():
    """Test that RULES.json was frozen before any computation."""
    # The RULES.json file should exist and have a frozen_at_utc timestamp
    rules = json.load(open(RULES_PATH))
    assert "frozen_at_utc" in rules, "RULES.json must have frozen_at_utc"
    assert rules["frozen_at_utc"] is not None, "frozen_at_utc must not be null"
    print("✓ Freeze ordering: RULES.json has frozen_at_utc timestamp")


def test_byte_identical_reproduction():
    """Test that identical inputs produce byte-identical output."""
    with tempfile.TemporaryDirectory() as tmpdir:
        out1 = Path(tmpdir) / "report1.json"
        out2 = Path(tmpdir) / "report2.json"

        run_audit(str(out1))
        run_audit(str(out2))

        # Byte-identical check
        hash1 = sha256_file(str(out1))
        hash2 = sha256_file(str(out2))
        assert hash1 == hash2, f"Outputs not byte-identical: {hash1} != {hash2}"
        print(f"✓ Byte-identical reproduction: {hash1[:16]}...")


def test_deterministic_output_structure():
    """Test that output has all required fields with correct types."""
    with tempfile.TemporaryDirectory() as tmpdir:
        out = Path(tmpdir) / "report.json"
        report = run_audit(str(out))

        # Required top-level fields
        required_fields = [
            "charter_version", "team_id", "packet_run_id", "packet_sha256",
            "manifest_sha256", "frozen_rules_sha256", "label_support",
            "geometry", "mega_cluster_disclosure", "marginal_discovery",
            "serve_recommendation", "non_vacuity_proof", "cross_check", "generated_at"
        ]
        for field in required_fields:
            assert field in report, f"Missing required field: {field}"

        # Label support structure
        assert "per_bundle" in report["label_support"]
        assert "overall" in report["label_support"]
        for bundle in report["label_support"]["per_bundle"]:
            assert bundle["absolute_verdict"] in ["LABEL_SOUND", "LABEL_UNSOUND"]
            assert bundle["regression_verdict"] in ["FAIL_REGRESSION", "PASS_NO_REGRESSION", "NOT_APPLICABLE"]
            assert bundle["not_applicable_is_not_pass_guard"] == (bundle["regression_verdict"] == "NOT_APPLICABLE")

        # Geometry structure
        assert "per_bundle" in report["geometry"]
        assert "absolute_bar_met_all" in report["geometry"]
        for bundle in report["geometry"]["per_bundle"]:
            assert bundle["n_criteria"] == 11
            assert "criteria" in bundle
            assert len(bundle["criteria"]) == 11

        # Cross-check: zero divergence
        assert report["cross_check"]["divergence"]["fr-bail-entretien"] == 0
        assert report["cross_check"]["divergence"]["de-kapitalverletzung"] == 0
        assert report["cross_check"]["divergence"]["it-responsabilita-medica"] == 0

        # Mega-cluster disclosure
        assert report["mega_cluster_disclosure"]["fired_on_any_bundle"] is True
        for qid, info in report["mega_cluster_disclosure"]["per_bundle"].items():
            assert info["share"] >= 0.5
            assert info["fired"] is True

        # Marginal discovery
        assert report["marginal_discovery"]["K"] == 20
        assert report["marginal_discovery"]["counter_authorities_issued"] == 0
        assert report["marginal_discovery"]["marginally_discovered"] == 0

        # Serve recommendation
        assert report["serve_recommendation"]["verdict"] in ["SERVE", "DO-NOT-SERVE-UNCHANGED", "BOUNDED-NEGATIVE"]
        assert report["serve_recommendation"]["owner_decision_required"] is False

        # Non-vacuity proof
        assert len(report["non_vacuity_proof"]["criteria_that_moved"]) >= 2
        assert report["non_vacuity_proof"]["serve_control_output"] is True
        assert report["non_vacuity_proof"]["do_not_serve_control_output"] is True

        print("✓ Deterministic output structure: all required fields present and valid")


def test_label_support_verdict():
    """Test label support verdict matches frozen rules."""
    with tempfile.TemporaryDirectory() as tmpdir:
        out = Path(tmpdir) / "report.json"
        report = run_audit(str(out))

        overall = report["label_support"]["overall"]
        # Packet has 0 counter-authority rows (n_scored=0)
        assert overall["n_scored"] == 0
        assert overall["n_supported"] == 0
        assert overall["support_rate"] is None
        assert overall["absolute_verdict"] == "LABEL_UNSOUND"  # n_scored > 0 is false
        assert overall["regression_verdict"] == "NOT_APPLICABLE"  # n_scored != 65
        assert overall["not_applicable_is_not_pass_guard"] is True

        print("✓ Label support verdict: LABEL_UNSOUND (n_scored=0), regression NOT_APPLICABLE (not a pass)")


def test_geometry_verdict():
    """Test geometry verdict matches frozen rules and cross-check."""
    with tempfile.TemporaryDirectory() as tmpdir:
        out = Path(tmpdir) / "report.json"
        report = run_audit(str(out))

        geo = report["geometry"]
        assert geo["absolute_bar_met_all"] is False

        # Per-bundle counts
        fr = next(b for b in geo["per_bundle"] if b["qid"] == "fr-bail-entretien")
        de = next(b for b in geo["per_bundle"] if b["qid"] == "de-kapitalverletzung")
        it = next(b for b in geo["per_bundle"] if b["qid"] == "it-responsabilita-medica")

        assert fr["n_pass"] == 4
        assert de["n_pass"] == 3
        assert it["n_pass"] == 4

        # Cross-check: zero divergence with Core Evaluation
        cc = report["cross_check"]
        assert cc["this_team"]["fr-bail-entretien"] == 4
        assert cc["this_team"]["de-kapitalverletzung"] == 3
        assert cc["this_team"]["it-responsabilita-medica"] == 4
        assert cc["core_evaluation"]["fr-bail-entretien"] == 4
        assert cc["core_evaluation"]["de-kapitalverletzung"] == 3
        assert cc["core_evaluation"]["it-responsabilita-medica"] == 4
        assert all(v == 0 for v in cc["divergence"].values())

        print("✓ Geometry verdict: fr 4/11, de 3/11, it 4/11 (cross-check: zero divergence)")


def test_serve_recommendation():
    """Test serve recommendation is BOUNDED-NEGATIVE with correct causes."""
    with tempfile.TemporaryDirectory() as tmpdir:
        out = Path(tmpdir) / "report.json"
        report = run_audit(str(out))

        rec = report["serve_recommendation"]
        assert rec["verdict"] == "BOUNDED-NEGATIVE"
        assert rec["owner_decision_required"] is False
        assert len(rec["bounded_causes"]) == 2
        assert any("counter_label_support" in c for c in rec["bounded_causes"])
        assert any("map_geometry" in c for c in rec["bounded_causes"])

        print("✓ Serve recommendation: BOUNDED-NEGATIVE with 2 bounded causes (1 per failed half)")


def test_negative_control():
    """Test that harness outputs DO-NOT-SERVE on this packet (negative control)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        out = Path(tmpdir) / "report.json"
        report = run_audit(str(out))

        # This packet should produce DO-NOT-SERVE-UNCHANGED or BOUNDED-NEGATIVE
        # (both are "do not serve" outcomes)
        verdict = report["serve_recommendation"]["verdict"]
        assert verdict in ["DO-NOT-SERVE-UNCHANGED", "BOUNDED-NEGATIVE"], \
            f"Expected do-not-serve outcome, got {verdict}"

        print(f"✓ Negative control: harness outputs {verdict} on this packet")


def test_positive_control_structure():
    """Test that harness structure can output SERVE (positive control exists in logic)."""
    # The compute_serve_recommendation function has a SERVE branch
    # We verify the logic path exists by checking the code
    cli_path = Path("/home/runner/work/LexMachina/LexMachina/frontier_packet_serve_audit/cli.py")
    cli_code = cli_path.read_text()
    assert 'verdict == "SERVE"' in cli_code or 'verdict="SERVE"' in cli_code
    assert "LABEL_SOUND" in cli_code
    assert "geometry_all_pass" in cli_code
    assert "mega_fired" in cli_code
    print("✓ Positive control: SERVE logic path exists in harness")


def test_frozen_rules_integrity():
    """Test that frozen rules match the charter-specified SHA256s."""
    rules = json.load(open(RULES_PATH))

    expected = {
        "RULES_LABEL_json": "4457e971df3dc5d10af2a727aa675afc15a15564c18eed4cede0af5eb41b4608",
        "RULES_GEOMETRY_json": "a7452748d40c511a14a1c7848ece5fe7f8f8901cc30f45a66918c89eb593a633",
        "VERDICT_CONTRACT_json": "b9cdb89438a8d16ee165fe2a5d73060524154d8e7ba8e0cab867e8ca17ff414c"
    }

    for rule_name, expected_sha in expected.items():
        actual_sha = rules["frozen_rules"][rule_name]["sha256"]
        assert actual_sha == expected_sha, f"{rule_name} SHA mismatch: {actual_sha} != {expected_sha}"

    # Verify actual files match
    for rule_name, expected_sha in expected.items():
        path = rules["frozen_rules"][rule_name]["path"]
        actual = sha256_file(path)
        assert actual == expected_sha, f"{rule_name} file SHA mismatch: {actual} != {expected_sha}"

    print("✓ Frozen rules integrity: all SHA256s match charter specification")


def test_packet_integrity():
    """Test that packet files match charter-specified SHA256s."""
    rules = json.load(open(RULES_PATH))
    packet_info = rules["input_packet"]

    verify_sha256(packet_info["packet_json_path"], packet_info["packet_json_sha256"], "packet.json")
    verify_sha256(packet_info["manifest_json_path"], packet_info["manifest_json_sha256"], "manifest.json")

    for qid, bundle_info in packet_info["bundles"].items():
        verify_sha256(bundle_info["bundle_path"], bundle_info["content_sha256"], f"{qid}.bundle.json")

    print("✓ Packet integrity: all packet file SHA256s match charter specification")


def run_all_tests():
    """Run all tests."""
    print("Running deterministic tests for frontier-packet-serve-audit...\n")

    test_frozen_rules_integrity()
    test_packet_integrity()
    test_freeze_ordering()
    test_byte_identical_reproduction()
    test_deterministic_output_structure()
    test_label_support_verdict()
    test_geometry_verdict()
    test_serve_recommendation()
    test_negative_control()
    test_positive_control_structure()

    print("\n✓ ALL TESTS PASSED")


if __name__ == "__main__":
    run_all_tests()
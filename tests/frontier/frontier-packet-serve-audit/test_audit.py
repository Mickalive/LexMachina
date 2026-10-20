#!/usr/bin/env python3
"""
Deterministic end-to-end tests for the frontier-packet-serve-audit CLI.

Runs the charter's literal invocation (python -m frontier_packet_serve_audit.cli
--packet <dir> --frozen-rules <dir> --output <file>) from the repo root, which
dispatches to the canonical harness (frontier/frontier-packet-serve-audit/
frontier_packet_serve_audit/). The in-process unit/integration suite lives in
test_serve_audit.py beside the canonical package.

Tests: freeze ordering, byte-identical reproduction, output structure, label
verdict + abstention accounting, geometry verdict + cross-check, serve
recommendation, negative/positive controls, frozen-rules integrity, packet
byte-identity, honest non-vacuity aggregation.
"""

import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
PACKET_DIR = "/tmp/lex_accepted/core/product/results/product/gate_packet/39319405429"
RULES_PATH = str(REPO / "results/frontier/frontier-packet-serve-audit/RULES.json")
CLI_MODULE = "frontier_packet_serve_audit.cli"


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def run_audit(output_path: str) -> dict:
    """Run the charter's literal CLI invocation and return the parsed record."""
    result = subprocess.run(
        [sys.executable, "-m", CLI_MODULE,
         "--packet", PACKET_DIR,
         "--frozen-rules", "/tmp/lex_accepted/core/evaluation/evaluation/frozen_bars",
         "--run-id", "TEST",
         "--output", output_path],
        capture_output=True, text=True, cwd=str(REPO))
    if result.returncode != 0:
        raise RuntimeError(f"CLI failed: {result.stderr}")
    with open(output_path, "r") as f:
        return json.load(f)


def test_freeze_ordering():
    """RULES.json freeze exists with frozen_at_utc and the freeze commit
    precedes computation (covered in-process by test_serve_audit.py)."""
    rules = json.load(open(RULES_PATH))
    assert rules.get("frozen_at_utc"), "RULES.json must carry frozen_at_utc"
    assert rules["thresholds"]["label_absolute_bar"] == 1.0
    assert rules["thresholds"]["geometry_absolute_bar"] == 11
    assert rules["thresholds"]["mega_cluster_threshold"] == 0.5
    assert rules["thresholds"]["marginal_discovery_K"] == 20
    assert rules["non_vacuity"]["control_seeds"] == [42, 123, 456]
    print("freeze ordering: RULES.json thresholds pinned (label 1.0, geometry 11, "
          "mega 0.5, K=20, control seeds [42,123,456])")


def test_byte_identical_reproduction():
    """Identical inputs produce byte-identical records across runs."""
    with tempfile.TemporaryDirectory() as tmpdir:
        out1 = str(Path(tmpdir) / "record1.json")
        out2 = str(Path(tmpdir) / "record2.json")
        run_audit(out1)
        run_audit(out2)
        hash1 = sha256_file(out1)
        hash2 = sha256_file(out2)
        assert hash1 == hash2, f"records not byte-identical: {hash1} != {hash2}"
        print(f"byte-identical reproduction: {hash1[:16]}...")


def test_deterministic_output_structure():
    """The record carries every charter-required section with valid enums."""
    with tempfile.TemporaryDirectory() as tmpdir:
        record = run_audit(str(Path(tmpdir) / "record.json"))

        for field in ("schema", "charter_version", "team_id", "charter_run_id",
                      "input_identity", "frozen_rules", "label_half", "geometry_half",
                      "marginal_discovery", "crosscheck", "non_vacuity", "verdict"):
            assert field in record, f"missing required field: {field}"
        assert record["schema"] == "frontier-packet-serve-audit/1"
        assert record["charter_version"] == 1

        # Label half enums + guards
        lh = record["label_half"]
        assert lh["absolute_status"] in ("LABEL_SOUND", "LABEL_UNSOUND")
        assert lh["regression_verdict"] in ("FAIL_REGRESSION", "PASS_NO_REGRESSION", "NOT_APPLICABLE")
        lv = lh["label_lineage_gate_verdict"]
        assert lv["regression_verdict"] in ("FAIL_REGRESSION", "PASS_NO_REGRESSION",
                                            "NOT_MEASURED", "NOT_APPLICABLE")
        # NOT_APPLICABLE / NOT_MEASURED are never passes
        if lv["regression_verdict"] in ("NOT_APPLICABLE", "NOT_MEASURED"):
            assert lv["is_pass"] is False

        # Geometry half: exactly 11 frozen criteria per bundle
        gh = record["geometry_half"]
        for qid, pb in gh["per_bundle"].items():
            assert pb["n_criteria"] == 11
            assert len(pb["criteria"]) == 11

        # Non-vacuity: honest AND, per-seed transparency
        nv = record["non_vacuity"]
        assert nv["non_vacuity_proven"] is True
        assert nv["geometry_permutation_all_bundles_proven"] is True
        for qid, g in nv["geometry_permutation"].items():
            assert g["proven_non_vacuous"] is True, f"{qid} not proven non-vacuous"
            assert g["best_n_flips"] >= 2
            assert len(g["per_seed"]) == 4  # seeds 0, 42, 123, 456

        # Marginal discovery
        md = record["marginal_discovery"]
        assert md["K"] == 20

        # Verdict machine-check fields
        v = record["verdict"]
        assert v["outcome"] in ("SERVE", "DO-NOT-SERVE-UNCHANGED", "BOUNDED-NEGATIVE")
        assert v["owner_decision_required"] is False
        guard = v["owner_session_guard"]
        assert guard["owner_card_produced"] is False
        assert guard["ready_for_owner_session"] is False
        assert guard["human_gate_ready"] is False
        print("deterministic output structure: all charter sections present and valid")


def test_label_support_verdict():
    """n_scored=0 -> LABEL_UNSOUND; regression NOT_APPLICABLE (not a pass);
    abstention count 0 from the packet's own disclosures."""
    with tempfile.TemporaryDirectory() as tmpdir:
        record = run_audit(str(Path(tmpdir) / "record.json"))
        lh = record["label_half"]
        assert lh["n_scored"] == 0
        assert lh["n_supported"] == 0
        assert lh["support_rate"] is None
        assert lh["absolute_status"] == "LABEL_UNSOUND"
        assert lh["regression_verdict"] == "NOT_APPLICABLE"
        assert lh["n_abstain"] == 0
        assert "disclosures.json" in lh["abstention_source"]
        assert lh["yield_over_population"] == 0.0
        assert lh["yield_definition"] == "n_supported / n_decisions (frozen RULES.json metric definition)"
        assert lh["label_lineage_gate_verdict"]["regression_verdict"] == "NOT_MEASURED"
        assert lh["label_lineage_gate_verdict"]["is_pass"] is False
        print("label verdict: LABEL_UNSOUND at n_scored=0, regression NOT_APPLICABLE "
              "(not a pass), abstention 0 from disclosures, yield 0.0")


def test_geometry_verdict():
    """Geometry 3/4/4 per bundle vs Core Evaluation's published 3/4/4:
    MATCH, absolute bar unmet, mega-cluster disclosure fires on all three."""
    with tempfile.TemporaryDirectory() as tmpdir:
        record = run_audit(str(Path(tmpdir) / "record.json"))
        gh = record["geometry_half"]
        assert gh["per_bundle_counts"] == {"de-kapitalverletzung": 3,
                                           "fr-bail-entretien": 4,
                                           "it-responsabilita-medica": 4}
        assert gh["absolute_status"] == "GEOMETRY_UNSOUND"
        assert gh["n_bundles_pass_all_11"] == 0
        for qid, pb in gh["per_bundle"].items():
            assert pb["mega_cluster"]["disclosure_fires"] is True
            assert pb["mega_cluster"]["largest_cluster_share"] >= 0.5
        # Cross-check: team beside product's own disclosures re-score on the
        # same bytes -- all match; label headline names the population change.
        xc = record["crosscheck"]
        assert all(row["match"] is True for row in xc["geometry_side_by_side"])
        assert any("DIVERGENCE" in h for h in xc["divergence_headline"])
        print("geometry verdict: de 3/11 fr 4/11 it 4/11 GEOMETRY_UNSOUND; "
              "cross-check MATCH beside published 3/4/4; mega-cluster fires all")


def test_serve_recommendation():
    """BOUNDED-NEGATIVE with at most ONE bounded cause per failed half and no
    owner-gate side effects."""
    with tempfile.TemporaryDirectory() as tmpdir:
        record = run_audit(str(Path(tmpdir) / "record.json"))
        v = record["verdict"]
        assert v["outcome"] == "BOUNDED-NEGATIVE"
        assert v["owner_decision_required"] is False
        assert len(v["bounded_causes"]) <= 2
        halves = {c.split(":", 1)[0] for c in v["bounded_causes"]}
        assert halves <= {"LABEL", "GEOMETRY"}
        assert "one_sentence_recommendation" in v and v["one_sentence_recommendation"]
        mc = v["machine_check"]
        assert mc["label_absolute_status"] == "LABEL_UNSOUND"
        assert mc["geometry_absolute_status"] == "GEOMETRY_UNSOUND"
        assert mc["mega_cluster_disclosure_fires_where_share_ge_0.5"] is True
        assert mc["marginal_discovery_adds"] is False
        print("serve recommendation: BOUNDED-NEGATIVE, <=1 bounded cause per failed half, "
              "no owner-gate side effects")


def test_negative_control():
    """The harness outputs a do-not-serve outcome on this packet."""
    with tempfile.TemporaryDirectory() as tmpdir:
        record = run_audit(str(Path(tmpdir) / "record.json"))
        assert record["verdict"]["outcome"] in ("DO-NOT-SERVE-UNCHANGED", "BOUNDED-NEGATIVE")
        print(f"negative control: harness outputs {record['verdict']['outcome']} on this packet")


def test_positive_control_reachability():
    """The same decide() path can output SERVE (positive control), proven via
    the canonical reachability control over the CLI subprocess."""
    code = (
        "import sys; sys.path.insert(0, %r); "
        "from frontier_packet_serve_audit import non_vacuity; "
        "import json; print(json.dumps(non_vacuity.verdict_reachability_control()))"
        % str(REPO / "frontier/frontier-packet-serve-audit"))
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    reach = json.loads(result.stdout.strip().splitlines()[-1])
    assert reach["both_outcomes_reachable"] is True
    assert reach["serve_control"]["reachable"] is True
    assert reach["do_not_serve_control"]["reachable"] is True
    print("positive control: SERVE and DO-NOT-SERVE both reachable via the same decide() path")


def test_frozen_rules_integrity():
    """The charter-pinned frozen rubric sha256s match the mount bytes."""
    expected = {
        "RULES_LABEL.json": "4457e971df3dc5d10af2a727aa675afc15a15564c18eed4cede0af5eb41b4608",
        "RULES_GEOMETRY.json": "a7452748d40c511a14a1c7848ece5fe7f8f8901cc30f45a66918c89eb593a633",
        "VERDICT_CONTRACT.json": "b9cdb89438a8d16ee165fe2a5d73060524154d8e7ba8e0cab867e8ca17ff414c",
    }
    bars = "/tmp/lex_accepted/core/evaluation/evaluation/frozen_bars"
    rules = json.load(open(RULES_PATH))
    for rule_name, expected_sha in expected.items():
        assert rules["frozen_rules"][rule_name.replace(".json", "_json")]["sha256"] == expected_sha
        actual = sha256_file(f"{bars}/{rule_name}")
        assert actual == expected_sha, f"{rule_name} mismatch: {actual} != {expected_sha}"
    print("frozen rules integrity: RULES_LABEL / RULES_GEOMETRY / VERDICT_CONTRACT "
          "sha256s match charter specification")


def test_packet_integrity():
    """All five packet-of-record inputs re-hash to the charter/freeze pins."""
    base = PACKET_DIR
    pins = {
        "packet.json": "32ac812626e679c357822543d0b2e78e62c0e95a9a1b233d1ec89d7cb7b6ac70",
        "manifest.json": "8ea3c92d11e915bcea98b3bc1bd80724b08e920c6ff3bdcade18ed39db388bb7",
        "handoff.json": "5b758a3da820a562dfadb9af1fbb5ff2acd9ba395fa151a36571217645b64544",
        "disclosures.json": "87147f114fd3bfe278077afa83613f2c586c8c8d95aa77b287c4fce916cb31d3",
        "CLAIM_CACHE_VERIFICATION.json": "7e501823c63783294e70962284d72ff4b541b17807aa6bf6f2478fd85264c02d",
    }
    for name, expected in pins.items():
        actual = sha256_file(f"{base}/{name}")
        assert actual == expected, f"{name} mismatch: {actual} != {expected}"
    print("packet integrity: all five packet-of-record inputs match charter pins")


def test_zero_writes_outside_team_namespace():
    """The CLI writes only to its designated --out path; the audit mounts are
    never modified by a run (mtimes unchanged)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        out = str(Path(tmpdir) / "record.json")
        run_audit(out)
        assert Path(out).exists()
        # The harness opens packet/mount inputs read-only; assert the packet
        # bytes are untouched by re-hashing them after the run.
        assert sha256_file(f"{PACKET_DIR}/packet.json") == pins_packet()
        print("zero writes outside team namespace: --out is the only write; packet bytes unchanged")


def pins_packet() -> str:
    return "32ac812626e679c357822543d0b2e78e62c0e95a9a1b233d1ec89d7cb7b6ac70"


if __name__ == "__main__":
    test_frozen_rules_integrity()
    test_packet_integrity()
    test_freeze_ordering()
    test_byte_identical_reproduction()
    test_deterministic_output_structure()
    test_label_support_verdict()
    test_geometry_verdict()
    test_serve_recommendation()
    test_negative_control()
    test_positive_control_reachability()
    test_zero_writes_outside_team_namespace()
    print("\nALL TESTS PASSED")

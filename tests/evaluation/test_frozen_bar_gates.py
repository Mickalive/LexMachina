"""Frozen-bar gates: digests, incumbent recomputation, non-vacuity, semantics.

No threshold is asserted here beyond the frozen RULES files themselves and
the accepted incumbent values of record (labels 5/65 with classes
OFF-DOMAIN 38 / UNBACKED 22 / SUPPORTED 5 / INVERTED 0; geometry de 6 / fr 5 /
it 5). Served-packet tests skip when the accepted product mount is absent.
"""
import copy
import json
import os
from pathlib import Path

import pytest

from evaluation.frozen_bars import geometry_gate, label_gate
from evaluation.frozen_bars.run_bar_gates import (
    EXPECTED_BUNDLE_SHA256,
    EXPECTED_GEOMETRY_PASSES,
    QIDS,
    SERVED_PACKET_DIR,
)

BAR_DIR = Path("evaluation/frozen_bars")
MOUNT_AVAILABLE = all((SERVED_PACKET_DIR / f"{qid}.bundle.json").exists() for qid in QIDS)
needs_mount = pytest.mark.skipif(not MOUNT_AVAILABLE, reason="accepted product mount absent")


def test_rules_label_digest_is_frozen():
    rules = label_gate.load_frozen_rules()
    assert rules.sha256 == "4457e971df3dc5d10af2a727aa675afc15a15564c18eed4cede0af5eb41b4608"


def test_vendored_files_match_pinned_digests():
    """M1 repair (audit 38964129305): vendored rubric/reference bytes are pinned.

    Before this test a weakened vendored edit that INFLATED label support
    would still pass the one-sided regression gate: the label path imports
    the vendored rubric directly and nothing re-checked its bytes.  Every
    vendored file must match VENDORED_SHA256.json at test time, so a lenient
    edit becomes a visible red instead of an invisible green.
    """
    import hashlib
    vendored_sha = json.loads(
        (BAR_DIR / "vendored" / "VENDORED_SHA256.json").read_text(encoding="utf-8"))
    assert vendored_sha["files"], "VENDORED_SHA256.json pins no files"
    mismatches = []
    for rel, expected in vendored_sha["files"].items():
        actual = hashlib.sha256(Path(rel).read_bytes()).hexdigest()
        if actual != expected:
            mismatches.append({"path": rel, "expected_sha256": expected,
                               "actual_sha256": actual})
    assert not mismatches, f"vendored digest mismatch: {mismatches}"


def test_rules_geometry_digest_is_frozen():
    rules = geometry_gate.load_frozen_geometry_rules()
    assert geometry_gate.EXPECTED_RULES_SHA256 == "a7452748d40c511a14a1c7848ece5fe7f8f8901cc30f45a66918c89eb593a633"
    assert rules["charter_version"] == 2
    assert rules["criteria"].keys() == EXPECTED_GEOMETRY_PASSES["de-kapitalverletzung"].keys()


def test_rules_sha_mismatch_refuses_to_score(tmp_path):
    bad = tmp_path / "RULES_LABEL.json"
    bad.write_text(json.dumps({"schema": "frontier-counter-label-integrity/rules/1",
                               "rubric": {}, "verdict_rule": {}, "non_vacuity": {},
                               "lexicons": {}, "question_anchors": {}}))
    with pytest.raises(Exception):
        label_gate.load_frozen_rules(bad)


def test_label_injection_non_vacuity_always_proven():
    rules = label_gate.load_frozen_rules()
    nv = label_gate.non_vacuity_control(rules)
    assert nv["n_cases"] > 0
    assert nv["n_cases_pass"] == nv["n_cases"]
    assert nv["proven_non_vacuous"] is True


def test_label_negative_fixture_scores_zero_support():
    rules = label_gate.load_frozen_rules()
    res = label_gate.score_bundle(str(BAR_DIR / "fixtures" / "label_negative_bundle.json"),
                                  rules, "fr-bail-entretien")
    assert res["n_scored"] == 3
    assert res["n_supported"] == 0
    assert res["classes"] == {"UNBACKED": 3}


def test_label_mixed_fixture_discriminates():
    rules = label_gate.load_frozen_rules()
    res = label_gate.score_bundle(str(BAR_DIR / "fixtures" / "label_mixed_bundle.json"),
                                  rules, "it-responsabilita-medica")
    assert res["n_scored"] == 2
    assert res["n_supported"] == 1


def test_geometry_negative_fixture_fails_absolute():
    rules = geometry_gate.load_frozen_geometry_rules()
    bundle = json.loads((BAR_DIR / "fixtures" / "geometry_negative_bundle.json").read_text())
    V, _ = geometry_gate.score_bundle(bundle, "fr", rules["query_term_lexicons"]["fr-bail-entretien"])
    assert V["STRUCTURE_LARGEST"]["pass"] is False
    assert V["RELATIONS"]["pass"] is False
    assert V["LABEL_CONTENT_FRACTION"]["pass"] is False
    assert geometry_gate.bundle_pass_count(V) < 11


def test_geometry_unknown_bundle_refuses_invented_lexicon():
    rules = geometry_gate.load_frozen_geometry_rules()
    with pytest.raises(ValueError):
        geometry_gate.score_packet({"made-up-qid": {"decisions": []}}, rules)


def test_label_unknown_anchor_refuses_invented_profile(tmp_path):
    """Label-side boundary pin, symmetric with the geometry refusal (R1 repair
    optional hardening, run 38971202786): a qid outside the 5 frozen
    question_anchors is refused with an actionable ValueError, never scored
    with an invented profile. Needs no mount: fixture bytes are committed."""
    rules = label_gate.load_frozen_rules()
    neg = tmp_path / "fr-bail-entretien.bundle.json"
    neg.write_bytes((BAR_DIR / "fixtures" / "label_negative_bundle.json").read_bytes())
    with pytest.raises(ValueError, match="no frozen anchor profile"):
        label_gate.score_packet({"made-up-qid": str(neg)}, rules)


@needs_mount
def test_label_incumbent_recomputed_on_served_packet():
    rules = label_gate.load_frozen_rules()
    paths = {qid: str(SERVED_PACKET_DIR / f"{qid}.bundle.json") for qid in QIDS}
    res = label_gate.score_packet(paths, rules)
    assert res["lineage_matches_incumbent_population"] is True
    assert res["n_scored"] == 65
    assert res["n_supported"] == 5
    assert res["classes"].get("OFF-DOMAIN", 0) == 38
    assert res["classes"].get("UNBACKED", 0) == 22
    assert res["classes"].get("SUPPORTED", 0) == 5
    assert res["classes"].get("INVERTED", 0) == 0
    # Absolute bar is REPORTED, not enforced: unsound but not blocking.
    assert res["absolute_status"] == "LABEL_UNSOUND"
    assert res["absolute_enforced_as_build_blocker"] is False
    assert res["regression_verdict"] == "PASS_NO_REGRESSION"
    assert res["gate_blocks_build"] is False


@needs_mount
def test_geometry_incumbent_recomputed_on_served_packet():
    rules = geometry_gate.load_frozen_geometry_rules()
    bundles = {qid: json.loads((SERVED_PACKET_DIR / f"{qid}.bundle.json").read_text()) for qid in QIDS}
    res = geometry_gate.score_packet(bundles, rules)
    assert res["lineage_matches_incumbent"] is True
    assert res["per_bundle_counts"] == {"de-kapitalverletzung": 6,
                                        "fr-bail-entretien": 5,
                                        "it-responsabilita-medica": 5}
    for qid in QIDS:
        for crit, expected in EXPECTED_GEOMETRY_PASSES[qid].items():
            assert res["per_bundle"][qid]["criteria"][crit]["pass"] is expected, (qid, crit)
    assert res["absolute_status"] == "GEOMETRY_UNSOUND"
    assert res["absolute_enforced_as_build_blocker"] is False
    assert res["regression_verdict"] == "PASS_NO_REGRESSION"
    assert res["gate_blocks_build"] is False


@needs_mount
def test_label_blanked_evidence_packet_fails_regression():
    from evaluation.frozen_bars.run_bar_gates import _blank_label_evidence
    import tempfile
    rules = label_gate.load_frozen_rules()
    with tempfile.TemporaryDirectory() as tmp:
        paths = {}
        for qid in QIDS:
            b = json.loads((SERVED_PACKET_DIR / f"{qid}.bundle.json").read_text())
            p = os.path.join(tmp, f"{qid}.bundle.json")
            with open(p, "w") as fh:
                json.dump(_blank_label_evidence(b), fh)
            paths[qid] = p
        res = label_gate.score_packet(paths, rules)
    assert res["lineage_matches_incumbent_population"] is True
    assert res["n_supported"] == 0
    assert res["regression_verdict"] == "FAIL_REGRESSION"
    assert res["gate_blocks_build"] is True


@needs_mount
def test_geometry_hostile_packet_fails_regression():
    from evaluation.frozen_bars.run_bar_gates import _hostile_geometry
    rules = geometry_gate.load_frozen_geometry_rules()
    bundles = {qid: json.loads((SERVED_PACKET_DIR / f"{qid}.bundle.json").read_text()) for qid in QIDS}
    reg = {qid: _hostile_geometry(b) for qid, b in bundles.items()}
    res = geometry_gate.score_packet(reg, rules)
    assert res["lineage_matches_incumbent"] is True
    assert res["regressed_qids"] != []
    assert res["regression_verdict"] == "FAIL_REGRESSION"
    assert res["gate_blocks_build"] is True


@needs_mount
def test_served_bundle_bytes_match_accepted_inputs():
    import hashlib
    for qid in QIDS:
        h = hashlib.sha256((SERVED_PACKET_DIR / f"{qid}.bundle.json").read_bytes()).hexdigest()
        assert h == EXPECTED_BUNDLE_SHA256[qid], qid


def test_bar_gates_score_arbitrary_packet_without_regression_verdict(tmp_path):
    """Off-lineage scoring (run 38968781838; scope corrected R1, run 38971202786).

    A single-fixture packet built from a FROZEN anchor qid
    (fr-bail-entretien) at a non-incumbent population is outside the
    served-packet lineage, so each gate must report its measurement with
    regression_verdict NOT_APPLICABLE and gate_blocks_build False. Proven
    scope is exactly this: frozen-anchor qids at a non-incumbent population
    do not take a spurious regression verdict and do not block the build,
    without inventing a threshold, without a new absolute bar, and without
    re-measuring any candidate. NOT claimed: executability on genuinely new
    packets — qids outside the frozen anchor/lexicon/language set are
    refused BY DESIGN (geometry ValueError, label refusal; see
    test_geometry_unknown_bundle_refuses_invented_lexicon and
    test_label_unknown_anchor_refuses_invented_profile), so a new product
    packet needs a disclosed rules re-freeze. Needs no mount: fixture bytes
    are committed.
    """
    rules_l = label_gate.load_frozen_rules()
    neg = tmp_path / "fr-bail-entretien.bundle.json"
    neg.write_bytes((BAR_DIR / "fixtures" / "label_negative_bundle.json").read_bytes())
    res_l = label_gate.score_packet({"fr-bail-entretien": str(neg)}, rules_l)
    assert res_l["lineage_matches_incumbent_population"] is False
    assert res_l["n_scored"] == 3
    assert res_l["n_supported"] == 0
    assert res_l["absolute_status"] == "LABEL_UNSOUND"
    assert res_l["absolute_enforced_as_build_blocker"] is False
    assert res_l["regression_verdict"] == "NOT_APPLICABLE"
    assert res_l["gate_blocks_build"] is False

    rules_g = geometry_gate.load_frozen_geometry_rules()
    bundle = json.loads((BAR_DIR / "fixtures" / "geometry_negative_bundle.json").read_text())
    res_g = geometry_gate.score_packet({"fr-bail-entretien": bundle}, rules_g)
    assert res_g["lineage_matches_incumbent"] is False
    assert res_g["absolute_status"] == "GEOMETRY_UNSOUND"
    assert res_g["absolute_enforced_as_build_blocker"] is False
    assert res_g["regression_verdict"] == "NOT_APPLICABLE"
    assert res_g["gate_blocks_build"] is False

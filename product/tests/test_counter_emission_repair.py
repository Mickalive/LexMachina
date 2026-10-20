"""Intake of the accepted ``frontier-counter-label-emission`` repair (dir v61 ordered work 2).

What is locked here
-------------------
1. The vendored accepted repair is byte-identical to the accepted Frontier source
   (``product/vendored/frontier_counter_label_emission/PROVENANCE.json``) and the
   seam REFUSES to run on a drifted component (fail-closed).
2. ``apply_counter_emission_repair`` promotes only the adversarial stage's own
   gate-passed heuristic proposals (``adversarial_retrieval_signal``) into the
   scored ``counter_status`` fields; it skips already-scored rows, never moves
   geometry, is a pure/deterministic function and stamps
   ``counter_proposal_source='heuristic_proposal_promotion_v1'`` on every
   promoted row.
3. The accepted Frontier measurement is harvested as a PRODUCT-OWNED intake
   snapshot carrying the accepted audit gate and the three-number publication
   (n_scored / n_abstained / support-among-issued / yield) beside the frozen
   absolute-bar status. The product reproduction on the committed packet bytes
   matches the intake's per-bundle numbers (n_scored 0 -> 8/8/4).
4. The seam is wired into ``product/query/pipeline.py`` BETWEEN
   ``adversarial_retrieval_pass()`` and ``apply_anchor_labels()`` exactly where
   the accepted INTEGRATION_CONTRACT names.
5. The seam NEVER re-derives a frozen bar/rubric, NEVER re-tunes the accepted
   classifier, NEVER asserts any decision IS supporting/contrary/limiting, and
   NEVER touches ``human_gate_ready`` / ``ready_for_owner_session``.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from product.query import counter_emission_repair as cer  # noqa: E402

INTAKE = (ROOT / "results" / "product" / "frontier_verdicts"
          / "frontier-counter-label-emission_intake.json")
REPRO = (ROOT / "results" / "product" / "counter_emission_repair"
         / "CYCLE_3943548421_reproduction.json")
PACKET = ROOT / "results" / "product" / "gate_packet" / "39319405429" / "questions"
SCORED = ("candidate-limiting", "candidate-contrary", "contrary_or_exception", "limiting")


def _decision(did: str, status: str = "none", signal: dict | None = None) -> dict:
    d = {
        "decision_id": did,
        "counter_status": status,
        "counter_evidence": "",
        "counter_evidence_verified": False,
        "x": 1.0,
        "y": 2.0,
        "cluster_id": 0,
        "is_outlier": False,
        "rank": 5,
        "citation": f"cite-{did}",
    }
    if signal is not None:
        d["adversarial_retrieval_signal"] = signal
    return d


def _bundle(decisions: list[dict]) -> dict:
    return {"bundle_version": "1.0", "query": "q", "decisions": decisions,
            "provenance": {"qid": "de-kapitalverletzung"}}


# --------------------------------------------------------------------------- #
# vendored component
# --------------------------------------------------------------------------- #

def test_vendored_repair_matches_accepted_provenance():
    out = cer.verify_vendored()
    assert out["ok"] is True
    prov = json.loads((cer.VENDORED_ROOT / "PROVENANCE.json").read_text(encoding="utf-8"))
    for rel, meta in prov["vendored_files"].items():
        path = cer.VENDORED_ROOT / rel
        assert path.exists(), f"vendored file missing: {rel}"
        assert hashlib.sha256(path.read_bytes()).hexdigest() == meta["sha256"]


def test_vendored_drift_is_refused(tmp_path):
    """Non-vacuity: a drifted vendored file must make verify_vendored raise."""
    src = cer.VENDORED_ROOT / "frontier_counter_label_emission" / "emission.py"
    payload = src.read_text(encoding="utf-8") + "\n# drift\n"
    (tmp_path / "PROVENANCE.json").write_text(
        (cer.VENDORED_ROOT / "PROVENANCE.json").read_text(encoding="utf-8"),
        encoding="utf-8")
    dst = tmp_path / "frontier_counter_label_emission"
    dst.mkdir()
    (dst / "emission.py").write_text(payload, encoding="utf-8")
    # Point the loader at the synthetic drifted tree and prove it refuses.
    import importlib
    mod = importlib.import_module("product.query.counter_emission_repair")
    orig = mod.VENDORED_ROOT
    mod.VENDORED_ROOT = tmp_path
    try:
        with pytest.raises(ValueError):
            mod.verify_vendored()
    finally:
        mod.VENDORED_ROOT = orig


# --------------------------------------------------------------------------- #
# repair behaviour
# --------------------------------------------------------------------------- #

def test_repair_promotes_only_gate_passed_proposals():
    long_evidence = "x" * 60
    b = _bundle([
        _decision("a", signal={"heuristic_status": "contrary_or_exception",
                               "evidence": long_evidence, "markers": ["m"]}),
        _decision("b", signal={"heuristic_status": "", "evidence": "", "markers": []}),
        _decision("c", signal={"heuristic_status": "candidate-limiting",
                               "evidence": "too short", "markers": []}),
    ])
    out = cer.apply_counter_emission_repair(b)
    by = {d["decision_id"]: d for d in out["decisions"]}
    assert by["a"]["counter_status"] == "contrary_or_exception"
    assert by["a"]["counter_proposal_source"] == cer.REPAIR_ID
    assert by["a"]["counter_evidence"] == long_evidence
    assert by["a"]["counter_evidence_verified"] is False
    assert by["b"]["counter_status"] == "none"
    assert "counter_proposal_source" not in by["b"]
    assert by["c"]["counter_status"] == "none"  # evidence below the frozen min


def test_repair_skips_already_scored_rows():
    b = _bundle([
        _decision("a", status="candidate-limiting",
                  signal={"heuristic_status": "contrary_or_exception", "evidence": "y" * 60}),
        _decision("b", status="contrary_or_exception",
                  signal={"heuristic_status": "limiting", "evidence": "y" * 60}),
    ])
    out = cer.apply_counter_emission_repair(b)
    by = {d["decision_id"]: d for d in out["decisions"]}
    assert by["a"]["counter_status"] == "candidate-limiting"  # unchanged
    assert "counter_proposal_source" not in by["a"]
    assert by["b"]["counter_status"] == "contrary_or_exception"  # unchanged
    assert "counter_proposal_source" not in by["b"]


def test_repair_never_moves_geometry_or_ranks():
    b = _bundle([_decision("a", signal={"heuristic_status": "limiting", "evidence": "z" * 60})])
    before = {k: b["decisions"][0][k] for k in ("x", "y", "cluster_id", "is_outlier", "rank")}
    out = cer.apply_counter_emission_repair(b)
    after = {k: out["decisions"][0][k] for k in ("x", "y", "cluster_id", "is_outlier", "rank")}
    assert before == after
    # and the input bundle is not mutated in place (pure function)
    assert b["decisions"][0]["counter_status"] == "none"


def test_repair_is_deterministic_and_is_a_pure_function():
    sig = {"heuristic_status": "candidate-contrary", "evidence": "q" * 60}
    b = _bundle([_decision("a", signal=sig), _decision("b", signal=sig)])
    r1 = cer.apply_counter_emission_repair(b)
    r2 = cer.apply_counter_emission_repair(b)
    assert json.dumps(r1, sort_keys=True) == json.dumps(r2, sort_keys=True)
    assert b["decisions"][0]["counter_status"] == "none"


def test_repair_provenance_carries_accepted_audit_gate():
    b = _bundle([_decision("a", signal={"heuristic_status": "limiting", "evidence": "w" * 60})])
    out = cer.apply_counter_emission_repair(b)
    prov = out["provenance"]["counter_emission_repair"]
    assert prov["applied"] is True
    assert prov["repair_id"] == cer.REPAIR_ID
    assert prov["audit_gate"] == "PASS"
    assert prov["audit_run_id"] == cer.ADOPTION["audit_run_id"]
    assert prov["n_promoted"] == 1


# --------------------------------------------------------------------------- #
# committed intake snapshot + product reproduction
# --------------------------------------------------------------------------- #

def test_intake_snapshot_is_accepted_and_carries_the_three_numbers():
    art = json.loads(INTAKE.read_text(encoding="utf-8"))
    assert art["accepted"] is True
    assert art["evidence_tier"] == "ACCEPTED"
    assert art["accepted_audit"]["gate"] == "PASS"
    assert art["accepted_audit"]["safe_to_integrate"] is True
    assert art["accepted_audit"]["required_fixes"] == []
    assert art["promotion_outcome"] == "A_EMISSION_RECOVERED"
    assert art["attribution_primary_cause_all_bundles"] == "e_EMISSION_WRITER_ABORT"
    assert art["repair_id"] == cer.REPAIR_ID
    assert art["absolute_bar_status"].startswith("UNMET_AS_WRITTEN")
    for q in ("de-kapitalverletzung", "fr-bail-entretien", "it-responsabilita-medica"):
        row = art["per_bundle"][q]
        assert row["n_scored_before"] == 0
        assert row["n_scored_after"] > 0
        assert row["n_emitted_after"] == 0
        assert row["n_abstained_after"] == row["n_scored_after"]
        assert "support_rate_among_issued" in row and "yield_over_population" in row
        assert row["absolute_bar_satisfied"] is False
        assert row["determinism_identical"] is True and row["determinism_n_runs"] == 3
        assert row["non_vacuity_pass"] is True


def test_product_reproduction_matches_the_intake_numbers():
    intake = json.loads(INTAKE.read_text(encoding="utf-8"))
    repro = json.loads(REPRO.read_text(encoding="utf-8"))
    packet_sha = hashlib.sha256(
        (ROOT / "results" / "product" / "gate_packet" / "39319405429"
         / "packet.json").read_bytes()).hexdigest()
    assert repro["packet_json_raw_sha256"] == packet_sha
    for q, row in repro["per_bundle"].items():
        assert row["bundle_raw_sha256"], q
        assert row["n_scored_before"] == 0
        assert row["n_scored_after"] == intake["per_bundle"][q]["n_scored_after"]
        assert row["n_emitted_after"] == intake["per_bundle"][q]["n_emitted_after"]
        assert row["n_abstained_after"] == intake["per_bundle"][q]["n_abstained_after"]
        assert row["abstention_reasons"] == intake["per_bundle"][q]["abstention_reasons"]


def test_reproduction_can_be_derived_live_from_committed_packet_bytes():
    """The committed reproduction is re-derivable from the packet bytes + seam."""
    from product.query.counter_anchor import apply_anchor_labels
    expected = {"de-kapitalverletzung": 8, "fr-bail-entretien": 8,
                "it-responsabilita-medica": 4}
    for q in expected:
        raw = (PACKET / f"{q}.bundle.json").read_bytes()
        b = json.loads(raw)
        rep = cer.apply_counter_emission_repair(b)
        out = apply_anchor_labels(rep, qid=q)
        ca = out["provenance"]["counter_anchor"]
        assert ca["n_scored"] == expected[q], q
        assert ca["n_abstained"] == expected[q], q
        assert ca["n_emitted"] == 0, q


# --------------------------------------------------------------------------- #
# pipeline wiring + claim ceiling
# --------------------------------------------------------------------------- #

def test_pipeline_wires_the_repair_between_adversarial_and_anchor():
    src = (ROOT / "product" / "query" / "pipeline.py").read_text(encoding="utf-8")
    assert "apply_counter_emission_repair" in src
    adv = src.index("audited = adversarial_retrieval_pass(")
    rep = src.index("audited = apply_counter_emission_repair(audited)")
    anchor = src.index("audited = apply_anchor_labels(")
    assert adv < rep < anchor, "repair must run between adversarial_retrieval_pass and apply_anchor_labels"


def test_claim_ceiling_never_asserts_a_decision_is_a_label():
    banned = (" is supporting", " is contrary", " is limiting",
              "we classify", "we label", "we find")
    for text in (cer.CLAIM_CEILING, json.dumps(cer.ADOPTION)):
        for pat in banned:
            assert pat not in text


def test_seam_never_touches_the_owner_gate():
    src = (ROOT / "product" / "query" / "counter_emission_repair.py").read_text(encoding="utf-8")
    for field in ("human_gate_ready", "ready_for_owner_session"):
        # the seam may only name these in a refusal/negation context
        for line in src.splitlines():
            if field in line:
                assert "never" in line.lower() or "no " in line.lower() or "false" in line.lower()

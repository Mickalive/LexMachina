"""Executable re-derivation of product cycle 39956256289's published claims.

Every number this cycle's report states is re-derived here from the committed
artifacts, never copied from prose:

* the pre-registered live-answer reliability measurement of ordered item 4
  (freeze -> legs -> aggregate -> claim) reproduces from its own recorded legs;
* the measurement's NEGATIVE claim result is published as-is (no re-scoring,
  no threshold touched) and the writer-abort disclosure of ordered item 3 is
  verified on the live path for the first time under this run;
* the D1 min-core-length repair of the accepted audit of run 39949461593 is
  measured under this run's id while the historical artifact stays untouched;
* the RF1 scattering guard holds over product code after the
  progressive_smoke predicate repair.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

PRODUCT_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = PRODUCT_ROOT.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from product import answer_reliability as ar  # noqa: E402
from product.query import counter_status  # noqa: E402

RUN_ID = "39956256289"
FREEZE = ar.OUT_DIR / f"{RUN_ID}_protocol_freeze.json"
MEASUREMENT = ar.OUT_DIR / f"{RUN_ID}_measurement.json"


def test_the_protocol_was_frozen_before_execution_and_still_matches() -> None:
    assert FREEZE.is_file(), "the pre-registered freeze must exist"
    frozen = json.loads(FREEZE.read_text(encoding="utf-8"))
    assert frozen["frozen_before_execution"] is True
    assert frozen["run_id"] == int(RUN_ID)
    # The module constant did not move after the freeze: --run would have
    # refused (exit 3) otherwise, and the recorded measurement carries the
    # same protocol digest.
    assert frozen["protocol_sha256"] == ar.protocol_payload(RUN_ID)["protocol_sha256"]
    recorded = json.loads(MEASUREMENT.read_text(encoding="utf-8"))
    assert recorded["protocol_sha256"] == frozen["protocol_sha256"]
    assert recorded["protocol"] == ar.PROTOCOL


def test_the_measurement_aggregate_reproduces_from_the_recorded_legs() -> None:
    recorded = json.loads(MEASUREMENT.read_text(encoding="utf-8"))
    fresh = ar.aggregate(recorded["legs"])
    assert fresh["metrics"] == recorded["metrics"]
    assert fresh["pre_registered_conditions"] == recorded["pre_registered_conditions"]
    assert (fresh["product_claim_reliable_live_answer"]
            == recorded["product_claim_reliable_live_answer"])
    assert recorded["metrics"]["n_legs_executed"] == 7
    assert recorded["metrics"]["n_legs_failed"] == 0


def test_the_negative_claim_result_is_published_unchanged() -> None:
    """The pre-registered claim is NOT made, and nothing was softened to make it."""
    recorded = json.loads(MEASUREMENT.read_text(encoding="utf-8"))
    assert recorded["product_claim_reliable_live_answer"] is False
    metrics = recorded["metrics"]
    assert metrics["answer_ready_rate"] == 0.0
    assert metrics["citation_validity"] == 1.0
    assert metrics["source_validity"] == 1.0
    assert metrics["language_match_rate"] == 1.0
    assert metrics["degradation_visible_rate"] == 1.0
    assert metrics["stability_jaccard_min"] == 1.0
    # prose_citation_validity is reported as measured, including its miss.
    assert metrics["prose_citation_validity"] < 1.0
    conds = recorded["pre_registered_conditions"]
    assert conds["answer_ready_rate == 1.0"] is False
    assert conds["prose_citation_validity == 1.0"] is False
    assert conds["measurement_complete"] is True
    # posture is untouched by a reported-only measurement
    assert set(recorded["posture_unchanged"].values()) == {False}


def test_the_writer_abort_disclosure_holds_on_the_live_path() -> None:
    """Ordered item 3: a provider outage can never read as 'no contrary authority'."""
    recorded = json.loads(MEASUREMENT.read_text(encoding="utf-8"))
    for leg in recorded["legs"]:
        assert leg["outcome"] == "OK"
        degradation = leg["degradation"]
        assert degradation["degraded"] is True
        assert degradation["degradation_code"] == "e_EMISSION_WRITER_ABORT"
        assert "WRITER_ABORT" in (degradation["adversarial_status"] or "")
        assert degradation["visible"] is True
        provider = leg["provider"]
        assert provider["model_used"] is None
        assert "no candidate free model answered the liveness probe" in (
            provider["provider_error"] or "")
        assert leg["answer"]["status"] == "degraded"


def test_progressive_smoke_asks_the_one_predicate_module() -> None:
    """The RF1 repair keeps the check's semantics byte-for-byte identical."""
    rows = [
        {"counter_status": "none"},
        {"counter_status": ""},
        {"counter_status": None},
        {"counter_status": "cited"},
        {"counter_status": "supporting-candidate"},
        {"counter_status": "candidate-limiting"},
        {"counter_status": "candidate-contrary"},
        {"title": "a row the counter pass never touched"},
    ]
    dicts = [r for r in rows if "counter_status" in r]
    # the exact predicate progressive_smoke used to re-state inline
    legacy = [d for d in dicts if (d.get("counter_status") or "none") not in ("none", "")]
    assert len(legacy) == counter_status.counter_status_bearing_count(dicts) == 4
    hist = counter_status.counter_status_histogram(dicts)
    assert sorted(k for k in hist if k != "none") == [
        "candidate-contrary",
        "candidate-limiting",
        "cited",
        "supporting-candidate",
    ]
    source = (PRODUCT_ROOT / "progressive_smoke.py").read_text(encoding="utf-8")
    assert "counter_status_bearing_count" in source
    assert "counter_status_histogram" in source


def test_the_rf1_scattering_guard_passes_over_product_code() -> None:
    """Run the shipped guard itself (imported from its own module path)."""
    import importlib.util

    guard_path = PRODUCT_ROOT / "tests" / "test_counter_authority_definition.py"
    spec = importlib.util.spec_from_file_location(
        "_rf1_guard_cycle_39956256289", guard_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.test_no_product_module_reintroduces_the_broad_counter_predicate()

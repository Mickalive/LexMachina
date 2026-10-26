"""Cycle 40257275384 snapshot: the interrupted live retrieval is reproducible.

The snapshot's report claimed this test file existed, but the commit that
carried the replay artifacts did not include it.  The test therefore does two
things at once:

* it makes the report's claim true (a committed test path);
* it verifies the one durable artifact the snapshot produced: the replay of the
  interrupted run's committed OpenCaseLaw cache, re-read offline, source-linked,
  defect-free and reproducible from the same bytes.

No network call is made.  The replay driver installs its own non-loopback trap.
"""
import json
import math
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from product.live_cache_replay import DEFAULT_CACHE_COMMIT, run as replay_run  # noqa: E402
from product.query.bundle import validate_bundle  # noqa: E402

RUN_ID = "40257275384"
INTERRUPTED = "40254231396"
SUMMARY = (ROOT / "results" / "product" / "live_cache_replay"
           / f"CYCLE_{RUN_ID}" / "summary.json")
BUNDLE = (ROOT / "results" / "product" / "live_cache_replay"
          / f"CYCLE_{RUN_ID}" / "rent-default-live-cache.bundle.json")
DIAGNOSIS = (ROOT / "results" / "product" / "orchestration"
             / f"CYCLE_{RUN_ID}_resume_diagnosis.json")
REPORT = ROOT / "reports" / "product" / f"CYCLE_{RUN_ID}.md"


def test_report_claims_this_test_path():
    assert REPORT.is_file()
    assert f"product/tests/test_cycle_{RUN_ID}.py" in REPORT.read_text(
        encoding="utf-8")


def test_replay_summary_is_complete_and_defect_free():
    rec = json.loads(SUMMARY.read_text(encoding="utf-8"))
    assert rec["schema"] == "product-live-cache-replay/1"
    assert rec["verdict"] == "PASS"
    assert rec["checks"] and all(rec["checks"].values())
    assert len(rec["checks"]) == 16
    assert rec["n_failed_checks"] == []
    assert rec["bundle"]["n_decisions"] == 150
    assert rec["bundle"]["n_clusters"] >= 2
    assert rec["bundle"]["rows_with_xy"] == 150
    assert rec["bundle"]["rows_with_source_link"] == 150
    assert rec["bundle"]["validate_errors"] == []
    assert rec["answer"]["status"] == "ready"
    assert rec["answer"]["n_cited"] == 2
    span = rec["counter_evidence_span"]
    assert span["applied"] is True
    assert span["n_verified"] == 5
    assert span["n_verified_defective"] == 0
    assert span["downgraded_ids"] == ["bger_4A_78_2013"]
    assert span["abstention_reasons"] == {"off_topic_span": 1}
    net = rec["network"]
    assert net["adapter_network_calls"] == 0
    assert net["adapter_cache_writes"] == 0
    assert net["independent_cache_probe"]["n_files_touched"] == 0


def test_replay_bundle_is_source_linked_and_validates():
    bundle = json.loads(BUNDLE.read_text(encoding="utf-8"))
    assert validate_bundle(bundle) == []
    rows = bundle["decisions"]
    assert len(rows) == 150
    assert len(bundle["clusters"]) >= 2
    for row in rows:
        assert row.get("decision_id")
        assert isinstance(row.get("x"), (int, float))
        assert isinstance(row.get("y"), (int, float))
        assert math.isfinite(row["x"]) and math.isfinite(row["y"])
        assert -1.0 <= row["x"] <= 1.0
        assert -1.0 <= row["y"] <= 1.0
        assert row.get("canonical_url") or row.get("source_url")
    cited = bundle["answer"]["cited_decision_ids"]
    ids = {row["decision_id"] for row in rows}
    assert cited and set(cited).issubset(ids)


def test_replay_reproduces_from_the_same_bytes_in_an_out_of_tree_dir(tmp_path):
    """A supported ``--out-dir /tmp/...`` run must not depend on repo layout.

    This is also the regression test for the path bug that crashed
    ``probe_bundle``/``live_cache_replay`` when the verification output lived
    outside the checkout.
    """
    out = replay_run(
        run_id=f"{RUN_ID}-repro",
        interrupted_run_id=INTERRUPTED,
        cache_commit=DEFAULT_CACHE_COMMIT,
        out_dir=tmp_path / "replay",
    )
    fresh = out["record"]
    committed = json.loads(SUMMARY.read_text(encoding="utf-8"))
    assert fresh["verdict"] == "PASS"
    assert fresh["checks"] == committed["checks"]
    assert fresh["bundle"]["n_decisions"] == committed["bundle"]["n_decisions"]
    assert fresh["bundle"]["n_clusters"] == committed["bundle"]["n_clusters"]
    assert fresh["bundle"]["languages"] == committed["bundle"]["languages"]
    assert fresh["answer"] == committed["answer"]
    assert fresh["counter_evidence_span"]["verified_ids"] == (
        committed["counter_evidence_span"]["verified_ids"])
    assert fresh["counter_evidence_span"]["downgraded_ids"] == (
        committed["counter_evidence_span"]["downgraded_ids"])
    fresh_bundle = out["bundle"]
    committed_bundle = json.loads(BUNDLE.read_text(encoding="utf-8"))
    assert [r["decision_id"] for r in fresh_bundle["decisions"]] == (
        [r["decision_id"] for r in committed_bundle["decisions"]])
    assert [(r["x"], r["y"]) for r in fresh_bundle["decisions"]] == (
        [(r["x"], r["y"]) for r in committed_bundle["decisions"]])
    assert Path(fresh["bundle"]["path"]).is_absolute()


def test_snapshot_diagnosis_is_explicitly_unadjudicated():
    diag = json.loads(DIAGNOSIS.read_text(encoding="utf-8"))
    assert diag["run_id"] == RUN_ID
    assert diag["orchestration"]["classification"] == "RAW_SNAPSHOT_UNAVAILABLE"
    assert diag["orchestration"]["mechanism_unobserved"] is True
    assert diag["durable_delta"]["classification"] == "ZERO_DURABLE_DELTA"
    assert diag["durable_delta"]["changed_files"] == 0
    assert diag["adjudication"]["status"] == "UNADJUDICATED"
    assert diag["adjudication"]["accepted"] is False

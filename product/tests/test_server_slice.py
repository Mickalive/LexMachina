"""The SERVED vertical slice: shipped HTTP handler -> bundle -> shipped page.

What this suite pins is the composition that no other module covered:

* ``product/offline_slice.py`` proved the pipeline with no server;
* ``product/tests/test_progressive_query.py`` proved the job contract over HTTP
  but never rendered what the server returned;
* ``product/verify_query_page.js`` renders a bundle read from disk.

``product/server_slice.py`` drives the shipped ``query_app.Handler`` over a real
socket the way the browser does, then runs the shipped page contract on the
bundle the server actually served. The tests below are offline and deterministic
(fixture retrieval + fixture generation), and the negative controls are real:
a moved point, an invalid bundle and an outbound connect must each FAIL.
"""
from __future__ import annotations

import json
import socket
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PRODUCT = ROOT / "product"
sys.path.insert(0, str(PRODUCT))
sys.path.insert(0, str(ROOT))

import product.server_slice as ss  # noqa: E402


def _claims(result: dict, needle: str) -> list[dict]:
    return [c for c in result["checks"] if needle in c["claim"]]


def test_served_slice_passes_end_to_end_and_publishes_every_check():
    result = ss.execute("Kündigung Mietvertrag Mietrecht", 100)
    assert result["_served_bundle"], "the served bundle must be handed back for artifacting"
    assert result["verdict"] == "PASS", result["failures"]
    assert result["failures"] == []
    assert len(result["checks"]) >= 9
    for row in result["checks"]:
        assert row["status"] == "PASS", row
        assert row["claim"] and row["definition_source"], row

    counts = result["counts"]
    assert counts["n_first_page"] >= 50
    assert counts["n_final"] >= counts["n_first_page"]
    assert counts["n_clusters_final"] >= 2
    assert counts["rows_with_source_url"] == counts["n_final"], (
        "every served row must carry its OpenCaseLaw source link")
    assert counts["n_cited"] >= 1, "the served run must end with a sourced answer"
    assert counts["counter_status_bearing_rows"] >= counts["counter_authorities"]
    assert counts["page_contract_assertions"] >= 50, (
        "the page contract must actually have run assertions, not an empty pass")

    bundle = result["_served_bundle"]
    from query.bundle import validate_bundle
    assert validate_bundle(bundle) == []


def test_the_loopback_trap_is_part_of_the_run_not_a_comment():
    result = ss.execute("Kündigung Mietvertrag Mietrecht", 100)
    row = _claims(result, "non-loopback trap")
    assert row, "the run must publish the trap's own non-vacuity row"
    assert row[0]["status"] == "PASS"
    assert "blocked" in str(row[0]["observed"])


def test_loopback_guard_blocks_outbound_and_allows_local():
    restore = ss.install_loopback_guard()
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        listener.bind(("127.0.0.1", 0))
        listener.listen(1)
        port = listener.getsockname()[1]

        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            client.connect(("127.0.0.1", port))  # local server: allowed
        finally:
            client.close()

        outbound = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            try:
                outbound.connect(("192.0.2.1", 80))
            except AssertionError:
                pass
            else:  # pragma: no cover - the control failing is the point
                raise AssertionError("the guard let an outbound connect through")
        finally:
            outbound.close()
    finally:
        listener.close()
        restore()


def test_a_moved_point_is_a_failure_not_a_pass(monkeypatch):
    """A geometry that drifts under enrichment must be caught by the served run."""
    import query_app

    real = query_app.enrich_query_bundle

    def moving_enrich(bundle, **kwargs):
        final = real(bundle, **kwargs)
        rows = final.get("decisions") or []
        if rows:
            rows[0]["x"] = float(rows[0].get("x", 0.0)) + 0.123
        return final

    monkeypatch.setattr(query_app, "enrich_query_bundle", moving_enrich)
    result = ss.execute("Kündigung Mietvertrag Mietrecht", 100)
    assert result["verdict"] == "FAIL", "a moved point must not pass"
    assert any("preserved the geometry" in f for f in result["failures"]), result["failures"]
    row = _claims(result, "preserved the geometry")[0]
    assert row["status"] == "FAIL"
    assert row["observed"]["geometry_preserved"] is False


def test_an_invalid_bundle_fails_the_real_page_contract():
    """Negative control on the instrument's own last step, with the real script."""
    ok, message, n_rows = ss._page_contract({"decisions": []})
    assert ok is False, "an empty bundle must not pass the shipped page contract"
    assert n_rows >= 0 and message


def test_one_command_writes_the_artifact_and_names_the_artifact(tmp_path, capsys):
    out = tmp_path / "served"
    rc = ss.main(["--out", str(out), "--run-id", "99999999999"])
    assert rc == 0, capsys.readouterr()
    summary = json.loads((out / "summary.json").read_text(encoding="utf-8"))
    assert summary["schema"] == "product-server-slice/1"
    assert summary["verdict"] == "PASS"
    assert summary["artifact_dir"]
    assert summary["claim_ceiling"].startswith("WIRING EVIDENCE")
    served = json.loads((out / "served.bundle.json").read_text(encoding="utf-8"))
    first = json.loads((out / "first_page.bundle.json").read_text(encoding="utf-8"))
    # the geometry claim is recomputable from the two committed bundles
    assert ss._preserved(first, served)[0] is True
    printed = capsys.readouterr().out
    assert "served slice verdict: PASS" in printed


def test_summary_exposes_stage_timings_separately():
    result = ss.execute("Kündigung Mietvertrag Mietrecht", 100)
    timing = result["timing_s"]
    for key in ("start_http_s", "expand_job_s", "enrich_job_s", "total_s"):
        assert key in timing, f"{key} missing from the served-slice timings"
        assert timing[key] >= 0
    assert "upstream OpenCaseLaw" not in json.dumps(result), (
        "a fixture run must not publish an upstream latency number")

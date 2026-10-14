"""Acceptance (2): list <-> map switch over the SAME loaded bundle, offline."""
from __future__ import annotations

import json
import re

from _bootstrap import (FIXTURE_PATH, REPO_ROOT, STATIC_DIR, SWITCH_JS, VERIFY_JS,
                        load_fixture, require_node, run_node)

from frontier_human_gate_harness.bundle_io import bundle_sha256
from frontier_human_gate_harness.demo_page import render_demo_page

NETWORK_TOKENS = ["fetch(", "XMLHttpRequest", "WebSocket", "EventSource", "sendBeacon",
                  "importScripts", "@import", "navigator.send"]


def test_node_switch_assertions_pass():
    require_node()
    proc = run_node([str(VERIFY_JS)])
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "ALL" in proc.stdout and "FAILED" not in proc.stdout
    count = sum(1 for line in proc.stdout.splitlines() if line.startswith("ok "))
    assert count >= 30, f"expected >=30 node assertions, saw {count}"


def test_switch_source_is_offline_and_frozen():
    source = SWITCH_JS.read_text(encoding="utf-8")
    for token in NETWORK_TOKENS:
        assert token not in source, f"network token {token!r} in switch component"
    assert "getBundle" in source, "switch must read the bundle from the host page"
    assert "connect" not in source.replace("connected", "")
    css = (STATIC_DIR / "lex_gate_switch.css").read_text(encoding="utf-8")
    for token in NETWORK_TOKENS:
        assert token not in css, f"network token {token!r} in stylesheet"


def test_switch_never_resorts_or_mutates_the_bundle():
    source = SWITCH_JS.read_text(encoding="utf-8")
    for pattern in (r"\.decisions\s*\.sort", r"decisions\s*\.sort\s*\(",
                    r"\.decisions\s*=", r"decisions\.splice", r"decisions\.reverse"):
        assert not re.search(pattern, source), f"in-place bundle mutation pattern: {pattern}"
    assert "slice()" in source or ".slice(" in source, \
        "the switch should copy before sorting"

    # Python side: the baseline renderer must not mutate its input either
    bundle = load_fixture()
    before = json.dumps(bundle, sort_keys=True, ensure_ascii=False)
    from frontier_human_gate_harness import baseline_view as bv

    bv.build_model(bundle)
    bv.render_rows_html(bundle)
    bv.render_document(bundle)
    after = json.dumps(bundle, sort_keys=True, ensure_ascii=False)
    assert before == after
    provenance = json.loads((FIXTURE_PATH.parent / "FIXTURE_PROVENANCE.json")
                            .read_text(encoding="utf-8"))
    assert bundle_sha256(bundle) == provenance["bundle_canonical_sha256"], \
        "harness bundle hash and fixture provenance disagree"
    import hashlib

    assert provenance["fixture_file_sha256"] == hashlib.sha256(
        FIXTURE_PATH.read_bytes()).hexdigest()
    assert provenance["fixture_sha256"] == provenance["fixture_file_sha256"]


def test_demo_page_is_one_bundle_one_switch_one_card():
    bundle = load_fixture()
    html = render_demo_page(bundle)
    switch_source = SWITCH_JS.read_text(encoding="utf-8")
    assert switch_source in html, "demo must embed the real switch component verbatim"
    assert "window.__LEX_FIXTURE_BUNDLE__" in html
    assert bundle_sha256(bundle) in html
    assert 'id="lexViewToggle"' in html or "lexViewToggle" in html
    assert 'id="lexListView"' in html and 'id="lexMapView"' in html
    assert 'id="lexCardFr"' in html and 'id="lexCardDe"' in html
    assert "missing_answers" in html and "answers" in html
    assert "LexGateSwitch.attach" in html
    for token in NETWORK_TOKENS:
        assert token not in html, f"network token {token!r} in demo page"
    # the demo carries the same decision ids the baseline rows show
    first_id = bundle["decisions"][0]["decision_id"]
    assert first_id in html
    # and it renders the baseline rows through the shared renderer
    from frontier_human_gate_harness import baseline_view as bv

    assert bv.render_rows_html(bundle) in html


def test_bundle_reported_by_fixture_is_the_one_rendered():
    bundle = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    assert bundle["bundle_version"] == "1.0"
    assert bundle["query"], "fixture must record the query it answers"
    assert isinstance(bundle["decisions"], list) and len(bundle["decisions"]) >= 100
    assert REPO_ROOT.is_dir() and VERIFY_JS.is_file()

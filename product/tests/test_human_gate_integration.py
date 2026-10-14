"""Tests for the adopted human-gate list<->map switch (fast MVP slice).

The clickable slice had no conventional ranked-list baseline, so the comparative
human product gate defined by the Master Prompt could not be answered at all.
The accepted team ``frontier-human-gate-harness`` ships that baseline; product
adopted it byte-identically and wired it into ``product/static/query.html``.

These tests pin the four properties the product actually depends on:

1. the adopted files are the accepted artifacts (pinned sha256 from the team's
   INTEGRATION_CONTRACT.json, plus byte-identity when the peer mount is present);
2. the product page implements every documented hook, so the switch renders the
   *same* bundle the map drew rather than a second retrieval;
3. the baseline really is conventional — no cluster/proximity/counter leakage —
   and it covers 100-300 real product decisions in rank order;
4. nothing in the integration claims the human gate itself; ``human_gate_ready``
   stays the owner's.

Everything is offline.  The rendering tests use a real bundle produced by
``run_query_initial(retrieval_mode="fixture")`` and the node runtime when one is
available (skipped otherwise).
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "product"))
sys.path.insert(0, str(ROOT / "product" / "query"))

import human_gate  # noqa: E402  (product/query/human_gate.py)

QUERY_HTML = ROOT / "product" / "static" / "query.html"
SWITCH_JS = ROOT / "product" / "static" / "lex_gate_switch.js"

NODE = shutil.which("node")


# --------------------------------------------------------------------------- #
# 1. adopted assets
# --------------------------------------------------------------------------- #
def test_adopted_assets_match_the_accepted_contract_digests():
    report = human_gate.verify_assets()
    assert report["ok"], report
    for name, spec in human_gate.ACCEPTED_ASSETS.items():
        asset = report["assets"][name]
        assert asset["present"], f"{name} is not installed"
        assert asset["sha256"] == spec["sha256"], (
            f"{name} was modified after acceptance; product must adopt the accepted bytes, "
            f"not a local edit"
        )


def test_installed_assets_are_byte_identical_to_the_accepted_mount():
    source_dir = human_gate.accepted_source_dir()
    if source_dir is None:
        pytest.skip("accepted peer mount not present in this cycle")
    for name in human_gate.ACCEPTED_ASSETS:
        upstream = source_dir / name
        if not upstream.is_file():
            pytest.skip(f"{name} not in the accepted mount")
        assert human_gate.sha256_of(upstream) == human_gate.sha256_of(human_gate.installed_path(name))


def test_query_html_implements_every_contract_hook():
    report = human_gate.verify_html_hooks()
    assert report["ok"], f"missing hooks: {report['missing']}"
    assert report["missing"] == []


def test_list_view_sits_beside_the_map_inside_main():
    html = QUERY_HTML.read_text(encoding="utf-8")
    main = html[html.index("<main>"): html.index("</main>")]
    assert '<div id="lexListView" hidden></div>' in main
    assert main.index('id="mapWrap"') < main.index('id="lexListView"')
    # the list must start hidden so the first paint is still the product map
    assert 'id="lexListView" hidden' in main


def test_bundle_hook_returns_the_loaded_object_not_a_url():
    html = QUERY_HTML.read_text(encoding="utf-8")
    assert "getBundle:function(){return BUNDLE}" in html
    assert "/api/query" not in html.split("LexGateSwitch.attach({")[1][:400]


def test_product_status_and_list_are_restored_after_the_switch_rewrites_them():
    """The harness owns #status during a toggle; product re-applies its wording.

    Two things must be repaired by a listener registered AFTER attach(), because
    it runs after the harness listener: the list pane (attach() ran before the
    first query, so it starts empty) and the product status text (phase pill,
    result count, latency).  Registering the listener earlier would silently lose
    both for the rest of the session — which is exactly what the DOM smoke below
    caught during integration.
    """
    html = QUERY_HTML.read_text(encoding="utf-8")
    attach = html.index("LexGateSwitch.attach({")
    listener = html.index('addEventListener("click",function(){')
    assert attach < listener
    assert "LexGateSwitch.notifyBundleChanged();" in html[listener: listener + 400]
    assert "restoreStatus();" in html[listener: listener + 400]
    assert "function restoreStatus()" in html


def test_switch_contains_no_network_capability():
    """A view change must never re-retrieve, or a gate session mixes two result sets."""
    js = SWITCH_JS.read_text(encoding="utf-8")
    for banned in ("fetch(", "XMLHttpRequest", "WebSocket", "sendBeacon", "EventSource",
                   "import(", "navigator.send"):
        assert banned not in js, f"the accepted switch must not contain {banned}"


def test_integration_report_never_claims_the_human_gate():
    """Mentioning the owner's gate in a disclaimer is fine; asserting it is not."""
    report = human_gate.integration_report()

    def walk(node):
        if isinstance(node, dict):
            for key, value in node.items():
                yield key
                yield from walk(value)
        elif isinstance(node, list):
            for item in node:
                yield from walk(item)
        elif isinstance(node, str):
            yield node

    tokens = list(walk(report))
    assert "human_gate_ready" not in tokens
    assert not any('"human_gate_ready": true' in t for t in tokens)
    assert not any("human gate passed" in t.lower() for t in tokens)
    assert "human_gate_ready" not in SWITCH_JS.read_text(encoding="utf-8")


# --------------------------------------------------------------------------- #
# 2. the baseline renders the product's real bundle
# --------------------------------------------------------------------------- #
def _fixture_bundle(tmp_path: Path) -> Path:
    from query import run_query_initial

    bundle = run_query_initial(
        "Kündigung Mietvertrag Mietrecht", top_n=100, retrieval_mode="fixture"
    )
    path = tmp_path / "bundle.json"
    path.write_text(json.dumps(bundle, ensure_ascii=False), encoding="utf-8")
    return path


@pytest.mark.skipif(NODE is None, reason="node runtime unavailable")
def test_baseline_renders_every_decision_in_rank_order(tmp_path):
    bundle_path = _fixture_bundle(tmp_path)
    script = tmp_path / "render.js"
    script.write_text(
        "const fs=require('fs');"
        "const S=require(process.argv[2]);"
        "const b=JSON.parse(fs.readFileSync(process.argv[3],'utf8'));"
        "const model=S.buildListModel(b);"
        "const html=S.renderRowsHtml(b);"
        "process.stdout.write(JSON.stringify({"
        "  rows:model.length,"
        "  decisions:b.decisions.length,"
        "  ranks:model.map(r=>r.rank),"
        "  ids:model.map(r=>r.decision_id),"
        "  html,"
        "}));",
        encoding="utf-8",
    )
    out = subprocess.run(
        [NODE, str(script), str(SWITCH_JS), str(bundle_path)],
        capture_output=True, text=True, check=True,
    )
    result = json.loads(out.stdout)
    assert result["rows"] == result["decisions"] >= 100
    assert result["ranks"] == sorted(result["ranks"])
    assert result["ids"] == [d["decision_id"] for d in json.loads(bundle_path.read_text())["decisions"]]
    assert result["html"].count('class="lex-row"') == result["decisions"]


@pytest.mark.skipif(NODE is None, reason="node runtime unavailable")
def test_baseline_carries_no_map_information(tmp_path):
    """The comparison is only honest if the baseline is genuinely conventional."""
    bundle_path = _fixture_bundle(tmp_path)
    script = tmp_path / "render.js"
    script.write_text(
        "const fs=require('fs');"
        "const S=require(process.argv[2]);"
        "const b=JSON.parse(fs.readFileSync(process.argv[3],'utf8'));"
        "process.stdout.write(S.renderRowsHtml(b));",
        encoding="utf-8",
    )
    html = subprocess.run(
        [NODE, str(script), str(SWITCH_JS), str(bundle_path)],
        capture_output=True, text=True, check=True,
    ).stdout
    for banned in ("cluster", "counter_status", "outlier", "is_outlier", "proximity", "x=", "y="):
        assert banned not in html, f"baseline leaked map information: {banned}"
    # every row still links to the public source
    assert 'class="lex-source"' in html


@pytest.mark.skipif(NODE is None, reason="node runtime unavailable")
def test_real_page_boots_renders_and_switches_without_network(tmp_path):
    """Execute product/static/query.html itself, not a reconstruction of it."""
    bundle_path = _fixture_bundle(tmp_path)
    script = ROOT / "product" / "verify_query_page.js"
    proc = subprocess.run(
        [NODE, str(script), str(bundle_path)],
        capture_output=True, text=True, cwd=str(ROOT),
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "PASS" in proc.stdout
    assert "FAIL" not in proc.stdout
    assert f"one row per decision (100/100)" in proc.stdout


@pytest.mark.skipif(NODE is None, reason="node runtime unavailable")
def test_switching_views_never_calls_the_network_or_mutates_the_bundle(tmp_path):
    bundle_path = _fixture_bundle(tmp_path)
    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    before = json.dumps(bundle, sort_keys=True, ensure_ascii=False)
    script = tmp_path / "switch.js"
    script.write_text(
        "const fs=require('fs');"
        "const S=require(process.argv[2]);"
        "const b=JSON.parse(fs.readFileSync(process.argv[3],'utf8'));"
        "const bundle=JSON.parse(fs.readFileSync(process.argv[3],'utf8'));"
        "let gets=0;"
        "const c=S.createController({getBundle:function(){gets++;return bundle}});"
        "c.switchTo('list');"
        "c.toggle();"
        "c.openDecision(bundle.decisions[0].decision_id);"
        "const counter=bundle.decisions.find(d=>d.counter_status&&"
        "!['none','cited','supporting-candidate','context','unclassified'].includes(d.counter_status));"
        "process.stdout.write(JSON.stringify({"
        "  gets:gets, view:c.viewMode, rows:(c.lastListHtml.match(/class=\"lex-row\"/g)||[]).length,"
        "  counter:c.openCounter(counter?counter.decision_id:'missing'),"
        "  actions:c.actions.map(a=>a.event)}));",
        encoding="utf-8",
    )
    out = subprocess.run(
        [NODE, str(script), str(SWITCH_JS), str(bundle_path)],
        capture_output=True, text=True, check=True,
    )
    result = json.loads(out.stdout)
    assert result["rows"] == len(bundle["decisions"])
    assert result["actions"] == ["switch", "switch", "open_decision"]
    assert json.dumps(bundle, sort_keys=True, ensure_ascii=False) == before
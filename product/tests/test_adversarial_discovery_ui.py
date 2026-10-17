"""Adversarial-pass DISCOVERY is visible on the map, and labelled as provenance.

Why this module exists
----------------------
The canonical product loop ends with an *independent* search for authority that
contradicts, limits, distinguishes or excepts the provisional answer, and the
Master Prompt requires that "counter-authorities are visually discoverable".
Cycle 39063665073 found the live slice violating exactly that: the frozen
counter-anchor reviewer legitimately **abstains** when no verbatim sentence
supports a line (adopt contract: support-among-emitted 1.0, 60 abstentions,
yield 0.0769), so on the real live run
``results/product/progressive_slice/bundle_39060279436_LIVE_V2.json`` the
independent pass admitted **8** new authorities through its
contrary / exception / minority / older-line probes while the page reported
``Aucune contre-autorité qualifiée à ce stade`` and drew all 202 rows with no
trace of the discovery. The half of the product that finds the authorities a
ranked list hides was, in the browser, invisible.

The fix is additive and honest: the ``adversarial.*`` **retrieval channel** a
row was found through is rendered as a discovery marker (cyan ring, sidebar
card, map filter, detail panel) — and every surface states that this is
provenance of retrieval, not a legal qualification.

What is asserted here
---------------------
* render level, via ``product/canvas_probe.js`` (the real ``draw()``):
  the accepted v55 contour contract is UNCHANGED (pts / fills / red / amber /
  gold / no stray dash), and the discovery ring is painted exactly once per
  adversarially discovered row — 40 / 40 / 40 on the served packet,
  8 on the live V2 bundle;
* behaviour level, via ``product/verify_query_page.js`` (the page's own DOM
  contract): every discovered authority is named in the sidebar with its probe
  channel, one click opens it, the map filter isolates exactly the discovered
  rows, and an unqualified discovery never renders as a counter qualification;
* non-vacuity: a mutant page without the discovery ring measures 0, and a
  mutant without the sidebar panel fails the page contract — so this module
  fails on the pre-39063665073 page and passes on the shipped one, in one run.

These are render-contract and DOM-contract checks against committed bundles.
They are NOT a discoverability, map-quality or legal-usefulness claim; whether
the map actually helps a jurist find minority authority is the human gate.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

NODE = shutil.which("node")
PROBE = REPO_ROOT / "product" / "canvas_probe.js"
VERIFY = REPO_ROOT / "product" / "verify_query_page.js"
PAGE = REPO_ROOT / "product" / "static" / "query.html"
SERVE_PACKET = REPO_ROOT / "results" / "product" / "gate_packet" / "38839347028"
LIVE_BUNDLE = (REPO_ROOT / "results" / "product" / "progressive_slice"
               / "bundle_39060279436_LIVE_V2.json")

QUESTIONS = ["de-kapitalverletzung", "fr-bail-entretien", "it-responsabilita-medica"]

#: The accepted v55 contour contract (unchanged by this cycle) — see
#: product/tests/test_canvas_ring_strokes.py, which owns those numbers.
ACCEPTED_CONTRACT = {
    "de-kapitalverletzung": {"pts": 214, "red": 24, "amber": 1, "gold": 1},
    "fr-bail-entretien": {"pts": 217, "red": 11, "amber": 4, "gold": 6},
    "it-responsabilita-medica": {"pts": 211, "red": 14, "amber": 11, "gold": 4},
}

DISCOVERY_STROKE = 'if(isAdversarial(p)){ctx.lineWidth=1.6;'
REJECTED_STROKE = 'if(false&&isAdversarial(p)){ctx.lineWidth=1.6;'
RENDER_DISCOVERY = "renderCounters();renderAdversarial();renderClusters();"
REJECTED_RENDER = "renderCounters();renderClusters();"


def _run(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, cwd=str(REPO_ROOT))


def _probe(bundle_path: Path, html_path: Path | None = None) -> dict:
    cmd = [NODE, str(PROBE), str(bundle_path)]
    if html_path is not None:
        cmd.append(str(html_path))
    proc = _run(cmd)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    return json.loads(proc.stdout)


def _discovered_rows(bundle_path: Path) -> list[str]:
    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    return sorted(d["decision_id"] for d in bundle["decisions"]
                  if any(isinstance(c, str) and c.startswith("adversarial.")
                         for c in (d.get("channels") or [])))


needs_node = pytest.mark.skipif(NODE is None, reason="node runtime unavailable")


# --------------------------------------------------------------------------
# render level
# --------------------------------------------------------------------------
@needs_node
@pytest.mark.skipif(not SERVE_PACKET.is_dir(),
                    reason="served gate packet 38839347028 not present")
@pytest.mark.parametrize("question", QUESTIONS)
def test_discovery_ring_does_not_disturb_the_accepted_contour_contract(question):
    """Adding the discovery ring must not move a single accepted number."""
    report = _probe(SERVE_PACKET / "questions" / f"{question}.bundle.json")
    want = ACCEPTED_CONTRACT[question]
    assert report["pts"] == want["pts"], report
    assert report["fills"] == want["pts"], report          # still one paint per row
    assert report["red"] == want["red"], report
    assert report["amber"] == want["amber"], report
    assert report["gold"] == want["gold"], report
    assert report["dashed_other"] == 0, report             # still no stray dash
    # one discovery ring per adversarially discovered row, counted from the data
    n = len(_discovered_rows(SERVE_PACKET / "questions" / f"{question}.bundle.json"))
    assert report["discovery"] == n, (
        f"{question}: {report['discovery']} discovery rings for {n} discovered rows")


@needs_node
@pytest.mark.skipif(not LIVE_BUNDLE.is_file(), reason="live V2 bundle not present")
def test_live_run_paints_the_authorities_its_adversarial_pass_found():
    """The real live slice: 8 admitted discoveries must be visible, 202 points."""
    report = _probe(LIVE_BUNDLE)
    assert report["pts"] == 202, report
    assert report["discovery"] == 8, (
        f"the live run's 8 adversarially admitted authorities must render a "
        f"discovery ring; measured {report['discovery']}")


@needs_node
@pytest.mark.skipif(not LIVE_BUNDLE.is_file(), reason="live V2 bundle not present")
def test_probe_discriminates_the_page_without_the_discovery_ring(tmp_path):
    """Non-vacuity: the pre-fix page paints 0 discovery rings in the same run."""
    html = PAGE.read_text(encoding="utf-8")
    assert html.count(DISCOVERY_STROKE) == 1, (
        "the discovery ring branch is no longer the shipped one")
    mutant = tmp_path / "no_discovery_query.html"
    mutant.write_text(html.replace(DISCOVERY_STROKE, REJECTED_STROKE, 1),
                      encoding="utf-8")
    assert _probe(LIVE_BUNDLE)["discovery"] == 8
    assert _probe(LIVE_BUNDLE, mutant)["discovery"] == 0


# --------------------------------------------------------------------------
# behaviour level
# --------------------------------------------------------------------------
@needs_node
@pytest.mark.skipif(not LIVE_BUNDLE.is_file(), reason="live V2 bundle not present")
def test_page_contract_on_the_live_bundle_lists_and_labels_every_discovery():
    proc = _run([NODE, str(VERIFY), str(LIVE_BUNDLE)])
    out = proc.stdout + proc.stderr
    assert proc.returncode == 0, out
    # 47 assertions before this cycle's discovery section; the section adds 17
    # more on a bundle that actually carries discoveries.
    assert "PASS" in out and "FAIL" not in out, out
    for label in (
        "every authority the adversarial pass found is named in the sidebar",
        "each discovered authority names the probe channel that found it",
        "the discovery panel states that the marker is provenance, not a legal qualification",
        "opening a discovered authority shows its decision",
        "a discovery is never rendered as a counter qualification",
        "the 'passe contradictoire' filter isolates exactly the discovered rows",
        "discovery never manufactures a counter claim",
        "an unqualified discovery is NOT listed as a counter-authority",
    ):
        assert f"ok - {label}" in out, out


@needs_node
@pytest.mark.skipif(not LIVE_BUNDLE.is_file(), reason="live V2 bundle not present")
def test_page_contract_fails_when_the_discovery_panel_is_removed(tmp_path):
    """Non-vacuity: the SAME behavioural contract fails on the pre-fix page.

    ``verify_query_page.js`` takes an optional page override, so the mutant is
    exercised through the real DOM harness rather than through a reconstruction:
    on the shipped page the run passes, on a page whose ``renderBundle`` no
    longer calls ``renderAdversarial()`` the discovery assertion fails and the
    script exits non-zero.
    """
    html = PAGE.read_text(encoding="utf-8")
    assert html.count(RENDER_DISCOVERY) == 1, (
        "renderBundle no longer calls renderAdversarial()")
    mutant = tmp_path / "no_panel_query.html"
    mutant.write_text(html.replace(RENDER_DISCOVERY, REJECTED_RENDER, 1),
                      encoding="utf-8")
    assert mutant.read_text(encoding="utf-8") != html

    shipped = _run([NODE, str(VERIFY), str(LIVE_BUNDLE)])
    assert shipped.returncode == 0, shipped.stdout + shipped.stderr
    assert "every authority the adversarial pass found is named in the sidebar" in shipped.stdout

    broken = _run([NODE, str(VERIFY), str(LIVE_BUNDLE), "", str(mutant)])
    assert broken.returncode != 0, (
        "a page whose renderBundle drops renderAdversarial() still passed the "
        "discovery contract: " + broken.stdout)
    assert "FAIL - every authority the adversarial pass found is named in the sidebar" \
        in broken.stdout, broken.stdout


# --------------------------------------------------------------------------
# honesty: an offline slice has nothing to disclose and says so
# --------------------------------------------------------------------------
@needs_node
def test_offline_slice_bundle_states_that_no_discovery_was_made(tmp_path):
    """No network, no adversarial pass: the panel must not invent discoveries."""
    bundle = tmp_path / "no-discovery.bundle.json"
    bundle.write_text(json.dumps({
        "query": "offline", "query_variants": [],
        "answer": {"status": "ready", "prose": "", "cited_decision_ids": []},
        "decisions": [{"decision_id": "row-1", "court": "BGE", "language": "fr",
                       "rank": 1, "score": 1.0, "provenance": {}, "snippet": "s",
                       "cluster_id": 0, "x": 0, "y": 0, "counter_status": "none",
                       "channels": ["search"], "canonical_url": "https://e/1",
                       "citation": ""}],
        "clusters": [{"cluster_id": 0, "size": 1, "label": "s"}],
        "relations": [], "provenance": {},
    }), encoding="utf-8")
    proc = _run([NODE, str(VERIFY), str(bundle)])
    out = proc.stdout + proc.stderr
    assert proc.returncode == 0, out
    assert "ok - a bundle with no adversarial finding says so instead of inventing one" in out, out
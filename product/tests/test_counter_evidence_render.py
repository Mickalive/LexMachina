"""v55 render-truth: the served packet's unevidenced counter rows must render
as an explicitly marked unevidenced state, never as a confident counter.

The factory direction's top product item (v55, director run 38874399407) measured
16 of 65 counter-authority labels on the packet the owner will be served
(results/product/gate_packet/38839347028) carrying an EMPTY counter_evidence at
uncertainty 0.95-1.0 with counter_evidence_verified ABSENT — while the map's
render predicate gated on counter_status alone and drew a confident red ring.

These tests execute the REAL page (product/static/query.html, via the shared
dom_shim runtime) against the REAL served bundles and require:
  - the page boots and renders every bundle without a network call;
  - the owner card states the unevidenced count of the served bundle;
  - unevidenced rows are explicitly marked as retained for visibility.

The synthetic predicate/ring/pill behaviour is asserted inside
product/verify_query_page.js itself (section 8); this module owns the
served-data integration check.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

NODE = shutil.which("node")
SERVE_PACKET = REPO_ROOT / "results" / "product" / "gate_packet" / "38839347028"
QUESTIONS = ["de-kapitalverletzung", "fr-bail-entretien", "it-responsabilita-medica"]

# The director's measurement on the served packet: 16 of 65 counter labels are
# unevidenced (de 1, fr 4, it 11).  The count is recomputed from the data in
# the test itself; this table is the cross-check that the fixtures on disk are
# still the measured ones.
EXPECTED_UNEVIDENCED = {"de-kapitalverletzung": 1, "fr-bail-entretien": 4,
                        "it-responsabilita-medica": 11}


def _is_counter(d: dict) -> bool:
    status = d.get("counter_status")
    return bool(status) and status not in (
        "none", "cited", "supporting-candidate", "context", "unclassified")


def _unevidenced(bundle: dict) -> list[dict]:
    return [d for d in bundle.get("decisions", [])
            if _is_counter(d) and not (d.get("counter_evidence") or "").strip()]


@pytest.mark.skipif(NODE is None, reason="node runtime unavailable")
@pytest.mark.skipif(not SERVE_PACKET.is_dir(),
                    reason="served gate packet 38839347028 not present")
@pytest.mark.parametrize("question", QUESTIONS)
def test_served_bundle_renders_unevidenced_counters_honestly(tmp_path, question):
    bundle_path = SERVE_PACKET / "questions" / f"{question}.bundle.json"
    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    unevidenced = _unevidenced(bundle)
    assert len(unevidenced) == EXPECTED_UNEVIDENCED[question], (
        f"the served {question} bundle no longer carries the measured "
        f"{EXPECTED_UNEVIDENCED[question]} unevidenced counter rows")

    # Run the real page against the real served bundle, offline.
    local = tmp_path / "bundle.json"
    local.write_text(json.dumps(bundle, ensure_ascii=False), encoding="utf-8")
    proc = subprocess.run(
        [NODE, str(REPO_ROOT / "product" / "verify_query_page.js"), str(local)],
        capture_output=True, text=True, cwd=str(REPO_ROOT),
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "FAIL" not in proc.stdout
    # The owner card states the unevidenced count of THIS served bundle.
    assert f"owner card states the unevidenced count of the served bundle (" \
           f"{len(unevidenced)} non étayées)" in proc.stdout
    assert "served bundle's unevidenced rows are explicitly marked" in proc.stdout
    # And the synthetic predicate checks ran in the same pass.
    assert "an unevidenced row is never an evidenced counter" in proc.stdout
    assert "unevidenced detail panel never carries the confident red pill" in proc.stdout


@pytest.mark.skipif(not SERVE_PACKET.is_dir(),
                    reason="served gate packet 38839347028 not present")
def test_served_packet_never_claims_label_soundness():
    """The packet has never been falsified under the frozen rubrics; nothing in
    the served artifacts may claim label soundness or geometry coherence."""
    disclosures_path = SERVE_PACKET / "disclosures.json"
    disclosures = json.loads(disclosures_path.read_text(encoding="utf-8"))
    adoption = disclosures.get("frontier_verdict_adoption", {})
    # covers_this_packet lives nested per-verdict (v54 adoption shape), not at
    # the adoption top level: neither frozen verdict was measured on this
    # packet's rows.
    cli = adoption.get("frontier_counter_label_integrity", {})
    assert cli.get("covers_this_packet") is False
    assert cli.get("every_scored_bundle_is_pre_repair") is True
    # counter_label_re_measured=false is recorded product-side in the sweep
    # state (state/product.json frontier_verdict_sweep), not in the packet
    # disclosures; the packet must also carry no soundness claim.
    ceiling = (adoption.get("claim_ceiling", "")
               + " " + disclosures.get("claim_ceiling", ""))
    assert "not on this packet" in ceiling or "PRE-FIX" in ceiling
    assert "LABEL_SOUND" not in ceiling or "must not be read as LABEL_SOUND" in ceiling \
        or "INSUFFICIENT_POPULATION" in ceiling

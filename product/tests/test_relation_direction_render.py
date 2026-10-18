"""Relation-direction render contract: a shared_citation edge states the
co-citation in French and never exposes the raw machine token.

Found 2026-10-18 while generalizing the offline slice beyond the rent-default
fixture. The petty-theft-dismissal and corporate-criminal-liability bundles
carry ONLY ``shared_citation`` edges (typed ``citation`` edges exist only where
the recorded OpenCaseLaw envelopes carry ``/citations`` provenance), and the
detail panel rendered those edges as ``↔ X · shared_citation`` - an English
machine token in a French jurist-facing panel, with no citation semantics at
all. Both bundles failed the product's own DOM contract assertion "detail
panel states the citation direction" (offline slice directories
20261018T095123Z / 20261018T095432Z; rent-default and business-judgment-rule
were unaffected - the first has zero relations, the second has typed edges).

A shared_citation edge is symmetric by nature: BOTH endpoints cite the named
authority. The renderer now states that honestly (``cite en commun « X »``).
The synthetic line-level checks live in ``product/verify_query_page.js``
(section 5); this module owns the REAL-bundle integration check: the real
offline pipeline output for a query whose edges are shared_citation must pass
the real page's contract, and the fixture must non-vacuously carry the edge
kind under test.
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

#: The reality-leg query whose recorded envelopes produce shared_citation-only
#: relations (typed citation edges are absent - no /citations provenance in the
#: fixture). business-judgment-rule is the contrast leg: it carries typed
#: edges and passed before the fix.
SHARED_CITATION_SLUG = "petty-theft-dismissal"
TYPED_CITATION_SLUG = "business-judgment-rule"


def _build_bundle(slug: str) -> dict:
    """Real offline pipeline output for ``slug`` (network booby-trapped)."""
    sys.path.insert(0, str(REPO_ROOT / "product"))
    from offline_slice import build_bundle

    return build_bundle(slug, 100, enrich=True)


def _page_contract(bundle: dict, tmp_path: Path) -> subprocess.CompletedProcess:
    """Run the REAL page (query.html via dom_shim) against the REAL bundle."""
    local = tmp_path / "bundle.json"
    local.write_text(json.dumps(bundle, ensure_ascii=False), encoding="utf-8")
    return subprocess.run(
        [NODE, str(REPO_ROOT / "product" / "verify_query_page.js"), str(local)],
        capture_output=True, text=True, cwd=str(REPO_ROOT), timeout=300,
    )


@pytest.mark.skipif(NODE is None, reason="node runtime unavailable")
def test_shared_citation_slice_carries_the_edge_kind_under_test():
    """Non-vacuity: the fixture must really produce shared_citation edges.

    If the retrieval fixture ever changes so this query no longer yields
    shared_citation relations, the page-contract test below would pass
    vacuously; this test fails instead, forcing the fixture (not the contract)
    to be re-examined.
    """
    bundle = _build_bundle(SHARED_CITATION_SLUG)
    relations = bundle.get("relations") or []
    assert relations, f"{SHARED_CITATION_SLUG} produced no relations at all"
    assert any(r.get("kind") == "shared_citation" for r in relations), (
        f"{SHARED_CITATION_SLUG} no longer carries a shared_citation edge; "
        f"kinds={sorted({r.get('kind') for r in relations})}")
    # And the shared edge names the authority both endpoints cite - the whole
    # point of the French rendering is that name.
    edge = next(r for r in relations if r.get("kind") == "shared_citation")
    assert edge.get("shared"), "a shared_citation edge must name the shared authority"


@pytest.mark.skipif(NODE is None, reason="node runtime unavailable")
def test_shared_citation_slice_passes_the_page_contract(tmp_path):
    """The real page renders the real shared_citation bundle with no failure.

    This is the regression pin for the 20261018T095123Z failure: the page
    contract's "detail panel states the citation direction" assertion failed on
    exactly this bundle before the renderer fix.
    """
    bundle = _build_bundle(SHARED_CITATION_SLUG)
    proc = _page_contract(bundle, tmp_path)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    out = proc.stdout
    assert "FAIL" not in out, out
    # The contract's direction assertions ran and passed on this real bundle.
    assert "detail panel states the citation direction" in out
    assert "ok - detail panel states the citation direction" in out
    # The synthetic shared_citation line checks (added with the fix) also ran.
    assert "ok - a shared_citation edge states the co-citation in French and names the shared authority" in out
    assert "ok - the raw relation-kind token never reaches the jurist-facing panel" in out


@pytest.mark.skipif(NODE is None, reason="node runtime unavailable")
def test_typed_citation_slice_still_passes_the_page_contract(tmp_path):
    """Contrast leg: typed citation edges keep their directional rendering.

    business-judgment-rule carries typed ``citation`` edges (from OpenCaseLaw
    /citations provenance); it passed before the fix and must keep passing -
    the shared_citation branch must not have disturbed the directional one.
    """
    bundle = _build_bundle(TYPED_CITATION_SLUG)
    relations = bundle.get("relations") or []
    assert any(r.get("kind") == "citation" for r in relations), (
        f"{TYPED_CITATION_SLUG} no longer carries a typed citation edge")
    proc = _page_contract(bundle, tmp_path)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "FAIL" not in proc.stdout, proc.stdout
    assert "ok - detail panel states the citation direction" in proc.stdout

"""Renderer precondition regression test: negative cluster_id = unclustered context.

Why this module exists
----------------------
The accepted Frontier component ``frontier-query-conditioned-map-geometry``
(team run 38978981369, audit ``CYCLE_38973386164_GATE.json`` PASS, accept commit
``be5eba7f``) marks un-hydrated unclustered context rows with a unique NEGATIVE
``cluster_id``.  Its ``RENDERER_PRECONDITION.json`` records that the live query
map indexed the palette with ``(cluster_id % COLORS.length)``; JavaScript ``%``
truncates toward zero, so a negative id indexes BEFORE the array, ``COLORS[-1]``
is ``undefined``, and assigning ``undefined`` to ``ctx.fillStyle`` is an invalid
value the canvas silently ignores — every unclustered shell was painted in the
colour of whichever point was drawn immediately before it.

That finding was raised as a BLOCKING_PRECONDITION_FOR_DROP_IN_ADOPTION and its
owner is Core Product (``product/static/query.html``).  This test proves the
product satisfies the precondition:

  * a point with a negative ``cluster_id`` is painted the declared neutral
    UNCLUSTERED_COLOR, never an undefined fillStyle;
  * every non-negative ``cluster_id`` keeps the palette modulo lookup, so the
    change is inert for the incumbent geometry;
  * a discrimination control runs the SAME probe against the pre-fix expression
    and requires at least one undefined fill, so the assertion cannot pass on a
    probe that simply never measures fills.

These are render-contract assertions, never a map-quality claim.
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
PAGE = REPO_ROOT / "product" / "static" / "query.html"
SERVE_PACKET = REPO_ROOT / "results" / "product" / "gate_packet" / "38839347028"
QUESTION = "de-kapitalverletzung"

UNCLUSTERED_COLOR = "#9aa3ad"
# The exact pre-fix expression, as recorded in RENDERER_PRECONDITION.json.
FIXED_FILL = "ctx.fillStyle=colorFor(p.cluster_id);"
PREFIXED_FILL = "ctx.fillStyle=COLORS[(p.cluster_id??0)%COLORS.length];"


def _probe(bundle_path: Path, html_path: Path | None = None) -> dict:
    cmd = [NODE, str(PROBE), str(bundle_path)]
    if html_path is not None:
        cmd.append(str(html_path))
    proc = subprocess.run(cmd, capture_output=True, text=True, cwd=str(REPO_ROOT))
    assert proc.returncode == 0, proc.stdout + proc.stderr
    return json.loads(proc.stdout)


def _unclustered_bundle(tmp_path: Path, n_negative: int = 3) -> Path:
    src = SERVE_PACKET / "questions" / f"{QUESTION}.bundle.json"
    bundle = json.loads(src.read_text(encoding="utf-8"))
    for i, d in enumerate(bundle["decisions"][:n_negative]):
        d["cluster_id"] = -(i + 1)
        d["unclustered"] = True
    out = tmp_path / f"{QUESTION}_unclustered.bundle.json"
    out.write_text(json.dumps(bundle), encoding="utf-8")
    return out


@pytest.mark.skipif(NODE is None, reason="node runtime unavailable")
@pytest.mark.skipif(not PROBE.is_file(), reason="product/canvas_probe.js missing")
@pytest.mark.skipif(not SERVE_PACKET.is_dir(),
                    reason="served gate packet 38839347028 not present")
def test_negative_cluster_ids_get_the_neutral_colour_not_undefined(tmp_path):
    assert PAGE.read_text(encoding="utf-8").count(FIXED_FILL) == 1, (
        "the point fill is no longer the negative-safe colorFor(cluster_id) lookup")
    bundle = _unclustered_bundle(tmp_path, n_negative=3)
    report = _probe(bundle)
    assert report["pts"] == report["fills"], report
    assert report["fill_undefined"] == 0, (
        "a negative cluster_id produced an undefined fillStyle; the canvas would "
        f"silently reuse the previous point's colour: {report}")
    assert report["fill_colors"].get(UNCLUSTERED_COLOR) == 3, (
        "the three unclustered-context rows must paint the declared neutral colour; "
        f"got {report['fill_colors']}")


@pytest.mark.skipif(NODE is None, reason="node runtime unavailable")
@pytest.mark.skipif(not PROBE.is_file(), reason="product/canvas_probe.js missing")
@pytest.mark.skipif(not SERVE_PACKET.is_dir(),
                    reason="served gate packet 38839347028 not present")
def test_incumbent_geometry_is_byte_identical_under_the_fix():
    """No negative ids in the incumbent packet -> the fix changes nothing for it."""
    report = _probe(SERVE_PACKET / "questions" / f"{QUESTION}.bundle.json")
    assert report["fill_undefined"] == 0, report
    assert UNCLUSTERED_COLOR not in report["fill_colors"], report
    assert report["fills"] == report["pts"] == 214, report


@pytest.mark.skipif(NODE is None, reason="node runtime unavailable")
@pytest.mark.skipif(not PROBE.is_file(), reason="product/canvas_probe.js missing")
@pytest.mark.skipif(not SERVE_PACKET.is_dir(),
                    reason="served gate packet 38839347028 not present")
def test_probe_discriminates_the_prefix_head(tmp_path):
    """Negative control: the pre-fix expression must produce undefined fills."""
    html = PAGE.read_text(encoding="utf-8")
    assert html.count(FIXED_FILL) == 1, html.count(FIXED_FILL)
    mutant = tmp_path / "prefix_query.html"
    mutant.write_text(html.replace(FIXED_FILL, PREFIXED_FILL, 1), encoding="utf-8")
    assert mutant.read_text(encoding="utf-8") != html

    bundle = _unclustered_bundle(tmp_path, n_negative=3)
    fixed = _probe(bundle)
    broken = _probe(bundle, mutant)
    assert fixed["fill_undefined"] == 0, fixed
    assert broken["fill_undefined"] == 3, broken
    assert broken["fill_colors"].get(UNCLUSTERED_COLOR) in (None, 0), broken

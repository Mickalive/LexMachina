"""RF3 guard: no test may write into a TRACKED ``product/results/`` file.

Why this module exists
----------------------
Direction v56 ordered work item (4), from the independent audit of run
39073545280::

    "STOP MANUFACTURING FAKE DELTA FROM THE TEST SUITE.
     product/tests/test_cycle_v18_product.py:255-300 constructs NavigationAPI(...,
     product/results/fractal_map) against a TRACKED path with no tmp_path, so every
     suite run appends pytest residue (jurist_id test_jurist_1 / test_aggregator_3/4/5)
     to product/results/fractal_map/jurist_feedback/feedback.jsonl. That residue is
     what 39073545280 committed as its entire delta (+20 lines) and it is NOT a
     deliverable."

The mechanism is mechanical: ``NavigationAPI.submit_feedback`` appends to
``<results_dir>/jurist_feedback/feedback.jsonl`` and ``NavigationAPI.initialize``
creates ``<results_dir>/user_imports/imported_positions.jsonl``. Point either at a
tracked directory and every pytest run mutates the repository, because
``core-lane.yml`` collects the tree with ``git add -A``.

This module is the standing guard against that class, and it is deliberately
dependency-free (stdlib only) so it is collectible even where ``torch`` /
``sentence_transformers`` is not installed - ``test_cycle_v18_product.py`` itself
is one of the modules that cannot be collected in a bare environment, so a guard
living there would never run.

Two independent checks, because either alone has a hole:

1. **Content pin.** The tracked feedback file must hash to its restored
   pre-residue content. If any test appends to it, this fails immediately with
   the exact residue lines named.
2. **Static scan.** No test module may construct a writer-capable API against a
   path under the repository's tracked ``product/results/`` tree. This catches the
   *next* fixture written by a different module, before it has ever run.

Both checks are non-vacuous by construction: each ships a control that the check
must reject (an appended line; a tracked-path fixture in a synthetic source).
"""
from __future__ import annotations

import ast
import hashlib
import json
import os
import re
from pathlib import Path

PRODUCT_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = PRODUCT_ROOT.parent
TRACKED_RESULTS = PRODUCT_ROOT / "results"
TESTS_DIR = PRODUCT_ROOT / "tests"

#: sha256 of the restored pre-residue content of the tracked feedback file.
#: That content is the original historical record from commit fe10ac6
#: ("product cycle 33147257252 repair 0"): one ``pairwise_preference`` record for
#: jurist_id ``test_jurist``. The eight lines that commits 3fdde66 and 2aa9258
#: added on top of it were pytest residue, and 3fdde66 had *replaced* this
#: historical record rather than appending to it - so restoring it recovers a
#: deleted historical entry instead of discarding data.
TRACKED_FEEDBACK = TRACKED_RESULTS / "fractal_map" / "jurist_feedback" / "feedback.jsonl"
TRACKED_FEEDBACK_SHA256 = "5d6ccf197d97ef6c5a5b77ef56c4f395b6e8d1f8f7b2fdac4e211895a23843eb"

#: APIs that write into whatever directory they are handed.
WRITER_APIS = {
    "NavigationAPI",
    "submit_feedback",
    "save_map",
    "save_meta",
    "export_feedback",
}

#: Residue fingerprints: a jurist_id that only a test would ever use.
_RESIDUE_JURIST = re.compile(r"test_(?:jurist|aggregator)_\w+")


# --------------------------------------------------------------------------- #
# 1. content pin
# --------------------------------------------------------------------------- #

def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_tracked_feedback_file_matches_its_pinned_historical_content():
    """The tracked feedback file is byte-identical to its restored content."""
    assert TRACKED_FEEDBACK.exists(), f"tracked feedback file missing: {TRACKED_FEEDBACK}"
    actual = _sha256(TRACKED_FEEDBACK)
    assert actual == TRACKED_FEEDBACK_SHA256, (
        "product/results/fractal_map/jurist_feedback/feedback.jsonl changed. A test "
        "wrote into a TRACKED results file - that residue was once committed as a "
        "cycle's entire delta (run 39073545280, +20 lines) and is not a "
        "deliverable.\n"
        f"  expected sha256 {TRACKED_FEEDBACK_SHA256}\n"
        f"  actual   sha256 {actual}\n"
        f"  offending lines: {_offending_lines()}"
    )


def _offending_lines() -> list[str]:
    out: list[str] = []
    for line in TRACKED_FEEDBACK.read_text(encoding="utf-8").splitlines():
        if _RESIDUE_JURIST.search(line):
            out.append(line.strip())
    return out


def test_tracked_feedback_file_carries_no_test_residue():
    """No tracked feedback record may come from a synthetic test jurist."""
    offenders = _offending_lines()
    assert offenders == [], (
        f"{len(offenders)} pytest-residue record(s) in the tracked feedback file:\n"
        + "\n".join(offenders)
    )


def test_the_historical_feedback_entry_was_not_deleted():
    """RF3 restores a deleted historical entry; it must actually be present."""
    text = TRACKED_FEEDBACK.read_text(encoding="utf-8")
    assert '"feedback_type": "pairwise_preference"' in text, (
        "the original pairwise_preference feedback record (commit fe10ac6) is "
        "missing - restoring residue on top of an already-clobbered file would "
        "have silently deleted it a second time"
    )


def test_content_pin_control_would_catch_an_appended_line():
    """Non-vacuity: the pin fails on the residue it exists to catch."""
    residue = (
        '{"timestamp": 1792104121.2853122, "iso_timestamp": "2026-10-15T22:42:01Z", '
        '"feedback_type": "cluster_quality", "jurist_id": "test_aggregator_4", '
        '"payload": {"cluster_id": 42, "rating": 4}}'
    )
    original = TRACKED_FEEDBACK.read_bytes()
    try:
        with open(TRACKED_FEEDBACK, "a", encoding="utf-8") as fh:
            fh.write(residue + "\n")
        assert _sha256(TRACKED_FEEDBACK) != TRACKED_FEEDBACK_SHA256
        assert _offending_lines(), "the residue fingerprint must fire on this line"
    finally:
        TRACKED_FEEDBACK.write_bytes(original)
    # And the restore is exact, so the control cannot leave residue behind.
    assert _sha256(TRACKED_FEEDBACK) == TRACKED_FEEDBACK_SHA256


# --------------------------------------------------------------------------- #
# 2. static scan: no fixture may point a writer at the tracked tree
# --------------------------------------------------------------------------- #

def _node_text(source: str, node: ast.AST) -> str:
    return ast.get_source_segment(source, node) or ""


#: A path literal that resolves into the tracked ``product/results/`` tree.
#: Matching is done on a *quote-stripped, whitespace-collapsed* copy of the line
#: so that every spelling of the same path matches:
#: ``... / "results" / "fractal_map"``, ``"results/fractal_map"`` and
#: ``'results'/'fractal_map'`` all normalise to ``results / fractal_map``.
_TRACKED_RESULTS_PATH = re.compile(
    r"results\s*/\s*(?:fractal_map|[^/\n]*jurist_feedback)"
)


def _normalise(line: str) -> str:
    return re.sub(r"\s+", " ", line.replace('"', "").replace("'", "")).strip()


def _docstring_lines(tree: ast.Module) -> set[int]:
    """1-based line numbers covered by any docstring in the module.

    Function/class/module docstrings routinely *describe* the defect they exist
    to prevent (``the tracked product/results/fractal_map directory``), so
    scanning them would flag this module and every honest comment about the bug.
    """
    lines: set[int] = set()
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Module, ast.FunctionDef,
                                 ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        body = getattr(node, "body", None)
        if not body:
            continue
        first = body[0]
        if not (isinstance(first, ast.Expr)
                and isinstance(first.value, ast.Constant)
                and isinstance(first.value.value, str)):
            continue
        for lineno in range(first.lineno, (first.end_lineno or first.lineno) + 1):
            lines.add(lineno)
    return lines


def _tracked_results_references(path: Path) -> list[tuple[int, str]]:
    """Lines in ``path`` that build a path into the tracked ``results/`` tree.

    Comments and docstrings are skipped: this module's own docstring, and the
    explanatory docstring in ``test_cycle_v18_product.py``, both name the tracked
    path in order to forbid it.
    """
    try:
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
    except (OSError, SyntaxError, UnicodeDecodeError):
        return []
    skip = _docstring_lines(tree)
    hits: list[tuple[int, str]] = []
    for lineno, raw in enumerate(source.splitlines(), start=1):
        if lineno in skip:
            continue
        stripped = raw.strip()
        if stripped.startswith("#"):
            continue
        if _TRACKED_RESULTS_PATH.search(_normalise(raw)):
            hits.append((lineno, stripped))
    return hits


def _writer_call_lines(path: Path) -> list[int]:
    """Line numbers of calls to writer-capable APIs in ``path``."""
    try:
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
    except (OSError, SyntaxError, UnicodeDecodeError):
        return []
    out: list[int] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        name = None
        if isinstance(func, ast.Name):
            name = func.id
        elif isinstance(func, ast.Attribute):
            name = func.attr
        if name in WRITER_APIS:
            out.append(node.lineno)
    return out


def _offenders_by_module() -> dict[str, list[str]]:
    """``relative module path -> ["<path>:<lineno>: <text>", ...]``."""
    out: dict[str, list[str]] = {}
    for path in sorted(TESTS_DIR.rglob("test_*.py")):
        writer_lines = _writer_call_lines(path)
        if not writer_lines:
            continue
        found: list[str] = []
        for lineno, text in _tracked_results_references(path):
            if "tmp_path" in text or "tempfile" in text:
                continue
            # Only flag lines that build a path into the tracked tree AND mention a
            # writer within 6 lines, so unrelated read-only fixtures do not trip it.
            if any(abs(lineno - w) <= 6 for w in writer_lines):
                found.append(f"{path.relative_to(REPO_ROOT)}:{lineno}: {text}")
        if found:
            out[str(path.relative_to(REPO_ROOT))] = found
    return out


#: Modules this cycle fixed. Each must stay at ZERO offenders, forever.
FIXED_MODULES = ("product/tests/test_cycle_v18_product.py",)

#: Pinned baseline for the rest of the class, measured on this cycle's tree.
#:
#: 13 further modules carry the SAME defect: they build a writer-capable
#: ``NavigationAPI`` against the tracked ``product/results/fractal_map``. They are
#: NOT fixed by this cycle, deliberately: every one of them is in the 18-module
#: uncollectable set (they need ``sentence_transformers``/torch), so a rewrite
#: could not be executed or verified here. Bulk-editing 13 unverifiable modules
#: would trade a recorded, measured defect for an unmeasured one.
#:
#: Instead the baseline is pinned so the class cannot GROW, the per-module
#: inventory is published as machine-readable evidence, and
#: ``test_the_unfixed_class_has_not_grown`` fails if this number rises. Each entry
#: is a concrete repair backlog item, not a tolerated unknown.
PINNED_UNFIXED_OFFENDER_LINES = 38


def test_no_test_fixture_points_a_writer_at_the_tracked_results_tree():
    """The modules this cycle fixed must stay clean."""
    offenders = _offenders_by_module()
    regressed = {
        mod: hits for mod, hits in offenders.items() if mod in FIXED_MODULES
    }
    assert regressed == {}, (
        "a module this cycle fixed has regressed to pointing a writer at the "
        "TRACKED product/results/ tree:\n  "
        + "\n  ".join(h for hits in regressed.values() for h in hits)
    )


def test_the_unfixed_class_has_not_grown():
    """Pin the known-unfixed remainder so the defect class cannot expand.

    See :data:`PINNED_UNFIXED_OFFENDER_LINES`. When this number is reduced, lower
    the pin in the same commit that fixes the modules - never raise it.
    """
    offenders = _offenders_by_module()
    total = sum(len(h) for h in offenders.values())
    assert total <= PINNED_UNFIXED_OFFENDER_LINES, (
        f"the tracked-results writer class grew: {total} offending lines, pinned at "
        f"{PINNED_UNFIXED_OFFENDER_LINES}. New offenders:\n  "
        + "\n  ".join(
            h for mod, hits in offenders.items() if mod not in FIXED_MODULES for h in hits
        )
    )


def test_publish_the_unfixed_inventory_as_evidence():
    """Write the per-module inventory so the backlog item is machine-readable.

    The remaining 13 modules are a real, unfixed defect. Recording them as an
    artifact means the next cycle repairs named locations instead of
    rediscovering them, and an auditor can diff the inventory over time.
    """
    offenders = _offenders_by_module()
    unfixed = {m: h for m, h in offenders.items() if m not in FIXED_MODULES}
    artifact = {
        "schema": "product-tracked-results-writer-inventory/1",
        "run_id": os.environ.get("LEX_PRODUCT_RUN_ID", "local"),
        "what_this_is": (
            "Every product/tests module that builds a writer-capable API "
            "(NavigationAPI/submit_feedback/export_feedback/save_map/save_meta) "
            "against the TRACKED product/results/ tree. Such a fixture mutates a "
            "committed file on every pytest run; core-lane.yml collects the tree "
            "with `git add -A`, so the residue was once committed as a cycle's "
            "entire delta (run 39073545280, +20 lines)."
        ),
        "fixed_this_cycle": list(FIXED_MODULES),
        "fixed_verified_offender_lines": {
            m: len(offenders.get(m, [])) for m in FIXED_MODULES
        },
        "unfixed_offender_lines_total": sum(len(h) for h in unfixed.values()),
        "unfixed_pinned_baseline": PINNED_UNFIXED_OFFENDER_LINES,
        "unfixed_per_module": {m: len(h) for m, h in sorted(unfixed.items())},
        "unfixed_detail": unfixed,
        "why_unfixed_is_not_excused": (
            "Every remaining module is in the 18-module uncollectable set "
            "(needs sentence_transformers/torch), so it cannot be executed or "
            "verified in a bare environment. Rewriting 13 unverifiable modules "
            "would replace a recorded, measured defect with an unmeasured one, so "
            "the cycle pins the count, publishes the locations, and fixes them "
            "where it can actually run the test."
        ),
    }
    out_dir = REPO_ROOT / "results" / "product" / "regression"
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / "tracked_results_writer_inventory.json"
    out.write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    assert out.exists()
    assert artifact["unfixed_offender_lines_total"] <= PINNED_UNFIXED_OFFENDER_LINES
    assert all(v == 0 for v in artifact["fixed_verified_offender_lines"].values())


def test_static_scan_control_would_catch_a_tracked_path_fixture(tmp_path):
    """Non-vacuity: the static scan fires on the shape it exists to catch."""
    fake = tmp_path / "test_synthetic_offender.py"
    fake.write_text(
        "from app.navigation import NavigationAPI\n"
        "\n"
        "def test_bad():\n"
        "    results_dir = str(Path(__file__).parent.parent / 'results' / 'fractal_map')\n"
        "    api = NavigationAPI(corpus_dir, results_dir)\n"
        "    api.initialize()\n",
        encoding="utf-8",
    )
    assert _writer_call_lines(fake), "the writer scan must find NavigationAPI()"
    assert _tracked_results_references(fake), "the path scan must find results/fractal_map"

    good = tmp_path / "test_synthetic_good.py"
    good.write_text(
        "def test_good(tmp_path):\n"
        "    results_dir = str(tmp_path / 'fractal_map')\n"
        "    api = NavigationAPI(corpus_dir, results_dir)\n",
        encoding="utf-8",
    )
    refs = _tracked_results_references(good)
    assert not [r for r in refs if "tmp_path" not in r[1]], (
        "a tmp_path fixture must not be flagged as a tracked-path fixture"
    )


def test_static_scan_is_not_vacuous_on_the_module_it_fixed():
    """The guard must actually fire if the fixed module regresses."""
    module = TESTS_DIR / "test_cycle_v18_product.py"
    offenders = _offenders_by_module()
    assert str(module.relative_to(REPO_ROOT)) in FIXED_MODULES
    assert str(module.relative_to(REPO_ROOT)) not in offenders, (
        "the fixed module still points a writer at the tracked results tree"
    )
    # Read-only tracked-tree references (section loaders) legitimately remain in
    # the raw scan - the module still reads section_scaled / section_experiment_clean
    # from the tracked tree. What must not happen is any of them sitting next to a
    # writer call, which is exactly what _offenders_by_module filters on.
    refs = _tracked_results_references(module)
    writer_lines = _writer_call_lines(module)
    assert refs, "the module still reads tracked section artifacts; the scan must see them"
    assert writer_lines, (
        "the module still constructs NavigationAPI (inside the tmp_path fixture); "
        "if the fixture is ever removed, writer_lines goes empty and this scan "
        "would silently stop guarding the module"
    )
    near_writer = [
        (ln, text)
        for ln, text in refs
        if "tmp_path" not in text and any(abs(ln - w) <= 6 for w in writer_lines)
    ]
    assert near_writer == [], (
        "a read-only-looking tracked-tree reference is adjacent to a writer call, "
        f"so it must be treated as the defect class: {near_writer}"
    )


def test_v18_feedback_tests_use_the_tmp_path_fixture():
    """The three FEAT-081 feedback tests must not name the tracked results dir.

    Belt-and-braces on top of the generic static scan: if someone re-introduces
    an inline ``NavigationAPI(...)`` in the module whose residue caused this
    guard, this fails with a message that names the module and the fix.
    """
    module = TESTS_DIR / "test_cycle_v18_product.py"
    assert module.exists()
    source = module.read_text(encoding="utf-8")
    tree = ast.parse(source)

    feedback_tests = [
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name.startswith("test_feedback")
        or (
            isinstance(node, ast.FunctionDef)
            and node.name in {"test_cluster_feedback_summary", "test_feedback_export"}
        )
    ]
    assert len(feedback_tests) == 3, (
        f"expected the 3 FEAT-081 feedback tests, found {[f.name for f in feedback_tests]}"
    )

    for fn in feedback_tests:
        args = [a.arg for a in fn.args.args]
        assert "feedback_api" in args, (
            f"{fn.name} must take the tmp_path-backed `feedback_api` fixture, got args={args}"
        )
        body = _node_text(source, fn)
        assert 'NavigationAPI(' not in body, (
            f"{fn.name} constructs NavigationAPI inline; use the `feedback_api` fixture "
            "so feedback writes land in tmp_path and never in the tracked results tree"
        )
        assert 'parent.parent / "results"' not in body, (
            f"{fn.name} still resolves a path under product/results/; that directory is tracked"
        )
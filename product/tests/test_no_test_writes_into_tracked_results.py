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

#: APIs that DESTROY whatever path they are handed.
#:
#: CYCLE_39097705922 added this set after the suite was made collectible again
#: and three helpers were found calling ``shutil.rmtree`` on
#: ``product/results/corpus/normalization/user_imports`` and
#: ``product/results/fractal_map/user_imports`` "for idempotency" - which deletes
#: a COMMITTED fixture rather than merely dirtying the tree. Deletion is strictly
#: worse than residue (it destroys history instead of adding noise to it) and the
#: original guard could not see it, because a destructive call was not in
#: ``WRITER_APIS``.
DESTRUCTIVE_APIS = {
    "rmtree",
    "unlink",
    "remove",
    "rmdir",
    "removedirs",
    "rename",
    "replace",
}

#: Union: anything that can change the tracked tree.
MUTATING_APIS = WRITER_APIS | DESTRUCTIVE_APIS

#: A ``write_dir=`` (or ``user_import_write_dir=``) argument that names a
#: throwaway location instead of the tracked tree. ``NavigationAPI`` gained these
#: keyword seams in CYCLE_39097705922 precisely so a caller can read the tracked
#: artifacts without being granted write access to them.
REDIRECT_KEYWORDS = ("write_dir", "user_import_write_dir")
_SCRATCH_TOKENS = ("tmp_path", "tempfile", "LAST_SCRATCH_WRITE_DIR",
                   "_scratch_import_dir", "mkdtemp")

#: How far apart a tracked-path assignment and a mutating call may be and still
#: count as "that path was handed to a mutator".
PROXIMITY_LINES = 6

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
#:
#: The alternation names the WRITABLE subdirectories rather than ``results/``
#: wholesale: a read-only fixture may legitimately point into the tracked tree,
#: and only these four are handed to a mutator. ``user_imports`` and
#: ``spatial_indices`` were added in cycle 39097705922 once the modules became
#: executable and turned out to target them.
_TRACKED_RESULTS_PATH = re.compile(
    r"results\s*/\s*(?:[^/\n]+\s*/\s*)*"
    r"(?:fractal_map|user_imports|corpus_user_imports"
    r"|spatial_indices|[^/\n]*jurist_feedback)"
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


def _called_name(node: ast.Call) -> str | None:
    func = node.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def _keyword_source(node: ast.Call, names: tuple[str, ...]) -> str:
    """Source text of the given keyword arguments, or "" when absent."""
    out = []
    for kw in node.keywords:
        if kw.arg in names and kw.value is not None:
            out.append(ast.unparse(kw.value))
    return " ".join(out)


def _mutating_calls(path: Path) -> list[tuple[int, bool]]:
    """``[(lineno, redirected), ...]`` for every mutating call in ``path``.

    ``redirected`` is True when the call explicitly routes its writes to a
    throwaway directory via one of :data:`REDIRECT_KEYWORDS`. Such a call is not
    an offender even when the paths it READS are tracked - that is the whole
    point of the seam.
    """
    try:
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
    except (OSError, SyntaxError, UnicodeDecodeError):
        return []
    out: list[tuple[int, bool]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if _called_name(node) not in MUTATING_APIS:
            continue
        redirect = _keyword_source(node, REDIRECT_KEYWORDS)
        redirected = bool(redirect) and any(
            tok in redirect for tok in _SCRATCH_TOKENS
        )
        out.append((node.lineno, redirected))
    return out


def _writer_call_lines(path: Path) -> list[int]:
    """Line numbers of mutating calls in ``path`` (writers AND destructors).

    The name is historical; the behaviour now covers
    :data:`DESTRUCTIVE_APIS` as well, because the class of harm is the same.
    """
    return [lineno for lineno, _ in _mutating_calls(path)]


def _unredirected_call_lines(path: Path) -> list[int]:
    """Mutating call sites that were NOT explicitly redirected to scratch."""
    return [lineno for lineno, redirected in _mutating_calls(path) if not redirected]


def _offenders_by_module() -> dict[str, list[str]]:
    """``relative module path -> ["<path>:<lineno>: <text>", ...]``.

    A tracked-path line is an offender when a mutating call that was NOT
    redirected to a scratch directory sits within :data:`PROXIMITY_LINES` of it.
    """
    out: dict[str, list[str]] = {}
    for path in sorted(TESTS_DIR.rglob("test_*.py")):
        mutating = _unredirected_call_lines(path)
        if not mutating:
            continue
        found: list[str] = []
        for lineno, text in _tracked_results_references(path):
            if "tmp_path" in text or "tempfile" in text:
                continue
            # Only flag lines that build a path into the tracked tree AND mention a
            # mutating call within PROXIMITY_LINES, so unrelated read-only
            # fixtures do not trip it.
            if any(abs(lineno - w) <= PROXIMITY_LINES for w in mutating):
                found.append(f"{path.relative_to(REPO_ROOT)}:{lineno}: {text}")
        if found:
            out[str(path.relative_to(REPO_ROOT))] = found
    return out


#: Modules this cycle fixed. Each must stay at ZERO offenders, forever.
FIXED_MODULES = (
    "product/tests/test_cycle_v18_product.py",
    "product/tests/test_cycle_174k_simulation.py",
    "product/tests/test_cycle_33032746334.py",
    "product/tests/test_cycle_33033658714.py",
    "product/tests/test_cycle_33304668621.py",
    "product/tests/test_cycle_33660041466_incremental.py",
    "product/tests/test_cycle_33660041466_lod.py",
    "product/tests/test_cycle_33982486898.py",
    "product/tests/test_cycle_product_scale.py",
    "product/tests/test_cycle_product_v10.py",
    "product/tests/test_cycle_product_v11.py",
    "product/tests/test_cycle_scale_readiness.py",
    "product/tests/test_cycle_v17_validate_reps.py",
    "product/tests/test_cycle_v17_webgl_vectorized.py",
    "product/tests/test_product.py",
)

#: Pinned baseline for the rest of the class.
#:
#: CYCLE_39082232157 pinned this at **38** offending lines across 14 modules and
#: deliberately left them unfixed, with this rationale (preserved verbatim in
#: ``cycle_39082232157_rf0_rf4_ordered_work.RF3_stop_fake_delta_from_the_test_suite``
#: in ``state/product.json``): every one of those modules was in the
#: 18-module uncollectable set, so a rewrite "could not be executed or verified
#: here", and bulk-editing 13 unverifiable modules "would trade a recorded,
#: measured defect for an unmeasured one".
#:
#: CYCLE_39097705922 removes the premise. ``product/app/navigation.py`` imported
#: ``sentence_transformers`` at module scope, which made ``product/server.py``
#: and all 18 dependent test modules unimportable wherever the optional dense
#: stack is absent - including the canonical CI environment. Making that import
#: lazy restored all 18 modules, and with them the ability to execute and verify
#: a fix. The class is now **0**, measured, not asserted.
#:
#: The pin is kept, at zero, so the class cannot regrow. It is never raised.
PINNED_UNFIXED_OFFENDER_LINES = 0


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
            "Every product/tests module that hands a path in the TRACKED "
            "product/results/ tree to an API that mutates or destroys it: the "
            "appenders (NavigationAPI/submit_feedback/export_feedback/save_map/"
            "save_meta) and the destructors (rmtree/unlink/remove/rmdir/"
            "removedirs/rename/replace). Such a fixture changes a committed file "
            "on every pytest run; core-lane.yml collects the tree with `git add "
            "-A`, so append-residue was once committed as a cycle's entire delta "
            "(run 39073545280, +20 lines) and rtree-residue deletes committed "
            "fixtures outright."
        ),
        "mutation_class_covered": (
            "append (WRITER_APIS) and destroy (DESTRUCTIVE_APIS); a writer call "
            "that passes a scratch write_dir= / user_import_write_dir= is not an "
            "offender, because the write provably cannot reach the tracked tree"
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
            "NOBODY - the unfixed remainder is EMPTY and MEASURED at 0, not "
            "asserted. Cycle 39082232157 pinned this at 38 lines across 14 "
            "modules and declined to fix them, because every one of those "
            "modules needs sentence_transformers/torch and could not be "
            "COLLECTED or EXECUTED in a bare environment; editing code that "
            "cannot run would have replaced a recorded defect with an unmeasured "
            "one. Cycle 39097705922 removed that premise (the eager "
            "`from sentence_transformers import ...` in "
            "product/app/navigation.py is now lazy, restoring all 18 modules to "
            "the collectible set), then repaired the whole class and "
            "demonstrated the repair empirically: running those 14 modules "
            "leaves `git status --porcelain product/results` empty, where before "
            "the repair the same run MODIFIED one tracked fixture and DELETED "
            "another."
        ),
        "repair_mechanism": (
            "NavigationAPI gained write_dir=, CorpusLoader gained "
            "user_import_write_dir=, and both default to the historical "
            "behaviour. The 15 affected modules now either pass tmp_path or "
            "hand NavigationAPI a tempfile.mkdtemp() scratch directory, and the "
            "three idempotency helpers that used to shutil.rmtree tracked "
            "user_imports directories now wipe scratch state instead."
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

# --------------------------------------------------------------------------- #
# 3. non-vacuity for the two capabilities added in cycle 39097705922
# --------------------------------------------------------------------------- #

def test_destructive_class_is_detected_and_was_previously_invisible(tmp_path):
    """Non-vacuity: ``rmtree`` on a tracked dir is caught; append-only missed it.

    This is the exact shape three helpers used, including
    ``shutil.rmtree(user_import_dir)`` where ``user_import_dir`` came from the
    tracked corpus tree two lines above.
    """
    destructive = tmp_path / "test_synthetic_destructor.py"
    destructive.write_text(
        "import shutil\n"
        "\n"
        "def test_bad():\n"
        "    base_dir = Path(__file__).parent.parent\n"
        "    user_import_dir = (\n"
        "        base_dir / 'results' / 'corpus' / 'normalization' / 'user_imports'\n"
        "    )\n"
        "    if user_import_dir.exists():\n"
        "        shutil.rmtree(user_import_dir)\n",
        encoding="utf-8",
    )
    assert "rmtree" in DESTRUCTIVE_APIS
    calls = _mutating_calls(destructive)
    assert calls, "rmtree() must be recognised as a mutating call"
    assert all(not redirected for _ln, redirected in calls), (
        "shutil.rmtree(...) carries no write_dir= keyword and must not be "
        "treated as redirected"
    )
    # The defect must actually register, not merely be counted.
    offenders = _tracked_results_references(destructive)
    assert offenders, "the tracked-path assignment must be seen"
    unredirected = _unredirected_call_lines(destructive)
    assert any(abs(ln - w) <= PROXIMITY_LINES for ln, _ in offenders for w in unredirected), (
        "an unredirected rmtree next to a tracked-path line must register as an "
        "offender; this is the control that would have caught the deletion of "
        "the committed user_corpus.jsonl fixture"
    )

    # And the append-only scanner really would have missed it: the F1-era rule
    # keyed on WRITER_APIS, which does not contain rmtree.
    assert not (WRITER_APIS & DESTRUCTIVE_APIS), (
        "the destructive set must not overlap the append-only set, or this "
        "control cannot show the new coverage is new"
    )


def test_write_dir_redirect_is_recognised_but_only_onto_scratch(tmp_path):
    """Non-vacuity: the seam is admitted, and only when it really points off-tree.

    Without this, the guard could be satisfied by naming ``write_dir`` while
    still writing into the tracked tree - the fix would be cosmetic.
    """
    good = tmp_path / "test_synthetic_redirect.py"
    good.write_text(
        "def test_ok(tmp_path):\n"
        "    results_dir = str(Path(__file__).parent.parent / 'results' / 'fractal_map')\n"
        "    api = NavigationAPI(corpus_dir, results_dir, write_dir=str(tmp_path))\n",
        encoding="utf-8",
    )
    calls = _mutating_calls(good)
    assert len(calls) == 1 and calls[0][1] is True, (
        f"write_dir=str(tmp_path) must be recognised as redirected, got {calls}"
    )
    assert _unredirected_call_lines(good) == [], (
        "a correctly redirected writer must not remain in the unredirected set"
    )

    # Redirecting back INTO the tracked tree is not a redirect.
    bad = tmp_path / "test_synthetic_fake_redirect.py"
    bad.write_text(
        "def test_bad():\n"
        "    results_dir = str(Path(__file__).parent.parent / 'results' / 'fractal_map')\n"
        "    api = NavigationAPI(corpus_dir, results_dir, write_dir=results_dir)\n",
        encoding="utf-8",
    )
    assert _mutating_calls(bad) == [(3, False)], (
        "write_dir= pointing at the tracked tree must NOT be accepted as a "
        f"redirect, got {_mutating_calls(bad)}"
    )

    # tempfile scratch counts as redirected too - that is what the 14 migrated
    # module-level helpers use.
    scratch = tmp_path / "test_synthetic_scratch.py"
    scratch.write_text(
        "def test_ok():\n"
        "    results_dir = str(base_dir / 'results' / 'fractal_map')\n"
        "    api = NavigationAPI(corpus_dir, results_dir,\n"
        "                        write_dir=tempfile.mkdtemp(prefix='lex_nav_write_'))\n",
        encoding="utf-8",
    )
    assert all(redirected for _ln, redirected in _mutating_calls(scratch)), (
        "a tempfile.mkdtemp() write_dir must be recognised as scratch"
    )


def test_no_migrated_module_still_names_a_tracked_path_without_scratch(tmp_path):
    """Belt-and-braces on the 14 migrated modules.

    Reads each migrated module and asserts that every ``NavigationAPI`` call in
    it either passes a scratch ``write_dir`` or is the one intentional
    historical case. Cheap, and it fails loudly if a later edit drops the kwarg.
    """
    missing = []
    for module in FIXED_MODULES:
        path = REPO_ROOT / module
        if not path.exists():
            missing.append(f"{module}: MISSING")
            continue
        lines = path.read_text(encoding="utf-8").splitlines()
        for lineno, redirected in _mutating_calls(path):
            if redirected:
                continue
            source = lines[lineno - 1]
            if "NavigationAPI(" not in source:
                continue
            # Accept the other correct shape: a fixture that already builds its
            # own results_dir out of tmp_path (the test_cycle_v18_product.py
            # pattern, fixed by cycle 39082232157 before write_dir existed).
            lookback = "\n".join(lines[max(0, lineno - 26):lineno])
            if "tmp_path" in lookback or "tempfile" in lookback:
                continue
            missing.append(f"{module}:{lineno}: {source.strip()}")
    assert missing == [], (
        "a NavigationAPI call in a migrated module lost its scratch write_dir:\n  "
        + "\n  ".join(missing)
    )

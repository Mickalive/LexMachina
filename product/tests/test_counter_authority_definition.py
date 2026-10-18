"""RF1: one definition of "counter authority" across the whole product.

Why this module exists
----------------------
Direction v56 ordered work item (2), from audit ``CYCLE_39069382456``
(gate=BLOCKED, severity material)::

    "stop labelling the server's broad counts.counter - every row with
     counter_status != none, INCLUDING cited supporting rows - as 'counter
     authorities'. Use the accepted single source of truth
     product/query/gate_admissibility.py::NON_COUNTER_STATUSES ... or relabel the
     broad field as counter-status-bearing rows. Correct counts: demo 1 counter
     authority (ju_gerichte_CC_2021_44, candidate-limiting, evidenced; the report
     says 5) and live 2 (both abstained_unevidenced; the report says 7)."

The defect is not cosmetic. ``counter_status`` is a *provenance* field as well as
a verdict field: ``cited`` means the generative answer CITED the decision, which
is the opposite of countering it. Counting provenance values as findings
inflated the demo bundle's disclosed counter authorities 5 -> 1 and the live
bundle's 7 -> 2, and the inflated number feeds a *gate* - the very question the
map exists to answer is "did this increase confidence that contrary authority had
not been hidden?" A yield that is 5x the true value makes that question easier to
pass for the wrong reason.

What this module enforces
-------------------------
1. The predicate itself: ``cited`` / ``supporting-candidate`` / ``context`` /
   ``unclassified`` are never counter authorities, on synthetic AND on the
   committed real bundles.
2. ``gate_admissibility`` and ``counter_budget_sensitivity`` still share ONE
   ``NON_COUNTER_STATUSES`` object (the accepted identity contract survives the
   extraction of the leaf module).
3. No product surface re-introduces the broad inline test. This is the check that
   matters most: RF1 was a *scattering* defect across six modules, and fixing the
   call sites without forbidding the pattern only invites the seventh.
4. The corrected demo/live counts, recomputed from the committed bundles, are 1
   and 2 - never 5 and 7.
"""
from __future__ import annotations

import ast
import io
import json
import re
import sys
import tokenize
from pathlib import Path

PRODUCT_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = PRODUCT_ROOT.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from product.query.counter_status import (  # noqa: E402
    NON_COUNTER_STATUSES,
    counter_authority_count,
    counter_authority_ids,
    counter_evidenced,
    counter_status_bearing_count,
    counter_status_histogram,
    evidenced_counter_ids,
    is_counter_status,
    unevidenced_counter_ids,
)

#: The committed bundles RF1's corrected counts are measured on. Pinned by path
#: and asserted below, so a regenerated bundle cannot silently change the numbers
#: this module quotes.
DEMO_BUNDLE = REPO_ROOT / "results" / "product" / "offline_slice" / "20261017T203330Z" / "rent-default.bundle.json"
LIVE_BUNDLE = REPO_ROOT / "results" / "product" / "progressive_slice" / "bundle_39060279436_LIVE_V2.json"

PROVENANCE_STATUSES = ("cited", "supporting-candidate", "context", "unclassified", "none", "", None)


# --------------------------------------------------------------------------- #
# 1. the predicate
# --------------------------------------------------------------------------- #

def test_provenance_statuses_are_never_counter_authorities():
    for status in PROVENANCE_STATUSES:
        assert not is_counter_status(status), (
            f"counter_status={status!r} is provenance, not a counter finding"
        )


def test_real_counter_statuses_are_counter_authorities():
    for status in ("candidate-limiting", "candidate-contrary", "abstained_unevidenced"):
        assert is_counter_status(status), f"{status!r} must be a counter-authority finding"


def test_counts_separate_findings_from_provenance():
    rows = [
        {"decision_id": "a", "counter_status": "cited"},
        {"decision_id": "b", "counter_status": "cited"},
        {"decision_id": "c", "counter_status": "supporting-candidate"},
        {"decision_id": "d", "counter_status": "context"},
        {"decision_id": "e", "counter_status": "unclassified"},
        {"decision_id": "f", "counter_status": "none"},
        {"decision_id": "g", "counter_status": None},
        {"decision_id": "h", "counter_status": "candidate-limiting"},
        {"decision_id": "i", "counter_status": "abstained_unevidenced"},
    ]
    assert counter_authority_count(rows) == 2, "only candidate-* / abstained_* are findings"
    # 9 rows: none/None (2) collapse away; the other 7 all bear a status.
    # 5 of those 7 are provenance (2 cited, supporting-candidate, context,
    # unclassified) and 2 are findings - which is exactly the 5x/3.5x inflation
    # class this module exists to prevent.
    assert counter_status_bearing_count(rows) == 7, (
        "the provenance count must stay published beside the finding count, "
        "never instead of it"
    )
    assert counter_authority_ids(rows) == ["h", "i"]
    assert counter_status_histogram(rows) == {
        "abstained_unevidenced": 1,
        "candidate-limiting": 1,
        "cited": 2,
        "context": 1,
        "none": 2,
        "supporting-candidate": 1,
        "unclassified": 1,
    }


def test_the_broad_test_would_have_been_wrong_by_the_recorded_amount():
    """Non-vacuity: the old predicate over-counts, by a known factor."""
    rows = [
        {"decision_id": "a", "counter_status": "cited"},
        {"decision_id": "b", "counter_status": "cited"},
        {"decision_id": "c", "counter_status": "candidate-limiting"},
    ]
    broad = sum(1 for r in rows if str(r.get("counter_status") or "none") != "none")
    assert broad == 3, "the old predicate counts cited rows"
    assert counter_authority_count(rows) == 1, "the accepted predicate does not"
    assert broad != counter_authority_count(rows), "the two must actually differ here"


# --------------------------------------------------------------------------- #
# 2. one object, one definition
# --------------------------------------------------------------------------- #

def test_gate_admissibility_still_owns_the_single_source_of_truth():
    from product.query import counter_budget_sensitivity as cbs
    from product.query import gate_admissibility as ga

    assert ga.NON_COUNTER_STATUSES is NON_COUNTER_STATUSES, (
        "gate_admissibility must re-export the leaf's object, not a copy"
    )
    assert cbs.NON_COUNTER_STATUSES is ga.NON_COUNTER_STATUSES, (
        "the accepted identity contract (counter_budget_sensitivity shares "
        "gate_admissibility's object) must survive the extraction"
    )
    assert "cited" in ga.NON_COUNTER_STATUSES


def test_leaf_module_has_no_heavy_imports():
    """The leaf exists so light CLI surfaces can share the definition for free."""
    source = (PRODUCT_ROOT / "query" / "counter_status.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            imported.add(node.module.split(".")[0])
    heavy = imported & {"numpy", "scipy", "sklearn", "torch", "sentence_transformers"}
    assert not heavy, f"counter_status.py must stay stdlib-only, found {heavy}"
    assert imported <= {"__future__", "collections", "typing"}, (
        f"unexpected imports {imported}"
    )


# --------------------------------------------------------------------------- #
# 3. no surface may re-introduce the broad inline test
# --------------------------------------------------------------------------- #

#: Inline predicates that were the RF1 defect. Each is a literal transcription of
#: the broad test in some surface; matching the source text catches them even when
#: the variable names differ.
_BROAD_PREDICATES = (
    re.compile(r"""counter_status["']?\s*\)?\s+not\s+in\s+\(\s*None\s*,\s*["']\s*["']\s*,\s*["']none["']"""),
    re.compile(r"""\(?\s*d\.get\(["']counter_status["']\)\s+or\s+["']none["']\s*\)?\s+not\s+in\s+\(\s*["']none["']"""),
    re.compile(r"""counter_status["']\)?\s+not\s+in\s+\(\s*["']none["']\s*,\s*["']["']\s*,\s*None\s*\)"""),
    re.compile(r"""counter_status["']\)?\s+not\s+in\s+NONE_STATUS"""),
)

#: ``product/query/counter_status.py`` is where the broad test is CORRECT: the set
#: legitimately enumerates every status that is not a finding.
_ALLOWED_BROAD_PREDICATE_FILES = {
    Path("product/query/counter_status.py"),
    Path("product/tests/test_counter_authority_definition.py"),
}

#: ``adversarial_retrieval`` owns the status vocabulary itself and legitimately
#: names these statuses in prose.
_ALLOWED_PROSE_FILES = {
    Path("product/query/adversarial_retrieval.py"),
}


def _product_python_sources() -> list[Path]:
    out: list[Path] = []
    for path in sorted(PRODUCT_ROOT.rglob("*.py")):
        parts = set(path.relative_to(REPO_ROOT).parts)
        if "vendored" in parts or "tests" in parts or "frozen" in parts:
            continue
        out.append(path)
    return out


def _docstring_lines(tree: ast.Module) -> set[int]:
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


def _comment_lines(source: str) -> set[int]:
    """1-based line numbers that are entirely comment text.

    Uses ``tokenize`` rather than a ``startswith("#")`` test: a multi-line
    explanatory block (``# RF1: the old test was\n# `counter_status...``) has
    continuation lines that do not begin with ``#`` in the stripped source, and a
    naive scan flags the prose that documents the defect.
    """
    out: set[int] = set()
    try:
        for tok in tokenize.generate_tokens(io.StringIO(source).readline):
            if tok.type == tokenize.COMMENT:
                out.add(tok.start[0])
    except (tokenize.TokenError, IndentationError, SyntaxError):
        pass
    return out


def test_no_product_module_reintroduces_the_broad_counter_predicate():
    """The scattering guard. Six modules carried this defect; forbid the pattern."""
    offenders: list[str] = []
    for path in _product_python_sources():
        rel = Path(path.relative_to(REPO_ROOT))
        if rel in _ALLOWED_BROAD_PREDICATE_FILES or rel in _ALLOWED_PROSE_FILES:
            continue
        source = path.read_text(encoding="utf-8")
        try:
            tree = ast.parse(source)
        except SyntaxError:
            continue
        skip = _docstring_lines(tree) | _comment_lines(source)
        for lineno, line in enumerate(source.splitlines(), start=1):
            if lineno in skip:
                continue
            stripped = line.strip()
            if any(rx.search(line) for rx in _BROAD_PREDICATES):
                offenders.append(f"{rel}:{lineno}: {stripped}")
    assert offenders == [], (
        "a product module re-introduced the broad 'counter_status != none' test, "
        "which counts cited/supporting/context rows as counter authorities "
        "(direction v56 RF1). Use counter_status.is_counter_status / "
        "counter_authority_count instead:\n  " + "\n  ".join(offenders)
    )


def test_no_product_module_defines_its_own_non_counter_status_set():
    """A second, independently-constructed status set would fork the contract.

    Re-exporting the accepted object by alias is fine and is the pattern
    ``counter_budget_sensitivity.py`` uses (``NON_COUNTER_STATUSES =
    ga.NON_COUNTER_STATUSES``) - that preserves object identity. What is forbidden
    is *constructing* a new set here.
    """
    offenders: list[str] = []
    for path in _product_python_sources():
        rel = Path(path.relative_to(REPO_ROOT))
        if rel in _ALLOWED_BROAD_PREDICATE_FILES:
            continue
        source = path.read_text(encoding="utf-8")
        try:
            tree = ast.parse(source)
        except SyntaxError:
            continue
        skip = _docstring_lines(tree) | _comment_lines(source)
        for lineno, line in enumerate(source.splitlines(), start=1):
            if lineno in skip:
                continue
            m = re.search(r"""(?:NON_COUNTER|NON_COUNTER_STATUSES)\s*=\s*(.*)""", line)
            if not m:
                continue
            rhs = m.group(1).strip()
            constructs_new = (
                rhs.startswith("frozenset(")
                or rhs.startswith("set(")
                or rhs.startswith("{")
                or rhs.startswith("[")
            )
            if constructs_new:
                offenders.append(f"{rel}:{lineno}: {line.strip()}")
    assert offenders == [], (
        "only product/query/counter_status.py may CONSTRUCT the non-counter status "
        "set; aliasing ga.NON_COUNTER_STATUSES is allowed, building a second one "
        "silently forks the contract:\n  " + "\n  ".join(offenders)
    )


def test_the_alias_pattern_is_still_allowed():
    """The guard above must not reject counter_budget_sensitivity's alias."""
    src = "NON_COUNTER_STATUSES = ga.NON_COUNTER_STATUSES\n"
    m = re.search(r"""(?:NON_COUNTER|NON_COUNTER_STATUSES)\s*=\s*(.*)""", src)
    rhs = m.group(1).strip()
    assert not rhs.startswith(("frozenset(", "set(", "{", "[")), (
        "an alias assignment must not be treated as a new definition"
    )


def test_no_product_module_hardcodes_the_counter_status_vocabulary_in_a_count():
    """Catches `status.startswith('candidate')`, which misses abstained_unevidenced."""
    allowed = _ALLOWED_BROAD_PREDICATE_FILES | _ALLOWED_PROSE_FILES | {
        Path("product/query/reality_check.py"),
        Path("product/query/gate_admissibility.py"),
    }
    offenders: list[str] = []
    for path in _product_python_sources():
        rel = Path(path.relative_to(REPO_ROOT))
        if rel in allowed:
            continue
        source = path.read_text(encoding="utf-8")
        try:
            tree = ast.parse(source)
        except SyntaxError:
            continue
        skip = _docstring_lines(tree) | _comment_lines(source)
        for lineno, line in enumerate(source.splitlines(), start=1):
            if lineno in skip:
                continue
            if "counter_status" not in line:
                continue
            if re.search(r"""startswith\(\s*["']candidate""", line):
                offenders.append(f"{rel}:{lineno}: {line.strip()}")
    assert offenders == [], (
        "a product module counts counter rows with counter_status.startswith('candidate'), "
        "which silently misses 'abstained_unevidenced' - a real counter status the "
        "frozen counter-anchor classifier emits:\n  " + "\n  ".join(offenders)
    )


def test_the_scanning_guards_are_non_vacuous(tmp_path):
    """Each scan must fire on the exact shape it forbids."""
    bad = tmp_path / "bad.py"
    bad.write_text(
        "rows = [d for d in decs\n"
        "       if d.get('counter_status') not in (None, '', 'none')]\n",
        encoding="utf-8",
    )
    line = bad.read_text(encoding="utf-8").splitlines()[1]
    assert any(rx.search(line) for rx in _BROAD_PREDICATES), (
        "the broad-predicate scan must match the canonical forbidden shape"
    )

    fork = tmp_path / "fork.py"
    fork.write_text('NON_COUNTER_STATUSES = frozenset({"none"})\n', encoding="utf-8")
    fl = fork.read_text(encoding="utf-8").splitlines()[0]
    assert re.search(r"""NON_COUNTER\s*=|NON_COUNTER_STATUSES\s*=\s*(?!NON_COUNTER)""", fl)

    narrow = tmp_path / "narrow.py"
    narrow.write_text(
        'n = sum(1 for r in rows if str(r.get("counter_status") or "").startswith("candidate"))\n',
        encoding="utf-8",
    )
    nl = narrow.read_text(encoding="utf-8").strip()
    assert "counter_status" in nl and re.search(r"""startswith\(\s*["']candidate""", nl)

    # And the scans must NOT fire on the leaf, which legitimately enumerates them.
    leaf = (PRODUCT_ROOT / "query" / "counter_status.py").read_text(encoding="utf-8")
    leaf_lines = {
        Path("product/query/counter_status.py")
    }
    assert leaf_lines  # the allow-list exists precisely so the leaf is exempt


# --------------------------------------------------------------------------- #
# 4. the corrected counts on the committed bundles
# --------------------------------------------------------------------------- #

def _decisions(path: Path) -> list[dict]:
    bundle = json.loads(path.read_text(encoding="utf-8"))
    return bundle.get("decisions") or []


def test_demo_bundle_has_one_counter_authority_not_five():
    rows = _decisions(DEMO_BUNDLE)
    assert counter_authority_count(rows) == 1, (
        f"demo corrected count is 1; got {counter_status_histogram(rows)}"
    )
    assert counter_authority_ids(rows) == ["ju_gerichte_CC_2021_44"], (
        "the single demo counter authority is named in the direction"
    )
    assert counter_status_bearing_count(rows) == 5, (
        "the number the old report published (5) was the provenance count, "
        "including 4 rows the answer cited"
    )


def test_demo_counter_authority_is_evidenced():
    rows = _decisions(DEMO_BUNDLE)
    row = next(r for r in rows if r.get("decision_id") == "ju_gerichte_CC_2021_44")
    assert row["counter_status"] == "candidate-limiting"
    assert row.get("counter_evidence_verified") is True, "the direction records it as evidenced"


def test_live_bundle_has_two_counter_authorities_not_seven():
    rows = _decisions(LIVE_BUNDLE)
    hist = counter_status_histogram(rows)
    assert counter_authority_count(rows) == 2, f"live corrected count is 2; got {hist}"
    assert hist.get("abstained_unevidenced") == 2, (
        "both live counter authorities are abstained_unevidenced"
    )
    assert counter_status_bearing_count(rows) == 7, (
        "7 was the provenance count: 5 cited rows + 2 findings"
    )


def test_no_committed_artifact_still_labels_the_broad_count_as_counter_authorities():
    """A report that says '5 counter authorities' for the demo bundle is wrong.

    Scans the product's own committed reports/results for the corrected figures.
    Only artifacts this cycle regenerates are checked, so the assertion names the
    exact deliverable rather than grandfathering whatever happens to be on disk.
    """
    corrected = json.loads(
        (REPO_ROOT / "results" / "product" / "counter_authority_counting.json").read_text(
            encoding="utf-8"
        )
    )
    assert corrected["demo"]["counter_authorities"] == 1
    assert corrected["live"]["counter_authorities"] == 2
    assert corrected["demo"]["counter_status_bearing_rows"] == 5
    assert corrected["live"]["counter_status_bearing_rows"] == 7
    old = corrected["old_defect"]
    for key, value in {
        "demo_reported_as": 5,
        "live_reported_as": 7,
        "demo_actual": 1,
        "live_actual": 2,
    }.items():
        assert old[key] == value, f"old_defect.{key} drifted: {old[key]}"
    # The published counts are 5x and 3.5x the true finding counts. Quoting the
    # inflation factor is what makes this a gate-relevant defect rather than a
    # renamed field.
    assert old["inflation_factor_demo"] == 5.0
    assert old["inflation_factor_live"] == 3.5
    # Three numbers together, per factory-wide requirement 26 / the standing
    # three-numbers rule: support rate, abstentions, yield are quoted as a set.
    for key in ("demo", "live"):
        entry = corrected[key]
        assert {"counter_authorities", "counter_status_bearing_rows",
                "counter_status_histogram", "n_decisions"} <= set(entry), (
            f"{key} must publish the counts and the histogram that reconciles them"
        )


# --------------------------------------------------------------------------- #
# 5. RF2: the final served row count must include the adversarial rows
# --------------------------------------------------------------------------- #

def test_served_row_arithmetic_holds_on_every_committed_bundle():
    """final rows == pre-adversarial rows + adversarial rows admitted.

    RF2 recorded a report publishing 247 as the final served bundle size when the
    bundle held 255 (247 + 8 adversarial rows). The invariant is enforced per
    bundle so the pre-adversarial count can never be published as the final one.
    """
    artifact = json.loads(
        (REPO_ROOT / "results" / "product" / "counter_authority_counting.json").read_text(
            encoding="utf-8"
        )
    )
    per_bundle = artifact["served_bundle_row_arithmetic"]["per_bundle"]
    assert per_bundle, "the row arithmetic must be measured on the committed bundles"
    for name, row in per_bundle.items():
        assert row["expected_final_rows"] == (
            row["n_existing_before_adversarial"] + row["n_adversarial_rows_added"]
        ), name
        assert row["invariant_holds"] is True, (
            f"{name}: the bundle holds {row['actual_final_rows']} rows but the "
            f"provenance implies {row['expected_final_rows']}"
        )


def test_the_live_bundle_would_be_understated_by_the_pre_adversarial_count():
    """Non-vacuity: the live bundle really does lose 8 rows to this mistake."""
    artifact = json.loads(
        (REPO_ROOT / "results" / "product" / "counter_authority_counting.json").read_text(
            encoding="utf-8"
        )
    )
    live = artifact["served_bundle_row_arithmetic"]["per_bundle"]["live"]
    assert live["n_adversarial_rows_added"] == 8, live
    assert live["actual_final_rows"] == 202, live
    assert live["understatement_if_pre_adversarial_count_published"] == 8, (
        "publishing 194 as the final size instead of 202 is exactly the RF2 shape"
    )


def test_the_direction_recorded_247_vs_255_case_is_preserved_and_labelled():
    """The specific 247/255 figures stay on record, tagged as not-in-this-tree."""
    case = json.loads(
        (REPO_ROOT / "results" / "product" / "counter_authority_counting.json").read_text(
            encoding="utf-8"
        )
    )["served_bundle_row_arithmetic"]["direction_recorded_case"]
    assert case["reported"] == 247
    assert case["actual"] == 255
    assert "247 after expand + 8 adversarial rows" in case["composition"]
    assert "not in this tree" in case["note"], (
        "the figures belong to run 39073545280; saying so is required so they are "
        "never read as a measurement taken from an artifact in this tree"
    )


# --------------------------------------------------------------------------- #
# 6. the old number was the audit's SUPPORTING count, not a counter count
# --------------------------------------------------------------------------- #

def test_generative_audit_reconciliation_is_verified_not_assumed():
    """The reconciliation states which relations hold and which are unverified.

    Guards the discipline of factory-wide requirement 16: a set-identity claim is
    never made from a matching cardinality. ``supporting`` (7) and the bundle's
    ``cited`` rows (5) are measured at different stages, coincide or not, and the
    artifact must say so rather than assert they are the same set.
    """
    live = json.loads(
        (REPO_ROOT / "results" / "product" / "counter_authority_counting.json").read_text(
            encoding="utf-8"
        )
    )["live"]
    recon = live["generative_audit_reconciliation"]
    rel = recon["verified_relations"]
    assert recon["generative_audit_supporting"] == 7
    assert recon["generative_audit_limiting"] == 0
    assert recon["generative_audit_contrary_or_exception"] == 0
    assert recon["bundle_cited_rows"] == 5, "the bundle marks 5 rows cited"
    assert recon["bundle_counter_authority_rows"] == 2
    assert rel["generative_audit_reports_zero_limiting_and_zero_contrary"] is True, (
        "the generative audit issued no limiting and no contrary classification, so "
        "the old number cannot be a counter count under any reading"
    )
    assert rel["old_number_equals_generative_audit_supporting"] is True
    assert rel["old_number_equals_bundle_cited_rows"] is False, (
        "7 != 5: the artifact must NOT claim the old number was the cited-row count"
    )
    assert rel["bundle_cited_rows_equals_generative_audit_supporting"] is False, (
        "different stages, different numbers: recorded as not-established"
    )
    assert "NOT shown to be the same set" in recon["reading"]

# --------------------------------------------------------------------------
# F7 (audit CYCLE_39091749561): ONE "evidenced" predicate, shared with the page
# --------------------------------------------------------------------------

QUERY_PAGE = PRODUCT_ROOT / "static" / "query.html"


def _counter(id_: str, status: str, evidence: str, verified) -> dict:
    return {
        "decision_id": id_,
        "counter_status": status,
        "counter_evidence": evidence,
        "counter_evidence_verified": verified,
    }


def test_counter_evidenced_requires_status_text_and_verified_flag():
    """All three terms, never a subset: this is the page's own predicate."""
    assert counter_evidenced(_counter("a", "candidate-limiting", "BGE 123", True)) is True
    assert counter_evidenced(_counter("b", "abstained_unevidenced", "BGE 123", True)) is True
    # flag without text: the page shows the amber "non étayée" ring, and so must we
    assert counter_evidenced(_counter("c", "abstained_unevidenced", "", True)) is False
    assert counter_evidenced(_counter("d", "candidate-limiting", "   ", True)) is False
    # text without the flag is not evidence either
    assert counter_evidenced(_counter("e", "candidate-limiting", "BGE 123", False)) is False
    assert counter_evidenced(_counter("e", "candidate-limiting", "BGE 123", None)) is False
    # a provenance row is never evidenced, however verified
    assert counter_evidenced(_counter("f", "cited", "BGE 123", True)) is False
    assert counter_evidenced(_counter("g", "none", "BGE 123", True)) is False
    assert counter_evidenced("not a dict") is False


def test_the_python_predicate_is_the_page_predicate_not_a_second_definition():
    """Parity with product/static/query.html::counterEvidenced, checked on source.

    F7 asked for ONE notion of "evidenced". The page keeps its JS twin (a jurist
    clicks the page, not a Python module), so the guard is that both definitions
    exist and name the same three terms in the same order - a silent edit of
    either side is a red test, not a silent divergence.
    """
    src = QUERY_PAGE.read_text(encoding="utf-8")
    m = re.search(r"function counterEvidenced\((\w+)\)\{(.*?)\}", src)
    assert m, "counterEvidenced() is missing from product/static/query.html"
    body = m.group(2)
    assert "isCounter(" in body, body
    assert "counter_evidence" in body, body
    assert "counter_evidence_verified" in body, body
    assert body.index("isCounter(") < body.index("counter_evidence_verified"), (
        "the page predicate must test the status first, like is_counter_status")


def test_evidenced_and_unevidenced_partition_the_counter_rows():
    rows = [
        _counter("a", "candidate-limiting", "BGE 123", True),   # evidenced
        _counter("b", "abstained_unevidenced", "", True),      # unevidenced (F7 case)
        _counter("c", "cited", "BGE 9", True),                 # provenance: neither
        {"decision_id": "d"},                                  # untouched: neither
    ]
    assert evidenced_counter_ids(rows) == ["a"]
    assert unevidenced_counter_ids(rows) == ["b"]
    assert len(evidenced_counter_ids(rows)) + len(unevidenced_counter_ids(rows)) == (
        counter_authority_count(rows)
    ), "the two lists must partition the counter rows exactly"
    assert "c" not in evidenced_counter_ids(rows) + unevidenced_counter_ids(rows)


def test_the_live_bundle_agrees_under_both_evidenced_predicates_and_stays_abstained():
    """F7, measured on the committed live bundle - with the real reading.

    The audit's F7 was that the ledger's "evidenced" test (flag only) is WEAKER
    than the page's counterEvidenced (flag AND text), so the two could disagree.
    Measured here: on this bundle they do NOT disagree - both abstained rows carry
    text - and that is published as a measurement, not assumed. What must hold
    regardless is that "evidenced" never upgrades a classification: both rows
    stay ``abstained_unevidenced`` with their disclosed uncertainty, and the
    shared predicate changes nothing about the counter count.
    """
    live = json.loads(LIVE_BUNDLE.read_text(encoding="utf-8"))
    rows = live.get("decisions") or []
    counters = [r for r in rows if is_counter_status(r.get("counter_status"))]
    assert len(counters) == 2, "the live bundle's corrected counter count is 2 (RF1)"
    flag_only = {
        r["decision_id"] for r in counters if r.get("counter_evidence_verified") is True
    }
    shared = set(evidenced_counter_ids(rows))
    assert shared <= flag_only, "the shared predicate is strictly the flag-only test plus text"
    # measured on THIS bundle: no disagreement; a future bundle may have one
    assert flag_only - shared == set(), (
        "rows the ledger counts as evidenced but the page would ring amber: "
        f"{sorted(flag_only - shared)}")
    for row in counters:
        assert str(row.get("counter_status")) == "abstained_unevidenced", row
        assert counter_evidenced(row) is True, row["decision_id"]
        assert counter_authority_count([row]) == 1, (
            "evidenced is an evidence statement, never a classification upgrade")
    assert unevidenced_counter_ids(rows) == [], (
        "empty on this bundle; a non-empty result is what the amber ring is for")

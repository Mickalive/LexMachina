"""RF2/RF4 guards: test accounting must be derived and commit-anchored.

Why this module exists
----------------------
Factory direction v56 ordered two defects that share one root cause: a number in a
report that the measurements do not support.

**RF2** - arithmetic. A report published net new passing tests of "+7" when the
measured change was "+10" (base 564 -> head 574). The delta disagreed with the two
counts it was derived from.

**RF4** - the pin. That report's supporting count was pinned to a *re-probed moving
snapshot* (21:30:00Z). By the time the independent audit of run 39073545280 read it,
the control plane's 22:24:12Z snapshot had already superseded it; the audit
recomputed 162 passed / 1 failed and the "163 passed / 13 passed (fixed)" claim was
falsified. The direction's rule: pin against a NAMED run id and commit, never a
moving snapshot, and if a pin cannot be made correct say so rather than repinning.

These guards test ``product/test_accounting.py``, the tool that replaces both
defects. They are written first as property tests on the tool's refusal paths,
because a tool whose refusals are untested will eventually be bypassed by simply
not calling it - in which case the same fabricated delta returns.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

PRODUCT_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = PRODUCT_ROOT.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from product import test_accounting as ta  # noqa: E402


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=REPO_ROOT, capture_output=True, text=True, check=False
    ).stdout.strip()


# --------------------------------------------------------------------------- #
# parsing: refuse rather than guess
# --------------------------------------------------------------------------- #

def test_parses_a_real_pytest_summary():
    log = (
        "..................\n"
        "45 failed, 562 passed, 2 skipped, 30 errors in 82.92s (0:01:22)\n"
    )
    got = ta.parse_pytest_summary(log)
    assert got["failed"] == 45
    assert got["passed"] == 562
    assert got["skipped"] == 2
    assert got["errors"] == 30
    assert got["total_collected"] == 639


def test_parses_a_summary_with_no_failures():
    got = ta.parse_pytest_summary("649 passed, 2 skipped in 91.4s (0:01:31)\n")
    assert got["passed"] == 649
    assert got["failed"] == 0
    assert got["total_collected"] == 651


def test_refuses_an_unparseable_log_instead_of_returning_zeros():
    """The zero-return is exactly how '+7' could be published against no data."""
    for bad in ("", "\n\n", "collected nothing at all\n", "!!!!!!! KeyboardInterrupt\n"):
        try:
            ta.parse_pytest_summary(bad)
        except SystemExit as exc:
            assert "could not parse" in str(exc) or "empty" in str(exc), str(exc)
        else:  # pragma: no cover - would be the defect
            raise AssertionError(f"unparseable log was accepted: {bad!r}")


# --------------------------------------------------------------------------- #
# deltas: derived, never asserted
# --------------------------------------------------------------------------- #

def test_delta_is_computed_not_supplied():
    base = {"failed": 45, "passed": 562, "skipped": 2, "errors": 30}
    head = {"failed": 45, "passed": 591, "skipped": 2, "errors": 30}
    d = ta.compute_delta(base, head)
    assert d["net_new_passing_tests"] == 29, "must be head.passed - baseline.passed"
    assert d["net_new_failing_tests"] == 0
    assert d["net_change_in_collected"] == 29
    assert d["per_outcome"]["passed"] == 29


def test_delta_reproduces_the_rf2_direction_case():
    """RF2's own numbers: base 564 -> head 574 is +10, not the published +7."""
    d = ta.compute_delta(
        {"failed": 0, "passed": 564, "skipped": 0, "errors": 0},
        {"failed": 0, "passed": 574, "skipped": 0, "errors": 0},
    )
    assert d["net_new_passing_tests"] == 10
    assert d["net_new_passing_tests"] != 7, (
        "the published '+7' is what RF2 ordered corrected; the tool must produce 10"
    )


def test_delta_is_signed_so_a_regression_cannot_read_as_a_gain():
    d = ta.compute_delta(
        {"failed": 10, "passed": 500, "skipped": 0, "errors": 0},
        {"failed": 12, "passed": 498, "skipped": 0, "errors": 0},
    )
    assert d["net_new_passing_tests"] == -2
    assert d["net_new_failing_tests"] == 2


# --------------------------------------------------------------------------- #
# pins: a named run and a commit, never a timestamp
# --------------------------------------------------------------------------- #

def test_pin_requires_a_named_run_id():
    """A moving snapshot is not a pin; 'local' / 'now' is how the rot started."""
    for bad in ("local", "now", "none", "unknown", "", None):
        try:
            ta._require_anchor(bad, "0" * 40, "baseline")
        except SystemExit as exc:
            assert "NAMED run id" in str(exc), str(exc)
        else:  # pragma: no cover
            raise AssertionError(f"an unnamed run id was accepted: {bad!r}")


def test_pin_requires_a_resolvable_commit():
    for bad in ("", None, "latest", "HEAD~1", "main", "2026-10-17T21:30:00Z", "123"):
        try:
            ta._require_anchor("39082232157", bad, "baseline")
        except SystemExit as exc:
            assert "commit" in str(exc), str(exc)
        else:  # pragma: no cover
            raise AssertionError(f"a non-commit pin was accepted: {bad!r}")


def test_pin_rejects_a_timestamp_even_though_it_looks_like_a_pin():
    """RF4's exact failure: 21:30:00Z looks authoritative and pins nothing."""
    try:
        ta._require_anchor("39073545280", "2026-10-17T21:30:00Z", "baseline")
    except SystemExit as exc:
        assert "commit" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("a timestamp was accepted as a commit pin")


def test_pin_accepts_a_real_run_and_commit():
    got = ta._require_anchor("39082232157", "03a4cabb72df5cb38b5228c65ca9fb3fd1a04974", "baseline")
    assert got["run_id"] == "39082232157"
    assert got["commit"].startswith("03a4cab")


def test_baseline_and_head_must_not_pin_to_the_same_commit():
    """A delta between one tree is always 0; publishing it fabricates a result."""
    head = _git("rev-parse", "HEAD")
    argv = [
        "--baseline-run-id", "1", "--baseline-commit", head,
        "--baseline-file", "/dev/null",
        "--head-run-id", "2", "--head-file", "/dev/null",
    ]
    try:
        ta.main(argv)
    except SystemExit as exc:
        assert "SAME commit" in str(exc), str(exc)
    else:  # pragma: no cover
        raise AssertionError("a zero-delta measurement was published")


def test_baseline_must_be_an_ancestor_of_head():
    """Comparing unrelated trees makes the delta meaningless."""
    try:
        ta.main([
            "--baseline-run-id", "1", "--baseline-commit", "0" * 40,
            "--baseline-file", "/dev/null",
            "--head-run-id", "2", "--head-file", "/dev/null",
        ])
    except SystemExit as exc:
        assert "not an ancestor" in str(exc) or "could not parse" in str(exc), str(exc)
    else:  # pragma: no cover
        raise AssertionError("a delta between unrelated trees was allowed")


def test_head_measurement_is_required():
    """No --head-file: there is no delta, so the tool refuses before pinning.

    The precondition is checked first on purpose - a caller who forgot the head
    measurement must be told that, not a confusing pin error about two commits.
    """
    try:
        ta.main([
            "--baseline-run-id", "1",
            "--baseline-commit", _git("rev-parse", "HEAD"),
            "--baseline-file", "/dev/null",
        ])
    except SystemExit as exc:
        assert "--head-file" in str(exc), str(exc)
    else:  # pragma: no cover
        raise AssertionError("a delta was published with no head measurement")


def test_baseline_measurement_is_required_too():
    try:
        ta.main([
            "--baseline-run-id", "1",
            "--baseline-commit", _git("rev-parse", "HEAD"),
            "--head-file", "/dev/null",
        ])
    except SystemExit as exc:
        assert "--baseline-file" in str(exc), str(exc)
    else:  # pragma: no cover
        raise AssertionError("a delta was published with no baseline measurement")


def test_the_missing_measurement_check_precedes_the_pin_check():
    """Ordering is load-bearing: the real error must be the one reported."""
    try:
        ta.main([
            "--baseline-run-id", "local",           # would fail the pin check
            "--baseline-commit", "not-a-commit",    # would fail the pin check
            "--baseline-file", "/dev/null",
        ])
    except SystemExit as exc:
        message = str(exc)
        assert "--head-file" in message, message
        assert "NAMED run id" not in message, (
            "the missing-measurement precondition must be reported before the "
            f"pin problem, got: {message}"
        )


# --------------------------------------------------------------------------- #
# the committed artifact
# --------------------------------------------------------------------------- #

ACCOUNTING = REPO_ROOT / "results" / "product" / "regression" / "test_accounting.json"


def test_committed_accounting_is_commit_anchored():
    """If an artifact exists, it must name two commits and they must be related."""
    if not ACCOUNTING.exists():
        return  # no measurement taken in this environment; nothing to assert
    art = json.loads(ACCOUNTING.read_text(encoding="utf-8"))
    for key in ("baseline", "head"):
        assert art[key]["commit"], f"{key} has no commit pin"
        assert re.fullmatch(r"[0-9a-f]{7,40}", art[key]["commit"]), art[key]["commit"]
        assert art[key]["run_id"], f"{key} has no named run id"
    assert art["baseline"]["commit"] != art["head"]["commit"]
    assert "timestamp" in art["pinning_rule"].lower()


def test_committed_accounting_deltas_agree_with_their_own_counts():
    """The RF2 guard, applied to the real artifact: no hand-written delta."""
    if not ACCOUNTING.exists():
        return
    art = json.loads(ACCOUNTING.read_text(encoding="utf-8"))
    for key in ("failed", "passed", "skipped", "errors"):
        expected = art["head"][key] - art["baseline"][key]
        assert art["delta"]["per_outcome"][key] == expected, (
            f"delta.{key} disagrees with the two counts it is derived from"
        )
    assert art["delta"]["net_new_passing_tests"] == (
        art["head"]["passed"] - art["baseline"]["passed"]
    )


def test_the_excluded_module_set_is_named_not_implied():
    """A silent change of the excluded set invalidates the whole comparison."""
    if not ACCOUNTING.exists():
        return
    scope = json.loads(ACCOUNTING.read_text(encoding="utf-8"))["collection_scope"]
    listed = scope["uncollectable_modules_excluded"]
    assert listed, "the excluded modules must be listed by name, not implied"
    assert scope["n_uncollectable_modules"] == len(listed)
    assert all(m.endswith(".py") for m in listed), listed
"""The collected-test delta decomposition is MEASURED, and the measurement is checked.

Why this exists
---------------
Audit RF-1 of rejected cycle 39144924680: ``reports/product/
CYCLE_39144924680_REPAIR4.md`` §4 decomposed its own ``+21`` collected-test delta
as ``+17 (the predecessor cycle) + +4 (this cycle)``. The predecessor cycle
39139648336 contributed **0** - it touched no file under ``product/tests/`` at
all. The +17 belongs to the three commits of cycle 39128456801 (``db3891e``
+11, ``c1bda4a`` +2, ``9bfd03f`` +4).

That was the third recurrence of one defect class in this repair chain (6 -> 5
cited, 13 -> 17 tests, "+7 tests" against a measured +10): a number typed into
prose instead of derived from the measurement it summarises. The audit's
terminal condition for round 5 says what to do about the third one: route the
loop to a structural remedy rather than open a sixth round. So the decomposition
is now produced by ``product/test_delta_attribution.py`` and the report quotes
its output verbatim; this module is what keeps that from rotting.

What is checked here
--------------------
* the committed artifact's arithmetic closes (step deltas sum to the total);
* its BASE total is corroborated by the committed regression-scope artifact,
  which measured the same named commit with a full suite run;
* the artifact's HEAD total still equals what THIS tree collects - the staleness
  detector, so a later cycle that adds tests is told to regenerate rather than
  to keep quoting a number that has stopped being true;
* the false-attribution target is machine-pinned: no step is the rejected cycle
  39139648336's head commit, because that commit touched no test module;
* the canonical sentence is derived by git, not hard-coded, and the tool REFUSES
  to publish an attribution whose steps do not close (proven against a synthetic
  repository, not asserted).

Deliberately NOT claimed: nothing about pass/fail (this tool runs collection
only), nothing about any frozen bar, nothing about any other environment or root.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from product import test_delta_attribution as tda  # noqa: E402

#: The attribution this cycle commits. Named by file, not "newest", because it
#: is the artifact a report quotes: a later cycle that regenerates it must not
#: silently change what an older report says.
#:
#: PIN REPOINT, recorded twice, both kept here because a pin move with no
#: recorded reason is indistinguishable from an unexplained edit:
#:
#: 1. (operational resume run 39169296466, base commit 4acd595) the pin
#:    previously named ``CYCLE_39149741259_test_delta_attribution.json``, whose
#:    ``working_tree.collected_total`` (1169) is the tree of that cycle. That
#:    resume re-applied the accepted Evaluation handoff disclosure together with
#:    ``product/tests/test_query_concept_disclosure.py`` (+5 collected).
#: 2. (repair round 1 of rejected cycle 39169296466, run 39172315384) the pin
#:    named ``CYCLE_39169296466_test_delta_attribution.json``, whose
#:    ``working_tree.collected_total`` (1175) is that cycle's tree. This repair
#:    adds 16 collected tests - 6 ledger controls in ``test_cycle_verify_is_a_gate``,
#:    2 preservation/currency guards in this module's sibling
#:    ``test_report_artifact_arithmetic``, and 8 register-retention tests in the
#:    new ``test_state_register_retention`` - so the staleness detector below
#:    must measure against the artifact of THIS tree. Leaving the old pin would
#:    have shipped a SECOND red committed guard, which is exactly audit F1 of
#:    CYCLE_39169296466_GATE.json on this module's sibling.
#:
#: 3. (served-slice cycle 39202428670, run 39202428670) the pin STILL named
#:    ``CYCLE_39172315384_test_delta_attribution.json`` (``working_tree`` 1191)
#:    while the accepted tip collected 1217 - three later cycles
#:    (39185124744, 39193356789, 39199428702) regenerated an attribution for the
#:    lane ONE-COMMAND ledger, which reads the NEWEST artifact
#:    (``product/cycle_verify.py::check_test_delta_attribution`` uses
#:    ``candidates[-1]``), and therefore never noticed that THIS pytest pin had
#:    been left behind. Measured on the accepted tip ``577efeb`` before this
#:    cycle: ``test_working_tree_total_still_equals_what_this_tree_collects``
#:    FAILED with "this tree collects 1217 tests but the committed attribution
#:    says 1191". The pin is moved to this cycle's regenerated artifact, which is
#:    measured with the same base commit and cross-checked against the same
#:    regression-scope artifact; the stale measurement stays on disk untouched.
#:
#: Each time the independent auditor named the same remedy (audit
#: CYCLE_39160624523_GATE.json D1): regenerate the attribution for the new tree
#: and repoint the pin with a recorded reason. The old artifacts are neither
#: deleted nor rewritten; only which artifact THIS module checks moves.
#:
#: REPOINT RECORD (cycle 39262796670): the working tree gained 17 tests
#: (``product/tests/test_concept_seed.py``, the NLCS-1 concept-seed arm
#: integration), so the pin moved from CYCLE_39202428670 to this cycle's
#: regenerated artifact CYCLE_39262796670 (base 9727a45, head 3e18eb7, working
#: tree 1242 collected, delta +17 uncommitted). The prior artifact was already
#: stale by one collected test on the accepted tip; the regeneration closes both.
#: The old artifact stays on disk untouched.
#:
#: REPOINT RECORD (cycle 39357593249): the working tree gained 5 tests
#: (``product/tests/test_serve_verdict_intake.py``, the BOUNDED-NEGATIVE /
#: SERVE-CHANGED / DO-NOT-SERVE-AS-IS verdict-taxonomy arm), so the pin moved
#: from CYCLE_39262796670 to this cycle's regenerated artifact
#: CYCLE_39357593249 (base 9727a45, head 53659e6, working tree 1273 collected,
#: delta +5 uncommitted). The old artifact stays on disk untouched.
#:
#: REPOINT RECORD (cycle 39384462218): the working tree gained 4 tests
#: (``product/tests/test_served_page_integration.py``, the page<->server seam:
#: the shipped ``query.html`` driving the shipped server over a real socket),
#: so the pin moved from CYCLE_39357593249 to this cycle's regenerated
#: artifact CYCLE_39384462218 (base 9727a45, head 1ee024c2, working tree 1277
#: collected, delta +0 uncommitted). The old artifact stays on disk untouched.
#:
#: REPOINT RECORD (cycle 39538762904): the working tree gained 29 tests that the
#: pin CYCLE_39384462218 (working-tree total 1277) no longer measured - the
#: counter-instability disclosure cycle 39422322667 (``5c0b2e3``, +16) and the
#: frontier-counter-label-emission harvest cycle 3943548421 (``651b5c9``, +13)
#: both touched ``product/tests/``. Measured live this cycle:
#: ``tda.collect_count(ROOT)`` returned 1306 against the pin's 1277, so the
#: staleness detector below was RED on the very tree that shipped. The pin moves
#: to this cycle's regenerated artifact CYCLE_39538762904 (base 9727a45, head
#: c3ad235, working tree 1306 collected, delta +0 uncommitted). The old artifact
#: stays on disk byte-identical and joins ATTRIBUTION_HISTORY.
#:
#: REPOINT RECORD (cycle 39651573572, operational resume): the accepted tree
#: shipped a pin that no longer named the artifact its own guard asserted. The
#: pin read CYCLE_39538762904, ATTRIBUTION_PREVIOUS_PIN still read
#: CYCLE_39384462218, and the preservation test below still asserted the
#: CYCLE_39357593249 numbers (head 53659e6, working tree 1273) - so the
#: history guard was RED on the accepted tip, and the staleness detector was
#: RED too: this tree collects 1312 tests against the pin's 1306. Measured live
#: this cycle: ``tda.collect_count(ROOT)`` returned 1312, and the regeneration
#: attributes the +6 to this cycle's own commit ``fe30b0da6``
#: (``product/tests/test_server_query_api.py``, the shipped-launch-command
#: query-API guard). The pin moves to this cycle's regenerated artifact
#: CYCLE_39651573572 (base 9727a45, head fe30b0da6, working tree 1312
#: collected, delta +0 uncommitted). ATTRIBUTION_PREVIOUS_PIN moves with it, to
#: CYCLE_39538762904 (head c3ad235, working tree 1306), so the history guard
#: checks the artifact that really was the previous pin. Every older artifact
#: stays on disk byte-identical and joins ATTRIBUTION_HISTORY.
#:
#: REPOINT RECORD (cycle 39674781875, repair round 1): the working tree gained
#: 49 collected tests that the pin CYCLE_39651573572 (working-tree total 1312)
#: no longer measured - this cycle's own repair added 30 (the cache-rewrite
#: attribution guard, the register-merge guard and the cycle-claims guard) and
#: the accepted tip carried 19 more that the accepted pin never regenerated for
#: (the Frontier-intake and the served-page modules). Measured live this cycle:
#: ``tda.collect_count(ROOT)`` returned 1361 against the pin's 1312, so the
#: staleness detector below was RED on the very tree that shipped. The pin
#: moves to this cycle's regenerated artifact CYCLE_39674781875 (base 9727a45,
#: head dc924cd, working tree 1361 collected, delta +0 uncommitted). The
#: regeneration attributes +18 to the accepted commit 3f94e0e, +1 to the
#: rejected cycle's repair commit e9ac94e and +30 to this cycle's own repair
#: commit dc924cd. ATTRIBUTION_PREVIOUS_PIN moves with it, to
#: CYCLE_39651573572 (head fe30b0da6, working tree 1312), so the history guard
#: checks the artifact that really was the previous pin. Every older artifact
#: stays on disk byte-identical and joins ATTRIBUTION_HISTORY.
#: REPOINT RECORD (cycle 39689729561, operational resume): the inherited
#: artifact this pin named carried cross_check NOT_RUN - it had never been
#: corroborated against the independent full-run regression artifact - and the
#: tree it measured was 12 collected tests short of this one (the new
#: cycle-claims guard, product/tests/test_state_cycle_39689729561.py). Measured
#: live this cycle: ``tda.collect_count(ROOT)`` returned 1373 against the pin's
#: 1361, and the pinned artifact's own cross_check read "NOT_RUN", so the
#: staleness detector below and the corroboration check were both RED on the
#: tree this cycle inherited. The pin moves to this cycle's regenerated
#: artifact CYCLE_39689729561 (base 9727a45, head eb3fb98, working tree 1373
#: collected, delta +0 uncommitted, cross_check COMPARED with base_agrees
#: true). The regeneration attributes +0 to the inherited pin move (90d6283)
#: and +12 to this cycle's own commit eb3fb98. ATTRIBUTION_PREVIOUS_PIN moves
#: with it, to CYCLE_39674781875 (head dc924cd, working tree 1361), so the
#: history guard checks the artifact that really was the previous pin. Every
#: older artifact stays on disk byte-identical and joins ATTRIBUTION_HISTORY.
#:
#: REPOINT RECORD (cycle 39758711075, operational resume of snapshot 39752638579):
#: the inherited snapshot commit 3b9d33b added test_query_text_coverage.py and
#: extended test_adversarial_retrieval.py (+20 collected) and this resume adds
#: the D4 regression tests and the cycle-claims module (+17 collected), while
#: the pin still named CYCLE_39689729561 (working-tree total 1373). Measured
#: live this cycle: ``tda.collect_count(ROOT)`` returned 1413 against the pin's
#: 1373, so the staleness detector was RED on the tree this cycle ships - the
#: exact defect (D3) the resume diagnosis records. The pin moves to this
#: cycle's regenerated artifact CYCLE_39758711075 (base 9727a45, head WORKTREE,
#: working tree 1413 collected). ATTRIBUTION_PREVIOUS_PIN moves with it, to
#: CYCLE_39689729561 (head eb3fb98, working tree 1373), so the history guard
#: checks the artifact that really was the previous pin. Every older artifact
#: stays on disk byte-identical and joins ATTRIBUTION_HISTORY.
#: ARTIFACT LANDING RECORD (repair round 1 of rejected cycle 39764730877, run
#: 39764730877): the pin above MOVED in cycle 39758711075, but the artifact it
#: moved to was never committed. Audit F1 of CYCLE_39764730877_GATE.json: the
#: path ``CYCLE_39758711075_test_delta_attribution.json`` did not exist in the
#: producer workspace and ``git log --all --`` on it was empty, while this
#: module and ``state/product.json`` both named it - so 21 committed guards
#: were red on an artifact that no run had ever written. This is a pin move
#: with the measurement left behind, exactly the shape the REPOINT records
#: above exist to prevent. It is closed here by LANDing the missing artifact
#: rather than re-pointing the pin: ``python3 product/test_delta_attribution.py
#: --base 9727a45 --run-id 39758711075 --regression-artifact
#: results/product/regression/CYCLE_39144924680_regression_scope.json --out
#: results/product/regression/CYCLE_39758711075_test_delta_attribution.json``
#: measured base ``9727a45`` -> head ``f2dfca6`` -> the working tree of the
#: repair of run 39764730877, and the pin, the run id and every historical
#: artifact stay exactly where they were. The rule this records: a pin may
#: only move together with the bytes it names, and a missing named artifact is
#: repaired by producing it from the measurement tool - never by deleting the
#: check.
#:
#: TWO artifacts, and why both exist. The artifact named for run 39758711075 is
#: the one this pin and ``product/tests/test_state_cycle_39758711075.py`` read,
#: so it must carry that run's id AND measure the CURRENT tree (both are
#: committed guards, and neither may be relaxed to make a file name tidy). Its
#: own ``head`` field names the range endpoint it measured and its
#: ``working_tree`` field names the tree it measured, so the artifact is
#: self-describing; the report of record for run 39764730877 discloses that it
#: was (re)generated in this repair round because the pin had moved without its
#: bytes. The artifact named for THIS round,
#: ``CYCLE_39764730877_test_delta_attribution.json``, is the same measurement
#: under this round's own run id, so that a file named for a run holds that
#: run's measurement. Both are committed; neither replaces the other; the
#: older one is never rewritten again.
ATTRIBUTION = (ROOT / "results" / "product" / "regression"
               / "CYCLE_39758711075_test_delta_attribution.json")
#: The previous pin, kept as a readable constant so a reader can diff the two
#: artifacts instead of trusting prose about them.
ATTRIBUTION_PREVIOUS_PIN = (ROOT / "results" / "product" / "regression"
                             / "CYCLE_39689729561_test_delta_attribution.json")
#: Every attribution artifact this pin has ever named, oldest first, each of
#: which must still exist. A pin move moves a CHECK; it never removes evidence.
#: The newest entry is the pin this module currently reads.
ATTRIBUTION_HISTORY = (
    ROOT / "results" / "product" / "regression"
    / "CYCLE_39172315384_test_delta_attribution.json",
    ROOT / "results" / "product" / "regression"
    / "CYCLE_39262796670_test_delta_attribution.json",
    ROOT / "results" / "product" / "regression"
    / "CYCLE_39357593249_test_delta_attribution.json",
    ROOT / "results" / "product" / "regression"
    / "CYCLE_39384462218_test_delta_attribution.json",
    ROOT / "results" / "product" / "regression"
    / "CYCLE_39538762904_test_delta_attribution.json",
    ROOT / "results" / "product" / "regression"
    / "CYCLE_39651573572_test_delta_attribution.json",
    ROOT / "results" / "product" / "regression"
    / "CYCLE_39674781875_test_delta_attribution.json",
    ROOT / "results" / "product" / "regression"
    / "CYCLE_39689729561_test_delta_attribution.json",
    ROOT / "results" / "product" / "regression"
    / "CYCLE_39758711075_test_delta_attribution.json",
    ROOT / "results" / "product" / "regression"
    / "CYCLE_39764730877_test_delta_attribution.json",
)
#: The full-run regression measurement whose base is the SAME named commit. An
#: independent measurement path (full run, not collection-only) of the same tree.
REGRESSION = (ROOT / "results" / "product" / "regression"
              / "CYCLE_39144924680_regression_scope.json")
#: The rejected cycle whose head commit touched no test module, and which the
#: round-4 report wrongly credited with +17.
REJECTED_CYCLE_HEAD = "2b0b902"


def _artifact() -> dict:
    assert ATTRIBUTION.exists(), f"missing attribution artifact {ATTRIBUTION}"
    return json.loads(ATTRIBUTION.read_text(encoding="utf-8"))


def test_committed_attribution_arithmetic_closes():
    art = _artifact()
    steps = art["steps"]
    assert steps, "an attribution with no steps attributes the delta to nobody"
    total = sum(s["collected_delta_vs_previous_step"] for s in steps)
    assert total == art["observed_collected_delta"], (
        f"per-step deltas sum to {total} but the observed total delta is "
        f"{art['observed_collected_delta']} - the tool refuses to publish this")
    assert art["reconciles"] is True
    assert art["head"]["collected_total"] - art["base"]["collected_total"] == total


def test_head_total_is_corroborated_by_the_full_run_regression_artifact():
    """Two different measurement paths, one named BASE tree, same collected count.

    What must agree forever is the BASE: one named commit, measured once by a
    full suite run (the regression-scope artifact) and once by collection-only
    (this tool).  What is allowed to differ is the HEAD: the regression artifact
    measured the tree of its own cycle, this attribution measures the tree of the
    cycle that regenerated it, and the cross-check's own ``note`` states that a
    head disagreement is expected exactly when tests were added in between.
    Asserting head equality here would assert that no cycle may add a test, so
    the head is pinned to the artifact's own range endpoint and checked for
    ancestry instead (pin move recorded at the ATTRIBUTION constant).
    """
    art = _artifact()
    reg = json.loads(REGRESSION.read_text(encoding="utf-8"))
    assert art["cross_check"]["status"] == "COMPARED"
    assert art["cross_check"]["artifact_collected_baseline"] == reg["baseline_run"]["collected"], (
        "the attribution cross-check does not read the regression artifact it names")
    assert art["cross_check"]["base_agrees"] is True, (
        f"base collected disagrees: tool {art['cross_check']['tool_collected_base']} "
        f"vs full-run artifact {art['cross_check']['artifact_collected_baseline']} - "
        "one of them measured something else; re-derive before publishing")
    head = art["head"]["commit"]
    assert head and len(head) >= 7, "the attribution must name its range-endpoint commit"
    ancestry = subprocess.run(  # noqa: S603
        ["git", "merge-base", "--is-ancestor", head, "HEAD"],
        cwd=str(ROOT), capture_output=True, text=True, check=False)
    assert ancestry.returncode == 0, (
        f"the attribution's head {head} is not an ancestor of this branch's HEAD, "
        "so it did not measure a tree this lane shipped")
    if art["cross_check"]["head_agrees"] is not True:
        # Expected exactly when this cycle added tests after the regression
        # artifact's tree. It must be the documented case, never silence.
        assert "expected exactly when" in str(art["cross_check"].get("note") or ""), (
            "head_agrees is false but the cross-check carries no documented "
            "reason for the drift; re-derive rather than publish an unexplained "
            "disagreement")


def test_the_previous_pin_artifact_is_preserved_as_history():
    """The re-pointed pin moves a CHECK, never a piece of evidence.

    ``CYCLE_39689729561_test_delta_attribution.json`` is the artifact the pin
    named before this cycle's move (working-tree total 1373, head eb3fb98).
    The artifact before it, ``CYCLE_39651573572_test_delta_attribution.json``
    (working-tree total 1312, head fe30b0da6), the one before that,
    ``CYCLE_39538762904_test_delta_attribution.json`` (working-tree total 1306,
    head c3ad235), the one before that,
    ``CYCLE_39384462218_test_delta_attribution.json`` (working-tree total 1277,
    head 1ee024c2), the one before that,
    ``CYCLE_39357593249_test_delta_attribution.json`` (working-tree total 1273,
    head 53659e6), ``CYCLE_39262796670_test_delta_attribution.json`` (working-tree
    total 1242, head 3e18eb7) and the oldest,
    ``CYCLE_39172315384_test_delta_attribution.json`` (working-tree total 1191,
    head 2d8768e), are still on disk too: the pin has now moved eight times and
    no move may remove a measurement. Repointing ATTRIBUTION must not delete or
    rewrite any of them; the reason the pin moved is recorded at the constant,
    and the old numbers stay readable so a reader can compare the artifacts
    instead of trusting prose about them.

    AUDIT F2b of rejected cycle 39764730877 charged this guard as a STALE
    PIN: the inherited commit moved ``ATTRIBUTION_PREVIOUS_PIN`` forward to
    ``CYCLE_39689729561_test_delta_attribution.json`` but left the assertions
    below on the PREVIOUS artifact's numbers (head dc924cd / working-tree total
    1361, which are ``CYCLE_39674781875``'s), so the guard was red on its own
    named artifact. Refreshed, not relaxed: the assertions now name the
    artifact the constant actually points at, the whole history chain is still
    walked, and every historical measurement is still required to be on disk
    and byte-stable.
    """
    assert ATTRIBUTION_PREVIOUS_PIN.exists(), (
        "the historical attribution artifact the previous pin named is gone - "
        "a pin move must never remove evidence")
    assert ATTRIBUTION_PREVIOUS_PIN.name == "CYCLE_39689729561_test_delta_attribution.json", (
        f"the previous pin points at {ATTRIBUTION_PREVIOUS_PIN.name}; this guard's "
        "recorded numbers belong to a different artifact")
    old = json.loads(ATTRIBUTION_PREVIOUS_PIN.read_text(encoding="utf-8"))
    assert old["head"]["commit"].startswith("eb3fb98"), (
        f"the historical artifact no longer records the tree it was published "
        f"for (head {old['head']['commit'][:7]})")
    assert old["working_tree"]["collected_total"] == 1373, (
        "the historical artifact's working-tree total was edited; a re-pointed "
        "pin must leave the previous measurement byte-stable")
    prior_pin = (ROOT / "results" / "product" / "regression"
                 / "CYCLE_39674781875_test_delta_attribution.json")
    assert prior_pin.exists(), (
        "the artifact the pin named BEFORE the previous move is gone; nine pin "
        "moves must have preserved every historical measurement")
    prior = json.loads(prior_pin.read_text(encoding="utf-8"))
    assert prior["head"]["commit"].startswith("dc924cd")
    assert prior["working_tree"]["collected_total"] == 1361
    prior_pin = (ROOT / "results" / "product" / "regression"
                 / "CYCLE_39651573572_test_delta_attribution.json")
    assert prior_pin.exists(), (
        "the artifact the pin named BEFORE the last move is gone; seven pin moves "
        "must have preserved every historical measurement")
    prior = json.loads(prior_pin.read_text(encoding="utf-8"))
    assert prior["head"]["commit"].startswith("fe30b0d")
    assert prior["working_tree"]["collected_total"] == 1312
    prior_pin = (ROOT / "results" / "product" / "regression"
                 / "CYCLE_39538762904_test_delta_attribution.json")
    assert prior_pin.exists(), (
        "the artifact the pin named BEFORE the last move is gone; six pin moves "
        "must have preserved every historical measurement")
    prior = json.loads(prior_pin.read_text(encoding="utf-8"))
    assert prior["head"]["commit"].startswith("c3ad235")
    assert prior["working_tree"]["collected_total"] == 1306
    grand = (ROOT / "results" / "product" / "regression"
             / "CYCLE_39262796670_test_delta_attribution.json")
    assert grand.exists(), (
        "the artifact the pin named BEFORE the last move is gone; five pin moves "
        "must have preserved every historical measurement")
    prior = json.loads(grand.read_text(encoding="utf-8"))
    assert prior["head"]["commit"].startswith("3e18eb7")
    assert prior["working_tree"]["collected_total"] == 1242
    great = (ROOT / "results" / "product" / "regression"
             / "CYCLE_39172315384_test_delta_attribution.json")
    assert great.exists(), (
        "the artifact the pin named two moves ago is gone; it is evidence too")
    oldest = json.loads(great.read_text(encoding="utf-8"))
    assert oldest["head"]["commit"].startswith("2d8768e")
    assert oldest["working_tree"]["collected_total"] == 1191


def test_working_tree_total_still_equals_what_this_tree_collects():
    """Staleness detector: a tree that grew tests must regenerate the artifact.

    Measured live (collection only, ~2s). If this fails, the honest fix is to
    re-run ``product/test_delta_attribution.py`` on the new tree - never to
    restate the old number.
    """
    art = _artifact()
    tree = art["working_tree"]
    assert tree["measured"] is True
    measured = tda.collect_count(ROOT)
    assert measured == tree["collected_total"], (
        f"this tree collects {measured} tests but the committed attribution says "
        f"{tree['collected_total']}; regenerate with "
        "`python3 product/test_delta_attribution.py --base "
        f"{art['base']['commit'][:7]} --run-id <id> "
        "--out results/product/regression/CYCLE_<id>_test_delta_attribution.json`")
    assert tree["reconciles"] is True, (
        "the working-tree delta is not attributable to its untracked new modules "
        f"({tree}); re-derive rather than restate")


def test_committed_range_and_working_tree_are_kept_apart():
    """A cycle's in-flight tests never enter a committed range's arithmetic."""
    art = _artifact()
    tree = art["working_tree"]
    assert tree["head_commit"] == art["head"]["commit"], (
        "the working tree is measured over a different commit than the range endpoint")
    assert tree["head_collected_total"] == art["head"]["collected_total"]
    assert art["observed_collected_delta"] == (
        art["head"]["collected_total"] - art["base"]["collected_total"])
    assert tree["collected_total"] >= tree["head_collected_total"]


def test_rejected_cycle_39139648336_is_pinned_as_contributing_no_step():
    """RF-1's target, pinned as an executable fact.

    The round-4 report credited +17 to the rejected cycle 39139648336. Its head
    commit touched no file under product/tests/, so it cannot be a step. If a
    future commit makes it one, this assertion is the thing that fires first.
    """
    art = _artifact()
    shorts = {s["short"] for s in art["steps"]}
    assert REJECTED_CYCLE_HEAD not in shorts, (
        f"{REJECTED_CYCLE_HEAD} is credited with a collected-count delta it did "
        "not produce - re-derive the attribution")
    touched = subprocess.run(  # noqa: S603
        ["git", "show", "--name-only", "--format=", REJECTED_CYCLE_HEAD],
        cwd=str(ROOT), capture_output=True, text=True, check=False)
    assert "product/tests/" not in touched.stdout, (
        "the premise of this assertion moved: the rejected cycle's head commit "
        "now touches product/tests/, so the attribution must be re-derived")


def test_attribution_is_derived_from_git_not_hard_coded():
    """Every step names the test modules git says it added or modified."""
    art = _artifact()
    for step in art["steps"]:
        touched = subprocess.run(  # noqa: S603
            ["git", "show", "--name-only", "--format=", step["commit"]],
            cwd=str(ROOT), capture_output=True, text=True, check=False)
        assert "product/tests/" in touched.stdout, (
            f"step {step['short']} is credited with a collected-count delta but "
            "touches no test module")
        assert step["modules_added"] or step["modules_modified"]
    assert art["method"]["step_selection"].startswith("git log --reverse")


def _synthetic_repo(tmp_path: Path, *, unattributable: bool) -> Path:
    """A minimal repo with one test module and a second commit adding another.

    ``unattributable=True`` then edits a tracked CONFTEST in the working tree so the
    tree collects a test that no changed test module accounts for - the situation
    the tool must refuse to explain away. ``False`` adds a new UNTRACKED module,
    which does reconcile and must publish.
    """
    repo = tmp_path / "synthetic"
    (repo / "product" / "tests").mkdir(parents=True)
    env = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
           "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t",
           "PATH": "/usr/bin:/bin:/usr/local/bin"}

    def git(*args: str) -> str:
        return subprocess.run(["git", *args], cwd=str(repo), check=True,
                              capture_output=True, text=True, env=env).stdout

    git("init", "-q", "-b", "main")
    (repo / "product" / "tests" / "test_a.py").write_text(
        "def test_one():\n    assert True\n", encoding="utf-8")
    git("add", "-A")
    git("commit", "-qm", "base")
    (repo / "product" / "tests" / "test_b.py").write_text(
        "def test_two():\n    assert True\n", encoding="utf-8")
    if unattributable:
        # A tracked conftest that gains a parametrisation hook in the working
        # tree: collection moves, and no test MODULE changed.
        (repo / "product" / "tests" / "conftest.py").write_text(
            "# committed, inert\n", encoding="utf-8")
        git("add", "-A")
        git("commit", "-qm", "inert conftest")
        # ...and the working-tree conftest stops collecting one of them. No test
        # MODULE changed, so nothing in the test tree accounts for the movement.
        (repo / "product" / "tests" / "conftest.py").write_text(
            "collect_ignore_glob = ['test_b.py']\n", encoding="utf-8")
    else:
        git("add", "-A")
        git("commit", "-qm", "adds a module")
        (repo / "product" / "tests" / "test_c.py").write_text(
            "def test_three():\n    assert True\n", encoding="utf-8")
    return repo


def _run_tool(repo: Path, out: Path) -> subprocess.CompletedProcess:
    base = subprocess.run(["git", "rev-parse", "HEAD~1"], cwd=str(repo),
                          capture_output=True, text=True, check=True).stdout.strip()
    return subprocess.run(  # noqa: S603
        [sys.executable, str(ROOT / "product" / "test_delta_attribution.py"),
         "--base", base, "--root", str(repo), "--out", str(out)],
        cwd=str(repo), capture_output=True, text=True, check=False)


def test_tool_refuses_to_publish_a_collection_change_it_cannot_attribute(tmp_path):
    """Negative control on the refusal itself, against a synthetic repository.

    The working tree collects one more test than the head commit and no changed
    test MODULE accounts for it - an uncommitted conftest did. The tool must exit 2
    and write nothing, rather than publish a decomposition that closes only by
    coincidence. This is the shape that actually occurs: a cycle tweaks collection
    without touching a test module.
    """
    repo = _synthetic_repo(tmp_path, unattributable=True)
    out = tmp_path / "should_not_exist.json"
    proc = _run_tool(repo, out)
    assert proc.returncode == 2, (
        f"an unattributable collection change must be REFUSED with exit 2, got "
        f"{proc.returncode}: {proc.stdout[-400:]} {proc.stderr[-400:]}")
    assert "REFUSED" in (proc.stdout + proc.stderr)
    assert not out.exists(), "a refused attribution must write no artifact at all"


def test_tool_publishes_when_the_collection_change_is_attributable(tmp_path):
    """Positive control: the refusal above is not "always refuse".

    An untracked NEW module in the working tree reconciles against its own
    collected count, so the tool publishes and says which module it is.
    """
    repo = _synthetic_repo(tmp_path, unattributable=False)
    out = tmp_path / "published.json"
    proc = _run_tool(repo, out)
    assert proc.returncode == 0, f"expected publication: {proc.stdout[-400:]} {proc.stderr[-400:]}"
    art = json.loads(out.read_text(encoding="utf-8"))
    assert art["reconciles"] is True
    assert art["working_tree"]["reconciles"] is True
    assert art["working_tree"]["attributed_by_module"] == {"test_c.py": 1}
    assert art["working_tree"]["delta_vs_head_commit"] == 1
    assert art["working_tree"]["attributed_delta"] == 1
    assert [s["short"] for s in art["steps"]] == [
        subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=str(repo),
                       capture_output=True, text=True, check=True).stdout.strip()]


def test_canonical_sentence_is_generated_from_the_steps():
    """The report quotes this function's output; it must not be a second wording."""
    steps = [
        {"short": "aaaaaaa", "collected_delta_vs_previous_step": 11},
        {"short": "bbbbbbb", "collected_delta_vs_previous_step": -2},
        {"short": "ccccccc", "collected_delta_vs_previous_step": 4},
    ]
    assert tda.build_decomposition_line("zzzzzzz", 13, steps) == (
        "collected-test delta zzzzzzz -> head = +13 = +11 + -2 + +4  "
        "(aaaaaaa=+11, bbbbbbb=-2, ccccccc=+4)"
    )
    assert tda.build_decomposition_line("zzzzzzz", 0, []) == (
        "collected-test delta zzzzzzz -> head = +0 = +0  ()"
    )


def test_report_of_record_quotes_the_tool_output_verbatim():
    """The prose is not a second source of truth: it must BE the tool's line.

    This is the structural half of RF-1. A hand-written decomposition in the
    report can no longer disagree with the measurement without failing the build.
    """
    art = _artifact()
    line = art["decomposition_line"]
    quoted = [
        p for p in (ROOT / "reports" / "product").glob("*.md")
        if art.get("run_id") and ATTRIBUTION.name in p.read_text(encoding="utf-8")
    ]
    assert quoted, f"no report cites {ATTRIBUTION.name}; the correction would be unanchored"
    for report in quoted:
        assert line in report.read_text(encoding="utf-8"), (
            f"{report.name} cites the attribution artifact but does not quote its "
            f"decomposition line verbatim: {line!r}")


@pytest.mark.parametrize("field", [
    "schema", "base", "head", "steps", "observed_collected_delta",
    "decomposition_line", "method", "claim_ceiling", "environment",
])
def test_artifact_carries_every_field_a_reader_needs(field):
    art = _artifact()
    assert field in art, f"the artifact has no {field}: an unreadable measurement is a defect"
    assert art["claim_ceiling"], "a measurement without a claim ceiling is a boast"
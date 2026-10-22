"""The frozen-cache rewrite attribution must be measured, not asserted in prose.

Audit CYCLE_39674781875, finding D2
------------------------------------
``product/live_slice.py``'s docstring and its default-cache comment said that
cycle 39667945530's two live runs "turned 9 more" manifest-covered cache
entries.  The two recorded runs' OWN independent probes list 7 of the 9
manifest-covered entries that commit ``3f94e0e`` rewrote; two files were
rewritten in the same commit with no probe attribution at all.  A published
attribution that does not reproduce from the committed tree is the binding
defect class of this factory (requirement: "a published claim does not
reproduce from the committed tree"), and the same class had already cost this
lane a cycle.

So the number is now measured by ``product/cache_rewrite_attribution.py`` and
published in a run-named artifact, and the PROSE in the shipped module is
pinned to that measurement: these tests read the docstring, extract the
attribution numbers and compare them against a fresh recomputation from git.

The tests fail closed: if the measurement cannot be taken (no git history, no
manifest, missing record) they FAIL rather than skip or pass on an empty
expectation set.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest

PRODUCT_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PRODUCT_ROOT.parent
for _p in (str(PRODUCT_ROOT), str(REPO_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from product import cache_rewrite_attribution as cra  # noqa: E402

LIVE_SLICE = PRODUCT_ROOT / "live_slice.py"
ARTIFACT = cra.ARTIFACT

#: The machine-readable attribution sentence the docstring must carry.
ATTRIBUTION_RE = re.compile(
    r"manifest-covered\s+entries\s+rewritten\s+by\s+commit\s+(?P<commit>[0-9a-f]+)\s*=\s*"
    r"(?P<rewritten>\d+);\s*attributed\s+to\s+the\s+two\s+recorded\s+runs'\s+own\s+probes\s*=\s*"
    r"(?P<attributed>\d+);\s*carrying\s+no\s+probe\s+attribution\s*=\s*"
    r"(?P<unattributed>\d+)"
)


def _docstring() -> str:
    return LIVE_SLICE.read_text(encoding="utf-8")


def test_the_tool_measures_the_attribution_from_git_and_the_frozen_manifest():
    """A fresh measurement, not a cached value: 9 rewritten, 7 attributed, 2 not."""
    payload = cra.measure()
    counts = payload["attribution"]["counts"]
    assert counts["manifest_covered_rewritten"] == 9, (
        "the manifest-covered rewrite count changed - re-derive it and record "
        f"why in the artifact, do not silently re-baseline: {counts}")
    assert counts["distinct_attributed"] == 7, (
        "the number of rewrites the recorded probes account for changed: "
        f"{counts}")
    assert counts["unattributed"] == 2, (
        "the number of rewrites NO recorded probe accounts for changed: "
        f"{counts}")
    # the partition must hold exactly: attributed and unattributed together
    # are the rewritten set, with no overlap
    attr = payload["attribution"]
    assert set(attr["distinct_attributed"]) | set(attr["unattributed"]) == set(
        payload["manifest_covered_rewritten"])
    assert not (set(attr["distinct_attributed"]) & set(attr["unattributed"]))


def test_the_two_unattributed_files_are_the_two_the_audit_named():
    payload = cra.measure()
    unattributed = [Path(p).name for p in payload["attribution"]["unattributed"]]
    assert unattributed == [
        "11c69a8b8d6957fcb1348469a840098bf523ea1d558853b7ab008e978d714927.json",
        "88a3a731a6829455f6911b8931a1f4c3e9235d5d7a64519018e16563a3e33598.json",
    ], (
        "the unattributed pair changed; re-derive it from the records' own "
        f"probes and record why: {unattributed}")


def test_the_committed_artifact_matches_a_fresh_measurement():
    """The published attribution must reproduce, byte for byte, from the tree.

    The REPRODUCIBLE CORE of every published artifact is the attribution
    itself: it is a pure function of git history, so it has to reproduce
    forever.  The working-tree snapshot inside it is a DATED OBSERVATION and
    is allowed to move (see the next test).
    """
    assert ARTIFACT.is_file(), (
        f"missing the run-named attribution artifact: {ARTIFACT}")
    committed = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    fresh = cra.artifact_payload(committed.get("run_id") or "39674781875")
    assert cra.core_of(committed) == cra.core_of(fresh), (
        "the committed attribution artifact does not reproduce from the "
        "committed tree - re-run `python3 product/cache_rewrite_attribution.py "
        "--write` and record why in the report of record")


def test_every_drift_from_the_superseded_manifest_is_attributed_to_a_commit():
    """The 38759730609 manifest no longer describes the tree; say WHO moved it.

    Accepted commits e77733b and 128870a rewrote 15 manifest-covered cache
    entries in place.  The old check could only express that as a permanent
    failure ("the frozen manifest is not intact"), which is a true fact with
    no actionable consequence.  The honest invariant is: every drifted entry
    is attributable to a NAMED commit, and an unattributable drift fails.
    """
    payload = cra.measure()
    tree = payload["current_tree"]
    drift = tree["drift_attributed"]
    assert tree["n_unattributed_drift"] == 0, (
        "a drifted cache entry is not attributable to any commit - that is a "
        f"silent rewrite: {[d for d in drift if not d['attributed']]}")
    for entry in drift:
        assert entry["last_changed_commit"], (
            f"{entry['path']} drifted with no commit to name")
        assert entry["last_changed_subject"], (
            f"{entry['path']} drifted with no commit subject")
    # the drift is real and it is named, never hidden
    if not tree["intact"]:
        assert tree["drift_commits"], (
            "the tree drifted from the frozen manifest but no commit is named")


def test_the_frozen_snapshot_in_force_matches_the_working_tree():
    """The protection stays alive: the snapshot in force must describe the tree."""
    snapshot = cra.newest_snapshot()
    assert snapshot is not None, (
        "no superseding frozen cache-manifest snapshot exists - the tree "
        "drifted from the 38759730609 manifest, so the protection must be "
        "re-frozen with --write-snapshot")
    payload = json.loads(snapshot.read_text(encoding="utf-8"))
    entries = {str(e["path"]): str(e["sha256"])
               for e in (payload.get("entries") or [])}
    tree = cra.current_tree_integrity(entries)
    assert tree["intact"], (
        f"the frozen snapshot in force ({snapshot.name}) does not match the "
        f"working tree: {tree['n_mismatch']} mismatched, {tree['n_missing']} "
        "missing")
    assert payload.get("supersedes", {}).get("path"), (
        "the superseding snapshot must name the manifest it supersedes")


def test_the_published_attributions_all_verify_together():
    """The tool's own verdict must be green, and it must be checkable."""
    code, problems = cra.check_all()
    assert code == 0, f"the published cache attribution does not verify: {problems}"


def test_the_shipped_docstring_states_the_measured_numbers():
    """The prose is pinned to the measurement: it cannot drift again."""
    match = ATTRIBUTION_RE.search(_docstring())
    assert match, (
        "product/live_slice.py's docstring no longer carries the machine-readable "
        "attribution sentence ('manifest-covered entries rewritten by commit "
        "<sha> = N; attributed to the two recorded runs' own probes = N; "
        "carrying no probe attribution = N'); the measured attribution must be "
        "visible where the default cache root is explained")
    payload = cra.measure()
    counts = payload["attribution"]["counts"]
    assert int(match.group("rewritten")) == counts["manifest_covered_rewritten"]
    assert int(match.group("attributed")) == counts["distinct_attributed"]
    assert int(match.group("unattributed")) == counts["unattributed"]
    assert match.group("commit") == payload["range"]["head"] or \
        match.group("commit") in payload["range"]["head"], (
        "the docstring names a commit that is not the one the measurement "
        "attributes")


def test_the_shipped_docstring_names_the_unattributed_files():
    """The two files with no probe attribution are named, not hidden."""
    payload = cra.measure()
    doc = _docstring()
    for path in payload["attribution"]["unattributed"]:
        name = Path(path).name
        assert name in doc, (
            f"the docstring must name {name}: it was rewritten in the same "
            "commit as the attributed ones and NO recorded probe lists it")
    assert "9 more" not in doc, (
        "the superseded sentence ('9 more ... manifest-covered entries') is "
        "still in the docstring; it is the claim the audit found false")


def test_the_default_cache_comment_states_the_measured_numbers():
    """The in-code comment carries the same corrected attribution."""
    source = LIVE_SLICE.read_text(encoding="utf-8")
    assert "NO probe attribution" in source, (
        "the default-cache comment above run() must carry the corrected "
        "attribution (7 attributed / 2 unattributed), not the superseded '9'")
    assert "turned 9 more" not in source, (
        "the superseded 'turned 9 more' attribution is still in the code")


# --------------------------------------------------------------------------
# non-vacuity controls: the tool must DETECT a wrong attribution
# --------------------------------------------------------------------------

def test_a_rewrite_no_probe_lists_is_reported_as_unattributed():
    """The control: an unprobed rewrite must never be folded into a run."""
    rewritten = ["a/aaa.json", "b/bbb.json"]
    probes = {"RUN_A": ["a/aaa.json"]}
    out = cra.attribute(rewritten, probes)
    assert out["counts"] == {"manifest_covered_rewritten": 2,
                              "distinct_attributed": 1,
                              "unattributed": 1}
    assert out["unattributed"] == ["b/bbb.json"]


def test_a_file_probed_by_two_records_is_counted_once():
    """The union is over sets: a double-probed file is ONE file."""
    rewritten = ["a/aaa.json"]
    probes = {"RUN_A": ["a/aaa.json"], "RUN_B": ["a/aaa.json"]}
    out = cra.attribute(rewritten, probes)
    assert out["counts"]["distinct_attributed"] == 1
    assert out["counts"]["unattributed"] == 0


def test_a_measurement_that_cannot_be_taken_fails_closed():
    """A missing record is an error, never an empty attribution."""
    with pytest.raises(cra.MeasurementError):
        cra.record_probes(["results/product/live_slice/does-not-exist.json"])

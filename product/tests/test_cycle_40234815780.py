"""Repair round 1 of rejected product cycle 40230559317 — machine-enforced.

The audit of run 40230559317 returned `gate=REVISE` with exactly two
`required_fixes`. Both were prose-or-expectation defects, which is the class
that silently returns unless a test carries it:

1. ``test_counter_content_rejection_v68.py::
   test_fixture_mode_offline_slice_downgrades_the_known_letterhead_row`` failed
   because it pinned an incidental retrieval-order property (that the
   Graubünden letterhead decision is ``work["decisions"][2]``, the fixture
   challenge row) on top of the P0 contract it exists to pin. The committed
   query cache has since gained the two ``legal_concept`` envelopes the rejected
   cycle's run missed, so a fresh build is no longer degraded, the candidate
   pool changes and index 2 is a different decision.
2. ``reports/product/CYCLE_40230559317.md`` published ``80 passed, 21 warnings``
   for a group whose measured terminal line was ``1 failed, 80 passed, 21
   warnings``.

Every claim below is re-derived from committed bytes: the two raw pytest logs
under ``results/product/repair_40234815780/``, the counts artifact, the two
reports, and ``git diff`` of this worktree. No frozen gate, rubric, threshold,
bar or success rule is imported, edited or re-tuned here.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
PRODUCT = ROOT / "product"
for _p in (str(ROOT), str(PRODUCT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from product.test_accounting import compute_delta, parse_pytest_summary  # noqa: E402

REPAIR_DIR = ROOT / "results" / "product" / "repair_40234815780"
COUNTS = REPAIR_DIR / "test_counts_40234815780.json"
AS_SUBMITTED_LOG = REPAIR_DIR / "pytest_group1_as_submitted_40230559317.log"
REPAIRED_LOG = REPAIR_DIR / "pytest_group1_repaired_40234815780.log"
PRODUCER_REPORT = ROOT / "reports" / "product" / "CYCLE_40230559317.md"
REPAIR_REPORT = ROOT / "reports" / "product" / "CYCLE_40234815780_REPAIR1.md"
TEST_MODULE = PRODUCT / "tests" / "test_counter_content_rejection_v68.py"

#: The exact line the rejected cycle published, which required_fixes item 2
#: orders corrected. It may survive only as a MARKED quotation of what was
#: published, never as the report's live claim.
SUPERSEDED_CLAIM = "# 80 passed, 21 warnings (baseline before this delta: 72 passed)"

#: What the group measured when the rejected cycle submitted it.
AS_SUBMITTED = {"failed": 1, "passed": 80, "total_collected": 81}
#: What the same group measures with the repaired expectation.
REPAIRED = {"failed": 0, "passed": 81, "total_collected": 81}


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True,
                          text=True, check=False).stdout


def test_repair_artifacts_exist_and_are_named_by_both_reports():
    """The evidence a claim rests on must exist, not be referenced."""
    for path in (AS_SUBMITTED_LOG, REPAIRED_LOG, COUNTS, PRODUCER_REPORT, REPAIR_REPORT):
        assert path.is_file(), f"missing repair artifact: {path.relative_to(ROOT)}"
        assert path.read_bytes(), f"zero-byte repair artifact: {path.relative_to(ROOT)}"
    producer = PRODUCER_REPORT.read_text(encoding="utf-8")
    repair = REPAIR_REPORT.read_text(encoding="utf-8")
    assert AS_SUBMITTED_LOG.name in producer and REPAIRED_LOG.name in producer, (
        "the corrected producer report must name the raw logs its numbers come from")
    for name in (AS_SUBMITTED_LOG.name, REPAIRED_LOG.name, COUNTS.name):
        assert name in repair, f"the repair report must cite {name}"


def test_required_fix_2_group_measures_80_passed_1_failed_as_submitted():
    """required_fixes item 2: the measured line is `1 failed, 80 passed`, not `80 passed`."""
    measured = parse_pytest_summary(AS_SUBMITTED_LOG.read_text(encoding="utf-8"))
    for key, expected in AS_SUBMITTED.items():
        assert measured[key] == expected, (
            f"as-submitted group measured {key}={measured[key]}, expected {expected}; "
            "the audit's required_fixes item 2 names exactly this mismatch")
    assert measured["total_collected"] == measured["passed"] + measured["failed"]


def test_required_fix_1_the_repaired_group_is_fully_green():
    """required_fixes item 1: the same group now passes in full."""
    measured = parse_pytest_summary(REPAIRED_LOG.read_text(encoding="utf-8"))
    for key, expected in REPAIRED.items():
        assert measured[key] == expected, (
            f"repaired group measured {key}={measured[key]}, expected {expected}")
    delta = compute_delta(
        parse_pytest_summary(AS_SUBMITTED_LOG.read_text(encoding="utf-8")), measured)
    assert delta["net_new_passing_tests"] == 1
    assert delta["net_new_failing_tests"] == -1
    assert delta["net_change_in_collected"] == 0, (
        "the repair changed expectations, not the population: collected stays 81")


def test_the_counts_artifact_agrees_with_the_logs_it_pins():
    """RF2: the artifact's numbers are re-derived here, never trusted."""
    artifact = json.loads(COUNTS.read_text(encoding="utf-8"))
    as_sub = parse_pytest_summary(AS_SUBMITTED_LOG.read_text(encoding="utf-8"))
    repaired = parse_pytest_summary(REPAIRED_LOG.read_text(encoding="utf-8"))
    for side, measured in (("as_submitted", as_sub), ("repaired", repaired)):
        for key in ("failed", "passed", "skipped", "errors", "total_collected", "seconds"):
            assert artifact[side][key] == measured[key], (
                f"artifact {side}.{key}={artifact[side][key]} != log {measured[key]}")
    assert artifact["delta"] == compute_delta(as_sub, repaired)
    # the pins must be real bytes on disk, re-hashed here
    import hashlib
    for side, log in (("baseline", AS_SUBMITTED_LOG), ("head", REPAIRED_LOG)):
        pin = artifact["pins"][side]["raw_log"]
        data = log.read_bytes()
        assert hashlib.sha256(data).hexdigest() == pin["sha256"], (
            f"{side} raw log no longer hashes to its pin")
    assert artifact["pins"]["baseline"]["run_id"] == "40230559317"
    assert artifact["pins"]["head"]["run_id"] == "40234815780"
    assert artifact["claim_being_corrected"]["as_published"] == SUPERSEDED_CLAIM


def test_the_producer_report_corrects_the_claim_it_was_found_to_make():
    """The correction is side-by-side (RF2) and the bare claim is no longer live."""
    text = PRODUCER_REPORT.read_text(encoding="utf-8")
    assert SUPERSEDED_CLAIM not in text, (
        "the superseded `80 passed` line is still in the report as a live claim; "
        "required_fixes item 2 orders it corrected")
    assert "1 failed, 80 passed, 21 warnings in 16.55s" in text, (
        "the measured as-submitted line must be published beside the superseded one")
    assert "81 passed, 21 warnings in 16.78s" in text, (
        "the post-repair measurement must be published too")
    assert "Repair round 1 annotation" in text and "40234815780" in text, (
        "the in-place correction must be attributed to this repair run")
    # RF2: both numbers side by side, never a silent replacement
    assert "AS SUBMITTED" in text and "CORRECTED" in text


def test_the_repaired_fixture_mode_test_pins_the_contract_not_the_cache_order():
    """required_fixes item 1, at its measured scope.

    Guards the SHAPE of the repair so it cannot be reverted into either of the
    two weakening moves: re-adding the bare single-row assertion as the only
    letterhead check, or deleting the leg's end-to-end proof.
    """
    src = TEST_MODULE.read_text(encoding="utf-8")
    body = src.split("def test_fixture_mode_offline_slice_downgrades_the_known_letterhead_row", 1)
    assert len(body) == 2, "the fixture-mode test disappeared"
    fixture_body = body[1]
    # (a) the shipped path must still be proven to run the leg on a fresh build
    assert 'assert prov.get("applied") is True' in fixture_body
    assert "n_downgraded" in fixture_body and ">= 1" in fixture_body
    # (b) the per-downgrade contract the repair added
    for needle in ('"reason_code"', '"defects"', "counter_evidence_unevidenced",
                   "incumbent_sweep", "seam_abstention"):
        assert needle in fixture_body, f"repaired contract lost: {needle}"
    # (c) the bundle-wide P0 invariant is still asserted
    assert "frozen_content_defects" in fixture_body
    # (d) the weakening move is absent. The rejected version pinned the letterhead
    #     row's *state* unconditionally at function scope, which is exactly what
    #     stopped holding when the committed cache gained the two legal_concept
    #     envelopes: `assert row.get("counter_evidence_unevidenced") is True`
    #     at 4-space indent, straight after `assert row.get("counter_evidence_verified") is False`.
    #     The repaired body keeps those assertions only INSIDE the per-downgrade
    #     loop / behind the `if ... and defects:` guard (8-space indent).
    assert '\n    assert row.get("counter_evidence_verified") is False' not in fixture_body, (
        "the build-specific unconditional state pin that required_fixes item 1 "
        "repairs has been restored")
    assert '\n    assert row.get("counter_evidence_unevidenced") is True' not in fixture_body, (
        "the unconditional letterhead expectation that required_fixes item 1 "
        "repairs has been restored; the conditional form must be used instead")
    assert 'if str(row.get("counter_evidence") or "").strip() and defects:' in fixture_body, (
        "the conditional letterhead check must stay conditional")
    # the row is addressed by stable present-id, never by the incidental index
    # (the function's docstring still *narrates* work["decisions"][2] as the
    # historical cause, so only selection code is checked here)
    assert 'row = by_id.get("gr_gerichte_ERZ 2010 25")' in fixture_body
    assert 'next(d for d in bundle["decisions"]' not in fixture_body
    # (e) the frozen-predicate provenance pin survives
    assert "FROZEN_PREDICATE_SOURCE_SHA" in fixture_body


def test_this_repair_touched_no_frozen_baseline_data_or_committed_bundle():
    """The repair's write scope, measured from git rather than asserted in prose."""
    changed = [ln.strip() for ln in _git("diff", "--name-only", "HEAD").splitlines() if ln.strip()]
    untracked = [ln.strip() for ln in
                 _git("ls-files", "--others", "--exclude-standard").splitlines() if ln.strip()]
    paths = changed + untracked
    if not paths:  # already committed by the workflow before this test ran
        pytest.skip("worktree clean: the workflow committed the repair before tests ran")
    forbidden_prefixes = (
        "product/frozen/",
        "results/product/gate_packet/",
        "results/product/offline_slice/",
        "results/product/server_slice/",
        "results/product/counter_content_family/",
        "results/product/map_integrity/",
        "evaluation/",
        "results/evaluation/",
        ".github/",
    )
    offenders = [p for p in paths if p.startswith(forbidden_prefixes)]
    assert not offenders, (
        "the repair wrote outside its declared scope (frozen baselines, committed "
        f"bundles or control-plane workflows): {offenders}")
    allowed = (
        "product/tests/test_counter_content_rejection_v68.py",
        "product/tests/test_cycle_40234815780.py",
        "reports/product/CYCLE_40230559317.md",
        "reports/product/CYCLE_40234815780_REPAIR1.md",
        "results/product/repair_40234815780/",
        "state/product.json",
    )
    unexpected = [p for p in paths if not p.startswith(allowed)]
    assert not unexpected, (
        f"files changed by this repair outside its declared delta: {unexpected}")

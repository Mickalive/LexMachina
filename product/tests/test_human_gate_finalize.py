"""Tests for the human-gate session finalizer (direction v51 delta 1).

The accepted ``frontier-human-gate-harness`` switch exports a ``status: "draft"``
session whose bundle hashes are ``null`` and whose ``integrity`` is asserted by
nobody. These tests freeze what the finalizer must guarantee before a session is
allowed to become lane evidence:

* it never fabricates a gate answer (missing answers -> incomplete + exit 3);
* it never marks a session usable when the bundle it was run on is a different
  bundle, or when the session claims to have opened decisions that do not exist;
* it binds the record to the bundle digest, so a hand-edited draft is detectable;
* a negative session (the jurist answered "no") survives as valid evidence;
* a record that contradicts itself is refused **in the write path**, and the
  tests assert on the exact file the CLI reports, not on a directory listing.

Cycle 38726191935 shipped a guard test that could not fail; the tests below are
built so that the regression it missed is detected both here and in
``product/human_gate_evidence.py``.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

PRODUCT_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PRODUCT_ROOT.parent
if str(PRODUCT_ROOT) not in sys.path:
    sys.path.insert(0, str(PRODUCT_ROOT))

import human_gate_finalize as hgf  # noqa: E402
from human_gate_finalize import (  # noqa: E402
    CANONICAL_DIR_DEFAULT,
    CLAIM_CEILING_REAL,
    CLAIM_CEILING_SIMULATED,
    DEFAULT_OUT_DIR,
    GATE_QUESTIONS,
    MIN_REAL_BUNDLE_DECISIONS,
    SIMULATED_OUT_DIR,
    IncompleteSession,
    FinalizeError,
    bundle_evidence,
    canonical_sha256,
    claim_ceiling_for,
    finalize,
    record_admissibility_problems,
    session_metrics,
    validate_draft,
    validate_real_session,
    write_record,
)

COUNTER_ID = "SR 123/2020"
PLAIN_ID = "SR 999/2020"

#: A query-specific map carries 100-300 decisions in production; the fixture
#: bundle is deliberately larger than MIN_REAL_BUNDLE_DECISIONS so that the
#: "plausible bundle" guard is exercised, not bypassed.
FILLER_DECISIONS = 24


def make_bundle(
    query: str = "Kündigung Mietvertrag Mietrecht",
    *,
    n_filler: int = FILLER_DECISIONS,
) -> dict:
    decisions = [
        {"decision_id": COUNTER_ID, "counter_status": "candidate-limiting", "citation": "SR 123/2020"},
        {"decision_id": PLAIN_ID, "counter_status": "none", "citation": "SR 999/2020"},
    ]
    decisions += [
        {
            "decision_id": f"SR {400 + i}/2021",
            "counter_status": "none",
            "citation": f"SR {400 + i}/2021",
            "canonical_url": f"https://mcp.opencaselaw.ch/api/decisions/SR-{400 + i}-2021",
        }
        for i in range(n_filler)
    ]
    return {
        "bundle_version": "query_result_bundle v1.0",
        "query": query,
        "decisions": decisions,
        "clusters": [],
        "relations": [],
        "provenance": {},
    }


def make_draft(**overrides) -> dict:
    draft = {
        "schema_version": "1.0",
        "record_type": "lex_human_gate_session",
        "team_id": "frontier-human-gate-harness",
        "charter_version": 1,
        "session_id": None,
        "status": "draft",
        "source": "switch",
        "query": "Kündigung Mietvertrag Mietrecht",
        "bundle_ref": {"query": "Kündigung Mietvertrag Mietrecht", "n_decisions": 2},
        "bundle_sha256": None,
        "query_sha256": None,
        "bundle_hash_status": "not_verified",
        "started_at": "2026-10-14T20:00:00.000Z",
        "ended_at": "2026-10-14T20:07:30.000Z",
        "view_mode_initial": "map",
        "view_mode_final": "list",
        "actions": [
            {"at": "2026-10-14T20:00:01.000Z", "view_mode": "map", "event": "switch_view", "ref": None},
            {"at": "2026-10-14T20:01:00.000Z", "view_mode": "list", "event": "open_decision", "ref": PLAIN_ID},
            {"at": "2026-10-14T20:02:00.000Z", "view_mode": "list", "event": "open_counter", "ref": COUNTER_ID},
        ],
        "decisions_opened": [PLAIN_ID],
        "counter_authorities_opened": [COUNTER_ID],
        "answers": {},
        "missing_answers": list(GATE_QUESTIONS),
        "latency": {"baseline_render_ms": None, "session_wall_clock_seconds": None},
    }
    draft.update(overrides)
    return draft


def all_yes() -> dict:
    return {qid: {"rating": "yes", "note": ""} for qid in GATE_QUESTIONS}


# --------------------------------------------------------------------------
# draft validation
# --------------------------------------------------------------------------


def test_valid_draft_has_no_problems() -> None:
    assert validate_draft(make_draft()) == []


@pytest.mark.parametrize(
    "mutation, expected",
    [
        ({"record_type": "something_else"}, "record_type"),
        ({"team_id": "other-team"}, "team_id"),
        ({"actions": []}, "actions is empty"),
        ({"ended_at": "2026-10-14T19:00:00.000Z"}, "ended_at precedes started_at"),
        ({"started_at": None}, "started_at"),
        ({"decisions_opened": "SR-1"}, "decisions_opened must be a list"),
    ],
)
def test_invalid_drafts_are_rejected_with_a_reason(mutation, expected) -> None:
    problems = validate_draft(make_draft(**mutation))
    assert any(expected in problem for problem in problems), problems


def test_finalize_rejects_invalid_draft_with_exit_4() -> None:
    with pytest.raises(FinalizeError) as excinfo:
        finalize(make_draft(record_type="nope"), all_yes(), make_bundle())
    assert excinfo.value.exit_code == 4


# --------------------------------------------------------------------------
# the gate answers are never fabricated
# --------------------------------------------------------------------------


def test_missing_answers_yield_incomplete_evidence_and_exit_3() -> None:
    with pytest.raises(IncompleteSession) as excinfo:
        finalize(make_draft(), {"q1": "yes", "q2": "yes"}, make_bundle(), simulated=True)
    assert excinfo.value.exit_code == 3
    assert excinfo.value.missing == ["q3", "q4"]
    record = excinfo.value.record
    assert record["status"] == "incomplete"
    assert set(record["answers"]) == {"q1", "q2"}


def test_no_answers_at_all_is_rejected() -> None:
    with pytest.raises(IncompleteSession) as excinfo:
        finalize(make_draft(), None, make_bundle(), simulated=True)
    assert excinfo.value.missing == list(GATE_QUESTIONS)


def test_finalized_record_binds_to_the_bundle_digest() -> None:
    record = finalize(make_draft(), all_yes(), make_bundle(), simulated=True)
    assert record["status"] == "finalized"
    assert record["bundle_hash_status"] == "verified"
    assert record["bundle_sha256"] == canonical_sha256(make_bundle())
    assert record["query_sha256"] == canonical_sha256("Kündigung Mietvertrag Mietrecht")
    assert record["missing_answers"] == []


def test_negative_session_is_valid_evidence() -> None:
    """The Master Prompt's 'if not, stop the standalone product' case must survive."""
    record = finalize(
        make_draft(),
        {qid: {"rating": "no", "note": "the map hid nothing I could not see in the list"} for qid in GATE_QUESTIONS},
        make_bundle(),
        simulated=True,
    )
    assert record["status"] == "finalized"
    assert all(record["answers"][q]["rating"] == "no" for q in GATE_QUESTIONS)


def test_free_text_answers_are_kept_verbatim() -> None:
    note = "FR 4A exception invisible in the ranked list"
    record = finalize(make_draft(), {**{q: "yes" for q in ("q1", "q2", "q4")}, "q3": note}, make_bundle(), simulated=True)
    assert record["answers"]["q3"]["note"] == note
    assert record["answers"]["q3"]["rating"] == ""
    assert record["answers"]["q1"]["rating"] == "yes"


def test_answers_can_be_taken_from_the_draft_itself() -> None:
    draft = make_draft(answers={"q1": {"rating": "yes"}, "q2": "partly", "q3": "no", "q4": "mixed"})
    record = finalize(draft, None, make_bundle(), simulated=True)
    assert record["status"] == "finalized"
    assert record["answers"]["q3"]["rating"] == "no"


def test_tool_never_claims_human_gate_ready() -> None:
    """No field may assert the gate is passed; the director decides from records."""
    record = finalize(make_draft(), all_yes(), make_bundle(), simulated=True)
    assert "human_gate_ready" not in record
    def walk(node):
        if isinstance(node, dict):
            for key, value in node.items():
                assert key != "human_gate_ready"
                walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)
    walk(record)


# --------------------------------------------------------------------------
# integrity against the bundle
# --------------------------------------------------------------------------


def test_bundle_mismatch_on_query_is_refused_with_exit_5() -> None:
    with pytest.raises(FinalizeError) as excinfo:
        finalize(make_draft(), all_yes(), make_bundle("Eine ganz andere Frage"))
    assert excinfo.value.exit_code == 5
    assert "does not match" in str(excinfo.value)


def test_opened_decision_absent_from_the_bundle_is_refused() -> None:
    draft = make_draft(decisions_opened=[PLAIN_ID, "SR 000/1900"])
    with pytest.raises(FinalizeError) as excinfo:
        finalize(draft, all_yes(), make_bundle())
    assert excinfo.value.exit_code == 5
    assert "absent from the bundle" in str(excinfo.value)


def test_counter_opened_without_counter_status_is_refused() -> None:
    draft = make_draft(counter_authorities_opened=[PLAIN_ID])
    with pytest.raises(FinalizeError) as excinfo:
        finalize(draft, all_yes(), make_bundle())
    assert excinfo.value.exit_code == 5
    assert "without a counter status" in str(excinfo.value)


def test_draft_without_bundle_stays_unverified_evidence() -> None:
    record = finalize(make_draft(), all_yes(), None, simulated=True)
    assert record["bundle_hash_status"] == "not_verified"
    assert record["bundle_evidence"]["bundle_supplied"] is False


def test_bundle_evidence_counts_real_counter_openings() -> None:
    evidence = bundle_evidence(make_draft(), make_bundle())
    assert evidence["opened_in_bundle"] == 1
    assert evidence["counters_in_bundle"] == 1
    assert evidence["bundle_counter_count"] == 1
    assert evidence["integrity_problems"] == []


# --------------------------------------------------------------------------
# derived session metrics
# --------------------------------------------------------------------------


def test_session_metrics_count_baseline_use_and_wall_clock() -> None:
    metrics = session_metrics(make_draft())
    assert metrics["n_decisions_opened"] == 1
    assert metrics["n_counter_authorities_opened"] == 1
    assert metrics["used_conventional_baseline"] is True
    assert metrics["view_mode_initial"] == "map" and metrics["view_mode_final"] == "list"
    assert metrics["wall_clock_seconds"] == 450.0
    assert metrics["events"]["open_counter"] == 1


def test_session_metrics_tolerate_missing_timestamps() -> None:
    metrics = session_metrics(make_draft(started_at=None, ended_at=None))
    assert metrics["wall_clock_seconds"] is None


# --------------------------------------------------------------------------
# persistence + CLI
# --------------------------------------------------------------------------


def test_write_record_lands_in_results_product(tmp_path: Path) -> None:
    record = finalize(make_draft(), all_yes(), make_bundle(), run_id="38649613677", finalized_by="test-user", simulated=True)
    path = write_record(record, tmp_path)
    assert path.is_file()
    stored = json.loads(path.read_text(encoding="utf-8"))
    assert stored["run_id"] == "38649613677"
    assert stored["status"] == "finalized"


def test_cli_end_to_end(tmp_path: Path) -> None:
    draft_path = tmp_path / "draft.json"
    bundle_path = tmp_path / "bundle.json"
    answers_path = tmp_path / "answers.json"
    draft_path.write_text(json.dumps(make_draft()), encoding="utf-8")
    bundle_path.write_text(json.dumps(make_bundle()), encoding="utf-8")
    answers_path.write_text(json.dumps(all_yes()), encoding="utf-8")

    out_dir = tmp_path / "sessions"
    result = subprocess.run(
        [
            sys.executable, str(PRODUCT_ROOT / "human_gate_finalize.py"),
            "--draft", str(draft_path), "--bundle", str(bundle_path),
            "--answers", str(answers_path), "--out", str(out_dir), "--run-id", "38649613677",
            "--finalized-by", "test-user",
        ],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "human_gate_ready is NOT set" in result.stdout
    written = list(out_dir.glob("session_*.json"))
    assert len(written) == 1
    assert json.loads(written[0].read_text(encoding="utf-8"))["status"] == "finalized"


def test_cli_exits_3_on_incomplete_session_but_still_records_it(tmp_path: Path) -> None:
    draft_path = tmp_path / "draft.json"
    bundle_path = tmp_path / "bundle.json"
    draft_path.write_text(json.dumps(make_draft()), encoding="utf-8")
    bundle_path.write_text(json.dumps(make_bundle()), encoding="utf-8")
    out_dir = tmp_path / "sessions"
    result = subprocess.run(
        [
            sys.executable, str(PRODUCT_ROOT / "human_gate_finalize.py"),
            "--draft", str(draft_path), "--bundle", str(bundle_path), "--out", str(out_dir),
            "--simulated",
        ],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    assert result.returncode == 3, result.stdout + result.stderr
    written = list(out_dir.glob("session_*.json"))
    assert len(written) == 1
    assert json.loads(written[0].read_text(encoding="utf-8"))["status"] == "incomplete"


# --------------------------------------------------------------------------
# simulated-session guard (audit F3/F5, cycle 38726191935)
#
# The previous guard asserted on `list(SIMULATED_OUT_DIR.glob(...))[-1]`;
# Path.glob() is unsorted, so it read whatever entry the filesystem listed last
# and passed green on the exact defect it was written for. Every assertion below
# reads the path the CLI itself reports, and the negative tests below genuinely
# fail when the claim ceiling or the write guard regresses.
# --------------------------------------------------------------------------


def _run_cli(argv: list[str], *, env: dict[str, str] | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(PRODUCT_ROOT / "human_gate_finalize.py"), *argv],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
        env={**os.environ, **(env or {})},
    )


def _write_inputs(tmp_path: Path, *, n_filler: int = FILLER_DECISIONS) -> tuple[Path, Path, Path]:
    draft_path = tmp_path / "draft.json"
    bundle_path = tmp_path / "bundle.json"
    answers_path = tmp_path / "answers.json"
    draft_path.write_text(json.dumps(make_draft()), encoding="utf-8")
    bundle_path.write_text(json.dumps(make_bundle(n_filler=n_filler)), encoding="utf-8")
    answers_path.write_text(json.dumps(all_yes()), encoding="utf-8")
    return draft_path, bundle_path, answers_path


def _finalized_path(stdout: str, tmp_path: Path) -> Path:
    """The exact file the CLI says it wrote (never a directory listing)."""
    reported = [line.split(":", 1)[1].strip() for line in stdout.splitlines() if line.startswith("finalized:")]
    assert len(reported) == 1, f"expected exactly one 'finalized:' line, got {reported} in {stdout!r}"
    path = Path(reported[0])
    assert path.is_file(), f"CLI reported {path} but it does not exist"
    assert path.parent == tmp_path, f"record escaped the requested directory: {path}"
    return path


def test_simulated_flag_redirects_to_simulated_dir_and_marks_record(tmp_path: Path) -> None:
    """--simulated writes to the simulated directory and stamps the simulated ceiling.

    Non-vacuous by construction: the assertion reads the exact path printed by
    the CLI, so a stale record left in the directory by an earlier run cannot
    satisfy it.
    """
    draft_path, bundle_path, answers_path = _write_inputs(tmp_path)
    out_dir = tmp_path / "sessions_simulated"
    env = {
        "LEX_HUMAN_GATE_SIMULATED_OUT_DIR": str(out_dir),
        "LEX_HUMAN_GATE_OUT_DIR": str(tmp_path / "canonical_untouched"),
    }
    result = _run_cli(
        ["--draft", str(draft_path), "--bundle", str(bundle_path), "--answers", str(answers_path), "--simulated"],
        env=env,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "redirecting output" in result.stderr
    path = _finalized_path(result.stdout, out_dir)
    assert path.parent == out_dir
    record = json.loads(path.read_text(encoding="utf-8"))
    assert record.get("simulated") is True
    assert record.get("claim_ceiling") == CLAIM_CEILING_SIMULATED
    assert "SIMULATED SESSION" in record["claim_ceiling"]
    assert "documents one owner/jurist session" not in record["claim_ceiling"]
    assert record["bundle_hash_status"] == "verified"
    assert not (tmp_path / "canonical_untouched").exists(), "simulated run wrote into the canonical directory"


def test_simulated_record_is_refused_in_the_canonical_directory(tmp_path: Path) -> None:
    """A simulated record aimed anywhere under the canonical directory is refused (exit 8)."""
    draft_path, bundle_path, answers_path = _write_inputs(tmp_path)
    canonical = tmp_path / "human_gate_sessions"
    result = _run_cli(
        [
            "--draft", str(draft_path), "--bundle", str(bundle_path), "--answers", str(answers_path),
            "--simulated", "--out", str(canonical / "nested"),
        ],
        env={"LEX_HUMAN_GATE_OUT_DIR": str(canonical), "LEX_HUMAN_GATE_SIMULATED_OUT_DIR": str(tmp_path / "sim")},
    )
    assert result.returncode == 8, result.stdout + result.stderr
    assert "inadmissible" in result.stderr
    assert "::error::" in result.stderr, "the refusal must be a clean CLI error, not a traceback"
    assert not list(tmp_path.rglob("session_*.json")), "the refused record was written anyway"


def test_claim_ceiling_regression_is_refused_by_the_write_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """NEGATIVE TEST: reintroduce the cycle-38726191935 defect and prove it is caught.

    The defect was a simulated record whose claim ceiling claimed it documented
    an owner/jurist session. Here that regression is injected into the ceiling
    function and the *production write path* must refuse the record.
    """
    monkeypatch.setattr(hgf, "claim_ceiling_for", lambda simulated: CLAIM_CEILING_REAL)
    record = finalize(make_draft(), all_yes(), make_bundle(), simulated=True)
    assert record["simulated"] is True
    assert record["claim_ceiling"] == CLAIM_CEILING_REAL  # the defect is present

    problems = record_admissibility_problems(record, SIMULATED_OUT_DIR)
    assert any("SIMULATED SESSION claim ceiling" in problem for problem in problems), problems

    target = tmp_path / "written"
    with pytest.raises(FinalizeError) as excinfo:
        write_record(record, target)
    assert excinfo.value.exit_code == 8
    assert not list(target.glob("*.json")) if target.exists() else True


def test_ceiling_regression_is_caught_end_to_end_through_the_cli(tmp_path: Path) -> None:
    """NEGATIVE TEST at process level: a regressed CLI must exit 8 and write nothing.

    The mutation is applied to a copy of the module so the CLI subprocess loads
    a build in which simulated records claim to document owner sessions — the
    exact shipped pathology. If the source anchor ever moves, this test fails
    loudly instead of silently passing.
    """
    source = (PRODUCT_ROOT / "human_gate_finalize.py").read_text(encoding="utf-8")
    anchor = "return CLAIM_CEILING_SIMULATED if simulated else CLAIM_CEILING_REAL"
    assert anchor in source, "mutation anchor missing: claim_ceiling_for changed shape; update this test"
    regressed = source.replace(
        anchor,
        "return CLAIM_CEILING_REAL  # REGRESSION: simulated records claim to be owner sessions",
    )
    module_copy = tmp_path / "human_gate_finalize.py"
    module_copy.write_text(regressed, encoding="utf-8")

    draft_path, bundle_path, answers_path = _write_inputs(tmp_path)
    out_dir = tmp_path / "regressed_out"
    result = subprocess.run(
        [
            sys.executable, str(module_copy),
            "--draft", str(draft_path), "--bundle", str(bundle_path), "--answers", str(answers_path),
            "--simulated", "--out", str(out_dir),
        ],
        cwd=str(REPO_ROOT),
        # The copy's own REPO_ROOT bootstrap resolves to tmp_path (it is derived
        # from __file__), so the copy cannot import the repo's ``product`` package
        # on its own. PYTHONPATH puts the real repo root back on the import path;
        # without it this test measures ModuleNotFoundError rather than the
        # claim-ceiling guard it exists to prove (audit CYCLE_39091749561 F2).
        env={**os.environ, "PYTHONPATH": str(REPO_ROOT)},
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    assert result.returncode == 8, result.stdout + result.stderr
    assert "inadmissible" in result.stderr
    assert not out_dir.exists() or not list(out_dir.glob("*.json"))


def test_claim_ceiling_constants_are_distinct_and_authoritative() -> None:
    assert claim_ceiling_for(True) == CLAIM_CEILING_SIMULATED
    assert claim_ceiling_for(False) == CLAIM_CEILING_REAL
    assert "SIMULATED SESSION" not in CLAIM_CEILING_REAL
    assert "SIMULATED SESSION" in CLAIM_CEILING_SIMULATED
    assert claim_ceiling_for(False).startswith("human gate EVIDENCE only")


# --------------------------------------------------------------------------
# real-session provenance (audit F5)
# --------------------------------------------------------------------------


def _real_record(**overrides) -> dict:
    record = finalize(
        make_draft(), all_yes(), make_bundle(), run_id="38649613677", finalized_by="test-user", **overrides
    )
    return record


def test_real_session_requires_finalized_by_run_id_and_wall_clock() -> None:
    """The three self-attested fields are still required."""
    base = _real_record()
    assert validate_real_session(base) == []

    for field, value, needle in (
        ("finalized_by", None, "finalized_by"),
        ("run_id", None, "run_id"),
    ):
        broken = dict(base)
        broken[field] = value
        problems = validate_real_session(broken)
        assert any(needle in problem for problem in problems), problems

    broken_clock = json.loads(json.dumps(base))
    broken_clock["session_metrics"]["wall_clock_seconds"] = 0.0
    assert any("wall_clock_seconds" in p for p in validate_real_session(broken_clock))


def test_real_session_requires_a_bundle_that_verifies(tmp_path: Path) -> None:
    """A session bound to no bundle is draft evidence and cannot be promoted."""
    with pytest.raises(FinalizeError) as excinfo:
        finalize(make_draft(), all_yes(), None, run_id="38649613677", finalized_by="owner")
    assert excinfo.value.exit_code == 7
    assert "bundle" in str(excinfo.value)

    unverified = _real_record()
    unverified["bundle_hash_status"] = "not_verified"
    assert any("verifies against the draft" in p for p in validate_real_session(unverified))


def test_real_session_requires_a_plausible_number_of_decisions() -> None:
    """A two-decision fixture cannot back a human-gate claim."""
    with pytest.raises(FinalizeError) as excinfo:
        finalize(make_draft(), all_yes(), make_bundle(n_filler=0), run_id="38649613677", finalized_by="owner")
    assert excinfo.value.exit_code == 7
    assert "at least %d decisions" % MIN_REAL_BUNDLE_DECISIONS in str(excinfo.value)


def test_provenance_is_recorded_as_self_attested() -> None:
    record = _real_record()
    assert record["provenance_strength"] == "self_attested"
    assert "not authentication" in record["provenance_note"]


def test_cli_reads_provenance_from_an_attestation_file(tmp_path: Path) -> None:
    draft_path, bundle_path, answers_path = _write_inputs(tmp_path)
    attest_path = tmp_path / "session_attest.json"
    attest_path.write_text(json.dumps({"run_id": "38732097101", "finalized_by": "owner-attest"}), encoding="utf-8")
    out_dir = tmp_path / "sessions"
    result = _run_cli(
        [
            "--draft", str(draft_path), "--bundle", str(bundle_path), "--answers", str(answers_path),
            "--attest", str(attest_path), "--out", str(out_dir),
        ]
    )
    assert result.returncode == 0, result.stdout + result.stderr
    record = json.loads(_finalized_path(result.stdout, out_dir).read_text(encoding="utf-8"))
    assert record["run_id"] == "38732097101"
    assert record["finalized_by"] == "owner-attest"


def test_documented_invocation_in_the_module_docstring_works(tmp_path: Path) -> None:
    """F7: the command the owner will run for the last milestone must not exit 7."""
    docstring = (PRODUCT_ROOT / "human_gate_finalize.py").read_text(encoding="utf-8").split('"""')[1]
    assert "--run-id" in docstring and "--finalized-by" in docstring, "usage example lost its provenance flags"

    draft_path, bundle_path, answers_path = _write_inputs(tmp_path)
    out_dir = tmp_path / "sessions"
    result = _run_cli(
        [
            "--draft", str(draft_path), "--bundle", str(bundle_path), "--answers", str(answers_path),
            "--run-id", "38732097101", "--finalized-by", "owner", "--out", str(out_dir),
        ]
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "human_gate_ready is NOT set" in result.stdout


# --------------------------------------------------------------------------
# the repository's own evidence directories
# --------------------------------------------------------------------------


def test_unit_run_never_writes_into_the_repository_results_tree() -> None:
    """F4: conftest redirects the output dirs, so DEFAULT_OUT_DIR is outside the repo."""
    assert CANONICAL_DIR_DEFAULT.is_dir() or not CANONICAL_DIR_DEFAULT.exists()
    assert DEFAULT_OUT_DIR != CANONICAL_DIR_DEFAULT
    assert SIMULATED_OUT_DIR != CANONICAL_DIR_DEFAULT
    assert not str(DEFAULT_OUT_DIR).startswith(str(REPO_ROOT / "results"))
    assert not str(SIMULATED_OUT_DIR).startswith(str(REPO_ROOT / "results"))


def test_repository_evidence_directories_are_admissible() -> None:
    """The committed tree must hold no inadmissible human-gate record (audit F1/F2)."""
    from human_gate_evidence import CANONICAL_DIR, SIMULATED_DIR, scan_dir

    blocking = [f for d in (CANONICAL_DIR, SIMULATED_DIR) for f in scan_dir(d) if f["severity"] == "blocking"]
    assert blocking == [], blocking


def test_canonical_directory_requires_a_declared_owner_session(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The canonical evidence directory only accepts a declared human session.

    Found by accident in this cycle: the one-command runner dropped ``--out`` and a
    machine-authored rehearsal was written into the canonical directory, where it
    satisfied every other rule. The declaration is the mechanical difference
    between a person answering the four questions and an agent rehearsing.
    """
    canonical = tmp_path / "human_gate_sessions"
    monkeypatch.setattr(hgf, "DEFAULT_OUT_DIR", canonical)
    monkeypatch.setattr(hgf, "SIMULATED_OUT_DIR", tmp_path / "human_gate_sessions_simulated")

    undeclared = finalize(make_draft(), all_yes(), make_bundle(), run_id="38732097101", finalized_by="agent")
    assert undeclared["owner_session_confirmed"] is False
    problems = record_admissibility_problems(undeclared, canonical)
    assert any("--owner-session" in problem for problem in problems), problems
    with pytest.raises(FinalizeError) as excinfo:
        write_record(undeclared, canonical)
    assert excinfo.value.exit_code == 8
    assert not canonical.exists()

    declared = finalize(
        make_draft(), all_yes(), make_bundle(), run_id="38732097101", finalized_by="owner", owner_session=True
    )
    assert declared["owner_session_confirmed"] is True
    assert record_admissibility_problems(declared, canonical) == []
    written = write_record(declared, canonical)
    assert written.is_file()


def test_a_simulated_record_cannot_declare_an_owner_session(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(hgf, "DEFAULT_OUT_DIR", tmp_path / "human_gate_sessions")
    monkeypatch.setattr(hgf, "SIMULATED_OUT_DIR", tmp_path / "human_gate_sessions_simulated")
    record = finalize(make_draft(), all_yes(), make_bundle(), simulated=True, owner_session=True)
    assert "a simulated record cannot carry owner_session_confirmed" in "; ".join(
        record_admissibility_problems(record, tmp_path / "human_gate_sessions_simulated")
    )

"""The repair of audit CYCLE_39119287975 DEFECT A and DEFECT B, as tests.

Both defects were the same shape: a true invariant, published as a claim that an
auditor could not reproduce.

* DEFECT A - the FAIL-write refusal was "demonstrated live" with
  ``--only regression --run-id 99999999999 --write``.  That invocation only
  FAILs while the NEWEST regression artifact records a new failure.  The moment
  cycle 39119287975's clean artifact landed, the demonstration wrote its file and
  exited 0, and the report's claim became false.  The invariant was fine; the
  demonstration was time-dependent.
* DEFECT B - the snapshot diagnosis published
  ``CYCLE_39116225867_regression_scope.json`` among the artifacts that produce
  PASS/PASS for ``check_regression_set_relation``.  It FAILs (n_repaired_only=1).
  The list was hand-written from a COPY of the gate's three expressions, and the
  copy drifted.

These tests make both reproducible forever, and make the corrected claims
machine-enforced in the shipped ledger (``cycle_verify``'s ``regression_matrix``
check recomputes the classification the diagnosis publishes).
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

from product import cycle_verify as cv
from product.regression_set_relation_matrix import classify_all, render

ROOT = Path(__file__).resolve().parents[2]
DIAGNOSIS = ROOT / "results" / "product" / "orchestration" / "CYCLE_39116225867_snapshot_diagnosis.json"
FAILING = "CYCLE_39116225867_regression_scope.json"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# --------------------------------------------------------------------------
# DEFECT B - the artifact classification is derived, not written by hand
# --------------------------------------------------------------------------

def test_the_artifact_the_diagnosis_called_pass_pass_actually_fails():
    """The exact DEFECT B claim, inverted: 39116225867 must NOT be PASS/PASS.

    It records n_repaired_only = 1, so the gate's first claim fails.  This test
    is the reason the diagnosis can no longer list it.
    """
    rows = {r["name"]: r for r in classify_all()["rows"]}
    assert FAILING in rows, sorted(rows)
    row = rows[FAILING]
    assert row["all_pass"] is False
    assert row["verdicts"] == ["FAIL", "PASS", "PASS"], row
    assert any("no failing test id absent from the baseline" in c for c in row["any_fail"])


def test_the_matrix_agrees_with_the_gate_on_every_committed_artifact():
    """No copy of the predicate may exist anywhere: the matrix imports the gate's."""
    matrix = classify_all()
    assert matrix["rows"], "no committed regression artifact found"
    for row in matrix["rows"]:
        art = ROOT / row["artifact"]
        data = json.loads(art.read_text(encoding="utf-8"))
        direct = [r["status"] for r in cv.regression_set_relation_rows(art, data)]
        assert row["verdicts"] == direct, row["name"]
        assert row["all_pass"] is all(v == "PASS" for v in direct), row["name"]


def test_the_newest_artifact_the_live_gate_reads_is_classified_too():
    matrix = classify_all()
    newest = matrix["newest"]["name"]
    candidates = sorted((ROOT / "results" / "product" / "regression").glob("CYCLE_*_regression_scope.json"))
    assert candidates[-1].name == newest
    assert matrix["newest"]["all_pass"] is True


def test_the_diagnosis_publishes_only_artifacts_that_really_pass():
    """The ledger claim ``regression_matrix`` enforces, asserted directly."""
    rows = cv.check_regression_matrix_matches_diagnosis()
    assert rows, "the matrix check returned no claims"
    assert all(r["status"] == "PASS" for r in rows), [r for r in rows if r["status"] != "PASS"]


def test_a_later_artifact_does_not_force_an_edit_to_the_historical_diagnosis(monkeypatch, tmp_path):
    """Direction matters: the diagnosis is a point-in-time record.

    Every cycle commits a new regression artifact that is PASS/PASS.  Requiring
    the reverse direction ("everything passing today is listed") made this very
    repair's own regression run fail its own suite - the self-referential class
    the diagnosis is about.  Additive artifacts must be DISCLOSED, not banned.
    """
    matrix = classify_all()
    extra = [r["name"] for r in matrix["rows"] if r["all_pass"]]
    assert extra, "no passing artifact to work with"

    data = json.loads(DIAGNOSIS.read_text(encoding="utf-8"))
    data["run_id_diagnosing"] = 1  # everything looks "committed after" the record
    victim = tmp_path / "diagnosis.json"
    victim.write_text(json.dumps(data), encoding="utf-8")
    monkeypatch.setattr(cv, "DIAGNOSIS_39116225867_ARTIFACT", victim)
    rows = cv.check_regression_matrix_matches_diagnosis()
    assert all(r["status"] == "PASS" for r in rows), [r for r in rows if r["status"] != "PASS"]


def test_dropping_an_artifact_that_existed_at_diagnosis_time_is_caught(monkeypatch, tmp_path):
    """Completeness IS enforced in the direction that can be known."""
    data = json.loads(DIAGNOSIS.read_text(encoding="utf-8"))
    data["run_id_diagnosing"] = 99_999_999_999  # later than every artifact in the tree
    listed = data["classification"]["evidence"][
        _produce_pass_pass_index(data)]["observed"]["produce_pass_pass"]
    dropped_name = listed.pop()
    assert dropped_name in listed or True  # the removed entry is the dropped one
    victim = tmp_path / "diagnosis.json"
    victim.write_text(json.dumps(data), encoding="utf-8")
    monkeypatch.setattr(cv, "DIAGNOSIS_39116225867_ARTIFACT", victim)
    rows = cv.check_regression_matrix_matches_diagnosis()
    failed = [r for r in rows if r["status"] != "PASS"]
    assert failed, "an incomplete published list passed"
    assert any(dropped_name in json.dumps(r["observed"]) for r in failed)


def _produce_pass_pass_index(data: dict) -> int:
    for i, ev in enumerate(data["classification"]["evidence"]):
        if "produce_pass_pass" in (ev.get("observed") or {}):
            return i
    raise AssertionError("the diagnosis has no produce_pass_pass list")


def test_a_later_artifact_that_FAILS_is_still_caught(monkeypatch, tmp_path):
    """Additive tolerance must not extend to a later artifact that fails."""
    data = json.loads(DIAGNOSIS.read_text(encoding="utf-8"))
    data["run_id_diagnosing"] = 1
    hits: list = []
    _add_to_lists(data, "produce_pass_pass", FAILING, hits)
    victim = tmp_path / "diagnosis.json"
    victim.write_text(json.dumps(data), encoding="utf-8")
    monkeypatch.setattr(cv, "DIAGNOSIS_39116225867_ARTIFACT", victim)
    rows = cv.check_regression_matrix_matches_diagnosis()
    assert any(r["status"] != "PASS" for r in rows)


def test_run_id_of_reads_the_cycle_number_or_nothing():
    assert cv._run_id_of("CYCLE_39119287975_regression_scope.json") == 39119287975
    assert cv._run_id_of("CYCLE_39123358661_cycle_verify.json") == 39123358661
    assert cv._run_id_of(None) is None
    assert cv._run_id_of("no number here") is None


def _add_to_lists(node, key: str, extra: str, hits: list) -> None:
    """Mutate every ``key`` list in a parsed tree wherever it is nested."""
    if isinstance(node, dict):
        for k, v in node.items():
            if k == key and isinstance(v, list):
                v.append(extra)
                hits.append(v)
            _add_to_lists(v, key, extra, hits)
    elif isinstance(node, list):
        for item in node:
            _add_to_lists(item, key, extra, hits)


def test_the_matrix_check_fails_when_the_diagnosis_republishes_the_false_entry(monkeypatch, tmp_path):
    """Non-vacuity: re-inserting the DEFECT B line must turn the ledger red."""
    data = json.loads(DIAGNOSIS.read_text(encoding="utf-8"))
    hits: list = []
    _add_to_lists(data, "produce_pass_pass", FAILING, hits)
    assert hits, "the mutation found no produce_pass_pass list to corrupt"
    victim = tmp_path / "diagnosis.json"
    victim.write_text(json.dumps(data), encoding="utf-8")
    monkeypatch.setattr(cv, "DIAGNOSIS_39116225867_ARTIFACT", victim)

    rows = cv.check_regression_matrix_matches_diagnosis()
    failed = [r for r in rows if r["status"] != "PASS"]
    assert failed, "the check passed a diagnosis that republishes the false entry"
    assert any(FAILING in json.dumps(r["observed"], default=str) for r in failed)


def test_the_matrix_check_fails_on_a_duplicated_list(monkeypatch, tmp_path):
    """Two lists cannot be compared to one recomputed set, so the check refuses."""
    data = json.loads(DIAGNOSIS.read_text(encoding="utf-8"))
    data["classification"]["evidence"].append(
        {"claim": "a second, conflicting list", "observed": {"produce_pass_pass": []}})
    victim = tmp_path / "diagnosis.json"
    victim.write_text(json.dumps(data), encoding="utf-8")
    monkeypatch.setattr(cv, "DIAGNOSIS_39116225867_ARTIFACT", victim)
    rows = cv.check_regression_matrix_matches_diagnosis()
    assert len(rows) == 1 and rows[0]["status"] == "FAIL"


def test_the_matrix_check_fails_when_the_diagnosis_artifact_is_missing(monkeypatch, tmp_path):
    monkeypatch.setattr(cv, "DIAGNOSIS_39116225867_ARTIFACT", tmp_path / "absent.json")
    rows = cv.check_regression_matrix_matches_diagnosis()
    assert len(rows) == 1 and rows[0]["status"] == "FAIL"


def test_the_diagnosis_never_publishes_a_failing_artifact_as_pass_pass():
    """DEFECT B as a standing property of the record, independent of the tool."""
    diag = json.loads(DIAGNOSIS.read_text(encoding="utf-8"))
    published = set()
    for ev in diag["classification"]["evidence"]:
        published |= set(ev.get("produce_pass_pass") or [])
    assert FAILING not in published, (
        "DEFECT B: the diagnosis publishes the genuinely failing artifact as PASS/PASS")


def test_the_report_of_record_shows_no_unpinned_refusal_demonstration():
    """DEFECT A as a standing property of the prose.

    The false claim had two shapes: a fenced command block running
    ``--only regression --run-id 99999999999 --write`` with nothing pinned, and
    a prose arrow claiming it "→ refused, exit 1, no file written".  Both are
    forbidden.  A fenced block must carry ``--regression-dir`` whenever it runs
    the refusal demonstration.  The correction text is allowed to QUOTE the old
    command while stating that it was time-dependent - that is the correction
    working, not the defect returning.
    """
    text = (ROOT / "reports" / "product" / "CYCLE_39119287975.md").read_text(encoding="utf-8")
    blocks = re.findall(r"```[a-z]*\n(.*?)```", text, flags=re.S)
    offenders = []
    for block in blocks:
        flat = " ".join(block.split())
        if "99999999999" in flat and "--write" in flat and "--regression-dir" not in flat:
            offenders.append(flat)
    assert not offenders, f"DEFECT A: unpinned refusal demonstration in a command block: {offenders}"
    assert "→ refused, exit 1, no file written" not in text, (
        "DEFECT A: the old prose arrow claim is still present")
    assert "--regression-dir product/data/regression_fail_fixture" in " ".join(
        " ".join(b.split()) for b in blocks), (
        "DEFECT A: the corrected, pinned demonstration is not shown as a command")


# --------------------------------------------------------------------------
# DEFECT A - the refusal demonstration is pinned, not time-dependent
# --------------------------------------------------------------------------

def test_the_pinned_fail_fixture_is_a_byte_copy_of_the_failing_artifact():
    """The fixture must be the REAL committed failing artifact, not a hand-made one."""
    src = ROOT / "results" / "product" / "regression" / FAILING
    dst = cv.FAIL_FIXTURE_DIR / FAILING
    assert dst.is_file(), f"missing pinned failing fixture: {dst}"
    assert _sha256(src) == _sha256(dst), (
        "the pinned fixture drifted from the committed artifact it copies")


def test_the_pinned_fail_fixture_really_fails_the_gate():
    rows = cv.regression_set_relation_rows(
        cv.FAIL_FIXTURE_DIR / FAILING,
        json.loads((cv.FAIL_FIXTURE_DIR / FAILING).read_text(encoding="utf-8")))
    assert rows[0]["status"] == "FAIL", rows
    assert rows[0]["observed"]["repaired_only_new_failures"], rows[0]["observed"]


def test_the_demonstrated_invocation_still_refuses_and_writes_nothing(monkeypatch, tmp_path, capsys):
    """The exact corrected demonstration, run in-process: refused, exit 1, no file.

    It is deterministic because it reads a PINNED failing artifact, so unlike the
    original it cannot silently turn into a PASS when a later clean artifact lands.
    """
    canonical = tmp_path / "canonical"
    canonical.mkdir()
    monkeypatch.setattr(cv, "DEFAULT_OUT_DIR", canonical)
    rc = cv.main(["--only", "regression",
                 "--regression-dir", str(cv.FAIL_FIXTURE_DIR),
                 "--run-id", "99999999999", "--write"])
    assert rc == 1
    assert list(canonical.glob("*.json")) == []
    assert "REFUSED" in capsys.readouterr().err


def test_the_same_invocation_against_the_canonical_dir_is_a_pass(monkeypatch, tmp_path):
    """Non-vacuity of the demonstration itself: the FAIL is the fixture's doing."""
    canonical = tmp_path / "canonical"
    canonical.mkdir()
    monkeypatch.setattr(cv, "DEFAULT_OUT_DIR", canonical)
    rc = cv.main(["--only", "regression", "--run-id", "99999999999", "--write"])
    assert rc == 0
    assert (canonical / "CYCLE_99999999999_cycle_verify.json").is_file()


def test_the_regression_dir_override_never_leaks_into_the_next_invocation(monkeypatch, tmp_path):
    """A demonstration flag must not change what the ordinary ledger reads."""
    monkeypatch.setattr(cv, "DEFAULT_OUT_DIR", tmp_path)
    assert cv.main(["--only", "regression", "--regression-dir", str(cv.FAIL_FIXTURE_DIR),
                    "--run-id", "1", "--json"]) == 1
    assert cv.REGRESSION_DIR_OVERRIDE is None
    ledger = cv.run(["regression"])
    assert ledger["verdict"] == "PASS", ledger
    assert all("regression_fail_fixture" not in json.dumps(r["observed"], default=str)
               for r in ledger["claims"])


def test_an_override_in_flight_is_restored_even_when_a_check_raises(monkeypatch, tmp_path):
    """The restore lives in a finally: a blow-up must not leave the gate repointed."""
    monkeypatch.setattr(cv, "DEFAULT_OUT_DIR", tmp_path)
    monkeypatch.setitem(cv.CHECKS, "boom", lambda: (_ for _ in ()).throw(RuntimeError("kaboom")))
    assert cv.main(["--only", "boom", "--regression-dir", str(cv.FAIL_FIXTURE_DIR),
                    "--run-id", "1", "--json"]) == 1
    assert cv.REGRESSION_DIR_OVERRIDE is None


def test_the_demonstration_runs_as_the_documented_command():
    """End-to-end in a subprocess: the exact line the report publishes."""
    proc = subprocess.run(  # noqa: S603
        [sys.executable, "product/cycle_verify.py", "--only", "regression",
         "--regression-dir", "product/data/regression_fail_fixture",
         "--run-id", "99999999999", "--write"],
        cwd=str(ROOT), capture_output=True, text=True, timeout=600, check=False)
    assert proc.returncode == 1, proc.stdout + proc.stderr
    assert "REFUSED" in proc.stderr
    assert not (ROOT / "results" / "product" / "cycle_verify"
                / "CYCLE_99999999999_cycle_verify.json").exists(), (
        "the refused demonstration actually wrote into the canonical directory")


def test_the_original_time_dependent_invocation_is_now_a_documented_pass(monkeypatch, tmp_path):
    """DEFECT A, stated as the property it actually has.

    ``--only regression --run-id 99999999999 --write`` FAILS only while the
    newest regression artifact records a new failure.  That is why it stopped
    reproducing.  The refusal is unchanged and is what the pinned fixture
    demonstrates; this test pins the fact that made the old demo fragile, so a
    future reader sees the dependency instead of rediscovering it.
    """
    canonical = tmp_path / "canonical"
    canonical.mkdir()
    monkeypatch.setattr(cv, "DEFAULT_OUT_DIR", canonical)
    rc = cv.main(["--only", "regression", "--run-id", "99999999999", "--write"])
    assert rc == 0
    written = canonical / "CYCLE_99999999999_cycle_verify.json"
    assert written.is_file()
    assert json.loads(written.read_text(encoding="utf-8"))["verdict"] == "PASS"


def test_pointing_the_same_invocation_at_a_failing_artifact_is_what_makes_it_fail(monkeypatch, tmp_path):
    """Non-vacuity of the demonstration: identical arguments, different verdict."""
    canonical = tmp_path / "canonical"
    canonical.mkdir()
    monkeypatch.setattr(cv, "DEFAULT_OUT_DIR", canonical)
    rc = cv.main(["--only", "regression", "--regression-dir", str(cv.FAIL_FIXTURE_DIR),
                  "--run-id", "99999999999", "--write"])
    assert rc == 1
    assert list(canonical.glob("*.json")) == []


def test_the_rendered_table_says_which_artifact_the_live_gate_reads():
    out = render(classify_all(), None)
    assert "newest" in out and FAILING in out
    assert "produce PASS/PASS" in out


def test_the_matrix_tool_runs_standalone_and_is_deterministic():
    a = subprocess.run([sys.executable, "product/regression_set_relation_matrix.py", "--json"],
                       cwd=str(ROOT), capture_output=True, text=True, timeout=300, check=False)
    b = subprocess.run([sys.executable, "product/regression_set_relation_matrix.py", "--json"],
                       cwd=str(ROOT), capture_output=True, text=True, timeout=300, check=False)
    assert a.returncode == 0, a.stderr
    assert a.stdout == b.stdout, "the matrix is not deterministic across runs"
    parsed = json.loads(a.stdout)
    assert parsed["schema"] == "product-regression-set-relation-matrix/1"
    assert FAILING in parsed["any_fail"]
    assert FAILING not in parsed["pass_pass"]


def test_an_empty_regression_directory_is_a_failure_not_an_empty_pass(tmp_path):
    empty = classify_all(tmp_path)
    assert empty["n_artifacts"] == 0
    assert empty["pass_pass"] == [] and empty["any_fail"] == []
    assert empty["newest"] is None
    rows = cv.regression_set_relation_rows(tmp_path / "absent.json", {})
    assert all(r["status"] == "FAIL" for r in rows), rows
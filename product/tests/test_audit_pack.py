"""Regression tests for the product-owned audit pack (``product/audit_pack.py``).

Why this module exists
----------------------
Five product cycles produced a team snapshot with **no** persisted audit
verdict.  The pack is the producer-side mitigation: one command that recomputes
every v52 endgame claim from committed artifacts in seconds, so the independent
auditor verifies instead of reconstructing under a 45-minute work quantum
(``LEX_WORK_QUANTUM_EXPIRED`` killed the audit of run 39034350468).

A mitigation that reports *its own* environment problems as product failures is
worse than no mitigation: it invites a wrong verdict.  ``core-lane.yml`` has no
``actions/setup-python`` and no ``pip install`` step in either the team or the
audit job, so the audit checkout may legitimately have no numpy.  In this very
run, before the fix, six checks died with ``ModuleNotFoundError`` and printed as
plain ``FAIL`` -- one with an empty reason, because the check swallowed the
import error and returned ``ok=False``.

What is frozen here
-------------------
1. environment triage: a missing import is ``BLOCKED_MISSING_DEPENDENCY``, never
   a product failure, and the counters keep the two apart;
2. the exit-code contract (0 / 1 / 2 / 3);
3. ``CheckBlocked``: a check that cannot conclude declares itself blocked and
   still reports its dependency-free measurement;
4. the auditor write scope is exactly the two relative paths the workflow allows;
5. state/run coherence, including the ``--run-id local`` exemption;
6. the dependency-blind path really does survive without numpy installed, proven
   by blocking the import in a subprocess rather than by monkeypatching.
"""
from __future__ import annotations

import json
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from product import audit_pack as ap  # noqa: E402


# --------------------------------------------------------------------------- #
# 1. environment triage
# --------------------------------------------------------------------------- #
def test_classify_separates_missing_import_from_a_real_failure():
    assert ap.classify(ModuleNotFoundError("No module named 'numpy'", name="numpy")) == ap.STATUS_BLOCKED
    assert ap.classify(ImportError("cannot import name 'qmap'")) == ap.STATUS_BLOCKED
    assert ap.classify(ap.CheckBlocked("no verdict", blocked_by="numpy")) == ap.STATUS_BLOCKED
    assert ap.classify(ValueError("bundle is malformed")) == ap.STATUS_FAIL


def test_missing_module_finds_the_name_through_a_cause_chain():
    root_cause = ModuleNotFoundError("No module named 'sklearn'", name="sklearn")
    try:
        try:
            raise root_cause
        except ModuleNotFoundError as inner:
            raise RuntimeError("importing the vendor failed") from inner
    except RuntimeError as outer:
        assert ap._missing_module(outer) == "sklearn"
    assert ap._missing_module(ValueError("nope")) is None


def test_run_checks_reports_a_blocked_check_as_blocked_not_failed(monkeypatch):
    """The core defect: an environment fact must not read as a broken product."""
    def _explodes(root):
        raise ModuleNotFoundError("No module named 'numpy'", name="numpy")

    monkeypatch.setattr(ap, "CHECKS", (("synthetic_needs_numpy", _explodes),))
    (rec,) = ap.run_checks(ROOT, include_tests=False, run_id="39042713389")

    assert rec["ok"] is False
    assert rec["status"] == ap.STATUS_BLOCKED
    assert rec["blocked_by"] == "numpy"
    assert rec["bootstrap_command"] == ap.BOOTSTRAP_COMMAND
    # ...and the summary must not count it as a product failure.
    summary = ap.summarise([rec])
    assert summary["n_failed"] == 0
    assert summary["n_blocked_missing_dependency"] == 1
    assert summary["blocked_ids"] == ["synthetic_needs_numpy"]
    assert summary["no_product_failure"] is True


def test_summarise_keeps_blocked_and_failed_apart():
    checks = [
        {"id": "a", "ok": True, "status": ap.STATUS_OK},
        {"id": "b", "ok": False, "status": ap.STATUS_FAIL},
        {"id": "c", "ok": False, "status": ap.STATUS_BLOCKED},
        {"id": "d", "ok": True, "status": ap.STATUS_SKIPPED},
    ]
    summary = ap.summarise(checks)
    assert (summary["n_passed"], summary["n_failed"],
            summary["n_blocked_missing_dependency"], summary["n_skipped"]) == (1, 1, 1, 1)
    assert summary["failed_ids"] == ["b"] and summary["blocked_ids"] == ["c"]
    assert summary["all_ok"] is False and summary["no_product_failure"] is False


# --------------------------------------------------------------------------- #
# 2. exit-code contract
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("summary,expected", [
    ({"all_ok": True, "n_failed": 0, "n_blocked_missing_dependency": 0}, 0),
    ({"all_ok": False, "n_failed": 2, "n_blocked_missing_dependency": 0}, 1),
    ({"all_ok": False, "n_failed": 0, "n_blocked_missing_dependency": 6}, 2),
    # a product failure outranks a blocked check
    ({"all_ok": False, "n_failed": 1, "n_blocked_missing_dependency": 6}, 1),
])
def test_exit_code_contract(summary, expected):
    assert ap.exit_code_for(summary) == expected


def test_main_writes_a_pack_and_reports_exit_zero(tmp_path):
    out = tmp_path / "pack.json"
    rc = ap.main(["--run-id", "local", "--no-tests", "--out", str(out)])
    pack = json.loads(out.read_text(encoding="utf-8"))
    assert rc == pack["exit_code"]
    assert pack["schema"] == ap.SCHEMA
    assert pack["all_ok"] is True, [c for c in pack["checks"] if not c["ok"]]
    assert pack["no_product_failure"] is True


def test_main_refuses_to_clobber_an_existing_pack_artifact(tmp_path):
    """A committed pack is evidence of the run that wrote it (AGENTS.md 6).

    Regression from run 39042713389: a convenience re-run with ``--run-id local``
    silently overwrote run 39039195228's committed ``CYCLE_local_pack.json``.
    """
    out = tmp_path / "pack.json"
    assert ap.main(["--run-id", "local", "--no-tests", "--out", str(out)]) == 0
    original = out.read_text(encoding="utf-8")

    rc = ap.main(["--run-id", "local", "--no-tests", "--out", str(out)], )
    assert rc == 3
    assert out.read_text(encoding="utf-8") == original, "refused run still modified the artifact"

    # --force is the explicit, deliberate escape hatch
    assert ap.main(["--run-id", "local", "--no-tests", "--out", str(out), "--force"]) == 0


def test_default_out_path_is_namespaced_by_run_id():
    assert ap.default_out_path("39042713389").name == "CYCLE_39042713389_pack.json"
    assert ap.default_out_path("39042713389").parent.name == "audit_pack"
    assert ap.default_out_path("local").name == "CYCLE_local_pack.json"


# --------------------------------------------------------------------------- #
# 3. CheckBlocked carries its evidence
# --------------------------------------------------------------------------- #
def test_check_blocked_rides_along_with_its_measurement():
    exc = ap.CheckBlocked("inconclusive", blocked_by="numpy", measured={"violations": None})
    assert ap.classify(exc) == ap.STATUS_BLOCKED
    assert ap._blocked_module(exc) == "numpy"
    assert exc.measured == {"violations": None}


def test_readiness_guard_never_swallows_an_import_error_into_a_verdict(monkeypatch):
    """The specific instance found in run 39042713389.

    ``readiness_claim_guard`` catches every exception from ``recheck_packet``.
    When that is an import failure the check used to return ``ok=False`` -- the
    same verdict it returns for a genuine readiness violation.
    """
    import product.gate_packet as gp

    monkeypatch.setattr(
        gp, "recheck_packet",
        lambda *a, **k: (_ for _ in ()).throw(
            ModuleNotFoundError("No module named 'numpy'", name="numpy")),
    )
    with pytest.raises(ap.CheckBlocked) as caught:
        ap.check_readiness_claim_guard(ROOT, "39042713389")
    assert caught.value.blocked_by == "numpy"
    # the dependency-free half of the computation is still reported
    measured = caught.value.measured
    assert measured["violations"] is None
    assert measured["n_occurrences"] >= 1
    assert measured["blocked_rechecks"], measured["blocked_rechecks"]


# --------------------------------------------------------------------------- #
# 4. auditor write scope
# --------------------------------------------------------------------------- #
def test_auditor_write_scope_is_exactly_the_two_workflow_allowed_paths():
    assert ap.AUDITOR_WRITE_SCOPE == (
        "results/audit/product/CYCLE_<run_id>_GATE.json",
        "reports/audit/product/CYCLE_<run_id>.md",
    )
    for path in ap.AUDITOR_WRITE_SCOPE:
        assert path.startswith(("results/audit/product/", "reports/audit/product/"))
        assert not Path(path).is_absolute()


def test_producer_has_committed_no_audit_artifact_for_this_run():
    rec = dict(zip((n for n, _ in ap.CHECKS),
                   ap.run_checks(ROOT, include_tests=False, run_id="39042713389"))) \
        ["producer_wrote_no_audit_artifact"]
    assert rec["ok"] is True, rec.get("measured")


# --------------------------------------------------------------------------- #
# 5. state/run coherence
# --------------------------------------------------------------------------- #
def test_state_run_coherence_rejects_a_state_that_names_another_run(tmp_path):
    state_dir = tmp_path / "state"
    state_dir.mkdir()
    (state_dir / "product.json").write_text(json.dumps({
        "current_run": "39034350468",
        "state_updated_by_run": "39034350468",
    }), encoding="utf-8")
    ok, measured, _expected, _detail, _evidence = ap.check_state_run_coherence(tmp_path, "39042713389")
    assert ok is False
    assert measured["enforced"] is True
    assert set(measured["mismatched"]) == {"current_run", "state_updated_by_run"}
    assert "cannot tell which cycle is speaking" in measured["verdict"]


def test_state_run_coherence_accepts_the_current_run(tmp_path):
    state_dir = tmp_path / "state"
    state_dir.mkdir()
    (state_dir / "product.json").write_text(json.dumps({
        "current_run": "39042713389",
        "state_updated_by_run": "39042713389",
    }), encoding="utf-8")
    ok, measured, _e, _d, _v = ap.check_state_run_coherence(tmp_path, "39042713389")
    assert ok is True and measured["mismatched"] is None


def test_state_run_coherence_is_not_enforced_for_an_unnumbered_local_run(tmp_path):
    state_dir = tmp_path / "state"
    state_dir.mkdir()
    (state_dir / "product.json").write_text(json.dumps({"current_run": "39034350468"}),
                                            encoding="utf-8")
    ok, measured, _e, _d, _v = ap.check_state_run_coherence(tmp_path, "local")
    assert ok is True
    assert measured["enforced"] is False
    assert measured["verdict"].startswith("SKIPPED_NO_RUN_ID")


def test_repository_state_names_the_run_that_wrote_it():
    """The live tree must satisfy the rule the resumed snapshot violated."""
    run_id = "39042713389"
    ok, measured, _e, detail, _v = ap.check_state_run_coherence(ROOT, run_id)
    assert ok is True, detail or measured


# --------------------------------------------------------------------------- #
# 6. the dependency-blind path, proven by actually removing numpy
# --------------------------------------------------------------------------- #
_BLOCKER = '''
import sys
_BLOCKED = {"numpy", "scipy", "sklearn"}
class _Blocker:
    def find_spec(self, name, path=None, target=None):
        if name.split(".")[0] in _BLOCKED:
            raise ModuleNotFoundError("No module named %r" % name, name=name)
        return None
sys.meta_path.insert(0, _Blocker())
'''


def test_pack_survives_a_checkout_without_numpy(tmp_path):
    """The exact condition of a bare audit job, exercised for real.

    Before run 39042713389 this printed six plain ``FAIL`` lines and exited 1.
    The contract now is: no PRODUCT failure, every dependency-bound check
    blocked, and a bootstrap command the auditor can run in one step.
    """
    blocker = tmp_path / "sitecustomize.py"
    blocker.write_text(textwrap.dedent(_BLOCKER), encoding="utf-8")
    out = tmp_path / "bare_pack.json"
    env = {"PYTHONPATH": str(tmp_path), "PATH": "/usr/bin:/bin", "HOME": str(tmp_path)}
    proc = subprocess.run(
        [sys.executable, "-S", "product/audit_pack.py", "--run-id", "local",
         "--no-tests", "--bootstrap-deps", "off", "--out", str(out)],
        cwd=str(ROOT), capture_output=True, text=True, env=env, timeout=300, check=False,
    )
    assert out.is_file(), proc.stderr[-2000:]
    pack = json.loads(out.read_text(encoding="utf-8"))

    assert pack["n_failed"] == 0, [c for c in pack["checks"] if c["status"] == ap.STATUS_FAIL]
    assert pack["n_blocked_missing_dependency"] >= 4, pack["blocked_ids"]
    assert pack["no_product_failure"] is True
    assert proc.returncode == 2, proc.stdout[-2000:]

    blocked = [c for c in pack["checks"] if c["status"] == ap.STATUS_BLOCKED]
    for check in blocked:
        assert check["blocked_by"], check
        assert check["bootstrap_command"] == ap.BOOTSTRAP_COMMAND
        # the reason always names the module that was absent (ModuleNotFoundError
        # directly, or CheckBlocked wrapping it for readiness_claim_guard)
        assert check["blocked_by"] in check["error"], check
        assert "ModuleNotFoundError" in check["error"] or check["error"].startswith("CheckBlocked:")
    # the dependency-free checks must still have proven something
    passed = {c["id"] for c in pack["checks"] if c["status"] == ap.STATUS_OK}
    assert {"frozen_rubric_rehash", "do_not_serve_order_stands", "state_contract"} <= passed
    assert pack["dependencies"]["missing"], pack["dependencies"]


def test_dependency_preflight_reports_complete_when_installed():
    status = ap.dependency_status()
    assert status["complete"] is (not status["missing"]), status
    assert status["requirements_file_present"] is True
    assert status["why"]
    assert ap.BOOTSTRAP_COMMAND == "python3 -m pip install -r product/requirements-query.txt"


def test_failure_note_never_prints_an_empty_reason():
    """Regression: the console used to print '' for a tuple-style failure."""
    assert ap._failure_note({"ok": False, "measured": {"error": "boom"}, "detail": ""})
    assert "boom" in ap._failure_note({"ok": False, "measured": {"error": "boom"}})
    assert "INCOHERENT" in ap._failure_note(
        {"ok": False, "detail": "x", "measured": {"verdict": "INCOHERENT: ..."}})
    assert ap._failure_note({"ok": False, "detail": "", "measured": {}})


# --------------------------------------------------------------------------- #
# 7. the known-failing baseline is a baseline, not a whitelist
# --------------------------------------------------------------------------- #
def test_known_baseline_is_recorded_with_a_reason_for_every_entry():
    assert ap.KNOWN_BASELINE_FAILURES, "an empty baseline would assert nothing"
    for test_id, reason in ap.KNOWN_BASELINE_FAILURES.items():
        assert test_id.startswith("product/tests/"), test_id
        assert "::" in test_id, test_id
        assert len(reason) > 20, f"{test_id} has no stated reason"
        module = test_id.split("::")[0]
        assert module in ap.BASELINE_TEST_MODULES, test_id
        assert (ROOT / module).is_file(), module


def test_known_baseline_check_reports_no_new_failure_on_the_live_tree():
    ok, measured, expected, detail, evidence = ap.check_known_baseline_test_failures(ROOT)
    assert ok is True, (measured.get("new_failures"), detail)
    assert measured["new_failures"] is None
    assert measured["n_observed"] == measured["n_baseline"] == len(ap.KNOWN_BASELINE_FAILURES)
    assert set(evidence) <= set(ap.BASELINE_TEST_MODULES)


def test_known_baseline_check_would_catch_a_new_failure(monkeypatch, tmp_path):
    """Negative control: the baseline must not silently absorb a regression."""
    payload = ("FAILED product/tests/test_cache_non_orphan.py::test_brand_new_regression - x\n"
               "FAILED product/tests/test_audit_seam.py::test_known_dead_models_agree_with_control_plane_health - y\n"
               "1 failed\n")
    monkeypatch.setattr(ap.subprocess, "run",
                        lambda *a, **k: type("P", (), {"stdout": payload, "stderr": "",
                                                      "returncode": 1})())
    ok, measured, _e, detail, _v = ap.check_known_baseline_test_failures(ROOT)
    assert ok is False
    assert measured["new_failures"] == [
        "product/tests/test_cache_non_orphan.py::test_brand_new_regression"]
    # the 7 baseline entries that did not run are reported as drift, not failure
    assert len(measured["baseline_now_passing"]) == len(ap.KNOWN_BASELINE_FAILURES) - 1
    assert "NEW failure" in detail


# --------------------------------------------------------------------------- #
# 8. the pack is green on the live tree, and declares no silent coverage loss
# --------------------------------------------------------------------------- #
def test_declared_core_test_modules_all_exist():
    missing = [m for m in ap.CORE_TEST_MODULES if not (ROOT / m).is_file()]
    assert not missing, f"declared but absent (the subset would silently shrink): {missing}"


def test_live_pack_is_green():
    pack = ap.build_pack(include_tests=False, run_id="local")
    failing = [(c["id"], c.get("error") or c.get("measured"))
               for c in pack["checks"] if not c["ok"]]
    assert not failing, failing
    assert pack["exit_code"] == 0
    assert pack["claim_ceiling"]
    assert "not_claimable" in pack and len(pack["not_claimable"]) == 3
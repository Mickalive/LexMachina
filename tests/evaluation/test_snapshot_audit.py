"""Snapshot audit-readiness verifier: integration plus per-check breaking fixtures.

Discipline: every check has a synthetic input that makes it FAIL (a green
that cannot go red is not evidence). The integration test needs the accepted
product mount, exactly like the frozen-bar gate tests.
"""
import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

from evaluation.frozen_bars.run_bar_gates import QIDS, SERVED_PACKET_DIR
from evaluation.snapshot_audit import run_snapshot_audit as rsa
from evaluation.snapshot_audit import write_scope as ws

MOUNT_AVAILABLE = all((SERVED_PACKET_DIR / f"{qid}.bundle.json").exists() for qid in QIDS)
needs_mount = pytest.mark.skipif(not MOUNT_AVAILABLE, reason="accepted product mount absent")

CHECK_IDS = {
    "frozen_rubric_rehash",
    "bar_gates_verdict",
    "h1_default_record_identity",
    "lane_suite_pass",
    "state_evidence_refs_resolve",
    "deliverable_manifest_complete",
    "orchestration_diagnosis_record",
    "producer_write_scope_clean",
    "write_scope_diagnosis_record",
    "orchestration_diagnosis_38986445355",
    "retrieval_ca_benchmark_record",
    # run 38993062549 added check_gate_validity_sweep to the verifier but this
    # set was not extended, so the suite has been RED (1 failed / 25 passed) on
    # the accepted tree since that commit. Verified pre-existing by stashing this
    # cycle's work and re-running at 21b64ad0. Set-completeness repair only: the
    # verifier's behaviour is unchanged and no check was weakened or removed.
    "gate_validity_sweep",
    # run 39004097533: the counter-authority label falsification (PRODUCT_FALSIFIED
    # plus five fired gate predicates) is pinned so it cannot be softened silently.
    "counter_authority_label_benchmark",
    # run 39010105493 (completed by resume run 39012970379): the packet-admission
    # conformance falsification, its live re-execution, and the diagnosis of the
    # producer step that died before it could write its own report and state.
    "packet_admission_conformance",
    "packet_admission_conformance_reexecution",
    "orchestration_diagnosis_39010105493",
    # run 39043684319 (operational resume of 39040205229): every orchestration
    # diagnosis must PARSE. Added after the 39027041693 record was found
    # committed truncated, which four consecutive readiness records reported as
    # clean because no check had ever parsed it. The same check also requires
    # run 39040205229's diagnosis to keep the quantum falsification.
    "diagnosis_artifacts_all_parse",
    # run 39043684319: the accepted evaluation branch head carries one ungated
    # run (39027041693). The check re-derives it from git and requires the gap
    # to stay DISCLOSED, so a NEW ungated run at the head goes red.
    "accepted_base_gate_coverage_recorded",
}


# ---------------------------------------------------------------- fixtures --

def _fake_root(tmp_path: Path, rules_bytes: bytes = b'{"tampered": true}',
               vendored_files: dict | None = None) -> Path:
    """Minimal fake repo root carrying the three rubric-path files."""
    bar = tmp_path / "evaluation/frozen_bars"
    bar.mkdir(parents=True)
    (bar / "RULES_LABEL.json").write_bytes(rules_bytes)
    (bar / "RULES_GEOMETRY.json").write_bytes(rules_bytes)
    vend = bar / "vendored"
    vend.mkdir()
    if vendored_files is None:
        vendored_files = {
            "evaluation/frozen_bars/RULES_LABEL.json":
                __import__("hashlib").sha256(rules_bytes).hexdigest(),
            "evaluation/frozen_bars/RULES_GEOMETRY.json":
                __import__("hashlib").sha256(rules_bytes).hexdigest(),
        }
    (vend / "VENDORED_SHA256.json").write_text(json.dumps({"files": vendored_files}))
    return tmp_path


def _minimal_valid_diagnosis() -> dict:
    return {
        "schema": "lex-evaluation-orchestration-diagnosis/1",
        "query_method": "test-double",
        "limits": "test-double",
        "runs": {
            "38972887369": {"conclusion": "failure",
                            "jobs": {"audit": {"failed_step": "Run lane cycle"}}},
            "38977570612": {"conclusion": "failure",
                             "jobs": {"audit": {"failed_step": "Enforce audit scope and read gate",
                                                "ambiguity_flag": "logs 403; two candidate causes"}}},
        },
    }


# ------------------------------------------------------- breaking fixtures --

def test_rubric_rehash_fails_on_tampered_bytes(tmp_path):
    root = _fake_root(tmp_path)
    res = rsa.check_rubric_rehash(root)
    assert res["status"] == "FAIL"
    assert res["mismatches"], "tampered rubric bytes must produce mismatches"


def test_rubric_rehash_passes_on_correct_bytes(tmp_path):
    real_label = Path("evaluation/frozen_bars/RULES_LABEL.json").read_bytes()
    real_geom = Path("evaluation/frozen_bars/RULES_GEOMETRY.json").read_bytes()
    bar = tmp_path / "evaluation/frozen_bars"
    bar.mkdir(parents=True)
    (bar / "RULES_LABEL.json").write_bytes(real_label)
    (bar / "RULES_GEOMETRY.json").write_bytes(real_geom)
    vend = bar / "vendored"
    vend.mkdir()
    (vend / "VENDORED_SHA256.json").write_text(json.dumps({"files": {
        "evaluation/frozen_bars/RULES_LABEL.json":
            __import__("hashlib").sha256(real_label).hexdigest(),
        "evaluation/frozen_bars/RULES_GEOMETRY.json":
            __import__("hashlib").sha256(real_geom).hexdigest(),
    }}))
    res = rsa.check_rubric_rehash(tmp_path)
    assert res["status"] == "PASS", res


def test_h1_comparator_identical_except_elapsed():
    base = {"verdict": "PASS_NO_REGRESSION", "label_gate": {"n_supported": 5}, "elapsed_s": 1.0}
    other = json.loads(json.dumps(base))
    other["elapsed_s"] = 9.9
    res = rsa.compare_h1(base, other)
    assert res["identical_except_elapsed_s"] is True
    assert res["differing_fields"] == []


def test_h1_comparator_detects_verdict_divergence():
    base = {"verdict": "PASS_NO_REGRESSION", "elapsed_s": 1.0}
    other = {"verdict": "FAIL_REGRESSION", "elapsed_s": 1.0}
    res = rsa.compare_h1(base, other)
    assert res["identical_except_elapsed_s"] is False
    assert "verdict" in res["differing_fields"]


def test_h1_comparator_detects_nested_divergence():
    base = {"label_gate": {"classes": {"SUPPORTED": 5}}, "elapsed_s": 1.0}
    other = {"label_gate": {"classes": {"SUPPORTED": 3}}, "elapsed_s": 2.0}
    res = rsa.compare_h1(base, other)
    assert res["identical_except_elapsed_s"] is False
    assert "label_gate" in res["differing_fields"]


def test_evidence_refs_checker_fails_on_broken_ref(tmp_path):
    (tmp_path / "state").mkdir()
    (tmp_path / "state/evaluation.json").write_text(json.dumps(
        {"evidence_refs": ["state/evaluation.json", "does/not/exist.json"]}))
    res = rsa.check_evidence_refs(tmp_path)
    assert res["status"] == "FAIL"
    assert res["missing"] == ["does/not/exist.json"]


def test_evidence_refs_checker_passes_when_all_resolve(tmp_path):
    (tmp_path / "state").mkdir()
    (tmp_path / "state/evaluation.json").write_text(json.dumps(
        {"evidence_refs": ["state/evaluation.json"]}))
    res = rsa.check_evidence_refs(tmp_path)
    assert res["status"] == "PASS", res


def test_diagnosis_checker_rejects_missing_file(tmp_path):
    res = rsa.check_diagnosis_record(tmp_path)
    assert res["status"] == "FAIL"


def test_diagnosis_checker_rejects_incomplete_structure(tmp_path):
    diag = _minimal_valid_diagnosis()
    diag["runs"]["38977570612"]["jobs"]["audit"].pop("ambiguity_flag")
    p = tmp_path / "evaluation/snapshot_audit"
    p.mkdir(parents=True)
    (p / "orchestration_diagnosis_2026-10-16.json").write_text(json.dumps(diag))
    res = rsa.check_diagnosis_record(tmp_path)
    assert res["status"] == "FAIL"
    assert "runs.38977570612 ambiguous-cause flag" in res["problems"]


def test_diagnosis_checker_passes_on_valid_structure(tmp_path):
    p = tmp_path / "evaluation/snapshot_audit"
    p.mkdir(parents=True)
    (p / "orchestration_diagnosis_2026-10-16.json").write_text(
        json.dumps(_minimal_valid_diagnosis()))
    res = rsa.check_diagnosis_record(tmp_path)
    assert res["status"] == "PASS", res


def test_manifest_checker_fails_on_missing_deliverables(tmp_path):
    res = rsa.check_manifest(tmp_path)
    assert res["status"] == "FAIL"
    assert len(res["missing"]) == len(rsa.DELIVERABLE_MANIFEST_PATHS)


# ------------------------------------------------------------ integration --

@needs_mount
def test_readiness_record_passes_on_current_snapshot(tmp_path):
    out = tmp_path / "readiness.json"
    # The run-id is a labeling input only; the readiness checks themselves are
    # run-id-independent. Pin to the operational-resume run of record so the
    # gate-path assertions below name the actual audit contract for this tree.
    run_id = "38989947869"
    rc = rsa.main(["--run-id", run_id, "--out", str(out),
                   "--repo-root", str(Path.cwd())])
    assert rc == 0, "verifier must exit 0 (READY) on the current snapshot"
    record = json.loads(out.read_text(encoding="utf-8"))
    assert record["schema"] == "lex-evaluation-snapshot-audit/1"
    assert record["run_id"] == run_id
    assert record["ready_for_independent_audit"] is True
    assert {c["id"] for c in record["checks"]} == CHECK_IDS
    assert all(c["status"] == "PASS" for c in record["checks"])
    assert record["n_passed"] == record["n_checks"]
    assert record["audit_gate_path"] == \
        f"results/audit/evaluation/CYCLE_{run_id}_GATE.json"
    assert record["audit_report_path"] == \
        f"reports/audit/evaluation/CYCLE_{run_id}.md"
    assert len(record["deliverable_sha256"]) == len(rsa.DELIVERABLE_MANIFEST_PATHS)
    assert record["snapshot_claims_not_certified"], \
        "the record must state what it does NOT certify"


@needs_mount
def test_main_exit_code_is_one_when_a_check_fails(tmp_path, monkeypatch):
    """Breaking fixture at the record level: force one check red and require
    exit 1 with ready=false (a verifier that cannot fail is not evidence)."""
    monkeypatch.setattr(rsa, "check_lane_suite",
                        lambda repo_root: {"id": "lane_suite_pass", "status": "FAIL",
                                          "detail": "forced red"})
    out = tmp_path / "readiness.json"
    rc = rsa.main(["--run-id", "FORCEDRED", "--out", str(out),
                   "--repo-root", str(Path.cwd())])
    assert rc == 1
    record = json.loads(out.read_text(encoding="utf-8"))
    assert record["ready_for_independent_audit"] is False
    assert record["n_passed"] == record["n_checks"] - 1


# ------------------------------------------- write-scope gate (run 38982176936) --
# Run 38982176936 failed at the workflow step "Enforce lane write scope"
# because the producer authored audit-of-record files outside its scope.
# These tests pin the classifier, its fidelity to the control-plane step,
# and the diagnosis/void artifacts that document the failure.

FAILED_SNAPSHOT_PORCELAIN = [
    "?? reports/audit/evaluation/CYCLE_38982176936.md",
    "?? results/audit/evaluation/CYCLE_38982176936_GATE.json",
    "?? results/evaluation/bar_gates/38982176936.json",
    "?? results/evaluation/snapshot_audit/38982176936.json",
]


def _fake_write_scope_root(tmp_path: Path) -> Path:
    """Minimal root that satisfies check_write_scope_diagnosis, so each test
    can break exactly one ingredient."""
    diag = {
        "runs": {
            "38982176936": {
                "jobs": {"team": {"failed_step": "Enforce lane write scope"},
                         "audit": {"conclusion": "skipped"}},
                "root_cause": {"out_of_scope_paths": list(rsa.OUT_OF_SCOPE_ORIGINALS)},
            },
            "38982728075": {},
        },
    }
    repro = {
        "real_control_plane_step_fidelity": {"identical_bad_set": True,
                                             "real_step_exit_code": 3},
        "python_port_verdict": {"bad_paths": list(rsa.OUT_OF_SCOPE_ORIGINALS)},
    }
    void = {"artifacts": [{"original_path": p,
                           "sha256": rsa.VOID_EXPECTED_SHA256[Path(p).name]}
                          for p in rsa.OUT_OF_SCOPE_ORIGINALS]}
    (tmp_path / "evaluation/snapshot_audit").mkdir(parents=True)
    (tmp_path / "evaluation/snapshot_audit/orchestration_diagnosis_38982176936.json") \
        .write_text(json.dumps(diag))
    (tmp_path / "results/evaluation/snapshot_audit").mkdir(parents=True)
    (tmp_path / "results/evaluation/snapshot_audit/38982176936_write_scope_repro.json") \
        .write_text(json.dumps(repro))
    void_dir = tmp_path / rsa.VOID_DIR
    void_dir.mkdir(parents=True)
    (void_dir / "VOID.json").write_text(json.dumps(void))
    for name in rsa.VOID_EXPECTED_SHA256:
        src = Path(rsa.VOID_DIR) / name
        assert src.exists(), f"missing preserved copy in repo: {src}"
        shutil.copyfile(src, void_dir / name)
    return tmp_path


def test_write_scope_classifier_allows_the_producer_scope():
    allowed = ["evaluation/frozen_bars/x.py", "tests/evaluation/test_x.py",
               "results/evaluation/bar_gates/x.json", "reports/evaluation/CYCLE_x.md",
               "state/evaluation.json", "data/evaluation/cache/blob", ""]
    for p in allowed:
        assert ws.classify_path(p, "evaluation") is True, p


def test_write_scope_classifier_blocks_audit_of_record_paths():
    blocked = ["results/audit/evaluation/CYCLE_X_GATE.json",
               "reports/audit/evaluation/CYCLE_X.md",
               "state/blockers/evaluation.json", ".github/workflows/core-lane.yml",
               "product/query/qmap.py", "state/evaluation.json.bak"]
    for p in blocked:
        assert ws.classify_path(p, "evaluation") is False, p


def test_write_scope_product_only_files_require_the_product_lane():
    for p in ("requirements.txt", "pyproject.toml", "uv.lock"):
        assert ws.classify_path(p, "product") is True
        assert ws.classify_path(p, "evaluation") is False


def test_write_scope_flags_the_exact_38982176936_defect():
    """The reconstruction of the failed run's tree must be rejected with
    exactly the two audit-of-record paths."""
    verdict = ws.evaluate_porcelain(FAILED_SNAPSHOT_PORCELAIN, "evaluation")
    assert verdict["scope_clean"] is False
    assert verdict["verdict"] == "SCOPE_VIOLATION"
    assert sorted(verdict["bad_paths"]) == sorted(rsa.OUT_OF_SCOPE_ORIGINALS)
    assert verdict["n_bad"] == 2


def test_write_scope_drops_only_junk_the_workflow_deletes_first():
    lines = ["?? evaluation/__pycache__/write_scope.cpython-312.pyc",
             "?? evaluation/snapshot_audit/write_scope.py",
             "?? .pytest_cache/v/cache/nodeids"]
    verdict = ws.evaluate_porcelain(lines, "evaluation")
    assert verdict["junk_dropped"] == ["evaluation/__pycache__/write_scope.cpython-312.pyc"]
    # .pytest_cache is NOT deleted by the workflow, so it must still be scored.
    assert verdict["bad_paths"] == [".pytest_cache/v/cache/nodeids"]


def test_write_scope_checker_fails_on_an_out_of_scope_tree(monkeypatch):
    monkeypatch.setattr(ws, "live_porcelain", lambda repo_root: FAILED_SNAPSHOT_PORCELAIN)
    res = rsa.check_producer_write_scope(Path.cwd())
    assert res["status"] == "FAIL"
    assert sorted(res["bad_paths"]) == sorted(rsa.OUT_OF_SCOPE_ORIGINALS)


def test_write_scope_checker_passes_on_the_current_tree():
    res = rsa.check_producer_write_scope(Path.cwd())
    assert res["status"] == "PASS", res


def test_real_control_plane_step_matches_the_python_port(tmp_path):
    """Fidelity: the step body extracted from origin/main, executed against a
    stubbed git(1) emitting the failed snapshot's porcelain, must exit 3 with
    the same BAD set the Python port reports. This is what makes the lane-side
    gate a mirror of the control plane rather than an opinion."""
    try:
        src = subprocess.run(["git", "show", "origin/main:.github/workflows/core-lane.yml"],
                             capture_output=True, text=True, check=True).stdout.splitlines()
    except (subprocess.CalledProcessError, FileNotFoundError):
        pytest.skip("origin/main not fetchable in this checkout")
    start = base = None
    for i, line in enumerate(src):
        if "name: Enforce lane write scope" in line:
            start = i + 1
        if start and "run: |" in line:
            base = i + 1
            break
    assert base, "write-scope step not found in the control-plane workflow"
    body, i = [], base + 1
    while i < len(src):
        line = src[i]
        if line.strip() and not line.startswith(" " * 8):
            break
        body.append(line[8:] if line.startswith(" " * 8) else line)
        i += 1
    step = tmp_path / "step.sh"
    step.write_text("\n".join(body) + "\n")
    porcelain = tmp_path / "porcelain.txt"
    porcelain.write_text("\n".join(FAILED_SNAPSHOT_PORCELAIN) + "\n")
    shim = tmp_path / "git"
    shim.write_text("#!/usr/bin/env bash\n"
                    'if [[ "$1 $2 $3" == "status --porcelain -uall" ]]; then\n'
                    f'  cat "{porcelain}"\n'
                    "  exit 0\nfi\nexit 0\n")
    shim.chmod(0o755)
    env = dict(os.environ)
    env["PATH"] = f"{tmp_path}:{env['PATH']}"
    env["LANE"] = "evaluation"
    proc = subprocess.run(["bash", str(step)], capture_output=True, text=True, env=env)
    assert proc.returncode == 3, proc.stdout + proc.stderr
    real_bad = sorted(ln.strip() for ln in (proc.stdout + proc.stderr).splitlines()
                      if "/audit/" in ln)
    assert real_bad == sorted(ws.evaluate_porcelain(
        FAILED_SNAPSHOT_PORCELAIN, "evaluation")["bad_paths"])


def test_write_scope_diagnosis_checker_rejects_a_missing_artifact(tmp_path):
    res = rsa.check_write_scope_diagnosis(tmp_path)
    assert res["status"] == "FAIL"
    assert any("orchestration_diagnosis_38982176936.json missing" in p for p in res["problems"])


def test_write_scope_diagnosis_checker_passes_on_a_valid_root(tmp_path):
    res = rsa.check_write_scope_diagnosis(_fake_write_scope_root(tmp_path))
    assert res["status"] == "PASS", res


def test_write_scope_diagnosis_checker_rejects_a_swapped_void_copy(tmp_path):
    root = _fake_write_scope_root(tmp_path)
    (root / rsa.VOID_DIR / "CYCLE_38982176936_GATE.json").write_text('{"tampered": true}')
    res = rsa.check_write_scope_diagnosis(root)
    assert res["status"] == "FAIL"
    assert any("void copy sha256 mismatch" in p for p in res["problems"])


def test_write_scope_diagnosis_checker_rejects_the_originals_still_in_tree(tmp_path):
    root = _fake_write_scope_root(tmp_path)
    for rel in rsa.OUT_OF_SCOPE_ORIGINALS:
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("{}")
    res = rsa.check_write_scope_diagnosis(root)
    assert res["status"] == "FAIL"
    assert any(p.startswith("out-of-scope original still in tree") for p in res["problems"])


def test_write_scope_diagnosis_checker_rejects_an_unreproduced_cause(tmp_path):
    root = _fake_write_scope_root(tmp_path)
    repro = json.loads((root / "results/evaluation/snapshot_audit/"
                               "38982176936_write_scope_repro.json").read_text())
    repro["real_control_plane_step_fidelity"]["identical_bad_set"] = False
    (root / "results/evaluation/snapshot_audit/"
            "38982176936_write_scope_repro.json").write_text(json.dumps(repro))
    res = rsa.check_write_scope_diagnosis(root)
    assert res["status"] == "FAIL"
    assert any("not identical" in p for p in res["problems"])


# ------------------------------------------- run 39010105493 (checks 14-16) --

def _fake_pac_root(tmp_path: Path) -> Path:
    """Minimal repo root carrying the frozen hypothesis and the execution record
    of run 39010105493, byte-copied from the real snapshot when available."""
    src = Path(".")
    for rel in (rsa.PAC_FROZEN_HYPOTHESIS, rsa.PAC_RECORD):
        d = (tmp_path / rel).parent
        d.mkdir(parents=True, exist_ok=True)
        (tmp_path / rel).write_bytes((src / rel).read_bytes())
    return tmp_path


def test_pac_record_checker_fails_when_the_record_is_missing(tmp_path):
    res = rsa.check_packet_admission_conformance(tmp_path)
    assert res["status"] == "FAIL"
    assert any("missing" in p for p in res["problems"])


def test_pac_record_checker_rejects_a_softened_verdict(tmp_path):
    """Breaking fixture: a record re-labelled HELD or exit 0 must go red, so the
    falsification of record cannot be quietly flipped by editing the JSON."""
    root = _fake_pac_root(tmp_path)
    rec = json.loads((root / rsa.PAC_RECORD).read_text())
    rec["verdict"] = "PACKET_ADMISSION_INVARIANT_HELD"
    rec["exit_code"] = 0
    (root / rsa.PAC_RECORD).write_text(json.dumps(rec))
    res = rsa.check_packet_admission_conformance(root)
    assert res["status"] == "FAIL"
    assert any(p.startswith("verdict=") for p in res["problems"])
    assert any(p.startswith("exit_code=") for p in res["problems"])


def test_pac_record_checker_rejects_a_dropped_violation(tmp_path):
    """Breaking fixture: removing one of the three violating records must fail,
    so the frozen violation set cannot shrink silently."""
    root = _fake_pac_root(tmp_path)
    rec = json.loads((root / rsa.PAC_RECORD).read_text())
    dropped = rec["metric"]["violations"].pop()
    rec["metric"]["n_violations"] = len(rec["metric"]["violations"])
    rec["violations_total"] = len(rec["metric"]["violations"])
    (root / rsa.PAC_RECORD).write_text(json.dumps(rec))
    res = rsa.check_packet_admission_conformance(root)
    assert res["status"] == "FAIL"
    assert any("violation file set" in p for p in res["problems"])
    assert dropped["file"] in set(rsa.PAC_VIOLATION_FILES)


def test_pac_record_checker_rejects_an_unproven_battery(tmp_path):
    """Breaking fixture: a non-vacuity battery that did not hold voids the
    finding, and this checker must say so."""
    root = _fake_pac_root(tmp_path)
    rec = json.loads((root / rsa.PAC_RECORD).read_text())
    rec["non_vacuity_battery"]["all_hold"] = False
    (root / rsa.PAC_RECORD).write_text(json.dumps(rec))
    res = rsa.check_packet_admission_conformance(root)
    assert res["status"] == "FAIL"
    assert any("non-vacuity battery" in p for p in res["problems"])


def test_pac_record_checker_passes_on_the_committed_record():
    res = rsa.check_packet_admission_conformance(Path("."))
    assert res["status"] == "PASS", res
    assert set(res["violation_files"]) == set(rsa.PAC_VIOLATION_FILES)


def test_pac_reexecution_check_fails_without_the_product_mount(tmp_path, monkeypatch):
    """Environment limit is a recorded FAIL with a reason, never a silent pass."""
    monkeypatch.setenv("LEX_ACCEPTED_PRODUCT_MOUNT", str(tmp_path / "absent"))
    res = rsa.check_packet_admission_conformance_reexecution(Path("."), tmp_path)
    assert res["status"] == "FAIL"
    assert res["environment_limited"] is True


def test_pac_diagnosis_checker_rejects_a_missing_artifact(tmp_path):
    res = rsa.check_pac_diagnosis(tmp_path)
    assert res["status"] == "FAIL"


def test_pac_diagnosis_checker_rejects_a_single_asserted_cause(tmp_path):
    """The cause must stay a recorded candidate set: job logs are 403 and an
    asserted single cause would be an over-claim."""
    diag = json.loads(Path(rsa.PAC_DIAGNOSIS).read_text())
    diag["runs"]["39010105493"]["root_cause"][
        "candidate_causes_of_the_step_failure_not_disambiguated"] = []
    p = tmp_path / rsa.PAC_DIAGNOSIS
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(diag))
    res = rsa.check_pac_diagnosis(tmp_path)
    assert res["status"] == "FAIL"
    assert any("candidate_causes" in x for x in res["problems"])


def test_pac_diagnosis_checker_passes_on_the_committed_artifact():
    res = rsa.check_pac_diagnosis(Path("."))
    assert res["status"] == "PASS", res


# ---------------------------- check 17: diagnosis_artifacts_all_parse ------
#
# Regression tests for the defect cycle 39043684319 found: the accepted
# orchestration_diagnosis_39027041693.json had been committed TRUNCATED (the
# root object was never closed), so json.loads and `jq -e .` both FAIL on it,
# and four consecutive readiness records reported the snapshot clean because no
# check had ever parsed these files. Each test below makes the check go RED.

def _copy_diagnosis_tree(tmp_path: Path) -> Path:
    """A fake repo root holding real copies of the diagnosis artifacts."""
    src = Path("evaluation/snapshot_audit")
    dst = tmp_path / "evaluation/snapshot_audit"
    dst.mkdir(parents=True)
    for f in src.glob("orchestration_diagnosis_*.json"):
        shutil.copy(f, dst / f.name)
    return tmp_path


def test_diagnosis_parse_check_passes_on_the_committed_tree():
    res = rsa.check_diagnosis_39040205229(Path("."))
    assert res["status"] == "PASS", res
    assert res["parse_status"]


def test_diagnosis_parse_check_catches_a_truncated_record(tmp_path):
    """The exact 39027041693 defect: root object never closed."""
    root = _copy_diagnosis_tree(tmp_path)
    victim = root / "evaluation/snapshot_audit/orchestration_diagnosis_39027041693.json"
    raw = victim.read_bytes()
    victim.write_bytes(raw[:-2])          # drop the final "}\n"
    with pytest.raises(json.JSONDecodeError):
        json.loads(victim.read_bytes())
    res = rsa.check_diagnosis_39040205229(root)
    assert res["status"] == "FAIL"
    assert any("unparseable" in x for x in res["problems"])


def test_diagnosis_parse_check_catches_a_reverted_repair(tmp_path):
    """The repair is hash-pinned: putting the truncated pre-image back fails."""
    root = _copy_diagnosis_tree(tmp_path)
    victim = root / "evaluation/snapshot_audit/orchestration_diagnosis_39027041693.json"
    raw = victim.read_bytes()
    victim.write_bytes(raw[:rsa.DIAGNOSIS_39027041693_PRE_REPAIR_BYTES])
    res = rsa.check_diagnosis_39040205229(root)
    assert res["status"] == "FAIL"
    assert any("sha256" in x for x in res["problems"])


def test_diagnosis_parse_check_rejects_a_softened_quantum_falsification(tmp_path):
    """Deleting the falsification must go RED: it is the load-bearing result."""
    root = _copy_diagnosis_tree(tmp_path)
    p = root / rsa.DIAGNOSIS_39040205229
    d = json.loads(p.read_text())
    d["quantum_hypothesis_test"]["verdict"] = "CONFIRMED"
    p.write_text(json.dumps(d))
    res = rsa.check_diagnosis_39040205229(root)
    assert res["status"] == "FAIL"
    assert any("quantum_hypothesis_test.verdict" in x for x in res["problems"])


def test_diagnosis_parse_check_rejects_an_asserted_single_cause(tmp_path):
    """Job logs are 403: promoting the remaining hypothesis to fact over-claims."""
    root = _copy_diagnosis_tree(tmp_path)
    p = root / rsa.DIAGNOSIS_39040205229
    d = json.loads(p.read_text())
    d["best_supported_remaining_hypothesis"]["status"] = "ESTABLISHED_FACT"
    p.write_text(json.dumps(d))
    res = rsa.check_diagnosis_39040205229(root)
    assert res["status"] == "FAIL"
    assert any("inference" in x for x in res["problems"])


def test_diagnosis_parse_check_requires_the_audit_skip_to_be_recorded(tmp_path):
    root = _copy_diagnosis_tree(tmp_path)
    p = root / rsa.DIAGNOSIS_39040205229
    d = json.loads(p.read_text())
    d["runs"]["39040205229"]["jobs"]["audit"]["conclusion"] = "success"
    p.write_text(json.dumps(d))
    res = rsa.check_diagnosis_39040205229(root)
    assert res["status"] == "FAIL"
    assert any("audit.conclusion" in x for x in res["problems"])


def test_diagnosis_parse_check_requires_the_snapshot_rescue_commit(tmp_path):
    """The 39040205229 tree was rescued by the persist step; losing that
    provenance would hide that steps 7+9 never validated the snapshot."""
    root = _copy_diagnosis_tree(tmp_path)
    p = root / rsa.DIAGNOSIS_39040205229
    d = json.loads(p.read_text())
    del d["runs"]["39040205229"]["snapshot_rescued"]
    p.write_text(json.dumps(d))
    res = rsa.check_diagnosis_39040205229(root)
    assert res["status"] == "FAIL"
    assert any("snapshot_rescued" in x for x in res["problems"])


# ------------------- check 18: accepted_base_gate_coverage_recorded ---------

def test_accepted_base_coverage_is_disclosed_on_the_live_branch():
    """The one ungated run at origin/lab/evaluation's head must be disclosed,
    and the disclosure must match what git re-derives."""
    res = rsa.check_accepted_base_gate_coverage(Path("."))
    if res.get("environment_limited"):
        pytest.skip("origin/lab/evaluation not fetchable here")
    assert res["status"] == "PASS", res
    assert res["derived_ungated_runs"] == ["39027041693"], res
    assert res["declared_ungated_runs"] == res["derived_ungated_runs"]


def test_accepted_base_coverage_fails_without_the_disclosure_record(tmp_path, monkeypatch):
    """A clean snapshot must not pass by having no disclosure on disk."""
    rec = Path(rsa.ACCEPTED_BASE_COVERAGE_RECORD)
    tmp_rec = tmp_path / "rec.json"
    tmp_rec.write_bytes(rec.read_bytes())
    monkeypatch.setattr(rsa, "ACCEPTED_BASE_COVERAGE_RECORD", "rec.json")
    assert rsa.check_accepted_base_gate_coverage(tmp_path)["status"] == "FAIL"
    assert rsa.check_accepted_base_gate_coverage(tmp_path)["problems"] == ["disclosure record missing"]


def test_accepted_base_coverage_flags_an_undisclosed_new_ungated_run(tmp_path, monkeypatch):
    """Dropping a disclosed run must read as a NEW ungated run, not as clean."""
    monkeypatch.setattr(rsa, "ACCEPTED_BASE_COVERAGE_RECORD", "rec.json")
    rec = json.loads(Path(rsa.ACCEPTED_BASE_COVERAGE_RECORD).read_text())
    rec["ungated_runs_above_the_newest_accept_commit"] = []
    (tmp_path / "rec.json").write_text(json.dumps(rec))
    res = rsa.check_accepted_base_gate_coverage(tmp_path)
    assert res["status"] == "FAIL"
    assert any("new ungated run" in x for x in res["problems"]), res


def test_accepted_base_coverage_flags_a_stale_branch_head(tmp_path, monkeypatch):
    """A disclosure pinned to a different head must not silently pass."""
    monkeypatch.setattr(rsa, "ACCEPTED_BASE_COVERAGE_RECORD", "rec.json")
    rec = json.loads(Path(rsa.ACCEPTED_BASE_COVERAGE_RECORD).read_text())
    rec["accepted_branch_head"] = "0" * 40
    (tmp_path / "rec.json").write_text(json.dumps(rec))
    res = rsa.check_accepted_base_gate_coverage(tmp_path)
    assert res["status"] == "FAIL"
    assert any("accepted_branch_head" in x for x in res["problems"]), res


def test_accepted_base_coverage_requires_the_boundaries_of_the_gap(tmp_path, monkeypatch):
    """A coverage gap without 'what is NOT claimed' is an over-claim."""
    monkeypatch.setattr(rsa, "ACCEPTED_BASE_COVERAGE_RECORD", "rec.json")
    rec = json.loads(Path(rsa.ACCEPTED_BASE_COVERAGE_RECORD).read_text())
    rec["finding"]["what_is_NOT_claimed"] = []
    (tmp_path / "rec.json").write_text(json.dumps(rec))
    res = rsa.check_accepted_base_gate_coverage(tmp_path)
    assert res["status"] == "FAIL"
    assert any("what_is_NOT_claimed" in x for x in res["problems"]), res


def test_accepted_base_coverage_is_environment_limited_without_the_ref(tmp_path):
    """No accepted ref is an environment_limited FAIL, never a silent pass."""
    res = rsa.check_accepted_base_gate_coverage(tmp_path)
    assert res["status"] == "FAIL"
    assert res["environment_limited"] is True
    assert res["n_ungated_runs"] is None

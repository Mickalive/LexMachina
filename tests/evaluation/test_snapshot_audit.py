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
    # run 39047050629: no prose may assert a readiness verdict its record does
    # not carry. Added after that run found 39043684319's snapshot committing a
    # RED record (16/18) behind three green headlines and a state block with no
    # n_passed at all. The same cycle repaired check 5's order dependence (the
    # readiness record's own path is now a declared, post-write-verified self
    # reference) and gave check 4 the failing lane-suite check names.
    "readiness_claims_match_record",
    # run 39082753086: the direction's own item-(1) trigger must be EXECUTED,
    # not asserted. Audit CYCLE_39079133613 (gate=REVISE, fixes R1/R2 both HIGH)
    # found NO_NEW_PACKET published for four consecutive cycles while the frozen
    # newhead_recompute --mode trigger returns ADJUDICATE_REQUIRED against the
    # very mount the reports named. Check 19 certified self-consistency only,
    # so a claim no record measured passed vacuously. Set-completeness of the
    # verifier's check set; no check was weakened or removed.
    "trigger_verdict_matches_record",
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

def _current_state_run_id() -> str:
    """The run id the committed state publishes as the current cycle.

    Check 19 (added by cycle 39047050629) compares the state block of the run
    the verifier is executing AS against the record it just computed, so the
    integration test below must execute the verifier as that run. It used to
    pin a hard-coded historical id, which no longer carries a state block; the
    id is therefore derived from the committed state instead of being written
    by hand, so the test keeps working as the run id advances.
    """
    state = json.loads(Path("state/evaluation.json").read_text())
    candidates = []
    for key, block in state.items():
        if key.startswith("snapshot_audit_") and isinstance(block, dict) and block.get("record"):
            rec = Path(block["record"])
            if rec.exists():
                candidates.append((key[len("snapshot_audit_"):], block))
    assert candidates, "state/evaluation.json publishes no snapshot_audit_<run> block"
    run_id, block = max(candidates, key=lambda kv: int(kv[0]))
    # the block must already agree with its own record, or the integration test
    # would be asserting READY over a snapshot that is not.
    rec = json.loads(Path(block["record"]).read_text())
    assert block.get("n_passed") == rec["n_passed"], (block, rec["n_passed"])
    return run_id


@needs_mount
def test_readiness_record_passes_on_current_snapshot(tmp_path):
    out = tmp_path / "readiness.json"
    # The run-id is a labeling input for every check EXCEPT 19, which compares
    # the state block of this run with the record; run as the run the committed
    # state publishes, so the gate-path assertions below name the actual audit
    # contract for this tree.
    run_id = _current_state_run_id()
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
    # Execute as the run the committed state publishes, so the ONLY thing this
    # fixture breaks is the lane suite. (An unknown run id would also fail
    # check 19, and the "-1" arithmetic below would no longer isolate the
    # forced red.)
    run_id = _current_state_run_id()
    rc = rsa.main(["--run-id", run_id, "--out", str(out),
                   "--repo-root", str(Path.cwd())])
    assert rc == 1
    record = json.loads(out.read_text(encoding="utf-8"))
    assert record["ready_for_independent_audit"] is False
    assert "lane_suite_pass" in record["failing_checks"]
    assert record["n_passed"] < record["n_checks"]


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
    """The ungated runs at origin/lab/evaluation's head must be disclosed,
    and the disclosure must match what git re-derives.

    REPAIRED by run 39111232991 (2026-10-18). This test used to hard-code
    ``derived_ungated_runs == ["39027041693"]``, a measurement taken by cycle
    39043684319 when the accepted branch head was 09970e83. Four further
    evaluation cycles have since been ACCEPTED onto origin/lab/evaluation (most
    recently cycle 39109815075 at head 3c2fcab6), so the newest
    "accept evaluation cycle" commit is now the head itself and the derived
    ungated set is empty. The hard-coded list therefore became a FALSE
    assertion on the committed tree. The invariant that matters is the
    coverage contract, not the frozen value: the declared set must equal the
    set the check re-derives from git, and the record must carry a non-empty
    claim ceiling and a non-empty ``finding.what_is_NOT_claimed``. The 39043684319
    measurement is preserved verbatim under
    ``results/evaluation/accepted_base_gate_coverage_39043684319.json`` ->
    ``superseded_snapshot_39043684319``; it is superseded as present tense,
    not deleted.
    """
    res = rsa.check_accepted_base_gate_coverage(Path("."))
    if res.get("environment_limited"):
        pytest.skip("origin/lab/evaluation not fetchable here")
    assert res["status"] == "PASS", res
    assert res["declared_ungated_runs"] == res["derived_ungated_runs"], res
    rec = _committed_coverage_record()
    assert rec["accepted_branch_head"] == res["accepted_branch_head"], res
    assert rec["claim_ceiling"], "a coverage record must state its boundaries"
    assert rec["finding"]["what_is_NOT_claimed"], "a coverage gap must state its boundaries"


#: Captured at import, because the fixtures below monkeypatch the module
#: constant to "rec.json" and must still read the COMMITTED record.
_COMMITTED_COVERAGE_RECORD_PATH = rsa.ACCEPTED_BASE_COVERAGE_RECORD


def _committed_coverage_record() -> dict:
    """The committed disclosure record, read from the repo, not rebuilt."""
    return json.loads(Path(_COMMITTED_COVERAGE_RECORD_PATH).read_text())


def _fake_accepted_branch(monkeypatch, head: str = "1" * 40,
                          gates=("38971202786", "39020603510")) -> None:
    """Make ``git`` inside check 18 deterministic and hermetic.

    PRE-EXISTING RED, repaired by cycle 39047050629: these four fixtures ran
    ``git rev-parse`` with ``cwd=tmp_path``, which is not a git repository, so
    the check returned its environment-limited branch BEFORE reaching the
    ingredient each fixture breaks, and two of them then read a ``rec.json``
    they had never created. Four committed tests were therefore red on the
    committed tree while the file's own module docstring claims every check
    has a breaking fixture. The stub restores the intent: the check runs to
    completion against a FIXED branch and exactly one ingredient is broken.
    """
    def fake_git(repo_root, *args):
        if args[:2] == ("rev-parse", "--verify"):
            return head
        if args[0] == "ls-tree":
            return "\n".join(
                f"results/audit/evaluation/CYCLE_{g}_GATE.json" for g in gates) + "\n"
        if args[0] == "log":
            # git log order is newest first, and check 18 reads the commits
            # ABOVE the newest 'accept evaluation cycle' commit, i.e. the ones
            # listed BEFORE it.
            return ("evaluation cycle 39027041693: producer work\n"
                    "accept evaluation cycle 39020603510\n")
        return ""
    monkeypatch.setattr(rsa, "_git", fake_git)


def test_accepted_base_coverage_fails_without_the_disclosure_record(tmp_path, monkeypatch):
    """A clean snapshot must not pass by having no disclosure on disk."""
    _fake_accepted_branch(monkeypatch)
    monkeypatch.setattr(rsa, "ACCEPTED_BASE_COVERAGE_RECORD", "rec.json")
    assert rsa.check_accepted_base_gate_coverage(tmp_path)["status"] == "FAIL"
    assert rsa.check_accepted_base_gate_coverage(tmp_path)["problems"] == ["disclosure record missing"]


def test_accepted_base_coverage_flags_an_undisclosed_new_ungated_run(tmp_path, monkeypatch):
    """Dropping a disclosed run must read as a NEW ungated run, not as clean."""
    _fake_accepted_branch(monkeypatch)
    monkeypatch.setattr(rsa, "ACCEPTED_BASE_COVERAGE_RECORD", "rec.json")
    rec = _committed_coverage_record()
    rec["ungated_runs_above_the_newest_accept_commit"] = []
    (tmp_path / "rec.json").write_text(json.dumps(rec))
    res = rsa.check_accepted_base_gate_coverage(tmp_path)
    assert res["status"] == "FAIL"
    assert any("new ungated run" in x for x in res["problems"]), res


def test_accepted_base_coverage_flags_a_stale_branch_head(tmp_path, monkeypatch):
    """A disclosure pinned to a different head must not silently pass."""
    _fake_accepted_branch(monkeypatch)
    monkeypatch.setattr(rsa, "ACCEPTED_BASE_COVERAGE_RECORD", "rec.json")
    rec = _committed_coverage_record()
    rec["accepted_branch_head"] = "0" * 40
    (tmp_path / "rec.json").write_text(json.dumps(rec))
    res = rsa.check_accepted_base_gate_coverage(tmp_path)
    assert res["status"] == "FAIL"
    assert any("accepted_branch_head" in x for x in res["problems"]), res


def test_accepted_base_coverage_requires_the_boundaries_of_the_gap(tmp_path, monkeypatch):
    """A coverage gap without 'what is NOT claimed' is an over-claim."""
    _fake_accepted_branch(monkeypatch)
    monkeypatch.setattr(rsa, "ACCEPTED_BASE_COVERAGE_RECORD", "rec.json")
    rec = _committed_coverage_record()
    rec["finding"]["what_is_NOT_claimed"] = []
    (tmp_path / "rec.json").write_text(json.dumps(rec))
    res = rsa.check_accepted_base_gate_coverage(tmp_path)
    assert res["status"] == "FAIL"
    assert any("what_is_NOT_claimed" in x for x in res["problems"]), res


def test_accepted_base_coverage_passes_against_the_fake_branch(tmp_path, monkeypatch):
    """The hermetic stub must actually exercise the PASS path, otherwise the
    four repaired fixtures above could pass for the wrong reason."""
    _fake_accepted_branch(monkeypatch)
    monkeypatch.setattr(rsa, "ACCEPTED_BASE_COVERAGE_RECORD", "rec.json")
    rec = _committed_coverage_record()
    rec["accepted_branch_head"] = "1" * 40
    rec["ungated_runs_above_the_newest_accept_commit"] = ["39027041693"]
    (tmp_path / "rec.json").write_text(json.dumps(rec))
    res = rsa.check_accepted_base_gate_coverage(tmp_path)
    assert res["status"] == "PASS", res


def test_accepted_base_coverage_is_environment_limited_without_the_ref(tmp_path):
    """No accepted ref is an environment_limited FAIL, never a silent pass."""
    res = rsa.check_accepted_base_gate_coverage(tmp_path)
    assert res["status"] == "FAIL"
    assert res["environment_limited"] is True
    assert res["n_ungated_runs"] is None


# ---------------- check 5 repair: the order-dependence of the self-reference --
#
# Run 39043684319 committed a readiness record that is RED (16/18) together
# with three green prose headlines. One of the two root causes was that check 5
# ran BEFORE the readiness record was written, so when state/evaluation.json
# cited the record of the CURRENT run its verdict depended on whether the
# verifier had been run before. These tests pin the repair and its guard.


def test_evidence_refs_treats_the_current_record_as_a_self_reference(tmp_path):
    """The record's own path must NOT be reported as unresolved..."""
    (tmp_path / "state").mkdir()
    rec_rel = "results/evaluation/snapshot_audit/999.json"
    (tmp_path / "state/evaluation.json").write_text(json.dumps(
        {"evidence_refs": ["state/evaluation.json", rec_rel]}))
    res = rsa.check_evidence_refs(tmp_path, rec_rel)
    assert res["status"] == "PASS", res
    assert res["self_reference_refs"] == [rec_rel]
    assert res["missing"] == []


def test_evidence_refs_still_fails_on_a_genuinely_broken_ref_alongside_the_self_reference(tmp_path):
    """The self-reference exemption must not launder another broken ref."""
    (tmp_path / "state").mkdir()
    rec_rel = "results/evaluation/snapshot_audit/999.json"
    (tmp_path / "state/evaluation.json").write_text(json.dumps(
        {"evidence_refs": [rec_rel, "does/not/exist.json"]}))
    res = rsa.check_evidence_refs(tmp_path, rec_rel)
    assert res["status"] == "FAIL"
    assert res["missing"] == ["does/not/exist.json"]


def test_post_write_self_reference_verifies_the_record_it_just_wrote(tmp_path):
    out = tmp_path / "rec.json"
    record = {"schema": rsa.SCHEMA, "run_id": "999", "ready_for_independent_audit": True}
    out.write_text(json.dumps(record))
    # the record under test is the in-flight dict, written twice by main()
    assert rsa._post_write_self_reference(out, "999", ["rec.json"], record) is True
    assert record["post_write_self_reference"]["status"] == "VERIFIED"


def test_post_write_self_reference_fails_when_the_record_does_not_parse(tmp_path):
    out = tmp_path / "rec.json"
    out.write_text('{"schema": "x", ')          # truncated, the 39027041693 class
    record = {"schema": rsa.SCHEMA, "run_id": "999", "ready_for_independent_audit": True}
    assert rsa._post_write_self_reference(out, "999", ["rec.json"], record) is False
    assert record["post_write_self_reference"]["status"] == "FAILED"
    assert record["ready_for_independent_audit"] is False


def test_post_write_self_reference_fails_on_another_run_record(tmp_path):
    out = tmp_path / "rec.json"
    out.write_text(json.dumps({"schema": rsa.SCHEMA, "run_id": "111"}))
    record = {"schema": rsa.SCHEMA, "run_id": "999", "ready_for_independent_audit": True}
    assert rsa._post_write_self_reference(out, "999", ["rec.json"], record) is False
    assert "not this run's record" in record["post_write_self_reference"]["why"]


def test_post_write_state_claim_catches_a_state_block_that_does_not_repeat_the_record(tmp_path):
    (tmp_path / "state").mkdir()
    (tmp_path / "state/evaluation.json").write_text(json.dumps(
        {"snapshot_audit_999": {"record": "rec.json", "verdict": "READY",
                                "n_checks": 19, "n_passed": 19}}))
    record = {"n_checks": 19, "n_passed": 18, "ready_for_independent_audit": False,
              "checks": []}
    assert rsa._post_write_state_claim(tmp_path, "999", record) is False
    assert record["post_write_state_claim"]["status"] == "FAILED"
    assert record["ready_for_independent_audit"] is False


# ---------------- check 19: readiness_claims_match_record ---------------------
#
# The defect that check 19 exists for, verbatim: run 39043684319's report said
# "READY (18/18 checks PASS)" in its Status line AND in section 4, said
# "READY 17/17" in its evidence list, and its state block said verdict READY
# with n_checks 18 and NO n_passed - over a record reading 16/18 and
# ready_for_independent_audit=false. Each reinstatement below must go RED.

_RECORD_16_OF_18 = {
    "n_checks": 18, "n_passed": 16, "ready_for_independent_audit": False,
    "checks": [{"id": "lane_suite_pass", "status": "FAIL", "n_failed_checks": 1,
                "detail": "exit=1 summary=FAIL"}],
}


def _claim_root(tmp_path: Path, block: dict, report: str | None = None) -> Path:
    (tmp_path / "state").mkdir()
    (tmp_path / "state/evaluation.json").write_text(
        json.dumps({"evidence_refs": [], "snapshot_audit_999": block,
                    "lane_suite_999": {}}))
    if report is not None:
        p = tmp_path / "reports/evaluation"
        p.mkdir(parents=True)
        (p / "CYCLE_999.md").write_text(report)
    return tmp_path


def test_readiness_claims_catch_the_exact_39043684319_state_green(tmp_path):
    """verdict READY + n_checks 18 + NO n_passed, over a 16/18 record."""
    block = {"record": "rec.json", "verdict": "READY", "n_checks": 18}
    res = rsa.check_readiness_claims(_claim_root(tmp_path, block), "999", _RECORD_16_OF_18)
    assert res["status"] == "FAIL", res
    assert any("n_passed" in p for p in res["problems"]), res
    assert any("verdict" in p for p in res["problems"]), res


def test_readiness_claims_catch_the_18_of_18_headline(tmp_path):
    block = {"record": "rec.json", "verdict": "NOT_READY", "n_checks": 18,
             "n_passed": 16, "ready_for_independent_audit": False}
    report = ("# Run 999\n\n**Status:** DELIVERED - snapshot audit READY "
              "(18/18 checks PASS)\n")
    res = rsa.check_readiness_claims(
        _claim_root(tmp_path, block, report), "999", _RECORD_16_OF_18)
    assert res["status"] == "FAIL", res
    assert res["current_report_state"] == "MISMATCH"


def test_readiness_claims_catch_a_lane_suite_green_over_a_red_suite(tmp_path):
    block = {"record": "rec.json", "verdict": "NOT_READY", "n_checks": 18,
             "n_passed": 16, "ready_for_independent_audit": False}
    root = _claim_root(tmp_path, block)
    state = json.loads((root / "state/evaluation.json").read_text())
    state["lane_suite_999"] = {"overall_pass": True, "n_failed": 0, "n_checks": 49}
    (root / "state/evaluation.json").write_text(json.dumps(state))
    res = rsa.check_readiness_claims(root, "999", _RECORD_16_OF_18)
    assert res["status"] == "FAIL", res
    assert any("lane_suite.overall_pass" in p for p in res["problems"]), res


def test_readiness_claims_pass_when_state_and_report_agree(tmp_path):
    block = {"record": "rec.json", "verdict": "NOT_READY", "n_checks": 18,
             "n_passed": 16, "ready_for_independent_audit": False}
    report = "snapshot audit: NOT READY (16/18 checks PASS)\n"
    res = rsa.check_readiness_claims(
        _claim_root(tmp_path, block, report), "999", _RECORD_16_OF_18)
    assert res["status"] == "PASS", res
    assert res["current_report_state"] == "VERIFIED"


def test_readiness_claims_tolerate_an_absent_current_report(tmp_path):
    """A report written after the checks is a DISCLOSED pending item, not a
    silent pass and not a red: the record lists it in post_write_pending."""
    block = {"record": "rec.json", "verdict": "NOT_READY", "n_checks": 18,
             "n_passed": 16, "ready_for_independent_audit": False}
    res = rsa.check_readiness_claims(_claim_root(tmp_path, block), "999", _RECORD_16_OF_18)
    assert res["status"] == "PASS", res
    assert res["current_report_state"] == "ABSENT_FOR_THIS_RUN"


def test_readiness_claims_flag_an_undisclosed_historical_disagreement(tmp_path):
    """History is preserved, not silently corrected: an undisclosed mismatch
    between a historical state block and ITS OWN record is red."""
    rec = tmp_path / "rec.json"
    rec.write_text(json.dumps(_RECORD_16_OF_18))
    block = {"record": "rec.json", "verdict": "READY", "n_checks": 18}
    (tmp_path / "state").mkdir()
    (tmp_path / "state/evaluation.json").write_text(json.dumps(
        {"evidence_refs": [], "snapshot_audit_888": block,
         "snapshot_audit_999": {"record": "rec.json", "verdict": "NOT_READY",
                                "n_checks": 18, "n_passed": 16,
                                "ready_for_independent_audit": False}}))
    res = rsa.check_readiness_claims(tmp_path, "999", _RECORD_16_OF_18)
    assert res["status"] == "FAIL", res
    assert any("UNDISCLOSED disagreement" in p and "888" in p for p in res["problems"]), res


def test_readiness_claims_accept_a_disclosed_historical_disagreement(tmp_path):
    """A disclosed historical disagreement is NOT red: history is preserved and
    the disclosure is what keeps the check honest."""
    rec = tmp_path / "rec.json"
    rec.write_text(json.dumps(_RECORD_16_OF_18))
    # the EXACT shape of run 39043684319's committed state block: verdict READY,
    # n_checks 18, and no n_passed at all.
    block = {"record": "rec.json", "verdict": "READY", "n_checks": 18}
    disclosures = [
        {"run_id": "888", "field": "verdict", "recorded_value": "READY",
         "record_value": "NOT_READY",
         "disclosure": "run 888 asserted a green over a red record; preserved, not rewritten"},
        {"run_id": "888", "field": "n_passed", "recorded_value": None,
         "record_value": 16,
         "disclosure": "run 888 published no n_passed, so no comparison was possible"},
        {"run_id": "888", "field": "lane_suite.overall_pass", "recorded_value": True,
         "record_value": False,
         "disclosure": "run 888 published overall_pass true over a FAIL lane_suite_pass"},
        {"run_id": "888", "field": "lane_suite.n_failed", "recorded_value": 0,
         "record_value": 1,
         "disclosure": "run 888 published n_failed 0 over a lane_suite_pass that records 1 failing check"},
    ]
    (tmp_path / "state").mkdir()
    (tmp_path / "state/evaluation.json").write_text(json.dumps({
        "evidence_refs": [],
        "snapshot_audit_888": block,
        "lane_suite_888": {"overall_pass": True, "n_failed": 0},
        "snapshot_audit_999": {"record": "rec.json", "verdict": "NOT_READY",
                               "n_checks": 18, "n_passed": 16,
                               "ready_for_independent_audit": False},
        rsa.READINESS_DISAGREEMENT_KEY: disclosures}))
    res = rsa.check_readiness_claims(tmp_path, "999", _RECORD_16_OF_18)
    assert res["status"] == "PASS", res
    assert len(res["historical_disagreements"]) == 4


def test_readiness_claims_require_a_prose_disclosure_text(tmp_path):
    rec = tmp_path / "rec.json"
    rec.write_text(json.dumps(_RECORD_16_OF_18))
    (tmp_path / "state").mkdir()
    (tmp_path / "state/evaluation.json").write_text(json.dumps({
        "evidence_refs": [],
        "snapshot_audit_888": {"record": "rec.json", "verdict": "READY", "n_checks": 18},
        "snapshot_audit_999": {"record": "rec.json", "verdict": "NOT_READY",
                               "n_checks": 18, "n_passed": 16,
                               "ready_for_independent_audit": False},
        rsa.READINESS_DISAGREEMENT_KEY: [
            {"run_id": "888", "field": "verdict", "recorded_value": "READY",
             "record_value": "NOT_READY"},
            {"run_id": "888", "field": "n_passed", "recorded_value": None,
             "record_value": 16}]}))
    res = rsa.check_readiness_claims(tmp_path, "999", _RECORD_16_OF_18)
    assert res["status"] == "FAIL", res
    assert any("without a prose disclosure" in p for p in res["problems"]), res


def test_readiness_claims_require_a_current_state_block(tmp_path):
    """A run that publishes no machine-checkable counts is not READY."""
    (tmp_path / "state").mkdir()
    (tmp_path / "state/evaluation.json").write_text(json.dumps({"evidence_refs": []}))
    res = rsa.check_readiness_claims(tmp_path, "999", _RECORD_16_OF_18)
    assert res["status"] == "FAIL", res
    assert any("no snapshot_audit_999 block" in p for p in res["problems"]), res


def test_readiness_claims_catch_a_report_lane_suite_green_over_a_red_suite(tmp_path):
    block = {"record": "rec.json", "verdict": "NOT_READY", "n_checks": 18,
             "n_passed": 16, "ready_for_independent_audit": False}
    report = ("snapshot audit: NOT READY (16/18 checks PASS)\n\n"
              "the lane suite is 49/49 with the accepted pytest scope green\n"
              "lane suite: PASS (48/49 checks, 420.864s)\n")
    res = rsa.check_readiness_claims(
        _claim_root(tmp_path, block, report), "999", _RECORD_16_OF_18)
    assert res["status"] == "FAIL", res
    assert any("lane suite: PASS" in p for p in res["problems"]), res


# --------------------------- check 21: trigger-claim assertion scope --------

def test_check21_flags_a_bare_negative_trigger_claim():
    """The defect audit CYCLE_39079133613 R1/R2 found: a 'does not fire' claim
    asserted with no matching trigger record. It must be an ASSERTION here."""
    hits = [h for h in rsa._scan_trigger_claims(
        "The re-score trigger does not fire this cycle.", "t")
        if h["claim"] in rsa.NEGATIVE_CLAIM_LABELS]
    assert hits, "a bare negative trigger claim must be flagged as an assertion"


def test_check21_does_not_flag_retraction_or_historical_text():
    """Preserved retraction evidence must NOT be flagged: the lane is forbidden
    from rewriting claim-bearing history, so the check must discriminate
    assertion from reference rather than demanding deletion of the record."""
    preserved = [
        "NO_NEW_PACKET is RETRACTED; the frozen trigger returns ADJUDICATE_REQUIRED.",
        "retracted_verdict = NO_NEW_PACKET",
        "cycles 39064597912..39079133613 published NO_NEW_PACKET without ever "
        "executing the trigger",
        "the trigger returns ADJUDICATE_REQUIRED",
    ]
    for text in preserved:
        hits = [h for h in rsa._scan_trigger_claims(text, "t")
                if h["claim"] in rsa.NEGATIVE_CLAIM_LABELS]
        assert not hits, f"reference/retraction text wrongly flagged: {text[:60]}"


def test_check21_requires_a_committed_trigger_record():
    """No declared record for this run is a FAIL, not a vacuous pass."""
    import json as _json
    import tempfile
    from pathlib import Path as _P
    with tempfile.TemporaryDirectory() as td:
        root = _P(td)
        (root / "state").mkdir()
        (root / "state/evaluation.json").write_text(
            _json.dumps({"lane": "evaluation", "trigger_reconciliation_999": {}}))
        out = rsa.check_trigger_verdict_matches_record(root, "999", root)
        assert out["status"] == "FAIL"
        assert out["trigger_verdict"] is None


def test_check21_is_environment_limited_not_silent_pass_when_mount_absent():
    """An unavailable product mount must be an explicit environment_limited FAIL,
    never a silent PASS (same convention as checks 15 and 18)."""
    import json as _json
    import os
    import tempfile
    from pathlib import Path as _P
    with tempfile.TemporaryDirectory() as td:
        root = _P(td)
        (root / "state").mkdir()
        rec = root / "rec.json"
        rec.write_text(_json.dumps({"schema": "lex-evaluation-trigger-reconciliation/1",
                                    "trigger": {"verdict": "ADJUDICATE_REQUIRED"}}))
        (root / "state/evaluation.json").write_text(
            _json.dumps({"trigger_reconciliation_999": {"record": "rec.json"}}))
        old = os.environ.get("LEX_PRODUCT_MOUNT")
        os.environ["LEX_PRODUCT_MOUNT"] = str(root / "no_such_mount")
        try:
            out = rsa.check_trigger_verdict_matches_record(root, "999", root)
        finally:
            if old is None:
                os.environ.pop("LEX_PRODUCT_MOUNT", None)
            else:
                os.environ["LEX_PRODUCT_MOUNT"] = old
        assert out["status"] == "FAIL"
        assert out.get("environment_limited") is True


# ------------------- audit CYCLE_39082753086 F1-F3: pinned regressions -------

def test_check21_state_scan_is_order_independent_at_head_and_tail():
    """F3 negative control (a): the audit measured that a bare negative claim
    placed at the HEAD of the state scope survived with 0 negatives, because the
    scope was serialized on ONE physical line so the documented line anchor could
    never engage. The same shape must be caught at head AND at tail."""
    import json as _json
    defect = {"verdict": "NO_NEW_PACKET", "direction_item_1_trigger_fires": False,
              "note": "The direction item (1) trigger does not fire this cycle."}
    scope = {"cycle_status": "DELIVERED", "verdict": "ADJUDICATE_REQUIRED",
             "n_checks": 21}
    for shaped in ({**{"injected": defect}, **scope}, {**scope, "injected": defect}):
        hits = [h for k in shaped
                for h in rsa._scan_trigger_claims(
                    _json.dumps({k: shaped[k]}, indent=2), k, machine=True)
                if h["claim"] in rsa.NEGATIVE_CLAIM_LABELS]
        assert len(hits) == 3, (hits, shaped.keys())


def test_check21_state_scan_catches_an_assertion_sharing_a_line_with_a_retraction_cue():
    """F3 negative control (b): the audit measured that a live assertion sharing a
    line with any retraction cue was excused and the check returned PASS. A cue in
    a DIFFERENT sentence must not excuse the claim it is not attached to."""
    import json as _json
    shaped = {"live": ("A prior claim was false. The trigger does not fire this cycle; "
                       "NO_NEW_PACKET stands")}
    hits = [h for h in rsa._scan_trigger_claims(
        _json.dumps(shaped, indent=2), "state", machine=True)
        if h["claim"] in rsa.NEGATIVE_CLAIM_LABELS]
    assert hits, "a cue two sentences away must not excuse a live assertion"


def test_check21_sibling_boolean_false_never_excuses_a_claim():
    """F3 root cause: ``false`` as a RETRACTION_MARKER matched a bare JSON boolean
    in a SIBLING field, so any field carrying false excused a claim anywhere near
    it. A machine source masks bare literals; quoted prose 'false' still counts."""
    import json as _json
    sibling = {"flag": {"value": False}, "claim": {"verdict": "NO_NEW_PACKET"}}
    hits = [h for k in sibling
            for h in rsa._scan_trigger_claims(
                _json.dumps({k: sibling[k]}, indent=2), k, machine=True)
            if h["claim"] in rsa.NEGATIVE_CLAIM_LABELS]
    assert hits, "a sibling boolean must not excuse a claim in another field"
    prose = _json.dumps({"v": "the prior claim was false; NO_NEW_PACKET is withdrawn"},
                        indent=2)
    assert not [h for h in rsa._scan_trigger_claims(prose, "s", machine=True)
                if h["claim"] in rsa.NEGATIVE_CLAIM_LABELS]


def test_state_file_is_excluded_from_the_record_manifest_with_a_stated_reason():
    """F2: a record cannot pin the sha256 of the file that carries the record's own
    sha256; the pin is stale by construction once state is updated. The exclusion
    must be declared with its reason, not silently dropped."""
    assert "state/evaluation.json" not in rsa.DELIVERABLE_MANIFEST_PATHS
    assert "state/evaluation.json" in rsa.MANIFEST_EXCLUSIONS
    assert "stale by construction" in rsa.MANIFEST_EXCLUSIONS["state/evaluation.json"]


def test_manifest_check_publishes_the_exclusion_reason():
    import tempfile
    from pathlib import Path as _P
    with tempfile.TemporaryDirectory() as td:
        res = rsa.check_manifest(_P(td))
        assert "excluded from the pin with stated reason" in res["detail"]
        assert "state/evaluation.json" in res["excluded_with_reason"]


def test_report_post_write_claim_reconciliation_parses_both_fields():
    text = ("post-write self-reference **VERIFIED** (...), post-write state claim "
            "**VERIFIED**.")
    got = rsa._report_declared_post_write(text)
    assert got == {"post_write_self_reference": "VERIFIED", "post_write_state_claim": "VERIFIED"}


def test_report_post_write_claim_reconciliation_catches_the_39082753086_defect(tmp_path):
    """F1 end to end: the report says NOT_APPLICABLE while the record says
    VERIFIED. Check 19 must go FAIL and the record must not be ready."""
    import json as _json
    (tmp_path / "reports/evaluation").mkdir(parents=True)
    (tmp_path / "reports/evaluation/CYCLE_999.md").write_text(
        "READY (21/21 checks PASS), post-write self-reference NOT_APPLICABLE "
        "(no declared self-reference), post-write state claim VERIFIED.", encoding="utf-8")
    record = {"schema": rsa.SCHEMA, "run_id": "999", "n_checks": 21, "n_passed": 21,
              "ready_for_independent_audit": True,
              "checks": [rsa._check("readiness_claims_match_record", True, "ok"),
                         rsa._check("some_other_check", True, "ok")],
              "post_write_self_reference": {"status": "VERIFIED"},
              "post_write_state_claim": {"status": "VERIFIED"}}
    out = rsa._post_write_report_claims(tmp_path, "999", record)
    assert out["status"] == "FAILED"
    assert any("NOT_APPLICABLE" in p for p in out["problems"])
    assert record["ready_for_independent_audit"] is False
    assert record["failing_checks"] == ["readiness_claims_match_record"]


def test_report_post_write_claim_reconciliation_passes_on_an_agreeing_report(tmp_path):
    import json as _json
    (tmp_path / "reports/evaluation").mkdir(parents=True)
    (tmp_path / "reports/evaluation/CYCLE_999.md").write_text(
        "READY (21/21 checks PASS), post-write self-reference VERIFIED, "
        "post-write state claim VERIFIED.", encoding="utf-8")
    record = {"schema": rsa.SCHEMA, "run_id": "999", "n_checks": 21, "n_passed": 21,
              "ready_for_independent_audit": True,
              "checks": [rsa._check("readiness_claims_match_record", True, "ok")],
              "post_write_self_reference": {"status": "VERIFIED"},
              "post_write_state_claim": {"status": "VERIFIED"}}
    out = rsa._post_write_report_claims(tmp_path, "999", record)
    assert out["status"] == "VERIFIED", out
    assert record["ready_for_independent_audit"] is True


def test_report_post_write_claim_ignores_quoted_code_but_keeps_real_declarations():
    """F1 follow-up measured this cycle: a repair report that QUOTES the sentence
    it corrected (`post-write self-reference NOT_APPLICABLE` inside backticks) must
    not be read as declaring that status. Inline code is masked; declarations
    outside it are still reconciled, and two disagreeing declarations are a FAIL
    rather than a silent first-wins."""
    import json as _json
    quoted = ("the report said `post-write self-reference NOT_APPLICABLE (no declared "
              "self-reference)`, which the record contradicted. It now reads post-write "
              "self-reference **VERIFIED**, post-write state claim **VERIFIED**.")
    got = rsa._report_declared_post_write(quoted)
    assert got == {"post_write_self_reference": "VERIFIED",
                   "post_write_state_claim": "VERIFIED"}
    conflicting = ("post-write self-reference **VERIFIED**. post-write self-reference "
                   "NOT_APPLICABLE. post-write state claim **VERIFIED**.")
    assert "__conflicts__" in rsa._report_declared_post_write(conflicting)

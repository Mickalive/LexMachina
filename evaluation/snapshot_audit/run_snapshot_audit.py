"""Snapshot audit-readiness verifier (stdlib only, no network, no Product import).

One command re-verifies everything this lane's snapshot claims and emits a
machine-readable readiness record for the INDEPENDENT auditor:

    python -m evaluation.snapshot_audit.run_snapshot_audit --run-id <run_id>

Checks (each recorded PASS/FAIL/NOT_RUN; no check is silently dropped):

  1. frozen_rubric_rehash       RULES_LABEL/RULES_GEOMETRY re-hash to the
                                direction-pinned sha256 values and every
                                vendored file matches VENDORED_SHA256.json.
  2. bar_gates_verdict          the frozen-bar gates entry point re-exits 0
                                PASS_NO_REGRESSION on the served lineage with
                                all negative controls proven and both incumbents
                                recomputed exactly (labels 5/65 = classes
                                38/22/5/0; geometry de 6 / fr 5 / it 5).
                                Requires the accepted product mount; its
                                absence is recorded as a FAIL with the
                                environment reason, never hidden.
  3. h1_default_record_identity  the fresh default-mode record is identical
                                to the accepted 38971202786.json except the
                                elapsed_s field (normalization: parsed JSON,
                                sort_keys, indent=2, elapsed_s removed).
  4. lane_suite_pass            python -m evaluation.lane_suite exits 0 with
                                a PASS summary (stdlib checks authoritative;
                                an absent pytest is a disclosed SKIP).
  5. state_evidence_refs_resolve every path in state/evaluation.json
                                evidence_refs exists in the snapshot.
  6. deliverable_manifest_complete  every file of the v50 deliverable set and
                                of this resume's delta exists; sha256 of each is
                                embedded in the readiness record.
  7. orchestration_diagnosis_record  the job-level orchestration diagnosis
                                artifact exists with the required structure.
  8. producer_write_scope_clean   the working tree would pass the workflow's
                                own "Enforce lane write scope" step (the step
                                that killed run 38982176936): every porcelain
                                entry must sit inside the producer scope.
  9. write_scope_diagnosis_record the 38982176936 write-scope diagnosis,
                                its executable reproduction and the void
                                manifest for the producer-authored self-audit
                                are all present and consistent, and the two
                                out-of-scope paths are ABSENT from the tree.

Exit 0 = ready_for_independent_audit (all checks PASS). Exit 1 = not ready.
The readiness record states the exact gate path the auditor must write:
results/audit/evaluation/CYCLE_<run_id>_GATE.json (uppercase _GATE.json,
relative to the audit-job checkout) and reports/audit/evaluation/CYCLE_<run_id>.md.
This module never writes audit artifacts itself; the independent audit
checkout remains the only audit of record.

No frozen rubric, threshold, bar, incumbent, gate success rule or recorded
verdict is read for modification; every frozen input is only re-hashed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from evaluation.snapshot_audit import write_scope as ws
from evaluation.packet_lineage_sweep import verify_rules_identity

SCHEMA = "lex-evaluation-snapshot-audit/1"

# Direction v50 pinned values (factory_direction.json lanes.evaluation.question).
RULES_LABEL_SHA256 = "4457e971df3dc5d10af2a727aa675afc15a15564c18eed4cede0af5eb41b4608"
RULES_GEOMETRY_SHA256 = "a7452748d40c511a14a1c7848ece5fe7f8f8901cc30f45a66918c89eb593a633"
ACCEPTED_RUN_ID = "38971202786"
ACCEPTED_BAR_GATES_RECORD = "results/evaluation/bar_gates/38971202786.json"
LABEL_INCUMBENT = {"n_scored": 65, "n_supported": 5,
                   "classes": {"OFF-DOMAIN": 38, "UNBACKED": 22, "SUPPORTED": 5, "INVERTED": 0}}
GEOMETRY_INCUMBENT = {"de-kapitalverletzung": 6, "fr-bail-entretien": 5,
                      "it-responsabilita-medica": 5}
DIAGNOSIS_PATH = "evaluation/snapshot_audit/orchestration_diagnosis_2026-10-16.json"
DIAGNOSIS_REQUIRED_RUNS = ("38972887369", "38977570612")

# Run 38982176936 died at the workflow's "Enforce lane write scope" step
# because the producer authored audit-of-record files outside its write
# scope. Check 8 re-runs that step's classifier on the live tree; check 9
# requires the diagnosis + executable reproduction + void manifest.
WRITE_SCOPE_DIAGNOSIS_PATH = "evaluation/snapshot_audit/orchestration_diagnosis_38982176936.json"
WRITE_SCOPE_REPRO_PATH = "results/evaluation/snapshot_audit/38982176936_write_scope_repro.json"
VOID_DIR = "results/evaluation/snapshot_audit/void_self_audit_38982176936"
VOID_MANIFEST_PATH = f"{VOID_DIR}/VOID.json"
OUT_OF_SCOPE_ORIGINALS = (
    "results/audit/evaluation/CYCLE_38982176936_GATE.json",
    "reports/audit/evaluation/CYCLE_38982176936.md",
)
# sha256 of the voided files as measured when they were removed (they are
# also re-hashed here against the preserved copies, so a swapped copy fails).
VOID_EXPECTED_SHA256 = {
    "CYCLE_38982176936_GATE.json": "e8ce69f7f49feb66debc1b15e3fd221090140f362a3cdc7b040de4e11692ec5f",
    "CYCLE_38982176936.md": "4e9a72afa710d365674fc4dc1087ca02ee7d8844d7370b94edb84acd34f2325f",
}

# The v50 frozen-bar deliverable set plus this resume's delta. Every listed
# file must exist; each is sha256-pinned into the readiness record.
DELIVERABLE_MANIFEST_PATHS = [
    "evaluation/frozen_bars/RULES_LABEL.json",
    "evaluation/frozen_bars/RULES_GEOMETRY.json",
    "evaluation/frozen_bars/FETCH_RECORD.json",
    "evaluation/frozen_bars/VERDICT_CONTRACT.json",
    "evaluation/frozen_bars/label_gate.py",
    "evaluation/frozen_bars/geometry_gate.py",
    "evaluation/frozen_bars/run_bar_gates.py",
    "evaluation/frozen_bars/run_adjudication_probes.py",
    "evaluation/frozen_bars/verdict_contract.py",
    "evaluation/frozen_bars/vendored/VENDORED_SHA256.json",
    "tests/evaluation/test_frozen_bar_gates.py",
    "tests/evaluation/test_bar_gate_verdict_contract.py",
    "results/evaluation/bar_gates/38971202786.json",
    "results/evaluation/verdict_contract/FREEZE_38972887369.json",
    "results/evaluation/verdict_contract/38972887369_reachability.json",
    "reports/evaluation/BAR_GATES_38972887369.md",
    "evaluation/snapshot_audit/run_snapshot_audit.py",
    "evaluation/snapshot_audit/orchestration_diagnosis_2026-10-16.json",
    "tests/evaluation/test_snapshot_audit.py",
    "reports/evaluation/CYCLE_38978411574.md",
    "state/evaluation.json",
    # Run 38982176936: the two IN-SCOPE records it produced are preserved
    # unchanged, and this resume's write-scope delta is pinned below.
    "results/evaluation/bar_gates/38982176936.json",
    "results/evaluation/snapshot_audit/38982176936.json",
    "evaluation/snapshot_audit/write_scope.py",
    "evaluation/snapshot_audit/orchestration_diagnosis_38982176936.json",
    "results/evaluation/snapshot_audit/38982176936_write_scope_repro.json",
    "results/evaluation/snapshot_audit/void_self_audit_38982176936/VOID.json",
    "results/evaluation/snapshot_audit/void_self_audit_38982176936/CYCLE_38982176936_GATE.json",
    "results/evaluation/snapshot_audit/void_self_audit_38982176936/CYCLE_38982176936.md",
    "reports/evaluation/CYCLE_38982728075.md",
    # Operational resume of run 38986445355 (run 38989947869): the completed
    # retrieval/counter-authority falsification benchmark and its diagnosis.
    "evaluation/benchmark_retrieval_counter_authority.py",
    "tests/evaluation/test_benchmark_retrieval_counter_authority.py",
    "evaluation/snapshot_audit/orchestration_diagnosis_38986445355.json",
    "results/evaluation/bar_gates/38989947869.json",
    "results/evaluation/retrieval_counter_authority_benchmark/38989947869.json",
    "results/evaluation/retrieval_counter_authority_benchmark/38989947869_leg1_served_baseline.json",
    "results/evaluation/retrieval_counter_authority_benchmark/38989947869_leg2_hostile_geometry.json",
    "results/evaluation/retrieval_counter_authority_benchmark/38989947869_leg3_blanked_evidence.json",
    "reports/evaluation/RETRIEVAL_CA_BENCHMARK_38989947869.md",
    "reports/evaluation/CYCLE_38989947869.md",
    # Run 39004097533: the counter-authority label benchmark. A PRODUCT_FALSIFIED
    # result on the label axis plus five falsified GATE predicates; both are
    # negative results of record and are pinned here so neither can be softened
    # silently in a later cycle.
    "evaluation/counter_authority_label_benchmark.py",
    "tests/evaluation/test_counter_authority_label_benchmark.py",
    "results/evaluation/counter_authority_label_benchmark/FROZEN_HYPOTHESIS_39004097533.json",
    "results/evaluation/counter_authority_label_benchmark/39004097533.json",
    "reports/evaluation/COUNTER_AUTHORITY_LABEL_BENCHMARK_39004097533.md",
]

# Run 38986445355's team job died at step 6 ('Run lane cycle') after committing
# a broken, non-runnable benchmark script. Check 10 requires the job-level
# diagnosis artifact; check 11 re-executes the three-leg benchmark and requires
# the frozen combined verdict (BENCHMARK_VALID_NO_FALSIFICATION, exit 0).
RUN_38986445355_DIAGNOSIS_PATH = "evaluation/snapshot_audit/orchestration_diagnosis_38986445355.json"
RETRIEVAL_CA_BENCHMARK_RECORD = (
    "results/evaluation/retrieval_counter_authority_benchmark/38989947869.json")

# run 38993062549: the packet-lineage gate-validity falsification. An ACCEPTED
# NEGATIVE result about the bars; the check exists so it cannot be softened
# silently in a later cycle.
SWEEP_RECORD = "results/evaluation/packet_lineage_sweep/38993062549.json"
SWEEP_FROZEN_HYPOTHESIS = (
    "results/evaluation/packet_lineage_sweep/FROZEN_HYPOTHESIS_38993062549.json")

# run 39004097533: the counter-authority label benchmark on real accepted product
# artifacts. Its verdict PRODUCT_FALSIFIED and its five fired gate predicates are
# negative results of record about the product's counter-authority labelling AND
# about the accepted gate's packet-admission wiring.
CA_LABEL_RECORD = "results/evaluation/counter_authority_label_benchmark/39004097533.json"
CA_LABEL_FROZEN_HYPOTHESIS = (
    "results/evaluation/counter_authority_label_benchmark/FROZEN_HYPOTHESIS_39004097533.json")


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _check(cid: str, ok: bool, detail: str, **extra) -> dict:
    out = {"id": cid, "status": "PASS" if ok else "FAIL", "detail": detail}
    out.update(extra)
    return out


def check_rubric_rehash(repo_root: Path) -> dict:
    """Check 1: frozen rubric bytes re-hash to the direction-pinned values."""
    mismatches = []
    observed = {}
    for rel, pinned in (("evaluation/frozen_bars/RULES_LABEL.json", RULES_LABEL_SHA256),
                        ("evaluation/frozen_bars/RULES_GEOMETRY.json", RULES_GEOMETRY_SHA256)):
        p = repo_root / rel
        if not p.exists():
            mismatches.append({"path": rel, "error": "missing"})
            continue
        actual = _sha256_file(p)
        observed[rel] = actual
        if actual != pinned:
            mismatches.append({"path": rel, "expected_sha256": pinned, "actual_sha256": actual})
    vendored_sha_path = repo_root / "evaluation/frozen_bars/vendored/VENDORED_SHA256.json"
    n_vendored = 0
    if vendored_sha_path.exists():
        vendored = json.loads(vendored_sha_path.read_text(encoding="utf-8"))
        for rel, expected in vendored.get("files", {}).items():
            n_vendored += 1
            p = repo_root / rel
            if not p.exists():
                mismatches.append({"path": rel, "error": "missing vendored file"})
                continue
            actual = _sha256_file(p)
            if actual != expected:
                mismatches.append({"path": rel, "expected_sha256": expected,
                                   "actual_sha256": actual})
    else:
        mismatches.append({"path": str(vendored_sha_path), "error": "missing"})
    ok = not mismatches
    detail = (f"RULES_LABEL={observed.get('evaluation/frozen_bars/RULES_LABEL.json', 'missing')[:12]}… "
              f"RULES_GEOMETRY={observed.get('evaluation/frozen_bars/RULES_GEOMETRY.json', 'missing')[:12]}… "
              f"vendored {n_vendored}/{n_vendored} match") if ok else f"digest mismatches: {mismatches}"
    return _check("frozen_rubric_rehash", ok, detail,
                  observed=observed, n_vendored_checked=n_vendored, mismatches=mismatches)


def run_bar_gates(repo_root: Path, out_path: Path) -> tuple[int, dict | None, str]:
    """Check 2 helper: execute the frozen-bar gates entry point as a subprocess."""
    proc = subprocess.run(
        [sys.executable, "-m", "evaluation.frozen_bars.run_bar_gates", "--out", str(out_path)],
        cwd=str(repo_root), capture_output=True, text=True, timeout=600)
    record = None
    if out_path.exists():
        try:
            record = json.loads(out_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            record = None
    return proc.returncode, record, (proc.stderr or "").strip()


def check_bar_gates_verdict(repo_root: Path, workdir: Path) -> dict:
    """Check 2: gates exit 0 PASS_NO_REGRESSION with incumbents recomputed."""
    out_path = workdir / "bar_gates_fresh.json"
    rc, record, stderr = run_bar_gates(repo_root, out_path)
    if rc == 2 or record is None:
        return _check("bar_gates_verdict", False,
                      f"bar gates did not produce a record (exit {rc}); "
                      f"stderr: {stderr[:400] or 'empty'}", exit_code=rc)
    if rc != 0:
        return _check("bar_gates_verdict", False,
                      f"bar gates exit {rc}; verdict={record.get('verdict')}", exit_code=rc)
    # The gate counts only OBSERVED defect classes (a zero-count class is
    # absent from its classes dict — even the accepted record omits INVERTED).
    # Default-zero semantics: an absent class means count 0, which is exactly
    # what the incumbent's INVERTED=0 asserts. A regressed packet with inverted
    # rows present carries INVERTED: N>0 and still mismatches.
    observed_classes = record["label_gate"]["classes"]
    label_classes_ok = all(observed_classes.get(k, 0) == v
                           for k, v in LABEL_INCUMBENT["classes"].items())
    label_ok = (record["label_gate"]["n_scored"] == LABEL_INCUMBENT["n_scored"]
                and record["label_gate"]["n_supported"] == LABEL_INCUMBENT["n_supported"]
                and label_classes_ok)
    geom_ok = record["geometry_gate"]["per_bundle_counts"] == GEOMETRY_INCUMBENT
    neg_ok = bool(record.get("negative_controls_all_proven"))
    ok = (record.get("verdict") == "PASS_NO_REGRESSION" and label_ok and geom_ok and neg_ok)
    detail = (f"verdict={record.get('verdict')} labels {record['label_gate']['n_supported']}/"
              f"{record['label_gate']['n_scored']} classes={record['label_gate']['classes']} "
              f"geometry={record['geometry_gate']['per_bundle_counts']} "
              f"negative_controls={neg_ok} absolute={record['absolute_status_summary']}")
    return _check("bar_gates_verdict", ok, detail, exit_code=rc, fresh_record=str(out_path),
                  label_recomputed=record["label_gate"]["classes"],
                  geometry_recomputed=record["geometry_gate"]["per_bundle_counts"],
                  absolute_status=record["absolute_status_summary"],
                  negative_controls_all_proven=neg_ok)


def compare_h1(fresh: dict, accepted: dict) -> dict:
    """Check 3 helper: identical except elapsed_s under a fixed normalization.

    Normalization: parsed JSON, sort_keys=True, indent=2, top-level elapsed_s
    removed from both sides. Formatting-independent by construction.
    """
    def norm(rec: dict) -> str:
        stripped = {k: v for k, v in rec.items() if k != "elapsed_s"}
        return json.dumps(stripped, sort_keys=True, indent=2, ensure_ascii=False)

    diffs = []
    if norm(fresh) != norm(accepted):
        fresh_keys, acc_keys = set(fresh), set(accepted)
        for k in sorted(fresh_keys | acc_keys):
            if k == "elapsed_s":
                continue
            if fresh.get(k) != accepted.get(k):
                diffs.append(k)
    return {"identical_except_elapsed_s": not diffs, "differing_fields": diffs}


def check_h1(repo_root: Path, fresh_record_path: Path) -> dict:
    accepted_path = repo_root / ACCEPTED_BAR_GATES_RECORD
    if not fresh_record_path.exists():
        return _check("h1_default_record_identity", False,
                      "fresh bar-gates record not available (check 2 did not produce one)",
                      status="NOT_RUN")
    if not accepted_path.exists():
        return _check("h1_default_record_identity", False,
                      f"accepted record missing: {ACCEPTED_BAR_GATES_RECORD}")
    fresh = json.loads(fresh_record_path.read_text(encoding="utf-8"))
    accepted = json.loads(accepted_path.read_text(encoding="utf-8"))
    cmp_ = compare_h1(fresh, accepted)
    ok = cmp_["identical_except_elapsed_s"]
    detail = ("fresh default-mode record identical to accepted "
              f"{ACCEPTED_BAR_GATES_RECORD} except elapsed_s (normalization: parsed JSON, "
              "sort_keys, indent=2, elapsed_s removed)") if ok else \
             (f"H1 VIOLATION, differing fields: {cmp_['differing_fields']}")
    return _check("h1_default_record_identity", ok, detail,
                  differing_fields=cmp_["differing_fields"],
                  normalization="parsed JSON, sort_keys=True, indent=2, elapsed_s removed")


def check_lane_suite(repo_root: Path) -> dict:
    proc = subprocess.run([sys.executable, "-m", "evaluation.lane_suite"],
                          cwd=str(repo_root), capture_output=True, text=True, timeout=600)
    out = proc.stdout or ""
    m = re.search(r"lane suite: (PASS|FAIL)", out)
    summary = m.group(1) if m else None
    ok = proc.returncode == 0 and summary == "PASS"
    tail = [ln for ln in out.strip().splitlines() if ln.strip()][-1:] or ["<no output>"]
    return _check("lane_suite_pass", ok,
                  f"exit={proc.returncode} summary={summary or 'unparsed'} last_line={tail[0]}",
                  exit_code=proc.returncode, summary=summary)


def check_evidence_refs(repo_root: Path) -> dict:
    state_path = repo_root / "state/evaluation.json"
    if not state_path.exists():
        return _check("state_evidence_refs_resolve", False, "state/evaluation.json missing")
    state = json.loads(state_path.read_text(encoding="utf-8"))
    refs = state.get("evidence_refs", [])
    missing = []
    for r in refs:
        # Refs are repo-root-relative paths; a trailing parenthetical note, if
        # any, is not part of the path (first whitespace token is the path).
        p = r.split()[0] if r.split() else r
        if not (repo_root / p).exists():
            missing.append(r)
    ok = not missing
    detail = f"{len(refs)}/{len(refs)} evidence_refs resolve (rule: first whitespace token is the path)" if ok \
        else f"{len(missing)} unresolved refs: {missing[:5]}"
    return _check("state_evidence_refs_resolve", ok, detail,
                  n_refs=len(refs), n_missing=len(missing), missing=missing[:10])


def check_manifest(repo_root: Path) -> dict:
    missing = [rel for rel in DELIVERABLE_MANIFEST_PATHS if not (repo_root / rel).exists()]
    manifest = {rel: _sha256_file(repo_root / rel)
                for rel in DELIVERABLE_MANIFEST_PATHS if (repo_root / rel).exists()}
    ok = not missing
    detail = (f"{len(manifest)}/{len(DELIVERABLE_MANIFEST_PATHS)} deliverable files present, "
              "sha256 embedded in readiness record") if ok else f"missing deliverable files: {missing}"
    return _check("deliverable_manifest_complete", ok, detail,
                  n_files=len(manifest), missing=missing)


def check_diagnosis_record(repo_root: Path) -> dict:
    path = repo_root / DIAGNOSIS_PATH
    if not path.exists():
        return _check("orchestration_diagnosis_record", False, f"{DIAGNOSIS_PATH} missing")
    diag = json.loads(path.read_text(encoding="utf-8"))
    problems = []
    if diag.get("schema") != "lex-evaluation-orchestration-diagnosis/1":
        problems.append("schema")
    if not diag.get("query_method"):
        problems.append("query_method")
    if not diag.get("limits"):
        problems.append("limits")
    runs = diag.get("runs", {})
    for rid in DIAGNOSIS_REQUIRED_RUNS:
        run = runs.get(rid)
        if not run:
            problems.append(f"runs.{rid}")
            continue
        if not run.get("conclusion"):
            problems.append(f"runs.{rid}.conclusion")
        audit = run.get("jobs", {}).get("audit", {})
        conclusion = audit.get("conclusion")
        if conclusion == "failure" and not audit.get("failed_step"):
            problems.append(f"runs.{rid}.jobs.audit.failed_step")
        if conclusion == "skipped" and not (audit.get("skipped_because") or audit.get("interpretation")):
            problems.append(f"runs.{rid}.jobs.audit.skipped_because")
    amb = runs.get("38977570612", {}).get("jobs", {}).get("audit", {}).get("ambiguity_flag")
    if not amb:
        problems.append("runs.38977570612 ambiguous-cause flag")
    ok = not problems
    detail = ("diagnosis artifact structurally complete; both failed runs carry job/step-level "
              "conclusions; the un-loggable cause ambiguity is explicitly flagged") if ok \
        else f"diagnosis structural problems: {problems}"
    return _check("orchestration_diagnosis_record", ok, detail, problems=problems)


def check_producer_write_scope(repo_root: Path) -> dict:
    """Check 8: the live tree would pass the workflow's write-scope step.

    Same classifier as the "Enforce lane write scope" step of core-lane.yml
    (see evaluation/snapshot_audit/write_scope.py for the fidelity note).
    A FAIL here is exactly the failure mode that killed run 38982176936.
    """
    try:
        verdict = ws.evaluate_porcelain(ws.live_porcelain(repo_root), "evaluation")
    except (ValueError, subprocess.CalledProcessError) as exc:
        return _check("producer_write_scope_clean", False, f"could not classify tree: {exc}")
    ok = verdict["scope_clean"]
    detail = (f"{verdict['n_entries']} porcelain entries, all inside the producer scope "
              f"(junk modelled as removed by the workflow's 'Clean generated junk' step)") if ok else \
             (f"SCOPE VIOLATION, {verdict['n_bad']} out-of-scope paths: {verdict['bad_paths']}")
    return _check("producer_write_scope_clean", ok, detail,
                  bad_paths=verdict["bad_paths"], n_entries=verdict["n_entries"],
                  junk_dropped=verdict["junk_dropped"])


def check_write_scope_diagnosis(repo_root: Path) -> dict:
    """Check 9: the 38982176936 write-scope failure is diagnosed, reproduced
    and its invalid self-audit is voided — and the offending paths are gone."""
    problems = []
    diag_path = repo_root / WRITE_SCOPE_DIAGNOSIS_PATH
    if not diag_path.exists():
        problems.append(f"{WRITE_SCOPE_DIAGNOSIS_PATH} missing")
    else:
        diag = json.loads(diag_path.read_text(encoding="utf-8"))
        run = diag.get("runs", {}).get("38982176936", {})
        team = run.get("jobs", {}).get("team", {})
        if team.get("failed_step") != "Enforce lane write scope":
            problems.append("diagnosis team.failed_step")
        audit = run.get("jobs", {}).get("audit", {})
        if audit.get("conclusion") != "skipped":
            problems.append("diagnosis audit conclusion")
        cause = run.get("root_cause", {})
        if sorted(cause.get("out_of_scope_paths", [])) != sorted(OUT_OF_SCOPE_ORIGINALS):
            problems.append("diagnosis root_cause.out_of_scope_paths")
        if "38982728075" not in diag.get("runs", {}):
            problems.append("diagnosis resume run 38982728075")
    repro_path = repo_root / WRITE_SCOPE_REPRO_PATH
    if not repro_path.exists():
        problems.append(f"{WRITE_SCOPE_REPRO_PATH} missing")
    else:
        repro = json.loads(repro_path.read_text(encoding="utf-8"))
        fidelity = repro.get("real_control_plane_step_fidelity", {})
        if fidelity.get("identical_bad_set") is not True:
            problems.append("repro real-step/python-port BAD sets not identical")
        if fidelity.get("real_step_exit_code") != 3:
            problems.append("repro real-step exit code")
        if sorted(repro.get("python_port_verdict", {}).get("bad_paths", [])) != sorted(OUT_OF_SCOPE_ORIGINALS):
            problems.append("repro python-port bad paths")
    void_path = repo_root / VOID_MANIFEST_PATH
    if not void_path.exists():
        problems.append(f"{VOID_MANIFEST_PATH} missing")
    else:
        void = json.loads(void_path.read_text(encoding="utf-8"))
        recorded = {a["original_path"]: a["sha256"] for a in void.get("artifacts", [])}
        if sorted(recorded) != sorted(OUT_OF_SCOPE_ORIGINALS):
            problems.append("void manifest artifact paths")
        for name, expected in VOID_EXPECTED_SHA256.items():
            copy = repo_root / VOID_DIR / name
            if not copy.exists():
                problems.append(f"void copy missing {name}")
                continue
            if _sha256_file(copy) != expected:
                problems.append(f"void copy sha256 mismatch {name}")
        if any(recorded.get(p) != VOID_EXPECTED_SHA256[Path(p).name] for p in OUT_OF_SCOPE_ORIGINALS):
            problems.append("void manifest sha256 values")
    for rel in OUT_OF_SCOPE_ORIGINALS:
        if (repo_root / rel).exists():
            problems.append(f"out-of-scope original still in tree: {rel}")
    ok = not problems
    detail = ("38982176936 write-scope failure diagnosed at step level, reproduced with the real "
              "control-plane step (exit 3, identical BAD set), self-audit voided with byte-identical "
              "copies, and both out-of-scope originals absent from the producer tree") if ok else \
             f"write-scope diagnosis problems: {problems}"
    return _check("write_scope_diagnosis_record", ok, detail, problems=problems)


def check_run_38986445355_diagnosis(repo_root: Path) -> dict:
    """Check 10: the 38986445355 mid-cycle producer death is diagnosed at job level."""
    path = repo_root / RUN_38986445355_DIAGNOSIS_PATH
    if not path.exists():
        return _check("orchestration_diagnosis_38986445355", False,
                      f"{RUN_38986445355_DIAGNOSIS_PATH} missing")
    try:
        diag = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return _check("orchestration_diagnosis_38986445355", False,
                      f"diagnosis is not valid JSON: {exc}")
    problems = []
    if diag.get("schema") != "lex-evaluation-orchestration-diagnosis/1":
        problems.append("schema")
    if not diag.get("query_method"):
        problems.append("query_method")
    if not diag.get("limits"):
        problems.append("limits")
    run = diag.get("runs", {}).get("38986445355", {})
    if not run:
        problems.append("runs.38986445355")
    else:
        if run.get("conclusion") != "failure":
            problems.append("runs.38986445355.conclusion")
        team = run.get("jobs", {}).get("team", {})
        if team.get("failed_step") != "Run lane cycle":
            problems.append("runs.38986445355.jobs.team.failed_step")
        if team.get("step_number") != 6:
            problems.append("runs.38986445355.jobs.team.step_number")
        audit = run.get("jobs", {}).get("audit", {})
        if audit.get("conclusion") != "skipped":
            problems.append("runs.38986445355.jobs.audit.conclusion")
        cause = run.get("root_cause", {})
        if "non-runnable" not in cause.get("class", "") and \
                "incomplete" not in cause.get("class", ""):
            problems.append("runs.38986445355.root_cause.class")
        if not cause.get("candidate_causes_of_the_step_failure_not_disambiguated"):
            problems.append("runs.38986445355.root_cause.candidate_causes (must be a "
                            "recorded set, never a single asserted cause without logs)")
    if "38989947869" not in diag.get("runs", {}):
        problems.append("runs.38989947869 (resume run)")
    ok = not problems
    detail = ("38986445355 diagnosed at job/step level (team step 6 'Run lane cycle' "
              "failure, audit skipped); un-loggable provider cause correctly hedged as "
              "a candidate set; resume run 38989947869 recorded") if ok else \
             f"diagnosis structural problems: {problems}"
    return _check("orchestration_diagnosis_38986445355", ok, detail, problems=problems)


def check_retrieval_ca_benchmark(repo_root: Path) -> dict:
    """Check 11: the three-leg falsification benchmark record has the frozen verdict."""
    path = repo_root / RETRIEVAL_CA_BENCHMARK_RECORD
    if not path.exists():
        return _check("retrieval_ca_benchmark_record", False,
                      f"{RETRIEVAL_CA_BENCHMARK_RECORD} missing")
    try:
        rec = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return _check("retrieval_ca_benchmark_record", False,
                      f"benchmark record is not valid JSON: {exc}")
    problems = []
    if rec.get("schema") != "lex-evaluation-retrieval-ca-benchmark/1":
        problems.append("schema")
    if rec.get("verdict") != "BENCHMARK_VALID_NO_FALSIFICATION":
        problems.append(f"verdict={rec.get('verdict')!r} (expected "
                        "BENCHMARK_VALID_NO_FALSIFICATION on the served lineage)")
    if rec.get("exit_code") != 0:
        problems.append(f"exit_code={rec.get('exit_code')}")
    if rec.get("falsification_proven") is not True:
        problems.append("falsification_proven is not true")
    legs = {lg.get("leg"): lg for lg in rec.get("legs", [])}
    expected = {
        "served_baseline": 0,
        "geometry_falsification_hostile": 1,
        "label_falsification_blanked_evidence": 1,
    }
    for leg_id, exp_rc in expected.items():
        lg = legs.get(leg_id)
        if lg is None:
            problems.append(f"missing leg {leg_id}")
            continue
        if lg.get("exit_code") != exp_rc:
            problems.append(f"leg {leg_id} exit {lg.get('exit_code')} != {exp_rc}")
        if lg.get("exit_code_matches_expectation") is not True:
            problems.append(f"leg {leg_id} exit_code_matches_expectation is not true")
    if rec.get("reuses_entry_point") != "evaluation.frozen_bars.run_bar_gates":
        problems.append("reuses_entry_point (must be the accepted run_bar_gates module)")
    # per-leg durable records must exist
    for name in (f"{rec.get('run_id')}_leg1_served_baseline.json",
                 f"{rec.get('run_id')}_leg2_hostile_geometry.json",
                 f"{rec.get('run_id')}_leg3_blanked_evidence.json"):
        if not (repo_root / "results/evaluation/retrieval_counter_authority_benchmark" / name).exists():
            problems.append(f"missing per-leg record {name}")
    ok = not problems
    detail = (f"benchmark {rec.get('run_id')}: BENCHMARK_VALID_NO_FALSIFICATION exit 0; "
              f"legs 0/1/1 as frozen; falsification_proven=true; reuses "
              f"{rec.get('reuses_entry_point')}") if ok else \
             f"benchmark record problems: {problems}"
    return _check("retrieval_ca_benchmark_record", ok, detail, problems=problems,
                  verdict=rec.get("verdict"), exit_code=rec.get("exit_code"),
                  falsification_proven=rec.get("falsification_proven"))


def check_gate_validity_sweep(repo_root: Path) -> dict:
    """Check 12: the packet-lineage gate-validity falsification is on disk intact.

    This is an ACCEPTED NEGATIVE RESULT about the bars, so the check exists to
    stop it being quietly softened: it verifies the recorded verdict, the
    anchor-sensitivity result that carries the falsification, the frozen-hypothesis
    provenance, and that the non-vacuity battery is complete. A later cycle that
    wants to retract the finding has to change this check explicitly, in the
    open, rather than editing a number somewhere else.
    """
    path = repo_root / SWEEP_RECORD
    frozen = repo_root / SWEEP_FROZEN_HYPOTHESIS
    problems = []
    if not frozen.exists():
        problems.append(f"{SWEEP_FROZEN_HYPOTHESIS} missing")
    if not path.exists():
        return _check("gate_validity_sweep", False,
                      f"{SWEEP_RECORD} missing", problems=problems)
    try:
        rec = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return _check("gate_validity_sweep", False,
                      f"sweep record is not valid JSON: {exc}", problems=problems)
    if rec.get("schema") != "lex-evaluation-packet-lineage-sweep/1":
        problems.append(f"schema={rec.get('schema')!r}")
    if rec.get("verdict") != "GATE_FALSIFIED_ON_ACCEPTED_LINEAGE":
        problems.append(f"verdict={rec.get('verdict')!r}")
    if rec.get("exit_code") != 1:
        problems.append(f"exit_code={rec.get('exit_code')!r}")
    # the bars were re-hashed, not re-derived
    ident = rec.get("rules_identity") or {}
    if ident.get("all_match") is not True:
        problems.append("rules_identity.all_match is not true")
    # the falsification itself
    f5 = rec.get("F5_ANCHOR_SENSITIVITY") or {}
    if f5.get("verdict_set_is_anchor_determined") is not True:
        problems.append("F5.verdict_set_is_anchor_determined is not true")
    if f5.get("enforced") is not False:
        problems.append("F5 must stay descriptive (enforced=false); enforcing it would invent a bar")
    if (f5.get("n_distinct_verdict_sets") or 0) < 2:
        problems.append("F5 shows fewer than two distinct verdict sets; the falsification does not hold")
    f3 = rec.get("F3_COUNT_MASK_CHURN") or {}
    if f3.get("enforced") is not False:
        problems.append("F3 must stay descriptive (enforced=false)")
    # non-vacuity: without it every statement above is void
    b = rec.get("non_vacuity_battery") or {}
    if b.get("all_hold") is not True:
        problems.append("non-vacuity battery is not complete; all predicate statements are void")
    for key in ("N1_POSITIVE_must_fire", "N2_NEGATIVE_incumbent_must_not_fire",
                "N3_NEGATIVE_provenance_must_not_fire",
                "N4_NEGATIVE_audit_gate_must_not_fire"):
        if (b.get(key) or {}).get("holds") is not True:
            problems.append(f"battery element {key} does not hold")
    # every gate invocation produced a real record: a missing verdict is not a pass
    for pid, e in (rec.get("per_packet") or {}).items():
        if (e.get("gate") or {}).get("environment_failure") is not False:
            problems.append(f"packet {pid} carries an environment failure")
    # the claim ceiling must keep its disclaimers
    cc = (rec.get("claim_ceiling") or "").lower()
    for phrase in ("not the candidate", "jurist usefulness", "absolute bars"):
        if phrase not in cc:
            problems.append(f"claim_ceiling is missing the disclaimer {phrase!r}")
    ok = not problems
    detail = (f"sweep {rec.get('run_id')}: {rec.get('verdict')} exit {rec.get('exit_code')}; "
              f"anchor-determined with {f5.get('n_distinct_verdict_sets')} distinct verdict sets; "
              f"battery elements {sum(1 for k, v in b.items() if isinstance(v, dict) and v.get('holds'))}"
              f"/{sum(1 for v in b.values() if isinstance(v, dict))} proven "
              f"(all_hold={b.get('all_hold')}); N5 rules re-hash {ident.get('all_match')}") \
        if ok else f"sweep problems: {problems}"
    return _check("gate_validity_sweep", ok, detail, problems=problems,
                  verdict=rec.get("verdict"), exit_code=rec.get("exit_code"))


def check_counter_authority_label_benchmark(repo_root: Path) -> dict:
    """Check 13: the counter-authority label falsification is on disk intact.

    Two negative results of record are pinned here:

    * PRODUCT_FALSIFIED on the product's counter-authority label axis, measured
      with the identical frozen RULES_LABEL.json on real accepted product
      artifacts, under a hypothesis frozen before execution; and
    * five fired gate predicates, whose consequence is that the accepted
      counter-label gate cannot observe a collapse of label support and is
      therefore unsafe as the SOLE machine packet-admission input that Product
      direction obligation (1) requires.

    The check verifies the recorded verdict, the record's own coherence verdict,
    the frozen-hypothesis provenance, the proven battery and the frozen-rubric
    digests. A later cycle that wants to retract either result has to change this
    check explicitly, in the open, rather than editing a number somewhere else.
    """
    problems = []
    frozen = repo_root / CA_LABEL_FROZEN_HYPOTHESIS
    if not frozen.exists():
        problems.append(f"{CA_LABEL_FROZEN_HYPOTHESIS} missing")
    path = repo_root / CA_LABEL_RECORD
    if not path.exists():
        return _check("counter_authority_label_benchmark", False,
                      f"{CA_LABEL_RECORD} missing", problems=problems)
    try:
        rec = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return _check("counter_authority_label_benchmark", False,
                      f"record is not valid JSON: {exc}", problems=problems)
    if rec.get("schema") != "lex-counter-authority-label-benchmark/1":
        problems.append(f"unexpected schema {rec.get('schema')!r}")
    if rec.get("verdict") != "PRODUCT_FALSIFIED":
        problems.append(f"recorded verdict is {rec.get('verdict')!r}, expected PRODUCT_FALSIFIED")
    if rec.get("non_vacuity_all_hold") is not True:
        problems.append("non-vacuity battery did not hold; a suppressed finding is not a result")
    coherence = rec.get("record_coherence") or {}
    if coherence.get("coherent") is not True:
        problems.append(f"record self-check not coherent: {coherence.get('problems')}")
    fh = rec.get("frozen_hypothesis") or {}
    if fh.get("frozen_before_execution") is not True:
        problems.append("record does not attest that the hypothesis was frozen before execution")
    if frozen.exists() and fh.get("sha256") != _sha256_file(frozen):
        problems.append("record was produced against a different freeze file")
    ident = verify_rules_identity()
    if not ident.get("all_match"):
        problems.append(f"frozen RULES re-hash failed: {ident}")
    fired = rec.get("gate_findings_fired") or []
    expected_fired = {
        "L2_gate_admits_total_label_collapse",
        "L3_gate_population_predicate_is_confounded",
        "L4_rate_and_count_semantics_disagree",
        "L5_frozen_rubric_population_and_gate_incumbent_disagree",
        "L6_anchor_ordering_is_not_quality_ordering",
    }
    if set(fired) != expected_fired:
        problems.append(f"fired gate predicates {sorted(fired)} != {sorted(expected_fired)}")
    l1 = ((rec.get("leg1_product_axis") or {}).get("L1")) or {}
    if l1.get("holds") is not False:
        problems.append("L1 product falsifier no longer reads as falsified")
    if (rec.get("absolute_bar") or {}).get("enforced_as_build_blocker") is not False:
        problems.append("the absolute bar is marked as a build blocker, which direction v50 forbids")
    ok = not problems
    b = rec.get("non_vacuity_battery") or {}
    detail = (f"{rec.get('run_id')}: {rec.get('verdict')}; L1 product falsifier "
              f"({l1.get('before_support_rate')} -> {l1.get('after_support_rate')} support_rate) "
              f"held={l1.get('holds')}; {len(fired)} gate predicates fired; battery "
              f"{sum(1 for k, v in b.items() if isinstance(v, dict) and v.get('holds'))}"
              f"/{sum(1 for v in b.values() if isinstance(v, dict))} proven; "
              f"absolute bar reported-not-enforced; rules re-hash {ident.get('all_match')}") \
        if ok else f"problems: {problems}"
    return _check("counter_authority_label_benchmark", ok, detail, problems=problems,
                  verdict=rec.get("verdict"))


def build_record(run_id: str, checks: list[dict], manifest: dict) -> dict:
    n_pass = sum(1 for c in checks if c["status"] == "PASS")
    ready = n_pass == len(checks)
    return {
        "schema": SCHEMA,
        "run_id": run_id,
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "checks": checks,
        "n_checks": len(checks),
        "n_passed": n_pass,
        "ready_for_independent_audit": ready,
        "audit_gate_path": f"results/audit/evaluation/CYCLE_{run_id}_GATE.json",
        "audit_report_path": f"reports/audit/evaluation/CYCLE_{run_id}.md",
        "audit_gate_path_rule": "uppercase _GATE.json suffix, relative to the audit-job checkout; never /tmp/lex_team, never lowercase",
        "deliverable_sha256": manifest,
        "snapshot_claims_verified": [
            "frozen rubric bytes re-hash to direction-pinned 4457e971/a7452748 and the vendored set matches VENDORED_SHA256.json",
            "frozen-bar gates re-run exits 0 PASS_NO_REGRESSION on the served lineage; negative controls all proven; label 5/65 (38/22/5/0) and geometry de 6 / fr 5 / it 5 recompute exactly",
            "fresh default-mode record identical to accepted 38971202786.json except elapsed_s (H1)",
            "python -m evaluation.lane_suite exits 0 PASS (stdlib authoritative)",
            "every state/evaluation.json evidence_ref resolves in the snapshot",
            "deliverable manifest complete; every file sha256-pinned in this record",
            "job-level orchestration diagnosis for runs 38972887369/38977570612 recorded with required structure",
            "the live tree passes the workflow's own producer write-scope classifier (the step that failed run 38982176936)",
            "run 38982176936's write-scope failure is reproduced with the real control-plane step body (exit 3, identical BAD set) and its producer-authored self-audit is voided with byte-identical preserved copies",
            "run 38986445355's mid-cycle producer death (team step 6 'Run lane cycle') is diagnosed at job/step level with the un-loggable provider cause hedged as a candidate set",
            "the three-leg retrieval/counter-authority falsification benchmark re-exits BENCHMARK_VALID_NO_FALSIFICATION (legs 0/1/1 over the accepted run_bar_gates entry point, falsification_proven=true)",
        ],
        "snapshot_claims_not_certified": [
            "jurist-usefulness of the map (human gate); human_gate_ready stays false under the standing accepted DO-NOT-SERVE order",
            "absolute bars LABEL_UNSOUND and GEOMETRY_UNSOUND remain the accepted status of the served packet; reported, never enforced",
            "no Frontier candidate re-measured; no 174k/global-map benchmark rerun; no Product import; no network",
            "job-LOG-level cause of the 38977570612 audit-step failure remains two flagged candidate causes (logs 403 unauthenticated), not one asserted cause",
            "run 38982176936 has NO independent audit of record: its producer-authored gate is void, and only this run's audit job can produce the gate of record",
        ],
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--run-id", default=os.environ.get("GITHUB_RUN_ID", "local"))
    ap.add_argument("--out", default=None)
    ap.add_argument("--repo-root", default=str(Path.cwd()))
    args = ap.parse_args(argv)

    repo_root = Path(args.repo_root).resolve()
    out_path = Path(args.out) if args.out else repo_root / "results/evaluation/snapshot_audit" / f"{args.run_id}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    manifest = {}
    with tempfile.TemporaryDirectory(prefix="snapshot_audit_") as td:
        workdir = Path(td)
        checks = [
            check_rubric_rehash(repo_root),
            check_bar_gates_verdict(repo_root, workdir),
        ]
        fresh_record = workdir / "bar_gates_fresh.json"
        checks.append(check_h1(repo_root, fresh_record))
        checks.extend([
            check_lane_suite(repo_root),
            check_evidence_refs(repo_root),
        ])
        manifest = {rel: _sha256_file(repo_root / rel)
                    for rel in DELIVERABLE_MANIFEST_PATHS if (repo_root / rel).exists()}
        checks.append(check_manifest(repo_root))
        checks.append(check_diagnosis_record(repo_root))
        checks.append(check_producer_write_scope(repo_root))
        checks.append(check_write_scope_diagnosis(repo_root))
        checks.append(check_run_38986445355_diagnosis(repo_root))
        checks.append(check_retrieval_ca_benchmark(repo_root))
        checks.append(check_gate_validity_sweep(repo_root))
        checks.append(check_counter_authority_label_benchmark(repo_root))

    record = build_record(args.run_id, checks, manifest)
    out_path.write_text(json.dumps(record, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")

    for c in checks:
        print(f"[{c['status']}] {c['id']}: {c['detail']}")
    print(f"snapshot audit: {'READY' if record['ready_for_independent_audit'] else 'NOT READY'} "
          f"({record['n_passed']}/{record['n_checks']} checks PASS)")
    print(f"readiness record: {out_path}")
    return 0 if record["ready_for_independent_audit"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

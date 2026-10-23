"""Operational-resume verification instrument for run 39936790420 (stdlib only, no network).

Resumes the producer snapshot of run 39929883261 (commit 5cc6a326), which was
persisted after the factory supervisor cancelled the team job at the 3300s
stale-job threshold.  The lane-cycle step, the active-MVP-state validation,
the write-scope enforcement, and the audit/integrate chain never ran, and
``lab/evaluation`` was advanced to the unaudited snapshot.

Frozen gates (hypothesis V1, committed before execution):

  R1  the snapshot is preserved, its parent is the true accepted base 3eeced9a,
      its diff is exactly the six declared paths, and its five claim-bearing
      artifacts re-hash to their frozen digests;
  R2  the committed orchestration diagnosis and REST capture are structured and
      carry the measured cancel/step facts, the lab-promotion anomaly and the
      product-advance facts;
  R3  the four frozen bars, accepted fixtures, accepted gate, current accepted
      product head, planner pin and V3 bundle hashes all re-hash exactly;
  R4  the snapshot wrapper/engine records are byte-identical to the accepted
      39927760701 records modulo identity fields (583/558 leaves, 0
      non-identity diffs) and the claim fields are intact;
  R5  the five-file test shim reproduces 88 passed / 2 failed / 6 unsupported
      with the same per-file/per-case results, and the same two files/cases are
      red at a detached worktree of 3eeced9a (inherited, not caused here);
  R6  the accepted product advanced to d22f9b63 at 09:46:52Z before the
      snapshot commit; the V3 packet bytes are unchanged; a frozen
      re-measurement on the new accepted mount produces a valid PRODUCT_FALSIFIED
      record with the same four failed gates and no input drift;
  R7  the lane state and every evidence ref reconcile, the product-advance
      disclosure is present, and all admission/human flags stay false.

Controls C1-C5 plant drift in-memory and require each gate to detect it.  A
control that fails to detect forces RESUME_DIVERGENCE; gates are never weakened.

Usage:
    python -m evaluation.operational_resume_39936790420 [--run-id 39936790420]
        [--out results/evaluation/operational_resume/39936790420.json]

Exit codes (frozen in the hypothesis): 0 RESUME_VERIFIED_AND_AUDIT_READY,
1 RESUME_DIVERGENCE, 2 ENVIRONMENT_OR_VACUOUS.
"""

from __future__ import annotations

import argparse
import copy
import datetime
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

RUN_ID = "39936790420"
RESUMED_RUN_ID = "39929883261"
DIRECTION_VERSION = 63
ACCEPTED_BASE = "3eeced9a25d486356870755e48422f8473a5f90c"
SNAPSHOT_COMMIT = "5cc6a326cdc77b821f73f7819acb6bd3b3303a1e"
ACCEPTED_RUN_ID = "39927760701"
PRODUCT_HEAD_AT_MEASUREMENT = "ae854b6a9ff4df4429d36725e364e721cb73096b"
PRODUCT_HEAD_CURRENT = "d22f9b633c9bce70258915579f5da5195f6b2f53"
PLANNER_SHA = "9764a37e8bc7c8c31a329ba15db89657e8ee47dde8ada924fa55d5e755fd06a9"
PACKET = "39319405429"

HYPOTHESIS = "evaluation/OPERATIONAL_RESUME_39936790420_HYPOTHESIS_V2.json"
FREEZE = "evaluation/OPERATIONAL_RESUME_39936790420_FREEZE_V2.json"
DIAGNOSIS = "evaluation/snapshot_audit/orchestration_diagnosis_39936790420.json"
REST_CAPTURE = "results/evaluation/orchestration/39936790420_rest_job_capture.json"
INHERITED_RED = ("results/evaluation/orchestration/"
                 "39936790420_inherited_red_3eeced9a.json")

SNAPSHOT_PINS = {
    "results/evaluation/minimal_retrieval_ca_benchmark/39929883261.json":
        "202ffeb5d653a34ee703358fc3b68d9914f9b37a5559b2bac18e06a63f31d416",
    "results/evaluation/minimal_retrieval_ca_benchmark/"
    "39929883261_engine_mapping_free_recall_falsifier.json":
        "373e77974c191477eff267d4fefb5f076e57aada69291a40ad340653258f9ef6",
    "results/evaluation/minimal_retrieval_ca_benchmark/"
    "39929883261_LINEAGE_DISCLOSURE.json":
        "04b72edecfbd98f13a0f515f14b30d5f473490050df1216afe7530d5aa4a38b7",
    "reports/evaluation/RETRIEVAL_CA_BENCHMARK_39929883261.md":
        "6572fd8300b8589b48c3396aa99bc92102a8a516784d1340f76cfc58aa17d931",
    "results/evaluation/orchestration/"
    "39929883261_multiling_prov_benchmark_pytest_shim.json":
        "643f1e0891cd8876361de057879b970a28ebeefe2566b401ce4e00b9ac491e77",
}
EXPECTED_SNAPSHOT_DIFF = {
    "results/evaluation/minimal_retrieval_ca_benchmark/39929883261.json",
    "results/evaluation/minimal_retrieval_ca_benchmark/"
    "39929883261_engine_mapping_free_recall_falsifier.json",
    "results/evaluation/minimal_retrieval_ca_benchmark/"
    "39929883261_LINEAGE_DISCLOSURE.json",
    "reports/evaluation/RETRIEVAL_CA_BENCHMARK_39929883261.md",
    "results/evaluation/orchestration/"
    "39929883261_multiling_prov_benchmark_pytest_shim.json",
    "state/evaluation.json",
}
FROZEN_PINS = {
    "evaluation/frozen_bars/RULES_LABEL.json":
        "4457e971df3dc5d10af2a727aa675afc15a15564c18eed4cede0af5eb41b4608",
    "evaluation/frozen_bars/RULES_GEOMETRY.json":
        "a7452748d40c511a14a1c7848ece5fe7f8f8901cc30f45a66918c89eb593a633",
    "evaluation/frozen_bars/VERDICT_CONTRACT.json":
        "b9cdb89438a8d16ee165fe2a5d73060524154d8e7ba8e0cab867e8ca17ff414c",
    "evaluation/retrieval_gate/frozen_retrieval_benchmark.json":
        "187b0e54b03b326c62d45d8ba48fc78dc88501086761cd91a84c304a7478ba72",
}
FIXTURE_PINS = {
    "evaluation/vendored_frontier_serve_audit/VERDICT_39371834165.json":
        "403aeb0c005b1fa9c4866277a8c302f87418cf89d78b93bb75e6eb99215954d4",
    "results/evaluation/counter_probe_repair_verification/39687372110.json":
        "53b3fc9c71c81bb238a000eadde5bf3bacd7d37349fa1a43017d5527e651e340",
    "results/evaluation/shipped_planner_remedy_verification/39813664201.json":
        "1f8a6675e61930cf35bae7a9610f4672354433b6234fc96e18b98da08691372f",
    "results/evaluation/offline_emission_path/39856081942.json":
        "98aa4a4421bbe9b81b7591e0b8434845f68f4bad604262b4377957141e3264b0",
    "results/audit/evaluation/CYCLE_39927760701_GATE.json":
        "0ed04c6a81103921045b95b26fd7088eaef0f14c0568f36ebdfc71c56ec18e29",
    "results/evaluation/minimal_retrieval_ca_benchmark/39927760701.json":
        "60d35b95bfe70c98784b136833495adf4b8036fea283e1f310419cfc6ab047b1",
    "results/evaluation/mapping_free_recall_falsifier/"
    "39927760701_engine_mapping_free_recall_falsifier.json":
        "06d73f9f0a1dec42de18fcdd687f4c170a75b5218ce16193de173bf261715f0c",
}
V3_BUNDLE_PINS = {
    "de-kapitalverletzung":
        "9b856e2b1b3e4675f8d4d135cd5d1ad23f0baa63fcb2e4cc7bc45182c012881b",
    "fr-bail-entretien":
        "054bec47ae8e5a0f98593902c2c7bd09f7f52761be1c85225328853f34d3213b",
    "it-responsabilita-medica":
        "345e20d1f352fd4e907cac144c8dbbae296f3a9132605d4354f12e7a783e6e3b",
}
FAILED_GATES = {
    "mf::concept_coverage::39319405429::de-kapitalverletzung",
    "mf::counter_authority_surface::39319405429::de-kapitalverletzung",
    "mf::counter_authority_surface::39319405429::fr-bail-entretien",
    "mf::counter_authority_surface::39319405429::it-responsabilita-medica",
}
IDENTITY_LEAVES = {"run_id", "generated_at_utc", "engine_record_path"}
SHIM_FILES = [
    "tests/evaluation/test_minimal_retrieval_ca_benchmark.py",
    "tests/evaluation/test_mapping_free_recall_falsifier.py",
    "tests/evaluation/test_stand_ready_multilingual_probe.py",
    "tests/evaluation/test_mount_provenance_gate.py",
    "tests/evaluation/test_repair_39338699604_provenance.py",
]
SHIM_EXPECTED = {
    "tests/evaluation/test_minimal_retrieval_ca_benchmark.py": (21, 0, 0),
    "tests/evaluation/test_mapping_free_recall_falsifier.py": (22, 0, 2),
    "tests/evaluation/test_stand_ready_multilingual_probe.py": (16, 0, 0),
    "tests/evaluation/test_mount_provenance_gate.py": (8, 1, 4),
    "tests/evaluation/test_repair_39338699604_provenance.py": (21, 7, 0),
}
SHIM_TOTAL = (88, 2, 6)
INHERITED_RED_FILES = [
    "tests/evaluation/test_mount_provenance_gate.py",
    "tests/evaluation/test_repair_39338699604_provenance.py",
]
PRODUCT_MOUNT_CANDIDATES = ["/tmp/lex_accepted/product",
                            os.environ.get("LEX_PRODUCT_MOUNT", "")]


# --------------------------------------------------------------------- helpers
def sha256_file(path: str | os.PathLike) -> str | None:
    if not os.path.isfile(path):
        return None
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load(path: str | os.PathLike):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def git_out(args, cwd=None, check=True):
    return subprocess.run(["git"] + args, cwd=cwd, capture_output=True,
                          text=True, check=check).stdout.strip()


def resolve_mount() -> str | None:
    for c in PRODUCT_MOUNT_CANDIDATES:
        if c and os.path.isdir(os.path.join(c, "product")):
            return c
    return None


def _check_pins(repo_root: str, pins: dict) -> dict:
    got, drifted, missing = {}, [], []
    for rel, exp in pins.items():
        g = sha256_file(os.path.join(repo_root, rel))
        got[rel] = g
        if g is None:
            missing.append(rel)
        elif g != exp:
            drifted.append({"path": rel, "expected": exp, "got": g})
    return {"rehashed": got, "drifted": drifted, "missing": missing,
            "n_pins": len(pins), "n_ok": len(pins) - len(drifted) - len(missing)}


def _flatten(obj, prefix=""):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from _flatten(v, f"{prefix}.{k}" if prefix else str(k))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from _flatten(v, f"{prefix}[{i}]")
    else:
        yield prefix, obj


def _leaf_is_identity(path: str) -> bool:
    return any(part in IDENTITY_LEAVES for part in path.replace("[", ".").split("."))


# --------------------------------------------------------------------------- R1
def r1_snapshot_preserved(repo_root: str, snapshot_pins_override: dict | None = None) -> dict:
    pins = snapshot_pins_override if snapshot_pins_override is not None else SNAPSHOT_PINS
    exists = git_out(["cat-file", "-t", SNAPSHOT_COMMIT], cwd=repo_root, check=False) == "commit"
    parent = git_out(["rev-parse", SNAPSHOT_COMMIT + "^"], cwd=repo_root, check=False)
    names = [n for n in git_out(["diff", "--name-only", ACCEPTED_BASE, SNAPSHOT_COMMIT],
                                cwd=repo_root, check=False).splitlines() if n]
    statuses = [s for s in git_out(["diff", "--name-status", ACCEPTED_BASE, SNAPSHOT_COMMIT],
                                   cwd=repo_root, check=False).splitlines() if s]
    pin = _check_pins(repo_root, pins)
    unexpected = sorted(set(names) - EXPECTED_SNAPSHOT_DIFF)
    missing = sorted(EXPECTED_SNAPSHOT_DIFF - set(names))
    non_add = [s for s in statuses if not s.startswith("A\t")
               and s != "M\tstate/evaluation.json"]
    ok = (exists and parent == ACCEPTED_BASE and not unexpected and not missing
          and not non_add and not pin["drifted"] and not pin["missing"])
    return {"name": "R1_producer_snapshot_preserved_and_in_scope", "pass": ok,
            "details": {"snapshot": SNAPSHOT_COMMIT, "parent": parent,
                        "true_accepted_base": ACCEPTED_BASE,
                        "changed_paths": names, "name_status": statuses,
                        "unexpected_paths": unexpected, "missing_paths": missing,
                        "non_added_non_state_paths": non_add, "artifact_pins": pin,
                        "network_calls": []}}


# --------------------------------------------------------------------------- R2
def _diag_violations(diag: dict, capture: dict) -> list[str]:
    v = []
    run = diag.get("prior_run_facts_measured_via_rest_api") or {}
    if run.get("run_id") != RESUMED_RUN_ID:
        v.append("prior run id missing")
    if run.get("conclusion") != "cancelled":
        v.append("prior run conclusion is not cancelled")
    tj = run.get("team_job") or {}
    if tj.get("conclusion") != "cancelled":
        v.append("prior team job is not cancelled")
    if tj.get("duration_seconds") != 3402:
        v.append("prior team job duration is not 3402s")
    steps = {s.get("number"): s for s in diag.get("team_job_steps_measured_via_rest_api", [])}
    for num, expected in ((6, "cancelled"), (7, "skipped"), (9, "skipped"), (10, "success")):
        if (steps.get(num) or {}).get("conclusion") != expected:
            v.append(f"step {num} conclusion is not {expected}")
    if (run.get("audit_job") or {}).get("conclusion") != "cancelled":
        v.append("audit job is not cancelled")
    if (run.get("integrate_job") or {}).get("conclusion") != "cancelled":
        v.append("integrate job is not cancelled")
    if (run.get("resilience_job") or {}).get("conclusion") != "success":
        v.append("resilience job is not success")
    if run.get("resilience_dispatched_run_id") != RUN_ID:
        v.append("resilience did not dispatch this run")
    tree = diag.get("persisted_tree_facts_measured_via_git") or {}
    if tree.get("snapshot_commit") != SNAPSHOT_COMMIT:
        v.append("snapshot commit fact missing")
    if tree.get("remote_lab_evaluation_head") != SNAPSHOT_COMMIT:
        v.append("lab/evaluation anomaly fact missing")
    if tree.get("remote_audit_branch_for_prior_run") is not None:
        v.append("diagnosis claims an audit branch exists")
    padv = diag.get("product_advance_during_producer_run") or {}
    if padv.get("accepted_product_commit") != PRODUCT_HEAD_CURRENT:
        v.append("product advance commit fact missing")
    if padv.get("accepted_at") != "2026-10-23T09:46:52Z":
        v.append("product advance time fact missing")
    if padv.get("packet_bytes_unchanged") is not True:
        v.append("packet-unchanged fact missing")
    jobs = {j.get("id"): j for j in capture.get("jobs_39929883261", [])}
    if not any(j.get("name") == "team" and j.get("conclusion") == "cancelled"
               for j in jobs.values()):
        v.append("REST capture has no cancelled team job")
    if not any(j.get("name") == "resilience" and j.get("conclusion") == "success"
               for j in jobs.values()):
        v.append("REST capture has no successful resilience job")
    return v


def r2_diagnosis_structured(repo_root: str, diag_override: dict | None = None,
                            capture_override: dict | None = None) -> dict:
    try:
        diag = diag_override or load(os.path.join(repo_root, DIAGNOSIS))
        capture = capture_override or load(os.path.join(repo_root, REST_CAPTURE))
    except Exception as e:
        return {"name": "R2_orchestration_diagnosis_structured", "pass": False,
                "details": {"error": str(e)}}
    v = _diag_violations(diag, capture)
    audit_ref = git_out(["rev-parse", "--verify", "--quiet",
                         "origin/cycle/core/evaluation/39929883261/audit"],
                        cwd=repo_root, check=False)
    if audit_ref:
        v.append("origin audit branch unexpectedly exists")
    return {"name": "R2_orchestration_diagnosis_structured", "pass": not v,
            "details": {"violations": v,
                        "diagnosis_sha256": sha256_file(os.path.join(repo_root, DIAGNOSIS)),
                        "rest_capture_sha256": sha256_file(os.path.join(repo_root, REST_CAPTURE)),
                        "audit_branch_present": bool(audit_ref)}}


# --------------------------------------------------------------------------- R3
def r3_pins_hold(repo_root: str, frozen_override: dict | None = None) -> dict:
    frozen = _check_pins(repo_root, frozen_override if frozen_override is not None else FROZEN_PINS)
    fixtures = _check_pins(repo_root, FIXTURE_PINS)
    mount = resolve_mount()
    product = {"mount": mount, "head": None, "planner_sha256": None,
               "head_matches_current": False, "planner_matches": False,
               "v3_bundles": {}, "v3_bundles_match": False}
    if mount:
        product["head"] = git_out(["rev-parse", "HEAD"], cwd=mount, check=False)
        product["head_matches_current"] = product["head"] == PRODUCT_HEAD_CURRENT
        planner_path = os.path.join(mount, "product/query/adversarial_retrieval.py")
        product["planner_sha256"] = sha256_file(planner_path)
        product["planner_matches"] = product["planner_sha256"] == PLANNER_SHA
        base = os.path.join(mount, "results/product/gate_packet", PACKET, "questions")
        for q, exp in V3_BUNDLE_PINS.items():
            got = sha256_file(os.path.join(base, f"{q}.bundle.json"))
            product["v3_bundles"][q] = {"expected": exp, "got": got, "match": got == exp}
        product["v3_bundles_match"] = all(x["match"] for x in product["v3_bundles"].values())
    ok = (not frozen["drifted"] and not frozen["missing"]
          and not fixtures["drifted"] and not fixtures["missing"]
          and product["head_matches_current"] and product["planner_matches"]
          and product["v3_bundles_match"])
    return {"name": "R3_frozen_and_accepted_pins_hold", "pass": ok,
            "details": {"frozen_bars": frozen, "accepted_fixtures": fixtures,
                        "product_mount": product}}


# --------------------------------------------------------------------------- R4
def lineage_violations(snapshot_wrapper: dict, accepted_wrapper: dict,
                       snapshot_engine: dict, accepted_engine: dict) -> list[str]:
    v = []
    for label, a, b, n_expected in (
            ("wrapper", snapshot_wrapper, accepted_wrapper, 583),
            ("engine", snapshot_engine, accepted_engine, 558)):
        fa, fb = dict(_flatten(a)), dict(_flatten(b))
        if len(fa) != n_expected or len(fb) != n_expected:
            v.append(f"{label}: leaf counts {len(fa)}/{len(fb)} != {n_expected}")
        for key in sorted(set(fa) | set(fb)):
            if fa.get(key) == fb.get(key):
                continue
            if _leaf_is_identity(key):
                continue
            v.append(f"{label}: non-identity diff at {key}: {fa.get(key)!r} != {fb.get(key)!r}")
    return v


def r4_lineage(repo_root: str, wrapper_override: tuple | None = None) -> dict:
    try:
        sw = load(os.path.join(repo_root,
                               "results/evaluation/minimal_retrieval_ca_benchmark/39929883261.json"))
        se = load(os.path.join(
            repo_root,
            "results/evaluation/minimal_retrieval_ca_benchmark/"
            "39929883261_engine_mapping_free_recall_falsifier.json"))
        aw = load(os.path.join(repo_root,
                               "results/evaluation/minimal_retrieval_ca_benchmark/39927760701.json"))
        ae = load(os.path.join(
            repo_root,
            "results/evaluation/mapping_free_recall_falsifier/"
            "39927760701_engine_mapping_free_recall_falsifier.json"))
    except Exception as e:
        return {"name": "R4_lineage_byte_identity_and_claim_integrity", "pass": False,
                "details": {"error": str(e)}}
    if wrapper_override is not None:
        sw, aw = wrapper_override
    v = lineage_violations(sw, aw, se, ae)
    failed = {g.get("gate") for g in (sw.get("failed_gates") or [])}
    if failed != FAILED_GATES:
        v.append(f"failed gate set differs: {sorted(failed)}")
    for key, expected in (("verdict", "PRODUCT_FALSIFIED"), ("exit_code", 1),
                          ("n_questions_measured", 3), ("n_gates", 18),
                          ("n_passed", 11), ("n_failed", 4), ("n_reported", 3),
                          ("product_mount_head", PRODUCT_HEAD_AT_MEASUREMENT)):
        if sw.get(key) != expected:
            v.append(f"wrapper {key} {sw.get(key)!r} != {expected!r}")
    if sw.get("packets_measured") != [PACKET]:
        v.append(f"wrapper packets_measured {sw.get('packets_measured')!r} != [{PACKET!r}]")
    if sw.get("input_drift") != []:
        v.append("wrapper input_drift is not empty")
    vac = sw.get("non_vacuity") or {}
    if vac.get("all_hold") is not True or len(vac.get("battery") or []) != 4:
        v.append("wrapper non-vacuity is not 4/4")
    if se.get("verdict") != "PRODUCT_FALSIFIED":
        v.append("engine verdict is not PRODUCT_FALSIFIED")
    return {"name": "R4_lineage_byte_identity_and_claim_integrity", "pass": not v,
            "details": {"violations": v,
                        "wrapper_leaf_counts": (len(dict(_flatten(sw))),
                                                len(dict(_flatten(aw)))),
                        "engine_leaf_counts": (len(dict(_flatten(se))),
                                               len(dict(_flatten(ae)))),
                        "failed_gate_set": sorted(failed),
                        "input_drift": sw.get("input_drift"),
                        "non_vacuity_all_hold": vac.get("all_hold"),
                        "per_gate_direction_versions": {
                            "wrapper": sw.get("direction_version"),
                            "engine": se.get("direction_version"),
                            "lane": DIRECTION_VERSION,
                            "disclosure": ("the wrapper/engine direction_version fields are "
                                           "historical 61/57 misstatements pinned by the accepted "
                                           "fixture; they are disclosed, never rewritten")}}}


# --------------------------------------------------------------------------- R5
def _run_shim(repo_root: str, out_path: str, test_files: list[str]) -> dict:
    cmd = [sys.executable, "-m", "evaluation.no_pytest_runner",
           "--run-id", RUN_ID, "--repo-root", repo_root, "--out", out_path]
    for tf in test_files:
        cmd += ["--test-file", tf]
    proc = subprocess.run(cmd, cwd=repo_root, capture_output=True, text=True, timeout=900)
    rec = None
    if os.path.isfile(out_path):
        try:
            rec = load(out_path)
        except Exception:
            rec = None
    return {"cmd": cmd, "returncode": proc.returncode, "stdout_tail": proc.stdout[-2000:],
            "stderr_tail": proc.stderr[-2000:], "record": rec, "record_path": out_path}


def _shim_shape(rec: dict) -> dict:
    return {
        "n_passed": rec.get("n_passed"), "n_failed": rec.get("n_failed"),
        "n_unsupported": rec.get("n_unsupported"), "verdict": rec.get("verdict"),
        "files": {r.get("test_file"): {
            "status": r.get("status"), "n_passed": r.get("n_passed"),
            "n_failed": r.get("n_failed"), "n_unsupported": r.get("n_unsupported"),
            "failed_cases": sorted(c.get("test") for c in (r.get("cases") or [])
                                   if c.get("status") == "FAIL"),
        } for r in (rec.get("results") or [])},
    }


def r5_shim_and_inherited_red(repo_root: str) -> dict:
    shim_out = os.path.join(repo_root, "results/evaluation/orchestration/"
                            f"{RUN_ID}_multiling_prov_benchmark_pytest_shim.json")
    shim = _run_shim(repo_root, shim_out, SHIM_FILES)
    rec = shim.get("record") or {}
    shape = _shim_shape(rec) if rec else {}
    v = []
    if (rec.get("n_passed"), rec.get("n_failed"), rec.get("n_unsupported")) != SHIM_TOTAL:
        v.append(f"shim total {rec.get('n_passed')}/{rec.get('n_failed')}/"
                 f"{rec.get('n_unsupported')} != {SHIM_TOTAL}")
    for tf, expected in SHIM_EXPECTED.items():
        got = (shape.get("files") or {}).get(tf) or {}
        if (got.get("n_passed"), got.get("n_failed"), got.get("n_unsupported")) != expected:
            v.append(f"{tf}: {got.get('n_passed')}/{got.get('n_failed')}/"
                     f"{got.get('n_unsupported')} != {expected}")
    prior = load(os.path.join(
        repo_root, "results/evaluation/orchestration/"
        "39929883261_multiling_prov_benchmark_pytest_shim.json"))
    if _shim_shape(prior) != shape:
        v.append("fresh shim shape differs from the snapshot shim record")

    # inherited red at the true accepted base
    tmp = tempfile.mkdtemp(prefix="lex_resume_tip_")
    inherited = {"worktree": tmp, "record_path": INHERITED_RED,
                 "record": None, "error": None}
    try:
        add = subprocess.run(["git", "worktree", "add", "--detach", tmp, ACCEPTED_BASE],
                             cwd=repo_root, capture_output=True, text=True)
        if add.returncode != 0:
            inherited["error"] = f"worktree add failed: {add.stderr[-800:]}"
            v.append(inherited["error"])
        else:
            tip_out = os.path.join(repo_root, INHERITED_RED)
            tip = _run_shim(tmp, tip_out, INHERITED_RED_FILES)
            inherited["record"] = tip.get("record")
            inherited["returncode"] = tip.get("returncode")
            tip_shape = _shim_shape(tip.get("record") or {})
            for tf in INHERITED_RED_FILES:
                snap = (shape.get("files") or {}).get(tf) or {}
                tipf = (tip_shape.get("files") or {}).get(tf) or {}
                if snap.get("failed_cases") != tipf.get("failed_cases"):
                    v.append(f"{tf}: inherited failing cases differ: "
                             f"snapshot={snap.get('failed_cases')} tip={tipf.get('failed_cases')}")
                if (snap.get("n_passed"), snap.get("n_failed")) != \
                        (tipf.get("n_passed"), tipf.get("n_failed")):
                    v.append(f"{tf}: snapshot {snap.get('n_passed')}/{snap.get('n_failed')} "
                             f"!= tip {tipf.get('n_passed')}/{tipf.get('n_failed')}")
            with open(os.path.join(repo_root, INHERITED_RED), "w", encoding="utf-8") as f:
                json.dump({"schema": "lex-evaluation-inherited-red-verification/1",
                           "run_id": RUN_ID, "base": ACCEPTED_BASE,
                           "generated_at_utc": _now(),
                           "snapshot_shim_record": os.path.relpath(shim_out, repo_root),
                           "tip_shim_shape": tip_shape,
                           "snapshot_failed_cases": {
                               tf: ((shape.get("files") or {}).get(tf) or {}).get("failed_cases")
                               for tf in INHERITED_RED_FILES},
                           "tip_failed_cases": {
                               tf: ((tip_shape.get("files") or {}).get(tf) or {}).get("failed_cases")
                               for tf in INHERITED_RED_FILES},
                           "verdict": "INHERITED_RED_CONFIRMED" if not v else "DIVERGENCE",
                           "claim_ceiling": ("Proves only that these failing cases are red at the "
                                             "true accepted base 3eeced9a before any snapshot "
                                             "change; not a product finding.")}, f, indent=1)
                f.write("\n")
    finally:
        subprocess.run(["git", "worktree", "remove", "--force", tmp],
                       cwd=repo_root, capture_output=True, text=True)
        subprocess.run(["git", "worktree", "prune"], cwd=repo_root,
                       capture_output=True, text=True)
        shutil.rmtree(tmp, ignore_errors=True)
    return {"name": "R5_shim_reproduction_and_inherited_red_isolated", "pass": not v,
            "details": {"violations": v, "shim_shape": shape,
                        "shim_record": os.path.relpath(shim_out, repo_root),
                        "shim_record_sha256": sha256_file(shim_out),
                        "inherited_red": inherited,
                        "inherited_red_record_sha256": sha256_file(
                            os.path.join(repo_root, INHERITED_RED))}}


# --------------------------------------------------------------------------- R6
def r6_reopen_measurement(repo_root: str) -> dict:
    mount = resolve_mount()
    if not mount:
        return {"name": "R6_product_advance_resolved_by_frozen_reopen_measurement",
                "pass": False, "details": {"error": "accepted product mount absent"}}
    head = git_out(["rev-parse", "HEAD"], cwd=mount, check=False)
    packet_diff = git_out(["diff", "--stat", PRODUCT_HEAD_AT_MEASUREMENT,
                           PRODUCT_HEAD_CURRENT, "--",
                           f"results/product/gate_packet/{PACKET}/"],
                          cwd=mount, check=False)
    bundle_ok = {}
    base = os.path.join(mount, "results/product/gate_packet", PACKET, "questions")
    for q, exp in V3_BUNDLE_PINS.items():
        got = sha256_file(os.path.join(base, f"{q}.bundle.json"))
        bundle_ok[q] = got == exp
    planner = sha256_file(os.path.join(mount,
                                       "product/query/adversarial_retrieval.py"))

    cmd = [sys.executable, "-m", "evaluation.minimal_retrieval_ca_benchmark",
           "--run-id", RUN_ID, "--product-mount", mount, "--packets", PACKET]
    proc = subprocess.run(cmd, cwd=repo_root, capture_output=True, text=True, timeout=900)
    rec_path = os.path.join(repo_root,
                            "results/evaluation/minimal_retrieval_ca_benchmark/"
                            f"{RUN_ID}.json")
    eng_path = os.path.join(repo_root,
                            "results/evaluation/minimal_retrieval_ca_benchmark/"
                            f"{RUN_ID}_engine_mapping_free_recall_falsifier.json")
    rec = load(rec_path) if os.path.isfile(rec_path) else {}
    eng = load(eng_path) if os.path.isfile(eng_path) else {}
    v = []
    if head != PRODUCT_HEAD_CURRENT:
        v.append(f"mount head {head} != frozen current accepted head {PRODUCT_HEAD_CURRENT}")
    if packet_diff:
        v.append(f"V3 packet bytes changed across the product advance: {packet_diff}")
    if not all(bundle_ok.values()):
        v.append(f"V3 bundle hash mismatch: {bundle_ok}")
    if planner != PLANNER_SHA:
        v.append(f"planner pin changed: {planner}")
    if proc.returncode != 1:
        v.append(f"re-open wrapper exit {proc.returncode} != 1 (PRODUCT_FALSIFIED)")
    if rec.get("verdict") != "PRODUCT_FALSIFIED":
        v.append(f"re-open verdict {rec.get('verdict')!r} != PRODUCT_FALSIFIED")
    if rec.get("product_mount_head") != PRODUCT_HEAD_CURRENT:
        v.append(f"re-open product_mount_head {rec.get('product_mount_head')!r} "
                 f"!= {PRODUCT_HEAD_CURRENT}")
    if rec.get("input_drift") != []:
        v.append(f"re-open input_drift {rec.get('input_drift')!r} is not empty")
    failed = {g.get("gate") for g in (rec.get("failed_gates") or [])}
    if failed != FAILED_GATES:
        v.append(f"re-open failed gate set differs: {sorted(failed)}")
    if (rec.get("non_vacuity") or {}).get("all_hold") is not True:
        v.append("re-open non-vacuity does not hold")
    if rec.get("run_valid") is not True:
        v.append("re-open run_valid is not true")
    return {"name": "R6_product_advance_resolved_by_frozen_reopen_measurement",
            "pass": not v,
            "details": {"violations": v, "mount": mount, "mount_head": head,
                        "packet_diff": packet_diff, "bundle_hashes_match": bundle_ok,
                        "planner_sha256": planner, "wrapper_exit": proc.returncode,
                        "wrapper_stdout_tail": proc.stdout[-1600:],
                        "wrapper_stderr_tail": proc.stderr[-1600:],
                        "record": os.path.relpath(rec_path, repo_root),
                        "record_sha256": sha256_file(rec_path),
                        "engine_record_sha256": sha256_file(eng_path),
                        "verdict": rec.get("verdict"),
                        "failed_gate_set": sorted(failed),
                        "input_drift": rec.get("input_drift"),
                        "non_vacuity_all_hold": (rec.get("non_vacuity") or {}).get("all_hold")}}


# --------------------------------------------------------------------------- R7
def _state_violations(state: dict, repo_root: str, github_run: str) -> list[str]:
    v = []
    if state.get("direction_version") != DIRECTION_VERSION:
        v.append(f"direction_version {state.get('direction_version')}")
    if str(state.get("github_run")) != github_run:
        v.append(f"github_run {state.get('github_run')} != {github_run}")
    if str(state.get("proposed_run_id")) != github_run:
        v.append(f"proposed_run_id {state.get('proposed_run_id')} != {github_run}")
    if state.get("accepted_run_id") != ACCEPTED_RUN_ID:
        v.append(f"accepted_run_id {state.get('accepted_run_id')} != {ACCEPTED_RUN_ID}")
    if state.get("cycle_status") != "COMPLETE":
        v.append("cycle_status is not COMPLETE")
    for flag in ("human_gate_ready", "machine_gate_ready", "packet_admitted",
                 "ready_for_owner_session"):
        if state.get(flag) is True:
            v.append(f"{flag} must not be true")
    padv = state.get("product_advance_after_snapshot_measurement") or {}
    if padv.get("accepted_product_commit") != PRODUCT_HEAD_CURRENT:
        v.append("state product-advance disclosure missing")
    rec = state.get("minimal_retrieval_ca_benchmark") or {}
    if rec.get("run_id") != RUN_ID:
        v.append(f"state minimal_retrieval_ca_benchmark.run_id {rec.get('run_id')} != {RUN_ID}")
    if rec.get("product_mount_head") != PRODUCT_HEAD_CURRENT:
        v.append("state minimal_retrieval_ca_benchmark mount head is stale")
    block = state.get(f"operational_resume_{github_run}") or {}
    if block.get("resumed_snapshot_run_id") != RESUMED_RUN_ID:
        v.append("state operational_resume block missing resumed snapshot id")
    refs = state.get("evidence_refs", [])
    if state.get("evidence_refs_n", -1) != len(refs):
        v.append("evidence_refs_n != len(evidence_refs)")
    exempt = {
        f"results/evaluation/operational_resume/{github_run}.json",
        f"reports/evaluation/OPERATIONAL_RESUME_{github_run}.md",
    }
    unresolved = [r for r in refs
                  if r not in exempt and not os.path.exists(os.path.join(repo_root, r))]
    if unresolved:
        v.append(f"unresolved evidence_refs: {unresolved}")
    return v


def r7_state_reconciled(repo_root: str, state_override: dict | None = None,
                        github_run_override: str | None = None) -> dict:
    try:
        state = state_override or load(os.path.join(repo_root, "state/evaluation.json"))
    except Exception as e:
        return {"name": "R7_state_and_evidence_refs_reconciled", "pass": False,
                "details": {"error": str(e)}}
    github_run = github_run_override or RUN_ID
    v = _state_violations(state, repo_root, str(github_run))
    return {"name": "R7_state_and_evidence_refs_reconciled", "pass": not v,
            "details": {"violations": v, "n_refs": len(state.get("evidence_refs", [])),
                        "github_run": state.get("github_run"),
                        "accepted_run_id": state.get("accepted_run_id"),
                        "continue_recommended": state.get("continue_recommended")}}


# ----------------------------------------------------------------------- controls
def c1_planted_pin_drift(repo_root: str) -> dict:
    pins = dict(FROZEN_PINS)
    pins["evaluation/frozen_bars/RULES_LABEL.json"] = "0" * 64
    r = r3_pins_hold(repo_root, frozen_override=pins)
    return {"name": "C1_planted_frozen_pin_drift_is_detected", "holds": not r["pass"]}


def c2_planted_lineage_drift(repo_root: str) -> dict:
    sw = load(os.path.join(repo_root,
                           "results/evaluation/minimal_retrieval_ca_benchmark/39929883261.json"))
    aw = load(os.path.join(repo_root,
                           "results/evaluation/minimal_retrieval_ca_benchmark/39927760701.json"))
    planted = copy.deepcopy(sw)
    planted.setdefault("gates", [])
    if planted["gates"]:
        planted["gates"][0]["pass"] = "PLANTED_DRIFT"
    else:
        planted["claim_ceiling"] = "PLANTED_DRIFT"
    r = r4_lineage(repo_root, wrapper_override=(planted, aw))
    return {"name": "C2_planted_lineage_drift_is_detected", "holds": not r["pass"]}


def c3_wrong_run_id(run_id: str) -> dict:
    return {"name": "C3_wrong_run_id_is_exit_2", "holds": run_id != RUN_ID,
            "checked_by_wrapper": True}


def c4_planted_diagnosis_violation(repo_root: str) -> dict:
    diag = load(os.path.join(repo_root, DIAGNOSIS))
    cap = load(os.path.join(repo_root, REST_CAPTURE))
    planted = copy.deepcopy(diag)
    for s in planted.get("team_job_steps_measured_via_rest_api", []):
        if s.get("number") == 6:
            s["conclusion"] = "success"
    v = _diag_violations(planted, cap)
    return {"name": "C4_planted_diagnosis_violation_is_detected", "holds": bool(v)}


def c5_planted_state_ref_break(repo_root: str) -> dict:
    state = load(os.path.join(repo_root, "state/evaluation.json"))
    state = copy.deepcopy(state)
    state.setdefault("evidence_refs", []).append(
        "results/evaluation/operational_resume/DOES_NOT_EXIST_39936790420.json")
    state["evidence_refs_n"] = len(state["evidence_refs"])
    r = r7_state_reconciled(repo_root, state_override=state,
                            github_run_override=str(state.get("github_run")))
    return {"name": "C5_planted_state_ref_break_is_detected",
            "holds": "DOES_NOT_EXIST_39936790420" in json.dumps(
                r["details"].get("violations", []))}


# --------------------------------------------------------------------------- main
def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def run(run_id: str = RUN_ID, out_path: str | None = None,
        repo_root: str | None = None) -> dict:
    if run_id != RUN_ID:
        return {"schema": "lex-evaluation-operational-resume-result/1",
                "run_id": run_id, "verdict": "ENVIRONMENT_OR_VACUOUS", "exit_code": 2,
                "reason": f"instrument is frozen to run id {RUN_ID}, got {run_id}"}
    repo_root = repo_root or os.getcwd()
    freeze_path = os.path.join(repo_root, FREEZE)
    hypo_path = os.path.join(repo_root, HYPOTHESIS)
    hypo_sha, freeze_sha = sha256_file(hypo_path), sha256_file(freeze_path)
    try:
        freeze = load(freeze_path)
        freeze_ok = (freeze.get("hypothesis_sha256") == hypo_sha
                     and freeze.get("diagnosis_sha256") == sha256_file(
                         os.path.join(repo_root, DIAGNOSIS))
                     and freeze.get("rest_capture_sha256") == sha256_file(
                         os.path.join(repo_root, REST_CAPTURE))
                     and freeze.get("instrument_sha256") == sha256_file(__file__))
    except Exception as e:
        freeze_ok, freeze = False, {"error": str(e)}
    if not freeze_ok:
        return {"schema": "lex-evaluation-operational-resume-result/1",
                "run_id": run_id, "verdict": "ENVIRONMENT_OR_VACUOUS", "exit_code": 2,
                "reason": "freeze pins drifted before execution",
                "freeze_sha256": freeze_sha, "hypothesis_sha256": hypo_sha}

    gates = [
        r1_snapshot_preserved(repo_root),
        r2_diagnosis_structured(repo_root),
        r3_pins_hold(repo_root),
        r4_lineage(repo_root),
        r5_shim_and_inherited_red(repo_root),
        r6_reopen_measurement(repo_root),
        r7_state_reconciled(repo_root),
    ]
    controls = [
        c1_planted_pin_drift(repo_root),
        c2_planted_lineage_drift(repo_root),
        c3_wrong_run_id("00000000000"),
        c4_planted_diagnosis_violation(repo_root),
        c5_planted_state_ref_break(repo_root),
    ]
    gates_pass = all(g["pass"] for g in gates)
    controls_pass = all(c["holds"] for c in controls)
    verdict = "RESUME_VERIFIED_AND_AUDIT_READY" if (gates_pass and controls_pass) \
        else "RESUME_DIVERGENCE"
    exit_code = 0 if (gates_pass and controls_pass) else 1
    result = {
        "schema": "lex-evaluation-operational-resume-result/1",
        "run_id": run_id, "resumed_snapshot_run_id": RESUMED_RUN_ID,
        "direction_version": DIRECTION_VERSION, "generated_at_utc": _now(),
        "verdict": verdict, "exit_code": exit_code,
        "frozen_before_execution": True,
        "hypothesis_sha256": hypo_sha, "freeze_record_sha256": freeze_sha,
        "true_accepted_base": ACCEPTED_BASE, "snapshot_commit": SNAPSHOT_COMMIT,
        "gates": gates, "controls": controls, "network_calls": [],
        "numeric_environment": {"python": sys.version.split()[0], "platform": sys.platform},
        "claim_ceiling": (
            "Establishes only that the producer snapshot is preserved and in scope, that its "
            "claim-bearing measurement and shim counts reproduce, that the two red files are "
            "inherited from the true accepted base, that every frozen pin holds, that the "
            "product advance d22f9b63 is disclosed and re-measured on the unchanged V3 packet "
            "bytes, and that state/evidence reconcile. It is not a new bar, not an admission, "
            "not a serve recommendation and not a claim that the map helps a jurist; both "
            "DO-NOT-SERVE orders stand and every admission/human flag stays false."),
    }
    out_path = out_path or os.path.join(
        repo_root, "results/evaluation/operational_resume", f"{run_id}.json")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=1, sort_keys=True)
        f.write("\n")
    result["result_file"] = os.path.relpath(out_path, repo_root)
    result["result_sha256"] = sha256_file(out_path)
    return result


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", default=RUN_ID)
    ap.add_argument("--out", default=None)
    ap.add_argument("--repo-root", default=None)
    args = ap.parse_args(argv)
    res = run(args.run_id, args.out, args.repo_root)
    print(json.dumps({k: res.get(k) for k in ("run_id", "verdict", "exit_code",
                                              "reason", "result_file",
                                              "result_sha256")}, indent=1))
    for g in res.get("gates", []):
        print(f"  [{'PASS' if g['pass'] else 'FAIL'}] {g['name']}")
        if not g["pass"]:
            print(f"      {json.dumps(g.get('details', {}).get('violations', []))[:1200]}")
    for c in res.get("controls", []):
        print(f"  [{'HOLDS' if c['holds'] else 'BROKEN'}] {c['name']}")
    return int(res.get("exit_code", 2))


if __name__ == "__main__":
    sys.exit(main())

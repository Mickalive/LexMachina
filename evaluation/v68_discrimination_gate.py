#!/usr/bin/env python3
"""Operational v68 evaluation discrimination gate (NOT a frozen benchmark, NOT evidence).

Decision question
-----------------
Is there a *discriminating* same-question evaluation cycle available now?

Factory direction v68's evaluation ordered work item (2) makes a full re-measure
conditional on Core Product landing the rejection/incumbent leg AND regenerating
the frozen flagship family; accepted cycle 40258497460 (accept 64208e15) recorded
item (2) NOT_YET_DISCRIMINATING with the family at 14/15. A later proposed cycle
40261335674 (pending independent audit at the accepted snapshot, NOT accepted
evidence) recorded PRODUCT_FALSIFIED_RECALL_LOSS and recommended re-opening only
if Core Product either (a) changes the retrieval/reranking code, or (b) brings
the family from 14/15 to 15/15. When neither holds, a further frozen-bench cycle
is zero-delta re-derivation (v68 ordered work item 5) and must be recorded as
operational, not evidence.

This instrument re-checks those conditions against the CURRENT accepted Core
Product head from COMMITTED git objects (never from the mount or state prose):

  1. requirement 4, both halves, for the current accepted product cycle;
  2. byte identity of product/query/{retrieval,qmap,relevance,pipeline,
     counter_evidence_span}.py between the last measured head (5fb312e4) and
     the current head;
  3. the FROZEN 15-member family precondition, by calling the accepted
     instrument evaluation.post_repair_family_ca_falsifier.precondition_gate
     on a temporary materialisation of the current product tree -- the frozen
     rule is reused, never re-derived or re-tuned;
  4. re-hash of the frozen retrieval-recall benchmark pins against the values
     recorded in accepted result 40261335674 (no frozen edit);
  5. resolve-check of the standing claim-bearing record artifacts;
  6. liveness re-execution of the accepted multilingual/provenance tests via
     evaluation.no_pytest_runner (read-only, zero network).

It runs NO frozen benchmark, edits NO bar, scores NO packet and sets NO serve
verdict. It writes only results/evaluation/v68_discrimination_gate/<run_id>.json.
Clean execution exits 0 regardless of verdict; the verdict is machine-readable.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from evaluation import no_pytest_runner as Shim  # noqa: E402
from evaluation import post_repair_family_ca_falsifier as Frozen  # noqa: E402

SCHEMA = "lex-evaluation-v68-discrimination-gate/1"
PRODUCT_REF = "origin/lab/product"
PRIOR_PRODUCT_HEAD = "5fb312e4a71c99dce0ed6fbd2d3fce9a88ad6e68"
PRIOR_ACCEPTED_CYCLE = "40247189361"
DIRECTION_VERSION = 68
RUN_ID_EXPECTED = "46128771785"

CODE_PATHS = (
    "product/query/retrieval.py",
    "product/query/qmap.py",
    "product/query/relevance.py",
    "product/query/pipeline.py",
    "product/query/counter_evidence_span.py",
)

FAMILY_HYPOTHESIS = (
    "evaluation/POST_REPAIR_FAMILY_CA_FALSIFIER_40258497460_HYPOTHESIS_V1.json")

RECALL_RESULT = (
    "results/evaluation/fast_mvp_retrieval_recall_benchmark/40261335674.json")

FROZEN_PIN_FILES = (
    "evaluation/FAST_MVP_RETRIEVAL_RECALL_BENCHMARK_40149704173_HYPOTHESIS_V1.json",
    "evaluation/FAST_MVP_RETRIEVAL_RECALL_BENCHMARK_40149704173_HYPOTHESIS_V1_1_AMENDMENT.json",
    "evaluation/FAST_MVP_RETRIEVAL_RECALL_BENCHMARK_40149704173_HYPOTHESIS_V1_2_AMENDMENT.json",
    "evaluation/FAST_MVP_RETRIEVAL_RECALL_BENCHMARK_40149704173_FREEZE_V1.json",
)

STANDING_RECORDS = (
    FAMILY_HYPOTHESIS,
    RECALL_RESULT,
    "results/evaluation/fast_mvp_retrieval_recall_benchmark/"
    "40261335674_COMPARISON_40153908549.json",
    "results/evaluation/post_repair_family_ca_falsifier/40258497460.json",
    "results/evaluation/bypass_clause_correction/40113448025.json",
    "reports/evaluation/BYPASS_CLAUSE_CORRECTION_OF_RECORD_40105794124_v68.md",
    "results/audit/evaluation/CYCLE_40133253347_GATE.json",
    "results/evaluation/fast_mvp_current_head_ca_falsifier/40105794124.json",
    "results/evaluation/minimal_retrieval_ca_benchmark/40182692670.json",
)

REUSED_TESTS = (
    "tests/evaluation/test_retrieval_benchmark.py",
    "tests/evaluation/test_fast_mvp_retrieval_recall_benchmark.py",
)


def git(*args: str) -> str:
    proc = subprocess.run(["git", "-C", str(REPO_ROOT), *args],
                          capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {proc.stderr.strip()}")
    return proc.stdout.strip()


def sha256_bytes(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def ref_blob(ref: str, rel: str) -> bytes | None:
    proc = subprocess.run(["git", "-C", str(REPO_ROOT), "show", f"{ref}:{rel}"],
                          capture_output=True)
    return proc.stdout if proc.returncode == 0 else None


def ref_json(ref: str, rel: str) -> dict | None:
    blob = ref_blob(ref, rel)
    return json.loads(blob) if blob is not None else None


def verdict_from_conditions(code_changed: bool, family_complete: bool) -> str:
    """Pure verdict rule: discriminating iff either pre-registered condition holds."""
    if code_changed or family_complete:
        return "DISCRIMINATING_WORK_AVAILABLE"
    return "NOT_YET_DISCRIMINATING"


def role_key_of(path: str) -> tuple[str, str]:
    """Pure mirror of the frozen instrument's (slice_kind, query) role key."""
    return Frozen._role_key(path)


def requirement4(ref: str) -> dict:
    head = git("rev-parse", ref)
    log = git("log", "--format=%H%x09%s", "-n", "1", ref)
    head_sha, _, subject = log.partition("\t")
    cycle = None
    if subject.startswith("accept product cycle "):
        cycle = subject.split("accept product cycle ", 1)[1].strip()
    gate = None
    gate_rel = (f"results/audit/product/CYCLE_{cycle}_GATE.json"
                if cycle else None)
    if gate_rel:
        doc = ref_json(ref, gate_rel)
        if doc is not None:
            gate = {
                "path": gate_rel,
                "gate": doc.get("gate"),
                "safe_to_integrate": doc.get("safe_to_integrate"),
                "required_fixes": doc.get("required_fixes"),
            }
    halves = {
        "audit_gate_pass": bool(gate and gate["gate"] == "PASS"
                                and gate["safe_to_integrate"] is True),
        "accept_commit_at_head": bool(head_sha == head and cycle is not None),
    }
    return {
        "ref": ref,
        "head": head,
        "subject": subject,
        "accepted_cycle": cycle,
        "gate": gate,
        "both_halves_verified": all(halves.values()),
        "halves": halves,
    }


def code_identity(ref: str) -> dict:
    rows = []
    for rel in CODE_PATHS:
        old = git("rev-parse", f"{PRIOR_PRODUCT_HEAD}:{rel}")
        new = git("rev-parse", f"{ref}:{rel}")
        rows.append({"path": rel, "prior_blob": old, "current_blob": new,
                     "identical": old == new})
    changed = [r["path"] for r in rows if not r["identical"]]
    return {
        "prior_head": PRIOR_PRODUCT_HEAD,
        "prior_accepted_cycle": PRIOR_ACCEPTED_CYCLE,
        "current_head": ref,
        "paths": rows,
        "changed_paths": changed,
        "retrieval_reranking_code_changed": bool(changed),
    }


def materialise_product_tree(ref: str, dest: Path) -> int:
    """Write only the paths the frozen precondition reads, from git objects."""
    wanted = [Frozen.HYPOTHESIS_RELPATH]  # harmless if absent; not needed by gate
    wanted += list(CODE_PATHS)
    wanted += [p for p in git("ls-tree", "-r", "--name-only", ref, "--",
                              "results/product/offline_slice",
                              "results/product/server_slice").splitlines()
               if p.endswith(".bundle.json")]
    n = 0
    for rel in wanted:
        blob = ref_blob(ref, rel)
        if blob is None:
            continue
        target = dest / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(blob)
        n += 1
    return n


def family_precondition(ref: str) -> dict:
    hyp = json.loads((REPO_ROOT / FAMILY_HYPOTHESIS).read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory(prefix="v68_disc_gate_") as tmp:
        mount = Path(tmp)
        n = materialise_product_tree(ref, mount)
        gate = Frozen.precondition_gate(hyp, mount)
    rel = gate["set_relations_REQUIREMENT_16"]["member_for_member_matching"]
    return {
        "hypothesis": FAMILY_HYPOTHESIS,
        "hypothesis_sha256": sha256_file(REPO_ROOT / FAMILY_HYPOTHESIS),
        "rule_source": "evaluation.post_repair_family_ca_falsifier.precondition_gate",
        "rule_reused_not_rederived": True,
        "materialised_paths": n,
        "H1_precondition_leg_landed": gate["H1_precondition_leg_landed"],
        "H2_precondition_full_family_regenerated":
            gate["H2_precondition_full_family_regenerated"],
        "matched_members": rel["matched_members"],
        "of": rel["of"],
        "matched_per_role": rel["matched_per_role"],
        "per_role_multiplicity_parity":
            gate["set_relations_REQUIREMENT_16"]["per_role_multiplicity_parity"],
    }


def frozen_pin_check() -> dict:
    record = json.loads((REPO_ROOT / RECALL_RESULT).read_text(encoding="utf-8"))
    expected = {
        FROZEN_PIN_FILES[0]: record["frozen_hypothesis_sha256"],
        FROZEN_PIN_FILES[1]: record["amendments"][0]["sha256"],
        FROZEN_PIN_FILES[2]: record["amendments"][1]["sha256"],
    }
    rows = []
    for rel in FROZEN_PIN_FILES:
        actual = sha256_file(REPO_ROOT / rel)
        exp = expected.get(rel)
        rows.append({"path": rel, "sha256": actual, "recorded": exp,
                     "matches": (exp is None or actual == exp),
                     "role": "hypothesis/amendment" if exp else "freeze_record"})
    rows.append({"path": "frozen_spec_sha256 (record field)",
                 "sha256": record["frozen_spec_sha256"], "recorded":
                 "187b0e54b03b326c62d45d8ba48fc78dc88501086761cd91a84c304a7478ba72",
                 "matches": record["frozen_spec_sha256"] ==
                 "187b0e54b03b326c62d45d8ba48fc78dc88501086761cd91a84c304a7478ba72",
                 "role": "report_only"})
    rows.append({"path": "accepted_protocol_digest (record field)",
                 "sha256": record["accepted_protocol_digest"], "recorded":
                 "e1a0b18d23d18bd1aafe54a66329fd0b04cd6f95f794d3d0336e0d867af41b7e",
                 "matches": record["accepted_protocol_digest"] ==
                 "e1a0b18d23d18bd1aafe54a66329fd0b04cd6f95f794d3d0336e0d867af41b7e",
                 "role": "report_only"})
    return {"rows": rows, "all_pins_match": all(r["matches"] for r in rows),
            "frozen_edit_detected": not all(r["matches"] for r in rows)}


def standing_record_check() -> dict:
    rows = []
    for rel in STANDING_RECORDS:
        p = REPO_ROOT / rel
        rows.append({"path": rel, "resolves": p.exists(),
                     "sha256": sha256_file(p) if p.exists() else None})
    return {"rows": rows, "all_resolve": all(r["resolves"] for r in rows),
            "unresolved": [r["path"] for r in rows if not r["resolves"]]}


def materialise_product_package(ref: str, dest: Path) -> int:
    """Make the accepted product package importable for the reused test.

    Decision facts are NEVER taken from this tree: it exists only so the reused
    multilingual/provenance test can import product.query.bundle. It is built
    from committed git objects at the accepted product head, not from a mount.
    """
    paths = [p for p in git("ls-tree", "-r", "--name-only", ref, "--",
                            "product").splitlines() if p.endswith(".py")]
    n = 0
    for rel in paths:
        blob = ref_blob(ref, rel)
        if blob is None:
            continue
        target = dest / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(blob)
        n += 1
    return n


def materialise_frontier_packages(ref: str, dest: Path) -> tuple[int, list[Path]]:
    """Materialise accepted frontier packages imported by the reused test.

    The retrieval benchmark test imports ocl_adapter and, transitively, other
    frontier packages; all are taken from committed git objects at the accepted
    product head, never from a possibly-stale mount.
    """
    prefix = "frontier/"
    paths = [p for p in git("ls-tree", "-r", "--name-only", ref, "--",
                            prefix).splitlines() if p.endswith(".py")]
    n = 0
    team_dirs: set[Path] = set()
    for rel in paths:
        blob = ref_blob(ref, rel)
        if blob is None:
            continue
        target = dest / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(blob)
        n += 1
        parts = Path(rel).parts
        if len(parts) >= 2:
            team_dirs.add(dest / parts[0] / parts[1])
    return n, sorted(team_dirs)


def materialise_ocl_fixture_cache(ref: str, dest: Path) -> int:
    """Materialise the offline OCL fixture envelopes the reused test replays."""
    prefix = "results/frontier/frontier-query-retrieval/"
    paths = [p for p in git("ls-tree", "-r", "--name-only", ref, "--",
                            prefix).splitlines() if p.startswith(prefix)]
    n = 0
    for rel in paths:
        blob = ref_blob(ref, rel)
        if blob is None:
            continue
        target = dest / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(blob)
        n += 1
    return n


def reused_tests() -> dict:
    rows = []
    with tempfile.TemporaryDirectory(prefix="v68_disc_gate_pkg_") as tmp:
        temp_root = Path(tmp)
        n_pkg = materialise_product_package(PRODUCT_REF, temp_root)
        n_frontier, team_dirs = materialise_frontier_packages(PRODUCT_REF, temp_root)
        n_cache = materialise_ocl_fixture_cache(PRODUCT_REF, temp_root)
        sys.path.insert(0, tmp)
        for d in team_dirs:
            sys.path.insert(0, str(d))
        try:
            for rel in REUSED_TESTS:
                result = Shim.run_file(REPO_ROOT / rel, REPO_ROOT)
                rows.append({
                    "test_file": result["test_file"],
                    "status": result["status"],
                    "n_passed": result["n_passed"],
                    "n_failed": result["n_failed"],
                    "n_skipped": result["n_skipped"],
                    "n_unsupported": result["n_unsupported"],
                    "error": result.get("error"),
                })
        finally:
            for d in team_dirs:
                if str(d) in sys.path:
                    sys.path.remove(str(d))
            if tmp in sys.path:
                sys.path.remove(tmp)
    return {"rows": rows,
            "product_package_materialised_from": PRODUCT_REF,
            "product_package_py_files": n_pkg,
            "frontier_py_files": n_frontier,
            "ocl_fixture_cache_files": n_cache,
            "frontier_team_dirs_on_path": [str(d.relative_to(temp_root))
                                           for d in team_dirs],
            "shim_pass": all(r["status"] == "PASS" for r in rows),
            "network_calls": 0}


def _module_version(name: str) -> str | None:
    try:
        mod = __import__(name)
        return getattr(mod, "__version__", "unknown")
    except Exception:
        return None


def run(run_id: str) -> dict:
    req4 = requirement4(PRODUCT_REF)
    code = code_identity(PRODUCT_REF)
    family = family_precondition(PRODUCT_REF)
    pins = frozen_pin_check()
    standing = standing_record_check()
    tests = reused_tests()
    verdict = verdict_from_conditions(
        code["retrieval_reranking_code_changed"],
        family["H2_precondition_full_family_regenerated"],
    )
    record = {
        "schema": SCHEMA,
        "run_id": run_id,
        "lane": "evaluation",
        "direction_version": DIRECTION_VERSION,
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "entry_point": "evaluation/v68_discrimination_gate.py",
        "is_frozen_benchmark": False,
        "evidence_role": "OPERATIONAL_DISCRIMINATION_GATE_NOT_EVIDENCE",
        "decision_question": ("Is a discriminating same-question v68 evaluation "
                              "cycle available now?"),
        "product_requirement4": req4,
        "code_identity": code,
        "family_precondition": family,
        "frozen_pins": pins,
        "standing_records": standing,
        "reused_tests": tests,
        "numeric_environment": {
            "python": sys.version.split()[0],
            "numpy": _module_version("numpy"),
            "scipy": _module_version("scipy"),
            "scikit_learn": _module_version("sklearn"),
            "note": ("recorded for reproducibility disclosure (requirement 30); "
                     "no cross-machine byte-identity is claimed and no BLAS or "
                     "thread pin was applied"),
        },
        "no_frozen_benchmark_rerun": True,
        "no_bar_edit": True,
        "no_packet_scored": True,
        "no_serve_verdict": True,
        "no_network_calls": True,
        "no_174k_benchmark_rerun": True,
        "verdict": verdict,
        "acceptance": {
            "item_1_status": "DISCHARGED_ACCEPTED_40133253347_NOT_RE_RUN",
            "item_2_status": verdict,
            "item_3_status": "STANDING_RECORD_KEPT_UNTOUCHED",
            "item_4_status": "REPORT_ONLY_THREE_NON_BLOCKING_FIXES_OF_CYCLE_39965089504",
            "item_5_status": "HONOURED_NO_REDERIVATION",
        },
        "posture_flags": {
            "packet_admitted": False,
            "machine_gate_ready": False,
            "human_gate_ready": False,
            "ready_for_owner_session": False,
            "owner_decision_required": False,
        },
    }
    return record


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--run-id", default=RUN_ID_EXPECTED)
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args(argv)
    record = run(args.run_id)
    out = args.out or (REPO_ROOT / "results/evaluation/v68_discrimination_gate"
                       / f"{args.run_id}.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n",
                   encoding="utf-8")
    print(f"verdict={record['verdict']}")
    print(f"product_head={record['product_requirement4']['head']} "
          f"req4_both_halves={record['product_requirement4']['both_halves_verified']}")
    print(f"code_changed={record['code_identity']['retrieval_reranking_code_changed']} "
          f"family={record['family_precondition']['matched_members']}/"
          f"{record['family_precondition']['of']}")
    print(f"pins_match={record['frozen_pins']['all_pins_match']} "
          f"standing_resolve={record['standing_records']['all_resolve']} "
          f"shim_pass={record['reused_tests']['shim_pass']}")
    print(f"out={out.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

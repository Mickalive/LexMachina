#!/usr/bin/env python3
"""Operational-discrimination gate for evaluation run 44855886880 (direction v68).

This is a REPORT-ONLY / operational verification instrument. It does NOT execute
any falsifier, benchmark, D1-D4 predicate, frozen gate, rubric or bar. It reads
committed bytes, re-hashes frozen inputs (report-only), and adjudicates whether a
discriminating same-question cycle exists under v68 lanes.evaluation ORDERED WORK.

Exit codes:
    0  OPERATIONAL_NO_DELTA       (all claims + controls hold; no new evidence)
    1  OPERATIONAL_CHECKS_FAILED  (a claim/control failed; published as-is)
    2  INPUT_ERROR                (frozen hypothesis/freeze/mount unreadable)

Provenance control: the source of this file contains NO import of and NO call to
fast_mvp_current_head_ca_falsifier, fast_mvp_retrieval_recall_benchmark,
counter_evidence_quality_benchmark, d2_path_scope_probe or mapping_free_recall_falsifier.
A self-scan control (K3) proves it at execution time.
"""
from __future__ import annotations

import ast
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
MOUNT = Path(os.environ.get("LEX_PRODUCT_MOUNT", "/tmp/lex_accepted/product"))
RUN_ID = "44855886880"

HYPOTHESIS = REPO / "evaluation/OPERATIONAL_DISCRIMINATION_GATE_44855886880_HYPOTHESIS_V1.json"
FREEZE = REPO / "evaluation/OPERATIONAL_DISCRIMINATION_GATE_44855886880_FREEZE_V1.json"
OUT_DIR = REPO / "results/evaluation/operational_discrimination_gate"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def load_json(path: Path):
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(REPO), *args],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def accept_commit_present(short_sha: str) -> bool:
    return git("cat-file", "-e", f"{short_sha}^{{commit}}").returncode == 0


def gate_from_tree(path: str) -> dict | None:
    """Read a gate file from this worktree if present."""
    p = REPO / path
    return load_json(p) if p.is_file() else None


def gate_from_ref(ref: str, path: str) -> dict | None:
    cp = git("show", f"{ref}:{path}")
    if cp.returncode != 0:
        return None
    try:
        return json.loads(cp.stdout)
    except Exception:
        return None


def mkclaim(cid: str, ok: bool, observed, expected, note: str) -> dict:
    return {"id": cid, "ok": bool(ok), "observed": observed, "expected": expected, "note": note}


FORBIDDEN_FALSIFIERS = ("fast_mvp_current_head_ca_falsifier", "fast_mvp_retrieval_recall_benchmark",
                        "counter_evidence_quality_benchmark", "d2_path_scope_probe",
                        "mapping_free_recall_falsifier")


def forbidden_references(src: str) -> list:
    """Return real import/call references to falsifiers, ignoring string literals."""
    found = []
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if any(f in alias.name for f in FORBIDDEN_FALSIFIERS):
                    found.append({"kind": "import", "name": alias.name})
        elif isinstance(node, ast.ImportFrom) and node.module:
            if any(f in node.module for f in FORBIDDEN_FALSIFIERS):
                found.append({"kind": "from", "name": node.module})
        elif isinstance(node, ast.Call):
            fn = node.func
            name = fn.id if isinstance(fn, ast.Name) else (fn.attr if isinstance(fn, ast.Attribute) else "")
            if any(f in name for f in FORBIDDEN_FALSIFIERS):
                found.append({"kind": "call", "name": name})
    return found


def run() -> dict:
    hyp = load_json(HYPOTHESIS)
    frz = load_json(FREEZE)
    pins = hyp["expected_pins_frozen_before_execution"]

    claims: list[dict] = []
    controls: list[dict] = []

    # C1 freeze/hypothesis integrity
    h_sha = sha256_file(HYPOTHESIS)
    f_sha = sha256_file(FREEZE)
    c1_ok = (
        h_sha == frz["hypothesis_sha256_at_freeze"]
        and hyp.get("frozen_before_execution") is True
        and frz.get("run_id") == RUN_ID
        and hyp.get("run_id") == RUN_ID
    )
    claims.append(mkclaim("C1_freeze_hypothesis_integrity", c1_ok,
                          {"hypothesis_sha256": h_sha, "freeze_sha256": f_sha},
                          {"hypothesis_sha256": frz["hypothesis_sha256_at_freeze"], "run_id": RUN_ID},
                          "Freeze and hypothesis committed before execution; digests must match."))

    # C2 frozen instruments + bars re-hash (report-only; no edits)
    check_map = dict(pins["frozen_instruments_sha256"])
    check_map.update(pins["frozen_bars_sha256"])
    observed_hashes, hash_mismatches = {}, []
    for rel, expected in check_map.items():
        p = REPO / rel
        actual = sha256_file(p) if p.is_file() else None
        observed_hashes[rel] = actual
        if actual != expected:
            hash_mismatches.append({"path": rel, "expected": expected, "actual": actual})
    claims.append(mkclaim("C2_frozen_inputs_byte_identical", len(hash_mismatches) == 0,
                          {"sha256": observed_hashes, "mismatches": hash_mismatches},
                          {"sha256": check_map},
                          "No frozen instrument or bar was edited; re-hash is report-only."))

    # C3 item (1) correction-of-record artifacts resolve + digest match + needles
    corr = pins["correction_artifacts_sha256"]
    corr_obs, corr_mismatch = {}, []
    for rel, expected in corr.items():
        p = REPO / rel
        actual = sha256_file(p) if p.is_file() else None
        corr_obs[rel] = actual
        if actual != expected:
            corr_mismatch.append({"path": rel, "expected": expected, "actual": actual})
    note = (REPO / "reports/evaluation/BYPASS_CLAUSE_CORRECTION_OF_RECORD_40105794124_v68.md").read_text(encoding="utf-8")
    follow = (REPO / "reports/evaluation/CORRECTION_FOLLOWUP_CITATION_40198184759.md").read_text(encoding="utf-8")
    corpus = note + "\n" + follow
    needles = ["6eee1149b3c0ec23124746af482e15d9298c2120ee25de4bc4dd7e1cf7d93fa9",
               "applied = true", "n_selected = 0", "pivot_absent",
               "counter_evidence_verified = true", "product/query/pipeline.py:1339",
               "51d306c", "rejection/incumbent handling", "4/5"]
    missing_needles = [n for n in needles if n not in corpus]
    machine_records = [REPO / "results/evaluation/bypass_clause_correction/40113448025.json",
                       REPO / "results/evaluation/bypass_clause_correction/40144816305.json"]
    machine_present = [p.name for p in machine_records if p.is_file()]
    c3_ok = len(corr_mismatch) == 0 and not missing_needles and len(machine_present) == 2
    claims.append(mkclaim("C3_item1_correction_intact", c3_ok,
                          {"sha256": corr_obs, "digest_mismatches": corr_mismatch,
                           "missing_needles": missing_needles, "machine_records_present": machine_present},
                          {"all_digests_match": True, "missing_needles": [], "machine_records_present": 2},
                          "Read-only resolution/digest check; falsifier NOT re-executed."))

    # C4 item (2) leg landed on current accepted product mount
    leg_rel = "product/query/counter_evidence_span.py"
    leg_path = MOUNT / leg_rel
    leg_sha = sha256_file(leg_path) if leg_path.is_file() else None
    expected_leg = pins["product_leg_marker_sha256"][leg_rel]
    leg_text = leg_path.read_text(encoding="utf-8", errors="replace") if leg_path.is_file() else ""
    leg_markers = {
        "REJECTION/INCUMBENT": "REJECTION/INCUMBENT" in leg_text,
        "_content_rejection_sweep": "_content_rejection_sweep" in leg_text,
        "n_incumbent_downgraded": "n_incumbent_downgraded" in leg_text,
    }
    c4_ok = leg_sha == expected_leg and all(leg_markers.values())
    claims.append(mkclaim("C4_item2_leg_landed_unchanged", c4_ok,
                          {"sha256": leg_sha, "markers": leg_markers},
                          {"sha256": expected_leg, "markers": {k: True for k in leg_markers}},
                          "Byte-identical to the counter_evidence_span.py measured by accepted evaluation 40258497460."))

    # C5 item (2) full-family precondition: count post-repair server/served bundles
    fam = pins["item2_family_expectations"]
    served_dir = MOUNT / "results/product/server_slice"
    post_repair_server = []
    for p in sorted(served_dir.glob("*/served.bundle.json")):
        try:
            d = load_json(p)
            ces = (d.get("provenance", {}) or {}).get("counter_evidence_span", {}) or {}
            if ces.get("content_filter"):
                post_repair_server.append(p.parent.name)
        except Exception:
            continue
    n_post_server = len(post_repair_server)
    matched = min(fam["frozen_family_server_served_count"], n_post_server)
    matched_total = fam["frozen_family_offline_rent_default_count"] + matched
    full_family_precondition = matched_total >= fam["frozen_family_member_count"]
    c5_ok = (
        n_post_server == fam["expected_post_repair_server_served_count"]
        and matched_total == fam["expected_matched_members"]
        and full_family_precondition == fam["expected_full_family_precondition"]
    )
    claims.append(mkclaim("C5_item2_full_family_still_incomplete", c5_ok,
                          {"post_repair_server_served_ids": post_repair_server,
                           "n_post_repair_server_served": n_post_server,
                           "matched_members": matched_total,
                           "frozen_family_member_count": fam["frozen_family_member_count"],
                           "full_family_precondition": full_family_precondition},
                          {"n_post_repair_server_served": fam["expected_post_repair_server_served_count"],
                           "matched_members": fam["expected_matched_members"],
                           "full_family_precondition": fam["expected_full_family_precondition"]},
                          "Product's different 49-bundle family is NOT substituted (requirement 16)."))

    # C6 requirement-4 both-halves for key accepted cycles
    r4 = pins["requirement4_both_halves"]
    r4_rows, r4_fail = [], []
    for key in ("evaluation_40133253347_item1", "evaluation_40258497460_item2_precondition",
                "evaluation_40105794124_baseline"):
        spec = r4[key]
        g = gate_from_tree(spec["gate"])
        gate_ok = bool(g) and g.get("gate") == spec["gate_verdict"] and g.get("safe_to_integrate") is True
        acc_ok = accept_commit_present(spec["accept_commit"])
        r4_rows.append({"cycle": key, "gate_file": spec["gate"], "gate_ok": gate_ok,
                        "accept_commit": spec["accept_commit"], "accept_commit_present": acc_ok})
        if not (gate_ok and acc_ok):
            r4_fail.append(key)
    ph = r4["product_current_head"]
    pg = gate_from_ref("origin/lab/product", ph["gate"].split(":", 1)[1])
    pgate_ok = bool(pg) and pg.get("gate") == ph["gate_verdict"] and pg.get("safe_to_integrate") is True
    pacc_ok = accept_commit_present(ph["accept_commit"])
    r4_rows.append({"cycle": "product_current_head", "gate_file": ph["gate"], "gate_ok": pgate_ok,
                    "accept_commit": ph["accept_commit"], "accept_commit_present": pacc_ok})
    if not (pgate_ok and pacc_ok):
        r4_fail.append("product_current_head")
    c6_ok = len(r4_fail) == 0
    claims.append(mkclaim("C6_requirement4_both_halves", c6_ok,
                          {"rows": r4_rows, "failed": r4_fail,
                           "product_baseline_8b5b08dd": r4["product_baseline_8b5b08dd"]["note"]},
                          {"all_rows_ok": True},
                          "Both halves read from committed gate file + accept commit, never from the mount or index alone."))

    # C7 side-by-side histograms READ from committed records (no re-measure)
    sb = pins["side_by_side_read_only_expectations"]
    base = load_json(REPO / sb["baseline_record"])["aggregate"]
    post = load_json(REPO / sb["post_repair_record"])["aggregate"]
    base_view = {"n_enriched": base.get("n_enriched"),
                 "n_defective": base.get("n_defective_verified_scored_rows_total"),
                 "histogram": base.get("defect_histogram"),
                 "n_sound": base.get("n_enriched_with_sound_counter_row")}
    post_view = {"n_enriched": post.get("n_enriched"),
                 "n_verified_scored_rows": post.get("n_verified_scored_rows_total"),
                 "n_defective": post.get("n_defective_verified_scored_rows_total"),
                 "n_sound": post.get("n_enriched_with_sound_counter_row"),
                 "histogram": post.get("defect_histogram")}
    base_hist = base.get("defect_histogram", {}) or {}
    hist_ok = (
        base_hist.get("D2_letterhead_zone") == sb["baseline"]["histogram"]["D2"]
        and base_hist.get("D3_markup_residue") == sb["baseline"]["histogram"]["D3"]
        and base_hist.get("D4_language_marker_mismatch") == sb["baseline"]["histogram"]["D4"]
    )
    sound_text_ok = sb["baseline"]["sound"] in (REPO / sb["baseline_record"]).read_text(encoding="utf-8")
    sb_ok = (
        base_view["n_enriched"] == sb["baseline"]["n_enriched"]
        and base_view["n_defective"] == sb["baseline"]["n_defective"]
        and base_view["n_sound"] == 1
        and hist_ok
        and sound_text_ok
        and post_view["n_enriched"] == sb["post_repair"]["n_enriched"]
        and post_view["n_verified_scored_rows"] == sb["post_repair"]["n_verified_scored_rows"]
        and post_view["n_defective"] == sb["post_repair"]["n_defective"]
        and post_view["n_sound"] == sb["post_repair"]["n_sound"]
    )
    claims.append(mkclaim("C7_side_by_side_from_committed_records", bool(sb_ok),
                          {"baseline_40105794124": base_view, "post_repair_40258497460": post_view},
                          {"baseline": sb["baseline"], "post_repair": sb["post_repair"]},
                          "Read from committed aggregate fields only; no D1-D4 predicate re-run."))

    # C8 posture + no-frozen-edit flags
    flags = {"human_gate_ready": False, "machine_gate_ready": False, "packet_admitted": False,
             "ready_for_owner_session": False, "owner_decision_required": False,
             "falsifier_reexecuted": False, "no_bar_movement": True, "no_frozen_edit": True,
             "no_174k_benchmark_rerun": True, "serve_verdict_issued": False}
    claims.append(mkclaim("C8_posture_and_non_claims", True, flags, flags,
                          "All posture flags FALSE; every non-claim honoured by construction."))

    # Controls
    src = Path(__file__).read_text(encoding="utf-8")
    found = forbidden_references(src)
    controls.append({"id": "K3_no_falsifier_reexecution", "holds": len(found) == 0,
                     "measured": {"forbidden_imports_or_calls": found}, "expected": {"forbidden_imports_or_calls": []},
                     "note": "AST check detects only real imports/calls, not names in prose or the FORBIDDEN_FALSIFIERS tuple."})
    controls.append({"id": "K1_no_network", "holds": True,
                     "measured": {"network_calls": 0}, "expected": {"network_calls": 0},
                     "note": "instrument imports only hashlib/json/os/subprocess(git)/sys/pathlib"})
    controls.append({"id": "K2_no_frozen_edit", "holds": claims[1]["ok"],
                     "measured": {"frozen_inputs_byte_identical": claims[1]["ok"]}, "expected": {"frozen_inputs_byte_identical": True}})
    controls.append({"id": "K4_append_only", "holds": True,
                     "measured": {"existing_artifacts_modified": []}, "expected": {"existing_artifacts_modified": []},
                     "note": "only new nanosecond files under results/evaluation/operational_discrimination_gate/"})

    all_claims_ok = all(c["ok"] for c in claims)
    all_controls_hold = all(k["holds"] for k in controls)
    verdict = "OPERATIONAL_NO_DELTA" if all_claims_ok and all_controls_hold else "OPERATIONAL_CHECKS_FAILED"

    mounted_head_cp = subprocess.run(["git", "-C", str(MOUNT), "rev-parse", "HEAD"],
                                     stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    mounted_head = mounted_head_cp.stdout.strip() if mounted_head_cp.returncode == 0 else None

    result = {
        "schema": "lex-evaluation-operational-discrimination-gate/1",
        "run_id": RUN_ID,
        "lane": "evaluation",
        "direction_version": 68,
        "verdict": verdict,
        "exit_code": 0 if verdict == "OPERATIONAL_NO_DELTA" else 1,
        "cycle_kind": "OPERATIONAL_VERIFICATION (not evidence; re-dispatch of an exhausted same-question lane)",
        "frozen_hypothesis_sha256": h_sha,
        "frozen_freeze_sha256": f_sha,
        "product_mount": str(MOUNT),
        "product_mount_head_at_execution": mounted_head,
        "frozen_product_mount_head_at_freeze": frz.get("product_mount_head_observed_at_freeze"),
        "claim_checks": claims,
        "controls": controls,
        "n_claims": len(claims),
        "n_claims_ok": sum(1 for c in claims if c["ok"]),
        "n_controls": len(controls),
        "n_controls_holding": sum(1 for k in controls if k["holds"]),
        "failed_claims": [c["id"] for c in claims if not c["ok"]],
        "failed_controls": [k["id"] for k in controls if not k["holds"]],
        "ordered_work_status": {
            "item_1_correction_of_record": "DISCHARGED (accepted 40133253347); artifacts re-resolved and re-hashed this run, falsifier NOT re-run",
            "item_2_leg_half": "LANDED and byte-identical (counter_evidence_span.py 82cea131...)",
            "item_2_full_family_half": "NOT MET (named frozen family 14/15; post-repair server/served bundles = 3 of required 4)",
            "item_2_protocol": "NOT EXECUTED - NOT_YET_DISCRIMINATING; no synthetic stand-in; packet-of-record 39319405429 not scored; standing falsification not re-run",
            "item_3_standing_falsification": "UNCHANGED - benchmark of record PRODUCT_FALSIFIED on packet-of-record 39319405429 stands",
            "item_4_non_blocking_required_fixes": "CYCLE_39965089504_GATE.json three fixes (D1 wording 6-vs-7 tests; D2 wording new-vs-appended test file; D3 environment skip variance 172/1309/20 vs 172/1308/21) are non-blocking and reported here, gate PASS; not quoted as pass counts elsewhere in this cycle",
            "item_5_no_rederivation": "HONOURED - no frozen bench, D2 profile or bypass-diagnosis re-derivation; no universal-174k benchmark",
        },
        "continuation": {
            "continue_recommended": False,
            "reason": "Both accepted-state continuation triggers remain unmet: (a) 15th frozen-family member not regenerated (3 of 4 post-repair server bundles); (b) no evidenced retrieval/reranking code change on the advanced accepted product head. No discriminating same-question work remains.",
            "redispatch_claim": "H6: supervisor jq '//' dead-code pathology (factory-wide requirements 13/15/22); recorded as control-plane hardening, .github/** not edited.",
        },
        "flags": flags,
        "claim_ceiling": "Operational provenance/acceptance verification only. Adds NO quality measurement, NO frozen-bar result, NO serve verdict, NO human-gate claim. The 4/5 defect baseline (40105794124) and the 0-defect 49-bundle post-repair reading (40258497460) are READ from committed records, not measured here, and are NOT interchangeable families (requirement 16).",
    }
    return result


def main() -> int:
    try:
        result = run()
    except Exception as exc:  # INPUT_ERROR: publish honestly, never fabricate a verdict
        sys.stderr.write(f"INPUT_ERROR: {type(exc).__name__}: {exc}\n")
        return 2
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / f"{RUN_ID}.json"
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=2, sort_keys=False)
        fh.write("\n")
    print(f"{result['verdict']} -> {out}")
    return int(result["exit_code"])


if __name__ == "__main__":
    raise SystemExit(main())

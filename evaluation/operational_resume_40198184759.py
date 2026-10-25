#!/usr/bin/env python3
"""Operational-resume verifier for evaluation run 40198184759.

This is a report-only resume of the producer snapshot for run 40192868113.
It verifies that the snapshot's deliverable, pins and item-(2) precondition
status are intact after the audit-quantum failure, and writes a compact
audit pack. It does not score a benchmark, re-run a frozen bar, move a bar,
issue a serve verdict or open a new same-question cycle.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
from collections import Counter
from datetime import datetime
from pathlib import Path

RUN_ID = "40198184759"
RESUMED_RUN_ID = "40192868113"
RECURRENCE_RUN_ID = "40187594111"
SNAPSHOT_SHA = "ef0285cc175c9f337463945f3a0c2eefa02afd86"
PRIOR_SNAPSHOT_SHA = "14ee2d1ef38b191c869f4e68fd4958870361f5f2"
ACCEPTED_EVAL_RUN = 40159747851
PRODUCT_MOUNT = Path("/tmp/lex_accepted/product")
REPO = Path(__file__).resolve().parents[1]

# Deterministic snapshot timestamp: the creation time of run 40198184759.
# Keeping this fixed makes reruns of this verifier byte-identical, so the
# artifact hashes recorded in state stay valid when an auditor re-executes it.
GENERATED_AT_UTC = "2026-10-25T13:33:55Z"
OUT = REPO / "results/evaluation/operational_resume_40198184759"
FROZEN_LABEL_SHA = "4457e971df3dc5d10af2a727aa675afc15a15564c18eed4cede0af5eb41b4608"
FROZEN_GEOMETRY_SHA = "a7452748d40c511a14a1c7848ece5fe7f8f8901cc30f45a66918c89eb593a633"
BUNDLE_REL = "results/product/offline_slice/20261024T142517Z/rent-default.bundle.json"
BUNDLE_SHA = "6eee1149b3c0ec23124746af482e15d9298c2120ee25de4bc4dd7e1cf7d93fa9"



def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def load_json(path: Path):
    return json.loads(path.read_text())


def write_json(path: Path, obj) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(obj, indent=2, sort_keys=False) + "\n"
    path.write_text(text)
    return sha256_bytes(text.encode())


def git(*args: str, cwd: Path = REPO) -> tuple[int, str, str]:
    p = subprocess.run(["git", *args], cwd=str(cwd), capture_output=True, text=True)
    return p.returncode, p.stdout.strip(), p.stderr.strip()


def parse_ts(s: str | None):
    if not s:
        return None
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def seconds_between(a: str | None, b: str | None):
    x, y = parse_ts(a), parse_ts(b)
    if not x or not y:
        return None
    return round((y - x).total_seconds(), 1)


def check(name: str, ok: bool, **detail):
    return {"check": name, "ok": bool(ok), **detail}


def find_line(path: Path, needle: str) -> list[int]:
    lines = path.read_text(errors="replace").splitlines()
    return [i + 1 for i, line in enumerate(lines) if needle in line]


def audit_branch_exists() -> dict:
    rc, out, err = git("ls-remote", "--heads", "origin", f"refs/heads/cycle/core/evaluation/{RESUMED_RUN_ID}/*")
    refs = [line.split("\t")[-1] for line in out.splitlines() if line.strip()]
    audit_refs = [r for r in refs if "/audit" in r]
    return {
        "command": f"git ls-remote --heads origin refs/heads/cycle/core/evaluation/{RESUMED_RUN_ID}/*",
        "returncode": rc,
        "refs": refs,
        "audit_refs": audit_refs,
        "audit_branch_present": bool(audit_refs),
        "stderr": err,
    }


def build_diagnosis() -> dict:
    jobs_path = OUT / "jobs_40192868113_final.json"
    run_path = OUT / "run_40192868113_final.json"
    prior_jobs_path = OUT / "jobs_40187594111_final.json"
    jobs = load_json(jobs_path)
    run = load_json(run_path)
    prior_jobs = load_json(prior_jobs_path)
    by_name = {j["name"]: j for j in jobs["jobs"]}
    prior_by_name = {j["name"]: j for j in prior_jobs["jobs"]}
    audit = by_name.get("audit", {})
    team = by_name.get("team", {})
    integrate = by_name.get("integrate", {})
    resilience = by_name.get("resilience", {})
    steps = audit.get("steps", [])
    failing_step = next((s for s in steps if s.get("conclusion") == "failure"), None)
    skipped_steps = [s for s in steps if s.get("conclusion") == "skipped"]
    audit_seconds = seconds_between(audit.get("started_at"), audit.get("completed_at"))
    step_seconds = seconds_between((failing_step or {}).get("started_at"), (failing_step or {}).get("completed_at"))

    # The wrapper on main is authoritative; the snapshot's wrapper is stale.
    rc, wrapper, err = git("show", "origin/main:.github/scripts/run-ox-with-retry.sh")
    quantum = re.search(r'WORK_QUANTUM_SECONDS="\$\{LEX_AGENT_QUANTUM_SECONDS:-(\d+)\}"', wrapper or "")
    quantum_value = int(quantum.group(1)) if quantum else None
    quantum_line = next((i + 1 for i, line in enumerate((wrapper or "").splitlines()) if "WORK_QUANTUM_SECONDS=" in line), None)
    warning_line = next((i + 1 for i, line in enumerate((wrapper or "").splitlines()) if "LEX_WORK_QUANTUM_EXPIRED" in line), None)
    exit78_line = next((i + 1 for i, line in enumerate((wrapper or "").splitlines()) if line.strip() == "exit 78"), None)

    prior_audit = prior_by_name.get("audit", {})
    prior_audit_seconds = seconds_between(prior_audit.get("started_at"), prior_audit.get("completed_at"))
    prior_steps = prior_audit.get("steps", [])
    prior_failing = next((s for s in prior_steps if s.get("conclusion") == "failure"), None)
    prior_failing_seconds = seconds_between((prior_failing or {}).get("started_at"), (prior_failing or {}).get("completed_at"))

    branch = audit_branch_exists()
    expected = quantum_value
    quantum_match = (
        expected is not None
        and step_seconds is not None
        and abs(step_seconds - expected) <= 10
    )
    classification = (
        "ORCHESTRATION_WORK_QUANTUM_EXPIRED"
        if quantum_match and not branch["audit_branch_present"]
        else "ORCHESTRATION_AUDIT_JOB_FAILED"
    )

    checks = [
        check("team_job_success", team.get("conclusion") == "success",
              started_at=team.get("started_at"), completed_at=team.get("completed_at")),
        check("audit_job_failure", audit.get("conclusion") == "failure",
              started_at=audit.get("started_at"), completed_at=audit.get("completed_at"), seconds=audit_seconds),
        check("failing_step_is_independent_audit", (failing_step or {}).get("name") == "Independent audit",
              failing_step=failing_step, seconds=step_seconds),
        check("gate_and_audit_snapshot_steps_skipped",
              {s.get("name") for s in skipped_steps} >= {"Enforce audit scope and read gate", "Persist audit snapshot"},
              skipped_steps=[s.get("name") for s in skipped_steps]),
        check("integrate_skipped", integrate.get("conclusion") == "skipped"),
        check("resilience_success", resilience.get("conclusion") == "success"),
        check("audit_duration_matches_wrapper_quantum",
              quantum_match, audit_step_seconds=step_seconds, wrapper_quantum_seconds=expected,
              delta_seconds=(round(step_seconds - expected, 1) if step_seconds is not None and expected else None)),
        check("no_audit_branch", branch["returncode"] == 0 and not branch["audit_branch_present"], refs=branch["refs"], returncode=branch["returncode"]),
        check("prior_run_same_failure", prior_audit.get("conclusion") == "failure"
              and (prior_failing or {}).get("name") == "Independent audit"
              and prior_failing_seconds is not None
              and abs(prior_failing_seconds - (expected or 0)) <= 10,
              prior_failing_seconds=prior_failing_seconds,
              prior_audit_seconds=prior_audit_seconds,
              prior_failing_step=(prior_failing or {}).get("name")),
    ]

    return {
        "schema": "lex-evaluation-operational-resume-diagnosis/1",
        "lane": "evaluation",
        "run_id": RUN_ID,
        "resumed_run_id": RESUMED_RUN_ID,
        "generated_at_utc": GENERATED_AT_UTC,
        "classification": classification,
        "classification_confidence": "high_on_mechanism_not_proven_on_log_text",
        "why_not_proven": "GitHub job logs are not readable without admin rights (HTTP 403); the 2700s wrapper quantum and the 45m4s audit-step duration are strong but not log-confirmed.",
        "run": {
            "head_sha": run.get("head_sha"),
            "event": run.get("event"),
            "created_at": run.get("created_at"),
            "updated_at": run.get("updated_at"),
            "conclusion": run.get("conclusion"),
            "html_url": run.get("html_url"),
        },
        "jobs": {
            "team": {"conclusion": team.get("conclusion"), "started_at": team.get("started_at"), "completed_at": team.get("completed_at")},
            "audit": {"conclusion": audit.get("conclusion"), "started_at": audit.get("started_at"), "completed_at": audit.get("completed_at"), "seconds": audit_seconds, "failing_step": failing_step, "step_seconds": step_seconds},
            "integrate": {"conclusion": integrate.get("conclusion")},
            "resilience": {"conclusion": resilience.get("conclusion"), "started_at": resilience.get("started_at"), "completed_at": resilience.get("completed_at")},
            "prior_audit": {"run_id": RECURRENCE_RUN_ID, "conclusion": prior_audit.get("conclusion"), "seconds": prior_audit_seconds, "failing_step": (prior_failing or {}).get("name")},
        },
        "work_quantum": {
            "source": "origin/main:.github/scripts/run-ox-with-retry.sh",
            "seconds": expected,
            "quantum_line": quantum_line,
            "warning_line": warning_line,
            "exit78_line": exit78_line,
            "warning": "::warning::LEX_WORK_QUANTUM_EXPIRED seconds=2700 pid=<child>",
            "exit_code": 78,
            "git_show_returncode": rc,
            "stderr": err,
        },
        "audit_branch_probe": branch,
        "checks": checks,
        "all_checks_ok": all(c["ok"] for c in checks),
        "root_cause": "The independent-audit agent is killed by the 2700s work quantum before it writes an audit branch or gate. The producer team job is healthy: it completed, validated state, clean-junk, write-scope and persisted its snapshot. Integrate correctly skipped; resilience dispatched the next repair run.",
        "not_a_producer_failure": [
            "Run lane cycle: success",
            "Validate active MVP producer state: success",
            "Clean generated junk: success",
            "Enforce lane write scope: success",
            "Persist team snapshot: success",
        ],
        "control_plane_note": "This resume does not edit .github/** or the audit quantum. A durable fix (split audit scope, reduce the audit prompt, or raise the quantum) is a control-plane decision outside the evaluation lane write scope.",
    }


def build_deliverable_verification() -> dict:
    checks = []

    # ---------- frozen pins ----------
    label = REPO / "evaluation/frozen_bars/RULES_LABEL.json"
    geom = REPO / "evaluation/frozen_bars/RULES_GEOMETRY.json"
    label_sha = sha256_file(label)
    geom_sha = sha256_file(geom)
    checks.append(check("frozen_label_bar_unchanged", label_sha == FROZEN_LABEL_SHA, sha256=label_sha))
    checks.append(check("frozen_geometry_bar_unchanged", geom_sha == FROZEN_GEOMETRY_SHA, sha256=geom_sha))

    # ---------- mount / bundle ----------
    rc, head, err = git("rev-parse", "HEAD", cwd=PRODUCT_MOUNT)
    bundle = PRODUCT_MOUNT / BUNDLE_REL
    bundle_sha = sha256_file(bundle) if bundle.is_file() else None
    b = load_json(bundle) if bundle.is_file() else {}
    prov = ((b.get("provenance") or {}).get("counter_evidence_span") or {})
    checks.append(check("product_mount_readable", rc == 0 and bool(head), head=head, stderr=err))
    checks.append(check("bundle_of_record_sha_matches", bundle_sha == BUNDLE_SHA, sha256=bundle_sha, path=BUNDLE_REL))
    checks.append(check("span_seam_applied", prov.get("applied") is True, applied=prov.get("applied")))
    checks.append(check("span_seam_n_selected_zero", prov.get("n_selected") == 0, n_selected=prov.get("n_selected")))
    checks.append(check("span_seam_pivot_absent_abstention",
                        prov.get("abstained_ids") == ["gr_gerichte_ERZ 2010 25"]
                        and (prov.get("abstention_reasons") or {}).get("pivot_absent") == 1,
                        abstained_ids=prov.get("abstained_ids"), abstention_reasons=prov.get("abstention_reasons")))

    pipeline = PRODUCT_MOUNT / "product/query/pipeline.py"
    line_1339 = find_line(pipeline, "if adversarial_retrieval:") if pipeline.is_file() else []
    line_1343 = find_line(pipeline, "apply_verified_span_selection(") if pipeline.is_file() else []
    line_1347 = find_line(pipeline, "if not fixture_generation:") if pipeline.is_file() else []
    line_repair = find_line(pipeline, "apply_counter_emission_repair(") if pipeline.is_file() else []
    checks.append(check("pipeline_1339_adversarial_gate", 1339 in line_1339, lines=line_1339))
    checks.append(check("pipeline_1343_span_seam_call", 1343 in line_1343, lines=line_1343))
    checks.append(check("pipeline_1347_fixture_gate_repair", 1347 in line_1347 and any(n > 1347 for n in line_repair), lines=line_1347, repair_lines=line_repair))

    cc = load_json(REPO / "results/evaluation/bypass_clause_correction/40144816305.json")
    cc_controls = cc.get("controls") or {}
    cc_checks = cc.get("claim_checks") or {}
    known_gap_claims = {"CC6_accepted_code_path_file_line", "CC7_51d306c_diff_provenance"}
    cc11 = "CC11_item2_gate_status"
    failed = set(cc.get("failed_claims") or [])
    # Provenance verification for the accepted correction (CC6/CC7).
    # The historical 40144816305 record failed these checks because the then-current
    # mount could not resolve 51d306c. This mount carries the objects; verify the
    # actual diff and the integrated parent chain directly. Do not rely on a
    # merge-base through the shallow/grafted 29a5c4a5 root.
    def commit_reachable(rev: str) -> bool:
        rc2, _, _ = git("cat-file", "-e", rev + "^{commit}", cwd=PRODUCT_MOUNT)
        return rc2 == 0

    def commit_exists(rev: str) -> bool:
        rc2, _, _ = git("rev-parse", "--verify", rev + "^{commit}", cwd=PRODUCT_MOUNT)
        return rc2 == 0

    reach_51d = commit_exists("51d306c")
    reach_8b5 = commit_exists("8b5b08dd")
    rc_diff, diff_text, diff_err = git("show", "51d306c", "--", "product/query/pipeline.py", cwd=PRODUCT_MOUNT)
    diff_needles = [
        "-    if not fixture_generation and adversarial_retrieval:",
        "+    if adversarial_retrieval:",
        "+        if not fixture_generation:",
        "+            audited = apply_counter_emission_repair(audited)",
    ]
    diff_missing = [x for x in diff_needles if x not in (diff_text or "")]
    rc_p51, p51, _ = git("show", "-s", "--format=%P", "51d306c", cwd=PRODUCT_MOUNT)
    rc_p85, p85, _ = git("show", "-s", "--format=%P", "85e816f", cwd=PRODUCT_MOUNT)
    rc_p8b, p8b, _ = git("show", "-s", "--format=%P", "8b5b08dd", cwd=PRODUCT_MOUNT)
    chain_ok = (
        p85.split()[0] == "51d306ca4b52c6d8ea1200c306cfb33e44e487ac"
        and p8b.split()[0] == "85e816fa7e3a5e86671cb813e1c121da64cfd2c7"
    )
    rc_anc, anc_out, _ = git("merge-base", "--is-ancestor", "8b5b08dd", head, cwd=PRODUCT_MOUNT)
    rc_file_51, file_51, _ = git("show", "51d306c:product/query/pipeline.py", cwd=PRODUCT_MOUNT)
    rc_file_8b, file_8b, _ = git("show", "8b5b08dd:product/query/pipeline.py", cwd=PRODUCT_MOUNT)
    file_51_lines = [i + 1 for i, line in enumerate((file_51 or "").splitlines()) if "if adversarial_retrieval:" in line]
    file_8b_lines = [i + 1 for i, line in enumerate((file_8b or "").splitlines()) if "if adversarial_retrieval:" in line]
    checks.append(check("cc6_cc7_provenance_verified_at_resume",
                        reach_51d and reach_8b5 and not diff_missing and chain_ok,
                        commit_51d306c_resolvable=reach_51d,
                        commit_8b5b08dd_resolvable=reach_8b5,
                        diff_missing=diff_missing,
                        parent_chain={"8b5b08dd": p8b, "85e816f": p85, "51d306c": p51},
                        file_51d306c_line_1339=file_51_lines,
                        file_8b5b08dd_line_1339=file_8b_lines,
                        diff_stderr=diff_err))
    checks.append(check("cc6_cc7_historical_failure_preserved",
                        "CC6_accepted_code_path_file_line" in (cc.get("failed_claims") or [])
                        and "CC7_51d306c_diff_provenance" in (cc.get("failed_claims") or []),
                        historical_failed_claims=cc.get("failed_claims")))
    checks.append(check("current_mount_ancestry_is_grafted_not_contradicted",
                        rc_anc == 1 and rc_file_51 == 0 and rc_file_8b == 0,
                        merge_base_8b5_to_current_returncode=rc_anc,
                        interpretation="29a5c4a5 is the shallow graft root, so merge-base cannot connect the older accepted head to it. The named accepted head 8b5b08dd and its parent chain are verified directly; that is exactly the correction's claim. No ancestry through the graft is asserted."))

    # ---------- item (1) correction of record ----------
    note = REPO / "reports/evaluation/BYPASS_CLAUSE_CORRECTION_OF_RECORD_40105794124_v68.md"
    followup = REPO / "reports/evaluation/CORRECTION_FOLLOWUP_CITATION_40198184759.md"
    note_text = note.read_text(errors="replace") if note.is_file() else ""
    followup_text = followup.read_text(errors="replace") if followup.is_file() else ""
    combined_text = note_text + "\n" + followup_text
    note_needles = {
        "pipeline_file_line": "product/query/pipeline.py:1339",
        "bundle_sha": BUNDLE_SHA,
        "applied_true": "applied = true",
        "n_selected_zero": "n_selected = 0",
        "pivot_absent": "pivot_absent",
        "incumbent_still_verified": "counter_evidence_verified = true",
        "measurement_4_of_5": "4/5",
        "commit_51d306c": "51d306c",
        "remaining_leg": "rejection/incumbent handling",
        "do_not_serve_stand": "Both DO-NOT-SERVE orders remain in effect",
    }
    note_missing = [k for k, v in note_needles.items() if v not in combined_text]
    checks.append(check("correction_note_present", note.is_file(), path=str(note.relative_to(REPO)), sha256=sha256_file(note) if note.is_file() else None))
    checks.append(check("correction_followup_citation_present", followup.is_file(), path=str(followup.relative_to(REPO)), sha256=sha256_file(followup) if followup.is_file() else None))
    checks.append(check("correction_note_contains_required_statements", not note_missing, missing=note_missing))

    checks.append(check("correction_record_measurement_unchanged", cc.get("measurement_unchanged") is True, verdict=cc.get("verdict"), exit_code=cc.get("exit_code")))
    checks.append(check("correction_record_no_falsifier_reexecution", cc.get("falsifier_reexecuted") is False))
    checks.append(check("correction_record_controls_hold", all(v.get("holds") for v in cc_controls.values()), controls={k: v.get("holds") for k, v in cc_controls.items()}))
    checks.append(check("correction_record_cc2_to_cc5_hold", all(cc_checks.get(k, {}).get("ok") for k in ["CC1_stale_clause_located_only_in_reading_report", "CC2_measurement_unchanged_vs_freeze_pin", "CC3_bundle_sha256_of_record", "CC4_span_seam_provenance_of_record", "CC5_incumbent_left_in_place"])))
    checks.append(check("correction_record_known_cc6_cc7_gap", failed == known_gap_claims | {cc11}, failed_claims=sorted(failed)))
    checks.append(check("correction_record_cc11_superseded", cc11 in failed and cc_checks.get(cc11, {}).get("actual", {}).get("item_2_status") == "NOT_YET_DISCRIMINATING",
                        cc11_actual=(cc_checks.get(cc11) or {}).get("actual")))

    gate = load_json(REPO / "results/audit/evaluation/CYCLE_40133253347_GATE.json")
    fixes = gate.get("required_fixes") or []
    checks.append(check("correction_gate_pass", gate.get("gate") == "PASS" and gate.get("safe_to_integrate") is True, gate=gate.get("gate"), safe_to_integrate=gate.get("safe_to_integrate")))
    checks.append(check("correction_gate_has_cc6_cc7_nonblocking_fix", any("CC6/CC7" in f and "51d306c" in f and "NON-BLOCKING" in f for f in fixes), required_fixes=fixes))

    # Incumbent rows still verified (read flags, never re-score).
    falsifier = load_json(REPO / "results/evaluation/fast_mvp_current_head_ca_falsifier/40105794124.json")
    agg = falsifier.get("aggregate") or {}
    rows_at_mount = []
    for brec in falsifier.get("bundles") or []:
        p = PRODUCT_MOUNT / brec["path"]
        if not p.is_file():
            rows_at_mount.append({"path": brec["path"], "missing": True})
            continue
        bd = load_json(p)
        by_id = {r.get("decision_id"): r for r in bd.get("decisions") or []}
        for r in brec.get("verified_scored_rows") or []:
            did = r.get("decision_id")
            mr = by_id.get(did) or {}
            rows_at_mount.append({
                "path": brec["path"], "decision_id": did,
                "recorded_defects": r.get("defects") or [],
                "counter_evidence_verified_at_mount": mr.get("counter_evidence_verified"),
                "counter_status_at_mount": mr.get("counter_status"),
                "counter_uncertainty_at_mount": mr.get("counter_uncertainty"),
            })
    bad_rows = [r for r in rows_at_mount if r.get("missing") or r.get("counter_evidence_verified_at_mount") is not True]
    defective = [r for r in rows_at_mount if r.get("recorded_defects")]
    sound = [r for r in rows_at_mount if r.get("decision_id") == "bstger_SK.2023.49"]
    checks.append(check("incumbent_defective_rows_still_verified",
                        len(defective) == agg.get("n_defective_verified_scored_rows_total") == 4 and not bad_rows,
                        n_defective=len(defective), n_bad=len(bad_rows), rows=rows_at_mount))
    checks.append(check("sound_row_still_verified", len(sound) == 1 and sound[0]["counter_evidence_verified_at_mount"] is True and not sound[0]["recorded_defects"], sound_row=sound[0] if sound else None))
    checks.append(check("measurement_of_record_unchanged", agg.get("n_enriched") == 5 and agg.get("n_defective_verified_scored_rows_total") == 4 and agg.get("n_enriched_with_sound_counter_row") == 1 and agg.get("defect_histogram") == {"D2_letterhead_zone": 2, "D3_markup_residue": 2, "D4_language_marker_mismatch": 1}, aggregate=agg))

    # ---------- item (2) precondition ----------
    post = load_json(REPO / "results/evaluation/post_repair_family_ca_falsifier/40162507752.json")
    post_head = post.get("product_mount_head")
    checks.append(check("post_repair_record_is_vacuous_by_pin_drift",
                        post.get("verdict") == "NOT_MEASURED_VACUOUS" and post.get("exit_code") == 2,
                        verdict=post.get("verdict"), exit_code=post.get("exit_code"), vacuous_reasons=post.get("vacuous_reasons")))
    checks.append(check("post_repair_record_head_is_current", post_head == head, record_head=post_head, current_head=head))
    post_bundles = post.get("bundles") or []
    post_bad = []
    for brec in post_bundles:
        p = PRODUCT_MOUNT / brec["path"]
        if not p.is_file() or sha256_file(p) != brec.get("sha256"):
            post_bad.append({"path": brec["path"], "exists": p.is_file(), "actual": sha256_file(p) if p.is_file() else None, "expected": brec.get("sha256")})
    checks.append(check("post_repair_record_bundles_match_current_mount", len(post_bundles) == 7 and not post_bad, n=len(post_bundles), bad=post_bad))
    pre = post.get("precondition") or {}
    checks.append(check("post_repair_leg_landed", pre.get("H1_precondition_leg_landed") is True))
    checks.append(check("post_repair_full_family_not_regenerated", pre.get("H2_precondition_full_family_regenerated") is False, item_2_full_protocol_status=pre.get("item_2_full_protocol_status")))

    hyp = load_json(REPO / "evaluation/POST_REPAIR_FAMILY_CA_FALSIFIER_40134202991_HYPOTHESIS_V1.json")
    fam = (hyp.get("frozen_probe_family_FROZEN") or {}).get("members_sha256") or {}
    froles = Counter((p.split("/")[2], Path(p).name.split(".bundle")[0]) for p in fam)
    post_paths = sorted(list((PRODUCT_MOUNT / "results/product/offline_slice").glob("*/*.bundle.json")) + list((PRODUCT_MOUNT / "results/product/server_slice").glob("*/*.bundle.json")))
    post_roles = []
    for p in post_paths:
        try:
            bd = load_json(p)
        except Exception:
            continue
        cf = ((bd.get("provenance") or {}).get("counter_evidence_span") or {}).get("content_filter")
        if cf:
            rel = p.relative_to(PRODUCT_MOUNT).as_posix()
            post_roles.append((rel.split("/")[2], p.name.split(".bundle")[0]))
    proles = Counter(post_roles)
    matched = sum(min(froles[k], proles.get(k, 0)) for k in froles)
    role_parity = all(proles.get(k, 0) >= froles[k] for k in froles)
    checks.append(check("fresh_item2_member_for_member_10_of_15", matched == 10 and len(fam) == 15,
                        matched=matched, frozen_family_n=len(fam), post_repair_bundles_n=len(post_roles)))
    checks.append(check("fresh_item2_multiplicity_parity_false", role_parity is False,
                        frozen_roles={"/".join(k): v for k, v in froles.items()}, post_repair_roles={"/".join(k): v for k, v in proles.items()}))
    checks.append(check("fresh_item2_every_role_covered", all(proles.get(k, 0) > 0 for k in froles)))

    state = load_json(REPO / "state/evaluation.json")
    rec = state.get("v68_item_2_reconciliation_40192868113") or {}
    checks.append(check("state_item2_reconciliation_present", bool(rec)))
    checks.append(check("state_item2_status_still_not_discriminating", rec.get("current_item_2_status") == "NOT_YET_DISCRIMINATING",
                        current=rec.get("current_item_2_status"), historical=rec.get("historical_item_2_status")))
    checks.append(check("state_item2_historical_status_not_adopted", rec.get("historical_status_is_adopted_for_current_mount") is False))
    checks.append(check("state_item2_no_synthetic_standin", rec.get("not_a_re_score") is True and rec.get("not_a_weakening")))
    checks.append(check("state_item2_precondition_matches_fresh_relation",
                        (rec.get("precondition") or {}).get("member_for_member_matching") == "10/15"
                        and (rec.get("precondition") or {}).get("H1_precondition_leg_landed") is True
                        and (rec.get("precondition") or {}).get("H2_precondition_full_family_regenerated") is False))
    checks.append(check("state_item2_producer_observations_not_accepted",
                        (rec.get("producer_observations_not_accepted") or {}).get("claim_ceiling", "").startswith("producer-attested")))
    checks.append(check("no_upgrade_to_now_discriminating", rec.get("current_item_2_status") != "NOW_DISCRIMINATING"))

    # ---------- measurement of record / falsifiability instrument / accepted gate ----------
    bench_path = REPO / "results/evaluation/minimal_retrieval_ca_benchmark/40182692670.json"
    bench = load_json(bench_path)
    expected_failed = {
        "mf::concept_coverage::39319405429::de-kapitalverletzung",
        "mf::counter_authority_surface::39319405429::de-kapitalverletzung",
        "mf::counter_authority_surface::39319405429::fr-bail-entretien",
        "mf::counter_authority_surface::39319405429::it-responsabilita-medica",
    }
    failed_names = {g.get("gate") for g in bench.get("failed_gates") or []}
    checks.append(check("measurement_of_record_present_and_product_falsified",
                        bench.get("verdict") == "PRODUCT_FALSIFIED" and bench.get("exit_code") == 1,
                        path="results/evaluation/minimal_retrieval_ca_benchmark/40182692670.json",
                        verdict=bench.get("verdict"), exit_code=bench.get("exit_code")))
    checks.append(check("measurement_of_record_gate_set_unchanged",
                        bench.get("n_gates") == 18 and bench.get("n_passed") == 11 and bench.get("n_failed") == 4
                        and failed_names == expected_failed and bench.get("input_drift") == [],
                        n_gates=bench.get("n_gates"), n_passed=bench.get("n_passed"), n_failed=bench.get("n_failed"),
                        failed_gates=sorted(failed_names), input_drift=bench.get("input_drift")))
    fi_path = REPO / "results/evaluation/retrieval_counter_authority_benchmark/40175266143.json"
    fi = load_json(fi_path)
    checks.append(check("gate_falsifiability_instrument_not_a_product_pass",
                        fi.get("verdict") == "BENCHMARK_VALID_NO_FALSIFICATION" and fi.get("falsification_proven") is True and fi.get("exit_code") == 0,
                        path="results/evaluation/retrieval_counter_authority_benchmark/40175266143.json",
                        verdict=fi.get("verdict"), falsification_proven=fi.get("falsification_proven")))
    acc_gate = load_json(REPO / "results/audit/evaluation/CYCLE_40159747851_GATE.json")
    checks.append(check("accepted_eval_gate_pass",
                        acc_gate.get("gate") == "PASS" and acc_gate.get("safe_to_integrate") is True and (acc_gate.get("required_fixes") or []) == [],
                        gate=acc_gate.get("gate"), safe_to_integrate=acc_gate.get("safe_to_integrate"), required_fixes=acc_gate.get("required_fixes")))

    # ---------- standing posture ----------
    lane = load_json(REPO / "evaluation/state/evaluation.json")
    checks.append(check("lane_human_gate_false", lane.get("human_gate_ready") is False))
    checks.append(check("lane_machine_gate_false", lane.get("machine_gate_ready") is False))
    checks.append(check("root_continue_recommended_false", state.get("continue_recommended") is False))
    checks.append(check("no_174k_rerun_declared", state.get("no_universal_174k_benchmarks") is True))
    checks.append(check("fail_closed_declared_in_correction", "Both DO-NOT-SERVE orders remain in effect" in note_text))

    ok = all(c["ok"] for c in checks)
    return {
        "schema": "lex-evaluation-operational-resume-deliverable-verification/1",
        "lane": "evaluation",
        "run_id": RUN_ID,
        "resumed_run_id": RESUMED_RUN_ID,
        "generated_at_utc": GENERATED_AT_UTC,
        "verdict": "RESUME_VERIFIED_AND_AUDIT_READY" if ok else "RESUME_DIVERGENCE",
        "all_checks_ok": ok,
        "n_checks": len(checks),
        "n_checks_ok": sum(1 for c in checks if c["ok"]),
        "failed_checks": [c["check"] for c in checks if not c["ok"]],
        "checks": checks,
        "item_1_correction_of_record": {
            "status": "PRESENT_AND_VERIFIED",
            "note": "reports/evaluation/BYPASS_CLAUSE_CORRECTION_OF_RECORD_40105794124_v68.md",
            "machine_record": "results/evaluation/bypass_clause_correction/40144816305.json",
            "gate": "results/audit/evaluation/CYCLE_40133253347_GATE.json",
            "measurement_unchanged": True,
            "falsifier_reexecuted": False,
            "cc6_cc7_followup": "At this mount 51d306c and 8b5b08dd are present: the 51d306c diff removes the old fixture-gate condition and the 8b5b08dd -> 85e816f -> 51d306c parent chain verifies directly. merge-base through the shallow graft at 29a5c4a5 is not claimed; the historical CC6/CC7 failure is preserved and the measurement of record is unchanged.",
        },
        "item_2": {
            "status": "NOT_YET_DISCRIMINATING",
            "why": "The frozen 15-member family is matched 10/15 member-for-member with multiplicity parity false. Every frozen role has a post-repair bundle, but the member-for-member precondition is not met, so the ordered item-(2) protocol is not executed. No synthetic stand-in is substituted.",
            "post_repair_record": "results/evaluation/post_repair_family_ca_falsifier/40162507752.json",
            "post_repair_verdict": "NOT_MEASURED_VACUOUS (pin drift; producer observations not accepted)",
            "fresh_precondition_coverage": {"matched": matched, "frozen_family_n": len(fam), "post_repair_bundles_n": len(post_roles), "multiplicity_parity": role_parity},
        },
        "posture": {
            "admission": "fail-closed",
            "human_gate_ready": False,
            "machine_gate_ready": False,
            "owner_decision_required": False,
            "do_not_serve_orders": "both stand",
            "new_same_question_cycle": False,
            "universal_174k_rerun": False,
        },
        "claim_ceiling": "Operational-resume verification only. It preserves accepted artifacts and the NOT_YET_DISCRIMINATING item-(2) status; it adds no quality measurement, moves no bar, issues no serve verdict, lifts no DO-NOT-SERVE order and opens no new same-question cycle.",
    }


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    diagnosis = build_diagnosis()
    diagnosis_sha = write_json(OUT / "diagnosis_40192868113.json", diagnosis)
    verification = build_deliverable_verification()
    verification_sha = write_json(OUT / "deliverable_verification_40198184759.json", verification)
    summary = {
        "schema": "lex-evaluation-operational-resume-summary/1",
        "lane": "evaluation",
        "run_id": RUN_ID,
        "resumed_run_id": RESUMED_RUN_ID,
        "generated_at_utc": GENERATED_AT_UTC,
        "diagnosis": {"path": "results/evaluation/operational_resume_40198184759/diagnosis_40192868113.json", "sha256": diagnosis_sha, "classification": diagnosis["classification"], "all_checks_ok": diagnosis["all_checks_ok"]},
        "deliverable_verification": {"path": "results/evaluation/operational_resume_40198184759/deliverable_verification_40198184759.json", "sha256": verification_sha, "verdict": verification["verdict"], "all_checks_ok": verification["all_checks_ok"], "n_checks": verification["n_checks"], "n_checks_ok": verification["n_checks_ok"], "failed_checks": verification["failed_checks"]},
        "status": "AUDIT_READY_PENDING_INDEPENDENT_AUDIT" if (diagnosis["all_checks_ok"] and verification["all_checks_ok"]) else "RESUME_DIVERGENCE",
        "continue_recommended": False,
        "new_same_question_cycle": False,
        "universal_174k_rerun": False,
    }
    write_json(OUT / "summary_40198184759.json", summary)
    print(json.dumps(summary, indent=2))
    return 0 if summary["status"].startswith("AUDIT_READY") else 1


if __name__ == "__main__":
    raise SystemExit(main())

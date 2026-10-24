#!/usr/bin/env python3
"""Operational-resume state repair for run 40096174340 (resume of 40094203248).

This run's producer snapshot is byte-identical to 367119e3 (zero durable
producer delta): 'Run lane cycle' was killed after ~2704s (~LEX_AGENT_QUANTUM),
steps 7 and 9 were skipped, and 'Persist team snapshot' force-pushed the
unchanged tree. The snapshot CARRIES the complete v67 item-(1) deliverable
inherited from run 40089391202 (the freeze-first D2 letterhead pattern
heterogeneity profile). This script makes the snapshot audit-ready by:
  - recording the orchestration failure diagnosis and reproduction verification,
  - advancing the run identity with full disclosure (append-only),
  - appending verification evidence refs,
  - updating the nested-refs guard expectations if needed (it already passes),
  - stating that item (2) remains NOT_YET_DISCRIMINATING (product not landed),
without inventing measurements, without overwriting 40089391202.json or
40094203248.json, and without editing the frozen instrument or any bar/rubric.
"""
import json, hashlib
from datetime import datetime, timezone
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
STATE = _REPO_ROOT / "state" / "evaluation.json"
RUN="40096174340"; RESUMED="40094203248"; DELIV="40089391202"

NEW_REFS = [
 f"evaluation/OPERATIONAL_RESUME_{RUN}_HYPOTHESIS_V1.json",
 f"evaluation/OPERATIONAL_RESUME_{RUN}_FREEZE_V1.json",
 f"evaluation/OPERATIONAL_RESUME_{RUN}_FREEZE_V1_ADDENDUM_FIELD_COUNT.json",
 "evaluation/operational_resume_40096174340_state_repair.py",
 f"results/evaluation/d2_letterhead_pattern_profile/{RUN}.json",
 f"reports/evaluation/D2_LETTERHEAD_PATTERN_PROFILE_{RUN}.md",
 f"results/evaluation/d2_letterhead_pattern_profile/{RUN}_reproduction_check_vs_{DELIV}.json",
 "results/evaluation/orchestration/40096174340_rest_jobs.json",
 f"reports/evaluation/OPERATIONAL_RESUME_{RUN}.md",
]

def _sha256_file(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main():
    state = json.loads(STATE.read_text(encoding="utf-8"))
    repairs=[]
    # run identity history disclosure (append-only)
    state.setdefault("run_identity_history",[])
    if state.get("github_run")=="40094203248":
        state["run_identity_history"].append({
            "run_id":"40094203248","role":"operational resume of 40089391202; reproduction-verified item-(1); finished phantom role-note keys",
            "chain_outcome":"producer+resume landed; NOT ACCEPTED; orchestration of 40089391202 already diagnosed",
        })
    state["github_run"]=RUN
    state["operational_resume_of"]=RESUMED
    state["inherited_deliverable_of_record"]=DELIV
    repairs.append(f"R1: run identity advanced to operational-resume run {RUN} (resume of {RESUMED}); {DELIV}.json remains item-(1) deliverable of record; zero-durable-delta producer snapshot (team commit 367119e3) preserved intact.")

    repro=json.loads((_REPO_ROOT/f"results/evaluation/d2_letterhead_pattern_profile/{RUN}_reproduction_check_vs_{DELIV}.json").read_text())
    assert repro["verdict"]=="REPRODUCES" and repro["n_mismatches"]==0
    assert repro["n_discrimination_fields_compared"]>=18
    assert repro["controls_all_pass"] is True

    state["operational_resume_40096174340"]={
     "resumed_producer_run":RESUMED,
     "inherited_deliverable_run":DELIV,
     "producer_snapshot_commit":"367119e3f9f33f44d5907d7602bad4602250057d",
     "producer_snapshot_byte_identical_to_prior":True,
     "diagnosis":{
      "team_job":"failed at step 6 'Run lane cycle' after 2704s (2026-10-24T12:59:46Z-13:44:50Z); steps 7 'Validate active MVP producer state' and 9 'Enforce lane write scope' skipped; step 10 'Persist team snapshot' succeeded (always()) force-pushing unchanged tree",
      "audit_job":"skipped (needs team success)",
      "integrate_job":"skipped",
      "resilience_job":"success dispatched this resume (core-lane.yml resilience logic) - see results/evaluation/orchestration/40096174340_rest_jobs.json",
      "rc_inference":"timing-based inference to LEX_WORK_QUANTUM_EXPIRED (rc 78) ~2700s quantum + kill/cleanup is HEDGED because unauthenticated logs are 403; other rc classes cannot be excluded. ORCHESTRATION class per requirement 20.",
      "gate_exists":False,
      "audit_branch_exists":False,
      "acceptance_status":"NOT ACCEPTED (requirement 4)"
     },
     "work_preserved":"Inherited complete v67 item-(1) D2 letterhead pattern heterogeneity profile from 40089391202 (LETTERHEAD_PATTERNS_MECHANICALLY_DETECTED, 93 pinned bundles, 41 D2 rows -> 2 distinct P1 patterns, controls C3-C6 all pass, baseline 40062917685 unmoved). Prior resume 40094203248 verification retained.",
     "verification_this_run":{
      "reproduction_check":f"Fresh re-execution of byte-identical frozen instrument (sha aac86527...) under run {RUN}: REPRODUCES — 19/19 discrimination fields identical to 40089391202.json, 0 mismatches vs deliverable and 0 vs 40094203248, controls C3-C6 all pass; JSON byte-identity NOT claimed (requirement 30). Artifact: results/evaluation/d2_letterhead_pattern_profile/{RUN}_reproduction_check_vs_{DELIV}.json",
      "product_p0_reverified_this_run":"origin/lab/product head e2270c37 still bypasses filter on fixture path (offline_slice.py:79 retrieval_mode='fixture', fixture_generation=True; pipeline.py:1339 if not fixture_generation and adversarial_retrieval). v67 item (2) stays NOT_YET_DISCRIMINATING; no synthetic stand-in; standing falsification record not re-run."
     },
     "repairs_applied":repairs,
     "claim_ceiling":"Operational-resume disclosure only: zero-durable-delta producer snapshot diagnosed and verified; inherited deliverable reproduction-checked; no product/bar/serve claim. Both DO-NOT-SERVE orders stand; admission fail-closed."
    }

    refs=state.setdefault("evidence_refs",[])
    for r in NEW_REFS:
        if r not in refs: refs.append(r)
    state["evidence_refs_n"]=len(refs)
    repairs.append(f"R2: appended {len(NEW_REFS)} verification refs; evidence_refs_n={state['evidence_refs_n']}")

    state["operational_resume_40096174340"]["repairs_applied"]=repairs
    state["cycle_status"]="COMPLETE"
    state["evidence_tier"]="REPRODUCED"
    state["acceptance_status"]="PROPOSED_PENDING_INDEPENDENT_AUDIT"
    for f in ("human_gate_ready","machine_gate_ready","packet_admitted","ready_for_owner_session","owner_decision_required"):
        state[f]=False
    state["continue_recommended"]=False
    state["continue_recommended_reason"]=(
        "v67 ordered work is FULLY discharged with accepted/preserved evidence: item (1) inherited from 40089391202 and reproduction-verified under 40094203248 and again under 40096174340 (19/19 discrimination fields identical); item (2) blocked on product not yet landing the dual P0 fix (re-verified this run, NOT_YET_DISCRIMINATING); items (3)/(4) standing. Zero-durable-delta orchestration failure of 40096174340 diagnosed and snapshot made audit-ready; do not restart from scratch."
    )
    state["next_recommendation"]=(
        "NOT_YET_DISCRIMINATING (item (2) blocked on product): Core Product must land letterhead detector fix for the two profiled P1 offset-0 multi-line court-header patterns AND route the offline/slice path through the filter (fixture_generation bypass prevents execution). Re-run the frozen item-(2) post-repair re-measure + d2_path_scope_probe on that head. The v67 item-(1) profile is reproduction-verified and available as Core Product input. Do not re-run item (1); do not re-score packet 39319405429."
    )
    state["state_updated_at"]=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    state["state_updated_by"]="operational_resume_40096174340"
    STATE.write_text(json.dumps(state,indent=1,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps({"state_sha256":_sha256_file(STATE),"github_run":state["github_run"],"evidence_refs_n":state["evidence_refs_n"],"continue_recommended":state["continue_recommended"]},indent=1))
    return 0

if __name__=="__main__":
    raise SystemExit(main())

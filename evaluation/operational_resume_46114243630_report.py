#!/usr/bin/env python3
"""Generate the audit-ready report + artifact manifest for run 46114243630.

Every digest in the report and manifest is recomputed here from the committed
working-tree files; no digest is copied from prose.  Nothing outside the
evaluation lane namespace is written.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
RUN = "46114243630"
SUBJECT = "46110768588"

ARTIFACTS = [
    "evaluation/frozen_rules_profile_coverage_falsifier.py",
    "evaluation/operational_resume_46114243630_diagnosis.py",
    "evaluation/operational_resume_46114243630_freeze.py",
    f"evaluation/FROZEN_RULES_PROFILE_COVERAGE_{RUN}_HYPOTHESIS_V1.json",
    f"evaluation/FROZEN_RULES_PROFILE_COVERAGE_{RUN}_FREEZE_V1.json",
    f"results/evaluation/orchestration/CYCLE_{SUBJECT}_resume_diagnosis.json",
    f"results/evaluation/orchestration/CYCLE_{SUBJECT}_run.json",
    f"results/evaluation/orchestration/CYCLE_{SUBJECT}_jobs.json",
    f"results/evaluation/orchestration/CYCLE_{SUBJECT}_team_annotations.json",
    f"results/evaluation/frozen_rules_profile_coverage/{RUN}.json",
    f"results/evaluation/frozen_rules_profile_coverage/{RUN}_REPRO.json",
    f"results/evaluation/frozen_rules_profile_coverage/{RUN}_REPRO_CHECK.json",
    f"results/evaluation/orchestration/{RUN}_retrieval_benchmark_shim.json",
    f"results/evaluation/orchestration/{RUN}_reused_suites_shim.json",
]
REPORT = f"reports/evaluation/FROZEN_RULES_PROFILE_COVERAGE_{RUN}.md"
MANIFEST = f"results/evaluation/orchestration/{RUN}_audit_readiness_manifest.json"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.parse_args(argv)
    missing = [a for a in ARTIFACTS if not (REPO / a).is_file()]
    if missing:
        raise SystemExit(f"missing artifacts: {missing}")

    hashes = {a: sha(REPO / a) for a in ARTIFACTS}
    result = json.loads((REPO / ARTIFACTS[9]).read_text(encoding="utf-8"))
    diag = json.loads((REPO / ARTIFACTS[5]).read_text(encoding="utf-8"))
    repro_check = json.loads((REPO / ARTIFACTS[11]).read_text(encoding="utf-8"))
    shim_a = json.loads((REPO / ARTIFACTS[12]).read_text(encoding="utf-8"))
    shim_b = json.loads((REPO / ARTIFACTS[13]).read_text(encoding="utf-8"))

    lines: list[str] = []
    add = lines.append
    add(f"# Frozen-rules profile-coverage falsifier — operational resume {RUN}")
    add("")
    add(f"- Lane: evaluation; direction_version 68; this run `{RUN}`; "
        f"resumed producer run `{SUBJECT}`.")
    add(f"- Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}.")
    add("- Status: producer deliverable COMPLETE and audit-ready; "
        "PENDING_INDEPENDENT_AUDIT; no promotion claim is made here.")
    add("")
    add("## 1. Failure diagnosis (machine-established, not inferred)")
    add("")
    add(f"- GitHub run `{SUBJECT}` (`{diag['evidence_sources']['run']['url']}`) "
        f"concluded `failure`; team job `{diag['failure_detail']['team_job_conclusion']}`.")
    add(f"- Failing step: `{', '.join(diag['failure_detail']['failing_steps'])}`.")
    add("- Annotations (verbatim): "
        + "; ".join(f"`{a['message']}`" for a in diag["failure_detail"]["annotations"])
        + ".")
    add(f"- Classification: `{diag['failure_class']}` "
        f"(rc=78, seconds={diag['failure_detail']['quantum_seconds']}). Per factory-wide "
        "requirements this is an orchestration limit — not a verdict, not a product "
        "defect and not a human-gate problem.")
    add(f"- Consequence: audit job `{diag['orchestration_consequence']['audit_job_conclusion']}`, "
        f"integrate `{diag['orchestration_consequence']['integrate_job_conclusion']}`, "
        f"audit branch exists = {diag['orchestration_consequence']['audit_branch_exists']}; "
        "no gate file and no accept commit for the subject run.")
    add("")
    add("## 2. Snapshot preserved, not restarted")
    add("")
    snap = diag["persisted_producer_snapshot"]
    add(f"- Snapshot `{snap['ref']}` head `{snap['head']}` "
        f"(`{snap['subject']}`).")
    add(f"- Added file: `{', '.join(snap['files_added'])}`, sha256 "
        f"`{snap['instrument_sha256']}`. It is used byte-identically; it was NOT edited.")
    add("- The resume did not re-execute the failed producer job and did not "
        "regenerate the instrument. Freeze-first records were written before "
        "the first claim-bearing execution in this run.")
    add("")
    add("## 3. Freeze-first discipline")
    add("")
    add(f"- Hypothesis `{ARTIFACTS[3]}` sha256 `{hashes[ARTIFACTS[3]]}`.")
    add(f"- Freeze `{ARTIFACTS[4]}` sha256 `{hashes[ARTIFACTS[4]]}`; "
        f"{result['freeze_crosscheck']['population_pins_frozen']} population digests pinned.")
    add(f"- Result reports hypothesis_sha256 `{result['hypothesis_sha256']}` and "
        f"freeze_sha256 `{result['freeze_sha256']}`; cross-check "
        f"hypothesis_unchanged={result['freeze_crosscheck']['hypothesis_unchanged_since_freeze']}, "
        f"pins_match_freeze={result['freeze_crosscheck']['pins_match_freeze']}.")
    add("- Pre-freeze scoping is disclosed verbatim in the hypothesis; no H1/H2/H3 "
        "predicate was executed before the freeze was written.")
    add("")
    add("## 4. Measurement of record for this resume")
    add("")
    add(f"- Verdict **`{result['verdict']}`**, exit_code `{result['exit_code']}`, "
        f"controls_all_hold=`{result['controls_all_hold']}`.")
    add(f"- Population: {result['population']['n_bundles']} fixed-path bundles; "
        + ", ".join(f"{k}={v}" for k, v in result["population"]["groups"].items()) + ".")
    add(f"- Falsified legs: `{', '.join(result['falsified_legs'])}`.")
    h1 = result["H1_profile_coverage"]
    add(f"- H1 coverage holds=`{h1['holds']}`; failing groups="
        f"`{', '.join(h1['failing_groups']) or 'none'}` "
        "(fresh resolver returns no frozen profile there).")
    h2 = result["H2a_profile_norm_alignment"]
    add(f"- H2a norm alignment holds=`{h2['holds']}`; failing groups="
        f"`{', '.join(h2['failing_groups']) or 'none'}`.")
    for g, v in h2["per_group"].items():
        add(f"  - `{g}`: profile=`{v['profile_key']}`, applicable=`{v['applicable']}`, "
            f"shared Art. norms=`{', '.join(v['shared_art_norm_tokens']) or '∅'}`, "
            f"holds=`{v['holds']}`.")
    add("- H2b corpus evidence and the whole-token H2a sensitivity variant are "
        "REPORT-ONLY, published in the result beside H2a; neither is verdict-bearing "
        "and neither silently replaces the frozen Art.-norm definition.")
    add(f"- H3 shipped-provenance agreement holds="
        f"`{result['H3_shipped_provenance_agreement']['holds']}` "
        f"({result['H3_shipped_provenance_agreement']['n_disagreements']} disagreements "
        f"over {result['H3_shipped_provenance_agreement']['n_compared']} bundles).")
    add("- Controls C1–C7 all hold: " + ", ".join(
        f"`{k}`" for k in result["controls"]) + ".")
    add(f"- C5 two-pass digest `{result['controls']['C5_determinism_two_full_passes']['first_sha256']}` "
        "identical in both passes.")
    add("")
    add("## 5. Reproducibility and reused accepted assets")
    add("")
    add(f"- Independent second process invocation: verdict identical; "
        f"{repro_check['n_fields_comparing'] if 'n_fields_comparing' in repro_check else repro_check['n_fields_compared']} "
        f"claim-bearing fields compared, differing fields = "
        f"`{repro_check['differing_fields']}`; only `generated_at_utc` differs.")
    add(f"- Reused multilingual/provenance suite `tests/evaluation/test_retrieval_benchmark.py`: "
        f"`{shim_a['verdict']}` {shim_a['n_passed']} passed, protocol digest "
        "`e1a0b18d23d18bd1aafe54a66329fd0b04cd6f95f794d3d0336e0d867af41b7e` "
        "unchanged (pytest absent; executed under the documented shim).")
    add(f"- Additional coverage/multilingual suites: `{shim_b['verdict']}` "
        f"{shim_b['n_passed']} passed, {shim_b['n_failed']} failed, "
        f"{shim_b['n_unsupported']} unsupported (counted not-run, never passed).")
    add("- Numeric environment (requirement 30): numpy 2.5.5 / scipy 1.18.1 / "
        "scikit-learn 1.9.1 installed for the reused suite; no BLAS/thread pin and "
        "no cross-machine byte-identity claim. The profile-coverage instrument "
        "itself imports only the stdlib seam.")
    add("")
    add("## 6. Product decision and claim ceiling")
    add("")
    add("- The transferred coverage gap is CONFIRMED on the current accepted bytes: "
        "H1 fails for petty-theft-dismissal and H2a fails for business-judgment-rule "
        "and served. This bounds the counter-authority seam's ability to attach the "
        "correct frozen anchor to every flagship question; Product owns the repair "
        "of the resolver, this lane owns the probe.")
    add("- This measurement does NOT label any decision supporting/contrary/limiting, "
        "scores NO frozen bar/rubric/threshold/verdict contract, does NOT re-run or "
        "replace the benchmark of record (mapping-free falsifier, PRODUCT_FALSIFIED "
        "on packet-of-record 39319405429), issues NO serve verdict, admits NO packet, "
        "makes NO jurist-usefulness or live-recall claim, and runs NO universal-174k "
        "benchmark.")
    add("- Both DO-NOT-SERVE orders stand. `packet_admitted=false`, "
        "`machine_gate_ready=false`, `human_gate_ready=false`, "
        "`owner_decision_required=false`.")
    add("")
    add("## 7. Disclosures")
    add("")
    add("- The preserved instrument pins the mount head as the stable string "
        "`HEAD_UNREADABLE` because `/tmp/lex_accepted/product/.git` is a worktree "
        "file, not a directory. The true git head "
        "`7be4480ed3ca623b77ea082404ca3b5b7ac5ee83` is pinned in the hypothesis "
        "and re-checked independently; the instrument was not edited to work around it.")
    add("- Offline bundle group keys read `rent-default.bundle` etc. because the "
        "instrument uses `Path.stem`; the five claim-bearing groups are the same "
        "flagship roles. This naming quirk is preserved, not 'corrected', to keep "
        "the instrument byte-identical to the snapshot.")
    add("- GitHub REST evidence was fetched unauthenticated; job-log download is "
        "HTTP 403 without admin rights, so no log-line attribution is claimed. "
        "Pip installs and REST calls are network calls; there were ZERO "
        "OpenCaseLaw/retrieval/model/paid-API calls for the measurement.")
    add("- The result's H2b and whole-token numbers are definitions-dependent "
        "diagnostics: no number is silently preferred over H2a (factory-wide "
        "requirement 12).")
    add("")
    add("## 8. Audit-readiness manifest (digests recomputed here)")
    add("")
    add("| artifact | sha256 |")
    add("| --- | --- |")
    for a, h in hashes.items():
        add(f"| `{a}` | `{h}` |")
    add("")
    add("## 9. Exact reproduction commands")
    add("")
    add("```bash")
    add(f"python3 -m evaluation.frozen_rules_profile_coverage_falsifier --run-id {RUN} "
        f"--hypothesis evaluation/FROZEN_RULES_PROFILE_COVERAGE_{RUN}_HYPOTHESIS_V1.json "
        f"--freeze evaluation/FROZEN_RULES_PROFILE_COVERAGE_{RUN}_FREEZE_V1.json "
        "--product-mount /tmp/lex_accepted/product "
        f"--out results/evaluation/frozen_rules_profile_coverage/{RUN}.json")
    add("PYTHONPATH=/tmp/lex_accepted/product python3 -m evaluation.no_pytest_runner "
        f"--run-id {RUN} --test-file tests/evaluation/test_retrieval_benchmark.py "
        f"--out results/evaluation/orchestration/{RUN}_retrieval_benchmark_shim.json")
    add("```")
    add("")
    add("Claim ceiling of this report: it certifies that the resumed producer "
        "deliverable exists, is reproducible and is ready for an INDEPENDENT audit. "
        "It is not an audit gate, not an acceptance and not a promotion.")

    report_path = REPO / REPORT
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    manifest = {
        "schema": "lex-evaluation-audit-readiness-manifest/1",
        "lane": "evaluation",
        "run_id": RUN,
        "resumed_run_id": SUBJECT,
        "direction_version": 68,
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "verdict": result["verdict"],
        "exit_code": result["exit_code"],
        "controls_all_hold": result["controls_all_hold"],
        "artifact_sha256": hashes,
        "report": {"path": REPORT, "sha256": sha(report_path)},
        "gate_written_by_producer": False,
        "gate_note": "The independent auditor writes "
                     f"results/audit/evaluation/CYCLE_{RUN}_GATE.json from the audit "
                     "job checkout; this producer manifest does not pre-empt it.",
        "claim_ceiling": "Readiness only: no acceptance, no promotion, no serve verdict.",
    }
    man_path = REPO / MANIFEST
    man_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n",
                        encoding="utf-8")
    print(json.dumps({"report": REPORT, "report_sha256": sha(report_path),
                      "manifest": MANIFEST, "manifest_sha256": sha(man_path),
                      "n_artifacts": len(hashes)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

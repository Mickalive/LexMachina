#!/usr/bin/env python3
"""Freeze-first records for the resumed frozen-rules profile-coverage falsifier.

Run 46114243630 (operational resume of 46110768588).  This script WRITES the
hypothesis and freeze JSON files only.  It does not execute the measurement:
the claim-bearing instrument is invoked by a separate command after these files
exist.  Population digests are computed with the instrument's own selectors so
the frozen population is exactly the one the instrument will observe.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
MOUNT = Path("/tmp/lex_accepted/product")
INSTRUMENT = Path("evaluation/frozen_rules_profile_coverage_falsifier.py")
SPEC = Path("evaluation/retrieval_gate/frozen_retrieval_benchmark.json")
RUN_ID = "46114243630"


def sha_b(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def load_instrument():
    spec = importlib.util.spec_from_file_location("lex_cov_falsifier", REPO / INSTRUMENT)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["lex_cov_falsifier"] = mod
    spec.loader.exec_module(mod)
    return mod


def git_head() -> str:
    p = subprocess.run(["git", "-C", str(MOUNT), "rev-parse", "HEAD"],
                       capture_output=True, text=True, timeout=30)
    return p.stdout.strip() if p.returncode == 0 else "UNRESOLVED"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--force", action="store_true",
                    help="refuse by default if files already exist")
    args = ap.parse_args(argv)

    mod = load_instrument()
    hyp_path = REPO / f"evaluation/FROZEN_RULES_PROFILE_COVERAGE_{RUN_ID}_HYPOTHESIS_V1.json"
    freeze_path = REPO / f"evaluation/FROZEN_RULES_PROFILE_COVERAGE_{RUN_ID}_FREEZE_V1.json"
    if not args.force and (hyp_path.exists() or freeze_path.exists()):
        raise SystemExit("freeze files already exist; refusing to overwrite "
                         "(an edited freeze invalidates the run)")

    paths = mod.select_population(MOUNT)
    pop: dict[str, str] = {}
    rel_meta: list[dict[str, Any]] = []
    for p in paths:
        rel = str(p.relative_to(MOUNT))
        pop[rel] = mod.sha256_file(p)
        b = json.loads(p.read_text(encoding="utf-8"))
        span = ((b.get("provenance") or {}).get("counter_evidence_span") or {})
        rel_meta.append({
            "rel_path": rel,
            "group": mod.group_of(p),
            "sha256": pop[rel],
            "recorded_anchor_profile": span.get("anchor_profile"),
            "recorded_applied": span.get("applied"),
        })

    instrument_sha = mod.sha256_file(REPO / INSTRUMENT)
    spec_sha = mod.sha256_file(REPO / SPEC)
    rules_sha = mod.sha256_file(MOUNT / "product/frozen/RULES_LABEL.json")
    seam_sha = mod.sha256_file(MOUNT / "product/query/counter_anchor.py")
    instr_mount_head = mod._mount_head(MOUNT)  # exact value the instrument pins
    true_head = git_head()

    hypothesis: dict[str, Any] = {
        "schema": "lex-evaluation-frozen-rules-profile-coverage-hypothesis/1",
        "lane": "evaluation",
        "run_id": RUN_ID,
        "direction_version": 68,
        "title": "FAST-MVP frozen-rules anchor-profile coverage/norm-alignment "
                 "falsifier on the accepted post-repair flagship family",
        "frozen_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "frozen_before_execution": True,
        "resume_provenance": {
            "resume_run_id": RUN_ID,
            "subject_run_id": "46110768588",
            "subject_failure_class": "LEX_WORK_QUANTUM_EXPIRED (rc=78, seconds=2700)",
            "snapshot_ref": "origin/cycle/core/evaluation/46110768588/team",
            "snapshot_head": "752c3efe335ee847f50961a2230fa7c94a19a574",
            "preserved_instrument": str(INSTRUMENT),
            "instrument_sha256": instrument_sha,
            "note": "The instrument was authored by the failed producer run and "
                    "is preserved byte-identically. No claim-bearing execution "
                    "of it had occurred before this freeze.",
        },
        "fast_mvp_directive": (
            "Smallest executable counter-authority falsifier on committed bytes: "
            "no live retrieval, no model call, no universal-174k benchmark."),
        "why_this_cycle": (
            "Core Product's accepted state (state/product.json item 6, and "
            "reports/product/CYCLE_40272586794.md) DISCLOSED and TRANSFERRED to "
            "evaluation a frozen-rules profile coverage gap: business-judgment-"
            "rule resolves to the domain-mismatched fr-bail-entretien profile and "
            "petty-theft-dismissal resolves to None. Product never re-derives a "
            "profile. This is a concrete evaluation decision: whether the shipped "
            "counter-authority seam can attach the correct frozen anchor to every "
            "flagship question, which bounds counter-authority discovery quality."),
        "product_decision_unlocked": (
            "If coverage or norm alignment is falsified, Product must treat the "
            "anchor-profile resolver as an open defect affecting counter-authority "
            "routing; if both hold and provenance agrees, the transferred coverage "
            "gap is closed on the current accepted bytes."),
        "hypotheses": {
            "H1_profile_coverage": (
                "For every flagship group of the fixed-path regeneration family "
                "(rent-default, business-judgment-rule, corporate-criminal-liability, "
                "petty-theft-dismissal, served), a fresh resolution executed here "
                "through the byte-pinned product seam returns a non-None frozen "
                "anchor profile. Falsified when any group resolves to None."),
            "H2a_profile_norm_alignment": (
                "For each group whose profile resolves and whose frozen pivot "
                "carries a digit-bearing norm token, at least one such token "
                "appears as an 'Art. <token>' citation in that group's OWN query "
                "plus its query_variants. Vacuously true when no digit-bearing "
                "norm pivot exists; H1 separately covers non-resolution."),
            "H2b_corpus_evidence_REPORT_ONLY": (
                "The same intersection over retrieved decision text, plus a "
                "whole-token sensitivity variant of H2a, are reported side by "
                "side with H2a and are NEVER verdict-bearing (two definitions "
                "of 'the query's own norm text' exist; none is silently preferred)."),
            "H3_shipped_provenance_agreement": (
                "Fresh resolution equals provenance.counter_evidence_span."
                "anchor_profile recorded by each shipped bundle; any disagreement "
                "is a shipped-honesty defect."),
        },
        "controls_FROZEN": {
            "C1": "frozen RULES_LABEL.json sha256 == 4457e971...; re-hashed before scoring",
            "C2": "each of the five frozen anchor qids resolves to itself (non-vacuous resolver)",
            "C3": "unknown gibberish query resolves to None",
            "C4": "synthetic norm extractor emits a shared token (non-vacuous extractor)",
            "C5": "two full measurement passes are byte-identical",
            "C6": "frozen pins and mount identity stable before/after; hypothesis unchanged",
            "C7": "observed population equals the pinned population exactly (set relation)",
        },
        "population_FROZEN": {
            "selection_rule": mod.SELECTION_RULE_FROZEN,
            "n_bundles": len(pop),
            "bundle_sha256_by_rel_path": pop,
            "bundle_metadata_at_freeze": rel_meta,
        },
        "expected_pins_at_freeze": {
            "instrument_sha256": instrument_sha,
            "frozen_spec_sha256": spec_sha,
            "frozen_rules_sha256": rules_sha,
            "seam_sha256": seam_sha,
            "instrument_computed_mount_head": instr_mount_head,
            "true_git_mount_head": true_head,
            "mount_head_disclosure": (
                "The preserved instrument's _mount_head() reads mount/.git as a "
                "DIRECTORY; /tmp/lex_accepted/product/.git is a worktree FILE, so "
                "the instrument pins the stable string HEAD_UNREADABLE. This is "
                "an identity limitation, not a quality bar. The true git head is "
                "pinned here and re-checked independently by the resume report; "
                "the instrument itself was NOT edited."),
        },
        "baselines_REPORT_ONLY": {
            "product_disclosure_40146845666": {
                "business-judgment-rule": "fr-bail-entretien (domain-mismatched)",
                "petty-theft-dismissal": None,
                "source": "reports/audit/product/CYCLE_40146845666.md and "
                          "state/product.json item 6 (product-authored, not this measurement)",
            },
            "standing_falsification_of_record": {
                "verdict": "PRODUCT_FALSIFIED",
                "packet_of_record": "39319405429",
                "note": "untouched, not re-run, not replaced by this instrument",
            },
        },
        "success_rule_FROZEN": {
            "COVERAGE_AND_ALIGNMENT_HOLD": "all controls hold, H1 and H2a hold, H3 holds",
            "PROFILE_COVERAGE_FALSIFIED": "controls hold and any H1 or H2a leg fails",
            "NOT_MEASURED_VACUOUS": "any control fails (pin drift, population mismatch, "
                                    "or non-determinism)",
            "no_frozen_bar": "no rubric, threshold, verdict contract or serve verdict "
                             "is scored, edited or moved",
        },
        "claim_ceiling": (
            "Measures only shipped anchor-profile coverage, norm-token alignment "
            "and shipped-provenance agreement over the pinned flagship family on "
            "committed bytes. Does NOT label any decision supporting/contrary/"
            "limiting; does NOT score RULES_LABEL, any frozen bar or verdict "
            "contract; does NOT replace the benchmark of record; issues NO serve "
            "verdict; claims NO jurist usefulness and NO live recall."),
        "not_in_scope": [
            "no frozen bar, rubric, threshold or verdict contract is edited",
            "no DO-NOT-SERVE order is lifted; no packet is admitted",
            "no universal-174k benchmark rerun",
            "no comparison map-vs-ranked-list claim",
            "posture flags stay FALSE; owner_decision_required stays false",
            "the failed producer run is not re-dispatched; its snapshot is preserved",
        ],
        "pre_freeze_disclosure_VERBATIM": (
            "Before writing this freeze I read: the failed run's GitHub REST "
            "run/job/annotation records (rc-78 quantum expiry), the team-branch "
            "snapshot and its single added instrument file, the instrument source, "
            "the accepted product mount's bundle inventory and provenance fields "
            "(anchor_profile, applied, content_filter presence), the frozen "
            "RULES_LABEL.json anchors and counter_anchor.py resolver, and sha256 "
            "of every selected bundle. I did NOT execute the instrument or any "
            "H1/H2/H3 predicate, and did not inspect its result or verdict."),
    }
    hyp_path.write_text(json.dumps(hypothesis, indent=2, sort_keys=True) + "\n",
                        encoding="utf-8")
    hyp_sha = sha_b(hyp_path.read_bytes())

    freeze: dict[str, Any] = {
        "schema": "lex-evaluation-frozen-rules-profile-coverage-freeze/1",
        "lane": "evaluation",
        "run_id": RUN_ID,
        "direction_version": 68,
        "freeze_recorded_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "hypothesis_file": str(hyp_path.relative_to(REPO)),
        "hypothesis_sha256_at_freeze": hyp_sha,
        "expected_pins_before_execution": {
            "hypothesis": hyp_sha,
            "frozen_spec": spec_sha,
            "mount:product/frozen/RULES_LABEL.json": rules_sha,
            "mount:product/query/counter_anchor.py": seam_sha,
            "mount_head": instr_mount_head,
        },
        "population_sha256_at_freeze": pop,
        "true_git_mount_head_at_freeze": true_head,
        "instrument_sha256_at_freeze": instrument_sha,
        "freeze_discipline": (
            "This record and its hypothesis are written BEFORE the first "
            "claim-bearing execution of the preserved instrument under run "
            "46114243630. No threshold, predicate, population member, control, "
            "success rule or expected digest may be edited after execution; an "
            "edit invalidates the run and must be declared as a NEW frozen spec."),
        "ordering_proof_contract": (
            "Reproduce with: git log --diff-filter=A --format='%H %cI %s' -- "
            f"{hyp_path.relative_to(REPO)} and compare with the first commit "
            "adding results/evaluation/frozen_rules_profile_coverage/46114243630.json"),
        "what_this_record_does_not_freeze": (
            "It does not edit, re-derive or re-tune the frozen rubric, any frozen "
            "bar, threshold or verdict contract, and it does not freeze an "
            "expected measurement outcome. Mount digests are identity checks."),
    }
    freeze_path.write_text(json.dumps(freeze, indent=2, sort_keys=True) + "\n",
                           encoding="utf-8")
    print(json.dumps({
        "hypothesis": str(hyp_path), "hypothesis_sha256": hyp_sha,
        "freeze": str(freeze_path),
        "freeze_sha256": sha_b(freeze_path.read_bytes()),
        "n_population": len(pop),
        "instrument_sha256": instrument_sha,
        "true_git_mount_head": true_head,
    }, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())

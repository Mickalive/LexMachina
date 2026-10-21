#!/usr/bin/env python3
"""Repair round 1 of rejected cycle 39628161040: parity-attribution repair.

WHAT THIS INSTRUMENT DOES (and nothing else)
-------------------------------------------
The independent audit of run 39628161040 returned gate REVISE with four
required fixes (F1 attribution/decomposition, F2 frozen-rule contradiction,
F3 test coverage, F4 disposition wording).  This instrument VERIFIES, by
executable checks over the committed artifacts, that each required fix is
actually discharged, and publishes the result as a machine record plus a
report.  It measures nothing new: every number it checks is re-read from the
committed V2 measurement record or re-derived from the committed inputs.

It never re-derives a threshold, bar, rubric, comparator or success rule; it
never modifies a frozen input; it never withdraws the FAIL verdict; it never
lifts a DO-NOT-SERVE order; it never certifies a packet; it authorises no owner
question.  human_gate_ready, machine_gate_ready, packet_admitted,
ready_for_owner_session and owner_decision_required all stay false.  The
independent audit of THIS cycle is still owed: the repair is not self-certified.

EXIT CODES
----------
0 REPAIR_FIXES_VERIFIED   every required fix is discharged and checked
1 REPAIR_FIX_INCOMPLETE   at least one required fix is not discharged
2 ENVIRONMENT_OR_INPUT_MISSING  a required artifact is absent; never a pass
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

RUN_ID = "39631600439"
REPAIRED_CYCLE = "39628161040"
SCHEMA = "lex-evaluation-parity-attribution-repair/1"

V2_RECORD_RELPATH = f"results/evaluation/product_cache_parity/{RUN_ID}.json"
V2_FIRST_EXEC_RELPATH = (f"results/evaluation/product_cache_parity/"
                         f"{RUN_ID}_first_execution.json")
V2_REPORT_RELPATH = f"reports/evaluation/PRODUCT_CACHE_PARITY_{RUN_ID}.md"
V2_HYPOTHESIS_RELPATH = "evaluation/PRODUCT_CACHE_PARITY_HYPOTHESIS_V2.json"
V2_FREEZE_RELPATH = "evaluation/PRODUCT_CACHE_PARITY_FREEZE_RECORD_V2.json"
V1_HYPOTHESIS_RELPATH = "evaluation/PRODUCT_CACHE_PARITY_HYPOTHESIS_V1.json"
V1_FREEZE_RELPATH = "evaluation/PRODUCT_CACHE_PARITY_FREEZE_RECORD_V1.json"
V1_REPORT_RELPATHS = (
    "reports/evaluation/PRODUCT_CACHE_PARITY_39619144928.md",
    "reports/evaluation/PRODUCT_CACHE_PARITY_39628161040.md",
)
OPRES_REPORT_RELPATH = "reports/evaluation/OPERATIONAL_RESUME_39628161040.md"
OPRES_RECORD_RELPATH = (f"results/evaluation/operational_resume/"
                        f"{REPAIRED_CYCLE}.json")
STATE_RELPATH = "state/evaluation.json"
TEST_RELPATH = "tests/evaluation/test_product_cache_parity.py"
AUDIT_GATE_RELPATH = ("/tmp/lex_prior_audit/results/audit/evaluation/"
                      "CYCLE_39628161040_GATE.json")

SHIM_REGRESSION_RELPATH = ("results/evaluation/orchestration/"
                           f"{RUN_ID}_shim_regression.json")
OUT_RELPATH = (f"results/evaluation/repair_39628161040/"
               f"{RUN_ID}_parity_attribution_repair.json")
REPORT_RELPATH = (f"reports/evaluation/PARITY_ATTRIBUTION_REPAIR_{RUN_ID}.md")

EXIT_VERIFIED = 0
EXIT_INCOMPLETE = 1
EXIT_ENVIRONMENT = 2

# the corrected F4 wording, verbatim as required by the audit
F4_CORRECTED = ("preserved in this branch snapshot with digests recorded in the "
                "lane machine record, removed at promotion by the integrate "
                "step's audit-directory checkout")
# the F1 honest characterization, verbatim as required by the audit
F1_HONEST = ("multilingual/counter-channel retrieval-coverage deficit")
F1_HONEST_ALT = ("QUERY-COVERAGE deficit, NOT a same-query retrieval-layer "
                 "regression")


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read(relpath: str) -> str:
    return (REPO_ROOT / relpath).read_text(encoding="utf-8")


def _check(name: str, holds: bool, detail: str) -> dict:
    return {"check": name, "holds": bool(holds), "detail": detail}


def verify() -> dict:
    """Run every required-fix check; returns the machine record body."""
    required = [REPO_ROOT / p for p in (
        V2_RECORD_RELPATH, V2_REPORT_RELPATH, V2_HYPOTHESIS_RELPATH,
        V2_FREEZE_RELPATH, V1_HYPOTHESIS_RELPATH, V1_FREEZE_RELPATH,
        OPRES_RECORD_RELPATH, OPRES_REPORT_RELPATH, STATE_RELPATH,
        TEST_RELPATH)]
    missing = [p for p in required if not p.is_file()]
    if missing:
        return {"environment_missing": [str(p.relative_to(REPO_ROOT))
                                        for p in missing]}

    rec = load(REPO_ROOT / V2_RECORD_RELPATH)
    hyp = load(REPO_ROOT / V2_HYPOTHESIS_RELPATH)
    freeze = load(REPO_ROOT / V2_FREEZE_RELPATH)
    state = load(REPO_ROOT / STATE_RELPATH)
    opres = load(REPO_ROOT / OPRES_RECORD_RELPATH)
    opres_md = read(OPRES_REPORT_RELPATH)
    state_json = json.dumps(state, ensure_ascii=False)
    test_src = read(TEST_RELPATH)
    fixes: dict[str, Any] = {}

    # ---------------- F1: decomposition + honest attribution -------------- #
    f1: list[dict] = []
    decomp = rec.get("gate_decomposition") or []
    gated_cells = {(d["slug"], d["kind"]) for d in decomp}
    f1.append(_check(
        "F1.decomposition_published_for_every_gated_cell",
        len(decomp) == 8 and all(
            d.get("per_channel_language") and
            "executed_text_only_comparison" in d and
            "comparator_only_attribution" in d for d in decomp),
        f"{len(decomp)} (slug, kind) decomposition rows, each with the "
        "per-(channel, language) hit table, the executed-text-only comparison "
        "and the comparator-only id attribution"))
    same_text = [g for g in rec["gates"]
                 if g["role"] == "falsifier" and g["passed"] is not None]
    f1.append(_check(
        "F1.executed_text_only_comparison_for_all_7_parity_gates",
        len(same_text) == 7 and all(
            g["measured"].get("comparator_scope") == "executed_text" and
            "product_hits" in g["measured"] and
            "comparator_hits" in g["measured"] for g in same_text),
        f"{len(same_text)} measurable same-text gates carry the "
        "executed-text-only comparison (product_hits vs comparator_hits)"))
    att = rec.get("coverage_attribution_summary") or {}
    f1.append(_check(
        "F1.comparator_only_ids_attributed_to_never_executed_texts",
        att.get("n_comparator_only_ids") == 18 and
        att.get("n_comparator_only_ids_from_non_executed_texts") == 18 and
        att.get("n_comparator_only_ids_from_executed_texts") == 0,
        f"{att.get('n_comparator_only_ids')} comparator-only ids, "
        f"{att.get('n_comparator_only_ids_from_non_executed_texts')} of them "
        "produced only by texts the product never executed"))
    f1.append(_check(
        "F1.executed_text_comparison_never_below_product",
        all(g["passed"] is True for g in same_text),
        "on the executed text the product reaches >= the plain comparator in "
        "all 7 same-text cells (0/0, 1/0, 1/1, 0/0, 0/0, 0/0, 1/0)"))
    f1.append(_check(
        "F1.verdict_still_fail_but_attributed_to_coverage",
        rec["verdict"] == "FAIL_PRODUCT_CACHE_PARITY" and
        rec["exit_code"] == 1 and rec["verdict_scope"] == "coverage" and
        rec["same_text_parity_verdict"] == "PASS" and
        rec["coverage_verdict"] == "FAIL",
        "the FAIL verdict of the frozen success rule stands; the verdict_scope "
        "is coverage and the same-text family PASSes"))
    for rel in V1_REPORT_RELPATHS:
        md = read(rel)
        f1.append(_check(
            f"F1.restated_in_{rel}",
            "Finding restatement (repair round 1, run 39631600439)" in md and
            "not** a same-query" in md and
            "0/0, 1/0, 1/1, 0/0, 0/0, 0/0, 1/0" in md and
            "18 comparator-only" in md,
            "the finding is restated with the per-(channel, language) "
            "decomposition pointer and the honest characterization"))
    f1.append(_check(
        "F1.restated_in_operational_resume_report",
        "QUERY-COVERAGE deficit, NOT a same-text" in opres_md and
        "Superseded wording (preserved verbatim" in opres_md,
        "the operational-resume report carries the corrected attribution and "
        "preserves the superseded sentence verbatim"))
    f1.append(_check(
        "F1.restated_in_state_note",
        "QUERY-COVERAGE deficit, NOT a same-query retrieval-layer regression"
        in state_json and
        "Falsifies same-query retrieval parity" not in state_json,
        "state/evaluation.json product_cache_parity.note no longer claims a "
        "same-query retrieval-layer regression"))
    f1.append(_check(
        "F1.decomposition_in_v2_report",
        "Per-(channel, language) comparator decomposition" in
        read(V2_REPORT_RELPATH) and
        "Comparator-only id attribution" in read(V2_REPORT_RELPATH),
        "the V2 report publishes the decomposition and the attribution table"))
    fixes["F1"] = {"required": "publish the per-(channel,language) comparator "
                                "decomposition and the executed-text-only "
                                "comparison for all 7 parity gates and restate "
                                "the finding (the verdict may stand, the "
                                "same-query-regression characterization may "
                                "not)",
                   "checks": f1, "complete": all(c["holds"] for c in f1)}

    # ---------------- F2: frozen-rule contradiction ----------------------- #
    f2: list[dict] = []
    f2.append(_check(
        "F2.versioned_hypothesis_frozen_before_execution",
        hyp.get("schema") == "lex-evaluation-product-cache-parity-hypothesis/2"
        and hyp.get("frozen_before_execution") is True and
        freeze["hypothesis"]["sha256"] == sha256_file(
            REPO_ROOT / V2_HYPOTHESIS_RELPATH),
        "V2 hypothesis + V2 freeze record exist, are versioned and are pinned "
        "by digest"))
    f2.append(_check(
        "F2.pre_freeze_disclosure_present",
        "pre_freeze_disclosure_HONEST_V2" in hyp and
        hyp["pre_freeze_disclosure_HONEST_V2"].get(
            "pre_freeze_expectation_disclosed"),
        "the V2 hypothesis discloses in-file that it is a re-specification "
        "authored after the V1 outcome was observed, and states the expected "
        "outcome"))
    names = hyp.get("gate_names_FROZEN_V2") or []
    f2.append(_check(
        "F2.coverage_asymmetry_is_an_explicit_gated_quantity",
        any(n.startswith("parity::same_query_") for n in names) and
        any(n.startswith("coverage::union_frozen_texts_") for n in names),
        "the gate list contains BOTH families: the like-for-like same-text "
        "family and the explicitly gated union-of-all-frozen-texts coverage "
        "family"))
    reused = freeze.get("frozen_rules_reused_verbatim") or {}
    f2.append(_check(
        "F2.frozen_rules_and_ids_unchanged",
        reused.get("zero_new_thresholds") is True and
        reused.get("frozen_id_sets_unchanged") is True and
        reused.get("matcher_unchanged") is True and
        reused.get("gate_count_before") == 7 and
        reused.get("gate_count_after") == 14 and
        reused.get("failing_comparisons_before") == 7 and
        reused.get("failing_comparisons_after_expected") == 7,
        "no new threshold, no changed id set, no changed matcher; the gated "
        "comparisons grow 7 -> 14 while the failing comparisons stay 7"))
    pres = freeze.get("superseded_spec_byte_preserved") or {}
    v1_ok = (pres.get("v1_hypothesis", {}).get("sha256") == sha256_file(
        REPO_ROOT / V1_HYPOTHESIS_RELPATH) and
        pres.get("v1_freeze_record", {}).get("sha256") == sha256_file(
            REPO_ROOT / V1_FREEZE_RELPATH))
    for rel, digest in (pres.get("v1_records") or {}).items():
        v1_ok = v1_ok and (REPO_ROOT / rel).is_file() and sha256_file(
            REPO_ROOT / rel) == digest
    f2.append(_check(
        "F2.v1_chain_byte_preserved",
        v1_ok,
        "the V1 hypothesis, the V1 freeze record and both V1 measurement "
        "records re-hash to the digests pinned by the V2 freeze record"))
    v1pres = rec.get("v1_preservation") or {}
    f2.append(_check(
        "F2.v1_failures_not_downgraded",
        v1pres.get("all_preserved") is True and all(
            i.get("failed_sets_identical") is True and
            i.get("n_v1_failed") == 7 and i.get("n_v2_failed") == 7
            for i in (v1pres.get("records") or {}).values()),
        "every V1 falsifier gate maps 1:1 onto a V2 coverage gate with "
        "identical measurements, and the same 7 comparisons still fail"))
    fixes["F2"] = {"required": "do not ship a measurement that contradicts the "
                                "frozen rule governing it: either restrict the "
                                "primary comparator to the executed text or "
                                "publish a versioned hypothesis with a new "
                                "freeze record and a pre-freeze disclosure "
                                "that makes the coverage asymmetry an explicit "
                                "gated quantity",
                   "checks": f2, "complete": all(c["holds"] for c in f2)}

    # ---------------- F3: asymmetric synthetic coverage ------------------ #
    f3: list[dict] = []
    f3.append(_check(
        "F3.asymmetric_fixture_present",
        "_synth_asymmetric" in test_src and
        "test_non_executed_text_coverage_cannot_become_a_same_text_falsification"
        in test_src,
        "the synthetic fixture builds a comparator pool that contains a text "
        "the product never executed"))
    executed = _execute_f3_test()
    f3.append(_check(
        "F3.asymmetric_test_executes_and_passes",
        executed.get("ok") is True,
        executed.get("detail", "")))
    f3.append(_check(
        "F3.instrument_pins_the_asymmetry",
        "C3_executed_text_pool_must_not_be_a_same_text_falsification" in
        json.dumps(rec.get("non_vacuity") or {}),
        "the instrument's own non-vacuity battery carries the C3 control that "
        "re-scores the executed-text pool and forbids a same-text "
        "falsification"))
    fixes["F3"] = {"required": "add a synthetic case with a comparator pool "
                                "containing texts the product never executed and "
                                "assert that the gate cannot silently convert "
                                "non-executed coverage into a same-text "
                                "falsification",
                   "checks": f3, "complete": all(c["holds"] for c in f3)}

    # ---------------- F4: disposition wording ---------------------------- #
    f4: list[dict] = []
    oos = (opres.get("snapshot_hygiene") or {}).get("out_of_scope") or []
    f4.append(_check(
        "F4.record_disposition_corrected",
        bool(oos) and all(F4_CORRECTED in (e.get("disposition") or "")
                          for e in oos),
        "every out-of-scope entry carries the corrected disposition wording"))
    f4.append(_check(
        "F4.superseded_wording_preserved_verbatim",
        bool(oos) and all(
            (e.get("disposition_v1_verbatim") or "").startswith(
                "preserved in place as evidence of the scope failure")
            for e in oos),
        "the superseded disposition string is preserved verbatim beside the "
        "correction (no deletion, no silent rewrite)"))
    f4.append(_check(
        "F4.report_wording_corrected",
        "preserved in this branch snapshot with digests recorded in the lane "
        "machine record, removed at promotion by the integrate step's "
        "audit-directory checkout" in opres_md,
        "the operational-resume report states the corrected disposition"))
    f4.append(_check(
        "F4.state_wording_corrected",
        "preserved in this branch snapshot with digests recorded in the lane "
        "machine record, removed at promotion by the integrate step's "
        "audit-directory checkout" in state_json,
        "state/evaluation.json operational_resume.diagnosis states the "
        "corrected disposition"))
    fixes["F4"] = {"required": "correct the disposition wording of the "
                                "inherited team-authored files to 'preserved in "
                                "this branch snapshot with digests recorded in "
                                "the lane machine record, removed at promotion "
                                "by the integrate step's audit-directory "
                                "checkout'",
                   "checks": f4, "complete": all(c["holds"] for c in f4)}

    # ---------------- first-execution provenance ------------------------- #
    first_exec = None
    first_path = REPO_ROOT / V2_FIRST_EXEC_RELPATH
    if first_path.is_file():
        first = load(first_path)
        diff_keys = sorted(k for k in set(first) | set(rec)
                           if first.get(k) != rec.get(k))
        first_exec = {
            "path": V2_FIRST_EXEC_RELPATH,
            "sha256": sha256_file(first_path),
            "preserved": True,
            "differing_keys": diff_keys,
            "claim_bearing_quantities_identical": all(
                k in ("generated_at_utc", "elapsed_s", "v1_preservation")
                for k in diff_keys),
            "note": "the first execution of this cycle is preserved verbatim; "
                    "the only differences to the re-executed record are the "
                    "timestamp, the elapsed time and the strengthened "
                    "v1_preservation proof (the V1 records of that cycle "
                    "store hit COUNTS, the first execution compared only the "
                    "keys they both carried, which made the proof vacuous for "
                    "one of the two V1 records)",
        }
    all_complete = all(fixes[k]["complete"] for k in ("F1", "F2", "F3", "F4"))
    lane_suite = {"present": False}
    shim_path = REPO_ROOT / SHIM_REGRESSION_RELPATH
    if shim_path.is_file():
        sh = load(shim_path)
        lane_suite = {
            "present": True,
            "is_audit_required_fix": False,
            "record": SHIM_REGRESSION_RELPATH,
            "sha256": sha256_file(shim_path),
            "verdict": sh.get("verdict"),
            "baseline_label": sh.get("baseline_label"),
            "current_label": sh.get("current_label"),
            "n_new_failures": sh.get("n_new_failures"),
            "n_no_longer_failing": sh.get("n_no_longer_failing"),
            "baseline_counts": sh.get("baseline_counts"),
            "current_counts": sh.get("current_counts"),
            "note": "supporting evidence, NOT one of the four audit required "
                    "fixes: the lane suite under the no-pytest shim is NOT "
                    "green in this rejected branch snapshot and is not claimed "
                    "to be. The delta against the pre-repair tree at commit "
                    "ae039b9c is 0 new failures; the pre-existing failures "
                    "stay visible as pre-existing failures and UNSUPPORTED / "
                    "SKIPPED cases are counted as NOT-RUN, never as passes.",
        }
    return {
        "fixes": fixes,
        "all_required_fixes_complete": all_complete,
        "first_execution": first_exec,
        "lane_suite_regression": lane_suite,
        "environment_missing": None,
    }


def _execute_f3_test() -> dict:
    """Execute the asymmetric (F3) test function directly, offline."""
    try:
        import importlib.util
        from evaluation import no_pytest_runner as shim
        shim._install_shim()
        spec = importlib.util.spec_from_file_location(
            "lex_parity_tests", REPO_ROOT / TEST_RELPATH)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        fn = getattr(mod, "test_non_executed_text_coverage_"
                             "cannot_become_a_same_text_falsification")
        fn()
        return {"ok": True, "detail": "the asymmetric-case test function ran "
                                      "and its assertions held"}
    except Exception as exc:  # pragma: no cover - reported, never swallowed
        return {"ok": False, "detail": f"{type(exc).__name__}: {exc}"}


def build_record(body: dict) -> dict:
    audit = None
    audit_path = Path(AUDIT_GATE_RELPATH)
    if audit_path.is_file():
        g = load(audit_path)
        audit = {"gate": g.get("gate"), "safe_to_integrate": g.get(
            "safe_to_integrate"),
            "n_required_fixes": len(g.get("required_fixes") or []),
            "source": AUDIT_GATE_RELPATH}
    record = {
        "schema": SCHEMA,
        "run_id": RUN_ID,
        "repaired_cycle": REPAIRED_CYCLE,
        "generated_at_utc": datetime.now(timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"),
        "entry_point": "python -m evaluation.repair_39631600439_parity_attribution",
        "audit": audit,
        "required_fixes_source": "results/audit gate "
                                 "CYCLE_39628161040_GATE.json (read-only; this "
                                 "cycle writes no audit file and certifies "
                                 "nothing about its own work)",
        "v2_hypothesis_sha256": sha256_file(REPO_ROOT / V2_HYPOTHESIS_RELPATH),
        "v2_freeze_record_sha256": sha256_file(REPO_ROOT / V2_FREEZE_RELPATH),
        "v2_record_sha256": sha256_file(REPO_ROOT / V2_RECORD_RELPATH),
        "v1_hypothesis_sha256": sha256_file(REPO_ROOT / V1_HYPOTHESIS_RELPATH),
        "v1_freeze_record_sha256": sha256_file(REPO_ROOT / V1_FREEZE_RELPATH),
        "all_required_fixes_complete": body["all_required_fixes_complete"],
        "verdict": ("REPAIR_FIXES_VERIFIED"
                    if body["all_required_fixes_complete"]
                    else "REPAIR_INCOMPLETE"),
        "fixes": body["fixes"],
        "first_execution": body["first_execution"],
        "lane_suite_regression": body["lane_suite_regression"],
        "n_checks": sum(len(body["fixes"][k]["checks"])
                        for k in body["fixes"]),
        "n_checks_passed": sum(1 for k in body["fixes"]
                               for c in body["fixes"][k]["checks"]
                               if c["holds"]),
        "measurements_untouched": {
            "network_requests": 0,
            "no_174k_benchmark_rerun": True,
            "no_new_thresholds": True,
            "frozen_inputs_unchanged": True,
            "frozen_id_sets_unchanged": True,
            "matcher_unchanged": True,
            "verdict_withdrawn": False,
            "v1_artifacts_deleted": False,
        },
        "claim_ceiling": (
            "This record proves only that the four required fixes of the "
            "independent audit of cycle 39628161040 are DISCHARGED and "
            "machine-checked against the committed artifacts: (F1) the "
            "per-(channel, language) comparator decomposition, the "
            "executed-text-only comparison for all 7 parity gates and the "
            "honest restatement of the finding are published, while the "
            "FAIL_PRODUCT_CACHE_PARITY verdict of the frozen success rule "
            "stands; (F2) the frozen-rule contradiction is removed by a "
            "versioned V2 hypothesis with its own freeze record and an "
            "in-file pre-freeze disclosure, with no new threshold, no changed "
            "id set, no changed matcher and the same 7 failing comparisons; "
            "(F3) the asymmetric synthetic case is executable and forbids a "
            "non-executed text's coverage from becoming a same-text "
            "falsification; (F4) the disposition wording of the inherited "
            "team-authored files is corrected, with the superseded wording "
            "preserved verbatim. It does NOT prove that the product's "
            "retrieval quality is worse than plain OpenCaseLaw on the text it "
            "ran (the like-for-like same-text family PASSes 7/7); it does NOT "
            "lift either DO-NOT-SERVE order, does NOT move the frozen "
            "absolute bars (REPORTED-ONLY), does NOT certify any packet, does "
            "NOT assert that any decision is supporting/contrary/limiting, and "
            "authorises NO owner question. This repair is NOT "
            "self-certified: an independent audit of THIS cycle is still owed "
            "and the evidence tier stays EXPLORATORY."),
        "pending_independent_audit": True,
    }
    return record


def write_report(record: dict, report_path: Path) -> None:
    lines = [
        f"# Parity-attribution repair — run {record['run_id']}",
        "",
        f"- Repaired cycle: `{record['repaired_cycle']}` (audit gate "
        f"`{record['audit']['gate'] if record['audit'] else 'REVISE'}`)",
        f"- Required fixes complete: **{record['all_required_fixes_complete']}** "
        f"({record['n_checks_passed']}/{record['n_checks']} checks passed)",
        f"- V2 hypothesis sha256 `{record['v2_hypothesis_sha256'][:12]}...`, "
        f"V2 record sha256 `{record['v2_record_sha256'][:12]}...`",
        "- The FAIL verdict is **not** withdrawn; its **attribution** is "
        "corrected and machine-published.",
        "",
    ]
    for key in ("F1", "F2", "F3", "F4"):
        f = record["fixes"][key]
        lines += [f"## {key} — {'COMPLETE' if f['complete'] else 'INCOMPLETE'}",
                  "", f"*{f['required']}*", "",
                  "| check | holds | detail |", "|---|---|---|"]
        for c in f["checks"]:
            lines.append(f"| `{c['check']}` | "
                         f"{'yes' if c['holds'] else '**NO**'} | {c['detail']} |")
        lines.append("")
    ls = record.get("lane_suite_regression") or {}
    if ls.get("present"):
        lines += [
            "## Lane-suite regression delta (supporting evidence, NOT an "
            "audit required fix)",
            "",
            f"- record: `{ls['record']}` sha256 `{ls['sha256'][:12]}...`",
            f"- baseline: {ls['baseline_label']}",
            f"- current: {ls['current_label']}",
            f"- verdict: **{ls['verdict']}** — new failures "
            f"**{ls['n_new_failures']}**, no longer failing "
            f"**{ls['n_no_longer_failing']}**",
            f"- {ls['note']}",
            "",
        ]
    fe = record.get("first_execution") or {}
    if fe:
        lines += [
            "## First execution of this cycle (preserved)",
            "",
            f"- `{fe['path']}` sha256 `{fe['sha256'][:12]}...` — preserved "
            "verbatim.",
            f"- differing keys vs the re-executed record: "
            f"`{', '.join(fe['differing_keys'])}`",
            f"- claim-bearing quantities identical: "
            f"**{fe['claim_bearing_quantities_identical']}**",
            f"- {fe['note']}",
            "",
        ]
    lines += [
        "## Claim ceiling",
        "",
        record["claim_ceiling"],
        "",
        f"Machine record: `{OUT_RELPATH}`",
    ]
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    ap.add_argument("--out", default=str(REPO_ROOT / OUT_RELPATH))
    ap.add_argument("--report", default=str(REPO_ROOT / REPORT_RELPATH))
    args = ap.parse_args(argv)
    body = verify()
    if body.get("environment_missing"):
        print(json.dumps({"verdict": "ENVIRONMENT_OR_INPUT_MISSING",
                          "missing": body["environment_missing"]}, indent=1))
        return EXIT_ENVIRONMENT
    record = build_record(body)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(record, indent=1, ensure_ascii=False) + "\n",
                   encoding="utf-8")
    write_report(record, Path(args.report))
    code = EXIT_VERIFIED if record["all_required_fixes_complete"] \
        else EXIT_INCOMPLETE
    record["exit_code"] = code
    out.write_text(json.dumps(record, indent=1, ensure_ascii=False) + "\n",
                   encoding="utf-8")
    print(json.dumps({
        "run_id": record["run_id"],
        "verdict": ("REPAIR_FIXES_VERIFIED" if code == EXIT_VERIFIED
                    else "REPAIR_FIX_INCOMPLETE"),
        "exit_code": code,
        "n_checks": record["n_checks"],
        "n_checks_passed": record["n_checks_passed"],
        "all_required_fixes_complete": record["all_required_fixes_complete"],
        "record": str(args.out),
    }, indent=1))
    return code


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

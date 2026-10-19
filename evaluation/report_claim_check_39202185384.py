#!/usr/bin/env python3
"""Committed generator of the cycle-39202185384 report-claim check (audit F-3).

WHY THIS FILE EXISTS
--------------------
Audit ``results/audit/evaluation/CYCLE_39202185384_GATE.json`` F-2/F-3 found
that the report and lane state quoted a check count their own cited artifact
contradicted, and that neither machine checker had a committed generator at all
— so by factory-wide requirement 29 both "verified" claims were UNREPRODUCED.
This module is the generator for
``results/evaluation/product_served_bundle_falsification/39202185384_report_claims.json``,
committed in the lane namespace and named by commit in the cycle report.

WHAT A CHECK IS
---------------
Every check re-derives ONE published claim from bytes that are on disk right
now — the committed record, the report itself, the frozen hypothesis, the lane
state, the served packet on the accepted mount (re-hashed against the frozen
pins first), a fresh pytest execution, or a ``git cat-file`` of a named commit.
A check never compares a claim with another claim.

Counts
------
``n_checks`` is the length of this module's check list, not a number read from
the report.  Two checks assert that the report's and the state's quoted
``N/N`` literal equals that length, so a stale count fails loudly instead of
quietly circulating (that is exactly audit fix F-2).

Exit codes
----------
0  every check passed
1  at least one check failed
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from evaluation.query_map.product_served_bundle_falsification import (  # noqa: E402
    rehash_pins,
)

SCHEMA = "lex-evaluation-report-claim-check/1"
RUN_ID = "39202185384"

REPORT_REL = "reports/evaluation/CYCLE_39202185384.md"
RECORD_REL = "results/evaluation/product_served_bundle_falsification/39202185384.json"
HYPOTHESIS_REL = "evaluation/PRODUCT_SERVED_BUNDLE_FALSIFICATION_HYPOTHESIS_V1.json"
REPRO_REL = ("results/evaluation/product_served_bundle_falsification/"
             "39202185384_reproduction_check.json")
STATE_REL = "state/evaluation.json"
INSTRUMENT_REL = "evaluation/query_map/product_served_bundle_falsification.py"
OUT_REL = "results/evaluation/product_served_bundle_falsification/39202185384_report_claims.json"

MOUNT = Path("/tmp/lex_accepted/product")

GENERATOR_COMMIT_RE = re.compile(
    r"Generators committed at:\s*`([0-9a-f]{40})`")

CYCLE_TEST_FILE = "tests/evaluation/test_product_served_bundle_falsification.py"
FIVE_TEST_FILES = [
    CYCLE_TEST_FILE,
    "tests/evaluation/test_query_map_bundle_producer.py",
    "tests/evaluation/test_question_native_transfer.py",
    "tests/evaluation/test_report_claim_check.py",
    "tests/evaluation/test_v57_open_items.py",
]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _load(rel: str):
    with open(REPO_ROOT / rel, encoding="utf-8") as fh:
        return json.load(fh)


def _pytest_summary(files: list[str]) -> dict:
    """Run pytest on the named files and parse its summary line."""
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "pytest", "-q", "--tb=no", "-p", "no:cacheprovider", *files],
            cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=600)
    except Exception as exc:  # pragma: no cover - environment disclosure
        return {"error": f"{type(exc).__name__}: {exc}", "returncode": None}
    blob = (proc.stdout or "") + "\n" + (proc.stderr or "")
    counts = {}
    for name in ("passed", "failed", "skipped", "error", "errors"):
        m = re.findall(rf"(\d+) {name}", blob)
        if m:
            counts[name] = int(m[-1])
    return {"returncode": proc.returncode, "counts": counts,
            "summary_line": next(
                (ln for ln in reversed(blob.splitlines())
                 if " passed" in ln or " failed" in ln or " error" in ln), ""),
            "error": None}


def _git(*args: str) -> tuple[bool, str]:
    try:
        proc = subprocess.run(["git", "-C", str(REPO_ROOT), *args],
                              capture_output=True, text=True, timeout=60)
    except Exception as exc:  # pragma: no cover
        return False, f"{type(exc).__name__}: {exc}"
    if proc.returncode != 0:
        return False, (proc.stderr or proc.stdout).strip()[-300:]
    return True, proc.stdout.strip()


def build_checks() -> list[dict]:
    report = (REPO_ROOT / REPORT_REL).read_text(encoding="utf-8")
    state_text = (REPO_ROOT / STATE_REL).read_text(encoding="utf-8")
    record = _load(RECORD_REL)
    hyp = _load(HYPOTHESIS_REL)
    repro = _load(REPRO_REL)
    state = json.loads(state_text)
    checks: list[dict] = []

    def add(cid: str, claim: str, ok, detail="") -> None:
        checks.append({"id": cid, "claim": claim, "ok": bool(ok),
                       "detail": detail if isinstance(detail, (str, int, float))
                       else json.dumps(detail, ensure_ascii=False)[:400]})

    l2 = record["L2_counter_authority_liveness"]["per_qid"]
    head_l2 = record["headline"]["L2_counter_authority_yield"]
    head_cite = record["headline"]["L2_answer_cites_counter_authority"]
    both = head_l2["both_definitions_published_together"]
    prod_set = head_cite["under_the_products_own_counter_set"]
    l3 = record["L3_handoff_question_native_coverage"]
    l4 = record["L4_language_provenance_determinism"]["per_qid"]
    l1agg = record["L1_product_bytes_contract"]["aggregate"]

    # ---------------------------------------------------------------- digests
    rec_sha = sha256_file(REPO_ROOT / RECORD_REL)
    add("D-1", "record sha256 quoted in the report",
        rec_sha in report, rec_sha[:16])
    add("D-2", "record sha256 matches the artifact's own hypothesis binding",
        record["hypothesis"]["sha256"] == sha256_file(REPO_ROOT / HYPOTHESIS_REL),
        record["hypothesis"]["sha256"][:16])
    hyp_sha = sha256_file(REPO_ROOT / HYPOTHESIS_REL)
    add("D-3", "hypothesis sha256 quoted in the report",
        hyp_sha[:8] in report and record["hypothesis"]["sha256"] == hyp_sha,
        hyp_sha[:16])
    add("D-4", "hypothesis freeze commit 95499f16 quoted in the report",
        "95499f16" in report)

    pins = rehash_pins(hyp, REPO_ROOT, MOUNT)
    add("P-1", "21/21 frozen pins re-hashed live against the accepted mount",
        pins["n_checks"] == 21 and pins["n_match"] == 21 and pins["n_drift"] == 0,
        f"{pins['n_match']}/{pins['n_checks']} drift={pins['n_drift']}")
    add("P-2", "the report quotes 21/21 and pins_unchanged_during_run",
        "21/21" in report and record["pins_unchanged_during_run"] is True)
    add("P-3", "the accepted mount is at the pinned head and the report names it",
        pins["accepted_product_head_match"] is True
        and pins["accepted_product_head_declared"] in report
        and record["mount"]["head_resolved"] == pins["accepted_product_head_declared"],
        pins["accepted_product_head_resolved"] or "None")

    # ------------------------------------------------------- run + L3 + L1/L2
    add("R-1", "verdict ENVIRONMENT_OR_VACUOUS and exit 2 quoted",
        record["verdict"] == "ENVIRONMENT_OR_VACUOUS"
        and record["exit_code"] == 2
        and "ENVIRONMENT_OR_VACUOUS" in report and "exit **2**" in report)
    add("L3-1", "L3 aggregate HANDOFF_PASS quoted",
        l3["aggregate"]["aggregate_verdict"] == "HANDOFF_PASS"
        and "`HANDOFF_PASS`" in report)
    add("L3-2", "L3 per-qid verdicts as published",
        l3["aggregate"]["verdicts"] == {
            "de-kapitalverletzung": "HANDOFF_PASS",
            "fr-bail-entretien": "NO_DEFECT_INSTANCE_ON_THIS_QID",
            "it-responsabilita-medica": "NO_DEFECT_INSTANCE_ON_THIS_QID"}
        and "NO_DEFECT_INSTANCE_ON_THIS_QID" in report)
    add("L3-3", "no BEFORE finding code lost (condition e)",
        all(v["regression"]["finding_codes_lost_in_after"] == []
            for v in l3["per_qid"].values())
        and l3["aggregate"]["any_regression"] is False)
    add("L3-4", "all L3 non-vacuity controls fired, report says so",
        l3["aggregate"]["all_controls_fired"] is True and "both fired" in report)
    add("L3-5", "BEFORE admission sha256 456f065d quoted and matching",
        all((v["before"]["sha256"] or "").startswith("456f065d")
            for v in l3["per_qid"].values()) and "456f065d" in report)
    add("L3-6", "AFTER product admission module sha256 7d8d20c5 quoted and matching",
        all((v["after"]["product_code_sha256"] or "").startswith("7d8d20c5")
            for v in l3["per_qid"].values()) and "7d8d20c5" in report)
    add("L3-7", "frozen predicate module sha256 ffb2c70f quoted and matching",
        hyp["frozen_inputs"]["lane_frozen_sha256"][
            "evaluation/question_native_transfer.py"].startswith("ffb2c70f")
        and "ffb2c70f" in report)

    add("L1-1", "13 of 15 mutation controls fired, as published",
        head_l2 is not None
        and record["headline"]["L1_non_vacuity"]["n_fired"] == 13
        and record["headline"]["L1_non_vacuity"]["n_controls"] == 15
        and "13 of 15" in report)
    add("L1-2", "the two unfired controls are named as UNEXERCISED on fr, not passed",
        l1agg["vacuity"]["controls_not_fired"] == [
            "fr-bail-entretien:blanked_counter_evidence:UNEXERCISED_POPULATION_EMPTY",
            "fr-bail-entretien:blanked_counter_uncertainty:UNEXERCISED_POPULATION_EMPTY"]
        and "blanked_counter_evidence" in report
        and "UNEXERCISED_POPULATION_EMPTY" in report)
    add("L1-3", "all three bundles pass every measurable contract check",
        l1agg["all_contract_pass"] is True and l1agg["n_contract_pass"] == 3)
    add("L1-4", "NOT_MEASURED checks excluded from the measurable set on every qid",
        all(
            block["checks"][name] == "NOT_MEASURED"
            and name not in block["measurable_checks"]
            for block in record["L1_product_bytes_contract"]["per_qid"].values()
            for name in ("progressive_phases", "geometry_preserved_after_enrichment")
        ))

    add("L2-1", "642 decisions / 5 emitted labels / 0.78%, as published",
        head_l2["n_decisions_total"] == 642
        and head_l2["n_counter_labels_total"] == 5
        and head_l2["label_rate_over_all_decisions"] == 0.007788
        and "642" in report and "5 (0.78%)" in report)
    add("L2-2", "per-qid emitted labels 2 / 0 / 3, as published",
        head_l2["per_qid_labels"] == {"de-kapitalverletzung": 2,
                                      "fr-bail-entretien": 0,
                                      "it-responsabilita-medica": 3}
        and "56, 130" in report and "51, 163, 164" in report)
    add("L2-3", "15 answer citations with 0 EMITTED counter labels, as published",
        head_cite["n_answer_citations_total"] == 15
        and head_cite["n_citations_that_are_counter_authority"] == 0
        and head_cite["per_qid"] == {
            "de-kapitalverletzung": {"cited_rows": 4, "cited_counter_overlap": 0},
            "fr-bail-entretien": {"cited_rows": 6, "cited_counter_overlap": 0},
            "it-responsabilita-medica": {"cited_rows": 5, "cited_counter_overlap": 0}})
    add("L2-4", "fr-bail-entretien support_rate_among_issued is null, not 1.0",
        l2["fr-bail-entretien"]["support_rate_among_issued"] is None
        and "null" in report)
    add("L2-5", "the emitted-only definition is named wherever the zero is claimed",
        "EMITTED ONLY" in head_cite["definition_used_for_the_zero_count"]
        and "EMITTED" in report)

    # ------------------------------------- F-1: both accounting definitions
    add("F1-1", "product counter set 25/15/25 published beside the lane's 5/642",
        both["product_admission_definition"]["per_qid"] == {
            "de-kapitalverletzung": 25, "fr-bail-entretien": 15,
            "it-responsabilita-medica": 25}
        and both["product_admission_definition"]["n_total"] == 65
        and both["emitted_labels_lane_harness_definition"]["n_total"] == 5
        and "65/642" in report and "5/642" in report)
    add("F1-2", "product counter_yield 0.1168 / 0.0691 / 0.1185 published",
        both["product_admission_definition"]["per_qid_counter_yield"] == {
            "de-kapitalverletzung": 0.1168, "fr-bail-entretien": 0.0691,
            "it-responsabilita-medica": 0.1185}
        and all(s in report for s in ("0.1168", "0.0691", "0.1185")))
    add("F1-3", "the 60 abstentions (23+15+22) are published together",
        both["abstentions"]["n_abstained_unevidenced_rows_total"] == 60
        and both["abstentions"]["per_qid"] == {"de-kapitalverletzung": 23,
                                               "fr-bail-entretien": 15,
                                               "it-responsabilita-medica": 22}
        and both["abstentions"]["emitted_plus_abstained_equals_product_counter_set"] is True
        and "60" in report)
    add("F1-4", "4 of the 15 citations are product counter rows, all abstained",
        prod_set["n_citations_in_product_counter_set"] == 4
        and prod_set["n_answer_citations_total"] == 15
        and prod_set["all_are_abstained_unevidenced"] is True
        and prod_set["per_qid"]["de-kapitalverletzung"]["n_in_product_counter_set"] == 3
        and prod_set["per_qid"]["it-responsabilita-medica"]["n_in_product_counter_set"] == 1
        and "4 of the 15" in report)
    add("F1-5", "the report's §4(b) headline names its definition at the point of the claim",
        _section(report, "## 4.", "## 5.") is not None
        and "EMITTED" in _section(report, "## 4.", "## 5.")
        and "product-defined counter rows" in _section(report, "## 4.", "## 5."))
    cf = state["critical_findings"]["the_answer_cites_no_counter_authority_at_all"]
    add("F1-6", "state.critical_findings carries the same qualification",
        "EMITTED" in cf and "4 of the 15" in cf)
    oi = state["open_items"]["counter_authority_yield_negative"]
    add("F1-7", "state.open_items carries both counts, the abstentions and the yield",
        "60 abstention" in oi and "65/642" in oi and "5/642" in oi)
    cc = state["claim_ceiling"]
    add("F1-8", "state.claim_ceiling no longer asserts the unqualified zero",
        "EMITTED" in cc and "4 of the 15" in cc)

    # --------------------------------------------------- F-4 / F-5 / F-8 record
    add("F4-1", "n_abstained_unevidenced_rows reads 23/15/22, not 0",
        {q: v["n_abstained_unevidenced_rows"] for q, v in l2.items()} == {
            "de-kapitalverletzung": 23, "fr-bail-entretien": 15,
            "it-responsabilita-medica": 22}
        and all(v["n_abstained_unevidenced_rows"]
                == v["counter_status_histogram_all_rows"]["abstained_unevidenced"]
                for v in l2.values()))
    l1c = l1agg["controls_per_qid"]
    add("F5-1", "unexercised_reading is conditional, not a constant",
        all(v["unexercised_reading"].startswith("EXERCISED")
            for q, v in l1c.items() if not v["unexercised_checks"])
        and all(v["unexercised_reading"].startswith("UNEXERCISED")
                for q, v in l1c.items() if v["unexercised_checks"])
        and l1c["fr-bail-entretien"]["unexercised_checks"])
    src = (REPO_ROOT / INSTRUMENT_REL).read_text(encoding="utf-8")
    scratch = src.split("SCRATCH-RUN OBLIGATION", 1)[1].split('"""', 1)[0]
    add("F8-1", "the module docstring names the real --out-dir flag, not --report",
        "--out-dir" in scratch and "--report" not in scratch)
    add("F8-2", "the unused DEFAULT_REPORT constant is gone",
        "DEFAULT_REPORT =" not in src)

    # --------------------------------------------------------- F-3 generators
    m = GENERATOR_COMMIT_RE.search(report)
    gen_ok = bool(m)
    gen_detail = m.group(1) if m else "no 'Generators committed at: <sha>' line in the report"
    if m:
        sha = m.group(1)
        for path in ("evaluation/reproduction_check_39202185384.py",
                     "evaluation/report_claim_check_39202185384.py"):
            ok, out = _git("cat-file", "-e", f"{sha}:{path}")
            gen_ok = gen_ok and ok
            if not ok:
                gen_detail = f"{sha}:{path} -> {out}"
    add("F3-1", "the report names a commit that really contains both generators",
        gen_ok, gen_detail)
    add("F3-2", "both generator modules exist in this tree",
        (REPO_ROOT / "evaluation/reproduction_check_39202185384.py").is_file()
        and (REPO_ROOT / "evaluation/report_claim_check_39202185384.py").is_file())
    add("F3-3", "both generator paths are quoted in the report",
        "evaluation/reproduction_check_39202185384.py" in report
        and "evaluation/report_claim_check_39202185384.py" in report)
    add("F3-4", "the reproduction artifact records this module as its generator",
        repro["generator"] == "evaluation/reproduction_check_39202185384.py"
        and repro["generator_sha256"]
        == sha256_file(REPO_ROOT / "evaluation/reproduction_check_39202185384.py"))
    add("F3-5", "the reproduction artifact's instrument/record digests match this tree",
        repro["instrument_sha256"] == sha256_file(REPO_ROOT / INSTRUMENT_REL)
        and repro["committed_record_sha256"] == rec_sha)

    # ------------------------------------------------- F-6 control substitution
    s7 = _section(report, "## 7.", "## 8.")
    add("F6-1", "report §7 discloses the L3 control substitution and why the frozen "
                "control could not execute as written",
        s7 is not None and "substitut" in s7.lower()
        and "could not execute as written" in s7
        and "C1_empty_query" in s7 and "C2_swapped_query" in s7)
    add("F6-2", "the frozen hypothesis itself is untouched (re-hashed, unchanged)",
        sha256_file(REPO_ROOT / HYPOTHESIS_REL) == hyp_sha
        and hyp["frozen_at"] and "pre_freeze_disclosure" in hyp)

    # ------------------------------------------------- F-7 state summary + F-2
    summary = state["summary"]
    add("F7-1", "state.summary describes cycle 39202185384, not the previous cycle",
        "39202185384" in str(summary.get("cycle"))
        and "repair round 1 of rejected cycle 39199651952" not in str(summary.get("cycle")))

    # ------------------------------------------------------ reproduction claims
    add("RP-1", "the reproduction artifact says the record reproduces",
        repro["reproduces"] is True and repro["verdict_reproduces"] is True
        and repro["pins_reproduce"] is True)
    add("RP-2", "zero SUBSTANTIVE differing leaves, and the leaf walk really ran",
        repro["n_substantive_differing_leaves"] == 0
        and repro["n_substantive_differing_leaves_alternate_root"] == 0
        and repro["self_check"]["pass"] is True
        and repro["self_check"]["leaf_walk_counted"] >= repro["self_check"]["min_leaves_required"])
    add("RP-3", "the report quotes the reproduction figures that reproduce",
        str(repro["n_leaves_compared"]) in report
        and "0 substantive" in report)
    add("RP-4", "root-directory dependence is disclosed and measured, not asserted",
        repro["root_directory_dependence"]["measured_not_asserted"] is True
        and repro["root_directory_dependence"]["alternate_root"]["n_differed"] == 12
        and "root-directory" in report)
    add("RP-5", "the checker's past false clean is disclosed in the report",
        "never called it" in report and repro["self_check"]["leaf_walk_counted"] > 0)

    # ------------------------------------------------- frozen bars re-hashed
    for rel, prefix, short in (
        ("evaluation/frozen_bars/RULES_LABEL.json", "4457e971", "4457e971"),
        ("evaluation/frozen_bars/RULES_GEOMETRY.json", "a7452748", "a7452748"),
        ("evaluation/retrieval_gate/frozen_retrieval_benchmark.json", "187b0e54", "187b0e54"),
        ("evaluation/retrieval_gate/FREEZE_RECORD.json", "b06a2ad0", "b06a2ad0"),
    ):
        expect = hyp["frozen_inputs"]["lane_frozen_sha256"][rel]
        actual = sha256_file(REPO_ROOT / rel)
        add(f"FZ-{short[:4]}", f"frozen {rel} re-hashes to its pinned digest and is quoted",
            actual == expect == hyp["frozen_inputs"]["lane_frozen_sha256"][rel]
            and expect.startswith(prefix) and short in report,
            actual[:16])

    # ------------------------------------------------------------ environment
    env = record["numeric_environment"]
    add("ENV-1", "numeric environment quoted in the report matches the record",
        env["python"] in report and env["numpy"] in report
        and env["scipy"] in report and env["sklearn"] in report
        and env["numpy_blas"] in report)

    # ---------------------------------------------------- language + provenance
    shares = [l4[q]["question_language_share"] for q in
              ("de-kapitalverletzung", "fr-bail-entretien", "it-responsabilita-medica")]
    add("L4-1", "question-language shares 0.4206 / 0.1797 / 0.3318 as published",
        shares == [0.4206, 0.1797, 0.3318]
        and all(str(s) in report for s in shares))
    unlab = [l4[q]["language_histogram"].get("?", 0) for q in
             ("de-kapitalverletzung", "fr-bail-entretien", "it-responsabilita-medica")]
    add("L4-2", "rows without a language 50 / 37 / 47 as published",
        unlab == [50, 37, 47] and all(str(n) in report for n in unlab))
    absent = [l4[q]["source_url"]["n_rows_without_source_url"] for q in
              ("de-kapitalverletzung", "fr-bail-entretien", "it-responsabilita-medica")]
    hosts = [l4[q]["source_url"]["n_hosts"] for q in
             ("de-kapitalverletzung", "fr-bail-entretien", "it-responsabilita-medica")]
    add("L4-3", "source_url absent 35/37/35 and hosts 24/17/11 as published",
        absent == [35, 37, 35] and hosts == [24, 17, 11]
        and all(str(n) in report for n in absent + hosts))
    lat = [l4[q]["latency_recorded_in_bytes"]["latency_seconds_total"] for q in
           ("de-kapitalverletzung", "fr-bail-entretien", "it-responsabilita-medica")]
    add("L4-4", "latency totals quoted in the report match the record",
        lat == [115.463, 251.653, 188.637] and all(str(v) in report for v in lat))
    add("L4-5", "geometry signature reproducible and order-invariant on all three",
        all(v["determinism"]["geometry_signature_reproducible"]
            and v["determinism"]["geometry_signature_order_invariant"]
            and v["determinism"]["bundle_sha256_stable"]
            for v in l4.values()))
    add("L4-6", "0 duplicate cores and 0 off-contract canonical_url as published",
        all(v["duplicate_suppression_frozen_rule"]["n_duplicate_cores"] == 0
            and v["canonical_url"]["n_off_contract"] == 0 for v in l4.values()))
    add("L4-7", "fixture_mode false / mode live on all three",
        all(v["fixture_mode"] is False and v["mode"] == "live" for v in l4.values()))

    # -------------------------------------------------------- test-count claims
    cyc = _pytest_summary([CYCLE_TEST_FILE])
    five = _pytest_summary(FIVE_TEST_FILES)
    cyc_counts = cyc.get("counts") or {}
    add("T-1", "the report's '34 passed' reproduces from a fresh pytest run",
        cyc_counts.get("passed") == 34 and cyc_counts.get("failed", 0) == 0
        and "34 passed" in report,
        cyc.get("summary_line") or cyc.get("error"))
    f_counts = five.get("counts") or {}
    add("T-2", "the report's 102 passed / 1 skipped / 4 failed reproduces",
        f_counts.get("passed") == 102 and f_counts.get("skipped") == 1
        and f_counts.get("failed") == 4
        and "102 passed, 1 skipped, **4 failed**" in report,
        five.get("summary_line") or five.get("error"))
    add("T-3", "no UNNEGATED universal test-pass claim appears in the report",
        _no_unnegated_universal_test_claim(report))

    # ----------------------------------------------------------- side-by-side
    sbs = record["side_by_side_lane_own_numbers"]
    add("SB-1", "the lane's own 39200567493 numbers are published beside, not instead",
        sbs["status"] == "PRESENT" and sbs["run_id"] == "39200567493"
        and "39200567493" in report)
    add("SB-2", "frontier-query-concept-recall is cited as its own result, not re-scored",
        record["frontier_query_concept_recall_outcome_of_record"][
            "recomputed_by_this_run"] is False)

    # --------------------------------------------------- F-2 count self-consistency
    total = len(checks) + 2  # these two count checks complete the list
    literal = f"{total}/{total}"
    add("F2-1", "the report's quoted check count equals this artifact's n_checks/n_pass",
        literal in report, f"expected literal {literal}")
    add("F2-2", "state.verification_note quotes the same count and pass=true",
        literal in state["verification_note"] and "pass=true" in state["verification_note"],
        f"expected literal {literal}")

    assert len(checks) == total, (len(checks), total)
    return checks


def _section(report: str, start: str, end: str) -> str | None:
    i = report.find(start)
    if i < 0:
        return None
    j = report.find(end, i + len(start))
    return report[i:j if j > 0 else len(report)]


_NEGATION_RE = re.compile(r"\b(no|not|never|without|neither|nor)\b", re.I)


def _no_unnegated_universal_test_claim(report: str) -> bool:
    """A universal 'all tests pass' is only allowed as a disclosed negation."""
    for m in re.finditer(r"all tests pass", report, re.I):
        window = report[max(0, m.start() - 80):m.start()]
        if not _NEGATION_RE.search(window):
            return False
    for m in re.finditer(r"all \d+ tests pass", report, re.I):
        return False
    return True


def main(argv=None) -> int:
    checks = build_checks()
    n_pass = sum(1 for c in checks if c["ok"])
    n_fail = len(checks) - n_pass
    report_path = REPO_ROOT / REPORT_REL
    record_path = REPO_ROOT / RECORD_REL
    repro_path = REPO_ROOT / REPRO_REL
    out = {
        "schema": SCHEMA,
        "run_id": RUN_ID,
        "generator": "evaluation/report_claim_check_39202185384.py",
        "generator_sha256": sha256_file(Path(__file__)),
        "report": REPORT_REL,
        "report_sha256": sha256_file(report_path),
        "record_sha256": sha256_file(record_path),
        "state": STATE_REL,
        "state_sha256": sha256_file(REPO_ROOT / STATE_REL),
        "hypothesis_sha256": sha256_file(REPO_ROOT / HYPOTHESIS_REL),
        "reproduction_check_sha256": sha256_file(repro_path),
        "note": ("Re-derives this cycle's report and state claims from committed "
                 "bytes, from the pinned served packet (re-hashed first) and from "
                 "fresh pytest executions. n_checks is this module's list length, "
                 "not a number read from the report; F2-1/F2-2 assert that the "
                 "report's and the state's quoted N/N equals it."),
        "n_checks": len(checks),
        "n_pass": n_pass,
        "n_fail": n_fail,
        "failed": [c for c in checks if not c["ok"]],
        "pass": n_fail == 0,
        "checks": checks,
    }
    out_path = REPO_ROOT / OUT_REL
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n",
                        encoding="utf-8")
    print(json.dumps({k: out[k] for k in
                      ("schema", "run_id", "n_checks", "n_pass", "n_fail", "pass")},
                     indent=2))
    for c in out["failed"]:
        print("FAIL", c["id"], c["claim"], "->", c["detail"])
    return 0 if out["pass"] else 1


if __name__ == "__main__":  # pragma: no cover - CLI
    raise SystemExit(main())

"""Machine-check: every number in REPORT.md section 9 is TRUE OF THE ARTIFACTS.

Charter-1 RF1 was a promoted one-liner falsified three lines below by its own
table. The same discipline applies to the section-9 addendum: a human-readable
addendum is exactly the kind of prose an auditor cannot check by eye. This script
derives each claimed number FROM the emitted report.json and asserts the rendered
string is present in the report, so a table that drifts from the artifacts fails
the check instead of shipping.

Exit 0 + CHECK-OK lines only if every claim holds.
Usage: PYTHONPATH=frontier/frontier-map-semantics python3 check_report_numbers.py
"""
import json
import sys
from pathlib import Path

ROOT = Path("results/frontier/frontier-map-semantics")
REPORT = Path("reports/frontier/frontier-map-semantics/REPORT.md")
GATE = ["de-kapitalverletzung", "fr-bail-entretien", "it-responsabilita-medica"]
CONTEXT = "additional-287"
ALTS = ["A1_drop_unhydrated", "A2_language_aware_tfidf", "A3_mds_cosine"]
SUITE = Path("tests/frontier/frontier-map-semantics/test_harness.py")

# The 8 repeats of the same RF1 shape across four cycles: a claim-bearing report
# section asserting something its own artifacts contradict. Audit CYCLE_38849595347
# fixes R1-R4 for exactly this document, so each fixed claim now gets a checker.
# Anything below that is only a string test is worthless: every number is derived
# from the emitted artifact and the rendered text is required to carry it.
OVERCLAIM_PATTERNS = [
    r"MET on all three gate bundles",
    r"MET on all 3 gate bundles",
    r"test 4[^.]{0,80}\bis\b[^.]{0,40}\bMET\b[^.]{0,40}\ball (?:three|3)\b",
    r"acceptance test 4[^.]{0,80}\bMET on (?:all|every)\b",
]


def check_absent(cond, msg):
    if not cond:
        print(f"CHECK-FAIL: {msg}")
        sys.exit(1)
    print(f"CHECK-OK: {msg}")


def check(cond, msg):
    if not cond:
        print(f"CHECK-FAIL: {msg}")
        sys.exit(1)
    print(f"CHECK-OK: {msg}")


def main(report_path=None, root=None):
    global ROOT, SUITE
    if root is not None:
        ROOT = Path(root)
    if report_path is not None:
        REPORT_OVERRIDE = Path(report_path)
    else:
        REPORT_OVERRIDE = REPORT
    text = REPORT_OVERRIDE.read_text()
    # Markdown hard-wraps inside sentences, so any prose claim can straddle a
    # newline. Collapse whitespace once and do every substring/count check on the
    # flattened text: a claim must not be able to pass or fail merely because the
    # author wrapped the line differently.
    flat = " ".join(text.split())
    check("## 9. Operational resume (run 38846038296)" in text,
          "report carries the section-9 addendum for this run")

    # ---- movability audit: the claimed 3/11 and 5/11 caps -----------------
    for b in GATE + [CONTEXT]:
        rep = json.loads((ROOT / b / "report.json").read_text())
        nv = rep["nonvacuity"]
        ch, fu = nv["charter"], nv["full"]
        check(ch["n_movable_criteria"] == 3 and ch["n_invariant_criteria"] == 8,
              f"{b} charter movability 3 movable / 8 invariant")
        check(fu["n_movable_criteria"] == 5 and fu["n_invariant_criteria"] == 6,
              f"{b} full movability 5 movable / 6 invariant")
        check(f"**{ch['n_movable_criteria']} / 11**" in text,
              f"{b} charter movable count appears in the report table")
        check(f"**{fu['n_movable_criteria']} / 11**" in text,
              f"{b} full movable count appears in the report table")
        for c in ch["movable_criteria"]:
            check(c in text, f"{b} movable criterion {c} named in the report")

    # ---- positive control: flips, bounds, reachability ---------------------
    expect = {
        "de-kapitalverletzung": dict(flips=2, lang=0.055, term=0.041),
        "fr-bail-entretien": dict(flips=2, lang=0.041, term=0.329),
        "it-responsabilita-medica": dict(flips=2, lang=0.111, term=0.178),
        CONTEXT: dict(flips=1, lang=0.005, term=0.056),
    }
    for b, exp in expect.items():
        rep = json.loads((ROOT / b / "report.json").read_text())
        pc = rep["nonvacuity"]["positive_control"]
        check(pc["n_flips"] == exp["flips"],
              f"{b} positive-control flips == {exp['flips']}")
        check(pc["passed"] is (exp["flips"] >= 2),
              f"{b} positive-control assertion flag == flips>=2")
        check(pc["control_kind"] == "positive_control_not_corruption",
              f"{b} positive control is labelled a control, not a corruption")
        # the shipped value quoted in the addendum table
        check(f"{exp['lang']:.3f}" in text, f"{b} shipped coherence_lang {exp['lang']:.3f} in report")
        # reachability must be derived, never asserted
        bar = rep["criteria"]["COHERENCE_QUERY_LANG"]["bar"]
        reachable = pc["max_reachable_query_lang_share"] >= bar
        check(pc["coherence_lang_reachable"] is reachable,
              f"{b} coherence_lang reachability flag is the computed comparison")
        # the control attains the hard upper bound it claims
        check(abs(pc["values"]["COHERENCE_QUERY_LANG"]
                  - pc["max_reachable_query_lang_share"]) < 1e-9,
              f"{b} positive control attains max_reachable_query_lang_share")

    # ---- the 287 bundle's provably-unreachable language share -------------
    ctx = json.loads((ROOT / CONTEXT / "report.json").read_text())
    pc = ctx["nonvacuity"]["positive_control"]
    check(pc["coherence_lang_reachable"] is False,
          "287 coherence_lang_reachable is False")
    check(pc["n_rows_query_language"] == 37 and pc["n_decisions"] == 287,
          "287 holds 37 query-language rows of 287")
    check("37/195 = **0.190**" in text,
          "287 max attainable share 37/195 rendered in the report")

    # ---- frozen control results reported unchanged ------------------------
    for b, n in (("de-kapitalverletzung", 2), ("fr-bail-entretien", 2),
                 ("it-responsabilita-medica", 1), (CONTEXT, 1)):
        nv = json.loads((ROOT / b / "report.json").read_text())["nonvacuity"]
        check(nv["charter"]["n_flips"] == n, f"{b} frozen charter flips still {n}")
        check(nv["charter"]["corrupted_overall"] == "FAIL",
              f"{b} frozen corrupted geometry still FAILs")
        check(nv["full"]["corrupted_overall"] == "FAIL",
              f"{b} frozen full corrupted geometry still FAILs")
    for b in ("it-responsabilita-medica", CONTEXT):
        nv = json.loads((ROOT / b / "report.json").read_text())["nonvacuity"]
        check(nv["passed"] is False,
              f"{b} frozen nonvacuity.passed still False (not redefined to hide)")

    # ---- verdict counts and frozen-file identity quoted in the addendum ----
    for b, n in (("de-kapitalverletzung", 5), ("fr-bail-entretien", 5),
                 ("it-responsabilita-medica", 4)):
        rep = json.loads((ROOT / b / "report.json").read_text())
        got = sum(1 for v in rep["criteria"].values() if v["pass"])
        check(got == n and f"{n}/11" in text, f"{b} {n}/11 passes named in report")
    import hashlib
    h = hashlib.sha256((ROOT / "RULES.json").read_bytes()).hexdigest()
    check(h in text, "RULES.json freeze sha256 quoted in the report matches the file")
    check(h == "a7452748d40c511a14a1c7848ece5fe7f8f8901cc30f45a66918c89eb593a633",
          "RULES.json still byte-identical to its freeze value")

    # ---- no truncation marker anywhere in the report ----------------------
    # Section 8 QUOTES the literal marker that run 38839351403 left behind, so
    # match the numeric tool form rather than any mention of the words.
    import re
    check(re.search(r"\[\s*truncated\s+\d+\s+chars?\]", text) is None,
          "report carries no numeric tool truncation marker")

    # ---- R2: the section-5 table states the relation collapse, derived ------
    # Audit CYCLE_38849595347 R2: the DE cell claimed A1 "fixes COH x2" and left
    # out the five criteria A1 actually fails, the decisive one being RELATIONS.
    SHIPPED_REL = 25
    rel_by_bundle = {}
    for b in GATE:
        rep = json.loads((ROOT / b / "report.json").read_text())
        shipped = {k: v["pass"] for k, v in rep["criteria"].items()}
        check(rep["criteria"]["RELATIONS"]["value"] == SHIPPED_REL,
              f"{b} shipped RELATIONS really is {SHIPPED_REL} edges")
        check(shipped["RELATIONS"] is True,
              f"{b} shipped RELATIONS is a PASS (the alternatives must lose it)")
        alt = json.loads((ROOT / b / "alternatives.json").read_text())
        for a in ALTS:
            v = alt[a]
            check(v["error"] is None and v["overall"] == "FAIL",
                  f"{b} {a} measured FAIL with no error")
            check(alt["best"] is None, f"{b} best alternative is None")
            check(v["within_budget"] is True and v["elapsed_s"] < 2.0,
                  f"{b} {a} inside the frozen 2 s budget")
            # the verdict delta the cell must be derived from
            n_alt = sum(v["criteria"].values())
            gains = sorted(k for k in v["criteria"]
                           if v["criteria"][k] and not shipped[k])
            check(f"FAIL {n_alt}/{len(v['criteria'])}" in flat,
                  f"{b} {a} pass count {n_alt}/{len(v['criteria'])} rendered")
            for g in gains:
                check(g in flat, f"{b} {a} gain {g} named in the report")
            # R2: every alternative flips RELATIONS PASS -> FAIL.
            check(not v["criteria"]["RELATIONS"] and shipped["RELATIONS"],
                  f"{b} {a} flips RELATIONS PASS -> FAIL")
            check(v["values"]["RELATIONS"] < 10,
                  f"{b} {a} drops RELATIONS below the frozen 10-edge bar")
            rel_by_bundle.setdefault(b, []).append(v["values"]["RELATIONS"])
    n_cells = len(GATE) * len(ALTS)
    check(flat.count("loses RELATIONS") >= n_cells,
          f"alternatives table names the RELATIONS loss in all {n_cells} "
          f"alt-bundle cells (found {flat.count('loses RELATIONS')})")
    for b in GATE:
        rels = rel_by_bundle[b]
        check(len(set(rels)) == 1 and rels[0] < SHIPPED_REL,
              f"{b} all three alternatives collapse RELATIONS to {rels[0]}")
    check(f"{SHIPPED_REL} -> {rel_by_bundle[GATE[0]][0]} on DE" in flat
          or f"{SHIPPED_REL} → {rel_by_bundle[GATE[0]][0]} on DE" in flat,
          "report states the DE relation collapse 25 -> 1 explicitly")
    check(f"{SHIPPED_REL} -> {rel_by_bundle[GATE[1]][0]} on FR and IT" in flat
          or f"{SHIPPED_REL} → {rel_by_bundle[GATE[1]][0]} on FR and IT" in flat,
          "report states the FR/IT relation collapse 25 -> 0 explicitly")

    # ---- R3: the wall-time column carries the committed elapsed_s values ----
    # Audit CYCLE_38849595347 R3: three hand-typed ranges matched nothing in
    # alternatives.json. The committed number is now required to appear.
    slowest = 0.0
    for b in GATE:
        alt = json.loads((ROOT / b / "alternatives.json").read_text())
        for a in ALTS:
            e = alt[a]["elapsed_s"]
            slowest = max(slowest, e)
            check(f"{e:.4f}" in flat,
                  f"{b} {a} committed elapsed_s {e:.4f} in the report")
    check(slowest < 2.0 and f"{slowest:.4f} s" in flat,
          f"report compares the slowest committed cell {slowest:.4f} s "
          f"against the frozen 2.0 s budget")

    # ---- R4: the quoted test count is the suite's own count ----------------
    n_tests = len(re.findall(r"^def test_", SUITE.read_text(), re.M))
    check(n_tests >= 11, f"suite still holds >= 11 test functions (has {n_tests})")
    for stale in ("**10 passed**", "**6 passed**", "— 6 passed"):
        check_absent(stale not in flat,
                     f"no stale test count {stale!r} survives in the report")
    check(flat.count(f"**{n_tests} test functions**") >= 2,
          f"report quotes the suite's real count (**{n_tests} test functions**) "
          f"in >= 2 places (found {flat.count(f'**{n_tests} test functions**')})")

    # ---- R1: the acceptance-test-4 sentence matches the frozen artifacts ----
    flips = {b: json.loads((ROOT / b / "report.json").read_text())["nonvacuity"]
             ["charter"]["n_flips"] for b in GATE + [CONTEXT]}
    passed = {b: json.loads((ROOT / b / "report.json").read_text())["nonvacuity"]
              ["passed"] for b in GATE + [CONTEXT]}
    check(flips[GATE[0]] == 2 and flips[GATE[1]] == 2 and flips[GATE[2]] == 1,
          "frozen control flips are 2 / 2 / 1 on DE / FR / IT")
    check(passed[GATE[0]] is True and passed[GATE[1]] is True
          and passed[GATE[2]] is False,
          "frozen nonvacuity.passed is true / true / false on DE / FR / IT")
    for b in GATE:
        pc = json.loads((ROOT / b / "report.json").read_text())[
            "nonvacuity"]["positive_control"]
        check(pc["n_flips"] == 2,
              f"{b} positive control independently reaches 2 flips")
    met = [b for b in GATE if flips[b] >= 2]
    unmet = [b for b in GATE if flips[b] < 2]
    check(len(met) == 2 and len(unmet) == 1,
          "the frozen assertion is MET on exactly 2 of 3 gate bundles")
    check(f"2 / 2 / **{flips[GATE[2]]}**" in flat,
          "report renders the per-bundle frozen flip counts 2 / 2 / 1")
    check("MET on DE and FR and NOT MET on IT" in flat,
          "report states acceptance test 4 MET on DE+FR and NOT MET on IT")
    check("does **not** substitute for it" in flat,
          "report states the positive control is not a substitute for the frozen control")
    for pat in OVERCLAIM_PATTERNS:
        check_absent(re.search(pat, text) is None,
                     f"no acceptance-test-4 overclaim matching /{pat}/")

    print("ALL-CHECKS-PASSED")
    return 0


if __name__ == "__main__":
    main()

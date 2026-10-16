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


def check(cond, msg):
    if not cond:
        print(f"CHECK-FAIL: {msg}")
        sys.exit(1)
    print(f"CHECK-OK: {msg}")


def main():
    text = REPORT.read_text()
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
    print("ALL-CHECKS-PASSED")


if __name__ == "__main__":
    main()

"""Machine-check: the promoted one-sentence decision is TRUE OF THE TABLES.

Reads the emitted reports/alternatives and asserts every number/boolean the
DECISION.txt sentence claims. Exit 0 + prints CHECK-OK only if all hold.
(charter-1 RF1: promoted one-liner falsified by its own table.)
Usage: PYTHONPATH=frontier/frontier-map-semantics python check_decision.py
"""
import json
import sys
from pathlib import Path

ROOT = Path("results/frontier/frontier-map-semantics")
GATE = ["de-kapitalverletzung", "fr-bail-entretien", "it-responsabilita-medica"]
EXPECT_PASSES = {"de-kapitalverletzung": 5, "fr-bail-entretien": 5,
                 "it-responsabilita-medica": 4}
EXPECT_LANG = {"de-kapitalverletzung": 0.055, "fr-bail-entretien": 0.041,
               "it-responsabilita-medica": 0.111}
EXPECT_ARTIFACT = {"de-kapitalverletzung": True, "fr-bail-entretien": False,
                   "it-responsabilita-medica": True}


def check(cond, msg):
    if not cond:
        print(f"CHECK-FAIL: {msg}")
        sys.exit(1)
    print(f"CHECK-OK: {msg}")


def main():
    sent = (ROOT / "DECISION.txt").read_text().strip()
    check(len(sent.split(". ")) == 1 or sent.count(".") <= 3,
          "decision is a single sentence")
    for b in GATE:
        rep = json.loads((ROOT / b / "report.json").read_text())
        alt = json.loads((ROOT / b / "alternatives.json").read_text())
        n_pass = sum(1 for v in rep["criteria"].values() if v["pass"])
        check(rep["overall"] == "FAIL", f"{b} overall FAIL")
        check(n_pass == EXPECT_PASSES[b], f"{b} passes=={EXPECT_PASSES[b]} (got {n_pass})")
        check(f"{b} {n_pass}/11" in sent or f"{b.split('-')[0].upper()} {n_pass}/11" in sent
              or str(n_pass) + "/11" in sent, f"{b} count {n_pass}/11 named in sentence")
        lang = round(rep["criteria"]["COHERENCE_QUERY_LANG"]["value"], 3)
        check(abs(lang - EXPECT_LANG[b]) < 0.002, f"{b} dominant lang share {lang}")
        check(str(EXPECT_LANG[b]) in sent, f"{b} lang share in sentence")
        check(rep["ablation"]["ARTIFACT"] is EXPECT_ARTIFACT[b],
              f"{b} ARTIFACT=={EXPECT_ARTIFACT[b]}")
        check(rep["criteria"]["RELATIONS"]["pass"] is True
              and rep["criteria"]["RELATIONS"]["value"] == 25,
              f"{b} RELATIONS 25 pass")
        check(rep["criteria"]["LABEL_CONTENT_FRACTION"]["pass"] is True,
              f"{b} LABEL_CONTENT pass")
        check(alt["best"] is None, f"{b} alternatives best is None")
        for name in ("A1_drop_unhydrated", "A2_language_aware_tfidf", "A3_mds_cosine"):
            check(alt[name]["overall"] == "FAIL", f"{b} {name} FAIL")
            check(alt[name]["elapsed_s"] < 2.0, f"{b} {name} within 2 s budget")
    check("0/3" in sent, "sentence states 0/3 bundles pass")
    check("CLOSE" in sent or "close" in sent, "sentence states closure")
    fr = json.loads((ROOT / "fr-bail-entretien" / "report.json").read_text())
    hyd = round(fr["ablation"]["hydrated_largest_share"], 3)
    check("0.217" in sent and str(hyd) in sent, "FR hydrated share collapse named")
    print("ALL-CHECKS-PASSED")


if __name__ == "__main__":
    main()

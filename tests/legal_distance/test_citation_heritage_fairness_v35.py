#!/usr/bin/env python3
"""
Legal-distance v35 — citation-heritage fairness audit verification tests.

Verifies the deterministic findings of:
  legal_distance/experiments/citation_heritage_fairness_audit_v35.py
  legal_distance/experiments/citation_heritage_relation_decomposition_v35.py

Run:  python3 tests/legal_distance/test_citation_heritage_fairness_v35.py
Exits non-zero on any failed assertion.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
AUD = ROOT / "legal_distance/results/citation_heritage_fairness_audit_v35/fairness_audit_results.json"
DEC = ROOT / "legal_distance/results/citation_heritage_fairness_audit_v35/relation_decomposition_results.json"

PASS, FAIL = [], []


def check(name, cond, detail=""):
    (PASS if cond else FAIL).append(name)
    print(f"  [{'PASS' if cond else 'FAIL'}] {name}" + (f"  ({detail})" if detail else ""))


def main():
    assert AUD.exists(), f"missing {AUD}"
    assert DEC.exists(), f"missing {DEC}"
    a = json.load(open(AUD))
    d = json.load(open(DEC))

    cov = a["pair_coverage"]
    # T1: self-pairs are present at a material rate
    check("orig_self_pair_rate_material",
          cov["ORIG"]["self_pos"] >= 100 and cov["ORIG"]["self_pos"] / cov["ORIG"]["pos"] > 0.10,
          f"{cov['ORIG']['self_pos']}/{cov['ORIG']['pos']}")

    # T1b: self-pairs inflate AUC for EVERY representation by >= 0.03
    spi = a["self_pair_inflation"]
    for rep, m in spi.items():
        check(f"self_pair_inflation_ge_0.03__{rep}", m["delta"] >= 0.03, f"delta={m['delta']:.4f}")

    # T2: as-published apparent advantage reproduces (apples-to-oranges)
    pub = a["published_asreported"]
    dense_pub = pub["ORIG_all"]["dense_cp64"]["auc"]          # dense on 730 matched, w/ self
    tf_pub = pub["ORIG_all"]["cited_decisions_tfidf"]["auc"]  # tf-idf on all 1020, w/ self
    check("as_published_dense_apparently_beats_tfidf", dense_pub - tf_pub > 0.02,
          f"dense={dense_pub:.4f} tfidf={tf_pub:.4f}")

    # T2b: but on the IDENTICAL matched set with self-pairs removed, they tie
    fair = a["fair_matched"]["P_matched_no_self"]
    d64 = fair["dense_cp64"]["auc"]
    tf = fair["cited_decisions_tfidf"]["auc"]
    check("fair_matched_dense_tfidf_within_0.02", abs(d64 - tf) < 0.02, f"dense={d64:.4f} tfidf={tf:.4f}")

    # PRIMARY success rule: margin < 0.02 => claim FALSIFIED
    mg = a["margin"]
    check("primary_margin_below_success_threshold", mg["margin"] < mg["success_threshold"],
          f"margin={mg['margin']:+.4f} thr={mg['success_threshold']}")
    check("primary_verdict_falsified", mg["verdict"] == "FALSIFIED", mg["verdict"])
    check("bootstrap_ci_crosses_zero",
          mg["bootstrap"]["lo"] < 0 < mg["bootstrap"]["hi"],
          f"[{mg['bootstrap']['lo']:+.4f},{mg['bootstrap']['hi']:+.4f}]")

    # Both representations evaluated on the SAME number of pairs in the fair comparison
    check("fair_comparison_identical_pair_count",
          fair["dense_cp64"]["n_pos"] == fair["cited_decisions_tfidf"]["n_pos"] == 606,
          f"{fair['dense_cp64']['n_pos']} vs {fair['cited_decisions_tfidf']['n_pos']}")

    # Relation decomposition
    gs = d["graph_stats"]
    check("graph_stats_present", gs["sources"] == 5031 and gs["targets"] == 918,
          json.dumps(gs))

    direct_hard = d["results"]["DIRECT__NEG_hard"]
    check("faithful_citation_repr_beats_dense_on_direct",
          direct_hard["citation_jaccard_full"]["auc"] > direct_hard["dense_cp64"]["auc"],
          f"jaccard={direct_hard['citation_jaccard_full']['auc']:.4f} dense={direct_hard['dense_cp64']['auc']:.4f}")

    s2 = d["results"]["SHARED2__NEG_hard"]
    check("production_tfidf128_is_poor_citation_encoder",
          s2["tfidf_cited_decisions_128"]["auc"] < 0.72,
          f"tfidf128={s2['tfidf_cited_decisions_128']['auc']:.4f}")
    check("dense_recovers_shared2_relation",
          s2["dense_cp64"]["auc"] > 0.90,
          f"dense_cp64={s2['dense_cp64']['auc']:.4f}")
    check("citation_jaccard_oracle_on_shared",
          s2["citation_jaccard_full"]["auc"] >= 0.999,
          f"jaccard={s2['citation_jaccard_full']['auc']:.4f}")

    print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
    if FAIL:
        print("FAILED: " + ", ".join(FAIL))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

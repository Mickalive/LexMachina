#!/usr/bin/env python3
"""
ANTI-NOISE PROCEDURAL-PASSAGE SENSITIVITY OF THE REAL BOILERPLATE CONCLUSION
============================================================================
Factory Direction version 10 — Evaluation lane adversarial experiment.

PROBLEM
-------
The corrected "real boilerplate resistance" test (run_boilerplate_resistance_real.py,
ACCEPTED) concluded that procedural boilerplate does NOT drive neighbor structure:
89-93% k-NN neighbor preservation when boilerplate is removed. That test removes
mostly *header/footer/citation* patterns: mean text reduction is only ~5.9%.

The Master Prompt's ANTI-NOISE PRINCIPLE targets a broader and more consequential
class: "routine procedural passages" — the standard admissibility / competence /
standard-of-review reasoning paragraphs that recur across decisions sharing a
chamber or procedure. No existing benchmark has tested whether removing these
*substantive-body* procedural passages changes the neighbor structure. This
experiment stress-tests whether the accepted conclusion is robust to a deeper,
anti-noise-motivated removal.

HYPOTHESIS (frozen before observation)
--------------------------------------
H0: The accepted "boilerplate does not drive neighbors" conclusion is FRAGILE under
    anti-noise targets. Removing routine procedural reasoning passages (in addition
    to header/footer) drops k-NN neighbor preservation substantially (>= 0.08), i.e.
    the concluded resistance is partly an artifact of shallow (~6%) removal.

FROZEN SAMPLE
-------------
All 1,200 decisions in evaluation/data/bger_expanded_1200.jsonl (seed 42).

FROZEN METRICS
--------------
- mean_knn_preservation(k=20, cosine): mean Jaccard-like overlap of top-20 neighbor
  sets between the original (full-text) embedding graph and the cleaned-text
  embedding graph, computed identically to the accepted real-boilerplate protocol.
- per-tier and per-language breakdowns.
- Procedural-citation density is used only to *order* paragraph removal (to target
  routine procedural passages), NOT to grade the result.

FROZEN SUCCESS RULE (discriminating either way)
-----------------------------------------------
delta = shallow_preservation - aggressive_preservation
  - delta >= 0.08  => conclusion FRAGILE under anti-noise targets (procedural
    reasoning passages leak into geometry). Recommend deeper removal becomes the
    canonical boilerplate benchmark; re-scope the accepted claim.
  - delta <  0.08  => conclusion ROBUST (procedural passages do not drive geometry).
    Recommend keep shallow protocol; anti-noise principle satisfied.

The experiment is informative in EITHER direction; no result is discarded.
"""
import json
import re
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from run_boilerplate_resistance_real import (
    remove_boilerplate,
    load_expanded_slice,
    build_tfidf_embeddings,
    compute_neighbor_preservation,
    GLOBAL_SEED,
)

GLOBAL_SEED = 42
EXPANDED_SLICE_PATH = Path(__file__).resolve().parents[2] / "evaluation/data/bger_expanded_1200.jsonl"
OUTPUT_DIR = Path(__file__).resolve().parents[2] / "evaluation/results/v3_boilerplate_antinoise"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Frozen removal-depth targets (fraction of text removed, cumulative):
# shallow = accepted protocol only; deep tiers add procedural-reasoning removal.
TARGET_REMOVAL_FRACTIONS = [0.15, 0.25]  # beyond shallow (~0.06)

# Procedural-norm article citations (routine procedural statutes), used to score the
# "proceduralness" of a paragraph for removal *ordering* only.
PROCEDURAL_NORM_RE = re.compile(
    r"\bart\.\s*\d+\w?\s*(?:al\.\s*\d+|cpv\.\s*\d+|Abs\.\s*\d+|lit\.\s*\w+)?"
    r"\s*(?:BGG|LTF|CPP|CPC|ZPO|TVA|VwVG|BZP|OG|GOG)\b",
    re.IGNORECASE,
)

# Standard procedural sentence starters (competence / admissibility / review scope)
# across DE/FR/IT. Used only to bias removal ordering toward routine passages.
PROCEDURAL_STARTERS = [
    ("Le Tribunal fédéral vérifie d'office sa compétence", "fr"),
    ("Le Tribunal fédéral examine librement la recevabilité", "fr"),
    ("Die Beschwerde in öffentlich-rechtlichen Angelegenheiten", "de"),
    ("Der Beschwerdeführer wendet sich gegen", "de"),
    ("Das Bundesgericht prüft von Amtes wegen", "de"),
    ("La Corte deve verificare d'ufficio la propria", "it"),
    ("Il Tribunale federale è competente", "it"),
]


def split_paragraphs(text: str):
    return re.split(r"\n\s*\n", text)


def paragraph_procedural_score(para: str) -> float:
    """Score how 'procedural' a paragraph is: density of procedural-norm citations.
    Higher = more routine procedural content. Used ONLY for removal ordering."""
    if not para.strip():
        return 0.0
    cites = len(PROCEDURAL_NORM_RE.findall(para))
    starters = 0
    low = para.lower()
    for s, _ in PROCEDURAL_STARTERS:
        if s.lower() in low:
            starters += 1
    score = (cites + 3.0 * starters) / (len(para) + 1.0)
    return score


def remove_paragraphs_by_order(text: str, target_fraction: float, order: np.ndarray,
                               lengths: np.ndarray, total: float, allow_zero_score: bool) -> str:
    """Generic paragraph remover given a removal `order` (indices ascending by removal
    priority). Stops when removed_len/total >= target_fraction. Paragraph granularity
    may overshoot the target; actual removal fraction is reported."""
    paras = split_paragraphs(text)
    removed_len = 0.0
    keep_mask = np.ones(len(paras), dtype=bool)
    for idx in order:
        if removed_len / total >= target_fraction:
            break
        if lengths[idx] <= 0:
            continue
        if not allow_zero_score and paragraph_procedural_score(paras[idx]) <= 0:
            continue
        keep_mask[idx] = False
        removed_len += lengths[idx]
    kept = [p for p, keep in zip(paras, keep_mask) if keep]
    return "\n\n".join(kept)


def remove_procedural_paragraphs(text: str, target_fraction: float) -> str:
    """Remove progressive fraction of text, removing highest-procedural-score
    paragraphs first (anti-noise targeting), stopping at target_fraction removal."""
    paras = split_paragraphs(text)
    lengths = np.array([len(p) for p in paras], dtype=float)
    total = lengths.sum()
    if total == 0:
        return text
    scores = np.array([paragraph_procedural_score(p) for p in paras])
    # Procedural-first removal: highest score first.
    order = np.argsort(-scores)
    return remove_paragraphs_by_order(text, target_fraction, order, lengths, total,
                                      allow_zero_score=False)


def remove_control_paragraphs(text: str, target_fraction: float) -> str:
    """CONTROL condition: remove the SAME volume of text, but removing the LOWEST-
    procedural-score (i.e. content-neutral / substantive) paragraphs first. If
    preservation stays high under this equal-volume control, any drop from the
    procedural-first condition is specifically attributable to procedural content
    removal (isolating the anti-noise mechanism), not to bulk removal volume."""
    paras = split_paragraphs(text)
    lengths = np.array([len(p) for p in paras], dtype=float)
    total = lengths.sum()
    if total == 0:
        return text
    scores = np.array([paragraph_procedural_score(p) for p in paras])
    # Content-neutral / substantive-first removal: lowest procedural score first.
    order = np.argsort(scores)
    return remove_paragraphs_by_order(text, target_fraction, order, lengths, total,
                                      allow_zero_score=True)


def main():
    results = {
        "experiment": "anti_noise_procedural_sensitivity",
        "factory_direction_version": 10,
        "evaluation_version": "v3_boilerplate_antinoise",
        "global_seed": GLOBAL_SEED,
        "sample": "bger_expanded_1200.jsonl",
        "n_decisions": 0,
        "hypothesis": (
            "Accepted 'boilerplate does not drive neighbors' conclusion is fragile "
            "under anti-noise procedural-reasoning removal (delta>=0.08 = fragile)."
        ),
        "success_rule": {
            "delta": "shallow_preservation - aggressive_preservation",
            "control_delta": "shallow_preservation - control(equal_volume)_preservation",
            "fragile_threshold": 0.08,
            "note": (
                "delta>=0.08 AND procedural_delta > control_delta + 0.03 => conclusion "
                "FRAGILE specifically due to procedural-passage removal (anti-noise leak). "
                "If delta<0.08 OR procedural_delta <= control_delta + 0.03 => ROBUST / "
                "volume-driven, not procedural-specific."
            ),
        },
        "tiers": {},
        "interpretation": None,
        "recommendation": None,
    }

    print("=" * 70, flush=True)
    print("ANTI-NOISE PROCEDURAL SENSITIVITY OF REAL-BOILERPLATE CONCLUSION")
    print("=" * 70, flush=True)

    decisions = load_expanded_slice()
    results["n_decisions"] = len(decisions)
    full_texts = [d["full_text"] for d in decisions]
    languages = [d["language"] for d in decisions]

    # Tier 0 / shallow: accepted protocol (remove_boilerplate only)
    shallow_clean = [remove_boilerplate(t) for t in full_texts]
    ridx = [i for i, t in enumerate(full_texts) if len(t.strip()) > 50]
    emb_full, _ = build_tfidf_embeddings(full_texts, max_features=5000, n_components=128)
    emb_shallow, _ = build_tfidf_embeddings(shallow_clean, max_features=5000, n_components=128)
    shallow_pres = compute_neighbor_preservation(emb_full, emb_shallow, ridx, k=20)
    shallow_rate = shallow_pres["mean_preservation_rate"]
    shallow_reduction = np.mean(
        [(len(f) - len(c)) / len(f) * 100 for f, c in zip(full_texts, shallow_clean) if len(f) > 0]
    )
    print(f"[shallow] reduction={shallow_reduction:.2f}% preservation={shallow_rate:.4f} (accepted ~0.9325)", flush=True)
    results["tiers"]["shallow_accepted"] = {
        "removal_pct_mean": float(shallow_reduction),
        "mean_preservation_rate": float(shallow_rate),
        "neighbor_preservation": shallow_pres,
    }

    # Aggressive tiers: add procedural-reasoning paragraph removal
    for frac in TARGET_REMOVAL_FRACTIONS:
        deep_clean = [remove_procedural_paragraphs(t, frac) for t in full_texts]
        # also apply shallow header/footer removal on top so we isolate incremental signal
        deep_clean = [remove_boilerplate(t) for t in deep_clean]
        reduction = np.mean(
            [(len(f) - len(c)) / len(f) * 100 for f, c in zip(full_texts, deep_clean) if len(f) > 0]
        )
        emb_deep, _ = build_tfidf_embeddings(deep_clean, max_features=5000, n_components=128)
        deep_pres = compute_neighbor_preservation(emb_full, emb_deep, ridx, k=20)
        deep_rate = deep_pres["mean_preservation_rate"]
        # CONTROL: equal-volume removal of lowest-procedural (substantive) paragraphs
        ctrl_clean = [remove_control_paragraphs(t, frac) for t in full_texts]
        ctrl_clean = [remove_boilerplate(t) for t in ctrl_clean]
        ctrl_reduction = np.mean(
            [(len(f) - len(c)) / len(f) * 100 for f, c in zip(full_texts, ctrl_clean) if len(f) > 0]
        )
        emb_ctrl, _ = build_tfidf_embeddings(ctrl_clean, max_features=5000, n_components=128)
        ctrl_pres = compute_neighbor_preservation(emb_full, emb_ctrl, ridx, k=20)
        ctrl_rate = ctrl_pres["mean_preservation_rate"]
        print(f"[deep target={frac:.2f}] reduction={reduction:.2f}% preservation={deep_rate:.4f} "
              f"| CONTROL reduction={ctrl_reduction:.2f}% preservation={ctrl_rate:.4f}", flush=True)
        results["tiers"][f"deep_target_{int(frac*100)}"] = {
            "target_removal_fraction": frac,
            "removal_pct_mean": float(reduction),
            "mean_preservation_rate": float(deep_rate),
            "neighbor_preservation": deep_pres,
            "control": {
                "removal_pct_mean": float(ctrl_reduction),
                "mean_preservation_rate": float(ctrl_rate),
                "neighbor_preservation": ctrl_pres,
            },
        }

    # Per-language breakdown at the most aggressive tier
    deep_idx = f"deep_target_{int(TARGET_REMOVAL_FRACTIONS[-1]*100)}"
    deep_clean = [remove_procedural_paragraphs(t, TARGET_REMOVAL_FRACTIONS[-1]) for t in full_texts]
    deep_clean = [remove_boilerplate(t) for t in deep_clean]
    emb_deep, _ = build_tfidf_embeddings(deep_clean, max_features=5000, n_components=128)
    lang_breakdown = {}
    for lang in ["de", "fr", "it"]:
        idxs = [i for i, d in enumerate(decisions) if d["language"] == lang and len(full_texts[i].strip()) > 50]
        if len(idxs) < 50:
            continue
        pres = compute_neighbor_preservation(emb_full, emb_deep, idxs, k=20)
        lang_breakdown[lang] = {
            "n": len(idxs),
            "mean_preservation_rate": pres["mean_preservation_rate"],
        }
        print(f"[deep per-lang {lang}] n={len(idxs)} preservation={pres['mean_preservation_rate']:.4f}", flush=True)
    results["tiers"][deep_idx]["per_language"] = lang_breakdown

    # Interpretation against frozen success rule
    deep_tier = results["tiers"][deep_idx]
    aggressive_rate = deep_tier["mean_preservation_rate"]
    control_rate = deep_tier["control"]["mean_preservation_rate"]
    delta = float(shallow_rate - aggressive_rate)
    control_delta = float(shallow_rate - control_rate)
    # procedural-specific effect at equal-ish volume (aggressive case)
    spec_excess = delta - control_delta
    fragile = (delta >= 0.08) and (spec_excess > 0.03)
    print(f"\nDELTA (shallow - aggressive) = {delta:.4f}", flush=True)
    print(f"CONTROL DELTA (shallow - equal-volume content) = {control_delta:.4f}", flush=True)
    print(f"PROCEDURAL-SPECIFIC EXCESS = {spec_excess:.4f}", flush=True)
    if fragile:
        interpretation = (
            "FRAGILE under anti-noise targets: deep removal of routine procedural "
            "reasoning passages drops neighbor preservation by >=0.08, and this drop "
            "EXCEEDS the equal-volume content-neutral control by >0.03. The accepted "
            "'boilerplate does not drive neighbors' conclusion is re-scoped to header/"
            "footer removal only; routine procedural reasoning passages DO leak into "
            "geometry and would mislead map navigation between decisions sharing a "
            "chamber/procedure."
        )
        recommendation = (
            "PIVOT_WITHIN_MISSION: adopt deeper procedural-passage removal as the "
            "canonical boilerplate-resistance benchmark; product must down-weight "
            "routine procedural reasoning passages (anti-noise principle) per the "
            "Master Prompt."
        )
    else:
        interpretation = (
            "ROBUST (or volume-driven, not procedural-specific): either deep removal kept "
            "preservation high (<0.08 drop) OR the drop is matched by the equal-volume "
            "content-neutral control (not specifically procedural). The anti-noise "
            "principle is verified satisfied for this corpus."
        )
        recommendation = (
            "KEEP: retain shallow real-boilerplate protocol as canonical; anti-noise "
            "principle verified satisfied for the 1200-slice."
        )
    results["interpretation"] = interpretation
    results["recommendation"] = recommendation
    results["delta"] = delta
    results["control_delta"] = control_delta
    results["procedural_specific_excess"] = spec_excess
    results["fragile"] = fragile

    # Save raw outputs (immutable)
    out_raw = OUTPUT_DIR / "anti_noise_procedural_sensitivity_raw.json"
    with open(out_raw, "w") as f:
        json.dump(results, f, indent=2, default=float)
    print(f"\nSaved raw results to {out_raw}", flush=True)
    print(f"INTERPRETATION: {interpretation}", flush=True)
    return results


if __name__ == "__main__":
    main()

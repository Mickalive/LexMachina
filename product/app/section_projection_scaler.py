"""
LexMachina Section Projection Scaler

Blends section-specific projections (63 decisions) with the baseline
projection (1000 decisions) to produce full-corpus section-mode maps.

For each section mode, decisions WITH section projections use those positions;
decisions WITHOUT section projections fall back to the baseline projection.

Output: product/results/fractal_map/section_scaled/
"""
import json
import shutil
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np


BASELINE_DIR = Path(__file__).resolve().parent.parent / "results" / "fractal_map" / "baseline"
SECTION_DIR = Path(__file__).resolve().parent.parent / "results" / "fractal_map" / "section_experiment_clean"
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "results" / "fractal_map" / "section_scaled"

SECTION_MODES = [
    "sachverhalt",
    "erwaegungen",
    "dispositiv",
    "full_text",
    "erwaegungen_dispositiv",
    "sachverhalt_erwaegungen_dispositiv",
]

SECTION_LABELS = {
    "sachverhalt": "Facts (Sachverhalt)",
    "erwaegungen": "Reasoning (Erwägungen)",
    "dispositiv": "Holding (Dispositiv)",
    "full_text": "Full Text",
    "erwaegungen_dispositiv": "Reasoning + Holding",
    "sachverhalt_erwaegungen_dispositiv": "Facts + Reasoning + Holding",
}


def load_baseline() -> Tuple[List[str], np.ndarray]:
    """Load baseline decision IDs and 2D projection positions."""
    with open(BASELINE_DIR / "metadata.json", "r") as f:
        meta = json.load(f)
    ids = [m["decision_id"] for m in meta]
    proj = np.load(BASELINE_DIR / "projection_2d.npy")
    return ids, proj, meta


def load_section_metadata() -> List[str]:
    """Load section experiment decision IDs (order matches projection rows)."""
    with open(SECTION_DIR / "metadata.json", "r") as f:
        meta = json.load(f)
    return [m["decision_id"] for m in meta]


def build_blended_projection(
    baseline_ids: List[str],
    baseline_proj: np.ndarray,
    section_ids: List[str],
    section_proj: np.ndarray,
) -> np.ndarray:
    """Create a (1000, 2) array: section positions where available, baseline elsewhere."""
    # Build index lookup for section decisions
    section_idx = {did: i for i, did in enumerate(section_ids)}
    result = baseline_proj.copy()

    for i, did in enumerate(baseline_ids):
        if did in section_idx:
            result[i] = section_proj[section_idx[did]]

    return result


def run() -> None:
    """Generate blended section projections for the full 1000-decision corpus."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    baseline_ids, baseline_proj, baseline_meta = load_baseline()
    section_ids = load_section_metadata()

    section_idx_map = {did: i for i, did in enumerate(section_ids)}
    baseline_idx_map = {did: i for i, did in enumerate(baseline_ids)}

    # Track per-decision provenance
    decision_provenance = []
    for did in baseline_ids:
        if did in section_idx_map:
            decision_provenance.append({"decision_id": did, "source": "section_projection"})
        else:
            decision_provenance.append({"decision_id": did, "source": "baseline"})

    mode_stats = {}

    for mode_name in SECTION_MODES:
        section_proj_path = SECTION_DIR / f"projection_{mode_name}.npy"
        if not section_proj_path.exists():
            print(f"  SKIP {mode_name}: projection file not found")
            continue

        section_proj = np.load(section_proj_path)
        blended = build_blended_projection(baseline_ids, baseline_proj, section_ids, section_proj)

        # Save blended projection
        out_path = OUTPUT_DIR / f"projection_{mode_name}.npy"
        np.save(out_path, blended)

        n_section = sum(1 for p in decision_provenance if p["source"] == "section_projection")
        n_baseline = sum(1 for p in decision_provenance if p["source"] == "baseline")

        mode_stats[mode_name] = {
            "label": SECTION_LABELS.get(mode_name, mode_name),
            "total_decisions": len(baseline_ids),
            "section_decisions": n_section,
            "baseline_fallback": n_baseline,
            "coverage_pct": round(100.0 * n_section / len(baseline_ids), 1),
        }
        print(f"  {mode_name}: {n_section} section + {n_baseline} baseline = {len(baseline_ids)} total")

    # Copy baseline projection as the reference map
    shutil.copy2(BASELINE_DIR / "projection_2d.npy", OUTPUT_DIR / "projection_baseline.npy")

    # Copy section metadata (for reference)
    shutil.copy2(SECTION_DIR / "metadata.json", OUTPUT_DIR / "section_metadata.json")

    # Write metadata
    metadata = {
        "description": "Blended section + baseline projections for full 1000-decision corpus",
        "total_decisions": len(baseline_ids),
        "section_covered_decisions": len(section_ids),
        "section_modes": mode_stats,
        "decision_provenance": decision_provenance,
    }

    with open(OUTPUT_DIR / "metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)

    print(f"\nDone. Output: {OUTPUT_DIR}")
    print(f"Coverage: {len(section_ids)}/{len(baseline_ids)} decisions have section projections")


if __name__ == "__main__":
    run()

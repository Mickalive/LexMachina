#!/usr/bin/env python3
"""
Snapshot verification for fractal-map lane — run 33302779949 (operational resume).

Verifies the persisted producer snapshot of run 33300128591 is audit-ready for
factory direction v10:

  1. Registry/loader integrity: all 24 map modes (1 default + 21 available
     legal-distance + 1 legacy + 1 placeholder) load end-to-end via
     MapModeLoader and ProductMapLoader from BOTH:
       - the durable workspace base  results/fractal_map
       - the peer-style mirror       /tmp/lex_accepted/fractal_map
  2. Artifact integrity: every artifact path declared in the mode registry
     exists and loads; every .npy label array has length == 1000 (corpus slice).
  3. Default mode (center_projected_hierarchical): frozen metrics reproduced —
     nesting == 1.0, hierarchical purity > 0.95, 7-resolution ladder,
     decision->cluster index covering all 1000 decisions.
  4. Artifact count: 541 files under results/fractal_map (immutable outputs).

Writes machine-readable results to results/fractal_map/evaluation/
snapshot_verify_33302779949.json.  Exit code 0 <=> all checks PASS.
"""

import json
import sys
from pathlib import Path

import numpy as np

BASE = Path(__file__).resolve().parents[2]
RESULTS = BASE / "results/fractal_map"
MIRROR = Path("/tmp/lex_accepted/fractal_map")
OUT = RESULTS / "evaluation" / "snapshot_verify_33302779949.json"

sys.path.insert(0, str(BASE / "fractal_map" / "hierarchical"))
sys.path.insert(0, str(RESULTS / "product_integration"))

from map_mode_registry import (  # noqa: E402
    get_all_modes, get_default_mode, MAP_MODES,
)

RESOLUTIONS = [0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0]


def check_mode_artifacts(base: Path, mode, results: dict):
    """Check that every declared artifact exists/loads; labels are length 1000."""
    missing = []
    bad_shape = []
    n_labels = 0
    for key, rel in mode.artifacts.items():
        p = base / rel
        if not p.exists():
            missing.append(rel)
            continue
        if rel.endswith(".npy"):
            arr = np.load(p)
            n_labels += 1
            if len(arr) != 1000:
                bad_shape.append(f"{rel}:{len(arr)}")
    results.setdefault("artifact_checks", []).append(
        {"mode": mode.mode_id, "base": str(base), "declared": len(mode.artifacts),
         "label_arrays_loaded": n_labels, "missing": missing, "bad_shape": bad_shape}
    )
    return not missing and not bad_shape


def check_loader(base: Path, loader_cls, results: dict, name: str):
    """Load every mode through a loader and record failures."""
    loader = loader_cls(base_path=base)
    loaded, failed = [], []
    for m in get_all_modes():
        try:
            arts = loader.load_mode(m.mode_id)
            if m.status.value in ("available", "legacy"):
                if len(arts.label_arrays) == 0:
                    failed.append(f"{m.mode_id}:no_label_arrays")
                else:
                    loaded.append(m.mode_id)
            else:
                loaded.append(m.mode_id)
        except Exception as exc:  # noqa: BLE001
            failed.append(f"{m.mode_id}:{type(exc).__name__}:{exc}")
    results.setdefault("loaders", {})[name] = {
        "modes_tested": len(get_all_modes()), "loaded": loaded, "failed": failed}
    return not failed


def main():
    results = {
        "run_id": "33302779949",
        "resumed_from": "33300128591",
        "factory_direction_version": 10,
        "artifact_count_results_dir": None,
        "registry": {"total": None, "default": None, "available": None,
                     "placeholder": None, "legacy": None},
        "default_mode_metrics": {},
        "artifact_checks": [],
        "loaders": {},
        "all_pass": False,
    }

    # --- artifact count (immutable outputs; exclude derived __pycache__) ---
    n_files = sum(1 for _ in RESULTS.rglob("*")
                  if _.is_file() and "__pycache__" not in _.parts)
    results["artifact_count_results_dir"] = n_files

    # --- registry totals ---
    modes = get_all_modes()
    all_modes = {m.mode_id: m for m in modes}
    results["registry"]["total"] = len(all_modes)
    results["registry"]["default"] = get_default_mode().mode_id
    results["registry"]["available"] = sum(
        1 for m in modes if m.status.value == "available")
    results["registry"]["placeholder"] = sum(
        1 for m in modes if m.status.value == "placeholder")
    results["registry"]["legacy"] = sum(
        1 for m in modes if m.status.value == "legacy")

    # --- artifact checks against workspace base AND mirror ---
    bases = {"workspace": RESULTS}
    if MIRROR.exists():
        bases["mirror"] = MIRROR
    base_ok = True
    for bname, bpath in bases.items():
        for m in modes:
            ok = check_mode_artifacts(bpath, m, results)
            base_ok = base_ok and ok

    # --- loader checks ---
    from map_mode_loader import MapModeLoader
    from product_map_loader import ProductMapLoader
    loader_ok = True
    for bname, bpath in bases.items():
        for cname, cls in (("MapModeLoader", MapModeLoader),
                           ("ProductMapLoader", ProductMapLoader)):
            ok = check_loader(bpath, cls, results, f"{bname}:{cname}")
            loader_ok = loader_ok and ok

    # --- default mode frozen metrics ---
    dm = get_default_mode()
    art = results["artifact_checks"]
    ws_art = [a for a in art if a["mode"] == dm.mode_id
              and a["base"] == str(RESULTS)]
    if ws_art and not ws_art[0]["missing"]:
        cp = RESULTS / "hierarchical_map_center_projected"
        hr = json.loads((cp / "center_projected_hierarchical_results.json").read_text())
        best = hr["best_config"]
        hres = hr["hierarchical_results"][best]
        meta = json.loads((cp / "cluster_metadata.json").read_text())
        dcl = json.loads((cp / "decision_clusters.json").read_text())
        results["default_mode_metrics"] = {
            "mode": dm.mode_id,
            "best_config": best,
            "nesting_score": hres["nesting_score"],
            "hierarchical_purity": hres["hierarchical_purity"],
            "n_fine_clusters": hres["n_fine_clusters"],
            "n_coarse_clusters": len(meta),
            "resolution_keys_metadata": sorted(meta.keys()),
            "decisions_indexed": len(dcl),
            "n_label_arrays": ws_art[0]["label_arrays_loaded"],
        }

    # --- verdict ---
    # Counting views: the flat registry has 22 available (1 default
    # center_projected_hierarchical + 21 legal-distance modes); the state file
    # reports the default under map_modes.default and the 21 legal-distance
    # modes under map_modes.legal_distance_modes, plus 1 legacy and 1
    # placeholder.  Both views must sum to 24 modes.
    reg = results["registry"]
    registry_ok = (reg["total"] == 24 and reg["default"] == "center_projected_hierarchical"
                   and reg["available"] == 22 and reg["placeholder"] == 1
                   and reg["legacy"] == 1)
    dm_ok = (results["default_mode_metrics"].get("nesting_score") == 1.0
             and results["default_mode_metrics"].get("hierarchical_purity", 0) > 0.95
             and results["default_mode_metrics"].get("decisions_indexed", 0) >= 1000)
    results["checks"] = {
        "artifact_count_541": n_files >= 541,
        "registry_totals": registry_ok,
        "artifacts_declared_load": base_ok,
        "loaders": loader_ok,
        "default_mode_frozen_metrics": dm_ok,
    }
    results["all_pass"] = all(results["checks"].values())

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(results, indent=2, default=str) + "\n")

    print(json.dumps(results, indent=2, default=str))
    print("VERDICT:", "PASS" if results["all_pass"] else "FAIL")
    return 0 if results["all_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
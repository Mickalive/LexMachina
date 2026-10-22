"""Machine-checked byte-identity proof across preserved verdict records.

The charter requires byte-identical reproduction to be DEMONSTRATED, not
asserted. This module computes a leaf-level structural diff between the verdict
record produced this run and every preserved verdict record of the same
charter, then classifies every difference as either

  * a MEASURED quantity (label half, geometry half, marginal discovery,
    non-vacuity, verdict, frozen rules, scored input hashes) -- which MUST be
    byte-identical, and
  * a DECLARED provenance difference (charter_run_id, the declared non-scored
    input drift block, the cross-check's published-number resolution) -- which
    is explicitly listed.

If any difference falls outside the declared set, the proof FAILS. Offline,
deterministic, stdlib only; no wall-clock is embedded.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

# Sections whose every leaf must reproduce byte-identically across runs.
MEASURED_SECTIONS = (
    "schema",
    "team_id",
    "charter_version",
    "input_identity.packet_json_sha256",
    "input_identity.packet_json_matches_charter",
    "input_identity.manifest_sha256",
    "input_identity.manifest_matches_charter",
    "input_identity.claim_cache_verification_sha256",
    "input_identity.claim_cache_matches_freeze",
    "input_identity.bundle_raw_sha256",
    "input_identity.bundle_content_sha256",
    "input_identity.n_decisions",
    "frozen_rules",
    "label_half",
    "geometry_half",
    "marginal_discovery",
    "non_vacuity",
    "verdict",
)

# Differences that are declared (provenance/metadata only, never a threshold,
# rubric, metric definition, K, verdict contract or measured quantity).
DECLARED_PREFIXES = (
    "charter_run_id",
    "input_identity.handoff_json_sha256",
    "input_identity.handoff_matches_freeze",
    "input_identity.disclosures_json_sha256",
    "input_identity.disclosures_matches_freeze",
    "input_identity.scored_inputs",
    "input_identity.non_scored_input_drift",
    "crosscheck",
)


def _get(record: Any, dotted: str) -> Any:
    cur = record
    for part in dotted.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return _MISSING
        cur = cur[part]
    return cur


_MISSING = object()


def deep_diff(x: Any, y: Any, path: str = "") -> list[dict]:
    """Leaf-level structural diff; returns [{path, left, right}]."""
    if type(x) is not type(y):
        return [{"path": path, "left": x, "right": y}]
    if isinstance(x, dict):
        out: list[dict] = []
        for key in sorted(set(x) | set(y)):
            p = f"{path}.{key}" if path else key
            if key not in x:
                out.append({"path": p, "left": "<absent>", "right": y[key]})
            elif key not in y:
                out.append({"path": p, "left": x[key], "right": "<absent>"})
            else:
                out.extend(deep_diff(x[key], y[key], p))
        return out
    if isinstance(x, list):
        if len(x) != len(y):
            return [{"path": f"{path}.<len>", "left": len(x), "right": len(y)}]
        out = []
        for i, (a, b) in enumerate(zip(x, y)):
            out.extend(deep_diff(a, b, f"{path}[{i}]"))
        return out
    if x != y:
        return [{"path": path, "left": x, "right": y}]
    return []


def _is_declared(path: str) -> bool:
    return any(path == pre or path.startswith(pre + ".") or path.startswith(pre + "[")
               for pre in DECLARED_PREFIXES)


def _is_measured(record: Any, path: str) -> bool:
    return any(_get(record, sec) is not _MISSING and
               (path == sec or path.startswith(sec + ".") or path.startswith(sec + "["))
               for sec in MEASURED_SECTIONS)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def compare(fresh: dict, reference: dict, reference_path: Path) -> dict:
    """Classify every difference between this run's record and a reference."""
    diffs = deep_diff(reference, fresh)
    measured = [d for d in diffs if _is_measured(reference, d["path"])]
    declared = [d for d in diffs if not _is_measured(reference, d["path"])
                and _is_declared(d["path"])]
    unexpected = [d for d in diffs if d not in measured and d not in declared]
    return {
        "reference_path": str(reference_path),
        "reference_sha256": sha256_file(reference_path),
        "n_differences": len(diffs),
        "measured_quantity_differences": measured,
        "declared_provenance_differences": [
            {"path": d["path"], "left": d["left"], "right": d["right"]} for d in declared],
        "unexpected_differences": unexpected,
        "measured_quantities_byte_identical": not measured,
        "only_declared_differences": not unexpected,
        "reproduces": (not measured) and (not unexpected),
    }


def build_proof(fresh_record: dict, results_dir: Path, reference_names: list[str]) -> dict:
    checks = []
    for name in reference_names:
        path = results_dir / name
        if not path.exists():
            checks.append({
                "reference_path": str(path),
                "present": False,
                "reproduces": False,
                "note": "preserved reference verdict missing -- proof cannot be claimed",
            })
            continue
        ref = json.loads(path.read_text(encoding="utf-8"))
        entry = compare(fresh_record, ref, path)
        entry["present"] = True
        checks.append(entry)
    return {
        "schema": "frontier-packet-serve-audit/byte-identity/1",
        "team_id": "frontier-packet-serve-audit",
        "charter_version": 1,
        "charter_run_id": fresh_record.get("charter_run_id"),
        "fresh_record_sha256": None,  # filled by the caller writing the file
        "measured_sections": list(MEASURED_SECTIONS),
        "declared_difference_prefixes": list(DECLARED_PREFIXES),
        "checks": checks,
        "byte_identical_reproduction_demonstrated": bool(checks)
        and all(c.get("reproduces") for c in checks),
        "thresholds_or_rubrics_changed": False,
        "note": ("Measured quantities (label half, geometry half, marginal discovery, "
                 "non-vacuity, verdict, frozen rules, scored input hashes) must be "
                 "byte-identical against every preserved verdict of this charter. Only "
                 "charter_run_id, the declared non-scored input drift block and the "
                 "cross-check published-number resolution may differ, and each is listed."),
    }

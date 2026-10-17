"""Packet-admission conformance gate: are the two frozen bars actually BINDING?

Direction v50 (evaluation lane question + product obligation (1)) makes the two
accepted frozen bars a machine-readable input of packet admission:

    "...so no packet, owner card, disclosure or state field can carry
    ``ready_for_owner_session=true`` or ``human_gate_ready=true`` while
    counter-label support is below the frozen bar ``4457e971...`` or geometry
    below ``a7452748...``"

Core Evaluation OWNS THE BAR.  This module tests the one thing nobody owns:
whether that invariant holds, executably, over the ACCEPTED product artifacts.

What it does
------------
* walks a frozen population of accepted product records (packet.json,
  disclosures.json, frontier_verdicts/*.json, state/product.json);
* binds each owner-readiness claim to the packet whose bars it contradicts,
  using a deterministic, disclosed binding rule;
* reads the ACCEPTED per-packet bar status from this lane's own accepted
  record ``results/evaluation/packet_lineage_sweep/38993062549.json``
  (READ ONLY — no rubric is scored, no Frontier candidate is re-measured);
* cross-checks the served packet against the accepted Frontier verdict
  snapshot and requires the two sources to agree;
* runs a frozen non-vacuity battery (N1 must fire, N2/N3 must not, N4 re-hash)
  and SUPPRESSES every finding if any control fails;
* optionally executes Product's own ``packet_admission.assess()`` BLACK BOX in
  a child process (never imported into this module) to separate "the gate is
  broken" from "the gate was never applied to the shipped record".

Exit codes (frozen in FROZEN_HYPOTHESIS_39010105493.json)
--------------------------------------------------------
0  PACKET_ADMISSION_INVARIANT_HELD      violations == 0
1  PACKET_ADMISSION_INVARIANT_VIOLATED  violations >= 1
2  ENVIRONMENT_ERROR / ENVIRONMENT_OR_UNPROVEN, NO record emitted
   (mount absent, no gate_packet dir, bar record unreadable, or a
   non-vacuity control did not hold)

Stdlib only.  No network.  No Product import.  No frozen rubric, threshold,
bar, incumbent or recorded verdict is read for modification.  Never writes an
audit artifact.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

_MODULE_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _MODULE_DIR.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

SCHEMA = "lex-evaluation-packet-admission-conformance/1"

#: Direction-pinned frozen rubric identities (re-hashed, never re-derived).
EXPECTED_RULES_LABEL_SHA256 = (
    "4457e971df3dc5d10af2a727aa675afc15a15564c18eed4cede0af5eb41b4608"
)
EXPECTED_RULES_GEOMETRY_SHA256 = (
    "a7452748d40c511a14a1c7848ece5fe7f8f8901cc30f45a66918c89eb593a633"
)

DEFAULT_MOUNT = "/tmp/lex_accepted/product"
MOUNT_ENV = "LEX_ACCEPTED_PRODUCT_MOUNT"

#: Frozen population roots, relative to the accepted product mount.
POPULATION_GLOBS = (
    "results/product/gate_packet/*/packet.json",
    "results/product/gate_packet/*/disclosures.json",
    "results/product/frontier_verdicts/*.json",
    "state/product.json",
)

CLAIM_KEYS = ("ready_for_owner_session", "human_gate_ready")
ADMISSION_BLOCK_KEYS = ("packet_admission", "packet_admission_blocked")

#: Accepted, in-lane bar measurement record (READ ONLY).
BAR_RECORD_REL = Path("results/evaluation/packet_lineage_sweep/38993062549.json")
#: Accepted Frontier verdict snapshot used only as a cross-check of the served packet.
SERVED_PACKET_ID = "38839347028"
CROSSCHECK_REL = Path(
    "results/product/frontier_verdicts/"
    "ACCEPTED_frontier-served-packet-falsification_38880639079.json"
)

_PACKET_PATH_RE = re.compile(r"gate_packet/([A-Za-z0-9_.\-]+)")


class EnvironmentError2(Exception):
    """Environment/input failure: exit 2, never a product verdict."""


def sha256_file(path: str | Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _load_json(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise EnvironmentError2(f"unreadable JSON {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise EnvironmentError2(f"expected a JSON object at {path}")
    return data


# --------------------------------------------------------------------------- #
# N4: frozen rubric identity (re-hash before anything is used)
# --------------------------------------------------------------------------- #
def rules_identity() -> dict:
    bar_dir = _REPO_ROOT / "evaluation" / "frozen_bars"
    label = bar_dir / "RULES_LABEL.json"
    geom = bar_dir / "RULES_GEOMETRY.json"
    for p in (label, geom):
        if not p.is_file():
            raise EnvironmentError2(f"frozen rubric missing: {p}")
    obs_label = sha256_file(label)
    obs_geom = sha256_file(geom)
    ok = obs_label == EXPECTED_RULES_LABEL_SHA256 and obs_geom == EXPECTED_RULES_GEOMETRY_SHA256
    return {
        "rules_label_sha256": obs_label,
        "rules_geometry_sha256": obs_geom,
        "rules_label_expected": EXPECTED_RULES_LABEL_SHA256,
        "rules_geometry_expected": EXPECTED_RULES_GEOMETRY_SHA256,
        "rehashed_before_use": True,
        "match": ok,
    }


# --------------------------------------------------------------------------- #
# Bar status: READ the accepted per-packet measurement, never recompute it
# --------------------------------------------------------------------------- #
def load_bar_status(repo_root: Path) -> dict:
    path = repo_root / BAR_RECORD_REL
    if not path.is_file():
        raise EnvironmentError2(f"accepted bar record missing: {path}")
    rec = _load_json(path)
    per_packet = rec.get("per_packet")
    if not isinstance(per_packet, dict) or not per_packet:
        raise EnvironmentError2(f"accepted bar record has no per_packet: {path}")
    out: dict[str, dict] = {}
    for pid, entry in per_packet.items():
        gate = (entry or {}).get("gate") or {}
        label_abs = gate.get("label_absolute_status")
        geom_abs = gate.get("geometry_absolute_status")
        if not label_abs or not geom_abs:
            raise EnvironmentError2(
                f"accepted bar record lacks absolute status for packet {pid}"
            )
        counts = gate.get("geometry_per_bundle_counts") or {}
        out[pid] = {
            "packet_id": pid,
            "label_absolute_status": label_abs,
            "geometry_absolute_status": geom_abs,
            "label_n_scored": gate.get("label_n_scored"),
            "label_n_supported": gate.get("label_n_supported"),
            "geometry_per_bundle_counts": counts,
            "bars_unmet": bool(label_abs != "LABEL_SOUND" or geom_abs != "GEOMETRY_SOUND"),
            "source": str(BAR_RECORD_REL),
            "recomputed_by_this_benchmark": False,
        }
    return out


def crosscheck_served_packet(mount: Path, bar_status: dict) -> dict:
    """The accepted Frontier snapshot and the accepted in-lane record must agree."""
    path = mount / CROSSCHECK_REL
    if not path.is_file():
        raise EnvironmentError2(f"accepted Frontier verdict snapshot missing: {path}")
    snap = _load_json(path)
    half = snap.get("label_half") or {}
    ghalf = snap.get("geometry_half") or {}
    try:
        support_rate = float(half["support_rate"])
        n_bundles_pass = int(ghalf["n_bundles_pass"])
        n_bundles = int(ghalf["n_bundles"])
    except (KeyError, TypeError, ValueError) as exc:
        raise EnvironmentError2(f"snapshot half malformed: {exc}") from exc
    snap_unmet = bool(support_rate < 1.0 or n_bundles_pass < n_bundles)
    served = bar_status.get(SERVED_PACKET_ID)
    if served is None:
        raise EnvironmentError2(
            f"accepted bar record has no entry for served packet {SERVED_PACKET_ID}"
        )
    agree = bool(snap_unmet == served["bars_unmet"])
    return {
        "served_packet_id": SERVED_PACKET_ID,
        "snapshot_label_support_rate": support_rate,
        "snapshot_label_bar": 1.0,
        "snapshot_geometry_bundles_pass": n_bundles_pass,
        "snapshot_geometry_bundles": n_bundles,
        "snapshot_bars_unmet": snap_unmet,
        "lane_record_bars_unmet": served["bars_unmet"],
        "sources_agree": agree,
        "snapshot_sha256": sha256_file(path),
        "disagreement_is": "environment/evidence error, never silently resolved",
    }


# --------------------------------------------------------------------------- #
# Population walk and deterministic packet binding
# --------------------------------------------------------------------------- #
def _packet_id_from_file(path: Path, mount: Path) -> str | None:
    rel = path.relative_to(mount).as_posix()
    m = re.search(r"gate_packet/([^/]+)/", rel)
    return m.group(1) if m else None


def _bind_via_ancestors(hit_path: list[str], root: dict) -> tuple[str | None, str]:
    """Deterministic binding rule, disclosed in the record.

    Walk from the object owning the flag up to the root and take the FIRST
    level whose own subtree names exactly one distinct ``gate_packet/<id>``.
    Zero or several distinct ids at a level means that level is ambiguous and
    the walk continues.  Root reached with no unique id => unbound.
    """
    chain: list[dict] = []
    cur: object = root
    for seg in hit_path:
        if isinstance(cur, dict) and seg in cur:
            cur = cur[seg]
        elif isinstance(cur, list) and seg.isdigit():
            cur = cur[int(seg)]
        else:
            return None, "path_desync"
        if isinstance(cur, dict):
            chain.append(cur)
    # chain is owning-object-first, ancestors-last: walk it in order.
    for node in chain:
        ids = set(_PACKET_PATH_RE.findall(json.dumps(node, ensure_ascii=False)))
        if len(ids) == 1:
            return next(iter(ids)), "bound_via_enclosing_object"
    ids_root = set(_PACKET_PATH_RE.findall(json.dumps(root, ensure_ascii=False)))
    if len(ids_root) == 1:
        return next(iter(ids_root)), "bound_via_file_root"
    return None, "unbound_no_unique_gate_packet_id"


def walk_claims(obj: object, path: tuple[str, ...] = ()) -> list[dict]:
    """Every (key in CLAIM_KEYS) whose value is exactly True, with its path."""
    hits: list[dict] = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in CLAIM_KEYS and v is True:
                hits.append({
                    "key": k,
                    "json_path": ".".join(list(path) + [k]),
                    "owning_object_path": ".".join(path) if path else "<root>",
                })
            hits.extend(walk_claims(v, path + (str(k),)))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            hits.extend(walk_claims(v, path + (str(i),)))
    return hits


def _owner(obj: object, owning_path: str) -> dict:
    """The record subtree that owns the flag (for admission-block presence)."""
    if owning_path == "<root>":
        return obj if isinstance(obj, dict) else {}
    cur: object = obj
    for seg in owning_path.split("."):
        if isinstance(cur, dict):
            cur = cur.get(seg)
        elif isinstance(cur, list) and seg.isdigit():
            cur = cur[int(seg)]
        else:
            return {}
    return cur if isinstance(cur, dict) else {}


def collect_population(mount: Path) -> tuple[list[dict], list[str]]:
    """Every claim in the frozen population, with binding and block presence."""
    if not mount.is_dir():
        raise EnvironmentError2(f"accepted product mount absent: {mount}")
    files: list[Path] = []
    for glob in POPULATION_GLOBS:
        found = sorted(mount.glob(glob))
        if not found and glob.endswith("gate_packet/*/packet.json"):
            raise EnvironmentError2(f"no file matched frozen glob {glob} under {mount}")
        files.extend(found)
    if not any(p.name == "packet.json" for p in files):
        raise EnvironmentError2("population contains no gate_packet packet.json")

    claims: list[dict] = []
    for path in files:
        data = _load_json(path)
        rel = path.relative_to(mount).as_posix()
        file_pid = _packet_id_from_file(path, mount)
        for hit in walk_claims(data):
            owner = _owner(data, hit["owning_object_path"])
            block_present = any(k in owner for k in ADMISSION_BLOCK_KEYS)
            if file_pid:
                pid, how = file_pid, "bound_via_file_path"
            else:
                pid, how = _bind_via_ancestors(
                    hit["owning_object_path"].split(".") if hit["owning_object_path"] != "<root>" else [],
                    data,
                )
            claims.append({
                "file": rel,
                "key": hit["key"],
                "json_path": hit["json_path"],
                "owning_object_path": hit["owning_object_path"],
                "packet_id": pid,
                "packet_binding": how,
                "admission_block_present_on_owning_record": block_present,
                "file_sha256": sha256_file(path),
            })
    return claims, [p.relative_to(mount).as_posix() for p in files]


def evaluate_claims(claims: list[dict], bar_status: dict) -> dict:
    """Apply the FROZEN metric.  No tolerance, no interpretation."""
    rows = []
    for c in claims:
        pid = c["packet_id"]
        bar = bar_status.get(pid) if pid else None
        bound = bar is not None
        bars_unmet = bool(bar["bars_unmet"]) if bound else None
        violation = bool(
            bound and bars_unmet and not c["admission_block_present_on_owning_record"]
        )
        incoherent = bool(
            bound and bars_unmet and c["admission_block_present_on_owning_record"]
        )
        rows.append({**c,
                     "bar_status": (None if not bound else {
                         "label_absolute_status": bar["label_absolute_status"],
                         "geometry_absolute_status": bar["geometry_absolute_status"],
                         "label_n_supported": bar["label_n_supported"],
                         "label_n_scored": bar["label_n_scored"],
                         "geometry_per_bundle_counts": bar["geometry_per_bundle_counts"],
                         "bars_unmet": bar["bars_unmet"],
                         "source": bar["source"],
                         "recomputed": False,
                     }),
                     "bound_to_a_measured_packet": bound,
                     "violation": violation,
                     "incoherent_claim_with_persisted_block": incoherent})
    violations = [r for r in rows if r["violation"]]
    unbound = [r for r in rows if not r["bound_to_a_measured_packet"]]
    incoherent = [r for r in rows if r["incoherent_claim_with_persisted_block"]]
    return {
        "n_claims": len(rows),
        "n_violations": len(violations),
        "n_unbound_claims_reported_not_counted": len(unbound),
        "n_incoherent_claims_reported_not_counted": len(incoherent),
        "violations": violations,
        "unbound_claims": unbound,
        "incoherent_claims": incoherent,
        "all_claims": rows,
    }


# --------------------------------------------------------------------------- #
# Non-vacuity battery (frozen N1-N4)
# --------------------------------------------------------------------------- #
def _is_violation(claim_true: bool, bars_unmet: bool, block_present: bool) -> bool:
    return bool(claim_true) and bool(bars_unmet) and not bool(block_present)


def non_vacuity_battery(identity: dict) -> dict:
    n1 = _is_violation(True, True, False)
    n2 = _is_violation(False, True, False)
    n3 = _is_violation(True, False, False)
    n4 = bool(identity["match"])
    controls = [
        {"id": "N1_positive_must_fire", "holds": n1,
         "detail": "ready=true + bars unmet => violation"},
        {"id": "N2_negative_must_not_fire", "holds": (not n2),
         "detail": "ready=false + bars unmet => not a violation"},
        {"id": "N3_negative_must_not_fire", "holds": (not n3),
         "detail": "ready=true + bars MET => not a violation (not a tautology)"},
        {"id": "N4_rules_identity", "holds": n4,
         "detail": "RULES_LABEL/RULES_GEOMETRY re-hash to the direction-pinned shas"},
    ]
    return {
        "controls": controls,
        "n_controls": len(controls),
        "n_holding": sum(1 for c in controls if c["holds"]),
        "all_hold": all(c["holds"] for c in controls),
    }


# --------------------------------------------------------------------------- #
# Product-side positive controls (reported, never part of the pass rule)
# --------------------------------------------------------------------------- #
def obligation_2_disclosure(mount: Path) -> dict:
    """Direction v50 product obligation (2): size-based mega-cluster disclosure."""
    path = mount / "results/product/gate_packet" / SERVED_PACKET_ID / "disclosures.json"
    if not path.is_file():
        return {"status": "NOT_RUN", "reason": f"missing {path}", "holds": None}
    data = _load_json(path)
    per_question, threshold, consistent = [], None, True
    for q in data.get("questions") or []:
        d = ((q.get("v54_disclosures") or {}).get("d_mega_cluster_share_from_size") or {})
        if not d:
            continue
        thr = d.get("threshold_unchanged")
        share = d.get("share")
        fired = bool(d.get("disclosure_fired"))
        # Frozen H3 semantics: the size-based disclosure must FIRE EXACTLY WHEN
        # share >= threshold.  A question below threshold MUST NOT fire.
        should_fire = bool(
            thr is not None and share is not None and float(share) >= float(thr)
        )
        if thr is not None:
            threshold = thr
        consistent = consistent and (fired == should_fire)
        per_question.append({
            "qid": q.get("qid"),
            "share": share,
            "threshold_unchanged": thr,
            "disclosure_fired": fired,
            "should_fire": should_fire,
            "consistent": fired == should_fire,
        })
    return {
        "status": "MEASURED",
        "holds": bool(per_question) and consistent,
        "holds_semantics": (
            "disclosure_fired == (share >= threshold_unchanged) for every question; "
            "a below-threshold question firing would be over-disclosure, a "
            ">= threshold question silent would be under-disclosure"
        ),
        "n_questions_with_disclosure": len(per_question),
        "questions": per_question,
        "threshold_unchanged": threshold,
        "french_share": next(
            (p["share"] for p in per_question if p["qid"] == "fr-bail-entretien"), None
        ),
        "note": "reported as a product finding either way; not part of the pass rule",
        "source": str(path.relative_to(mount)),
    }


def human_gate_ready_scan(mount: Path) -> dict:
    hits = []
    for rel in ("results", "state"):
        root = mount / rel
        if not root.exists():
            continue
        for path in sorted(root.rglob("*.json")):
            try:
                text = path.read_text(encoding="utf-8")
            except OSError:
                continue
            if '"human_gate_ready": true' not in text:
                continue
            try:
                data = json.loads(text)
            except ValueError:
                continue
            for hit in walk_claims(data):
                if hit["key"] == "human_gate_ready":
                    hits.append({"file": path.relative_to(mount).as_posix(),
                                 "json_path": hit["json_path"]})
    return {"status": "MEASURED", "n_human_gate_ready_true": len(hits), "hits": hits,
            "holds": len(hits) == 0}


def admission_block_presence(mount: Path) -> dict:
    rows = []
    for path in sorted((mount / "results/product/gate_packet").glob("*/packet.json")):
        data = _load_json(path)
        rows.append({
            "packet": path.parent.name,
            "has_packet_admission": "packet_admission" in data,
            "has_packet_admission_blocked": "packet_admission_blocked" in data,
            "has_ready_for_owner_session_base": "ready_for_owner_session_base" in data,
            "ready_for_owner_session": data.get("ready_for_owner_session"),
        })
    return {"status": "MEASURED" if rows else "NOT_RUN",
            "n_packets": len(rows), "packets": rows}


def run_product_admission_blackbox(mount: Path, enabled: bool = True) -> dict:
    """H5: execute Product's own assess() in a CHILD PROCESS, never imported."""
    module_path = mount / "product/query/packet_admission.py"
    if not enabled:
        return {"status": "SKIPPED", "reason": "--skip-product-exec", "holds": None}
    if not module_path.is_file():
        return {"status": "NOT_RUN", "reason": f"absent {module_path}", "holds": None}
    driver = (
        "import importlib.util, json, sys\n"
        "spec = importlib.util.spec_from_file_location('pa_bm', sys.argv[1])\n"
        "m = importlib.util.module_from_spec(spec)\n"
        "spec.loader.exec_module(m)\n"
        "adm = m.assess()\n"
        "bars = adm.get('bars') or {}\n"
        "print(json.dumps({\n"
        " 'ready_for_owner_session_allowed': adm.get('ready_for_owner_session_allowed'),\n"
        " 'packet_admitted': adm.get('packet_admitted'),\n"
        " 'blocking_reason': adm.get('blocking_reason'),\n"
        " 'label_satisfied': (bars.get('counter_label') or {}).get('satisfied'),\n"
        " 'geometry_satisfied': (bars.get('map_geometry') or {}).get('satisfied'),\n"
        "}))\n"
    )
    try:
        proc = subprocess.run(
            [sys.executable, "-c", driver, str(module_path)],
            capture_output=True, text=True, timeout=120,
            cwd=str(mount),
        )
    except Exception as exc:  # pragma: no cover - environment
        return {"status": "ERROR", "reason": f"{type(exc).__name__}: {exc}",
                "holds": None, "module_sha256": sha256_file(module_path)}
    base = {
        "status": "EXECUTED",
        "executed_as": "child process; product code is NEVER imported into this module",
        "module": str(module_path),
        "module_sha256": sha256_file(module_path),
        "returncode": proc.returncode,
        "stderr_tail": (proc.stderr or "")[-500:],
    }
    if proc.returncode != 0:
        base.update({"status": "ERROR", "holds": None,
                     "reason": "child process failed"})
        return base
    try:
        out = json.loads((proc.stdout or "").strip().splitlines()[-1])
    except (ValueError, IndexError):
        base.update({"status": "ERROR", "holds": None, "reason": "unparsable child output",
                     "stdout_tail": (proc.stdout or "")[-500:]})
        return base
    base.update(out)
    base["holds"] = out.get("ready_for_owner_session_allowed") is False
    base["reading"] = (
        "the gate itself DENIES readiness today => the defect class is "
        "'the admission gate was never applied to the shipped record', not 'gate broken'"
        if base["holds"] else
        "product's own admission gate did NOT deny readiness on its committed snapshots"
    )
    base["claim_ceiling"] = (
        "Black-box execution of one product function on product's own committed "
        "snapshots. Reported as a positive control; NEVER part of the pass rule "
        "and never a bar measurement."
    )
    return base


# --------------------------------------------------------------------------- #
# Runner
# --------------------------------------------------------------------------- #
def run(run_id: str, mount: Path, *, product_exec: bool = True) -> tuple[dict, int]:
    t0 = time.time()
    identity = rules_identity()
    battery = non_vacuity_battery(identity)
    if not battery["all_hold"]:
        raise EnvironmentError2(
            "non-vacuity battery did not hold: "
            + ", ".join(c["id"] for c in battery["controls"] if not c["holds"])
        )

    bar_status = load_bar_status(_REPO_ROOT)
    crosscheck = crosscheck_served_packet(mount, bar_status)
    if not crosscheck["sources_agree"]:
        raise EnvironmentError2(
            "accepted bar sources disagree on the served packet "
            f"(snapshot={crosscheck['snapshot_bars_unmet']} "
            f"lane_record={crosscheck['lane_record_bars_unmet']})"
        )

    claims, files = collect_population(mount)
    evald = evaluate_claims(claims, bar_status)

    obs = {
        "obligation_2_mega_cluster_disclosure": obligation_2_disclosure(mount),
        "human_gate_ready_scan": human_gate_ready_scan(mount),
        "admission_block_presence": admission_block_presence(mount),
        "product_admission_blackbox": run_product_admission_blackbox(
            mount, enabled=product_exec
        ),
    }

    n_viol = evald["n_violations"]
    verdict = "PACKET_ADMISSION_INVARIANT_VIOLATED" if n_viol else "PACKET_ADMISSION_INVARIANT_HELD"
    exit_code = 1 if n_viol else 0

    record = {
        "schema": SCHEMA,
        "run_id": run_id,
        "lane": "evaluation",
        "direction_version": 50,
        "frozen_hypothesis": (
            "results/evaluation/packet_admission_conformance/"
            f"FROZEN_HYPOTHESIS_{run_id}.json"
        ),
        "started_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "product_mount": str(mount),
        "rules_identity": identity,
        "non_vacuity_battery": battery,
        "bar_status_source": {
            "record": str(BAR_RECORD_REL),
            "recomputed_by_this_benchmark": False,
            "frontier_candidates_remeasured": False,
            "packets": {k: {kk: vv for kk, vv in v.items() if kk != "source"}
                        for k, v in bar_status.items()},
        },
        "served_packet_crosscheck": crosscheck,
        "population": {
            "frozen_globs": list(POPULATION_GLOBS),
            "n_files": len(files),
            "files": files,
            "claim_keys": list(CLAIM_KEYS),
            "admission_block_keys": list(ADMISSION_BLOCK_KEYS),
        },
        "metric": evald,
        "reported_observations": obs,
        "baseline_under_test": (
            "state/product.json -> next_recommended: '...so no packet/card/state can "
            "carry ready_for_owner_session=true while counter-label support or geometry "
            "is below bar'"
        ),
        "verdict": verdict,
        "exit_code": exit_code,
        "violations_total": n_viol,
        "elapsed_s": round(time.time() - t0, 3),
        "claim_ceiling": (
            "Falsifies ONE machine-checkable invariant: an accepted product record "
            "claiming owner/human-gate readiness while an accepted frozen bar is "
            "unmet with no persisted admission block. It does NOT score either "
            "frozen rubric, does NOT re-measure any Frontier candidate, does NOT "
            "prove map usefulness to a jurist, does NOT move or meet either "
            "absolute bar, and does not author any audit artifact. human_gate_ready "
            "stays false."
        ),
        "product_execution_disclosure": (
            "product_admission_blackbox executes product/query/packet_admission.py "
            "in a child process; it is a reported positive control and is NEVER "
            "part of the pass rule. No product module is imported by this file."
        ),
    }
    return record, exit_code


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--mount", default=os.environ.get(MOUNT_ENV, DEFAULT_MOUNT))
    ap.add_argument("--out", default=None)
    ap.add_argument("--skip-product-exec", action="store_true")
    args = ap.parse_args(argv)

    try:
        record, code = run(args.run_id, Path(args.mount).resolve(),
                           product_exec=not args.skip_product_exec)
    except EnvironmentError2 as exc:
        print(f"packet admission conformance environment error: {exc}", file=sys.stderr)
        return 2

    text = json.dumps(record, ensure_ascii=False, indent=1, sort_keys=True) + "\n"
    out = Path(args.out) if args.out else (
        _REPO_ROOT / "results/evaluation/packet_admission_conformance"
        / f"{args.run_id}.json"
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    print(text, end="")
    print(
        f"\nverdict={record['verdict']} violations={record['violations_total']} "
        f"out={out}",
        file=sys.stderr,
    )
    return code


if __name__ == "__main__":
    raise SystemExit(main())

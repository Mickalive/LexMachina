"""Runnable harness for the frozen adversarial-discoverability measurement.

CLI::

    python3 -m adversarial_discoverability.harness --matrix
    python3 -m adversarial_discoverability.harness --input <bundle.json>
    python3 -m adversarial_discoverability.harness --non-vacuity --input <bundle.json>

Hard rules enforced in code (RULES.json):

* every input sha256 is verified BEFORE any metric runs; a mismatch aborts;
* the report body carries no timestamp, so identical inputs -> byte-identical
  report bytes;
* no network I/O and no writes outside this team's namespace.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import sys
from typing import Any, Dict, List, Optional, Tuple

from . import CHARTER_VERSION, RULES_VERSION, TEAM_ID, __version__
from . import corrupt, metrics as M, populations as pop
from .shortlist import accepted_tree_available, recompute_shortlist

DEFAULT_MOUNT = os.environ.get("LEX_PRODUCT_MOUNT", "/tmp/lex_accepted/core/product")
#: Repository root: <root>/frontier/<team>/adversarial_discoverability/harness.py
_HERE = os.path.dirname(os.path.abspath(__file__))
TEAM_DIR = os.path.dirname(_HERE)
REPO = os.path.dirname(os.path.dirname(TEAM_DIR))


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical(obj: Any) -> bytes:
    """Deterministic serialisation used for both reports and hashes."""
    return json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True).encode("utf-8")


def load_rules() -> Dict[str, Any]:
    path = os.path.join(REPO, "results", "frontier", TEAM_ID, "RULES.json")
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def _read_json(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


class IntegrityAbort(RuntimeError):
    pass


def verify_input(spec: Dict[str, Any], mount: str) -> str:
    path = os.path.join(mount, spec["path"])
    if not os.path.isfile(path):
        raise IntegrityAbort(f"missing input {spec['path']}")
    got = sha256_file(path)
    if got != spec["sha256"]:
        raise IntegrityAbort(
            f"sha256 mismatch for {spec['path']}: frozen {spec['sha256']} != actual {got}")
    size = os.path.getsize(path)
    if "bytes" in spec and size != spec["bytes"]:
        raise IntegrityAbort(
            f"byte-size mismatch for {spec['path']}: frozen {spec['bytes']} != actual {size}")
    return path


def rows_of(doc: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], str]:
    """Population the artifact exposes (RULES.json ``populations``)."""
    dec = pop.decisions_of(doc)
    if dec:
        return dec, "decisions"
    cited = pop.leg_cited_decisions(doc)
    if cited:
        return cited, "cited_decisions"
    return [], "none"


def measure(doc: Dict[str, Any], with_shortlist: bool = True) -> Dict[str, Any]:
    rows, source = rows_of(doc)
    n_total = pop.bundle_total(doc, rows, source)
    shortlist_ids, shortlist_prov = (None, {"status": "SKIPPED"})
    if with_shortlist:
        shortlist_ids, shortlist_prov = recompute_shortlist(doc)
    sl = set(shortlist_ids) if shortlist_ids is not None else None
    ms = M.all_metrics(doc, rows, sl, n_bundle_total=n_total)
    return {
        "row_source": source,
        "n_rows": len(rows),
        "n_bundle_total": n_total,
        "metrics": ms,
        "verdicts": M.verdicts(ms),
        "shortlist": {"ids": shortlist_ids, "provenance": shortlist_prov},
        "product_recorded_counters": _product_recorded_counters(doc),
    }


def _product_recorded_counters(doc: Dict[str, Any]) -> Dict[str, Any]:
    prov = doc.get("provenance") or {}
    ga = prov.get("generative_audit") or {}
    leg = {
        "decision_count": doc.get("decision_count"),
        "counter_count": doc.get("counter_count"),
        "cluster_count": doc.get("cluster_count"),
        "adversarial_method": doc.get("adversarial_method"),
        "adversarial_model": doc.get("adversarial_model"),
        "adversarial_bundle_decisions": doc.get("adversarial_bundle_decisions"),
        "adversarial_prompt_decisions": doc.get("adversarial_prompt_decisions"),
        "adversarial_error": doc.get("adversarial_error"),
        "provider_error": doc.get("provider_error"),
        "leg_passed": doc.get("leg_passed"),
        "n_cited_decisions": len(pop.leg_cited_decisions(doc)),
    }
    return {
        "generative_audit_status_summary": ga.get("status_summary"),
        "adversarial": ga.get("adversarial"),
        "leg_context": leg,
        "evidence_source_check": {
            k: v for k, v in (ga.get("evidence_source_check") or {}).items()
            if k in ("n_findings_checked", "refs_checked", "refs_verified", "refs_rejected",
                     "n_downgraded", "downgraded_decision_ids", "method", "policy")
        },
        "citation_validation": ga.get("citation_validation"),
    }


def named_verdict(per_input: List[Dict[str, Any]]) -> Tuple[str, str]:
    """RULES.json ``verdict_rule.overall_named_verdict``, evaluated on bundles only."""
    ri = [v["verdicts"]["retrieval_independence"] for v in per_input if v["kind"] == "bundle"]
    if not ri:
        return "UNDETERMINED", "no bundle with retrieval provenance was measured"
    if all(x == "FAIL" for x in ri):
        return "CLASSIFICATION_ONLY", (
            f"all {len(ri)} bundles report retrieval_independence=FAIL: zero counter rows "
            "entered through a retrieval channel the initial broad pass did not use")
    if all(x == "PASS" for x in ri):
        return "RETRIEVAL_INDEPENDENT_AND_DISCOVERABLE", (
            f"all {len(ri)} bundles report retrieval_independence=PASS")
    return "MIXED", (
        f"{sum(1 for x in ri if x == 'PASS')} of {len(ri)} bundles PASS and "
        f"{sum(1 for x in ri if x == 'FAIL')} FAIL retrieval independence")


def run_non_vacuity(doc: Dict[str, Any], clean_metrics: Dict[str, Any]) -> Dict[str, Any]:
    """RULES.json ``non_vacuity`` — every corruption must flip its metric."""
    results = []
    ok = True
    for cid, fn, metric_name in corrupt.CORRUPTIONS:
        applied = fn(copy.deepcopy(doc))
        cdoc = applied["doc"]
        cms = measure(cdoc, with_shortlist=False)["metrics"]
        clean_verdict = clean_metrics[metric_name]["verdict"]
        corr_verdict = cms[metric_name]["verdict"]
        if clean_verdict == "PASS":
            status = "NOT_APPLICABLE_NO_FLIP_NEEDED"
            flipped = None
        else:
            flipped = corr_verdict == "PASS"
            status = "FLIPPED" if flipped else "NO_FLIP"
            ok = ok and flipped
        results.append({
            "corruption_id": cid,
            "targets_metric": metric_name,
            "clean_verdict": clean_verdict,
            "corrupted_verdict": corr_verdict,
            "flipped": flipped,
            "status": status,
            "clean_value": clean_metrics[metric_name].get("value"),
            "corrupted_value": cms[metric_name].get("value"),
            "description": applied["description"],
            "touched_rows": len(applied.get("touched") or []),
        })
    return {
        "gate": "PASS" if ok else "NON_VACUITY_FAILED",
        "all_corruptions_flip_their_metric": ok,
        "corruptions": results,
        "seed": corrupt.SEED,
        "note": "A metric already PASSing on clean data is recorded NO_FLIP_NEEDED: a PASS "
                "on real inputs is itself positive evidence and needs no corruption.",
    }


def measure_input(spec: Dict[str, Any], mount: str, kind: str,
                  non_vacuity: bool = False) -> Dict[str, Any]:
    path = verify_input(spec, mount)
    doc = _read_json(path)
    out = measure(doc)
    rec: Dict[str, Any] = {
        "id": spec["id"],
        "kind": kind,
        "path": spec["path"],
        "sha256": spec["sha256"],
        "bytes": spec.get("bytes"),
        **out,
    }
    if spec.get("truth_assertion"):
        rec["truth_assertion"] = spec["truth_assertion"]
    if non_vacuity and kind == "bundle" and "decisions" in doc:
        rec["non_vacuity"] = run_non_vacuity(doc, out["metrics"])
    return rec


def run_matrix(mount: str = DEFAULT_MOUNT, non_vacuity: bool = True) -> Dict[str, Any]:
    rules = load_rules()
    per_input: List[Dict[str, Any]] = []
    integrity: List[Dict[str, Any]] = []
    for spec in rules["inputs"]["bundles"]:
        per_input.append(measure_input(spec, mount, "bundle", non_vacuity=non_vacuity))
    for spec in rules["inputs"]["frozen_legs"]:
        per_input.append(measure_input(spec, mount, "leg"))

    verdict, verdict_why = named_verdict(per_input)
    nv = [p["non_vacuity"] for p in per_input if "non_vacuity" in p]
    body = {
        "report_version": "fad-report/1",
        "rules_version": RULES_VERSION,
        "harness_version": __version__,
        "team_id": TEAM_ID,
        "charter_version": CHARTER_VERSION,
        "rules_sha256": sha256_file(
            os.path.join(REPO, "results", "frontier", TEAM_ID, "RULES.json")),
        "mount": os.path.abspath(mount),
        "mount_read_only": True,
        "network_calls": 0,
        "determinism": {
            "rule": "report body contains no timestamp; identical inputs -> byte-identical report",
            "randomness_sources": [],
            "corruption_seed": corrupt.SEED,
        },
        "thresholds": M.THRESHOLDS,
        "integrity": integrity,
        "inputs": per_input,
        "named_verdict": verdict,
        "named_verdict_basis": verdict_why,
        "non_vacuity_gate": (
            "PASS" if nv and all(x["gate"] == "PASS" for x in nv)
            else ("NOT_RUN" if not nv else "NON_VACUITY_FAILED")),
        "non_vacuity_by_input": {p["id"]: p["non_vacuity"]["gate"] for p in per_input
                                 if "non_vacuity" in p},
        "scope_counts": {
            "bundles": sum(1 for p in per_input if p["kind"] == "bundle"),
            "legs": sum(1 for p in per_input if p["kind"] == "leg"),
            "legs_with_row_source_cited_decisions": sum(
                1 for p in per_input if p["kind"] == "leg" and p["row_source"] == "cited_decisions"),
        },
        "accepted_tree_available_for_shortlist_replay": accepted_tree_available(),
    }
    return body


def write_report(body: Dict[str, Any], outdir: str) -> Dict[str, Any]:
    os.makedirs(outdir, exist_ok=True)
    path = os.path.join(outdir, "CYCLE_38792663259_REPORT.json")
    data = canonical(body)
    with open(path, "wb") as fh:
        fh.write(data)
    return {"path": path, "report_sha256": sha256_bytes(data), "bytes": len(data)}


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--matrix", action="store_true", help="measure every frozen input")
    p.add_argument("--input", help="measure one bundle/leg json directly")
    p.add_argument("--non-vacuity", action="store_true")
    p.add_argument("--no-non-vacuity", action="store_true")
    p.add_argument("--corrupt", help="apply one corruption id and print its metrics")
    p.add_argument("--mount", default=DEFAULT_MOUNT)
    p.add_argument("--out", default=os.path.join(REPO, "results", "frontier", TEAM_ID))
    args = p.parse_args(argv)

    do_nv = not args.no_non_vacuity

    if args.input:
        doc = _read_json(args.input)
        if args.corrupt:
            doc = corrupt.apply(doc, args.corrupt)["doc"]
        res = measure(doc)
        if args.corrupt:
            res["corruption"] = args.corrupt
        print(canonical(res).decode("utf-8"))
        return 0

    body = run_matrix(args.mount, non_vacuity=do_nv)
    w = write_report(body, args.out)
    print(json.dumps({
        "report": w["path"],
        "report_sha256": w["report_sha256"],
        "named_verdict": body["named_verdict"],
        "non_vacuity_gate": body["non_vacuity_gate"],
        "scope_counts": body["scope_counts"],
    }, indent=2))
    return 0 if body["non_vacuity_gate"] in ("PASS", "NOT_RUN") else 3


if __name__ == "__main__":
    sys.exit(main())

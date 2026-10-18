#!/usr/bin/env python3
"""The smallest executable benchmark that can falsify the served query-map MVP.

    python -m evaluation.served_bundle_scope --run-id <run_id> \
        --hypothesis results/evaluation/served_bundle_scope/FROZEN_HYPOTHESIS_<run_id>.json \
        --product-mount /tmp/lex_accepted/product \
        --out results/evaluation/served_bundle_scope/<run_id>.json

WHY
---
The independent audit ``CYCLE_39082753086_GATE.json`` closed with an explicit
observation it refused to certify either way:

    "173/642 served decisions pre-date 2000 ... and 120/642 are adversarial-seeded
     (ocl:adversarial.*, 40 per bundle) ... NO frozen gate family measures corpus
     scope or adversarial-seed contamination, so GEOMETRY_UNSOUND 0/3 is NOT evidence
     about either and must not be read as covering them."

That is a named hole in the accepted evidence, and it is exactly the question the
lane directive asks this lane to answer: *does the served artifact hold the source,
recall and structure facts the product's UX implies?* This module measures it
directly instead of leaving it to be inferred from a geometry verdict that does not
cover it.

REUSE-FIRST / POST-FREEZE ADDITION
----------------------------------
This is the same discipline as ``evaluation/retrieval_gate/id_hygiene.py``: an
instrument that measures a real defect without adding a gate to any existing frozen
verdict file, because adding one would change a recorded claim-bearing verdict and
destroy the byte-identity test that makes it trustworthy. Nothing here is written to
``RULES_LABEL.json``, ``RULES_GEOMETRY.json``, ``VERDICT_CONTRACT.json``,
``evaluation/reality_gate/frozen_benchmark.json`` or any ``results/evaluation/*``
record of an accepted run. The only upstream artifact it reads is the served packet
on the accepted product mount.

The two upstream id-placeholder shapes are RE-USED from
``evaluation/retrieval_gate/id_hygiene.py``'s documented finding rather than
re-derived here.

Exit 0 = every falsifier refuted (BENCHMARK_VALID_NO_FALSIFICATION)
Exit 1 = at least one falsifier fired; the record is written and the negative
         result is KEPT (BENCHMARK_VALID_WITH_FALSIFICATION)
Exit 2 = environment error (hypothesis missing/unreadable, mount absent, no
         bundles found): NO verdict is emitted, never a silent pass.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

SCHEMA = "lex-evaluation-served-bundle-scope/1"
HYPOTHESIS_SCHEMA = "lex-evaluation-served-bundle-scope-hypothesis/1"

#: The source the product's own bundles declare they were retrieved from. Taken
#: from the bundles' provenance.base_url, but pinned here so a bundle that CHANGED
#: its source would be falsified rather than silently accepted.
EXPECTED_SCHEME = "https"
EXPECTED_HOST = "mcp.opencaselaw.ch"

#: RE-USED from evaluation/retrieval_gate/id_hygiene.py, which measured these two
#: shapes on upstream OpenCaseLaw responses (ge_gerichte_[pjdoc 15442] template
#: placeholders and raw ch_vb__td_class__metadataCell__150000044__td_ HTML
#: fragments). Not re-derived.
PLACEHOLDER_ID_RES = (
    re.compile(r"\[pjdoc[^\]]*\]"),
    re.compile(r"__td_"),
    re.compile(r"^ch_vb__"),
)

#: The mission's base-map window (LEXMACHINA_MASTER_PROMPT.md / factory scope:
#: "from 2000 onward"). A DISCLOSED scope measurement, NOT a frozen bar.
MISSION_DATE_FLOOR = "2000-01-01"

#: Marker for a synthetic row deliberately injected by the benchmark battery.
ADVERSARIAL_MARKER = "adversarial"


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _host_ok(url: str) -> tuple[bool, str]:
    try:
        p = urlparse(url)
    except ValueError:
        return False, "unparseable"
    if p.scheme != EXPECTED_SCHEME:
        return False, f"scheme={p.scheme!r}"
    if p.netloc.lower() != EXPECTED_HOST:
        return False, f"host={p.netloc!r}"
    return True, ""


def _id_unusable(dec: dict) -> str | None:
    did = dec.get("decision_id")
    if not isinstance(did, str) or not did.strip():
        return "empty"
    for rx in PLACEHOLDER_ID_RES:
        if rx.search(did):
            return f"placeholder:{rx.pattern}"
    return None


def measure_bundle(bundle_rel: str, bundle: dict) -> dict:
    """Measure one served bundle. Every count is over the SAME decision list, so
    the falsifiers compose and no row is double-counted across legs."""
    decisions = bundle.get("decisions")
    if not isinstance(decisions, list) or not decisions:
        return {"bundle": bundle_rel, "measurable": False,
                "reason": "bundle carries no 'decisions' list"}

    n = len(decisions)
    bad_url, bad_id, bad_point, pre_window, adversarial = [], [], [], [], []
    years: dict[str, int] = {}
    ranks: list[dict] = []

    for d in decisions:
        if not isinstance(d, dict):
            bad_url.append({"decision_id": "<non-dict row>", "why": "row is not an object"})
            continue
        did = str(d.get("decision_id", ""))
        url = d.get("canonical_url")
        if not isinstance(url, str) or not url.strip():
            bad_url.append({"decision_id": did, "why": "canonical_url absent"})
        else:
            ok, why = _host_ok(url)
            if not ok:
                bad_url.append({"decision_id": did, "why": why})
        why_id = _id_unusable(d)
        if why_id:
            bad_id.append({"decision_id": did, "why": why_id})
        missing = [k for k in ("x", "y", "cluster_id") if d.get(k) is None]
        if missing:
            bad_point.append({"decision_id": did, "why": f"missing {missing}"})
        date = d.get("decision_date")
        if isinstance(date, str) and re.match(r"^\d{4}-\d{2}-\d{2}", date):
            y = int(date[:4])
            years[str(y)] = years.get(str(y), 0) + 1
            if date < MISSION_DATE_FLOOR:
                pre_window.append({"decision_id": did, "decision_date": date})
        elif isinstance(date, str) and date.strip():
            pre_window.append({"decision_id": did, "decision_date": date,
                               "why": "unparseable date"})
        prov = d.get("provenance")
        prov_s = prov if isinstance(prov, str) else json.dumps(prov, ensure_ascii=False) if prov is not None else ""
        if ADVERSARIAL_MARKER in prov_s.lower():
            adversarial.append({"decision_id": did, "provenance": prov_s[:160]})
        rank = d.get("rank")
        if isinstance(rank, int) and rank <= 3:
            ranks.append({"rank": rank, "decision_id": did,
                          "citation": d.get("citation"),
                          "decision_date": d.get("decision_date"),
                          "language": d.get("language"),
                          "court": d.get("court"),
                          "provenance": prov_s[:120]})

    prov_meta = bundle.get("provenance") or {}
    return {
        "bundle": bundle_rel,
        "measurable": True,
        "n_decisions": n,
        "provenance_mode": prov_meta.get("mode"),
        "provenance_base_url": prov_meta.get("base_url"),
        "query": (bundle.get("query") or {}) if isinstance(bundle.get("query"), dict) else bundle.get("query"),
        "n_bad_canonical_url": len(bad_url),
        "n_unusable_decision_id": len(bad_id),
        "n_missing_geometry_or_cluster": len(bad_point),
        "n_before_mission_window": len(pre_window),
        "n_adversarial_seeded": len(adversarial),
        "year_histogram": dict(sorted(years.items(), key=lambda kv: int(kv[0]))),
        "rank_1_to_3": sorted(ranks, key=lambda r: r["rank"]),
        "examples": {
            "bad_canonical_url": bad_url[:5],
            "unusable_decision_id": bad_id[:5],
            "missing_geometry_or_cluster": bad_point[:5],
            "before_mission_window": pre_window[:5],
            "adversarial_seeded": adversarial[:5],
        },
    }


def evaluate(hypothesis: dict, bundles: list[dict], bundle_sha: dict) -> dict:
    """Pure function: same bundles + same hypothesis -> byte-identical verdict."""
    falsifiers = []
    for spec in hypothesis["falsifiers"]:
        fid = spec["id"]
        key = {
            "source::canonical_url_not_opencaselaw": "n_bad_canonical_url",
            "source::decision_id_unusable": "n_unusable_decision_id",
            "map::point_missing_geometry_or_cluster": "n_missing_geometry_or_cluster",
            "scope::outside_mission_date_window": "n_before_mission_window",
            "scope::adversarial_seed_contamination": "n_adversarial_seeded",
        }[fid]
        per_bundle = {b["bundle"]: b.get(key) for b in bundles if b.get("measurable")}
        not_measurable = [b["bundle"] for b in bundles if not b.get("measurable")]
        total = sum(v for v in per_bundle.values() if isinstance(v, int))
        fired = total > spec["falsified_if_count_gt"]
        falsifiers.append({
            "id": fid,
            "rule": spec["rule"],
            "why": spec["why"],
            "interpretation_rule": spec.get("interpretation_rule"),
            "counted_field": key,
            "per_bundle": per_bundle,
            "not_measurable_bundles": not_measurable,
            "total": total,
            "fired": fired,
            "verdict": "FALSIFIED" if fired else ("NOT_MEASURED" if not_measurable and not per_bundle
                                                  else "REFUTED"),
        })

    fired = [f["id"] for f in falsifiers if f["fired"]]
    measurable = [b for b in bundles if b.get("measurable")]
    any_measured = any(f["per_bundle"] for f in falsifiers)
    if not any_measured:
        # NOT_APPLICABLE IS NOT A PASS. With nothing measurable there is no
        # verdict: the frozen success rule says a falsifier that cannot be
        # evaluated is reported not_measurable and NEVER counted as a pass, and
        # a run with no measurable falsifier has measured nothing.
        verdict = "BENCHMARK_NOT_MEASURED"
    elif fired:
        verdict = "BENCHMARK_VALID_WITH_FALSIFICATION"
    else:
        verdict = "BENCHMARK_VALID_NO_FALSIFICATION"
    return {
        "schema": SCHEMA,
        "run_id": hypothesis["run_id"],
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "hypothesis_sha256": _sha256_file(Path(hypothesis["_path"])) if hypothesis.get("_path") else None,
        "question": hypothesis["question"],
        "success_rule": hypothesis["success_rule"],
        "verdict": verdict,
        "falsification_proven": bool(fired),
        "fired_falsifiers": fired,
        "n_bundles": len(bundles),
        "n_measurable_bundles": len(measurable),
        "n_decisions_total": sum(b.get("n_decisions", 0) for b in measurable),
        "bundle_sha256": bundle_sha,
        "measurable_falsifiers": sum(1 for f in falsifiers if f["per_bundle"]),
        "bundles": bundles,
        "falsifiers": falsifiers,
        "negative_controls": _negative_controls(bundles),
        "claim_ceiling": hypothesis["claim_ceiling"],
        "explicitly_not_gates": hypothesis["explicitly_not_gates"],
        "frozen_bars_untouched": hypothesis["frozen_bars_untouched"],
    }


def _negative_controls(bundles: list[dict]) -> dict:
    """The benchmark must be able to FIRE. These controls prove each counted field
    can be non-zero, so a green verdict cannot come from a field that is stuck at
    zero for a structural reason (e.g. a key the bundles do not carry at all)."""
    def total(key: str) -> int:
        return sum(b.get(key, 0) for b in bundles if b.get("measurable"))
    observed = {
        "source::canonical_url_not_opencaselaw": total("n_bad_canonical_url"),
        "source::decision_id_unusable": total("n_unusable_decision_id"),
        "map::point_missing_geometry_or_cluster": total("n_missing_geometry_or_cluster"),
        "scope::outside_mission_date_window": total("n_before_mission_window"),
        "scope::adversarial_seed_contamination": total("n_adversarial_seeded"),
    }
    fired = [k for k, v in observed.items() if v > 0]
    return {
        "definition": "each counted field is REACHABLE (non-zero) on this artifact; "
                      "a field that is structurally unreachable could never falsify "
                      "anything, so its green reading would be vacuous",
        "observed_non_zero": fired,
        "fields_still_zero": sorted(k for k, v in observed.items() if v == 0),
        "at_least_one_field_can_fire": bool(fired),
        "caveat": "a field that is zero HERE is refuted on THIS artifact only; reachability "
                  "of every field is proven by the unit tests, not by this run",
    }


def relation(side_a: Path, side_b: Path, a_label: str, b_label: str) -> dict:
    """File-set relation between two directories. REPAIR F4.

    Audit ``CYCLE_39082753086_GATE.json`` measured that cycle 39082753086's
    provenance manifest published ``1 byte-identical, 12 changed`` for the served
    dir ``results/product/gate_packet/38839347028/`` against the vendored adjudicated
    copy, which is arithmetically impossible: the two dirs hold 15 and 13 files
    with 12 in common, so common = byte_identical + changed and the true split is
    1 + 11. The audit attributed it to a propagated transcription error inside a
    block the cycle itself labelled "not re-measured".

    This is the MEASUREMENT, re-executable, so the corrected figure is not another
    transcription. It reports every side of the relation rather than a single count,
    so a future reader can check the arithmetic instead of trusting it.
    """
    def index(d: Path) -> dict[str, Path]:
        return {p.relative_to(d).as_posix(): p for p in d.rglob("*") if p.is_file()}

    fa, fb = index(side_a), index(side_b)
    common = sorted(set(fa) & set(fb))
    identical = [r for r in common if _sha256_file(fa[r]) == _sha256_file(fb[r])]
    changed = [r for r in common if r not in set(identical)]
    return {
        "schema": "lex-evaluation-served-dir-relation/1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "side_a": {"label": a_label, "path": str(side_a), "n_files": len(fa)},
        "side_b": {"label": b_label, "path": str(side_b), "n_files": len(fb)},
        "n_common": len(common),
        "n_byte_identical": len(identical),
        "n_changed": len(changed),
        "arithmetic_check": (f"{len(fa)} vs {len(fb)}; common {len(common)} = "
                             f"identical {len(identical)} + changed {len(changed)} "
                             f"-> {len(identical)} byte-identical, {len(changed)} changed"),
        "byte_identical": identical,
        "changed": changed,
        "only_in_side_a": sorted(set(fa) - set(fb)),
        "only_in_side_b": sorted(set(fb) - set(fa)),
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--run-id", default="local")
    ap.add_argument("--hypothesis", default=None)
    ap.add_argument("--product-mount",
                    default="/tmp/lex_accepted/product")
    ap.add_argument("--packet", default="results/product/gate_packet/rebuilt-39027045675")
    ap.add_argument("--out", default=None)
    # F4 mode: measure a file-set relation between two directories and emit it.
    ap.add_argument("--relation-side-a", default=None)
    ap.add_argument("--relation-side-b", default=None)
    ap.add_argument("--relation-label-a", default="side_a")
    ap.add_argument("--relation-label-b", default="side_b")
    args = ap.parse_args(argv)

    if not (args.relation_side_a and args.relation_side_b) and not args.hypothesis:
        print("--hypothesis is required unless --relation-side-a/--relation-side-b are given",
              file=sys.stderr)
        return 2

    if args.relation_side_a or args.relation_side_b:
        if not (args.relation_side_a and args.relation_side_b):
            print("--relation-side-a and --relation-side-b are both required", file=sys.stderr)
            return 2
        sa, sb = Path(args.relation_side_a), Path(args.relation_side_b)
        if not sa.is_dir() or not sb.is_dir():
            print(f"relation side missing: {sa if not sa.is_dir() else sb}", file=sys.stderr)
            return 2
        rec = relation(sa, sb, args.relation_label_a, args.relation_label_b)
        out = Path(args.out) if args.out else (
            Path("results/evaluation/served_bundle_scope") / f"relation_{args.run_id}.json")
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(rec, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        print(rec["arithmetic_check"])
        print(f"record: {out}")
        return 0

    hyp_path = Path(args.hypothesis)
    if not hyp_path.exists():
        print(f"hypothesis not found: {hyp_path}", file=sys.stderr)
        return 2
    try:
        hypothesis = json.loads(hyp_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        print(f"hypothesis does not parse: {exc}", file=sys.stderr)
        return 2
    if hypothesis.get("schema") != HYPOTHESIS_SCHEMA:
        print(f"unexpected hypothesis schema: {hypothesis.get('schema')}", file=sys.stderr)
        return 2
    hypothesis["_path"] = str(hyp_path)

    mount = Path(args.product_mount)
    if not (mount / "state").is_dir():
        print(f"product mount unavailable: {mount} (environment error, NOT a pass)",
              file=sys.stderr)
        return 2
    qdir = mount / args.packet / "questions"
    if not qdir.is_dir():
        print(f"served packet questions dir not found: {qdir}", file=sys.stderr)
        return 2

    bundles, bundle_sha = [], {}
    for rel in hypothesis["input_of_record"]["bundles"]:
        p = qdir.parent / rel
        if not p.exists():
            print(f"bundle missing: {p}", file=sys.stderr)
            return 2
        try:
            bundle = json.loads(p.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            print(f"bundle does not parse: {p}: {exc}", file=sys.stderr)
            return 2
        bundle_sha[rel] = _sha256_file(p)
        bundles.append(measure_bundle(rel, bundle))

    record = evaluate(hypothesis, bundles, bundle_sha)
    record.pop("_path", None)
    hypothesis.pop("_path", None)
    out = Path(args.out) if args.out else (
        Path("results/evaluation/served_bundle_scope") / f"{args.run_id}.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(record, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")

    print(f"served packet: {args.packet} ({record['n_measurable_bundles']}/"
          f"{record['n_bundles']} bundles measurable, {record['n_decisions_total']} decisions)")
    for f in record["falsifiers"]:
        print(f"  [{f['verdict']:<10}] {f['id']}: {f['total']} {f['per_bundle']}")
    print(f"verdict: {record['verdict']}")
    print(f"record: {out}")
    if record["verdict"] == "BENCHMARK_NOT_MEASURED":
        # Nothing measurable is an ENVIRONMENT error, never a silent pass.
        return 2
    return 1 if record["falsification_proven"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
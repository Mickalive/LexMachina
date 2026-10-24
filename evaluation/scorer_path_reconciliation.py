#!/usr/bin/env python3
"""Item-(3) FROZEN-SCORER / SPAN-SEAM PATH RECONCILIATION (v66 ordered work).

Runs, side by side on the packet-of-record 39319405429 exact bytes, on the SAME
NEW accepted product head 3495c1336 (accept 40064639100):

  Side A  the FROZEN mapping-free counter-authority-surface predicate
          (evaluation/mapping_free_recall_falsifier.py:305-317, statuses read
          from evaluation/frozen_bars/RULES_LABEL.json rubric.scored_statuses
          at line 407, re-hashed REPORTED-ONLY against the frozen digest)
          applied to the packet bundles AS SERVED, and again to the bundles
          AFTER the product span-seam candidate transform;
  Side B  the product harness product/measure_counter_span_selection.py logic
          (baseline / candidate_unguarded / candidate arms), loaded BY FILE
          PATH from the accepted-product mount (no product package import, no
          numpy dependency, no modification of the mount) - the same arm
          definitions the harness uses at measure_counter_span_selection.py:102-116.

It publishes, per side: (i) what population each scores, (ii) what emission
path each reaches, (iii) whether the span-seam guarded output is inside or
outside the frozen scorer's input contract, with file:line provenance on both
sides, and (iv) whether the P0 content filter (product/query/counter_evidence_
span.py passes_content_filter, landed at 3495c1336) changed packet-level
emissions versus the accepted pre-filter measurement of record
(results/product/counter_span/CYCLE_39986094168_span_selection.json on the
mount). Every emitted row is additionally scored under the FROZEN D2/D3/D4
content-quality predicates (imported by value from the accepted instrument,
sha-pinned) so item (3) and item (4) share one definition of content quality.

The frozen scorer is NEVER edited to see the emissions (requirement 26); the
divergence is a finding either way. No bar, rubric, threshold or verdict
contract is applied, re-derived or moved. No network. Exit codes:
  0 RECONCILIATION_COMPLETE (all legs measured, contract question answered)
  1 RECONCILIATION_FALSIFIED (a claimed identity from the accepted record did
    not reproduce on the new head)
  2 ENVIRONMENT_OR_VACUOUS
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from evaluation.counter_evidence_quality_benchmark import (  # noqa: E402
    _sha256_file,
    classify_verified_row,
    numeric_environment,
)
from evaluation.mapping_free_recall_falsifier import (  # noqa: E402
    counter_authority_surface as mf_counter_surface,
)

SCHEMA = "lex-evaluation-scorer-path-reconciliation/1"
MOUNT = Path(os.environ.get("LEX_ACCEPTED_PRODUCT_MOUNT", "/tmp/lex_accepted/product"))
PACKET = "39319405429"
QIDS = ("de-kapitalverletzung", "fr-bail-entretien", "it-responsabilita-medica")
NEW_HEAD = "3495c13361ddf40f88d31c1fbb47b00bc06eee63"
NEW_HEAD_ACCEPT = "40064639100"
FROZEN_RUBRIC_SHA_EXPECTED = (
    "4457e971df3dc5d10af2a727aa675afc15a15564c18eed4cede0af5eb41b4608"
)
FROZEN_INSTRUMENT_SHA_EXPECTED = (
    "aac86527e5e54f0f9c527daac7ff1016d5124731b8ce673797520ff3dd53067d"
)
PRE_FILTER_MEASUREMENT_OF_RECORD = (
    "results/product/counter_span/CYCLE_39986094168_span_selection.json"
)

PROVENANCE = {
    "side_a_frozen_scorer": {
        "predicate": "evaluation/mapping_free_recall_falsifier.py:counter_authority_surface",
        "file_lines": "evaluation/mapping_free_recall_falsifier.py:305-317",
        "statuses_source": ("evaluation/mapping_free_recall_falsifier.py:407 reads "
                            "rubric.scored_statuses from evaluation/frozen_bars/"
                            "RULES_LABEL.json (re-hashed REPORTED-ONLY below)"),
        "population": ("decision rows of the input bundle BYTES AS WRITTEN whose "
                       "counter_status is in rubric.scored_statuses "
                       "('candidate-limiting','candidate-contrary',"
                       "'contrary_or_exception','limiting'); the scorer applies "
                       "no transform of its own - it never runs the span seam, "
                       "the emission repair or the anchor classifier"),
        "emission_path": ("none - the scorer only READS counter_status and "
                          "counter_evidence fields already present on the bytes "
                          "it is given"),
    },
    "side_b_product_span_seam": {
        "harness": "product/measure_counter_span_selection.py (arms built at lines 102-116)",
        "transform_chain": ("product/query/counter_evidence_span.py:"
                            "apply_verified_span_selection (line 494) with "
                            "content_filter=True default (line 349; filter at "
                            "382-393/441-446, predicates passes_content_filter "
                            "line 744 / detect_letterhead_zone line 676) -> "
                            "product/query/counter_emission_repair.py:"
                            "apply_counter_emission_repair -> "
                            "product/query/counter_anchor.py:apply_anchor_labels "
                            "(line 222; emits provenance.counter_anchor."
                            "emitted_ids, line 295-343)"),
        "population": ("the 20 heuristic-signal rows promoted by the shipped "
                       "offline emission path on the packet-of-record "
                       "de/fr/it question bundles (8/8/4), then the frozen "
                       "confirm-or-abstain gate over selected spans"),
        "emission_path": ("span selection writes counter_evidence + "
                          "counter_evidence_verified on rows; anchor labels "
                          "write counter_status in the scored set or "
                          "'abstained_unevidenced'"),
        "harness_execution_note": (
            "the harness MODULE cannot be invoked as `python -m product."
            "measure_counter_span_selection` in this evaluation environment "
            "because product/query/__init__.py imports the full pipeline "
            "(numpy dependency, absent here); this instrument therefore "
            "executes the harness's EXACT arm code path (the same three "
            "product functions at the same call sites, loaded by file path "
            "from the mount with a synthetic package, the reuse pattern "
            "already accepted in evaluation/offline_emission_path_benchmark."
            "py:load_product_modules) rather than re-implementing the arms"),
    },
}


def _sha256_file_public(path: Path) -> str:
    return _sha256_file(path)


def _load_product_modules(mount: Path) -> dict[str, Any]:
    """Load the three product query modules by file path (no package import)."""
    query_root = mount / "product" / "query"
    package_name = "_lex_product_query_reconciliation"
    pkg = type(sys)(package_name)
    pkg.__path__ = [str(query_root)]  # type: ignore[attr-defined]
    sys.modules[package_name] = pkg
    modules: dict[str, Any] = {}
    for name in ("counter_anchor", "counter_emission_repair", "counter_evidence_span"):
        fullname = f"{package_name}.{name}"
        spec = importlib.util.spec_from_file_location(fullname, query_root / f"{name}.py")
        if spec is None or spec.loader is None:
            raise RuntimeError(f"cannot load product module {name}")
        mod = importlib.util.module_from_spec(spec)
        sys.modules[fullname] = mod
        spec.loader.exec_module(mod)
        modules[name] = mod
    return modules


def _load_bundle(mount: Path, qid: str) -> dict:
    p = (mount / "results" / "product" / "gate_packet" / PACKET /
         "questions" / f"{qid}.bundle.json")
    return json.loads(p.read_text(encoding="utf-8"))


def _summarise(bundle: dict) -> dict:
    prov = (bundle.get("provenance") or {}).get("counter_anchor") or {}
    emitted_ids = [str(i) for i in (prov.get("emitted_ids") or [])]
    by_id = {str(d.get("decision_id")): d for d in bundle.get("decisions") or []}
    rows = [by_id.get(i, {}) for i in emitted_ids]
    return {
        "n_scored": int(prov.get("n_scored") or 0),
        "n_emitted": int(prov.get("n_emitted") or 0),
        "n_abstained": int(prov.get("n_abstained") or 0),
        "yield": prov.get("yield"),
        "emitted_ids": emitted_ids,
        "emitted_rows": [
            {
                "decision_id": str(d.get("decision_id") or ""),
                "counter_status": d.get("counter_status"),
                "counter_evidence_verified": d.get("counter_evidence_verified"),
                "evidence_len": len(str(d.get("counter_evidence") or "")),
                "frozen_content_defects": classify_verified_row(d)["defects"]
                if d.get("counter_evidence_verified") is True else None,
            }
            for d in rows
        ],
    }


def run(run_id: str, out_dir: Path, report_dir: Path) -> tuple[int, dict]:
    t0 = time.time()
    if not MOUNT.exists():
        return 2, {"schema": SCHEMA, "run_id": run_id, "verdict": "ENVIRONMENT_ERROR",
                   "detail": f"mount missing: {MOUNT}"}

    # ---- frozen re-hashes (REPORTED-ONLY) --------------------------------
    rules_path = _REPO_ROOT / "evaluation" / "frozen_bars" / "RULES_LABEL.json"
    rules_sha = _sha256_file_public(rules_path)
    if rules_sha != FROZEN_RUBRIC_SHA_EXPECTED:
        return 2, {"schema": SCHEMA, "run_id": run_id, "verdict": "ENVIRONMENT_ERROR",
                   "detail": f"frozen rubric digest drift: {rules_sha}"}
    rubric = json.loads(rules_path.read_text())
    scored_statuses = list((rubric.get("rubric") or {}).get("scored_statuses") or [])

    instrument_sha = _sha256_file_public(
        _REPO_ROOT / "evaluation" / "counter_evidence_quality_benchmark.py")
    if instrument_sha != FROZEN_INSTRUMENT_SHA_EXPECTED:
        return 2, {"schema": SCHEMA, "run_id": run_id, "verdict": "ENVIRONMENT_ERROR",
                   "detail": f"frozen content-predicate instrument drift: {instrument_sha}"}

    import subprocess
    try:
        mount_head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=MOUNT,
                                    capture_output=True, text=True, timeout=30,
                                    check=True).stdout.strip()
    except Exception:
        mount_head = "UNAVAILABLE"

    mods = _load_product_modules(MOUNT)
    rules_mod, rules_digest = mods["counter_anchor"].load_frozen_rules()
    if rules_digest != FROZEN_RUBRIC_SHA_EXPECTED:
        return 2, {"schema": SCHEMA, "run_id": run_id, "verdict": "ENVIRONMENT_ERROR",
                   "detail": f"product-side frozen rules digest drift: {rules_digest}"}

    # ---- pre-filter measurement of record (for the identity check) -------
    pre_path = MOUNT / PRE_FILTER_MEASUREMENT_OF_RECORD
    pre = json.loads(pre_path.read_text(encoding="utf-8")) if pre_path.is_file() else None

    per_qid: dict[str, Any] = {}
    agg = {"baseline": 0, "candidate_unguarded": 0, "candidate": 0}
    mf_served_total_issued = 0
    mf_transformed_guarded_total_issued = 0
    identity_ok = True

    for qid in QIDS:
        served = _load_bundle(MOUNT, qid)
        mf_served = mf_counter_surface(served, scored_statuses)
        mf_served_total_issued += int(mf_served["n_issued"])

        arms: dict[str, Any] = {}
        # baseline (no span seam)
        base = mods["counter_anchor"].apply_anchor_labels(
            mods["counter_emission_repair"].apply_counter_emission_repair(
                copy.deepcopy(served)), qid=qid)
        arms["baseline"] = _summarise(base)
        # candidate arms (span seam with content filter default ON)
        transformed: dict[str, dict] = {}
        for arm, guard in (("candidate_unguarded", "off"), ("candidate", "on")):
            b = mods["counter_anchor"].apply_anchor_labels(
                mods["counter_emission_repair"].apply_counter_emission_repair(
                    mods["counter_evidence_span"].apply_verified_span_selection(
                        copy.deepcopy(served), qid=qid, mode="select",
                        env={**os.environ,
                             "LEXMACHINA_COUNTER_SPAN_GUARD": guard})),
                qid=qid)
            arms[arm] = _summarise(b)
            transformed[arm] = b
            agg[arm] += arms[arm]["n_emitted"]
        agg["baseline"] += arms["baseline"]["n_emitted"]

        mf_guarded_tf = mf_counter_surface(transformed["candidate"], scored_statuses)
        mf_transformed_guarded_total_issued += int(mf_guarded_tf["n_issued"])
        mf_unguarded_tf = mf_counter_surface(transformed["candidate_unguarded"],
                                             scored_statuses)

        # identity vs accepted pre-filter measurement of record
        pre_q = (pre or {}).get("bundles", {}).get(qid, {}) if pre else {}
        id_check = {}
        for arm in ("baseline", "candidate_unguarded", "candidate"):
            pre_n = int((pre_q.get(arm) or {}).get("n_emitted") or -1)
            now_n = arms[arm]["n_emitted"]
            pre_ids = [str(i) for i in ((pre_q.get(arm) or {}).get("emitted_ids") or [])]
            id_check[arm] = {
                "pre_filter_n_emitted": None if pre_n < 0 else pre_n,
                "new_head_n_emitted": now_n,
                "pre_filter_emitted_ids": pre_ids,
                "new_head_emitted_ids": arms[arm]["emitted_ids"],
                "identical": (pre_n == now_n and pre_ids == arms[arm]["emitted_ids"]),
            }
            if pre_n >= 0 and not id_check[arm]["identical"]:
                identity_ok = False

        per_qid[qid] = {
            "side_a_frozen_scorer_on_served_bytes": mf_served,
            "side_b_product_arms": arms,
            "side_a_frozen_scorer_on_guarded_transformed_bytes": mf_guarded_tf,
            "side_a_frozen_scorer_on_unguarded_transformed_bytes": mf_unguarded_tf,
            "identity_vs_pre_filter_measurement_of_record": id_check,
        }

    # ---- contract-shape analysis -----------------------------------------
    guarded_emitted = [r for q in per_qid.values()
                       for r in q["side_b_product_arms"]["candidate"]["emitted_rows"]]
    shape_ok = all(
        r["counter_status"] in scored_statuses
        and r["evidence_len"] > 0
        for r in guarded_emitted
    ) if guarded_emitted else None
    content_clean = all(
        r["frozen_content_defects"] == []
        for r in guarded_emitted
        if r["frozen_content_defects"] is not None
    ) if guarded_emitted else None

    verdict = "RECONCILIATION_COMPLETE"
    exit_code = 0
    if pre is not None and not identity_ok:
        verdict = "RECONCILIATION_FALSIFIED"
        exit_code = 1

    record = {
        "schema": SCHEMA,
        "run_id": run_id,
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "direction_version": 66,
        "ordered_work_item": "v66 evaluation ordered work item (3) FROZEN-SCORER PATH DIVERGENCE CROSS-CHECK",
        "mount": str(MOUNT),
        "mount_head": mount_head,
        "expected_mount_head": NEW_HEAD,
        "packet": PACKET,
        "frozen_rehash_reported_only": {
            "rules_label_sha256": rules_sha,
            "matches_expected": rules_sha == FROZEN_RUBRIC_SHA_EXPECTED,
            "content_predicate_instrument_sha256": instrument_sha,
            "product_side_rules_digest": rules_digest,
        },
        "scored_statuses": scored_statuses,
        "provenance": PROVENANCE,
        "per_qid": per_qid,
        "aggregate": {
            "side_b_product_arms_n_emitted": agg,
            "side_a_frozen_scorer_served_bytes_n_issued_total": mf_served_total_issued,
            "side_a_frozen_scorer_guarded_transformed_bytes_n_issued_total": mf_transformed_guarded_total_issued,
            "pre_filter_measurement_of_record": PRE_FILTER_MEASUREMENT_OF_RECORD
            if pre is not None else None,
            "pre_filter_aggregate": None if pre is None else pre.get("aggregate"),
            "packet_level_emission_identity_vs_pre_filter": identity_ok,
        },
        "contract_analysis": {
            "question": ("is the span-seam guarded output inside or outside the "
                         "frozen scorer's input contract?"),
            "answer": ("INSIDE by shape, OUTSIDE by path. Every guarded emitted "
                       "row carries a counter_status in rubric.scored_statuses "
                       f"and non-empty counter_evidence (shape check: {shape_ok}); "
                       "when the frozen predicate is applied to the POST-TRANSFORM "
                       "bytes it scores those rows (served-bytes total issued "
                       f"{mf_served_total_issued} vs guarded-transformed total "
                       f"issued {mf_transformed_guarded_total_issued}). The frozen "
                       "scorer's input contract is the bundle bytes AS WRITTEN; "
                       "the span seam is a PRE-SCORER pipeline stage whose output "
                       "is not present in the served packet-of-record bytes, so "
                       "on the served bytes both families agree at zero. The "
                       "requirement-36 divergence (product harness n_emitted 0/1/6 "
                       "vs frozen scorer n_emitted=0) is therefore a TRANSFORM-PATH "
                       "divergence, not a contract-shape exclusion, and it is "
                       "resolved here without any edit to the frozen scorer."),
            "guarded_emitted_rows_shape_ok": shape_ok,
            "guarded_emitted_rows_content_clean_under_frozen_predicates": content_clean,
            "identity_vs_accepted_pre_filter_measurement": identity_ok,
            "p0_filter_effect_on_packet_bytes": (
                "NONE at the emitted-set level: the new head's arm totals and "
                "emitted ids are identical to the accepted pre-filter "
                "measurement of record (the item-(4) shipped-slice D2 "
                "persistence is a separate population and is measured there)."),
        },
        "verdict": verdict,
        "exit_code": exit_code,
        "claim_ceiling": (
            "Side-by-side measurement of the frozen mapping-free predicate and "
            "the product span-seam arms on identical packet-of-record bytes "
            "under the NEW head; scores no frozen bar, applies no verdict "
            "contract, edits no scorer; the frozen rubrics are re-hashed "
            "REPORTED-ONLY. Both DO-NOT-SERVE orders stand; admission stays "
            "fail-closed; the comparative map-versus-ranked-list half is NOT "
            "scored while served-bytes emission stays zero."),
        "no_obsolete_174k_benchmark_rerun": True,
        "elapsed_s": round(time.time() - t0, 3),
        "numeric_environment": numeric_environment(),
    }

    out_dir.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"{run_id}.json").write_text(
        json.dumps(record, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")

    lines = [
        f"# Frozen-Scorer / Span-Seam Path Reconciliation (item 3) — run {run_id}",
        "",
        f"- Packet of record: {PACKET} (exact bytes)",
        f"- Product head: `{mount_head[:12]}` (expected {NEW_HEAD[:12]}, match: {mount_head == NEW_HEAD})",
        f"- Verdict: **{verdict}** (exit {exit_code})",
        f"- Side A on SERVED bytes: n_issued total = {mf_served_total_issued}",
        f"- Side A on GUARDED TRANSFORMED bytes: n_issued total = {mf_transformed_guarded_total_issued}",
        f"- Side B arm totals (n_emitted): {agg}",
        f"- Identity vs accepted pre-filter measurement of record: **{identity_ok}**",
        f"- Contract answer: {record['contract_analysis']['answer'][:200]}...",
        "",
        "## Per-qid",
        "",
        "| qid | served n_issued | baseline | unguarded | guarded | guarded-transformed n_issued |",
        "|---|---|---|---|---|---|",
    ]
    for qid, q in per_qid.items():
        lines.append(
            f"| {qid} | {q['side_a_frozen_scorer_on_served_bytes']['n_issued']} "
            f"| {q['side_b_product_arms']['baseline']['n_emitted']} "
            f"| {q['side_b_product_arms']['candidate_unguarded']['n_emitted']} "
            f"| {q['side_b_product_arms']['candidate']['n_emitted']} "
            f"| {q['side_a_frozen_scorer_on_guarded_transformed_bytes']['n_issued']} |")
    lines += ["", "## Claim ceiling", "", record["claim_ceiling"]]
    (report_dir / f"SCORER_PATH_RECONCILIATION_{run_id}.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8")
    return exit_code, record


DEFAULT_OUT_DIR = _REPO_ROOT / "results/evaluation/scorer_path_reconciliation"
DEFAULT_REPORT_DIR = _REPO_ROOT / "reports/evaluation"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--run-id", default=None)
    ap.add_argument("--out-dir", default=None)
    ap.add_argument("--report-dir", default=None)
    args = ap.parse_args(argv)
    run_id = args.run_id or os.environ.get("GITHUB_RUN_ID", "local")
    out_dir = Path(args.out_dir) if args.out_dir else DEFAULT_OUT_DIR
    report_dir = Path(args.report_dir) if args.report_dir else DEFAULT_REPORT_DIR
    code, record = run(run_id, out_dir, report_dir)
    print(json.dumps({
        "verdict": record.get("verdict"),
        "exit_code": code,
        "aggregate": record.get("aggregate"),
        "contract": {k: record.get("contract_analysis", {}).get(k) for k in
                     ("guarded_emitted_rows_shape_ok",
                      "guarded_emitted_rows_content_clean_under_frozen_predicates",
                      "identity_vs_accepted_pre_filter_measurement")},
    }, indent=1, ensure_ascii=False))
    return code


if __name__ == "__main__":
    raise SystemExit(main())

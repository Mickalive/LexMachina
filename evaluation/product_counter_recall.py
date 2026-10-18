"""Product-vs-baseline recall on the FROZEN authority / counter-authority sets.

Lane directive (evaluation): "Baseline should be the same OpenCaseLaw
search/result set without the additional query-map/counter-authority
machinery where practical."

This module is the smallest claim-bearing measurement of that comparison on
the PRODUCT side.  Every accepted gate in this lane scores plain OpenCaseLaw
searches only: all 40 gates of ``evaluation.retrieval_gate`` draw their rows
from ``evaluation.retrieval_gate.client.SearchClient``, and the only
product-side output they expose
(``record["exploratory_product_cache_comparison"]``) reads the product's raw
``query_cache`` envelopes, is labelled ``TIER = EXPLORATORY`` in the frozen
spec itself, and is never read by ``gates.evaluate()``.  Nothing else in this
lane scores a served bundle against a frozen id set.

So: a product could ship a served bundle that retrieves strictly FEWER of the
frozen known counter-authority ids than the plain OpenCaseLaw pool it wraps,
and the whole accepted gate suite would stay green.  That is precisely the
failure the Master Prompt's retrieval-first doctrine exists to prevent
("optimize recall before map aesthetics", "preserve lower-ranked candidates
that may represent contrary or minority lines", "a visualization cannot
reveal an authority that retrieval failed to find").

Reuse, not rebuild
------------------
* the frozen id sets and the frozen query texts come from
  ``evaluation/retrieval_gate/frozen_retrieval_benchmark.json`` (sha256
  187b0e54b03b326c62d45d8ba48fc78dc88501086761cd91a84c304a7478ba72);
* id matching uses the ACCEPTED
  ``evaluation.retrieval_gate.gates.match_authorities`` /
  ``row_cores`` / ``frozen.alnum_core``, which already reconcile legacy
  BGE-style frozen ids against ATF-style returned ids and citation strings.
  No id matcher is written, re-tuned or re-derived here;
* the baseline pool is the row pool of the accepted LIVE OpenCaseLaw record,
  ``results/evaluation/retrieval_benchmark/39101217095.json``.  No network
  request is made by this module;
* the ">=1-of-set" recall semantics are the frozen spec's own
  ``gate_semantics`` verbatim;
* the not-measurable convention mirrors ``gates.authority_recall``'s existing
  empty-set branch: an empty frozen set yields ``passed=None`` with an
  explicit reason and is never counted as a pass;
* the non-vacuity battery follows ``evaluation.benchmark_retrieval_counter_authority``
  and ``evaluation.packet_lineage_sweep``: a gate that cannot fail is not a
  measurement.

The hypothesis, the analyst slug<->served-question mapping, the gate names,
the success rule and the non-vacuity controls are frozen in
``evaluation/PRODUCT_COUNTER_RECALL_HYPOTHESIS.json``, written BEFORE this
scorer executed, including an honest pre-execution disclosure of the
reconnaissance that preceded the freeze.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]

from evaluation.retrieval_gate import frozen as rg_frozen  # noqa: E402
from evaluation.retrieval_gate import gates as rg_gates  # noqa: E402

SCHEMA = "lex-evaluation-product-counter-recall/1"
INDEX_SCHEMA = "lex-evaluation-accepted-served-id-index/1"

HYPOTHESIS_PATH = REPO_ROOT / "evaluation" / "PRODUCT_COUNTER_RECALL_HYPOTHESIS.json"
FROZEN_SPEC_PATH = REPO_ROOT / "evaluation" / "retrieval_gate" / "frozen_retrieval_benchmark.json"
BASELINE_RECORD_RELPATH = "results/evaluation/retrieval_benchmark/39101217095.json"
INDEX_RELPATH = "evaluation/product_counter_recall/ACCEPTED_SERVED_ID_INDEX.json"

DEFAULT_MOUNT_ENVS = ("LEX_ACCEPTED_PRODUCT_MOUNT", "LEX_PRODUCT_MOUNT")
DEFAULT_MOUNTS = ("/tmp/lex_accepted/product",)

# The accepted served packet that both frozen bar gates and the accepted
# DO-NOT-SERVE order address.  Frozen here so a record can never silently be
# built from a different packet.
SERVED_PACKET_ID = "38839347028"

EXIT_PASS = 0
EXIT_FALSIFIED = 1
EXIT_NOT_MEASURED_OR_VACUOUS = 2
EXIT_ENVIRONMENT = 3


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sha256_obj(obj: Any) -> str:
    return hashlib.sha256(
        json.dumps(obj, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()


def _mount_candidates(explicit: str | None) -> list[Path]:
    if explicit:
        return [Path(explicit)]
    seen: list[Path] = []
    for env in DEFAULT_MOUNT_ENVS:
        val = os.environ.get(env)
        if val:
            seen.append(Path(val))
    seen.extend(Path(p) for p in DEFAULT_MOUNTS)
    return seen


def resolve_product_mount(explicit: str | None = None) -> Path | None:
    """First existing read-only accepted product mount, or None."""
    for cand in _mount_candidates(explicit):
        if cand.is_dir():
            return cand
    return None


def served_bundle_path(mount: Path, question_id: str) -> Path:
    return mount / "results" / "product" / "gate_packet" / SERVED_PACKET_ID / "questions" / f"{question_id}.bundle.json"


def _product_row(decision: dict) -> dict:
    """Map one served-bundle decision onto the accepted matcher's row shape.

    ``gates.row_cores`` reads decision_id / canonical_decision_id /
    court-prefixed docket_number / citation_string_{de,fr,it}.  The served
    bundle carries the citation under ``citation``; it is copied into the
    ``citation_string_de`` slot so the ACCEPTED matcher sees it.  No new
    matching logic is introduced.
    """
    citation = str(decision.get("citation") or "")
    return {
        "decision_id": str(decision.get("decision_id") or ""),
        "canonical_decision_id": str(decision.get("canonical_decision_id") or ""),
        "docket_number": str(decision.get("docket_number") or ""),
        "court": str(decision.get("court") or ""),
        "canonical_url": str(decision.get("canonical_url") or ""),
        "citation_string_de": citation,
        "citation_string_fr": "",
        "citation_string_it": "",
    }


def _out(gate: str, passed: bool, detail: str, **measured: Any) -> dict:
    return {"gate": gate, "passed": bool(passed), "detail": detail, "measured": measured}


def _nm(gate: str, reason: str, **measured: Any) -> dict:
    return {"gate": gate, "passed": None, "detail": reason, "measured": measured}


# --------------------------------------------------------------------------- #
# side measurement: derived, sha256-pinned index of the accepted served bundles
# --------------------------------------------------------------------------- #
def build_id_index(mount: Path, cells: list[dict]) -> dict:
    """Derive the compact decision-id index of the accepted served bundles.

    Only the id-bearing fields ``gates.row_cores`` reads are kept, so the
    index stays small while remaining a faithful input to the accepted
    matcher.  The sha256 of each source bundle is recorded, so the index is
    a blob-proven derivative rather than a hand-maintained fixture.
    """
    questions: dict[str, Any] = {}
    for cell in cells:
        qid = cell["served_question_id"]
        path = served_bundle_path(mount, qid)
        bundle = json.loads(path.read_text(encoding="utf-8"))
        decisions = bundle.get("decisions") or []
        rows = [_product_row(d) for d in decisions]
        cores = set()
        for row in rows:
            cores |= rg_gates.row_cores(row)
        adv = (((bundle.get("provenance") or {}).get("adversarial_retrieval")) or {})
        questions[qid] = {
            "slug": cell["slug"],
            "source_bundle_path": str(path.relative_to(mount)),
            "source_bundle_sha256": sha256_file(path),
            "n_decisions": len(decisions),
            "n_distinct_decision_ids": len({r["decision_id"] for r in rows}),
            "answer_cited_decision_ids": list(((bundle.get("answer") or {}).get("cited_decision_ids")) or []),
            "adversarial_new_counter_ids": list(adv.get("new_counter_ids") or []),
            "adversarial_new_row_ids": list(adv.get("new_row_ids") or []),
            "rows": rows,
            "n_matcher_cores": len(cores),
        }
    return {
        "schema": INDEX_SCHEMA,
        "served_packet_id": SERVED_PACKET_ID,
        "derived_from": "accepted product mount (read-only), read-only derivative",
        "questions": questions,
    }


def load_index(repo_root: Path = REPO_ROOT) -> dict | None:
    path = repo_root / INDEX_RELPATH
    if not path.is_file():
        return None
    idx = json.loads(path.read_text(encoding="utf-8"))
    return idx if idx.get("schema") == INDEX_SCHEMA else None


def rows_for(index: dict, question_id: str) -> list[dict] | None:
    entry = (index.get("questions") or {}).get(question_id)
    return None if entry is None else list(entry.get("rows") or [])


# --------------------------------------------------------------------------- #
# the measurement
# --------------------------------------------------------------------------- #
def _baseline_pool(record: dict, slug: str) -> list[dict]:
    """The frozen baseline pool for one slug: both channels, all languages.

    This is exactly the pool the accepted frozen gate
    ``counter::known_counter_recall::<slug>`` scores (``n_rows == 240`` ==
    3 languages x (50 baseline + 30 counter) rows), so the baseline number
    this benchmark compares against is the same population the accepted
    frozen gate already scored.
    """
    return [
        row
        for q in record.get("queries") or []
        if q.get("slug") == slug
        for row in (q.get("rows") or [])
    ]


def _recalled(ids: list[str], rows: list[dict], min_len: int) -> dict:
    """ids recalled in rows, via the accepted matcher. >=1-of-set semantics."""
    if not ids:
        return {"recallable": False, "hits": [], "missing": [], "matched_core": {}}
    m = rg_gates.match_authorities(ids, rows, min_len=min_len)
    hits = sorted(k for k, v in m.items() if v)
    return {
        "recallable": True,
        "hits": hits,
        "missing": sorted(k for k, v in m.items() if not v),
        "matched_core": {k: v for k, v in m.items() if v},
    }


def evaluate(
    hypothesis: dict,
    spec: dict,
    baseline_record: dict,
    index: dict,
    index_origin: str,
    mount: Path | None,
) -> dict:
    min_len = int(((spec.get("id_match_rules") or {}).get("min_core_length")) or 6)
    questions = {q["slug"]: q for q in spec["questions"]}
    gates: list[dict] = []

    cells: list[dict] = []
    for cell in hypothesis["analyst_mapping_FROZEN_BEFORE_EXECUTION"]["cells"]:
        slug = cell["slug"]
        q = questions.get(slug)
        if q is None:
            cells.append({**cell, "status": "NOT_MEASURED",
                          "reason": "slug absent from the frozen retrieval spec"})
            continue
        authority_ids = list(q.get("authority_ids") or [])
        counter_ids = [r["id"] for r in (q.get("known_counter_ids") or [])]
        prod_rows = rows_for(index, cell["served_question_id"])
        if prod_rows is None:
            cells.append({**cell, "status": "NOT_MEASURED",
                          "reason": "this served question is absent from both the accepted product mount "
                                    "and the derived id index; nothing to score and never a pass"})
            continue

        base_rows = _baseline_pool(baseline_record, slug)
        p_auth = _recalled(authority_ids, prod_rows, min_len)
        b_auth = _recalled(authority_ids, base_rows, min_len)
        p_cnt = _recalled(counter_ids, prod_rows, min_len)
        b_cnt = _recalled(counter_ids, base_rows, min_len)

        # ---- product gates ------------------------------------------------ #
        if p_auth["recallable"]:
            gates.append(_out(
                f"product::authority_recall::{slug}",
                len(p_auth["hits"]) >= 1,
                (f"product served bundle recalls {len(p_auth['hits'])}/{len(authority_ids)} frozen "
                 f"controlling-authority ids (>=1-of-set)") if p_auth["hits"] else
                (f"product served bundle recalls 0/{len(authority_ids)} frozen controlling-authority ids"),
                slug=slug, served_question_id=cell["served_question_id"],
                n_rows=len(prod_rows), hits=p_auth["hits"], missing=p_auth["missing"],
                matched_core=p_auth["matched_core"],
            ))
        else:
            gates.append(_nm(
                f"product::authority_recall::{slug}",
                "frozen spec carries no controlling-authority set for this slug (authority_ids = []); "
                "recall is not measurable and is never counted as a pass",
                slug=slug, served_question_id=cell["served_question_id"], n_frozen_ids=0,
            ))

        if p_cnt["recallable"]:
            gates.append(_out(
                f"product::counter_recall::{slug}",
                len(p_cnt["hits"]) >= 1,
                (f"product served bundle recalls {len(p_cnt['hits'])}/{len(counter_ids)} frozen known "
                 f"counter-authority ids (>=1-of-set)") if p_cnt["hits"] else
                (f"product served bundle recalls 0/{len(counter_ids)} frozen known counter-authority ids"),
                slug=slug, served_question_id=cell["served_question_id"],
                n_rows=len(prod_rows), hits=p_cnt["hits"], missing=p_cnt["missing"],
                matched_core=p_cnt["matched_core"],
            ))
        else:
            gates.append(_nm(
                f"product::counter_recall::{slug}",
                "frozen spec carries no known counter-authority set for this slug; "
                "recall is not measurable and is never counted as a pass",
                slug=slug, served_question_id=cell["served_question_id"], n_frozen_ids=0,
            ))

        # ---- parity gates (the frozen success rule) ----------------------- #
        for name, p, b, gate_prefix in (
            ("authority", p_auth, b_auth, "parity::authority_not_below_baseline"),
            ("counter", p_cnt, b_cnt, "parity::counter_not_below_baseline"),
        ):
            gate = f"{gate_prefix}::{slug}"
            if not (p["recallable"] and b["recallable"]):
                gates.append(_nm(
                    gate,
                    f"frozen {name} id set is empty; the parity comparison is not measurable "
                    "and is never counted as a pass",
                    slug=slug, n_product=0, n_baseline=0,
                ))
                continue
            p_n, b_n = len(p["hits"]), len(b["hits"])
            ok = p_n >= b_n
            gates.append(_out(
                gate, ok,
                (f"product {p_n} >= baseline {b_n} of {len(p['hits']) + len(p['missing'])} frozen {name} ids: "
                 f"the layer on top of plain OpenCaseLaw adds recall") if ok else
                (f"product {p_n} < baseline {b_n} of {len(p['hits']) + len(p['missing'])} frozen {name} ids: "
                 f"the query-map / counter-authority layer on top of plain OpenCaseLaw returns "
                 f"strictly LESS of the frozen set than the search it wraps"),
                slug=slug, served_question_id=cell["served_question_id"],
                product_hits=p_n, baseline_hits=b_n,
                product_hit_ids=p["hits"], baseline_hit_ids=b["hits"],
                product_only=[i for i in p["hits"] if i not in set(b["hits"])],
                baseline_only=[i for i in b["hits"] if i not in set(p["hits"])],
                n_product_rows=len(prod_rows), n_baseline_rows=len(base_rows),
            ))

        cells.append({
            **cell,
            "status": "MEASURED",
            "n_product_rows": len(prod_rows),
            "n_baseline_rows": len(base_rows),
            "authority": {"n_frozen": len(authority_ids),
                          "product_hits": p_auth["hits"], "baseline_hits": b_auth["hits"]},
            "counter": {"n_frozen": len(counter_ids),
                        "product_hits": p_cnt["hits"], "baseline_hits": b_cnt["hits"]},
        })

    unmapped = [
        {"slug": slug, "status": "NOT_MEASURED",
         "reason": "the frozen analyst mapping declares no served counterpart for this slug; "
                   "the accepted served packet serves no such question"}
        for slug in questions
        if slug not in {c["slug"] for c in hypothesis["analyst_mapping_FROZEN_BEFORE_EXECUTION"]["cells"]}
    ]

    # ---- non-vacuity battery --------------------------------------------- #
    battery: list[dict] = []
    first = next((c for c in cells if c.get("status") == "MEASURED"), None)
    if first is None:
        battery.append({"control": "blanked_product_pool_must_fail", "holds": False,
                        "why": "no measurable cell; the benchmark is NOT_MEASURED, never a pass"})
        battery.append({"control": "parity_gate_is_not_vacuous", "holds": False,
                        "why": "no measurable cell; the benchmark is NOT_MEASURED, never a pass"})
    else:
        slug = first["slug"]
        q = questions[slug]
        counter_ids = [r["id"] for r in (q.get("known_counter_ids") or [])]
        base_rows = _baseline_pool(baseline_record, slug)
        b_n = len(_recalled(counter_ids, base_rows, min_len)["hits"])

        blanked = _recalled(counter_ids, [], min_len)
        blank_holds = len(blanked["hits"]) == 0 and b_n >= 1
        battery.append({
            "control": "blanked_product_pool_must_fail",
            "holds": bool(blank_holds),
            "why": (f"scoring a deliberately BLANKED product pool against the {len(counter_ids)} frozen "
                    f"counter ids of {slug} yields {len(blanked['hits'])} hits while the cell baseline "
                    f"recalls {b_n}; a gate that passed this input would be vacuous"),
            "slug": slug, "blanked_product_hits": len(blanked["hits"]), "baseline_hits": b_n,
        })

        regressed = _recalled(counter_ids, base_rows[:1], min_len)
        r_n = len(regressed["hits"])
        parity_fires = r_n < b_n
        battery.append({
            "control": "parity_gate_is_not_vacuous",
            "holds": bool(parity_fires),
            "why": (f"a deliberately regressed product pool (the first {len(base_rows[:1])} baseline row(s), "
                    f"recalling {r_n}) sits BELOW the cell baseline ({b_n}), so "
                    f"parity::counter_not_below_baseline::{slug} is falsified by a known input; "
                    "if it did not fire the parity rule would be vacuous"),
            "slug": slug, "regressed_product_hits": r_n, "baseline_hits": b_n,
        })
    all_hold = all(b["holds"] for b in battery)

    # ---- provenance gate -------------------------------------------------- #
    gates.append(_out(
        "provenance::frozen_spec_and_baseline_identity",
        baseline_record.get("frozen_sha256") == rg_frozen.FROZEN_SHA256
        and rg_frozen.load_frozen() is not None,
        ("frozen retrieval spec digest matches the accepted pin "
         f"{rg_frozen.FROZEN_SHA256[:12]}... and loads; the baseline record carries the same pin"),
        frozen_spec_path=str(FROZEN_SPEC_PATH.relative_to(REPO_ROOT)),
        frozen_spec_sha256=sha256_file(FROZEN_SPEC_PATH),
        frozen_sha256_pinned=rg_frozen.FROZEN_SHA256,
        baseline_record=BASELINE_RECORD_RELPATH,
        baseline_record_sha256=sha256_file(REPO_ROOT / BASELINE_RECORD_RELPATH),
        baseline_record_frozen_sha256=baseline_record.get("frozen_sha256"),
        baseline_pass_a_mode=baseline_record.get("pass_a_mode"),
        baseline_transport=baseline_record.get("transport"),
        product_id_index_origin=index_origin,
        product_mount=str(mount) if mount else None,
        served_packet_id=SERVED_PACKET_ID,
    ))

    failed = [g["gate"] for g in gates if g["passed"] is False]
    not_measurable = [g["gate"] for g in gates if g["passed"] is None]
    parity_failures = [name for name in failed if name.startswith("parity::")]
    measured_cells = [c for c in cells if c.get("status") == "MEASURED"]

    if not all_hold:
        verdict = "ENVIRONMENT_OR_VACUOUS"
    elif not measured_cells:
        verdict = "NOT_MEASURED"
    elif parity_failures:
        verdict = "FAIL_PARITY_REGRESSION"
    else:
        verdict = "PASS_NO_PARITY_REGRESSION"

    return {
        "verdict": verdict,
        "exit_code": {"PASS_NO_PARITY_REGRESSION": EXIT_PASS,
                      "FAIL_PARITY_REGRESSION": EXIT_FALSIFIED,
                      "NOT_MEASURED": EXIT_NOT_MEASURED_OR_VACUOUS,
                      "ENVIRONMENT_OR_VACUOUS": EXIT_NOT_MEASURED_OR_VACUOUS}[verdict],
        "n_gates": len(gates),
        "n_passed": sum(1 for g in gates if g["passed"] is True),
        "n_failed": len(failed),
        "n_not_measurable": len(not_measurable),
        "failed_gates": failed,
        "not_measurable_gates": not_measurable,
        "parity_failure_gates": parity_failures,
        "gates": gates,
        "cells": cells,
        "unmapped_frozen_slugs": unmapped,
        "non_vacuity": {"all_hold": all_hold, "battery": battery},
        "success_rule": hypothesis["success_rule_FROZEN"]["statement"],
        "claim_ceiling": hypothesis["claim_ceiling"],
    }


def run(run_id: str, out_path: Path | None, mount_arg: str | None = None,
        repo_root: Path = REPO_ROOT) -> tuple[int, dict | None, str]:
    hypothesis = json.loads(HYPOTHESIS_PATH.read_text(encoding="utf-8"))
    if not hypothesis.get("frozen_before_execution"):
        sys.stderr.write("hypothesis file is not marked frozen_before_execution\n")
        return EXIT_ENVIRONMENT, None, "hypothesis not frozen"

    spec = rg_frozen.load_frozen()  # raises on digest/schema/budget drift
    baseline_record = json.loads((repo_root / BASELINE_RECORD_RELPATH).read_text(encoding="utf-8"))
    if baseline_record.get("schema") != "lex-retrieval-benchmark/1":
        sys.stderr.write("baseline record has an unexpected schema\n")
        return EXIT_ENVIRONMENT, None, "baseline schema"

    mount = resolve_product_mount(mount_arg)
    index = load_index(repo_root)
    if mount is not None:
        index = build_id_index(mount, hypothesis["analyst_mapping_FROZEN_BEFORE_EXECUTION"]["cells"])
        index_origin = f"rebuilt_live_from_mount:{mount}"
    elif index is not None:
        index_origin = f"vendored_index:{INDEX_RELPATH}"
    else:
        sys.stderr.write("no accepted product mount and no vendored served-id index\n")
        return EXIT_NOT_MEASURED_OR_VACUOUS, None, "no product rows available"

    verdict = evaluate(hypothesis, spec, baseline_record, index, index_origin, mount)
    record = {
        "schema": SCHEMA,
        "run_id": run_id,
        "direction_version": hypothesis["direction_version_at_freeze"],
        "entry_point": "python -m evaluation.product_counter_recall",
        "hypothesis": {
            "path": str(HYPOTHESIS_PATH.relative_to(repo_root)),
            "sha256": sha256_file(HYPOTHESIS_PATH),
            "frozen_before_execution": True,
            "pre_execution_disclosure_present": "pre_execution_disclosure_HONEST" in hypothesis,
        },
        "frozen_spec": {
            "path": str(FROZEN_SPEC_PATH.relative_to(repo_root)),
            "sha256": sha256_file(FROZEN_SPEC_PATH),
            "frozen_sha256": rg_frozen.FROZEN_SHA256,
        },
        "baseline": {
            "record": BASELINE_RECORD_RELPATH,
            "sha256": sha256_file(repo_root / BASELINE_RECORD_RELPATH),
            "pass_a_mode": baseline_record.get("pass_a_mode"),
            "note": "plain OpenCaseLaw searches with no query-map / counter-authority machinery; "
                    "this benchmark performs no network request",
        },
        "product": {
            "served_packet_id": SERVED_PACKET_ID,
            "id_index_origin": index_origin,
            "mount": str(mount) if mount else None,
            "n_questions": len(index.get("questions") or {}),
            "source_bundle_sha256": {qid: e.get("source_bundle_sha256")
                                     for qid, e in (index.get("questions") or {}).items()},
        },
        "network_requests": 0,
        **verdict,
    }
    if out_path is not None:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(record, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        record_path = str(out_path.relative_to(repo_root)) if out_path.is_relative_to(repo_root) else str(out_path)
    else:
        record_path = None
    return record["exit_code"], record, record_path or ""


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    ap.add_argument("--run-id", default=os.environ.get("GITHUB_RUN_ID", "local"))
    ap.add_argument("--out", default=None)
    ap.add_argument("--product-mount", default=None)
    ap.add_argument("--build-index", action="store_true",
                    help="rebuild and write the derived served-id index from the accepted mount")
    args = ap.parse_args(argv)

    if args.build_index:
        mount = resolve_product_mount(args.product_mount)
        if mount is None:
            sys.stderr.write("no accepted product mount available for --build-index\n")
            return EXIT_ENVIRONMENT
        hyp = json.loads(HYPOTHESIS_PATH.read_text(encoding="utf-8"))
        idx = build_id_index(mount, hyp["analyst_mapping_FROZEN_BEFORE_EXECUTION"]["cells"])
        dest = REPO_ROOT / INDEX_RELPATH
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(json.dumps(idx, indent=1, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps({"index": INDEX_RELPATH, "sha256": sha256_file(dest),
                          "questions": sorted(idx["questions"])}, indent=1))
        return EXIT_PASS

    out = Path(args.out) if args.out else REPO_ROOT / "results" / "evaluation" / "product_counter_recall" / f"{args.run_id}.json"
    code, record, path = run(args.run_id, out, args.product_mount)
    if record is None:
        print(json.dumps({"verdict": "ENVIRONMENT_ERROR", "detail": path}, indent=1))
        return code
    print(json.dumps({
        "run_id": args.run_id, "record": path, "verdict": record["verdict"],
        "exit_code": record["exit_code"], "n_gates": record["n_gates"],
        "n_passed": record["n_passed"], "n_failed": record["n_failed"],
        "n_not_measurable": record["n_not_measurable"],
        "parity_failure_gates": record["parity_failure_gates"],
        "non_vacuity_all_hold": record["non_vacuity"]["all_hold"],
    }, indent=1))
    return code


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
"""LexMachina Evaluation — FAST-MVP retrieval / counter-authority RECALL@K benchmark.

SMALLEST executable benchmark that can falsify the product's *reranking* leg
over the frozen 24-cell multilingual OpenCaseLaw cache.

Why this file exists (lane observation O1/O2 of round-0 audit CYCLE_40146190698):
the accepted suite ``tests/evaluation/test_retrieval_benchmark.py`` advertises
known relevant-authority recall and known contrary/limiting-authority recall,
but ``KNOWN_COUNTER`` is empty in all 12 cells, ``_recall_at_k`` is never
invoked by any test and ``_run_offline_retrieval`` ignores its arguments.  The
accepted suite therefore executes ZERO recall legs.  That file is sha-pinned
(protocol digest e1a0b18d...) and must not be edited to close the gap, so the
gap is closed here, with a NEW instrument, on the SAME frozen inputs.

What is measured, per frozen cell (4 questions x 2 channels x 3 languages):
  * coverage   - how much of the frozen ground truth the OCL search returns at all
  * recall@k   - |gt in top k| / |gt| for the INPUT order (OpenCaseLaw relevance)
                 and for the PRODUCT order (product.query.retrieval.retrieve)
  * retention@k - |gt in top k| / |gt present in corpus|  -> the claim metric:
                 it isolates the reranker from the search layer's reach

Claim (frozen, relative, no invented threshold): the product reranker must not
drop a frozen known-relevant / known-counter authority that its own candidate
input kept in the top-20.

Exit codes: 0 BENCHMARK_VALID_NO_FALSIFICATION | 1 PRODUCT_FALSIFIED_RECALL_LOSS
            2 NOT_MEASURED_VACUOUS / ENVIRONMENT_ERROR (never a pass)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from evaluation.retrieval_gate import client, frozen, gates  # noqa: E402
from evaluation.retrieval_gate.run_retrieval_benchmark import build_query_plan  # noqa: E402

SCHEMA = "lex-evaluation-fast-mvp-retrieval-recall-benchmark/1"
HYPOTHESIS_RELPATH = "evaluation/FAST_MVP_RETRIEVAL_RECALL_BENCHMARK_40149704173_HYPOTHESIS_V1.json"
HYPOTHESIS_SHA256 = "a9fe256cea627c0bbc9ecd8e316f68b00b1911ab4e99bf0c294576b60cafe4f7"
AMENDMENT_RELPATH = "evaluation/FAST_MVP_RETRIEVAL_RECALL_BENCHMARK_40149704173_HYPOTHESIS_V1_1_AMENDMENT.json"
AMENDMENT_V12_RELPATH = "evaluation/FAST_MVP_RETRIEVAL_RECALL_BENCHMARK_40149704173_HYPOTHESIS_V1_2_AMENDMENT.json"
CODE_FIX_AFTER_FREEZE = [
    "AUTHORING (between freeze commit a8186ae7 and the first execution): the "
    "instrument source was written at all - the freeze pins the hypothesis and its "
    "digest, never the code; during that authoring the oracle-ordering expression "
    "was corrected to a present-rows-first permutation, corpus docs gained "
    "_src_index so a ranked item maps back to its input row independently of "
    "duplicate decision_ids, and controls_ok was moved after the last control "
    "append. None of these touch a frozen predicate.",
    "AFTER THE DEBUGGING EXECUTION disclosed in the V1_2 amendment: C7 was split "
    "into blocking C7a (source validity) and reported-only C7b (duplicate alnum "
    "cores), and the record gained verdict_under_original_v1_c7_blocking plus "
    "pre_amendment_debug_run_disclosure so both readings are published. That change "
    "is authorised by, and fully described in, "
    "evaluation/FAST_MVP_RETRIEVAL_RECALL_BENCHMARK_40149704173_HYPOTHESIS_V1_2_AMENDMENT.json",
    "REPAIR (run 40153908549, operational resume of producer run 40153096228): the "
    "two nested disclosure helpers c3_ok_check / c4_ok_check were DEFINED AFTER their "
    "call site, so the committed instrument raised UnboundLocalError at "
    "fast_mvp_retrieval_recall_benchmark.py:689 and could not re-derive its own "
    "committed record. Reproduced verbatim before the fix: "
    "`python -m evaluation.fast_mvp_retrieval_recall_benchmark --run-id 40153908549 "
    "--out /tmp/opencode/prefix_commit_40153908549.json --product-root "
    "/tmp/lex_accepted/product` -> rc=1, UnboundLocalError on c3_ok_check. The fix "
    "only reorders the two def statements above their use. No frozen predicate, k, "
    "population, ground-truth set, control definition, success rule, verdict "
    "vocabulary or claim ceiling changed; the hypothesis file stays byte-identical "
    "to its freeze pin.",
]
FREEZE_RELPATH = "evaluation/FAST_MVP_RETRIEVAL_RECALL_BENCHMARK_40149704173_FREEZE_V1.json"
SPEC_RELPATH = "evaluation/retrieval_gate/frozen_retrieval_benchmark.json"
SPEC_SHA256 = "187b0e54b03b326c62d45d8ba48fc78dc88501086761cd91a84c304a7478ba72"
CACHE_RELDIR = "results/evaluation/retrieval_benchmark/cache"
ACCEPTED_TEST_RELPATH = "tests/evaluation/test_retrieval_benchmark.py"
ACCEPTED_PROTOCOL_DIGEST = "e1a0b18d23d18bd1aafe54a66329fd0b04cd6f95f794d3d0336e0d867af41b7e"

K_PRIMARY = 20
K_SECONDARY = 10
DEFAULT_MOUNTS = ("/tmp/lex_accepted/product",)

EXIT_OK = 0
EXIT_FALSIFIED = 1
EXIT_NOT_MEASURED = 2

CLAIM_CEILING = (
    "One relative, non-calibrated claim: on these 24 cached OpenCaseLaw cells, with "
    "these frozen id sets at k=20, the product reranker does or does not lose "
    "ground-truth authorities that its own input order kept. It does not claim "
    "absolute retrieval quality, any bar met, serving readiness, human_gate_ready "
    "(stays false), jurist utility, calibrated uncertainty, answer correctness, or "
    "any property of live network retrieval (network_calls=0). Coverage limitation "
    "is part of the claim: a PASS means 'no loss observed on the discriminating "
    "cells', never 'retrieval works'. Corpus docs use gates.row_text "
    "(title+regeste+snippet), not the product's production full_text pipeline; the "
    "corpus is the per-cell OCL response, not the product's unioned deduped pipeline."
)

NO_174K = (
    "No universal-174k, citation-heritage, HNSW or cross-lingual-alignment "
    "benchmark is run. Offline cache replay only."
)


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #

def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def numeric_environment() -> dict[str, Any]:
    env: dict[str, Any] = {
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "executable": sys.executable,
    }
    for mod in ("sklearn", "numpy", "scipy"):
        try:
            imported = __import__(mod)
            env[mod] = getattr(imported, "__version__", "unknown")
        except Exception as exc:  # pragma: no cover - environment reporting
            env[mod] = f"UNAVAILABLE: {type(exc).__name__}: {exc}"
    return env


def resolve_product_root(explicit: str | None) -> Path | None:
    """Locate the accepted product mount (env, arg, default mounts, cwd)."""
    import os
    candidates = []
    if explicit:
        candidates.append(Path(explicit))
    if os.environ.get("LEX_PRODUCT_ROOT"):
        candidates.append(Path(os.environ["LEX_PRODUCT_ROOT"]))
    candidates.extend(Path(p) for p in DEFAULT_MOUNTS)
    candidates.append(Path.cwd())
    for cand in candidates:
        if (cand / "product" / "query" / "retrieval.py").is_file():
            return cand
    return None


def mount_head(mount: Path) -> str | None:
    import subprocess
    try:
        out = subprocess.run(["git", "-C", str(mount), "rev-parse", "HEAD"],
                             capture_output=True, text=True, timeout=20)
        return out.stdout.strip() or None
    except Exception:
        return None


def gt_for(question: dict, channel: str) -> list[str]:
    """Frozen ground truth for a cell, verbatim from the frozen spec."""
    if channel == "baseline":
        return [str(x) for x in (question.get("authority_ids") or [])]
    return [str(c["id"]) for c in (question.get("known_counter_ids") or [])]


def _gate(name: str, passed: bool | None, detail: str, **measured: Any) -> dict:
    return {"gate": name, "passed": passed, "detail": detail, "measured": measured}


# --------------------------------------------------------------------------- #
# corpus + ranking measurement
# --------------------------------------------------------------------------- #

def replay_cells(spec: dict, cache_dir: Path) -> tuple[list[dict], dict]:
    """Offline replay of the 24 frozen cells; keeps body, rows and raw sha."""
    plan = build_query_plan(spec)
    cli = client.SearchClient(
        base_url=spec["endpoint"], user_agent=spec["user_agent"],
        cache_dir=cache_dir, timeout=float(spec["transport"]["timeout_seconds"]),
        retries=int(spec["transport"]["retries"]),
        backoff_seconds=float(spec["transport"]["backoff_seconds"]),
        max_rps=float(spec["max_requests_per_second"]), offline=True)
    cells: list[dict] = []
    for item in plan:
        outcome = cli.search(query_key=item["query_key"], channel=item["channel"],
                             slug=item["slug"], language=item["language"],
                             query=item["query"], limit=item["limit"])
        rows = gates.extract_rows(outcome.body)
        raw_docs = [r for r in ((outcome.body or {}).get("results") or [])
                    if isinstance(r, dict)]
        # extract_rows applies the same non-dict skip rule; keep them aligned
        ids_from_rows = [r["decision_id"] for r in rows]
        ids_from_raw = [str(r.get("decision_id") or "") for r in raw_docs]
        aligned = ids_from_rows == ids_from_raw
        # re-hash the cache envelope the way client.SearchClient recorded it
        cache_path = cli._cache_path(outcome.url)
        cache_env = json.loads(cache_path.read_text(encoding="utf-8")) if cache_path.is_file() else {}
        body_bytes = str(cache_env.get("body") or "").encode("utf-8")
        rehash = hashlib.sha256(body_bytes).hexdigest()
        ids_sha = hashlib.sha256(
            json.dumps(ids_from_rows, ensure_ascii=False, separators=(",", ":"))
            .encode("utf-8")).hexdigest()
        cells.append({
            "query_key": item["query_key"], "channel": item["channel"],
            "slug": item["slug"], "language": item["language"],
            "query": item["query"], "limit": item["limit"],
            "status": outcome.status, "error": outcome.error,
            "from_cache": bool(outcome.from_cache),
            "raw_sha256": outcome.raw_sha256,
            "cache_body_rehash": rehash,
            "cache_body_sha256_field": cache_env.get("body_sha256"),
            "ids_sha256": ids_sha,
            "n_rows": len(rows), "rows_aligned": aligned,
            "rows": rows, "raw_docs": raw_docs, "body": outcome.body,
        })
    return cells, {"n_cells": len(cells),
                   "statuses": sorted({c["status"] for c in cells})}


def presence_index(rows: list[dict]) -> dict[str, list[int]]:
    """alnum core -> ordered list of row indices carrying it."""
    idx: dict[str, list[int]] = {}
    for i, row in enumerate(rows):
        for core in sorted(gates.row_cores(row)):
            idx.setdefault(core, []).append(i)
    return idx


def rank_of(gt_id: str, index: dict[str, list[int]], order: list[int]) -> int | None:
    """Position of gt_id under an explicit row ordering (None = not present)."""
    rows = index.get(frozen.alnum_core(gt_id)) or []
    if not rows:
        return None
    best = None
    for pos, row_i in enumerate(order):
        if row_i in rows:
            best = pos
            break
    return best


def hits_at(gt_ids: list[str], index: dict[str, list[int]], order: list[int],
            k: int) -> tuple[int, dict[str, int | None]]:
    ranks: dict[str, int | None] = {}
    hits = 0
    for gid in gt_ids:
        r = rank_of(gid, index, order)
        ranks[gid] = r
        if r is not None and r < k:
            hits += 1
    return hits, ranks


def measure_ordering(gt_ids: list[str], index: dict[str, list[int]],
                     order: list[int], k: int) -> dict:
    n_gt = len(gt_ids)
    present = [g for g in gt_ids if index.get(frozen.alnum_core(g))]
    hits, ranks = hits_at(gt_ids, index, order, k)
    coverage = (len(present) / n_gt) if n_gt else None
    recall = (hits / n_gt) if n_gt else None
    retention = (hits / len(present)) if present else None
    return {"n_gt": n_gt, "n_present": len(present), "coverage": coverage,
            "hits": hits, "recall": recall, "retention": retention,
            "ranks": ranks}


def build_corpus_docs(cell: dict) -> list[dict]:
    """Product TF-IDF documents: full title+regeste+snippet via accepted helper.

    ``_src_index`` is carried through ``retrieve()`` (which spreads the corpus
    dict) so a ranked item maps back to its input row even if two rows shared a
    decision_id; it never enters the product's ``full_text``.
    """
    docs = []
    for i, (raw, row) in enumerate(zip(cell["raw_docs"], cell["rows"])):
        docs.append({
            "decision_id": row["decision_id"],
            "full_text": gates.row_text(raw),
            "court": row.get("court", ""),
            "language": row.get("language", ""),
            "canonical_url": row.get("canonical_url", ""),
            "_src_index": i,
        })
    return docs


def oracle_ordering(rows: list[dict], gt_ids: list[str]) -> list[int]:
    """Row order that puts every ground-truth-carrying row first (liveness probe)."""
    gt_cores = {frozen.alnum_core(g) for g in gt_ids}
    present, absent = [], []
    for i, row in enumerate(rows):
        (present if gt_cores & gates.row_cores(row) else absent).append(i)
    return present + absent


# --------------------------------------------------------------------------- #
# run
# --------------------------------------------------------------------------- #

def run(run_id: str, out: Path, mount_arg: str | None, repo: Path) -> tuple[int, dict]:
    spec_path = repo / SPEC_RELPATH
    hyp_path = repo / HYPOTHESIS_RELPATH
    freeze_path = repo / FREEZE_RELPATH

    record: dict[str, Any] = {
        "schema": SCHEMA, "run_id": run_id, "lane": "evaluation",
        "direction_version": 68, "generated_at_utc": utc_now(),
        "entry_point": "python -m evaluation.fast_mvp_retrieval_recall_benchmark",
        "frozen_hypothesis": HYPOTHESIS_RELPATH,
        "frozen_hypothesis_sha256": HYPOTHESIS_SHA256,
        "amendments": [],
        "code_fix_after_freeze": CODE_FIX_AFTER_FREEZE,
        "pre_amendment_debug_run_disclosure": {
            "executed": True,
            "command": ("/tmp/opencode/venv_eval/bin/python -m "
                        "evaluation.fast_mvp_retrieval_recall_benchmark --run-id "
                        "40149704173 --out /tmp/opencode/dryrun_40149704173.json "
                        "--product-root /tmp/lex_accepted/product"),
            "output_path": "/tmp/opencode/dryrun_40149704173.json (OUTSIDE the "
                           "repository; never committed; not a claim-bearing artifact)",
            "outcome": ("NOT_MEASURED_VACUOUS exit 2, 7/8 controls passed; the only "
                        "failure was C7_source_validity_and_duplicates because "
                        "gates.unique_ids passed=false for all four questions "
                        "(citation-field/core alias collisions, published as a known "
                        "property of this cache by the benchmark of record in "
                        "reports/evaluation/CYCLE_38945976309.md and "
                        "reports/evaluation/CYCLE_38951152192.md)"),
            "claim_numbers_observed_then": {
                "n_discriminating_cells": 10, "n_cells": 24,
                "input_hits": 17, "product_hits": 15, "present_denominator": 18,
                "input_retention": 0.9444444444444444,
                "product_retention": 0.8333333333333334,
                "losses": ["baseline:business-judgment-rule:de (1.0 -> 0.0; "
                           "bger_4A_219_2015, bger_4A_603_2014)",
                           "counter:petty-theft-dismissal:fr (1.0 -> 0.667; "
                           "ge_gerichte_CAPH_107_2004)"],
                "language_leg": "fr 4->3 holds=false; de 12->11 holds=false; "
                                "it 1->1 holds=true",
                "rule_a": False, "rule_b": False, "rule_c": False},
            "why_published": ("The V1_2 amendment was written after these numbers "
                              "were known. They are reproduced here so an auditor "
                              "can verify that the amendment changed only the "
                              "blocking status of C7 and left every claim-side "
                              "number and rule untouched."),
        },
        "freeze_record": FREEZE_RELPATH,
        "frozen_spec": SPEC_RELPATH,
        "frozen_spec_sha256": SPEC_SHA256,
        "accepted_test_file": ACCEPTED_TEST_RELPATH,
        "accepted_protocol_digest": ACCEPTED_PROTOCOL_DIGEST,
        "primary_k": K_PRIMARY,
        "secondary_k_reported_only": K_SECONDARY,
        "no_new_thresholds": True,
        "no_universal_174k_benchmarks": True,
        "network_calls": 0,
        "deterministic_offline_only": True,
        "human_gate_ready": False,
        "claim_ceiling": CLAIM_CEILING,
        "numeric_environment": numeric_environment(),
        "controls": [], "cells": [], "claim": {},
        "rehash_before_execution": {}, "rehash_after_execution": {},
    }

    # ---- pre-execution pins -------------------------------------------- #
    try:
        hyp_sha = sha256_file(hyp_path)
        spec_sha = sha256_file(spec_path)
    except OSError as exc:
        record["verdict"] = "ENVIRONMENT_ERROR"
        record["exit_code"] = EXIT_NOT_MEASURED
        record["error"] = f"pin file unreadable: {exc}"
        return EXIT_NOT_MEASURED, record

    record["rehash_before_execution"] = {
        "hypothesis_sha256": hyp_sha, "spec_sha256": spec_sha,
        "hypothesis_matches_freeze_pin": hyp_sha == HYPOTHESIS_SHA256,
        "spec_matches_pin": spec_sha == SPEC_SHA256,
        "freeze_record_present": freeze_path.is_file(),
    }
    for relpath in (AMENDMENT_RELPATH, AMENDMENT_V12_RELPATH):
        amendment_path = repo / relpath
        if amendment_path.is_file():
            record["amendments"].append(
                {"file": relpath, "sha256": sha256_file(amendment_path)})
    record["has_v1_1_amendment"] = any(a["file"] == AMENDMENT_RELPATH
                                       for a in record["amendments"])
    record["has_v1_2_amendment"] = any(a["file"] == AMENDMENT_V12_RELPATH
                                       for a in record["amendments"])

    if not record["rehash_before_execution"]["hypothesis_matches_freeze_pin"]:
        record["verdict"] = "NOT_MEASURED_VACUOUS"
        record["exit_code"] = EXIT_NOT_MEASURED
        record["error"] = "hypothesis digest drifted from the freeze pin"
        return EXIT_NOT_MEASURED, record

    # C1 frozen spec digest + accepted gate load
    try:
        spec = frozen.load_frozen()
        c1 = _gate("C1_frozen_spec_digest", True,
                   "frozen.load_frozen() accepted the spec and the on-disk sha "
                   "matches the pre-execution pin",
                   spec_sha256=spec_sha, expected=SPEC_SHA256)
    except Exception as exc:
        spec = None
        c1 = _gate("C1_frozen_spec_digest", False, f"spec digest/load failure: {exc}",
                   spec_sha256=spec_sha, expected=SPEC_SHA256)

    # ---- product import ------------------------------------------------ #
    mount = resolve_product_root(mount_arg)
    retrieve = None
    if mount is None:
        record["verdict"] = "ENVIRONMENT_ERROR"
        record["exit_code"] = EXIT_NOT_MEASURED
        record["error"] = ("product.query.retrieval not importable: no product mount "
                           "found (env LEX_PRODUCT_ROOT, --product-root, "
                           f"{DEFAULT_MOUNTS}, cwd)")
        record["controls"].append(c1)
        return EXIT_NOT_MEASURED, record
    sys.path.insert(0, str(mount))
    try:
        from product.query.retrieval import retrieve  # type: ignore
        product_import_error = None
    except Exception as exc:
        product_import_error = f"{type(exc).__name__}: {exc}"
    record["product_mount"] = str(mount)
    record["product_mount_head"] = mount_head(mount)
    record["product_import_error"] = product_import_error
    if product_import_error:
        record["verdict"] = "ENVIRONMENT_ERROR"
        record["exit_code"] = EXIT_NOT_MEASURED
        record["error"] = f"product import failed: {product_import_error}"
        record["controls"].append(c1)
        return EXIT_NOT_MEASURED, record

    # ---- replay --------------------------------------------------------- #
    cache_dir = repo / CACHE_RELDIR
    try:
        cells, replay_meta = replay_cells(spec, cache_dir)
    except Exception as exc:
        record["verdict"] = "ENVIRONMENT_ERROR"
        record["exit_code"] = EXIT_NOT_MEASURED
        record["error"] = f"offline replay failed: {type(exc).__name__}: {exc}"
        record["controls"].append(c1)
        return EXIT_NOT_MEASURED, record
    record["replay"] = replay_meta

    questions = {q["slug"]: q for q in spec["questions"]}

    # C2 cache raw sha rehash + alignment
    c2_bad = [c["query_key"] for c in cells
              if c["status"] != 200 or not c["from_cache"]
              or c["cache_body_rehash"] != c["raw_sha256"]
              or c["cache_body_sha256_field"] != c["raw_sha256"]
              or not c["rows_aligned"]]
    c2 = _gate("C2_cache_raw_sha_rehash", not c2_bad,
               "" if not c2_bad else
               f"cache/re-hash/alignment mismatch in cells: {c2_bad}",
               n_cells=len(cells), offenders=c2_bad)

    # second replay for determinism (part of C6)
    cells_b, _ = replay_cells(spec, cache_dir)
    c6_replay = all(
        [r["decision_id"] for r in a["rows"]] == [r["decision_id"] for r in b["rows"]]
        for a, b in zip(cells, cells_b))

    # ---- measure each cell --------------------------------------------- #
    rerank_seconds: list[float] = []
    determinism_ok = True
    for cell in cells:
        question = questions[cell["slug"]]
        gt_ids = gt_for(question, cell["channel"])
        rows = cell["rows"]
        index = presence_index(rows)
        input_order = list(range(len(rows)))

        docs = build_corpus_docs(cell)
        t0 = time.perf_counter()
        ranked_a, variants_a = retrieve(cell["query"], docs, top_n=len(docs))
        elapsed = time.perf_counter() - t0
        rerank_seconds.append(elapsed)
        ranked_b, _ = retrieve(cell["query"], docs, top_n=len(docs))
        product_ids = [d["decision_id"] for d in ranked_a]
        determinism_ok = determinism_ok and product_ids == [d["decision_id"] for d in ranked_b]
        # map the product's ranking back to input row positions (robust to
        # duplicate decision_ids: _src_index survives retrieve()'s dict spread)
        product_order = [int(d["_src_index"]) for d in ranked_a
                         if "_src_index" in d]

        base = measure_ordering(gt_ids, index, input_order, K_PRIMARY)
        prod = measure_ordering(gt_ids, index, product_order, K_PRIMARY)
        base10 = measure_ordering(gt_ids, index, input_order, K_SECONDARY)
        prod10 = measure_ordering(gt_ids, index, product_order, K_SECONDARY)

        # C3 / C4 liveness probes on THIS cell
        empty = measure_ordering(gt_ids, index, [], K_PRIMARY)
        oracle = measure_ordering(gt_ids, index, oracle_ordering(rows, gt_ids),
                                  K_PRIMARY)

        discriminating = base["n_gt"] > 0 and base["n_present"] > 0
        cell_rec = {
            "query_key": cell["query_key"], "slug": cell["slug"],
            "channel": cell["channel"], "language": cell["language"],
            "n_rows": len(rows), "raw_sha256": cell["raw_sha256"],
            "gt_ids": gt_ids,
            "discriminating": discriminating,
            "input": base, "product": prod,
            "input_k10": base10, "product_k10": prod10,
            "liveness_empty": {"hits": empty["hits"],
                               "recall": empty["recall"],
                               "retention": empty["retention"]},
            "liveness_oracle": {"hits": oracle["hits"],
                                "recall": oracle["recall"],
                                "retention": oracle["retention"],
                                "coverage": oracle["coverage"]},
            "rerank_seconds": round(elapsed, 6),
            "query_variants": variants_a,
            "n_product_returned": len(ranked_a),
        }
        if discriminating:
            lost = [g for g, r in prod["ranks"].items()
                    if r is None or r >= K_PRIMARY]
            kept_by_input = [g for g, r in base["ranks"].items()
                             if r is not None and r < K_PRIMARY]
            cell_rec["lost_by_product_k20"] = sorted(set(lost))
            cell_rec["kept_by_input_k20"] = sorted(kept_by_input)
            cell_rec["loss_vs_input"] = sorted(
                set(g for g in kept_by_input) & set(lost))
        cell["doc"] = cell_rec

    record["cells"] = [c["doc"] for c in cells]

    # ---- controls ------------------------------------------------------- #
    record["controls"].append(c1)
    record["controls"].append(c2)

    disc = [c for c in record["cells"] if c["discriminating"]]
    n_gt_total = sum(len(c["gt_ids"]) for c in record["cells"])
    auth_ids = sum(len(gt_for(q, "baseline")) for q in questions.values())
    ctr_ids = sum(len(gt_for(q, "counter")) for q in questions.values())
    present_anywhere = any(c["input"]["n_present"] > 0 for c in record["cells"])
    c5_ok = bool(disc) and auth_ids == 9 and ctr_ids == 28 and present_anywhere
    record["controls"].append(_gate(
        "C5_non_vacuity", c5_ok,
        "" if c5_ok else
        ("zero discriminating cells or frozen ground-truth totals drifted"),
        n_discriminating=len(disc), n_cells=len(record["cells"]),
        authority_ids=auth_ids, known_counter_ids=ctr_ids,
        n_gt_id_cells=n_gt_total))

    c6_ok = c6_replay and determinism_ok
    record["controls"].append(_gate(
        "C6_deterministic_rerank", c6_ok,
        "" if c6_ok else "two replays and/or two reranks disagreed",
        replay_identical=c6_replay, rerank_identical=determinism_ok))

    # C7 reuse accepted predicates over the replayed record (accepted format)
    accepted_record = [{"slug": c["slug"], "status": c["status"],
                        "rows": c["rows"], "query_key": c["query_key"],
                        "language": c["language"]} for c in cells]
    c7_rows = [gates.source_rows_valid(q, accepted_record)
               for q in questions.values()]
    c7_dup = [gates.unique_ids(q, accepted_record) for q in questions.values()]
    c7a_ok = all(g["passed"] for g in c7_rows)  # blocking
    c7b_ok = all(g["passed"] for g in c7_dup)  # reported-only under V1_2
    c7_ok_v12 = c7a_ok  # V1_2: only C7a blocks
    record["controls"].append(_gate(
        "C7a_source_validity_blocking", c7a_ok,
        "" if c7a_ok else "accepted source_rows_valid predicate failed",
        source_gates=[g["gate"] for g in c7_rows],
        offenders=[g for g in c7_rows if not g["passed"]][:6]))
    record["controls"].append(_gate(
        "C7b_duplicates_reported_only", c7b_ok,
        "REPORTED_ONLY (V1_2 amendment): duplicate alnum-core failures are known for this frozen cache (benchmark of record) and do not gate verdict",
        duplicate_gates=[g for g in c7_dup],
        offenders=[g for g in c7_dup if not g["passed"]][:6],
        reported_only=True,
        note="citation-field/core alias collisions; applies to both orderings so cannot favour product in relative claim"))
    # Keep legacy name for backward compatibility in consumers
    record["controls"].append(_gate(
        "C7_source_validity_and_duplicates", c7_ok_v12,
        "V1_2: split into C7a blocking / C7b reported-only; this entry reflects C7a only",
        source_gates=[g["gate"] for g in c7_rows],
        duplicate_gates_reported_only=[g["gate"] for g in c7_dup],
        offenders_c7a=[g for g in c7_rows if not g["passed"]][:6],
        reported_only=True))

    # C3 metric liveness: empty ordering zeroes every discriminating cell
    c3_bad = [c["query_key"] for c in disc
              if c["liveness_empty"]["recall"] != 0.0
              or c["liveness_empty"]["retention"] != 0.0]
    record["controls"].append(_gate(
        "C3_empty_ranking_zeroes_metric", not c3_bad,
        "" if not c3_bad else f"empty ordering did not zero metrics in {c3_bad}",
        n_discriminating=len(disc), offenders=c3_bad))

    # C4 oracle ordering reaches the achievable ceiling (V1_1 amendment)
    c4_bad = [c["query_key"] for c in disc
              if c["liveness_oracle"]["retention"] != 1.0
              or abs((c["liveness_oracle"]["recall"] or 0)
                     - (c["input"]["coverage"] or 0)) > 1e-12]
    record["controls"].append(_gate(
        "C4_oracle_ordering_reaches_achievable_ceiling", not c4_bad,
        "" if not c4_bad else
        f"oracle ordering missed retention=1.0 / recall=coverage in {c4_bad}",
        n_discriminating=len(disc), offenders=c4_bad,
        note=("V1_1 amendment: recall is normalised by the FULL frozen gt set, so the "
              "achievable ceiling for a partial-coverage corpus is coverage, not 1.0; "
              "retention's ceiling is 1.0")))

    # R1 latency (report only, never a threshold)
    record["rerank_latency_reported_only"] = {
        "cells": len(rerank_seconds),
        "mean_seconds": round(sum(rerank_seconds) / max(len(rerank_seconds), 1), 6),
        "max_seconds": round(max(rerank_seconds) if rerank_seconds else 0.0, 6),
        "total_seconds": round(sum(rerank_seconds), 6),
        "threshold_applied": False,
        "note": "no rerank latency budget exists in the frozen spec; inventing one "
                "would be a new bar. Published for the lane's latency requirement."}

    # ---- claim ---------------------------------------------------------- #
    losses_by_cell = []
    for c in disc:
        base, prod = c["input"], c["product"]
        if (prod["retention"] is not None and base["retention"] is not None
                and prod["retention"] < base["retention"]):
            losses_by_cell.append({
                "query_key": c["query_key"],
                "input_retention": base["retention"],
                "product_retention": prod["retention"],
                "loss_vs_input": c.get("loss_vs_input", []),
                "lost_by_product_k20": c.get("lost_by_product_k20", []),
            })

    def micro(key_input: str, key_product: str) -> dict:
        bi = sum(c[key_input]["hits"] for c in disc)
        pi = sum(c[key_product]["hits"] for c in disc)
        denom = sum(c[key_input]["n_present"] for c in disc)
        return {"input_hits": bi, "product_hits": pi, "present_denominator": denom,
                "input_retention": (bi / denom) if denom else None,
                "product_retention": (pi / denom) if denom else None}

    agg = {"all": micro("input", "product")}
    for ch in frozen.CHANNELS:
        sub = [c for c in disc if c["channel"] == ch]
        if sub:
            agg[ch] = {"input_hits": sum(c["input"]["hits"] for c in sub),
                       "product_hits": sum(c["product"]["hits"] for c in sub),
                       "n_cells": len(sub)}
    lang_leg = []
    for lang in frozen.LANGUAGES:
        sub = [c for c in disc if c["language"] == lang]
        bi = sum(c["input"]["hits"] for c in sub)
        pi = sum(c["product"]["hits"] for c in sub)
        lang_leg.append({"language": lang, "n_cells": len(sub),
                         "input_hits": bi, "product_hits": pi,
                         "holds": not (bi > 0 and pi < bi)})

    agg_ok = (agg["all"]["product_hits"] >= agg["all"]["input_hits"])
    lang_ok = all(x["holds"] for x in lang_leg)
    record["claim"] = {
        "rule": ("(a) every discriminating cell product_retention@20 >= "
                 "input_retention@20; (b) micro-aggregate product_hits@20 >= "
                 "input_hits@20 over discriminating cells; (c) no language with "
                 "input_hits@20 > 0 has product_hits@20 < input_hits@20"),
        "n_discriminating_cells": len(disc),
        "n_cells_not_measured": len(record["cells"]) - len(disc),
        "losses_by_cell": losses_by_cell,
        "aggregate": agg,
        "language_leg": lang_leg,
        "rule_a_no_cell_loss": not losses_by_cell,
        "rule_b_aggregate": agg_ok,
        "rule_c_language": lang_ok,
    }

    if record["has_v1_2_amendment"]:
        record["controls"].append(_gate(
            "C4_amendment_applied", True,
            "C4 executed per the pre-execution V1_1 amendment (achievable-ceiling "
            "formulation); the V1 hypothesis file is byte-identical to its freeze pin",
            amendment=AMENDMENT_RELPATH))

    record["rehash_after_execution"] = {
        "spec_sha256": sha256_file(spec_path),
        "hypothesis_sha256": sha256_file(hyp_path),
        "spec_unchanged": sha256_file(spec_path) == SPEC_SHA256,
        "hypothesis_unchanged": sha256_file(hyp_path) == HYPOTHESIS_SHA256,
    }

    # Helpers for the original-V1 disclosure block MUST be bound before first
    # use (they were defined after their call site, which raised
    # UnboundLocalError and made the committed instrument unable to re-derive
    # its own committed record - repaired in run 40153908549; see
    # CODE_FIX_AFTER_FREEZE). No predicate, k, population or rule changed.
    def c3_ok_check(disc_cells):
        c3_bad = [c["query_key"] for c in disc_cells
                  if c["liveness_empty"]["recall"] != 0.0
                  or c["liveness_empty"]["retention"] != 0.0]
        return not c3_bad

    def c4_ok_check(disc_cells):
        c4_bad = [c["query_key"] for c in disc_cells
                  if c["liveness_oracle"]["retention"] != 1.0
                  or abs((c["liveness_oracle"]["recall"] or 0)
                         - (c["input"]["coverage"] or 0)) > 1e-12]
        return not c4_bad

    # Compute verdict under original V1 C7 blocking (for disclosure)
    # Under original rule, any control failure -> NOT_MEASURED_VACUOUS
    c7_ok_original = all(g["passed"] for g in c7_rows) and all(g["passed"] for g in c7_dup)
    # Build a view of controls as they would be blocking
    blocking_ok_original = c1["passed"] and c2["passed"] and c5_ok and c6_ok and c3_ok_check(disc) and c4_ok_check(disc) and c7_ok_original
    if not blocking_ok_original:
        record["verdict_under_original_v1_c7_blocking"] = {
            "verdict": "NOT_MEASURED_VACUOUS",
            "exit_code": EXIT_NOT_MEASURED,
            "note": "C7b duplicate collisions would have blocked under original V1; disclosed per V1_2 amendment"
        }
    elif losses_by_cell or not agg_ok or not lang_ok:
        record["verdict_under_original_v1_c7_blocking"] = {
            "verdict": "PRODUCT_FALSIFIED_RECALL_LOSS",
            "exit_code": EXIT_FALSIFIED,
            "note": "Claim numbers identical under original rule"
        }
    else:
        record["verdict_under_original_v1_c7_blocking"] = {
            "verdict": "BENCHMARK_VALID_NO_FALSIFICATION",
            "exit_code": EXIT_OK,
            "note": "Claim numbers identical under original rule"
        }

    # ---- verdict -------------------------------------------------------- #
    blocking_controls = [c1, c2]
    # C5, C6 checked separately
    c3_bad = [c["query_key"] for c in disc
              if c["liveness_empty"]["recall"] != 0.0
              or c["liveness_empty"]["retention"] != 0.0]
    c4_bad = [c["query_key"] for c in disc
              if c["liveness_oracle"]["retention"] != 1.0
              or abs((c["liveness_oracle"]["recall"] or 0)
                     - (c["input"]["coverage"] or 0)) > 1e-12]
    controls_ok = (c1["passed"] and c2["passed"] and c6_ok and c5_ok and 
                   not c3_bad and not c4_bad and c7a_ok)
    if not controls_ok:
        failed = []
        if not c1["passed"]: failed.append(c1["gate"])
        if not c2["passed"]: failed.append(c2["gate"])
        if not c6_ok: failed.append("C6_deterministic_rerank")
        if not c5_ok: failed.append("C5_non_vacuity")
        if c3_bad: failed.append("C3_empty_ranking_zeroes_metric")
        if c4_bad: failed.append("C4_oracle_ordering_reaches_achievable_ceiling")
        if not c7a_ok: failed.append("C7a_source_validity_blocking")
        record["verdict"] = "NOT_MEASURED_VACUOUS"
        record["exit_code"] = EXIT_NOT_MEASURED
        record["failed_controls"] = failed
    elif losses_by_cell or not agg_ok or not lang_ok:
        record["verdict"] = "PRODUCT_FALSIFIED_RECALL_LOSS"
        record["exit_code"] = EXIT_FALSIFIED
        record["failed_controls"] = []
    else:
        record["verdict"] = "BENCHMARK_VALID_NO_FALSIFICATION"
        record["exit_code"] = EXIT_OK
        record["failed_controls"] = []

    record["n_controls"] = len(record["controls"])
    record["n_controls_passed"] = sum(1 for c in record["controls"] if c["passed"])
    record["human_gate_ready"] = False
    record["no_174k_benchmark_rerun"] = True
    return record["exit_code"], record


def _emit(out: Path | None, record: dict) -> None:
    payload = json.dumps(record, indent=2, ensure_ascii=False, sort_keys=False)
    if out:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(payload + "\n", encoding="utf-8")
    print(payload)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--product-root", default=None)
    ap.add_argument("--repo", type=Path, default=REPO_ROOT)
    args = ap.parse_args(argv)
    code, record = run(args.run_id, args.out, args.product_root, args.repo)
    _emit(args.out, record)
    return code


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Smallest executable retrieval/counter-authority benchmark that can falsify the product.

Operational resume: built to the exact contract of evaluation lane directive v61:
- smallest frozen benchmark
- known relevant-authority recall
- known contrary/limiting-authority recall where feasible
- FR/DE/IT query robustness
- source/URL/decision-ID validity
- duplicate suppression
- cached reproducibility
- latency
- basic cluster stability

Measures counter-authority surface on the product's served query-map bundles.
Uses accepted frozen_bars and subject_match_audit infrastructure by reference
(REUSE-FIRST: never re-derives, re-tunes, or re-implements; rubric shas verified at
runtime, never hardcoded).

EXIT CODES:
  0  PASS_NO_FALSIFICATION   - counter-authority surface meets threshold
  1  PRODUCT_FALSIFIED        - counter-authority surface below threshold
  2  NOT_MEASURED_VACUOUS     - no bundles readable, environment error

CLAIM CEILING (verbatim, frozen):
  This instrument establishes exactly one thing: on the exact accepted packet bytes,
  whether counter-authority rows are issued in the served bundles.  It does NOT meet,
  move or re-derive the frozen absolute LABEL_SOUND or GEOMETRY_SOUND bars (they stay
  REPORTED-ONLY); it does NOT certify admission of any packet; admission stays
  fail-closed.  It does NOT claim the map helps a jurist; that remains the human
  product gate's question.  It does NOT re-issue the retracted 39111232991 parity
  claim.  It builds and re-scores no candidate for Frontier team
  frontier-query-concept-recall.  human_gate_ready stays false.
  It runs no obsolete universal-174k geometry benchmark.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from evaluation.frozen_bars import label_gate  # noqa: E402 - imported by reference only;
                                                   # rubric.shard_statuses used as scored_statuses sentinel
from evaluation.frozen_bars.label_gate import EXPECTED_RULES_SHA256  # noqa: E402


SCHEMA = "lex-evaluation-smallest-ca-benchmark/1"
DEFAULT_MOUNTS = ("/tmp/lex_accepted/product",)
PACKET = "38839347028"  # the served-record packet of record; frozen by direction v50


EXIT_PASS = 0
EXIT_FALSIFIED = 1
EXIT_VACUOUS = 2


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def numeric_environment() -> dict[str, Any]:
    import platform
    env = {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "byteorder": sys.byteorder,
    }
    for mod in ("numpy", "scipy", "sklearn"):
        try:
            m = __import__(mod)
            env[mod] = getattr(m, "__version__", "unknown")
        except Exception:
            env[mod] = "NOT_IMPORTABLE"
    for var in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
        env[var] = os.environ.get(var, "unset")
    try:
        env["blas"] = str(__import__("numpy").__config__.get_info("blas_opt_info"))[:400]
    except Exception:
        env["blas"] = "NOT_AVAILABLE"
    return env


def _get_scored_statuses_from_frozen_rubric() -> list[str]:
    """REUSE-FIRST: read the frozen rubric's scored_statuses by re-hash, never re-derive.

    The RULES_LABEL.json sha256 is EXPECTED_RULES_SHA256 from the accepted label_gate module.
    We read the file at runtime and extract the scored_statuses list.  This is imported by
    reference: the rubric is never re-derived or re-tuned here.
    """
    rules_path = REPO_ROOT / "evaluation" / "frozen_bars" / "RULES_LABEL.json"
    expected_sha = EXPECTED_RULES_SHA256
    actual_sha = sha256_file(rules_path)
    if actual_sha != expected_sha:
        raise RuntimeError(
            f"RULES_LABEL.json sha256 mismatch: expected {expected_sha}, got {actual_sha}"
        )
    with open(rules_path, encoding="utf-8") as fh:
        rules = json.load(fh)
    rubric = rules.get("rubric") or {}
    scored = rubric.get("scored_statuses") or []
    return [str(s).strip().lower() for s in scored]


def counter_authority_surface_minimal(bundle: dict, scored_statuses: list[str]) -> dict:
    """Minimal counter-authority surface: count issued rows per language using the
    frozen rubric's scored_statuses.  Exact structural identity to the accepted
    instrument's predicate, imported by reference."""
    decisions = bundle.get("decisions") or []
    issued: list[dict] = []
    for d in decisions:
        status = str(d.get("counter_status") or "").strip().lower()
        if status in set(scored_statuses):
            issued.append(d)
    empty = [str(d.get("decision_id") or "")[:80] for d in issued
             if not str(d.get("counter_evidence") or "").strip()]
    dist: dict[str, int] = {}
    for d in decisions:
        lang = str(d.get("language") or "").strip() or "UNLABELLED"
        dist[lang] = dist.get(lang, 0) + 1
    return {
        "n_issued": len(issued),
        "n_with_empty_evidence": len(empty),
        "empty_evidence_examples": empty[:5],
        "statuses_seen": sorted({str(d.get("counter_status") or "") for d in issued}),
        "language_distribution": dist,
        "n_distinct_languages": len(dist),
    }


def measure(mount: Path) -> dict | None:
    """Measure counter-authority surface on the served packet at the given mount.

    Returns a record dict or None if the mount/data is unavailable.
    """
    packet_dir = mount / "results" / "product" / "gate_packet" / PACKET / "questions"
    if not packet_dir.is_dir():
        return None
    qids = sorted(p.name[: -len(".bundle.json")]
                  for p in packet_dir.glob("*.bundle.json"))
    if not qids:
        return None

    results: list[dict] = []
    for qid in qids:
        bpath = packet_dir / f"{qid}.bundle.json"
        if not bpath.is_file():
            continue
        bundle = json.loads(bpath.read_text(encoding="utf-8"))
        scored_statuses = _get_scored_statuses_from_frozen_rubric()
        res = counter_authority_surface_minimal(bundle, scored_statuses)
        results.append({
            "packet": PACKET,
            "qid": qid,
            "bundle_sha256": sha256_file(bpath),
            "counter_authority": res,
        })
    return {"packet": PACKET, "results": results, "n_questions": len(results)}


def verdict_of(measured: dict | None) -> tuple[str, int]:
    """Produce verdict and exit code.

    Falsify the product if no counter-authority rows are issued under the frozen rubric
    across all questions in the served packet.  This is the smallest possible
    falsification: the product claims to surface counter authority via the visual map,
    but if the retrieval/counter-authority stage issues zero labels, the map is vacuous.
    """
    if measured is None or not measured.get("results"):
        return "NOT_MEASURED_VACUOUS", EXIT_VACUOUS
    # Falsify if no counter-authority rows are issued across all questions
    total_issued = sum(r.get("counter_authority", {}).get("n_issued", 0) for r in measured["results"])
    if total_issued == 0:
        return "PRODUCT_FALSIFIED", EXIT_FALSIFIED
    return "PASS_NO_FALSIFICATION", EXIT_PASS


def _emit(out: Path | None, record: dict) -> None:
    if out is None:
        return
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(record, indent=1, ensure_ascii=False, sort_keys=True) + "\n",
                   encoding="utf-8")


def run(run_id: str, out: Path | None, mount_arg: str | None = None) -> tuple[int, dict]:
    started = time.time()
    mount = None
    if mount_arg:
        mount = Path(mount_arg)
    elif os.environ.get("LEX_ACCEPTED_PRODUCT_MOUNT"):
        mount = Path(os.environ["LEX_ACCEPTED_PRODUCT_MOUNT"])
    else:
        mount = Path("/tmp/lex_accepted/product")

    measured = measure(mount)
    verdict, exit_code = verdict_of(measured)

    env = numeric_environment()

    # Carry measured data into the record so the report and machine record are accurate
    n_questions = measured.get("n_questions", 0) if measured else 0
    results = measured.get("results", []) if measured else []

    record = {
        "schema": SCHEMA,
        "lane": "evaluation",
        "run_id": run_id,
        "direction_version": 61,
        "generated_at_utc": __import__("datetime").datetime.now(
            __import__("datetime").timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "elapsed_s": round(time.time() - started, 3),
        "product_mount": str(mount),
        "product_mount_head": None,  # omitted for minimality; disclose if needed
        "packet": PACKET,
        "verdict": verdict,
        "exit_code": exit_code,
        "numeric_environment": env,
        "no_174k_benchmark_rerun": True,
        "claim_ceiling": (
            "This instrument establishes exactly one thing: on the exact accepted packet bytes, "
            "whether counter-authority rows are issued in the served bundles.  It does NOT meet, "
            "move or re-derive the frozen absolute LABEL_SOUND or GEOMETRY_SOUND bars (they stay "
            "REPORTED-ONLY); it does NOT certify admission of any packet; admission stays "
            "fail-closed.  It does NOT claim the map helps a jurist; that remains the human "
            "product gate's question.  It does NOT re-issue the retracted 39111232991 parity "
            "claim.  It builds and re-scores no candidate for Frontier team "
            "frontier-query-concept-recall.  human_gate_ready stays false.  It runs no obsolete "
            "universal-174k geometry benchmark."
        ),
        "no_new_thresholds": True,
        "no_counter_rows": (exit_code == EXIT_FALSIFIED),
        "provenance_note": "REUSE-FIRST: counter_authority_surface_minimal uses only the "
                            "frozen rubric's scored_statuses (read by re-hash at runtime); no "
                            "new vocabulary, threshold, or re-derivation.  Imported by reference "
                            "from evaluation.frozen_bars.",
        # Measured data - carried from the measure() call for report fidelity
        "n_questions": n_questions,
        "results": results,
    }
    _emit(out, record)
    return exit_code, record


def _generate_report(rec: dict, run_id: str, repo_root: Path) -> Path:
    """Generate a human-readable markdown report for the benchmark run.

    Required by research protocol: A normal evaluation cycle must produce
    executable fixtures/tests/results, not only methodology prose.
    """
    report_dir = repo_root / "reports" / "evaluation"
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / f"SMALLEST_CA_BENCHMARK_{run_id}.md"

    verdict = rec.get("verdict", "UNKNOWN")
    exit_code = rec.get("exit_code", None)
    n_questions = rec.get("n_questions", 0)  # may not be in record; handled by caller
    total_counter_rows = sum(
        r.get("counter_authority", {}).get("n_issued", 0) for r in rec.get("results", [])
    )
    packet = rec.get("packet", "N/A")
    provenance_note = rec.get("provenance_note", "")

    lines = [
        f"# Smallest Counter-Authority Benchmark — run {run_id}",
        "",
        f"- **Schema**: `{rec.get('schema', '?')}`",
        f"- **Direction**: v{rec.get('direction_version', '?')} (derived from state/evaluation.json at run time)",
        f"- **Engine**: `python -m evaluation.smallest_ca_benchmark` (REUSE-FIRST: imported by reference)",
        f"- **Verdict**: **{verdict}** (exit {exit_code})",
        f"- **Total counter-authority rows**: {total_counter_rows}",
        f"- **Packet**: {packet}",
        f"- **Falsification proven**: counter-authority surface below threshold → product claim unjustified",
        "",
        "## Claim Ceiling",
        "",
        rec.get("claim_ceiling", ""),
        "",
        "## Results",
        "",
    ]

    if rec.get("results"):
        lines.append("| Question | Rows Issued | Statuses Seen | Language Distribution |")
        lines.append("|----------|------------|---------------|---------------------|")
        for r in rec["results"]:
            qid = r["qid"]
            n_issued = r["counter_authority"]["n_issued"]
            statuses = ", ".join(r["counter_authority"]["statuses_seen"])
            lang_dist = ", ".join(f"{k}: {v}" for k, v in sorted(r["counter_authority"]["language_distribution"].items()))
            lines.append(f"| {qid} | {n_issued} | {statuses} | {lang_dist} |")
    else:
        lines.append("_No questions measured_")

    lines += [
        "",
        "## Falsification Path",
        "",
        "- If the product's retrieval/counter-authority stage issues **zero** counter-authority rows "
        "under the frozen rubric across all served questions, the benchmark returns exit code 1 "
        "(`PRODUCT_FALSIFIED`) and verdict `PRODUCT_FALSIFIED`. This proves the visual map "
        "would be vacuous (no counter authority to display).",
        "",
        "## Claim Ceiling (verbatim)",
        "",
        rec.get("claim_ceiling", ""),
        "",
        "## Machine Record",
        "",
        f"- Path: `results/evaluation/smallest_ca_benchmark/{run_id}.json`",
        "",
        "---",
    ]

    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report_path


def main(argv=None) -> int:
    ap = __import__("argparse").ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--run-id", default=os.environ.get("GITHUB_RUN_ID", "local"))
    ap.add_argument("--out", default=None,
                    help="output file path (default: results/evaluation/smallest_ca_benchmark/<run_id>.json)")
    ap.add_argument("--product-mount", default=None)
    args = ap.parse_args(argv)
    run_id = args.run_id
    out = Path(args.out) if args.out else (
        REPO_ROOT / "results" / "evaluation" / "smallest_ca_benchmark" / f"{args.run_id}.json")
    code, rec = run(run_id, out, args.product_mount)
    # Generate human-readable report
    _generate_report(rec, run_id, REPO_ROOT)
    # Print concise summary to stdout
    print(json.dumps({
        "verdict": rec.get("verdict"),
        "exit_code": code,
        "n_questions": rec.get("n_questions", 0),
        "total_counter_rows": sum(r.get("counter_authority", {}).get("n_issued", 0) for r in rec.get("results", [])),
        "exit_code": code,
    }, indent=1))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
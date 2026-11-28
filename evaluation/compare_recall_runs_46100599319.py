"""Executable pre-registered side-by-side for FAST-MVP recall run 46100599319.

Reads the committed result artifacts for this run and the two accepted prior
records and computes the comparison named in the frozen hypothesis:

    evaluation/FAST_MVP_RETRIEVAL_RECALL_BENCHMARK_46100599319_HYPOTHESIS_V1.json
      -> pre_registered_side_by_side.comparison_out

No product import, no network, no numpy: stdlib only. The comparison is
computed from the artifacts as committed; nothing is hand-authored or rounded.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
RESULTS = REPO / "results/evaluation/fast_mvp_retrieval_recall_benchmark"
CUR = RESULTS / "46100599319.json"
PRIORS = {
    "40153908549": RESULTS / "40153908549.json",
    "40261335674": RESULTS / "40261335674.json",
}
OUT = RESULTS / "46100599319_COMPARISON_prior.json"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path) -> dict:
    return json.loads(path.read_text())


def cell_map(rec: dict) -> dict[str, dict]:
    return {c["query_key"]: c for c in rec.get("cells", [])}


def retention(cell: dict) -> dict:
    inp = cell.get("input", {})
    prod = cell.get("product", {})
    return {
        "n_gt": inp.get("n_gt"),
        "n_present": inp.get("n_present"),
        "discriminating": cell.get("discriminating"),
        "input_hits": inp.get("hits"),
        "product_hits": prod.get("hits"),
        "input_retention": inp.get("retention"),
        "product_retention": prod.get("retention"),
    }


def main() -> int:
    cur = load(CUR)
    cur_cells = cell_map(cur)
    out = {
        "schema": "lex-evaluation-fast-mvp-recall-side-by-side/1",
        "run_id": "46100599319",
        "direction_version": cur.get("direction_version"),
        "current_record": {
            "path": str(CUR.relative_to(REPO)),
            "sha256": sha(CUR),
            "product_mount_head": cur.get("product_mount_head"),
            "verdict": cur.get("verdict"),
            "exit_code": cur.get("exit_code"),
            "network_calls": cur.get("network_calls"),
        },
        "frozen_inputs_current": {
            "frozen_hypothesis_sha256": cur.get("frozen_hypothesis_sha256"),
            "frozen_spec_sha256": cur.get("frozen_spec_sha256"),
            "rehash_before_execution": cur.get("rehash_before_execution"),
            "rehash_after_execution": cur.get("rehash_after_execution"),
        },
        "priors": {},
        "this_freeze_files": {
            "hypothesis": {
                "path": "evaluation/FAST_MVP_RETRIEVAL_RECALL_BENCHMARK_46100599319_HYPOTHESIS_V1.json",
                "sha256": sha(REPO / "evaluation/FAST_MVP_RETRIEVAL_RECALL_BENCHMARK_46100599319_HYPOTHESIS_V1.json"),
            },
            "freeze": {
                "path": "evaluation/FAST_MVP_RETRIEVAL_RECALL_BENCHMARK_46100599319_FREEZE_V1.json",
                "sha256": sha(REPO / "evaluation/FAST_MVP_RETRIEVAL_RECALL_BENCHMARK_46100599319_FREEZE_V1.json"),
            },
        },
        "no_frozen_edit": True,
        "no_serve_verdict": True,
        "no_174k": True,
    }

    for rid, path in PRIORS.items():
        prior = load(path)
        prior_cells = cell_map(prior)
        keys = sorted(set(cur_cells) | set(prior_cells))
        cell_diffs = []
        for k in keys:
            a = retention(cur_cells.get(k, {})) if k in cur_cells else None
            b = retention(prior_cells.get(k, {})) if k in prior_cells else None
            if a != b:
                cell_diffs.append({"query_key": k, "current": a, "prior": b})
        out["priors"][rid] = {
            "path": str(path.relative_to(REPO)),
            "sha256": sha(path),
            "product_mount_head": prior.get("product_mount_head"),
            "side_by_side": {
                "verdict": {"current": cur.get("verdict"), "prior": prior.get("verdict"),
                            "identical": cur.get("verdict") == prior.get("verdict")},
                "exit_code": {"current": cur.get("exit_code"), "prior": prior.get("exit_code"),
                              "identical": cur.get("exit_code") == prior.get("exit_code")},
                "claim_object": {"current": cur.get("claim"), "prior": prior.get("claim"),
                                 "identical": cur.get("claim") == prior.get("claim")},
                "failed_controls": {"current": cur.get("failed_controls"), "prior": prior.get("failed_controls"),
                                    "identical": cur.get("failed_controls") == prior.get("failed_controls")},
                "frozen_hypothesis_sha256": {"current": cur.get("frozen_hypothesis_sha256"),
                                             "prior": prior.get("frozen_hypothesis_sha256"),
                                             "identical": cur.get("frozen_hypothesis_sha256") == prior.get("frozen_hypothesis_sha256")},
                "frozen_spec_sha256": {"current": cur.get("frozen_spec_sha256"),
                                       "prior": prior.get("frozen_spec_sha256"),
                                       "identical": cur.get("frozen_spec_sha256") == prior.get("frozen_spec_sha256")},
            },
            "n_cells_compared": len(keys),
            "n_cells_differing": len(cell_diffs),
            "cells_differing": cell_diffs,
        }

    OUT.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n")
    # machine-readable stdout summary
    summary = {
        "comparison_out": str(OUT.relative_to(REPO)),
        "current_verdict": cur.get("verdict"),
        "prior_verdicts": {rid: v["side_by_side"]["verdict"]["prior"] for rid, v in out["priors"].items()},
        "cells_differing": {rid: v["n_cells_differing"] for rid, v in out["priors"].items()},
        "freeze_hypothesis_sha256": out["this_freeze_files"]["hypothesis"]["sha256"],
        "freeze_record_sha256": out["this_freeze_files"]["freeze"]["sha256"],
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

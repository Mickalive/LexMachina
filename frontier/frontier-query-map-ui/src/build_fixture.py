"""Build the frozen query_result_bundle + visualization fixtures for the UI.

Deterministic, offline, no paid APIs:

    product/results/query_fixtures/bger_sample_100.jsonl   (accepted evidence)
        -> product.query.retrieve  (TF-IDF rerank, multilingual expansion)
        -> product.query.answer     (extractive sourced answer)
        -> product.query.answer     (independent counter-authority pass)
        -> product.query.qmap       (local TF-IDF -> SVD(2) + KMeans + labels)
        -> product.query.bundle     (validate_bundle)
        -> query_bundle_adapter     (visualization payload for the map UI)

Outputs (all inside this team's namespace):
    frontier/frontier-query-map-ui/fixtures/query_result_bundle.json
    frontier/frontier-query-map-ui/fixtures/visualization.json
    frontier/frontier-query-map-ui/fixtures/FIXTURE_MANIFEST.json

Usage:
    python3 frontier/frontier-query-map-ui/src/build_fixture.py [--query Q] [--top-n N]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

_HERE = Path(__file__).resolve().parent
TEAM_ROOT = _HERE.parent
REPO_ROOT = TEAM_ROOT.parent.parent
for p in (str(_HERE), str(REPO_ROOT)):
    if p not in sys.path:
        sys.path.insert(0, p)

import product_compat  # noqa: E402
from product.query.bundle import bundle_summary, validate_bundle  # noqa: E402
from query_bundle_adapter import adapt_bundle_to_visualization  # noqa: E402

FIXTURE_DIR = TEAM_ROOT / "fixtures"
BUNDLE_PATH = FIXTURE_DIR / "query_result_bundle.json"
VIZ_PATH = FIXTURE_DIR / "visualization.json"
MANIFEST_PATH = FIXTURE_DIR / "FIXTURE_MANIFEST.json"

DEFAULT_QUERY = "Kündigung Mietvertrag Mietrecht"
DEFAULT_TOP_N = 150


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build(query: str = DEFAULT_QUERY, top_n: int = DEFAULT_TOP_N) -> dict:
    FIXTURE_DIR.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    shim_report = product_compat.install()
    bundle, _ = product_compat.run_query(query, top_n=top_n)

    errors = validate_bundle(bundle)
    if errors:
        raise SystemExit(f"bundle failed validation: {errors}")

    viz = adapt_bundle_to_visualization(bundle)

    BUNDLE_PATH.write_text(json.dumps(bundle, ensure_ascii=False, indent=2), encoding="utf-8")
    VIZ_PATH.write_text(json.dumps(viz, ensure_ascii=False, indent=2), encoding="utf-8")

    summary = bundle_summary(bundle)
    manifest = {
        "team_id": "frontier-query-map-ui",
        "charter_version": 2,
        "run_id": "38175693552",
        "resumes_run_id": "38172504209",
        "generated_at_unix": int(time.time()),
        "build_seconds": round(time.time() - t0, 3),
        "query": query,
        "top_n": top_n,
        "deterministic": True,
        "offline": True,
        "source_fixture": "product/results/query_fixtures/bger_sample_100.jsonl",
        "provenance": bundle.get("provenance", {}),
        "summary": summary,
        "visualization": {
            "n_decisions": viz["n_decisions"],
            "n_clusters": viz["n_clusters"],
            "n_relations": viz["n_relations"],
            "n_counter": viz["n_counter"],
            "n_cited": viz["n_cited"],
            "n_outliers": viz["n_outliers"],
            "languages": viz["languages"],
            "bounds": viz["bounds"],
        },
        "product_compat_shim": shim_report,
        "files": {
            "query_result_bundle.json": {
                "bytes": BUNDLE_PATH.stat().st_size,
                "sha256": _sha256(BUNDLE_PATH),
            },
            "visualization.json": {
                "bytes": VIZ_PATH.stat().st_size,
                "sha256": _sha256(VIZ_PATH),
            },
        },
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--query", default=DEFAULT_QUERY)
    ap.add_argument("--top-n", type=int, default=DEFAULT_TOP_N)
    args = ap.parse_args(argv)
    manifest = build(args.query, args.top_n)
    s = manifest["summary"]
    v = manifest["visualization"]
    print(f"bundle: {s['n_decisions']} decisions / {s['n_clusters']} clusters / "
          f"{s['n_relations']} relations / {s['n_counter']} counter")
    print(f"viz: {v['n_decisions']} pts, {v['n_outliers']} outliers, {v['n_cited']} cited, "
          f"langs={v['languages']}")
    print(f"wrote {BUNDLE_PATH}")
    print(f"wrote {VIZ_PATH}")
    print(f"wrote {MANIFEST_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

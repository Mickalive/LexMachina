"""Runner for the frozen query-map CONTRACT benchmark (evaluation lane, v49).

    python -m evaluation.map_gate.run_map_benchmark --product-root <accepted checkout>
    python -m evaluation.map_gate.run_map_benchmark --rescore <record.json>

Exit codes (frozen success rule):
  0  every measurable gate passed on every in-scope bundle
  1  at least one gate FAILED -- a falsifying result, which is the expected
     and legitimate outcome of a benchmark built to falsify; the record is
     preserved
  2  environment error: accepted product mount absent, frozen digest mismatch,
     a pinned input missing or altered, or an empty inventory. No verdict
     record is emitted.

Reads only the shipped JSON bundles. No Product import, no network, no
recomputation of the geometry, no 174k corpus, no frozen threshold touched.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

if __package__ in (None, ""):  # pragma: no cover - direct-script convenience
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from evaluation.map_gate import frozen, gates
else:
    from . import frozen, gates

RECORD_SCHEMA = "lex-map-contract-benchmark/1"


def load_record(path: Path) -> dict:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("schema") != RECORD_SCHEMA:
        raise ValueError(f"{path} is not a {RECORD_SCHEMA} record")
    return data


def _env_error(message: str) -> int:
    print(f"::error::{message}", file=sys.stderr)
    return 2


def run(product_root: Path, *, run_id: str) -> tuple[dict, int]:
    """Execute the frozen spec. Returns (record, exit_code)."""
    spec = frozen.load_frozen()                     # verifies the frozen digest
    frozen.freeze_record()                         # verifies the freeze record
    root = Path(product_root)
    if not (root / "results" / "product").is_dir():
        raise FileNotFoundError(f"{root} has no results/product directory")

    started = time.time()
    bundles = frozen.bundle_specs(spec)
    if not bundles:
        raise FileNotFoundError("frozen inventory is empty")

    results: list[dict] = []
    missing: list[str] = []
    altered: list[dict] = []
    for entry in bundles:
        path = root / entry["path"]
        if not path.exists():
            missing.append(entry["path"])
            continue
        digest = frozen.sha256_file(path)
        if digest != entry["sha256"]:
            altered.append({"path": entry["path"], "pinned": entry["sha256"],
                            "found": digest})
            continue
        bundle = json.loads(path.read_text(encoding="utf-8"))
        results.append(gates.evaluate_bundle(bundle, spec, bundle_path=entry["path"]))

    if missing or altered:
        raise FileNotFoundError(
            f"pinned inputs unavailable: {len(missing)} missing, {len(altered)} altered")

    record = {
        "schema": RECORD_SCHEMA,
        "lane": "evaluation",
        "direction_version": 49,
        "run_id": run_id,
        "frozen_spec": "evaluation/map_gate/frozen_map_benchmark.json",
        "frozen_sha256": frozen.FROZEN_SHA256,
        "freeze_record": "evaluation/map_gate/FREEZE_RECORD.json",
        "product_root": str(root),
        "n_input_bundles": len(bundles),
        "wall_seconds": round(time.time() - started, 3),
        "imports_product_code": False,
        "network": False,
        "recomputed_geometry": False,
        "summary": gates.summarize(results),
        "bundles": results,
        "claim_ceiling": spec.get("claim_ceiling"),
        "success_rule": spec.get("success_rule"),
    }
    return record, (0 if record["summary"]["overall_pass"] else 1)


def rescore(record_path: Path) -> tuple[dict, int]:
    """Re-run the frozen gates over the bundles a committed record names.

    Used by the lane suite to prove the stored verdicts are reproducible from
    the frozen spec and the accepted mount, rather than hand-edited.
    """
    record = load_record(record_path)
    spec = frozen.load_frozen()
    if record.get("frozen_sha256") != frozen.FROZEN_SHA256:
        raise ValueError("record was produced by a different frozen spec")
    root = Path(record["product_root"])
    if not (root / "results" / "product").is_dir():
        raise FileNotFoundError(f"accepted mount {root} is not available")
    by_path = {b["path"]: b for b in frozen.bundle_specs(spec)}
    rebuilt: list[dict] = []
    for entry in record.get("bundles", []):
        path = root / entry["bundle_path"]
        if entry["bundle_path"] not in by_path:
            raise ValueError(f"{entry['bundle_path']} is not in the frozen inventory")
        if not path.exists():
            raise FileNotFoundError(f"missing {path}")
        bundle = json.loads(path.read_text(encoding="utf-8"))
        rebuilt.append(gates.evaluate_bundle(bundle, spec, bundle_path=entry["bundle_path"]))
    summary = gates.summarize(rebuilt)
    same = summary == record.get("summary")
    return {
        "schema": "lex-map-contract-rescore/1",
        "record": str(record_path),
        "summary_matches_record": same,
        "recomputed_summary": summary,
        "recorded_summary": record.get("summary"),
    }, (0 if same else 1)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--product-root", help="accepted product checkout to score")
    ap.add_argument("--rescore", help="re-score a committed record instead")
    ap.add_argument("--out", help="where to write the record")
    ap.add_argument("--run-id", default="adhoc")
    args = ap.parse_args(argv)

    try:
        if args.rescore:
            payload, code = rescore(Path(args.rescore))
        elif args.product_root:
            payload, code = run(Path(args.product_root), run_id=args.run_id)
        else:
            ap.error("one of --product-root or --rescore is required")
            return 2
    except frozen.FrozenBenchmarkError as exc:
        return _env_error(f"frozen benchmark invalid: {exc}")
    except (FileNotFoundError, ValueError, KeyError, OSError) as exc:
        return _env_error(f"{type(exc).__name__}: {exc}")

    text = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8")

    if args.rescore:
        verdict = "MATCH" if payload["summary_matches_record"] else "MISMATCH"
        print(f"rescore {verdict}: {payload['record']}")
    else:
        s = payload["summary"]
        print(f"\nmap-contract benchmark: {'PASS' if s['overall_pass'] else 'FAIL'}")
        print(f"  bundles passed {s['n_bundles_passed']}/{s['n_bundles']}")
        for gate, row in sorted(s["per_gate"].items()):
            print(f"  {gate}: {row['n_passed']}/{row['n_measurable']} passed, "
                  f"{row['n_failed']} failed, {row['n_not_measurable']} n/m")
        if s["failed_bundle_paths"]:
            print(f"  failing bundles ({len(s['failed_bundle_paths'])}):")
            for p in s["failed_bundle_paths"]:
                print(f"    - {p}")
    return code


if __name__ == "__main__":
    raise SystemExit(main())

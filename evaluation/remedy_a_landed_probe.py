#!/usr/bin/env python3
"""Stand-ready probe: has the product lane landed counter-probe remedy (a)?

Remedy (a), recommended by the accepted counter-probe repair verification
(run 39687372110, verdict REPAIR_VERIFIED_ON_RECORDED_BYTES), is: strip the
redaction placeholder from the answer prose before the product's own probe
planner. The accepted record published the acceptance fixture per bundle:
the BASELINE (shipped) probe queries and the FIXED (de-contaminated) probe
queries for every measurable bundle.

This probe loads the SHIPPED planner from the accepted product mount and asks,
per fixture bundle, whether the shipped planner now reproduces the FIXED arm
(remedy landed), still reproduces the BASELINE arm (not landed), or issues
something else (unexpected — always disclosed, never counted as landed).

Deterministic, zero network, no threshold. It is a STATUS OBSERVATION for the
evaluation lane's stand-ready duty, NOT a product gate, NOT a bar, and it
re-derives no rubric or verdict contract.

Exit codes
----------
0  REMEDY_A_LANDED       — shipped planner reproduces the FIXED arm on every
                           bundle the fixture marks as fixed-comparable.
1  REMEDY_A_NOT_LANDED   — shipped planner still reproduces the BASELINE arm
                           on at least the contaminated bundles.
2  ENVIRONMENT_OR_VACUOUS — fixture, mount or product loader unavailable;
                           never a landing verdict.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from evaluation import counter_probe_anchor_falsifier as cpa  # noqa: E402

FIXTURE = REPO_ROOT / "results" / "evaluation" / "counter_probe_repair_verification" / "39687372110.json"
DEFAULT_MOUNT = Path("/tmp/lex_accepted/product")
PLANNER_REL = "product/query/adversarial_retrieval.py"
PRE_REMEDY_PLANNER_SHA256 = "57b6a6f99793ef6663957ccdcd51a577feb9c8d7075efcc339f5c25bece065e1"

EXIT_LANDED = 0
EXIT_NOT_LANDED = 1
EXIT_ENV = 2


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _queries_of(plan: list[dict]) -> list[str]:
    return [str(p.get("query") or "") for p in plan]


def classify(shipped: list[str], baseline: list[str], fixed: list[str]) -> str:
    if shipped == fixed and fixed != baseline:
        return "FIXED_ARM_REPRODUCED"
    if shipped == baseline and baseline == fixed:
        return "BASELINE_EQUALS_FIXED_NOOP"
    if shipped == baseline:
        return "BASELINE_ARM_REPRODUCED"
    if shipped == fixed:
        return "FIXED_ARM_REPRODUCED"
    return "UNEXPECTED_PLANNER_OUTPUT"


def run(fixture_path: Path, mount: Path) -> tuple[int, dict]:
    if not fixture_path.is_file() or not mount.is_dir():
        return EXIT_ENV, {"verdict": "ENVIRONMENT_OR_VACUOUS", "exit_code": EXIT_ENV,
                          "fixture_exists": fixture_path.is_file(),
                          "mount_exists": mount.is_dir(),
                          "claim_ceiling": "no landing verdict without both inputs"}

    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    rows_in = fixture.get("bundles") or []
    if not rows_in:
        return EXIT_ENV, {"verdict": "ENVIRONMENT_OR_VACUOUS", "exit_code": EXIT_ENV,
                          "n_fixture_rows": 0,
                          "claim_ceiling": "empty fixture is never a landing verdict"}

    planner_path = mount / PLANNER_REL
    planner_sha = sha256_file(planner_path) if planner_path.is_file() else None

    try:
        product = cpa.ProductCode(mount)
    except Exception as exc:  # pragma: no cover - environment disclosure
        return EXIT_ENV, {"verdict": "ENVIRONMENT_OR_VACUOUS", "exit_code": EXIT_ENV,
                          "loader_error": repr(exc), "planner_sha256": planner_sha,
                          "claim_ceiling": "product loader failure is never a landing verdict"}

    rows = []
    for fr in rows_in:
        src = Path(str(fr.get("source_path") or ""))
        if not src.is_file():
            rows.append({"source_path": str(src), "status": "SOURCE_ABSENT",
                         "baseline_anchor_contaminated": fr.get("baseline_anchor_contaminated")})
            continue
        bundle = json.loads(src.read_text(encoding="utf-8"))
        prose = str((bundle.get("answer") or {}).get("prose") or "")
        query = str(bundle.get("query") or "")
        shipped_queries = _queries_of(product.plan_adversarial_queries(query, prose))
        baseline = list(fr.get("baseline_probe_queries") or [])
        fixed = list(fr.get("fixed_probe_queries") or [])
        status = classify(shipped_queries, baseline, fixed)
        rows.append({
            "packet": fr.get("packet"), "question_slug": fr.get("question_slug"),
            "source_path": str(src), "source_sha256": cpa.sha256_file(src),
            "baseline_anchor_contaminated": bool(fr.get("baseline_anchor_contaminated")),
            "status": status,
            "shipped_reproduces_baseline": shipped_queries == baseline,
            "shipped_reproduces_fixed": shipped_queries == fixed,
            "placeholder_occurrences_in_prose": prose.count(product.redaction_placeholder or "\x00"),
        })

    measured = [r for r in rows if r.get("status") not in ("SOURCE_ABSENT",)]
    if not measured:
        return EXIT_ENV, {"verdict": "ENVIRONMENT_OR_VACUOUS", "exit_code": EXIT_ENV,
                          "rows": rows, "n_measured": 0,
                          "claim_ceiling": "no fixture bundle was loadable; never a landing verdict"}

    contaminated = [r for r in measured if r.get("baseline_anchor_contaminated")]
    all_fixed = all(r["status"] in ("FIXED_ARM_REPRODUCED", "BASELINE_EQUALS_FIXED_NOOP")
                    for r in measured)
    contaminated_fixed = all(r["status"] in ("FIXED_ARM_REPRODUCED", "BASELINE_EQUALS_FIXED_NOOP")
                             for r in contaminated) if contaminated else None
    any_baseline = any(r["status"] == "BASELINE_ARM_REPRODUCED" for r in measured)
    any_unexpected = any(r["status"] == "UNEXPECTED_PLANNER_OUTPUT" for r in measured)

    if any_unexpected:
        verdict, code = "REMEDY_A_UNEXPECTED_PLANNER_OUTPUT", EXIT_NOT_LANDED
    elif contaminated_fixed and all_fixed:
        verdict, code = "REMEDY_A_LANDED", EXIT_LANDED
    elif any_baseline:
        verdict, code = "REMEDY_A_NOT_LANDED", EXIT_NOT_LANDED
    else:
        verdict, code = "REMEDY_A_MIXED_REPRODUCTION", EXIT_NOT_LANDED

    out = {
        "schema": "lex-evaluation-remedy-a-landed-probe/1",
        "lane": "evaluation",
        "verdict": verdict, "exit_code": code,
        "fixture": str(fixture_path), "fixture_sha256": sha256_file(fixture_path),
        "mount": str(mount), "product_mount_head": None,
        "planner_path": PLANNER_REL, "planner_sha256": planner_sha,
        "planner_matches_pre_remedy_pin": planner_sha == PRE_REMEDY_PLANNER_SHA256,
        "pre_remedy_planner_pin": PRE_REMEDY_PLANNER_SHA256,
        "n_fixture_rows": len(rows_in), "n_measured": len(measured),
        "n_baseline_contaminated": len(contaminated),
        "rows": rows,
        "claim_ceiling": (
            "STATUS OBSERVATION only: whether the shipped planner on the current accepted "
            "product mount reproduces the accepted repair-verification fixture's FIXED or "
            "BASELINE arm. It is NOT a counter-authority recall measurement, NOT a label or "
            "geometry bar claim, NOT a serve recommendation, and it lifts no DO-NOT-SERVE "
            "order. human_gate_ready stays false."),
    }
    try:
        import subprocess
        r = subprocess.run(["git", "-C", str(mount), "rev-parse", "HEAD"],
                           capture_output=True, text=True, timeout=20)
        out["product_mount_head"] = r.stdout.strip() or None
    except Exception:  # pragma: no cover
        pass
    return code, out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    ap.add_argument("--fixture", default=str(FIXTURE))
    ap.add_argument("--mount", default=str(DEFAULT_MOUNT))
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)
    code, out = run(Path(args.fixture), Path(args.mount))
    text = json.dumps(out, indent=1, ensure_ascii=False, sort_keys=True) + "\n"
    if args.out:
        p = Path(args.out)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
    print(json.dumps({"verdict": out.get("verdict"), "exit_code": code,
                      "n_measured": out.get("n_measured"),
                      "planner_matches_pre_remedy_pin": out.get("planner_matches_pre_remedy_pin"),
                      "record": args.out}, indent=1))
    return code


if __name__ == "__main__":
    raise SystemExit(main())

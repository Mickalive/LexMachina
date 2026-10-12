#!/usr/bin/env bash
# Scope-safe verification for the OpenCaseLaw retrieval adapter
# (frontier-query-retrieval, charter v2). Charter acceptance (1)-(9).
#
# SCOPE SAFETY - this script is the supported way to smoke-test the adapter
# from ANY working directory (repository root, worktree, auditor checkout):
#   * it never writes at the repository root (no stray bundle*.json);
#   * it never leaves __pycache__ in the checkout (PYTHONDONTWRITEBYTECODE=1
#     and python3 -B);
#   * it writes only into results/frontier/frontier-query-retrieval/
#     verification/<stamp>/ (team namespace) and, for --live, a cache dir
#     inside that same folder;
#   * it never overwrites claim-bearing results (LIVE_*.json, fixtures/).
#
# Usage:
#   bash frontier/frontier-query-retrieval/verify_scope_safe.sh            # offline (default)
#   bash frontier/frontier-query-retrieval/verify_scope_safe.sh --live     # + one live query run
#   LEX_VERIFY_OUT=<dir> bash .../verify_scope_safe.sh                     # choose output dir
#
# Exit codes: 0 all checks passed, 1 a check failed, 2 bad usage.
set -uo pipefail

TEAM_REL="frontier/frontier-query-retrieval"
TESTS_REL="tests/frontier/frontier-query-retrieval"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"   # frontier/frontier-query-retrieval -> repo root
TEAM_DIR="$ROOT/$TEAM_REL"

LIVE=0
for arg in "$@"; do
  case "$arg" in
    --live) LIVE=1 ;;
    -h|--help) sed -n '2,26p' "${BASH_SOURCE[0]}"; exit 0 ;;
    *) echo "unknown argument: $arg" >&2; exit 2 ;;
  esac
done

STAMP="${LEX_VERIFY_RUN_ID:-$(date -u +%Y%m%dT%H%M%SZ)}"
OUT="${LEX_VERIFY_OUT:-$ROOT/results/frontier/frontier-query-retrieval/verification/$STAMP}"
mkdir -p "$OUT"
LOG="$OUT/verification.log"

export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH="$TEAM_DIR${PYTHONPATH:+:$PYTHONPATH}"

pass=0; fail=0
say()   { printf '%s\n' "$*" | tee -a "$LOG"; }
check() { # check <name> <rc:0|1> <detail>
  local name="$1" rc="$2" detail="$3"
  if [[ "$rc" == "0" ]]; then pass=$((pass+1)); say "PASS  $name :: $detail";
  else fail=$((fail+1)); say "FAIL  $name :: $detail"; fi
}

say "=== ocl_adapter scope-safe verification ==="
say "repo_root=$ROOT"
say "out_dir=$OUT"
say "python=$(python3 -V 2>&1) live=$LIVE"

# ---------------------------------------------------------------- (8) tests
t0=$(date +%s.%N)
python3 -B -m unittest discover -s "$ROOT/$TESTS_REL" -p 'test_*.py' >"$OUT/unit_tests.txt" 2>&1
rc=$?
t1=$(date +%s.%N)
n_tests=$(grep -oE 'Ran [0-9]+ tests?' "$OUT/unit_tests.txt" | grep -oE '[0-9]+' | head -1)
check "8_unit_tests" "$rc" "rc=$rc tests=${n_tests:-?} seconds=$(awk "BEGIN{printf \"%.1f\", $t1-$t0}") (log: unit_tests.txt)"

# ------------------------------------------- (7) deterministic fixture replay
python3 -B - "$OUT" <<'PY' >"$OUT/replay_check.txt" 2>&1
import json, os, pathlib, subprocess, sys

out = pathlib.Path(sys.argv[1])
env = dict(os.environ)
rcs = []
for i in (1, 2):
    p = subprocess.run(
        [sys.executable, "-B", "-m", "ocl_adapter", "Kündigung Mietvertrag Mietrecht",
         "--preset", "fixtures", "--out", str(out / f"replay_{i}.json"),
         "--validate", "--quiet"],
        capture_output=True, text=True, env=env, timeout=300, cwd=str(out))
    rcs.append(p.returncode)
    (out / f"replay_{i}.stderr.txt").write_text(p.stderr or "", encoding="utf-8")

a = json.loads((out / "replay_1.json").read_text(encoding="utf-8"))
b = json.loads((out / "replay_2.json").read_text(encoding="utf-8"))
ids_a = [c["decision_id"] for c in a["candidates"]]
ids_b = [c["decision_id"] for c in b["candidates"]]
prov_a = [c["provenance"] for c in a["candidates"]]
prov_b = [c["provenance"] for c in b["candidates"]]
chan_a = sorted({ch for c in a["candidates"] for ch in c.get("channels", [])})
langs_a = sorted({c["language"] for c in a["candidates"] if c.get("language")})
same = (rcs == [0, 0]) and ids_a == ids_b and prov_a == prov_b and len(ids_a) >= 100
result = {
    "returncodes": rcs,
    "n_candidates": [len(ids_a), len(ids_b)],
    "identical_decision_ids": ids_a == ids_b,
    "identical_provenance": prov_a == prov_b,
    "channels": chan_a,
    "languages": langs_a,
    "deterministic": same,
}
print(json.dumps(result, ensure_ascii=False, indent=2))
sys.exit(0 if same else 1)
PY
rc=$?
check "7_fixture_replay_deterministic" "$rc" "two replays compared (log: replay_check.txt)"

# ------------------------------------------------- (1)-(6,9) contract import
# NOTE: the repository root is passed in by the shell (computed from this
# script's own location). It must NOT be guessed by walking parents looking
# for 'frontier/frontier-query-retrieval': that pattern also matches
# 'results/frontier/frontier-query-retrieval', which made an earlier version
# of this check fail with FileNotFoundError on INTEGRATION_CONTRACT.json.
python3 -B - "$OUT" "$ROOT" <<'PY' >"$OUT/contract_import.txt" 2>&1
import json, pathlib, sys

p = pathlib.Path(sys.argv[1])
repo = pathlib.Path(sys.argv[2]).resolve()
assert (repo / "frontier" / "frontier-query-retrieval").is_dir(), f"bad repo root: {repo}"
assert (repo / "frontier" / "frontier-query-retrieval" / "INTEGRATION_CONTRACT.json").is_file()
sys.path.insert(0, str(repo / "frontier" / "frontier-query-retrieval"))

from ocl_adapter import (AdapterConfig, build_candidate_bundle, bundle_summary,
                         build_variants, to_product_bundle, validate_against_product,
                         validate_candidate_bundle, __version__)
from ocl_adapter.fixtures import replay_fixtures

contract = json.loads((repo / "frontier" / "frontier-query-retrieval" / "INTEGRATION_CONTRACT.json")
                      .read_text(encoding="utf-8"))
bundle = replay_fixtures()
errs = validate_candidate_bundle(bundle)
perrs = validate_against_product(bundle)
prod = to_product_bundle(bundle)
summary = bundle_summary(bundle)
missing = [k for k in contract["product_bundle"]["required_decision_keys"]
           if prod["decisions"] and k not in prod["decisions"][0]]
langs = sorted({c["language"] for c in bundle["candidates"] if c.get("language")})
variants = build_variants("Kündigung Mietvertrag Mietrecht")
cfg = AdapterConfig()
checks = {
    "contract_version": contract["contract_version"],
    "adapter_version": __version__,
    "n_candidates": summary["n_candidates"],
    "validation_errors": errs,
    "product_validation_errors": perrs,
    "product_decisions": len(prod["decisions"]),
    "missing_decision_keys": missing,
    "languages": langs,
    "n_query_variants": len(variants),
    "channels": summary.get("channels", {}),
    "degraded": summary.get("degraded"),
    "default_target": cfg.target,
    "default_max_rps": cfg.max_rps,
}
print(json.dumps(checks, ensure_ascii=False, indent=2))
ok = (not errs) and (not perrs) and (not missing) and summary["n_candidates"] >= 100 \
     and len(langs) >= 2 and len(variants) >= 3 and cfg.max_rps <= 5.0 \
     and contract["charter_version"] == 2 and callable(build_candidate_bundle)
sys.exit(0 if ok else 1)
PY
rc=$?
check "1_2_3_6_9_contract_import_bridge" "$rc" "sys.path import -> replay -> validate -> to_product_bundle (log: contract_import.txt)"

# --------------------------------------------------------------- (1) live
if [[ "$LIVE" == "1" ]]; then
  say "running live query (max_rps=4.0 <= charter 5.0) ..."
  python3 -B -m ocl_adapter "Kündigung Mietvertrag Mietrecht" \
      --target 120 --max-rps 4.0 --hydrate-top 2 \
      --cache-dir "$OUT/live_cache" \
      --out "$OUT/live_bundle.json" \
      --product-bundle "$OUT/live_product_bundle.json" \
      --validate >"$OUT/live_run.txt" 2>&1
  rc=$?
  python3 -B - "$OUT" <<'PY' >>"$OUT/live_run.txt" 2>&1
import json, pathlib, sys
out = pathlib.Path(sys.argv[1])
b = json.loads((out / "live_bundle.json").read_text(encoding="utf-8"))
cands = b["candidates"]
ids = {c["decision_id"] for c in cands}
prov = b.get("provenance", {})
langs = sorted({c["language"] for c in cands if c.get("language")})
checks = {
    "n_candidates": len(cands),
    "n_unique_decision_ids": len(ids),
    "languages": langs,
    "request_summary": prov.get("request_summary", {}),
    "rate_limit": prov.get("rate_limit", {}),
    "channels": sorted({ch for c in cands for ch in c.get("channels", [])}),
    "n_hydrated": sum(1 for c in cands if c.get("detail_status") == "hydrated"),
    "degraded": prov.get("degraded"),
    "failures": prov.get("failures"),
}
print(json.dumps(checks, ensure_ascii=False, indent=2))
sys.exit(0 if (len(cands) >= 100 and len(ids) == len(cands) and len(langs) >= 2) else 1)
PY
  check "1_2_live_run_ge_100" "$?" "live bundle written to $OUT/live_bundle.json (log: live_run.txt)"
else
  say "SKIP  live run (pass --live to execute it)"
fi

# ------------------------------------------------------------- write summary
python3 -B - "$OUT" "$pass" "$fail" "$LIVE" <<'PY'
import json, pathlib, sys, time
out = pathlib.Path(sys.argv[1])
summary = {
    "schema": "ocl_adapter_verification_v1",
    "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    "checks_passed": int(sys.argv[2]),
    "checks_failed": int(sys.argv[3]),
    "live_requested": sys.argv[4] == "1",
    "network_required": sys.argv[4] == "1",
    "scope_safe": {
        "writes_only": [str(out)],
        "repository_root_writes": "none",
        "pycache": "suppressed (PYTHONDONTWRITEBYTECODE=1, python3 -B)",
        "claim_bearing_results_overwritten": "none",
    },
    "files": sorted(p.name for p in out.iterdir()),
}
(out / "VERIFICATION.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
PY

say "=== result: passed=$pass failed=$fail ==="
say "summary: $OUT/VERIFICATION.json"
[[ "$fail" == "0" ]] || exit 1
exit 0

#!/usr/bin/env bash
# One-command offline smoke for frontier-human-gate-harness (acceptance 5/6/7).
#
#   bash frontier/frontier-human-gate-harness/smoke.sh
#
# Everything below runs with no network: fixture check -> offline tests ->
# one-command CLI run -> node assertions -> evidence files under
# results/frontier/frontier-human-gate-harness/. Exit 0 only if every step passes.
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TEAM_RESULTS="$ROOT/results/frontier/frontier-human-gate-harness"
EVIDENCE="$TEAM_RESULTS/evidence"
SMOKE_OUT="$TEAM_RESULTS/smoke"
FIXTURE="$TEAM_RESULTS/fixtures/query_result_bundle_kuendigung_101.json"
HARNESS="$ROOT/frontier/frontier-human-gate-harness"
TESTS="$ROOT/tests/frontier/frontier-human-gate-harness"

mkdir -p "$EVIDENCE" "$SMOKE_OUT"
status=0
step() { printf '\n=== %s ===\n' "$1"; }

step "1/6 fixture regeneration check (deterministic, offline)"
if (cd "$HARNESS" && python3 tools/make_fixture.py --check) 2>&1 | tee "$EVIDENCE/fixture_check.txt"; then
  echo "fixture check: OK"
else
  echo "fixture check: FAILED"; status=1
fi

step "2/6 offline test suite (stdlib runner)"
if python3 "$TESTS/run_tests.py" 2>&1 | tee "$EVIDENCE/tests_run.txt"; then
  echo "tests: OK"
else
  echo "tests: FAILED"; status=1
fi

step "3/6 node assertions for static/lex_gate_switch.js"
if node "$TESTS/js/verify_switch.js" 2>&1 | tee "$EVIDENCE/node_verify_switch.txt"; then
  echo "node: OK"
else
  echo "node: FAILED"; status=1
fi

step "4/6 one-command offline CLI run (baseline + card + empty capture + demo)"
find "$SMOKE_OUT" -mindepth 1 -delete
if (cd "$HARNESS" && python3 -m frontier_human_gate_harness.cli \
     --fixture "$FIXTURE" --out "$SMOKE_OUT" \
     --now 2026-10-14T00:00:00Z) 2>&1 | tee "$EVIDENCE/cli_smoke_stdout.txt"; then
  echo "cli: OK"
else
  echo "cli: FAILED"; status=1
fi

step "5/6 outputs present + capture schema spot-check"
python3 - "$SMOKE_OUT" <<'PYEOF' 2>&1 | tee "$EVIDENCE/outputs_check.txt"
import json, sys
from pathlib import Path
out = Path(sys.argv[1])
required = ["baseline_view.html", "owner_card_fr.html", "owner_card_de.html",
            "owner_card.json", "harness_demo.html", "summary.json"]
missing = [name for name in required if not (out / name).is_file()]
sessions = sorted(out.glob("session_*.json"))
ok = not missing and len(sessions) >= 1
summary = json.loads((out / "summary.json").read_text(encoding="utf-8")) if not missing else {}
session = json.loads(sessions[0].read_text(encoding="utf-8")) if sessions else {}
checks = {
    "missing_outputs": missing,
    "session_files": [p.name for p in sessions],
    "summary_offline": summary.get("offline"),
    "session_status": session.get("status"),
    "session_missing_answers": session.get("missing_answers"),
    "session_hash_status": session.get("bundle_hash_status"),
    "baseline_label": (summary.get("baseline") or {}).get("label"),
    "n_rows": (summary.get("baseline") or {}).get("n_rows"),
}
print(json.dumps(checks, ensure_ascii=False, indent=1))
if not ok or session.get("missing_answers") != ["q1", "q2", "q3", "q4"] \
   or session.get("status") != "empty" or session.get("bundle_hash_status") != "computed":
    sys.exit(1)
PYEOF
[ $? -eq 0 ] || { echo "outputs check: FAILED"; status=1; }

step "6/6 scope: no writes outside the five team paths"
if git -C "$ROOT" status --porcelain -uall | awk '{print $2}' \
   | grep -Ev '^(frontier/frontier-human-gate-harness/|tests/frontier/frontier-human-gate-harness/|results/frontier/frontier-human-gate-harness/|reports/frontier/frontier-human-gate-harness/|state/frontier/frontier-human-gate-harness\.json)' \
   | tee "$EVIDENCE/scope_violations.txt"; then
  echo "scope: FAILED (violations listed above)"; status=1
else
  : > "$EVIDENCE/scope_violations.txt"
  echo "scope: OK (no writes outside the team namespace)"
fi

step "result"
if [ "$status" -eq 0 ]; then
  echo "SMOKE OK — see results/frontier/frontier-human-gate-harness/{smoke,evidence}"
else
  echo "SMOKE FAILED — see results/frontier/frontier-human-gate-harness/evidence"
fi
exit "$status"

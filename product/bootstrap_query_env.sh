#!/usr/bin/env bash
# Install the query fast path's third-party runtime, pinned.
#
#   bash product/bootstrap_query_env.sh          # install if missing / mismatched
#   bash product/bootstrap_query_env.sh --check  # report only, never installs
#
# Why this exists: no step of .github/workflows/core-lane.yml installs
# product/requirements-query.txt, so a fresh runner reaches the vertical slice
# with no numpy and no scikit-learn, and product/cycle_verify.py then reports
# ModuleNotFoundError for five checks - a validation failure that has nothing to
# do with the product.  .github/** is control-plane scope and is never edited
# from this lane, so the lane bootstraps itself, reproducibly, in one command.
#
# Free-only: everything here comes from PyPI.  No paid inference, no account.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY="${PYTHON:-python3}"
CHECK_ONLY=0
[[ "${1:-}" == "--check" ]] && CHECK_ONLY=1

# The versions this lane measured on a real fresh-network run of the slice, as
# "pip-name==version import-name".  Kept in sync with
# product/query_env.py::PINNED, which is the machine-readable copy the ledger
# checks against (the pip name of scikit-learn is not its import name).
PINNED=(
  "numpy==2.5.4 numpy"
  "scipy==1.18.1 scipy"
  "scikit-learn==1.9.1 sklearn"
  "pytest==9.1.1 pytest"
)

status=0
for entry in "${PINNED[@]}"; do
  spec="${entry%% *}"
  module="${entry##* }"
  version="$("$PY" -c "import $module;print(getattr($module,'__version__','unknown'))" 2>/dev/null || true)"
  if [[ -n "$version" ]]; then
    echo "[ok]      $spec (import $module)"
  else
    status=1
    echo "[missing] $spec (import $module)"
  fi
done

if [[ "$CHECK_ONLY" == "1" || "$status" == "0" ]]; then
  echo
  if [[ "$status" == "0" ]]; then
    echo "query fast-path runtime: OK"
  else
    echo "query fast-path runtime: INCOMPLETE - run without --check to install"
  fi
  exit "$status"
fi

echo
echo "installing pinned query runtime into the current interpreter's user site..."
specs=(); for e in "${PINNED[@]}"; do specs+=("${e%% *}"); done
"$PY" -m pip install --user --quiet "${specs[@]}"
echo
echo "re-checking..."
# Re-check with BASH, not with $PY: this file is a bash script (set -euo
# pipefail at line 15), so handing it to the Python interpreter makes the
# remedy path die with SyntaxError right after a successful install - the
# exact defect the 39128456801 audit (F3) re-measured empirically.
exec bash "${REPO_ROOT}/product/bootstrap_query_env.sh" --check
#!/usr/bin/env bash
set -uo pipefail

# Bootstrap invariant: a persistent lab/cycle branch must never keep executing an
# obsolete launcher. Re-exec the exact current wrapper from main when it differs.
if [[ "${LEX_WRAPPER_REEXEC:-0}" != "1" ]]; then
  LATEST_WRAPPER="$(mktemp)"
  if git fetch -q origin main 2>/dev/null && git show origin/main:.github/scripts/run-ox-with-retry.sh > "$LATEST_WRAPPER" 2>/dev/null; then
    if ! cmp -s "$0" "$LATEST_WRAPPER"; then
      chmod +x "$LATEST_WRAPPER"
      export LEX_WRAPPER_REEXEC=1
      exec bash "$LATEST_WRAPPER" "$@"
    fi
  fi
  rm -f "$LATEST_WRAPPER"
fi

REAL="${OPENCODE_BIN:-$HOME/.opencode/bin/opencode}"
MAX_ATTEMPTS="${OX_MAX_ATTEMPTS:-8}"
RETRY_DELAY="${OX_RETRY_DELAY_SECONDS:-90}"
STALL_SECONDS="${OX_NETWORK_STALL_SECONDS:-420}"
LOG="$(mktemp)"; STALL_FLAG="$(mktemp)"
CHILD_PID=""; MONITOR_PID=""; START_HEAD=""; REPAIR_INTENT=false; OVERLAY=false
NETWORK_RE='(network_error|NetworkError|network error|fetch failed|APIConnectionError|ECONNRESET|ECONNREFUSED|EAI_AGAIN|ENETUNREACH|ENOTFOUND|ETIMEDOUT|timed out|timeout|socket hang up|connection (reset|refused|closed|error)|upstream.*(reset|closed|unavailable|error)|HTTP[^0-9]*(429|500|502|503|504)|status[^0-9]*(429|500|502|503|504)|too many requests|rate.?limit|service unavailable|bad gateway|gateway timeout|temporar(y|ily) unavailable|TLS|SSL.*error|Unexpected server error|internal server error)'

restore_overlay() {
  [[ "$OVERLAY" == true ]] || return 0
  for p in AGENTS.md .opencode/agents; do
    git reset -q HEAD -- "$p" 2>/dev/null || true
    if git cat-file -e "HEAD:$p" 2>/dev/null; then git checkout -q -- "$p" 2>/dev/null || true; else rm -rf -- "$p"; fi
    git clean -fdq -- "$p" 2>/dev/null || true
  done
  OVERLAY=false
}
cleanup(){ [[ -n "$MONITOR_PID" ]] && kill "$MONITOR_PID" 2>/dev/null || true; [[ -n "$CHILD_PID" ]] && kill "$CHILD_PID" 2>/dev/null || true; restore_overlay || true; rm -f "$LOG" "$STALL_FLAG"; }
trap cleanup EXIT INT TERM

stage_control(){
  local ref="origin/main"
  if ! git fetch -q origin main; then echo "::warning::main refresh failed; using workflow checkout"; ref="${GITHUB_SHA:-HEAD}"; fi
  rm -rf /tmp/lex_control; mkdir -p /tmp/lex_control
  for p in AGENTS.md LEXMACHINA_MASTER_PROMPT.md ARCHITECTURE.md docs/RESEARCH_PROTOCOL.md docs/agents/AGENT_CARDS.md state/factory_direction.json state/frontier_portfolio.json; do
    if git cat-file -e "$ref:$p" 2>/dev/null; then mkdir -p "/tmp/lex_control/$(dirname "$p")"; git show "$ref:$p" > "/tmp/lex_control/$p"; fi
  done
  if git cat-file -e "$ref:directives/lanes" 2>/dev/null; then git archive "$ref" directives/lanes | tar -x -C /tmp/lex_control; fi
  for p in AGENTS.md .opencode/agents; do if git cat-file -e "$ref:$p" 2>/dev/null; then git checkout -q "$ref" -- "$p"; fi; done
  OVERLAY=true
}

validate_registry(){
  local reg="/tmp/lex_control/docs/agents/AGENT_CARDS.md" bad=0 file id count requested="" prev="" arg marker
  [[ -f "$reg" ]] || { echo "::error::Missing canonical agent registry"; return 64; }
  while IFS= read -r file; do id="${file#.opencode/agents/}"; id="${id%.md}"; count=$(grep -Fc "<!-- AGENT_CARD: ${id} " "$reg" || true); [[ "$count" -eq 1 ]] || { echo "::error::Agent $id has $count cards; expected 1"; bad=1; }; done < <(find .opencode/agents -type f -name '*.md' | sort)
  while IFS= read -r id; do [[ -f ".opencode/agents/${id}.md" ]] || { echo "::error::Card $id has no agent definition"; bad=1; }; done < <(grep '^<!-- AGENT_CARD:' "$reg" | awk '{print $3}')
  [[ "$bad" -eq 0 ]] || return 66
  for arg in "$@"; do if [[ "$prev" == "--agent" ]]; then requested="$arg"; break; fi; case "$arg" in --agent=*) requested="${arg#--agent=}"; break;; esac; prev="$arg"; done
  [[ -z "$requested" ]] && return 0
  marker=$(grep -F "<!-- AGENT_CARD: ${requested} " "$reg" | head -n1 || true)
  [[ -n "$marker" ]] || { echo "::error::Agent $requested lacks canonical card"; return 64; }
  [[ "$marker" != *"status=LEGACY_DISABLED"* ]] || { echo "::error::Agent $requested is disabled"; return 65; }
  echo "LEX_AGENT_CARD_OK agent=$requested"
}

for arg in "$@"; do if [[ "$arg" == REPAIR\ * || "$arg" == *" REPAIR "* ]]; then REPAIR_INTENT=true; break; fi; done
[[ "${LEX_REQUIRE_DELTA:-0}" == 1 ]] && REPAIR_INTENT=true
stage_control; START_HEAD=$(git rev-parse HEAD 2>/dev/null || echo ""); validate_registry "$@" || exit $?

run_once(){
  : >"$LOG"; rm -f "$STALL_FLAG"; local wd="${GITHUB_WORKSPACE:-$PWD}"
  (cd "$wd" || exit 70; "$REAL" "$@") > >(tee -a "$LOG") 2> >(tee -a "$LOG" >&2) & CHILD_PID=$!
  (local size=0 last now cur; last=$(date +%s); while kill -0 "$CHILD_PID" 2>/dev/null; do sleep 15; cur=$(wc -c <"$LOG" 2>/dev/null || echo 0); now=$(date +%s); if [[ "$cur" -ne "$size" ]]; then size="$cur"; last="$now"; elif (( now-last >= STALL_SECONDS )); then if grep -Eiq "$NETWORK_RE" "$LOG"; then echo "LEX_NETWORK_STALL" >&2; touch "$STALL_FLAG"; kill "$CHILD_PID" 2>/dev/null || true; sleep 5; kill -9 "$CHILD_PID" 2>/dev/null || true; exit 0; fi; last="$now"; fi; done) & MONITOR_PID=$!
  wait "$CHILD_PID"; local rc=$?; kill "$MONITOR_PID" 2>/dev/null || true; wait "$MONITOR_PID" 2>/dev/null || true; CHILD_PID=""; MONITOR_PID=""; [[ -f "$STALL_FLAG" ]] && return 75; return "$rc"
}

attempt=1
while ((attempt<=MAX_ATTEMPTS)); do
  echo "LEX_OX_ATTEMPT=$attempt/$MAX_ATTEMPTS"; run_once "$@"; rc=$?
  if [[ "$rc" -eq 0 ]]; then
    restore_overlay || exit 1
    if [[ "$REPAIR_INTENT" == true ]]; then cur=$(git rev-parse HEAD 2>/dev/null || echo ""); delta=$(git status --porcelain 2>/dev/null || true); if [[ "$cur" == "$START_HEAD" && -z "$delta" ]]; then echo "::error::LEX_ZERO_DELTA_REPAIR"; exit 67; fi; fi
    exit 0
  fi
  if [[ "$rc" -eq 75 ]] || grep -Eiq "$NETWORK_RE" "$LOG"; then if ((attempt<MAX_ATTEMPTS)); then echo "::warning::Transient Ox failure; retrying"; sleep "$RETRY_DELAY"; attempt=$((attempt+1)); continue; fi; restore_overlay || true; exit 75; fi
  echo "Ox failed without transient signature (rc=$rc)" >&2; restore_overlay || true; exit "$rc"
done
restore_overlay || true; exit 75

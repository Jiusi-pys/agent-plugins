#!/usr/bin/env bash
# preflight.sh — deterministic gate + intake scoring for the multi-review pipeline.
#
# Emits ONE JSON object on stdout conforming to the review-contract preflight shape:
#   { gate, deterministic_gate, gates_run, intake:{score,reject,signals},
#     diff:{changed_files,changed_lines,high_risk_paths,test_weakening,
#           threshold_drop,public_api_or_schema}, reasons }
# Exit code: 0=OK, 10=BLOCK (deterministic gate failed), 20=REJECT_INTAKE.
#
# Usage:   scripts/review/preflight.sh [<target>]
#   (no arg)   → working tree vs HEAD (git diff HEAD) + untracked files
#   staged     → staged changes only (git diff --staged)
#   <rev>^!    → exactly that one commit (its diff vs its parent), e.g. abc123^! or HEAD^!
#   <a>..<b>   → explicit range as-is (a...b also works)
#   <ref>      → this branch vs <ref>  (git diff <ref>...HEAD)
#
# Env toggles (all optional):
#   REVIEW_RUN_GATES=1     run detected fast gates (lint/typecheck). 0 to skip.
#   REVIEW_RUN_TESTS=0     run the test gate (can be slow). 1 to enable.
#   REVIEW_GATE_TIMEOUT=180 per-gate timeout seconds (needs `timeout`).
#   REVIEW_REJECT_SCORE=12 intake score at/above which → REJECT_INTAKE.
#   REVIEW_HARD_MAX_LINES=4000 / REVIEW_HARD_MAX_FILES=80 hard split thresholds.
#   REVIEW_INTENT_FILE=.review/intent.md  per-PR intent file to check.
#   REVIEW_TEST_EVIDENCE=1 assert that test evidence exists (skip the -2 signal).
set -uo pipefail

TARGET="${1:-}"
RUN_GATES="${REVIEW_RUN_GATES:-1}"
RUN_TESTS="${REVIEW_RUN_TESTS:-0}"
REJECT_SCORE="${REVIEW_REJECT_SCORE:-12}"
HARD_MAX_LINES="${REVIEW_HARD_MAX_LINES:-4000}"
HARD_MAX_FILES="${REVIEW_HARD_MAX_FILES:-80}"
INTENT_FILE="${REVIEW_INTENT_FILE:-.review/intent.md}"

# accumulators (init under set -u)
score=0
reject=false
test_weakening=false
threshold_drop=false
public_api=false
det="skipped"
det_fail=0
F=0
L=0
declare -a signals=()
declare -a reasons=()
declare -a gates_run=()
declare -a highrisk=()

emit() {
  local gate="$1"
  if command -v python3 >/dev/null 2>&1; then
    GATE="$gate" DET="$det" SCORE="$score" REJECT="$reject" \
    CHANGED_FILES="$F" CHANGED_LINES="$L" TW="$test_weakening" TD="$threshold_drop" PA="$public_api" \
    HIGH_RISK="$(printf '%s\n' "${highrisk[@]:-}")" \
    GATES_RUN="$(printf '%s\n' "${gates_run[@]:-}")" \
    SIGNALS="$(printf '%s\n' "${signals[@]:-}")" \
    REASONS="$(printf '%s\n' "${reasons[@]:-}")" \
    python3 - <<'PY'
import os, json
def lines(k):
    return [x for x in os.environ.get(k, '').split('\n') if x.strip()]
def b(k):
    return os.environ.get(k, 'false') == 'true'
def i(k):
    try: return int(os.environ.get(k, '0') or 0)
    except ValueError: return 0
sig = []
for s in lines('SIGNALS'):
    name, _, pts = s.rpartition('|')
    try: pts = int(pts)
    except ValueError: pts = 0
    sig.append({"signal": name or s, "points": pts})
out = {
    "gate": os.environ["GATE"],
    "deterministic_gate": os.environ["DET"],
    "gates_run": lines('GATES_RUN'),
    "intake": {"score": i('SCORE'), "reject": b('REJECT'), "signals": sig},
    "diff": {
        "changed_files": i('CHANGED_FILES'),
        "changed_lines": i('CHANGED_LINES'),
        "high_risk_paths": lines('HIGH_RISK'),
        "test_weakening": b('TW'),
        "threshold_drop": b('TD'),
        "public_api_or_schema": b('PA'),
    },
    "reasons": lines('REASONS'),
}
print(json.dumps(out, ensure_ascii=False))
PY
  else
    # minimal manual fallback (arrays omitted for safety without a JSON tool)
    printf '{"gate":"%s","deterministic_gate":"%s","gates_run":[],"intake":{"score":%s,"reject":%s,"signals":[]},"diff":{"changed_files":%s,"changed_lines":%s,"high_risk_paths":[],"test_weakening":%s,"threshold_drop":%s,"public_api_or_schema":%s},"reasons":[]}\n' \
      "$gate" "$det" "$score" "$reject" "$F" "$L" "$test_weakening" "$threshold_drop" "$public_api"
  fi
}

finish() {
  local gate
  if [ "$det" = "fail" ]; then gate="BLOCK"
  elif [ "$reject" = "true" ]; then gate="REJECT_INTAKE"
  else gate="OK"; fi
  emit "$gate"
  case "$gate" in
    BLOCK) exit 10 ;;
    REJECT_INTAKE) exit 20 ;;
    *) exit 0 ;;
  esac
}

REPO="$(git rev-parse --show-toplevel 2>/dev/null || true)"
if [ -z "$REPO" ]; then
  reasons+=("not a git repository — cannot compute a diff")
  det="skipped"
  finish
fi
cd "$REPO" || { reasons+=("cannot cd to repo root"); finish; }

# ---- resolve what to diff (see TARGET grammar in the header) ----
case "$TARGET" in
  "")
    ARGS="HEAD" ;;                              # working tree vs HEAD (+ untracked, below)
  staged|cached)
    ARGS="--staged" ;;                          # staged changes only
  *"^!")                                        # exactly one commit: its diff vs its parent
    c="${TARGET%"^!"}"
    if git rev-parse --verify -q "${c}^" >/dev/null 2>&1; then
      ARGS="${c}^..${c}"
    elif git rev-parse --verify -q "$c" >/dev/null 2>&1; then
      ARGS="$(git hash-object -t tree /dev/null) ${c}"   # root commit → diff vs empty tree
    else
      reasons+=("cannot resolve commit '${c}'"); finish
    fi ;;
  *..*)
    ARGS="$TARGET" ;;                           # explicit range (a..b or a...b)
  *)
    ARGS="${TARGET}...HEAD" ;;                  # bare ref → this branch vs <ref>
esac

TRACKED_NAMES="$(git diff --name-only $ARGS 2>/dev/null || true)"
DELETED_PATHS="$(git diff --name-status $ARGS 2>/dev/null | awk '$1 ~ /^D/ {print $NF}' || true)"
NUMSTAT="$(git diff --numstat $ARGS 2>/dev/null || true)"
DIFFTEXT="$(git diff $ARGS 2>/dev/null || true)"

# Working-tree mode also accounts for UNTRACKED (new) files — `git diff HEAD`
# omits them, but new files are exactly what a review must scrutinise. Use
# --no-index against /dev/null so the index is never mutated (stays read-only).
UNTRACKED=""
if [ -z "$TARGET" ]; then
  UNTRACKED="$(git ls-files --others --exclude-standard 2>/dev/null || true)"
fi
if [ -n "$UNTRACKED" ]; then
  n=0
  while IFS= read -r f; do
    [ -z "$f" ] && continue
    n=$((n + 1))
    if [ "$n" -le 500 ]; then
      NUMSTAT="$NUMSTAT
$(git diff --no-index --numstat -- /dev/null "$f" 2>/dev/null || true)"
      DIFFTEXT="$DIFFTEXT
$(git diff --no-index -- /dev/null "$f" 2>/dev/null || true)"
    fi
  done <<EOF
$UNTRACKED
EOF
  [ "$n" -gt 500 ] && reasons+=("$n untracked files; analysed first 500 line-by-line")
fi
CHANGED_PATHS="$(printf '%s\n%s\n' "$TRACKED_NAMES" "$UNTRACKED" | grep -v '^[[:space:]]*$' | sort -u)"

F="$(printf '%s\n' "$CHANGED_PATHS" | grep -c . || true)"
[ -z "$F" ] && F=0
# changed_lines = added + deleted (binary '-' counted as 0)
L="$(printf '%s\n' "$NUMSTAT" | awk 'NF>=2 { a=($1=="-")?0:$1; d=($2=="-")?0:$2; s+=a+d } END { print s+0 }')"
[ -z "$L" ] && L=0

if [ "$F" -eq 0 ]; then
  reasons+=("no changes detected for range '$ARGS'")
  finish
fi

# ---- pattern signals ----
HIGHRISK_RE='(^|/)(auth|authz|billing|payment[A-Za-z0-9_-]*|privacy|pii)(/|$)|(^|/)migration[A-Za-z0-9_-]*(/|$)|(^|/)schema[A-Za-z0-9_-]*(/|$)|(^|/)\.github/workflows/|(^|/)ci/|(^|/)infrastructure/|(^|/)(terraform|k8s|helm)/|(^|/)(agents|prompt[A-Za-z0-9_-]*|llm)(/|$)'
SCHEMA_RE='(^|/)migrations?/|\.sql$|(^|/)(openapi|swagger)|\.proto$|\.graphql$|(^|/)schemas?/|(^|/)api/'
TESTPAT='(^|/)(tests?|__tests__|spec)/|(\.|_)(test|spec)\.[a-z0-9]+$|_test\.(go|py|rb)$|(^|/)test_[^/]*\.py$'
SKIP_RE='(\.skip\(|\.only\(|xit\(|xdescribe\(|fit\(|fdescribe\(|@pytest\.mark\.skip|@unittest\.skip|t\.Skip\(|#\[ignore\]|it\.todo\(|test\.skip\()'
THRESH_DROP_RE='^-.*(fail_under|coverageThreshold|minCoverage|"strict"[[:space:]]*:[[:space:]]*true|:[[:space:]]*"error")'

# high-risk paths
while IFS= read -r p; do
  [ -n "$p" ] && highrisk+=("$p")
done < <(printf '%s\n' "$CHANGED_PATHS" | grep -E "$HIGHRISK_RE" || true)

# public API / schema
if printf '%s\n' "$CHANGED_PATHS" | grep -qE "$SCHEMA_RE"; then public_api=true; fi

# test weakening: deleted test file, OR added skip marker, OR net assertion loss
if printf '%s\n' "$DELETED_PATHS" | grep -qE "$TESTPAT"; then test_weakening=true; fi
if printf '%s\n' "$DIFFTEXT" | grep -E '^\+' | grep -qE "$SKIP_RE"; then test_weakening=true; fi
ASSERT_RE='\b(assert|expect|require\.|EXPECT_|ASSERT_|t\.Error|t\.Fatal)\b|\.should\b'
rem="$(printf '%s\n' "$DIFFTEXT" | grep -E '^-[^-]' | grep -cE "$ASSERT_RE" || true)"
add="$(printf '%s\n' "$DIFFTEXT" | grep -E '^\+[^+]' | grep -cE "$ASSERT_RE" || true)"
[ -z "$rem" ] && rem=0; [ -z "$add" ] && add=0
if [ "$rem" -gt "$add" ]; then test_weakening=true; fi

# threshold drop
if printf '%s\n' "$DIFFTEXT" | grep -qE "$THRESH_DROP_RE"; then threshold_drop=true; fi

# intent / test evidence
has_acceptance=false
has_test_evidence=false
if [ -f "$INTENT_FILE" ]; then
  # a filled acceptance bullet = a "- " line with non-comment text in the Acceptance section
  if awk '/Acceptance criteria/{f=1;next} /^## /{f=0} f && /^[[:space:]]*-[[:space:]]+[^[:space:]<]/{print}' "$INTENT_FILE" | grep -q .; then
    has_acceptance=true
  fi
  # test evidence = a fenced block with a command under "Commands run"
  if awk '/Commands run/{f=1;next} /^## /{f=0} f && /[$]|[a-zA-Z]/{print}' "$INTENT_FILE" | grep -qE '[$][[:space:]]|test|pytest|cargo|go test|npm'; then
    has_test_evidence=true
  fi
fi
[ "${REVIEW_TEST_EVIDENCE:-0}" = "1" ] && has_test_evidence=true

# ---- scoring ----
add_sig() { score=$((score + $2)); signals+=("$1|$2"); }
[ "$F" -gt 25 ] && add_sig "changed_files=$F (>25)" 2
[ "$L" -gt 800 ] && add_sig "changed_lines=$L (>800)" 2
[ "${#highrisk[@]}" -gt 0 ] && add_sig "touches high-risk path(s)" 3
[ "$test_weakening" = "true" ] && add_sig "tests deleted/skipped/loosened" 4
[ "$threshold_drop" = "true" ] && add_sig "coverage/lint/type/security threshold lowered" 5
[ "$public_api" = "true" ] && add_sig "public API or persisted schema change" 3
[ "$has_acceptance" = "false" ] && add_sig "no acceptance criteria supplied" 2
[ "$has_test_evidence" = "false" ] && add_sig "no test command + output supplied" 2

# ---- reject (intake circuit-break) ----
if [ "$score" -ge "$REJECT_SCORE" ]; then reject=true; reasons+=("intake score $score ≥ $REJECT_SCORE"); fi
if [ "$L" -gt "$HARD_MAX_LINES" ]; then reject=true; reasons+=("changed_lines $L > $HARD_MAX_LINES — split required"); fi
if [ "$F" -gt "$HARD_MAX_FILES" ]; then reject=true; reasons+=("changed_files $F > $HARD_MAX_FILES — split required"); fi

# ---- deterministic gates ----
TO() { if command -v timeout >/dev/null 2>&1; then timeout "${REVIEW_GATE_TIMEOUT:-180}" "$@"; else "$@"; fi; }
have() { command -v "$1" >/dev/null 2>&1; }
PM=""
if [ -f package.json ]; then
  if [ -f pnpm-lock.yaml ] && have pnpm; then PM=pnpm
  elif [ -f yarn.lock ] && have yarn; then PM=yarn
  elif have npm; then PM=npm; fi
fi
has_pkg_script() { [ -n "$PM" ] && grep -qE "\"$1\"[[:space:]]*:" package.json 2>/dev/null; }

run_gate() { # name cmd...
  local name="$1"; shift
  local out
  if out="$(TO "$@" 2>&1)"; then
    gates_run+=("$name:pass")
  else
    gates_run+=("$name:fail")
    det_fail=1
    reasons+=("deterministic gate '$name' failed")
  fi
}

if [ "$RUN_GATES" = "1" ]; then
  # lint
  if has_pkg_script lint; then run_gate lint $PM run -s lint
  elif have ruff; then run_gate lint ruff check .
  elif have flake8; then run_gate lint flake8
  elif have golangci-lint; then run_gate lint golangci-lint run; fi
  # typecheck
  if [ -f tsconfig.json ] && [ -x node_modules/.bin/tsc ]; then run_gate typecheck node_modules/.bin/tsc --noEmit
  elif has_pkg_script typecheck; then run_gate typecheck $PM run -s typecheck
  elif have mypy && ls ./*.py >/dev/null 2>&1; then run_gate typecheck mypy .
  elif [ -f go.mod ] && have go; then run_gate typecheck go build ./...; fi
  # tests (opt-in)
  if [ "$RUN_TESTS" = "1" ]; then
    if has_pkg_script test; then run_gate test $PM test
    elif have pytest; then run_gate test pytest -q
    elif [ -f go.mod ] && have go; then run_gate test go test ./...
    elif have cargo && [ -f Cargo.toml ]; then run_gate test cargo test --quiet; fi
  fi
fi
if [ "${#gates_run[@]}" -gt 0 ]; then
  if [ "$det_fail" -eq 1 ]; then det="fail"; else det="pass"; fi
fi

finish

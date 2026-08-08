#!/usr/bin/env bash
# ============================================================================
# Smoke test — run the WHOLE pipeline on a tiny matrix, then validate it.
# ============================================================================
# Purpose: find out that something is broken in ~20 minutes instead of six hours
# into the overnight run. It touches every stage and every method:
#
#   split -> render -> export -> run every method + ablation -> eval-traj
#   -> eval-recon -> eval-metric -> perf -> report -> report-clean -> verify-clean
#   -> report-tables -> snapshots (all 3 mask variants) -> smoke_check
#
# It uses config.smoke.yaml as an ADDITIVE overlay (PRISM_CONFIG_OVERLAY), so your
# frozen scene list in config.local.yaml is never modified.
#
# Results land in the normal results/ tree, tagged by the smoke scene, so they are
# easy to clear afterwards and are excluded from any real aggregate by scene name.
#
#   bash scripts/smoke_test.sh              # everything (recommended before a big run)
#   SMOKE_METHODS="prism pi3" bash scripts/smoke_test.sh     # subset the methods
#   SMOKE_TRAJ=synthetic_2.0hz_s0 bash scripts/smoke_test.sh # one trajectory (fastest)
#   SMOKE_SCENE=office_0 bash scripts/smoke_test.sh
#   SMOKE_KEEP=1 bash scripts/smoke_test.sh # keep previous smoke results (resume)
#
# Default size: 1 scene x 6 trajectories (3 motion families x 2 seeds) x every method.
# Runtime is dominated by per-run model load, not by frames. If you just want a 5-minute
# "does anything work at all" check, set SMOKE_TRAJ=synthetic_2.0hz_s0 — but note that
# skips the stop-and-go/loop paths, which is where the 2026-07 run actually broke.
# ============================================================================
set -uo pipefail

cd "$(dirname "$0")/.."
export PRISM_CONFIG_OVERLAY="${PRISM_CONFIG_OVERLAY:-config.smoke.yaml}"

SMOKE_KEEP="${SMOKE_KEEP:-0}"
SMOKE_TRAJ="${SMOKE_TRAJ:-all}"

# Scene comes from the overlay's must_include (or SMOKE_SCENE). We deliberately do NOT
# run `make split` here: split freezes a scene list into a config overlay, and the smoke
# has no business rewriting config files. Passing SCENES=... on the make command line is
# equivalent and side-effect free. (Note it must be on the COMMAND LINE, not exported:
# bench.env sets `SCENES :=`, and a makefile assignment beats the environment.)
if [ -z "${SMOKE_SCENE:-}" ]; then
  SMOKE_SCENE=$(uv run python -c "
from bench.config import load_config
c = load_config('config.yaml')
mi = c['datasets']['replica'].get('must_include') or []
sc = c['datasets']['replica'].get('scenes') or []
print((mi or sc or ['room_0'])[0])
" 2>/dev/null || echo room_0)
fi
LOG_DIR="logs"; mkdir -p "$LOG_DIR"
LOG="$LOG_DIR/smoke_$(date +%Y%m%d_%H%M%S).log"
ln -sf "$(basename "$LOG")" "$LOG_DIR/smoke_latest.log" 2>/dev/null || true

# Every method + ablation from the config, unless overridden.
if [ -z "${SMOKE_METHODS:-}" ]; then
  SMOKE_METHODS=$(uv run python -c "
from bench.config import load_config
c = load_config('config.yaml')
print(' '.join(m['name'] for m in c.get('methods', []) + c.get('ablations', [])))
" 2>/dev/null)
fi

FAILED_STAGES=()
START=$(date +%s)

say() { echo "" | tee -a "$LOG"; echo "=== $* ===" | tee -a "$LOG"; }

# Run a stage but DON'T abort the script: a smoke test that stops at the first
# error tells you about one problem per attempt. Running on and reporting every
# broken stage at the end is the whole point.
stage() {
  local name="$1"; shift
  say "$name"
  if "$@" >>"$LOG" 2>&1; then
    echo "    ok: $name" | tee -a "$LOG"
  else
    echo "    FAILED: $name (see $LOG)" | tee -a "$LOG"
    FAILED_STAGES+=("$name")
  fi
}

echo "PRISM-benchmarks SMOKE TEST" | tee "$LOG"
echo "overlay : $PRISM_CONFIG_OVERLAY" | tee -a "$LOG"
echo "scene   : $SMOKE_SCENE" | tee -a "$LOG"
echo "traj    : $SMOKE_TRAJ" | tee -a "$LOG"
echo "methods : $SMOKE_METHODS" | tee -a "$LOG"
echo "log     : $LOG" | tee -a "$LOG"

if [ "$SMOKE_KEEP" != "1" ]; then
  say "clearing previous results (SMOKE_KEEP=1 to resume instead)"
  rm -rf results/* 2>/dev/null || true
fi

# ── dataset ────────────────────────────────────────────────────────────────
MK=(SCENES="$SMOKE_SCENE" TRAJ="$SMOKE_TRAJ")
stage "render (pano + pinhole + GT)"    make render "${MK[@]}"
stage "export (adapter inputs)"         make export "${MK[@]}"

# The co-visibility mask — and therefore the masked F-score AND the covis/masked
# snapshot variants — needs the pinhole export. Fail loudly and early if it's absent,
# because everything downstream would silently degrade to full-360 only.
if ! ls dataset/exports/*/*/*/pinhole/*/intrinsics.json >/dev/null 2>&1; then
  echo "    FAILED: no pinhole export -> co-visibility mask impossible" | tee -a "$LOG"
  FAILED_STAGES+=("pinhole export missing")
fi

# ── run every method in its own env ────────────────────────────────────────
for m in $SMOKE_METHODS; do
  case "$m" in
    prism|panovggt|pi3|mapanything|vggtslam|laser)
      stage "run $m" make "run-$m" "${MK[@]}" ;;
    *)  # ablation arms go through the generic runner
      stage "run $m (ablation)" \
        uv run python adapters/run.py --method "$m" --config config.yaml \
          --scenes "$SMOKE_SCENE" --traj "$SMOKE_TRAJ" ;;
  esac
done

# ── evaluate ───────────────────────────────────────────────────────────────
stage "eval-traj"   make eval-traj
stage "eval-recon"  make eval-recon
stage "eval-metric" make eval-metric
stage "perf"        make perf
stage "report"      make report

# ── the publication path (seeded-only) ─────────────────────────────────────
stage "report-clean"  make report-clean SOURCE=live
stage "verify-clean"  make verify-clean
stage "report-tables" make report-tables

# ── figures ────────────────────────────────────────────────────────────────
stage "snapshots (all 3 mask variants)" make snapshots

# ── validate ───────────────────────────────────────────────────────────────
ELAPSED=$(( $(date +%s) - START ))
say "smoke pipeline finished in $((ELAPSED / 60))m $((ELAPSED % 60))s"

if [ ${#FAILED_STAGES[@]} -gt 0 ]; then
  echo "" | tee -a "$LOG"
  echo "STAGES THAT FAILED:" | tee -a "$LOG"
  for s in "${FAILED_STAGES[@]}"; do echo "  - $s" | tee -a "$LOG"; done
  echo "" | tee -a "$LOG"
fi

# smoke_check runs regardless — a failed stage plus a detailed artifact report is
# far more useful than a bare stage failure.
uv run python eval/smoke_check.py --config config.yaml \
  --expect-methods "$(echo "$SMOKE_METHODS" | tr ' ' ',')" 2>&1 | tee -a "$LOG"
CHECK_RC=${PIPESTATUS[0]}

echo "" | tee -a "$LOG"
echo "full log: $LOG" | tee -a "$LOG"
if [ ${#FAILED_STAGES[@]} -gt 0 ] || [ "$CHECK_RC" != "0" ]; then
  echo "SMOKE TEST FAILED — do not start the long run yet." | tee -a "$LOG"
  exit 1
fi
echo "SMOKE TEST PASSED — safe to start the full run (make bench-overnight)." | tee -a "$LOG"

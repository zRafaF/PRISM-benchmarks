#!/usr/bin/env bash
# ============================================================================
# PRISM-benchmarks — overnight big-benchmark driver
# ----------------------------------------------------------------------------
# Runs the whole matrix (6 scenes × 2 seeds × {smooth rate-sweep, stop-and-go,
# loop} × all methods + alignment/guard ablations), in PRIORITY ORDER so the
# headline results are done first, with eval+report CHECKPOINTS after each phase
# (so there is always a current report even if the run is interrupted).
#
# Survives SSH disconnect + is resumable:
#   * launch it detached (see below) — it keeps running after logout;
#   * every method run SKIPS if its output already exists (base.py resume), so
#     re-launching after a crash continues where it stopped. Set FORCE=1 to redo.
#
# LAUNCH (pick one), from the repo root:
#   tmux new -s bench 'bash scripts/run_overnight.sh'        # reattach: tmux attach -t bench
#   nohup bash scripts/run_overnight.sh >/dev/null 2>&1 &    # then: tail -f logs/overnight_*.log
#   make bench-overnight                                     # = the tmux form
#
# MONITOR:  tail -f logs/overnight_<stamp>.log
#           cat  logs/overnight_<stamp>.progress
# ============================================================================
set -u -o pipefail
cd "$(dirname "$0")/.."                     # repo root

STAMP="$(date +%Y%m%d_%H%M%S)"
mkdir -p logs
LOG="logs/overnight_${STAMP}.log"
PROG="logs/overnight_${STAMP}.progress"
ln -sf "overnight_${STAMP}.log" logs/overnight_latest.log

# All stdout/stderr -> terminal AND the log file (so nothing is lost on disconnect).
exec > >(tee -a "$LOG") 2>&1

RUN="uv run python"
[ "${FORCE:-0}" = "1" ] && export PRISM_FORCE=1     # redo completed runs if FORCE=1

# ── Method sets ─────────────────────────────────────────────────────────────
CORE="prism panovggt pi3 mapanything vggtslam laser"   # ours + all baselines
ALIGN="prism_sim3 prism_se3"                            # alignment-group study (sl4=prism)
GUARD="prism_nolock prism_nostill prism_noguards"       # guard study

log()  { echo "[$(date +%H:%M:%S)] $*"; }
note() { echo "$*" >> "$PROG"; }

# run METHODS × one concrete traj (scenes come from the frozen config list).
run_set() {
  local traj="$1"; shift
  for m in "$@"; do
    log ">>> RUN  method=$m  traj=$traj"
    if $RUN adapters/run.py --method "$m" --config config.yaml --scenes "" --traj "$traj"; then
      note "ok   $traj  $m"
    else
      note "FAIL $traj  $m   (continuing)"
      log  "!!! FAILED method=$m traj=$traj — continuing"
    fi
  done
}

checkpoint() {   # eval everything produced so far + refresh the report
  log "=== CHECKPOINT: eval + perf + report (phase: $1) ==="
  $RUN eval/eval_traj.py        --config config.yaml || true
  $RUN eval/eval_recon.py       --config config.yaml || true
  $RUN eval/metric_accuracy.py  --config config.yaml || true
  $RUN eval/collect_perf.py     --config config.yaml || true
  $RUN eval/make_report.py      --config config.yaml || true
  note "checkpoint after phase $1  ->  results/report/report.md"
  log "=== report refreshed: results/report/report.md ==="
}

log "############ PRISM overnight benchmark  stamp=$STAMP ############"
note "start $STAMP"

# ── Stage 0: env + dataset freeze ───────────────────────────────────────────
log "### Stage 0: setup / download / split (freeze scene list)"
make setup
$RUN dataset/download.py   --config config.yaml || true    # prints/fetches active datasets
$RUN dataset/make_split.py --config config.yaml || true    # freezes 6 scenes -> config.local.yaml

# ── Stage 1: render + export the WHOLE matrix (GT for every traj) ────────────
log "### Stage 1: render + export all trajectories (this is the GT; needed by eval)"
make render SCENES="" TRAJ=all || true
make export SCENES="" TRAJ=all || true

# ── Stage 2: method runs, PRIORITY ORDER, with checkpoints ──────────────────
# Phase 1 — headline: every method on the primary comparison (smooth 2 Hz, seed 0).
log "### Phase 1: headline  (smooth 2 Hz, seed 0)"
run_set synthetic_2.0hz_s0 $CORE $ALIGN
checkpoint P1

# Phase 2 — motion stress: loop + stop-and-go (2 Hz, seed 0), incl. guard study.
log "### Phase 2: motion stress  (loop + stop-and-go, seed 0)"
run_set loop_2.0hz_s0   $CORE $ALIGN $GUARD
run_set stopgo_2.0hz_s0 $CORE $ALIGN $GUARD
checkpoint P2

# Phase 3 — variance: second seed of the three primary motion patterns.
log "### Phase 3: variance  (seed 1 of the primary trajectories)"
run_set synthetic_2.0hz_s1 $CORE $ALIGN
run_set loop_2.0hz_s1      $CORE $ALIGN $GUARD
run_set stopgo_2.0hz_s1    $CORE $ALIGN $GUARD
checkpoint P3

# Phase 4 — rate sweep: 0.5 + 5 Hz smooth, both seeds (core + alignment only).
log "### Phase 4: rate sweep  (0.5 + 5 Hz smooth, both seeds)"
for t in synthetic_0.5hz_s0 synthetic_5.0hz_s0 synthetic_0.5hz_s1 synthetic_5.0hz_s1; do
  run_set "$t" $CORE $ALIGN
done
checkpoint P4

# ── Stage 3: standardized snapshots for the primary trajectories ────────────
log "### Stage 3: snapshots (primary trajectories, PRISM arms + key baselines)"
make snapshots SNAP_METHODS="prism prism_sim3 prism_se3 vggtslam panovggt pi3" \
               SNAP_SCENES="" SNAP_TRAJ="synthetic_2.0hz_s0 loop_2.0hz_s0 stopgo_2.0hz_s0" || true

log "############ DONE  stamp=$STAMP ############"
note "done $STAMP"
echo "Report:    results/report/report.md"
echo "Snapshots: results/report/snapshots/"

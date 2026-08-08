#!/usr/bin/env bash
# ============================================================================
# PRISM-benchmarks — overnight big-benchmark driver
# ----------------------------------------------------------------------------
# Runs the whole matrix in PRIORITY ORDER so the headline results land first,
# with eval + CLEAN-report CHECKPOINTS after each phase — so there is always a
# current, citable report even if the run is interrupted.
#
# Survives SSH disconnect + is resumable:
#   * launch it detached (`make bench-overnight` does this for you);
#   * every method run SKIPS if its output already exists (adapters/base.py
#     resume), so re-launching after a crash continues where it stopped.
#     FORCE=1 redoes completed runs.
#
# LAUNCH (from the repo root):
#   make bench-overnight          # detached; picks tmux, else setsid, else nohup
#   make bench-status             # progress + live tail
#   make bench-stop               # stop it
#
# The method/trajectory lists are DERIVED FROM config.yaml, not hardcoded. The
# previous version hardcoded `prism_sim3` and two seeds; when the default
# alignment group flipped to Sim(3) that arm ceased to exist and the run would
# have burned hours failing on every alignment arm.
# ============================================================================
set -u -o pipefail
cd "$(dirname "$0")/.."                     # repo root

STAMP="$(date +%Y%m%d_%H%M%S)"
mkdir -p logs
LOG="logs/overnight_${STAMP}.log"
PROG="logs/overnight_${STAMP}.progress"
ln -sf "overnight_${STAMP}.log" logs/overnight_latest.log
ln -sf "overnight_${STAMP}.progress" logs/overnight_latest.progress

exec > >(tee -a "$LOG") 2>&1

RUN="uv run python"
[ "${FORCE:-0}" = "1" ] && export PRISM_FORCE=1

log()  { echo "[$(date +%H:%M:%S)] $*"; }
note() { echo "[$(date +%H:%M:%S)] $*" >> "$PROG"; }

# ── Method sets, read from the config so they can never drift ───────────────
read_cfg() { $RUN - <<'PY'
from bench.config import load_config
c = load_config('config.yaml')
ms = c.get('methods', []); ab = c.get('ablations', [])
core = [m['name'] for m in ms]
align = [m['name'] for m in ab if m.get('align_group')]
vslam = [m['name'] for m in ab if m.get('runner') == 'vggtslam']
guard = [m['name'] for m in ab
         if not m.get('align_group') and m.get('runner') != 'vggtslam']
print('CORE=' + ' '.join(core))
print('ALIGN=' + ' '.join(align))
print('VSLAM=' + ' '.join(vslam))
print('GUARD=' + ' '.join(guard))
print('NSEEDS=' + str(len(c['datasets'].get('seeds') or [c['datasets'].get('seed')])))
PY
}
eval "$(read_cfg)"
CORE="${CORE:-}"; ALIGN="${ALIGN:-}"; VSLAM="${VSLAM:-}"; GUARD="${GUARD:-}"
NSEEDS="${NSEEDS:-1}"

# Trajectory ids for a family, one per seed (suffix only when >1 seed).
seeds_of() {  # seeds_of <family_prefix>_<rate>hz
  local base="$1" out=""
  if [ "$NSEEDS" -le 1 ]; then echo "$base"; return; fi
  for i in $(seq 0 $((NSEEDS - 1))); do out="$out ${base}_s${i}"; done
  echo "$out"
}

run_set() {   # run_set <traj> <methods...>
  local traj="$1"; shift
  for m in "$@"; do
    [ -z "$m" ] && continue
    log ">>> RUN  method=$m  traj=$traj"
    if $RUN adapters/run.py --method "$m" --config config.yaml --scenes "" --traj "$traj"; then
      note "ok   $traj  $m"
    else
      note "FAIL $traj  $m   (continuing)"
      log  "!!! FAILED method=$m traj=$traj — continuing"
    fi
  done
}

checkpoint() {
  log "=== CHECKPOINT: eval + CLEAN report (phase: $1) ==="
  $RUN eval/eval_traj.py       --config config.yaml || true
  $RUN eval/eval_recon.py      --config config.yaml || true
  $RUN eval/metric_accuracy.py --config config.yaml || true
  $RUN eval/collect_perf.py    --config config.yaml || true
  $RUN eval/make_report.py     --config config.yaml || true
  # The publication path too: seeded-only, complete-runs-only, plus the
  # contamination check. Costs seconds and means an interrupted run still leaves
  # citable numbers rather than only the aggregate-everything report.
  $RUN eval/aggregate_clean.py     --config config.yaml --source live || true
  $RUN eval/export_report_tables.py                                   || true
  $RUN eval/verify_clean.py --skip-published-check                    || true
  # Surface the failure rate immediately — this is the metric that would have
  # caught the 2026-07 problem on the night rather than weeks later.
  if [ -f results/report_clean/completion.csv ]; then
    log "--- completion so far (method,total,complete,incomplete,%) ---"
    cut -d, -f1-5 results/report_clean/completion.csv | sed 's/^/    /'
    awk -F, 'NR>1 && $4+0 > 0 {bad++} END {if (bad) print "    ** " bad
      " method(s) have INCOMPLETE runs — check results/report_clean/completion.csv **"}' \
      results/report_clean/completion.csv
  fi
  note "checkpoint after phase $1 -> results/report_clean/clean_report.md"
}

log "############ PRISM overnight benchmark  stamp=$STAMP ############"
note "start $STAMP"
log "CORE  = $CORE"
log "ALIGN = $ALIGN"
log "VSLAM = $VSLAM"
log "GUARD = $GUARD"
log "seeds = $NSEEDS"

# ── Preflight: fail in seconds, not hours ───────────────────────────────────
log "### Preflight"
PREFLIGHT_FAIL=0
for m in $CORE; do
  env_dir=$($RUN -c "
from bench.config import load_config
c=load_config('config.yaml')
print(next((x['env'] for x in c['methods']+c['ablations'] if x['name']=='$m'), ''))" 2>/dev/null)
  if [ -n "$env_dir" ] && [ ! -x "$env_dir/.venv/bin/python" ]; then
    log "!!! PREFLIGHT: $m has no env at $env_dir/.venv — run 'make setup-$m'"
    PREFLIGHT_FAIL=1
  fi
done
if [ "$PREFLIGHT_FAIL" = "1" ] && [ "${IGNORE_PREFLIGHT:-0}" != "1" ]; then
  log "ABORTING: method envs missing. Fix them, or IGNORE_PREFLIGHT=1 to run anyway."
  note "aborted: preflight"
  exit 1
fi

# ── Stage 0: env + dataset freeze ───────────────────────────────────────────
log "### Stage 0: setup / download / split (freeze scene list)"
make setup
$RUN dataset/download.py   --config config.yaml || true
$RUN dataset/make_split.py --config config.yaml || true

# ── Stage 1: render + export the WHOLE matrix (this is the GT) ──────────────
log "### Stage 1: render + export all trajectories"
make render SCENES="" TRAJ=all || true
make export SCENES="" TRAJ=all || true

# ── Stage 2: method runs, PRIORITY ORDER, with checkpoints ──────────────────
# Phase 1 — headline: every method on the primary comparison (smooth 2 Hz, seed 0).
log "### Phase 1: headline  (smooth 2 Hz, seed 0)"
P1_TRAJ=$([ "$NSEEDS" -le 1 ] && echo synthetic_2.0hz || echo synthetic_2.0hz_s0)
run_set "$P1_TRAJ" $CORE $ALIGN $VSLAM
checkpoint P1

# Phase 2 — motion stress at seed 0. This is where 30 of the 43 failures were in
# 2026-07, so it runs early: if PRISM is going to fall over, find out by checkpoint 2.
log "### Phase 2: motion stress  (loop + stop-and-go, seed 0)"
for fam in loop_2.0hz stopgo_2.0hz; do
  t=$([ "$NSEEDS" -le 1 ] && echo "$fam" || echo "${fam}_s0")
  run_set "$t" $CORE $ALIGN $VSLAM $GUARD
done
checkpoint P2

# Phase 3 — variance: every remaining seed of the three primary motion patterns.
log "### Phase 3: variance  (seeds 1..$((NSEEDS - 1)) of the primary trajectories)"
if [ "$NSEEDS" -gt 1 ]; then
  for i in $(seq 1 $((NSEEDS - 1))); do
    run_set "synthetic_2.0hz_s${i}" $CORE $ALIGN $VSLAM
    run_set "loop_2.0hz_s${i}"      $CORE $ALIGN $VSLAM $GUARD
    run_set "stopgo_2.0hz_s${i}"    $CORE $ALIGN $VSLAM $GUARD
    checkpoint "P3.s${i}"
  done
else
  log "(single seed configured — no variance phase)"
fi

# Phase 4 — rate sweep: 0.5 + 5 Hz smooth, every seed (core + alignment only).
log "### Phase 4: rate sweep  (0.5 + 5 Hz smooth, all seeds)"
for fam in synthetic_0.5hz synthetic_5.0hz; do
  for t in $(seeds_of "$fam"); do
    run_set "$t" $CORE $ALIGN
  done
done
checkpoint P4

# ── Stage 3: standardized snapshots, all co-visibility mask variants ────────
# SNAP_METHODS is derived, so it can't reference an arm that no longer exists.
log "### Stage 3: snapshots (primary trajectories; full/covis/masked variants)"
SNAP_M="$(echo $CORE $ALIGN | tr ' ' '\n' | grep -v '^$' | tr '\n' ' ')"
SNAP_T=$([ "$NSEEDS" -le 1 ] \
  && echo "synthetic_2.0hz loop_2.0hz stopgo_2.0hz" \
  || echo "synthetic_2.0hz_s0 loop_2.0hz_s0 stopgo_2.0hz_s0")
make snapshots SNAP_METHODS="$SNAP_M" SNAP_SCENES="" SNAP_TRAJ="$SNAP_T" || true

log "############ DONE  stamp=$STAMP ############"
note "done $STAMP"
echo
echo "Clean report : results/report_clean/clean_report.md   <- cite this one"
echo "Report tables: results/report_tables/                 <- for uofa-2026-report"
echo "Completion   : results/report_clean/completion.csv    <- read before any mean"
echo "Snapshots    : results/report/snapshots/"
echo "Full log     : $LOG"

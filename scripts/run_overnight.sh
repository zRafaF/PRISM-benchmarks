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
#   DRY_RUN=1 bash scripts/run_overnight.sh    # print the plan and exit
#
# ---------------------------------------------------------------------------
# POST-MORTEM (2026-08-08 run, fixed here). That run executed ZERO method runs
# and still exited "successfully", then its checkpoints aggregated leftover
# smoke-test results — so it looked like a completed 1-scene benchmark.
#
# Cause: the config was read with
#     print('CORE=' + ' '.join(core))      ->  CORE=prism panovggt pi3 ...
#     eval "$(read_cfg)"
# Unquoted, bash read that as "set CORE=prism for the duration of the command
# `panovggt`", which does not exist. Hence `panovggt: command not found`, and
# CORE/ALIGN/VSLAM/GUARD all ended up EMPTY. `run_set` then looped over nothing.
#
# Three defences added, because any one alone would have let it through:
#   1. values are emitted shell-quoted and sourced from a file — no bare `eval`;
#   2. an empty method list is a hard ABORT, not a silent no-op;
#   3. the full plan is PRINTED and every run is counted [n/N], so "it ran
#      nothing" or "it ran one scene" is obvious in the first screen of output.
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

# Overridable so the plan logic can be exercised without the uv bootstrap (tests/CI).
RUN="${RUN:-uv run python}"
DRY_RUN="${DRY_RUN:-0}"
[ "${FORCE:-0}" = "1" ] && export PRISM_FORCE=1

log()  { echo "[$(date +%H:%M:%S)] $*"; }
note() { echo "[$(date +%H:%M:%S)] $*" >> "$PROG"; }
die()  { echo ""; echo "!!!!!! ABORT: $*"; echo ""; note "ABORT: $*"; exit 1; }

# ── A smoke overlay leaking in here would silently shrink the whole matrix ───
if [ -n "${PRISM_CONFIG_OVERLAY:-}" ]; then
  die "PRISM_CONFIG_OVERLAY=$PRISM_CONFIG_OVERLAY is set. That is the smoke-test
      overlay (1 scene, 20 frames). It would silently shrink this run to the
      smoke matrix. Run 'unset PRISM_CONFIG_OVERLAY' and relaunch."
fi

# ── Read the plan from config.yaml ──────────────────────────────────────────
# Emitted SHELL-QUOTED into a file and sourced. Never `eval` an unquoted string.
PLAN_SH="logs/.overnight_plan_${STAMP}.sh"
$RUN - "$PLAN_SH" <<'PY' || die "could not read config.yaml"
import shlex, sys
from bench.config import load_config, resolve_trajs
c = load_config('config.yaml')
ms, ab = c.get('methods', []), c.get('ablations', [])
core  = [m['name'] for m in ms]
align = [m['name'] for m in ab if m.get('align_group')]
vslam = [m['name'] for m in ab if m.get('runner') == 'vggtslam']
sweep = [m['name'] for m in ab if m.get('role') == 'sweep']
guard = [m['name'] for m in ab
         if not m.get('align_group') and m.get('runner') != 'vggtslam'
         and m.get('role') != 'sweep']
ds     = c['datasets'][c['datasets']['active'][0]]
scenes = list(ds.get('scenes') or [])
seeds  = list(c['datasets'].get('seeds') or [c['datasets'].get('seed')])
trajs  = resolve_trajs(c, 'all')
with open(sys.argv[1], 'w') as f:
    def put(k, v): f.write(f"{k}={shlex.quote(str(v))}\n")
    put('CORE',   ' '.join(core))
    put('ALIGN',  ' '.join(align))
    put('VSLAM',  ' '.join(vslam))
    put('GUARD',  ' '.join(guard))
    put('SWEEP',  ' '.join(sweep))
    put('SCENES_FROZEN', ' '.join(scenes))
    put('TRAJS',  ' '.join(trajs))
    put('NSEEDS', len(seeds))
    put('SEEDS',  ' '.join(str(s) for s in seeds))
    put('NFRAMES', c['trajectories']['n_frames'])
    put('NSCENES_TARGET', ds.get('n_scenes_start', 0))
    put('DS', c['datasets']['active'][0])
PY
# shellcheck disable=SC1090
. "$PLAN_SH"

# ── Defence 2: refuse to run with an empty method list ──────────────────────
[ -z "${CORE:-}" ]  && die "CORE method list is EMPTY — config.yaml 'methods' did not parse.
      This is the exact failure that made the 2026-08-08 run do nothing."
[ -z "${ALIGN:-}" ] && log "WARNING: no alignment-group ablation arms found in config.ablations"
[ -z "${VSLAM:-}" ] && log "WARNING: no VGGT-SLAM fairness arms found in config.ablations"

ALL_METHODS="$CORE $ALIGN $VSLAM $GUARD $SWEEP"
N_METHODS=$(echo $ALL_METHODS | wc -w)
N_MAIN=$(echo $CORE $ALIGN $VSLAM $GUARD | wc -w)
N_SWEEP=$(echo ${SWEEP:-} | wc -w)
N_TRAJS=$(echo $TRAJS | wc -w)
N_SCENES=$(echo ${SCENES_FROZEN:-} | wc -w)

# ── Defence 3: PRINT THE PLAN, loudly, before anything runs ─────────────────
cat <<PLAN

################################################################################
#  PRISM overnight benchmark — RUN PLAN                      stamp=$STAMP
################################################################################
  scenes frozen    : ${N_SCENES} -> ${SCENES_FROZEN:-<none: 'make split' will freeze them>}
  target scenes    : ${NSCENES_TARGET}   (datasets.<ds>.n_scenes_start)
  seeds            : ${NSEEDS}  [${SEEDS}]
  frames/traj      : ${NFRAMES}
  trajectories     : ${N_TRAJS}
      ${TRAJS}
  methods          : ${N_METHODS}
      core   : ${CORE}
      align  : ${ALIGN:-<none>}
      vggt   : ${VSLAM:-<none>}
      guards : ${GUARD:-<none>}
      sweep  : ${SWEEP:-<none>}  (voxel/max_depth curve; reduced scene+traj set, see Phase 5)

  TOTAL PLANNED RUNS : ~$(( ${N_SCENES:-0} * N_TRAJS * N_MAIN + N_SWEEP * 4 ))
      = ${N_SCENES:-0} scenes x $N_TRAJS trajs x $N_MAIN main methods  ($(( ${N_SCENES:-0} * N_TRAJS * N_MAIN )))
      + $N_SWEEP sweep arms on ONE scene x ~4 trajs             (~$(( N_SWEEP * 4 )))
      Sweep arms deliberately do NOT run the full grid (Phase 5). Guard arms, if any,
      only run the stress trajectories. The exact count is printed as [n] per run.

  If any number above looks wrong -- especially "scenes frozen" being 1, or an
  empty method list -- STOP NOW (make bench-stop) rather than burning a night.
################################################################################

PLAN

if [ "$N_SCENES" -le 1 ] && [ "${NSCENES_TARGET}" -gt 1 ]; then
  log "NOTE: only ${N_SCENES} scene(s) frozen but n_scenes_start=${NSCENES_TARGET}."
  log "      'make split' runs below and should freeze ${NSCENES_TARGET}; the plan is"
  log "      re-printed after it so you can confirm before the method runs start."
fi

# ── Stale results from a different matrix? (this is what masked the last run) ─
if [ -d results ] && [ "${FORCE:-0}" != "1" ]; then
  # Enumerate REAL run dirs by their perf.json at the canonical depth:
  #   results/<method>/<dataset>/<scene>/<traj>/<variant>/perf.json   -> scene is $4
  # A directory glob is not enough: it also matches results/report*/ AND any extracted
  # results bundle sitting under results/ (which nests its own results/ tree one level
  # deeper), so it reported method names and "report_clean" as if they were scenes --
  # misleading precisely when you are deciding whether the tree is stale.
  EXISTING=$(ls results/*/*/*/*/*/perf.json 2>/dev/null | awk -F/ '{print $4}' | sort -u | tr '\n' ' ')
  if [ -n "$EXISTING" ]; then
    log "NOTE: results/ already contains runs for scene(s): $EXISTING"
    log "      Completed runs are SKIPPED (resume). If those are stale smoke results,"
    log "      clear them first with 'make clean-results' — otherwise they will be"
    log "      aggregated into the report alongside the new ones."
  fi
fi

if [ "$DRY_RUN" = "1" ]; then
  log "DRY_RUN=1 — plan printed, exiting without running anything."
  rm -f "$PLAN_SH"
  exit 0
fi

# ── Counters ────────────────────────────────────────────────────────────────
RUN_N=0
RUN_OK=0
RUN_FAIL=0

run_set() {   # run_set <traj> <methods...>
  local traj="$1"; shift
  for m in "$@"; do
    [ -z "$m" ] && continue
    RUN_N=$((RUN_N + 1))
    log ">>> RUN [$RUN_N]  method=$m  traj=$traj  (ok=$RUN_OK fail=$RUN_FAIL)"
    if $RUN adapters/run.py --method "$m" --config config.yaml --scenes "" --traj "$traj"; then
      RUN_OK=$((RUN_OK + 1)); note "ok   $traj  $m"
    else
      RUN_FAIL=$((RUN_FAIL + 1)); note "FAIL $traj  $m   (continuing)"
      log  "!!! FAILED method=$m traj=$traj — continuing"
    fi
  done
}

# Each eval step keeps going on failure (a checkpoint must never abort the night),
# but a failure is now ANNOUNCED and counted. On 2026-08-09 eval_recon.py died on
# one degenerate run, `|| true` swallowed it, and 196 of 590 runs silently lost
# their reconstruction metrics while the log said the checkpoint completed.
EVAL_FAIL=0
eval_step() {   # eval_step <phase> <script> [args...]
  local phase="$1" script="$2"; shift 2
  if ! $RUN "$script" "$@"; then
    EVAL_FAIL=$((EVAL_FAIL + 1))
    log "!!! EVAL STEP FAILED: $script  (phase $phase)"
    log "!!!   Runs this step did not reach have NO metrics and will be counted"
    log "!!!   as incomplete. Do not cite this checkpoint's tables."
    note "EVAL FAIL $script  (phase $phase)"
  fi
}

checkpoint() {
  log "=== CHECKPOINT: eval + CLEAN report (phase: $1) — $RUN_N runs dispatched so far ==="
  eval_step "$1" eval/eval_traj.py       --config config.yaml
  eval_step "$1" eval/eval_recon.py      --config config.yaml
  eval_step "$1" eval/metric_accuracy.py --config config.yaml
  eval_step "$1" eval/collect_perf.py    --config config.yaml
  eval_step "$1" eval/make_report.py     --config config.yaml
  eval_step "$1" eval/aggregate_clean.py --config config.yaml --source live
  eval_step "$1" eval/export_report_tables.py
  eval_step "$1" eval/verify_clean.py --skip-published-check
  if [ -f results/report_clean/completion.csv ]; then
    log "--- completion so far (method,total,complete,incomplete,%) ---"
    cut -d, -f1-5 results/report_clean/completion.csv | sed 's/^/    /'
    awk -F, 'NR>1 && $4+0 > 0 {bad++} END {if (bad) print "    ** " bad
      " method(s) have INCOMPLETE runs — see results/report_clean/completion.csv **"}' \
      results/report_clean/completion.csv
  fi
  note "checkpoint after phase $1 ($RUN_N runs: $RUN_OK ok / $RUN_FAIL failed)"
}

log "############ PRISM overnight benchmark  stamp=$STAMP ############"
note "start $STAMP  ($N_METHODS methods x $N_TRAJS trajs)"

# ── Preflight: fail in seconds, not hours ───────────────────────────────────
log "### Preflight"
PREFLIGHT_FAIL=0
for m in $ALL_METHODS; do
  env_dir=$($RUN -c "
from bench.config import load_config
c=load_config('config.yaml')
print(next((x['env'] for x in c['methods']+c['ablations'] if x['name']=='$m'), ''))" 2>/dev/null)
  if [ -z "$env_dir" ]; then
    log "!!! PREFLIGHT: '$m' is not in config.yaml methods/ablations"; PREFLIGHT_FAIL=1
  elif [ ! -x "$env_dir/.venv/bin/python" ]; then
    log "!!! PREFLIGHT: $m has no env at $env_dir/.venv — run 'make setup-$m'"; PREFLIGHT_FAIL=1
  fi
done
if [ "$PREFLIGHT_FAIL" = "1" ] && [ "${IGNORE_PREFLIGHT:-0}" != "1" ]; then
  die "method envs missing (see above). Fix them, or IGNORE_PREFLIGHT=1 to run anyway."
fi
log "preflight OK — $N_METHODS methods have envs"

# ── Stage 0: env + dataset freeze ───────────────────────────────────────────
log "### Stage 0: setup / download / split (freeze scene list)"
make setup
$RUN dataset/download.py   --config config.yaml || true
$RUN dataset/make_split.py --config config.yaml || true

# Re-read the frozen scene list AFTER split and re-print, so the scene count that
# will actually be benchmarked is visible before any GPU time is spent.
SCENES_AFTER=$($RUN -c "
from bench.config import load_config
c=load_config('config.yaml'); ds=c['datasets'][c['datasets']['active'][0]]
print(' '.join(ds.get('scenes') or []))" 2>/dev/null)
N_SCENES_AFTER=$(echo $SCENES_AFTER | wc -w)
log "### Scene list after split: ${N_SCENES_AFTER} scene(s) -> ${SCENES_AFTER:-<EMPTY>}"
[ "$N_SCENES_AFTER" -eq 0 ] && die "no scenes frozen — is the dataset downloaded? (make download)"
log "### TOTAL RUNS THIS SESSION: ~$(( N_SCENES_AFTER * N_TRAJS * N_MAIN + N_SWEEP * 4 ))"
log "###   = ${N_SCENES_AFTER} scenes x ${N_TRAJS} trajs x ${N_MAIN} main methods ($(( N_SCENES_AFTER * N_TRAJS * N_MAIN )))"
log "###   + ${N_SWEEP} sweep arms on a reduced set (~$(( N_SWEEP * 4 )))   [same split as the RUN PLAN above]"
note "scenes: $SCENES_AFTER"

# ── Stage 0b: can every scene even produce every trajectory? ─────────────────
# Seconds, no GPU, no images: builds the waypoints + spline for every (scene, traj)
# pair and reports what each WOULD render. On 2026-08-09 this check would have caught
# both scene failures (room_2 rendering nothing, office_0 rendering a 0.6 m circuit)
# before the run started, instead of after seven hours.
log "### Stage 0b: pre-flight — every scene x trajectory buildable at target length"
if ! make check-scenes; then
  log "!!! PRE-FLIGHT FAILED — at least one scene cannot produce a usable trajectory."
  [ "${IGNORE_RENDER_FAIL:-0}" != "1" ] && die "fix the scenes above, or IGNORE_RENDER_FAIL=1"
  log "!!!   IGNORE_RENDER_FAIL=1 set — continuing anyway."
fi

# ── Stage 1: render + export the WHOLE matrix (this is the GT) ──────────────
# A render failure is FATAL unless explicitly waived. On 2026-08-09 `make render` died
# on room_2 (its floor estimate was 0.85 m too low, so no waypoint could pass the
# bare-floor test), `|| true` swallowed the non-zero exit, and the whole night ran on
# 5 scenes instead of 6 — with nothing in the summary saying so. Every method then had
# an unequal, unexplained N. Set IGNORE_RENDER_FAIL=1 to proceed deliberately.
log "### Stage 1: render + export all trajectories ($N_TRAJS trajs x $N_SCENES_AFTER scenes)"
if ! make render SCENES="" TRAJ=all; then
  log "!!! RENDER FAILED — at least one scene/trajectory did not render."
  log "!!!   Running the matrix now would silently benchmark a SUBSET of the scenes."
  log "!!!   Scroll up for the [waypoints]/[mesh]/[traj] debug of the failing scene."
  [ "${IGNORE_RENDER_FAIL:-0}" != "1" ] && die "render failed (IGNORE_RENDER_FAIL=1 to override)"
  log "!!!   IGNORE_RENDER_FAIL=1 set — continuing with an INCOMPLETE scene set."
fi
if ! make export SCENES="" TRAJ=all; then
  log "!!! EXPORT FAILED — see above."
  [ "${IGNORE_RENDER_FAIL:-0}" != "1" ] && die "export failed (IGNORE_RENDER_FAIL=1 to override)"
fi

# Confirm every frozen scene actually produced every trajectory before spending GPU on
# them. A scene that rendered zero trajectories is the room_2 failure; a scene whose
# trajectories are far shorter than the target is the office_0 failure.
MISSING=""
for sc in $SCENES_AFTER; do
  for tj in $TRAJS; do
    [ -d "dataset/exports/${DS:-replica}/$sc/$tj" ] || MISSING="$MISSING $sc/$tj"
  done
done
if [ -n "$MISSING" ]; then
  log "!!! MISSING EXPORTS:$MISSING"
  [ "${IGNORE_RENDER_FAIL:-0}" != "1" ] && die "some scene/trajectory pairs never rendered"
fi
log "### Stage 1 OK — all $N_SCENES_AFTER scenes x $N_TRAJS trajectories exported"

# ── Stage 2: method runs, PRIORITY ORDER, with checkpoints ──────────────────
log "### Phase 1: headline  (smooth 2 Hz, seed 0)"
P1_TRAJ=$([ "$NSEEDS" -le 1 ] && echo synthetic_2.0hz || echo synthetic_2.0hz_s0)
run_set "$P1_TRAJ" $CORE $ALIGN $VSLAM
checkpoint P1

# Phase 2 — motion stress at seed 0. This is where 30 of the 43 failures were in
# 2026-07, so it runs early: if PRISM is going to fall over, find out by checkpoint 2.
# Stress families come from TRAJS (i.e. from config.trajectories.extra_kinds), not a
# hardcoded list — disabling stop-and-go in the config must not leave this loop asking
# for a trajectory that was never rendered.
STRESS_FAMS=$(echo "$TRAJS" | tr ' ' '\n' | grep -E '^(loop|stopgo)_' | sed 's/_s[0-9]*$//' | sort -u | tr '\n' ' ')
log "### Phase 2: motion stress  (${STRESS_FAMS:-<none configured>}, seed 0)"
for fam in $STRESS_FAMS; do
  t=$([ "$NSEEDS" -le 1 ] && echo "$fam" || echo "${fam}_s0")
  run_set "$t" $CORE $ALIGN $VSLAM $GUARD
done
checkpoint P2

log "### Phase 3: variance  (seeds 1..$((NSEEDS - 1)) of the primary trajectories)"
if [ "$NSEEDS" -gt 1 ]; then
  for i in $(seq 1 $((NSEEDS - 1))); do
    run_set "synthetic_2.0hz_s${i}" $CORE $ALIGN $VSLAM
    for fam in $STRESS_FAMS; do
      run_set "${fam}_s${i}" $CORE $ALIGN $VSLAM $GUARD
    done
    checkpoint "P3.s${i}"
  done
else
  log "(single seed configured — no variance phase)"
fi

log "### Phase 4: rate sweep  (all non-2Hz smooth trajectories, all seeds)"
for t in $TRAJS; do
  case "$t" in
    synthetic_2.0hz*|loop_*|stopgo_*) continue ;;   # already done above
    *) run_set "$t" $CORE $ALIGN ;;
  esac
done
checkpoint P4

# ── Phase 5: fidelity-vs-memory sweep (PRISM only, REDUCED set) ─────────────
# Deliberately not the full matrix: the sweep answers "what does the voxel/max_depth
# knob buy", which needs a few points on one representative scene, not 6 scenes x 12
# trajectories. Running it across everything would roughly double the night for no
# extra information. 5 arms x SWEEP_TRAJS on SWEEP_SCENE ~= 30 runs.
SWEEP_SCENE="${SWEEP_SCENE:-}"
if [ -z "$SWEEP_SCENE" ]; then
  # a mid-size scene: skip the two pinned small rooms if there is anything else
  SWEEP_SCENE=$(echo "$SCENES_AFTER" | tr ' ' '\n' | grep -vE '^(room_0|office_0)$' | head -1)
  [ -z "$SWEEP_SCENE" ] && SWEEP_SCENE=$(echo "$SCENES_AFTER" | awk '{print $1}')
fi
SWEEP_TRAJS="${SWEEP_TRAJS:-}"
if [ -z "$SWEEP_TRAJS" ]; then
  if [ "$NSEEDS" -le 1 ]; then
    SWEEP_TRAJS="synthetic_2.0hz synthetic_5.0hz loop_2.0hz"
  else
    SWEEP_TRAJS="synthetic_2.0hz_s0 synthetic_2.0hz_s1 synthetic_5.0hz_s0 loop_2.0hz_s0"
  fi
fi
if [ -n "${SWEEP:-}" ]; then
  log "### Phase 5: fidelity/memory sweep — scene=$SWEEP_SCENE  trajs=$SWEEP_TRAJS"
  log "###          arms: $SWEEP  (plus 'prism' itself as the 0.02 m / 4.5 m reference)"
  for t in $SWEEP_TRAJS; do
    for m in $SWEEP; do
      RUN_N=$((RUN_N + 1))
      log ">>> RUN [$RUN_N]  method=$m  traj=$t  scene=$SWEEP_SCENE  (sweep)"
      if $RUN adapters/run.py --method "$m" --config config.yaml \
             --scenes "$SWEEP_SCENE" --traj "$t"; then
        RUN_OK=$((RUN_OK + 1)); note "ok   $t  $m (sweep)"
      else
        RUN_FAIL=$((RUN_FAIL + 1)); note "FAIL $t  $m (sweep)"
        log "!!! FAILED sweep method=$m traj=$t — continuing"
      fi
    done
  done
  checkpoint P5-sweep
else
  log "### Phase 5: no sweep arms configured — skipping"
fi

# ── Stage 3: standardized snapshots, all co-visibility mask variants ────────
log "### Stage 3: snapshots (primary trajectories; full/covis/masked variants)"
SNAP_M="$(echo $CORE $ALIGN | tr ' ' '\n' | grep -v '^$' | tr '\n' ' ')"
SNAP_T=$([ "$NSEEDS" -le 1 ] \
  && echo "synthetic_2.0hz loop_2.0hz stopgo_2.0hz" \
  || echo "synthetic_2.0hz_s0 loop_2.0hz_s0 stopgo_2.0hz_s0")
make snapshots SNAP_METHODS="$SNAP_M" SNAP_SCENES="" SNAP_TRAJ="$SNAP_T" || true

rm -f "$PLAN_SH"
log "############ DONE  stamp=$STAMP ############"
log "### $RUN_N runs dispatched: $RUN_OK ok, $RUN_FAIL failed"
note "done $STAMP  ($RUN_N runs: $RUN_OK ok / $RUN_FAIL failed)"
[ "$RUN_N" -eq 0 ] && log "!!!!!! WARNING: ZERO runs were dispatched. The report below is NOT from this session."
if [ "${EVAL_FAIL:-0}" -gt 0 ]; then
  log "!!!!!! WARNING: $EVAL_FAIL eval step(s) FAILED during this session."
  log "!!!!!!   The tables below are computed over whatever those steps managed to"
  log "!!!!!!   reach before dying — methods will have UNEQUAL N and the per-method"
  log "!!!!!!   means are NOT like-for-like. Grep this log for 'EVAL STEP FAILED'."
fi
echo
echo "Runs         : $RUN_N dispatched ($RUN_OK ok / $RUN_FAIL failed)"
[ "${EVAL_FAIL:-0}" -gt 0 ] && echo "Eval steps   : $EVAL_FAIL FAILED  <- tables are incomplete, see log"
echo "Clean report : results/report_clean/clean_report.md   <- cite this one"
echo "Report tables: results/report_tables/                 <- for uofa-2026-report"
echo "Completion   : results/report_clean/completion.csv    <- read before any mean"
echo "Snapshots    : results/report/snapshots/"
echo "Full log     : $LOG"

#!/usr/bin/env bash
# rerun-v3 PILOT: test the new (grid-planner) trajectories on a small dense render,
# and pick the capture rate and PRISM window, before re-rendering the full matrix.
# Config: config.pilot.yaml (overlay). Inputs/results live under the tag pilot-v3.
#
#   PC  (WSL):  bash scripts/pilot.sh inputs   # audit gate -> render 10 Hz -> derive 5/2 Hz -> export -> pack
#               bash scripts/pilot.sh push     # upload to HF inputs/pilot-v3/
#   pod:        bash scripts/pilot.sh pod      # prep (if needed) -> fetch -> runs -> report -> HF
#               PILOT_PHASES="A C" bash scripts/pilot.sh pod   # choose phases (default "A C B")
#   any:        bash scripts/pilot.sh report   # summary table from results/p3_*
#   PC  (WSL):  bash scripts/pilot.sh fetch    # download + merge the pod's results pack
#
# Phases (each run is skipped if already finished; HF checkpoint after every phase):
#   A  p3_prism, p3_vggtslam, p3_laser at 10 / 5 / 2 Hz, every pilot scene      (27 runs)
#   C  PRISM window sweep w24o8 w32o8 w32o16 w48o16 w64o16 at 10 Hz,
#      + w24o8 w32o8 at 5 Hz                                                     (21 runs)
#   B  p3_vggtslam_kf50 (50 px keyframing) + p3_laser_w20o5 at 10 Hz             ( 6 runs)
# Rough cost on the RTX 5090: A ~1 h, C ~50 min, B ~20 min (+ prep on a fresh pod).
set -euo pipefail
cd "$(dirname "$0")/.."
[ -f .pod.env ] && { set -a; . ./.pod.env; set +a; }
_benv() { sed -n "s/^$1[[:space:]]*[?:]*=[[:space:]]*//p" bench.env 2>/dev/null | head -1; }
export PRISM_CONFIG_OVERLAY=config.pilot.yaml
export INPUTS_TAG="${PILOT_TAG:-pilot-v3}"
export RESULTS_TAG="$INPUTS_TAG"
export INPUTS_HF_REPO="${INPUTS_HF_REPO:-$(_benv INPUTS_HF_REPO)}"
export PATH="$HOME/.local/bin:$PATH"
RUN="${RUN:-uv run python}"
mkdir -p logs
LOG="logs/pilot_$(date +%Y%m%d_%H%M%S)_${1:-help}.log"
exec > >(tee -a "$LOG") 2>&1
say() { echo; echo "[$(date +%H:%M:%S)] ===== $* ====="; echo "$(date +%H:%M) pilot: $*" > logs/pod_stage; }

ARMS_A="p3_prism p3_vggtslam p3_laser"
ARMS_B="p3_vggtslam_kf50 p3_laser_w20o5"
ARMS_C10="p3_prism_w24o8 p3_prism_w32o8 p3_prism_w32o16 p3_prism_w48o16 p3_prism_w64o16"
ARMS_C5="p3_prism_w24o8 p3_prism_w32o8"
export BENCH_METHODS="$ARMS_A $ARMS_B $ARMS_C10"
SCENES="$($RUN -c "from bench.config import load_config; c=load_config('config.yaml'); print(' '.join(c['datasets'][c['datasets']['active'][0]]['scenes']))")"

run_arm() {   # run_arm <arm> <traj>  (all pilot scenes)
  local arm="$1" traj="$2" sc
  for sc in $SCENES; do
    $RUN adapters/run.py --method "$arm" --config config.yaml --scenes "$sc" --traj "$traj" \
      || echo "!! $arm $sc $traj failed (recorded in its perf.json; continuing)"
  done
}
checkpoint() {
  if [ -n "${INPUTS_HF_REPO:-}" ] && [ -n "${HF_TOKEN:-}" ]; then
    bash scripts/results.sh sync-up || echo "!! HF checkpoint failed (results are still on disk)"
  fi
}

case "${1:-}" in
inputs)
  say "audit: generated trajectories vs the mesh (no rendering)"
  $RUN scripts/traj_audit.py --generate --traj all --plot
  say "check-scenes (pre-flight: every trajectory buildable and collision-free)"
  $RUN dataset/check_scenes.py --config config.yaml
  say "render 10 Hz + derive 5 / 2 Hz: $SCENES"
  $RUN dataset/render_scene.py --config config.yaml --traj all
  say "export adapter inputs"
  $RUN dataset/export_inputs.py --config config.yaml --traj all
  say "audit: rendered GT poses (exact rendered geometry)"
  $RUN scripts/traj_audit.py --traj all --plot
  say "pack -> dataset/inputs/$INPUTS_TAG/"
  bash scripts/inputs.sh pack
  echo ">> next: bash scripts/pilot.sh push" ;;
push)
  bash scripts/inputs.sh push ;;
pod)
  if [ ! -f logs/.done_prep ]; then bash scripts/pod.sh prep && touch logs/.done_prep; fi
  if [ ! -f logs/.done_check ]; then bash scripts/pod.sh check && touch logs/.done_check; fi
  say "data: fetch inputs/$INPUTS_TAG"
  bash scripts/inputs.sh fetch
  say "resume: pull the pilot checkpoint, if any"
  bash scripts/results.sh sync-down || true
  for ph in ${PILOT_PHASES:-A C B}; do
    case "$ph" in
      A) say "phase A: defaults at 10 / 5 / 2 Hz"
         for tj in synthetic_10.0hz synthetic_5.0hz synthetic_2.0hz; do
           for a in $ARMS_A; do run_arm "$a" "$tj"; done
         done ;;
      C) say "phase C: PRISM window sweep"
         for a in $ARMS_C10; do run_arm "$a" synthetic_10.0hz; done
         for a in $ARMS_C5; do run_arm "$a" synthetic_5.0hz; done ;;
      B) say "phase B: baselines in their published settings (10 Hz)"
         for a in $ARMS_B; do run_arm "$a" synthetic_10.0hz; done ;;
      *) echo "!! unknown phase $ph" ;;
    esac
    checkpoint
    $RUN scripts/pilot_report.py || true
  done
  say "pack + upload"
  bash scripts/results.sh pack
  if [ -n "${INPUTS_HF_REPO:-}" ] && [ -n "${HF_TOKEN:-}" ]; then bash scripts/results.sh push || true; fi
  $RUN scripts/pilot_report.py || true
  say "pilot DONE" ;;
report)
  $RUN scripts/pilot_report.py ;;
fetch)
  bash scripts/results.sh fetch
  bash scripts/results.sh merge
  $RUN scripts/pilot_report.py ;;
*)
  sed -n '2,20p' "$0"; exit 1 ;;
esac

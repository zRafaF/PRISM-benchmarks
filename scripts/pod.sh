#!/usr/bin/env bash
# ============================================================================
# pod.sh — ONE fresh GPU pod from zero to downloadable results, unattended.
#
#   make pod            # = bash scripts/pod.sh all, detached in tmux session 'pod'
#   make pod-status     # which stage, progress, last log lines
#
# Every run is SEQUENTIAL on the one GPU, so all timing/VRAM numbers are clean.
#
# Stages (each can be re-run alone:  bash scripts/pod.sh <stage>):
#   prep      apt packages, uv, pinned submodules (bench.env), every method env, weights
#   check     env-check: GPU, CUDA in every env, prism-v2 engine, nvblox FUSES a frame,
#             VGGT-SLAM reproduces its own office_loop loop closure. If ONLY nvblox
#             fails, PRISM's env is rebuilt with nvblox from source and re-checked.
#   data      THE DATASET. Rendered on your PC and uploaded (recommended):
#               INPUTS_HF_REPO set          -> download + unpack the pre-rendered frames
#               tars in dataset/inputs/<tag> -> unpack them (you copied them by hand)
#             otherwise renders here: Replica -> split -> check -> render -> export
#   precheck  every method on ONE real sequence + validation table + full-run ETA.
#             The benchmark does not start unless every method PASSES.
#   bench     the method matrix (no scoring on the GPU box)
#   capacity  OPTIONAL (POD_CAPACITY=1): VRAM-vs-length prefix sweep for Fig. vram
#   eval      OPTIONAL (POD_EVAL=1): score on this pod's CPU (else score locally)
#   pack      raw results + scoring inputs + logs -> results/bundles/pod_*.tar
#   studio    Gradio Studio with a public link; Download tab lists the pack
#   all       prep check data precheck bench [capacity] [eval] pack studio
#
# Env: POD_CAPACITY=1, POD_EVAL=1, POD_STUDIO=0, RESULTS_HF_REPO + HF_TOKEN (auto-upload),
#      SHARD=k/N (only if you ever split across pods).
# ============================================================================
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p logs
STAMP="$(date +%Y%m%d_%H%M%S)"
LOG="logs/pod_${STAMP}.log"
ln -sf "pod_${STAMP}.log" logs/pod_latest.log
exec > >(tee -a "$LOG") 2>&1
export PATH="$HOME/.local/bin:$PATH"

say() { echo; echo "[$(date +%H:%M:%S)] ===== $* ====="; echo "$(date +%H:%M) $*" > logs/pod_stage; }

stage_prep() {
  say "prep: system packages"
  if command -v apt-get >/dev/null 2>&1; then
    SUDO=""; [ "$(id -u)" -ne 0 ] && SUDO="sudo"
    $SUDO apt-get update -qq
    $SUDO apt-get install -y -qq wget pigz unzip tmux git curl zstd lsb-release \
        build-essential cmake git-lfs python3-dev >/dev/null
  fi
  command -v uv >/dev/null 2>&1 || curl -LsSf https://astral.sh/uv/install.sh | sh
  say "prep: pinned submodules (bench.env: PRISM-VGGT @ prism-v2, baselines @ commits)"
  make init
  say "prep: orchestrator env"
  make setup
  for m in prism vggtslam laser pi3 mapanything; do
    say "prep: setup-$m"
    make "setup-$m"
  done
}

stage_check() {
  if [ "${POD_SKIP_CHECK:-0}" = "1" ]; then say "check: SKIPPED (POD_SKIP_CHECK=1)"; return; fi
  say "check: env-check"
  if bash scripts/env_check.sh; then return; fi
  # Only the nvblox fusion failed? -> rebuild PRISM's nvblox from source, re-check.
  local fails
  fails=$(python3 -c "import json;d=json.load(open('logs/env/env_check.json'));print(' '.join(c['check'] for c in d['checks'] if c['status']=='FAIL'))")
  if [ "$fails" = "nvblox_integrate" ]; then
    say "check: prebuilt nvblox wheel failed on this GPU -> building nvblox from source (~15-25 min)"
    NVBLOX_MODE=source make setup-prism
    bash scripts/env_check.sh
  else
    echo "!! env-check failed: $fails — fix before spending GPU time (see logs/env/)"; exit 1
  fi
}

stage_data() {
  local tag="${INPUTS_TAG:-rerun-v2}"
  if [ -n "${INPUTS_HF_REPO:-}" ]; then
    say "data: download the frames rendered on your PC ($INPUTS_HF_REPO, $tag)"
    bash scripts/inputs.sh fetch
    touch logs/.data_ready; return
  fi
  if ls "dataset/inputs/$tag"/*.tar >/dev/null 2>&1; then
    say "data: unpack the frames you copied into dataset/inputs/$tag"
    bash scripts/inputs.sh unpack
    touch logs/.data_ready; return
  fi
  say "data: no pre-rendered inputs -> rendering on this pod. Download Replica (no approval)"
  make replica
  say "data: freeze the scene split (6 scenes, fixed seed) -> config.local.yaml"
  make split
  say "data: pre-flight — every scene x trajectory buildable (no rendering)"
  make check-scenes
  say "data: render pano + pinhole + ground truth, then export method inputs"
  make render SCENES="${BENCH_SCENES:-}" TRAJ=all
  make export SCENES="${BENCH_SCENES:-}" TRAJ=all
  bash scripts/inputs.sh verify
  touch logs/.data_ready
}

stage_precheck() {
  [ -f logs/.data_ready ] || { echo "!! run the data stage first"; exit 1; }
  say "precheck: every method on one real sequence (results are kept and reused)"
  make precheck
}

stage_bench() {
  [ -f logs/.data_ready ] || { echo "!! run the data stage first"; exit 1; }
  say "bench: method matrix, sequential on one GPU (SKIP_EVAL=1, SKIP_RENDER=1)"
  SKIP_EVAL=1 SKIP_RENDER=1 bash scripts/run_overnight.sh
}

stage_capacity() {
  say "capacity: VRAM-vs-length prefix sweep (Fig. vram)"
  make capacity-sweep || echo "!! capacity sweep failed — continuing"
}

stage_eval() {
  say "eval: scoring on this pod's CPU"
  make eval-all publication
}

stage_pack() {
  say "pack: raw results + scoring inputs for offline scoring"
  bash scripts/results.sh pack
  if [ -n "${RESULTS_HF_REPO:-}" ]; then
    bash scripts/results.sh push || echo "!! push failed — download the pack from Studio instead"
  fi
}

stage_studio() {
  if [ "${POD_STUDIO:-1}" = "0" ]; then say "studio: not started (POD_STUDIO=0)"; return; fi
  say "studio: public Gradio link below; Download tab lists results/bundles/pod_*.tar"
  make studio
}

case "${1:-all}" in
  prep)     stage_prep ;;
  check)    stage_check ;;
  data)     stage_data ;;
  precheck) stage_precheck ;;
  bench)    stage_bench ;;
  capacity) stage_capacity ;;
  eval)     stage_eval ;;
  pack)     stage_pack ;;
  studio)   stage_studio ;;
  all)
    stage_prep; stage_check; stage_data; stage_precheck; stage_bench
    [ "${POD_CAPACITY:-0}" = "1" ] && stage_capacity
    [ "${POD_EVAL:-0}" = "1" ] && stage_eval
    stage_pack; say "DONE"; stage_studio ;;
  *) sed -n '2,26p' "$0"; exit 1 ;;
esac

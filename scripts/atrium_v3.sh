#!/usr/bin/env bash
# atrium-v3 (decisions D36): PRISM with an 8 m TSDF range + LASER fused through the same
# TSDF, on the real 360Loc atrium mapping walk. Config: config.real360.yaml +
# config.atrium_v3.yaml. Installs ONLY the PRISM-VGGT and LASER envs.
#
#   pod:        make atrium3-pod     # prep -> GPU check -> 2 runs -> LASER TSDF -> pack -> HF
#               make atrium3-watch   # progress (Ctrl-C leaves; the run continues)
#   PC  (WSL):  make atrium3-fetch   # download + merge + score (map scores at 10 m for every atrium run)
set -euo pipefail
cd "$(dirname "$0")/.."
[ -f .pod.env ] && { set -a; . ./.pod.env; set +a; }
_benv() { sed -n "s/^$1[[:space:]]*[?:]*=[[:space:]]*//p" bench.env 2>/dev/null | head -1; }
export PRISM_CONFIG_OVERLAY=config.real360.yaml,config.atrium_v3.yaml
export INPUTS_TAG="${REAL_INPUTS_TAG:-real360-v1}"      # the atrium mapping walk, unchanged
export RESULTS_TAG="${ATRIUM3_TAG:-atrium-v3}"
export RESULTS_DATASET=loc360
export INPUTS_HF_REPO="${REAL_HF_REPO:-${INPUTS_HF_REPO:-$(_benv INPUTS_HF_REPO)}}"
export PATH="$HOME/.local/bin:$PATH"
RUN="${RUN:-uv run python}"
mkdir -p logs
LOGF="atrium3_$(date +%Y%m%d_%H%M%S)_${1:-help}.log"
exec > >(tee -a "logs/$LOGF") 2>&1
CMD="${1:-}"
[ "$CMD" = pod ] && ln -sf "$LOGF" logs/pod_latest.log || true
say() { echo; echo "[$(date +%H:%M:%S)] ===== $* ====="; [ "$CMD" = pod ] && echo "$(date +%H:%M) atrium3: $*" > logs/pod_stage || true; }

case "$CMD" in
pod)
  if [ ! -f logs/.done_prep_atrium3 ]; then
    say "prep: system packages + uv"
    apt-get update -qq && apt-get install -y -qq wget pigz unzip tmux git curl zstd lsb-release \
        build-essential cmake git-lfs python3-dev bc libegl1 libgl1 libgomp1 libglib2.0-0 >/dev/null
    command -v uv >/dev/null 2>&1 || curl -LsSf https://astral.sh/uv/install.sh | sh
    say "prep: PRISM-VGGT + LASER only, pinned in bench.env"
    ONLY="PRISM-VGGT LASER" bash scripts/add_submodules.sh
    make setup
    make setup-prism
    make setup-laser
    touch logs/.done_prep_atrium3
  fi
  say "check: GPU visible in both envs"
  for env in PRISM-VGGT LASER; do
    submodules/$env/.venv/bin/python -c "import torch; assert torch.cuda.is_available(); p=torch.cuda.get_device_properties(0); print('[check]', p.name, round(p.total_memory/2**30), 'GiB'); torch.ones(1, device='cuda').sum().item()" \
      || { echo "!! no CUDA in the $env env (broken GPU host?): start a new pod"; exit 1; }
  done
  mkdir -p results && echo "$RESULTS_TAG" > results/.tag
  say "data: fetch inputs/$INPUTS_TAG"
  bash scripts/inputs.sh fetch
  export BENCH_METHODS="prism_r8 laser"
  for a in prism_r8 laser; do
    say "run $a on atrium/ref"
    $RUN adapters/run.py --method "$a" --config config.yaml --scenes atrium --traj ref || echo "!! $a failed (see its run.log)"
  done
  say "LASER through prism_r8's TSDF (voxel 6 cm, range 8 m) -> results/laser_tsdf"
  for rd in results/laser/loc360/atrium/ref/*/; do
    [ -d "$rd/_depth" ] && FUSE_LIKE=prism_r8 $RUN eval/fuse_tsdf.py --config config.yaml --run "$rd" || echo "!! fuse_tsdf: no depth in $rd"
  done
  for f in results/*/loc360/atrium/ref/*/perf.json; do
    $RUN -c "import json; d=json.load(open('$f')); print('$f', 'ok' if d.get('completed') else d.get('failure_kind'), 'VRAM', d.get('vram_peak_gb'))" || true
  done
  say "pack + upload (results/$RESULTS_TAG)"
  bash scripts/results.sh pack
  if [ -n "${INPUTS_HF_REPO:-}" ] && [ -n "${HF_TOKEN:-}" ]; then
    bash scripts/results.sh push || echo "!! push failed: rerun RESULTS_TAG=$RESULTS_TAG bash scripts/results.sh push"
  else
    echo "!! HF_TOKEN not set: read -s HF_TOKEN; export HF_TOKEN; RESULTS_TAG=$RESULTS_TAG bash scripts/results.sh push"
  fi
  say "atrium3 DONE" ;;
fetch)
  bash scripts/results.sh fetch
  NEWEST="$(ls dataset/_hf/results/"$RESULTS_TAG"/*.tar | awk -F_ '{print $(NF-1) $NF, $0}' | sort | tail -1 | cut -d' ' -f2)"
  echo ">> merging the newest pack: $NEWEST (adds prism_r8, laser_tsdf; replaces results/laser/loc360/atrium)"
  MERGE_OVERWRITE=1 bash scripts/results.sh merge "$NEWEST"
  say "score: trajectory, metric scale, perf; map scores at 10 m for EVERY atrium run"
  $RUN eval/eval_traj.py --config config.yaml
  $RUN eval/metric_accuracy.py --config config.yaml || true
  $RUN eval/collect_perf.py --config config.yaml || true
  $RUN eval/map_metrics.py --config config.yaml --glob 'results/*/loc360/atrium/ref/*' --force
  $RUN scripts/real360_report.py || true
  for a in prism prism_r8 laser laser_tsdf vggtslam panovggt; do
    for j in results/$a/loc360/atrium/ref/*/map.json; do
      [ -f "$j" ] && $RUN -c "import json; d=json.load(open('$j')); m=d['map']; l=d.get('local') or {}; print('%-11s acc %.2f m  local %.2f m  ghost@20 %.2f' % ('$a', m['acc_median_m'], l.get('acc_median_of_tiles_m', float('nan')), l.get('ghost@0.2', float('nan'))))"
    done
  done ;;
*)
  sed -n '2,8p' "$0"; exit 1 ;;
esac

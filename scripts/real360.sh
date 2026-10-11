#!/usr/bin/env bash
# Real 360 deg data (360Loc, decisions D31): import -> pack -> quick check on a pod.
# Config: config.real360.yaml (overlay). Tag: real360-v1 (inputs and results), separate
# from the Replica matrix — nothing here changes or re-runs the synthetic benchmark.
#
#   PC  (WSL):  bash scripts/real360.sh download   # scenes in the overlay, from the authors' links
#               bash scripts/real360.sh list       # sequences found in each scene
#               bash scripts/real360.sh inputs     # import -> export -> pack
#               bash scripts/real360.sh push       # HF inputs/real360-v1/
#   pod:        bash scripts/real360.sh pod        # prep (if needed) -> fetch -> 5 arms -> report -> HF
#   PC  (WSL):  bash scripts/real360.sh fetch      # merge the pod's pack, print the table
#   any:        bash scripts/real360.sh report
set -euo pipefail
cd "$(dirname "$0")/.."
[ -f .pod.env ] && { set -a; . ./.pod.env; set +a; }
_benv() { sed -n "s/^$1[[:space:]]*[?:]*=[[:space:]]*//p" bench.env 2>/dev/null | head -1; }
export PRISM_CONFIG_OVERLAY=config.real360.yaml
export INPUTS_TAG="${REAL_TAG:-real360-v1}"
export RESULTS_TAG="$INPUTS_TAG"
export RESULTS_DATASET=loc360
# 360Loc states no licence, so its imported frames can go to a separate (e.g. private) HF
# repo: REAL_HF_REPO=<user>/<repo>. Default: the main dataset repo.
export INPUTS_HF_REPO="${REAL_HF_REPO:-${INPUTS_HF_REPO:-$(_benv INPUTS_HF_REPO)}}"
export PATH="$HOME/.local/bin:$PATH"
RUN="${RUN:-uv run python}"
mkdir -p logs
LOGF="real360_$(date +%Y%m%d_%H%M%S)_${1:-help}.log"
exec > >(tee -a "logs/$LOGF") 2>&1
# `pod`: feed `make real-watch` (scripts/progress.py reads logs/pod_stage + pod_latest.log)
podlog() { [ "${1:-}" = pod ] && ln -sf "$LOGF" logs/pod_latest.log || true; }
podlog "${1:-}"
say() { echo; echo "[$(date +%H:%M:%S)] ===== $* ====="; [ "${CMD:-}" = pod ] && echo "$(date +%H:%M) real360: $*" > logs/pod_stage || true; }
CMD="${1:-}"
cfgq() { $RUN -c "from bench.config import load_config; c=load_config('config.yaml'); $1"; }

ARMS="$(cfgq "print(' '.join(m['name'] for m in c['methods']))")"
SCENES="$(cfgq "d=c['datasets'][c['datasets']['active'][0]]; print(' '.join(d['scenes']))")"
TRAJS="$(cfgq "from bench.config import resolve_trajs; print(' '.join(resolve_trajs(c,'all')))")"
export BENCH_METHODS="$ARMS"

# 360Loc scene zips. Primary: the authors' file server (direct links, sizes in bytes:
# atrium 7.9 GB, concourse 4.4 GB, hall 7.1 GB, piatrium 7.1 GB). Fallback: the SharePoint
# links in the 360Loc repo's onekey.py (these now return an HTML page instead of the zip).
declare -A URL=(
  [atrium]="https://hkustvgd.com/statics/360loc/atrium.zip"
  [concourse]="https://hkustvgd.com/statics/360loc/concourse.zip"
  [hall]="https://hkustvgd.com/statics/360loc/hall.zip"
  [piatrium]="https://hkustvgd.com/statics/360loc/piatrium.zip"
)
RAW=dataset/raw/360loc

case "${1:-}" in
download)
  mkdir -p "$RAW"
  for sc in $SCENES; do
    if [ -d "$RAW/$sc" ]; then echo ">> $sc: present"; continue; fi
    z="$RAW/$sc.zip"
    # A previous attempt may have saved an HTML page as the zip: never resume onto it.
    if [ -f "$z" ] && [ "$(head -c 2 "$z")" != "PK" ]; then echo ">> $z is not a zip (HTML page?) — removing"; rm -f "$z"; fi
    say "download $sc (360Loc, authors' server)"
    wget -c --progress=dot:giga "${URL[$sc]}" -O "$z"
    [ "$(head -c 2 "$z")" = "PK" ] || { echo "!! $z is not a zip (got: $(file -b "$z" 2>/dev/null))"; rm -f "$z"; exit 1; }
    unzip -q "$z" -d "$RAW" && rm -f "$z"
  done
  echo ">> if a link fails, get the zip from https://hkustvgd.com/statics/360loc/ by hand and unzip it into $RAW/" ;;
list)
  $RUN dataset/import_360loc.py --list ;;
inputs)
  say "import 360Loc: $SCENES / $TRAJS"
  $RUN dataset/import_360loc.py --workers "${IMPORT_WORKERS:-4}"
  say "export adapter inputs"
  $RUN dataset/export_inputs.py --config config.yaml --traj all
  say "pack -> dataset/inputs/$INPUTS_TAG/"
  bash scripts/inputs.sh pack
  echo ">> next: bash scripts/real360.sh push" ;;
push)
  bash scripts/inputs.sh push ;;
pod)
  say "prep: system packages, method envs, model weights (30-60 min on a fresh pod)"
  if [ ! -f logs/.done_prep ]; then bash scripts/pod.sh prep && touch logs/.done_prep; fi
  podlog pod
  say "check: GPU in every method env"
  if [ ! -f logs/.done_check ]; then
    bash scripts/pod.sh check || { echo "!! env check FAILED — not running anything (see logs/env/). A pod whose every env reports 'no CUDA' / CUDA error 999 has a broken GPU host: start a new pod."; exit 1; }
    touch logs/.done_check
  fi
  podlog pod
  say "data: fetch inputs/$INPUTS_TAG"
  bash scripts/inputs.sh fetch
  say "runs: $ARMS on $SCENES / $TRAJS (finished runs are skipped)"
  for tj in $TRAJS; do
    for a in $ARMS; do
      for sc in $SCENES; do
        say "run $a on $sc/$tj"
        $RUN adapters/run.py --method "$a" --config config.yaml --scenes "$sc" --traj "$tj" \
          || echo "!! $a $sc $tj failed (see its run.log; continuing)"
      done
    done
    $RUN scripts/real360_report.py || true
  done
  say "pack + upload (results/$RESULTS_TAG, loc360 runs only)"
  bash scripts/results.sh pack
  if [ -n "${INPUTS_HF_REPO:-}" ] && [ -n "${HF_TOKEN:-}" ]; then bash scripts/results.sh push || true; fi
  $RUN scripts/real360_report.py || true
  say "real360 DONE" ;;
fetch)
  bash scripts/results.sh fetch
  bash scripts/results.sh merge
  say "reconstruction scores vs the GT map (needs this PC's exports: gt_cloud.ply, pinhole depth)"
  $RUN eval/eval_recon.py --config config.yaml || echo "!! eval_recon failed — trajectory metrics below are still valid"
  $RUN scripts/real360_report.py ;;
report)
  $RUN scripts/real360_report.py ;;
*)
  sed -n '2,13p' "$0"; exit 1 ;;
esac

#!/usr/bin/env bash
# OFFLINE references (decisions D33/D34): PanoVGGT (360) and Pi3 (pinhole), full batch,
# one run per scene (Replica seed 0) + the real 360Loc atrium. Config: config.offline.yaml
# (overlay; + config.real360.yaml for the atrium pass). Installs ONLY the PRISM-VGGT and
# Pi3 envs (nvblox is not used by these runners). Full length first; a sequence that
# does not fit in memory is recorded and rerun subsampled (OFFLINE_FALLBACK_FRAMES=200).
#
#   pod:        make offline-pod     # prep -> GPU check -> Replica 12 runs -> atrium 2 runs -> pack -> HF
#               make offline-watch   # progress (Ctrl-C leaves; the run continues)
#   PC  (WSL):  make offline-fetch   # download + merge (results/panovggt/...) + score + table
set -euo pipefail
cd "$(dirname "$0")/.."
[ -f .pod.env ] && { set -a; . ./.pod.env; set +a; }
_benv() { sed -n "s/^$1[[:space:]]*[?:]*=[[:space:]]*//p" bench.env 2>/dev/null | head -1; }
export PRISM_CONFIG_OVERLAY=config.offline.yaml
export INPUTS_TAG="${INPUTS_TAG:-$(_benv INPUTS_TAG)}"          # rerun-v3: the same frames
export RESULTS_TAG="${OFFLINE_TAG:-offline-v3}"                  # own pack on HF, never mixed
export RESULTS_DATASET=replica
export INPUTS_HF_REPO="${INPUTS_HF_REPO:-$(_benv INPUTS_HF_REPO)}"
export PATH="$HOME/.local/bin:$PATH"
RUN="${RUN:-uv run python}"
mkdir -p logs
LOGF="offline_$(date +%Y%m%d_%H%M%S)_${1:-help}.log"
exec > >(tee -a "logs/$LOGF") 2>&1
CMD="${1:-}"
podlog() { [ "$CMD" = pod ] && ln -sf "$LOGF" logs/pod_latest.log || true; }
podlog
say() { echo; echo "[$(date +%H:%M:%S)] ===== $* ====="; [ "$CMD" = pod ] && echo "$(date +%H:%M) offline: $*" > logs/pod_stage || true; }
cfgq() { $RUN -c "from bench.config import load_config; c=load_config('config.yaml'); $1"; }

case "$CMD" in
pod)
  if [ ! -f logs/.done_prep_offline ]; then
    say "prep: system packages + uv"
    apt-get update -qq && apt-get install -y -qq wget pigz unzip tmux git curl zstd lsb-release \
        build-essential cmake git-lfs python3-dev bc libegl1 libgl1 libgomp1 libglib2.0-0 >/dev/null
    command -v uv >/dev/null 2>&1 || curl -LsSf https://astral.sh/uv/install.sh | sh
    say "prep: PRISM-VGGT (PanoVGGT inside) + Pi3 only, pinned in bench.env"
    ONLY="PRISM-VGGT Pi3" bash scripts/add_submodules.sh
    say "prep: orchestrator env"
    make setup
    say "prep: PRISM-VGGT env + PanoVGGT weights (prebuilt nvblox wheel, no compile)"
    make setup-prism
    say "prep: Pi3 env"
    make setup-pi3
    touch logs/.done_prep_offline
  fi
  podlog
  say "check: GPU visible in both envs"
  for env in PRISM-VGGT Pi3; do
    submodules/$env/.venv/bin/python - <<'PY' || { echo "!! no CUDA in the $env env — broken GPU host or driver older than CUDA 12.8: start a new pod"; exit 1; }
import torch
assert torch.cuda.is_available(), "no CUDA"
p = torch.cuda.get_device_properties(0)
print(f"[check] {p.name}, {p.total_memory/2**30:.0f} GiB, torch {torch.__version__}, CUDA {torch.version.cuda}")
torch.ones(1, device="cuda").sum().item()
PY
  done
  mkdir -p results logs/offline_oom && echo "$RESULTS_TAG" > results/.tag
  FB="${OFFLINE_FALLBACK_FRAMES:-200}"

  # One run; if the FULL sequence does not fit (OOM / host-RAM kill), record that and
  # rerun it uniformly subsampled to $FB frames, marked in arm_config.json.
  run_one() {  # arm scene traj
    local a="$1" sc="$2" tj="$3"
    say "run $a on $sc/$tj (full length)"
    $RUN adapters/run.py --method "$a" --config config.yaml --scenes "$sc" --traj "$tj" || true
    local pj; pj=$(ls results/"$a"/*/"$sc"/"$tj"/*/perf.json 2>/dev/null | head -1)
    [ -n "$pj" ] || { echo "!! $a $sc $tj: no perf.json"; return; }
    if $RUN -c "import json,sys; d=json.load(open('$pj')); sys.exit(0 if d.get('completed') else 1)"; then return; fi
    local kind; kind=$($RUN -c "import json; print(json.load(open('$pj')).get('failure_kind'))")
    local rd; rd=$(dirname "$pj")
    cp "$pj" "logs/offline_oom/${a}_${sc}_${tj}_full_perf.json"; cp "$rd/run.log" "logs/offline_oom/${a}_${sc}_${tj}_full_run.log" 2>/dev/null || true
    if [ "$kind" != "oom" ] && [ "$kind" != "killed" ]; then echo "!! $a $sc $tj failed ($kind) — not a memory limit, kept as a failure"; return; fi
    say "run $a on $sc/$tj: full length did not fit ($kind) -> rerun subsampled to $FB frames"
    rm -rf "$rd"
    OFFLINE_MAX_FRAMES="$FB" $RUN adapters/run.py --method "$a" --config config.yaml --scenes "$sc" --traj "$tj" || true
    [ -f "$rd/perf.json" ] && $RUN - "$rd" "$FB" "$kind" <<'PY'
import json, sys
from pathlib import Path
rd, fb, kind = Path(sys.argv[1]), int(sys.argv[2]), sys.argv[3]
ac = rd / "arm_config.json"
d = json.loads(ac.read_text()) if ac.exists() else {}
d.update({"full_length_oom": True, "full_length_failure": kind, "frames_used": fb})
ac.write_text(json.dumps(d, indent=2))
print(f"[offline] {rd}: marked full_length_oom, frames_used={fb}")
PY
  }

  pass() {  # overlay inputs_tag label
    export PRISM_CONFIG_OVERLAY="$1" INPUTS_TAG="$2"
    local ARMS SCENES TRAJS
    ARMS="$(cfgq "print(' '.join(m['name'] for m in c['methods']))")"
    SCENES="$(cfgq "d=c['datasets'][c['datasets']['active'][0]]; print(' '.join(d['scenes']))")"
    TRAJS="$(cfgq "from bench.config import resolve_trajs; from bench.matrix import offline_seed_ok
print(' '.join(t for t in resolve_trajs(c,'all') if offline_seed_ok(c, t)))")"
    export BENCH_METHODS="$ARMS"
    say "$3 — data: fetch inputs/$INPUTS_TAG"
    bash scripts/inputs.sh fetch
    # The Replica scene split is frozen in config.local.yaml, which arrives WITH the
    # inputs: read the scene list only now (offline-v3 read it before the fetch, got an
    # empty list and ran no Replica sequence).
    SCENES="$(cfgq "d=c['datasets'][c['datasets']['active'][0]]; print(' '.join(d['scenes']))")"
    [ -n "$SCENES" ] || { echo "!! $3: no scenes in the config — refusing to continue"; exit 1; }
    say "$3 — runs: $ARMS on $SCENES / $TRAJS"
    for tj in $TRAJS; do for sc in $SCENES; do for a in $ARMS; do run_one "$a" "$sc" "$tj"; done; done; done
  }
  pass "config.offline.yaml"                      "$(_benv INPUTS_TAG)" "Replica (rerun-v3)"
  pass "config.real360.yaml,config.offline.yaml"  "${REAL_TAG:-real360-v1}" "360Loc atrium (real)"

  say "pack + upload (results/$RESULTS_TAG: Replica + atrium offline runs)"
  unset RESULTS_DATASET
  bash scripts/results.sh pack
  if [ -n "${INPUTS_HF_REPO:-}" ] && [ -n "${HF_TOKEN:-}" ]; then
    bash scripts/results.sh push || echo "!! push failed — rerun: RESULTS_TAG=$RESULTS_TAG bash scripts/results.sh push"
  else
    echo "!! HF_TOKEN not set — push by hand: read -s HF_TOKEN; export HF_TOKEN; RESULTS_TAG=$RESULTS_TAG bash scripts/results.sh push"
  fi
  for f in results/*/*/*/*/*/perf.json; do
    $RUN -c "import json,pathlib;p=pathlib.Path('$f');d=json.load(open(p));a=p.parent/'arm_config.json';ac=json.load(open(a)) if a.exists() else {}
print(*p.parts[1:6], 'ok' if d.get('completed') else d.get('failure_kind'), 'VRAM', d.get('vram_peak_gb'), 'GB', ('subsampled to %s (full length: %s)'%(ac['frames_used'],ac['full_length_failure'])) if ac.get('full_length_oom') else 'full length')" || true
  done
  say "offline DONE" ;;
fetch)
  bash scripts/results.sh fetch
  bash scripts/results.sh merge
  say "score the new runs (trajectory + reconstruction; existing runs are skipped)"
  unset PRISM_CONFIG_OVERLAY RESULTS_DATASET
  $RUN eval/eval_traj.py --config config.yaml
  for a in panovggt pi3; do EVAL_GLOB="$a/replica/*/*" $RUN eval/eval_recon.py --config config.yaml || true; done
  $RUN eval/aggregate_clean.py --config config.yaml --source live || true
  echo; echo "== Replica (report_clean/aggregate_per_method.csv)"
  grep -iE "^Method|^panovggt|^pi3|^prism,|^laser,|^vggtslam," results/report_clean/aggregate_per_method.csv | cut -c1-200 || true
  echo; echo "== 360Loc atrium"
  for a in panovggt pi3; do PRISM_CONFIG_OVERLAY=config.real360.yaml EVAL_GLOB="$a/loc360/*/*/*" $RUN eval/eval_recon.py --config config.yaml || true; done
  PRISM_CONFIG_OVERLAY=config.real360.yaml $RUN scripts/real360_report.py || true
  grep -h "full_length_oom" results/{panovggt,pi3}/*/*/*/*/arm_config.json 2>/dev/null | head -1 >/dev/null && \
    echo ">> some runs were subsampled after a full-length OOM — see their arm_config.json (frames_used)" || true ;;
*)
  sed -n '2,8p' "$0"; exit 1 ;;
esac

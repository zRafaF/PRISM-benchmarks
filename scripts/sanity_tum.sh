#!/usr/bin/env bash
# VGGT-SLAM sanity check on its OWN benchmark (TUM RGB-D fr1), before trusting its
# numbers on our renders. Two runs on the same 9 sequences and the same settings as
# VGGT-SLAM's published evaluation (submap 32, min_disparity 50, loop closure on):
#
#   A. "theirs": VGGT-SLAM's own evals/eval_tum.sh, unmodified except for the dataset
#      path, scored with evo_ape -as (its own pipeline). Checks the INSTALL: our pinned
#      commit + env must reproduce the paper's TUM numbers.
#   B. "ours":   the same sequences converted to our input layout
#      (scripts/tum_to_export.py) and run through OUR runner
#      (adapters/runners/vggtslam_runner.py), scored with our Sim(3) ATE. Checks the
#      HARNESS: if A matches the paper and B matches A, the benchmark is not what makes
#      VGGT-SLAM fail on the Replica renders.
#
# Usage (pod, after `make setup-vggtslam`; ~3 GB download, ~30-40 min GPU):
#   bash scripts/sanity_tum.sh            # download + A + B + table
#   SANITY_SEQS="room desk" bash scripts/sanity_tum.sh     # subset (fr1_<name>)
#   SANITY_PARTS="B" bash scripts/sanity_tum.sh            # only one part
# Output: results/_sanity_tum/summary.csv (+ the per-run dirs). Not part of the matrix.
set -euo pipefail
cd "$(dirname "$0")/.."
ROOT="$(pwd)"
export PATH="$HOME/.local/bin:$PATH"
RUN="${RUN:-uv run python}"
VS="$ROOT/submodules/VGGT-SLAM"
PY="$VS/.venv/bin/python"
[ -x "$PY" ] || { echo "!! $PY missing — run 'make setup-vggtslam' first"; exit 1; }
TUM="$ROOT/dataset/raw/tum"
ALL="360 desk desk2 floor plant room rpy teddy xyz"
SEQS="${SANITY_SEQS:-$ALL}"
PARTS="${SANITY_PARTS:-A B}"
if [ "${1:-}" = "push" ]; then
  # Publish the check (summary, both pipelines' poses and logs, provenance) to the HF
  # dataset under sanity/tum_vggtslam/ — clouds excluded (large, not needed to verify).
  _benv() { sed -n "s/^$1[[:space:]]*[?:]*=[[:space:]]*//p" bench.env 2>/dev/null | head -1; }
  REPO="${INPUTS_HF_REPO:-$(_benv INPUTS_HF_REPO)}"
  [ -f results/_sanity_tum/summary.csv ] || { echo "!! no results/_sanity_tum/summary.csv — run make sanity-tum"; exit 1; }
  [ -f results/_sanity_tum/theirs_logs/rgbd_dataset_freiburg1_room_run1_w32.txt ] || \
    { mkdir -p results/_sanity_tum/theirs_logs; cp submodules/VGGT-SLAM/logs/rgbd_dataset_freiburg1_*_run1_w32.txt results/_sanity_tum/theirs_logs/ 2>/dev/null || true; }
  ${HF_CLI:-uvx --from 'huggingface_hub[cli]>=0.34' hf} upload "$REPO" results/_sanity_tum sanity/tum_vggtslam \
      --repo-type dataset --exclude "*.ply" "*.pcd" "*_points*" --commit-message "VGGT-SLAM TUM sanity check (D29)"
  exit 0
fi
OUT="$ROOT/results/_sanity_tum"
mkdir -p "$TUM" "$OUT" logs
exec > >(tee -a "logs/sanity_tum_$(date +%Y%m%d_%H%M%S).log") 2>&1

echo "== download TUM fr1 ($SEQS) — ~5 GB from cvg.cit.tum.de, all in parallel"
pids=()
for s in $SEQS; do
  d="rgbd_dataset_freiburg1_$s"
  [ -f "$TUM/$d/groundtruth.txt" ] && { echo "   $d: present"; continue; }
  ( wget -c -nv "https://cvg.cit.tum.de/rgbd/dataset/freiburg1/$d.tgz" -O "$TUM/$d.tgz" \
      && tar -xzf "$TUM/$d.tgz" -C "$TUM" && rm -f "$TUM/$d.tgz" && echo "   $d: done" ) &
  pids+=($!)
done
# progress while waiting: bytes downloaded so far
while [ -n "$(jobs -rp)" ]; do
  sleep 30; echo "   ... $(du -sh "$TUM" 2>/dev/null | cut -f1) downloaded/extracted"
done
for p in "${pids[@]+"${pids[@]}"}"; do wait "$p" || echo "!! a download failed — re-run (wget -c resumes)"; done

# evo_ape for VGGT-SLAM's own scorer, isolated from every method env.
SHIM="$ROOT/logs/.evo_shim"; mkdir -p "$SHIM"
printf '#!/bin/sh\nexec uvx --from evo evo_ape "$@"\n' > "$SHIM/evo_ape"; chmod +x "$SHIM/evo_ape"

if [[ " $PARTS " == *" A "* ]]; then
  echo "== A: VGGT-SLAM's evals/eval_tum.sh (its settings, its scorer)"
  SCRIPT="$ROOT/logs/.eval_tum_bench.sh"
  # Only the dataset paths and the sequence list change; everything else is upstream.
  sed -e "s#^dataset_path=.*#dataset_path=\"$TUM/\"#" -e "s#^gt_path=.*#gt_path=\"$TUM/\"#" \
      "$VS/evals/eval_tum.sh" > "$SCRIPT"
  python3 - "$SCRIPT" "$SEQS" <<'PY'
import re, sys
p, seqs = sys.argv[1], sys.argv[2].split()
s = open(p).read()
lst = "\n".join(f"    rgbd_dataset_freiburg1_{x}" for x in seqs)
s = re.sub(r"datasets=\(\n.*?\n\)", "datasets=(\n" + lst + "\n)", s, flags=re.S)
open(p, "w").write(s)
PY
  rm -f "$VS/logs/tum_results_w32.txt"
  ( cd "$VS" && PATH="$VS/.venv/bin:$SHIM:$PATH" bash "$SCRIPT" 32 )
  cp "$VS/logs/tum_results_w32.txt" "$OUT/theirs_tum_results_w32.csv"
  mkdir -p "$OUT/theirs_logs" && cp "$VS"/logs/rgbd_dataset_freiburg1_*_run1_w32.txt "$OUT/theirs_logs/" 2>/dev/null || true
fi

if [[ " $PARTS " == *" B "* ]]; then
  echo "== B: the same sequences through OUR runner"
  for s in $SEQS; do
    $RUN scripts/tum_to_export.py --seq "$TUM/rgbd_dataset_freiburg1_$s" --name "fr1_$s"
    in="$ROOT/dataset/exports/tum/fr1_$s/native/pinhole/synthetic_fov"
    o="$OUT/ours/fr1_$s"; rm -rf "$o"; mkdir -p "$o"
    ( cd "$VS" && VGGTSLAM_SUBMAP_SIZE=32 VGGTSLAM_MIN_DISPARITY=50 VGGTSLAM_MAX_LOOPS=1 \
        "$PY" "$ROOT/adapters/runners/vggtslam_runner.py" --in "$in" --out "$o" \
        --config "$ROOT/config.yaml" > "$o/run.log" 2>&1 ) || echo "!! fr1_$s failed (see $o/run.log)"
  done
fi

echo "== summary"
$RUN scripts/sanity_tum_eval.py --out "$OUT" --seqs "$SEQS"
{ echo "date: $(date -Is)"; echo "host: $(hostname)"
  echo "benchmarks: $(git rev-parse HEAD)$(git diff --quiet || echo ' DIRTY')"
  echo "VGGT-SLAM: $(git -C "$VS" rev-parse HEAD)"
  command -v nvidia-smi >/dev/null && nvidia-smi --query-gpu=name,driver_version --format=csv,noheader
} > "$OUT/provenance.txt"
echo ">> publish with: make sanity-tum-push"

#!/usr/bin/env bash
# ============================================================================
# results.sh — move a pod's raw results to wherever they are scored.
#
#   bash scripts/results.sh pack            # results/ + logs + provenance -> results/bundles/pod_*.tar
#   bash scripts/results.sh push            # upload that tar to RESULTS_HF_REPO (optional)
#   bash scripts/results.sh fetch           # (offline box) download every pod tar for RESULTS_TAG
#   bash scripts/results.sh merge F.tar...  # unpack pod tars into results/, refusing collisions
#   bash scripts/results.sh sync-up         # checkpoint: upload finished run dirs + logs to HF
#                                           #   (results/<tag>/live/), only new/changed files
#   bash scripts/results.sh sync-down       # resume: pull that checkpoint into results/
#   CONFIRM=yes bash scripts/results.sh hf-reset   # wipe results/<tag>/ on HF (before any pod)
#                                           #   (never overwrites) so finished runs are skipped
#
# Unlike `make bundle` (a report-oriented zip WITHOUT point clouds), a pod pack is the
# raw material for scoring: every run dir incl. cloud.ply, the run logs, the overnight
# log, the env freezes and env-check, and the exact commits of every submodule — PLUS
# the scoring half of this shard's exports (poses_gt.tum, pinhole depth + intrinsics,
# one gt_mesh.ply per scene; no rgb), so ANY CPU box can score the merged packs
# without Replica or a re-render. Shards
# write disjoint results/<method>/<ds>/<scene>/... trees, so merging is a copy; merge
# still refuses to overwrite an existing run dir unless MERGE_OVERWRITE=1.
#
# Env: RESULTS_TAG (default = INPUTS_TAG or rerun-v2), RESULTS_HF_REPO, HF_TOKEN, SHARD.
# ============================================================================
set -euo pipefail
cd "$(dirname "$0")/.."
TAG="${RESULTS_TAG:-${INPUTS_TAG:-rerun-v2}}"
REPO_ID="${RESULTS_HF_REPO:-${INPUTS_HF_REPO:-}}"
HF="${HF_CLI:-uvx --from huggingface_hub[cli]>=0.34 hf}"
OUTD=results/bundles
SHARD_ID="$(echo "${SHARD:-all}" | sed 's#/#of#')"

# This pod's methods (BENCH_METHODS) scope every upload/download/pack, so two pods
# never touch each other's files. Unset = every method under results/.
METHODS="${BENCH_METHODS:-}"
run_dirs() {   # finished-or-not run dirs of THIS pod's methods
  ls -d results/*/*/*/*/*/ 2>/dev/null | grep -vE '^results/(report|bundles|figures|_|prism-benchmarks_)' \
    | { if [ -n "$METHODS" ]; then grep -E "^results/($(echo $METHODS | tr ' ' '|'))/"; else cat; fi; } || true
}
hf_retry() {   # concurrent commits from two pods can collide: retry with backoff
  local i; for i in 1 2 3 4 5; do "$@" && return 0; echo "   (HF call failed, retry $i/5)"; sleep $((i * 15)); done; return 1
}

provenance() {
  mkdir -p logs/env
  {
    echo "host: $(hostname)"; echo "date: $(date -Is)"; echo "shard: ${SHARD:-all}"
    echo "benchmarks: $(git rev-parse HEAD) $(git rev-parse --abbrev-ref HEAD)$(git diff --quiet || echo ' DIRTY')"
    for m in submodules/*/; do
      [ -e "$m/.git" ] && echo "$(basename "$m"): $(git -C "$m" rev-parse HEAD) $(git -C "$m" rev-parse --abbrev-ref HEAD)$(git -C "$m" diff --quiet || echo ' DIRTY')"
    done
    command -v nvidia-smi >/dev/null && nvidia-smi --query-gpu=name,driver_version --format=csv,noheader
  } > logs/env/provenance.txt
  for m in PRISM-VGGT Pi3 map-anything LASER; do
    py="submodules/$m/.venv/bin/python"
    [ -x "$py" ] && uv pip freeze --python "$py" > "logs/env/$(echo "$m" | tr 'A-Z' 'a-z').freeze.txt" 2>/dev/null || true
  done
}

case "${1:-}" in
sync-up)
  [ -n "$REPO_ID" ] || { echo "!! set INPUTS_HF_REPO or RESULTS_HF_REPO"; exit 1; }
  provenance
  INC=(); if [ -n "$METHODS" ]; then for m in $METHODS; do INC+=(--include "$m/*"); done
          else INC=(--exclude "bundles/*" --exclude "report*/*" --exclude "figures/*" --exclude "_*/*" --exclude "prism-benchmarks_*/*"); fi
  hf_retry $HF upload "$REPO_ID" results "results/$TAG/live/results" --repo-type dataset "${INC[@]}" \
      --commit-message "checkpoint $(hostname) $(date +%H:%M) [${METHODS:-all}]" >/dev/null
  hf_retry $HF upload "$REPO_ID" logs "results/$TAG/live/logs/$(hostname)" --repo-type dataset \
      --exclude ".done_*" --commit-message "checkpoint logs $(hostname)" >/dev/null
  echo ">> checkpoint uploaded: $(run_dirs | wc -l) run dirs [${METHODS:-all methods}] -> $REPO_ID results/$TAG/live/" ;;
sync-down)
  [ -n "$REPO_ID" ] || { echo ">> no HF repo set — nothing to resume from"; exit 0; }
  rm -rf dataset/_hf_live
  INC=(); if [ -n "$METHODS" ]; then for m in $METHODS; do INC+=(--include "results/$TAG/live/results/$m/*"); done
          else INC=(--include "results/$TAG/live/results/*"); fi
  hf_retry $HF download "$REPO_ID" --repo-type dataset "${INC[@]}" --local-dir dataset/_hf_live >/dev/null 2>&1 || true
  src="dataset/_hf_live/results/$TAG/live/results"
  if [ -d "$src" ]; then
    n=$(find "$src" -name perf.json | wc -l)
    cp -rn "$src/." results/
    echo ">> resumed $n run(s) [${METHODS:-all methods}] from the HF checkpoint (local files kept;"
    echo "   half-done or crashed ones are redone by the adapter)"
  else
    echo ">> no HF checkpoint for $TAG [${METHODS:-all methods}] — starting fresh"
  fi
  rm -rf dataset/_hf_live ;;
hf-reset)
  # Delete results/<tag>/ (checkpoints + packs) from the HF repo. Run ONCE, before any
  # pod starts — never while a pod is running.
  [ -n "$REPO_ID" ] || { echo "!! no HF repo set"; exit 1; }
  [ "${CONFIRM:-}" = "yes" ] || { echo "!! this deletes results/$TAG/ from $REPO_ID — rerun with CONFIRM=yes"; exit 1; }
  uvx --from 'huggingface_hub>=0.34' python - "$REPO_ID" "$TAG" <<'PY'
import sys
from huggingface_hub import HfApi
repo, tag = sys.argv[1], sys.argv[2]
api = HfApi()
files = [f for f in api.list_repo_files(repo, repo_type="dataset") if f.startswith(f"results/{tag}/")
         or f == "results/_write_test.txt"]
if not files:
    print(f">> nothing under results/{tag}/ — already clean")
else:
    api.delete_files(repo, delete_patterns=[f"results/{tag}/**", "results/_write_test.txt"],
                     repo_type="dataset", commit_message=f"reset results/{tag}")
    print(f">> deleted {len(files)} file(s) under results/{tag}/ in {repo} (inputs untouched)")
PY
  ;;
pack)
  provenance
  mkdir -p "$OUTD"
  F="$OUTD/pod_${TAG}_${SHARD_ID}_$(hostname)_$(date +%Y%m%d_%H%M).tar"
  # Run dirs only (results/<method>/<ds>/<scene>/<traj>/<variant>/...), never the
  # report*/bundles dirs, plus logs.
  mapfile -t RUNDIRS < <(run_dirs)
  [ "${#RUNDIRS[@]}" -gt 0 ] || { echo "!! no run dirs under results/"; exit 1; }
  # Scoring inputs for the scenes this pod ran.
  SCORE=()
  for sd in $(printf '%s\n' "${RUNDIRS[@]}" | awk -F/ '{print "dataset/exports/"$3"/"$4}' | sort -u); do
    [ -d "$sd" ] || continue
    first_mesh=""
    for td in "$sd"/*/; do
      td="${td%/}"
      [ -f "$td/poses_gt.tum" ] && SCORE+=("$td/poses_gt.tum")
      [ -f "$td/measured_camera_height.json" ] && SCORE+=("$td/measured_camera_height.json")
      for pv in "$td"/pinhole/*/; do
        pv="${pv%/}"
        for f in intrinsics.json meta.json depth; do [ -e "$pv/$f" ] && SCORE+=("$pv/$f"); done
      done
      # gt_mesh.ply is an identical copy in every trajectory dir; ship ONE per scene.
      if [ -z "$first_mesh" ] && [ -f "$td/gt_mesh.ply" ]; then
        first_mesh="$td/gt_mesh.ply"; cp -f "$first_mesh" "$sd/_gt_mesh.ply"; SCORE+=("$sd/_gt_mesh.ply")
      fi
    done
  done
  [ -f config.local.yaml ] && SCORE+=(config.local.yaml)
  tar -chf "$F" "${RUNDIRS[@]}" "${SCORE[@]}" logs
  echo ">> $F  ($(du -h "$F" | cut -f1), ${#RUNDIRS[@]} run dirs + scoring exports)" ;;
push)
  [ -n "$REPO_ID" ] || { echo "!! set RESULTS_HF_REPO"; exit 1; }
  F="$(ls -t "$OUTD"/pod_"${TAG}"_*.tar 2>/dev/null | head -1)"
  [ -n "$F" ] || { echo "!! no pod pack in $OUTD (results.sh pack)"; exit 1; }
  $HF repo create "$REPO_ID" --repo-type dataset --private >/dev/null 2>&1 || true
  hf_retry $HF upload "$REPO_ID" "$F" "results/$TAG/$(basename "$F")" --repo-type dataset \
      --commit-message "results $TAG $(basename "$F")" ;;
fetch)
  [ -n "$REPO_ID" ] || { echo "!! set RESULTS_HF_REPO"; exit 1; }
  $HF download "$REPO_ID" --repo-type dataset --include "results/$TAG/*.tar" --local-dir dataset/_hf
  ls -1 dataset/_hf/results/"$TAG"/*.tar ;;
merge)
  shift
  [ "$#" -gt 0 ] || set -- dataset/_hf/results/"$TAG"/*.tar
  for F in "$@"; do
    echo ">> merging $F"
    clash=$(tar -tf "$F" | grep -E '^results/[^/]+/[^/]+/[^/]+/[^/]+/[^/]+/perf.json$' \
            | while read -r p; do if [ -e "$p" ]; then echo "$p"; fi; done | head -5 || true)
    if [ -n "$clash" ] && [ "${MERGE_OVERWRITE:-0}" != "1" ]; then
      echo "!! $F would overwrite existing runs (e.g. $clash). MERGE_OVERWRITE=1 to allow."; exit 1
    fi
    mkdir -p "logs/pods/$(basename "$F" .tar)"
    tar -xf "$F" --exclude='logs/*' -C .
    # Restore the per-trajectory gt_mesh.ply copies the pack de-duplicated.
    for m in dataset/exports/*/*/_gt_mesh.ply; do
      [ -f "$m" ] || continue
      for td in "$(dirname "$m")"/*/; do
        if [ -f "${td}poses_gt.tum" ] && [ ! -f "${td}gt_mesh.ply" ]; then cp "$m" "${td}gt_mesh.ply"; fi
      done
    done
    tar -xf "$F" -C "logs/pods/$(basename "$F" .tar)" --strip-components=1 --wildcards 'logs/*' 2>/dev/null || true
  done
  echo ">> merged. Score with: make eval-all" ;;
*)
  sed -n '2,17p' "$0"; exit 1 ;;
esac

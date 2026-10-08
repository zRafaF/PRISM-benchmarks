#!/usr/bin/env bash
# ============================================================================
# results.sh — move a pod's raw results to wherever they are scored.
#
#   bash scripts/results.sh pack            # results/ + logs + provenance -> results/bundles/pod_*.tar
#   bash scripts/results.sh push            # upload that tar to RESULTS_HF_REPO (optional)
#   bash scripts/results.sh fetch           # (offline box) download every pod tar for RESULTS_TAG
#   bash scripts/results.sh merge F.tar...  # unpack pod tars into results/, refusing collisions
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
pack)
  provenance
  mkdir -p "$OUTD"
  F="$OUTD/pod_${TAG}_${SHARD_ID}_$(hostname)_$(date +%Y%m%d_%H%M).tar"
  # Run dirs only (results/<method>/<ds>/<scene>/<traj>/<variant>/...), never the
  # report*/bundles dirs, plus logs.
  mapfile -t RUNDIRS < <(ls -d results/*/*/*/*/*/ 2>/dev/null | grep -vE '^results/(report|bundles|figures|_)' || true)
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
  $HF upload "$REPO_ID" "$F" "results/$TAG/$(basename "$F")" --repo-type dataset \
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

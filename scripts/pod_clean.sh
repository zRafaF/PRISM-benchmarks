#!/usr/bin/env bash
# Start a pod run from a clean slate for the current tag (INPUTS_TAG, bench.env), so no
# result or input from an earlier campaign can leak in. The earlier campaigns used the
# same method names and trajectory ids (e.g. prism / synthetic_2.0hz_s0), so a leftover
# results/ dir would be SKIPPED as "already done", and leftover frames in
# dataset/exports would be read alongside the new ones (rooms went from 300 to 121
# frames). Nothing is deleted irreversibly that cannot be fetched again:
#   results/                   -> results_archive/<old tag>_<stamp>/   (moved, kept)
#   dataset/exports/, dataset/_hf, dataset/_hf_live   -> deleted (re-fetched from HF)
#   logs/.done_data, .done_precheck, .data_ready        -> deleted (stages re-run)
# Kept: method envs (prep/check), results/_sanity_tum (environment check, not a result
# of the matrix), config.local.yaml is replaced by the inputs pack on fetch.
# Then results/.tag records the tag; the bench stage refuses to run on a results/ dir
# stamped with another tag.
set -euo pipefail
cd "$(dirname "$0")/.."
_benv() { sed -n "s/^$1[[:space:]]*[?:]*=[[:space:]]*//p" bench.env 2>/dev/null | head -1; }
TAG="${INPUTS_TAG:-$(_benv INPUTS_TAG)}"
STAMP="$(date +%Y%m%d_%H%M%S)"
if tmux has-session -t pod 2>/dev/null; then echo "!! tmux session 'pod' is running — make pod-stop first"; exit 1; fi
if [ -d results ] && [ -n "$(ls -A results 2>/dev/null | grep -v '^_sanity_tum$\|^\.tag$')" ]; then
  old="$(cat results/.tag 2>/dev/null || echo untagged)"
  mkdir -p results_archive
  dest="results_archive/${old}_${STAMP}"
  mkdir -p "$dest"
  for e in results/* results/.tag; do
    [ -e "$e" ] || continue
    [ "$(basename "$e")" = "_sanity_tum" ] && continue
    mv "$e" "$dest/"
  done
  echo ">> moved previous results to $dest"
fi
rm -rf dataset/exports dataset/_hf dataset/_hf_live
rm -f logs/.done_data logs/.done_precheck logs/.data_ready
mkdir -p results
echo "$TAG" > results/.tag
echo ">> clean slate for tag '$TAG' (envs kept). Next: make pod"

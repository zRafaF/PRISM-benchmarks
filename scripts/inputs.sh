#!/usr/bin/env bash
# ============================================================================
# inputs.sh — render ONCE (on any CPU box), run on many GPU pods.
#
#   bash scripts/inputs.sh pack     # dataset/exports -> dataset/inputs/<tag>/<scene>.tar
#   bash scripts/inputs.sh push     # upload dataset/inputs/<tag>/ to a HF dataset repo
#   bash scripts/inputs.sh fetch    # on a pod: download + unpack (only this SHARD's scenes)
#   bash scripts/inputs.sh unpack   # on a pod: unpack tars you copied into dataset/inputs/<tag>/
#   bash scripts/inputs.sh verify   # every frozen (scene, traj) has its method inputs
#   bash scripts/inputs.sh rehash   # re-stamp MANIFEST fingerprint (render settings unchanged)
#
# A pack holds exactly what the METHODS read: rgb/ + mask/ + meta.json +
# intrinsics.json per camera, plus poses_gt.tum and measured_camera_height.json. It
# deliberately leaves out depth/ and gt_mesh.ply — only the offline scorer needs those,
# and they are most of the bytes — so the pod never needs Replica either. The frozen
# scene list (config.local.yaml) travels with the pack, so every pod shards the SAME
# list. MANIFEST.json records the git commit and a hash of the config that rendered it.
#
# Env: INPUTS_TAG (default rerun-v2), INPUTS_HF_REPO (e.g. you/prism-bench-inputs),
#      HF_TOKEN (private repo), SHARD=k/N or BENCH_SCENES="a b" (fetch subset).
# ============================================================================
set -euo pipefail
cd "$(dirname "$0")/.."
# Defaults from bench.env when not in the environment (e.g. run outside make/tmux).
_benv() { sed -n "s/^$1[[:space:]]*[?:]*=[[:space:]]*//p" bench.env 2>/dev/null | head -1; }
export INPUTS_TAG="${INPUTS_TAG:-$(_benv INPUTS_TAG)}"
export INPUTS_HF_REPO="${INPUTS_HF_REPO:-$(_benv INPUTS_HF_REPO)}"
export RESULTS_HF_REPO="${RESULTS_HF_REPO:-$(_benv RESULTS_HF_REPO)}"
TAG="${INPUTS_TAG:-rerun-v2}"
REPO_ID="${INPUTS_HF_REPO:-}"
DIR="dataset/inputs/$TAG"
EXP="dataset/exports"
RUN="${RUN:-uv run python}"
HF="${HF_CLI:-uvx --from huggingface_hub[cli]>=0.34 hf}"

frozen_scenes() {
  $RUN -c "
from bench.config import load_config
c=load_config('config.yaml'); ds=c['datasets'][c['datasets']['active'][0]]
print(' '.join(ds.get('scenes') or []))"
}
active_ds() { $RUN -c "from bench.config import load_config; print(load_config('config.yaml')['datasets']['active'][0])"; }
shard_of() {   # shard_of "<scenes>"
  local all="$1"
  if [ -n "${BENCH_SCENES:-}" ]; then echo "$BENCH_SCENES"; return; fi
  if [ -z "${SHARD:-}" ]; then echo "$all"; return; fi
  local k="${SHARD%/*}" n="${SHARD#*/}" i=0 out=""
  for sc in $all; do [ $((i % n)) -eq "$k" ] && out="$out $sc"; i=$((i + 1)); done
  echo "$out" | sed 's/^ *//'
}
need_repo() { [ -n "$REPO_ID" ] || { echo "!! set INPUTS_HF_REPO=<user>/<dataset-repo> (bench.env or env)"; exit 1; }; }

cmd="${1:-}"
case "$cmd" in
pack)
  DS="$(active_ds)"; SC="$(frozen_scenes)"
  [ -n "$SC" ] || { echo "!! no frozen scenes — run 'make split' first"; exit 1; }
  mkdir -p "$DIR"
  for sc in $SC; do
    [ -d "$EXP/$DS/$sc" ] || { echo "!! $EXP/$DS/$sc missing — 'make render export' first"; exit 1; }
    echo ">> packing $sc"
    tar -cf "$DIR/$sc.tar" --exclude='*/depth' --exclude='*/depth/*' --exclude='gt_mesh.ply' \
        -C . "$EXP/$DS/$sc"
  done
  cp config.local.yaml "$DIR/config.local.yaml"
  $RUN - "$DIR" "$DS" "$SC" <<'PY'
import hashlib, json, subprocess, sys, time
from pathlib import Path
d, ds, sc = Path(sys.argv[1]), sys.argv[2], sys.argv[3].split()
from bench.render_hash import render_hash
git = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
dirty = bool(subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True).stdout.strip())
(d / "MANIFEST.json").write_text(json.dumps({
    "tag": d.name, "dataset": ds, "scenes": sc, "created": time.strftime("%Y-%m-%dT%H:%M:%S"),
    "git_commit": git, "git_dirty": dirty, "render_config_sha256": render_hash(), "hash_v": 2,
    "files": {p.name: p.stat().st_size for p in sorted(d.glob("*.tar"))}}, indent=2))
print(f">> MANIFEST: {len(sc)} scenes, commit {git[:8]}{' (DIRTY)' if dirty else ''}")
PY
  du -sh "$DIR"/* ;;
push)
  need_repo
  [ -f "$DIR/MANIFEST.json" ] || { echo "!! nothing packed at $DIR (inputs.sh pack)"; exit 1; }
  $HF repo create "$REPO_ID" --repo-type dataset --private >/dev/null 2>&1 || true
  $HF upload "$REPO_ID" "$DIR" "inputs/$TAG" --repo-type dataset \
      --commit-message "inputs $TAG" ;;
fetch)
  need_repo
  mkdir -p "$DIR"
  $HF download "$REPO_ID" --repo-type dataset --include "inputs/$TAG/MANIFEST.json" \
      --include "inputs/$TAG/config.local.yaml" --local-dir dataset/_hf >/dev/null
  if [ -f config.local.yaml ] && ! cmp -s config.local.yaml "dataset/_hf/inputs/$TAG/config.local.yaml"; then
    cp config.local.yaml "config.local.yaml.bak.$(date +%s)"
    echo ">> existing config.local.yaml backed up (the pack's frozen scene list wins)"
  fi
  cp "dataset/_hf/inputs/$TAG/config.local.yaml" config.local.yaml
  cp "dataset/_hf/inputs/$TAG/MANIFEST.json" "$DIR/MANIFEST.json"
  bash "$0" check-hash
  SC="$(shard_of "$(frozen_scenes)")"
  echo ">> fetching inputs/$TAG for: $SC"
  for sc in $SC; do
    $HF download "$REPO_ID" --repo-type dataset --include "inputs/$TAG/$sc.tar" \
        --local-dir dataset/_hf >/dev/null
    tar -xf "dataset/_hf/inputs/$TAG/$sc.tar" -C .
    rm -f "dataset/_hf/inputs/$TAG/$sc.tar"
    echo "   $sc unpacked"
  done
  bash "$0" verify ;;
unpack)
  [ -f "$DIR/MANIFEST.json" ] && [ -f "$DIR/config.local.yaml" ] || {
    echo "!! copy MANIFEST.json, config.local.yaml and <scene>.tar into $DIR first"; exit 1; }
  if [ -f config.local.yaml ] && ! cmp -s config.local.yaml "$DIR/config.local.yaml"; then
    cp config.local.yaml "config.local.yaml.bak.$(date +%s)"
  fi
  cp "$DIR/config.local.yaml" config.local.yaml
  bash "$0" check-hash
  for t in "$DIR"/*.tar; do echo ">> unpacking $(basename "$t")"; tar -xf "$t" -C .; done
  bash "$0" verify ;;
check-hash)
  # The pod must run the SAME trajectory/render code that produced the inputs.
  M="$DIR/MANIFEST.json"
  [ -f "$M" ] || { echo "!! no $M"; exit 1; }
  $RUN - "$M" <<'PY'
import hashlib, json, sys
from pathlib import Path
m = json.loads(Path(sys.argv[1]).read_text())
from bench.render_hash import render_hash
ok = render_hash() == m.get("render_config_sha256")
if m.get("hash_v") != 2:
    print("!! MANIFEST uses the old whole-config fingerprint: on the PC run "
          "'bash scripts/inputs.sh rehash && make inputs-push'"); sys.exit(1)
print(f">> inputs rendered at commit {m.get('git_commit', '?')[:8]}"
      f"{' (DIRTY)' if m.get('git_dirty') else ''}: config/trajectory code "
      f"{'MATCHES' if ok else 'DIFFERS FROM'} this checkout")
if not ok:
    print("!! render settings (datasets/camera/trajectories) or trajectories.py / render_scene.py changed since the inputs were "
          "rendered. Re-render + re-pack on the PC, or check out the commit above.")
sys.exit(0 if ok else 1)
PY
  ;;
rehash)
  # Re-stamp MANIFEST.json with the current fingerprint WITHOUT re-rendering. Only valid
  # when the render settings/code are unchanged since the frames were made (e.g. after
  # editing run settings, or moving to a new fingerprint format).
  M="$DIR/MANIFEST.json"; [ -f "$M" ] || { echo "!! no $M"; exit 1; }
  $RUN - "$M" <<'PY'
import json, sys
from pathlib import Path
from bench.render_hash import render_hash
p = Path(sys.argv[1]); m = json.loads(p.read_text())
m["render_config_sha256"], m["hash_v"] = render_hash(), 2
p.write_text(json.dumps(m, indent=2)); print(">> MANIFEST re-stamped:", m["render_config_sha256"][:12])
PY
  ;;
verify)
  $RUN - <<'PY'
import os, sys
from bench.config import load_config, export_dir, resolve_trajs
c = load_config("config.yaml"); ds = c["datasets"]["active"][0]
scenes = (os.environ.get("BENCH_SCENES") or "").split() or (c["datasets"][ds].get("scenes") or [])
sh = os.environ.get("SHARD", "")
if sh and not os.environ.get("BENCH_SCENES"):
    k, n = (int(x) for x in sh.split("/")); scenes = scenes[k::n]
missing = []
for sc in scenes:
    for tj in resolve_trajs(c, "all"):
        cams = [("pano", "")] + [("pinhole", v) for v in c["camera"]["pinhole"]["variants"]]
        for cam, var in cams:
            d = export_dir(ds, sc, tj, cam, var)
            if var == "real_intrinsics" and not d.exists():
                continue               # only rendered when the dataset has its own K
            if not (d / "meta.json").exists() or not any((d / "rgb").glob("*.png")):
                missing.append(str(d))
print(f">> verify: {len(scenes)} scene(s) x {len(resolve_trajs(c, 'all'))} traj(s): "
      f"{'OK' if not missing else str(len(missing)) + ' MISSING'}")
for m in missing[:20]:
    print("   missing", m)
sys.exit(1 if missing else 0)
PY
  ;;
*)
  sed -n '2,22p' "$0"; exit 1 ;;
esac

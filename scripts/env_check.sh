#!/usr/bin/env bash
# ============================================================================
# env_check.sh — prove a freshly provisioned pod can produce trustworthy numbers
# BEFORE any benchmark GPU time is spent (`make env-check`).
#
#   1. a CUDA GPU is visible;
#   2. every method env imports torch with CUDA (Blackwell sm_120 builds);
#   3. the PRISM submodule is the prism-v2 engine (dense alignment present);
#   4. VGGT-SLAM REPRODUCES ITS OWN REFERENCE: its bundled `office_loop` sequence with
#      the repo's default parameters must close >= 1 loop (the README promises exactly
#      one). This is the check that would have caught a broken GTSAM/torch combination
#      — the 2026-08 runs never verified that our VGGT-SLAM install behaved like
#      upstream's. Takes ~1-2 min. ENV_CHECK_SKIP_VSLAM_REF=1 skips it.
#
# Writes logs/env/env_check.json and exits non-zero on any FAIL.
# ============================================================================
set -u -o pipefail
cd "$(dirname "$0")/.."
mkdir -p logs/env
OUT=logs/env/env_check.json
FAILS=0
declare -a ROWS=()
row() { ROWS+=("{\"check\": \"$1\", \"status\": \"$2\", \"detail\": \"$(echo "$3" | tr -d '"\\' | tr '\n' ' ' | cut -c1-300)\"}"); \
        printf '  [%s] %-38s %s\n' "$2" "$1" "$3"; [ "$2" = "FAIL" ] && FAILS=$((FAILS + 1)); return 0; }

echo "=== env-check $(date -Is) ==="

# 1. GPU
if command -v nvidia-smi >/dev/null 2>&1 && nvidia-smi -L >/dev/null 2>&1; then
  row gpu PASS "$(nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader | head -1)"
else
  row gpu FAIL "nvidia-smi not found or no GPU visible"
fi

# 2. method envs: torch + CUDA
for m in PRISM-VGGT Pi3 VGGT-SLAM map-anything LASER; do
  py="submodules/$m/.venv/bin/python"
  if [ ! -x "$py" ]; then row "env:$m" FAIL "no venv at $py (make setup-all)"; continue; fi
  if msg=$("$py" -c "import torch; assert torch.cuda.is_available(), 'no CUDA'; \
x=torch.ones(8,device='cuda').sum().item(); \
print(torch.__version__, torch.cuda.get_device_name(0), 'sm_%d%d' % torch.cuda.get_device_capability(0))" 2>&1); then
    row "env:$m" PASS "$msg"
  else
    row "env:$m" FAIL "$(echo "$msg" | tail -1)"
  fi
done

# 3. PRISM engine version
P=submodules/PRISM-VGGT
if [ -d "$P/.git" ] || [ -f "$P/.git" ]; then
  rev="$(git -C "$P" rev-parse --short HEAD 2>/dev/null) ($(git -C "$P" rev-parse --abbrev-ref HEAD 2>/dev/null))"
  if grep -q "register_points_sim3_robust" "$P/prism_vggt/utils/geometry.py" 2>/dev/null; then
    row prism_engine PASS "prism-v2 dense alignment present @ $rev"
  else
    row prism_engine FAIL "PRISM-VGGT @ $rev is NOT the prism-v2 engine (check PRISM_REF in bench.env)"
  fi
  if [ -x "$P/.venv/bin/python" ]; then
    if msg=$(cd "$P" && .venv/bin/python -c "import nvblox_torch; from prism_vggt.engine import StreamingWindowEngine; print('nvblox_torch + engine import OK')" 2>&1); then
      row prism_import PASS "$msg"
    else
      row prism_import FAIL "$(echo "$msg" | tail -1)"
    fi
  fi
  # nvblox must actually FUSE on this GPU, not just import: the prebuilt wheel is the
  # one known risk on Blackwell (PRISM-VGGT setup.sh warns it can segfault). Runs in
  # its own process so a segfault is reported, not fatal to this script.
  if [ -x "$P/.venv/bin/python" ]; then
    if msg=$(cd "$P" && timeout 300 .venv/bin/python - 2>&1 <<'PY'
import numpy as np
from prism_vggt.tsdf import NvbloxPanoTSDF
t = NvbloxPanoTSDF(voxel_size_m=0.05, max_depth=4.5, face_size=256, device="cuda")
H, W = 256, 512
depth = np.full((H, W), 2.0, np.float32)               # a sphere of radius 2 m
rgb = np.full((H, W, 3), 128, np.uint8)
for k in range(3):
    pose = np.eye(4, dtype=np.float32); pose[0, 3] = 0.1 * k
    t.integrate(depth, rgb, np.ones((H, W), np.uint8), pose)
t.update_mesh()
n = t.num_tsdf_blocks()
assert n > 0, "integrated 3 frames but nvblox holds 0 TSDF blocks"
print(f"nvblox fused 3 synthetic panoramas -> {n} TSDF blocks")
PY
    ); then
      row nvblox_integrate PASS "$(echo "$msg" | tail -1)"
    else
      row nvblox_integrate FAIL "$(echo "$msg" | tail -1) (try: NVBLOX_MODE=source make setup-prism)"
    fi
  fi
  [ -f "$P/checkpoints/model.pt" ] && row panovggt_weights PASS "$(du -h "$P/checkpoints/model.pt" | cut -f1)" \
    || row panovggt_weights FAIL "missing $P/checkpoints/model.pt (make setup-prism)"
else
  row prism_engine FAIL "submodules/PRISM-VGGT missing (make init)"
fi

# 4. VGGT-SLAM reference reproduction
V=submodules/VGGT-SLAM
if [ "${ENV_CHECK_SKIP_VSLAM_REF:-0}" = "1" ]; then
  row vggtslam_reference SKIP "ENV_CHECK_SKIP_VSLAM_REF=1"
elif [ -x "$V/.venv/bin/python" ] && [ -f "$V/office_loop.zip" ]; then
  REF=$(mktemp -d)
  unzip -q "$V/office_loop.zip" -d "$REF"
  echo "  ... running VGGT-SLAM on its own office_loop sample (repo defaults, ~1-2 min)"
  ( cd "$V" && .venv/bin/python main.py --image_folder "$REF/office_loop" --max_loops 1 \
      --log_results --skip_dense_log --log_path "$REF/poses.txt" ) > logs/env/vggtslam_reference.log 2>&1
  rc=$?
  nl=$(grep -oE "Total number of loop closures in map[[:space:]]+[0-9]+" logs/env/vggtslam_reference.log | grep -oE "[0-9]+$" | tail -1)
  ns=$(grep -oE "Total number of submaps in map[[:space:]]+[0-9]+" logs/env/vggtslam_reference.log | grep -oE "[0-9]+$" | tail -1)
  if [ "$rc" -eq 0 ] && [ "${nl:-0}" -ge 1 ]; then
    row vggtslam_reference PASS "office_loop: ${ns} submaps, ${nl} loop closure(s) (upstream: 1)"
  else
    row vggtslam_reference FAIL "office_loop rc=$rc submaps=${ns:-?} loops=${nl:-?} — install does not reproduce upstream (logs/env/vggtslam_reference.log)"
  fi
  rm -rf "$REF"
else
  row vggtslam_reference FAIL "VGGT-SLAM env or office_loop.zip missing"
fi

{ echo "{\"time\": \"$(date -Is)\", \"host\": \"$(hostname)\", \"fails\": $FAILS, \"checks\": ["
  ( IFS=,; echo "${ROWS[*]}" )
  echo "]}"; } > "$OUT"
echo "=== env-check: $FAILS failure(s)  -> $OUT ==="
[ "$FAILS" -eq 0 ]

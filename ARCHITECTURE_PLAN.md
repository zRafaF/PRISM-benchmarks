# PRISM-benchmarks — Orchestrator Architecture & Plan (for review)

> **Status: PLAN ONLY. No code written yet.** This operationalizes
> `uofa-2026-report/resources/context/05_benchmark_plan.md` (ground truth; **05 wins on
> any conflict**) and the kickoff brief. Grounded against the real PRISM-VGGT API
> (`vat-monorepo/server/mapping/PRISM-VGGT`, commit as-mounted). Please review §11 (open
> questions) and §12 (brief-vs-05 conflicts) before I build anything.

Repo confirmed: **`C:\Dev\ualberta\PRISM-benchmarks`** (the orchestrator). PRISM-VGGT and
the baselines are pulled in as submodules; nothing here loosens PRISM's locked stack.

---

## 1. What this repo is (and is not)

The orchestrator is a **neutral referee**. It owns the shared dataset rendering, the
fair-comparison co-visibility masking, the eval + perf/resource collection, and the final
aggregated report. It runs each method as a **subprocess in that method's own isolated
env** and collects outputs into one common layout. **No method's dependencies ever leak
into the eval layer** — `eval/*` imports no method and never touches torch/nvblox/GTSAM.

It is *not* the PRISM self-contained benchmarks. Those stay inside
`PRISM-VGGT/benchmarks/` (currently a "Coming soon!" stub) for PRISM-only sanity/perf and
depend on nothing else. This repo is the cross-method comparison layer and may reuse
PRISM's pieces *via the PRISM submodule's env*, never by importing PRISM here.

---

## 2. Isolation strategy — submodules + per-submodule envs (the core mechanic)

Each method lives as a git submodule under `submodules/` and keeps its **own** `uv`/venv.
The orchestrator has a separate light env. The three stacks genuinely conflict:

| Method | Stack pins (why it must be isolated) |
|---|---|
| PRISM-VGGT (ours) | Python 3.12, CUDA 12.8 hard-lock, torch 2.8, `nvblox-torch` custom wheel, hydra/omegaconf. Installed by its own `setup.sh`. |
| VGGT-SLAM (MIT-SPARK) | GTSAM + custom SL(4) bindings + DINOv2-SALAD retrieval — heavy, different torch line. |
| Pi3 / π³ | Its own feed-forward stack. |
| Orchestrator | **No ML deps.** Open3D, evo, numpy, pandas, pynvml, matplotlib, pyyaml, tqdm. Renders + masks + evals + aggregates. |

**How isolation actually works:**

- `submodules/<method>/` — upstream repo, untouched, its own `.venv` created by `uv`.
- `envs/setup_<method>.sh` — thin wrapper that **delegates to each repo's own installer**
  (e.g. calls PRISM's `setup.sh`; for Pi3/VGGT-SLAM, `uv venv` + `uv pip install` per
  their README). We do not reimplement their installs; we shell out to them. This honors
  "prefer reusing each method's own offline entrypoint."
- Each adapter invokes the method by running that method's interpreter, e.g.
  `submodules/PRISM-VGGT/.venv/bin/python -m ...` (or `uv run --project submodules/<m> ...`)
  as a **subprocess**. The orchestrator process itself never imports the method.
- The orchestrator's own env is created by `uv sync` at the repo root against
  `pyproject.toml` here (its own light dependency set — never PRISM's).

This means the eval scripts run under the orchestrator env; the methods run under theirs;
they communicate only through files on disk (the common results layout, §6).

---

## 3. Renderer choice (recommendation + rationale)

Requirement: from one ScanNet scene mesh (`*_vh_clean_2.ply`, vertex-colored) + one shared
trajectory, render **two matched camera models from the SAME poses** — PANO (equirect RGB +
radial depth + validity mask, matching the live config e.g. 1036×518) and PINHOLE
(perspective RGB + depth at a chosen K/FOV) — plus GT poses in TUM.

Three candidates were on the table:

1. **Open3D `RaycastingScene` (tensor API) — RECOMMENDED.** Cast one ray per output pixel.
   - PINHOLE: build rays from `K`/FOV → returns hit distance; convert to optical Z-depth.
   - PANO: build rays on an equirectangular lat/long grid → returns **radial depth
     directly** (exactly what the pano branch wants — no cubemap→stitch step, no seams).
   - **Validity mask** falls out for free: pixels where `t_hit == inf` are invalid.
   - RGB: `RaycastingScene` returns `primitive_ids` + barycentric `primitive_uvs`; we
     interpolate the mesh's **vertex colors** to get per-ray RGB. This gives *identical*
     ray semantics for pano and pinhole (same intersection code, only the ray set differs)
     → the fairness argument ("any gap is method, not data") holds at the renderer level.
   - Pure geometry, no GL context — robust headless on the render box.

2. Open3D `OffscreenRenderer` (rasterization) — easy textured RGB for pinhole, but **no
   native equirect projection**; pano would still need the 6-face cubemap→stitch path.
   Kept as a **fallback** only if vertex-color interpolation quality is insufficient (e.g.
   we later switch to ScanNet++ textured meshes, where rasterization samples the texture
   map properly).

3. 6-face cubemap render → stitch to equirect — most code, seam handling, and it is exactly
   what PRISM does *internally* for TSDF. Rendering inputs this way risks baking our own
   projection assumptions into the "ground-truth" input. **Not recommended** for input
   generation.

**Recommendation: `RaycastingScene` for both camera models**, vertex-color RGB, `inf`-hit
validity mask. Revisit rasterization/texture sampling only when moving to textured meshes
(ScanNet++). Radial→optical depth conversion for pinhole is a one-liner; for PRISM we hand
it the pano radial depth unchanged (matches `FrameInput` expectations).

---

## 4. The dataset pipeline

Rendered from ScanNet scene meshes → **perfect GT for free**: GT poses = render trajectory
(TUM), GT geometry = scene mesh, GT depth = render depth buffer.

- **Two trajectory variants**, both rendered: (A) resample ScanNet's real camera path;
  (B) synthetic smooth spline walkthrough through free space (robot-like). See §11-Q5 for
  the free-space sampling question.
- **Start small:** 2–3 rooms, fixed seed, frozen scene list (`make_split.py`).
- **Caveat preserved in every output caption:** rendered frames are noise/artifact-free →
  **optimistic upper bound**; the report pairs these with real Theta-X captures (05 §Datasets).
- **ScanNet download:** signed ToU + official `download-scannet.py` (not a wget). Wrapped in
  a Make target that **stops with instructions at the manual ToU step** and documents it.
  ScanNet++ raised as an option (higher-fidelity meshes/textures) rather than chosen
  silently — see §11-Q3.

---

## 5. Metrics (all in the orchestrator env; no method imports)

1. **Trajectory** — ATE (RMSE) + RPE, **Sim(3) Umeyama alignment**, via `evo`
   (`evo_ape`/`evo_rpe`, `--align --correct_scale`). Reads method `poses.tum` vs GT
   `poses.tum`. Matches VGGT-SLAM's monocular TUM protocol.
2. **Reconstruction** — accuracy (pred→GT), completeness (GT→pred), Chamfer, F-score@5cm
   (Open3D `compute_point_cloud_distance`), computed **under the co-visibility mask** (§7)
   **and** separately full-360 no-mask for pano-capable methods.
3. **Performance & resources — EVERY method, same hardware, same harness.** The
   orchestrator wraps each method's subprocess in the *same* timing + sampler so numbers
   are directly comparable, not self-reported:
   - effective FPS, per-window + end-to-end latency;
   - peak VRAM (for ours, PyTorch alloc + nvblox slice via the engine's **`VRAMProfiler`**,
     confirmed at `prism_vggt/utils/profiler.py`; for baselines, sampled);
   - GPU util %/power (`pynvml`/`nvidia-smi` sampler), CPU RAM peak;
   - model/ckpt footprint; and (ours) TSDF block count vs. map size.

---

## 6. Adapter I/O contract (baseline-agnostic — this is the load-bearing interface)

For each method an adapter script (run under the **orchestrator** env, but which launches
the **method's** env as a subprocess) must:

**(a) Consume** the exported input sequence for its camera model, from a fixed input layout:
```
dataset/exports/<scene>/<traj>/<camera_model>/
  rgb/000000.png ...              # equirect (pano) or perspective (pinhole)
  depth/000000.npy ...            # radial (pano) or optical Z (pinhole), meters, float32
  mask/000000.png ...             # validity (pano); pinhole mask = all-valid
  intrinsics.json                 # pinhole: K, W, H, FOV. pano: W, H, projection=equirect
  poses_gt.tum                    # shared GT trajectory (for eval only; NOT fed to method)
  meta.json                       # camera_height (per-frame or const), fps, seed, config echo
```

**(b) Run** the method in **its own env** as a subprocess (no import into the orchestrator).

**(c) Write** results in the common layout — the *only* thing `eval/*` reads:
```
results/<method>/<scene>/<traj>/
  poses.tum        # timestamp tx ty tz qx qy qz qw   (from engine.get_poses() for ours)
  cloud.ply        # reconstructed point cloud in the method's world frame
  perf.json        # per-window + end-to-end timing, peak VRAM, GPU/CPU samples, ckpt size
  run.log          # stdout/stderr (profiler lines parsed for ours)
```

`eval/*` scripts read only `results/<method>/<scene>/<traj>/` — they never import a method.
Every field, unit, and coordinate convention will be documented precisely in `README.md`.

**PRISM adapter specifics (verified against the API):**
- `from prism_vggt import PanoVGGTBackend, StreamingWindowEngine, FrameInput, download_weights`.
- Build `FrameInput(image=uint8 HxWx3 equirect, mask=HxW validity, camera_height=float,
  timestamp=idx)` per frame (mirrors `apps/gradio_ui.py`).
- `engine = StreamingWindowEngine(perception, voxel_size=0.02, max_depth=4.5, face_size=768)`;
  iterate `engine.process_sequence(frames, window_size=16, overlap=4)` yielding
  `(mesh, pcd, trajectory, floor)`; then `ts, poses = engine.get_poses()` → dump TUM; save
  the final cloud → `cloud.ply`; parse profiler stdout → `perf.json`.
- **PanoVGGT-no-SLAM ablation** runs in the same PRISM env: per-window backend + naive
  concat (no Sim(3) anchor / guards), same pano inputs. Do this one for sure (05 confirms).

---

## 7. Fairness — co-visibility masking (`eval/visibility_mask.py`, shared)

Pano sees 360°, pinhole baselines see a frustum → restrict to the **shared observed volume**:
- Build the **union of all pinhole poses' bounded view frustums** (far = `max_depth`, e.g.
  4.5 m). Keep only points inside that union; apply the **same mask** to our recon, each
  baseline's recon, and the GT (for completeness).
- **Simple:** point-in-frustum-union containment.
- **Rigorous (we have GT depth):** per-frame visibility/occlusion test — a point counts as
  observed only if it projects into some pinhole frame's bounds **and** range ≤ GT depth +
  tol. Implement rigorous if cheap; else fall back to containment. (05 prefers rigorous.)
- Keep the **full-360 no-mask** eval as a separate table (credits our coverage).

---

## 8. Proposed repo layout

```
PRISM-benchmarks/
  .gitmodules                # PRISM-VGGT, Pi3, VGGT-SLAM, (StreamVGGT, LASER)
  submodules/                # method repos, each its own uv/.venv (gitignored build artifacts)
  Makefile                   # top-level control (see §9)
  pyproject.toml / uv.lock   # orchestrator's OWN light env (render+mask+eval+aggregate)
  config.yaml                # scenes, trajectories, camera params, engine knobs, thresholds, hw id
  README.md                  # end-to-end run guide + the adapter contract (§6)
  envs/
    setup_prism.sh setup_pi3.sh setup_vggtslam.sh   # delegate to each repo's installer
  dataset/
    download_scannet.py      # wrap official downloader (+ ToU stop/note)
    render_scene.py          # mesh + trajectory -> PANO (rgb/depth/mask) + PINHOLE + poses.tum
    trajectories.py          # variant A (ScanNet path resample) + variant B (synthetic spline)
    make_split.py            # pick N scenes, fixed seed, freeze list
    export_inputs.py         # emit per-method input sequences in the adapter format (§6a)
    raw/                     # gitignored: downloaded ScanNet
    exports/                 # gitignored: per-method inputs
  adapters/
    prism.py  panovggt.py  pi3.py  vggtslam.py       # run method in its env -> common outputs
  eval/
    visibility_mask.py       # frustum-union (+ occlusion) mask; shared
    eval_traj.py             # evo ATE/RPE -> ate.json
    eval_recon.py            # masked + full-360 recon metrics -> recon.json
    collect_perf.py          # parse profiler / pynvml -> perf.csv
    make_report.py           # aggregate all json/csv -> tables + plots (md/csv/png)
  results/                   # gitignored; per-method/scene/traj outputs + final report
```

Small, single-purpose scripts; everything reads `config.yaml`. `results/`, `dataset/raw/`,
`dataset/exports/`, and submodule build artifacts stay out of git.

---

## 9. Makefile targets (proposed names)

- `init` — `git submodule update --init --recursive`.
- `setup` — orchestrator env (`uv sync`).
- `setup-<method>` / `setup-all` — per-submodule isolated env via `envs/setup_*.sh`.
- `download` — ScanNet scenes (wraps official downloader; **stops at ToU** with instructions).
- `render` — render pano+pinhole+GT for `SCENES`/`TRAJ` (both variants).
- `export` — emit per-method adapter inputs.
- `run-<method>` / `run-all` — run each method in its env → common results layout.
- `eval-traj` / `eval-recon` / `perf` — metrics across all present results.
- `report` — aggregate into final tables + plots.
- `all` — `init → setup-all → download → render → export → run-all → eval-* → report`.

Variables with defaults matching the live/report config:
`SCENES`, `TRAJ`, `WINDOW=16`, `OVERLAP=4`, `VOXEL=0.02`, `MAX_DEPTH=4.5`, `FACE_SIZE=768`,
`DEVICE=cuda`, `HW_ID` (free-text hardware label for the perf table).

---

## 10. `config.yaml` schema (proposed)

```yaml
hardware:
  hw_id: "RTX PRO 6000"          # free-text; stamped into perf tables
  device: cuda

dataset:
  source: scannet                # scannet | scannetpp   (see Q3)
  scenes: [scene0000_00, scene0011_00]   # frozen list
  seed: 1234
  scannet_root: dataset/raw/scannet

camera:
  pano:    { width: 1036, height: 518, projection: equirect }
  pinhole: { width: 640, height: 480, fov_deg: 90 }   # K derived from fov (see Q6)
  camera_height_m: 1.7

trajectories:
  variants: [scannet_resampled, synthetic_spline]
  n_frames: 200                  # per sequence (cap length; drift honesty, 05)
  spline: { speed_mps: 0.5, min_clearance_m: 0.3 }   # variant B (see Q5)

engine:                          # PRISM knobs; mirror live config
  window_size: 16
  overlap: 4
  voxel_size: 0.02
  max_depth: 4.5
  face_size: 768
  processing_mode: parallel
  tsdf_prune_radius: 0           # full accumulation for quality runs (05 step 1)

eval:
  fscore_threshold_m: 0.05
  mask: { mode: rigorous, frustum_far_m: 4.5, occlusion_tol_m: 0.05 }
  align: { type: sim3, correct_scale: true }

methods:
  - { name: prism,     camera: pano,    env: submodules/PRISM-VGGT }
  - { name: panovggt,  camera: pano,    env: submodules/PRISM-VGGT }
  - { name: pi3,       camera: pinhole, env: submodules/Pi3 }
  - { name: vggtslam,  camera: pinhole, env: submodules/VGGT-SLAM }   # stretch (Q4)

report:
  label: preliminary             # every table caption
```

---

## 11. Open questions (need your call before / during build)

1. **Baseline repo URLs + commits to pin.** Pi3/π³ and VGGT-SLAM (MIT-SPARK) exact repo
   URLs and the commit/tag to pin per submodule. StreamVGGT / LASER — pin now or defer?
2. **PanoVGGT weights.** Confirm the adapters may call `download_weights()` (fetches
   `YijingGuo/PanoVGGT/model.pt` from HF) during `setup-prism`, and where checkpoints live
   (gitignored `submodules/PRISM-VGGT/checkpoints/`?).
3. **ScanNet vs ScanNet++.** Start on ScanNet (`_vh_clean_2.ply`, vertex colors) or go
   straight to ScanNet++ for higher-fidelity meshes/textures (also changes the renderer
   toward texture sampling, §3)? Both have separate ToU.
4. **VGGT-SLAM scope for this pass.** 05 says PanoVGGT-no-SLAM "for sure" and VGGT-SLAM
   "if setup allows" (GTSAM/SL(4)/DINO-SALAD is the heaviest install). Build its adapter
   now or land the PRISM + PanoVGGT + Pi3 path first and add VGGT-SLAM after?
5. **Synthetic trajectory (variant B) free-space sampling.** How to sample a collision-free
   spline: voxel/occupancy from the mesh + clearance radius, then fit a smooth spline
   through waypoints? Any preferred speed / smoothness / loop-vs-no-loop profile?
6. **Pinhole intrinsics.** Pick K/FOV for the pinhole renders — reuse ScanNet's real
   intrinsics (natural, matches variant A) or a fixed synthetic FOV (e.g. 90°) for both
   variants? This sets what the co-visibility frustum covers.
7. **Render/run hardware.** Confirm the box (RTX PRO 6000 per 05) and whether a second
   hardware point (RTX 3090) is in scope for the perf table.

---

## 12. Brief-vs-05 conflicts flagged (05 wins — please confirm resolution)

- **Sequencing / priority.** 05 (DECISION 2026-07-13) prioritizes, for the *first pass*,
  **(1) system performance** (profiler → table, no GT) and **(2) metric accuracy vs.
  tape-measure GT on the lab/mock-up captures**; it explicitly marks the **ScanNet-render
  pipeline "BUILD DEFERRED — hold for a later session"** and defers the ablation and the
  KITTI-360 cross-method ATE. The brief makes the **ScanNet-render orchestrator the main
  job**. Both are dated 2026-07-13; the brief is the newer operationalization ("this
  changed") and defines the two-level architecture.
  **Proposed resolution (confirm):** build the orchestrator skeleton + renderer + the
  PRISM/PanoVGGT (pano) and Pi3 (pinhole) paths now, since that is this repo's purpose;
  but honor 05's ordering *within* it — wire the **perf table first** (runnable without GT),
  then recon/traj — and treat **VGGT-SLAM and KITTI-360 as stretch**. If you'd rather
  strictly follow 05, we'd instead stand up only `collect_perf.py` + the lab-capture metric
  table first and postpone the render pipeline.
- **Primary dataset.** 05 recommends **our lab captures** (tape-measure accuracy + perf) as
  the strongest immediately-available result, and flags **Matterport3D / Stanford2D3D** as a
  more natural *panorama-native* public set than ScanNet for a quick pass. The brief centers
  ScanNet render. Flagging so the lab-capture perf/accuracy path isn't dropped — it can live
  in this repo as an additional `dataset/lab_captures` source feeding the same harness.

---

## 13. What I'll do on approval (build order)

1. Scaffold repo: `pyproject.toml` (orchestrator env), `.gitignore`, `config.yaml`,
   `Makefile`, `README` (adapter contract). `init` + `setup` working.
2. `dataset/render_scene.py` (RaycastingScene pano+pinhole) + `trajectories.py` +
   `make_split.py` + `export_inputs.py`; render 2–3 frozen scenes.
3. `adapters/prism.py` + `adapters/panovggt.py` (PRISM env) → common layout;
   `eval/collect_perf.py` + the **perf table first** (05 priority).
4. `eval/visibility_mask.py`, `eval_traj.py`, `eval_recon.py`; `adapters/pi3.py`.
5. `eval/make_report.py` → preliminary tables A/B/C/C2 + plots. VGGT-SLAM + KITTI-360 as
   stretch.

**Stopping here for your review — no code until the plan is agreed.**

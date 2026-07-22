#!/usr/bin/env python
"""PRISM-benchmarks Studio — a Gradio control panel (run `make preview`).

Tabs:
  * Run pipeline  — tick make targets, run them, watch stdout live, download the log.
  * Config        — edit key settings; saved to the gitignored config.local.yaml overlay.
  * Snapshots     — generate standardized paper images (GT-aligned, ceiling-clipped,
                    black/white bg) + gallery + zip download.
  * Point cloud   — interactive Plotly 3D viewer (+ optional GT overlay, aligned).
  * Frame preview — rendered RGB / depth / mask gallery.
  * Downloads     — browse & download any file/folder (folders zipped).

Runs from the repo root. `share=True` prints a public URL (handy on a remote box).
Only a fixed allowlist of make targets can be run — no arbitrary shell.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bench.config import REPO_ROOT, LOCAL_CONFIG, load_config

EXPORTS = REPO_ROOT / "dataset" / "exports"
RESULTS = REPO_ROOT / "results"
SNAP_DIR = RESULTS / "report" / "snapshots"

MAKE_TARGETS = [
    "init", "setup", "setup-prism", "setup-pi3", "setup-mapanything",
    "setup-vggtslam", "setup-laser", "download", "split", "render", "export",
    "run-prism", "run-pi3", "run-mapanything", "run-vggtslam", "run-laser",
    "eval-traj", "eval-recon", "eval-metric", "perf", "report", "snapshots",
    "fig-vram", "fig-vram-sweep", "fig-cubemap", "fig-cubemap-export", "figures",
]

# Report figures (first-class artifacts) live here; the Figures tab renders +
# serves them. Keep names in sync with eval/vram_scaling.py + eval/fig_cubemap.py.
FIG_DIR = RESULTS / "figures"
FIG_ARTIFACTS = {
    "VRAM vs. frames (plot)":   FIG_DIR / "vram_vs_frames.png",
    "VRAM scaling (CSV)":       FIG_DIR / "vram_scaling.csv",
    "Cubemap projection (plot)": FIG_DIR / "cubemap_projection.png",
}


# ── Run pipeline (stream make output) ─────────────────────────────────────────
# Log lives at the REPO ROOT (not under results/, which `clean-results` wipes mid-run).
LOGPATH = REPO_ROOT / "studio_run.log"


def _bar(k, n):
    filled = int(20 * k / max(n, 1))
    return "|" + "#" * filled + "." * (20 - filled) + f"| {100*k//max(n,1):d}%"


def run_targets(targets, scenes, traj):
    """Run each make target IN TURN, streaming to Gradio AND the terminal, with a
    per-target progress bar. Stops at the first failure (so the log shows what broke)."""
    if not targets:
        yield "Select at least one target.", None
        return
    extra = []
    if scenes and scenes.strip():
        extra.append(f"SCENES={scenes.strip()}")
    if traj and traj.strip():
        extra.append(f"TRAJ={traj.strip()}")

    acc = ""
    n = len(targets)
    lf = open(LOGPATH, "w")

    def emit(text):
        nonlocal acc
        acc += text
        lf.write(text); lf.flush()
        print(text, end="", flush=True)      # also to the terminal — survives a UI crash

    for k, tgt in enumerate(targets, 1):
        emit(f"\n{'='*64}\n[{k}/{n}] {_bar(k-1, n)}  make {tgt} {' '.join(extra)}\n{'='*64}\n")
        yield acc, None
        try:
            p = subprocess.Popen(["make", tgt] + extra, cwd=str(REPO_ROOT),
                                 stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                 text=True, bufsize=1)
        except Exception as e:
            emit(f"[failed to launch: {e}]\n"); yield acc, str(LOGPATH); return
        for line in p.stdout:
            emit(line)
            yield acc, str(LOGPATH)
        p.wait()
        emit(f"[{k}/{n}] {tgt} -> exit {p.returncode}\n")
        yield acc, str(LOGPATH)
        if p.returncode != 0:
            emit(f"\n[STOPPED — '{tgt}' failed; fix and re-run]\n")
            lf.close(); yield acc, str(LOGPATH); return
    emit(f"\n[DONE {n}/{n}] {_bar(n, n)}\n")
    lf.close()
    yield acc, str(LOGPATH)


METHODS = ["prism", "panovggt", "pi3", "vggtslam", "mapanything", "laser"]


def _save_pipeline_overlay(scenes, rates_csv, max_frames):
    import yaml
    overlay = (yaml.safe_load(LOCAL_CONFIG.read_text()) if LOCAL_CONFIG.exists() else {}) or {}
    if rates_csv and rates_csv.strip():
        overlay.setdefault("trajectories", {})["rates_hz"] = [
            float(x) for x in rates_csv.replace(" ", "").split(",") if x]
    if scenes and scenes.strip():
        overlay.setdefault("datasets", {}).setdefault("replica", {})["scenes"] = scenes.split()
    overlay.setdefault("baselines", {})["max_frames"] = None if not max_frames else int(max_frames)
    LOCAL_CONFIG.write_text(yaml.safe_dump(overlay, sort_keys=False))


def full_pipeline(scenes, methods, rates_csv, max_frames, clean_first, do_snapshots):
    """One button: (optionally clean) -> render -> export -> run each selected method
    -> eval-* -> report (-> snapshots), streaming the log. Applies scenes/rates/max_frames
    to the config overlay first so every step is consistent."""
    if not methods:
        yield "Select at least one method.", None
        return
    _save_pipeline_overlay(scenes, rates_csv, max_frames)
    targets = (["clean-results"] if clean_first else []) + ["render", "export"]
    targets += [f"run-{m}" for m in methods]
    targets += ["eval-traj", "eval-recon", "eval-metric", "perf", "report"]
    if do_snapshots:
        targets.append("snapshots")
    yield from run_targets(targets, scenes, "all")


# ── Config overlay editor ─────────────────────────────────────────────────────
def load_config_fields():
    cfg = load_config("config.yaml")
    rates = ", ".join(str(r) for r in cfg["trajectories"].get("rates_hz", []))
    scenes = " ".join(cfg["datasets"].get("replica", {}).get("scenes") or [])
    mf = (cfg.get("baselines") or {}).get("max_frames")
    fscore = cfg["eval"]["fscore_threshold_m"]
    noise = cfg["eval"].get("cleanliness", {}).get("noise_threshold_m", 0.10)
    return rates, scenes, (mf or 0), fscore, noise


def save_config_fields(rates_str, scenes_str, max_frames, fscore_thr, noise_thr):
    import yaml
    overlay = {}
    if LOCAL_CONFIG.exists():
        overlay = yaml.safe_load(LOCAL_CONFIG.read_text()) or {}
    if rates_str.strip():
        overlay.setdefault("trajectories", {})["rates_hz"] = [
            float(x) for x in rates_str.replace(" ", "").split(",") if x]
    if scenes_str.strip():
        overlay.setdefault("datasets", {}).setdefault("replica", {})["scenes"] = scenes_str.split()
    overlay.setdefault("baselines", {})["max_frames"] = None if not max_frames else int(max_frames)
    ev = overlay.setdefault("eval", {})
    ev["fscore_threshold_m"] = float(fscore_thr)
    ev.setdefault("cleanliness", {})["noise_threshold_m"] = float(noise_thr)
    LOCAL_CONFIG.write_text(yaml.safe_dump(overlay, sort_keys=False))
    return f"Saved -> {LOCAL_CONFIG.name} (gitignored; merged over config.yaml):\n\n" + \
           yaml.safe_dump(overlay, sort_keys=False)


# ── Snapshots ─────────────────────────────────────────────────────────────────
# (snapshot generation is wired inline in the Snapshots tab via eval.snapshots.generate)


def _zip_dir(d: Path):
    tmp = tempfile.mkdtemp()
    return shutil.make_archive(os.path.join(tmp, d.name or "snapshots"), "zip", root_dir=str(d))


def _snap_scene(n):
    body = n.split("__", 1)[1] if "__" in n else n
    return body.split("_synthetic_")[0]


def _snap_method(n):
    return n.split("__", 1)[0]


def _snap_view(n):
    return "oblique" if "__oblique__" in n else ("top" if "__top__" in n else "")


def _snap_bg(n):
    return "black" if n.endswith("__black.png") else ("white" if n.endswith("__white.png") else "")


def _filter_snaps(scenes, methods, views, bgs):
    """Filter snapshot PNGs by multi-select criteria (empty list = no filter on that field)."""
    if not SNAP_DIR.exists():
        return []
    files = []
    for p in sorted(SNAP_DIR.glob("*.png")):
        n = p.name
        if scenes and _snap_scene(n) not in scenes:
            continue
        if methods and _snap_method(n) not in methods:
            continue
        if views and _snap_view(n) not in views:
            continue
        if bgs and _snap_bg(n) not in bgs:
            continue
        files.append(str(p))
    return files


PAGE_SIZE = 24


def snap_page(scenes, methods, views, bgs, page):
    """Return (paths_for_page, status_text) — paginated so the gallery always loads."""
    files = _filter_snaps(scenes, methods, views, bgs)
    n = len(files)
    pages = max(1, (n + PAGE_SIZE - 1) // PAGE_SIZE)
    page = max(1, min(int(page or 1), pages))
    sl = files[(page - 1) * PAGE_SIZE: page * PAGE_SIZE]
    return sl, f"{n} images match · page {page}/{pages}  ({PAGE_SIZE}/page)"


def zip_filtered(scenes, methods, views, bgs):
    """Zip the currently-filtered snapshots for download."""
    import zipfile
    files = _filter_snaps(scenes, methods, views, bgs)
    if not files:
        return None
    tmp = tempfile.mkdtemp()
    zpath = os.path.join(tmp, "snapshots.zip")
    with zipfile.ZipFile(zpath, "w") as z:
        for f in files:
            z.write(f, os.path.basename(f))
    return zpath


def _snap_scene_choices():
    return sorted({_snap_scene(p.name) for p in SNAP_DIR.glob("*.png")}) if SNAP_DIR.exists() else []


def _snap_method_choices():
    """Method names actually present in the snapshot dir (so ablation arms like
    prism_se3 / prism_sl4 appear in the filter, not just the hardcoded baselines)."""
    if not SNAP_DIR.exists():
        return METHODS + ["GT"]
    found = sorted({_snap_method(p.name) for p in SNAP_DIR.glob("*.png")})
    return found or (METHODS + ["GT"])


# ── Frame preview ─────────────────────────────────────────────────────────────
def list_runs():
    return sorted({str(p.parent.relative_to(EXPORTS)) for p in EXPORTS.glob("*/*/*/**/rgb")})


def _frame_names(run):
    return sorted(p.stem for p in (EXPORTS / run / "rgb").glob("*.png")) if run else []


def _depth_to_rgb(depth):
    import matplotlib.cm as cm
    d = depth.astype(np.float32); valid = d > 0
    if valid.any():
        lo, hi = np.percentile(d[valid], [2, 98])
        dn = np.clip((d - lo) / max(hi - lo, 1e-6), 0, 1)
    else:
        dn = np.zeros_like(d)
    rgb = (cm.turbo(dn)[..., :3] * 255).astype(np.uint8); rgb[~valid] = 0
    return rgb


def preview_frame(run, idx):
    import imageio.v2 as imageio
    if not run:
        return None, None, None, "Pick a run."
    base = EXPORTS / run
    names = _frame_names(run)
    if not names:
        return None, None, None, f"No frames in {run}"
    i = int(max(0, min(idx, len(names) - 1)))
    name = names[i]
    rgb = np.asarray(imageio.imread(base / "rgb" / f"{name}.png"))
    depth = np.load(base / "depth" / f"{name}.npy")
    mp = base / "mask" / f"{name}.png"
    mask = np.asarray(imageio.imread(mp)) if mp.exists() else np.zeros(depth.shape, np.uint8)
    valid = depth[depth > 0]
    dr = (f"depth {valid.min():.2f}-{valid.max():.2f} m, {100*(depth>0).mean():.0f}% valid"
          if valid.size else "⚠ 0% valid — camera outside / wrong up-axis?")
    return rgb, _depth_to_rgb(depth), mask, f"{run}\nframe {i+1}/{len(names)} ({name})\n{dr}"


# ── Point cloud viewer ────────────────────────────────────────────────────────
def list_clouds():
    items = ["pred: " + str(p.relative_to(RESULTS)) for p in RESULTS.glob("*/*/*/*/*/cloud.ply")]
    items += ["GT:   " + str(p.relative_to(EXPORTS)) for p in EXPORTS.glob("*/*/*/gt_mesh.ply")]
    return sorted(items)


def _subsample(pts, cols, n, seed=0):
    if len(pts) > n:
        idx = np.random.default_rng(seed).choice(len(pts), n, replace=False)
        return pts[idx], (cols[idx] if cols is not None else None)
    return pts, cols


def show_cloud(label, max_points, overlay_gt=False):
    import open3d as o3d
    import plotly.graph_objects as go
    if not label:
        return go.Figure()
    rel = label[6:].strip()
    path = (RESULTS / rel) if label.startswith("pred:") else (EXPORTS / rel)
    pcd = o3d.io.read_point_cloud(str(path))
    pts = np.asarray(pcd.points)
    if len(pts) == 0:
        return go.Figure(layout={"title": f"empty: {path.name}"})
    cols = np.asarray(pcd.colors) if pcd.has_colors() else None
    traces, title = [], f"{path.name}: {len(pts):,} pts"
    if overlay_gt and label.startswith("pred:"):
        try:
            from eval.eval_recon import _align_pred_to_gt, _icp_refine
            parts = Path(rel).parts
            ds, scene, traj = parts[1], parts[2], parts[3]
            gtd = EXPORTS / ds / scene / traj
            aligned, _ = _align_pred_to_gt(pts, (RESULTS / rel).parent / "poses.tum",
                                           gtd / "poses_gt.tum", True)
            gt = o3d.io.read_point_cloud(str(gtd / "gt_mesh.ply"))
            gtp = np.asarray(gt.points)
            aligned = _icp_refine(aligned, gtp, 0.15)
            pts = aligned
            gp, _ = _subsample(gtp, None, max_points, 1)
            traces.append(go.Scatter3d(x=gp[:, 0], y=gp[:, 1], z=gp[:, 2], mode="markers",
                                       name="GT", marker=dict(size=1.0, color="lightgray")))
            title += " + GT (aligned)"
        except Exception as e:
            title += f"  (overlay failed: {e})"
    sp, sc = _subsample(pts, cols, max_points)
    if sc is not None:
        mk = dict(size=1.4, color=["rgb(%d,%d,%d)" % (r*255, g*255, b*255) for r, g, b in sc])
    else:
        mk = dict(size=1.4, color=sp[:, 2], colorscale="Viridis")
    traces.append(go.Scatter3d(x=sp[:, 0], y=sp[:, 1], z=sp[:, 2], mode="markers",
                               name="reconstruction", marker=mk))
    fig = go.Figure(traces)
    fig.update_layout(scene=dict(aspectmode="data"), margin=dict(l=0, r=0, t=30, b=0),
                      title=title, showlegend=True)
    return fig


# ── Report figures (Deliverables 1 & 2: VRAM sweep + cubemap projection) ───────
def _run_fig_script(rel_script: str, extra_args: list[str]):
    """Run an eval/*.py figure script in the orchestrator env, return its combined
    stdout. Uses the studio's own interpreter (the preview env has matplotlib/numpy)."""
    cmd = [sys.executable, str(REPO_ROOT / rel_script)] + extra_args
    p = subprocess.run(cmd, cwd=str(REPO_ROOT), stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT, text=True)
    return f"$ {' '.join(cmd)}\n\n{p.stdout}\n[exit {p.returncode}]"


def _fig_gallery():
    return [str(p) for p in (FIG_DIR / "vram_vs_frames.png",
                             FIG_DIR / "cubemap_projection.png") if p.exists()]


def _fig_files():
    return [str(p) for p in FIG_ARTIFACTS.values() if p.exists()]


def gen_vram(source, scene, frames="", traj="", tile=False):
    args = ["--source", source, "--scene", scene or "auto"]
    if source == "sweep":
        args += ["--logx", "--traj", traj or "synthetic_2.0hz_s0"]
        if frames and frames.strip():
            args += ["--frames", frames.replace(" ", "")]
        if tile:
            args += ["--tile"]
    log = _run_fig_script("eval/vram_scaling.py", args)
    return log, _fig_gallery(), _fig_files()


def gen_cubemap(mode, scene, traj):
    args = ["--mode", mode]
    if scene:
        args += ["--scene", scene]
    if mode == "export":
        args += ["--traj", traj or "synthetic_2.0hz_s0"]
    log = _run_fig_script("eval/fig_cubemap.py", args)
    return log, _fig_gallery(), _fig_files()


# ── File downloader ───────────────────────────────────────────────────────────
def prepare_download(selected_path):
    import gradio as gr
    if not selected_path:
        raise gr.Error("Select a file or folder first.")
    full = os.path.abspath(selected_path)
    if not os.path.exists(full):
        raise gr.Error("Not found on the server.")
    if os.path.isfile(full):
        return full
    tmp = tempfile.mkdtemp()
    return shutil.make_archive(os.path.join(tmp, os.path.basename(full) or "archive"), "zip", root_dir=full)


def build_app():
    import gradio as gr
    with gr.Blocks(title="PRISM-benchmarks Studio") as demo:
        gr.Markdown("# 🛠️ PRISM-benchmarks Studio")

        with gr.Tab("▶ Pipeline (one button)"):
            gr.Markdown("Configure and run the **whole benchmark** end-to-end: "
                        "render → export → run methods → eval → report (→ snapshots). "
                        "Output streams live; the log is downloadable.")
            r0, s0, m0, _f0, _n0 = load_config_fields()
            default_scenes = s0 if len(s0.split()) >= 2 else "office_4 apartment_0"
            with gr.Row():
                pl_scenes = gr.Textbox(value=default_scenes, label="Scenes (space-separated)", scale=2)
                pl_rates = gr.Textbox(value=(r0 or "0.5,2.0,5.0"), label="Rates Hz (comma)", scale=1)
                pl_maxf = gr.Number(value=m0, label="max_frames (0=all)", precision=0, scale=1)
            pl_methods = gr.CheckboxGroup(METHODS, value=METHODS, label="Methods to run")
            with gr.Row():
                pl_clean = gr.Checkbox(value=True, label="Clean previous results first")
                pl_snap = gr.Checkbox(value=True, label="Render snapshots at the end")
            pl_btn = gr.Button("▶  Run FULL pipeline", variant="primary")
            pl_out = gr.Textbox(label="Live output", lines=22, autoscroll=True)
            pl_log = gr.File(label="Download log", interactive=False)
            pl_btn.click(full_pipeline, [pl_scenes, pl_methods, pl_rates, pl_maxf, pl_clean, pl_snap],
                         [pl_out, pl_log])

        with gr.Tab("Run targets (advanced)"):
            gr.Markdown("Tick targets and run. Output streams live; the log is downloadable. "
                        "Typical order: setup → render → export → run-* → eval-* → report → snapshots.")
            tsel = gr.CheckboxGroup(MAKE_TARGETS, label="make targets (run in order)")
            with gr.Row():
                sc = gr.Textbox(label="SCENES (optional)", scale=1)
                tj = gr.Textbox(value="all", label="TRAJ", scale=1)
            run_btn = gr.Button("Run selected", variant="primary")
            out = gr.Textbox(label="Live output", lines=24, autoscroll=True)
            logf = gr.File(label="Download log", interactive=False)
            run_btn.click(run_targets, [tsel, sc, tj], [out, logf])

        with gr.Tab("Config"):
            gr.Markdown("Edits are saved to **config.local.yaml** (gitignored, merged over "
                        "config.yaml) — survives `git pull`.")
            r0, s0, m0, f0, n0 = load_config_fields()
            rates = gr.Textbox(value=r0, label="rates_hz (comma-separated capture rates)")
            scenes = gr.Textbox(value=s0, label="replica scenes (space-separated; blank = keep)")
            maxf = gr.Number(value=m0, label="baselines.max_frames (0 = all)", precision=0)
            fscore = gr.Number(value=f0, label="eval F-score threshold (m)")
            noise = gr.Number(value=n0, label="cleanliness noise threshold (m)")
            save_btn = gr.Button("Save overlay", variant="primary")
            cfg_out = gr.Textbox(label="Saved overlay", lines=10)
            save_btn.click(save_config_fields, [rates, scenes, maxf, fscore, noise], cfg_out)

        with gr.Tab("Snapshots"):
            gr.Markdown("Standardized paper images — every cloud aligned to GT (ground on "
                        "floor), ceiling clipped, black & white backgrounds.")
            with gr.Row():
                keep_h = gr.Slider(0.0, 3.0, value=2.0, step=0.1, label="Keep height (m)")
                snap_maxp = gr.Slider(20000, 400000, value=150000, step=10000, label="Max points")
                snap_ptsize = gr.Slider(0.5, 15.0, value=5.0, step=0.5, label="Point size")
            snap_btn = gr.Button("Generate snapshots (all methods × scenes × rates)", variant="primary")
            gr.Markdown("**Filter (multi-select; empty = all) + paginate:**")
            with gr.Row():
                f_scene = gr.Dropdown(_snap_scene_choices(), value=[], multiselect=True, label="Scenes")
                f_method = gr.Dropdown(_snap_method_choices(), value=[], multiselect=True, label="Methods")
            with gr.Row():
                f_view = gr.Dropdown(["oblique", "top"], value=["oblique"], multiselect=True, label="Views")
                f_bg = gr.Dropdown(["black", "white"], value=["white"], multiselect=True, label="Backgrounds")
                f_page = gr.Number(value=1, precision=0, label="Page")
                show_btn = gr.Button("Show / next page", variant="primary")
            snap_status = gr.Markdown("")
            gallery = gr.Gallery(label="Snapshots", columns=4, height=560)
            with gr.Row():
                dl_btn = gr.Button("Zip filtered for download")
                snap_zip = gr.File(label="Download", interactive=False)

            def _gen(kh, mp, ps):
                from eval import snapshots
                snapshots.generate(load_config("config.yaml"), keep_h=float(kh),
                                   max_points=int(mp), point_size=float(ps))
                imgs, status = snap_page([], [], ["oblique"], ["white"], 1)
                return (imgs, status, gr.update(choices=_snap_scene_choices()),
                        gr.update(choices=_snap_method_choices()))

            snap_btn.click(_gen, [keep_h, snap_maxp, snap_ptsize],
                           [gallery, snap_status, f_scene, f_method])
            show_btn.click(snap_page, [f_scene, f_method, f_view, f_bg, f_page], [gallery, snap_status])
            dl_btn.click(zip_filtered, [f_scene, f_method, f_view, f_bg], snap_zip)
            demo.load(lambda: snap_page([], [], ["oblique"], ["white"], 1), None, [gallery, snap_status])

        with gr.Tab("Point cloud"):
            clouds = list_clouds()
            with gr.Row():
                cdd = gr.Dropdown(choices=clouds, value=(clouds[0] if clouds else None), label="Cloud")
                cmax = gr.Slider(5000, 300000, value=80000, step=5000, label="Max points")
                cov = gr.Checkbox(value=False, label="Overlay GT (aligned)")
            cplot = gr.Plot(label="3D view (drag to orbit)")
            for ev in (cdd.change, cmax.change, cov.change):
                ev(show_cloud, [cdd, cmax, cov], cplot)
            gr.Button("Refresh clouds").click(lambda: gr.update(choices=list_clouds()), None, cdd)
            demo.load(show_cloud, [cdd, cmax, cov], cplot)

        with gr.Tab("Frame preview"):
            runs = list_runs()
            with gr.Row():
                run = gr.Dropdown(choices=runs, value=(runs[0] if runs else None), label="Run")
                n0f = max(len(_frame_names(runs[0])) - 1, 1) if runs else 1
                idx = gr.Slider(0, n0f, value=0, step=1, label="Frame index")
            info = gr.Textbox(label="Info", interactive=False)
            with gr.Row():
                im_rgb = gr.Image(label="RGB"); im_d = gr.Image(label="Depth"); im_m = gr.Image(label="Mask")

            def on_run(r):
                n = max(len(_frame_names(r)) - 1, 1)
                a, b, c, t = preview_frame(r, 0)
                return gr.update(maximum=n, value=0), a, b, c, t
            run.change(on_run, [run], [idx, im_rgb, im_d, im_m, info])
            idx.change(preview_frame, [run, idx], [im_rgb, im_d, im_m, info])
            demo.load(on_run, [run], [idx, im_rgb, im_d, im_m, info])

        with gr.Tab("Report figures"):
            gr.Markdown(
                "Regenerate the two report figures on demand and download them "
                "(**vram_vs_frames.png** + **vram_scaling.csv**, **cubemap_projection.png**). "
                "They land in `results/figures/`.\n\n"
                "* **VRAM — perf.csv**: reproducible from the committed seeded run, on real "
                "benchmark scenes (no GPU). "
                "* **VRAM — sweep**: on-GPU prefix sweep — pick the frame grid (e.g. "
                "`1,2,4,…,256`); each method's curve stops at its real OOM cap (needs exports "
                "+ method envs). "
                "* **Cubemap — schematic**: labelled preview (no GPU). "
                "* **Cubemap — export**: real engine intermediates on a real pano frame "
                "(needs the PRISM-VGGT env).")
            with gr.Row():
                fig_scene = gr.Textbox(value="auto", label="Scene ('auto' = best-covered)", scale=2)
                fig_traj = gr.Textbox(value="synthetic_2.0hz_s0", label="Traj (sweep/export)", scale=2)
            with gr.Row():
                fig_frames = gr.Textbox(value="1,2,4,8,16,32,64,128,256",
                                        label="Sweep frame grid (comma-separated)", scale=3)
                fig_tile = gr.Checkbox(value=False, label="Tile past render length (for large counts)")
            with gr.Row():
                b_vram = gr.Button("VRAM — from perf.csv", variant="primary")
                b_vram_sweep = gr.Button("VRAM — on-GPU sweep", variant="primary")
                b_cube = gr.Button("Cubemap — schematic")
                b_cube_exp = gr.Button("Cubemap — engine export")
            fig_log = gr.Textbox(label="Output", lines=12, autoscroll=True)
            fig_gallery = gr.Gallery(label="Figures", columns=2, height=420)
            fig_files = gr.Files(label="Download artifacts", interactive=False)
            b_vram.click(lambda s: gen_vram("perf-csv", s), [fig_scene],
                         [fig_log, fig_gallery, fig_files])
            b_vram_sweep.click(lambda s, fr, t, tl: gen_vram("sweep", s, fr, t, tl),
                               [fig_scene, fig_frames, fig_traj, fig_tile],
                               [fig_log, fig_gallery, fig_files])
            b_cube.click(lambda s, t: gen_cubemap("illustrative", s, t), [fig_scene, fig_traj],
                         [fig_log, fig_gallery, fig_files])
            b_cube_exp.click(lambda s, t: gen_cubemap("export", s, t), [fig_scene, fig_traj],
                             [fig_log, fig_gallery, fig_files])
            demo.load(lambda: (_fig_gallery(), _fig_files()), None, [fig_gallery, fig_files])

        with gr.Tab("Downloads"):
            explorer = gr.FileExplorer(root_dir=str(REPO_ROOT), ignore_glob=".*",
                                       file_count="single", label="Server filesystem")
            dl = gr.File(label="Download ready", interactive=False)
            gr.Button("Prepare download", variant="primary").click(prepare_download, explorer, dl)
    return demo


def launch():
    # allowed_paths so gr.File can serve zips/logs from tmp + the repo (downloads).
    build_app().launch(server_name="0.0.0.0", server_port=7860, share=True,
                       allowed_paths=[tempfile.gettempdir(), str(REPO_ROOT)])


if __name__ == "__main__":
    launch()

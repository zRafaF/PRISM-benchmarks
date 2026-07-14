#!/usr/bin/env python
"""Preview + download server for rendered frames and results.

A small Gradio app (modelled on PRISM's apps/downloader.py) so you can, from a
browser, (1) eyeball rendered frames — pano RGB, colour-mapped depth, validity
mask, pinhole RGB — to confirm a render is correct before running a method, and
(2) download any export/results file or folder (folders come back zipped).

Run from the repo root (through uv):  make preview
It prints a public share URL (share=True), handy when the box is remote.
"""
from __future__ import annotations

import os
import shutil
import sys
import tempfile
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bench.config import REPO_ROOT

EXPORTS = REPO_ROOT / "dataset" / "exports"
RESULTS = REPO_ROOT / "results"


def list_runs() -> list[str]:
    """Every rendered camera dir that has frames, as 'dataset/scene/traj/camera[/variant]'."""
    runs = []
    for rgb_dir in EXPORTS.glob("*/*/*/**/rgb"):
        runs.append(str(rgb_dir.parent.relative_to(EXPORTS)))
    return sorted(set(runs))


def _depth_to_rgb(depth: np.ndarray) -> np.ndarray:
    import matplotlib.cm as cm
    d = depth.astype(np.float32)
    valid = d > 0
    if valid.any():
        lo, hi = np.percentile(d[valid], [2, 98])
        dn = np.clip((d - lo) / max(hi - lo, 1e-6), 0, 1)
    else:
        dn = np.zeros_like(d)
    rgb = (cm.turbo(dn)[..., :3] * 255).astype(np.uint8)
    rgb[~valid] = 0
    return rgb


def list_clouds() -> list[str]:
    """Reconstructed clouds under results/ + the GT meshes under exports/ (viewable
    as their vertex clouds), labelled so you can compare pred vs. GT."""
    items = []
    for p in RESULTS.glob("*/*/*/*/*/cloud.ply"):
        items.append("pred: " + str(p.relative_to(RESULTS)))
    for p in EXPORTS.glob("*/*/*/gt_mesh.ply"):
        items.append("GT:   " + str(p.relative_to(EXPORTS)))
    return sorted(items)


def _subsample(pts, cols, max_points, seed=0):
    if len(pts) > max_points:
        idx = np.random.default_rng(seed).choice(len(pts), max_points, replace=False)
        return pts[idx], (cols[idx] if cols is not None else None)
    return pts, cols


def _align_pred_for_overlay(rel: str, pred_pts):
    """Register a pred cloud into the GT frame (Sim(3)+ICP, same as eval) so it can
    be overlaid on the original scene. Returns (aligned_pred, gt_pts, gt_cols) or None."""
    import open3d as o3d
    from eval.eval_recon import _align_pred_to_gt, _icp_refine
    parts = Path(rel).parts                      # method/ds/scene/traj/variant/cloud.ply
    ds, scene, traj = parts[1], parts[2], parts[3]
    gt_dir = EXPORTS / ds / scene / traj
    pred_tum = (RESULTS / rel).parent / "poses.tum"
    gt_tum = gt_dir / "poses_gt.tum"
    gt_mesh = gt_dir / "gt_mesh.ply"
    if not (pred_tum.exists() and gt_tum.exists() and gt_mesh.exists()):
        return None
    aligned, _ = _align_pred_to_gt(pred_pts, pred_tum, gt_tum, True)
    gt = o3d.io.read_point_cloud(str(gt_mesh))
    gt_pts = np.asarray(gt.points)
    aligned = _icp_refine(aligned, gt_pts, 0.15)
    gt_cols = np.asarray(gt.colors) if gt.has_colors() else None
    return aligned, gt_pts, gt_cols


def show_cloud(label: str, max_points: int, overlay_gt: bool = False):
    """Interactive Plotly 3D scatter of a cloud (RGB if present, else height-coloured).
    With overlay_gt, a pred cloud is aligned to the GT scene and both are shown."""
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

    traces = []
    title = f"{path.name}: {len(pts):,} pts"
    if overlay_gt and label.startswith("pred:"):
        try:
            res = _align_pred_for_overlay(rel, pts)
        except Exception as e:
            res = None
            title += f"  (overlay failed: {e})"
        if res is not None:
            pts, gt_pts, gt_cols = res
            gpts, _ = _subsample(gt_pts, None, max_points, seed=1)
            traces.append(go.Scatter3d(x=gpts[:, 0], y=gpts[:, 1], z=gpts[:, 2], mode="markers",
                                       name="GT scene", marker=dict(size=1.0, color="lightgray")))
            title += " + GT (aligned)"

    spts, scols = _subsample(pts, cols, max_points)
    if scols is not None:
        marker = dict(size=1.4, color=["rgb(%d,%d,%d)" % (r * 255, g * 255, b * 255) for r, g, b in scols])
    else:
        marker = dict(size=1.4, color=spts[:, 2], colorscale="Viridis")
    traces.append(go.Scatter3d(x=spts[:, 0], y=spts[:, 1], z=spts[:, 2], mode="markers",
                               name="reconstruction", marker=marker))
    fig = go.Figure(traces)
    fig.update_layout(scene=dict(aspectmode="data"), margin=dict(l=0, r=0, t=30, b=0),
                      title=title, showlegend=True)
    return fig


def _frame_names(run: str) -> list[str]:
    if not run:
        return []
    return sorted(p.stem for p in (EXPORTS / run / "rgb").glob("*.png"))


def preview_frame(run: str, idx: int):
    import imageio.v2 as imageio
    if not run:
        return None, None, None, "Pick a run."
    base = EXPORTS / run
    names = _frame_names(run)
    if not names:
        return None, None, None, f"No frames in {run}"
    i = int(max(0, min(idx, len(names) - 1)))     # clamp — never index out of range
    name = names[i]
    rgb = np.asarray(imageio.imread(base / "rgb" / f"{name}.png"))
    depth = np.load(base / "depth" / f"{name}.npy")
    mask_p = base / "mask" / f"{name}.png"
    mask = np.asarray(imageio.imread(mask_p)) if mask_p.exists() else np.zeros(depth.shape, np.uint8)
    valid = depth[depth > 0]
    valid_pct = 100.0 * (depth > 0).mean()
    if valid.size:
        drange = f"depth {valid.min():.2f}–{valid.max():.2f} m, {valid_pct:.0f}% valid"
    else:
        drange = "⚠ 0% valid — every ray missed the mesh (camera outside / wrong up-axis?)"
    info = f"{run}\nframe {i+1}/{len(names)} ({name})\n{drange}"
    return rgb, _depth_to_rgb(depth), mask, info


def prepare_download(selected_path: str):
    """Return a file directly, or zip a directory into a temp file (like downloader.py)."""
    import gradio as gr
    if not selected_path:
        raise gr.Error("Select a file or folder first.")
    full = os.path.abspath(selected_path)
    if not os.path.exists(full):
        raise gr.Error("Not found on the server.")
    if os.path.isfile(full):
        return full
    tmp = tempfile.mkdtemp()
    base = os.path.join(tmp, os.path.basename(full) or "archive")
    return shutil.make_archive(base, "zip", root_dir=full)


def build_app():
    import gradio as gr
    runs = list_runs()
    with gr.Blocks(title="PRISM-benchmarks preview") as demo:
        gr.Markdown("# 🖼️ PRISM-benchmarks — render preview & download")
        with gr.Tab("Frame preview"):
            with gr.Row():
                run = gr.Dropdown(choices=runs, label="Run (dataset/scene/traj/camera)",
                                  value=(runs[0] if runs else None))
                n0 = max(len(_frame_names(runs[0])) - 1, 0) if runs else 0
                idx = gr.Slider(0, max(n0, 1), value=0, step=1, label="Frame index")
            info = gr.Textbox(label="Info", interactive=False)
            with gr.Row():
                img_rgb = gr.Image(label="RGB", type="numpy")
                img_depth = gr.Image(label="Depth (turbo)", type="numpy")
                img_mask = gr.Image(label="Validity mask", type="numpy")

            def on_run(r):
                # fit the slider to the actual frame count, reset to 0, show frame 0
                n = max(len(_frame_names(r)) - 1, 0)
                rgb, dep, msk, txt = preview_frame(r, 0)
                return gr.update(maximum=max(n, 1), value=0), rgb, dep, msk, txt

            run.change(on_run, [run], [idx, img_rgb, img_depth, img_mask, info])
            idx.change(preview_frame, [run, idx], [img_rgb, img_depth, img_mask, info])
            demo.load(on_run, [run], [idx, img_rgb, img_depth, img_mask, info])
            gr.Button("Refresh runs").click(lambda: gr.update(choices=list_runs()), None, run)
        with gr.Tab("Point cloud"):
            gr.Markdown("View a reconstructed cloud (`pred:`) or a GT mesh's vertices "
                        "(`GT:`). Note: pred is in its OWN frame; eval aligns it to GT, "
                        "this raw view does not.")
            clouds = list_clouds()
            with gr.Row():
                cloud_dd = gr.Dropdown(choices=clouds, label="Cloud",
                                       value=(clouds[0] if clouds else None))
                maxp = gr.Slider(5000, 300000, value=80000, step=5000, label="Max points")
                overlay = gr.Checkbox(value=False, label="Overlay GT scene (aligned)")
            plot = gr.Plot(label="3D view (drag to orbit)")
            for ev in (cloud_dd.change, maxp.change, overlay.change):
                ev(show_cloud, [cloud_dd, maxp, overlay], plot)
            gr.Button("Refresh clouds").click(lambda: gr.update(choices=list_clouds()), None, cloud_dd)
            demo.load(show_cloud, [cloud_dd, maxp, overlay], plot)

        with gr.Tab("Download files"):
            gr.Markdown("Browse `dataset/exports` and `results`. File → direct download; "
                        "folder → zipped.")
            explorer = gr.FileExplorer(root_dir=str(REPO_ROOT), ignore_glob=".*",
                                       file_count="single", label="Server filesystem")
            out = gr.File(label="Download ready", interactive=False)
            gr.Button("Prepare download", variant="primary").click(prepare_download, explorer, out)
    return demo


if __name__ == "__main__":
    build_app().launch(server_name="0.0.0.0", server_port=7860, share=True)

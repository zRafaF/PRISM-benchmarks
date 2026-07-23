#!/usr/bin/env python
"""Per-view vs fused figure (fig-fusion) — fusion is the ONLY variable.

Matches the report's fig-fusion caption: feed-forward models emit a separate point map
per view; these overlap, duplicate the same surfaces, and carry per-pixel noise. Fusing
the posed depth into one volumetric surface removes the duplication and yields a single,
consistent, compact map. The figure must make the point with the SAME backbone and the
SAME frames on both sides — only the fusion differs.

Exports TWO matched, text-free panels (no titles/arrows/captions — the report composes
those in Typst), from ONE fixed oblique camera, white background, identical framing:

  fusion_perview.png   raw per-view geometry (overlapping, duplicated, floater-laden)
  fusion_fused.png     the single clean fused surface of the SAME frames
  fusion.txt           provenance / caption sidecar

Two sources:

  --mode dataset  (default, no GPU/engine)
      Take one window of overlapping frames from a seeded scene's pano export and
      back-project the render's GT depth through the GT poses. LEFT = every frame's
      points concatenated (no fusion → overlap + duplication + edge floaters); RIGHT =
      the SAME points voxel-fused at voxel_size (one point per cell → compact surface).
      Same backbone (the render), same frames, same camera; only fusion changes.
      Caveat: GT depth is noise-free, so the per-pixel *noise* is understated vs a real
      feed-forward net (the duplication / redundancy / compactness story is exact).

  --mode results  (uses the benchmark output clouds — real engine geometry)
      LEFT = results/panovggt/... (the raw full-batch PanoVGGT point map, no PRISM
      fusion); RIGHT = results/prism/... (the nvblox-fused surface from the SAME
      backbone over the SAME sequence). Rendered with the snapshot pipeline, GT-aligned.

Reuses eval/snapshots._render so viewpoint / background / point size / framing are
IDENTICAL to the benchmark snapshots. Seeded data only.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bench.config import REPO_ROOT, load_config
from eval.snapshots import _render, _subsample, _clip_ceiling, VIEWS
from eval.fig_cubemap import _equirect_pixel_dirs, _load_tum

DEFAULT_OUT = REPO_ROOT / "results" / "figures"


def _voxel_dedup(pts: np.ndarray, cols: np.ndarray, voxel: float):
    """One point per occupied voxel (the fusion proxy) — same hashing as the streaming
    fuser (adapters/runners/_stream.fuse_pointmaps), colours carried along."""
    if len(pts) == 0:
        return pts, cols
    keys = np.floor(pts / voxel).astype(np.int64)
    h = (keys[:, 0] * 73856093) ^ (keys[:, 1] * 19349663) ^ (keys[:, 2] * 83492791)
    _, idx = np.unique(h, return_index=True)
    return pts[idx], (cols[idx] if cols is not None else None)


def _backproject_window(pano_dir: Path, start: int, window: int, cfg, stride: int):
    """Concatenate posed, metric per-frame point clouds (GT depth back-projected via GT
    poses) for a window of overlapping frames. Returns (points_world, colors)."""
    import imageio.v2 as imageio
    names = sorted(p.stem for p in (pano_dir / "rgb").glob("*.png"))
    if not names:
        raise SystemExit(f"[fig-fusion] no pano frames at {pano_dir} — run `make render export` first.")
    poses = _load_tum(pano_dir.parent / "poses_gt.tum")
    if not poses:
        raise SystemExit(f"[fig-fusion] no GT poses at {pano_dir.parent/'poses_gt.tum'} — "
                         "dataset mode needs posed frames to place the per-view clouds.")
    end = min(len(names), start + window)
    idxs = list(range(start, end))
    max_depth = float(cfg["engine"]["max_depth"])
    P, C = [], []
    dirs = None
    for i in idxs:
        nm = names[i]
        dp = pano_dir / "depth" / f"{nm}.npy"
        if not dp.exists():
            continue
        d = np.load(dp).astype(np.float32)
        rgb = np.asarray(imageio.imread(pano_dir / "rgb" / f"{nm}.png"))[..., :3]
        if dirs is None or dirs.shape[:2] != d.shape:
            dirs = _equirect_pixel_dirs(*d.shape)
        pts_cam = dirs * d[..., None]
        valid = (d > 0) & (d <= max_depth)
        pc = pts_cam[valid][::stride]
        col = rgb[valid][::stride].astype(np.float32) / 255.0
        T = poses.get(i, np.eye(4))
        P.append((T[:3, :3] @ pc.T).T + T[:3, 3])
        C.append(col)
    if not P:
        raise SystemExit("[fig-fusion] no depth frames found in the window.")
    return np.concatenate(P), np.concatenate(C), idxs


def _shared_limits(pts, keep_h):
    floor_z = float(np.percentile(pts[:, 2], 1.0))
    clipped, _ = _clip_ceiling(pts, None, floor_z, keep_h)
    ref = clipped if len(clipped) else pts
    pad = 0.2
    return ((ref[:, 0].min() - pad, ref[:, 0].max() + pad),
            (ref[:, 1].min() - pad, ref[:, 1].max() + pad),
            (floor_z - 0.05, floor_z + keep_h)), floor_z


def _dataset_panels(cfg, scene, traj, start, window, stride, keep_h, max_points, point_size, out):
    from bench.config import export_dir
    ds = cfg["datasets"]["active"][0]
    pano = export_dir(ds, scene, traj, "pano", "")
    voxel = float(cfg["engine"]["voxel_size"])
    pv_pts, pv_cols, idxs = _backproject_window(pano, start, window, cfg, stride)
    fu_pts, fu_cols = _voxel_dedup(pv_pts, pv_cols, voxel)
    print(f"[fig-fusion] window {scene}/{traj} frames {idxs[0]}–{idxs[-1]} "
          f"({len(idxs)} frames): per-view {len(pv_pts):,} pts -> fused {len(fu_pts):,} pts "
          f"(voxel {voxel} m, {len(pv_pts)/max(len(fu_pts),1):.1f}x reduction)", flush=True)

    limits, _ = _shared_limits(pv_pts, keep_h)   # SAME framing for both panels
    view = VIEWS["oblique"]
    pv_c, pvc_c = _clip_ceiling(pv_pts, pv_cols, limits[2][0] + 0.05, keep_h)
    fu_c, fuc_c = _clip_ceiling(fu_pts, fu_cols, limits[2][0] + 0.05, keep_h)
    pv_c, pvc_c = _subsample(pv_c, pvc_c, max_points)
    fu_c, fuc_c = _subsample(fu_c, fuc_c, max_points)
    out.mkdir(parents=True, exist_ok=True)
    _render(pv_c, pvc_c, limits, view, "white", out / "fusion_perview.png", point_size, label="")
    _render(fu_c, fuc_c, limits, view, "white", out / "fusion_fused.png", point_size, label="")
    print(f"[fig-fusion] wrote {out/'fusion_perview.png'}", flush=True)
    print(f"[fig-fusion] wrote {out/'fusion_fused.png'}", flush=True)
    meta = (f"Real dataset export — {scene}/{traj} frames {idxs[0]}–{idxs[-1]}, "
            f"oblique view, voxel={voxel} m, max_depth={cfg['engine']['max_depth']} m. "
            "Same backbone (rendered GT depth) + same frames both panels; only fusion "
            "differs (left = per-view concat, right = voxel-fused). GT depth is noise-free "
            "(optimistic vs. real capture) — the duplication/compactness contrast is exact, "
            "per-pixel noise is understated.")
    (out / "fusion.txt").write_text(meta + "\n")
    print(f"[fig-fusion] caption -> {out/'fusion.txt'}", flush=True)


def _results_panels(cfg, scene, traj, variant, keep_h, max_points, point_size, out):
    """Render the real benchmark clouds: panovggt (per-view/no-fusion) vs prism (fused),
    GT-aligned, shared framing — same backbone, fusion is the only difference."""
    import open3d as o3d
    from eval.eval_recon import _align_pred_to_gt, _export_base
    ds = cfg["datasets"]["active"][0]
    base = _export_base(ds, scene, traj)
    gt_tum = base / "poses_gt.tum"
    gt_mesh = base / "gt_mesh.ply"
    correct_scale = cfg["eval"]["align"]["correct_scale"]

    def _load_align(method):
        for var in ([variant] if variant else ["pano", "synthetic_fov", "real_intrinsics"]):
            c = REPO_ROOT / "results" / method / ds / scene / traj / var / "cloud.ply"
            if c.exists():
                pcd = o3d.io.read_point_cloud(str(c))
                pts = np.asarray(pcd.points)
                cols = np.asarray(pcd.colors) if pcd.has_colors() else None
                if len(pts) and gt_tum.exists():
                    pts, _ = _align_pred_to_gt(pts, c.parent / "poses.tum", gt_tum, correct_scale)
                return pts, cols, c
        return None, None, None

    pv_pts, pv_cols, pv_path = _load_align("panovggt")
    fu_pts, fu_cols, fu_path = _load_align("prism")
    if pv_pts is None or fu_pts is None:
        raise SystemExit("[fig-fusion] results mode needs results/panovggt/... and "
                         "results/prism/... clouds for this scene/traj — run those methods first.")
    ref = np.asarray(o3d.io.read_point_cloud(str(gt_mesh)).points) if gt_mesh.exists() else fu_pts
    limits, floor_z = _shared_limits(ref, keep_h)
    view = VIEWS["oblique"]
    out.mkdir(parents=True, exist_ok=True)
    for pts, cols, name in ((pv_pts, pv_cols, "fusion_perview.png"),
                            (fu_pts, fu_cols, "fusion_fused.png")):
        p, c = _clip_ceiling(pts, cols, floor_z, keep_h)
        p, c = _subsample(p, c, max_points)
        _render(p, c, limits, view, "white", out / name, point_size, label="")
        print(f"[fig-fusion] wrote {out/name}", flush=True)
    (out / "fusion.txt").write_text(
        f"Real engine clouds — per-view={pv_path.relative_to(REPO_ROOT)}, "
        f"fused={fu_path.relative_to(REPO_ROOT)}; {scene}/{traj}, oblique, GT-aligned. "
        "Same PanoVGGT backbone both panels; only PRISM's fusion differs. Rendered scene "
        "(noise-free; optimistic vs. real capture).\n")
    print(f"[fig-fusion] caption -> {out/'fusion.txt'}", flush=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--mode", choices=["dataset", "results"], default="dataset")
    ap.add_argument("--config", default="config.yaml")
    ap.add_argument("--scene", default="")
    ap.add_argument("--traj", default="synthetic_5.0hz_s0",
                    help="dense (high-overlap) seeded traj is best for the per-view story")
    ap.add_argument("--variant", default="", help="results mode: cloud variant (pano/synthetic_fov)")
    ap.add_argument("--frame-start", type=int, default=0)
    ap.add_argument("--window", type=int, default=0, help="0 = config engine.window_size")
    ap.add_argument("--stride", type=int, default=3, help="pixel stride when back-projecting")
    ap.add_argument("--keep-height", type=float, default=2.0)
    ap.add_argument("--max-points", type=int, default=400000)
    ap.add_argument("--point-size", type=float, default=5.0)
    ap.add_argument("--out-dir", default=str(DEFAULT_OUT))
    args = ap.parse_args()
    cfg = load_config(args.config)
    scene = args.scene if args.scene and args.scene != "auto" else \
        (cfg["datasets"].get("replica", {}).get("scenes") or ["scene"])[0]
    window = args.window or int(cfg["engine"]["window_size"])
    out = Path(args.out_dir)
    print(f"[fig-fusion] mode={args.mode} scene={scene} traj={args.traj}", flush=True)

    if args.mode == "dataset":
        _dataset_panels(cfg, scene, args.traj, args.frame_start, window, args.stride,
                        args.keep_height, args.max_points, args.point_size, out)
    else:
        _results_panels(cfg, scene, args.traj, args.variant, args.keep_height,
                        args.max_points, args.point_size, out)


if __name__ == "__main__":
    main()

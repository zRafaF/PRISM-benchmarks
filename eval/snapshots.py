"""Standardized point-cloud snapshots for the paper.

For every reconstructed cloud (and the GT), this renders fixed, comparable images:
  * aligned to the GT frame (Sim(3)+ICP) so orientation is IDENTICAL for all methods
    ("ground on the floor" — fixes the tilted baseline clouds),
  * optional ceiling removal so the room interior is visible from above,
  * a couple of fixed viewpoints, on BOTH black and white backgrounds,
  * identical axis framing per scene/traj so methods are directly comparable.

Headless-safe: uses matplotlib (Agg), not an Open3D GL window. Output ->
results/report/snapshots/<method>__<scene>_<traj>_<variant>__<mask>__<view>__<bg>.png

CO-VISIBILITY MASK VARIANTS
---------------------------
A panoramic cloud looks far more complete than a pinhole one simply because it saw
more, so an unmasked side-by-side flatters PRISM for a reason that has nothing to do
with reconstruction quality. The scored comparison uses the co-visibility mask
(eval/visibility_mask.py); these renders make that visible instead of implicit:

  full    every point the method produced — credits full 360deg coverage
  covis   kept points in colour + masked-away points in desaturated grey at low
          opacity — the honest figure, showing what was discarded to make the
          comparison fair rather than quietly deleting it
  masked  only the kept points — exactly the geometry the masked F-score scored

IMPORTANT: the mask here is computed on the ceiling-clipped, subsampled cloud that
gets rendered, so it is a faithful *visualisation* of the eval mask, not a
bit-identical reproduction of it. Do not quote point counts off these images — the
numbers come from eval_recon, which masks the full cloud.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bench.config import REPO_ROOT, load_config
from eval.eval_recon import _align_pred_to_gt, _icp_refine, _export_base
from eval.visibility_mask import build_mask

VIEWS = {"oblique": dict(elev=55, azim=-60), "top": dict(elev=88, azim=-90)}
MASK_VARIANTS = ("full", "covis", "masked")

# How the masked-away points are drawn in the "covis" variant. Grey + low alpha reads
# as "present but excluded" without competing with the kept geometry for attention.
DROPPED_GREY = 0.55
DROPPED_ALPHA = 0.18
DROPPED_SIZE_SCALE = 0.7


def _load_points(path: Path):
    import open3d as o3d
    pcd = o3d.io.read_point_cloud(str(path))
    pts = np.asarray(pcd.points)
    cols = np.asarray(pcd.colors) if pcd.has_colors() else None
    return pts, cols


def _clip_ceiling(pts, cols, floor_z, keep_h):
    if keep_h <= 0:
        return pts, cols
    m = pts[:, 2] <= (floor_z + keep_h)
    return pts[m], (cols[m] if cols is not None else None)


def _subsample(pts, cols, n, extra=None):
    """Subsample points (+ colours, + an optional parallel boolean array)."""
    if len(pts) > n:
        idx = np.random.default_rng(0).choice(len(pts), n, replace=False)
        return (pts[idx], (cols[idx] if cols is not None else None),
                (extra[idx] if extra is not None else None))
    return pts, cols, extra


def _point_colours(pts, cols):
    """Real RGB when the cloud has it; height-coloured otherwise so it's never flat."""
    import matplotlib.cm as cm
    if cols is not None and len(cols) == len(pts):
        c = np.clip(np.asarray(cols, dtype=float), 0, 1)
        return c / 255.0 if c.max() > 1.0 else c
    z = pts[:, 2]
    zn = (z - z.min()) / max(float(z.max() - z.min()), 1e-6)
    return cm.viridis(zn)[:, :3]


def _render(pts, cols, limits, view, bg, out_path, point_size, label="",
            keep=None, mask_variant="full", dropped_grey=DROPPED_GREY,
            dropped_alpha=DROPPED_ALPHA):
    """Render one image.

    `keep` is the co-visibility boolean over `pts`; `mask_variant` selects how it is
    applied — see the module docstring. When variant == "covis" the dropped points are
    drawn FIRST, in grey at low alpha, so the kept geometry layers on top of them.
    (matplotlib's 3D axes don't depth-sort across separate scatter calls, so draw
    order is what puts the excluded points visually behind.)
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fg = "white" if bg == "black" else "black"
    fig = plt.figure(figsize=(6, 6), facecolor=bg)
    ax = fig.add_subplot(111, projection="3d")
    ax.set_facecolor(bg)

    if keep is None or mask_variant == "full":
        shown, shown_cols, dropped = pts, cols, None
    elif mask_variant == "masked":
        shown = pts[keep]
        shown_cols = cols[keep] if cols is not None else None
        dropped = None
    else:                                    # "covis"
        shown = pts[keep]
        shown_cols = cols[keep] if cols is not None else None
        dropped = pts[~keep]

    if dropped is not None and len(dropped):
        ax.scatter(dropped[:, 0], dropped[:, 1], dropped[:, 2],
                   c=[[dropped_grey] * 3], s=point_size * DROPPED_SIZE_SCALE,
                   marker="o", linewidths=0, depthshade=False, alpha=dropped_alpha)
    if len(shown):
        ax.scatter(shown[:, 0], shown[:, 1], shown[:, 2],
                   c=_point_colours(shown, shown_cols),
                   s=point_size, marker="o", linewidths=0, depthshade=False)
    (xlo, xhi), (ylo, yhi), (zlo, zhi) = limits
    ax.set_xlim(xlo, xhi); ax.set_ylim(ylo, yhi); ax.set_zlim(zlo, zhi)
    ax.set_box_aspect((xhi - xlo, yhi - ylo, zhi - zlo))
    ax.view_init(elev=view["elev"], azim=view["azim"])
    ax.set_axis_off()
    if label:
        fig.text(0.5, 0.965, label, ha="center", va="top", color=fg,
                 fontsize=13, fontweight="bold")
    fig.tight_layout(pad=0)
    fig.savefig(out_path, dpi=150, facecolor=bg, bbox_inches="tight", pad_inches=0.05)
    plt.close(fig)


def _covis_keep(pts, dataset, scene, traj, cfg):
    """Co-visibility keep-mask for a cloud, or None if the pinhole export is absent.

    Uses the SAME build_mask + the same pinhole variant that eval_recon scores with,
    so the picture and the number tell the same story.
    """
    pin_dir = _export_base(dataset, scene, traj) / "pinhole"
    variants = sorted(p for p in pin_dir.glob("*") if p.is_dir()) if pin_dir.exists() else []
    if not variants:
        return None
    try:
        return build_mask(pts, variants[0], cfg)
    except Exception as e:                      # never let a figure break the run
        print(f"[snapshots]   co-vis mask unavailable ({e.__class__.__name__}: {e})")
        return None


def generate(cfg, keep_h=2.0, max_points=120000, point_size=5.0,
             bgs=("black", "white"), views=None,
             methods=None, scenes=None, trajs=None, mask_variants=MASK_VARIANTS,
             dropped_grey=DROPPED_GREY, dropped_alpha=DROPPED_ALPHA):
    views = views or VIEWS
    out_dir = REPO_ROOT / cfg["report"]["out_dir"] / "snapshots"
    out_dir.mkdir(parents=True, exist_ok=True)
    correct_scale = cfg["eval"]["align"]["correct_scale"]
    # Optional filters (sets or None) to render a focused comparison, e.g. just the
    # PRISM alignment arms on one scene/rate.
    methods = set(methods) if methods else None
    scenes = set(scenes) if scenes else None
    trajs = set(trajs) if trajs else None
    mask_variants = [m for m in (mask_variants or MASK_VARIANTS) if m in MASK_VARIANTS]
    written = []

    # group runs by (dataset, scene, traj) so GT framing is shared and GT rendered once
    runs = sorted((REPO_ROOT / "results").glob("*/*/*/*/*/cloud.ply"))
    seen_gt = set()
    for cloud in runs:
        parts = cloud.parent.parts
        i = parts.index("results")
        method, dataset, scene, traj, variant = parts[i + 1:i + 6]
        if (methods and method not in methods) or (scenes and scene not in scenes) \
                or (trajs and traj not in trajs):
            continue
        base = _export_base(dataset, scene, traj)
        gt_mesh = base / "gt_mesh.ply"
        gt_tum = base / "poses_gt.tum"
        if not gt_mesh.exists():
            print(f"[snapshots] no GT for {scene}/{traj}; skip {method}"); continue

        gt_pts, gt_cols = _load_points(gt_mesh)
        floor_z = float(np.percentile(gt_pts[:, 2], 1.0))
        gt_pts_c, gt_cols_c = _clip_ceiling(gt_pts, gt_cols, floor_z, keep_h)
        pad = 0.2
        limits = ((gt_pts_c[:, 0].min() - pad, gt_pts_c[:, 0].max() + pad),
                  (gt_pts_c[:, 1].min() - pad, gt_pts_c[:, 1].max() + pad),
                  (floor_z - 0.05, floor_z + keep_h))

        # GT reference images (once per scene/traj). The GT is masked in eval too, so it
        # gets the same variants — otherwise a masked method would be compared against
        # an unmasked reference in the figure.
        gt_key = (dataset, scene, traj)
        if gt_key not in seen_gt:
            seen_gt.add(gt_key)
            gp, gc, _ = _subsample(gt_pts_c, gt_cols_c, max_points)
            gkeep = _covis_keep(gp, dataset, scene, traj, cfg) \
                if any(m != "full" for m in mask_variants) else None
            for mv in mask_variants:
                if mv != "full" and gkeep is None:
                    continue
                frac = f"  [{gkeep.sum()}/{len(gkeep)} co-vis]" if (
                    gkeep is not None and mv != "full") else ""
                for vn, v in views.items():
                    for bg in bgs:
                        p = out_dir / f"GT__{scene}_{traj}__{mv}__{vn}__{bg}.png"
                        _render(gp, gc, limits, v, bg, p, point_size,
                                label=f"GT   {scene}/{traj}   {mv}{frac}",
                                keep=gkeep, mask_variant=mv,
                                dropped_grey=dropped_grey, dropped_alpha=dropped_alpha)
                        written.append(p)

        # method cloud: align to GT frame (ground on floor), clip ceiling, render
        pred, pcols = _load_points(cloud)
        if len(pred) == 0:
            continue
        # Trajectory Sim(3) alignment only — NO ICP for snapshots. ICP diverges on a
        # badly-drifted cloud (e.g. VGGT-SLAM on the apartment: fitness ~0.34) and rotates/
        # shrinks it in the image. The Sim(3) from the trajectory is robust for a visual.
        # (eval_recon still uses ICP for the metric numbers.)
        pred, _ = _align_pred_to_gt(pred, cloud.parent / "poses.tum", gt_tum, correct_scale)
        pred, pcols = _clip_ceiling(pred, pcols, floor_z, keep_h)
        pred, pcols, _ = _subsample(pred, pcols, max_points)
        # Mask computed once per cloud, then reused across every view/background.
        keep = _covis_keep(pred, dataset, scene, traj, cfg) \
            if any(m != "full" for m in mask_variants) else None
        if keep is not None:
            print(f"[snapshots]   co-vis: {int(keep.sum())}/{len(keep)} pts kept "
                  f"({100.0 * keep.sum() / max(len(keep), 1):.1f}%)")
        for mv in mask_variants:
            if mv != "full" and keep is None:
                print(f"[snapshots]   skipping '{mv}' (no pinhole export for the mask)")
                continue
            frac = f"  [{int(keep.sum())}/{len(keep)} co-vis]" if (
                keep is not None and mv != "full") else ""
            for vn, v in views.items():
                for bg in bgs:
                    p = (out_dir /
                         f"{method}__{scene}_{traj}_{variant}__{mv}__{vn}__{bg}.png")
                    _render(pred, pcols, limits, v, bg, p, point_size,
                            label=f"{method}   {scene}/{traj}/{variant}   {mv}{frac}",
                            keep=keep, mask_variant=mv,
                            dropped_grey=dropped_grey, dropped_alpha=dropped_alpha)
                    written.append(p)
        n_mv = len([m for m in mask_variants if m == "full" or keep is not None])
        print(f"[snapshots] {method} {scene}/{traj}/{variant}: "
              f"{n_mv * len(views) * len(bgs)} images ({n_mv} mask variants)")
    print(f"[snapshots] wrote {len(written)} images -> {out_dir}")
    return [str(p) for p in written]


def main():
    ap = argparse.ArgumentParser(description="Standardized cloud snapshots for the paper")
    ap.add_argument("--config", default="config.yaml")
    ap.add_argument("--keep-height", type=float, default=2.0, help="metres above floor to keep (ceiling clip)")
    ap.add_argument("--max-points", type=int, default=120000)
    ap.add_argument("--point-size", type=float, default=5.0, help="marker size in the render")
    ap.add_argument("--methods", default="", help="space/comma list to render (default: all)")
    ap.add_argument("--scenes", default="", help="space/comma list of scenes (default: all)")
    ap.add_argument("--traj", default="", help="space/comma list of traj dirs, e.g. synthetic_2.0hz")
    ap.add_argument("--mask-variants", default=",".join(MASK_VARIANTS),
                    help="which co-visibility variants to render: "
                         "full (all points) | covis (kept in colour + dropped in grey) | "
                         "masked (kept only). Default: all three.")
    ap.add_argument("--dropped-alpha", type=float, default=DROPPED_ALPHA,
                    help="opacity of masked-away points in the 'covis' variant "
                         "(raise it when the mask removes only a little)")
    ap.add_argument("--dropped-grey", type=float, default=DROPPED_GREY,
                    help="greyscale level (0=black, 1=white) of masked-away points")
    args = ap.parse_args()
    cfg = load_config(args.config)

    def _split(s):
        return [x for x in s.replace(",", " ").split() if x] or None

    generate(cfg, keep_h=args.keep_height, max_points=args.max_points,
             point_size=args.point_size, methods=_split(args.methods),
             scenes=_split(args.scenes), trajs=_split(args.traj),
             mask_variants=_split(args.mask_variants) or MASK_VARIANTS,
             dropped_grey=args.dropped_grey, dropped_alpha=args.dropped_alpha)


if __name__ == "__main__":
    main()

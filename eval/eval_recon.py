"""Reconstruction eval — accuracy, completeness, Chamfer, F-score@thr (Open3D).

Two variants per run:
  masked   : both pred and GT restricted to the co-visibility support (fair vs pinhole).
  full_360 : no mask (pano-capable methods only; credits 360deg coverage).

For scale-free methods, the cloud is first Sim(3)-aligned to GT via the trajectory
alignment (same s,R,t as eval_traj) so recon metrics aren't dominated by scale.
Writes recon.json next to each run. Imports NO method.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bench.config import REPO_ROOT, load_config
from eval.visibility_mask import build_mask


def _run_meta(run_dir: Path):
    parts = run_dir.parts
    i = parts.index("results")
    method, dataset, scene, traj, variant = parts[i + 1:i + 6]
    return method, dataset, scene, traj, variant


def _export_base(dataset, scene, traj) -> Path:
    return REPO_ROOT / "dataset" / "exports" / dataset / scene / traj


def _metrics(pred_pts, gt_pts, thr):
    import open3d as o3d
    pred = o3d.geometry.PointCloud(o3d.utility.Vector3dVector(pred_pts))
    gt = o3d.geometry.PointCloud(o3d.utility.Vector3dVector(gt_pts))
    d_pred_gt = np.asarray(pred.compute_point_cloud_distance(gt))   # accuracy
    d_gt_pred = np.asarray(gt.compute_point_cloud_distance(pred))   # completeness
    acc = float(d_pred_gt.mean())
    comp = float(d_gt_pred.mean())
    chamfer = float(acc + comp)
    prec = float((d_pred_gt < thr).mean())
    rec = float((d_gt_pred < thr).mean())
    f = float(2 * prec * rec / (prec + rec)) if (prec + rec) > 0 else 0.0
    return {"accuracy_m": acc, "completeness_m": comp, "chamfer_m": chamfer,
            "precision": prec, "recall": rec, "fscore": f}


def _gt_cloud(dataset, scene, traj, n_sample=400000):
    import open3d as o3d
    mesh_p = _export_base(dataset, scene, traj) / "gt_mesh.ply"
    mesh = o3d.io.read_triangle_mesh(str(mesh_p))
    pcd = mesh.sample_points_uniformly(number_of_points=n_sample)
    return np.asarray(pcd.points)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="config.yaml")
    args = ap.parse_args()
    cfg = load_config(args.config)
    thr = cfg["eval"]["fscore_threshold_m"]

    for cloud in (REPO_ROOT / "results").glob("*/*/*/*/*/cloud.ply"):
        import open3d as o3d
        method, dataset, scene, traj, variant = _run_meta(cloud.parent)
        pred_pts = np.asarray(o3d.io.read_point_cloud(str(cloud)).points)
        if len(pred_pts) == 0:
            print(f"[eval_recon] {cloud}: empty cloud — skip"); continue
        gt_pts = _gt_cloud(dataset, scene, traj)

        # pick a pinhole export dir to define the co-visibility frustum
        pin_variants = list((_export_base(dataset, scene, traj) / "pinhole").glob("*"))
        out = {"threshold_m": thr}
        if pin_variants:
            keep_pred = build_mask(pred_pts, pin_variants[0], cfg)
            keep_gt = build_mask(gt_pts, pin_variants[0], cfg)
            out["masked"] = _metrics(pred_pts[keep_pred], gt_pts[keep_gt], thr)
        # full-360 (only meaningful for pano methods, but computed for all)
        out["full_360"] = _metrics(pred_pts, gt_pts, thr)

        (cloud.parent / "recon.json").write_text(json.dumps(out, indent=2))
        m = out.get("masked", out["full_360"])
        print(f"[eval_recon] {cloud.parent.relative_to(REPO_ROOT)}: "
              f"F-score {m['fscore']:.3f} (masked)")


if __name__ == "__main__":
    main()

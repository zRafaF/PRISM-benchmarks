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


def _read_tum_map(path: Path) -> dict:
    """timestamp -> position (3,). Used to align the pred cloud into the GT frame."""
    out = {}
    for line in Path(path).read_text().splitlines():
        if line.strip():
            v = [float(x) for x in line.split()]
            out[round(v[0], 3)] = np.array(v[1:4])
    return out


def _umeyama_sim3(src: np.ndarray, tgt: np.ndarray):
    """Closed-form Sim(3): scale s, rotation R, translation t mapping src->tgt."""
    mu_s, mu_t = src.mean(0), tgt.mean(0)
    sc, tc = src - mu_s, tgt - mu_t
    cov = tc.T @ sc / len(src)
    U, D, Vt = np.linalg.svd(cov)
    S = np.eye(3)
    if np.linalg.det(U) * np.linalg.det(Vt) < 0:
        S[2, 2] = -1
    R = U @ S @ Vt
    var = (sc ** 2).sum() / len(src)
    s = float(np.trace(np.diag(D) @ S) / var) if var > 1e-12 else 1.0
    t = mu_t - s * R @ mu_s
    return s, R, t


def _align_pred_to_gt(pred_pts, pred_tum: Path, gt_tum: Path, correct_scale: bool):
    """Register the predicted cloud into the GT frame via the trajectory Sim(3).

    The cloud is produced in the method's own world frame; recon metrics are only
    meaningful after mapping it onto GT with the SAME transform that aligns the
    trajectories (Sim(3) if scale-free, SE(3) if the method is metric).
    """
    pm, gm = _read_tum_map(pred_tum), _read_tum_map(gt_tum)
    common = sorted(set(pm) & set(gm))
    if len(common) < 3:
        print(f"[eval_recon]   WARN: only {len(common)} matched poses — cloud NOT aligned")
        return pred_pts, (1.0, np.eye(3), np.zeros(3))
    src = np.array([pm[k] for k in common])
    tgt = np.array([gm[k] for k in common])
    s, R, t = _umeyama_sim3(src, tgt)
    if not correct_scale:
        s = 1.0
    aligned = (s * (R @ pred_pts.T).T) + t
    print(f"[eval_recon]   aligned pred->GT: scale={s:.3f} "
          f"|t|={np.linalg.norm(t):.2f}m over {len(common)} poses")
    return aligned, (s, R, t)


def _icp_refine(pred_pts, gt_pts, max_dist):
    """Tighten the pred->GT registration with point-to-point ICP after the coarse
    trajectory Sim(3). Standard in recon benchmarks so quality isn't penalised by a
    small residual misalignment. Returns the refined pred points."""
    import open3d as o3d
    src = o3d.geometry.PointCloud(o3d.utility.Vector3dVector(pred_pts))
    tgt = o3d.geometry.PointCloud(o3d.utility.Vector3dVector(gt_pts))
    reg = o3d.pipelines.registration.registration_icp(
        src, tgt, max_dist, np.eye(4),
        o3d.pipelines.registration.TransformationEstimationPointToPoint())
    src.transform(reg.transformation)
    print(f"[eval_recon]   ICP refine: fitness={reg.fitness:.3f} "
          f"inlier_rmse={reg.inlier_rmse*100:.1f}cm")
    return np.asarray(src.points)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="config.yaml")
    args = ap.parse_args()
    cfg = load_config(args.config)
    thr = cfg["eval"]["fscore_threshold_m"]
    correct_scale = cfg["eval"]["align"]["correct_scale"]
    icp_cfg = cfg["eval"].get("icp", {"enabled": True, "max_dist_m": 0.15})

    for cloud in (REPO_ROOT / "results").glob("*/*/*/*/*/cloud.ply"):
        import open3d as o3d
        method, dataset, scene, traj, variant = _run_meta(cloud.parent)
        pred_pts = np.asarray(o3d.io.read_point_cloud(str(cloud)).points)
        print(f"\n[eval_recon] {cloud.parent.relative_to(REPO_ROOT)}")
        print(f"[eval_recon]   pred cloud: {len(pred_pts)} pts "
              f"bbox={np.round(pred_pts.min(0),2)}..{np.round(pred_pts.max(0),2)}"
              if len(pred_pts) else "[eval_recon]   pred cloud EMPTY")
        if len(pred_pts) == 0:
            continue
        gt_pts = _gt_cloud(dataset, scene, traj)
        print(f"[eval_recon]   GT cloud:   {len(gt_pts)} pts "
              f"bbox={np.round(gt_pts.min(0),2)}..{np.round(gt_pts.max(0),2)}")

        # register pred -> GT frame using the trajectory alignment (critical!)
        gt_tum = _export_base(dataset, scene, traj) / "poses_gt.tum"
        pred_tum = cloud.parent / "poses.tum"
        pred_pts, _sim3 = _align_pred_to_gt(pred_pts, pred_tum, gt_tum, correct_scale)
        if icp_cfg.get("enabled", True) and len(pred_pts) and len(gt_pts):
            pred_pts = _icp_refine(pred_pts, gt_pts, icp_cfg.get("max_dist_m", 0.15))

        pin_variants = list((_export_base(dataset, scene, traj) / "pinhole").glob("*"))
        out = {"threshold_m": thr}
        if pin_variants:
            keep_pred = build_mask(pred_pts, pin_variants[0], cfg)
            keep_gt = build_mask(gt_pts, pin_variants[0], cfg)
            print(f"[eval_recon]   co-vis mask: pred {keep_pred.sum()}/{len(keep_pred)}, "
                  f"GT {keep_gt.sum()}/{len(keep_gt)} points kept")
            out["masked"] = _metrics(pred_pts[keep_pred], gt_pts[keep_gt], thr)
        out["full_360"] = _metrics(pred_pts, gt_pts, thr)

        (cloud.parent / "recon.json").write_text(json.dumps(out, indent=2))
        m = out.get("masked", out["full_360"])
        print(f"[eval_recon]   -> masked F@{int(thr*100)}cm={m['fscore']:.3f} "
              f"acc={m['accuracy_m']*100:.1f}cm compl={m['completeness_m']*100:.1f}cm")


if __name__ == "__main__":
    main()

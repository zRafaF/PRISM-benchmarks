"""OUR benchmark: absolute metric-scale accuracy.

Most baselines (Pi3, VGGT-SLAM, MapAnything, LASER) are monocular/scale-free — they
recover geometry only up to an unknown similarity scale, so their absolute size is
undefined and reported N/A here. PRISM-VGGT grounds metric scale from the RANSAC
floor + known camera height, so it should reconstruct at TRUE metric scale.

We quantify this with the rendered GT (which has exact metric scale, unlike
tape-measure captures): recover the similarity scale `s` that best aligns each
method's trajectory to GT. A perfectly metric method gives s≈1; the reported
metric-scale error is |s-1| (as a %) plus the room-extent (bbox diagonal) error of
the reconstructed cloud vs the GT mesh.

Config-gated (eval.metric_accuracy.enabled) and only run for methods with
metric=true in config. Writes metric.json next to each run. Imports NO method.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bench.config import REPO_ROOT, load_config


def _read_tum_positions(path: Path) -> np.ndarray:
    pos = []
    for line in Path(path).read_text().splitlines():
        if line.strip():
            v = [float(x) for x in line.split()]
            pos.append(v[1:4])
    return np.array(pos)


def _umeyama_scale(src: np.ndarray, tgt: np.ndarray):
    """Similarity scale mapping src->tgt; None if too few / degenerate poses."""
    n = min(len(src), len(tgt))
    if n < 3:
        return None
    src, tgt = src[:n], tgt[:n]
    s_c = src - src.mean(0)
    t_c = tgt - tgt.mean(0)
    cov = t_c.T @ s_c / n
    _, D, _ = np.linalg.svd(cov)
    var_s = (s_c ** 2).sum() / n
    return float(D.sum() / var_s) if var_s > 1e-12 else 1.0


def _bbox_diag(points: np.ndarray) -> float:
    if len(points) == 0:
        return 0.0
    return float(np.linalg.norm(points.max(0) - points.min(0)))


def _metric_methods(cfg) -> set[str]:
    return {m["name"] for m in cfg["methods"] if m.get("metric")}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="config.yaml")
    args = ap.parse_args()
    cfg = load_config(args.config)
    if not cfg["eval"]["metric_accuracy"]["enabled"]:
        print("[metric] disabled in config"); return
    metric_methods = _metric_methods(cfg)

    import open3d as o3d
    for pred in (REPO_ROOT / "results").glob("*/*/*/*/*/poses.tum"):
        parts = pred.parent.parts
        i = parts.index("results")
        method, dataset, scene, traj, variant = parts[i + 1:i + 6]
        if method not in metric_methods:
            (pred.parent / "metric.json").write_text(json.dumps(
                {"metric_capable": False, "note": "scale-free method — absolute scale N/A"}, indent=2))
            continue
        gt = REPO_ROOT / "dataset" / "exports" / dataset / scene / traj / "poses_gt.tum"
        if not gt.exists():
            continue
        s = _umeyama_scale(_read_tum_positions(pred), _read_tum_positions(gt))
        if s is None:
            # degenerate run (e.g. too few frames at 0.5 Hz on a small scene -> empty map)
            (pred.parent / "metric.json").write_text(json.dumps(
                {"metric_capable": True, "scale_estimate": None,
                 "metric_scale_error_pct": None, "note": "insufficient/empty poses"}, indent=2))
            print(f"[metric] {method}/{dataset}/{scene}/{traj}: skipped (insufficient poses)")
            continue
        out = {"metric_capable": True,
               "scale_estimate": s,
               "metric_scale_error_pct": abs(s - 1.0) * 100.0}
        cloud = pred.parent / "cloud.ply"
        gt_mesh = REPO_ROOT / "dataset" / "exports" / dataset / scene / traj / "gt_mesh.ply"
        if cloud.exists() and gt_mesh.exists():
            pd = _bbox_diag(np.asarray(o3d.io.read_point_cloud(str(cloud)).points))
            gd = _bbox_diag(np.asarray(o3d.io.read_triangle_mesh(str(gt_mesh)).vertices))
            out["extent_diag_pred_m"] = pd
            out["extent_diag_gt_m"] = gd
            out["extent_error_pct"] = abs(pd - gd) / gd * 100.0 if gd > 0 else None
        (pred.parent / "metric.json").write_text(json.dumps(out, indent=2))
        print(f"[metric] {method}/{dataset}/{scene}/{traj}: scale {s:.3f} "
              f"({out['metric_scale_error_pct']:.1f}% err)")


if __name__ == "__main__":
    main()

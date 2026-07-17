"""Trajectory eval — ATE (RMSE) + RPE with Sim(3) Umeyama alignment, via evo.

Reads each method's results/<...>/poses.tum vs the shared GT poses_gt.tum in the
matching export dir. Writes ate.json next to each run. Imports NO method.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bench.config import REPO_ROOT, load_config


def _gt_for(run_dir: Path) -> Path:
    # results/<method>/<dataset>/<scene>/<traj>/<variant> -> exports/.../poses_gt.tum
    parts = run_dir.parts
    i = parts.index("results")
    _, dataset, scene, traj, _variant = parts[i + 1:i + 6]
    return REPO_ROOT / "dataset" / "exports" / dataset / scene / traj / "poses_gt.tum"


def eval_one(pred: Path, gt: Path, correct_scale: bool) -> dict:
    from evo.core import metrics, sync
    from evo.tools import file_interface
    traj_ref = file_interface.read_tum_trajectory_file(str(gt))
    traj_est = file_interface.read_tum_trajectory_file(str(pred))
    n_matched = traj_ref.num_poses
    traj_ref, traj_est = sync.associate_trajectories(traj_ref, traj_est)
    align_out = traj_est.align(traj_ref, correct_scale=correct_scale)
    # evo returns (R, t, s) for Sim(3) alignment; s is the pred->GT scale it applied.
    align_scale = float(align_out[2]) if isinstance(align_out, (tuple, list)) and len(align_out) >= 3 else 1.0

    ate = metrics.APE(metrics.PoseRelation.translation_part)
    ate.process_data((traj_ref, traj_est))
    rpe = metrics.RPE(metrics.PoseRelation.translation_part, delta=1, delta_unit=metrics.Unit.frames)
    rpe.process_data((traj_ref, traj_est))

    # Fair, density-normalized drift: |Δpred - Δgt| / |Δgt| between consecutive matched
    # poses, i.e. relative pose error PER METRE of GT motion. Unlike frame-delta RPE this
    # is comparable across dense (per-frame) and sparse (keyframe) methods, so VGGT-SLAM /
    # LASER keyframe outputs aren't unfairly penalised for large keyframe spacing.
    est = np.asarray(traj_est.positions_xyz)
    ref = np.asarray(traj_ref.positions_xyz)
    de, dr = np.diff(est, axis=0), np.diff(ref, axis=0)
    seg = np.linalg.norm(dr, axis=1)
    m = seg > 1e-3
    rpe_per_m = float(np.mean(np.linalg.norm(de - dr, axis=1)[m] / seg[m])) if m.any() else None

    return {
        "ate_rmse_m": float(ate.get_statistic(metrics.StatisticsType.rmse)),
        "ate_mean_m": float(ate.get_statistic(metrics.StatisticsType.mean)),
        "rpe_rmse_m": float(rpe.get_statistic(metrics.StatisticsType.rmse)),
        "rpe_per_m": rpe_per_m,            # drift fraction per metre (fair across densities)
        "n_poses": int(traj_est.num_poses),
        "aligned_scale_corrected": correct_scale,
        "alignment_scale": align_scale,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="config.yaml")
    args = ap.parse_args()
    cfg = load_config(args.config)
    cs = cfg["eval"]["align"]["correct_scale"]

    for pred in (REPO_ROOT / "results").glob("*/*/*/*/*/poses.tum"):
        gt = _gt_for(pred.parent)
        if not gt.exists():
            print(f"[eval_traj] no GT for {pred} — skip"); continue
        if sum(1 for _ in open(pred) if _.strip()) < 3:
            print(f"[eval_traj] {pred.parent.relative_to(REPO_ROOT)}: <3 poses — skip"); continue
        try:
            res = eval_one(pred, gt, cs)
            (pred.parent / "ate.json").write_text(json.dumps(res, indent=2))
            print(f"[eval_traj] {pred.parent.relative_to(REPO_ROOT)}: "
                  f"ATE {res['ate_rmse_m']*100:.1f} cm  RPE {res['rpe_rmse_m']*100:.2f} cm  "
                  f"(align scale {res['alignment_scale']:.3f}, {res['n_poses']} poses)")
        except Exception as e:
            print(f"[eval_traj] {pred}: FAILED — {e}")


if __name__ == "__main__":
    main()

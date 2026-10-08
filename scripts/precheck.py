#!/usr/bin/env python
"""Pre-check: run EVERY method on ONE real sequence of the matrix and validate it,
before committing the GPU to the full benchmark.   `make precheck`

The sequence is a real unit of the matrix (default: the smallest frozen room, seed 0,
smooth 2 Hz), so the runs are kept and the full benchmark skips them afterwards.

Per method it checks:
  * the run completed (rc 0, no OOM) and wrote poses + a non-empty cloud;
  * every input frame got a pose (VGGT-SLAM: >= 80% of frames kept as keyframes and
    >= 2 submaps, i.e. its pose graph engaged);
  * PRISM arms: the world was levelled and the metric scale locked;
  * the trajectory is sane: ATE (Sim(3)-aligned, vs the rendered GT) is finite and
    under PRECHECK_MAX_ATE_M (default 0.5 m on a small room).
Then it prints a table with time / VRAM / ATE per method and projects the full run
time from the measured per-method times. Exits non-zero if anything FAILs.

Env: PRECHECK_SCENE, PRECHECK_TRAJ, PRECHECK_METHODS="a b", PRECHECK_FORCE=0 (reuse
existing results instead of re-running), PRECHECK_MAX_ATE_M.
"""
from __future__ import annotations

import json
import math
import os
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bench.config import REPO_ROOT, load_config, resolve_trajs
from bench.matrix import frozen_scenes, main_methods, plan

RUN = os.environ.get("RUN", "uv run python").split()


def _load(p: Path):
    try:
        return json.loads(p.read_text())
    except Exception:
        return None


def _ply_points(p: Path) -> int:
    try:
        with open(p, "rb") as f:
            for _ in range(30):
                ln = f.readline().decode("ascii", "replace").strip()
                if ln.startswith("element vertex"):
                    return int(ln.split()[-1])
                if ln == "end_header":
                    break
    except Exception:
        pass
    return 0


def main() -> int:
    cfg = load_config("config.yaml")
    ds = cfg["datasets"]["active"][0]
    scenes = frozen_scenes(cfg)
    if not scenes:
        print("!! no frozen scenes — run the data stage first"); return 1
    scene = os.environ.get("PRECHECK_SCENE") or next(
        (s for s in ("room_0", "office_0", "room_1") if s in scenes), scenes[0])
    trajs = resolve_trajs(cfg, "all")
    traj = os.environ.get("PRECHECK_TRAJ") or next(
        (t for t in trajs if t.startswith("synthetic_") and t.endswith(("_s0", "hz"))), trajs[0])
    methods = (os.environ.get("PRECHECK_METHODS") or "").split() or main_methods(cfg)
    force = os.environ.get("PRECHECK_FORCE", "1") == "1"
    max_ate = float(os.environ.get("PRECHECK_MAX_ATE_M", "0.5"))
    gt = REPO_ROOT / "dataset" / "exports" / ds / scene / traj / "poses_gt.tum"
    if not gt.exists():
        print(f"!! no ground truth at {gt} — inputs missing"); return 1

    print(f"=== PRE-CHECK: {len(methods)} methods on {ds}/{scene}/{traj} ===")
    env = dict(os.environ)
    if force:
        env["PRISM_FORCE"] = "1"
    for i, m in enumerate(methods, 1):
        print(f"\n--- [{i}/{len(methods)}] {m} ---", flush=True)
        t0 = time.time()
        rc = subprocess.call(RUN + ["adapters/run.py", "--method", m, "--config", "config.yaml",
                                    "--scenes", scene, "--traj", traj], cwd=REPO_ROOT, env=env)
        print(f"    adapter exit {rc} after {time.time() - t0:.0f}s")

    from eval.eval_traj import eval_one
    rows, fails = [], 0
    for m in methods:
        base = REPO_ROOT / "results" / m / ds / scene / traj
        vdirs = sorted(p for p in base.glob("*") if p.is_dir()) if base.exists() else []
        if not vdirs:
            rows.append({"method": m, "status": "FAIL", "why": "no result dir (method did not run)"})
            fails += 1
            continue
        d = vdirs[0]
        perf = _load(d / "perf.json") or {}
        arm = _load(d / "arm_config.json") or {}
        why, warn = [], []
        if not perf.get("completed"):
            why.append(f"not completed ({perf.get('failure_kind') or 'no perf.json'}) — see {d / 'run.log'}")
        ni, nd = perf.get("n_frames_input") or 0, perf.get("n_frames_done") or 0
        if m.startswith("vggtslam"):
            kr = arm.get("keyframe_ratio")
            if kr is None or kr < 0.8:
                why.append(f"keyframe_ratio {kr} < 0.8")
            if (arm.get("n_submaps") or 0) < 2:
                why.append(f"{arm.get('n_submaps')} submap(s): pose graph inactive")
        elif ni and nd and nd < ni and perf.get("completed"):
            why.append(f"posed {nd}/{ni} frames")
        npts = _ply_points(d / "cloud.ply")
        if perf.get("completed") and npts < 1000:
            why.append(f"cloud has {npts} points")
        if m.startswith("prism") and perf.get("completed"):
            if arm.get("level_source") in (None, "None"):
                why.append("world never levelled")
            if not arm.get("scale_locked"):
                warn.append("metric scale not locked")
            if arm.get("scale_locked_forced"):
                warn.append("scale lock forced")
        ate = None
        if (d / "poses.tum").exists():
            try:
                ate = eval_one(d / "poses.tum", gt, True)["ate_rmse_m"]
                (d / "ate.json").write_text(json.dumps({"ate_rmse_m": ate, "source": "precheck"}))
            except Exception as e:
                why.append(f"ATE failed: {e}")
        if ate is not None and (not math.isfinite(ate) or ate > max_ate):
            why.append(f"ATE {ate:.2f} m > {max_ate} m")
        status = "FAIL" if why else ("WARN" if warn else "PASS")
        fails += status == "FAIL"
        rows.append({"method": m, "status": status, "why": "; ".join(why + warn),
                     "wall_s": perf.get("wall_s"), "proc_s": perf.get("latency_end_to_end_s"),
                     "vram_peak_gb": perf.get("vram_peak_gb"), "ate_m": ate,
                     "frames": f"{nd}/{ni}", "extra": {k: arm.get(k) for k in
                     ("n_submaps", "n_loop_closures", "keyframe_ratio", "level_source",
                      "scale_locked", "align_mode") if k in arm}})

    # ── projection of the full benchmark from the measured per-method time ──
    units = plan(cfg)
    per_m = {}
    for u in units:
        per_m[u.method] = per_m.get(u.method, 0) + 1
    total_s = 0.0
    for r in rows:
        if r.get("wall_s"):
            total_s += per_m.get(r["method"], 0) * float(r["wall_s"])

    print("\n" + "=" * 100)
    print(f"PRE-CHECK  {ds}/{scene}/{traj}")
    print("=" * 100)
    print(f"{'method':18s} {'status':6s} {'wall':>7s} {'proc':>7s} {'VRAM':>7s} {'ATE':>8s} {'frames':>9s}  notes")
    for r in rows:
        w = f"{r['wall_s']:.0f}s" if r.get("wall_s") else "-"
        p = f"{r['proc_s']:.0f}s" if r.get("proc_s") else "-"
        v = f"{r['vram_peak_gb']:.1f}G" if r.get("vram_peak_gb") else "-"
        a = f"{100 * r['ate_m']:.1f}cm" if r.get("ate_m") is not None else "-"
        note = r["why"] or ", ".join(f"{k}={v}" for k, v in (r.get("extra") or {}).items())
        print(f"{r['method']:18s} {r['status']:6s} {w:>7s} {p:>7s} {v:>7s} {a:>8s} {r.get('frames', ''):>9s}  {note}")
    print("=" * 100)
    print(f"Full benchmark: {len(units)} runs, projected ~{total_s / 3600:.1f} h of sequential GPU time "
          f"(from these per-method times x runs per method).")
    (REPO_ROOT / "logs").mkdir(exist_ok=True)
    (REPO_ROOT / "logs" / "precheck.json").write_text(json.dumps(
        {"scene": scene, "traj": traj, "rows": rows, "projected_hours": total_s / 3600,
         "time": time.strftime("%Y-%m-%dT%H:%M:%S")}, indent=2, default=str))
    if fails:
        print(f"!! {fails} method(s) FAILED — fix before the full run (results kept; re-run: make precheck)")
        return 1
    print("All methods PASS — safe to start the full benchmark.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

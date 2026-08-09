"""Shared adapter driver.

An adapter's job (baseline-agnostic):
  (a) find the exported input sequence for its camera model,
  (b) run the method IN ITS OWN ENV as a subprocess (never import the method here),
  (c) collect poses.tum + cloud.ply + perf.json into the common results layout.

The method-specific work lives in adapters/runners/<method>_runner.py, which is
executed by that method's venv interpreter (submodules/<m>/.venv/bin/python). The
orchestrator wraps the subprocess in the uniform perf sampler (bench/perf.py) so
every method is timed identically.
"""
from __future__ import annotations

import math
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bench.config import REPO_ROOT, RunPaths, common_args, export_dir, load_config, resolve_scenes, resolve_trajs
from bench.perf import PerfResult, ResourceSampler


def method_cfg(cfg: dict, name: str) -> dict:
    for m in cfg.get("methods", []) + cfg.get("ablations", []):
        if m["name"] == name:
            return m
    raise KeyError(f"method '{name}' not in config.methods or config.ablations")


def method_python(env_rel: str) -> Path:
    """Path to the method env's python (its ISOLATED venv)."""
    p = REPO_ROOT / env_rel / ".venv" / "bin" / "python"
    return p


def input_dirs_for(cfg: dict, mcfg: dict, dataset: str, scene: str, traj: str):
    """Yield (variant, export_dir) for the method's camera model."""
    if mcfg["camera"] == "pano":
        yield "", export_dir(dataset, scene, traj, "pano", "")
    else:
        for vname in cfg["camera"]["pinhole"]["variants"]:
            yield vname, export_dir(dataset, scene, traj, "pinhole", vname)


def run_method(name: str):
    ap = common_args(f"Run {name} in its isolated env -> common results layout")
    args = ap.parse_args()
    cfg = load_config(args.config)
    mcfg = method_cfg(cfg, name)

    py = method_python(mcfg["env"])
    if not py.exists():
        print(f"[{name}] env python not found at {py} — run 'make setup-{name}' first.")
        return

    # `runner` override lets ablations (prism_nolock, ...) reuse prism_runner.
    runner = Path(__file__).parent / "runners" / f"{mcfg.get('runner', name)}_runner.py"
    device_index = 0
    # `run_env` overrides let ablations toggle PRISM engine guards via env vars.
    run_env = os.environ.copy()
    run_env.update({k: str(v) for k, v in (mcfg.get("run_env") or {}).items()})
    if mcfg.get("run_env"):
        print(f"[{name}] env overrides: {mcfg['run_env']}")

    for dataset in cfg["datasets"]["active"]:
        for scene in resolve_scenes(cfg, dataset, args.scenes):
            for traj in resolve_trajs(cfg, args.traj):
                for variant, in_dir in input_dirs_for(cfg, mcfg, dataset, scene, traj):
                    if not (in_dir / "meta.json").exists():
                        continue
                    rp = RunPaths(name, dataset, scene, traj, variant or mcfg["camera"])
                    # Resume: skip a run that already produced poses (unless PRISM_FORCE=1),
                    # so re-running the pipeline doesn't redo finished (slow) method runs.
                    if (rp.poses_tum.exists() and rp.poses_tum.stat().st_size > 0
                            and os.environ.get("PRISM_FORCE", "0") != "1"):
                        print(f"[{name}] {dataset}/{scene}/{traj}/{variant or mcfg['camera']}"
                              f" — already done, skip (PRISM_FORCE=1 to redo)")
                        continue
                    rp.dir().mkdir(parents=True, exist_ok=True)
                    cmd = [str(py), str(runner),
                           "--in", str(in_dir),
                           "--out", str(rp.dir()),
                           "--config", str(REPO_ROOT / args.config)]
                    print(f"[{name}] {dataset}/{scene}/{traj}/{variant or mcfg['camera']}")
                    result = PerfResult(method=name)
                    # Run in the METHOD's own repo dir: these repos resolve config /
                    # weights / third-party paths relative to their own root. All args
                    # we pass (--in/--out/--config) are absolute, so this is safe.
                    cwd = str((REPO_ROOT / mcfg["env"]).resolve())
                    hint = cfg.get("hardware", {}).get("hw_id")
                    with open(rp.run_log, "w") as log, \
                            ResourceSampler(device_index, pid=None, gpu_name_hint=hint) as smp:
                        proc = subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT,
                                              cwd=cwd, env=run_env)
                    import json
                    meta = json.loads((in_dir / "meta.json").read_text())
                    # n_frames_input  = what the method was ASKED to process.
                    # n_frames_done   = what it actually produced a pose for.
                    # On a run that dies part-way these differ, and using the input
                    # count would report a spuriously HIGH eff_fps (same wall clock,
                    # more nominal frames) — which is exactly how the 2026-07 big run
                    # ended up averaging crashed PRISM runs into its throughput.
                    result.n_frames_input = meta.get("n_frames", 0)
                    result.n_frames_done = _count_poses(rp.poses_tum)
                    result.n_frames = result.n_frames_done or result.n_frames_input
                    result.returncode = proc.returncode
                    result.failure_kind = _classify_failure(rp.run_log, proc.returncode)
                    result.oom = (result.failure_kind == "oom")
                    result.completed = bool(proc.returncode == 0 and result.n_frames_done)
                    smp.summarize(result)
                    _merge_runner_perf(rp, result, window=int(cfg["engine"]["window_size"]),
                                       overlap=int(cfg["engine"]["overlap"]))
                    result.write(rp.perf_json)
                    if result.oom:
                        print(f"[{name}]   -> OUT OF MEMORY at {result.n_frames_input} "
                              f"frames (peak {result.vram_peak_gb:.1f} GB of "
                              f"{result.gpu_total_gb} GB) — RECORDED as an OOM result, "
                              f"not a harness failure. See {rp.run_log}")
                    elif not result.completed:
                        print(f"[{name}]   -> FAILED ({result.failure_kind}) "
                              f"rc={proc.returncode} "
                              f"({result.n_frames_done}/{result.n_frames_input} frames) "
                              f"— see {rp.run_log}")
                    else:
                        print(f"[{name}]   -> {result.eff_fps:.2f} FPS, peak VRAM "
                              f"{result.vram_peak_gb:.2f} GB, e2e {result.latency_end_to_end_s:.1f}s "
                              f"[latency_source={result.latency_source}]")


# Signatures of an out-of-memory death, in the runner's log. OOM is NOT a bug in the
# harness and NOT a missing run — for a full-batch method it is a genuine, reportable
# property of the method (LASER's KITTI table reports VGGT / Pi3 / Fast3R as OOM on
# every sequence, so there is published precedent for stating it plainly). Recording
# it is the point: it is the cleanest evidence for why a streaming, bounded-memory
# engine is needed at all.
_OOM_PATTERNS = (
    "cuda out of memory",
    "torch.cuda.outofmemoryerror",
    "outofmemoryerror",
    "cublas_status_alloc_failed",
    "cudnn_status_alloc_failed",
    "failed to allocate",
    "std::bad_alloc",
    "out of memory",
)


def _classify_failure(run_log, returncode: int | None) -> str | None:
    """None if the run looks fine, else 'oom' | 'error' | 'killed'.

    'killed' covers the OOM-killer (SIGKILL = -9), which is what a *host* RAM
    exhaustion looks like from here — worth separating from a CUDA OOM.
    """
    if returncode == 0:
        return None
    try:
        text = run_log.read_text(errors="replace").lower() if run_log.exists() else ""
    except Exception:
        text = ""
    if any(p in text for p in _OOM_PATTERNS):
        return "oom"
    if returncode in (-9, 137):
        return "killed"
    return "error"


def _count_poses(poses_tum) -> int:
    """How many poses the method actually wrote (0 if it produced nothing)."""
    try:
        if not poses_tum.exists():
            return 0
        return sum(1 for ln in poses_tum.read_text().splitlines()
                   if ln.strip() and not ln.lstrip().startswith("#"))
    except Exception:
        return 0


def _merge_runner_perf(rp: RunPaths, result: PerfResult, window: int = 16, overlap: int = 4):
    """Fold in method-reported timings, then guarantee a valid latency for EVERY run.

    The 2026-07 big run logged `latency = 0.0` for 43 runs. The cause is here: a
    runner that never wrote `perf_runner.json` (because it crashed, or because it
    simply doesn't self-report — LASER and VGGT-SLAM emit no per-window markers)
    left the field at its 0.0 default, even though the orchestrator was holding a
    perfectly good wall-clock measurement the whole time.

    So: prefer the runner's own numbers when present, otherwise fall back to the
    orchestrator's `wall_s`, and always record WHERE the number came from in
    `latency_source` so a fallback can never be mistaken for a self-reported
    measurement:

        runner            — method reported it itself (most precise)
        orchestrator_wall — derived from the uniform subprocess timer
        unavailable       — no timing at all (should not happen post-fix)

    Per-window latency is likewise derived from wall time over the window count
    when a method emits no per-window markers, tagged via `per_window_source`.
    A derived value is an average, not a measured distribution — the aggregator
    reports the source alongside the number so the two are never silently mixed.
    """
    import json
    extra = rp.dir() / "perf_runner.json"
    if extra.exists():
        d = json.loads(extra.read_text())
        result.per_window_latency_s = d.get("per_window_latency_s", []) or []
        result.latency_end_to_end_s = d.get("latency_end_to_end_s", 0.0) or 0.0
        result.ckpt_size_mb = d.get("ckpt_size_mb", 0.0)
        result.extra = d.get("extra", {})

    wall = getattr(result, "wall_s", 0.0) or 0.0
    if result.latency_end_to_end_s and result.latency_end_to_end_s > 0:
        result.latency_source = "runner"
    elif wall > 0:
        result.latency_end_to_end_s = wall
        result.latency_source = "orchestrator_wall"
    else:
        result.latency_source = "unavailable"

    if result.per_window_latency_s:
        result.per_window_source = "runner"
    else:
        step = max(1, window - overlap)
        n_win = max(1, math.ceil(max(0, result.n_frames_done - overlap) / step)) \
            if result.n_frames_done else 0
        if n_win and result.latency_end_to_end_s > 0:
            result.per_window_latency_med_s = result.latency_end_to_end_s / n_win
            result.per_window_source = "derived_wall_over_windows"
            result.n_windows = n_win
        else:
            result.per_window_source = "unavailable"

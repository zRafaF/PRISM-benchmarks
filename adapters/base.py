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

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bench.config import REPO_ROOT, RunPaths, common_args, export_dir, load_config, resolve_scenes, resolve_trajs
from bench.perf import PerfResult, ResourceSampler


def method_cfg(cfg: dict, name: str) -> dict:
    for m in cfg["methods"]:
        if m["name"] == name:
            return m
    raise KeyError(f"method '{name}' not in config.methods")


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

    runner = Path(__file__).parent / "runners" / f"{name}_runner.py"
    device_index = 0

    for dataset in cfg["datasets"]["active"]:
        for scene in resolve_scenes(cfg, dataset, args.scenes):
            for traj in resolve_trajs(cfg, args.traj):
                for variant, in_dir in input_dirs_for(cfg, mcfg, dataset, scene, traj):
                    if not (in_dir / "meta.json").exists():
                        continue
                    rp = RunPaths(name, dataset, scene, traj, variant or mcfg["camera"])
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
                    with open(rp.run_log, "w") as log, ResourceSampler(device_index, pid=None) as smp:
                        proc = subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT, cwd=cwd)
                    # frame count from the input meta
                    import json
                    meta = json.loads((in_dir / "meta.json").read_text())
                    result.n_frames = meta.get("n_frames", 0)
                    smp.summarize(result)
                    _merge_runner_perf(rp, result)
                    result.write(rp.perf_json)
                    if proc.returncode != 0:
                        print(f"[{name}]   -> FAILED (see {rp.run_log})")
                    else:
                        print(f"[{name}]   -> {result.eff_fps:.2f} FPS, peak VRAM {result.vram_peak_gb:.2f} GB")


def _merge_runner_perf(rp: RunPaths, result: PerfResult):
    """Fold in method-reported timings (per-window latency, ckpt size, block count)
    that the runner may drop as perf_runner.json inside the result dir."""
    import json
    extra = rp.dir() / "perf_runner.json"
    if extra.exists():
        d = json.loads(extra.read_text())
        result.per_window_latency_s = d.get("per_window_latency_s", [])
        result.latency_end_to_end_s = d.get("latency_end_to_end_s", 0.0)
        result.ckpt_size_mb = d.get("ckpt_size_mb", 0.0)
        result.extra = d.get("extra", {})

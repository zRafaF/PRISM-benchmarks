"""Shared config + path helpers for every orchestrator script.

Kept dependency-light (pyyaml only). All scripts load config.yaml through here so
there is exactly one source of truth for scenes, camera params, thresholds, etc.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]


def _deep_merge(base: dict, over: dict) -> dict:
    for k, v in (over or {}).items():
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            base[k] = _deep_merge(base[k], v)
        else:
            base[k] = v
    return base


LOCAL_CONFIG = REPO_ROOT / "config.local.yaml"


def load_config(path: str | Path = "config.yaml") -> dict[str, Any]:
    """Load config.yaml, then merge a gitignored config.local.yaml on top if present.

    The overlay holds per-machine, non-committed state (e.g. the frozen scene list
    written by `make split`), so `git pull` never clobbers it or conflicts.
    """
    p = Path(path)
    if not p.is_absolute():
        p = REPO_ROOT / p
    with open(p, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    if LOCAL_CONFIG.exists():
        with open(LOCAL_CONFIG, "r", encoding="utf-8") as f:
            cfg = _deep_merge(cfg, yaml.safe_load(f) or {})
    return cfg


def common_args(description: str) -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=description)
    ap.add_argument("--config", default="config.yaml")
    ap.add_argument("--scenes", default="", help="space-separated scene ids; empty = config list")
    ap.add_argument("--traj", default="all", help="dataset_path | synthetic_spline | all")
    return ap


def resolve_scenes(cfg: dict, dataset: str, cli_scenes: str) -> list[str]:
    if cli_scenes.strip():
        return cli_scenes.split()
    return list(cfg["datasets"][dataset].get("scenes") or [])


def _seeds(cfg: dict) -> list[int]:
    """Benchmark seeds (variance study). Falls back to the single datasets.seed."""
    return list(cfg["datasets"].get("seeds") or [cfg["datasets"].get("seed", 1234)])


def resolve_trajs(cfg: dict, cli_traj: str) -> list[str]:
    """Expand trajectory families into concrete traj ids.

    Id scheme: ``<kind>_<rate>hz[_s<seedidx>]`` — e.g. ``synthetic_2.0hz``,
    ``loop_2.0hz_s1``. The smooth walkthrough keeps the ``synthetic_`` prefix (back-
    compat); ``trajectories.extra_kinds`` adds families like ``stopgo`` / ``loop``,
    each with its own rate list. The ``_s<i>`` suffix (only when >1 seed) indexes the
    seeds list, so each (kind × rate × seed) is a distinct, independently-rendered run.
    """
    tj = cfg["trajectories"]
    seeds = _seeds(cfg)
    nseed = len(seeds)
    # (prefix, rates) families: smooth first, then any extra kinds.
    families = [("synthetic", tj.get("rates_hz", [2.0]))]
    for name, kc in (tj.get("extra_kinds") or {}).items():
        families.append((name, (kc or {}).get("rates_hz", tj.get("rates_hz", [2.0]))))

    concrete = []
    for prefix, rates in families:
        for r in rates:
            for si in range(nseed):
                concrete.append(f"{prefix}_{r}hz" + (f"_s{si}" if nseed > 1 else ""))

    if cli_traj in ("all", ""):
        return concrete
    if cli_traj == "synthetic_spline":                 # legacy alias = the smooth sweep
        return [c for c in concrete if c.startswith("synthetic_")]
    if cli_traj in ("smooth", "stopgo", "loop"):       # a whole family
        return [c for c in concrete if c.startswith(cli_traj + "_")
                or (cli_traj == "smooth" and c.startswith("synthetic_"))]
    return [cli_traj]                                  # a single concrete id or dataset_path


def traj_rate_hz(traj: str, default: float = 2.0) -> float:
    """Parse the capture rate from any '<kind>_<rate>hz[_sN]' traj id."""
    import re
    m = re.search(r"([0-9]*\.?[0-9]+)hz", traj)
    return float(m.group(1)) if m else default


def traj_kind(traj: str) -> str:
    """Trajectory family from the id ('synthetic' | 'stopgo' | 'loop' | 'dataset_path')."""
    return traj.split("_", 1)[0] if "_" in traj else traj


def traj_seed(cfg: dict, traj: str) -> int:
    """Seed for a traj id: the '_s<idx>' suffix indexes the seeds list (else seed 0)."""
    import re
    seeds = _seeds(cfg)
    m = re.search(r"_s(\d+)$", traj)
    idx = int(m.group(1)) if m else 0
    return seeds[idx % len(seeds)]


# ── Common results layout (the ONLY thing eval/* reads) ──────────────────────
@dataclass(frozen=True)
class RunPaths:
    """results/<method>/<dataset>/<scene>/<traj>/<camera_variant>/"""
    method: str
    dataset: str
    scene: str
    traj: str
    variant: str

    def dir(self) -> Path:
        return REPO_ROOT / "results" / self.method / self.dataset / self.scene / self.traj / self.variant

    @property
    def poses_tum(self) -> Path:
        return self.dir() / "poses.tum"

    @property
    def cloud_ply(self) -> Path:
        return self.dir() / "cloud.ply"

    @property
    def perf_json(self) -> Path:
        return self.dir() / "perf.json"

    @property
    def run_log(self) -> Path:
        return self.dir() / "run.log"


def export_dir(dataset: str, scene: str, traj: str, camera_model: str, variant: str) -> Path:
    """dataset/exports/<dataset>/<scene>/<traj>/<camera_model>[/<variant>]"""
    base = REPO_ROOT / "dataset" / "exports" / dataset / scene / traj / camera_model
    return base / variant if variant else base

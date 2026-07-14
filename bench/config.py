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


def resolve_trajs(cfg: dict, cli_traj: str) -> list[str]:
    variants = cfg["trajectories"]["variants"]
    if cli_traj in ("all", ""):
        return list(variants)
    return [cli_traj]


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

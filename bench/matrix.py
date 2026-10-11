"""The run matrix as a list of (method, scene, traj) units — shared by the pre-check
(scripts/precheck.py) and the progress monitor (scripts/progress.py), so both agree
with scripts/run_overnight.sh on what "the whole benchmark" is.

A unit is one method on one rendered sequence. It is DONE when any camera-variant
dir under results/<method>/<ds>/<scene>/<traj>/ has a perf.json, and FAILED when
that perf.json says completed=false.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from bench.config import REPO_ROOT, load_config, resolve_trajs

import os

_SEED_RE = re.compile(r"_s(\d+)$")


def offline_enabled(cfg: dict) -> bool:
    """Offline (full-batch) methods run unless BENCH_OFFLINE=0 or baselines.run: false.
    They need 50-93 GB of VRAM at 200 frames, so turn them off on a 32 GB card."""
    env = os.environ.get("BENCH_OFFLINE", "").strip()
    if env:
        return env not in ("0", "false", "no")
    return bool((cfg.get("baselines") or {}).get("run", True))


def selected_methods() -> list[str]:
    """BENCH_METHODS="a b": this pod's share of the methods (multi-pod split)."""
    return os.environ.get("BENCH_METHODS", "").split()


def main_methods(cfg: dict) -> list[str]:
    """Every method the overnight runs on the full grid (sweep arms excluded),
    restricted to BENCH_METHODS when set (same rule as scripts/run_overnight.sh)."""
    off_ok = offline_enabled(cfg)
    out = [m["name"] for m in cfg.get("methods", []) if off_ok or m.get("mode") != "batch"]
    out += [m["name"] for m in cfg.get("ablations", []) if m.get("role") != "sweep"
            and (off_ok or m.get("mode") != "batch")]
    sel = selected_methods()
    return [m for m in out if m in sel] if sel else out


def offline_methods(cfg: dict) -> set[str]:
    """Methods limited to baselines.seeds: offline ones + arms flagged limited_seeds."""
    return {m["name"] for m in cfg.get("methods", []) + cfg.get("ablations", [])
            if m.get("mode") == "batch" or m.get("limited_seeds")}


def offline_seed_ok(cfg: dict, traj: str) -> bool:
    seeds = (cfg.get("baselines") or {}).get("seeds")
    if seeds is None:
        return True
    m = _SEED_RE.search(traj)
    return (m is None) or (int(m.group(1)) in {int(s) for s in seeds})


@dataclass
class Unit:
    method: str
    dataset: str
    scene: str
    traj: str

    def dir(self) -> Path:
        return REPO_ROOT / "results" / self.method / self.dataset / self.scene / self.traj

    def perf(self) -> dict | None:
        for pj in sorted(self.dir().glob("*/perf.json")):
            try:
                return json.loads(pj.read_text())
            except Exception:
                return {"completed": False}
        return None


def frozen_scenes(cfg: dict) -> list[str]:
    ds = cfg["datasets"]["active"][0]
    return list(cfg["datasets"][ds].get("scenes") or [])


def plan(cfg: dict | None = None, scenes: list[str] | None = None) -> list[Unit]:
    cfg = cfg or load_config("config.yaml")
    ds = cfg["datasets"]["active"][0]
    scenes = scenes or frozen_scenes(cfg)
    off = offline_methods(cfg)
    units = []
    for traj in resolve_trajs(cfg, "all"):
        for m in main_methods(cfg):
            if m in off and not offline_seed_ok(cfg, traj):
                continue
            for sc in scenes:
                units.append(Unit(m, ds, sc, traj))
    return units

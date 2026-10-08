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

_SEED_RE = re.compile(r"_s(\d+)$")


def main_methods(cfg: dict) -> list[str]:
    """Every method the overnight runs on the full grid (sweep arms excluded)."""
    out = [m["name"] for m in cfg.get("methods", [])]
    out += [m["name"] for m in cfg.get("ablations", []) if m.get("role") != "sweep"]
    return out


def offline_methods(cfg: dict) -> set[str]:
    return {m["name"] for m in cfg.get("methods", []) + cfg.get("ablations", [])
            if m.get("mode") == "batch"}


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

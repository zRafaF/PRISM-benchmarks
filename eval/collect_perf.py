"""Aggregate per-run perf.json into one perf.csv (Table A source).

The heavy lifting (uniform sampling of avg & peak VRAM, GPU util/power, latency)
happens in bench/perf.py while each method runs. This just gathers every
results/<...>/perf.json into a tidy CSV. Imports NO method.
"""
from __future__ import annotations

import argparse
import json
import statistics as st
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bench.config import REPO_ROOT, load_config

COLUMNS = ["method", "dataset", "scene", "traj", "variant", "n_frames",
           "eff_fps", "latency_end_to_end_s", "per_window_latency_med_s",
           "vram_avg_gb", "vram_peak_gb", "gpu_util_avg_pct", "gpu_power_avg_w",
           "cpu_ram_peak_gb", "ckpt_size_mb", "tsdf_block_count", "hw_id"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="config.yaml")
    args = ap.parse_args()
    cfg = load_config(args.config)
    hw = cfg["hardware"]["hw_id"]

    rows = []
    for pj in (REPO_ROOT / "results").glob("*/*/*/*/*/perf.json"):
        parts = pj.parent.parts
        i = parts.index("results")
        method, dataset, scene, traj, variant = parts[i + 1:i + 6]
        d = json.loads(pj.read_text())
        pw = d.get("per_window_latency_s") or []
        rows.append({
            "method": method, "dataset": dataset, "scene": scene, "traj": traj,
            "variant": variant, "n_frames": d.get("n_frames", 0),
            "eff_fps": round(d.get("eff_fps", 0), 3),
            "latency_end_to_end_s": round(d.get("latency_end_to_end_s", 0), 3),
            "per_window_latency_med_s": round(st.median(pw), 4) if pw else "",
            "vram_avg_gb": round(d.get("vram_avg_gb", 0), 3),
            "vram_peak_gb": round(d.get("vram_peak_gb", 0), 3),
            "gpu_util_avg_pct": round(d.get("gpu_util_avg_pct", 0), 1),
            "gpu_power_avg_w": round(d.get("gpu_power_avg_w", 0), 1),
            "cpu_ram_peak_gb": round(d.get("cpu_ram_peak_gb", 0), 3),
            "ckpt_size_mb": round(d.get("ckpt_size_mb", 0), 1),
            "tsdf_block_count": (d.get("extra") or {}).get("tsdf_block_count", ""),
            "hw_id": hw,
        })
    out = REPO_ROOT / "results" / "report"
    out.mkdir(parents=True, exist_ok=True)
    import csv
    with open(out / "perf.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        w.writeheader()
        w.writerows(rows)
    print(f"[collect_perf] {len(rows)} runs -> {out / 'perf.csv'}")


if __name__ == "__main__":
    main()

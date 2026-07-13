"""Uniform performance + resource sampling — applied to EVERY method.

Runs in the ORCHESTRATOR process that launches a method's subprocess, so the exact
same timer + GPU sampler wraps every method regardless of its own env. Numbers are
therefore directly comparable, not self-reported per repo.

Captures: wall time, effective FPS, per-window latencies (parsed from the method's
stdout markers, if it emits them), average & PEAK VRAM, GPU util %/power, CPU RAM peak.
"""
from __future__ import annotations

import json
import threading
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path


@dataclass
class PerfResult:
    method: str
    n_frames: int = 0
    wall_s: float = 0.0
    eff_fps: float = 0.0
    latency_end_to_end_s: float = 0.0
    per_window_latency_s: list[float] = field(default_factory=list)
    vram_peak_gb: float = 0.0
    vram_avg_gb: float = 0.0
    gpu_util_avg_pct: float = 0.0
    gpu_power_avg_w: float = 0.0
    cpu_ram_peak_gb: float = 0.0
    ckpt_size_mb: float = 0.0
    extra: dict = field(default_factory=dict)   # e.g. TSDF block count for ours

    def write(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(asdict(self), indent=2))


class ResourceSampler:
    """Background sampler for GPU (pynvml) + process RSS. Use as a context manager."""

    def __init__(self, device_index: int = 0, interval_s: float = 0.1, pid: int | None = None):
        self.device_index = device_index
        self.interval_s = interval_s
        self.pid = pid
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self.vram_samples_gb: list[float] = []
        self.util_samples: list[float] = []
        self.power_samples_w: list[float] = []
        self.rss_samples_gb: list[float] = []
        self._t0 = 0.0

    def _run(self):
        try:
            import pynvml
            pynvml.nvmlInit()
            h = pynvml.nvmlDeviceGetHandleByIndex(self.device_index)
        except Exception:
            h = None
        import os
        try:
            import psutil  # optional; RSS via /proc fallback if absent
            proc = psutil.Process(self.pid) if self.pid else None
        except Exception:
            proc = None
        while not self._stop.is_set():
            if h is not None:
                try:
                    import pynvml
                    mem = pynvml.nvmlDeviceGetMemoryInfo(h)
                    self.vram_samples_gb.append(mem.used / 1e9)
                    self.util_samples.append(pynvml.nvmlDeviceGetUtilizationRates(h).gpu)
                    try:
                        self.power_samples_w.append(pynvml.nvmlDeviceGetPowerUsage(h) / 1000.0)
                    except Exception:
                        pass
                except Exception:
                    pass
            if proc is not None:
                try:
                    self.rss_samples_gb.append(proc.memory_info().rss / 1e9)
                except Exception:
                    pass
            self._stop.wait(self.interval_s)

    def __enter__(self):
        self._t0 = time.perf_counter()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        return self

    def __exit__(self, *exc):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2.0)
        self.wall_s = time.perf_counter() - self._t0

    def summarize(self, result: PerfResult):
        import statistics as st
        result.wall_s = getattr(self, "wall_s", 0.0)
        if self.vram_samples_gb:
            result.vram_peak_gb = max(self.vram_samples_gb)
            result.vram_avg_gb = st.mean(self.vram_samples_gb)
        if self.util_samples:
            result.gpu_util_avg_pct = st.mean(self.util_samples)
        if self.power_samples_w:
            result.gpu_power_avg_w = st.mean(self.power_samples_w)
        if self.rss_samples_gb:
            result.cpu_ram_peak_gb = max(self.rss_samples_gb)
        if result.n_frames and result.wall_s > 0:
            result.eff_fps = result.n_frames / result.wall_s
        return result

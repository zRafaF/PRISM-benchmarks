#!/usr/bin/env python
"""VRAM-vs-#frames — the streaming claim, made measurable (report Deliverable 1).

Produces the memory-scaling figure the report promises ("a sweep of memory against
sequence length ... is left to future work", src/evaluation.typ): peak GPU memory
vs. number of input frames, measured the SAME way for every method, on one
representative seeded scene. The story it makes obvious: PRISM's streaming curve is
flat (bounded by window + mapped volume, ~15 GB); the offline batch nets
(PanoVGGT-offline, Pi3, MapAnything) grow with frame count and march into the GPU's
OOM ceiling.

Two sources, one output format (so the report wires in either without guesswork):

  --source perf-csv   (default, no GPU needed)
      Read the committed seeded perf.csv (real RTX PRO 6000 measurements) and plot
      peak VRAM vs. n_frames for ONE scene's rate sweep (same scene, increasing
      frames = a controlled prefix-like sweep). Reproducible from committed data.

  --source sweep      (on the reference GPU)
      Feed increasing prefixes of ONE seeded trajectory to each method, wrapped in
      the SAME bench.perf.ResourceSampler used everywhere else, and record peak VRAM
      + whether the run completed or hit CUDA OOM. This is what pushes past the
      200-frame config ceiling to each method's real OOM cap.

Both emit, into results/figures/ (or --out-dir):
  * vram_scaling.csv   — method, num_frames, peak_vram_gb, status(completed|oom), notes
  * vram_vs_frames.png — the plot (>=150 dpi at final size)

Data hygiene (non-negotiable, see docs/results_bigrun.md):
  * Seeded runs only (traj ending _s0/_s1); the contaminated aggregate tables are
    never read. Rendered scenes are noise-free (optimistic vs. real capture) — the
    caption keeps that caveat. OOM points are LABELLED, never extrapolated through.
  * The ~77-81 GB PRISM rows in the raw csv are GPU co-tenancy contamination (real
    footprint ~14-15 GB, roadmap gap #3); the single-scene view avoids them, and
    --drop-cotenancy clips any physically-impossible >co_tenancy_gb PRISM outliers.
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bench.config import REPO_ROOT, load_config, traj_rate_hz

DEFAULT_PERF_CSV = REPO_ROOT / "documentation" / "docs" / "data" / "bigrun_2026-07" / "perf.csv"
DEFAULT_OUT = REPO_ROOT / "results" / "figures"

# Display order + style. `kind` drives the visual grammar: batch = solid line +
# filled marker (grows); streaming = the flat curves (ours bold, others thin).
METHOD_STYLE = {
    "prism_sim3":  dict(label="PRISM-VGGT — Sim(3), streaming (ours)", kind="streaming",
                        color="#d62728", lw=2.8, ls="-",  marker="o", ms=7, z=6, headline=True),
    "prism":       dict(label="PRISM-VGGT — SL(4), streaming",         kind="streaming",
                        color="#e377c2", lw=2.0, ls="-",  marker="o", ms=6, z=5),
    "panovggt":    dict(label="PanoVGGT-offline (batch)",              kind="batch",
                        color="#1f77b4", lw=2.2, ls="-",  marker="s", ms=6, z=4),
    "pi3":         dict(label="Pi3 (batch)",                           kind="batch",
                        color="#ff7f0e", lw=2.2, ls="-",  marker="^", ms=6, z=4),
    "mapanything": dict(label="MapAnything (batch)",                   kind="batch",
                        color="#2ca02c", lw=2.2, ls="-",  marker="D", ms=6, z=4),
    "laser":       dict(label="LASER (streaming baseline)",            kind="streaming",
                        color="#7f7f7f", lw=1.4, ls="--", marker="v", ms=5, z=3),
    "vggtslam":    dict(label="VGGT-SLAM (streaming baseline)",        kind="streaming",
                        color="#9467bd", lw=1.4, ls="--", marker="P", ms=5, z=3),
}
DEFAULT_METHODS = ["prism_sim3", "panovggt", "pi3", "mapanything", "laser", "vggtslam"]


def _seeded(traj: str) -> bool:
    return traj.endswith("_s0") or traj.endswith("_s1")


# ── Source A: committed perf.csv (reproducible, no GPU) ───────────────────────
def _rows_from_perf_csv(perf_csv: Path, scene: str, methods: list[str],
                        traj_prefix: str, drop_cotenancy_gb: float):
    """Return {method: [(n_frames, peak_vram_gb, status, note), ...]} for one scene's
    seeded rate sweep. Aggregates the (>=1) seeds at each rate to a mean point, and
    keeps the individual seed points as faint 'raw' markers."""
    raw = list(csv.DictReader(open(perf_csv, newline="")))
    seeded = [r for r in raw if _seeded(r["traj"]) and r["traj"].startswith(traj_prefix)]
    if scene == "auto":
        # pick the scene with the most seeded rows for the requested methods
        from collections import Counter
        c = Counter(r["scene"] for r in seeded if r["method"] in methods)
        scene = c.most_common(1)[0][0] if c else ""
        print(f"[vram] auto-selected representative scene: {scene}")
    pts, rawpts = {}, {}
    card_gb = None
    for m in methods:
        rows = [r for r in seeded if r["method"] == m and r["scene"] == scene
                and r["n_frames"] and r["vram_peak_gb"]]
        # group by capture rate (same scene, one rate = one frame count, 1-2 seeds)
        by_rate: dict[float, list[tuple[int, float]]] = {}
        for r in rows:
            v = float(r["vram_peak_gb"])
            if card_gb is None and r.get("gpu_total_gb"):
                card_gb = float(r["gpu_total_gb"])
            # clip PRISM co-tenancy contamination (roadmap gap #3): a streaming pano
            # engine physically cannot exceed ~drop_cotenancy_gb; such rows are a
            # shared-GPU artefact, not this method's footprint.
            if drop_cotenancy_gb and m.startswith("prism") and v > drop_cotenancy_gb:
                continue
            by_rate.setdefault(traj_rate_hz(r["traj"]), []).append((int(r["n_frames"]), v))
        agg, rw = [], []
        for _rate, vals in sorted(by_rate.items()):
            nf = sum(a for a, _ in vals) / len(vals)
            vv = sum(b for _, b in vals) / len(vals)
            agg.append((nf, vv, "completed", f"mean of {len(vals)} seed(s)"))
            rw += [(a, b) for a, b in vals]
        if agg:
            pts[m] = sorted(agg)
            rawpts[m] = sorted(rw)
    return scene, pts, rawpts, (card_gb or 0.0)


# ── Source B: on-GPU prefix sweep (real OOM caps) ─────────────────────────────
def _run_prefix(cfg, mcfg, in_prefix: Path, out_dir: Path, device_index: int, hw_hint):
    """Run ONE method on ONE prefix export dir, wrapped in the shared sampler — the
    same subprocess+ResourceSampler block as adapters/base.py, so numbers are
    apples-to-apples. Returns (peak_vram_gb, status, note)."""
    import subprocess
    from adapters.base import method_python
    from bench.perf import PerfResult, ResourceSampler
    py = method_python(mcfg["env"])
    if not py.exists():
        return 0.0, "skipped", f"env python missing ({py}); run make setup-{mcfg['name']}"
    runner = REPO_ROOT / "adapters" / "runners" / f"{mcfg.get('runner', mcfg['name'])}_runner.py"
    out_dir.mkdir(parents=True, exist_ok=True)
    log = out_dir / "run.log"
    cmd = [str(py), str(runner), "--in", str(in_prefix), "--out", str(out_dir),
           "--config", str(REPO_ROOT / "config.yaml")]
    cwd = str((REPO_ROOT / mcfg["env"]).resolve())
    result = PerfResult(method=mcfg["name"])
    import os
    run_env = os.environ.copy()
    run_env.update({k: str(v) for k, v in (mcfg.get("run_env") or {}).items()})
    with open(log, "w") as lf, ResourceSampler(device_index, gpu_name_hint=hw_hint) as smp:
        proc = subprocess.run(cmd, stdout=lf, stderr=subprocess.STDOUT, cwd=cwd, env=run_env)
    smp.summarize(result)
    text = log.read_text(errors="ignore").lower() if log.exists() else ""
    oom = proc.returncode != 0 and ("out of memory" in text or "cuda oom" in text
                                    or "cublas_status_alloc_failed" in text)
    if oom:
        return result.vram_peak_gb, "oom", "CUDA OOM (marker in run.log)"
    if proc.returncode != 0:
        return result.vram_peak_gb, "failed", f"exit {proc.returncode} (see run.log)"
    return result.vram_peak_gb, "completed", ""


def _make_prefix_export(src_export: Path, n: int, tile: bool, work: Path) -> Path:
    """Build a prefix export dir with the first `n` frames (symlinked). If `tile`,
    repeat the sequence to reach n>available (memory stress beyond the render length:
    PRISM stays bounded on revisited volume while batch grows with frame count)."""
    import json
    names = sorted(p.stem for p in (src_export / "rgb").glob("*.png"))
    if not names:
        raise SystemExit(f"[vram] no frames in {src_export}")
    if n > len(names):
        if not tile:
            n = len(names)
        else:
            names = (names * (n // len(names) + 1))
    sel = names[:n]
    dst = work / f"prefix_{n:05d}"
    for sub in ("rgb", "depth", "mask"):
        (dst / sub).mkdir(parents=True, exist_ok=True)
    for i, nm in enumerate(sel):
        for sub, ext in (("rgb", ".png"), ("depth", ".npy"), ("mask", ".png")):
            s = src_export / sub / f"{nm}{ext}"
            if s.exists():
                d = (dst / sub / f"{i:05d}{ext}")
                if not d.exists():
                    d.symlink_to(s.resolve())
    for side in ("intrinsics.json", "meta.json"):
        if (src_export / side).exists():
            import shutil
            shutil.copy(src_export / side, dst / side)
    meta = json.loads((dst / "meta.json").read_text()) if (dst / "meta.json").exists() else {}
    meta["n_frames"] = n
    (dst / "meta.json").write_text(json.dumps(meta, indent=2))
    return dst


def _rows_from_sweep(cfg, scene, traj, methods, frames, tile, device_index):
    """Drive the real GPU sweep. Once a method OOMs at N frames it is not run at
    larger N (its curve stops at the cap)."""
    import tempfile
    from adapters.base import input_dirs_for, method_cfg
    dataset = cfg["datasets"]["active"][0]
    hw_hint = cfg.get("hardware", {}).get("hw_id")
    work = Path(tempfile.mkdtemp(prefix="vram_sweep_"))
    out_root = DEFAULT_OUT / "sweep_runs"
    print(f"[vram] === on-GPU sweep === scene={dataset}/{scene} traj={traj}", flush=True)
    print(f"[vram]     methods={methods}", flush=True)
    print(f"[vram]     frame grid={frames}  tile={tile}  device={device_index}", flush=True)
    print(f"[vram]     per-run logs under {out_root}/<method>/n<frames>/run.log\n", flush=True)
    pts = {}
    for mi, m in enumerate(methods, 1):
        mcfg = method_cfg(cfg, m)
        # locate this method's export for the chosen scene/traj (first variant)
        src = None
        for _variant, in_dir in input_dirs_for(cfg, mcfg, dataset, scene, traj):
            if (in_dir / "rgb").exists():
                src = in_dir
                break
        if src is None:
            print(f"[vram] ({mi}/{len(methods)}) {m}: no export at "
                  f"{dataset}/{scene}/{traj} — skip (run `make export` first)", flush=True)
            continue
        avail = len(list((src / "rgb").glob("*.png")))
        print(f"[vram] ({mi}/{len(methods)}) {m}: {avail} frames available at {src.name}/ — "
              f"sweeping {frames}", flush=True)
        series = []
        for n in frames:
            pdir = _make_prefix_export(src, n, tile, work)
            actual = len(list((pdir / "rgb").glob("*.png")))
            odir = out_root / m / f"n{actual:05d}"
            print(f"[vram]     {m:12s} n={actual:<5d} running… "
                  f"(log -> {odir}/run.log)", flush=True)
            vram, status, note = _run_prefix(cfg, mcfg, pdir, odir, device_index, hw_hint)
            icon = {"completed": "ok", "oom": "OOM", "failed": "FAIL",
                    "skipped": "skip"}.get(status, status)
            print(f"[vram]     {m:12s} n={actual:<5d} -> {vram:6.2f} GB  [{icon}]"
                  f"{('  ' + note) if note else ''}", flush=True)
            series.append((actual, vram, status, note))
            if status == "oom":
                print(f"[vram]     {m}: hit OOM at n={actual} — curve stops here.", flush=True)
                break
            if status == "skipped":
                break                       # env missing: same for every n, don't retry
        if series:
            pts[m] = series
    print(f"\n[vram] sweep done: {len(pts)}/{len(methods)} methods produced points.", flush=True)
    return pts


# ── Plot + CSV (shared) ───────────────────────────────────────────────────────
def _write_csv(out_csv: Path, pts: dict):
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with open(out_csv, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["method", "num_frames", "peak_vram_gb", "status", "notes"])
        for m in pts:
            for (nf, vram, status, note) in pts[m]:
                w.writerow([m, int(round(nf)), f"{vram:.2f}", status, note])
    print(f"[vram] wrote {out_csv}", flush=True)


def _plot(out_png: Path, scene: str, pts: dict, rawpts: dict, card_gb: float,
          logx: bool, source: str):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(8.0, 5.2))

    for m, series in pts.items():
        st = METHOD_STYLE.get(m, dict(label=m, kind="batch", color="k", lw=1.5,
                                      ls="-", marker="o", ms=5, z=3))
        xs = [nf for nf, *_ in series]
        ys = [v for _, v, *_ in series]
        ax.plot(xs, ys, color=st["color"], lw=st["lw"], ls=st["ls"], marker=st["marker"],
                ms=st["ms"], zorder=st["z"],
                label=st["label"] + (" ★" if st.get("headline") else ""))
        # faint raw seed points behind the aggregate
        if m in rawpts:
            rx = [a for a, _ in rawpts[m]]
            ry = [b for _, b in rawpts[m]]
            ax.scatter(rx, ry, s=12, color=st["color"], alpha=0.25, zorder=st["z"] - 1)
        # OOM marker: big X at the cap, curve already stops there
        for (nf, v, status, _n) in series:
            if status == "oom":
                ax.scatter([nf], [v], marker="x", s=170, color=st["color"],
                           linewidths=3, zorder=st["z"] + 1)
                ax.annotate("OOM", (nf, v), textcoords="offset points", xytext=(6, 6),
                            fontsize=8, color=st["color"], fontweight="bold")

    if card_gb:
        ax.axhline(card_gb, color="0.35", ls=":", lw=1.4, zorder=1)
        ax.text(ax.get_xlim()[1], card_gb, f"  GPU capacity {card_gb:.0f} GB (OOM ceiling)",
                va="bottom", ha="right", fontsize=8, color="0.35")

    if logx:
        ax.set_xscale("log")
    ax.set_xlabel("Number of input frames")
    ax.set_ylabel("Peak GPU memory (GB)")
    ax.set_title(f"Peak VRAM vs. sequence length — {scene} (seeded, RTX PRO 6000)")
    ax.grid(True, which="both", alpha=0.3)
    ax.legend(fontsize=8, loc="upper left", framealpha=0.9)
    cap = ("Source: committed seeded perf.csv (rate sweep on one scene)."
           if source == "perf-csv" else "Source: on-GPU prefix sweep.")
    fig.text(0.01, 0.005,
             cap + "  Rendered scenes are noise-free (optimistic vs. real capture). "
             "OOM points labelled, never extrapolated through.",
             fontsize=6.5, color="0.4")
    fig.tight_layout(rect=(0, 0.02, 1, 1))
    out_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_png, dpi=200)
    plt.close(fig)
    print(f"[vram] wrote {out_png}", flush=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--source", choices=["perf-csv", "sweep"], default="perf-csv")
    ap.add_argument("--config", default="config.yaml")
    ap.add_argument("--perf-csv", default=str(DEFAULT_PERF_CSV))
    ap.add_argument("--scene", default="auto",
                    help="representative scene (perf-csv: 'auto' picks the best-covered)")
    ap.add_argument("--traj", default="synthetic_2.0hz_s0",
                    help="sweep: the seeded trajectory whose prefixes are fed")
    ap.add_argument("--methods", default=",".join(DEFAULT_METHODS))
    ap.add_argument("--frames", default="1,2,4,8,16,32,64,128,256",
                    help="sweep: frame-count grid (prefixes); a method's curve stops at its OOM cap")
    ap.add_argument("--tile", action="store_true",
                    help="sweep: loop the sequence to reach frame counts beyond the render")
    ap.add_argument("--device", type=int, default=0)
    ap.add_argument("--logx", action="store_true", help="log-scale x-axis")
    ap.add_argument("--drop-cotenancy-gb", type=float, default=40.0,
                    help="clip PRISM rows above this as GPU co-tenancy artefacts (perf-csv)")
    ap.add_argument("--out-dir", default=str(DEFAULT_OUT))
    args = ap.parse_args()
    cfg = load_config(args.config)
    methods = [m.strip() for m in args.methods.split(",") if m.strip()]
    out = Path(args.out_dir)
    out_csv, out_png = out / "vram_scaling.csv", out / "vram_vs_frames.png"
    print(f"[vram] source={args.source}  out={out}", flush=True)

    if args.source == "perf-csv":
        traj_prefix = args.traj.split("_")[0] if "_" in args.traj else "synthetic"
        scene, pts, rawpts, card = _rows_from_perf_csv(
            Path(args.perf_csv), args.scene, methods, traj_prefix, args.drop_cotenancy_gb)
        if not pts:
            print("[vram] no matching seeded rows in perf.csv"); return
        _write_csv(out_csv, pts)
        _plot(out_png, scene, pts, rawpts, card, args.logx, "perf-csv")
    else:
        scene = args.scene if args.scene != "auto" else \
            (cfg["datasets"].get("replica", {}).get("scenes") or ["scene"])[0]
        frames = [int(x) for x in args.frames.replace(" ", "").split(",") if x]
        pts = _rows_from_sweep(cfg, scene, args.traj, methods, frames, args.tile, args.device)
        if not pts:
            print("[vram] sweep produced no points (exports missing?)"); return
        card = cfg.get("hardware", {}).get("gpu_total_gb", 0.0) or 0.0
        _write_csv(out_csv, pts)
        _plot(out_png, scene, pts, {}, card, args.logx or True, "sweep")


if __name__ == "__main__":
    main()

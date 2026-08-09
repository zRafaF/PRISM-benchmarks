#!/usr/bin/env python
"""PRISM-benchmarks Studio — a Gradio control panel (run `make preview`).

Tabs:
  * Run pipeline  — tick make targets, run them, watch stdout live, download the log.
  * Config        — edit key settings; saved to the gitignored config.local.yaml overlay.
  * Snapshots     — generate standardized paper images (GT-aligned, ceiling-clipped,
                    black/white bg) + gallery + zip download.
  * Point cloud   — interactive Plotly 3D viewer (+ optional GT overlay, aligned).
  * Frame preview — rendered RGB / depth / mask gallery.
  * Downloads     — browse & download any file/folder (folders zipped).

Runs from the repo root. `share=True` prints a public URL (handy on a remote box).
Only a fixed allowlist of make targets can be run — no arbitrary shell.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bench.config import REPO_ROOT, LOCAL_CONFIG, load_config

EXPORTS = REPO_ROOT / "dataset" / "exports"
RESULTS = REPO_ROOT / "results"
SNAP_DIR = RESULTS / "report" / "snapshots"

MAKE_TARGETS = [
    "init", "setup", "setup-prism", "setup-pi3", "setup-mapanything",
    "setup-vggtslam", "setup-laser", "download", "split", "render", "export",
    "run-prism", "run-pi3", "run-mapanything", "run-vggtslam", "run-laser",
    "eval-traj", "eval-recon", "eval-metric", "perf", "report", "snapshots",
    # Publication path (seeded-only). `report` aggregates EVERYTHING in results/,
    # which is what contaminated the 2026-07 tables; these are the clean ones.
    "ingest-archive", "report-clean", "report-tables", "verify-clean", "publication",
    # Fairness arms + the pre-flight test run.
    "run-vggtslam-arms", "smoke", "smoke-check", "bundle",
    "fig-vram", "fig-vram-sweep", "fig-cubemap", "fig-cubemap-export",
    "fig-cubemap-engine", "fig-fusion", "fig-fusion-results", "figures",
]

# Report figures (first-class artifacts) live here; the Figures tab renders +
# serves them. Keep names in sync with eval/vram_scaling.py + eval/fig_cubemap.py.
FIG_DIR = RESULTS / "figures"
FIG_ARTIFACTS = {
    "VRAM vs. frames (plot)":    FIG_DIR / "vram_vs_frames.png",
    "VRAM scaling (CSV)":        FIG_DIR / "vram_scaling.csv",
    "Cubemap — composed":        FIG_DIR / "cubemap_projection.png",
    "Cubemap — equirect":        FIG_DIR / "cubemap_equirect.png",
    "Cubemap — faces":           FIG_DIR / "cubemap_faces.png",
    "Cubemap — depth":           FIG_DIR / "cubemap_depth.png",
    "Cubemap — fused":           FIG_DIR / "cubemap_fused.png",
    "Cubemap — caption":         FIG_DIR / "cubemap_projection.txt",
    "Fusion — per-view":         FIG_DIR / "fusion_perview.png",
    "Fusion — fused":            FIG_DIR / "fusion_fused.png",
    "Fusion — caption":          FIG_DIR / "fusion.txt",
}


# ── Run pipeline (stream make output) ─────────────────────────────────────────
# Log lives at the REPO ROOT (not under results/, which `clean-results` wipes mid-run).
LOGPATH = REPO_ROOT / "studio_run.log"


def _bar(k, n):
    filled = int(20 * k / max(n, 1))
    return "|" + "#" * filled + "." * (20 - filled) + f"| {100*k//max(n,1):d}%"


def run_targets(targets, scenes, traj):
    """Run each make target IN TURN, streaming to Gradio AND the terminal, with a
    per-target progress bar. Stops at the first failure (so the log shows what broke)."""
    if not targets:
        yield "Select at least one target.", None
        return
    extra = []
    if scenes and scenes.strip():
        extra.append(f"SCENES={scenes.strip()}")
    if traj and traj.strip():
        extra.append(f"TRAJ={traj.strip()}")

    acc = ""
    n = len(targets)
    lf = open(LOGPATH, "w")

    def emit(text):
        nonlocal acc
        acc += text
        lf.write(text); lf.flush()
        print(text, end="", flush=True)      # also to the terminal — survives a UI crash

    for k, tgt in enumerate(targets, 1):
        emit(f"\n{'='*64}\n[{k}/{n}] {_bar(k-1, n)}  make {tgt} {' '.join(extra)}\n{'='*64}\n")
        yield acc, None
        try:
            p = subprocess.Popen(["make", tgt] + extra, cwd=str(REPO_ROOT),
                                 stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                 text=True, bufsize=1)
        except Exception as e:
            emit(f"[failed to launch: {e}]\n"); yield acc, str(LOGPATH); return
        for line in p.stdout:
            emit(line)
            yield acc, str(LOGPATH)
        p.wait()
        emit(f"[{k}/{n}] {tgt} -> exit {p.returncode}\n")
        yield acc, str(LOGPATH)
        if p.returncode != 0:
            emit(f"\n[STOPPED — '{tgt}' failed; fix and re-run]\n")
            lf.close(); yield acc, str(LOGPATH); return
    emit(f"\n[DONE {n}/{n}] {_bar(n, n)}\n")
    lf.close()
    yield acc, str(LOGPATH)


METHODS = ["prism", "panovggt", "pi3", "vggtslam", "mapanything", "laser"]


def _save_pipeline_overlay(scenes, rates_csv, max_frames):
    import yaml
    overlay = (yaml.safe_load(LOCAL_CONFIG.read_text()) if LOCAL_CONFIG.exists() else {}) or {}
    if rates_csv and rates_csv.strip():
        overlay.setdefault("trajectories", {})["rates_hz"] = [
            float(x) for x in rates_csv.replace(" ", "").split(",") if x]
    if scenes and scenes.strip():
        overlay.setdefault("datasets", {}).setdefault("replica", {})["scenes"] = scenes.split()
    overlay.setdefault("baselines", {})["max_frames"] = None if not max_frames else int(max_frames)
    LOCAL_CONFIG.write_text(yaml.safe_dump(overlay, sort_keys=False))


def full_pipeline(scenes, methods, rates_csv, max_frames, clean_first, do_snapshots):
    """One button: (optionally clean) -> render -> export -> run each selected method
    -> eval-* -> report (-> snapshots), streaming the log. Applies scenes/rates/max_frames
    to the config overlay first so every step is consistent."""
    if not methods:
        yield "Select at least one method.", None
        return
    _save_pipeline_overlay(scenes, rates_csv, max_frames)
    targets = (["clean-results"] if clean_first else []) + ["render", "export"]
    targets += [f"run-{m}" for m in methods]
    targets += ["eval-traj", "eval-recon", "eval-metric", "perf", "report"]
    # Always finish on the publication path: the clean seeded-only aggregate, the
    # report-facing bundle, and the contamination check. Cheap (no GPU) and it means
    # the one-button run leaves behind numbers that are actually citable.
    targets += ["report-clean", "report-tables", "verify-clean"]
    if do_snapshots:
        targets.append("snapshots")
    yield from run_targets(targets, scenes, "all")


# ── Config overlay editor ─────────────────────────────────────────────────────
def load_config_fields():
    cfg = load_config("config.yaml")
    rates = ", ".join(str(r) for r in cfg["trajectories"].get("rates_hz", []))
    scenes = " ".join(cfg["datasets"].get("replica", {}).get("scenes") or [])
    mf = (cfg.get("baselines") or {}).get("max_frames")
    fscore = cfg["eval"]["fscore_threshold_m"]
    noise = cfg["eval"].get("cleanliness", {}).get("noise_threshold_m", 0.10)
    return rates, scenes, (mf or 0), fscore, noise


def save_config_fields(rates_str, scenes_str, max_frames, fscore_thr, noise_thr):
    import yaml
    overlay = {}
    if LOCAL_CONFIG.exists():
        overlay = yaml.safe_load(LOCAL_CONFIG.read_text()) or {}
    if rates_str.strip():
        overlay.setdefault("trajectories", {})["rates_hz"] = [
            float(x) for x in rates_str.replace(" ", "").split(",") if x]
    if scenes_str.strip():
        overlay.setdefault("datasets", {}).setdefault("replica", {})["scenes"] = scenes_str.split()
    overlay.setdefault("baselines", {})["max_frames"] = None if not max_frames else int(max_frames)
    ev = overlay.setdefault("eval", {})
    ev["fscore_threshold_m"] = float(fscore_thr)
    ev.setdefault("cleanliness", {})["noise_threshold_m"] = float(noise_thr)
    LOCAL_CONFIG.write_text(yaml.safe_dump(overlay, sort_keys=False))
    return f"Saved -> {LOCAL_CONFIG.name} (gitignored; merged over config.yaml):\n\n" + \
           yaml.safe_dump(overlay, sort_keys=False)


# ── Snapshots ─────────────────────────────────────────────────────────────────
# (snapshot generation is wired inline in the Snapshots tab via eval.snapshots.generate)


def _zip_dir(d: Path):
    tmp = tempfile.mkdtemp()
    return shutil.make_archive(os.path.join(tmp, d.name or "snapshots"), "zip", root_dir=str(d))


# Snapshot filenames are  <method>__<scene>_<traj>_<variant>__<mask>__<view>__<bg>.png
# (and  GT__<scene>_<traj>__<mask>__<view>__<bg>.png). Scene and traj are joined by an
# underscore with no separator, so they're split on the trajectory-family prefix.
_TRAJ_RE = re.compile(r"_(?:synthetic|stopgo|loop)_\d")


def _snap_scene(n):
    """Scene id from a snapshot filename.

    Previously this split on the literal '_synthetic_', which silently produced
    garbage for the stop-and-go and loop families (and for pinhole runs, whose
    variant is itself called 'synthetic_fov' — so 'room_0_loop_2.0hz_s1_synthetic_fov'
    came back as 'room_0_loop_2.0hz_s1'). Splitting on the family prefix instead
    handles every trajectory id and both camera variants.
    """
    body = n.split("__", 1)[1] if "__" in n else n
    return _TRAJ_RE.split(body, maxsplit=1)[0]


def _snap_traj(n):
    """Trajectory id ('synthetic_2.0hz_s0', 'loop_2.0hz_s1', ...) or '' if absent."""
    body = n.split("__", 1)[1] if "__" in n else n
    m = re.search(r"(synthetic|stopgo|loop)_\d[^_]*(?:_s\d+)?", body)
    return m.group(0) if m else ""


def _snap_method(n):
    return n.split("__", 1)[0]


def _snap_view(n):
    return "oblique" if "__oblique__" in n else ("top" if "__top__" in n else "")


def _snap_mask(n):
    """Co-visibility variant encoded in the filename (full | covis | masked).

    Older snapshots predate the variant field and have no '__<mask>__' segment;
    they are reported as 'full', which is what they were.
    """
    for mv in ("full", "covis", "masked"):
        if f"__{mv}__" in n:
            return mv
    return "full"


def _snap_bg(n):
    return "black" if n.endswith("__black.png") else ("white" if n.endswith("__white.png") else "")


def _filter_snaps(scenes, methods, views, bgs, masks=None, trajs=None):
    """Filter snapshot PNGs by multi-select criteria (empty list = no filter on that field)."""
    if not SNAP_DIR.exists():
        return []
    files = []
    for p in sorted(SNAP_DIR.glob("*.png")):
        n = p.name
        if scenes and _snap_scene(n) not in scenes:
            continue
        if methods and _snap_method(n) not in methods:
            continue
        if views and _snap_view(n) not in views:
            continue
        if bgs and _snap_bg(n) not in bgs:
            continue
        if masks and _snap_mask(n) not in masks:
            continue
        if trajs and _snap_traj(n) not in trajs:
            continue
        files.append(str(p))
    return files


PAGE_SIZE = 24


def snap_page(scenes, methods, views, bgs, masks, trajs, page):
    """Return (paths_for_page, status_text) — paginated so the gallery always loads."""
    files = _filter_snaps(scenes, methods, views, bgs, masks, trajs)
    n = len(files)
    pages = max(1, (n + PAGE_SIZE - 1) // PAGE_SIZE)
    page = max(1, min(int(page or 1), pages))
    sl = files[(page - 1) * PAGE_SIZE: page * PAGE_SIZE]
    return sl, f"{n} images match · page {page}/{pages}  ({PAGE_SIZE}/page)"


def zip_filtered(scenes, methods, views, bgs, masks, trajs):
    """Zip the currently-filtered snapshots for download."""
    import zipfile
    files = _filter_snaps(scenes, methods, views, bgs, masks, trajs)
    if not files:
        return None
    tmp = tempfile.mkdtemp()
    zpath = os.path.join(tmp, "snapshots.zip")
    with zipfile.ZipFile(zpath, "w") as z:
        for f in files:
            z.write(f, os.path.basename(f))
    return zpath


def _snap_scene_choices():
    return sorted({_snap_scene(p.name) for p in SNAP_DIR.glob("*.png")}) if SNAP_DIR.exists() else []


def _snap_traj_choices():
    return sorted({t for t in (_snap_traj(p.name) for p in SNAP_DIR.glob("*.png")) if t}) \
        if SNAP_DIR.exists() else []


def _snap_method_choices():
    """Method names actually present in the snapshot dir (so ablation arms like
    prism_se3 / prism_sl4 appear in the filter, not just the hardcoded baselines)."""
    if not SNAP_DIR.exists():
        return METHODS + ["GT"]
    found = sorted({_snap_method(p.name) for p in SNAP_DIR.glob("*.png")})
    return found or (METHODS + ["GT"])


# ── Frame preview ─────────────────────────────────────────────────────────────
def list_runs():
    return sorted({str(p.parent.relative_to(EXPORTS)) for p in EXPORTS.glob("*/*/*/**/rgb")})


def _frame_names(run):
    return sorted(p.stem for p in (EXPORTS / run / "rgb").glob("*.png")) if run else []


def _depth_to_rgb(depth):
    import matplotlib.cm as cm
    d = depth.astype(np.float32); valid = d > 0
    if valid.any():
        lo, hi = np.percentile(d[valid], [2, 98])
        dn = np.clip((d - lo) / max(hi - lo, 1e-6), 0, 1)
    else:
        dn = np.zeros_like(d)
    rgb = (cm.turbo(dn)[..., :3] * 255).astype(np.uint8); rgb[~valid] = 0
    return rgb


def preview_frame(run, idx):
    import imageio.v2 as imageio
    if not run:
        return None, None, None, "Pick a run."
    base = EXPORTS / run
    names = _frame_names(run)
    if not names:
        return None, None, None, f"No frames in {run}"
    i = int(max(0, min(idx, len(names) - 1)))
    name = names[i]
    rgb = np.asarray(imageio.imread(base / "rgb" / f"{name}.png"))
    depth = np.load(base / "depth" / f"{name}.npy")
    mp = base / "mask" / f"{name}.png"
    mask = np.asarray(imageio.imread(mp)) if mp.exists() else np.zeros(depth.shape, np.uint8)
    valid = depth[depth > 0]
    dr = (f"depth {valid.min():.2f}-{valid.max():.2f} m, {100*(depth>0).mean():.0f}% valid"
          if valid.size else "⚠ 0% valid — camera outside / wrong up-axis?")
    return rgb, _depth_to_rgb(depth), mask, f"{run}\nframe {i+1}/{len(names)} ({name})\n{dr}"


# ── Point cloud viewer ────────────────────────────────────────────────────────
def list_clouds():
    items = ["pred: " + str(p.relative_to(RESULTS)) for p in RESULTS.glob("*/*/*/*/*/cloud.ply")]
    items += ["GT:   " + str(p.relative_to(EXPORTS)) for p in EXPORTS.glob("*/*/*/gt_mesh.ply")]
    return sorted(items)


def _subsample(pts, cols, n, seed=0):
    if len(pts) > n:
        idx = np.random.default_rng(seed).choice(len(pts), n, replace=False)
        return pts[idx], (cols[idx] if cols is not None else None)
    return pts, cols


def show_cloud(label, max_points, overlay_gt=False):
    import open3d as o3d
    import plotly.graph_objects as go
    if not label:
        return go.Figure()
    rel = label[6:].strip()
    path = (RESULTS / rel) if label.startswith("pred:") else (EXPORTS / rel)
    pcd = o3d.io.read_point_cloud(str(path))
    pts = np.asarray(pcd.points)
    if len(pts) == 0:
        return go.Figure(layout={"title": f"empty: {path.name}"})
    cols = np.asarray(pcd.colors) if pcd.has_colors() else None
    traces, title = [], f"{path.name}: {len(pts):,} pts"
    if overlay_gt and label.startswith("pred:"):
        try:
            from eval.eval_recon import _align_pred_to_gt, _icp_refine
            parts = Path(rel).parts
            ds, scene, traj = parts[1], parts[2], parts[3]
            gtd = EXPORTS / ds / scene / traj
            aligned, _ = _align_pred_to_gt(pts, (RESULTS / rel).parent / "poses.tum",
                                           gtd / "poses_gt.tum", True)
            gt = o3d.io.read_point_cloud(str(gtd / "gt_mesh.ply"))
            gtp = np.asarray(gt.points)
            aligned = _icp_refine(aligned, gtp, 0.15)
            pts = aligned
            gp, _ = _subsample(gtp, None, max_points, 1)
            traces.append(go.Scatter3d(x=gp[:, 0], y=gp[:, 1], z=gp[:, 2], mode="markers",
                                       name="GT", marker=dict(size=1.0, color="lightgray")))
            title += " + GT (aligned)"
        except Exception as e:
            title += f"  (overlay failed: {e})"
    sp, sc = _subsample(pts, cols, max_points)
    if sc is not None:
        mk = dict(size=1.4, color=["rgb(%d,%d,%d)" % (r*255, g*255, b*255) for r, g, b in sc])
    else:
        mk = dict(size=1.4, color=sp[:, 2], colorscale="Viridis")
    traces.append(go.Scatter3d(x=sp[:, 0], y=sp[:, 1], z=sp[:, 2], mode="markers",
                               name="reconstruction", marker=mk))
    fig = go.Figure(traces)
    fig.update_layout(scene=dict(aspectmode="data"), margin=dict(l=0, r=0, t=30, b=0),
                      title=title, showlegend=True)
    return fig


# ── Report figures (Deliverables 1 & 2: VRAM sweep + cubemap projection) ───────
def _fig_gallery():
    order = ["vram_vs_frames.png", "cubemap_projection.png", "cubemap_equirect.png",
             "cubemap_faces.png", "cubemap_depth.png", "cubemap_fused.png",
             "fusion_perview.png", "fusion_fused.png"]
    return [str(FIG_DIR / n) for n in order if (FIG_DIR / n).exists()]


def _fig_files():
    return [str(p) for p in FIG_ARTIFACTS.values() if p.exists()]


def _stream_fig_script(rel_script: str, extra_args: list[str]):
    """Run an eval/*.py figure script and STREAM its stdout live to the UI (a slow
    on-GPU sweep prints progress as it goes, instead of nothing until it finishes).
    `-u` + PYTHONUNBUFFERED make the child's prints arrive line-by-line."""
    cmd = [sys.executable, "-u", str(REPO_ROOT / rel_script)] + extra_args
    g0, f0 = _fig_gallery(), _fig_files()          # keep current figures visible during the run
    acc = f"$ {' '.join(cmd)}\n\n(running — live output below)\n\n"
    yield acc, g0, f0
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    try:
        p = subprocess.Popen(cmd, cwd=str(REPO_ROOT), stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT, text=True, bufsize=1, env=env)
    except Exception as e:
        yield acc + f"[failed to launch: {e}]\n", g0, f0
        return
    for line in p.stdout:
        acc += line
        yield acc, g0, f0
    p.wait()
    acc += f"\n[exit {p.returncode}]\n"
    yield acc, _fig_gallery(), _fig_files()          # refresh figures once, at the end


def gen_vram_perfcsv(scene):
    yield from _stream_fig_script(
        "eval/vram_scaling.py", ["--source", "perf-csv", "--scene", scene or "auto"])


def gen_vram_sweep(scene, frames, traj, tile):
    args = ["--source", "sweep", "--scene", scene or "auto", "--logx",
            "--traj", traj or "synthetic_2.0hz_s0"]
    if frames and frames.strip():
        args += ["--frames", frames.replace(" ", "")]
    if tile:
        args += ["--tile"]
    yield from _stream_fig_script("eval/vram_scaling.py", args)


def gen_cubemap_schematic(scene, traj):
    yield from _stream_fig_script("eval/fig_cubemap.py",
                                  ["--mode", "illustrative"] + (["--scene", scene] if scene else []))


def gen_cubemap_dataset(scene, traj):
    args = ["--mode", "dataset"] + (["--scene", scene] if scene and scene != "auto" else [])
    args += ["--traj", traj or "synthetic_2.0hz_s0"]
    yield from _stream_fig_script("eval/fig_cubemap.py", args)


def gen_cubemap_engine(scene, traj):
    args = ["--mode", "export"] + (["--scene", scene] if scene and scene != "auto" else [])
    args += ["--traj", traj or "synthetic_2.0hz_s0"]
    yield from _stream_fig_script("eval/fig_cubemap.py", args)


def gen_fusion_dataset(scene, traj):
    args = ["--mode", "dataset"] + (["--scene", scene] if scene and scene != "auto" else [])
    args += ["--traj", traj or "synthetic_5.0hz_s0"]
    yield from _stream_fig_script("eval/fig_fusion.py", args)


def gen_fusion_results(scene, traj):
    args = ["--mode", "results"] + (["--scene", scene] if scene and scene != "auto" else [])
    args += ["--traj", traj or "synthetic_5.0hz_s0"]
    yield from _stream_fig_script("eval/fig_fusion.py", args)


# ── File downloader ───────────────────────────────────────────────────────────
def prepare_download(selected_path):
    import gradio as gr
    if not selected_path:
        raise gr.Error("Select a file or folder first.")
    full = os.path.abspath(selected_path)
    if not os.path.exists(full):
        raise gr.Error("Not found on the server.")
    if os.path.isfile(full):
        return full
    tmp = tempfile.mkdtemp()
    return shutil.make_archive(os.path.join(tmp, os.path.basename(full) or "archive"), "zip", root_dir=full)


# ── Smoke test + clean-results helpers ────────────────────────────────────────
CLEAN_DIR = RESULTS / "report_clean"
TABLES_DIR = RESULTS / "report_tables"


def run_smoke(traj, methods_csv):
    """Stream the smoke test. Env vars (not make vars) drive scripts/smoke_test.sh."""
    env = os.environ.copy()
    if (traj or "").strip() and traj.strip() != "all":
        env["SMOKE_TRAJ"] = traj.strip()
    if (methods_csv or "").strip():
        env["SMOKE_METHODS"] = methods_csv.replace(",", " ").strip()
    buf = ["Running smoke test — this exercises EVERY stage and method on a tiny "
           "matrix, then projects how long the full run will take.\n"]
    yield "".join(buf), None
    try:
        proc = subprocess.Popen(["bash", "scripts/smoke_test.sh"], cwd=str(REPO_ROOT),
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                text=True, bufsize=1, env=env)
    except Exception as e:
        yield f"failed to launch: {e}", None
        return
    for line in iter(proc.stdout.readline, ""):
        buf.append(line)
        print(line, end="")
        yield "".join(buf[-400:]), None
    proc.wait()
    logs = sorted((REPO_ROOT / "logs").glob("smoke_*.log"))
    buf.append(f"\n=== smoke test exited {proc.returncode} "
               f"({'PASSED' if proc.returncode == 0 else 'FAILED'}) ===\n")
    yield "".join(buf[-400:]), (str(logs[-1]) if logs else None)


def _read_clean(name, limit=None):
    p = CLEAN_DIR / name
    if not p.exists():
        return f"_{name} not found — run **report-clean** first._"
    txt = p.read_text(encoding="utf-8", errors="replace")
    if limit:
        txt = "\n".join(txt.splitlines()[:limit])
    return txt


def _csv_md(name, max_rows=40):
    """Render a clean-results CSV as a markdown table for display."""
    import csv as _csv
    p = CLEAN_DIR / name
    if not p.exists():
        return f"_{name} not found — run **report-clean** first._"
    with open(p, newline="", encoding="utf-8") as f:
        rows = list(_csv.reader(f))
    if not rows:
        return f"_{name} is empty._"
    head, body = rows[0], rows[1:max_rows + 1]
    out = "| " + " | ".join(head) + " |\n| " + " | ".join("---" for _ in head) + " |\n"
    for r in body:
        out += "| " + " | ".join(r) + " |\n"
    if len(rows) - 1 > len(body):
        out += f"\n_{len(rows) - 1 - len(body)} more row(s) — download the CSV._"
    return out


def clean_bundle_files():
    """Every emitted clean/report-facing artifact, for download."""
    files = []
    for d in (CLEAN_DIR, TABLES_DIR):
        if d.exists():
            files += [str(p) for p in sorted(d.iterdir()) if p.is_file()]
    return files


# ── Results bundle (one-click download) ───────────────────────────────────────
def bundle_estimate_md(categories):
    """Markdown size table for the current selection, sizing EVERY category so the
    cost of including the point clouds is visible before you commit to it."""
    from eval import bundle_results as br
    # None = first load (use defaults); [] = the user explicitly unticked everything,
    # which must not silently fall back to the defaults.
    cats = list(br.DEFAULT_ON) if categories is None else list(categories)
    rows, total, count = br.estimate(cats)
    md = ("| Include | Category | Files | Size | What it is |\n"
          "| --- | --- | ---: | ---: | --- |\n")
    for cat, n, size, inc in rows:
        md += (f"| {'✅' if inc else '—'} | `{cat}` | {n} | {br.human(size)} | "
               f"{br.CATEGORIES[cat][1]} |\n")
    if not cats:
        return md + "\n> Nothing selected — tick at least one category above.\n"
    md += f"\n**Selected: {count} files, {br.human(total)}** (uncompressed).\n"
    if total > 2 * 1024 ** 3:
        md += ("\n> ⚠️ **Over 2 GB.** Browser downloads of this size are unreliable. "
               "Untick `clouds`, or pull it off the box directly:\n"
               "> ```\n> rsync -avz <host>:<repo>/results/ ./results/\n> ```\n")
    elif total == 0:
        md += "\n> Nothing found — has the benchmark run yet?\n"
    return md


def bundle_build(categories, compress):
    """Build the zip, streaming progress. Yields (status_md, file) for Gradio."""
    from eval import bundle_results as br
    from datetime import datetime
    cats = list(br.DEFAULT_ON) if categories is None else list(categories)
    if not cats:
        yield "Nothing selected — tick at least one category above.", None
        return
    _rows, total, count = br.estimate(cats)
    if count == 0:
        yield ("Nothing to bundle: the selected categories contain no files. "
               "Has the benchmark run yet?"), None
        return
    out = (REPO_ROOT / "results" / "bundles" /
           f"prism-benchmarks_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip")
    yield (f"Bundling {count} files ({br.human(total)})… "
           f"large selections take a while — the clouds are stored uncompressed."), None
    state = {"done": 0}

    def _p(i, n):
        state["done"] = i
    try:
        br.build(cats, out, compress=compress, progress=_p)
    except Exception as e:
        yield f"**Bundle failed:** `{e.__class__.__name__}: {e}`", None
        return
    size = out.stat().st_size
    yield (f"**Done — {count} files, {br.human(size)} zipped.**\n\n"
           f"Saved on the benchmark box at `{out.relative_to(REPO_ROOT)}` "
           f"(also downloadable below). Open `MANIFEST.txt` inside for what's included "
           f"and what to read first."), str(out)


def existing_bundles():
    d = RESULTS / "bundles"
    return [str(p) for p in sorted(d.glob("*.zip"), reverse=True)] if d.exists() else []


def build_app():
    import gradio as gr
    with gr.Blocks(title="PRISM-benchmarks Studio") as demo:
        gr.Markdown("# 🛠️ PRISM-benchmarks Studio")

        with gr.Tab("▶ Pipeline (one button)"):
            gr.Markdown("Configure and run the **whole benchmark** end-to-end: "
                        "render → export → run methods → eval → report (→ snapshots). "
                        "Output streams live; the log is downloadable.")
            r0, s0, m0, _f0, _n0 = load_config_fields()
            default_scenes = s0 if len(s0.split()) >= 2 else "office_4 apartment_0"
            with gr.Row():
                pl_scenes = gr.Textbox(value=default_scenes, label="Scenes (space-separated)", scale=2)
                pl_rates = gr.Textbox(value=(r0 or "0.5,2.0,5.0"), label="Rates Hz (comma)", scale=1)
                pl_maxf = gr.Number(value=m0, label="max_frames (0=all)", precision=0, scale=1)
            pl_methods = gr.CheckboxGroup(METHODS, value=METHODS, label="Methods to run")
            with gr.Row():
                pl_clean = gr.Checkbox(value=True, label="Clean previous results first")
                pl_snap = gr.Checkbox(value=True, label="Render snapshots at the end")
            pl_btn = gr.Button("▶  Run FULL pipeline", variant="primary")
            pl_out = gr.Textbox(label="Live output", lines=22, autoscroll=True)
            pl_log = gr.File(label="Download log", interactive=False)
            pl_btn.click(full_pipeline, [pl_scenes, pl_methods, pl_rates, pl_maxf, pl_clean, pl_snap],
                         [pl_out, pl_log])

        with gr.Tab("Run targets (advanced)"):
            gr.Markdown("Tick targets and run. Output streams live; the log is downloadable. "
                        "Typical order: setup → render → export → run-* → eval-* → report → snapshots.")
            tsel = gr.CheckboxGroup(MAKE_TARGETS, label="make targets (run in order)")
            with gr.Row():
                sc = gr.Textbox(label="SCENES (optional)", scale=1)
                tj = gr.Textbox(value="all", label="TRAJ", scale=1)
            run_btn = gr.Button("Run selected", variant="primary")
            out = gr.Textbox(label="Live output", lines=24, autoscroll=True)
            logf = gr.File(label="Download log", interactive=False)
            run_btn.click(run_targets, [tsel, sc, tj], [out, logf])

        with gr.Tab("Config"):
            gr.Markdown("Edits are saved to **config.local.yaml** (gitignored, merged over "
                        "config.yaml) — survives `git pull`.")
            r0, s0, m0, f0, n0 = load_config_fields()
            rates = gr.Textbox(value=r0, label="rates_hz (comma-separated capture rates)")
            scenes = gr.Textbox(value=s0, label="replica scenes (space-separated; blank = keep)")
            maxf = gr.Number(value=m0, label="baselines.max_frames (0 = all)", precision=0)
            fscore = gr.Number(value=f0, label="eval F-score threshold (m)")
            noise = gr.Number(value=n0, label="cleanliness noise threshold (m)")
            save_btn = gr.Button("Save overlay", variant="primary")
            cfg_out = gr.Textbox(label="Saved overlay", lines=10)
            save_btn.click(save_config_fields, [rates, scenes, maxf, fscore, noise], cfg_out)

        with gr.Tab("Snapshots"):
            gr.Markdown("Standardized paper images — every cloud aligned to GT (ground on "
                        "floor), ceiling clipped, black & white backgrounds.")
            gr.Markdown(
                "**Co-visibility variants.** A 360° cloud looks more complete than a "
                "pinhole one because it *saw* more, not because it reconstructed better. "
                "The scored comparison masks every cloud down to the shared observed "
                "volume, so each render comes in three flavours: **full** (everything), "
                "**covis** (kept in colour + masked-away points in grey — the honest "
                "figure), **masked** (only what the F-score actually scored).")
            with gr.Row():
                keep_h = gr.Slider(0.0, 3.0, value=2.0, step=0.1, label="Keep height (m)")
                snap_maxp = gr.Slider(20000, 400000, value=150000, step=10000, label="Max points")
                snap_ptsize = gr.Slider(0.5, 15.0, value=5.0, step=0.5, label="Point size")
            with gr.Row():
                snap_masks = gr.CheckboxGroup(
                    ["full", "covis", "masked"], value=["full", "covis", "masked"],
                    label="Mask variants to render")
                drop_alpha = gr.Slider(0.02, 1.0, value=0.18, step=0.02,
                                       label="Masked-away opacity (covis)")
                drop_grey = gr.Slider(0.0, 1.0, value=0.55, step=0.05,
                                      label="Masked-away grey level (covis)")
            snap_btn = gr.Button("Generate snapshots (all methods × scenes × rates)", variant="primary")
            gr.Markdown("**Filter (multi-select; empty = all) + paginate:**")
            with gr.Row():
                f_scene = gr.Dropdown(_snap_scene_choices(), value=[], multiselect=True, label="Scenes")
                f_method = gr.Dropdown(_snap_method_choices(), value=[], multiselect=True, label="Methods")
            with gr.Row():
                f_view = gr.Dropdown(["oblique", "top"], value=["oblique"], multiselect=True, label="Views")
                f_bg = gr.Dropdown(["black", "white"], value=["white"], multiselect=True, label="Backgrounds")
                f_mask = gr.Dropdown(["full", "covis", "masked"], value=["covis"],
                                     multiselect=True, label="Mask variant")
                f_traj = gr.Dropdown(_snap_traj_choices(), value=[], multiselect=True,
                                     label="Trajectory")
                f_page = gr.Number(value=1, precision=0, label="Page")
                show_btn = gr.Button("Show / next page", variant="primary")
            snap_status = gr.Markdown("")
            gallery = gr.Gallery(label="Snapshots", columns=4, height=560)
            with gr.Row():
                dl_btn = gr.Button("Zip filtered for download")
                snap_zip = gr.File(label="Download", interactive=False)

            def _gen(kh, mp, ps, masks, dalpha, dgrey):
                from eval import snapshots
                mv = [m for m in (masks or snapshots.MASK_VARIANTS)]
                snapshots.generate(load_config("config.yaml"), keep_h=float(kh),
                                   max_points=int(mp), point_size=float(ps),
                                   mask_variants=mv, dropped_alpha=float(dalpha),
                                   dropped_grey=float(dgrey))
                first = "covis" if "covis" in mv else mv[0]
                imgs, status = snap_page([], [], ["oblique"], ["white"], [first], [], 1)
                return (imgs, status, gr.update(choices=_snap_scene_choices()),
                        gr.update(choices=_snap_method_choices()),
                        gr.update(choices=_snap_traj_choices()))

            snap_btn.click(_gen, [keep_h, snap_maxp, snap_ptsize, snap_masks,
                                  drop_alpha, drop_grey],
                           [gallery, snap_status, f_scene, f_method, f_traj])
            show_btn.click(snap_page,
                           [f_scene, f_method, f_view, f_bg, f_mask, f_traj, f_page],
                           [gallery, snap_status])
            dl_btn.click(zip_filtered,
                         [f_scene, f_method, f_view, f_bg, f_mask, f_traj], snap_zip)
            demo.load(lambda: snap_page([], [], ["oblique"], ["white"], ["covis"], [], 1),
                      None, [gallery, snap_status])

        with gr.Tab("Point cloud"):
            clouds = list_clouds()
            with gr.Row():
                cdd = gr.Dropdown(choices=clouds, value=(clouds[0] if clouds else None), label="Cloud")
                cmax = gr.Slider(5000, 300000, value=80000, step=5000, label="Max points")
                cov = gr.Checkbox(value=False, label="Overlay GT (aligned)")
            cplot = gr.Plot(label="3D view (drag to orbit)")
            for ev in (cdd.change, cmax.change, cov.change):
                ev(show_cloud, [cdd, cmax, cov], cplot)
            gr.Button("Refresh clouds").click(lambda: gr.update(choices=list_clouds()), None, cdd)
            demo.load(show_cloud, [cdd, cmax, cov], cplot)

        with gr.Tab("Frame preview"):
            runs = list_runs()
            with gr.Row():
                run = gr.Dropdown(choices=runs, value=(runs[0] if runs else None), label="Run")
                n0f = max(len(_frame_names(runs[0])) - 1, 1) if runs else 1
                idx = gr.Slider(0, n0f, value=0, step=1, label="Frame index")
            info = gr.Textbox(label="Info", interactive=False)
            with gr.Row():
                im_rgb = gr.Image(label="RGB"); im_d = gr.Image(label="Depth"); im_m = gr.Image(label="Mask")

            def on_run(r):
                n = max(len(_frame_names(r)) - 1, 1)
                a, b, c, t = preview_frame(r, 0)
                return gr.update(maximum=n, value=0), a, b, c, t
            run.change(on_run, [run], [idx, im_rgb, im_d, im_m, info])
            idx.change(preview_frame, [run, idx], [im_rgb, im_d, im_m, info])
            demo.load(on_run, [run], [idx, im_rgb, im_d, im_m, info])

        with gr.Tab("Report figures"):
            gr.Markdown(
                "Regenerate the two report figures on demand and download them "
                "(**vram_vs_frames.png** + **vram_scaling.csv**, **cubemap_projection.png**). "
                "They land in `results/figures/`.\n\n"
                "* **VRAM — perf.csv**: reproducible from the committed seeded run, on real "
                "benchmark scenes (no GPU). "
                "* **VRAM — sweep**: on-GPU prefix sweep — pick the frame grid (e.g. "
                "`1,2,4,…,256`); each method's curve stops at its real OOM cap (needs exports "
                "+ method envs). "
                "* **Cubemap — from dataset**: REAL intermediates from a rendered pano frame "
                "(equirect RGB + GT depth + validity mask, fixed geometric reprojection; needs "
                "`render`+`export`, no GPU). "
                "* **Cubemap — engine**: the engine's own reprojection (needs the PRISM-VGGT env). "
                "* **Cubemap — schematic**: labelled preview (no data). "
                "* **Fusion — from dataset**: per-view vs fused panels, same backbone/frames "
                "(back-projected GT depth: concat vs voxel-fused; needs `render`+`export`). "
                "* **Fusion — from results**: real panovggt (per-view) vs prism (fused) clouds.")
            with gr.Row():
                fig_scene = gr.Textbox(value="auto", label="Scene ('auto' = best-covered)", scale=2)
                fig_traj = gr.Textbox(value="synthetic_2.0hz_s0", label="Traj (sweep/cubemap)", scale=2)
                fig_ftraj = gr.Textbox(value="synthetic_5.0hz_s0", label="Fusion traj (dense)", scale=2)
            with gr.Row():
                fig_frames = gr.Textbox(value="1,2,4,8,16,32,64,128,256",
                                        label="Sweep frame grid (comma-separated)", scale=3)
                fig_tile = gr.Checkbox(value=False, label="Tile past render length (for large counts)")
            with gr.Row():
                b_vram = gr.Button("VRAM — from perf.csv", variant="primary")
                b_vram_sweep = gr.Button("VRAM — on-GPU sweep", variant="primary")
            with gr.Row():
                b_cube_data = gr.Button("Cubemap — from dataset (real)", variant="primary")
                b_cube_eng = gr.Button("Cubemap — engine")
                b_cube = gr.Button("Cubemap — schematic")
            with gr.Row():
                b_fuse_data = gr.Button("Fusion — from dataset (real)", variant="primary")
                b_fuse_res = gr.Button("Fusion — from result clouds")
            fig_log = gr.Textbox(label="Output", lines=12, autoscroll=True)
            fig_gallery = gr.Gallery(label="Figures", columns=2, height=420)
            fig_files = gr.Files(label="Download artifacts", interactive=False)
            b_vram.click(gen_vram_perfcsv, [fig_scene],
                         [fig_log, fig_gallery, fig_files])
            b_vram_sweep.click(gen_vram_sweep, [fig_scene, fig_frames, fig_traj, fig_tile],
                               [fig_log, fig_gallery, fig_files])
            b_cube_data.click(gen_cubemap_dataset, [fig_scene, fig_traj],
                              [fig_log, fig_gallery, fig_files])
            b_cube_eng.click(gen_cubemap_engine, [fig_scene, fig_traj],
                             [fig_log, fig_gallery, fig_files])
            b_cube.click(gen_cubemap_schematic, [fig_scene, fig_traj],
                         [fig_log, fig_gallery, fig_files])
            b_fuse_data.click(gen_fusion_dataset, [fig_scene, fig_ftraj],
                              [fig_log, fig_gallery, fig_files])
            b_fuse_res.click(gen_fusion_results, [fig_scene, fig_ftraj],
                             [fig_log, fig_gallery, fig_files])
            demo.load(lambda: (_fig_gallery(), _fig_files()), None, [fig_gallery, fig_files])

        with gr.Tab("✅ Clean results & smoke test"):
            gr.Markdown(
                "### Before the long run\n"
                "`make report` aggregates **everything** in `results/` — seeded and "
                "unseeded, complete and crashed alike. That is what contaminated the "
                "2026-07 tables. Everything on this tab uses the **seeded-only, "
                "complete-runs-only** path instead.\n\n"
                "Run the **smoke test** first: it drives every stage and every method "
                "over a tiny matrix, validates the artifacts, and projects how many "
                "hours the real run will take — so a broken env costs you 20 minutes "
                "instead of a wasted night.")
            with gr.Row():
                sm_traj = gr.Textbox(value="all", label="SMOKE_TRAJ "
                                     "(e.g. synthetic_2.0hz_s0 for a ~5 min check)", scale=2)
                sm_methods = gr.Textbox(value="", label="SMOKE_METHODS (blank = all)", scale=2)
            sm_btn = gr.Button("🔥  Run SMOKE TEST", variant="primary")
            sm_out = gr.Textbox(label="Live output", lines=20, autoscroll=True)
            sm_log = gr.File(label="Download smoke log", interactive=False)
            sm_btn.click(run_smoke, [sm_traj, sm_methods], [sm_out, sm_log])

            gr.Markdown("---\n### Clean aggregation")
            with gr.Row():
                cl_src = gr.Dropdown(["auto", "live", "archive"], value="auto",
                                     label="SOURCE (live = results/, archive = committed snapshot)")
                cl_btn = gr.Button("Run report-clean + report-tables + verify-clean",
                                   variant="primary")
            cl_out = gr.Textbox(label="Live output", lines=14, autoscroll=True)
            cl_log = gr.File(label="Download log", interactive=False)

            def _run_clean(src):
                yield from run_targets(["report-clean", "report-tables", "verify-clean"],
                                       "", "all")
            cl_btn.click(_run_clean, [cl_src], [cl_out, cl_log])

            gr.Markdown("---\n### Completion / failure rate — **read this before any mean**\n"
                        "A method missing runs here is not comparable to one that "
                        "finished all of them.")
            comp_md = gr.Markdown()
            gr.Markdown("### Streaming comparison (with throughput)")
            stream_md = gr.Markdown()
            gr.Markdown("### Headline metrics with error bars")
            eb_md = gr.Markdown()
            gr.Markdown("### Paired head-to-head (what actually separates)")
            pair_md = gr.Markdown()
            refresh_btn = gr.Button("Refresh tables")
            clean_files = gr.Files(label="Download clean tables + report bundle",
                                   interactive=False)

            def _refresh():
                return (_csv_md("completion.csv"), _csv_md("streaming.csv"),
                        _csv_md("headline_errorbars.csv"),
                        _csv_md("paired_head_to_head.csv", max_rows=60),
                        clean_bundle_files())
            refresh_btn.click(_refresh, None,
                              [comp_md, stream_md, eb_md, pair_md, clean_files])
            demo.load(_refresh, None, [comp_md, stream_md, eb_md, pair_md, clean_files])

        with gr.Tab("📦 Download results"):
            gr.Markdown(
                "### Download the whole benchmark as one .zip\n"
                "Tables, per-run metrics, trajectories, snapshots, figures, logs and "
                "config — everything needed to read, re-plot or archive the run.\n\n"
                "**Point clouds are off by default.** They dominate `results/` "
                "(6–103 MB each in the 2026-07 run), so including them on a full matrix "
                "means tens of gigabytes. Hit *Estimate size* to see the real number "
                "for this run before deciding.")
            from eval import bundle_results as _br
            b_cats = gr.CheckboxGroup(
                list(_br.CATEGORIES), value=list(_br.DEFAULT_ON),
                label="What to include")
            with gr.Row():
                b_compress = gr.Checkbox(
                    value=True, label="Compress (off = faster, bigger)")
                b_est_btn = gr.Button("Estimate size")
                b_go = gr.Button("📦  Build & download .zip", variant="primary")
            b_table = gr.Markdown()
            b_status = gr.Markdown()
            b_file = gr.File(label="Your bundle", interactive=False)
            gr.Markdown("**Previously built bundles** (they live on the benchmark box "
                        "under `results/bundles/`):")
            b_prev = gr.Files(label="Earlier bundles", interactive=False)

            b_est_btn.click(bundle_estimate_md, [b_cats], b_table)
            b_cats.change(bundle_estimate_md, [b_cats], b_table)
            b_go.click(bundle_build, [b_cats, b_compress], [b_status, b_file]) \
                .then(lambda: existing_bundles(), None, b_prev)
            demo.load(lambda: (bundle_estimate_md(list(_br.DEFAULT_ON)),
                               existing_bundles()), None, [b_table, b_prev])

            gr.Markdown("---\n### Browse the server filesystem\n"
                        "For anything the bundle doesn't cover.")
            explorer = gr.FileExplorer(root_dir=str(REPO_ROOT), ignore_glob=".*",
                                       file_count="single", label="Server filesystem")
            dl = gr.File(label="Download ready", interactive=False)
            gr.Button("Prepare download").click(prepare_download, explorer, dl)
    return demo


def launch():
    # allowed_paths so gr.File can serve zips/logs from tmp + the repo (downloads).
    build_app().launch(server_name="0.0.0.0", server_port=7860, share=True,
                       allowed_paths=[tempfile.gettempdir(), str(REPO_ROOT)])


if __name__ == "__main__":
    launch()

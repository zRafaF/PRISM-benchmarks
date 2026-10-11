#!/usr/bin/env python
"""Methodology figures for README.md (no method outputs: inputs, protocol, metric definitions).

Reads only the exported inputs (dataset/exports/...), the GT and, for the real-data
figure, the raw 360Loc image. Writes documentation/figures/*.png.   `make readme-figures`

  walks.png         every planned Replica walk over the scene's obstacles (top view)
  motion.png        step length / turning rate / heading lag pooled over all walks
  cameras.png       one panorama with the pinhole and cube-face footprints + the faces
  pinhole.png       the pinhole view of the same timestep
  real360.png       360Loc import: raw frame, heading-aligned + masked frame, mask, GT walk
  lost_metrics.png  the continuity metrics on two SYNTHETIC estimates of a real walk
  covis.png         what the co-visibility mask keeps of the GT surface
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.colors import LinearSegmentedColormap
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts"))
from bench.config import load_config          # noqa: E402
import lost_metrics as lm                      # noqa: E402

OUT = ROOT / "documentation" / "figures"
EXP = ROOT / "dataset" / "exports"
C1, C2, C3 = "#2a78d6", "#eb6834", "#1baf7a"
INK, INK2, GRID, MESH = "#0b0b0b", "#52514e", "#d9d8d4", "#9b9a96"
plt.rcParams.update({"font.size": 10, "axes.edgecolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
                     "axes.spines.top": False, "axes.spines.right": False,
                     "savefig.facecolor": "white", "figure.facecolor": "white"})


def load_tum(p):
    return {k: T for k, T in lm.load_tum(p).items()}


def poses(p):
    t = load_tum(p)
    return np.stack([t[k] for k in sorted(t)])


def ply_points(p, n=150_000, seed=0):
    """Uniform random vertices of a binary little-endian PLY (memmap; no open3d)."""
    tm = {"float": "<f4", "float32": "<f4", "double": "<f8", "float64": "<f8", "uchar": "u1",
          "uint8": "u1", "int": "<i4", "int32": "<i4", "uint": "<u4", "uint32": "<u4"}
    props, nv, inv = [], 0, False
    with open(p, "rb") as f:
        while True:
            ln = f.readline().decode("ascii", "ignore").strip()
            if ln.startswith("element"):
                inv = ln.startswith("element vertex")
                if inv:
                    nv = int(ln.split()[-1])
            elif ln.startswith("property") and inv:
                _, t, name = ln.split()[:3]
                props.append((name, tm[t]))
            elif ln == "end_header":
                break
        off = f.tell()
    mm = np.memmap(p, dtype=np.dtype(props), mode="r", offset=off, shape=(nv,))
    idx = np.sort(np.random.default_rng(seed).choice(nv, min(n, nv), replace=False))
    a = mm[idx]
    return np.stack([a["x"], a["y"], a["z"]], 1).astype(np.float64)


def clean(ax):
    ax.set_xticks([]); ax.set_yticks([]); ax.set_aspect("equal")
    for s in ax.spines.values():
        s.set_visible(False)


def fig_walks(cfg):
    scenes = cfg["datasets"]["replica"]["scenes"]
    fig, axs = plt.subplots(3, len(scenes), figsize=(3 * len(scenes), 9.2), squeeze=False)
    for j, sc in enumerate(scenes):
        mesh = ply_points(EXP / "replica" / sc / "synthetic_2.0hz_s0" / "gt_mesh.ply")
        for i in range(3):
            d = EXP / "replica" / sc / f"synthetic_2.0hz_s{i}"
            ax = axs[i, j]
            if not (d / "poses_gt.tum").exists():
                ax.axis("off"); continue
            P = poses(d / "poses_gt.tum")[:, :3, 3]
            zc = P[0, 2]
            ob = mesh[(mesh[:, 2] > zc - 1.5) & (mesh[:, 2] < zc + 0.1)]
            ax.scatter(ob[:, 0], ob[:, 1], s=0.15, c=MESH, rasterized=True)
            ax.plot(P[:, 0], P[:, 1], color=C1, lw=1.3)
            ax.plot(*P[0, :2], "o", ms=6, color=C3, mec="white", mew=1.2)
            ax.plot(*P[-1, :2], "s", ms=5, color=C2, mec="white", mew=1)
            L = np.linalg.norm(np.diff(P, axis=0), axis=1).sum()
            ax.set_title(f"{sc}  seed {i}\n{len(P)} frames, {L:.1f} m", fontsize=9)
            clean(ax)
    fig.legend(handles=[Line2D([], [], color=MESH, marker="s", ls="", ms=4,
                               label="mesh between 0.2 m above the floor and camera height (obstacles)"),
                        Line2D([], [], color=C1, lw=1.5, label="camera path"),
                        Line2D([], [], color=C3, marker="o", ls="", label="start"),
                        Line2D([], [], color=C2, marker="s", ls="", label="end")],
               loc="lower center", ncol=4, frameon=False)
    fig.tight_layout(rect=(0, 0.04, 1, 1)); fig.savefig(OUT / "walks.png", dpi=90); plt.close(fig)


def fig_motion(cfg):
    steps, rate, lag, n = [], [], [], 0
    for sc in cfg["datasets"]["replica"]["scenes"]:
        for i in range(3):
            p = EXP / "replica" / sc / f"synthetic_2.0hz_s{i}" / "poses_gt.tum"
            if not p.exists():
                continue
            T = poses(p); n += len(T)
            d = np.diff(T[:, :3, 3], axis=0)
            steps += list(np.linalg.norm(d, axis=1))
            fwd = T[:, :3, 2]
            h = np.unwrap(np.arctan2(fwd[:, 1], fwd[:, 0]))
            rate += list(np.degrees(np.abs(np.diff(h))) * 2.0)            # 2 Hz
            th = np.arctan2(d[:, 1], d[:, 0])
            lag += list(np.degrees(np.abs((h[:-1] - th + np.pi) % (2 * np.pi) - np.pi)))
    cap = cfg["trajectories"]["synthetic_spline"]["max_yaw_rate_dps"]
    fig, axs = plt.subplots(1, 3, figsize=(13, 3.4))
    axs[0].hist(np.array(steps) * 100, bins=40, color=C1, edgecolor="white", linewidth=0.5)
    axs[0].set_xlabel("distance between consecutive frames (cm)")
    axs[0].set_title("Straight-line step (25 cm along the path;\nshorter where the path turns)")
    axs[1].hist(rate, bins=45, color=C1, edgecolor="white", linewidth=0.5)
    axs[1].axvline(cap, color=C2, lw=1.5)
    axs[1].text(cap + 1, axs[1].get_ylim()[1] * 0.85, f"cap {cap:.0f}°/s", color=INK2)
    axs[1].set_xlabel("heading change rate (deg/s)"); axs[1].set_title("Turning rate (rate-limited yaw)")
    axs[2].hist(lag, bins=36, range=(0, 180), color=C1, edgecolor="white", linewidth=0.5)
    axs[2].set_xlabel("camera forward vs travel direction (deg)")
    axs[2].set_title("Heading lag (camera level, pitch = roll = 0)")
    for a in axs:
        a.set_ylabel("frames"); a.grid(axis="y", color=GRID, lw=0.6); a.set_axisbelow(True)
    fig.suptitle(f"All Replica walks pooled ({n} frames)", fontsize=11)
    fig.tight_layout(); fig.savefig(OUT / "motion.png", dpi=90); plt.close(fig)


def _footprint(W, H, hfov, vfov, yaw_deg, n=60):
    tx, ty = np.tan(np.radians(hfov / 2)), np.tan(np.radians(vfov / 2))
    e = np.linspace(-1, 1, n)
    pts = np.concatenate([np.c_[e, -np.ones(n)], np.c_[np.ones(n), e],
                          np.c_[e[::-1], np.ones(n)], np.c_[-np.ones(n), e[::-1]]])
    d = np.c_[pts[:, 0] * tx, pts[:, 1] * ty, np.ones(len(pts))]
    d /= np.linalg.norm(d, axis=1, keepdims=True)
    a = np.radians(yaw_deg)
    Ry = np.array([[np.cos(a), 0, np.sin(a)], [0, 1, 0], [-np.sin(a), 0, np.cos(a)]])
    d = d @ Ry.T                                   # face k: k x yaw to the right about y
    lon, lat = np.arctan2(d[:, 0], d[:, 2]), np.arcsin(-d[:, 1])   # bench/cameras.py convention
    return W / 2 + lon / (2 * np.pi) * W, H / 2 - lat / np.pi * H


def _draw_wrapped(ax, u, v, W, **kw):
    br = np.flatnonzero(np.abs(np.diff(u)) > W / 2) + 1
    for k, (su, sv) in enumerate(zip(np.split(u, br), np.split(v, br))):
        ax.plot(su, sv, **(kw if k == 0 else {x: y for x, y in kw.items() if x != "label"}))


def _lon_axis(ax, W):
    ax.set_xticks([0, W / 4, W / 2, 3 * W / 4, W])
    ax.set_xticklabels(["−180°", "−90°", "0° (forward)", "+90°", "180°"]); ax.set_yticks([])


def fig_cameras(cfg, scene="apartment_1", traj="synthetic_2.0hz_s0", t=60):
    E = EXP / "replica" / scene / traj
    pano = np.array(Image.open(E / "pano" / "rgb" / f"{t:06d}.png")); H, W = pano.shape[:2]
    pin = json.loads((E / "pinhole" / "synthetic_fov" / "intrinsics.json").read_text())
    ph = 2 * np.degrees(np.arctan(pin["width"] / 2 / pin["fx"]))
    pv = 2 * np.degrees(np.arctan(pin["height"] / 2 / pin["fy"]))
    cube = {}
    for v in ("cube4", "cube4_o20"):
        fj = json.loads((E / "pinhole" / v / "faces.json").read_text())
        cube[v] = fj.get("fov_deg", 360.0 / fj["n_faces"] + fj.get("face_overlap_deg", 0.0))
    fig = plt.figure(figsize=(14, 11.5))
    gs = fig.add_gridspec(4, 4, height_ratios=[1.35, 1.35, 1, 1], hspace=0.35, wspace=0.06)
    rows = [("Panorama (PRISM, PanoVGGT) with the pinhole footprint",
             [(ph, pv, 0, C2, f"pinhole {ph:.0f}° × {pv:.0f}° (VGGT-SLAM, LASER, Pi3)")]),
            ("Same panorama with the cube-face footprints",
             [(cube["cube4"], cube["cube4"], k * 90, C1, f"cube4: 4 × {cube['cube4']:.0f}°" if k == 0 else None) for k in range(4)]
             + [(cube["cube4_o20"], cube["cube4_o20"], k * 90, C3, f"cube4_o20: 4 × {cube['cube4_o20']:.0f}°" if k == 0 else None) for k in range(4)])]
    for r, (title, specs) in enumerate(rows):
        ax = fig.add_subplot(gs[r, :]); ax.imshow(pano); _lon_axis(ax, W)
        for hf, vf, yw, c, lab in specs:
            u, v = _footprint(W, H, hf, vf, yw)
            _draw_wrapped(ax, u, v, W, color=c, lw=2, label=lab)
        ax.set_title(title, loc="left"); ax.legend(loc="lower left", fontsize=9, framealpha=0.9)
        ax.set_xlim(0, W); ax.set_ylim(H, 0)
    names = ["front", "right", "back", "left"]
    for r, var in [(2, "cube4"), (3, "cube4_o20")]:
        for k in range(4):
            ax = fig.add_subplot(gs[r, k])
            ax.imshow(Image.open(E / "pinhole" / var / "rgb" / f"{4 * t + k:06d}.png")); ax.set_xticks([]); ax.set_yticks([])
            ax.set_title(f"{var} · {names[k]} (image {4 * t + k} = 4·{t}+{k})", fontsize=9)
    fig.savefig(OUT / "cameras.png", dpi=80, bbox_inches="tight"); plt.close(fig)
    fig, ax = plt.subplots(figsize=(5, 3.9))
    ax.imshow(Image.open(E / "pinhole" / "synthetic_fov" / "rgb" / f"{t:06d}.png")); ax.set_xticks([]); ax.set_yticks([])
    ax.set_title(f"synthetic_fov: {pin['width']}×{pin['height']}, {ph:.0f}° horizontal", fontsize=9)
    fig.savefig(OUT / "pinhole.png", dpi=80, bbox_inches="tight"); plt.close(fig)


def fig_real(t=100):
    E = EXP / "loc360" / "atrium" / "ref"
    src = json.loads((E / "source.json").read_text())
    rcfg = __import__("yaml").safe_load((ROOT / "config.real360.yaml").read_text())
    raw_p = ROOT / rcfg["datasets"]["loc360"]["root"] / "atrium" / src["sequence"] / "image" / src["images"][t]
    fig = plt.figure(figsize=(14, 8.6))
    gs = fig.add_gridspec(2, 3, width_ratios=[1, 1, 0.62], hspace=0.25, wspace=0.16)
    if raw_p.exists():
        ax = fig.add_subplot(gs[0, 0]); ax.imshow(Image.open(raw_p).resize((1036, 518))); _lon_axis(ax, 1036)
        ax.set_title("360Loc image as recorded (image centre = operator's grip,\nnot the walking direction; operator visible)", loc="left", fontsize=9.5)
    ax = fig.add_subplot(gs[0, 1]); ax.imshow(Image.open(E / "pano" / "rgb" / f"{t:06d}.png")); _lon_axis(ax, 1036)
    ax.set_title("After import: rotated so 0° = smoothed direction of travel,\nfixed operator region blacked out (same pixels for every method)", loc="left", fontsize=9.5)
    ax = fig.add_subplot(gs[0, 2]); ax.imshow(Image.open(E / "pinhole" / "synthetic_fov" / "rgb" / f"{t:06d}.png")); ax.set_xticks([]); ax.set_yticks([])
    ax.set_title("Pinhole view resampled from\nthe same panorama (90°, forward)", loc="left", fontsize=9.5)
    om = src.get("operator_mask", {})
    ax = fig.add_subplot(gs[1, 0]); ax.imshow(np.array(Image.open(E / "pano" / "mask" / f"{t:06d}.png")), cmap="gray"); _lon_axis(ax, 1036)
    ax.set_title(f"Validity mask (white = used). Back ±{om.get('back_halfwidth_deg')}° below {om.get('top_lat_deg')}°, "
                 f"arms ±{om.get('arms_halfwidth_deg')}°\nbelow {om.get('arms_top_lat_deg')}°, everything below {om.get('nadir_lat_deg')}° latitude",
                 loc="left", fontsize=9.5)
    G = poses(E / "poses_gt.tum")[:, :3, 3]
    gz = ply_points(E / "gt_cloud.ply", 200_000)
    v = int(np.argmin(np.ptp(G, 0))); h = [i for i in range(3) if i != v]
    ax = fig.add_subplot(gs[1, 1:]); sl = gz[np.abs(gz[:, v] - np.median(G[:, v])) < 1.0]
    ax.scatter(sl[:, h[0]], sl[:, h[1]], s=0.2, c=MESH, rasterized=True)
    L = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(G, axis=0), axis=1))])
    cm = LinearSegmentedColormap.from_list("b", ["#bcd6f5", C1, "#0b3a75"])
    sc = ax.scatter(G[:, h[0]], G[:, h[1]], c=L, cmap=cm, s=5)
    ax.plot(*G[0, h], "o", color=C3, ms=7, mec="white"); clean(ax)
    fig.colorbar(sc, ax=ax, shrink=0.7).set_label("distance along the walk (m)")
    ax.set_title(f"atrium, {src['sequence']}: {len(G)} frames, {L[-1]:.0f} m, median step {100 * np.median(np.diff(L)):.0f} cm;\n"
                 "lidar GT poses over the GT map (fused from the dataset's 360 depth maps), ±1 m slice", loc="left", fontsize=9.5)
    fig.savefig(OUT / "real360.png", dpi=80, bbox_inches="tight"); plt.close(fig)


def fig_lost(scene="room_0", traj="synthetic_2.0hz_s0"):
    G = poses(EXP / "replica" / scene / traj / "poses_gt.tum"); pg = G[:, :3, 3]
    cum = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(pg, axis=0), axis=1))])
    rng = np.random.default_rng(0)
    Rz = lambda a: np.array([[np.cos(a), -np.sin(a), 0], [np.sin(a), np.cos(a), 0], [0, 0, 1]])
    # A: smooth drift — each step rotated / scaled by the drift accumulated so far
    Ed = G.copy(); P = [pg[0]]
    for i, d in enumerate(np.diff(pg, axis=0)):
        P.append(P[-1] + (1 + 0.004 * cum[i]) * Rz(np.radians(0.6) * cum[i]) @ d)
    Ed[:, :3, 3] = np.array(P) + rng.normal(0, 0.005, pg.shape)
    for i in range(len(G)):
        Ed[i, :3, :3] = Rz(np.radians(0.6) * cum[i]) @ G[i, :3, :3]
    # B: exact except a tear (jump + turn) at 40 % of the path
    Et = G.copy(); k = int(np.searchsorted(cum, 0.4 * cum[-1])); Rt = Rz(np.radians(15))
    Et[:, :3, 3] = pg + rng.normal(0, 0.005, pg.shape)
    Et[k:, :3, 3] = (Rt @ (pg[k:] - pg[k]).T).T + pg[k] + np.array([0.6, -0.3, 0]) + rng.normal(0, 0.005, (len(G) - k, 3))
    for i in range(k, len(G)):
        Et[i, :3, :3] = Rt @ G[i, :3, :3]
    fig, axs = plt.subplots(2, 3, figsize=(15, 8.2), gridspec_kw=dict(width_ratios=[1, 1.25, 1.25]))
    for r, (E, name) in enumerate([(Ed, "A. smooth drift (0.6°/m heading, 0.4 %/m scale)"),
                                   (Et, f"B. tear at {cum[k]:.0f} m (0.67 m jump, 15° turn), otherwise exact")]):
        a = lm.analyse(E, G)
        ax = axs[r, 0]; s, R, t = lm.umeyama(E[:, :3, 3], pg); Pa = s * (R @ E[:, :3, 3].T).T + t
        ax.plot(pg[:, 0], pg[:, 1], color=MESH, lw=2.5, label="GT"); ax.plot(Pa[:, 0], Pa[:, 1], color=C1, lw=1.2, label="estimate (global Sim(3))")
        clean(ax); ax.legend(fontsize=8, loc="lower right"); ax.set_title(name, loc="left", fontsize=9.5)
        W = []
        for s0 in np.arange(0.0, cum[-1] - lm.WIN_M + 1e-9, lm.STEP_M):
            i0 = int(np.searchsorted(cum, s0)); i1 = int(np.searchsorted(cum, s0 + lm.WIN_M)) + 1
            W.append((s0, *lm.seg_err(E, G, i0, i1)))
        W = np.array(W); ok = (W[:, 1] < lm.TAU_LOC_M) & (W[:, 2] < lm.TAU_ROT_DEG)
        ax = axs[r, 1]; ax.plot(W[:, 0] + lm.WIN_M / 2, np.maximum(W[:, 1], 1e-3) * 100, color=C1, lw=1.5)
        ax.axhline(lm.TAU_LOC_M * 100, color=C2, lw=1.2, ls="--"); ax.text(0.3, lm.TAU_LOC_M * 115, f"{lm.TAU_LOC_M * 100:.0f} cm", color=C2, fontsize=8.5)
        for (s0, *_), o in zip(W, ok):
            if not o:
                ax.axvspan(s0 + lm.WIN_M / 2 - lm.STEP_M / 2, s0 + lm.WIN_M / 2 + lm.STEP_M / 2, color=C2, alpha=0.18, lw=0)
        ax.set_yscale("log"); ax.set_ylim(0.1, 200); ax.set_xlabel("window centre along the path (m)")
        ax.set_ylabel(f"{lm.WIN_M:.0f} m window RMSE (cm), own Sim(3)")
        ax.set_title(f"Local continuity → tracked {a['tracked_pct']:.0f} %, loss events {a['n_lost']}", loc="left", fontsize=9.5)
        i2 = max(4, int(np.searchsorted(cum, lm.ANCHOR_M)) + 1); s, R, t = lm.umeyama(E[:i2, :3, 3], pg[:i2])
        e = np.linalg.norm(pg - (s * (R @ E[:, :3, 3].T).T + t), axis=1)
        ax = axs[r, 2]; ax.plot(cum, e * 100, color=C1, lw=1.5)
        ax.axhline(lm.TAU_FAIL_M * 100, color=C2, lw=1.2, ls="--"); ax.text(0.3, lm.TAU_FAIL_M * 115, f"{lm.TAU_FAIL_M * 100:.0f} cm", color=C2, fontsize=8.5)
        ax.axvspan(0, lm.ANCHOR_M, color=C3, alpha=0.15, lw=0); ax.text(0.15, 0.13, f"aligned on\nfirst {lm.ANCHOR_M:.0f} m", fontsize=8, color=INK2)
        ax.axvline(a["survive_m"], color=INK, lw=1); ax.text(a["survive_m"], 120, f" survive_m = {a['survive_m']:.1f}", fontsize=8.5)
        ax.set_yscale("log"); ax.set_ylim(0.1, 300); ax.set_xlabel("distance along the path (m)"); ax.set_ylabel("error (cm)")
        ax.set_title(f"Distance to failure; greedy segments at {lm.TAU_SEG_M * 100:.0f} cm: {a['segments']}", loc="left", fontsize=9.5)
        for x in axs[r, 1:]:
            x.grid(color=GRID, lw=0.5); x.set_axisbelow(True)
    fig.suptitle(f"Synthetic illustration of the continuity metrics on a real benchmark walk ({scene}, seed 0) — not a method's output", fontsize=11)
    fig.tight_layout(); fig.savefig(OUT / "lost_metrics.png", dpi=85); plt.close(fig)


def fig_covis(cfg, scene="room_0", traj="synthetic_2.0hz_s0"):
    from eval.visibility_mask import build_mask
    d = EXP / "replica" / scene / traj
    X = ply_points(d / "gt_mesh.ply", 150_000)
    keep = build_mask(X, d / "pinhole" / "synthetic_fov", cfg)
    P = poses(d / "poses_gt.tum")[:, :3, 3]; sel = X[:, 2] < P[0, 2] + 0.6
    fig, axs = plt.subplots(1, 2, figsize=(13, 4.6))
    far = cfg["eval"]["mask"]["frustum_far_m"]
    for ax, (title, m, c) in zip(axs, [("GT mesh points kept by the co-visibility mask", keep, C1),
                                       (f"points removed (never seen unoccluded by any pinhole frame within {far} m)", ~keep, C2)]):
        ax.scatter(X[sel & ~m, 0], X[sel & ~m, 1], s=0.3, c=GRID, rasterized=True)
        ax.scatter(X[sel & m, 0], X[sel & m, 1], s=0.3, c=c, rasterized=True)
        ax.plot(P[:, 0], P[:, 1], color=INK, lw=0.8); clean(ax); ax.set_title(title, loc="left", fontsize=9.5)
    fig.suptitle(f"{scene}, seed 0 (ceiling hidden): {100 * keep.mean():.0f} % of the GT surface samples are kept; "
                 "the same mask is applied to every method's cloud and to the GT", fontsize=10.5)
    fig.tight_layout(); fig.savefig(OUT / "covis.png", dpi=85); plt.close(fig)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    cfg = load_config("config.yaml")
    for name, fn in [("walks", lambda: fig_walks(cfg)), ("motion", lambda: fig_motion(cfg)),
                     ("cameras", lambda: fig_cameras(cfg)), ("real360", fig_real),
                     ("lost_metrics", fig_lost), ("covis", lambda: fig_covis(cfg))]:
        try:
            fn(); print(f"[readme_figures] {name}.png")
        except FileNotFoundError as e:
            print(f"[readme_figures] {name}: skipped (missing input: {e.filename})")


if __name__ == "__main__":
    main()

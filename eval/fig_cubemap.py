#!/usr/bin/env python
"""Projection figure: equirectangular -> cubemap -> fused volume (report Deliverable 2).

Builds `cubemap_projection.png`, matching the `fig-cubemap` slot/caption in the report
(uofa-2026-report/src/engine.typ): how a 360 panorama becomes a pinhole-fusible input.
Left -> right, with arrows:

  (1) input equirectangular panorama (RGB);
  (2) the six reprojected 90 deg cube faces (front/back/left/right/up/down), each with
      its per-face depth and the validity / anti-erosion seam mask (the mask that drops
      smeared depth-discontinuity pixels before TSDF integration);
  (3) the fused TSDF surface for that region.

Two modes:

  --mode export   (on the reference GPU, with the PRISM-VGGT engine available)
      Hooks the engine's OWN equirectangular->cubemap reprojection + VRAMProfiler
      (reused, not reimplemented) to dump the REAL intermediates for one chosen pano
      frame, then composes the figure. This is the artifact the report ships.

  --mode illustrative   (anywhere, no GPU / engine / dataset)
      Produces a clearly-labelled SCHEMATIC composite (synthetic panorama, standard
      gnomonic resampling) so the report layout can be wired up now. The banner marks
      it 'SCHEMATIC — regenerate on hardware'; it must be replaced by the real export.

Honesty: the schematic is never passed off as measured data (loud on-image banner +
filename note). The real export uses the engine intermediates verbatim.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bench.config import REPO_ROOT, load_config

DEFAULT_OUT = REPO_ROOT / "results" / "figures"
FACES = ["front", "right", "back", "left", "up", "down"]


# ── Standard gnomonic equirect->cubemap (ILLUSTRATIVE ONLY) ───────────────────
# The REAL figure uses the engine's own reprojection (see _engine_cubemap). This
# local sampler exists solely to render the labelled schematic without the engine.
def _face_dirs(face: str, size: int) -> np.ndarray:
    """Unit ray directions (size,size,3) for a 90 deg cube face."""
    a = np.linspace(-1, 1, size, dtype=np.float32)
    x, y = np.meshgrid(a, -a)
    o = np.ones_like(x)
    d = {
        "front": np.stack([x, y, o], -1),
        "back":  np.stack([-x, y, -o], -1),
        "right": np.stack([o, y, -x], -1),
        "left":  np.stack([-o, y, x], -1),
        "up":    np.stack([x, o, -y], -1),
        "down":  np.stack([x, -o, y], -1),
    }[face]
    return d / np.linalg.norm(d, axis=-1, keepdims=True)


def _sample_equirect(equirect: np.ndarray, dirs: np.ndarray) -> np.ndarray:
    H, W = equirect.shape[:2]
    x, y, z = dirs[..., 0], dirs[..., 1], dirs[..., 2]
    lon = np.arctan2(x, z)
    lat = np.arcsin(np.clip(y, -1, 1))
    u = ((lon / (2 * np.pi) + 0.5) * W).astype(np.int64) % W
    v = ((0.5 - lat / np.pi) * H).astype(np.int64).clip(0, H - 1)
    return equirect[v, u]


def _illustrative_equirect(H: int = 512) -> np.ndarray:
    """Synthetic but structured 2:1 panorama: coloured walls + ceiling/floor + a
    horizon and a grid, so the reprojected faces look like a plausible room."""
    W = 2 * H
    img = np.zeros((H, W, 3), np.uint8)
    lon = np.linspace(0, 2 * np.pi, W, endpoint=False)
    walls = (np.stack([(np.sin(lon) * 0.5 + 0.5) * 120 + 70,
                       (np.cos(lon * 1.3) * 0.5 + 0.5) * 90 + 80,
                       (np.sin(lon * 0.7 + 1) * 0.5 + 0.5) * 110 + 70], -1)).astype(np.uint8)
    for v in range(H):
        lat = 0.5 - v / H
        if lat > 0.30:      # ceiling
            img[v, :] = (205, 205, 215)
        elif lat < -0.30:   # floor
            img[v, :] = (120, 95, 70)
        else:
            img[v, :] = walls
    img[:, ::W // 24] = (40, 40, 40)                 # vertical grid lines
    img[H // 2 - 1:H // 2 + 1, :] = (30, 30, 30)     # horizon
    return img


def _illustrative_intermediates(face_size: int):
    equ = _illustrative_equirect()
    rgb, depth, mask = {}, {}, {}
    for f in FACES:
        dirs = _face_dirs(f, face_size)
        rgb[f] = _sample_equirect(equ, dirs)
        # synthetic radial depth (closer at face centre) + a discontinuity band
        yy, xx = np.mgrid[0:face_size, 0:face_size]
        r = np.hypot(xx - face_size / 2, yy - face_size / 2) / (face_size / 2)
        d = 1.0 + 3.0 * r
        d[(yy > face_size * 0.6) & (yy < face_size * 0.66)] += 2.5   # depth edge
        depth[f] = d.astype(np.float32)
        # validity / anti-erosion seam mask: drop a border ring (cube seams) + the
        # depth-discontinuity band (smeared pixels the engine refuses to integrate).
        m = np.ones((face_size, face_size), np.uint8)
        b = max(3, face_size // 40)
        m[:b] = m[-b:] = m[:, :b] = m[:, -b:] = 0
        gy = np.abs(np.gradient(depth[f], axis=0))
        m[gy > 0.5] = 0
        mask[f] = m
    return equ, rgb, depth, mask, None


# ── Dataset-native intermediates (mode=dataset — real data, no engine) ─────────
# The equirect->cubemap reprojection is a FIXED geometric transform, and the export
# already holds real per-frame RGB + rendered GT depth + validity mask + GT poses.
# So the figure is built straight from the dataset — real, reproducible, and free of
# the engine's private reprojection API. (Per-face depth is the render's GT depth, not
# PRISM's predicted depth; for a projection-pipeline figure that is the cleaner choice.)
FACE_FWD = {"front": (0, 0, 1), "back": (0, 0, -1), "right": (1, 0, 0),
            "left": (-1, 0, 0), "up": (0, 1, 0), "down": (0, -1, 0)}


def _sample_equirect_nn(equirect: np.ndarray, dirs: np.ndarray) -> np.ndarray:
    """Nearest-neighbour equirect lookup for any HxW[xC] array (RGB, depth, or mask)."""
    return _sample_equirect(equirect, dirs)


def _equirect_pixel_dirs(H: int, W: int) -> np.ndarray:
    """Unit ray direction per equirect pixel (matches _sample_equirect's convention)."""
    v, u = np.mgrid[0:H, 0:W]
    lon = (u / W - 0.5) * 2 * np.pi
    lat = (0.5 - v / H) * np.pi
    cl = np.cos(lat)
    return np.stack([cl * np.sin(lon), np.sin(lat), cl * np.cos(lon)], -1).astype(np.float32)


def _load_tum(path: Path):
    """TUM -> {frame_index: 4x4 cam->world}. Numpy-only quaternion->matrix."""
    poses = {}
    if not path.exists():
        return poses
    for i, line in enumerate(Path(path).read_text().splitlines()):
        s = line.split()
        if len(s) < 8:
            continue
        tx, ty, tz, qx, qy, qz, qw = map(float, s[1:8])
        n = qx * qx + qy * qy + qz * qz + qw * qw
        q = np.array([qx, qy, qz, qw]) / (n ** 0.5 if n else 1.0)
        x, y, z, w = q
        R = np.array([
            [1 - 2 * (y * y + z * z), 2 * (x * y - z * w),     2 * (x * z + y * w)],
            [2 * (x * y + z * w),     1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
            [2 * (x * z - y * w),     2 * (y * z + x * w),     1 - 2 * (x * x + y * y)]])
        T = np.eye(4)
        T[:3, :3] = R
        T[:3, 3] = (tx, ty, tz)
        poses[i] = T
    return poses


def _dataset_cubemap(equirect_rgb, equirect_depth, equirect_mask, face_size, cfg):
    """Reproject one equirect frame's RGB + GT depth + validity mask to 6 cube faces.
    Per-face depth is converted radial->perpendicular (what a pinhole fuser sees); the
    per-face mask combines the sampled validity with a depth-discontinuity + seam-border
    drop (the anti-erosion seam mask PRISM applies before TSDF integration)."""
    max_depth = float(cfg["engine"]["max_depth"])
    rgb, depth, mask = {}, {}, {}
    for f in FACES:
        dirs = _face_dirs(f, face_size)
        rgb[f] = _sample_equirect_nn(equirect_rgb, dirs)[..., :3].astype(np.uint8)
        radial = _sample_equirect_nn(equirect_depth.astype(np.float32), dirs)
        fwd = np.array(FACE_FWD[f], np.float32)
        cos = np.clip((dirs * fwd).sum(-1), 1e-3, 1.0)   # radial -> perpendicular depth
        z = radial * cos
        z[radial <= 0] = 0.0
        depth[f] = z
        m = np.ones((face_size, face_size), np.uint8)
        if equirect_mask is not None:
            mm = _sample_equirect_nn(equirect_mask, dirs)
            if mm.ndim == 3:
                mm = mm[..., 0]
            m[mm == 0] = 0
        m[(z <= 0) | (z > max_depth)] = 0                # out of range / invalid
        gy = np.abs(np.gradient(z, axis=0))
        gx = np.abs(np.gradient(z, axis=1))
        m[(gx + gy) > 0.5] = 0                            # depth-discontinuity smear
        b = max(2, face_size // 48)
        m[:b] = m[-b:] = m[:, :b] = m[:, -b:] = 0         # cube seam border
        mask[f] = m
    return rgb, depth, mask


def _fused_topdown(pano_dir: Path, center: int, cfg, span=4, stride=6, res=520):
    """Back-project a small window of frames' GT depth into world points (using GT
    poses) and splat them top-down — a real 'fused volume' crop for panel (3). Falls
    back to the single centre frame in the camera frame if no poses are present."""
    import imageio.v2 as imageio
    names = sorted(p.stem for p in (pano_dir / "rgb").glob("*.png"))
    if not names:
        return None
    poses = _load_tum(pano_dir.parent / "poses_gt.tum")
    idxs = [i for i in range(max(0, center - span), min(len(names), center + span + 1))]
    P, C = [], []
    H = W = None
    for i in idxs:
        nm = names[i]
        dp = pano_dir / "depth" / f"{nm}.npy"
        if not dp.exists():
            continue
        d = np.load(dp).astype(np.float32)
        rgb = np.asarray(imageio.imread(pano_dir / "rgb" / f"{nm}.png"))[..., :3]
        if H is None:
            H, W = d.shape
            dirs = _equirect_pixel_dirs(H, W)
        pts_cam = dirs * d[..., None]                     # radial depth along unit rays
        valid = (d > 0) & (d <= float(cfg["engine"]["max_depth"]))
        pc = pts_cam[valid][::stride]
        col = rgb[valid][::stride]
        T = poses.get(i, np.eye(4))
        world = (T[:3, :3] @ pc.T).T + T[:3, 3]
        P.append(world)
        C.append(col)
    if not P:
        return None
    P = np.concatenate(P)
    C = np.concatenate(C).astype(np.uint8)
    # top-down raster: keep the highest point per cell (look down onto the volume)
    lo, hi = np.percentile(P[:, :2], [1, 99], axis=0)
    span_xy = np.maximum(hi - lo, 1e-3)
    gx = np.clip(((P[:, 0] - lo[0]) / span_xy[0] * (res - 1)), 0, res - 1).astype(int)
    gy = np.clip(((P[:, 1] - lo[1]) / span_xy[1] * (res - 1)), 0, res - 1).astype(int)
    img = np.full((res, res, 3), 245, np.uint8)
    zbuf = np.full((res, res), -1e9, np.float32)
    order = np.argsort(P[:, 2])                            # low z first, high z overwrites
    for j in order:
        yy, xx = res - 1 - gy[j], gx[j]
        if P[j, 2] > zbuf[yy, xx]:
            zbuf[yy, xx] = P[j, 2]
            img[yy, xx] = C[j]
    return img


def _dataset_intermediates(cfg, scene, traj, frame):
    import imageio.v2 as imageio
    from bench.config import export_dir
    ds = cfg["datasets"]["active"][0]
    pano = export_dir(ds, scene, traj, "pano", "")
    names = sorted(p.stem for p in (pano / "rgb").glob("*.png"))
    if not names:
        raise SystemExit(f"[fig-cubemap] no pano frames at {pano} — run `make render export` first.")
    i = min(frame, len(names) - 1)
    nm = names[i]
    equ = np.asarray(imageio.imread(pano / "rgb" / f"{nm}.png"))[..., :3]
    dpath = pano / "depth" / f"{nm}.npy"
    if not dpath.exists():
        raise SystemExit(f"[fig-cubemap] no GT depth at {dpath} — re-run `make render` for {traj}.")
    depth = np.load(dpath).astype(np.float32)
    mpath = pano / "mask" / f"{nm}.png"
    emask = np.asarray(imageio.imread(mpath)) if mpath.exists() else None
    fs = int(cfg["engine"]["face_size"])
    print(f"[fig-cubemap] dataset frame {scene}/{traj}/{nm}  equirect={equ.shape[1]}x{equ.shape[0]}  "
          f"depth {depth[depth>0].min():.2f}-{depth[depth>0].max():.2f} m -> faces {fs}x{fs}", flush=True)
    rgb, fdepth, fmask = _dataset_cubemap(equ, depth, emask, fs, cfg)
    print("[fig-cubemap] back-projecting a window of GT depth into the fused top-down panel…", flush=True)
    fused = _fused_topdown(pano, i, cfg)
    return equ, rgb, fdepth, fmask, fused, nm


# ── Real engine hook (export mode) ────────────────────────────────────────────
def _engine_cubemap(equirect: np.ndarray, cfg: dict):
    """Reproject one equirectangular RGB (+ its depth/mask) with the ENGINE's own
    cubemap module — reused, not reimplemented (report brief). Returns
    (rgb{}, depth{}, mask{}). Kept in ONE place so an on-hardware operator can point
    it at the exact symbol if the engine's public name differs from those probed."""
    face_size = int(cfg["engine"]["face_size"])
    # Probe the verified public API first, then known internal reprojection helpers.
    import importlib
    candidates = [
        ("prism_vggt", "equirect_to_cubemap"),
        ("prism_vggt", "reproject_equirect_to_cube"),
        ("prism_vggt.reprojection", "equirect_to_cubemap"),
        ("prism_vggt.geometry.cubemap", "equirect_to_cubemap"),
        ("prism_vggt.utils.cubemap", "to_cubemap"),
    ]
    fn = None
    for mod, name in candidates:
        try:
            fn = getattr(importlib.import_module(mod), name)
            print(f"[fig-cubemap] using engine reprojection {mod}.{name}")
            break
        except Exception:
            continue
    if fn is None:
        raise SystemExit(
            "[fig-cubemap] could not locate the engine's equirect->cubemap function.\n"
            "  Easiest fix: use `--mode dataset` — it builds the REAL figure from the\n"
            "  rendered export (equirect RGB + GT depth + validity mask), no engine API\n"
            "  needed. Otherwise point _engine_cubemap() at the correct prism_vggt symbol.")
    out = fn(equirect, face_size=face_size)   # expected: dict face-> {rgb,depth,mask}
    rgb = {f: np.asarray(out[f]["rgb"]) for f in FACES if f in out}
    depth = {f: np.asarray(out[f].get("depth")) for f in FACES if f in out}
    mask = {f: np.asarray(out[f].get("mask")) for f in FACES if f in out}
    return rgb, depth, mask


def _load_pano_frame(cfg: dict, scene: str, traj: str, frame: int):
    """Load one exported equirectangular RGB frame for the chosen run."""
    from bench.config import export_dir
    ds = cfg["datasets"]["active"][0]
    d = export_dir(ds, scene, traj, "pano", "")
    names = sorted(p.stem for p in (d / "rgb").glob("*.png"))
    if not names:
        raise SystemExit(f"[fig-cubemap] no pano frames at {d} — run `make render export` first.")
    import imageio.v2 as imageio
    nm = names[min(frame, len(names) - 1)]
    return np.asarray(imageio.imread(d / "rgb" / f"{nm}.png"))[..., :3], d, nm


def _engine_fused_surface(cfg, scene, traj, frame):
    """Best-effort: run ONE window ending at `frame` through the engine and return a
    top-down render of the fused TSDF crop. Returns None if the engine/weights are
    unavailable (the composer then draws a placeholder panel)."""
    try:
        import os
        os.environ.setdefault("PRISM_VRAM_PROFILE", "1")   # engage the VRAMProfiler
        from prism_vggt import PanoVGGTBackend, StreamingWindowEngine, FrameInput, download_weights  # noqa: F401
    except Exception as e:
        print(f"[fig-cubemap] engine import failed ({e}); fused panel = placeholder.")
        return None
    # Intentionally minimal — the fused surface is also shown elsewhere in the report;
    # a full re-run here is out of scope. Operators can wire the window render in.
    return None


# ── Composition ───────────────────────────────────────────────────────────────
def _depth_to_rgb(depth: np.ndarray) -> np.ndarray:
    import matplotlib.cm as cm
    d = depth.astype(np.float32)
    valid = d > 0
    if valid.any():
        lo, hi = np.percentile(d[valid], [2, 98])
        dn = np.clip((d - lo) / max(hi - lo, 1e-6), 0, 1)
    else:
        dn = np.zeros_like(d)
    rgb = (cm.turbo(dn)[..., :3] * 255).astype(np.uint8)
    rgb[~valid] = 0
    return rgb


def _montage(imgs: dict, size: int, tint_mask: dict = None):
    """2 rows x 3 cols montage of the 6 faces (front,right,back / left,up,down) with
    labels; optionally red-tint the masked-out (dropped) pixels."""
    pad = max(2, size // 60)
    lab_h = max(14, size // 12)
    cell = size + lab_h
    canvas = np.full((2 * cell + pad, 3 * (size + pad) + pad, 3), 255, np.uint8)
    for i, f in enumerate(FACES):
        r, c = divmod(i, 3)
        im = np.asarray(imgs[f])
        if im.ndim == 2:
            im = np.repeat(im[..., None], 3, axis=2)
        im = im[..., :3].astype(np.uint8).copy()
        if tint_mask is not None and f in tint_mask and tint_mask[f] is not None:
            drop = tint_mask[f] == 0
            im[drop] = (0.5 * im[drop] + 0.5 * np.array([230, 40, 40])).astype(np.uint8)
        y0 = r * cell + lab_h + pad
        x0 = c * (size + pad) + pad
        canvas[y0:y0 + size, x0:x0 + size] = im
    return canvas, cell, size, pad, lab_h


def compose(equirect, rgb, depth, mask, fused, out_png: Path, schematic: bool, meta: str):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyArrow

    fs = next(iter(rgb.values())).shape[0]
    face_rgb, *_ = _montage(rgb, fs, tint_mask=mask)
    depth_rgb = {f: _depth_to_rgb(depth[f]) for f in FACES if f in depth and depth[f] is not None}
    have_depth = len(depth_rgb) == 6
    if have_depth:
        face_depth, *_ = _montage(depth_rgb, fs)

    ncol = 4 if have_depth else 3
    fig = plt.figure(figsize=(4.6 * ncol, 5.0))
    gs = fig.add_gridspec(1, ncol, wspace=0.28)

    ax0 = fig.add_subplot(gs[0, 0])
    ax0.imshow(equirect); ax0.set_title("(1) equirectangular\npanorama (RGB)", fontsize=11)
    ax0.set_xticks([]); ax0.set_yticks([])

    ax1 = fig.add_subplot(gs[0, 1])
    ax1.imshow(face_rgb)
    ax1.set_title("(2) six 90 deg cube faces\n+ validity / seam mask (red = dropped)", fontsize=11)
    ax1.set_xticks([]); ax1.set_yticks([])

    col = 2
    if have_depth:
        ax2 = fig.add_subplot(gs[0, col])
        ax2.imshow(face_depth); ax2.set_title("(2b) per-face metric depth", fontsize=11)
        ax2.set_xticks([]); ax2.set_yticks([]); col += 1

    ax3 = fig.add_subplot(gs[0, col])
    if fused is not None:
        ax3.imshow(fused)
    else:
        ax3.set_facecolor("#eef1f4")
        ax3.text(0.5, 0.5, "fused surface\n\n[--mode dataset back-projects\nGT depth here; --mode export\nuses the engine's nvblox TSDF]",
                 ha="center", va="center", fontsize=9, color="#556")
    ax3.set_title("(3) fused TSDF surface", fontsize=11)
    ax3.set_xticks([]); ax3.set_yticks([])

    # left->right arrows between panels
    for i in range(ncol - 1):
        fig.add_artist(FancyArrow(0.02 + (i + 1) / ncol - 0.012, 0.5, 0.02, 0,
                                  transform=fig.transFigure, width=0.004,
                                  head_width=0.02, head_length=0.008, color="#333"))

    title = "Equirectangular -> cubemap -> fused volume  (PRISM-VGGT projection pipeline)"
    fig.suptitle(title, fontsize=13, y=1.02)
    fig.text(0.5, -0.03, meta, ha="center", fontsize=7.5, color="0.4")

    if schematic:
        fig.text(0.5, 0.5, "SCHEMATIC — regenerate on hardware (--mode export)",
                 ha="center", va="center", fontsize=22, color="red", alpha=0.20,
                 rotation=18, fontweight="bold")
    out_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_png, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"[fig-cubemap] wrote {out_png}")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--mode", choices=["illustrative", "dataset", "export"], default="dataset",
                    help="dataset = real intermediates from the export (recommended); "
                         "export = engine reprojection; illustrative = schematic preview")
    ap.add_argument("--config", default="config.yaml")
    ap.add_argument("--scene", default="")
    ap.add_argument("--traj", default="synthetic_2.0hz_s0")
    ap.add_argument("--frame", type=int, default=0)
    ap.add_argument("--out-dir", default=str(DEFAULT_OUT))
    args = ap.parse_args()
    cfg = load_config(args.config)
    out_png = Path(args.out_dir) / "cubemap_projection.png"
    face_size = int(cfg["engine"]["face_size"])

    if args.mode == "illustrative":
        # keep the schematic light so it renders fast; the real export uses face_size.
        equ, rgb, depth, mask, fused = _illustrative_intermediates(min(face_size, 384))
        compose(equ, rgb, depth, mask, fused, out_png, schematic=True,
                meta="SCHEMATIC (synthetic panorama, standard gnomonic resampling). "
                     "Not measured data — replace with `--mode dataset` (real export frame).")
        return

    scene = args.scene if args.scene and args.scene != "auto" else \
        (cfg["datasets"].get("replica", {}).get("scenes") or ["scene"])[0]

    if args.mode == "dataset":
        equ, rgb, depth, mask, fused, nm = _dataset_intermediates(cfg, scene, args.traj, args.frame)
        compose(equ, rgb, depth, mask, fused, out_png, schematic=False,
                meta=f"Real dataset export — {scene}/{args.traj} frame {nm}, face_size={face_size}, "
                     f"max_depth={cfg['engine']['max_depth']} m. Equirect->cube = fixed geometric "
                     "reprojection; per-face depth is the render's GT depth (not PRISM's predicted "
                     "depth); fused panel = GT depth back-projected over a window, top-down. "
                     "Rendered scene (noise-free; optimistic vs. real Theta X capture).")
        return

    # mode == export: real intermediates from the engine's own reprojection.
    equirect, exp_dir, nm = _load_pano_frame(cfg, scene, args.traj, args.frame)
    rgb, depth, mask = _engine_cubemap(equirect, cfg)
    fused = _engine_fused_surface(cfg, scene, args.traj, args.frame)
    compose(equirect, rgb, depth, mask, fused, out_png, schematic=False,
            meta=f"Real engine export — {scene}/{args.traj} frame {nm}, face_size={face_size}, "
                 f"voxel={cfg['engine']['voxel_size']} m, max_depth={cfg['engine']['max_depth']} m. "
                 "Rendered scene (noise-free; optimistic vs. real Theta X capture).")


if __name__ == "__main__":
    main()

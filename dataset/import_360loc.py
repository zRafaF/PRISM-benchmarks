#!/usr/bin/env python
"""Import a real 360 deg sequence from 360Loc (CVPR 2024) into the benchmark's input layout.

360Loc: https://github.com/HuajianUP/360Loc — 4 campus scenes captured with a handheld
360 deg camera + lidar; equirectangular 6144x3072 images, cm-level lidar GT poses (c2w,
COLMAP/OpenCV camera axes: x right, y down, z forward). Its equirect convention
(process.py: dir = (cos lat sin lon, -sin lat, cos lat cos lon), image centre = +z) is
the same as ours (bench/cameras.py), so a pano only needs resizing and every other
camera is resampled from it — the pinhole and cube views see exactly the same capture
(decisions D28, D31).

Writes, per sequence (traj id):
  dataset/exports/<ds>/<scene>/<traj>/
    poses_gt.tum                 GT c2w, frame-index timestamps
    measured_camera_height.json  camera height above the floor (PRISM's metric anchor)
    source.json                  provenance: source dir, images used, steps, height method
    pano/{rgb,mask}/NNNNNN.png + intrinsics.json        (resized equirect)
    pinhole/<variant>/{rgb,mask}/... + intrinsics.json  (synthetic_fov, cube variants;
                                                        cube faces interleaved 4t+k + faces.json)
No GT mesh: the reconstruction GT is a map fused from the dataset's depth maps under the
GT poses (gt_cloud.ply), and the pinhole/cube views get depth resampled from the same
depth maps (for the co-visibility mask). `export_inputs.py` then writes meta.json as for
rendered scenes.

Two corrections for handheld 360Loc captures (decisions D31):
  * HEADING. The 360 images are gyro-levelled but their image centre is not the walking
    direction (it drifts with the operator's grip). Each panorama is rotated about the
    vertical (an exact column shift) so its centre looks along the smoothed direction of
    travel, and the GT orientation gets the same rotation. The pinhole "front" view then
    looks forward, as on a robot and in the Replica renders.
  * OPERATOR. The person holding the rig is in every panorama, behind and below the
    camera — after the heading correction always at the back. A fixed region (back
    sector below the horizon, wider sector for the arms, and everything near nadir) is
    blacked out in the panorama before any view is resampled, and marked invalid in the
    masks: every method loses the same pixels, the forward pinhole never sees them.
Camera height: from the dataset's 360 depth maps (straight-down depth, `depth_scale`
metres per unit — 0.01, i.e. centimetres, checked by aligning the depth clouds of two
frames with the GT poses), else from a point cloud, else from the config.

Use `--list` first to see which sequences a downloaded scene contains.
Usage (overlay config.real360.yaml sets the dataset, scenes and sequences):
  PRISM_CONFIG_OVERLAY=config.real360.yaml uv run python dataset/import_360loc.py --list
  PRISM_CONFIG_OVERLAY=config.real360.yaml uv run python dataset/import_360loc.py
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "dataset"))

from bench import cameras  # noqa: E402
from bench.config import export_dir, is_cube_variant, load_config, resolve_trajs  # noqa: E402

IMG_EXT = (".jpg", ".jpeg", ".png")


def _natkey(s: str):
    return [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", s)]


# ── discovery ────────────────────────────────────────────────────────────────
def find_sequences(scene_dir: Path) -> list[Path]:
    """Every directory under the scene that holds an image/ folder of 360 images."""
    out = []
    for d in sorted(scene_dir.rglob("image")):
        if d.is_dir() and any(p.suffix.lower() in IMG_EXT for p in d.iterdir()):
            out.append(d.parent)
    return out


def _load_pose_file(p: Path) -> dict:
    """{image_name: 4x4 c2w} from a 360Loc pose file (.json 4x4 or .txt name x y z qw qx qy qz)."""
    from scipy.spatial.transform import Rotation
    out = {}
    if p.suffix == ".json":
        try:
            d = json.loads(p.read_text())
        except Exception:
            return {}
        if isinstance(d, dict):
            for k, v in d.items():
                a = np.asarray(v, dtype=float)
                if a.shape in ((4, 4), (3, 4)):
                    T = np.eye(4); T[:a.shape[0], :] = a
                    out[Path(k).name] = T
    elif p.suffix == ".txt":
        for ln in p.read_text().splitlines():
            v = ln.split()
            if len(v) != 8 or ln.startswith("#"):
                continue
            try:
                x, y, z, qw, qx, qy, qz = (float(a) for a in v[1:])
            except ValueError:
                continue
            T = np.eye(4)
            T[:3, :3] = Rotation.from_quat([qx, qy, qz, qw]).as_matrix()
            T[:3, 3] = [x, y, z]
            # Keep the image path as written: query pose files list several sequences
            # whose images share names (query_360/daytime_360_1/image/0001.jpg,
            # .../daytime_360_2/image/0001.jpg, ...); keying by name alone mixes them.
            out[v[0].lstrip("./")] = T
    return out


def find_poses(seq_dir: Path, scene_dir: Path, names: list[str]) -> tuple[dict, Path]:
    """The pose file (next to the images, or under the scene's pose/ dir) that covers
    the most of this sequence's images."""
    cands = list(seq_dir.glob("*.json")) + list(seq_dir.glob("*.txt"))
    if (scene_dir / "pose").exists():
        cands += list((scene_dir / "pose").rglob("*.json")) + list((scene_dir / "pose").rglob("*.txt"))
    rel = seq_dir.relative_to(scene_dir).as_posix()
    best, best_p, best_n = {}, None, 0
    for p in cands:
        d = _load_pose_file(p)
        if any("/" in k for k in d):
            # path keys: only entries of THIS sequence (<seq>/image/<name>) count
            d = {Path(k).name: v for k, v in d.items() if k.startswith(rel + "/")}
        n = len(set(names) & set(d))
        if n > best_n:
            best, best_p, best_n = d, p, n
    return best, best_p


def find_cloud(scene_dir: Path) -> Path | None:
    """Largest point cloud / mesh file in the scene (for the camera-height estimate)."""
    c = [p for p in scene_dir.rglob("*") if p.suffix.lower() in (".ply", ".pcd") and p.is_file()]
    return max(c, key=lambda p: p.stat().st_size) if c else None


# ── geometry ─────────────────────────────────────────────────────────────────
def segments(P: np.ndarray, jump_m: float) -> list[tuple[int, int]]:
    """Split a trajectory where consecutive positions jump more than jump_m."""
    if len(P) < 2:
        return [(0, len(P))]
    step = np.linalg.norm(np.diff(P, axis=0), axis=1)
    cuts = list(np.flatnonzero(step > jump_m) + 1)
    b = [0] + cuts + [len(P)]
    return [(b[i], b[i + 1]) for i in range(len(b) - 1)]


def camera_height(poses: np.ndarray, cloud: Path | None, every: int = 10) -> tuple[float | None, str]:
    """Height of the camera above the floor, from the scene point cloud: up = mean
    camera up axis (-y, the 360 camera is gyro-levelled), floor = low percentile of the
    points within 1 m horizontally below each sampled camera."""
    if cloud is None:
        return None, "no point cloud found"
    import open3d as o3d
    pc = o3d.io.read_point_cloud(str(cloud))
    pts = np.asarray(pc.points)
    if len(pts) < 1000:
        m = o3d.io.read_triangle_mesh(str(cloud))
        pts = np.asarray(m.vertices)
    if len(pts) < 1000:
        return None, f"{cloud.name}: too few points"
    up = -poses[:, :3, 1].mean(0)
    up /= np.linalg.norm(up)
    hs = []
    for T in poses[::max(1, every)]:
        c = T[:3, 3]
        d = pts - c
        h = d @ up
        horiz = np.linalg.norm(d - np.outer(h, up), axis=1)
        sel = h[(horiz < 1.0) & (h < -0.3) & (h > -3.0)]
        if len(sel) > 50:
            hs.append(-np.percentile(sel, 2))
    if not hs:
        return None, f"{cloud.name}: no floor points under the cameras"
    return float(np.median(hs)), f"point cloud {cloud.name}: median over {len(hs)} cameras (spread {np.std(hs):.3f} m)"


def camera_height_from_depth(depth_dir: Path, names: list[str], scale: float,
                             every: int = 10) -> tuple[float | None, str]:
    """Median straight-down depth (latitude < -85 deg) of the dataset's 360 depth maps.
    The depth comes from the lidar map, so the operator below the camera is not in it."""
    if not depth_dir.exists():
        return None, "no depth maps"
    import imageio.v2 as imageio
    hs = []
    for nm in names[::max(1, every)]:
        p = depth_dir / (Path(nm).stem + ".png")
        if not p.exists():
            continue
        d = imageio.imread(p).astype(np.float64)
        H = d.shape[0]
        rows = d[int(H * (1 - 5.0 / 180.0)):]                 # last 5 deg of latitude
        v = rows[rows > 0]
        if v.size:
            hs.append(float(np.median(v)) * scale)
    if not hs:
        return None, f"{depth_dir.name}: no depth near nadir"
    return float(np.median(hs)), (f"depth maps (nadir, scale {scale} m/unit): median over "
                                  f"{len(hs)} frames, spread {np.std(hs):.3f} m")


def heading_yaw(P: np.ndarray, smooth: int = 5) -> np.ndarray:
    """Per-frame yaw (rad, about the camera's vertical y axis) that turns the camera's
    +z onto the direction of travel. The travel direction is smoothed in the WORLD frame
    (moving average of unit central-difference steps over `smooth` frames) and only then
    expressed in each camera frame — the camera's own heading may change arbitrarily
    between frames (the operator's grip)."""
    n = len(P)
    C = P[:, :3, 3]
    d = np.zeros((n, 3))
    for i in range(n):
        a, b = max(0, i - 1), min(n - 1, i + 1)
        v = C[b] - C[a]
        nv = np.linalg.norm(v)
        d[i] = v / nv if nv > 1e-9 else 0.0
    k = max(1, int(smooth))
    if k > 1:
        ds = np.zeros_like(d)
        for i in range(n):
            lo, hi = max(0, i - k // 2), min(n, i - k // 2 + k)
            ds[i] = d[lo:hi].sum(0)
        d = ds
    yaw = np.zeros(n)
    for i in range(n):
        if np.linalg.norm(d[i]) < 1e-9:
            yaw[i] = yaw[i - 1] if i else 0.0
            continue
        dc = P[i, :3, :3].T @ d[i]
        yaw[i] = np.arctan2(dc[0], dc[2])
    return yaw


def rot_y(a: float) -> np.ndarray:
    return np.array([[np.cos(a), 0.0, np.sin(a)], [0.0, 1.0, 0.0], [-np.sin(a), 0.0, np.cos(a)]])


def operator_mask(H: int, W: int, m: dict) -> np.ndarray:
    """True where the handheld operator is, in a heading-corrected panorama (operator at
    the back, azimuth 180). Sectors in degrees from the back direction / latitude."""
    lon = (np.arange(W) + 0.5) / W * 360.0 - 180.0
    lat = 90.0 - (np.arange(H) + 0.5) / H * 180.0
    LON, LAT = np.meshgrid(lon, lat)
    dback = 180.0 - np.abs(LON)
    out = (dback < m.get("back_halfwidth_deg", 55)) & (LAT < m.get("top_lat_deg", -8))
    out |= (dback < m.get("arms_halfwidth_deg", 85)) & (LAT < m.get("arms_top_lat_deg", -35))
    out |= LAT < m.get("nadir_lat_deg", -65)
    return out


def _sample_nearest(img: np.ndarray, dirs: np.ndarray, out_hw) -> np.ndarray:
    """Nearest-neighbour lookup (for depth: never blend across a depth edge)."""
    H, W = img.shape[:2]
    x, y, z = dirs[:, 0], dirs[:, 1], dirs[:, 2]
    lon = np.arctan2(x, z)
    lat = np.arcsin(np.clip(-y / np.linalg.norm(dirs, axis=1), -1, 1))
    u = np.rint((lon + np.pi) / (2 * np.pi) * W - 0.5).astype(int) % W
    v = np.clip(np.rint((np.pi / 2 - lat) / np.pi * H - 0.5).astype(int), 0, H - 1)
    return img[v, u].reshape(out_hw)


def _sample(pano: np.ndarray, dirs: np.ndarray, out_hw) -> np.ndarray:
    """Bilinear lookup of camera-frame ray directions in an equirect image (our / 360Loc
    convention), horizontally wrapped."""
    from scipy.ndimage import map_coordinates
    H, W = pano.shape[:2]
    x, y, z = dirs[:, 0], dirs[:, 1], dirs[:, 2]
    lon = np.arctan2(x, z)
    lat = np.arcsin(np.clip(-y / np.linalg.norm(dirs, axis=1), -1, 1))
    u = (lon + np.pi) / (2 * np.pi) * W - 0.5 + 1.0        # +1: wrap padding below
    v = (np.pi / 2 - lat) / np.pi * H - 0.5
    padded = np.concatenate([pano[:, -1:], pano, pano[:, :1]], axis=1)
    out = np.empty((len(dirs), pano.shape[2]), np.float32)
    for c in range(pano.shape[2]):
        out[:, c] = map_coordinates(padded[..., c].astype(np.float32), [v, u], order=1, mode="nearest")
    return np.clip(out, 0, 255).astype(np.uint8).reshape(out_hw[0], out_hw[1], -1)


# ── per-frame work (worker) ────────────────────────────────────────────────────
_JOB: dict = {}


def _init(job):
    _JOB.clear(); _JOB.update(job)


def _frame(args):
    i, src = args
    import imageio.v2 as imageio
    from PIL import Image
    j = _JOB
    full = np.asarray(Image.open(src).convert("RGB"))
    shift = int(j["shifts"][i])
    if shift:
        full = np.roll(full, -shift, axis=1)          # centre column -> direction of travel
    if j["op_mask"] is not None:
        om = j["op_mask"]
        if om.shape[:2] != full.shape[:2]:
            om = np.asarray(Image.fromarray(om.astype(np.uint8) * 255).resize(
                (full.shape[1], full.shape[0]), Image.NEAREST)) > 0
        full = full.copy()
        full[om] = 0                                  # every method loses the same pixels
    pw, ph = j["pano_wh"]
    pano = np.asarray(Image.fromarray(full).resize((pw, ph), Image.BOX))
    nm = f"{i:06d}.png"
    imageio.imwrite(Path(j["pano_dir"]) / "rgb" / nm, pano)
    imageio.imwrite(Path(j["pano_dir"]) / "mask" / nm, j["pano_mask"])
    valid = j["valid_full"]                          # (H,W,1) uint8 255 = valid, matches `full`
    for v in j["views"]:
        rots = v["faces"] if v["faces"] else [np.eye(3).tolist()]
        for k, R in enumerate(rots):
            d = v["dirs"] @ np.asarray(R).T
            img = _sample(full, d, (v["h"], v["w"]))
            msk = _sample(valid, d, (v["h"], v["w"]))[..., 0]
            fn = f"{len(rots) * i + k:06d}.png" if v["faces"] else nm
            imageio.imwrite(Path(v["dir"]) / "rgb" / fn, img)
            imageio.imwrite(Path(v["dir"]) / "mask" / fn, np.where(msk > 127, 255, 0).astype(np.uint8))

    # GT depth (if the sequence has 360Loc depth maps): pinhole depth for the co-visibility
    # mask of the reconstruction scores, and this frame's share of the GT reference map.
    pts = None
    dd = j.get("depth_dir")
    if dd:
        dp = Path(dd) / (Path(src).stem + ".png")
        if dp.exists():
            depth = imageio.imread(dp).astype(np.float32) * float(j["depth_scale"])   # metres, radial
            # (a) map points, from the ORIGINAL (un-rotated) depth and pose
            stp = int(j["map_step"])
            ds_ = depth[::stp, ::stp]
            dirs = cameras.equirect_rays_cam(ds_.shape[1], ds_.shape[0])
            r = ds_.reshape(-1)
            ok = (r > 0.1) & (r < float(j["map_range"]))
            T = np.asarray(j["P_orig"][i])
            pw_ = (dirs[ok] * r[ok, None]) @ T[:3, :3].T + T[:3, 3]
            vk = np.floor(pw_ / float(j["map_voxel"])).astype(np.int64)
            _, first = np.unique(vk, axis=0, return_index=True)
            pts = pw_[first].astype(np.float32)
            # (b) depth for the ordinary pinhole views (cube faces are not used for masks)
            if shift:
                depth = np.roll(depth, -shift, axis=1)
            for v in j["views"]:
                if v["faces"]:
                    continue
                rad = _sample_nearest(depth, v["dirs"], (v["h"], v["w"]))
                zc = (v["dirs"][:, 2] / np.linalg.norm(v["dirs"], axis=1)).reshape(v["h"], v["w"])
                mm = np.clip(rad * zc * 1000.0, 0, 65535).astype(np.uint16)
                (Path(v["dir"]) / "depth").mkdir(exist_ok=True)
                imageio.imwrite(Path(v["dir"]) / "depth" / nm, mm)
    return i, pts


def import_sequence(cfg, ds: str, scene: str, traj: str, seq_rel: str, workers: int):
    import shutil
    dcfg = cfg["datasets"][ds]
    scene_dir = ROOT / dcfg["root"] / scene
    seq_dir = scene_dir / seq_rel
    if not (seq_dir / "image").exists():
        subs = [s for s in find_sequences(seq_dir)] if seq_dir.exists() else []
        if len(subs) == 1:
            seq_dir = subs[0]
        else:
            raise SystemExit(f"!! {seq_dir}: no image/ folder; sequences under it: "
                             f"{[str(s.relative_to(scene_dir)) for s in subs]} — set "
                             f"datasets.{ds}.sequences.{traj} to one of them (see --list)")
    imgs = sorted((p for p in (seq_dir / "image").iterdir() if p.suffix.lower() in IMG_EXT),
                  key=lambda p: _natkey(p.name))
    poses_by_name, pose_file = find_poses(seq_dir, scene_dir, [p.name for p in imgs])
    imgs = [p for p in imgs if p.name in poses_by_name]
    if len(imgs) < 10:
        raise SystemExit(f"!! {seq_dir}: only {len(imgs)} images with a GT pose (pose file {pose_file})")
    P = np.stack([poses_by_name[p.name] for p in imgs])
    steps = np.linalg.norm(np.diff(P[:, :3, 3], axis=0), axis=1)
    med = float(np.median(steps))
    jump = float(dcfg.get("max_step_m") or max(1.0, 8 * med))
    segs = segments(P[:, :3, 3], jump)
    a, b = max(segs, key=lambda s: s[1] - s[0])
    stride = int(dcfg.get("stride", 1))
    sel = list(range(a, b, stride))
    maxf = dcfg.get("max_frames")
    if maxf:
        sel = sel[: int(maxf)]
    imgs = [imgs[i] for i in sel]
    P = P[sel]
    st = np.linalg.norm(np.diff(P[:, :3, 3], axis=0), axis=1)
    print(f"[360loc] {scene}/{traj}: {seq_dir.relative_to(scene_dir)} — poses from "
          f"{pose_file.relative_to(scene_dir) if pose_file else '?'}; {len(segs)} continuous "
          f"segment(s) (jump > {jump:.2f} m), using frames {a}..{b - 1} stride {stride} -> "
          f"{len(imgs)} frames, path {st.sum():.1f} m, step median {np.median(st):.3f} m / "
          f"max {st.max():.3f} m")

    h = dcfg.get("camera_height_m")
    how = "config"
    if h is None:
        h, how = camera_height_from_depth(seq_dir / "depth", [p.name for p in imgs],
                                          float(dcfg.get("depth_scale", 0.01)))
    if h is None:
        # Query sequences have no depth maps: same rig and operator as the scene's
        # reference sequence, so reuse the height measured there (import `ref` first).
        for mh in sorted((ROOT / "dataset" / "exports" / ds / scene).glob("*/measured_camera_height.json")):
            src = json.loads((mh.parent / "source.json").read_text()) if (mh.parent / "source.json").exists() else {}
            if str(src.get("camera_height_from", "")).startswith("depth maps"):
                h = float(json.loads(mh.read_text())["camera_height_m"])
                how = f"reference sequence {mh.parent.name} (depth maps)"
                break
    if h is None:
        h, how = camera_height(P, find_cloud(scene_dir))
    if h is None:
        raise SystemExit(f"!! camera height unknown ({how}); set datasets.{ds}.camera_height_m")
    print(f"[360loc] camera height {h:.3f} m ({how})")

    # Heading correction: rotate each panorama (and its GT orientation) about the camera's
    # vertical so the image centre looks along the direction of travel. Quantised to whole
    # columns of the source image so pixels and GT agree exactly.
    from PIL import Image
    W_src = Image.open(imgs[0]).size[0]
    P_orig = P.copy()                       # depth maps live in the original camera frames
    if dcfg.get("align_heading", True):
        yaw = heading_yaw(P, int(dcfg.get("heading_smooth_frames", 5)))
        shifts = np.rint(yaw / (2 * np.pi) * W_src).astype(int) % W_src
        yq = shifts * 2 * np.pi / W_src
        P = P.copy()
        for t in range(len(P)):
            P[t, :3, :3] = P[t, :3, :3] @ rot_y(yq[t])
        print(f"[360loc] heading-aligned: image centre -> direction of travel "
              f"(smoothed over {int(dcfg.get('heading_smooth_frames', 5))} frames)")
    else:
        shifts = np.zeros(len(P), int)

    out = ROOT / "dataset" / "exports" / ds / scene / traj
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    from scipy.spatial.transform import Rotation
    lines = []
    for i, T in enumerate(P):
        q = Rotation.from_matrix(T[:3, :3]).as_quat()
        lines.append(f"{i} {T[0, 3]:.6f} {T[1, 3]:.6f} {T[2, 3]:.6f} {q[0]:.6f} {q[1]:.6f} {q[2]:.6f} {q[3]:.6f}")
    (out / "poses_gt.tum").write_text("\n".join(lines) + "\n")
    (out / "measured_camera_height.json").write_text(json.dumps({"camera_height_m": h}, indent=2))

    pw, ph = cfg["camera"]["pano"]["width"], cfg["camera"]["pano"]["height"]
    pdir = export_dir(ds, scene, traj, "pano", "")
    for s in ("rgb", "mask"):
        (pdir / s).mkdir(parents=True, exist_ok=True)
    (pdir / "intrinsics.json").write_text(json.dumps({"projection": "equirect", "width": pw, "height": ph}, indent=2))
    # Operator mask (see the module docstring): fixed region in the heading-aligned frame.
    opm = dcfg.get("operator_mask")
    if opm:
        op_small = operator_mask(ph, pw, opm)
        pmask = np.where(op_small, 0, 255).astype(np.uint8)
        H_src = Image.open(imgs[0]).size[1]
        op_full = operator_mask(H_src, W_src, opm)
        valid_full = np.where(op_full, 0, 255).astype(np.uint8)[..., None]
        print(f"[360loc] operator mask: {100 * op_small.mean():.1f}% of the panorama blacked out")
    else:
        op_full = None
        pmask = np.full((ph, pw), 255, np.uint8)
        H_src = Image.open(imgs[0]).size[1]
        valid_full = np.full((H_src, W_src, 1), 255, np.uint8)

    views = []
    from render_scene import cube_face_rotations
    for vname, vcfg in cfg["camera"]["pinhole"]["variants"].items():
        if vcfg.get("use_dataset_k"):
            continue
        vdir = export_dir(ds, scene, traj, "pinhole", vname)
        for s in ("rgb", "mask"):
            (vdir / s).mkdir(parents=True, exist_ok=True)
        if is_cube_variant(vcfg):
            nf = int(vcfg.get("cube_faces", 4))
            size = int(vcfg.get("width", 512))
            fov = 360.0 / nf + float(vcfg.get("face_overlap_deg", 0.0))
            intr = cameras.PinholeIntrinsics.from_fov(size, size, fov)
            Rf = cube_face_rotations(nf)
            (vdir / "faces.json").write_text(json.dumps({
                "n_faces": nf, "order": ["front", "right", "back", "left"][:nf],
                "fov_deg": fov, "face_overlap_deg": float(vcfg.get("face_overlap_deg", 0.0)),
                "interleave": "image index = n_faces * timestep + face",
                "R_body_face": [r.tolist() for r in Rf]}, indent=2))
            faces = [r.tolist() for r in Rf]
        else:
            intr = cameras.PinholeIntrinsics.from_fov(vcfg["width"], vcfg["height"], vcfg["fov_deg"])
            faces = None
        (vdir / "intrinsics.json").write_text(json.dumps(intr.to_json(), indent=2))
        views.append({"dir": str(vdir), "w": intr.width, "h": intr.height, "faces": faces,
                      "dirs": cameras.pinhole_rays_cam(intr).astype(np.float32)})
    gm = dcfg.get("gt_map") or {}
    has_depth = (seq_dir / "depth").exists()
    job = {"pano_dir": str(pdir), "pano_wh": (pw, ph), "pano_mask": pmask, "views": views,
           "shifts": shifts.tolist(), "op_mask": op_full, "valid_full": valid_full,
           "depth_dir": str(seq_dir / "depth") if has_depth else None,
           "depth_scale": float(dcfg.get("depth_scale", 0.01)), "P_orig": P_orig.tolist(),
           "map_step": int(gm.get("pixel_step", 4)), "map_range": float(gm.get("max_range_m", 10.0)),
           "map_voxel": float(gm.get("voxel_m", 0.02))}
    work = list(enumerate(map(str, imgs)))
    vox = float(job["map_voxel"])
    acc, merged = [], np.zeros((0, 3), np.float32)

    def _merge(arrs, base):
        a = np.concatenate([base] + arrs) if arrs else base
        if not len(a):
            return a
        k = np.floor(a / vox).astype(np.int64)
        _, first = np.unique(k, axis=0, return_index=True)
        return a[first]

    def _take(res, n):
        nonlocal acc, merged
        if res[1] is not None:
            acc.append(res[1])
        if len(acc) >= 40:
            merged = _merge(acc, merged); acc = []
        if n % 50 == 0 or n == len(work):
            print(f"[360loc]   {n}/{len(work)} frames")

    if workers > 1:
        with ProcessPoolExecutor(workers, initializer=_init, initargs=(job,)) as ex:
            for n, res in enumerate(ex.map(_frame, work, chunksize=4), 1):
                _take(res, n)
    else:
        _init(job)
        for n, w in enumerate(work, 1):
            _take(_frame(w), n)
    merged = _merge(acc, merged)

    # GT reference map (decisions D31): the 360Loc depth maps are rendered from the
    # authors' lidar map, so fusing them with the GT poses rebuilds that map where the
    # reference sequence saw it. Built from the first sequence that has depth maps and
    # cached per scene; every sequence of the scene is scored against the same map.
    scene_map = ROOT / "dataset" / "exports" / ds / scene / "_gt_map.ply"
    import open3d as o3d
    if len(merged):
        pc = o3d.geometry.PointCloud(o3d.utility.Vector3dVector(merged.astype(np.float64)))
        o3d.io.write_point_cloud(str(scene_map), pc)
        print(f"[360loc] GT map: {len(merged)} points ({vox} m voxels, <= {job['map_range']} m "
              f"from each camera) -> {scene_map.relative_to(ROOT)}")
    if scene_map.exists():
        shutil.copy2(scene_map, out / "gt_cloud.ply")
    else:
        print(f"[360loc] NOTE: no GT map for {scene} yet (no depth maps in this sequence; import "
              f"the reference sequence first) — reconstruction cannot be scored for {traj}")
    (out / "source.json").write_text(json.dumps({
        "dataset": "360Loc (Huang et al., CVPR 2024)", "scene": scene,
        "sequence": str(seq_dir.relative_to(scene_dir)),
        "pose_file": str(pose_file.relative_to(scene_dir)) if pose_file else None,
        "frames_source_range": [a, b - 1], "stride": stride, "n_frames": len(imgs),
        "images": [p.name for p in imgs], "path_m": float(st.sum()),
        "step_median_m": float(np.median(st)), "camera_height_m": h, "camera_height_from": how,
        "heading_aligned": bool(dcfg.get("align_heading", True)),
        "operator_mask": opm or None}, indent=2))
    print(f"[360loc] {scene}/{traj}: wrote {len(imgs)} frames -> {out.relative_to(ROOT)}")


def main():
    ap = argparse.ArgumentParser(description="Import 360Loc sequences (real 360 deg) into the export layout")
    ap.add_argument("--config", default="config.yaml")
    ap.add_argument("--list", action="store_true", help="list the sequences found in each scene and exit")
    ap.add_argument("--workers", type=int, default=4)
    a = ap.parse_args()
    cfg = load_config(a.config)
    ds = cfg["datasets"]["active"][0]
    dcfg = cfg["datasets"][ds]
    for scene in dcfg.get("scenes") or []:
        scene_dir = ROOT / dcfg["root"] / scene
        if not scene_dir.exists():
            raise SystemExit(f"!! {scene_dir} missing — download it first (scripts/real360.sh download)")
        if a.list:
            print(f"== {scene}")
            for s in find_sequences(scene_dir):
                n = sum(1 for p in (s / "image").iterdir() if p.suffix.lower() in IMG_EXT)
                print(f"   {str(s.relative_to(scene_dir)):40s} {n:5d} images")
            c = find_cloud(scene_dir)
            print(f"   point cloud: {c.relative_to(scene_dir) if c else 'none found'}")
            continue
        seqmap = dcfg.get("sequences") or {}
        for traj in resolve_trajs(cfg, "all"):
            if traj not in seqmap:
                continue
            import_sequence(cfg, ds, scene, traj, seqmap[traj], a.workers)


if __name__ == "__main__":
    main()

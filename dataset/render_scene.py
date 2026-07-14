"""Render matched PANO + PINHOLE frames (+ GT) from a scene mesh.

Renderer: Open3D RaycastingScene (tensor API). One ray per output pixel; the mesh
intersection gives hit distance -> depth, and barycentric interpolation of the
mesh vertex colours gives RGB. Pano and pinhole use identical intersection code,
differing only in the ray set (bench/cameras.py).

Outputs, per scene / trajectory:
  dataset/exports/<dataset>/<scene>/<traj>/pano/{rgb,depth,mask}/NNNNNN.*   (+ intrinsics.json)
  dataset/exports/<dataset>/<scene>/<traj>/pinhole/<variant>/{rgb,depth,mask}/... (+ intrinsics.json)
  dataset/exports/<dataset>/<scene>/<traj>/poses_gt.tum
  dataset/exports/<dataset>/<scene>/<traj>/gt_mesh.ply   (symlink/copy for recon GT)

GT is free: GT poses = the render trajectory; GT geometry = the mesh; GT depth =
the render depth buffer. Rendered frames are noise/artifact-free -> optimistic
upper bound (flagged in every report caption).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bench import cameras
from bench.config import REPO_ROOT, common_args, export_dir, load_config, resolve_scenes, resolve_trajs
import trajectories as traj_mod


def _write_scalar_png(path: Path, arr: np.ndarray):
    import imageio.v2 as imageio
    path.parent.mkdir(parents=True, exist_ok=True)
    imageio.imwrite(path, arr)


def _render_rays(scene, mesh_t, origins, directions, width, height, max_depth):
    """Cast rays -> (radial_depth[H,W], rgb[H,W,3] uint8, valid_mask[H,W] uint8)."""
    import open3d as o3d

    rays = np.concatenate([origins, directions], axis=1).astype(np.float32)
    ans = scene.cast_rays(o3d.core.Tensor(rays))
    t_hit = ans["t_hit"].numpy().reshape(height, width)
    prim = ans["primitive_ids"].numpy().reshape(height, width)
    uv = ans["primitive_uvs"].numpy().reshape(height, width, 2)

    # Validity = ray actually hit the mesh. We do NOT clip by max_depth here: the
    # rendered frame is ground truth (full depth); max_depth is a fusion-stage knob
    # each method applies itself. Clipping here blacked out everything past 4.5 m.
    valid = np.isfinite(t_hit)
    radial = np.where(valid, t_hit, 0.0).astype(np.float32)

    # RGB from the hit triangle. Priority: (1) per-vertex colours (ScanNet/ScanNet++),
    # (2) texture-UV sampling (Replica and other textured meshes), (3) normal-shaded
    # grey fallback so geometry-only meshes still produce non-black frames.
    tris = np.asarray(mesh_t.triangle["indices"].numpy())
    pflat = prim.reshape(-1)
    okf = valid.reshape(-1)
    safe = np.clip(pflat, 0, len(tris) - 1)
    w1 = uv.reshape(-1, 2)[:, 0]
    w2 = uv.reshape(-1, 2)[:, 1]
    w0 = 1.0 - w1 - w2
    rgb = np.zeros((height, width, 3), dtype=np.uint8)

    vcol = np.asarray(mesh_t.vertex["colors"].numpy()) if "colors" in mesh_t.vertex else None
    if vcol is not None and vcol.dtype == np.uint8:
        vcol = vcol.astype(np.float64) / 255.0
    tex_uv = np.asarray(mesh_t.triangle["texture_uvs"].numpy()) if "texture_uvs" in mesh_t.triangle else None

    if vcol is not None:
        tri = tris[safe]
        c = (w0[:, None] * vcol[tri[:, 0]] + w1[:, None] * vcol[tri[:, 1]] + w2[:, None] * vcol[tri[:, 2]])
        c = np.clip(c * 255.0, 0, 255).astype(np.uint8)
        c[~okf] = 0
        rgb = c.reshape(height, width, 3)
    elif tex_uv is not None and _TEXTURE_IMG.get("img") is not None:
        img = _TEXTURE_IMG["img"]                       # (th, tw, 3) uint8
        th, tw = img.shape[:2]
        uv_tri = tex_uv[safe]                           # (HW, 3, 2)
        u = w0 * uv_tri[:, 0, 0] + w1 * uv_tri[:, 1, 0] + w2 * uv_tri[:, 2, 0]
        v = w0 * uv_tri[:, 0, 1] + w1 * uv_tri[:, 1, 1] + w2 * uv_tri[:, 2, 1]
        px = np.clip((u % 1.0) * (tw - 1), 0, tw - 1).astype(int)
        py = np.clip((1.0 - (v % 1.0)) * (th - 1), 0, th - 1).astype(int)
        c = img[py, px]
        c[~okf] = 0
        rgb = c.reshape(height, width, 3)
    else:
        # normal-shaded grey (Lambert on the ray direction) so nets get structure
        shade = np.clip(np.abs(directions[:, 2]) * 200 + 30, 0, 255).astype(np.uint8)
        shade[~okf] = 0
        rgb = np.repeat(shade.reshape(height, width, 1), 3, axis=2)
    return radial, rgb, valid.astype(np.uint8) * 255


# Module-level texture cache (set per scene in render_scene) so _render_rays stays cheap.
_TEXTURE_IMG: dict = {"img": None}


def _load_mesh_legacy(mesh_path: Path):
    """Load into an Open3D legacy TriangleMesh, robust to quad/polygon PLYs.

    Open3D's reader aborts on Replica's quad-face meshes, and trimesh mis-reads the
    face list (yields only a few triangles). So when Open3D fails we parse the PLY
    with `plyfile` and fan-triangulate the polygon faces ourselves — reliable and
    keeps per-vertex colours.
    """
    import open3d as o3d
    mesh = o3d.io.read_triangle_mesh(str(mesh_path), enable_post_processing=True)
    nv, nt = len(mesh.vertices), len(mesh.triangles)
    # Open3D can return a PARTIAL mesh on quad/polygon PLYs: it keeps the vertices
    # but silently drops the faces it can't triangulate (e.g. Replica -> only 5116
    # tris for ~1M verts). A real mesh has ~2 triangles per vertex, so treat a very
    # low tri:vert ratio as a failed read and parse the PLY ourselves.
    if nt >= max(1, 0.5 * nv):
        return mesh
    if mesh_path.suffix.lower() == ".ply":
        print(f"[render] Open3D read looks partial (verts={nv} tris={nt}) — parsing with plyfile")
        return _load_mesh_plyfile(mesh_path)
    return mesh


def _load_mesh_plyfile(mesh_path: Path):
    """Parse a PLY (incl. quad/polygon faces + per-vertex colour) via plyfile."""
    import open3d as o3d
    from plyfile import PlyData

    ply = PlyData.read(str(mesh_path))
    v = ply["vertex"]
    verts = np.column_stack([v["x"], v["y"], v["z"]]).astype(np.float64)
    names = v.data.dtype.names
    colors = None
    if all(c in names for c in ("red", "green", "blue")):
        colors = np.column_stack([v["red"], v["green"], v["blue"]]).astype(np.float64) / 255.0

    face_el = ply["face"]
    prop = next(p.name for p in face_el.properties)      # 'vertex_indices' / 'vertex_index'
    polys = face_el.data[prop]                           # object array of index lists
    lengths = np.fromiter((len(p) for p in polys), dtype=np.int64, count=len(polys))

    if lengths.min() == lengths.max() and lengths[0] in (3, 4):
        P = np.vstack([np.asarray(p, np.int64) for p in polys])   # (F, k) — vectorised
        tris = P if lengths[0] == 3 else np.concatenate([P[:, [0, 1, 2]], P[:, [0, 2, 3]]], 0)
    else:                                                # mixed polygons -> fan triangulate
        acc = []
        for p in polys:
            p = np.asarray(p, np.int64)
            for k in range(1, len(p) - 1):
                acc.append((p[0], p[k], p[k + 1]))
        tris = np.asarray(acc, dtype=np.int64)

    m = o3d.geometry.TriangleMesh()
    m.vertices = o3d.utility.Vector3dVector(verts)
    m.triangles = o3d.utility.Vector3iVector(tris.astype(np.int32))
    if colors is not None:
        m.vertex_colors = o3d.utility.Vector3dVector(colors)
    print(f"[render] plyfile: {len(verts)} verts, {len(tris)} tris "
          f"(faces {lengths.min()}-{lengths.max()}-gon), colours={colors is not None}")
    return m


def _cache_texture(mesh, mesh_path: Path):
    """Cache an albedo texture for textured meshes lacking vertex colours."""
    _TEXTURE_IMG["img"] = None
    if mesh.has_vertex_colors():
        return
    try:
        if getattr(mesh, "textures", None):
            for tx in mesh.textures:
                arr = np.asarray(tx)
                if arr.ndim == 3 and arr.size:
                    _TEXTURE_IMG["img"] = arr[..., :3].astype(np.uint8)
                    return
        import imageio.v2 as imageio
        for cand in list(mesh_path.parent.glob("*.jpg")) + list(mesh_path.parent.glob("textures/*.jpg")):
            _TEXTURE_IMG["img"] = np.asarray(imageio.imread(cand))[..., :3].astype(np.uint8)
            return
    except Exception as e:
        print(f"[render] texture load skipped ({e}); falling back to shaded grey")


def render_scene(cfg: dict, dataset: str, scene: str, traj: str, mesh_path: Path):
    import open3d as o3d
    import imageio.v2 as imageio

    mesh = _load_mesh_legacy(mesh_path)     # robust to quad/polygon PLYs (Replica)
    a0 = mesh.get_axis_aligned_bounding_box()
    print(f"[mesh] {mesh_path}")
    print(f"[mesh] verts={len(mesh.vertices)} tris={len(mesh.triangles)} "
          f"has_vertex_colors={mesh.has_vertex_colors()}")
    print(f"[mesh] pre-rotate AABB lo={np.round(a0.get_min_bound(),2)} "
          f"hi={np.round(a0.get_max_bound(),2)}")

    # Normalise to a Z-up world (our camera model, floor logic and PRISM engine all
    # assume Z-up). up_axis="auto" picks the shortest AABB extent as the up axis
    # (room height < footprint) — robust across datasets and per-scene frames.
    up_axis = cfg["datasets"][dataset].get("up_axis", "auto")
    ext = np.asarray(a0.get_extent())
    if up_axis == "auto":
        up_axis = "xyz"[int(np.argmin(ext))]
        print(f"[mesh] auto up_axis -> '{up_axis}' (extents X/Y/Z = {np.round(ext,2)})")
    if up_axis == "y":       # Y -> Z  (rotate +90° about X)
        mesh.rotate(o3d.geometry.get_rotation_matrix_from_axis_angle([np.pi / 2, 0, 0]), (0, 0, 0))
    elif up_axis == "x":     # X -> Z  (rotate -90° about Y)
        mesh.rotate(o3d.geometry.get_rotation_matrix_from_axis_angle([0, -np.pi / 2, 0]), (0, 0, 0))
    else:
        print("[mesh] up_axis=z — no rotation needed")

    mesh.compute_vertex_normals()
    mesh_t = o3d.t.geometry.TriangleMesh.from_legacy(mesh)

    _cache_texture(mesh, mesh_path)         # for textured meshes without vertex colours

    raycast = o3d.t.geometry.RaycastingScene()
    raycast.add_triangles(mesh_t)

    # Floor height so the camera sits camera_height ABOVE the floor (not at abs Z).
    aabb = mesh.get_axis_aligned_bounding_box()
    lo, hi = aabb.get_min_bound(), aabb.get_max_bound()
    floor_z = float(lo[2])
    centroid = np.asarray(mesh.get_center())
    n = cfg["trajectories"]["n_frames"]
    ch = cfg["camera"]["camera_height_m"]
    cam_z = floor_z + ch
    print(f"[mesh] post-rotate AABB lo={np.round(lo,2)} hi={np.round(hi,2)}")
    print(f"[mesh] centroid={np.round(centroid,2)} floor_z={floor_z:.2f} "
          f"camera_height={ch} -> cam_z={cam_z:.2f}")
    print(f"[mesh] room extent XYZ = {np.round(hi-lo,2)} m")

    if traj == "synthetic_spline":
        sp = cfg["trajectories"]["synthetic_spline"]
        wps = traj_mod.free_space_waypoints(mesh, n_waypoints=8,
                                            min_clearance_m=sp["min_clearance_m"],
                                            seed=cfg["datasets"]["seed"],
                                            probe_z=cam_z)
        poses = traj_mod.synthetic_spline(wps, n, camera_height=cam_z)
    else:  # dataset_path — loaded by the dataset-specific downloader/importer
        src = _load_dataset_poses(cfg, dataset, scene)
        poses = traj_mod.resample_path(src, n)

    cam_pos = poses[:, :3, 3]
    print(f"[traj] {traj}: {len(poses)} poses  cam_pos "
          f"min={np.round(cam_pos.min(0),2)} max={np.round(cam_pos.max(0),2)}")
    print(f"[traj] first cam pos={np.round(cam_pos[0],2)} mid={np.round(cam_pos[len(cam_pos)//2],2)}")

    # GT lives in the trajectory dir (eval reads .../<dataset>/<scene>/<traj>/).
    out_root = REPO_ROOT / "dataset" / "exports" / dataset / scene / traj
    out_root.mkdir(parents=True, exist_ok=True)

    # GT poses (TUM) + GT mesh copy
    _write_tum(out_root / "poses_gt.tum", poses)
    o3d.io.write_triangle_mesh(str(out_root / "gt_mesh.ply"), mesh)

    # ── PANO ──
    pw, ph = cfg["camera"]["pano"]["width"], cfg["camera"]["pano"]["height"]
    pano_dirs = cameras.equirect_rays_cam(pw, ph)
    pdir = export_dir(dataset, scene, traj, "pano", "")
    (pdir).mkdir(parents=True, exist_ok=True)
    with open(pdir / "intrinsics.json", "w") as f:
        json.dump({"projection": "equirect", "width": pw, "height": ph}, f, indent=2)
    for i, T in enumerate(poses):
        o, d = cameras.rays_to_world(pano_dirs, T)
        radial, rgb, mask = _render_rays(raycast, mesh_t, o, d, pw, ph, cfg["engine"]["max_depth"])
        _save_frame(pdir, i, rgb, radial, mask)
        if i in (0, n // 2, n - 1):
            valid = radial > 0
            drng = (f"{radial[valid].min():.2f}-{radial[valid].max():.2f}m"
                    if valid.any() else "NO HITS")
            print(f"[pano] frame {i}: cam={np.round(T[:3,3],2)} "
                  f"valid={100*valid.mean():.0f}% depth={drng}")

    # ── PINHOLE (both intrinsics variants) ──
    for vname, vcfg in cfg["camera"]["pinhole"]["variants"].items():
        if vcfg.get("use_dataset_k"):
            intr = _dataset_intrinsics(cfg, dataset, scene)
            if intr is None:
                print(f"[render] {dataset}/{scene}: no dataset K for '{vname}', skipping")
                continue
        else:
            intr = cameras.PinholeIntrinsics.from_fov(vcfg["width"], vcfg["height"], vcfg["fov_deg"])
        pin_dirs = cameras.pinhole_rays_cam(intr)
        vdir = export_dir(dataset, scene, traj, "pinhole", vname)
        vdir.mkdir(parents=True, exist_ok=True)
        with open(vdir / "intrinsics.json", "w") as f:
            json.dump(intr.to_json(), f, indent=2)
        for i, T in enumerate(poses):
            o, d = cameras.rays_to_world(pin_dirs, T)
            radial, rgb, mask = _render_rays(raycast, mesh_t, o, d, intr.width, intr.height,
                                             cfg["engine"]["max_depth"])
            optical = cameras.radial_to_optical_z(radial, pin_dirs, intr.width, intr.height)
            _save_frame(vdir, i, rgb, optical, mask)
    print(f"[render] {dataset}/{scene}/{traj}: {len(poses)} frames (pano + pinhole variants)")


def _save_frame(dir_: Path, i: int, rgb: np.ndarray, depth: np.ndarray, mask: np.ndarray):
    import imageio.v2 as imageio
    name = f"{i:06d}"
    (dir_ / "rgb").mkdir(exist_ok=True)
    (dir_ / "depth").mkdir(exist_ok=True)
    (dir_ / "mask").mkdir(exist_ok=True)
    imageio.imwrite(dir_ / "rgb" / f"{name}.png", rgb)
    np.save(dir_ / "depth" / f"{name}.npy", depth.astype(np.float32))
    imageio.imwrite(dir_ / "mask" / f"{name}.png", mask)


def _write_tum(path: Path, poses: np.ndarray):
    """timestamp tx ty tz qx qy qz qw  (timestamp = frame index)."""
    from scipy.spatial.transform import Rotation
    lines = []
    for i, T in enumerate(poses):
        tx, ty, tz = T[0, 3], T[1, 3], T[2, 3]
        qx, qy, qz, qw = Rotation.from_matrix(T[:3, :3]).as_quat()
        lines.append(f"{i} {tx:.6f} {ty:.6f} {tz:.6f} {qx:.6f} {qy:.6f} {qz:.6f} {qw:.6f}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n")


def _load_dataset_poses(cfg: dict, dataset: str, scene: str) -> np.ndarray:
    """Load the dataset's own camera path for variant A.

    Dataset-specific; wired per dataset as importers land. For a first ScanNet++
    room this reads the scene's pose_intrinsic_imu.json / traj file. Until the raw
    data is present this raises with a clear message.
    """
    raise NotImplementedError(
        f"dataset_path poses for {dataset}/{scene} not wired yet — run 'make download' "
        f"and add the per-dataset pose importer (docs/datasets.md). "
        f"Use --traj synthetic_spline to render without dataset poses.")


def _dataset_intrinsics(cfg: dict, dataset: str, scene: str):
    """Real pinhole K for the 'real_intrinsics' variant, or None if unavailable."""
    return None  # wired per dataset alongside _load_dataset_poses


def main():
    ap = common_args("Render pano + pinhole + GT from scene meshes")
    args = ap.parse_args()
    cfg = load_config(args.config)
    for dataset in cfg["datasets"]["active"]:
        scenes = resolve_scenes(cfg, dataset, args.scenes)
        if not scenes:
            print(f"[render] {dataset}: no scenes in config — run 'make download' + make_split")
            continue
        for scene in scenes:
            mesh_path = _find_mesh(cfg, dataset, scene)
            for traj in resolve_trajs(cfg, args.traj):
                render_scene(cfg, dataset, scene, traj, mesh_path)


def _find_mesh(cfg: dict, dataset: str, scene: str) -> Path:
    from bench.config import REPO_ROOT
    dcfg = cfg["datasets"][dataset]
    root = REPO_ROOT / dcfg["root"]
    glob = dcfg.get("mesh_glob", "*.ply").replace("*/", f"{scene}/")
    hits = list(root.glob(glob))
    if not hits:
        raise FileNotFoundError(f"no mesh for {dataset}/{scene} under {root} (glob {glob})")
    return hits[0]


if __name__ == "__main__":
    main()

# Datasets

All raw data is ToU-gated and lives under `dataset/raw/` (gitignored). `make download`
documents each dataset's manual step and stops rather than silently failing.

## ScanNet++ (start here)
Higher-fidelity meshes/textures than plain ScanNet. Sign the ToU at
`kaldir.vc.in.tum.de/scannetpp/`, use the official toolkit + token, and place scenes
under `dataset/raw/scannetpp/<scene_id>/scans/mesh_aligned_0.05.ply`. We render pano +
pinhole from the mesh → perfect GT (poses, geometry, depth). `make_split.py` freezes
one room to start (fixed seed).

*Renderer note:* start with vertex-colour interpolation; switch to texture sampling
(rasterization fallback) if the high-fidelity textures warrant it.

## KITTI-360 (stretch)
Outdoor. Stitch the two fisheye cameras → equirectangular for ours; use the perspective
camera for pinhole baselines; GT poses from GPS/IMU+laser, GT geometry from accumulated
laser. Heaviest to set up — one short sequence only.

## Matterport3D & Stanford2D3D (panorama-native)
Already equirectangular RGB-D with GT geometry/poses — the most natural fit for a
panoramic comparison. Matterport3D needs `download_mp.py` (email for it); Stanford
2D-3D-S needs the request form. For these the pano input is native (no mesh render);
pinhole frames are reprojected from the panorama or taken from their perspective crops.

## Trajectory variants (rendered datasets)
- `dataset_path` — resample the dataset's own camera path (per-dataset pose importer,
  wired as raw data lands; see `render_scene._load_dataset_poses`).
- `synthetic_spline` — collision-free Catmull-Rom walkthrough; waypoints rejection-
  sampled against the mesh with a clearance radius (`min_clearance_m`).

## Caveat carried into every report
Rendered frames are noise/artifact-free (no motion blur, no exposure shift, no lens
damage) → an **optimistic upper bound**. Real-sensor behaviour differs; state it.

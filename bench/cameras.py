"""Camera models + ray generation for the renderer.

Both camera models cast rays into the SAME Open3D RaycastingScene from the SAME
world poses, so the only difference between a pano and a pinhole frame is the ray
set — this keeps the fairness argument ("any metric gap is method, not data")
true at the renderer level.

Conventions (matches PRISM-VGGT):
  * world: right-handed, Z-up.
  * camera-to-world pose T_wc (4x4). Camera looks down +Z_cam, +X right, +Y down
    (OpenCV convention, as PRISM's metrification expects Y-down lower hemisphere).
  * pinhole depth: optical Z (metres). pano depth: radial distance (metres).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class PinholeIntrinsics:
    width: int
    height: int
    fx: float
    fy: float
    cx: float
    cy: float

    @classmethod
    def from_fov(cls, width: int, height: int, fov_deg: float) -> "PinholeIntrinsics":
        f = (width / 2.0) / np.tan(np.deg2rad(fov_deg) / 2.0)
        return cls(width, height, f, f, (width - 1) / 2.0, (height - 1) / 2.0)

    def K(self) -> np.ndarray:
        return np.array([[self.fx, 0, self.cx],
                         [0, self.fy, self.cy],
                         [0, 0, 1]], dtype=np.float64)

    def to_json(self) -> dict:
        return {"projection": "pinhole", "width": self.width, "height": self.height,
                "fx": self.fx, "fy": self.fy, "cx": self.cx, "cy": self.cy}


def pinhole_rays_cam(intr: PinholeIntrinsics) -> np.ndarray:
    """(H*W, 3) unit-ish ray directions in camera frame (not normalised: z=1 plane)."""
    u, v = np.meshgrid(np.arange(intr.width), np.arange(intr.height))
    x = (u - intr.cx) / intr.fx
    y = (v - intr.cy) / intr.fy
    z = np.ones_like(x)
    d = np.stack([x, y, z], axis=-1).reshape(-1, 3)
    return d / np.linalg.norm(d, axis=1, keepdims=True)


def equirect_rays_cam(width: int, height: int) -> np.ndarray:
    """(H*W, 3) unit ray directions for an equirectangular panorama.

    Longitude phi in [-pi, pi] across width; latitude theta in [-pi/2, pi/2] across
    height (top row = +pi/2). Y-down camera convention.
    """
    lon = (np.arange(width) + 0.5) / width * 2 * np.pi - np.pi          # [-pi, pi)
    lat = np.pi / 2 - (np.arange(height) + 0.5) / height * np.pi        # +pi/2 .. -pi/2
    lon, lat = np.meshgrid(lon, lat)
    cos_lat = np.cos(lat)
    x = cos_lat * np.sin(lon)
    y = -np.sin(lat)            # Y-down
    z = cos_lat * np.cos(lon)
    d = np.stack([x, y, z], axis=-1).reshape(-1, 3)
    return d / np.linalg.norm(d, axis=1, keepdims=True)


def rays_to_world(dirs_cam: np.ndarray, T_wc: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Return (origins[N,3], directions[N,3]) in world frame for a camera pose."""
    R = T_wc[:3, :3]
    t = T_wc[:3, 3]
    dirs_w = dirs_cam @ R.T
    origins = np.broadcast_to(t, dirs_w.shape).copy()
    return origins.astype(np.float32), dirs_w.astype(np.float32)


def radial_to_optical_z(radial: np.ndarray, dirs_cam: np.ndarray, width: int, height: int) -> np.ndarray:
    """Convert per-ray radial distance to optical Z-depth for a pinhole image."""
    z_component = dirs_cam[:, 2].reshape(height, width)
    return radial * z_component

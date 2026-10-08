#!/usr/bin/env python
"""Fetch ONLY the Replica scenes the benchmark uses — streamed, nothing big on disk.

Replica v1 ships as ONE tar.gz split into 17 x 2 GB parts on GitHub releases. A gzip
stream can only be decoded from its start, so no single scene can be fetched on its
own. This script streams the parts in order straight through gunzip + tar (no part is
ever written to disk) and keeps only <scene>/mesh.ply for the requested scenes — the
only file the renderer reads (vertex-coloured mesh). It stops as soon as every
requested mesh has been seen, so it downloads less when they come early in the archive.

    python dataset/fetch_replica.py                         # scenes from config.yaml
    python dataset/fetch_replica.py --scenes "room_0 office_0"
    python dataset/fetch_replica.py --list 40               # print the first 40 members

Disk: ~0.3-1 GB per scene instead of ~34 GB of parts + the full extracted dataset.
Bandwidth: up to the full ~34 GB. A dropped connection resumes the current part with
an HTTP Range request; a killed process restarts from part aa (meshes already written
are skipped).
"""
from __future__ import annotations

import argparse
import io
import os
import sys
import tarfile
import time
import urllib.request
from pathlib import Path

BASE = "https://github.com/facebookresearch/Replica-Dataset/releases/download/v1.0/"
PARTS = [f"replica_v1_0.tar.gz.parta{c}" for c in "abcdefghijklmnopq"]


class PartStream(io.RawIOBase):
    """The 17 parts as one sequential byte stream, with Range-resume on errors."""

    def __init__(self):
        self.i, self.off, self.resp, self.total = 0, 0, None, 0
        self.t0 = self.tlast = time.time()

    def _open(self):
        req = urllib.request.Request(BASE + PARTS[self.i])
        if self.off:
            req.add_header("Range", f"bytes={self.off}-")
        self.resp = urllib.request.urlopen(req, timeout=60)

    def readable(self):
        return True

    def readinto(self, b):
        tries = 0
        while self.i < len(PARTS):
            try:
                if self.resp is None:
                    self._open()
                n = self.resp.readinto(b)
            except Exception as e:                       # network hiccup -> resume
                tries += 1
                if tries > 8:
                    raise
                print(f"\n   ! {PARTS[self.i]} @ {self.off >> 20} MB: {e} — retry {tries}/8", flush=True)
                self.resp = None
                time.sleep(min(60, 5 * tries))
                continue
            if n:
                self.off += n
                self.total += n
                now = time.time()
                if now - self.tlast > 5:
                    rate = self.total / max(1e-6, now - self.t0) / 2**20
                    print(f"\r   part {self.i + 1}/17  {self.total / 2**30:5.1f} GB read  "
                          f"{rate:5.1f} MB/s", end="", flush=True)
                    self.tlast = now
                return n
            self.resp, self.i, self.off = None, self.i + 1, 0   # part finished
        return 0


def _scene_of(name: str):
    """'./room_0/mesh.ply' -> 'room_0' (only the top-level mesh.ply of a scene)."""
    p = [x for x in name.split("/") if x not in ("", ".")]
    if len(p) >= 2 and p[-1] == "mesh.ply":
        return p[-2] if len(p) == 2 or p[-3] in ("replica_v1", "Replica", "replica") else None
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="dataset/raw/replica")
    ap.add_argument("--scenes", default=None, help="space-separated; default config.yaml "
                    "datasets.replica.download_scenes")
    ap.add_argument("--list", type=int, default=0, help="print the first N members and exit")
    a = ap.parse_args()

    out = Path(a.out)
    if a.scenes:
        want = set(a.scenes.split())
    else:
        sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
        from bench.config import load_config
        want = set(load_config("config.yaml")["datasets"]["replica"].get("download_scenes") or [])
    if not want and not a.list:
        print("!! no scenes requested"); return 1
    todo = {s for s in want if not (out / s / "mesh.ply").exists()}
    if not todo and not a.list:
        print(f">> Replica: all {len(want)} scene meshes already in {out}"); return 0
    if not a.list:
        print(f">> Replica: streaming the archive, keeping mesh.ply for {sorted(todo)}")

    stream = io.BufferedReader(PartStream(), buffer_size=8 << 20)
    seen = 0
    with tarfile.open(fileobj=stream, mode="r|gz") as tf:
        for m in tf:
            seen += 1
            if a.list:
                print(f"{m.size >> 20:8d} MB  {m.name}")
                if seen >= a.list:
                    return 0
                continue
            sc = _scene_of(m.name)
            if sc not in todo or not m.isfile():
                continue
            dst = out / sc / "mesh.ply"
            dst.parent.mkdir(parents=True, exist_ok=True)
            tmp = dst.with_suffix(".ply.part")
            with tf.extractfile(m) as src, open(tmp, "wb") as f:
                while chunk := src.read(8 << 20):
                    f.write(chunk)
            os.replace(tmp, dst)
            todo.discard(sc)
            print(f"\n   + {sc}/mesh.ply ({m.size / 2**20:.0f} MB) — {len(todo)} to go", flush=True)
            if not todo:
                break
    if todo:
        print(f"\n!! archive ended without: {sorted(todo)} (check the scene names)"); return 1
    print(f"\n>> Replica: done, {len(want)} scene meshes in {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

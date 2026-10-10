"""Make torch.hub work without GitHub once a hub repo is cached (harness-level patch).

VGGT-SLAM's loop-closure model (SALAD) calls torch.hub.load('facebookresearch/dinov2', ...)
at start-up. With no branch given, torch.hub first asks github.com whether the repo has
a `main` branch — on every run, even when the code is already cached. A GitHub 504 on
2026-10-10 failed 3 VGGT-SLAM runs (both attempts) this way. If that lookup fails and the
repo is cached under the hub dir, use the cached `main` instead. Nothing changes when
GitHub answers, and the method's code is untouched. Injected only into VGGT-SLAM's
subprocess via PYTHONPATH (adapters/runners/vggtslam_runner.py).
"""
try:
    import os
    import torch.hub as _hub

    _orig = _hub._parse_repo_info

    def _parse_repo_info(github):
        try:
            return _orig(github)
        except Exception as e:  # noqa: BLE001  (URLError / HTTPError / timeout)
            owner_name = github.split(":")[0]
            owner, name = owner_name.split("/")
            cached = os.path.join(_hub.get_dir(), f"{owner}_{name}_main")
            if os.path.isdir(cached):
                print(f"[hubpatch] github lookup for {owner_name} failed ({e.__class__.__name__}); "
                      f"using the cached main branch at {cached}")
                return owner, name, "main"
            raise

    _hub._parse_repo_info = _parse_repo_info
except Exception:  # torch not importable here: nothing to patch
    pass

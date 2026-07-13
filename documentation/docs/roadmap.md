# Roadmap

## Now — first small run
- [x] Orchestrator scaffold: Makefile, config, envs, dataset, adapters, eval, docs.
- [ ] `make init` + `make setup-all` on the 6000 box (clone + isolated envs).
- [ ] ScanNet++ ToU + one room; `make render` (synthetic_spline first — no dataset poses needed).
- [ ] `run-prism` end-to-end; confirm PRISM outputs → perf/recon/metric tables.
- [ ] Confirm the baseline runner API seams (marked `<-- API line N`) against the
      pinned commits for Pi3, VGGT-SLAM; then `run-pi3`, `run-vggtslam`.

## Next
- [ ] `dataset_path` pose importer per dataset (variant A) + `real_intrinsics` K loader.
- [ ] MapAnything + LASER runners wired and validated.
- [ ] Matterport3D + Stanford2D3D (panorama-native) importers.
- [ ] KITTI-360 fisheye→equirect stitcher (stretch, one sequence).

## Later (for publication, not preliminary)
- [ ] More scenes; seeds + variance study (drop the "preliminary" label).
- [ ] Proper occupancy/ESDF free-space sampler for synthetic trajectories.
- [ ] Loop-closure comparison once PRISM grows a working panoramic loop closure.

## Known seams to confirm post-clone
Baseline runners import each method with the exact API marked by `<-- API line N`
comments. These are best-effort against the pinned commits and must be verified once
the repos are cloned (`make init`). PRISM's runner uses the verified public API and
needs no confirmation.

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

## Runner API status
- **PRISM** — verified public API. ✅
- **Pi3** — verified against the pinned commit's README (`Pi3.from_pretrained("yyfz233/Pi3")`,
  `model(imgs[None])`, outputs `camera_poses`/`points`). ✅
- **VGGT-SLAM, MapAnything, LASER** — runner seams still marked `<-- API line N`;
  confirm against each repo after `make init` before running.

## First comparison
PRISM (pano) vs. Pi3 (pinhole) on Replica `office_4`. See **Preliminary results** for
PRISM's numbers; run `make run-pi3` then re-eval to populate the baseline row. Recon is
compared in the **masked** (co-visibility) table for fairness; PRISM additionally gets
the full-360 credit.

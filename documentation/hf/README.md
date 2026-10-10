---
license: other
license_name: replica-dataset-research-terms
license_link: https://github.com/facebookresearch/Replica-Dataset/blob/main/LICENSE
pretty_name: PRISM-benchmarks inputs and results
tags:
  - 3d-reconstruction
  - slam
  - panoramic
  - replica
extra_gated_prompt: >-
  These files are renderings of (and, in the results packs, copies of meshes from) the
  Replica Dataset by Meta Reality Labs. Replica may be used, modified and published only
  for non-commercial research or educational purposes, and may be shared only with people
  who first agree to its terms
  (https://github.com/facebookresearch/Replica-Dataset/blob/main/LICENSE).
  By requesting access you agree to be bound by those terms.
extra_gated_fields:
  Name: text
  Affiliation: text
  I agree to the Replica Dataset Research Terms and will use this data only for non-commercial research or education: checkbox
---

# PRISM-benchmarks — inputs and results

Rendered inputs, raw method outputs and evaluation packs for the PRISM-VGGT streaming
panoramic mapping benchmark (code: https://github.com/zRafaF/PRISM-benchmarks). Published
so every number in the paper can be traced back to the exact frames and runs.

## Layout
- `inputs/<tag>/` — one tar per scene (RGB + masks + GT poses + adapter metadata; no
  depth, no meshes) plus `MANIFEST.json` (code commit and render-config fingerprint) and
  the frozen scene list. `rerun-v3` is the paper's matrix; `pilot-v3` the rate / window
  study; older tags are kept for traceability and are superseded (see the repo's
  `RESULTS_CHANGELOG.md`).
- `results/<tag>/` — per-pod packs: every run's poses, cloud, timing and logs, plus the
  scoring inputs (GT poses, pinhole depth, one GT mesh per scene). `live/` holds the
  in-progress checkpoints of a running pod.

## How the data were made
Replica meshes (6 scenes) are levelled and rendered on collision-free camera walks
planned on each scene's walkable free space, as an equirectangular panorama, a 90 deg
pinhole and 4-face cube views per timestep. Everything is regenerated from the code at
the commit in each `MANIFEST.json` (`make inputs`); see `documentation/docs/decisions.md`.

## Terms
Derived from the Replica Dataset (Straub et al., 2019) under the Replica Dataset Research
Terms: non-commercial research or education only; access requires agreeing to those
terms. Cite Replica and the PRISM-VGGT paper when using the data.

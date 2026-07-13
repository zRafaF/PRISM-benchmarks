# PRISM-benchmarks

A **neutral referee** that fairly compares PRISM-VGGT against streaming baselines on
a self-rendered dataset and produces one clear preliminary results report.

## The two-level picture

1. **PRISM-VGGT self-contained benchmarks** live *inside* the PRISM repo
   (`PRISM-VGGT/benchmarks/`), depend on nothing else, and cover PRISM-only
   sanity/perf. Not this repo's job.
2. **This orchestrator** is a separate project that pulls each method in as a git
   submodule, sets up an isolated env per submodule, owns the shared dataset
   rendering + fair-comparison masking + eval + perf collection + the final report,
   and runs each method as a subprocess *in that method's own env*. No method's
   dependencies leak into the eval layer.

## Guiding rules

- **Streaming only.** We test streaming performance; full-batch runs (which would
  only benchmark the underlying feed-forward net) are excluded.
- **Re-run, don't cite.** Baselines are re-run on our exact rendered frames on the
  same hardware (RTX PRO 6000); published numbers are on different data/sensors/GPUs.
- **Isolation.** Submodule + own env per method; the eval layer imports no method.
- **No training / no fine-tuning.** Frozen checkpoints only.
- **Everything preliminary.** Few scenes, fixed seed, no variance study yet. Rendered
  frames are noise-free → an optimistic upper bound.

See **Architecture** for the layout and **Design decisions** for why each choice was made.

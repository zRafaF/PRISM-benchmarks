# Running on a GPU pod (rerun-v3)

The complete run-book is in the top-level `README.md` (render on the PC, one pod runs
everything, score on the PC). Decisions behind the protocol: `decisions.md`; results
for the paper: `paper_findings.md`.

## Order of a run
1. PC: `make inputs && make inputs-push` (resumes per camera; only missing renders).
2. Pod (inside `tmux`): `make sanity-tum` once per environment (VGGT-SLAM on TUM, D29),
   then `make pod` (prep -> env check -> data -> precheck -> bench -> pack -> HF).
3. PC: `make results-fetch results-merge eval-all publication`.

## Working conventions (from the rerun-v2/v3 sessions)
- Run long jobs inside `tmux` — an SSH drop kills anything started in the plain shell.
- Iterate on 1-2 sequences, not the matrix:
  `PRISM_FORCE=1 uv run python adapters/run.py --method <m> --config config.yaml --scenes <scene> --traj <traj>`,
  then `make diag SCENE=<scene> TRAJ=<traj>` and `make lost`.
- `make precheck` gates the long run. `PRECHECK_MAX_ATE_M` defaults to 0.5 m; the
  rerun-v2 run used 3 because VGGT-SLAM exceeded it.
- Never run two GPU jobs at once on the pod (timings). `make watch` is read-only.
- Don't `git pull` on the pod while `pod.sh` / `run_overnight.sh` is executing (bash
  reads scripts incrementally); Python files are safe. Pulling a change to the render
  config also makes the pod refuse inputs rendered before it (input fingerprint check).
- `make -n` executes recipe lines containing `$(MAKE)` — it once started a 34 GB download.
- A finished pod's `logs/.done_<stage>` flags make `make pod` skip stages; to fetch new
  inputs on the same pod run `bash scripts/inputs.sh fetch` by hand.

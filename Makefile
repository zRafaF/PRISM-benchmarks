# ============================================================================
# PRISM-benchmarks — central control file (the orchestrator)
# ============================================================================
# The Makefile IS the orchestrator: it sets up each method's isolated env,
# renders the shared dataset, runs every method in its own env as a subprocess,
# evaluates the common outputs, and aggregates the final report.
#
# Public config lives in bench.env (safe to commit) + config.yaml (run params).
#
#   make help    → targets + the end-to-end pipeline order
#   make steps   → the full run-book, stage by stage
# ============================================================================

include bench.env
export                          # export every bench.env var to recipe shells

# Each method runs in its OWN isolated env (submodules/<m>/.venv). The eval layer
# runs in the orchestrator's own light env (./.venv) and imports NO method.
ORCH_RUN ?= uv run python
PYCHK    ?= python3

.DEFAULT_GOAL := help

.PHONY: help steps \
        deps init setup setup-all setup-prism setup-pi3 setup-vggtslam setup-mapanything setup-laser \
        download split render export \
        run-all run-prism run-panovggt run-pi3 run-vggtslam run-mapanything run-laser ablations ablations-align \
        eval-traj eval-recon eval-metric perf report all bench-overnight \
        fig-vram fig-vram-sweep fig-cubemap fig-cubemap-export fig-cubemap-engine figures \
        studio preview snapshots docs docs-serve clean clean-results

# ── Help / run-book ───────────────────────────────────────────────────────────
help:
	@echo "PRISM-benchmarks   hw=$(HW_ID)   config=$(CONFIG)"
	@echo ""
	@echo "Setup:"
	@echo "  make deps             system pkgs (wget/pigz/unzip/tmux); APT_SUDO=sudo if not root"
	@echo "  make init             clone + pin every method submodule (see bench.env)"
	@echo "  make setup            orchestrator env (uv sync) — render+mask+eval+report"
	@echo "  make setup-all        every method's ISOLATED env (delegates to each repo)"
	@echo "  make setup-<m>        one method: prism|pi3|vggtslam|mapanything|laser"
	@echo ""
	@echo "Dataset (shared, rendered in the orchestrator env):"
	@echo "  make download         print how to fetch active datasets (ToU/prereqs noted)"
	@echo "  make split            freeze the scene list into config.yaml (fixed seed)"
	@echo "  make render           render pano+pinhole+GT for SCENES/TRAJ (both variants)"
	@echo "  make export           emit per-method adapter inputs (the adapter contract)"
	@echo ""
	@echo "Run (each method in its OWN env, streaming harness):"
	@echo "  make run-all          run every configured method -> common results layout"
	@echo "  make run-<m>          one method: prism|panovggt|pi3|vggtslam|mapanything|laser"
	@echo "  make ablations        PRISM ablations: guards (nolock/nostill/noguards) + align (se3/sl4)"
	@echo "  make ablations-align  alignment-group study only: SE(3)+SL(4) vs Sim(3)=prism"
	@echo ""
	@echo "Evaluate (orchestrator env; reads only results/, imports no method):"
	@echo "  make eval-traj        evo ATE/RPE (Sim(3) align)          -> ate.json"
	@echo "  make eval-recon       masked + full-360 recon metrics     -> recon.json"
	@echo "  make eval-metric      OUR absolute-scale accuracy (metric methods) -> metric.json"
	@echo "  make perf             throughput/latency + avg & peak VRAM + GPU util -> perf.csv"
	@echo "  make report           aggregate everything -> tables + plots (md/csv/png)"
	@echo "  make studio           Studio: browser control panel — ONE-BUTTON pipeline + config + snapshots + viewers"
	@echo "  make snapshots        standardized paper images of every cloud (GT-aligned, ceiling-clipped)"
	@echo ""
	@echo "Report figures (-> results/figures/, downloadable in Studio):"
	@echo "  make figures          both report figures (vram_vs_frames.png + cubemap_projection.png)"
	@echo "  make fig-vram         VRAM-vs-frames from committed seeded perf.csv (no GPU) -> png + csv"
	@echo "  make fig-vram-sweep   on-GPU prefix sweep to real OOM caps (needs exports + method envs)"
	@echo "  make fig-cubemap      cubemap projection figure — SCHEMATIC preview (no data)"
	@echo "  make fig-cubemap-export  REAL cubemap figure from the dataset export (needs render+export, no GPU)"
	@echo "  make fig-cubemap-engine  cubemap figure from the engine's own reprojection (needs PRISM env)"
	@echo ""
	@echo "  make all              init -> setup-all -> download -> render -> export ->"
	@echo "                        run-all -> eval-* -> perf -> report"
	@echo ""
	@echo "Docs:  make docs | make docs-serve      Housekeeping: make clean | make clean-results"
	@echo ""
	@echo "Vars:  SCENES='$(SCENES)' TRAJ=$(TRAJ) WINDOW=$(WINDOW) OVERLAP=$(OVERLAP)"
	@echo "       VOXEL=$(VOXEL) MAX_DEPTH=$(MAX_DEPTH) FACE_SIZE=$(FACE_SIZE) DEVICE=$(DEVICE)"

steps:
	@echo "PRISM-benchmarks — end-to-end run-book (hw=$(HW_ID))"
	@echo ""
	@echo "Stage 0  One-time setup"
	@echo "  make init            # clone + checkout the pinned commit of every method"
	@echo "  make setup           # orchestrator env"
	@echo "  make setup-all       # each method's isolated env (heavy: VGGT-SLAM = GTSAM+SL4+DINO-SALAD)"
	@echo ""
	@echo "Stage 1  Dataset (shared)"
	@echo "  make download        # prints per-dataset fetch + prereqs (Replica needs wget pigz unzip)"
	@echo "  make split           # freeze the scene list (fixed seed) into config.yaml"
	@echo "  make render          # pano + pinhole(synthetic_fov & real_intrinsics) + GT poses.tum"
	@echo "  make export          # per-method input sequences in the adapter format"
	@echo ""
	@echo "Stage 2  Run (streaming harness; each method in its own env)"
	@echo "  make run-prism       # ours (pano)          -> results/prism/..."
	@echo "  make run-pi3         # baseline (pinhole)   -> results/pi3/..."
	@echo "  make run-vggtslam    # baseline (pinhole)   -> results/vggtslam/..."
	@echo "  make run-mapanything # optional (pinhole)"
	@echo "  make run-laser       # optional (pano)"
	@echo ""
	@echo "Stage 3  Evaluate + report (orchestrator env)"
	@echo "  make eval-traj eval-recon eval-metric perf"
	@echo "  make report          # preliminary tables A/B/C/C2 + plots"

# ── Stage 0: setup ────────────────────────────────────────────────────────────
# System packages (run once, as root): Replica downloader (wget/pigz/unzip) + the
# overnight-benchmark session manager (tmux). APT_SUDO=sudo if not already root.
APT_SUDO ?=
deps:
	@echo ">> installing system packages: wget pigz unzip tmux"
	$(APT_SUDO) apt-get update && $(APT_SUDO) apt-get install -y wget pigz unzip tmux

init:
	@echo ">> cloning + pinning method submodules"
	bash scripts/add_submodules.sh

setup:
	@echo ">> orchestrator env (light: open3d/evo/pynvml/matplotlib — NO torch)"
	$(UV) sync

setup-prism:
	bash envs/setup_prism.sh
setup-pi3:
	bash envs/setup_pi3.sh
setup-vggtslam:
	bash envs/setup_vggtslam.sh
setup-mapanything:
	bash envs/setup_mapanything.sh
setup-laser:
	bash envs/setup_laser.sh
setup-all: setup-prism setup-pi3 setup-vggtslam setup-mapanything setup-laser
	@echo ">> all method envs set up"

# ── Stage 1: dataset (orchestrator env) ───────────────────────────────────────
download: setup
	@echo ">> downloading active datasets (see config.yaml datasets.active)"
	$(ORCH_RUN) dataset/download.py --config $(CONFIG)

split: setup
	@echo ">> freezing scene list into config.yaml (fixed seed)"
	$(ORCH_RUN) dataset/make_split.py --config $(CONFIG)

render: setup
	@echo ">> rendering pano + pinhole + GT (SCENES='$(SCENES)' TRAJ=$(TRAJ))"
	$(ORCH_RUN) dataset/render_scene.py --config $(CONFIG) --scenes "$(SCENES)" --traj $(TRAJ)

export: setup
	@echo ">> exporting per-method adapter inputs"
	$(ORCH_RUN) dataset/export_inputs.py --config $(CONFIG) --scenes "$(SCENES)" --traj $(TRAJ)

# ── Stage 2: run each method in its OWN env (adapters shell out) ───────────────
run-prism:
	$(ORCH_RUN) adapters/prism.py       --config $(CONFIG) --scenes "$(SCENES)" --traj $(TRAJ)
run-panovggt:
	$(ORCH_RUN) adapters/panovggt.py    --config $(CONFIG) --scenes "$(SCENES)" --traj $(TRAJ)
run-pi3:
	$(ORCH_RUN) adapters/pi3.py         --config $(CONFIG) --scenes "$(SCENES)" --traj $(TRAJ)
run-vggtslam:
	$(ORCH_RUN) adapters/vggtslam.py    --config $(CONFIG) --scenes "$(SCENES)" --traj $(TRAJ)
run-mapanything:
	$(ORCH_RUN) adapters/mapanything.py --config $(CONFIG) --scenes "$(SCENES)" --traj $(TRAJ)
run-laser:
	$(ORCH_RUN) adapters/laser.py       --config $(CONFIG) --scenes "$(SCENES)" --traj $(TRAJ)
run-all: run-prism run-panovggt run-pi3 run-vggtslam run-mapanything run-laser
	@echo ">> all configured methods run"

# PRISM ablations — guard-contribution study + alignment-group study (sim3/se3/sl4).
# ALIGN=1 runs only the alignment arms; GUARDS=1 runs only the guard arms; default = all.
ABL_GUARDS ?= prism_nolock prism_nostill prism_noguards
ABL_ALIGN  ?= prism_sim3 prism_se3
ablations: setup
	@echo ">> running PRISM ablations (config.ablations)"
	@for a in $(ABL_GUARDS) $(ABL_ALIGN); do \
	  $(ORCH_RUN) adapters/run.py --method $$a --config $(CONFIG) --scenes "$(SCENES)" --traj $(TRAJ) || exit 1; \
	done

# Just the alignment-group study (sim3 is the plain `prism` run; add se3 + sl4).
ablations-align: setup
	@echo ">> alignment-group study: SE(3) + SL(4) arms (sim3 = the plain prism run)"
	@for a in $(ABL_ALIGN); do \
	  $(ORCH_RUN) adapters/run.py --method $$a --config $(CONFIG) --scenes "$(SCENES)" --traj $(TRAJ) || exit 1; \
	done

# ── Stage 3: evaluate + report (orchestrator env; imports NO method) ───────────
eval-traj: setup
	$(ORCH_RUN) eval/eval_traj.py    --config $(CONFIG)
eval-recon: setup
	$(ORCH_RUN) eval/eval_recon.py   --config $(CONFIG)
eval-metric: setup
	$(ORCH_RUN) eval/metric_accuracy.py --config $(CONFIG)
perf: setup
	$(ORCH_RUN) eval/collect_perf.py --config $(CONFIG)
report: setup
	$(ORCH_RUN) eval/make_report.py  --config $(CONFIG)

all: init setup-all download render export run-all eval-traj eval-recon eval-metric perf report
	@echo ">> full pipeline complete — see results/report/"

# ── Report figures (Deliverables 1 & 2) -> results/figures/ ────────────────────
# fig-vram is reproducible from the committed seeded perf.csv (no GPU). fig-vram-sweep
# and fig-cubemap-export need the reference GPU + method envs/exports. FIG_SCENE /
# FIG_TRAJ / FIG_FRAMES override the defaults (see eval/vram_scaling.py, eval/fig_cubemap.py).
FIG_SCENE  ?= auto
FIG_TRAJ   ?= synthetic_2.0hz_s0
FIG_FRAME  ?= 0                     # which pano frame the cubemap figure uses
FIG_FRAMES ?= 1,2,4,8,16,32,64,128,256
FIG_TILE   ?=                       # set FIG_TILE=1 to loop the sequence past its render length
fig-vram: setup
	@echo ">> VRAM-vs-frames from committed seeded perf.csv -> results/figures/"
	$(ORCH_RUN) eval/vram_scaling.py --source perf-csv --config $(CONFIG) --scene "$(FIG_SCENE)"
fig-vram-sweep: setup
	@echo ">> on-GPU prefix VRAM sweep (real OOM caps) -> results/figures/"
	$(ORCH_RUN) eval/vram_scaling.py --source sweep --config $(CONFIG) \
	  --scene "$(FIG_SCENE)" --traj "$(FIG_TRAJ)" --frames "$(FIG_FRAMES)" --logx \
	  $(if $(FIG_TILE),--tile,)
fig-cubemap: setup
	@echo ">> cubemap projection figure (SCHEMATIC preview, no data) -> results/figures/"
	$(ORCH_RUN) eval/fig_cubemap.py --mode illustrative --config $(CONFIG)
fig-cubemap-export: setup
	@echo ">> cubemap projection figure from the REAL dataset export -> results/figures/"
	$(ORCH_RUN) eval/fig_cubemap.py --mode dataset --config $(CONFIG) \
	  --scene "$(FIG_SCENE)" --traj "$(FIG_TRAJ)" --frame "$(FIG_FRAME)"
fig-cubemap-engine: setup
	@echo ">> cubemap projection figure from the ENGINE's own reprojection -> results/figures/"
	$(ORCH_RUN) eval/fig_cubemap.py --mode export --config $(CONFIG) \
	  --scene "$(FIG_SCENE)" --traj "$(FIG_TRAJ)" --frame "$(FIG_FRAME)"
figures: fig-vram fig-cubemap
	@echo ">> report figures in results/figures/ (vram_vs_frames.png + cubemap_projection.png)"

# ── Overnight big benchmark (SSH-proof, resumable, priority-ordered) ──────────
# Runs the whole matrix in a detached tmux session so it survives disconnect.
# Reattach: tmux attach -t bench   |   Monitor: tail -f logs/overnight_latest.log
bench-overnight:
	@command -v tmux >/dev/null 2>&1 || { echo "tmux not found: run 'nohup bash scripts/run_overnight.sh &' instead"; exit 1; }
	tmux new -d -s bench 'bash scripts/run_overnight.sh'
	@echo ">> launched in tmux session 'bench'."
	@echo "   reattach: tmux attach -t bench"
	@echo "   monitor : tail -f logs/overnight_latest.log"

# ── Studio (browser control panel: run pipeline, config, snapshots, viewers) ──
studio: setup
	@echo ">> Studio on :7860 (share URL printed): one-button pipeline + config + snapshots + viewers."
	$(UV) run --extra preview python tools/studio.py
preview: studio          # backwards-compatible alias for the old name

# ── Standardized paper snapshots (GT-aligned, ceiling-clipped, black+white bg) ─
snapshots: setup
	@echo ">> rendering standardized cloud snapshots -> results/report/snapshots/"
	$(ORCH_RUN) eval/snapshots.py --config $(CONFIG) \
	  --methods "$(SNAP_METHODS)" --scenes "$(SNAP_SCENES)" --traj "$(SNAP_TRAJ)"

# ── Docs ──────────────────────────────────────────────────────────────────────
docs:
	$(UV) run --extra docs mkdocs build -f documentation/mkdocs.yml
docs-serve:
	$(UV) run --extra docs mkdocs serve -f documentation/mkdocs.yml

# ── Housekeeping ────────────────────────────────────────────────────────────────
clean:
	@find . -name __pycache__ -type d -not -path './submodules/*' -exec rm -rf {} + 2>/dev/null || true
	@echo "cleaned __pycache__"
clean-results:
	@rm -rf results/* && echo "cleared results/"

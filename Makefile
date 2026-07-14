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
        init setup setup-all setup-prism setup-pi3 setup-vggtslam setup-mapanything setup-laser \
        download split render export \
        run-all run-prism run-pi3 run-vggtslam run-mapanything run-laser \
        eval-traj eval-recon eval-metric perf report all \
        preview docs docs-serve clean clean-results

# ── Help / run-book ───────────────────────────────────────────────────────────
help:
	@echo "PRISM-benchmarks   hw=$(HW_ID)   config=$(CONFIG)"
	@echo ""
	@echo "Setup:"
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
	@echo "  make run-<m>          one method: prism|pi3|vggtslam|mapanything|laser"
	@echo ""
	@echo "Evaluate (orchestrator env; reads only results/, imports no method):"
	@echo "  make eval-traj        evo ATE/RPE (Sim(3) align)          -> ate.json"
	@echo "  make eval-recon       masked + full-360 recon metrics     -> recon.json"
	@echo "  make eval-metric      OUR absolute-scale accuracy (metric methods) -> metric.json"
	@echo "  make perf             throughput/latency + avg & peak VRAM + GPU util -> perf.csv"
	@echo "  make report           aggregate everything -> tables + plots (md/csv/png)"
	@echo "  make preview          browser gallery of rendered frames + file downloader"
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
run-pi3:
	$(ORCH_RUN) adapters/pi3.py         --config $(CONFIG) --scenes "$(SCENES)" --traj $(TRAJ)
run-vggtslam:
	$(ORCH_RUN) adapters/vggtslam.py    --config $(CONFIG) --scenes "$(SCENES)" --traj $(TRAJ)
run-mapanything:
	$(ORCH_RUN) adapters/mapanything.py --config $(CONFIG) --scenes "$(SCENES)" --traj $(TRAJ)
run-laser:
	$(ORCH_RUN) adapters/laser.py       --config $(CONFIG) --scenes "$(SCENES)" --traj $(TRAJ)
run-all: run-prism run-pi3 run-vggtslam run-mapanything run-laser
	@echo ">> all configured methods run"

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

# ── Preview (browser gallery + downloader; prints a public share URL) ─────────
preview: setup
	@echo ">> preview server on :7860 (share URL printed). Browse renders + download."
	$(UV) run --extra preview python tools/preview.py

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

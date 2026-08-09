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
        bench-status bench-stop \
        ingest-archive report-clean aggregate-clean report-tables verify-clean \
        smoke smoke-check bundle bundle-estimate capacity-sweep \
        run-vggtslam-arms ablations-vggtslam \
        fig-vram fig-vram-sweep fig-cubemap fig-cubemap-export fig-cubemap-engine \
        fig-fusion fig-fusion-results figures \
        studio preview snapshots docs docs-serve clean clean-results publication

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
	@echo "  make ablations        PRISM ablations: guards (nolock/nostill/noguards) + align (sl4/se3)"
	@echo "  make ablations-align  alignment-group study only: SL(4)+SE(3) vs Sim(3)=prism"
	@echo ""
	@echo "Evaluate (orchestrator env; reads only results/, imports no method):"
	@echo "  make eval-traj        evo ATE/RPE (Sim(3) align)          -> ate.json"
	@echo "  make eval-recon       masked + full-360 recon metrics     -> recon.json"
	@echo "  make eval-metric      OUR absolute-scale accuracy (metric methods) -> metric.json"
	@echo "  make perf             throughput/latency + avg & peak VRAM + GPU util -> perf.csv"
	@echo "  make report           aggregate everything -> tables + plots (md/csv/png)"
	@echo ""
	@echo "Publication-grade aggregation (seeded-only; excludes contaminated runs):"
	@echo "  make report-clean     CLEAN seeded-only aggregate -> results/report_clean/"
	@echo "  make report-tables    report-facing CSV/JSON/md bundle for uofa-2026-report"
	@echo "  make verify-clean     assert no contaminated run leaked into the clean output"
	@echo "  make ingest-archive   archived big-run snapshot -> tidy per-run records"
	@echo "  make publication      report-clean + report-tables + verify-clean"
	@echo ""
	@echo "Before the long run:"
	@echo "  make smoke            TEST RUN: whole pipeline on a tiny matrix + ETA for the full run"
	@echo "  make smoke-check      re-validate the last smoke run without re-running it"
	@echo ""
	@echo "The long run (multi-hour; detached, survives SSH logout):"
	@echo "  make bench-overnight  launch the full matrix in the background"
	@echo "  make bench-status     progress + completion + last log lines"
	@echo "  make bench-stop       stop it (re-launch resumes; finished runs are skipped)"
	@echo "  make capacity-sweep   find each method's real OOM cap (the streaming argument)"
	@echo ""
	@echo "Take the results away:"
	@echo "  make bundle-estimate  what a bundle would contain + how big (check before building)"
	@echo "  make bundle           zip results+snapshots+logs+tables -> results/bundles/"
	@echo "                        (point clouds excluded; BUNDLE_INCLUDE=all adds them)"
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
	@echo "  make fig-fusion       per-view vs fused panels from the dataset export (no GPU)"
	@echo "  make fig-fusion-results  per-view (panovggt) vs fused (prism) from result clouds"
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

# PRISM ablations — guard-contribution study + alignment-group study.
# `prism` itself is the Sim(3) arm (the deployed default), so the alignment arms here
# are the OTHER two groups. This list previously said `prism_sim3`, which stopped
# existing when the default flipped to Sim(3) — `make ablations` would have failed on
# every alignment arm. Keep it in sync with config.yaml `ablations`.
ABL_GUARDS ?= prism_nolock prism_nostill prism_noguards
ABL_ALIGN  ?= prism_sl4 prism_se3
ablations: setup
	@echo ">> running PRISM ablations (config.ablations)"
	@for a in $(ABL_GUARDS) $(ABL_ALIGN); do \
	  $(ORCH_RUN) adapters/run.py --method $$a --config $(CONFIG) --scenes "$(SCENES)" --traj $(TRAJ) || exit 1; \
	done

# Just the alignment-group study (sim3 is the plain `prism` run; add se3 + sl4).
ablations-align: setup
	@echo ">> alignment-group study: SL(4) + SE(3) arms (Sim(3) = the plain prism run)"
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

# ── Publication-grade aggregation ─────────────────────────────────────────────
# `make report` keeps its original behaviour (aggregate EVERYTHING in results/) so
# nothing downstream breaks. The publication path is separate and additive:
#
#   report-clean   seeded-only + named exclusions + complete-runs-only
#   report-tables  freeze those into the column layout uofa-2026-report ingests
#   verify-clean   fail loudly if a contaminated run reached the clean output
#
# NOTE ON `clean-results`: it remains the DESTRUCTIVE housekeeping target it has
# always been (rm -rf results/*). The findings doc asks for "make clean-results" to
# mean seeded-only aggregation; repurposing a destructive target would be a footgun,
# so that job lives in `report-clean` instead. See RESULTS_CHANGELOG.md.
#
# SOURCE=auto|live|archive — `auto` uses results/ when populated, else the committed
# archive snapshot, so the clean report reproduces even with no results tree on disk.
SOURCE   ?= auto
RUN_ID   ?= bigrun_2026-07

ingest-archive: setup
	@echo ">> archived snapshot ($(RUN_ID)) -> tidy per-run records"
	$(ORCH_RUN) eval/ingest_archive.py --run-id $(RUN_ID)

report-clean: setup
	@echo ">> CLEAN seeded-only aggregate (source=$(SOURCE))"
	@if [ "$(SOURCE)" != "live" ]; then $(MAKE) --no-print-directory ingest-archive; fi
	$(ORCH_RUN) eval/aggregate_clean.py --config $(CONFIG) --source $(SOURCE) --run-id $(RUN_ID)
aggregate-clean: report-clean          # alias

report-tables: report-clean
	@echo ">> report-facing table bundle -> results/report_tables/"
	$(ORCH_RUN) eval/export_report_tables.py

verify-clean: setup
	@echo ">> verifying the clean aggregate contains no contaminated runs"
	$(ORCH_RUN) eval/verify_clean.py --run-id $(RUN_ID)

# ── Capacity / OOM sweep — where each method actually runs out of memory ─────
# This is the PRIMARY source of the OOM evidence, deliberately separated from the main
# matrix. The matrix runs at a fixed n_frames (300) and records any natural OOM, but
# that only tells you "it OOMed at 300". The prefix sweep feeds each method growing
# prefixes of one real sequence until it dies, so you get the actual cap per method
# plus a clean VRAM-vs-length curve — at a tiny fraction of the cost of running the
# whole matrix long enough to provoke it.
#
# Streaming methods should walk off the right-hand side of the plot flat; full-batch
# methods should hit a wall. That contrast IS the argument for a streaming engine.
# (LASER's KITTI table reports VGGT / Pi3 / Fast3R as OOM on every sequence, so
# reporting a capacity limit like this is established practice.)
#
# --tile loops the sequence past its rendered length, so the grid can exceed n_frames.
CAP_SCENE  ?= auto
CAP_TRAJ   ?= synthetic_5.0hz_s0
CAP_FRAMES ?= 16,32,64,96,128,192,256,384,512,768,1024
capacity-sweep: setup
	@echo ">> capacity sweep: growing prefixes until each method OOMs -> results/figures/"
	$(ORCH_RUN) eval/vram_scaling.py --source sweep --config $(CONFIG) \
	  --scene "$(CAP_SCENE)" --traj "$(CAP_TRAJ)" --frames "$(CAP_FRAMES)" --logx --tile

# ── Package the results for download ─────────────────────────────────────────
# One .zip of everything worth keeping. Point clouds are EXCLUDED by default: they
# dominate results/ (6-103 MB each in 2026-07), so a full matrix with clouds is tens
# of GB — past what a browser download will tolerate. Always estimate first.
#
#   make bundle-estimate                 # what would go in, and how big
#   make bundle                          # everything except point clouds
#   make bundle BUNDLE_INCLUDE=all       # including clouds (very large)
#   make bundle BUNDLE_INCLUDE=reports,snapshots
BUNDLE_INCLUDE ?= default
BUNDLE_OUT     ?=
bundle: setup
	@echo ">> packaging results -> results/bundles/"
	$(ORCH_RUN) eval/bundle_results.py --include "$(BUNDLE_INCLUDE)" \
	  $(if $(BUNDLE_OUT),--out "$(BUNDLE_OUT)",)

bundle-estimate: setup
	$(ORCH_RUN) eval/bundle_results.py --include "$(BUNDLE_INCLUDE)" --estimate

# ── Smoke test — prove the pipeline works BEFORE the long run ────────────────
# Tiny matrix (1 small scene x 3 motion families x 2 seeds x every method) through
# every stage, then eval/smoke_check.py validates the artifacts and projects how long
# the real run will take. Uses config.smoke.yaml as an additive overlay, so your
# frozen scene list in config.local.yaml is never touched.
#
#   make smoke                                  # full check (recommended)
#   make smoke SMOKE_TRAJ=synthetic_2.0hz_s0    # ~5 min sanity check
#   make smoke SMOKE_METHODS="prism pi3"        # subset the methods
smoke: setup
	@echo ">> SMOKE TEST — full pipeline on a tiny matrix (see logs/smoke_latest.log)"
	bash scripts/smoke_test.sh

smoke-check: setup
	@echo ">> validating the last smoke run's artifacts only (no re-run)"
	PRISM_CONFIG_OVERLAY=config.smoke.yaml $(ORCH_RUN) eval/smoke_check.py --config $(CONFIG)

publication: report-clean report-tables verify-clean
	@echo ">> publication artifacts ready:"
	@echo "   results/report_clean/clean_report.md   (analysis)"
	@echo "   results/report_tables/                 (for uofa-2026-report)"
	@echo "   RESULTS_CHANGELOG.md                   (what changed and why)"

# ── VGGT-SLAM fairness arms ───────────────────────────────────────────────────
# The 2026-07 head-to-head used loop closure OFF (max_loops=0) — VGGT-SLAM's headline
# feature disabled. Both arms are run so the paper reports the baseline in its native
# mode as well. Needs the VGGT-SLAM env + exports; GPU required.
ABL_VGGTSLAM ?= vggtslam_noloop vggtslam_loop
run-vggtslam-arms: setup
	@echo ">> VGGT-SLAM fairness arms: loop closure OFF and ON"
	@for a in $(ABL_VGGTSLAM); do \
	  $(ORCH_RUN) adapters/run.py --method $$a --config $(CONFIG) --scenes "$(SCENES)" --traj $(TRAJ) || exit 1; \
	done
ablations-vggtslam: run-vggtslam-arms

# ── Report figures (Deliverables 1 & 2) -> results/figures/ ────────────────────
# fig-vram is reproducible from the committed seeded perf.csv (no GPU). fig-vram-sweep
# and fig-cubemap-export need the reference GPU + method envs/exports. FIG_SCENE /
# FIG_TRAJ / FIG_FRAMES override the defaults (see eval/vram_scaling.py, eval/fig_cubemap.py).
FIG_SCENE  ?= auto
FIG_TRAJ   ?= synthetic_2.0hz_s0
FIG_FRAME  ?= 0                     # which pano frame the cubemap figure uses
FIG_FRAMES ?= 1,2,4,8,16,32,64,128,256
FIG_TILE   ?=                       # set FIG_TILE=1 to loop the sequence past its render length
# fig-fusion: window of overlapping frames (a dense traj gives the strongest per-view story)
FUSION_TRAJ  ?= synthetic_5.0hz_s0
FUSION_START ?= 0
FUSION_WINDOW ?= 0                  # 0 = config engine.window_size (16)
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
fig-fusion: setup
	@echo ">> per-view vs fused panels from the dataset export -> results/figures/"
	$(ORCH_RUN) eval/fig_fusion.py --mode dataset --config $(CONFIG) \
	  --scene "$(FIG_SCENE)" --traj "$(FUSION_TRAJ)" \
	  --frame-start "$(FUSION_START)" --window "$(FUSION_WINDOW)"
fig-fusion-results: setup
	@echo ">> per-view (panovggt) vs fused (prism) from result clouds -> results/figures/"
	$(ORCH_RUN) eval/fig_fusion.py --mode results --config $(CONFIG) \
	  --scene "$(FIG_SCENE)" --traj "$(FUSION_TRAJ)"
figures: fig-vram fig-cubemap
	@echo ">> report figures in results/figures/ (vram_vs_frames.png + cubemap_projection.png)"

# ── Overnight big benchmark (SSH-proof, resumable, priority-ordered) ──────────
# Runs the whole matrix in a detached tmux session so it survives disconnect.
# Reattach: tmux attach -t bench   |   Monitor: tail -f logs/overnight_latest.log
# Detached launch that survives SSH disconnect. Picks the best backend available
# rather than hard-failing when tmux is missing (the old behaviour): tmux if present
# (reattachable), else setsid, else nohup. All three fully detach from the terminal,
# so closing the SSH session cannot take the run down with it.
BENCH_SESSION ?= bench
bench-overnight:
	@if [ -f logs/overnight.pid ] && kill -0 "$$(cat logs/overnight.pid)" 2>/dev/null; then \
	  echo "!! a benchmark is ALREADY RUNNING (pid $$(cat logs/overnight.pid))."; \
	  echo "   make bench-status   to watch it   |   make bench-stop   to stop it"; \
	  exit 1; \
	fi
	@mkdir -p logs
	@if command -v tmux >/dev/null 2>&1; then \
	  tmux new -d -s $(BENCH_SESSION) 'bash scripts/run_overnight.sh'; \
	  tmux list-panes -t $(BENCH_SESSION) -F '#{pane_pid}' > logs/overnight.pid 2>/dev/null || true; \
	  echo ">> launched detached in tmux session '$(BENCH_SESSION)'  [survives logout]"; \
	  echo "   reattach : tmux attach -t $(BENCH_SESSION)   (detach again with Ctrl-b d)"; \
	elif command -v setsid >/dev/null 2>&1; then \
	  setsid nohup bash scripts/run_overnight.sh >/dev/null 2>&1 < /dev/null & \
	  echo $$! > logs/overnight.pid; \
	  echo ">> launched detached via setsid (pid $$(cat logs/overnight.pid))  [survives logout]"; \
	  echo "   no tmux, so there is nothing to reattach to — follow the log instead"; \
	else \
	  nohup bash scripts/run_overnight.sh >/dev/null 2>&1 < /dev/null & \
	  echo $$! > logs/overnight.pid; \
	  echo ">> launched detached via nohup (pid $$(cat logs/overnight.pid))  [survives logout]"; \
	fi
	@sleep 1
	@echo "   monitor  : make bench-status      (or: tail -f logs/overnight_latest.log)"
	@echo "   progress : cat logs/overnight_latest.progress"
	@echo "   stop     : make bench-stop"
	@echo "   resumable: re-running skips finished runs (FORCE=1 redoes them)"

bench-status:
	@if [ -f logs/overnight.pid ] && kill -0 "$$(cat logs/overnight.pid)" 2>/dev/null; then \
	  echo "RUNNING (pid $$(cat logs/overnight.pid))"; \
	elif command -v tmux >/dev/null 2>&1 && tmux has-session -t $(BENCH_SESSION) 2>/dev/null; then \
	  echo "RUNNING (tmux session '$(BENCH_SESSION)')"; \
	else \
	  echo "NOT RUNNING (finished, or never started)"; \
	fi
	@echo ""; echo "--- progress ---"
	@tail -n 15 logs/overnight_latest.progress 2>/dev/null || echo "(no progress file yet)"
	@echo ""; echo "--- completion so far ---"
	@if [ -f results/report_clean/completion.csv ]; then \
	  cut -d, -f1-5 results/report_clean/completion.csv | sed 's/^/  /'; \
	else echo "  (no clean report yet — first checkpoint not reached)"; fi
	@echo ""; echo "--- last 20 log lines ---"
	@tail -n 20 logs/overnight_latest.log 2>/dev/null || echo "(no log yet)"
	@echo ""; echo "follow live: tail -f logs/overnight_latest.log"

bench-stop:
	@if command -v tmux >/dev/null 2>&1 && tmux has-session -t $(BENCH_SESSION) 2>/dev/null; then \
	  tmux kill-session -t $(BENCH_SESSION) && echo ">> killed tmux session '$(BENCH_SESSION)'"; \
	fi
	@if [ -f logs/overnight.pid ]; then \
	  pkill -TERM -P "$$(cat logs/overnight.pid)" 2>/dev/null || true; \
	  kill -TERM "$$(cat logs/overnight.pid)" 2>/dev/null || true; \
	  rm -f logs/overnight.pid; echo ">> stopped"; \
	else echo ">> nothing to stop"; fi
	@echo "   re-launch with 'make bench-overnight' — finished runs are skipped."

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
# DESTRUCTIVE. Wipes the results tree. This is NOT the seeded-only aggregator —
# that is `make report-clean`. Kept destructive on purpose (see RESULTS_CHANGELOG.md).
clean-results:
	@rm -rf results/* && echo "cleared results/  (for the CLEAN AGGREGATE use: make report-clean)"

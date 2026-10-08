#!/usr/bin/env python
"""Benchmark progress: overall bar, ETA, what is running now, per-method table.

    make progress            # print once
    make watch               # refresh every 15 s (Ctrl-C to leave; the run continues)

Reads only files: results/**/perf.json (what finished), logs/overnight_latest.log
(what is running) and logs/precheck.json (per-method run time measured by the
pre-check, used for the ETA of methods that have not started yet). Safe to run at
any time, from any shell, while the benchmark runs.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
import time
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bench.config import REPO_ROOT, load_config
from bench.matrix import plan

LOG = REPO_ROOT / "logs" / "overnight_latest.log"
PRECHECK = REPO_ROOT / "logs" / "precheck.json"


def _fmt_dur(s: float) -> str:
    s = int(max(0, s))
    h, r = divmod(s, 3600)
    m, _ = divmod(r, 60)
    return f"{h}h{m:02d}m" if h else f"{m}m"


def _bar(frac: float, width: int) -> str:
    frac = min(max(frac, 0.0), 1.0)
    full = int(frac * width)
    part = " ▏▎▍▌▋▊▉"[int((frac * width - full) * 8)] if full < width else ""
    return "█" * full + part + " " * (width - full - len(part))


def _current():
    """(method, sequence, started_epoch, last_line) from the overnight log tail."""
    if not LOG.exists():
        return None
    try:
        with open(LOG, "rb") as f:
            f.seek(0, os.SEEK_END)
            f.seek(max(0, f.tell() - 200_000))
            tail = f.read().decode("utf-8", "replace").splitlines()
    except Exception:
        return None
    method = seq = None
    for ln in reversed(tail):
        m = re.match(r"\[(\w+)\] (\w+)/(\w+)/([\w.]+)/(\w+)\s*$", ln)
        if m and seq is None:
            method, seq = m.group(1), f"{m.group(3)}/{m.group(4)}"
        if ">>> RUN" in ln or "############ DONE" in ln or "ABORT" in ln:
            if "DONE" in ln:
                return ("(finished)", "", LOG.stat().st_mtime, ln)
            if "ABORT" in ln:
                return ("(ABORTED)", "", LOG.stat().st_mtime, ln)
            break
    last = next((x for x in reversed(tail) if x.strip()), "")
    return (method, seq, LOG.stat().st_mtime, last)


def render(cfg) -> str:
    units = plan(cfg)
    if not units:
        return "No frozen scenes yet (the data stage freezes them)."
    per = defaultdict(lambda: {"total": 0, "done": 0, "fail": 0, "secs": []})
    for u in units:
        d = per[u.method]
        d["total"] += 1
        p = u.perf()
        if p is not None:
            d["done"] += 1
            if not p.get("completed", False):
                d["fail"] += 1
            elif p.get("wall_s"):
                d["secs"].append(float(p["wall_s"]))
    pre = {}
    if PRECHECK.exists():
        try:
            pre = {r["method"]: r.get("wall_s") for r in json.loads(PRECHECK.read_text()).get("rows", [])}
        except Exception:
            pre = {}

    total = sum(d["total"] for d in per.values())
    done = sum(d["done"] for d in per.values())
    fail = sum(d["fail"] for d in per.values())
    remaining_s, unknown = 0.0, 0
    fam = defaultdict(list)            # prism_sl4 & co. take prism's time until measured
    for m, d in per.items():
        fam[m.split("_")[0]] += d["secs"]
    for m, d in per.items():
        left = d["total"] - d["done"]
        f = fam.get(m.split("_")[0])
        avg = ((sum(d["secs"]) / len(d["secs"])) if d["secs"] else pre.get(m)
               or ((sum(f) / len(f)) if f else None))
        if avg:
            remaining_s += left * float(avg)
        elif left:
            unknown += left

    width = max(20, min(50, shutil.get_terminal_size((100, 20)).columns - 50))
    frac = done / total if total else 0
    eta = (f"ETA {_fmt_dur(remaining_s)} (~{time.strftime('%H:%M', time.localtime(time.time() + remaining_s))})"
           + (f" + {unknown} runs with no timing yet" if unknown else ""))
    lines = [f"PRISM-benchmarks  [{_bar(frac, width)}] {100 * frac:5.1f}%  {done}/{total} runs"
             + (f"  {fail} FAILED" if fail else "") + f"   {eta}"]
    cur = _current()
    if cur:
        m, seq, mt, last = cur
        age = time.time() - mt
        lines.append(f"now : {m or '?'}  {seq or ''}   (log updated {int(age)} s ago)"
                     + ("   <-- no log output for >10 min: check `tmux attach -t pod`" if age > 600 else ""))
    lines.append("")
    lines.append(f"{'method':18s} {'done':>9s} {'fail':>5s} {'avg/run':>8s}  progress")
    for m, d in per.items():
        avg = (sum(d["secs"]) / len(d["secs"])) if d["secs"] else None
        a = f"{avg:6.0f}s" if avg else ("~%4.0fs" % pre[m] if pre.get(m) else "      -")
        f = d["done"] / d["total"] if d["total"] else 0
        lines.append(f"{m:18s} {d['done']:4d}/{d['total']:<4d} {d['fail']:5d} {a:>8s}  [{_bar(f, 20)}]")
    if fail:
        lines.append("")
        lines.append("failed runs: grep -l '\"completed\": false' results/*/*/*/*/*/perf.json")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--watch", type=float, default=0, help="refresh every N seconds")
    args = ap.parse_args()
    cfg = load_config("config.yaml")
    if not args.watch:
        print(render(cfg))
        return
    try:
        while True:
            out = render(cfg)
            sys.stdout.write("\033[2J\033[H" + out + f"\n\n(refresh {args.watch:.0f}s — Ctrl-C to leave; the run keeps going)\n")
            sys.stdout.flush()
            time.sleep(args.watch)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()

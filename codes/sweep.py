"""
Large multi-seed PS1 sweep: builds the term-paper dataset.

For every (seed, traffic-density, AV-penetration) combination it generates
routes (02), runs SUMO over TraCI (03), and stores one row of results.
Default: 200 seeds x 5 penetration rates x 1 density = 1000 simulation runs.

Design notes
  * The SAME seed is used at every penetration rate, so each seed gives the
    same trip demand and nested AV sets (the AVs at 25% are also AVs at 50%,
    etc.). That makes a paired comparison possible: "for the same demand,
    what did adding AVs change?" -- much tighter than comparing unrelated runs.
  * Resumable: finished runs leave a row.json; re-running the script skips
    them. Ctrl+C is safe; just run the same command again to continue.
  * Parallel: --workers runs several SUMO simulations at once.
  * Each run happens in its own folder under runs/, so parallel runs never
    overwrite each other's files. Big per-run files (routes, tripinfo) are
    deleted after parsing unless --keep-files is given.

Model comparison (see vehicle_models.py for what each set means)
    python 04_sweep.py --seeds 2 --workers 2 --model-sets idm_acc     # quick test first!
    python 04_sweep.py --seeds 50 --model-sets idm_acc eidm_acc idm_cacc
    python 04_sweep.py --seeds 50 --model-sets idm_acc --av-tau 1.0   # headway sensitivity
Your original Krauss runs are the default model set ("krauss") and are reused,
not re-run: they live in the legacy folder layout and are skipped on resume.
Because seeds 1..N use identical trip demand in every model set, the models can
be compared seed-by-seed.

Other usage
    python sweep.py                              # krauss, 200 seeds
    python sweep.py --periods 3.0 2.0 1.5        # several traffic densities
    python sweep.py --aggregate-only             # just rebuild the CSV

Output: dataset.csv  (one row per simulation run)
"""
import argparse
import concurrent.futures as cf
import csv
import json
import os
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from vehicle_models_2 import DEFAULT_AV_TAU, MODEL_SETS

HERE = Path(__file__).resolve().parent
PENETRATIONS = [0.0, 0.25, 0.5, 0.75, 1.0]
DEFAULT_STEP = 0.5

# NEW COLUMNS ADDED
COLUMNS = [
    "run_id", "model_set", "av_tau", "step_length", "seed", "period", "penetration",
    "avg_delay_s", "avg_speed_mps", "avg_travel_time_s", "avg_queue_length",
    "avg_fuel_ml", "avg_co2_mg",  # Environmental KPIs
    "completed_trips", "unfinished_trips", "collisions", "runtime_s",
]

def variant_name(model, av_tau, step):
    name = model
    if av_tau is not None:
        name += f"_avtau{av_tau:g}"
    if step != DEFAULT_STEP:
        name += f"_dt{step:g}"
    return name

def run_dir(root, variant, pen, seed, period):
    base = root if variant == "krauss" else root / variant
    return base / f"T{period:g}" / f"p{int(round(pen * 100)):03d}_s{seed:04d}"

def run_one(job):
    model, av_tau, step, pen, seed, period, net, root, keep = job
    variant = variant_name(model, av_tau, step)
    d = run_dir(root, variant, pen, seed, period)
    d.mkdir(parents=True, exist_ok=True)
    row_file = d / "row.json"
    if row_file.exists():
        return "skipped", job, ""

    t0 = time.time()
    err = ""
    route_cmd = [sys.executable, str(HERE / "02_generate_routes_2.py"),
                 "--net", net, "--penetration", str(pen), "--period", str(period),
                 "--seed", str(seed), "--model-set", model, "-o", "routes.rou.xml"]
    if av_tau is not None:
        route_cmd += ["--av-tau", str(av_tau)]
    for _attempt in range(2):
        try:
            subprocess.run(route_cmd, cwd=d, check=True, capture_output=True, text=True)
            subprocess.run(
                [sys.executable, str(HERE / "03_run_scenario_3.py"), # Call updated script
                 "--net", net, "--route", "routes.rou.xml",
                 "--penetration", str(pen), "--step-length", str(step),
                 "--out", "result.json"],
                cwd=d, check=True, capture_output=True, text=True)
            break
        except subprocess.CalledProcessError as e:
            err = (e.stderr or e.stdout or str(e))[-500:]
    else:
        return "failed", job, err

    with open(d / "result.json") as f:
        row = json.load(f)
    row.update({
        "run_id": f"{variant}_T{period:g}_p{int(round(pen * 100)):03d}_s{seed:04d}",
        "model_set": variant,
        "av_tau": DEFAULT_AV_TAU[model] if av_tau is None else av_tau,
        "step_length": step,
        "seed": seed,
        "period": period,
        "penetration": pen,
        "runtime_s": round(time.time() - t0, 1),
    })
    with open(row_file, "w") as f:
        json.dump(row, f)

    if not keep:
        for name in ("routes.rou.xml", "result.json", "result_tripinfo.xml"):
            try:
                (d / name).unlink()
            except FileNotFoundError:
                pass
    return "done", job, ""

def aggregate(root, out_csv):
    rows = []
    for p in sorted(root.rglob("row.json")):
        with open(p) as f:
            r = json.load(f)
        r.setdefault("model_set", "krauss")
        r.setdefault("av_tau", DEFAULT_AV_TAU.get("krauss", 0.6))
        r.setdefault("step_length", DEFAULT_STEP)
        # Handle older rows that don't have the new environmental KPIs
        r.setdefault("avg_fuel_ml", 0.0)
        r.setdefault("avg_co2_mg", 0.0)
        rows.append(r)
    rows.sort(key=lambda r: (r["model_set"], r["period"], r["seed"], r["penetration"]))
    with open(out_csv, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    print(f"Wrote {out_csv} with {len(rows)} runs")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--net", default="manhattan.net.xml")
    ap.add_argument("--seeds", type=int, default=200)
    ap.add_argument("--seed-start", type=int, default=1)
    ap.add_argument("--model-sets", nargs="+", default=["krauss"], choices=list(MODEL_SETS))
    ap.add_argument("--av-taus", type=float, nargs="+", default=[None])
    ap.add_argument("--step-length", type=float, default=DEFAULT_STEP)
    ap.add_argument("--periods", type=float, nargs="+", default=[2.0])
    ap.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2) // 2))
    ap.add_argument("--root", default="runs")
    ap.add_argument("--dataset", default="ps1_dataset_env.csv") # Output to new CSV
    ap.add_argument("--keep-files", action="store_true")
    ap.add_argument("--aggregate-only", action="store_true")
    args = ap.parse_args()

    root = Path(args.root).resolve()
    if args.aggregate_only:
        aggregate(root, args.dataset)
        return

    net = Path(args.net).resolve()
    if not net.exists():
        sys.exit(f"Network file not found: {net}")

    seeds = range(args.seed_start, args.seed_start + args.seeds)
    jobs = [(model, tau, args.step_length, pen, seed, period, str(net), root, args.keep_files)
            for seed in seeds for model in args.model_sets
            for period in args.periods for pen in PENETRATIONS for tau in args.av_taus]

    print(f"Starting {len(jobs)} runs. Includes Environmental KPI tracking.")

    done = skipped = 0
    failed = []
    t_start = time.time()
    ex = cf.ThreadPoolExecutor(max_workers=args.workers)
    try:
        futures = [ex.submit(run_one, j) for j in jobs]
        for fut in cf.as_completed(futures):
            status, job, err = fut.result()
            if status == "skipped":
                skipped += 1
                continue
            if status == "failed":
                failed.append((job, err))
                continue
            done += 1
    except KeyboardInterrupt:
        ex.shutdown(wait=False, cancel_futures=True)
    else:
        ex.shutdown()

    aggregate(root, args.dataset)

if __name__ == "__main__":
    main()

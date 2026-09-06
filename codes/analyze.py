"""
Purpose: Loads results.csv (from sweep.py) and produces:
          - one line chart per metric vs. AV penetration rate (PNG files)
          - a printed summary of the % change from 0% to 100% AV for each metric

Usage:
    python analyze.py
    python analyze.py --csv results.csv --outdir figures
"""
import argparse
import csv
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

METRICS = [
    ("avg_delay_s", "Average delay (s)", "Delay vs. AV Penetration"),
    ("avg_speed_mps", "Average speed (m/s)", "Average Speed vs. AV Penetration"),
    ("avg_travel_time_s", "Average travel time (s)", "Travel Time vs. AV Penetration"),
    ("avg_queue_length", "Average queue length (vehicles)", "Queue Length vs. AV Penetration"),
]


def load_results(csv_path):
    with open(csv_path) as f:
        rows = list(csv.DictReader(f))
    rows.sort(key=lambda r: float(r["penetration"]))
    return rows


def plot_metric(rows, field, ylabel, title, outdir):
    x = [float(r["penetration"]) * 100 for r in rows]
    y = [float(r[field]) for r in rows]

    plt.figure(figsize=(6, 4))
    plt.plot(x, y, marker="o", linewidth=2)
    plt.xlabel("AV Penetration Rate (%)")
    plt.ylabel(ylabel)
    plt.title(title)
    plt.grid(True, alpha=0.3)
    plt.tight_layout()

    out_path = os.path.join(outdir, f"{field}.png")
    plt.savefig(out_path, dpi=150)
    plt.close()
    return out_path


def print_summary(rows):
    first, last = rows[0], rows[-1]
    print(f"\nSummary: {float(first['penetration'])*100:.0f}% -> "
          f"{float(last['penetration'])*100:.0f}% AV penetration\n")
    for field, label, _ in METRICS:
        v0 = float(first[field])
        v1 = float(last[field])
        if v0 == 0:
            change = "n/a (baseline is 0)"
        else:
            pct = (v1 - v0) / v0 * 100
            direction = "increase" if pct > 0 else "decrease"
            change = f"{abs(pct):.1f}% {direction}"
        print(f"  {label:35s} {v0:8.2f} -> {v1:8.2f}   ({change})")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default="results.csv")
    ap.add_argument("--outdir", default="figures")
    args = ap.parse_args()

    os.makedirs(args.outdir, exist_ok=True)
    rows = load_results(args.csv)

    print(f"Loaded {len(rows)} penetration rates from {args.csv}")
    for field, ylabel, title in METRICS:
        path = plot_metric(rows, field, ylabel, title, args.outdir)
        print(f"Saved {path}")

    print_summary(rows)


if __name__ == "__main__":
    main()

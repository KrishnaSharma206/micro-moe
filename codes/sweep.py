"""
Purpose: Runs the full PS1 sweep: 0%, 25%, 50%, 75%, 100% AV penetration.
         Generates routes for each rate, runs the scenario, and writes results.csv.

Usage: python sweep.py
"""
import csv
import json
import subprocess
import sys

PENETRATIONS = [0.0, 0.25, 0.5, 0.75, 1.0]
SEED = 42

def label(p):
    return f"{int(p * 100)}"

def main():
    rows = []
    for p in PENETRATIONS:
        lbl = label(p)
        route_file = f"routes_{lbl}.rou.xml"
        result_file = f"results_{lbl}.json"
        print(f"\n=== {lbl}% AV penetration ===")
        subprocess.run([
            sys.executable, "generate_routes.py",
            "--penetration", str(p),
            "--seed", str(SEED),
            "-o", route_file,
        ], check=True)
        subprocess.run([
            sys.executable, "run_scenario.py",
            "--route", route_file,
            "--penetration", str(p),
            "--out", result_file,
        ], check=True)
        with open(result_file) as f:
            rows.append(json.load(f))
    with open("results.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print("\nWrote results.csv")
    for r in rows:
        print(r)

if __name__ == "__main__":
    main()
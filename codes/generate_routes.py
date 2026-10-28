"""
Generates trips for the network and assigns each vehicle a type
(human-driven or AV) according to a given penetration rate.

Usage:
    python generate_routes.py --penetration 0.5 --seed 42 -o routes_50.rou.xml

Requires $SUMO_HOME/tools on the path (for randomTrips.py) -- this is
set up automatically if SUMO_HOME is exported correctly.
"""
import argparse
import os
import random
import subprocess
import sys
import xml.etree.ElementTree as ET

from vehicle_models import MODEL_SETS, get_vtypes  # car-following model sets (see that file)


def run_random_trips(net_file, trips_file, end_time, period, seed):
    sumo_home = os.environ.get("SUMO_HOME")
    if not sumo_home:
        sys.exit("SUMO_HOME is not set — see setup step 2.")
    random_trips = os.path.join(sumo_home, "tools", "randomTrips.py")
    cmd = [
        sys.executable, random_trips,
        "-n", net_file,
        "-o", trips_file,
        "-e", str(end_time),
        "-p", str(period),
        "--seed", str(seed),
        "--fringe-factor", "5",
        "--validate",  # drop trips with no valid route -- real networks can have disconnected edges
    ]
    subprocess.run(cmd, check=True)


def assign_vehicle_types(trips_file, out_file, penetration, seed, human_vtype, av_vtype):
    """Reads the plain trip file randomTrips.py produced, assigns each
    vehicle a type by weighted coin flip, and writes a route file with
    both vType definitions plus the trips."""
    rng = random.Random(seed)
    tree = ET.parse(trips_file)
    root = tree.getroot()

    for trip in root.findall("trip"):
        vtype = "AV" if rng.random() < penetration else "human"
        trip.set("type", vtype)

    new_root = ET.Element("routes")
    ET.SubElement(new_root, "vType", human_vtype)
    ET.SubElement(new_root, "vType", av_vtype)
    for trip in root.findall("trip"):
        new_root.append(trip)

    ET.ElementTree(new_root).write(out_file, xml_declaration=True, encoding="UTF-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--net", default="manhattan.net.xml")
    ap.add_argument("--penetration", type=float, required=True,
                     help="Fraction of vehicles that are AVs, e.g. 0.25")
    ap.add_argument("--end", type=int, default=1800, help="Simulation horizon (s)")
    ap.add_argument("--period", type=float, default=2.0,
                     help="Mean seconds between vehicle insertions (lower = denser traffic). "
                          "0.6 gridlocked the Manhattan network; start at 2.0 and lower it gradually.")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--model-set", default="krauss", choices=list(MODEL_SETS),
                     help="car-following models for human and AV vehicles (see vehicle_models.py)")
    ap.add_argument("--av-tau", type=float, default=None,
                     help="override the AV desired time headway (s) for sensitivity runs")
    ap.add_argument("-o", "--output", required=True)
    args = ap.parse_args()

    tmp_trips = f"_tmp_trips_{args.seed}_{os.getpid()}.trips.xml"  # unique per process so parallel runs never collide
    run_random_trips(args.net, tmp_trips, args.end, args.period, args.seed)
    human_vtype, av_vtype, _ = get_vtypes(args.model_set, args.av_tau)
    assign_vehicle_types(tmp_trips, args.output, args.penetration, args.seed,
                         human_vtype, av_vtype)
    os.remove(tmp_trips)
    print(f"Wrote {args.output} at {args.penetration*100:.0f}% AV penetration ({args.model_set})")


if __name__ == "__main__":
    main()

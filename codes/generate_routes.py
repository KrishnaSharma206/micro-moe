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

from vehicle_models import MODEL_SETS, get_vtypes


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
        "--validate",
    ]
    subprocess.run(cmd, check=True)


def assign_vehicle_types(trips_file, out_file, penetration, seed, human_vtypes, av_vtype):
    rng = random.Random(seed)
    tree = ET.parse(trips_file)
    root = tree.getroot()

    # Traffic composition from reference paper
    HUMAN_DIST = [
        ("human_passenger", 0.785),
        ("human_truck", 0.143),
        ("human_trailer", 0.069),
        ("human_motorcycle", 0.003)
    ]

    def get_human_type():
        r = rng.random()
        cum = 0.0
        for v_id, prob in HUMAN_DIST:
            cum += prob
            if r <= cum:
                return v_id
        return "human_passenger"

    for trip in root.findall("trip"):
        if rng.random() < penetration:
            vtype = "AV"
        else:
            vtype = get_human_type()
        trip.set("type", vtype)

    new_root = ET.Element("routes")
    
    # Add all human vType definitions
    for h_id, params in human_vtypes.items():
        ET.SubElement(new_root, "vType", **params)
    # Add AV vType
    ET.SubElement(new_root, "vType", **av_vtype)
    
    for trip in root.findall("trip"):
        new_root.append(trip)

    ET.ElementTree(new_root).write(out_file, xml_declaration=True, encoding="UTF-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--net", default="manhattan.net.xml")
    ap.add_argument("--penetration", type=float, required=True)
    ap.add_argument("--end", type=int, default=1800)
    ap.add_argument("--period", type=float, default=2.0)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--model-set", default="krauss", choices=list(MODEL_SETS))
    ap.add_argument("--av-tau", type=float, default=None)
    ap.add_argument("-o", "--output", required=True)
    args = ap.parse_args()

    tmp_trips = f"_tmp_trips_{args.seed}_{os.getpid()}.trips.xml"
    run_random_trips(args.net, tmp_trips, args.end, args.period, args.seed)
    
    human_vtypes, av_vtype, _ = get_vtypes(args.model_set, args.av_tau)
    assign_vehicle_types(tmp_trips, args.output, args.penetration, args.seed,
                         human_vtypes, av_vtype)
    os.remove(tmp_trips)
    print(f"Wrote {args.output} at {args.penetration*100:.0f}% AV penetration ({args.model_set})")


if __name__ == "__main__":
    main()

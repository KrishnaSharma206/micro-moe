"""
Purpose: Generates trips for grid.net.xml and assigns each vehicle a type
         (human-driven or AV) according to a given penetration rate.

Usage: python generate_routes.py --penetration <penetration rate> --seed <randomness seed> -o <filename>.rou.xml

Requirements: SUMO_HOME is exported correctly.

Assumptions: "human" uses SUMO's default Krauss car-following model (conservative human
             driving). "AV" uses a tighter minGap / faster accel+decel to represent
             cooperative/automated driving behaviour.
"""
import argparse
import os
import random
import subprocess
import sys
import xml.etree.ElementTree as ET

HUMAN_VTYPE = dict(
    id="human", vClass="passenger", carFollowModel="Krauss",
    accel="2.6", decel="4.5", sigma="0.5", minGap="2.5", tau="1.2",
    maxSpeed="16.6", color="0.6,0.6,0.6",
)
AV_VTYPE = dict(
    id="AV", vClass="passenger", carFollowModel="Krauss",
    accel="3.0", decel="4.5", sigma="0.0", minGap="1.5", tau="0.8",
    maxSpeed="16.6", color="0,0.8,0",
)

def run_random_trips(net_file, trips_file, end_time, period, seed):
    sumo_home = os.environ.get("SUMO_HOME")
    if not sumo_home:
        sys.exit("SUMO_HOME is not set")
    random_trips = os.path.join(sumo_home, "tools", "randomTrips.py")
    cmd = [
        sys.executable, random_trips,
        "-n", net_file,
        "-o", trips_file,
        "-e", str(end_time),
        "-p", str(period),
        "--seed", str(seed),
        "--fringe-factor", "5",
    ]
    subprocess.run(cmd, check=True)


def assign_vehicle_types(trips_file, out_file, penetration, seed):
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
    ET.SubElement(new_root, "vType", HUMAN_VTYPE)
    ET.SubElement(new_root, "vType", AV_VTYPE)
    for trip in root.findall("trip"):
        new_root.append(trip)

    ET.ElementTree(new_root).write(out_file, xml_declaration=True, encoding="UTF-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--net", default="grid.net.xml")
    ap.add_argument("--penetration", type=float, required=True,
                     help="Fraction of vehicles that are AVs, e.g. 0.25")
    ap.add_argument("--end", type=int, default=1800, help="Simulation horizon (s)")
    ap.add_argument("--period", type=float, default=1.2,
                     help="Mean seconds between vehicle insertions (lower = denser traffic)")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("-o", "--output", required=True)
    args = ap.parse_args()

    tmp_trips = f"_tmp_trips_{args.seed}.trips.xml"
    run_random_trips(args.net, tmp_trips, args.end, args.period, args.seed)
    assign_vehicle_types(tmp_trips, args.output, args.penetration, args.seed)
    os.remove(tmp_trips)
    print(f"Wrote {args.output} at {args.penetration*100:.0f}% AV penetration")


if __name__ == "__main__":
    main()

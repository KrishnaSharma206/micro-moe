"""
Purpose: Runs a single SUMO scenario over TraCI and reports the four PS1 metrics:
         delay, average speed, travel time, queue length.

Usage: python run_scenario.py --net grid.net.xml --route <filename given by generate_routes.py>.rou.xml \
       --penetration <penetration rate> --out <output filename>.json --gui
"""
import argparse
import json
import os
import sys
import xml.etree.ElementTree as ET
import traci

def run(net_file, route_file, tripinfo_file, gui=False):
    binary = "sumo-gui" if gui else "sumo"
    traci.start([
        binary,
        "-n", net_file,
        "-r", route_file,
        "--tripinfo-output", tripinfo_file,
        "--no-step-log", "true",
        "--duration-log.disable", "true",
        "--time-to-teleport", "-1",
    ])

    speed_samples = []      # (num_vehicles_this_step, mean_speed_this_step)
    queue_samples = []      # halted vehicles, summed over all edges, this step
    edge_ids = traci.edge.getIDList()

    try:
        while traci.simulation.getMinExpectedNumber() > 0:
            traci.simulationStep()
            veh_ids = traci.vehicle.getIDList()
            if veh_ids:
                speeds = [traci.vehicle.getSpeed(v) for v in veh_ids]
                speed_samples.append((len(veh_ids), sum(speeds) / len(speeds)))
            halted = sum(traci.edge.getLastStepHaltingNumber(e) for e in edge_ids)
            queue_samples.append(halted)
    finally:
        traci.close()

    # Vehicle-count-weighted average speed across the whole run
    total_veh_seconds = sum(n for n, _ in speed_samples)
    avg_speed = (
        sum(n * s for n, s in speed_samples) / total_veh_seconds
        if total_veh_seconds else 0.0
    )
    avg_queue = sum(queue_samples) / len(queue_samples) if queue_samples else 0.0

    return avg_speed, avg_queue


def parse_tripinfo(tripinfo_file):
    """Pulls delay (timeLoss) and travel time (duration) per completed trip."""
    tree = ET.parse(tripinfo_file)
    trips = tree.getroot().findall("tripinfo")
    if not trips:
        return 0.0, 0.0
    time_losses = [float(t.get("timeLoss")) for t in trips]
    durations = [float(t.get("duration")) for t in trips]
    avg_delay = sum(time_losses) / len(time_losses)
    avg_travel_time = sum(durations) / len(durations)
    return avg_delay, avg_travel_time

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--net", default="grid.net.xml")
    ap.add_argument("--route", required=True)
    ap.add_argument("--penetration", type=float, required=True,
                     help="Recorded in the output for later aggregation")
    ap.add_argument("--out", required=True)
    ap.add_argument("--gui", action="store_true")
    args = ap.parse_args()
    tripinfo_file = args.out.replace(".json", "_tripinfo.xml")
    avg_speed, avg_queue = run(args.net, args.route, tripinfo_file, gui=args.gui)
    avg_delay, avg_travel_time = parse_tripinfo(tripinfo_file)

    result = {
        "penetration": args.penetration,
        "avg_delay_s": round(avg_delay, 3),
        "avg_speed_mps": round(avg_speed, 3),
        "avg_travel_time_s": round(avg_travel_time, 3),
        "avg_queue_length": round(avg_queue, 3),
    }
    with open(args.out, "w") as f:
        json.dump(result, f, indent=2)
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
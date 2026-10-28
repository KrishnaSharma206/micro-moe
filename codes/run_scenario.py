"""
Runs a single SUMO scenario over TraCI and reports the four PS1 metrics:
delay, average speed, travel time, queue length.

Delay and travel time come from SUMO's own tripinfo output (timeLoss and
duration), which is the standard, citable way to report them -- don't
recompute these by hand from TraCI, SUMO's internal accounting is more
accurate. Average speed and queue length are sampled live via TraCI each
step, since those aren't in tripinfo.

Usage:
    python run_scenario.py --net manhattan.net.xml --route routes_50.rou.xml \
        --penetration 0.5 --out results_50.json
"""
import argparse
import json
import os
import sys
import xml.etree.ElementTree as ET

import traci


def run(net_file, route_file, tripinfo_file, gui=False, max_time=3600, step_length=0.5):
    binary = "sumo-gui" if gui else "sumo"
    traci.start([
        binary,
        "-n", net_file,
        "-r", route_file,
        "--tripinfo-output", tripinfo_file,
        "--tripinfo-output.write-unfinished", "true",  # keep vehicles still on the road at cutoff
        "--no-step-log", "true",
        "--duration-log.disable", "true",
        "--time-to-teleport", "-1",  # don't teleport stuck vehicles; they're a real congestion signal
        # Car-following models can produce collisions when tau < step-length
        # (Krauss AV tau = 0.6 s; SUMO's docs also warn CACC collides at 1 s),
        # so the default step is 0.5 s. 'warn' keeps colliding vehicles in place rather
        # than teleporting them, and warnings are silenced to avoid flooding
        # the terminal; collisions are counted below instead.
        "--step-length", str(step_length),
        "--collision.action", "warn",
        "--no-warnings", "true",
    ])

    speed_samples = []      # (num_vehicles_this_step, mean_speed_this_step)
    queue_samples = []      # halted vehicles, summed over all edges, this step
    collisions = 0

    edge_ids = traci.edge.getIDList()

    try:
        # Hard time cap: a congested real network can gridlock and never empty,
        # which would otherwise leave this loop running forever.
        while (traci.simulation.getMinExpectedNumber() > 0
               and traci.simulation.getTime() < max_time):
            traci.simulationStep()
            collisions += traci.simulation.getCollidingVehiclesNumber()

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

    return avg_speed, avg_queue, collisions


def parse_tripinfo(tripinfo_file):
    """Delay (timeLoss) and travel time (duration), averaged over COMPLETED
    trips only. Trips still on the road at the time cap (arrival = -1) are
    counted separately: a high unfinished count signals gridlock/overload."""
    tree = ET.parse(tripinfo_file)
    trips = tree.getroot().findall("tripinfo")
    done = [t for t in trips if float(t.get("arrival", "-1")) >= 0]
    unfinished = len(trips) - len(done)
    if not done:
        return 0.0, 0.0, 0, unfinished
    avg_delay = sum(float(t.get("timeLoss")) for t in done) / len(done)
    avg_travel_time = sum(float(t.get("duration")) for t in done) / len(done)
    return avg_delay, avg_travel_time, len(done), unfinished


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--net", default="manhattan.net.xml")
    ap.add_argument("--route", required=True)
    ap.add_argument("--penetration", type=float, required=True,
                     help="Recorded in the output for later aggregation")
    ap.add_argument("--out", required=True)
    ap.add_argument("--gui", action="store_true")
    ap.add_argument("--step-length", type=float, default=0.5,
                     help="simulation step (s); keep identical across runs you compare")
    ap.add_argument("--max-time", type=int, default=3600,
                     help="Stop the simulation at this time (s) even if vehicles remain")
    args = ap.parse_args()

    tripinfo_file = args.out.replace(".json", "_tripinfo.xml")

    avg_speed, avg_queue, collisions = run(
        args.net, args.route, tripinfo_file, gui=args.gui, max_time=args.max_time,
        step_length=args.step_length)
    avg_delay, avg_travel_time, completed, unfinished = parse_tripinfo(tripinfo_file)

    result = {
        "penetration": args.penetration,
        "avg_delay_s": round(avg_delay, 3),
        "avg_speed_mps": round(avg_speed, 3),
        "avg_travel_time_s": round(avg_travel_time, 3),
        "avg_queue_length": round(avg_queue, 3),
        "completed_trips": completed,
        "unfinished_trips": unfinished,
        "collisions": collisions,
    }
    with open(args.out, "w") as f:
        json.dump(result, f, indent=2)

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

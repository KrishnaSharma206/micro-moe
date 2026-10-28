# micro-moe
Microscopic Simulation and Swarm-Based Cooperative Behaviour of  Autonomous Vehicles in Urban ITS

# Problem Statement

To study effect of AV penetration (0/25/50/75/100%) on
delay, average speed, travel time and queue length, simulated on a real
Midtown Manhattan network from OpenStreetMap, repeated over many random seeds
to build a research dataset.

# Documentation Used
1. SUMO User Documentation: https://sumo.dlr.de/docs/index.html
2. SUMO Tutorials: https://sumo.dlr.de/docs/Tutorials/index.html
3. MATLAB Documentation: https://in.mathworks.com/help/matlab/index.html

# Research Papers referred
1. Zaky, Muhammad. Urban Traffic Simulation Using SUMO Open Source Tools.
2. M. Berrazouane, K. Tong, S. Solmaz, M. Kiers and J. Erhart, "Analysis and Initial Observations on Varying Penetration Rates of Automated Vehicles in Mixed Traffic Flow utilizing SUMO," 2019 IEEE International Conference on Connected Vehicles and Expo (ICCVE)

# Tools Used

1. SUMO
2. TraACI API
3. Python
4. Matlab

# Comparative Evaluation of Autonomous Vehicle Behaviours in Microscopic Traffic Simulations.

Microscopic simulation study of autonomous vehicles (AVs) on a real urban street network, using
**SUMO + TraCI + Python** for simulation and **MATLAB** for analysis. The long-term goal is to design and
evaluate swarm-inspired coordination mechanisms for AVs at intersections and corridors; the first
step is a controlled baseline of how AV penetration changes urban traffic performance.

Two driver models are used for human driven cars and AVs.

The parameters are:

| Parameter | Human | AV |
|---|---|---|
| minGap | 2.5 m | 0.5 m |
| accel | 2.6 m/s^2 | 3.8 m/s^2 |
| deccel | 4.5 m/s^2 | 4.5 m/s^2 |
| sigma (driver imperfection) | 0.5 | 0.0 |
| tau (reaction time) | 1.0 s | 0.6 s |

After running the simulations 200 times for each penetration %. We get the following results:

<img width="2752" height="1801" alt="avg_delay_s_period2_models" src="https://github.com/user-attachments/assets/b15c9897-4a07-4789-a75a-d06f7e73fe57" />

Mean over seeds, 0% to 100% AV, with changes paired by seed:

| Model Set | AV (%) | Avg. Delay (s) | Avg. Speed (m/s) | Avg. Queue Length | Completed Trips |
|---|---|---|---|---|---|
| Krauss Baseline | 0% | 45.2 | 8.1 | 12.4 | 1450 |
| Krauss Baseline | 100% | 33.4 (-26.1%) | 9.7 (+19.8%) | 9.1 (-26.6%) | 1580 |
| EIDM + ACC | 0% | 48.1 | 7.6 | 14.1 | 1410 |
| EIDM + ACC | 100% | 41.3 (+14.1%) | 8.4 (+10.5%) | 11.5 (-18.4%) | 1495 |

The queue-length result goes against the other three metrics (it rises slightly with AV share). The
AV in this baseline is a Krauss car-following vehicle with tighter parameters, so treat these numbers as
specific to that modelling choice; the model-comparison sweep exists to test exactly this.

## Repository layout

```
docs/                       research plan and annotated bibliography
reading/                    tutorials, documentation and videos used
sumo_tutorial/              a 10-minute SUMO + TraCI starter
av_penetration/             the pipeline: network, demand, simulation, sweep, MATLAB analysis
```

## Getting started

1. Install [SUMO](https://sumo.dlr.de/docs/Downloads.php) and set `SUMO_HOME`.
2. `pip install -r requirements.txt` (use a virtual environment, not a conda/ROS base environment).
3. Try [`sumo_tutorial/`](sumo_tutorial/) to check the install end to end.
4. Reproduce AV Penetration following [`av_penetration/README.md`](av_penetration/README.md).

## One-time setup
```bash
./generate_network.sh        # downloads OSM data, writes manhattan.net.xml
```
(Falls back to other Overpass mirrors if the main server times out. Edit `BBOX`
in the script to change the area.)

## Build the dataset
```bash
python sweep.py --seeds 2 --workers 2     # quick test: 10 runs
python sweep.py                           # full: 200 seeds x 5 rates = 1000 runs
```
- `--workers N` runs N simulations in parallel (default: half your CPU cores).
- Resumable: Ctrl+C any time, then re-run the same command to continue.
  Finished runs are skipped; failed runs are retried.
- `--periods 3.0 2.0 1.5` repeats everything at several traffic densities
  (lower period = denser traffic). Multiplies the run count.
- `--keep-files` keeps routes + tripinfo XML for every run (very large).
- `--aggregate-only` rebuilds the CSV from finished runs without simulating.
- Output: `ps1_dataset.csv`, one row per run (seed, period, penetration, the
  four metrics, completed/unfinished trips, collisions, runtime).

Estimating total time: (runtime of one run) x (number of runs) / workers.
Use the quick test above to get the one-run time before launching the full job.

## Compare driver models (human + AV)
`vehicle_models.py` defines the car-following model sets: `krauss` (your original
200-seed baseline), `idm_acc`, `eidm_acc` (human = IDM / Extended IDM, AV = ACC)
and `idm_cacc` (AV = CACC, experimental). Read its header for exactly what is
held equal and which numbers are cited.
```bash
python sweep.py --seeds 2 --workers 2 --model-sets idm_acc            # quick test
python sweep.py --seeds 50 --model-sets idm_acc eidm_acc idm_cacc     # the comparison
python sweep.py --seeds 50 --model-sets idm_acc --av-tau 1.0          # AV headway sensitivity
python sweep.py --seeds 50 --model-sets idm_cacc --step-length 0.25   # if CACC collides
```
- Existing Krauss runs are reused, not re-run. Seeds 1..N have the same trips
  and the same AV assignment in every model set, so models compare seed-by-seed.
- Anything non-default (`--av-tau`, `--step-length`) becomes its own labelled
  variant (e.g. `idm_acc_avtau1`), so variants never mix with the default runs.
- Keep `--step-length` identical across the models you compare, and check the
  `collisions` and `unfinished_trips` columns before trusting a model set.

## Analyze (MATLAB)
`cd` into the project folder, then run `analyze.m`. It produces, per traffic
density: one figure per metric with all model sets overlaid (mean ± 95% CI), box
plots per model in `figures/`, plus
`summary.csv` (n, mean, sd, CI, paired difference vs 0% AV with its CI,
% change, p-value label). Changes vs. the 0% baseline are *paired by seed*.

## Scripts
| File | Purpose |
|---|---|
| `generate_network.sh` | OSM download + `netconvert` -> `manhattan.net.xml` |
| `generate_routes.py` | random trips (`randomTrips.py`) + AV/human type assignment |
| `run_scenario.py` | one SUMO run over TraCI; outputs the four metrics + diagnostics |
| `vehicle_models.py` | car-following model sets (human / AV vehicle types) |
| `sweep.py` | parallel, resumable multi-seed, multi-model sweep -> `dataset.csv` |
| `analyze.m` | MATLAB statistics + figures |

## Method notes for the paper
- Vehicle types: see `vehicle_models.py`. Krauss set: human = Level 0, AV = Level 5,
  Sadid & Antoniou (2023), Table 4. ACC/CACC sets: AV headway 1.3 s after Syed &
  Hasan; controller gains left at SUMO defaults
  (Milanes & Shladover 2014; Xiao et al. 2017). A conservative Krauss alternative
  (Amini et al. 2023, arXiv:2301.11083) is noted in `vehicle_models.py`.
- Delay = SUMO `timeLoss`; travel time = `duration`; both averaged over completed
  trips. Queue = halted vehicles summed over all edges, averaged over time.
- Simulation step 0.5 s (Krauss can collide when tau < step; AV tau = 0.6 s).
  Hard stop at 3600 s; check `unfinished_trips` and `collisions` columns.
- Seed `s` fixes the trip demand AND the AV assignment draws, so AV sets are
  nested across penetration rates and every seed is a matched comparison.
- Report the traffic density (`--period`) and network area in the methodology.

## Reproducibility notes

- Every run is seeded, the same seed gives the same trips and the same AV assignment at every penetration
  rate, so comparisons are paired
- The street network comes from OpenStreetMap and changes over time. Commit the exact
  `manhattan_bbox.osm.xml` / `manhattan.net.xml` you simulated (they are not git-ignored)
- Car-following parameters are cited in [`av_penetration/vehicle_models.py`](av_penetration/vehicle_models.py).
  Where a value is an assumption rather than a measurement (for example the 1.3 s ACC headway)

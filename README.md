# micro-moe
Microscopic Simulation and Swarm-Based Cooperative Behaviour of  Autonomous Vehicles in Urban ITS

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

## Reproducibility notes

- Every run is seeded, the same seed gives the same trips and the same AV assignment at every penetration
  rate, so comparisons are paired
- The street network comes from OpenStreetMap and changes over time. Commit the exact
  `manhattan_bbox.osm.xml` / `manhattan.net.xml` you simulated (they are not git-ignored)
- Car-following parameters are cited in [`av_penetration/vehicle_models.py`](av_penetration/vehicle_models.py).
  Where a value is an assumption rather than a measurement (for example the 1.3 s ACC headway)

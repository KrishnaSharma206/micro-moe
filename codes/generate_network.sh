#!/usr/bin/env bash
# Purpose: Generates a 4x4 grid network.
# Requirements: SUMO's netgenerate binary.
set -e

netgenerate --grid \
    --grid.number=4 \
    --grid.length=200 \
    --default.lanenumber=2 \
    --default.speed=13.9 \
    -o grid.net.xml

echo "Wrote grid.net.xml"

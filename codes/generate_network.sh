#!/usr/bin/env bash
# Downloads a real street network (Midtown Manhattan) from OpenStreetMap and
# converts it into a SUMO network.
#
# Bounding box: roughly W34th St to W57th St, between 6th Ave and Lexington
# Ave. Adjust BBOX below (https://www.openstreetmap.org/export or
# bboxfinder.com) to use a different area. A smaller box downloads faster and
# is less likely to hit Overpass timeouts.
#
# Requires internet access, curl, and $SUMO_HOME set.
set -e

if [ -z "$SUMO_HOME" ]; then
    echo "SUMO_HOME is not set — see the environment setup steps." >&2
    exit 1
fi

# lon_min,lat_min,lon_max,lat_max  (osmGet order)
BBOX="-73.9860,40.7480,-73.9750,40.7620"
OSM_FILE="manhattan_bbox.osm.xml"

IFS=',' read -r LON_MIN LAT_MIN LON_MAX LAT_MAX <<< "$BBOX"

valid_osm() {
    [ -s "$1" ] && grep -q "<node" "$1"
}

download_with_curl() {
    # Overpass bbox order is south,west,north,east
    local query="[out:xml][timeout:120];(way[\"highway\"](${LAT_MIN},${LON_MIN},${LAT_MAX},${LON_MAX});>;);out meta;"
    local mirrors=(
        "https://overpass-api.de/api/interpreter"
        "https://overpass.kumi.systems/api/interpreter"
        "https://lz4.overpass-api.de/api/interpreter"
    )
    for url in "${mirrors[@]}"; do
        echo "Trying $url ..."
        if curl -fsSL --max-time 180 --data-urlencode "data=${query}" \
                -o "$OSM_FILE" "$url" && valid_osm "$OSM_FILE"; then
            echo "Downloaded OSM data from $url"
            return 0
        fi
        echo "  failed, trying next mirror"
        rm -f "$OSM_FILE"
    done
    return 1
}

if valid_osm "$OSM_FILE"; then
    echo "$OSM_FILE already exists, skipping download."
else
    echo "Downloading OSM data for bbox $BBOX ..."
    if ! python3 "$SUMO_HOME/tools/osmGet.py" --bbox "$BBOX" -p manhattan \
         || ! valid_osm "$OSM_FILE"; then
        echo "osmGet.py failed; falling back to direct Overpass mirrors ..."
        rm -f "$OSM_FILE"
        if ! download_with_curl; then
            echo "All Overpass servers failed. Wait a few minutes and re-run, or" >&2
            echo "shrink BBOX, or export the area manually from" >&2
            echo "openstreetmap.org/export and save it as $OSM_FILE." >&2
            exit 1
        fi
    fi
fi

echo "Converting to a SUMO network ..."
netconvert \
    --osm-files "$OSM_FILE" \
    -o manhattan.net.xml \
    --keep-edges.by-vclass passenger \
    --geometry.remove \
    --roundabouts.guess \
    --ramps.guess \
    --junctions.join \
    --tls.guess-signals \
    --tls.discard-simple \
    --tls.join \
    --remove-edges.isolated

echo "Wrote manhattan.net.xml"

#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Repeat the Nanjing specification in other Chinese cities.

The paper's main experiment is one city on one date.  This driver applies the
*same* pipeline -- same grid resolution, same urban and cloud masks, same
vulnerability definition, same estimator and contamination protocol -- to a set
of cities that sample different climates and urban forms.  Nothing about the
analysis is tuned per city; only the bounding box, the UTM zone and the Landsat
scene change.  The scene is the one with the largest footprint coverage of the
box among scenes below 30% cloud in the search window, ties broken by cloud
cover: cloud alone is a poor selector, because a nearly clear scene can still
clip the study area at a WRS-2 path boundary.

Inputs are fetched, not shipped: ``fetch_inputs.py`` pulls the four Landsat
bands for each city from the Planetary Computer and the GHS-POP / GHS-BUILT-S
tiles come from the JRC portal.  See ``../data/README.md``.

    python run_cities.py --raw ../data/raw --out outputs --proxy http://127.0.0.1:7897
    python run_cities.py --cities nanjing,wuhan --skip-fetch

Each city writes ``outputs/city_<name>/{cells.csv,conditions.csv,draws.csv,
grid_metadata.json,run_metadata.json}``; ``summarise_cities.py`` collapses the
condition tables into one comparison table.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import subprocess
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
GHS_BASE = ("https://jeodpp.jrc.ec.europa.eu/ftp/jrc-opendata/GHSL/"
            "{product}_GLOBE_R2023A/{product}_E2020_GLOBE_R2023A_4326_30ss/"
            "V1-0/tiles/{product}_E2020_GLOBE_R2023A_4326_30ss_V1_0_{tile}.zip")

# name: (west, south, east, north) in EPSG:4326.  The boxes are 0.5 x 0.3
# degrees, the same size as the Nanjing box, centred on each urban core.
CITIES = {
    "nanjing":   (118.70, 31.92, 119.20, 32.22),
    "wuhan":     (114.10, 30.40, 114.60, 30.70),
    "hefei":     (117.10, 31.65, 117.60, 31.95),
    "hangzhou":  (120.00, 30.15, 120.50, 30.45),
    "shanghai":  (121.25, 31.05, 121.75, 31.35),
    "beijing":   (116.20, 39.75, 116.70, 40.05),
    "xian":      (108.75, 34.15, 109.25, 34.45),
    "zhengzhou": (113.45, 34.55, 113.95, 34.85),
}


def utm_zone(bbox):
    lon = 0.5 * (bbox[0] + bbox[2])
    return int(math.floor((lon + 180.0) / 6.0)) + 1


def ghs_tile(bbox):
    """GHSL 30 arc-second tile name covering the box (10 x 10 degree tiles).

    Rows are numbered from the north: R1 covers 79.1-89.1 N and the numbering
    increases southward, so R6 covers 29.1-39.1 N and R5 covers 39.1-49.1 N.
    Columns are numbered from the west: C30 covers 109.99-119.99 E.
    """
    lon = 0.5 * (bbox[0] + bbox[2])
    lat = 0.5 * (bbox[1] + bbox[3])
    col = int(math.floor((lon - 109.99) / 10.0)) + 30
    row = int(math.floor((89.0995 - lat) / 10.0)) + 1
    return "R{}_C{}".format(row, col)


def run(cmd):
    print("$ " + " ".join(cmd), flush=True)
    subprocess.run(cmd, check=True)


def download(url, out_zip, proxy):
    handlers = [urllib.request.ProxyHandler({"http": proxy, "https": proxy})] if proxy else []
    opener = urllib.request.build_opener(*handlers)
    opener.addheaders = [("User-Agent", "thermal-equity-data-integrity/0.3")]
    print("GET", url, flush=True)
    with opener.open(url, timeout=600) as r, open(out_zip, "wb") as fh:
        while True:
            chunk = r.read(1 << 20)
            if not chunk:
                break
            fh.write(chunk)


def ensure_ghs(raw, tile, proxy, bbox):
    paths = {}
    for product in ("GHS_POP", "GHS_BUILT_S"):
        name = "{}_E2020_GLOBE_R2023A_4326_30ss_V1_0_{}.tif".format(product, tile)
        tif = os.path.join(raw, name)
        paths[product] = tif
        if not os.path.exists(tif):
            zip_path = tif[:-4] + ".zip"
            url = GHS_BASE.format(product=product, tile=tile)
            download(url, zip_path, proxy)
            import zipfile
            with zipfile.ZipFile(zip_path) as zf:
                zf.extractall(raw)
            if not os.path.exists(tif):
                raise SystemExit("{} missing from {}".format(name, zip_path))
        # A tile that does not cover the box silently yields an empty grid, so
        # check the geometry before the three-stage pipeline runs.
        import rasterio
        with rasterio.open(tif) as ds:
            b = ds.bounds
            lon = 0.5 * (bbox[0] + bbox[2])
            lat = 0.5 * (bbox[1] + bbox[3])
            if not (b.left <= lon <= b.right and b.bottom <= lat <= b.top):
                raise SystemExit(
                    "GHS tile {} does not cover the box centre ({:.3f}, {:.3f}); "
                    "bounds are {:.3f}-{:.3f} E, {:.3f}-{:.3f} N".format(
                        tile, lon, lat, b.left, b.right, b.bottom, b.top))
    return paths


def scene_json(raw, city):
    path = os.path.join(raw, "scene_{}.json".format(city))
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--raw", default=os.path.join("..", "data", "raw"))
    ap.add_argument("--out", default="outputs")
    ap.add_argument("--cities", default=",".join(CITIES))
    ap.add_argument("--start", default="2021-04-01")
    ap.add_argument("--end", default="2021-10-31")
    ap.add_argument("--max-cloud", type=float, default=30.0,
                    help="scene-level cloud ceiling; footprint coverage is "
                         "ranked first, so clear scenes still win where they exist")
    ap.add_argument("--min-built", default="0.05")
    ap.add_argument("--repeats", type=int, default=30)
    ap.add_argument("--priority", default="heat")
    ap.add_argument("--model", default="rf")
    ap.add_argument("--proxy", default=None)
    ap.add_argument("--skip-fetch", action="store_true",
                    help="use rasters already in --raw")
    args = ap.parse_args(argv)

    os.makedirs(args.raw, exist_ok=True)
    os.makedirs(args.out, exist_ok=True)
    summary = []

    for city in [c.strip() for c in args.cities.split(",") if c.strip()]:
        if city not in CITIES:
            raise SystemExit("unknown city {!r}; known: {}".format(city, ", ".join(CITIES)))
        bbox = CITIES[city]
        zone = utm_zone(bbox)
        tile = ghs_tile(bbox)
        cdir = os.path.join(args.out, "city_" + city)
        os.makedirs(cdir, exist_ok=True)
        # A crashed or interrupted earlier run leaves tables behind; mixing a
        # fresh grid with stale conditions is exactly the kind of silent
        # mismatch the comparison table must not contain.
        for stale in ("conditions.csv", "draws.csv", "run_metadata.json", "city.json"):
            p = os.path.join(cdir, stale)
            if os.path.exists(p):
                os.remove(p)
        print("\n== {}  bbox={}  utm={}  ghs={}".format(city, bbox, zone, tile), flush=True)

        if not args.skip_fetch:
            fetch = [sys.executable, os.path.join(HERE, "fetch_inputs.py"),
                     "--outdir", args.raw,
                     "--bbox", *[str(v) for v in bbox],
                     "--start", args.start, "--end", args.end,
                     "--max-cloud", str(args.max_cloud), "--tag", city]
            if args.proxy:
                fetch += ["--proxy", args.proxy]
            run(fetch)
            meta = scene_json(args.raw, city)
            ghs = ensure_ghs(args.raw, tile, args.proxy, bbox)
        else:
            meta = scene_json(args.raw, city)
            ghs = ensure_ghs(args.raw, tile, args.proxy, bbox)

        if meta is None:
            raise SystemExit("no scene metadata for {}; run without --skip-fetch".format(city))
        prefix = city  # fetch_inputs writes <tag>__<BAND>.tif

        grid = [sys.executable, os.path.join(HERE, "build_grid.py"),
                "--lst", os.path.join(args.raw, prefix + "__ST_B10.tif"),
                "--red", os.path.join(args.raw, prefix + "__SR_B4.tif"),
                "--nir", os.path.join(args.raw, prefix + "__SR_B5.tif"),
                "--qa", os.path.join(args.raw, prefix + "__QA_PIXEL.tif"),
                "--max-cloud-frac", "0.10",
                "--pop", ghs["GHS_POP"], "--built", ghs["GHS_BUILT_S"],
                "--min-built", args.min_built,
                "--sr-scale", "2.75e-05", "--sr-offset", "-0.2",
                "--utm-zone", str(zone),
                "--bbox", *[str(v) for v in bbox], "--res", "1000",
                "--out", os.path.join(cdir, "cells.csv"),
                "--meta", os.path.join(cdir, "grid_metadata.json")]
        run(grid)

        model = [sys.executable, os.path.join(HERE, "model_and_poison.py"),
                 "--cells", os.path.join(cdir, "cells.csv"),
                 "--out", os.path.join(cdir, "conditions.csv"),
                 "--meta", os.path.join(cdir, "run_metadata.json"),
                 "--draws-out", os.path.join(cdir, "draws.csv"),
                 "--contamination", "0.05", "0.10", "0.15",
                 "--delta", "1", "2", "3", "--main-delta", "2", "--sweep-rate", "0.10",
                 "--trees", "300", "--seed", "7", "--repeats", str(args.repeats),
                 "--priority", args.priority, "--model", args.model]
        run(model)

        with open(os.path.join(cdir, "city.json"), "w", encoding="utf-8",
                  newline="\n") as fh:
            json.dump(dict(city=city, bbox=list(bbox), utm_zone=zone,
                           ghs_tile=tile, scene=meta.get("id"),
                           scene_cloud_pct=meta.get("cloud_cover_pct"),
                           scene_datetime=meta.get("datetime"),
                           min_built=float(args.min_built),
                           priority=args.priority, model=args.model,
                           repeats=args.repeats), fh, indent=2)
        summary.append(city)

    print("\nfinished: " + ", ".join(summary))
    print("run summarise_cities.py to build the comparison table")
    return 0


if __name__ == "__main__":
    sys.exit(main())

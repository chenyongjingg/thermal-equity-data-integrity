# -*- coding: utf-8 -*-
"""Identify the Landsat scene used in the paper and print its metadata.

Queries the public STAC endpoint for Landsat Collection 2 Level-2 and reports
the scene that matches the manuscript: 1 August 2021 over the Nanjing study
area.  This does not download imagery; it only proves which scene the paper
means, so that a reader can check the acquisition date and cloud cover against
the USGS record.

    python find_scene.py
    python find_scene.py --date 2021-08-01 --bbox 118.70 31.92 119.20 32.22

Output is JSON on stdout so it can be diffed between runs.
"""

import argparse
import json
import sys
import urllib.request

STAC = "https://earth-search.aws.element84.com/v1/search"
COLLECTION = "landsat-c2-l2"


def query(datetime_str, bbox, max_cloud):
    body = {
        "collections": [COLLECTION],
        "bbox": bbox,
        "datetime": datetime_str,
        "limit": 100,
        "query": {"eo:cloud_cover": {"lt": max_cloud}},
    }
    req = urllib.request.Request(
        STAC,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json", "Accept": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def summarize(feature):
    p = feature.get("properties", {})
    assets = feature.get("assets", {})
    def href(key):
        return assets.get(key, {}).get("href")
    return {
        "id": feature.get("id"),
        "datetime": p.get("datetime"),
        "cloud_cover_pct": p.get("eo:cloud_cover"),
        "platform": p.get("platform"),
        "wrs_path": p.get("landsat:wrs_path"),
        "wrs_row": p.get("landsat:wrs_row"),
        "collection_number": p.get("landsat:collection_number"),
        "processing_level": p.get("landsat:processing_level"),
        "sun_elevation": p.get("view:sun_elevation"),
        "assets": {
            "st_b10": href("lwir11") or href("ST_B10"),
            "sr_b4": href("red") or href("SR_B4"),
            "sr_b5": href("nir08") or href("SR_B5"),
        },
        "_asset_keys": sorted(assets.keys()),
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--date", default="2021-08-01",
                    help="acquisition date, YYYY-MM-DD (default: 2021-08-01)")
    ap.add_argument("--bbox", nargs=4, type=float,
                    default=[118.70, 31.92, 119.20, 32.22],
                    metavar=("W", "S", "E", "N"))
    ap.add_argument("--max-cloud", type=float, default=100.0)
    args = ap.parse_args(argv)

    dt = "{}T00:00:00Z/{}T23:59:59Z".format(args.date, args.date)
    data = query(dt, args.bbox, args.max_cloud)
    feats = data.get("features", [])
    out = {
        "endpoint": STAC,
        "query": {"datetime": dt, "bbox": args.bbox, "collection": COLLECTION},
        "n_returned": len(feats),
        "scenes": [summarize(f) for f in feats],
    }
    json.dump(out, sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")
    if not feats:
        sys.stderr.write("No scene returned for that date and extent.\n")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

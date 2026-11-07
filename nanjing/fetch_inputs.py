# -*- coding: utf-8 -*-
"""Download the Landsat bands for the study area from the Planetary Computer.

The USGS archive on AWS is a requester-pays bucket, and the Azure mirror is
private without a signature.  Both are reachable from the public STAC API of
the Microsoft Planetary Computer, which issues short-lived read tokens.  This
script asks for the token, locates the scene, and copies only the window that
covers the study area (about 20 MB instead of 360 MB for the full bands).

    python fetch_inputs.py --outdir ../data/raw

Writes ``LC08_*_ST_B10.tif``, ``LC08_*_SR_B4.tif`` and ``LC08_*_SR_B5.tif``
with their georeferencing intact.  The GHS-POP tile is downloaded separately
from the JRC portal; see ``../data/README.md``.
"""

import argparse
import json
import os
import sys
import urllib.request

import rasterio
from rasterio.warp import transform_bounds
from rasterio.windows import from_bounds

STAC = "https://planetarycomputer.microsoft.com/api/stac/v1/search"
TOKEN = "https://planetarycomputer.microsoft.com/api/sas/v1/token/landsat-c2-l2"
BANDS = {"lwir11": "ST_B10", "red": "SR_B4", "nir08": "SR_B5", "qa_pixel": "QA_PIXEL"}


def _opener(proxy):
    handlers = [urllib.request.ProxyHandler({"http": proxy, "https": proxy})] if proxy else []
    return urllib.request.build_opener(*handlers)


def find_scene(bbox, start, end, proxy, max_cloud=100.0):
    """Least cloudy scene over [start, end] (inclusive dates, UTC)."""
    body = {
        "collections": ["landsat-c2-l2"],
        "bbox": bbox,
        "datetime": "{}T00:00:00Z/{}T23:59:59Z".format(start, end),
        "limit": 100,
    }
    req = urllib.request.Request(
        STAC, data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"})
    with _opener(proxy).open(req, timeout=120) as r:
        feats = json.load(r).get("features", [])
    if not feats:
        raise SystemExit("no scene for {} in {}..{}".format(bbox, start, end))
    feats.sort(key=lambda f: f["properties"].get("eo:cloud_cover", 100))
    keep = [f for f in feats if f["properties"].get("eo:cloud_cover", 100) <= max_cloud]
    if not keep:
        raise SystemExit("no scene below {}% cloud in {}..{}".format(max_cloud, start, end))
    return keep[0]


def token(proxy):
    with _opener(proxy).open(TOKEN, timeout=120) as r:
        return json.load(r)["token"]


def crop(url, bbox, out_path, gdal_opts):
    with rasterio.Env(**gdal_opts):
        with rasterio.open("/vsicurl/" + url) as ds:
            bounds = transform_bounds("EPSG:4326", ds.crs, *bbox)
            win = from_bounds(*bounds, transform=ds.transform)
            data = ds.read(1, window=win)
            tr = ds.window_transform(win)
            profile = ds.profile.copy()
            profile.update(driver="GTiff", height=data.shape[0],
                           width=data.shape[1], count=1,
                           transform=tr, compress="deflate")
            with rasterio.open(out_path, "w", **profile) as out:
                out.write(data, 1)
    return data.shape


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--outdir", default=os.path.join("..", "data", "raw"))
    ap.add_argument("--bbox", nargs=4, type=float,
                    default=[118.70, 31.92, 119.20, 32.22], metavar=("W", "S", "E", "N"))
    ap.add_argument("--date", default=None,
                    help="single day to search (default 2021-08-01)")
    ap.add_argument("--start", default=None, help="first day of the search window")
    ap.add_argument("--end", default=None, help="last day of the search window")
    ap.add_argument("--max-cloud", type=float, default=100.0,
                    help="reject scenes with more cloud cover than this")
    ap.add_argument("--tag", default=None,
                    help="filename prefix for the outputs (defaults to the scene id)")
    ap.add_argument("--pad", type=float, default=0.02,
                    help="degrees of margin so the resampling window is covered")
    ap.add_argument("--proxy", default=None,
                    help="HTTP proxy for a restricted network, e.g. http://127.0.0.1:7897")
    args = ap.parse_args(argv)

    w, s, e, n = args.bbox
    query_bbox = [w - args.pad, s - args.pad, e + args.pad, n + args.pad]
    os.makedirs(args.outdir, exist_ok=True)

    start = args.start or args.date or "2021-08-01"
    end = args.end or args.date or start
    feat = find_scene(query_bbox, start, end, args.proxy, args.max_cloud)
    tok = token(args.proxy)
    print("scene:", feat["id"], "cloud:", feat["properties"].get("eo:cloud_cover"))

    gdal_opts = dict(GDAL_HTTP_TIMEOUT="120",
                     GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR",
                     CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".TIF,.tif")
    if args.proxy:
        gdal_opts["GDAL_HTTP_PROXY"] = args.proxy

    for key, band in BANDS.items():
        href = feat["assets"][key]["href"]
        url = href + ("&" if "?" in href else "?") + tok
        prefix = args.tag or feat["id"]
        out = os.path.join(args.outdir, "{}__{}.tif".format(prefix, band))
        shape = crop(url, query_bbox, out, gdal_opts)
        print("wrote", out, shape)

    meta_name = "landsat_scene.json" if not args.tag else "scene_{}.json".format(args.tag)
    with open(os.path.join(args.outdir, meta_name), "w", encoding="utf-8") as fh:
        json.dump({"id": feat["id"], "cloud_cover_pct": feat["properties"].get("eo:cloud_cover"),
                   "datetime": feat["properties"].get("datetime"),
                   "bbox": query_bbox, "search": [start, end]}, fh, indent=2)
    return 0


if __name__ == "__main__":
    sys.exit(main())

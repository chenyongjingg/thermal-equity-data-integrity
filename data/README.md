# data/

Raw rasters are **not** distributed here: both inputs are large and are better
obtained from their providers, which also keeps the provenance unambiguous.

| Layer | Product | Where |
|---|---|---|
| Land surface temperature, red, NIR | Landsat 8 Collection 2 Level-2, scene `LC08_L2SP_120038_20210801_02_T1` | USGS EarthExplorer <https://earthexplorer.usgs.gov>; the scene is also indexed by the public STAC endpoint `earth-search.aws.element84.com/v1` (collection `landsat-c2-l2`) |
| Population | GHS-POP R2023A, epoch 2020, 30 arc-seconds | JRC Global Human Settlement Layer <https://ghsl.jrc.ec.europa.eu> |
| Built-up surface (optional) | GHS-BUILT-S R2023A | same portal |

Put downloaded files anywhere (for example `data/raw/`) and pass their paths to
`nanjing/build_grid.py` or set `LST`, `RED`, `NIR`, `POP` before `make nanjing`.
`data/raw/` is git-ignored.

Derived cell-level tables are produced by the pipeline, not shipped; see the
note in the repository README.

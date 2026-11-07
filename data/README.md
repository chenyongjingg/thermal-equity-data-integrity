# data/

Raw rasters are **not** distributed here: both inputs are large and are better
obtained from their providers, which also keeps the provenance unambiguous.

| Layer | Product | Where |
|---|---|---|
| Land surface temperature, red, NIR, QA | Landsat 8 Collection 2 Level-2, scene `LC08_L2SP_120038_20210801_02_T1` (ST_B10, SR_B4, SR_B5, QA_PIXEL) | `nanjing/fetch_inputs.py` slices the study-area window from the Microsoft Planetary Computer STAC endpoint; the same scene is indexed by `earth-search.aws.element84.com/v1` and downloadable from USGS EarthExplorer <https://earthexplorer.usgs.gov> |
| Population | GHS-POP R2023A, epoch 2020, 30 arc-seconds | JRC Global Human Settlement Layer <https://ghsl.jrc.ec.europa.eu> |
| Built-up surface | GHS-BUILT-S R2023A, epoch 2020, 30 arc-seconds | same portal |

The JRC products are tiled; the tile covering Nanjing is
`GHS_*_E2020_GLOBE_R2023A_4326_30ss_V1_0_R6_C30` (110–120° E, 29.1–39.1° N).

Put downloaded files anywhere (for example `data/raw/`) and pass their paths to
`nanjing/build_grid.py`, or set `LST`, `RED`, `NIR`, `QA`, `POP` and `BUILT`
before `python run.py nanjing`. `data/raw/` is git-ignored.

The derived cell-level tables from the paper's run are committed under
`nanjing/results/` for inspection; the raw rasters are not, so they can be
regenerated but not audited from this repository alone.

# thermal-equity-data-integrity

Code and derived data for **“Data Integrity and Thermal Equity in Urban Forest
Management: How Illicit Data Markets Distort AI-Assisted Heat Mitigation”**
(Ziying Xue, Yongjin Chen, Songze Zhu — People's Public Security University of
China).

The paper asks what happens to a planting priority list when the labels that
train it are deliberately distorted in one direction. This repository contains
the two pieces of evidence that can be executed:

| Directory | What it is | Runnable |
|---|---|---|
| `synthetic/` | 600-cell synthetic city, 30 seeds, directional vs random label contamination. Produces **Figure S1** and **Table S1** of the paper. | **Yes** — bit-for-bit, verified by `synthetic/CHECKSUMS.txt` |
| `nanjing/` | The 1-km grid pipeline behind **Section 4.4**, **Table 2** and **Figures 3–4**: raster ingestion, urban mask, random-forest priority model, label contamination, metrics, figures. | **Yes** — after one download step; the committed tables in `nanjing/results/` are the output of this code |

## Quick start

```bash
pip install -r requirements.txt      # or: conda env create -f environment.yml

python run.py synthetic   # regenerates the synthetic results and verifies checksums (~3 min)
python run.py test        # end-to-end smoke test of the Nanjing pipeline on tiny rasters
python run.py checksums   # verify the synthetic CSVs and the committed Nanjing tables
python run.py nanjing     # the paper's specification; needs the six env vars below
```

`run.py` is the canonical entry point because `make` is not installed by
default on Windows. The `Makefile` wraps the same commands for POSIX users; it
is a convenience, not a second implementation.

## Reproducing the Nanjing experiment (Table 2, Figures 3–4)

Two public datasets, four Landsat bands, no restricted input. The window that
covers the study area is about 19 MB, so it is fetched rather than downloaded as
full scenes:

```bash
cd nanjing
python fetch_inputs.py --outdir ../data/raw         # ST_B10, SR_B4, SR_B5, QA_PIXEL
# GHS-POP and GHS-BUILT-S tiles from the JRC portal, see ../data/README.md
```

Then either set the environment variables and run the entry point

```bash
export LST=../data/raw/LC08_L2SP_120038_20210801_02_T1__ST_B10.tif
export RED=../data/raw/LC08_L2SP_120038_20210801_02_T1__SR_B4.tif
export NIR=../data/raw/LC08_L2SP_120038_20210801_02_T1__SR_B5.tif
export QA=../data/raw/LC08_L2SP_120038_20210801_02_T1__QA_PIXEL.tif
export POP=../data/raw/GHS_POP_E2020_GLOBE_R2023A_4326_30ss_V1_0_R6_C30.tif
export BUILT=../data/raw/GHS_BUILT_S_E2020_GLOBE_R2023A_4326_30ss_V1_0_R6_C30.tif
cd .. && python run.py nanjing
```

or run the whole reported matrix — three urban-mask definitions and the
population-weighted priority variant — with `sh nanjing/rerun_all.sh` from
inside `nanjing/` (about 25 min, mostly random-forest fits).

The robustness runs are separate drivers because they change one input at a
time and cost real time: `sh run_models.sh` (four estimators, ~35 min),
`python run_cities.py` (eight cities, downloads one Landsat window per city),
`python run_sensitivity.py` (six grid/seed/threshold configurations, ~2 h).
Each is described in `nanjing/README.md`.

### What the reported run is

| Setting | Value |
|---|---|
| Study area | Nanjing main urban area, 118.70–119.20° E, 31.92–32.22° N |
| Grid | 1 km, UTM zone 50N (EPSG:32650) |
| LST | Landsat 8 C2 L2 `LC08_L2SP_120038_20210801_02_T1`, 1 Aug 2021, cloud 12.86% |
| Urban mask | GHS-BUILT-S R2023A, built fraction ≥ 0.05 (0.02 / 0.10 as sensitivity) |
| Cloud filter | cell retained when ≤ 10% of its Landsat pixels carry a QA_PIXEL flag |
| Population | GHS-POP R2023A, 2020 epoch, 30 arc-seconds, treated as density |
| Vulnerable cell | population ≥ P70 **and** NDVI ≤ median |
| Model | random forest, 300 trees, `min_samples_leaf=2`, `n_jobs=1`, seed 7 |
| Priority | predicted LST (the `heat` variant); `heat_x_pop` reported as a sensitivity |
| Contamination | 5 / 10 / 15% of training labels, ΔT = 1 / 2 / 3 °C, 30 draws per condition |

### Results shipped with the code

`nanjing/results/conditions_heat_m0.05_r30.csv` is the file Table 2 is
built from:

| Condition | Rate | ΔT | Dropped (%) | Jaccard | ρ | Bias (°C) |
|---|---|---|---|---|---|---|
| Clean | 0 | — | 0.0 | 1.000 | 0.64 | 0.03 |
| Directional | 10 | 2 | 35.2 | 0.686 | 0.60 | −0.82 |
| Random (control) | 10 | 2 | 9.0 | 0.850 | 0.64 | −0.17 |

727 analysis cells, 162 vulnerable, clean top decile 73 cells of which 52% are
vulnerable. Under a population-weighted priority (`predicted heat × population`)
the drop-out rate is 0.0% and the Jaccard overlap 1.000 at every contamination
rate, because the ranking is dominated by population variance; that null result
is reported in Section 4.4 and is in
`nanjing/results/conditions_heat_x_pop_r30.csv`.

### Robustness runs

Four further sets of runs change one part of the design at a time. They are
described in the Supplementary Materials of the paper and are all shipped here.

| Check | What changes | Driver | Output |
|---|---|---|---|
| Estimator family | random forest → gradient boosting, ridge, k-nearest neighbours | `run_models.sh` | `model_summary.csv` (**Table S2**) |
| Cities | the same protocol in seven further Chinese cities, scene chosen by footprint coverage | `run_cities.py` | `city_summary.csv`, `cities/` (**Table S3**), `Figure_S2` |
| Grid, seeds and thresholds | 500 m and 2 km grids, estimator seeds 13 and 21, two other vulnerable-set definitions, planting budgets of the top 5% and 20% | `run_sensitivity.py` | `sensitivity_summary.csv` (**Table S4**) |
| Draw-level uncertainty | 95% t intervals per condition, Welch intervals for directional minus random | `uncertainty.py` | `uncertainty_nanjing*.csv` (**Table S5**) |
| Placebo arm | the same rate and shift aimed at the non-vulnerable complement | `model_and_poison.py --placebo-out` | `placebo_heat_m0.05_r30.csv` |

## What is and is not in this repository

- **Included:** all analysis code; the synthetic results; the Nanjing
  cell-level grid, condition tables, run metadata and figures under
  `nanjing/results/`; the scene identification; and the four robustness sets
  (estimators, eight cities, design choices, draw-level intervals) with the
  per-city grids and scene metadata under `nanjing/results/cities/`.
- **Not included:** the raw satellite and population rasters — large, and better
  obtained from the providers, which keeps their provenance unambiguous.
  `data/raw/` is git-ignored.
- The Nanjing tables in `nanjing/results/` were produced by `nanjing/rerun_all.sh`
  on the machine described in `nanjing/results/README.md`, whose
  `CHECKSUMS.txt` records the MD5 of every shipped table. If your run produces a
  different cell count, the built-up mask or the raster versions differ, not the
  analysis logic; `build_grid.py` prints every cell it drops and why.

## Mapping to the paper

| Paper element | File |
|---|---|
| Table 2 (experiment results) | `nanjing/results/conditions_heat_m0.05_r30.csv` |
| Figure 3 (composition and coupling at the main rate) | `nanjing/results/Figure_3.png` |
| Figure 4 (dose–response and shift size) | `nanjing/results/Figure_4.png` |
| Urban-mask and priority sensitivities (§4.4) | `nanjing/results/conditions_heat_m0.02_r30.csv`, `conditions_heat_m0.10_r30.csv`, `conditions_heat_x_pop_r30.csv` |
| Figure S1 (synthetic replication) | `synthetic/Figure_S1.png` |
| Table S1 (per-seed results) | `synthetic/results_per_seed.csv` |
| Table S2 (four estimators) | `nanjing/results/model_summary.csv` |
| Table S3 (eight cities) | `nanjing/results/city_summary.csv` |
| Figure S2 (cities, 95% intervals) | `nanjing/results/Figure_S2.png` |
| Table S4 (resolution, seed, thresholds) | `nanjing/results/sensitivity_summary.csv` |
| Table S5 (draw-level intervals and contrasts) | `nanjing/results/uncertainty_nanjing.csv`, `uncertainty_nanjing_contrasts.csv` |

## Reproducibility notes

- The random forest is fitted with `n_jobs = 1`. Parallel prediction
  accumulates in completion order, which changes the last digits of the
  predicted values and therefore the CSVs. This is the one setting that makes
  “fixed seed” mean “identical file”; do not change it.
- Every CSV is written with `lineterminator="\n"` and every metadata JSON with
  `newline="\n"`, so MD5 sums do not depend on the operating system.
  `.gitattributes` marks the CSVs `-text` so git never rewrites them on checkout;
  the JSONs are already LF and `* text=auto eol=lf` keeps them so on every
  platform.
- The synthetic pipeline is verified byte-for-byte: run it twice, `cmp` the
  outputs, then `python run.py checksums`.
- The Nanjing condition tables are reproducible on one machine and across
  machines only insofar as the same raster versions are used: the grid build
  depends on GDAL/rasterio resampling, the model on the scikit-learn version
  recorded in every `run_metadata_*.json`. The model stage, given the same
  `cells_*.csv`, is deterministic under the seed.
- Figure PNG/SVG files are not covered by the checksum files, because their
  bytes depend on the matplotlib and freetype versions. Within one environment
  they are reproducible: `make_figures.py` and `make_city_figure.py` fix the SVG
  hash salt and drop the embedded date, so two consecutive runs give identical
  `Figure_3/4` and `Figure_S2` bytes (verified for both PNG and SVG).
- `python run.py test` exercises the full Nanjing path on a 40 × 40 synthetic
  raster stack, so the code is testable without downloading anything. It checks
  the schema and the direction of the effect, not the paper's values — the test
  data are synthetic.

## Data sources

- Landsat 8 Collection 2 Level-2, scene **LC08_L2SP_120038_20210801_02_T1**
  (WRS-2 path 120, row 038; acquired 1 August 2021; scene cloud cover 12.86%).
  Available from USGS EarthExplorer, from the public STAC endpoint used to
  identify the scene (`earth-search.aws.element84.com/v1`), and — because the
  S3 bucket is requester-pays and the Azure mirror is private — as a signed
  windowed read through the Microsoft Planetary Computer
  (`nanjing/fetch_inputs.py`).
- **GHS-POP R2023A** (population grid, 2020 epoch, 30 arc-seconds), European
  Commission Joint Research Centre, <https://ghsl.jrc.ec.europa.eu>.
- **GHS-BUILT-S R2023A** (built-up surface, 2020 epoch, 30 arc-seconds), same
  portal.

## Caveats

The Nanjing experiment covers one city on one date and models a single
contamination path (training labels). It does not estimate how often such
contamination occurs, nor the temperature consequences of a reallocation. The
magnitude of the effect depends on the urban definition, and the effect
disappears altogether when priority is weighted by population; what the data
support is the asymmetry between directional and random error, not a fixed
percentage. Those limits are stated in Sections 4.4 and 6.3 of the paper and
should be kept with any reuse of these results.

## License and citation

Code: MIT (`LICENSE`). Derived data and figures: CC BY 4.0. Citation metadata
is in `CITATION.cff`; please cite the paper as well.

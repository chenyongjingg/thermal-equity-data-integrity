#!/bin/sh
# Re-run the full Nanjing pipeline exactly as reported in the manuscript.
# Writes LF-terminated CSVs so that checksums agree across platforms.
#   sh rerun_all.sh            (from nanjing/)
set -e
D=../data/raw
S=LC08_L2SP_120038_20210801_02_T1
POP=GHS_POP_E2020_GLOBE_R2023A_4326_30ss_V1_0_R6_C30.tif
BUILT=GHS_BUILT_S_E2020_GLOBE_R2023A_4326_30ss_V1_0_R6_C30.tif

for m in 0.02 0.05 0.10; do
  tag=$(echo $m | tr -d '.')
  python build_grid.py \
    --lst "$D/${S}__ST_B10.tif" --red "$D/${S}__SR_B4.tif" --nir "$D/${S}__SR_B5.tif" \
    --qa "$D/${S}__QA_PIXEL.tif" --max-cloud-frac 0.10 \
    --pop "$D/$POP" --built "$D/$BUILT" --min-built $m \
    --sr-scale 2.75e-05 --sr-offset -0.2 \
    --out outputs/cells_m$m.csv --meta outputs/grid_metadata_m$m.json
  python model_and_poison.py --cells outputs/cells_m$m.csv \
    --out outputs/conditions_heat_m${m}_r30.csv --meta outputs/run_metadata_heat_m${m}_r30.json \
    --contamination 0.05 0.10 0.15 --delta 1 2 3 --main-delta 2 --sweep-rate 0.10 \
    --trees 300 --seed 7 --repeats 30 --priority heat
done

python model_and_poison.py --cells outputs/cells_m0.05.csv \
  --out outputs/conditions_heat_x_pop_r30.csv --meta outputs/run_metadata_heat_x_pop_r30.json \
  --contamination 0.05 0.10 0.15 --delta 1 2 3 --main-delta 2 --sweep-rate 0.10 \
  --trees 300 --seed 7 --repeats 30 --priority heat_x_pop

python make_figures.py --conditions outputs/conditions_heat_m0.05_r30.csv --outdir outputs/figs_m0.05_r30
# copy the reported run into results/ and refresh CHECKSUMS.txt
python pack_results.py

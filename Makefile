PY      ?= python
BBOX    ?= 118.70 31.92 119.20 32.22
RES     ?= 1000
RATES   ?= 0.05 0.10 0.15
DELTAS  ?= 1 2 3
TREES   ?= 300
SEED    ?= 7
REPEATS ?= 30
PRIORITY ?= heat
MINBUILT ?= 0.05
MAXCLOUD ?= 0.10
SRSCALE ?= 2.75e-05
SROFFSET ?= -0.2

GRID    = nanjing/outputs/cells.csv
GRIDM   = nanjing/outputs/grid_metadata.json
CONDS   = nanjing/outputs/conditions.csv
CONDM   = nanjing/outputs/run_metadata.json

.PHONY: all synthetic nanjing grid model figures test checksums clean

all: synthetic test

## Synthetic city: regeneration + checksum verification (no downloads needed)
synthetic:
	cd synthetic && $(PY) simulate_poisoning.py
	cd synthetic && $(PY) make_figures.py
	$(MAKE) checksums

checksums:
	md5sum -c synthetic/CHECKSUMS.txt

## Nanjing experiment: needs LST, RED, NIR, QA, POP and BUILT in the environment
nanjing: grid model figures

grid: $(GRID)

$(GRID):
	$(PY) nanjing/build_grid.py --lst "$(LST)" --red "$(RED)" --nir "$(NIR)" --qa "$(QA)" --max-cloud-frac $(MAXCLOUD) --pop "$(POP)" --built "$(BUILT)" --min-built $(MINBUILT) --sr-scale $(SRSCALE) --sr-offset $(SROFFSET) --bbox $(BBOX) --res $(RES) --out $(GRID) --meta $(GRIDM)

model: $(CONDS)

$(CONDS): $(GRID)
	$(PY) nanjing/model_and_poison.py --cells $(GRID) --out $(CONDS) --meta $(CONDM) --contamination $(RATES) --delta $(DELTAS) --main-delta 2 --sweep-rate 0.10 --repeats $(REPEATS) --priority $(PRIORITY) --trees $(TREES) --seed $(SEED)

figures: $(CONDS)
	$(PY) nanjing/make_figures.py --conditions $(CONDS) --outdir nanjing/outputs

## Smoke test: full pipeline on a 40x40 raster stack, no downloads
test:
	$(PY) -m pytest nanjing/tests -q

clean:
	rm -rf nanjing/outputs/*.csv nanjing/outputs/*.json
	rm -rf nanjing/outputs/*.png nanjing/outputs/*.svg
	rm -rf .pytest_cache synthetic/__pycache__ nanjing/__pycache__

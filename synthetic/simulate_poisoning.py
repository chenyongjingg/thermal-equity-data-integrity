#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Proof-of-concept simulation for:
"Data Integrity and Thermal Equity in Urban Forest Management ..."

Question
--------
Can a modest, *directional* contamination of training labels reorder the
tree-planting priorities produced by an AI heat model, and shift the
distributional equity of the resulting allocation?

Design (stylised, deliberately transparent)
-------------------------------------------
* A synthetic city of N = 600 neighbourhoods on a 30 x 20 lattice.
* Latent fields (income, canopy, imperviousness) are spatially smooth,
  so that low-income neighbourhoods systematically have less canopy.
* Ground-truth land surface temperature (LST) is a known function of
  urban form + spatial noise.
* A random forest is trained on observed (noisy) LST labels and used to
  score planting priority = predicted heat burden x population exposure.
* Contamination: a fraction p of TRAINING labels drawn from the lower half
  of the income distribution is shifted downward by DELTA degrees
  (simulating systematic under-reporting of heat in poorer areas).
* Negative control: the same fraction p is contaminated, but drawn at
  random from the whole city (no income targeting).

Reported metrics (vs. the clean-label model, same seed):
  * Spearman rho of neighbourhood priority ranks
  * top-quintile reversal rate = 1 - |intersection| / |top set|
  * equity share = share of low-income neighbourhoods in the top quintile
  * mean priority percentile of low-income neighbourhoods
  * mean prediction bias for low-income neighbourhoods (deg C)

This is a demonstration on synthetic data, NOT an empirical estimate for
any real city. Running this file reproduces the numbers reported in the Supplementary
Materials (Figure S1 and Table S1).
"""

import numpy as np
import pandas as pd
from scipy.ndimage import gaussian_filter
from scipy.stats import spearmanr
from sklearn.ensemble import RandomForestRegressor

# ----------------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------------
N_SIDE_X, N_SIDE_Y = 30, 20          # 600 neighbourhoods
N = N_SIDE_X * N_SIDE_Y
N_SEEDS = 30
CONTAMINATION = [0.05, 0.10, 0.15]
DELTA = 2.0                          # deg C downward shift on poisoned labels
RF_TREES = 300
TOP_FRACTION = 0.20                  # "top quintile" of planting priority

FEATURES = ["canopy", "impervious", "bldg_density", "ndvi",
            "pop_density", "elderly_share", "income"]


def smooth_field(rng, sigma=3.0):
    """Spatially autocorrelated field on the lattice, standardised to [0, 1]."""
    raw = rng.normal(size=(N_SIDE_Y, N_SIDE_X))
    sm = gaussian_filter(raw, sigma=sigma, mode="reflect")
    sm = (sm - sm.min()) / (sm.max() - sm.min())
    return sm.ravel()


def make_city(seed):
    rng = np.random.default_rng(seed)

    # Income: smooth field plus a weak west-east gradient (a stylised
    # centre-periphery structure).
    grad = np.tile(np.linspace(0, 1, N_SIDE_X), N_SIDE_Y)
    income = 0.7 * smooth_field(rng) + 0.3 * grad
    income = (income - income.min()) / (income.max() - income.min())

    canopy = np.clip(0.55 - 0.38 * income + 0.20 * smooth_field(rng), 0.02, 0.90)
    imperv = np.clip(0.40 + 0.35 * (1 - income) + 0.20 * smooth_field(rng), 0.05, 0.95)
    bldg = np.clip(0.45 + 0.30 * (1 - income) + 0.20 * smooth_field(rng), 0.05, 0.95)
    ndvi = np.clip(0.65 * canopy + 0.25 * smooth_field(rng), 0.0, 1.0)

    pop = np.exp(rng.normal(0, 0.5, N)) * (0.6 + 0.8 * income)
    pop = pop / pop.max()
    elderly = np.clip(0.10 + 0.12 * smooth_field(rng) + rng.normal(0, 0.02, N), 0.02, 0.45)

    X = np.column_stack([canopy, imperv, bldg, ndvi, pop, elderly, income])

    # Ground-truth LST (deg C): hotter where impervious/built-up, cooler
    # where canopy/NDVI is high. Spatial noise mimics unobserved drivers.
    lst = (33.0
           + 9.0 * imperv
           - 7.0 * canopy
           - 2.0 * ndvi
           + 3.0 * bldg
           + 1.5 * smooth_field(rng)
           + rng.normal(0, 0.5, N))
    return X, lst, income, pop, elderly


def priority_scores(model, X, pop, elderly):
    """Planting priority = predicted heat burden x population exposure."""
    pred = model.predict(X)
    pred_c = pred - pred.mean()
    exposure = 0.5 * (pop / pop.max()) + 0.5 * (elderly / elderly.max())
    return pred_c * exposure, pred


def evaluate(seed):
    X, lst_true, income, pop, elderly = make_city(seed)
    rng = np.random.default_rng(10_000 + seed)

    observed = lst_true + rng.normal(0, 0.8, N)      # measurement noise
    low_income = income <= np.median(income)

    clean = RandomForestRegressor(n_estimators=RF_TREES, min_samples_leaf=3,
                                  random_state=seed, n_jobs=1)
    clean.fit(X, observed)
    p_clean, pred_clean = priority_scores(clean, X, pop, elderly)
    k = int(round(TOP_FRACTION * N))
    top_clean = set(np.argsort(-p_clean)[:k])

    rows = []
    for p in CONTAMINATION:
        for mode in ("targeted", "random"):
            y = observed.copy()
            n_poison = int(round(p * N))
            if mode == "targeted":
                pool = np.flatnonzero(low_income)
            else:
                pool = np.arange(N)
            idx = rng.choice(pool, size=n_poison, replace=False)
            y[idx] -= DELTA

            m = RandomForestRegressor(n_estimators=RF_TREES, min_samples_leaf=3,
                                      random_state=seed, n_jobs=1)
            m.fit(X, y)
            p_new, pred_new = priority_scores(m, X, pop, elderly)

            rho = spearmanr(p_clean, p_new).statistic
            top_new = set(np.argsort(-p_new)[:k])
            reversal = 1.0 - len(top_clean & top_new) / k
            share_low_top = np.mean(low_income[list(top_new)])
            mean_pct_low = np.mean(
                [np.mean(p_new <= p_new[i]) for i in np.flatnonzero(low_income)]
            ) * 100.0
            bias_low = np.mean((pred_new - lst_true)[low_income])

            rows.append(dict(seed=seed, contamination=p, mode=mode,
                             spearman=rho, top_reversal=reversal,
                             low_share_top=share_low_top,
                             mean_pct_low=mean_pct_low,
                             bias_low_C=bias_low))
    return rows, dict(seed=seed,
                      clean_low_share_top=np.mean(low_income[list(top_clean)]),
                      clean_mean_pct_low=np.mean(
                          [np.mean(p_clean <= p_clean[i]) for i in np.flatnonzero(low_income)]
                      ) * 100.0,
                      clean_bias_low=np.mean((pred_clean - lst_true)[low_income]))


def main():
    per_seed, baselines = [], []
    for s in range(1, N_SEEDS + 1):
        rows, base = evaluate(s)
        per_seed.extend(rows)
        baselines.append(base)
        print(f"seed {s:2d}/{N_SEEDS} done", flush=True)

    df = pd.DataFrame(per_seed)
    df.to_csv("results_per_seed.csv", index=False, lineterminator="\n")

    summary = (df.groupby(["mode", "contamination"])
                 .agg(spearman_mean=("spearman", "mean"),
                      spearman_sd=("spearman", "std"),
                      top_reversal_mean=("top_reversal", "mean"),
                      top_reversal_sd=("top_reversal", "std"),
                      low_share_top_mean=("low_share_top", "mean"),
                      low_share_top_sd=("low_share_top", "std"),
                      mean_pct_low_mean=("mean_pct_low", "mean"),
                      mean_pct_low_sd=("mean_pct_low", "std"),
                      bias_low_C_mean=("bias_low_C", "mean"),
                      bias_low_C_sd=("bias_low_C", "std"))
                 .reset_index())
    summary.to_csv("results_summary.csv", index=False, lineterminator="\n")

    b = pd.DataFrame(baselines)
    base_summary = b.drop(columns="seed").agg(["mean", "std"]).T
    base_summary.to_csv("results_clean_baseline.csv", lineterminator="\n")

    print("\n=== clean-label baseline (mean over seeds) ===")
    print(base_summary)
    print("\n=== scenario summary ===")
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()

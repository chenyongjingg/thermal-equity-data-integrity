# -*- coding: utf-8 -*-
"""Unit tests for the grid, tile and interval helpers.

These cover the two places where an off-by-one silently produces an empty
analysis rather than an error: the GHSL tile name (rows are numbered from the
north, so the tile for Beijing is R5, not R7) and the UTM zone.  The interval
helpers are checked against hand-computable cases.
"""

import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)

import run_cities     # noqa: E402
import uncertainty    # noqa: E402


def test_ghs_tile_rows_are_numbered_from_the_north():
    assert run_cities.ghs_tile(run_cities.CITIES["nanjing"]) == "R6_C30"
    assert run_cities.ghs_tile(run_cities.CITIES["wuhan"]) == "R6_C30"
    assert run_cities.ghs_tile(run_cities.CITIES["beijing"]) == "R5_C30"
    assert run_cities.ghs_tile(run_cities.CITIES["xian"]) == "R6_C29"
    assert run_cities.ghs_tile(run_cities.CITIES["shanghai"]) == "R6_C31"


def test_utm_zone():
    assert run_cities.utm_zone(run_cities.CITIES["nanjing"]) == 50
    assert run_cities.utm_zone(run_cities.CITIES["beijing"]) == 50
    assert run_cities.utm_zone(run_cities.CITIES["xian"]) == 49
    assert run_cities.utm_zone(run_cities.CITIES["hangzhou"]) == 51


def test_mean_ci_matches_hand_calculation():
    x = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    m, sd, lo, hi, n = uncertainty.mean_ci(x)
    assert m == 3.0
    assert n == 5
    assert abs(sd - np.std(x, ddof=1)) < 1e-12
    # symmetric, and the interval contains the mean
    assert abs((m - lo) - (hi - m)) < 1e-12
    assert lo < m < hi


def test_welch_zero_variance_arms_give_zero_difference():
    # Constant arms have no sampling variability, so the interval collapses.
    a = np.full(30, 5.0)
    diff, se, lo, hi, p = uncertainty.welch(a, a.copy())
    assert diff == 0.0
    assert se == 0.0
    assert lo == hi == 0.0


def test_welch_detects_a_shifted_arm():
    rng = np.random.default_rng(1)
    a = rng.normal(loc=10.0, size=30)
    b = rng.normal(loc=0.0, size=30)
    diff, se, lo, hi, p = uncertainty.welch(a, b)
    assert diff > 5.0
    assert lo > 0.0
    assert p < 1e-6

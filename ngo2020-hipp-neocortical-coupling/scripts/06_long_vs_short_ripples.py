#!/usr/bin/env python3
"""
Script 06: Long vs. Short Ripple Duration Comparison
======================================================
Ngo et al. (2020) Reproduction Pipeline

Reproduces Figure 4 of the paper:
- Split ripples by duration (median split)
- Compare NC spindle power for long vs. short ripples
- Expected: NC spindle power > for long-duration ripples (p=0.039)

METHODS:
  - Split ripples at median duration
  - Compare TFR spindle power (12-16 Hz cluster)
  - One-sided independent t-test (long > short)

INPUTS:
  - data/processed/detections/sub-XX_ripples.csv
  - results/stats/tfr_nc_ripple_locked.npy

OUTPUTS:
  - results/stats/ripple_duration_comparison.json
  - results/figures/long_vs_short_comparison.png

Usage:
    python scripts/06_long_vs_short_ripples.py

TODO: Implement median split and t-test comparison
Expected result: t(2937) = 1.76, p=0.039 (one-sided)
"""

import numpy as np
import pandas as pd
from scipy import stats
import pingouin as pg

print("[TEMPLATE] Script 06: Long vs. Short Ripple Duration")
print("TODO: Median split ripples, compare NC spindle power")
print("Expected: p=0.039, one-sided t-test")
print("Save to: results/stats/ripple_duration_comparison.json")

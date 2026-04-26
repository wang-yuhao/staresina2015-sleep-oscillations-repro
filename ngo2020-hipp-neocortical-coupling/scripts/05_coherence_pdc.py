#!/usr/bin/env python3
"""
Script 05: Coherence and Partial Directed Coherence (PDC) Analysis
====================================================================
Ngo et al. (2020) Reproduction Pipeline

Reproduces Figure 3 of the paper:
- Compute NC-HIPP coherence in spindle band around ripples
- Compute Partial Directed Coherence (PDC) for directionality
- Expected: NC drives HIPP ~250ms before ripple peak

METHODS:
  - Coherence: Magnitude-squared coherence in spindle band (12-16 Hz)
  - PDC: Multivariate autoregressive (MVAR) model, order 10
  - Time window: ±1 s around ripple
  - Directionality: NC→HIPP vs HIPP→NC

INPUTS:
  - data/processed/sub-XX_NC_preprocessed.npy
  - data/processed/sub-XX_HIPP_preprocessed.npy
  - data/processed/detections/sub-XX_ripples.csv
  - config/config.yaml

OUTPUTS:
  - results/stats/coherence_nc_hipp_spindle.npy
  - results/stats/pdc_nc_to_hipp.npy
  - results/stats/pdc_hipp_to_nc.npy

Usage:
    python scripts/05_coherence_pdc.py

KEY FUNCTIONS TO IMPLEMENT:
  - compute_coherence(nc_signal, hipp_signal, srate, fmin=10, fmax=20)
  - compute_pdc(nc_signal, hipp_signal, model_order=10, spindle_band=[12,16])
  - Use mne_connectivity.spectral_connectivity_epochs or mne_connectivity.vector_auto_regression

EXPECTED RESULTS (Figure 3):
  - NC-HIPP coherence elevated in spindle band around ripples
  - PDC: NC→HIPP influence starts ~250ms before ripple
  - PDC: Both regions synchronized from -250ms to +500ms
"""

import numpy as np
from pathlib import Path
import yaml
from mne_connectivity import spectral_connectivity_epochs, vector_auto_regression

print("[TEMPLATE] Script 05: Coherence & PDC Analysis")
print("TODO: Implement coherence and PDC computation")
print("Use: mne_connectivity.spectral_connectivity_epochs()")
print("     mne_connectivity.vector_auto_regression()")
print("Save to: results/stats/coherence_*.npy and pdc_*.npy")

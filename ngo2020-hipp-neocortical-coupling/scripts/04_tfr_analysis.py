#!/usr/bin/env python3
"""
Script 04: Time-Frequency Representation (TFR) Analysis
=========================================================
Ngo et al. (2020) Reproduction Pipeline

Reproduces Figure 2 of the paper:
- Compute time-frequency representations (TFR) of NC and HIPP signals
- Time-lock to individual ripple events (±1 s window)
- Normalize against matched ripple-free control events
- Identify spindle-band (12-16 Hz) power cluster
- Compute group-level average

METHODS (from paper):
  - TFR method: Morlet wavelets
  - Frequency range: 4-30 Hz
  - Time window: ±1 s relative to ripple peak
  - Baseline normalization: -1.0 to -0.5 s
  - Control events: Matched ripple-free intervals (>2s from any ripple)

INPUTS:
  - data/processed/sub-XX_NC_preprocessed.npy
  - data/processed/sub-XX_HIPP_preprocessed.npy
  - data/processed/detections/sub-XX_ripples.csv
  - config/config.yaml

OUTPUTS:
  - results/stats/tfr_nc_ripple_locked.npy
  - results/stats/tfr_hipp_ripple_locked.npy
  - results/stats/spindle_cluster_stats.json

Usage:
    python scripts/04_tfr_analysis.py

REFERENCE:
  Original MATLAB code: https://github.com/episodicmemorylab/Ngo_et_al_eLife2020
  Figure 2 in Ngo et al. (2020) eLife 9:e57011
"""

import numpy as np
import pandas as pd
from pathlib import Path
import yaml
from scipy import signal
import mne
from tqdm import tqdm

print("="*60)
print("[TEMPLATE] Script 04: TFR Analysis")
print("="*60)
print("")
print("This is a TEMPLATE script with implementation guidelines.")
print("")
print("TODO: Implement the following functions:")
print("")
print("1. compute_morlet_tfr(signal, srate, freqs, n_cycles=5):")
print("   - Use scipy.signal.morlet or mne.time_frequency.tfr_array_morlet")
print("   - Frequency range: 4-30 Hz (from config)")
print("   - Return: (n_freqs x n_times) array")
print("")
print("2. extract_ripple_locked_epochs(signal, ripple_times, window_s=1.0, srate):")
print("   - Extract ±1s epochs around each ripple peak")
print("   - Return: (n_ripples x n_samples) array")
print("")
print("3. find_matched_control_events(ripple_times, n_controls_per_ripple=3, min_dist_s=2.0):")
print("   - Find ripple-free intervals >2s from any ripple")
print("   - Match to ripple distribution")
print("   - Return: control_times array")
print("")
print("4. normalize_tfr(tfr_ripple, tfr_control):")
print("   - Compute (ripple - control) / control")
print("   - Or dB: 10 * log10(ripple / control)")
print("   - Baseline normalization: -1.0 to -0.5s")
print("")
print("5. identify_spindle_cluster(tfr, freq_band=[12, 16], time_window=[-0.5, 0.5]):")
print("   - Statistical cluster detection")
print("   - Use cluster permutation tests (mne.stats.permutation_cluster_test)")
print("   - Return: significant cluster mask")
print("")
print("Expected output:")
print("  - Spindle power (12-16 Hz) increases in NC and HIPP")
print("  - Significant cluster from ~-0.5 to +0.5 s around ripple")
print("  - Group-level TFR saved for Figure 2 plotting")
print("")
print("KEY PARAMETERS (from config.yaml):")
print("  - tfr.method: 'morlet'")
print("  - tfr.freqs_low: 4 Hz")
print("  - tfr.freqs_high: 30 Hz")
print("  - tfr.n_cycles: 5")
print("  - tfr.epoch_tmin: -1.0 s")
print("  - tfr.epoch_tmax: 1.0 s")
print("  - tfr.baseline_window: [-1.0, -0.5] s")
print("")
print("REFERENCE IMPLEMENTATION (MNE-Python):")
print("  import mne.time_frequency as mtf")
print("  tfr = mtf.tfr_array_morlet(data, sfreq, freqs, n_cycles, output='power')")
print("")
print("After implementation, this script should:")
print("  1. Load preprocessed NC and HIPP signals")
print("  2. Load detected ripples")
print("  3. Extract ripple-locked epochs")
print("  4. Compute TFR for each epoch")
print("  5. Average across ripples and subjects")
print("  6. Identify significant spindle-band cluster")
print("  7. Save results for plotting (script 07)")
print("")
print("Save to: results/stats/tfr_*.npy")

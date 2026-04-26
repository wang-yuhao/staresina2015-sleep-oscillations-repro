#!/usr/bin/env python3
"""
Script 03: Detect Spindles and Ripples
==========================================
Ngo et al. (2020) Reproduction Pipeline

Implements the spindle and ripple detection algorithms from Staresina et al. (2015)
and Ngo et al. (2020):

SPINDLE DETECTION (NC and HIPP, 12-16 Hz):
  1. Bandpass filter: 12-16 Hz
  2. Compute RMS with 200 ms window
  3. Smooth RMS with 200 ms window
  4. Threshold: mean + 2.5 SD (detection), mean + 9 SD (upper limit)
  5. Duration: 500-3000 ms

RIPPLE DETECTION (HIPP only, 80-100 Hz):
  1. Bandpass filter: 80-100 Hz
  2. Compute RMS with 20 ms window
  3. Threshold: mean + 5 SD
  4. Duration: 38-500 ms (3 cycles minimum)
  5. Require >= 3 cycles in raw signal
  6. Segment into ±1 s epochs centered on peak

INPUTS:
  - data/processed/sub-XX_NC_preprocessed.npy
  - data/processed/sub-XX_HIPP_preprocessed.npy
  - config/config.yaml

OUTPUTS:
  - data/processed/detections/sub-XX_spindles_NC.csv
  - data/processed/detections/sub-XX_spindles_HIPP.csv
  - data/processed/detections/sub-XX_ripples.csv

Columns: onset_sample, peak_sample, offset_sample, duration_ms, peak_amplitude

Usage:
    python scripts/03_detect_spindles_ripples.py

REFERENCE MATLAB CODE:
  https://github.com/episodicmemorylab/Ngo_et_al_eLife2020
  Staresina et al. (2015) Nature Neuroscience
"""

import numpy as np
import pandas as pd
from pathlib import Path
import yaml
from scipy import signal
from tqdm import tqdm

print("[STUB] This is a template script.")
print("TODO: Implement full RMS-based spindle & ripple detection.")
print("Refer to original MATLAB code and config/config.yaml for parameters.")
print("\nKey functions to implement:")
print("  - rms_detect_spindles(signal, fs, cfg)")
print("  - rms_detect_ripples(signal, fs, cfg)")
print("  - count_cycles_in_raw(signal, fs, band=(80,100))")
print("\nSave results to: data/processed/detections/")

#!/usr/bin/env python3
"""
Script 02: Preprocess Raw Data
==================================
Ngo et al. (2020) Reproduction Pipeline

This script loads raw .mat files downloaded from OSF, extracts NREM sleep segments,
applies artifact rejection, and saves preprocessed NC (neocortex) and HIPP (hippocampus)
signals for subsequent analysis.

Inputs:
  - data/raw/sub-XX/*.mat files (NC and HIPP recordings)

Outputs:
  - data/processed/sub-XX_NC_preprocessed.npy
  - data/processed/sub-XX_HIPP_preprocessed.npy
  - data/processed/sub-XX_metadata.json (srate, NREM epochs, etc.)

Usage:
    python scripts/02_preprocess.py
    python scripts/02_preprocess.py --subject 01  # Process single subject
"""

import argparse
import glob
import json
from pathlib import Path
import numpy as np
import yaml
from scipy import signal
from tqdm import tqdm

# Import mat file loaders
try:
    import scipy.io as spio
except ImportError:
    spio = None

try:
    import mat73
except ImportError:
    mat73 = None

def load_config():
    with open("config/config.yaml", "r") as f:
        return yaml.safe_load(f)

def load_mat_file(filepath):
    """
    Load .mat file, trying scipy first, then mat73 for v7.3 files.
    """
    try:
        return spio.loadmat(filepath, simplify_cells=True)
    except:
        if mat73:
            return mat73.loadmat(filepath)
        else:
            raise ImportError("Install mat73 for large .mat files: pip install mat73")

def extract_nrem_periods(data_dict):
    """
    Extract NREM sleep periods from the loaded data.
    Expected keys: 'nrem_periods', 'nrem_epochs', 'sleep_scoring', etc.
    Adapt based on actual OSF data structure.
    """
    # TODO: Inspect actual .mat structure from OSF and adapt this function
    # Placeholder:
    if 'nrem_periods' in data_dict:
        return data_dict['nrem_periods']
    elif 'nrem_epochs' in data_dict:
        return data_dict['nrem_epochs']
    else:
        print("WARNING: No NREM periods found. Using entire recording.")
        return None

def bandpass_filter(data, lowcut, highcut, fs, order=4):
    nyq = 0.5 * fs
    low = lowcut / nyq
    high = highcut / nyq
    b, a = signal.butter(order, [low, high], btype='band')
    return signal.filtfilt(b, a, data)

def preprocess_subject(sub_path, cfg):
    """
    Preprocess a single subject: load NC and HIPP, filter, extract NREM, save.
    """
    sub_id = sub_path.name
    print(f"\nProcessing {sub_id}...")
    
    # Find NC and HIPP .mat files
    nc_files = list(sub_path.glob("*NC*.mat")) + list(sub_path.glob("*Cz*.mat"))
    hipp_files = list(sub_path.glob("*HIPP*.mat"))
    
    if not nc_files or not hipp_files:
        print(f"  [SKIP] Missing NC or HIPP files for {sub_id}")
        return
    
    # Load files
    print(f"  Loading NC: {nc_files[0].name}")
    nc_data = load_mat_file(nc_files[0])
    print(f"  Loading HIPP: {hipp_files[0].name}")
    hipp_data = load_mat_file(hipp_files[0])
    
    # Extract signals (adapt keys based on actual .mat structure)
    nc_signal = nc_data.get('data', nc_data.get('EEG', None))
    hipp_signal = hipp_data.get('data', hipp_data.get('EEG', None))
    srate = nc_data.get('srate', nc_data.get('fs', 1000))
    
    if nc_signal is None or hipp_signal is None:
        print(f"  [ERROR] Could not extract signals. Keys: {list(nc_data.keys())}")
        return
    
    # Ensure 1D
    nc_signal = np.squeeze(nc_signal)
    hipp_signal = np.squeeze(hipp_signal)
    
    # Basic bandpass filter (0.5-200 Hz)
    print(f"  Filtering NC and HIPP...")
    nc_filt = bandpass_filter(nc_signal, 0.5, 200, srate)
    hipp_filt = bandpass_filter(hipp_signal, 0.5, 200, srate)
    
    # Extract NREM periods (TODO: adapt based on actual data)
    nrem_periods = extract_nrem_periods(nc_data)
    
    # Save preprocessed data
    out_dir = Path(cfg['paths']['processed_data'])
    out_dir.mkdir(parents=True, exist_ok=True)
    
    np.save(out_dir / f"{sub_id}_NC_preprocessed.npy", nc_filt)
    np.save(out_dir / f"{sub_id}_HIPP_preprocessed.npy", hipp_filt)
    
    metadata = {
        "subject_id": sub_id,
        "srate": int(srate),
        "n_samples_nc": len(nc_filt),
        "n_samples_hipp": len(hipp_filt),
        "nrem_periods": nrem_periods.tolist() if nrem_periods is not None else None,
    }
    
    with open(out_dir / f"{sub_id}_metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)
    
    print(f"  [DONE] {sub_id}: {len(nc_filt) / srate / 60:.1f} minutes")

def main():
    parser = argparse.ArgumentParser(description="Preprocess Ngo et al. (2020) data")
    parser.add_argument("--subject", type=str, help="Process specific subject (e.g., sub-01)")
    args = parser.parse_args()
    
    cfg = load_config()
    raw_dir = Path(cfg['paths']['raw_data'])
    
    if args.subject:
        sub_paths = [raw_dir / args.subject]
    else:
        sub_paths = sorted(raw_dir.glob("sub-*"))
    
    print(f"Found {len(sub_paths)} subject(s) to process")
    
    for sub_path in sub_paths:
        if sub_path.is_dir():
            preprocess_subject(sub_path, cfg)
    
    print("\n[DONE] Preprocessing complete.")
    print("Next step: python scripts/03_detect_spindles_ripples.py")

if __name__ == "__main__":
    main()

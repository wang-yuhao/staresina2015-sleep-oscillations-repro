"""
io.py - Data Loading and NREM Masking
======================================
PRINCIPLE:
  The dataset from Ngo, Fell & Staresina (eLife 2020) is stored as MATLAB .mat
  files, one per subject. Each file contains:
    - LFP_HC  : hippocampal local field potential (channels x samples, 1000 Hz)
    - LFP_Cz  : scalp Cz EEG (1 x samples)
    - sleep_score : per-30s-epoch sleep stage (0=Wake, 1=REM, 2=N2, 3=N3, 4=N4)
    - fs      : sampling rate (always 1000)

  WHY MATLAB FORMAT?
  The original Staresina lab uses MATLAB/FieldTrip for all analyses.
  scipy.io.loadmat() reads these files natively into Python dicts.

  WHY RESTRICT TO NREM?
  Slow oscillations, spindles and ripples only co-occur in NREM sleep
  (stages N2, N3, N4). Analysing wake or REM would introduce false events.
"""

import numpy as np
import pandas as pd
from pathlib import Path
from scipy.io import loadmat


def load_subject(mat_path: str) -> dict:
    """
    Load one subject's .mat file from the Ngo 2020 / Staresina lab dataset.

    Parameters
    ----------
    mat_path : str
        Path to the subject .mat file.

    Returns
    -------
    dict with keys:
        'hc'           : np.ndarray (n_samples,) hippocampal iEEG
        'cz'           : np.ndarray (n_samples,) scalp Cz (may be None)
        'sleep_stages' : np.ndarray (n_epochs,) integer sleep stage per 30s epoch
        'fs'           : int, sampling rate (1000 Hz)
        'subject'      : str, subject ID from filename
    """
    mat = loadmat(mat_path, squeeze_me=True, struct_as_record=False)

    # Try standard Ngo 2020 field names first
    if 'data' in mat:
        d = mat['data']
        hc = np.array(d.LFP_HC).squeeze()
        cz = np.array(d.LFP_Cz).squeeze() if hasattr(d, 'LFP_Cz') else None
        stages = np.array(d.sleep_score).squeeze().astype(int)
        fs = int(d.fs)
    elif 'LFP_HC' in mat:
        hc = np.array(mat['LFP_HC']).squeeze()
        cz = np.array(mat['LFP_Cz']).squeeze() if 'LFP_Cz' in mat else None
        stages = np.array(mat['sleep_score']).squeeze().astype(int) \
            if 'sleep_score' in mat else None
        fs = int(mat.get('fs', 1000))
    else:
        raise KeyError(
            f"Cannot find expected fields in {mat_path}.\n"
            f"Available keys: {[k for k in mat.keys() if not k.startswith('_')]}\n"
            f"Please inspect the file with: scipy.io.loadmat(path).keys()"
        )

    # If multiple HC channels exist, take first hippocampal channel
    if hc.ndim == 2:
        hc = hc[0]

    return {
        'hc': hc.astype(np.float64),
        'cz': cz.astype(np.float64) if cz is not None else None,
        'sleep_stages': stages,
        'fs': fs,
        'subject': Path(mat_path).stem,
    }


def get_nrem_mask(sleep_stages: np.ndarray, fs: int,
                  nrem_codes: tuple = (2, 3, 4),
                  epoch_len_s: float = 30.0) -> np.ndarray:
    """
    Convert per-epoch sleep stage labels into a sample-level boolean mask.

    PRINCIPLE:
      Sleep staging gives one label per 30-second epoch (standard PSG convention).
      We expand this to sample level so we can zero-out or skip non-NREM samples
      during filtering and event detection.

    Parameters
    ----------
    sleep_stages : array of int
        One integer per 30-second epoch.
    fs : int
        Sampling rate in Hz.
    nrem_codes : tuple
        Sleep stage codes to include (default: N2=2, N3=3, N4=4).
    epoch_len_s : float
        Length of each epoch in seconds (default 30).

    Returns
    -------
    np.ndarray of bool, shape (n_samples,)
        True where sample is in NREM sleep.
    """
    epoch_len_samples = int(epoch_len_s * fs)
    n_samples = len(sleep_stages) * epoch_len_samples
    mask = np.zeros(n_samples, dtype=bool)
    for i, stage in enumerate(sleep_stages):
        if stage in nrem_codes:
            start = i * epoch_len_samples
            end = start + epoch_len_samples
            mask[start:end] = True
    return mask


def save_events(df: pd.DataFrame, path) -> None:
    """Save event DataFrame to CSV."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)


def list_subjects(data_dir: str) -> list:
    """
    List all .mat subject files in data_dir.
    Returns sorted list of stem names (without .mat extension).
    """
    return sorted([p.stem for p in Path(data_dir).glob('*.mat')])

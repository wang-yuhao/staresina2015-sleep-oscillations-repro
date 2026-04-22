"""Data loading and I/O functions for EEG analysis.

This module handles loading EEG data from the Ngo et al. 2020 dataset,
which uses MATLAB .mat files with iEEG recordings from epilepsy patients.

Data Format:
-----------
The Ngo et al. 2020 dataset (OSF: https://osf.io/3hpvr/) contains:
- MATLAB .mat files with intracranial EEG from hippocampus and neocortex
- Sampling rate: 1000 Hz
- Sleep scoring annotations
- Channel information

For this reproduction, we focus on hippocampal channels during NREM sleep.
"""
import numpy as np
import scipy.io as sio
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Low-level MAT loading helpers
# ---------------------------------------------------------------------------

def load_mat_file(filepath: str) -> Dict:
    """Load a MATLAB .mat file (v5-7.2 via scipy, v7.3 HDF5 via h5py)."""
    filepath = Path(filepath)
    if not filepath.exists():
        raise FileNotFoundError(f"File not found: {filepath}")
    try:
        data = sio.loadmat(str(filepath), struct_as_record=False, squeeze_me=True)
        logger.info(f"Loaded .mat file: {filepath.name}")
        return data
    except Exception as e:
        try:
            import h5py
            logger.info(f"Trying h5py for v7.3 file: {filepath.name}")
            with h5py.File(str(filepath), 'r') as f:
                data = {}
                for key in list(f.keys()):
                    try:
                        data[key] = f[key][()]
                    except Exception:
                        data[key] = f[key]
            logger.info(f"Loaded with h5py: {filepath.name}")
            return data
        except ImportError:
            raise ValueError(
                f"Error loading {filepath}: {e}. Install h5py for v7.3 files."
            )


def extract_eeg_from_mat(
    mat_data: Dict,
    channel_name: Optional[str] = None,
) -> Tuple[np.ndarray, float]:
    """Extract EEG array and sampling rate from a loaded .mat dictionary."""
    available_keys = list(mat_data.keys())
    data_keys = ['data', 'lfp', 'eeg', 'signal', 'lfpdata', 'trial']
    srate_keys = ['fs', 'srate', 'sampling_rate', 'fsample', 'Fs']

    eeg_data = None
    sfreq = None

    for key in data_keys:
        if key in mat_data:
            eeg_data = np.array(mat_data[key])
            break

    for key in srate_keys:
        if key in mat_data:
            val = mat_data[key]
            sfreq = float(np.asarray(val).flat[0])
            break

    if eeg_data is None:
        raise ValueError(f"Could not find EEG data. Available keys: {available_keys}")
    if sfreq is None:
        logger.warning("Could not find sampling rate; defaulting to 1000 Hz.")
        sfreq = 1000.0

    return eeg_data, sfreq


# ---------------------------------------------------------------------------
# Subject-level loading (used by pipeline.py)
# ---------------------------------------------------------------------------

def list_subjects(data_dir: str) -> List[int]:
    """Return sorted list of patient indices found in data_dir.

    Scans for files like pat01.mat, pat02.mat … or sub-01.mat etc.
    Returns integer indices extracted from filenames.
    """
    data_dir = Path(data_dir)
    mat_files = sorted(data_dir.glob('*.mat'))
    indices = []
    for f in mat_files:
        # strip leading non-digits, keep trailing digits
        digits = ''.join(c for c in f.stem if c.isdigit())
        if digits:
            indices.append(int(digits))
    if not indices:
        # fall back: return range(1, n_files+1)
        indices = list(range(1, len(mat_files) + 1))
    return sorted(set(indices))


def _find_subject_file(data_dir: Path, pat_idx: int) -> Path:
    """Find the .mat file for a given patient index."""
    # Try several naming conventions
    candidates = [
        data_dir / f'pat{pat_idx:02d}.mat',
        data_dir / f'pat{pat_idx}.mat',
        data_dir / f'sub-{pat_idx:02d}.mat',
        data_dir / f'subject{pat_idx:02d}.mat',
        data_dir / f's{pat_idx:02d}.mat',
    ]
    for c in candidates:
        if c.exists():
            return c
    # Last resort: glob
    matches = list(data_dir.glob(f'*{pat_idx:02d}*.mat')) + \
              list(data_dir.glob(f'*{pat_idx}*.mat'))
    if matches:
        return matches[0]
    raise FileNotFoundError(
        f"No .mat file found for patient {pat_idx} in {data_dir}"
    )


def load_eeg(
    data_dir: str,
    pat_idx: int,
    channel: str = 'HIPP',
) -> np.ndarray:
    """Load raw EEG signal for a single hippocampal channel.

    Returns 1-D numpy array (n_samples,) in µV.
    If the .mat file contains multiple channels, we pick the first one
    whose name contains *channel* (case-insensitive).
    """
    data_dir = Path(data_dir)
    mat_file = _find_subject_file(data_dir, pat_idx)
    mat_data = load_mat_file(str(mat_file))
    eeg, _ = extract_eeg_from_mat(mat_data, channel_name=channel)

    # Flatten multi-channel to 1-D: take first matching channel
    if eeg.ndim == 2:
        ch_key = channel.lower()
        # Check if channel names are stored
        ch_names = None
        for k in ['ch_names', 'channels', 'label', 'chanlocs']:
            if k in mat_data:
                ch_names = list(mat_data[k])
                break
        if ch_names is not None:
            for i, name in enumerate(ch_names):
                if ch_key in str(name).lower():
                    return eeg[i] if eeg.shape[0] < eeg.shape[1] else eeg[:, i]
        # default: return first row
        eeg = eeg[0] if eeg.shape[0] < eeg.shape[1] else eeg[:, 0]

    return eeg.astype(np.float64)


def load_supplement(
    data_dir: str,
    pat_idx: int,
    channel: str = 'HIPP',
) -> Dict:
    """Load supplementary info: sleep scoring, artifact mask, data length.

    Returns dict with keys:
        scoring   : np.ndarray (n_epochs,)  – sleep-stage label per 30-s epoch
        artifacts : np.ndarray (n_samples,) – bool, True = artifact sample
        datalen   : int                     – total number of samples
    """
    data_dir = Path(data_dir)
    mat_file = _find_subject_file(data_dir, pat_idx)
    mat_data = load_mat_file(str(mat_file))

    # --- sleep scoring ---
    scoring = None
    for k in ['stages', 'hypnogram', 'sleep_stages', 'scoring', 'sleepstage']:
        if k in mat_data:
            scoring = np.array(mat_data[k]).ravel()
            break
    if scoring is None:
        logger.warning("No sleep scoring found; treating all data as NREM.")
        # estimate from data length
        eeg, fs_val = extract_eeg_from_mat(mat_data)
        n = eeg.shape[-1] if eeg.ndim > 1 else len(eeg)
        n_epochs = int(np.ceil(n / (30 * fs_val)))
        scoring = np.full(n_epochs, 2, dtype=int)  # label everything as N2

    # --- artifact flags ---
    artifacts = None
    for k in ['artifacts', 'artifact', 'bad_samples', 'reject']:
        if k in mat_data:
            artifacts = np.array(mat_data[k]).ravel().astype(bool)
            break
    if artifacts is None:
        eeg, _ = extract_eeg_from_mat(mat_data)
        n = eeg.shape[-1] if eeg.ndim > 1 else len(eeg)
        artifacts = np.zeros(n, dtype=bool)  # no artifacts flagged

    # --- data length ---
    eeg, _ = extract_eeg_from_mat(mat_data)
    datalen = eeg.shape[-1] if eeg.ndim > 1 else len(eeg)

    return {
        'scoring': scoring,
        'artifacts': artifacts,
        'datalen': datalen,
    }


def get_clean_nrem_mask(
    scoring: np.ndarray,
    artifacts: np.ndarray,
    datalen: int,
    fs: int = 1000,
    epoch_len_s: float = 30.0,
    nrem_stages: Tuple[int, ...] = (2, 3),
) -> np.ndarray:
    """Build a sample-level boolean mask: True = clean NREM sample.

    Parameters
    ----------
    scoring     : (n_epochs,) sleep stage per 30-s epoch
    artifacts   : (n_samples,) bool array, True = artifact
    datalen     : total number of samples
    fs          : sampling rate (Hz)
    epoch_len_s : duration of each scoring epoch in seconds
    nrem_stages : which stage labels count as NREM
    """
    epoch_samples = int(epoch_len_s * fs)
    nrem_mask = np.zeros(datalen, dtype=bool)
    for i, stage in enumerate(scoring):
        if stage in nrem_stages:
            start = i * epoch_samples
            end = min(start + epoch_samples, datalen)
            nrem_mask[start:end] = True

    # Remove artifact samples
    art = artifacts[:datalen] if len(artifacts) >= datalen else \
        np.pad(artifacts, (0, datalen - len(artifacts)))
    clean_mask = nrem_mask & ~art
    return clean_mask


def load_spindle_events(
    data_dir: str,
    pat_idx: int,
) -> Optional[np.ndarray]:
    """Load pre-annotated spindle event times (if present in .mat file).

    Returns sample indices as int array, or None if not found.
    """
    data_dir = Path(data_dir)
    mat_file = _find_subject_file(data_dir, pat_idx)
    mat_data = load_mat_file(str(mat_file))
    for k in ['spindle_times', 'spindles', 'spindle_events']:
        if k in mat_data:
            return np.array(mat_data[k]).ravel().astype(int)
    return None


def load_ripple_events(
    data_dir: str,
    pat_idx: int,
) -> Optional[np.ndarray]:
    """Load pre-annotated ripple event times (if present in .mat file).

    Returns sample indices as int array, or None if not found.
    """
    data_dir = Path(data_dir)
    mat_file = _find_subject_file(data_dir, pat_idx)
    mat_data = load_mat_file(str(mat_file))
    for k in ['ripple_times', 'ripples', 'ripple_events']:
        if k in mat_data:
            return np.array(mat_data[k]).ravel().astype(int)
    return None


# ---------------------------------------------------------------------------
# Convenience wrappers (kept for backward compatibility)
# ---------------------------------------------------------------------------

def load_subject_data(subject_dir: Path, channel: str = 'HC') -> Dict:
    """Load all data for a single subject from a directory."""
    mat_files = list(Path(subject_dir).glob('*.mat'))
    if not mat_files:
        raise FileNotFoundError(f"No .mat files in {subject_dir}")
    mat_data = load_mat_file(str(mat_files[0]))
    eeg_data, sfreq = extract_eeg_from_mat(mat_data, channel_name=channel)
    return {
        'eeg': eeg_data,
        'sfreq': sfreq,
        'mat_data': mat_data,
        'mat_file': mat_files[0],
    }


def load_eeg_data(mat_data: Dict) -> np.ndarray:
    """Extract raw EEG array from mat_data dict (backward compat)."""
    eeg_data, _ = extract_eeg_from_mat(mat_data)
    return eeg_data


def save_results(results: Dict, output_path: Path) -> None:
    """Pickle results to disk."""
    import pickle
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'wb') as f:
        pickle.dump(results, f)
    logger.info(f"Saved results to {output_path}")

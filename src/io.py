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
import mne
import logging

logger = logging.getLogger(__name__)


def load_mat_file(filepath: str) -> Dict:
    """Load a MATLAB .mat file.
    
    Args:
        filepath: Path to the .mat file
        
    Returns:
        Dictionary containing the MATLAB structure
        
    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If file is not a valid .mat file
    """
    filepath = Path(filepath)
    
    if not filepath.exists():
        raise FileNotFoundError(f"File not found: {filepath}")
    
    try:
        data = sio.loadmat(str(filepath), struct_as_record=False, squeeze_me=True)
        logger.info(f"Loaded .mat file: {filepath.name}")
        return data
    except Exception as e:
        # Try loading with h5py for MATLAB v7.3 files
        try:
            import h5py
            logger.info(f"Trying h5py for v7.3 file: {filepath.name}")
            with h5py.File(str(filepath), 'r') as f:
                # Convert h5py file to dictionary
                data = {}
                for key in list(f.keys()):
                    try:
                        # Try to load as dataset
                        data[key] = f[key][()]
                    except:
                        # If it's a group or has nested structure, store reference
                        data[key] = f[key]
                logger.info(f"Successfully loaded .mat file with h5py: {filepath.name}")
                return data
        except ImportError:
            logger.error("h5py not installed. Install it with: pip install h5py")
            raise ValueError(f"Error loading .mat file {filepath}: {str(e)}. Install h5py for v7.3 files.")


def extract_eeg_from_mat(mat_data: Dict, channel_name: Optional[str] = None) -> Tuple[np.ndarray, float]:
    """Extract EEG data and sampling rate from loaded .mat structure.
    
    The Ngo et al. dataset typically has fields like:
    - 'data' or 'lfp': EEG signal
    - 'fs' or 'srate': Sampling rate
    - 'channels' or 'ch_names': Channel labels
    
    Args:
        mat_data: Dictionary from loaded .mat file
        channel_name: Specific channel to extract (e.g., 'HC_L'). If None, uses first channel.
        
    Returns:
        Tuple of (eeg_data, sampling_rate)
        eeg_data: numpy array or shape (n_times,) or (n_channels, n_times)
        sampling_rate: float
    """
    
    # Look for EEG data with various possible key names
    available_keys = list(mat_data.keys())
    eeg_data = None
    sfreq = None
    
    # Common field names in the dataset
    data_keys = ['data', 'lfp', 'eeg', 'signal', 'lfpdata', 'trial']    srate_keys = ['fs', 'srate', 'sampling_rate', 'fsample', 'Fs']
    
    # Try to find EEG data
    for key in data_keys:
        if key in mat_data:
            eeg_data = np.array(mat_data[key])
            break
                
    # Special handling for FieldTrip 'trial' format (h5py references)
    if eeg_data is not None and 'trial' in mat_data:
        # FieldTrip stores trials as h5py references
        try:
            import h5py
            # Check if we got an h5py reference/group instead of actual data
            if isinstance(eeg_data, (h5py.Reference, h5py.Group, h5py.Dataset)):
                # Need to reopen file and extract trial data
                logger.warning("Field Trip 'trial' format detected but contains h5py references. Skipping for now.")
                eeg_data = None
            elif hasattr(eeg_data, 'shape') and len(eeg_data.shape) == 2 and eeg_data.shape[0] == 1:
                # If it's a 1xN array of references, we can't easily extract without file handle
                logger.warning("FieldTrip trial data appears to be references. Skipping.")
                eeg_data = None
        except ImportError:
            pass
    
    # Try to find sampling rate
    for key in srate_keys:
        if key in mat_data:
                    val = mat_data[key]
                    sfreq = float(np.asarray(val).item() if np.asarray(val).size == 1 else np.asarray(val).flat[0])            break
    
    if eeg_data is None:
        raise ValueError(f"Could not find EEG data. Available keys: {available_keys}")
    
    if sfreq is None:
        logger.warning(f"Could not find sampling rate. Using default 1000 Hz. Available keys: {available_keys}")
        sfreq = 1000.0
    
    return eeg_data, sfreq


def create_nrem_raw(eeg_data: np.ndarray, sfreq: float, channel_name: str = 'HC') -> mne.io.RawArray:
    """Create an MNE Raw object from NREM sleep data.
    
    Args:
        eeg_data: EEG time series data
        sfreq: Sampling frequency in Hz
        channel_name: Name of the channel
        
    Returns:
        MNE Raw object with the EEG data
    """
    # Ensure data is 2D (n_channels, n_times)
    if eeg_data.ndim == 1:
        eeg_data = eeg_data.reshape(1, -1)
    elif eeg_data.ndim == 2 and eeg_data.shape[0] > eeg_data.shape[1]:
        # If shape is (n_times, n_channels), transpose
        eeg_data = eeg_data.T
    
    n_channels = eeg_data.shape[0]
    
    # Create channel info
    if n_channels == 1:
        ch_names = [channel_name]
    else:
        ch_names = [f"{channel_name}_{i+1}" for i in range(n_channels)]
    
    ch_types = ['seeg'] * n_channels  # Stereo-EEG for intracranial recordings
    
    info = mne.create_info(ch_names=ch_names, sfreq=sfreq, ch_types=ch_types)
    raw = mne.io.RawArray(eeg_data, info)
    
    return raw


def load_sleep_stages(mat_data: Dict) -> Tuple[np.ndarray, np.ndarray]:
    """Load sleep stage annotations.
    
    Args:
        mat_data: Dictionary from loaded .mat file
        
    Returns:
        Tuple of (sleep_stages, time)
        sleep_stages: Array of sleep stage labels
        time: Time points for each stage
    """
    stage_keys = ['stages', 'hypnogram', 'sleep_stages', 'scoring']
    time_keys = ['time', 't', 'time_stages']
    
    stages = None
    time = None
    
    for key in stage_keys:
        if key in mat_data:
            stages = np.array(mat_data[key])
            break
    
    for key in time_keys:
        if key in mat_data:
            time = np.array(mat_data[key])
            break
    
    if stages is None:
        raise ValueError(f"Could not find sleep stages. Available keys: {list(mat_data.keys())}")
    
    return stages, time


def load_subject_data(subject_dir: Path, channel: str = "HC") -> Dict:
    """Load all data for a single subject.
    
    Args:
        subject_dir: Path to subject directory
        channel: Channel name to extract (default: "HC" for hippocampus)
        
    Returns:
        Dictionary with subject data including raw EEG, sampling rate, etc.
    """
    # Find .mat file in subject directory
    mat_files = list(subject_dir.glob("*.mat"))
    if not mat_files:
        raise FileNotFoundError(f"No .mat files found in {subject_dir}")
    
    mat_file = mat_files[0]  # Use first .mat file found
    logger.info(f"Loading subject data from: {mat_file}")
    
    # Load MATLAB file
    mat_data = load_mat_file(mat_file)
    eeg_data, sfreq = extract_eeg_from_mat(mat_data, channel_name=channel)
    
    # Create MNE Raw object
    raw = create_nrem_raw(eeg_data, sfreq, channel_name=channel)
    
    return {
        'raw': raw,
        'sfreq': sfreq,
        'mat_data': mat_data,
        'mat_file': mat_file
    }


def load_eeg_data(mat_data: Dict) -> np.ndarray:
    """Extract raw EEG data array from mat file.
    
    Args:
        mat_data: Dictionary from loaded .mat file
        
    Returns:
        EEG data as numpy array
    """
    eeg_data, _ = extract_eeg_from_mat(mat_data)
    return eeg_data


def save_results(results: Dict, output_path: Path) -> None:
    """Save analysis results to file.
    
    Args:
        results: Dictionary of results
        output_path: Path to save results
    """
    import pickle
    
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'wb') as f:
        pickle.dump(results, f)
    
    logger.info(f"Saved results to {output_path}")

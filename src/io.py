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
        raise ValueError(f"Error loading .mat file {filepath}: {str(e)}")


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
        eeg_data: numpy array of shape (n_times,) or (n_channels, n_times)
        sampling_rate: float
    """
    # Try common field names
    data = None
    for key in ['data', 'lfp', 'LFP_HC', 'eeg', 'signal']:
        if key in mat_data:
            data = mat_data[key]
            break
    
    if data is None:
        available_keys = [k for k in mat_data.keys() if not k.startswith('__')]
        raise ValueError(f"Could not find EEG data. Available keys: {available_keys}")
    
    # Get sampling rate
    sfreq = None
    for key in ['fs', 'srate', 'sfreq', 'sampling_rate']:
        if key in mat_data:
            sfreq = float(mat_data[key])
            break
    
    if sfreq is None:
        logger.warning("Sampling rate not found, assuming 1000 Hz")
        sfreq = 1000.0
    
    # Ensure data is numpy array
    data = np.array(data)
    
    # If 2D and we want a specific channel
    if data.ndim == 2 and channel_name is not None:
        if 'channels' in mat_data or 'ch_names' in mat_data:
            channel_names = mat_data.get('channels', mat_data.get('ch_names', []))
            try:
                ch_idx = list(channel_names).index(channel_name)
                data = data[ch_idx, :]
                logger.info(f"Extracted channel: {channel_name}")
            except ValueError:
                logger.warning(f"Channel {channel_name} not found, using first channel")
                data = data[0, :] if data.shape[0] < data.shape[1] else data[:, 0]
        else:
            data = data[0, :] if data.shape[0] < data.shape[1] else data[:, 0]
    
    # If still 2D, take first channel
    if data.ndim == 2:
        data = data[0, :] if data.shape[0] < data.shape[1] else data[:, 0]
    
    logger.info(f"EEG data shape: {data.shape}, sampling rate: {sfreq} Hz")
    return data, sfreq


def load_sleep_stages(mat_data: Dict) -> np.ndarray:
    """Extract sleep stage annotations from .mat file.
    
    Sleep stages are typically coded as:
    - 0: Wake
    - 1: REM
    - 2: N1 (Stage 1)
    - 3: N2 (Stage 2)
    - 4: N3 (Stage 3/SWS)
    
    Args:
        mat_data: Dictionary from loaded .mat file
        
    Returns:
        Array of sleep stage labels per epoch (30s epochs typically)
    """
    for key in ['sleep_stages', 'stages', 'hypnogram', 'sleep_scoring']:
        if key in mat_data:
            stages = np.array(mat_data[key])
            logger.info(f"Found sleep stages: {len(stages)} epochs")
            return stages
    
    logger.warning("No sleep stages found in data")
    return None


def create_mne_raw(data: np.ndarray, sfreq: float, ch_name: str = 'HC') -> mne.io.RawArray:
    """Create an MNE Raw object from numpy array.
    
    Args:
        data: EEG data array (n_times,) or (n_channels, n_times)
        sfreq: Sampling frequency in Hz
        ch_name: Channel name
        
    Returns:
        MNE Raw object
    """
    # Ensure 2D: (n_channels, n_times)
    if data.ndim == 1:
        data = data.reshape(1, -1)
    
    # Create channel info
    ch_names = [ch_name] if data.shape[0] == 1 else [f"{ch_name}_{i}" for i in range(data.shape[0])]
    ch_types = ['seeg'] * len(ch_names)  # Stereotactic EEG
    
    info = mne.create_info(ch_names=ch_names, sfreq=sfreq, ch_types=ch_types)
    raw = mne.io.RawArray(data, info, verbose='ERROR')
    
    logger.info(f"Created MNE Raw object: {raw}")
    return raw


def load_subject_data(subject_dir: Path, channel: str = 'HC') -> Dict:
    """Load all data for one subject.
    
    Args:
        subject_dir: Path to subject directory containing .mat files
        channel: Channel to extract (e.g., 'HC', 'HC_L', 'HC_R')
        
    Returns:
        Dictionary with keys:
        - 'raw': MNE Raw object
        - 'sleep_stages': Array of sleep stage labels
        - 'sfreq': Sampling rate
        - 'subject_id': Subject identifier
    """
    subject_dir = Path(subject_dir)
    
    if not subject_dir.exists():
        raise FileNotFoundError(f"Subject directory not found: {subject_dir}")
    
    # Find .mat files
    mat_files = list(subject_dir.glob('*.mat'))
    
    if not mat_files:
        raise FileNotFoundError(f"No .mat files found in {subject_dir}")
    
    # Load first .mat file (or combine if multiple)
    mat_file = mat_files[0]
    logger.info(f"Loading subject data from: {mat_file}")
    
    mat_data = load_mat_file(mat_file)
    eeg_data, sfreq = extract_eeg_from_mat(mat_data, channel_name=channel)
    sleep_stages = load_sleep_stages(mat_data)
    
    # Create MNE object
    raw = create_mne_raw(eeg_data, sfreq, ch_name=channel)
    
    return {
        'raw': raw,
        'sleep_stages': sleep_stages,
        'sfreq': sfreq,
        'subject_id': subject_dir.name,
        'mat_data': mat_data  # Keep original for reference
    }


def load_eeg_data(data_path: Path, channels: Optional[List[str]] = None) -> mne.io.Raw:
    """Main function to load EEG data.
    
    This is a simplified wrapper for compatibility with the pipeline.
    
    Args:
        data_path: Path to subject directory or .mat file
        channels: List of channel names to load (currently loads first only)
        
    Returns:
        MNE Raw object
    """
    data_path = Path(data_path)
    
    if data_path.is_dir():
        # Load from directory
        channel = channels[0] if channels else 'HC'
        subject_data = load_subject_data(data_path, channel=channel)
        return subject_data['raw']
    
    elif data_path.suffix == '.mat':
        # Load single file
        mat_data = load_mat_file(data_path)
        eeg_data, sfreq = extract_eeg_from_mat(mat_data)
        return create_mne_raw(eeg_data, sfreq)
    
    else:
        raise ValueError(f"Invalid data path: {data_path}")


def save_results(results: Dict, output_path: Path):
    """Save analysis results to file.
    
    Args:
        results: Dictionary containing analysis results
        output_path: Where to save (as .npz file)
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Convert to saveable format
    save_dict = {}
    for key, value in results.items():
        if isinstance(value, (np.ndarray, list, dict, str, int, float)):
            save_dict[key] = value
    
    np.savez(output_path, **save_dict)
    logger.info(f"Results saved to: {output_path}")

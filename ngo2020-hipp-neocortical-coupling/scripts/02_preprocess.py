#!/usr/bin/env python3
"""
Script 02: Preprocess Raw Data
==================================
Ngo et al. (2020) Reproduction Pipeline

This script loads raw .mat files downloaded from OSF and creates a clean,
organized dataset for analysis. Since the OSF data already contains detected
ripples and spindles, this script primarily organizes and validates the data.

Data Structure (from OSF):
  - data/raw/EEGs/pat01-14_HIPP.mat (raw hippocampal EEG)
  - data/raw/EEGs/pat01-14_HIPP_supplement.mat (supplementary data)
  - data/raw/Ripples/pat01-14_HIPP_ripples.mat (detected ripple events)
  - data/raw/Spindles/pat01-14_HIPP_spindles.mat (HIPP spindle detections)
  - data/raw/Spindles/pat01-14_NC_spindles.mat (neocortex spindle detections)
  - data/raw/ControlEvents/ngo_et_al_eLife2020_controlData_100sets/1-100/
      pat01-14_HIPP_controlNREM.mat, pat01-14_HIPP_controlREM.mat

Outputs:
  - data/processed/subjects.json (list of available patients and data files)
  - Validates data integrity and reports any missing files

Usage:
    python scripts/02_preprocess.py
    python scripts/02_preprocess.py --patient pat01  # Process specific patient
"""

import argparse
import glob
import json
from pathlib import Path
import numpy as np
import yaml
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

try:
    import h5py
except ImportError:
    h5py = None


def load_config():
    """Load configuration from config.yaml"""
    config_path = Path("config/config.yaml")
    if config_path.exists():
        with open(config_path, "r") as f:
            return yaml.safe_load(f)
    else:
        # Return default configuration
        return {
            'paths': {
                'raw_data': 'data/raw',
                'processed_data': 'data/processed'
            }
        }


def load_mat_file(filepath):
    """
    Load .mat file, trying different loaders for compatibility.
    
    Args:
        filepath: Path to .mat file
        
    Returns:
        Dictionary of loaded data
    """
    filepath = Path(filepath)
    
    # Try scipy.io first (fastest for older .mat files)
    if spio:
        try:
            return spio.loadmat(str(filepath), simplify_cells=True)
        except (NotImplementedError, ValueError):
            pass  # Fall through to mat73 or h5py
    
    # Try mat73 for MATLAB v7.3 files
    if mat73:
        try:
            return mat73.loadmat(str(filepath))
        except Exception:
            pass
    
    # Try h5py as last resort
    if h5py:
        try:
            data = {}
            with h5py.File(filepath, 'r') as f:
                for key in f.keys():
                    if not key.startswith('_'):
                        data[key] = f[key][:]
            return data
        except Exception:
            pass
    
    raise ImportError(
        f"Could not load {filepath}. Install mat73 or h5py: "
        "pip install mat73 h5py"
    )


def inspect_mat_file(filepath, max_keys=20):
    """
    Inspect a .mat file and return its structure.
    
    Args:
        filepath: Path to .mat file
        max_keys: Maximum number of keys to display
        
    Returns:
        Dictionary with file info
    """
    try:
        data = load_mat_file(filepath)
        keys = [k for k in data.keys() if not k.startswith('__')]
        
        info = {
            'filename': Path(filepath).name,
            'n_keys': len(keys),
            'keys': keys[:max_keys],
        }
        
        # Try to get shape information for arrays
        for key in keys[:5]:  # Only first 5 to avoid clutter
            val = data[key]
            if hasattr(val, 'shape'):
                info[f'{key}_shape'] = val.shape
            elif hasattr(val, '__len__'):
                info[f'{key}_len'] = len(val)
                
        return info
    except Exception as e:
        return {'filename': Path(filepath).name, 'error': str(e)}


def check_patient_data(patient_id, raw_dir):
    """
    Check which data files are available for a given patient.
    
    Args:
        patient_id: Patient identifier (e.g., 'pat01')
        raw_dir: Path to raw data directory
        
    Returns:
        Dictionary with file availability status
    """
    raw_dir = Path(raw_dir)
    
    files_status = {
        'patient_id': patient_id,
        'eeg_hipp': None,
        'eeg_hipp_supplement': None,
        'ripples_hipp': None,
        'spindles_hipp': None,
        'spindles_nc': None,
        'control_data_available': False,
    }
    
    # Check EEG files
    eeg_hipp = raw_dir / 'EEGs' / f'{patient_id}_HIPP.mat'
    if eeg_hipp.exists():
        files_status['eeg_hipp'] = str(eeg_hipp.relative_to(raw_dir))
    
    eeg_supp = raw_dir / 'EEGs' / f'{patient_id}_HIPP_supplement.mat'
    if eeg_supp.exists():
        files_status['eeg_hipp_supplement'] = str(eeg_supp.relative_to(raw_dir))
    
    # Check ripples
    ripples = raw_dir / 'Ripples' / f'{patient_id}_HIPP_ripples.mat'
    if ripples.exists():
        files_status['ripples_hipp'] = str(ripples.relative_to(raw_dir))
    
    # Check spindles
    spindles_hipp = raw_dir / 'Spindles' / f'{patient_id}_HIPP_spindles.mat'
    if spindles_hipp.exists():
        files_status['spindles_hipp'] = str(spindles_hipp.relative_to(raw_dir))
    
    spindles_nc = raw_dir / 'Spindles' / f'{patient_id}_NC_spindles.mat'
    if spindles_nc.exists():
        files_status['spindles_nc'] = str(spindles_nc.relative_to(raw_dir))
    
    # Check control data (check if at least one control set exists)
    control_dirs = list((raw_dir / 'ControlEvents' / 'ngo_et_al_eLife2020_controlData_100sets').glob('*'))
    if control_dirs:
        # Check if this patient has control data in any set
        for control_dir in control_dirs[:5]:  # Check first 5 sets
            control_nrem = control_dir / f'{patient_id}_HIPP_controlNREM.mat'
            if control_nrem.exists():
                files_status['control_data_available'] = True
                break
    
    return files_status


def main():
    parser = argparse.ArgumentParser(description="Organize and validate Ngo et al. (2020) data")
    parser.add_argument("--patient", type=str, help="Process specific patient (e.g., pat01)")
    parser.add_argument("--inspect", action="store_true", help="Inspect .mat file structure")
    parser.add_argument("--file", type=str, help="Specific file to inspect (with --inspect)")
    args = parser.parse_args()
    
    cfg = load_config()
    raw_dir = Path(cfg['paths']['raw_data'])
    processed_dir = Path(cfg['paths']['processed_data'])
    processed_dir.mkdir(parents=True, exist_ok=True)
    
    print("=" * 60)
    print("Ngo et al. (2020) Data Organization")
    print("=" * 60)
    
    # Inspect mode
    if args.inspect:
        if args.file:
            file_path = Path(args.file)
            if not file_path.exists():
                file_path = raw_dir / args.file
            print(f"\\nInspecting: {file_path}")
            info = inspect_mat_file(file_path)
            print(json.dumps(info, indent=2))
        else:
            print("\\nPlease specify a file with --file <path>")
        return
    
    # Find all patients by looking at EEG files
    eeg_dir = raw_dir / 'EEGs'
    if not eeg_dir.exists():
        print(f"\\nERROR: EEGs directory not found at {eeg_dir}")
        print("Please run: python scripts/01_download_data.py")
        return
    
    # Extract patient IDs from EEG filenames
    eeg_files = list(eeg_dir.glob('pat*_HIPP.mat'))
    patient_ids = sorted(set([f.name.split('_')[0] for f in eeg_files]))
    
    if not patient_ids:
        print(f"\\nNo patient data found in {eeg_dir}")
        return
    
    print(f"\\nFound {len(patient_ids)} patients: {', '.join(patient_ids)}")
    
    # Process specific patient or all
    if args.patient:
        if args.patient not in patient_ids:
            print(f"\\nERROR: Patient {args.patient} not found.")
            print(f"Available: {', '.join(patient_ids)}")
            return
        patients_to_process = [args.patient]
    else:
        patients_to_process = patient_ids
    
    # Check data availability for each patient
    print(f"\\nChecking data availability for {len(patients_to_process)} patient(s)...")
    
    all_patient_data = []
    for patient_id in tqdm(patients_to_process, desc="Patients"):
        patient_data = check_patient_data(patient_id, raw_dir)
        all_patient_data.append(patient_data)
    
    # Save summary
    summary_file = processed_dir / 'subjects.json'
    with open(summary_file, 'w') as f:
        json.dump({
            'n_patients': len(all_patient_data),
            'patients': all_patient_data,
            'data_structure': {
                'EEGs': 'Raw hippocampal and neocortex EEG recordings',
                'Ripples': 'Detected hippocampal ripple events',
                'Spindles': 'Detected sleep spindle events (HIPP and NC)',
                'ControlEvents': 'Shuffled control data for statistical testing (100 sets)'
            }
        }, f, indent=2)
    
    print(f"\\n{'='*60}")
    print("Data Availability Summary")
    print(f"{'='*60}")
    
    # Print summary table
    print(f"\\n{'Patient':<10} {'EEG':<5} {'Supp':<5} {'Ripples':<8} {'Spin_H':<8} {'Spin_NC':<8} {'Control':<8}")
    print("-" * 60)
    
    for pd in all_patient_data:
        print(f"{pd['patient_id']:<10} "
              f"{'✓' if pd['eeg_hipp'] else '✗':<5} "
              f"{'✓' if pd['eeg_hipp_supplement'] else '✗':<5} "
              f"{'✓' if pd['ripples_hipp'] else '✗':<8} "
              f"{'✓' if pd['spindles_hipp'] else '✗':<8} "
              f"{'✓' if pd['spindles_nc'] else '✗':<8} "
              f"{'✓' if pd['control_data_available'] else '✗':<8}")
    
    print(f"\\nSummary saved to: {summary_file}")
    
    # Print next steps
    print("\\n" + "="*60)
    print("Data Organization Complete!")
    print("="*60)
    print("""
The downloaded data is already pre-processed by the authors:
  - Ripples and spindles are already detected
  - Control events are pre-generated for statistical testing
  
Next steps:
  1. Inspect a sample file:
     python scripts/02_preprocess.py --inspect --file EEGs/pat01_HIPP.mat
  
  2. Run analysis scripts:
     python scripts/03_detect_spindles_ripples.py  # Verify/visualize detections
     python scripts/04_tfr_analysis.py             # Time-frequency analysis
     python scripts/05_coherence_pdc.py            # Coupling analysis
     python scripts/06_long_vs_short_ripples.py    # Compare ripple durations
     python scripts/07_plot_figures.py             # Generate figures
""")


if __name__ == "__main__":
    main()

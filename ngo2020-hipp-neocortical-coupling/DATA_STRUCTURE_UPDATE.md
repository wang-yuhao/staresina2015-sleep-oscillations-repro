# Data Structure Update - Ngo et al. (2020) Reproduction

**Date:** April 27, 2026  
**Status:** ✅ Critical files updated  
**Author:** Repository Maintenance

## Summary

The repository code has been updated to reflect the **actual OSF data structure** rather than the initially assumed structure. The OSF dataset is organized by data type (EEGs, Ripples, Spindles, ControlEvents) rather than by patient ID.

---

## Actual OSF Data Structure

The downloaded data from OSF (https://osf.io/3hpvr/) is organized as follows:

```
data/raw/
├── ControlEvents/
│   └── ngo_et_al_eLife2020_controlData_100sets/
│       ├── 1/
│       │   ├── pat01_HIPP_controlNREM.mat
│       │   ├── pat01_HIPP_controlREM.mat
│       │   ├── pat02_HIPP_controlNREM.mat
│       │   ├── pat02_HIPP_controlREM.mat
│       │   └── ... (up to pat14)
│       ├── 2/
│       │   └── ... (same structure)
│       └── ... (up to 100/)
├── EEGs/
│   ├── pat01_HIPP.mat
│   ├── pat01_HIPP_supplement.mat
│   ├── pat02_HIPP.mat
│   ├── pat02_HIPP_supplement.mat
│   └── ... (up to pat14)
├── Ripples/
│   ├── pat01_HIPP_ripples.mat
│   ├── pat02_HIPP_ripples.mat
│   └── ... (up to pat14)
└── Spindles/
    ├── pat01_HIPP_spindles.mat
    ├── pat01_NC_spindles.mat
    ├── pat02_HIPP_spindles.mat
    ├── pat02_NC_spindles.mat
    └── ... (up to pat14)
```

**Key Points:**
- **14 patients** (pat01 through pat14)
- **Pre-detected events**: Ripples and spindles are already detected by the authors
- **Control data**: 100 sets of shuffled control events for statistical comparison
- **Channels**: HIPP (hippocampus) and NC (neocortex, Cz electrode)

---

## Files Updated

### ✅ Completed Updates

1. **`scripts/01_download_data.py`**
   - Added recursive folder traversal for nested OSF directory structure
   - Updated to preserve OSF folder organization locally
   - Now correctly handles: `EEGs/`, `Ripples/`, `Spindles/`, `ControlEvents/`
   - Commit: Update 01_download_data.py for actual OSF data structure

2. **`scripts/02_preprocess.py`**
   - **Completely rewritten** as a data organization and validation script
   - No longer performs detection (data already contains detections)
   - Creates `data/processed/subjects.json` with file availability summary
   - Added `--inspect` mode to examine `.mat` file structures
   - Prints data availability table for all patients
   - Commit: Rewrite 02_preprocess.py for actual OSF data structure

3. **`config/config.yaml`**
   - Added `data_folders` section specifying OSF folder names
   - Added all 14 patient IDs (pat01-pat14)
   - Completed detection, TFR, coupling, and statistical parameters
   - Added visualization settings with color schemes
   - Commit: Update config.yaml for actual OSF data structure

###  Pending Updates

The following scripts still contain template code and need to be updated to work with the actual data structure:

4. **`scripts/03_detect_spindles_ripples.py`** (Template)
   - Should be converted to **verification and visualization** script
   - Load pre-detected events from `Ripples/` and `Spindles/` folders
   - Visualize example detections
   - Compare detection distributions with paper statistics

5. **`scripts/04_tfr_analysis.py`** (Template)  
   - Load EEG data from `EEGs/` folder
   - Load ripple events from `Ripples/` folder
   - Compute time-frequency representations
   - Use correct file paths as specified in config.yaml

6. **`scripts/05_coherence_pdc.py`** (Template)
   - Load hippocampal and neocortex spindle events
   - Load EEG signals
   - Compute coherence and PDC around ripple events

7. **`scripts/06_long_vs_short_ripples.py`** (Template)
   - Load ripple detections
   - Classify by duration (threshold: 70 ms from paper)
   - Compare NC spindle power between groups

8. **`scripts/07_plot_figures.py`** (Template)
   - Load results from previous scripts
   - Generate publication figures

9. **`README.md`** (Partially outdated)
   - Section "Step 2: Download the Dataset" (lines ~96-109) shows old structure
   - Should update manual download instructions to match actual OSF organization
   - Remove references to `sub-01/`, `sub-02/` folder structure
   - Update to show `EEGs/`, `Ripples/`, `Spindles/`, `ControlEvents/` structure

---

## Required Changes for Analysis Scripts (03-07)

### General Pattern

All analysis scripts should follow this pattern:

```python
import yaml
from pathlib import Path

# Load config
with open('config/config.yaml') as f:
    cfg = yaml.safe_load(f)

# Get paths
raw_dir = Path(cfg['paths']['raw_data'])
data_folders = cfg['data_folders']

# Load data for a specific patient
patient_id = 'pat01'

# Example: Load EEG
eeg_file = raw_dir / data_folders['eegs'] / f'{patient_id}_HIPP.mat'

# Example: Load ripples
ripples_file = raw_dir / data_folders['ripples'] / f'{patient_id}_HIPP_ripples.mat'

# Example: Load spindles
spindles_hipp = raw_dir / data_folders['spindles'] / f'{patient_id}_HIPP_spindles.mat'
spindles_nc = raw_dir / data_folders['spindles'] / f'{patient_id}_NC_spindles.mat'

# Example: Load control events (first set)
control_dir = raw_dir / data_folders['control_events'] / '1'
control_nrem = control_dir / f'{patient_id}_HIPP_controlNREM.mat'
```

### Specific Updates Needed

#### `03_detect_spindles_ripples.py`
```python
# Change from detection to visualization/verification
# Load pre-detected events:
ripples = load_mat(raw_dir / 'Ripples' / f'{patient_id}_HIPP_ripples.mat')
spindles_hipp = load_mat(raw_dir / 'Spindles' / f'{patient_id}_HIPP_spindles.mat')
spindles_nc = load_mat(raw_dir / 'Spindles' / f'{patient_id}_NC_spindles.mat')

# Visualize detections
# Compare statistics with paper
```

#### `04_tfr_analysis.py`
```python
# Load EEG and ripple events
eeg = load_mat(raw_dir / 'EEGs' / f'{patient_id}_HIPP.mat')
ripples = load_mat(raw_dir / 'Ripples' / f'{patient_id}_HIPP_ripples.mat')

# Compute TFR around ripple events
# Use control events for normalization
```

#### `05_coherence_pdc.py`
```python
# Load both channels
eeg_hipp = load_mat(raw_dir / 'EEGs' / f'{patient_id}_HIPP.mat')
# May need NC data from supplement file
eeg_nc_supp = load_mat(raw_dir / 'EEGs' / f'{patient_id}_HIPP_supplement.mat')

# Load events
spindles_hipp = load_mat(raw_dir / 'Spindles' / f'{patient_id}_HIPP_spindles.mat')
spindles_nc = load_mat(raw_dir / 'Spindles' / f'{patient_id}_NC_spindles.mat')
ripples = load_mat(raw_dir / 'Ripples' / f'{patient_id}_HIPP_ripples.mat')
```

#### `06_long_vs_short_ripples.py`
```python
# Load ripples and determine durations
ripples = load_mat(raw_dir / 'Ripples' / f'{patient_id}_HIPP_ripples.mat')

# Classify by duration (threshold: 0.07 s = 70 ms)
duration_threshold = cfg['detection']['ripple']['duration_threshold']
long_ripples = ripples[ripples['duration'] > duration_threshold]
short_ripples = ripples[ripples['duration'] <= duration_threshold]

# Compare NC spindle power
```

---

## How to Use

### 1. Download Data
```bash
python scripts/01_download_data.py
```

This will create the folder structure shown above.

### 2. Verify Data Organization
```bash
python scripts/02_preprocess.py
```

This creates `data/processed/subjects.json` with a summary of all available files.

### 3. Inspect a Sample File
```bash
python scripts/02_preprocess.py --inspect --file EEGs/pat01_HIPP.mat
```

This shows the keys and structure of the .mat file.

### 4. Update Analysis Scripts
Modify scripts 03-07 to load data from the correct paths as shown in this document.

### 5. Update README
Edit `README.md` lines ~96-109 to reflect the actual data structure.

---

## Testing Checklist

- [ ] Download data with `01_download_data.py`
- [ ] Verify folder structure matches this document
- [ ] Run `02_preprocess.py` to get subjects summary
- [ ] Inspect sample files with `--inspect` flag
- [ ] Update script 03 to load pre-detected events
- [ ] Update script 04 to use correct EEG paths
- [ ] Update script 05 for coherence analysis
- [ ] Update script 06 for ripple duration analysis
- [ ] Update script 07 for figure generation
- [ ] Update README.md data structure section
- [ ] Test full pipeline end-to-end

---

## Important Notes

1. **Ripples and spindles are pre-detected** - You don't need to implement detection algorithms; just load and analyze the provided detections.

2. **100 control sets** - For statistical comparison, the authors provide 100 shuffled control datasets in `ControlEvents/ngo_et_al_eLife2020_controlData_100sets/1` through `/100/`.

3. **File naming convention**:
   - `pat01` through `pat14` (14 patients)
   - `_HIPP` for hippocampus channel
   - `_NC` for neocortex channel (Cz electrode)
   - `_supplement` for additional data files

4. **MATLAB file compatibility**:
   - Some files may be MATLAB v7.3 format
   - Use `mat73` or `h5py` if `scipy.io.loadmat` fails
   - The `02_preprocess.py` script handles this automatically

---

## Questions or Issues?

If you encounter problems with the data structure:

1. Check the actual OSF website: https://osf.io/3hpvr/
2. Inspect files with the `--inspect` flag in `02_preprocess.py`
3. Verify paths in `config/config.yaml` match your data
4. Compare with original MATLAB code: https://github.com/episodicmemorylab/Ngo_et_al_eLife2020

---

**Last Updated:** April 27, 2026  
**Repository:** https://github.com/wang-yuhao/staresina2015-sleep-oscillations-repro

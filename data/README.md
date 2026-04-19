# Data Directory

This directory should contain the downloaded EEG data for analysis.

## Dataset Information

### Source
**Ngo et al. (2020)** - "Sleep spindles mediate hippocampal-neocortical coupling during long-duration ripples"

**Download from**: https://osf.io/3hpvr/

### Description
- Intracranial EEG recordings from epilepsy patients
- Hippocampal and neocortical channels
- Sleep scoring annotations included
- Data format: MATLAB .mat files
- Sampling rate: 1000 Hz

---

## Directory Structure

After downloading the dataset, organize it as follows:

```
data/
├── README.md  (this file)
├── raw/
│   ├── subject_01/
│   │   ├── *.mat  (EEG data files)
│   │   └── README.txt  (subject info if provided)
│   ├── subject_02/
│   │   └── *.mat
│   └── ...
└── processed/  (created automatically by pipeline)
    ├── subject_01/
    │   ├── so_events.npy
    │   ├── spindle_events.npy
    │   └── ripple_events.npy
    └── ...
```

---

## Setup Instructions

### 1. Download the Dataset

1. Go to https://osf.io/3hpvr/files/osfstorage
2. Download the data files:
   - Look for folders named with subject IDs
   - Download all .mat files
3. If the data is in a ZIP archive, extract it

### 2. Organize the Files

Place the downloaded files in `data/raw/` with the structure shown above:

```bash
# Example after download
data/raw/
├── sub-01/
│   └── night1_hippocampus.mat
├── sub-02/
│   └── night1_hippocampus.mat
└── sub-03/
    └── night1_hippocampus.mat
```

**Note**: The exact file and folder names may vary depending on how the OSF data is organized. The pipeline will automatically detect .mat files in subdirectories.

### 3. Verify Your Setup

Run this Python script to check your data structure:

```python
from pathlib import Path
import scipy.io as sio

data_dir = Path('data/raw')

# Find all .mat files
mat_files = list(data_dir.rglob('*.mat'))

print(f"Found {len(mat_files)} .mat files:")
for f in mat_files:
    print(f"  - {f.relative_to(data_dir)}")
    
    # Try to load one file to check structure
    if mat_files:
        test_file = mat_files[0]
        print(f"\nChecking file structure of: {test_file.name}")
        data = sio.loadmat(str(test_file))
        print(f"Available fields: {[k for k in data.keys() if not k.startswith('__')]}")
```

---

## Data Format Details

### Expected .mat File Contents

The .mat files should contain:

- **EEG/LFP data**: Field names might be:
  - `data`, `lfp`, `LFP_HC`, `eeg`, or similar
  - Shape: `(n_channels, n_timepoints)` or `(n_timepoints,)`

- **Sampling rate**: Field names might be:
  - `fs`, `srate`, `sfreq`, `sampling_rate`
  - Value: typically 1000 Hz

- **Sleep stages** (optional): Field names might be:
  - `sleep_stages`, `stages`, `hypnogram`, `sleep_scoring`
  - Encoding: 0=Wake, 1=REM, 2=N1, 3=N2, 4=N3

- **Channel names** (optional):
  - `channels`, `ch_names`, `channel_labels`

### Inspecting Your Data

To see what's in your .mat files:

```python
import scipy.io as sio

# Load a file
data = sio.loadmat('data/raw/subject_01/filename.mat')

# Print all variables
for key in data.keys():
    if not key.startswith('__'):
        val = data[key]
        print(f"{key}: {type(val)}, shape={getattr(val, 'shape', 'N/A')}")
```

---

## Troubleshooting

### "No .mat files found"
- Check that you've extracted any ZIP archives
- Ensure files are in `data/raw/` subdirectories
- Verify file extensions are `.mat` (not `.MAT` or other)

### "Could not find EEG data field"
- Run the inspection script above to see available fields
- Update `src/io.py` if your data uses different field names
- Check the OSF project page for documentation

### "File not loading correctly"
- Ensure MATLAB files are version 7.3 or earlier
- If files are MATLAB v7.3, you may need `h5py`:
  ```bash
  pip install h5py
  ```
  And modify the loading code to use `h5py.File()` instead of `scipy.io.loadmat()`

---
## Privacy & Ethics

⚠️ **Important**: This data comes from epilepsy patients and should be:
- Used only for research and education
- Not shared publicly beyond the OSF repository
- Cited appropriately in any publications
- Handled according to your institution's data policies

### Citation

If you use this data, please cite:

```
Ngo, H.-V. V., Fell, J., & Staresina, B. (2020). Sleep spindles mediate 
hippocampal-neocortical coupling during long-duration ripples. eLife, 9, e57011.
https://doi.org/10.7554/eLife.57011
```

---

## Next Steps

Once your data is organized:

1. Update `configs/analysis.yaml` with your subject IDs
2. Run the example notebook: `notebooks/01_getting_started.ipynb`
3. Or run the full pipeline: `python scripts/run_pipeline.py`

---

## Questions?

If you encounter issues:
1. Check the main README.md for setup instructions
2. Look at the example notebook for usage patterns
3. Open a GitHub issue with details about your problem

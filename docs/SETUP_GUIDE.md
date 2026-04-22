# Setup Guide — Staresina et al. 2015 Sleep Oscillation Reproduction

This guide walks you through every step from a fresh Python environment to fully
reproduced figures. Follow Steps 1–9 in order.

---

## Step 1 — Check Python version

```bash
python --version   # need Python 3.8 or higher
```

---

## Step 2 — Create project folder structure

```
staresina_repro/
  src/        ← Python source files (already in this repo)
  data/
    raw/      ← put .mat files here (Step 5)
  results/    ← figures and CSVs appear here
  configs/    ← analysis.yaml config file
```

Clone this repository first:

```bash
git clone https://github.com/wang-yuhao/staresina2015-sleep-oscillations-repro.git
cd staresina2015-sleep-oscillations-repro
mkdir -p data/raw results
```

---

## Step 3 — Create a virtual environment

```bash
python -m venv venv

# Activate (Linux / macOS)
source venv/bin/activate

# Activate (Windows PowerShell)
venv\Scripts\Activate.ps1
```

---

## Step 4 — Install dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

Key packages installed:

| Package | Purpose |
|---|---|
| `numpy`, `scipy` | Core signal processing |
| `pandas` | Event DataFrames |
| `matplotlib`, `seaborn` | Plotting |
| `h5py` | MATLAB v7.3 HDF5 files |
| `mne` | EDF loading (optional) |
| `pyyaml` | Config files |

---

## Step 5 — Download the dataset

1. Go to <https://osf.io/3hpvr>
2. Download all `.mat` files (there are 14 patient files)
3. Unzip and place **all** `.mat` files into `data/raw/`

Verify:
```bash
ls data/raw/*.mat   # should list ~14 files
```

---

## Step 6 — Discover channel names (IMPORTANT)

Before running the pipeline, inspect one file to find the exact channel labels:

```python
from src.io import load_mat_file

mat = load_mat_file('data/raw/pat01.mat')   # use actual filename
print(list(mat.keys()))   # shows all top-level fields

# If channel names exist:
import numpy as np
for k in ['ch_names', 'channels', 'label']:
    if k in mat:
        print(k, ':', list(mat[k]))
        break
```

Common patterns you'll see:
- Hippocampal: `LH1`, `LH2`, `RH1`, `rHC1`, `HC_L` …
- Neocortical: `Cz`, `EEG_Cz` …

Note down the **prefix** (e.g. `LH` or `RH`) — you'll pass this as `--hipp_kw`.

---

## Step 7 — Single-subject test run

Always test on 1 subject before running all 14:

```bash
# Run pipeline on subject 1 only
python -m src.pipeline \
  --config configs/analysis.yaml \
  --subjects 1
```

Or use the `analyze.py` module directly in Python:

```python
from src.analyze import run_subject

result = run_subject(
    data_dir='data/raw',
    pat_idx=1,
    hipp_channel='LH',    # adjust to your channel prefix
    nc_channel='Cz',
    output_dir='results',
    fs=1000,
)

print('SOs detected  :', len(result['so_events']))
print('Spindles      :', len(result['sp_events']))
print('Ripples       :', len(result['rp_events']))
```

**Expected counts for a single subject (NREM night):**

| Event | Expected |
|---|---|
| Slow Oscillations | 100–500 |
| Spindles | 200–800 |
| Ripples | 50–300 |

---

## Step 8 — Troubleshooting

### Error: `FileNotFoundError: No .mat file found for patient 1`
- Check the actual filename: `ls data/raw/`
- The loader tries `pat01.mat`, `pat1.mat`, `sub-01.mat`, `subject01.mat`
- If your files are named differently (e.g. `p1_night.mat`), use `load_mat_file()` directly

### Error: `Could not find EEG data. Available keys: [...]`
- Print `list(mat.keys())` and look for the field holding the signal
- Common names: `data`, `lfp`, `eeg`, `signal`
- If it's named something else, pass it to `extract_eeg_from_mat(mat, channel_name='your_key')`

### Error: `AssertionError: fs=... too low for ripple detection`
- Ripple detection (80–100 Hz) requires fs ≥ 200 Hz
- The Ngo 2020 dataset uses 1000 Hz — check you're reading the right field
- Wrong field can give a 1×N time vector instead of the signal

### 0 events detected
- Check that `clean_mask.mean()` > 0 (run `from src.preprocess import compute_artifact_mask`)
- The z-score threshold may be too strict for your data — lower `z_amp` from 4.0 to 5.0
- Check signal units: the dataset is in µV; if values are in V (very small), multiply ×1e6

### `ValueError: Error loading .mat file ... Install h5py for v7.3 files`
- Run `pip install h5py` — the file is saved in MATLAB v7.3 (HDF5) format

---

## Step 9 — Full group run (all 14 subjects)

```bash
python -m src.pipeline --config configs/analysis.yaml
```

This will take **20–90 minutes** depending on your hardware.

Results are saved to `results/` as:
- `pat01/so_events.csv`, `sp_events.csv`, `rp_events.csv`
- `pat01/tfr_so_avg_power.npy`, `tfr_sp_avg_power.npy`
- `pat01/pac_so_sp_MI.npy`, `pac_sp_rp_MI.npy`
- `fig2_so_locked_tfr.png`, `fig3_spindle_locked_tfr.png`

---

## Step 10 — Expected results vs. paper

Comparison against Staresina et al. 2015 Table 2 / Ngo et al. 2020 Table 2:

| Metric | Paper reports | Your output |
|---|---|---|
| Spindle density | ~5 /min NREM | Check `sp_events.csv` |
| Ripple density | ~1.2 /min NREM | Check `rp_events.csv` |
| SO trough amplitude | > 75th percentile | Threshold applied |
| Spindle–Ripple nesting | Rayleigh p < 0.001 | PAC MI > 0 |

---

## Step 11 — Adjust thresholds

If event counts are too high or too low, edit `configs/analysis.yaml`:

```yaml
detection:
  spindles:
    threshold: 2.0   # lower -> more spindles; raise to 3.0 for stricter
  slow_oscillations:
    amplitude_threshold: 75   # percentile; lower -> more SOs
  ripples:
    threshold: 3.0   # z-score; lower -> more ripples
```

---

## Module Overview

| File | What it does |
|---|---|
| `src/io.py` | Load `.mat` files, extract EEG, build NREM+artifact mask |
| `src/preprocess.py` | Bandpass, notch filter, artifact detection |
| `src/detect_events.py` | SO / spindle / ripple detectors |
| `src/tfr.py` | Morlet wavelet TFR, event-locked averages |
| `src/pac.py` | Modulation Index (Tort 2010), PAC comodulogram |
| `src/analyze.py` | Single-subject orchestration |
| `src/plots.py` | Figure generation |
| `src/pipeline.py` | CLI entry point, group-level analysis |
| `src/stats.py` | t-tests, cluster permutation testing |

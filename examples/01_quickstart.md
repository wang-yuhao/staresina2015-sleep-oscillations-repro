# Quickstart Guide: Running the Sleep Oscillation Analysis

This guide will walk you through running the complete analysis pipeline step-by-step.

## Prerequisites

- Python 3.8 or higher
- Downloaded Ngo et al. dataset from OSF
- At least 10GB of disk space

## Step 1: Clone and Setup the Repository

```bash
# Clone the repository
git clone https://github.com/wang-yuhao/staresina2015-sleep-oscillations-repro.git
cd staresina2015-sleep-oscillations-repro

# Create a virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install the package in editable mode with all dependencies
pip install -e .[dev]
```

## Step 2: Organize Your Downloaded Data

After downloading the Ngo dataset, organize it automatically:

```bash
python scripts/organize_data.py \
    --source ~/Downloads/ngo_dataset \
    --dest data/raw \
    --dry-run  # First do a dry run to check

# If everything looks good, run without --dry-run
python scripts/organize_data.py \
    --source ~/Downloads/ngo_dataset \
    --dest data/raw
```

This will:
- Scan all .mat files in your download directory
- Extract subject IDs from filenames
- Organize files into `data/raw/sub-01/`, `data/raw/sub-02/`, etc.
- Generate a report in `data/raw/organization_report.txt`

**Principle:** The Ngo dataset contains EEG recordings from multiple subjects. Each recording is stored as a MATLAB .mat file. The organization script uses regex pattern matching to identify which files belong to which subjects, then creates a standardized directory structure that the analysis pipeline expects.

## Step 3: Configure the Analysis

The analysis configuration is in `configs/analysis.yaml`. Review and adjust if needed:

```yaml
data:
  raw_dir: "data/raw"
  processed_dir: "data/processed"
  
preprocessing:
  sampling_rate: 1000  # Hz
  bandpass:
    low_freq: 0.5
    high_freq: 100
  notch_freq: 50  # Remove power line noise

detection:
  slow_oscillations:
    freq_range: [0.5, 1.2]  # Hz
    min_duration: 0.8  # seconds
    max_duration: 2.0
  
  spindles:
    freq_range: [11, 16]  # Hz
    min_duration: 0.5
    max_duration: 2.5
  
  ripples:
    freq_range: [80, 100]  # Hz
    min_duration: 0.02
    max_duration: 0.2
```

**Principle:** These parameters define what counts as each type of brain oscillation. Slow oscillations are low-frequency (<1 Hz) waves during deep sleep. Sleep spindles are 11-16 Hz bursts. Ripples are fast (80-100 Hz) hippocampal events. The paper found these three types are hierarchically nested.

## Step 4: Run the Analysis Pipeline

### Option A: Run Everything at Once

```bash
python scripts/run_pipeline.py \
    --config configs/analysis.yaml \
    --output-dir results/
```

### Option B: Run Step-by-Step (Recommended for Learning)

```python
from src.io import load_data
from src.preprocessing import preprocess_signal
from src.detect_so import detect_slow_oscillations
from src.detect_spindles import detect_spindles
from src.detect_ripples import detect_ripples
from src.coupling import compute_phase_amplitude_coupling
from src.visualization import plot_coupling_results

# 1. Load data for one subject
data = load_data('data/raw/sub-01')
print(f"Loaded {len(data)} channels")

# 2. Preprocess the signal
data_clean = preprocess_signal(
    data, 
    sampling_rate=1000,
    bandpass=(0.5, 100),
    notch_freq=50
)

# 3. Detect slow oscillations
so_events = detect_slow_oscillations(
    data_clean,
    freq_range=(0.5, 1.2),
    min_duration=0.8
)
print(f"Found {len(so_events)} slow oscillations")

# 4. Detect sleep spindles
spindle_events = detect_spindles(
    data_clean,
    freq_range=(11, 16),
    min_duration=0.5
)
print(f"Found {len(spindle_events)} spindles")

# 5. Detect ripples
ripple_events = detect_ripples(
    data_clean,
    freq_range=(80, 100),
    min_duration=0.02
)
print(f"Found {len(ripple_events)} ripples")

# 6. Compute coupling between oscillations
coupling_results = compute_phase_amplitude_coupling(
    so_events, spindle_events, ripple_events
)

# 7. Visualize results
plot_coupling_results(coupling_results, save_path='results/coupling.png')
```

**Principle Behind Each Step:**

1. **Loading Data**: Reads MATLAB files containing iEEG recordings from hippocampus
2. **Preprocessing**: Removes noise and filters signal to relevant frequencies
3. **Event Detection**: Uses bandpass filtering + threshold detection to find oscillations
4. **Coupling Analysis**: Checks if spindles occur at specific phases of slow oscillations, and if ripples occur during spindles
5. **Visualization**: Creates plots showing temporal relationships between oscillations

## Step 5: Verify Your Results

Run the unit tests to ensure everything works:

```bash
pytest tests/ -v
```

Check the generated results:

```bash
ls results/
# You should see:
# - coupling_matrix.npy
# - slow_oscillations.csv
# - spindles.csv
# - ripples.csv
# - figures/
```

## Expected Output

The analysis will produce:

1. **Event Files**: CSV files listing all detected oscillations with timing info
2. **Coupling Metrics**: Numpy arrays quantifying phase-amplitude coupling
3. **Figures**: 
   - Time series showing nested oscillations
   - Phase-amplitude coupling matrices
   - Distribution of coupling strengths

## Understanding the Results

The key finding to reproduce: **Ripples preferentially occur during the "up-state" of slow oscillations, when spindles are also active.**

Look for:
- High phase-amplitude coupling values (>0.3)
- Ripples concentrated at ~90° phase of slow oscillations
- Spindles modulating ripple occurrence

## Troubleshooting

### Issue: "No .mat files found"
**Solution**: Check that you've downloaded the Ngo dataset and the path in --source is correct

### Issue: "Memory Error"
**Solution**: Process one subject at a time, or reduce the data size

### Issue: "No events detected"
**Solution**: Your detection thresholds might be too strict. Try adjusting the parameters in `configs/analysis.yaml`

## Next Steps

- Read `docs/METHODOLOGY.md` for detailed explanation of methods
- Check `examples/02_advanced_analysis.md` for more sophisticated analyses
- Modify detection parameters to explore sensitivity
- Compare results across different subjects

## References

Staresina et al. (2015). "Hierarchical nesting of slow oscillations, spindles and ripples in the human hippocampus during sleep." Nature Neuroscience, 18(11), 1679-1686.

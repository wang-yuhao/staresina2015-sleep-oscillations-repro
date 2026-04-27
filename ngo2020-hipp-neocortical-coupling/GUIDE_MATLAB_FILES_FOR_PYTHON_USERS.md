# Understanding .MAT Files for Python Users

**A Beginner's Guide to MATLAB Data Files in Neuroscience Research**

---

## What is a .MAT File?

A **.mat file** is MATLAB's native file format for saving data. Think of it as MATLAB's version of a `.pkl` (pickle) file in Python or a `.csv` file, but specifically designed to store MATLAB workspace variables.

### Key Characteristics:
- **Binary format**: Not human-readable like CSV or JSON
- **Preserves data types**: Stores arrays, structures, cell arrays with their original types
- **Cross-platform**: Can be read on Windows, Mac, Linux
- **Commonly used in research**: Especially in neuroscience, signal processing, and engineering

---

## Why Do Researchers Use .MAT Files?

Many neuroscience labs use MATLAB for data analysis because:
1. **Legacy tools**: Established signal processing toolboxes (e.g., EEGLAB, FieldTrip)
2. **Easy matrix operations**: MATLAB is designed for array manipulation
3. **Standardization**: Common format for sharing data between research groups
4. **Rich metadata**: Can store complex nested structures

For the Ngo et al. (2020) paper, the authors processed EEG data in MATLAB and shared it in .mat format on OSF.

---

## .MAT File Analogy for Python Users

If you're familiar with Python data structures, here's how .mat files map:

| MATLAB (in .mat)    | Python Equivalent          | Description                          |
|---------------------|----------------------------|--------------------------------------|
| **Array/Matrix**    | `numpy.ndarray`            | Numeric data (EEG signals, timestamps) |
| **Structure**       | `dict` or class object     | Group of named variables            |
| **Cell array**      | `list` of mixed types      | Container for heterogeneous data    |
| **String**          | `str`                      | Text data                           |

### Example Comparison:

**MATLAB .mat file contains:**
```matlab
data.signal = [1.2, 3.4, 5.6, ...]        % 1D array
data.srate = 1000                          % scalar
data.channels = {'HIPP', 'NC'}            % cell array of strings
data.events.onsets = [10, 25, 47, ...]    % nested structure
```

**After loading in Python:**
```python
{
    'signal': array([1.2, 3.4, 5.6, ...]),    # NumPy array
    'srate': 1000,                             # int
    'channels': ['HIPP', 'NC'],                # list
    'events': {
        'onsets': array([10, 25, 47, ...])     # nested dict
    }
}
```

---

## How to Load .MAT Files in Python

There are **three main libraries** to load .mat files in Python, each for different file versions:

### 1. **scipy.io.loadmat** (Most Common)

**Best for:** MATLAB v7 and earlier (most research data)

```python
import scipy.io

# Load the file
data = scipy.io.loadmat('pat01_HIPP.mat')

# Access variables
signal = data['signal']           # Returns NumPy array
sampling_rate = data['srate']     # Returns array([[1000]])
print(signal.shape)
```

**Pros:**
- Fast and lightweight
- Built into SciPy (already installed)
- Works for most .mat files

**Cons:**
- Doesn't support MATLAB v7.3+ files (HDF5-based)
- Returns scalars as 2D arrays (requires `[0, 0]` indexing)

**Simplify with `simplify_cells=True`:**
```python
data = scipy.io.loadmat('file.mat', simplify_cells=True)
# Now data['srate'] returns 1000 instead of array([[1000]])
```

---

### 2. **mat73** (For Large Modern Files)

**Best for:** MATLAB v7.3+ files (HDF5 format)

```python
import mat73

# Load the file
data = mat73.loadmat('pat01_HIPP.mat')

# Access variables (same as scipy)
signal = data['signal']
```

**When to use:**
- If `scipy.io.loadmat` throws an error like:
  ```
  NotImplementedError: HDF5 v7.3+ files are not supported
  ```

**Installation:**
```bash
pip install mat73
```

---

### 3. **h5py** (Low-Level HDF5 Access)

**Best for:** When you need fine control over large v7.3 files

```python
import h5py
import numpy as np

# Open the file
with h5py.File('pat01_HIPP.mat', 'r') as f:
    # List all variables
    print(list(f.keys()))
    
    # Load specific variable
    signal = np.array(f['signal'])
```

**Pros:**
- Direct access to HDF5 structure
- Memory-efficient (can load parts of large arrays)

**Cons:**
- More complex syntax
- Need to understand HDF5 structure

---

## Practical Example: Loading Ngo et al. (2020) Data

Let's load one of the EEG files from your project:

### Step 1: Inspect the File

```python
import scipy.io

# Try scipy first (fastest method)
try:
    data = scipy.io.loadmat('data/raw/EEGs/pat01_HIPP.mat', simplify_cells=True)
    print("✓ Loaded with scipy.io")
except NotImplementedError:
    # File is MATLAB v7.3, use mat73
    import mat73
    data = mat73.loadmat('data/raw/EEGs/pat01_HIPP.mat')
    print("✓ Loaded with mat73")

# See what's inside
print("\nVariables in file:")
for key in data.keys():
    if not key.startswith('__'):  # Skip MATLAB metadata
        print(f"  {key}: {type(data[key])}")
```

**Expected output:**
```
✓ Loaded with scipy.io

Variables in file:
  signal: <class 'numpy.ndarray'>
  srate: <class 'int'>
  time: <class 'numpy.ndarray'>
  events: <class 'dict'>
```

---

### Step 2: Extract EEG Signal

```python
import numpy as np

# Load the file
data = scipy.io.loadmat('data/raw/EEGs/pat01_HIPP.mat', simplify_cells=True)

# Extract signal (hypothetical structure - inspect first!)
eeg_signal = data['signal']          # NumPy array
sampling_rate = data['srate']         # e.g., 1000 Hz
duration_sec = len(eeg_signal) / sampling_rate

print(f"EEG signal shape: {eeg_signal.shape}")
print(f"Sampling rate: {sampling_rate} Hz")
print(f"Duration: {duration_sec / 60:.1f} minutes")
```

---

### Step 3: Load Detected Events (Ripples/Spindles)

```python
# Load ripple detections
ripples = scipy.io.loadmat('data/raw/Ripples/pat01_HIPP_ripples.mat', simplify_cells=True)

# Typical structure (adapt based on actual file):
ripple_onsets = ripples['onsets']      # Start times (in seconds or samples)
ripple_durations = ripples['durations'] # Duration of each ripple
ripple_peaks = ripples['peaks']         # Peak amplitudes

print(f"Number of ripples detected: {len(ripple_onsets)}")
print(f"First 5 ripple start times (s): {ripple_onsets[:5]}")
```

---

## Common Issues and Solutions

### Issue 1: "NotImplementedError: HDF5 v7.3"

**Solution:**
```python
# Instead of scipy.io:
import mat73
data = mat73.loadmat('file.mat')
```

---

### Issue 2: Scalars Return as 2D Arrays

**Problem:**
```python
data = scipy.io.loadmat('file.mat')
srate = data['srate']  # Returns array([[1000]]) instead of 1000
```

**Solutions:**
```python
# Option 1: Use simplify_cells=True
data = scipy.io.loadmat('file.mat', simplify_cells=True)
srate = data['srate']  # Now returns 1000

# Option 2: Manual extraction
srate = data['srate'][0, 0]  # Extract scalar from 2D array
```

---

### Issue 3: "File does not exist"

**Check your path:**
```python
from pathlib import Path

file_path = Path('data/raw/EEGs/pat01_HIPP.mat')
if not file_path.exists():
    print(f"File not found: {file_path}")
    print(f"Current directory: {Path.cwd()}")
else:
    data = scipy.io.loadmat(file_path)
```

---

### Issue 4: Unknown Variable Names

**Inspect the file first:**
```python
import scipy.io

data = scipy.io.loadmat('file.mat')

# List all variables
print("Available variables:")
for key in data.keys():
    if not key.startswith('__'):
        value = data[key]
        if hasattr(value, 'shape'):
            print(f"  {key}: shape={value.shape}, dtype={value.dtype}")
        else:
            print(f"  {key}: type={type(value)}")
```

---

## Unified Loading Function (Recommended)

Use this helper function in your scripts:

```python
def load_mat_file(filepath):
    """
    Load .mat file with automatic version detection.
    
    Args:
        filepath: Path to .mat file
        
    Returns:
        Dictionary of variables
    """
    from pathlib import Path
    import scipy.io
    
    filepath = Path(filepath)
    
    # Try scipy.io first (fastest)
    try:
        return scipy.io.loadmat(str(filepath), simplify_cells=True)
    except (NotImplementedError, ValueError):
        pass  # Fall through to mat73
    
    # Try mat73 for v7.3 files
    try:
        import mat73
        return mat73.loadmat(str(filepath))
    except ImportError:
        print("ERROR: Install mat73 for MATLAB v7.3 files:")
        print("  pip install mat73")
        raise
    except Exception:
        pass  # Fall through to h5py
    
    # Last resort: h5py
    try:
        import h5py
        import numpy as np
        
        data = {}
        with h5py.File(filepath, 'r') as f:
            for key in f.keys():
                if not key.startswith('_'):
                    data[key] = np.array(f[key])
        return data
    except ImportError:
        print("ERROR: Install h5py for HDF5 files:")
        print("  pip install h5py")
        raise

# Usage:
data = load_mat_file('data/raw/EEGs/pat01_HIPP.mat')
```

---

## What's Inside Your Ngo et al. (2020) .MAT Files?

Based on the data structure, here's what to expect:

### **EEGs/pat01_HIPP.mat**
Likely contains:
- `signal` or `data`: Raw EEG time series (samples)
- `srate` or `fs`: Sampling rate (probably 1000 Hz)
- `time`: Time vector
- `channels`: Channel names (e.g., 'HIPP')

### **Ripples/pat01_HIPP_ripples.mat**
Likely contains:
- `onsets`: Start times of ripple events
- `offsets` or `durations`: End times or durations
- `peaks`: Peak timestamps
- `amplitudes`: Peak amplitudes
- `frequencies`: Dominant frequencies (80-100 Hz)

### **Spindles/pat01_HIPP_spindles.mat**
Similar structure to ripples, but for spindle events (12-16 Hz)

### **ControlEvents/.../pat01_HIPP_controlNREM.mat**
Shuffled/randomized event times for statistical comparison

---

## Quick Reference Cheat Sheet

```python
# 1. Import
import scipy.io
import mat73  # if needed
import h5py   # if needed

# 2. Load file
data = scipy.io.loadmat('file.mat', simplify_cells=True)

# 3. Inspect contents
print(list(data.keys()))

# 4. Extract variable
signal = data['signal']

# 5. Check shape and type
print(f"Shape: {signal.shape}, Type: {type(signal)}")

# 6. Convert to DataFrame (optional)
import pandas as pd
df = pd.DataFrame(data['events'])
```

---

## Summary

| Task                          | Command                                           |
|-------------------------------|---------------------------------------------------|
| Load v7 .mat file             | `scipy.io.loadmat('file.mat', simplify_cells=True)` |
| Load v7.3 .mat file           | `mat73.loadmat('file.mat')`                      |
| List variables                | `data.keys()`                                    |
| Access variable               | `data['variable_name']`                          |
| Check array shape             | `data['signal'].shape`                           |
| Extract scalar                | `data['value'][0, 0]` or use `simplify_cells=True` |

---

## Next Steps

1. **Download the data**: `python scripts/01_download_data.py`
2. **Inspect a file**: `python scripts/02_preprocess.py --inspect --file EEGs/pat01_HIPP.mat`
3. **Try loading**: Use the examples above in a Jupyter notebook
4. **Explore the structure**: Print shapes and types to understand the data

---

## Additional Resources

- **SciPy documentation**: https://docs.scipy.org/doc/scipy/reference/generated/scipy.io.loadmat.html
- **mat73 GitHub**: https://github.com/skjerns/mat73
- **h5py documentation**: https://docs.h5py.org/

---

**Questions?** Check the `DATA_STRUCTURE_UPDATE.md` file for project-specific guidance!

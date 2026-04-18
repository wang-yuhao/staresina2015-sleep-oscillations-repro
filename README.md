# staresina2015-sleep-oscillations-repro
# Staresina et al. 2015 — Sleep Oscillation Analysis Reproduction

[![CI](https://github.com/wang-yuhao/staresina2015-sleep-oscillations-repro/actions/workflows/ci.yml/badge.svg)](https://github.com/wang-yuhao/staresina2015-sleep-oscillations-repro/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)

## 📄 Paper Overview

This repository reproduces the key findings from:

**Staresina, B. P., Bergmann, T. O., Bonnefond, M., van der Meij, R., Jensen, O., Demarchi, G., ... & Fell, J. (2015).** *Hierarchical nesting of slow oscillations, spindles and ripples in the human hippocampus during sleep.* **Nature Neuroscience, 18(11), 1679-1686.**

### Key Findings
The paper demonstrates that during NREM sleep:
1. **Slow oscillations (SO, 0.5-1.25 Hz)** coordinate activity across brain regions
2. **Sleep spindles (9-16 Hz)** occur preferentially at SO troughs
3. **Hippocampal ripples (80-100 Hz)** nest within spindles
4. This three-tier hierarchy supports memory consolidation

---

## 🎯 For Data Engineers: What This Project Does

As a data engineer without neuroscience background, you need to understand that this project analyzes **brainwave recordings during sleep** to find **rhythmic patterns**. Think of it like finding patterns in time-series sensor data:

- **Slow Oscillations (SO)**: Like detecting slow waves in accelerometer data (~1 Hz)
- **Spindles**: Faster bursts within those slow waves (9-16 Hz)
- **Ripples**: Very high frequency events nested in spindles (80-100 Hz)

The pipeline applies signal processing (filtering, Fourier transforms, wavelet analysis) to detect these patterns and measure how they interact.

---

## 🚀 Quick Start

### 1. Clone the Repository
```bash
git clone https://github.com/wang-yuhao/staresina2015-sleep-oscillations-repro.git
cd staresina2015-sleep-oscillations-repro
```

### 2. Set Up Environment
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Download Data
The original Staresina 2015 data is not publicly available. We use the Ngo et al. 2020 dataset from the same lab:

**Dataset**: [OSF - Ngo et al. 2020](https://osf.io/3hpvr/)

Download and place data in `data/raw/`:
```
data/
└── raw/
    ├── sub-01/
    ├── sub-02/
    └── ...
```

### 4. Run the Pipeline
```bash
python scripts/run_pipeline.py
```

---

## 📁 Project Structure

```
staresina2015-sleep-oscillations-repro/
├── src/                     # Source code
│   ├── __init__.py
│   ├── io.py               # Data loading functions
│   ├── preprocess.py       # Signal preprocessing
│   ├── detect_events.py    # SO/spindle/ripple detection
│   ├── tfr.py              # Time-frequency analysis
│   ├── pac.py              # Phase-amplitude coupling
│   ├── stats.py            # Statistical testing
│   ├── plots.py            # Visualization functions
│   └── pipeline.py         # Main orchestration
├── configs/
│   └── analysis.yaml       # Analysis parameters
├── scripts/
│   └── run_pipeline.py     # Convenience script
├── tests/
│   └── test_detect_events.py  # Unit tests
├── .github/workflows/
│   └── ci.yml              # CI/CD configuration
├── requirements.txt
└── README.md
```

---

## 🧠 Understanding the Neuroscience

### Terminology for Data Engineers

| Neuroscience Term | Data Engineering Analogy |
|-------------------|-------------------------|
| **EEG Signal** | Time-series sensor data (like accelerometer) |
| **Sampling Rate (sfreq)** | Data points per second (e.g., 1000 Hz = 1000 samples/sec) |
| **Frequency Band** | Filtering data to specific frequency ranges |
| **Slow Oscillation (SO)** | Low-frequency pattern (~1 Hz, like heartbeat) |
| **Spindle** | Mid-frequency burst (9-16 Hz, like vibration) |
| **Ripple** | High-frequency spike (80-100 Hz, like noise burst) |
| **Phase** | Position in a wave cycle (0-360°) |
| **Amplitude** | Signal strength/magnitude |
| **Phase-Amplitude Coupling** | Correlation between phase of slow wave and amplitude of fast wave |

### Signal Processing Pipeline

1. **Data Loading** (`io.py`)
   - Read EEG files (various formats: EDF, BrainVision, etc.)
   - Similar to reading CSV/Parquet time-series data

2. **Preprocessing** (`preprocess.py`)
   - **Filtering**: Remove unwanted frequencies (like removing noise)
   - **Artifact rejection**: Remove bad data segments
   - **NREM extraction**: Select sleep stage 2 and 3 periods

3. **Event Detection** (`detect_events.py`)
   - **SO Detection**: Find slow waves using bandpass filter (0.5-1.25 Hz) + threshold
   - **Spindle Detection**: Find bursts in 9-16 Hz range lasting 0.5-3s
   - **Ripple Detection**: Find high-freq events (80-100 Hz) lasting 40-200ms

4. **Time-Frequency Analysis** (`tfr.py`)
   - **Wavelet Transform**: Like Fourier transform but preserves time info
   - Shows how frequency content changes over time

5. **Phase-Amplitude Coupling** (`pac.py`)
   - **Modulation Index**: Measures if fast oscillations sync with slow wave phase
   - High MI = strong coupling (ripples occur at specific spindle phases)

6. **Statistics** (`stats.py`)
   - **Permutation testing**: Non-parametric significance testing
   - **Cluster correction**: Control for multiple comparisons

---

## 🔧 Configuration

Edit `configs/analysis.yaml` to customize:

```yaml
detection:
  slow_oscillations:
    freq_range: [0.5, 1.25]  # Frequency band in Hz
    duration_range: [0.8, 2.0]  # Min/max duration in seconds
    amplitude_threshold: 1.25  # Threshold in std deviations
  
  spindles:
    freq_range: [9, 16]
    duration_range: [0.5, 3.0]
    threshold: 1.5
  
  ripples:
    freq_range: [80, 100]
    duration_range: [0.04, 0.2]
    threshold: 3.0
```

---

## 🧪 Testing

Run tests to verify installation:
```bash
pytest tests/ -v
```

Tests use synthetic signals to verify:
- Frequency-specific detection
- Duration constraints
- Threshold behavior
- False positive rates

---

## 📈 Output

The pipeline generates:

1. **Event Files** (`results/{subject_id}/`)
   - `so_events.npy`: Detected slow oscillations
   - `spindle_events.npy`: Detected spindles  
   - `ripple_events.npy`: Detected ripples

2. **Figures** (`results/`)
   - `group_event_counts.png`: Event counts across subjects
   - `group_comodulogram.png`: Phase-amplitude coupling matrix
   - `spindle_locked_tfr.png`: Time-frequency power around spindles

3. **Logs** (`results/pipeline.log`)
   - Processing logs for debugging

---

## 📚 Learning Resources

### For Understanding the Paper
1. **Sleep Stages**: [Sleep Foundation - Stages of Sleep](https://www.sleepfoundation.org/stages-of-sleep)
2. **EEG Basics**: Search "Introduction to EEG" on YouTube
3. **Signal Processing**: "The Scientist and Engineer's Guide to Digital Signal Processing" (free online)

### For Understanding the Code
1. **MNE-Python Tutorial**: [Official MNE Tutorials](https://mne.tools/stable/auto_tutorials/index.html)
2. **Scipy Signal Processing**: [Scipy Signal Docs](https://docs.scipy.org/doc/scipy/reference/signal.html)
3. **Wavelet Analysis**: "A Practical Guide to Wavelet Analysis" (Torrence & Compo, 1998)

---

## 📝 Step-by-Step Principles

### How Does Event Detection Work?

**Example: Spindle Detection**

1. **Filter the signal** to 9-16 Hz (keeps only spindle frequencies)
2. **Compute the envelope** (Hilbert transform - like finding the "outline" of the signal)
3. **Threshold the envelope** (events = when envelope > mean + 1.5*std)
4. **Check duration** (keep only events lasting 0.5-3 seconds)
5. **Extract event properties** (start time, end time, peak frequency, amplitude)

**In Code** (`detect_events.py`):
```python
def detect_spindles(data, sfreq, freq_sp=(9, 16), duration_sp=(0.5, 3.0), threshold=1.5):
    # 1. Bandpass filter
    filtered = apply_filter(data, sfreq, freq_sp[0], freq_sp[1])
    
    # 2. Hilbert transform for envelope
    analytic = hilbert(filtered)
    envelope = np.abs(analytic)
    
    # 3. Threshold
    mean_env = np.mean(envelope)
    std_env = np.std(envelope)
    thresh = mean_env + threshold * std_env
    
    # 4. Find events above threshold
    above_thresh = envelope > thresh
    events = find_continuous_segments(above_thresh)
    
    # 5. Filter by duration
    events = [e for e in events if duration_sp[0] < e['duration'] < duration_sp[1]]
    
    return events
```

---

## 🤝 Contributing

Contributions welcome! Areas for improvement:
- [ ] Add more sophisticated ripple detection (e.g., wavelet-based)
- [ ] Implement additional coupling metrics
- [ ] Add interactive visualization dashboard
- [ ] Support more data formats
- [ ] Optimize performance with parallel processing

---

## 📄 Citation

If you use this code, please cite the original paper:

```bibtex
@article{staresina2015hierarchical,
  title={Hierarchical nesting of slow oscillations, spindles and ripples in the human hippocampus during sleep},
  author={Staresina, Bernhard P and Bergmann, Til Ole and Bonnefond, Mathilde and van der Meij, Roemer and Jensen, Ole and Demarchi, Gianpaolo and Hermans, Erno J and Axmacher, Nikolai and Fell, Juergen},
  journal={Nature neuroscience},
  volume={18},
  number={11},
  pages={1679--1686},
  year={2015},
  publisher={Nature Publishing Group}
}
```

---

## 💬 Questions?

For questions about:
- **The code/implementation**: Open a GitHub issue
- **The neuroscience concepts**: See Learning Resources above
- **The original paper**: Contact the original authors

---

## 📝 License

MIT License - see [LICENSE](LICENSE) file

---

## 🚀 Next Steps for Learning

1. **Run the pipeline** on the example data
2. **Explore the outputs** - look at detected events and figures
3. **Modify parameters** in `configs/analysis.yaml` and see how results change
4. **Read the code** starting from `pipeline.py` and following the imports
5. **Add visualizations** - plot raw signals with detected events overlaid
6. **Experiment** - try detecting events in different frequency bands

Remember: The goal is to understand the principles of hierarchical brain oscillations, not to memorize neuroscience jargon. Think of it as analyzing multi-scale patterns in time-series data!

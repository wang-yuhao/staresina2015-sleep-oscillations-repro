"""
preprocess.py - Signal Preprocessing
=======================================
PRINCIPLE:
  Raw iEEG signals contain noise from several sources:
  1. LINE NOISE (50 Hz in Europe): Electrical interference from power lines.
     Removed with a notch filter at 50 Hz and its harmonics (100, 150 Hz).
  2. ARTIFACTS: Movement, electrode pop, seizure activity.
     Detected using z-score thresholding on amplitude, signal gradient,
     and high-frequency power (all three criteria from Staresina 2015 Methods).

  WHY BANDPASS?
  Each oscillation type lives in a specific frequency band:
    - Slow oscillations: 0.5-1.25 Hz
    - Spindles: 12-16 Hz
    - Ripples: 80-100 Hz
  Bandpass filtering isolates each band for event detection.

  WHY Z-SCORE FOR ARTIFACTS?
  Z-score = (value - mean) / std. Values with |z| > 4 are statistical
  outliers that likely represent non-physiological artifacts.
"""

import numpy as np
from scipy.signal import butter, sosfiltfilt, iirnotch, filtfilt


def bandpass(signal: np.ndarray, fs: int, lo: float, hi: float,
             order: int = 4) -> np.ndarray:
    """
    Zero-phase Butterworth bandpass filter.

    PRINCIPLE:
      Butterworth filters have maximally flat frequency response in the
      passband (no ripples). Zero-phase (sosfiltfilt) applies the filter
      forwards then backwards, eliminating phase distortion - critical
      for accurate event timing.

    Parameters
    ----------
    signal : np.ndarray (n_samples,)
    fs : int, sampling rate in Hz
    lo : float, lower cutoff frequency in Hz
    hi : float, upper cutoff frequency in Hz
    order : int, filter order (4 = good balance of sharpness vs stability)

    Returns
    -------
    np.ndarray, bandpass-filtered signal
    """
    nyq = fs / 2.0
    assert lo < hi < nyq, (
        f"Frequencies must satisfy lo < hi < nyq. Got lo={lo}, hi={hi}, nyq={nyq}.\n"
        f"Hint: for ripples (80-100 Hz) you need fs >= 201 Hz (use 1000 Hz)."
    )
    sos = butter(order, [lo / nyq, hi / nyq], btype='band', output='sos')
    return sosfiltfilt(sos, signal)


def notch_filter(signal: np.ndarray, fs: int,
                 freq: float = 50.0, q: float = 30.0) -> np.ndarray:
    """
    Remove line noise at freq Hz and its first two harmonics.

    PRINCIPLE:
      In Europe, power line frequency is 50 Hz. This creates a sharp
      spike at 50, 100, 150 Hz in any EEG recording. A notch filter
      creates a very narrow stop-band at exactly that frequency,
      leaving all other frequencies untouched.

      Q factor = center_freq / bandwidth. Q=30 means 50 Hz notch is
      ~1.67 Hz wide - narrow enough to not disturb spindle or ripple bands.

    Parameters
    ----------
    signal : np.ndarray
    fs : int
    freq : float, fundamental line noise frequency (50 Hz for Europe)
    q : float, quality factor (higher = narrower notch)

    Returns
    -------
    np.ndarray, notch-filtered signal
    """
    nyq = fs / 2.0
    for harmonic in [1, 2, 3]:
        f = freq * harmonic
        if f >= nyq:
            break
        b, a = iirnotch(f / nyq, q)
        signal = filtfilt(b, a, signal)
    return signal


def compute_artifact_mask(signal: np.ndarray, fs: int,
                          z_amp: float = 4.0,
                          z_grad: float = 4.0,
                          z_hf: float = 4.0,
                          hf_lo: float = 250.0,
                          hf_hi: float = 450.0,
                          pad_s: float = 0.5) -> np.ndarray:
    """
    Detect artifact-contaminated samples using 3-criterion z-score method.
    Based on Staresina et al. 2015, Methods section.

    PRINCIPLE:
      Three signals are z-scored. Any sample where ANY criterion exceeds
      the threshold is marked as artifact. A padding of pad_s seconds is
      added around each artifact to catch transition edges.

      CRITERION 1 - Amplitude: Very large voltage swings (electrode pops,
        movement artifacts). Z-score of raw amplitude.

      CRITERION 2 - Gradient: Very fast voltage changes (sharp transients,
        electrode noise). Z-score of the first derivative.

      CRITERION 3 - High-frequency power: Sustained high-frequency activity
        above 250 Hz indicates muscle artifact or electrical noise.
        Only applicable if fs > 500 Hz.

    Parameters
    ----------
    signal : np.ndarray
    fs : int
    z_amp, z_grad, z_hf : float, z-score thresholds for each criterion
    hf_lo, hf_hi : float, frequency range for high-frequency criterion
    pad_s : float, seconds to pad around detected artifacts

    Returns
    -------
    np.ndarray of bool, True = clean sample
    """
    n = len(signal)
    artifact = np.zeros(n, dtype=bool)

    # Criterion 1: amplitude z-score
    z1 = np.abs((signal - np.mean(signal)) / (np.std(signal) + 1e-10))
    artifact |= (z1 > z_amp)

    # Criterion 2: gradient z-score
    grad = np.diff(signal, prepend=signal[0])
    z2 = np.abs((grad - np.mean(grad)) / (np.std(grad) + 1e-10))
    artifact |= (z2 > z_grad)

    # Criterion 3: high-frequency power (only if fs allows)
    nyq = fs / 2.0
    if hf_hi < nyq and fs >= 500:
        hf = bandpass(signal, fs, hf_lo, min(hf_hi, nyq - 1))
        hf_env = np.abs(hf)
        z3 = np.abs((hf_env - np.mean(hf_env)) / (np.std(hf_env) + 1e-10))
        artifact |= (z3 > z_hf)

    # Pad around artifacts
    pad = int(pad_s * fs)
    if pad > 0:
        from scipy.ndimage import binary_dilation
        artifact = binary_dilation(artifact, iterations=pad)

    return ~artifact  # Return True where sample is CLEAN


def apply_mask(signal: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """
    Zero-out artifact/non-NREM samples.
    The signal length is preserved so sample indices remain valid.
    Zeroed regions are skipped during event detection.
    """
    out = signal.copy()
    out[~mask] = 0.0
    return out


def preprocess(signal: np.ndarray, fs: int, 
               bandpass_range: tuple = (0.5, 100),
               notch_freq: int = 50) -> np.ndarray:
    """
    Complete preprocessing pipeline for iEEG data.
    
    Applies bandpass filtering and notch filtering to remove line noise.
    
    Parameters
    ----------
    signal : np.ndarray
        Raw iEEG signal
    fs : int
        Sampling rate in Hz
    bandpass_range : tuple
        (low_freq, high_freq) for bandpass filter
    notch_freq : int
        Frequency to notch filter (e.g., 50 or 60 Hz)
    
    Returns
    -------
    np.ndarray
        Preprocessed signal
    """
    # Apply bandpass filter
    signal_bp = bandpass(signal, fs, bandpass_range[0], bandpass_range[1])
    
    # Apply notch filter to remove line noise
    signal_clean = notch_filter(signal_bp, fs, notch_freq)
    
    return signal_clean


def extract_nrem_epochs(signal: np.ndarray, fs: int,
                        sleep_stages: np.ndarray = None) -> np.ndarray:
    """
    Extract NREM sleep epochs from continuous recording.
    
    For this simplified implementation, if sleep staging is not available,
    we return the full signal. In a complete implementation, this would
    filter for N2/N3 sleep stages only.
    
    Parameters
    ----------
    signal : np.ndarray
        Preprocessed iEEG signal
    fs : int  
        Sampling rate in Hz
    sleep_stages : np.ndarray, optional
        Sleep stage annotations (if available)
    
    Returns
    -------
    np.ndarray
        Signal segments during NREM sleep
    """
    if sleep_stages is None:
        # No sleep staging available - return full signal
        # In practice, you would manually annotate or use automated staging
        return signal
    
    # Extract N2/N3 epochs (stages 2 and 3)
    nrem_mask = np.isin(sleep_stages, [2, 3])
    nrem_signal = signal[nrem_mask]
    
    return nrem_signal

"""
detect_events.py - Slow Oscillation, Spindle, and Ripple Detection
====================================================================
PRINCIPLE - HOW EACH OSCILLATION IS DETECTED:

  SLOW OSCILLATIONS (SOs, ~0.75 Hz):
    1. Bandpass filter signal at 0.5-1.25 Hz
    2. Find all negative half-waves (troughs) via zero-crossing detection
    3. Keep troughs where amplitude > percentile threshold (top 25%)
    4. Keep troughs where half-wave duration is within physiological range
       (0.8-2.0 s for a full SO cycle, i.e. 0.4-1.0 s for a half-wave)
    Reference: Molle et al. 2002; Staresina et al. 2015 Methods

  SLEEP SPINDLES (~14 Hz):
    1. Bandpass filter at 12-16 Hz (fast spindles, hippocampal type)
    2. Compute RMS (root mean square) envelope in a 200ms sliding window
    3. Z-score the envelope across the whole recording
    4. Detect threshold crossings (z > threshold, default 2.0)
    5. Keep events within duration range (0.5-3.0 s)
    Reference: Staresina et al. 2015; Helfrich et al. 2018

  HIPPOCAMPAL RIPPLES (~90 Hz):
    1. Bandpass filter at 80-100 Hz
    2. Compute instantaneous amplitude via Hilbert transform
    3. Threshold at 99th percentile of amplitude distribution (top 1%)
    4. Keep events within duration range (0.02-0.2 s = 20-200 ms)
    IMPORTANT: fs must be >= 200 Hz (use 1000 Hz for ripple detection)
    Reference: Staresina et al. 2015; Axmacher et al. 2008
"""

import numpy as np
import pandas as pd
from scipy.signal import hilbert
from .preprocess import bandpass


def _rms_envelope(signal: np.ndarray, fs: int, window_s: float = 0.2) -> np.ndarray:
    """Compute RMS in a sliding window. Equivalent to smoothed power."""
    win = max(1, int(window_s * fs))
    # Pad signal
    pad = win // 2
    padded = np.pad(signal ** 2, pad, mode='edge')
    # Cumulative sum trick for fast sliding window
    cs = np.cumsum(padded)
    rms = np.sqrt((cs[win:] - cs[:-win]) / win)
    return rms[:len(signal)]


def detect_slow_oscillations(
        signal: np.ndarray,
        fs: int,
        lo: float = 0.5,
        hi: float = 1.25,
        amp_pct: float = 75.0,
        min_dur: float = 0.8,
        max_dur: float = 2.0,
        clean_mask: np.ndarray = None) -> pd.DataFrame:
    """
    Detect slow oscillations via negative half-wave criterion.

    ALGORITHM (mirrors Staresina 2015 / Molle 2002):
      - Filter 0.5-1.25 Hz
      - Find zero crossings (negative-to-positive = end of negative half-wave)
      - For each half-wave: measure trough amplitude and duration
      - Keep half-waves where:
          (a) trough amplitude > amp_pct percentile of all troughs
          (b) half-wave duration within [min_dur/2, max_dur/2] seconds

    Returns
    -------
    pd.DataFrame with columns:
        down_sample   : sample index of the trough (most negative point)
        down_s        : time in seconds of trough
        start_sample  : sample index where negative half-wave starts
        end_sample    : sample index where negative half-wave ends
        duration_s    : full SO duration estimate (2x half-wave)
        trough_amp    : trough amplitude (negative value, in microvolts)
        trough_abs    : absolute trough amplitude
    """
    assert fs >= 10, "Sampling rate too low for SO detection"
    filt = bandpass(signal, fs, lo, hi)

    # Zero crossings: find where signal changes sign
    signs = np.sign(filt)
    signs[signs == 0] = 1
    zc = np.where(np.diff(signs))[0]  # indices just before crossing

    events = []
    for i in range(len(zc) - 1):
        start = zc[i]
        end = zc[i + 1]
        segment = filt[start:end]
        if len(segment) == 0:
            continue
        # Only keep negative half-waves (trough must be negative)
        trough_val = segment.min()
        if trough_val >= 0:
            continue
        trough_idx = start + segment.argmin()
        duration = (end - start) / fs
        # Half-wave duration check
        if not (min_dur / 2 <= duration <= max_dur / 2):
            continue
        # Artifact check
        if clean_mask is not None:
            if not np.all(clean_mask[start:end]):
                continue
        events.append({
            'down_sample': trough_idx,
            'down_s': trough_idx / fs,
            'start_sample': start,
            'end_sample': end,
            'duration_s': duration * 2,
            'trough_amp': trough_val,
            'trough_abs': abs(trough_val),
        })

    if not events:
        return pd.DataFrame(columns=['down_sample', 'down_s', 'start_sample',
                                      'end_sample', 'duration_s', 'trough_amp',
                                      'trough_abs'])

    df = pd.DataFrame(events)
    # Amplitude threshold: keep top (100 - amp_pct)% most negative troughs
    thresh = np.percentile(df['trough_abs'], amp_pct)
    df = df[df['trough_abs'] >= thresh].reset_index(drop=True)
    return df


def detect_spindles(
        signal: np.ndarray,
        fs: int,
        lo: float = 12.0,
        hi: float = 16.0,
        z_thresh: float = 2.0,
        min_dur: float = 0.5,
        max_dur: float = 3.0,
        clean_mask: np.ndarray = None) -> pd.DataFrame:
    """
    Detect sleep spindles via RMS envelope z-score thresholding.

    ALGORITHM:
      1. Bandpass filter 12-16 Hz
      2. Compute RMS envelope (200ms window)
      3. Z-score the envelope: z = (env - mean(env)) / std(env)
      4. Find contiguous segments where z > z_thresh
      5. Keep segments within duration range
      6. For each spindle: record center, peak envelope amplitude

    WHY RMS AND NOT HILBERT?
      RMS in a sliding window is more robust to brief noise spikes than
      Hilbert amplitude for spindle detection. Both are used in literature;
      RMS matches the Staresina 2015 approach.

    Returns
    -------
    pd.DataFrame with columns:
        center_sample  : sample index of peak RMS
        center_s       : time in seconds of peak
        start_sample   : sample index of spindle onset
        end_sample     : sample index of spindle offset
        duration_s     : spindle duration in seconds
        peak_env       : peak RMS amplitude
        mean_env       : mean RMS amplitude during spindle
    """
    assert fs >= 30, "Sampling rate too low for spindle detection"
    filt = bandpass(signal, fs, lo, hi)
    env = _rms_envelope(filt, fs, window_s=0.2)

    # Z-score envelope
    env_z = (env - np.mean(env)) / (np.std(env) + 1e-10)

    # Find threshold crossings
    above = env_z > z_thresh
    if clean_mask is not None:
        above &= clean_mask[:len(above)]

    # Find contiguous ON segments
    diff = np.diff(above.astype(int), prepend=0, append=0)
    starts = np.where(diff == 1)[0]
    ends = np.where(diff == -1)[0]

    events = []
    for s, e in zip(starts, ends):
        duration = (e - s) / fs
        if not (min_dur <= duration <= max_dur):
            continue
        seg = env[s:e]
        peak_idx = s + seg.argmax()
        events.append({
            'center_sample': int(peak_idx),
            'center_s': peak_idx / fs,
            'start_sample': int(s),
            'end_sample': int(e),
            'duration_s': duration,
            'peak_env': float(env[peak_idx]),
            'mean_env': float(seg.mean()),
        })

    return pd.DataFrame(events) if events else pd.DataFrame(
        columns=['center_sample', 'center_s', 'start_sample',
                 'end_sample', 'duration_s', 'peak_env', 'mean_env'])


def detect_ripples(
        signal: np.ndarray,
        fs: int,
        lo: float = 80.0,
        hi: float = 100.0,
        z_thresh: float = None,
        pct_thresh: float = 99.0,
        min_dur: float = 0.02,
        max_dur: float = 0.2,
        clean_mask: np.ndarray = None) -> pd.DataFrame:
    """
    Detect hippocampal ripples via Hilbert amplitude thresholding.

    ALGORITHM (Staresina et al. 2015, Methods):
      1. Bandpass filter 80-100 Hz
      2. Compute instantaneous amplitude via Hilbert transform:
         amplitude(t) = |analytic_signal(t)| = sqrt(real^2 + imag^2)
      3. Threshold at 99th percentile of amplitude across all clean NREM
      4. Keep events within duration range (20-200 ms)

    WHY HILBERT FOR RIPPLES (not RMS)?
      Ripples are brief (~50-100 ms). The Hilbert transform gives
      instantaneous amplitude at sample precision, while RMS requires
      a window that would blur the onset/offset of such short events.

    WHY TOP 1% THRESHOLD?
      Ripples are rare events. Using the 99th percentile ensures we only
      detect the strongest bursts that represent true hippocampal replay,
      not background noise in the 80-100 Hz band.

    IMPORTANT: Requires fs >= 200 Hz. For 1000 Hz data (Ngo 2020 dataset)
    this is well-satisfied.

    Returns
    -------
    pd.DataFrame with columns:
        center_sample  : sample of peak amplitude
        center_s       : time in seconds
        start_sample   : onset sample
        end_sample     : offset sample
        duration_s     : duration in seconds
        peak_amp       : peak Hilbert amplitude
        mean_amp       : mean amplitude during ripple
    """
    assert fs >= 200, (
        f"fs={fs} Hz is too low for ripple detection (need >= 200 Hz).\n"
        f"Ripples are 80-100 Hz bursts. At 200 Hz you have only 2 samples per cycle.\n"
        f"Use the Ngo 2020 dataset (1000 Hz) for proper ripple detection."
    )
    nyq = fs / 2.0
    hi_safe = min(hi, nyq - 5.0)
    assert lo < hi_safe, f"lo={lo} >= hi_safe={hi_safe}. Adjust ripple band."

    filt = bandpass(signal, fs, lo, hi_safe)
    analytic = hilbert(filt)
    amp = np.abs(analytic)

    # Threshold
    if clean_mask is not None:
        clean_amp = amp[clean_mask[:len(amp)]]
    else:
        clean_amp = amp
    if z_thresh is not None:
        threshold = np.mean(clean_amp) + z_thresh * np.std(clean_amp)
    else:
        threshold = np.percentile(clean_amp, pct_thresh)

    above = amp > threshold
    if clean_mask is not None:
        above &= clean_mask[:len(above)]

    diff = np.diff(above.astype(int), prepend=0, append=0)
    starts = np.where(diff == 1)[0]
    ends = np.where(diff == -1)[0]

    events = []
    for s, e in zip(starts, ends):
        duration = (e - s) / fs
        if not (min_dur <= duration <= max_dur):
            continue
        seg = amp[s:e]
        peak_idx = s + seg.argmax()
        events.append({
            'center_sample': int(peak_idx),
            'center_s': peak_idx / fs,
            'start_sample': int(s),
            'end_sample': int(e),
            'duration_s': duration,
            'peak_amp': float(amp[peak_idx]),
            'mean_amp': float(seg.mean()),
        })

    return pd.DataFrame(events) if events else pd.DataFrame(
        columns=['center_sample', 'center_s', 'start_sample',
                 'end_sample', 'duration_s', 'peak_amp', 'mean_amp'])

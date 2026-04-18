"""
tfr.py - Time-Frequency Representation (TFR)
=============================================
PRINCIPLE:
  A TFR shows how the POWER at each frequency changes over time.
  Think of it like a Grafana dashboard where the x-axis is time and
  y-axis is frequency, and color = power intensity.

  This module computes EVENT-LOCKED TFR:
    1. For each detected event (e.g., each SO trough), extract a time
       window of the signal centered on the event (e.g., -2s to +2s)
    2. Compute the power spectrogram for that window
    3. Average all windows together -> reveals what reliably happens
       around the event across the whole night

  WHY MORLET WAVELETS?
    Morlet wavelets are a common choice for neural oscillation analysis.
    They give good time-frequency resolution by convolving the signal with
    a sine wave tapered by a Gaussian window.
    The width parameter (n_cycles) controls the time-frequency trade-off:
    - More cycles = better frequency resolution, worse time resolution
    - Fewer cycles = better time resolution, worse frequency resolution
    For low frequencies (1-4 Hz): use 3-5 cycles
    For high frequencies (50-100 Hz): use 7-10 cycles

  WHY BASELINE NORMALIZATION?
    Absolute power varies between subjects, sessions, and frequencies.
    We normalize by dividing by the mean power in a baseline window
    (typically -1.5 to -0.5 s before the event) and expressing as
    percent change or dB. This reveals changes RELATIVE to background.
"""

import numpy as np
from scipy.signal import morlet2


def morlet_power(signal: np.ndarray, fs: int,
                 freqs: np.ndarray,
                 n_cycles: float = 7.0) -> np.ndarray:
    """
    Compute Morlet wavelet power spectrum.

    PRINCIPLE:
      For each frequency f, convolve the signal with a Morlet wavelet
      scaled to that frequency. The squared absolute value of the
      convolution output is the instantaneous power at frequency f.

    Parameters
    ----------
    signal : np.ndarray (n_samples,)
    fs : int
    freqs : np.ndarray, frequencies to compute power at (Hz)
    n_cycles : float, number of wavelet cycles (higher = better freq resolution)

    Returns
    -------
    np.ndarray (n_freqs, n_samples) - power at each frequency and time
    """
    n = len(signal)
    power = np.zeros((len(freqs), n))
    for i, f in enumerate(freqs):
        # Wavelet scale: width = n_cycles / (2 * pi * f)
        w = n_cycles
        # scipy morlet2: morlet2(M, w, s) where M=len, w=cycles, s=scale
        scale = w * fs / (2 * np.pi * f)
        M = min(int(10 * scale), n)  # wavelet length
        if M % 2 == 0:
            M += 1
        wav = morlet2(M, w=w, s=scale)
        # Convolve
        from scipy.signal import fftconvolve
        conv = fftconvolve(signal, wav, mode='same')
        power[i] = np.abs(conv) ** 2
    return power


def compute_event_locked_tfr(
        signal: np.ndarray,
        fs: int,
        event_samples: np.ndarray,
        tmin: float = -2.0,
        tmax: float = 2.0,
        freqs: np.ndarray = None,
        n_cycles: float = 7.0,
        baseline: tuple = (-1.5, -0.5)) -> dict:
    """
    Compute event-locked TFR: extract windows around events, average power.

    PRINCIPLE:
      This directly reproduces Figures 2-4 in Staresina 2015.
      For each event (SO trough, spindle peak, ripple peak):
        - Extract a [-tmin, tmax] second window
        - Compute Morlet power spectrogram
      Then average all windows: result shows what SYSTEMATICALLY happens
      around events (e.g., spindle power increases during SO up-state).

      Baseline normalization:
        norm_power(f,t) = (power(f,t) - mean_baseline(f)) / mean_baseline(f) * 100
      This gives percent change from baseline, making results comparable
      across subjects and frequencies.

    Parameters
    ----------
    signal : np.ndarray (n_samples,)
    fs : int
    event_samples : np.ndarray, sample indices of events
    tmin, tmax : float, window limits in seconds
    freqs : np.ndarray, frequencies (default: 1-120 Hz log-spaced)
    n_cycles : float
    baseline : tuple (start_s, end_s), baseline window relative to event

    Returns
    -------
    dict with keys:
        'avg_power'  : np.ndarray (n_freqs, n_times), baseline-normalized
        'times'      : np.ndarray (n_times,), time axis in seconds
        'freqs'      : np.ndarray (n_freqs,)
        'n_events'   : int, number of events used
        'all_power'  : np.ndarray (n_events, n_freqs, n_times), per-event
    """
    if freqs is None:
        freqs = np.logspace(np.log10(1), np.log10(120), 60)

    n_pre = int(abs(tmin) * fs)
    n_post = int(tmax * fs)
    n_win = n_pre + n_post
    times = np.linspace(tmin, tmax, n_win)

    # Baseline indices
    bl_start = int((baseline[0] - tmin) * fs)
    bl_end = int((baseline[1] - tmin) * fs)
    bl_start = max(0, bl_start)
    bl_end = min(n_win, bl_end)

    all_power = []
    for ev in event_samples:
        s = int(ev) - n_pre
        e = int(ev) + n_post
        if s < 0 or e > len(signal):
            continue
        win = signal[s:e]
        pw = morlet_power(win, fs, freqs, n_cycles=n_cycles)
        all_power.append(pw)

    if not all_power:
        return {'avg_power': np.zeros((len(freqs), n_win)),
                'times': times, 'freqs': freqs, 'n_events': 0,
                'all_power': np.zeros((0, len(freqs), n_win))}

    all_power = np.array(all_power)  # (n_events, n_freqs, n_times)
    avg = all_power.mean(axis=0)     # (n_freqs, n_times)

    # Baseline normalize: percent change from baseline
    baseline_mean = avg[:, bl_start:bl_end].mean(axis=1, keepdims=True)
    baseline_mean = np.where(baseline_mean == 0, 1e-10, baseline_mean)
    avg_norm = (avg - baseline_mean) / baseline_mean * 100

    return {
        'avg_power': avg_norm,
        'times': times,
        'freqs': freqs,
        'n_events': len(all_power),
        'all_power': all_power,
    }

"""
pac.py - Phase-Amplitude Coupling (PAC)
========================================
PRINCIPLE:
  PAC measures whether the AMPLITUDE of a fast oscillation is modulated
  by the PHASE of a slow oscillation.

  Example: Is spindle (14 Hz) amplitude highest at a specific phase
  of the slow oscillation (0.75 Hz)? If yes, there is PAC.

  DATA ENGINEERING ANALOGY:
    Phase = the position in a clock cycle (0 to 2*pi radians)
    Amplitude = the signal strength at each moment
    PAC asks: "Is signal strength predictable from clock position?"
    If amplitude is always highest at phase=pi (e.g. up-state of SO),
    then PAC is high. If amplitude is random relative to phase, PAC=0.

  MODULATION INDEX (Tort et al. 2010):
    1. Get phase of slow oscillation (via Hilbert transform)
    2. Get amplitude of fast oscillation (via Hilbert transform)
    3. Bin the amplitude by phase (e.g. 18 bins of 20 degrees each)
    4. Compute KL-divergence of amplitude distribution from uniform:
       MI = KL(amplitude_distribution || uniform) / log(N_bins)
    MI=0: amplitude is uniformly distributed across phases (no PAC)
    MI>0: amplitude is concentrated at certain phases (PAC present)

  WHY KL-DIVERGENCE?
    KL-divergence measures how much a distribution differs from
    a reference (here: uniform). If spindle amplitude peaks sharply
    at a specific SO phase, the amplitude-phase distribution deviates
    strongly from uniform -> high KL -> high MI.
    This is equivalent to the entropy of the distribution.
"""

import numpy as np
from scipy.signal import hilbert
from .preprocess import bandpass


def hilbert_phase(signal: np.ndarray) -> np.ndarray:
    """Instantaneous phase of signal via Hilbert transform (radians, -pi to pi)."""
    return np.angle(hilbert(signal))


def hilbert_amplitude(signal: np.ndarray) -> np.ndarray:
    """Instantaneous amplitude (envelope) via Hilbert transform."""
    return np.abs(hilbert(signal))


def compute_modulation_index(
        phase: np.ndarray,
        amplitude: np.ndarray,
        n_bins: int = 18) -> tuple:
    """
    Compute Modulation Index (MI) following Tort et al. 2010.

    ALGORITHM:
      1. Create n_bins phase bins spanning [-pi, pi]
      2. For each bin, compute mean amplitude of all samples in that bin
      3. Normalize mean amplitudes to sum to 1 (probability distribution)
      4. MI = KL(observed distribution, uniform distribution) / log(n_bins)
         where KL(p, q) = sum(p * log(p/q))
         and uniform distribution has q_i = 1/n_bins for all bins

    Parameters
    ----------
    phase : np.ndarray, instantaneous phase of slow oscillation (radians)
    amplitude : np.ndarray, instantaneous amplitude of fast oscillation
    n_bins : int, number of phase bins (18 bins = 20 degrees each)

    Returns
    -------
    tuple (MI, preferred_phase, amplitude_by_phase)
        MI : float, Modulation Index (0 = no coupling, >0 = coupling)
        preferred_phase : float, phase (radians) at peak amplitude
        amplitude_by_phase : np.ndarray (n_bins,), mean amplitude per bin
    """
    bins = np.linspace(-np.pi, np.pi, n_bins + 1)
    amp_by_phase = np.zeros(n_bins)

    for i in range(n_bins):
        idx = (phase >= bins[i]) & (phase < bins[i + 1])
        if idx.sum() > 0:
            amp_by_phase[i] = amplitude[idx].mean()
        else:
            amp_by_phase[i] = 0.0

    # Normalize to probability distribution
    total = amp_by_phase.sum()
    if total == 0:
        return 0.0, 0.0, amp_by_phase
    p = amp_by_phase / total

    # KL divergence from uniform distribution
    uniform = np.ones(n_bins) / n_bins
    # Avoid log(0)
    p_safe = np.where(p > 0, p, 1e-10)
    kl = np.sum(p_safe * np.log(p_safe / uniform))
    MI = kl / np.log(n_bins)

    # Preferred phase = bin center at maximum amplitude
    bin_centers = (bins[:-1] + bins[1:]) / 2
    preferred_phase = bin_centers[np.argmax(amp_by_phase)]

    return float(MI), float(preferred_phase), amp_by_phase


def compute_pac_comodulogram(
        signal: np.ndarray,
        fs: int,
        phase_freqs: np.ndarray = None,
        amp_freqs: np.ndarray = None,
        n_bins: int = 18,
        bandwidth: float = 2.0) -> dict:
    """
    Compute PAC comodulogram: MI for all phase-frequency x amplitude-frequency pairs.

    PRINCIPLE:
      This produces the comodulogram from Staresina 2015 Figure 5.
      X-axis: phase frequency (slow oscillation band)
      Y-axis: amplitude frequency (fast oscillation band)
      Color: Modulation Index value

      A bright spot at (x=0.75 Hz, y=14 Hz) means: spindle amplitude
      is coupled to the phase of slow oscillations. This is the key
      finding of the paper.

    Parameters
    ----------
    signal : np.ndarray
    fs : int
    phase_freqs : array of center frequencies for phase component
    amp_freqs : array of center frequencies for amplitude component
    n_bins : int, phase bins for MI calculation
    bandwidth : float, +/- Hz around each center frequency for bandpass

    Returns
    -------
    dict with keys:
        'MI_matrix'   : np.ndarray (n_phase_freqs, n_amp_freqs)
        'phase_freqs' : np.ndarray
        'amp_freqs'   : np.ndarray
    """
    if phase_freqs is None:
        phase_freqs = np.arange(0.5, 4.0, 0.5)
    if amp_freqs is None:
        amp_freqs = np.arange(4.0, 120.0, 4.0)

    nyq = fs / 2.0
    MI_matrix = np.zeros((len(phase_freqs), len(amp_freqs)))

    for i, pf in enumerate(phase_freqs):
        plo = max(0.1, pf - bandwidth)
        phi = min(nyq - 1, pf + bandwidth)
        try:
            xp = bandpass(signal, fs, plo, phi)
            phase = hilbert_phase(xp)
        except Exception:
            continue

        for j, af in enumerate(amp_freqs):
            alo = max(pf + bandwidth + 1, af - bandwidth)
            ahi = min(nyq - 1, af + bandwidth)
            if alo >= ahi:
                continue
            try:
                xa = bandpass(signal, fs, alo, ahi)
                amp = hilbert_amplitude(xa)
                MI, _, _ = compute_modulation_index(phase, amp, n_bins)
                MI_matrix[i, j] = MI
            except Exception:
                continue

    return {
        'MI_matrix': MI_matrix,
        'phase_freqs': phase_freqs,
        'amp_freqs': amp_freqs,
    }


def preferred_phase_subject(
        signal: np.ndarray,
        fs: int,
        phase_lo: float = 0.5,
        phase_hi: float = 1.25,
        amp_lo: float = 12.0,
        amp_hi: float = 16.0) -> tuple:
    """
    Get preferred phase (radians) and MI for a specific phase-amplitude pair.
    Used for statistical testing (V-test for preferred phase).

    Returns
    -------
    (MI, preferred_phase_rad, amplitude_by_phase)
    """
    xp = bandpass(signal, fs, phase_lo, phase_hi)
    xa = bandpass(signal, fs, amp_lo, amp_hi)
    phase = hilbert_phase(xp)
    amp = hilbert_amplitude(xa)
    return compute_modulation_index(phase, amp)

"""
plots.py - Reproduction Figures for Staresina et al. 2015
==========================================================
This module produces figures that match the main results of the paper:

  Figure 2: SO-locked TFR (spindle power increases at SO up-state)
  Figure 3: Spindle-locked TFR (ripple power increases at spindle trough)
  Figure 4: Ripple-locked TFR (spindle power increases around ripple)
  Figure 5: PAC comodulogram (MI heatmap showing SO-spindle coupling)
  Figure 6: Rose plot (preferred phase of spindle amplitude relative to SO)

EACH FIGURE EXPLAINED:
  TFR Heatmaps: x=time (seconds), y=frequency (Hz), color=power change (%)
    Warm colors (red) = power INCREASE relative to baseline
    Cool colors (blue) = power DECREASE
    The key result: at t=0 (event), specific frequency bands show red spots

  PAC Comodulogram: x=phase frequency, y=amplitude frequency, color=MI
    A bright spot at (0.75 Hz, 14 Hz) means: spindle (14 Hz) amplitude
    is modulated by the phase of slow oscillations (0.75 Hz)

  Rose Plot: circular histogram of preferred phases
    Each segment = fraction of subjects whose spindle amplitude peaks
    at that phase of the SO. Clustering at one direction = significant PAC
"""

import numpy as np
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend for server/pipeline use
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from pathlib import Path


def _save_or_show(fig, save_path=None):
    """Save to file if path given, else show interactively."""
    if save_path:
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(save_path, dpi=150, bbox_inches='tight')
        plt.close(fig)
        print(f"  Saved: {save_path}")
    else:
        plt.show()


def plot_so_locked_tfr(times, freqs, avg_power,
                       sig_mask=None,
                       title='SO-locked TFR (Reproducing Fig. 2)',
                       save_path=None):
    """
    Plot SO-locked time-frequency representation.

    WHAT TO EXPECT:
      Around t=0 (SO trough/down-state), you should see:
      - Decreased power at 12-16 Hz BEFORE t=0 (during down-state)
      - INCREASED power at 12-16 Hz AFTER t=0 (during up-state)
      This is the signature of spindles occurring during the SO up-state.

    Parameters
    ----------
    times : np.ndarray (n_times,)
    freqs : np.ndarray (n_freqs,)
    avg_power : np.ndarray (n_freqs, n_times), percent change from baseline
    sig_mask : np.ndarray (n_freqs, n_times) bool, optional significance mask
    """
    fig, ax = plt.subplots(figsize=(10, 5))

    # Symmetric color scale
    vmax = np.percentile(np.abs(avg_power), 98)
    vmin = -vmax

    im = ax.pcolormesh(times, freqs, avg_power,
                        cmap='RdBu_r', vmin=vmin, vmax=vmax,
                        shading='auto')

    # Overlay significance contour if provided
    if sig_mask is not None:
        ax.contour(times, freqs, sig_mask.astype(float),
                   levels=[0.5], colors='k', linewidths=1.5)

    ax.set_yscale('log')
    ax.set_yticks([1, 4, 12, 30, 80, 120])
    ax.set_yticklabels(['1', '4', '12', '30', '80', '120'])
    ax.set_xlabel('Time relative to SO trough (s)', fontsize=12)
    ax.set_ylabel('Frequency (Hz)', fontsize=12)
    ax.set_title(title, fontsize=13)
    ax.axvline(0, color='k', lw=1.5, ls='--', label='SO trough')
    ax.axhline(14, color='gray', lw=1, ls=':', alpha=0.7, label='14 Hz spindle')
    ax.legend(fontsize=9, loc='upper right')

    cbar = fig.colorbar(im, ax=ax)
    cbar.set_label('Power change (% from baseline)', fontsize=10)

    _save_or_show(fig, save_path)
    return fig


def plot_spindle_locked_tfr(times, freqs, avg_power,
                             sig_mask=None,
                             title='Spindle-locked TFR (Reproducing Fig. 3)',
                             save_path=None):
    """
    Plot spindle-locked TFR.

    WHAT TO EXPECT:
      Around t=0 (spindle peak), you should see:
      - Increased power at 80-100 Hz (ripple band) shortly AFTER t=0
      This shows that ripples are NESTED inside spindles.
    """
    fig, ax = plt.subplots(figsize=(10, 5))
    vmax = np.percentile(np.abs(avg_power), 98)
    im = ax.pcolormesh(times, freqs, avg_power,
                        cmap='RdBu_r', vmin=-vmax, vmax=vmax,
                        shading='auto')
    if sig_mask is not None:
        ax.contour(times, freqs, sig_mask.astype(float),
                   levels=[0.5], colors='k', linewidths=1.5)
    ax.set_yscale('log')
    ax.set_yticks([1, 4, 12, 30, 80, 120])
    ax.set_yticklabels(['1', '4', '12', '30', '80', '120'])
    ax.set_xlabel('Time relative to spindle peak (s)', fontsize=12)
    ax.set_ylabel('Frequency (Hz)', fontsize=12)
    ax.set_title(title, fontsize=13)
    ax.axvline(0, color='k', lw=1.5, ls='--', label='Spindle peak')
    ax.axhline(90, color='orange', lw=1, ls=':', alpha=0.7, label='90 Hz ripple')
    ax.legend(fontsize=9)
    cbar = fig.colorbar(im, ax=ax)
    cbar.set_label('Power change (% from baseline)', fontsize=10)
    _save_or_show(fig, save_path)
    return fig


def plot_pac_comodulogram(phase_freqs, amp_freqs, MI_matrix,
                          title='PAC Comodulogram (Reproducing Fig. 5)',
                          save_path=None):
    """
    Plot PAC comodulogram.

    WHAT TO EXPECT:
      A bright spot at approximately:
        phase frequency ~0.75-1.0 Hz (SO band)
        amplitude frequency ~12-16 Hz (spindle band)
      AND possibly at:
        phase frequency ~12-16 Hz (spindle band)
        amplitude frequency ~80-100 Hz (ripple band)
      These two spots represent SO->spindle and spindle->ripple coupling.
    """
    fig, ax = plt.subplots(figsize=(8, 6))
    im = ax.pcolormesh(phase_freqs, amp_freqs, MI_matrix.T,
                        cmap='hot', shading='auto')
    ax.set_xlabel('Phase frequency (Hz)', fontsize=12)
    ax.set_ylabel('Amplitude frequency (Hz)', fontsize=12)
    ax.set_title(title, fontsize=13)

    # Annotate key coupling regions
    ax.axvline(1.0, color='cyan', lw=1, ls='--', alpha=0.7,
                label='SO phase (1 Hz)')
    ax.axhline(14, color='lime', lw=1, ls='--', alpha=0.7,
                label='Spindle amp (14 Hz)')
    ax.legend(fontsize=9)

    cbar = fig.colorbar(im, ax=ax)
    cbar.set_label('Modulation Index (MI)', fontsize=10)
    _save_or_show(fig, save_path)
    return fig


def plot_preferred_phase_rose(preferred_phases,
                              title='Preferred Phase of Spindle Amplitude (Reproducing Fig. 5)',
                              expected_direction=0.0,
                              save_path=None):
    """
    Circular histogram (rose plot) of preferred phases across subjects.

    WHAT TO EXPECT:
      The histogram should be concentrated (not uniform) at around 0 rad
      (the SO up-state peak), showing that spindle amplitude consistently
      peaks at the SO up-state across all subjects.
    """
    fig = plt.figure(figsize=(6, 6))
    ax = fig.add_subplot(111, projection='polar')

    n_bins = 18
    bins = np.linspace(-np.pi, np.pi, n_bins + 1)
    counts, _ = np.histogram(preferred_phases, bins=bins)
    bin_centers = (bins[:-1] + bins[1:]) / 2
    width = 2 * np.pi / n_bins

    ax.bar(bin_centers, counts, width=width, alpha=0.7,
           color='steelblue', edgecolor='white')

    # Mark expected direction
    ax.axvline(expected_direction, color='red', lw=2,
                label=f'Expected: {np.degrees(expected_direction):.0f} deg')

    # Mark mean direction
    C = np.mean(np.cos(preferred_phases))
    S = np.mean(np.sin(preferred_phases))
    mean_dir = np.arctan2(S, C)
    ax.axvline(mean_dir, color='orange', lw=2, ls='--',
                label=f'Observed mean: {np.degrees(mean_dir):.0f} deg')

    ax.set_title(title, pad=20, fontsize=11)
    ax.legend(loc='lower right', fontsize=8)
    ax.set_theta_zero_location('N')

    _save_or_show(fig, save_path)
    return fig


def plot_event_counts(so_counts, spindle_counts, ripple_counts,
                      subject_ids=None, save_path=None):
    """
    Bar chart of detected event counts per subject.
    Useful quality-control figure to verify event detection worked.
    """
    n = len(so_counts)
    x = np.arange(n)
    if subject_ids is None:
        subject_ids = [f'S{i+1}' for i in range(n)]

    fig, axes = plt.subplots(1, 3, figsize=(14, 4))
    for ax, counts, label, color in zip(
            axes,
            [so_counts, spindle_counts, ripple_counts],
            ['Slow Oscillations', 'Spindles', 'Ripples'],
            ['royalblue', 'darkorange', 'crimson']):
        ax.bar(x, counts, color=color, alpha=0.8)
        ax.set_xticks(x)
        ax.set_xticklabels(subject_ids, rotation=45, fontsize=8)
        ax.set_ylabel('Event count')
        ax.set_title(label)
        ax.axhline(np.mean(counts), color='k', ls='--',
                    label=f'Mean={np.mean(counts):.0f}')
        ax.legend(fontsize=8)

    fig.suptitle('Detected Events per Subject (Quality Control)', fontsize=13)
    plt.tight_layout()
    _save_or_show(fig, save_path)
    return fig

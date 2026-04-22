"""analyze.py - Single-subject analysis orchestration.

This module ties together all analysis steps for a single subject:
  1. Load raw EEG + sleep scoring + artifact info
  2. Preprocess: notch filter, artifact mask, NREM mask
  3. Detect slow oscillations (SOs), spindles, ripples
  4. Compute event-locked TFRs (SO-locked, spindle-locked)
  5. Compute phase-amplitude coupling (PAC) comodulograms
  6. Run Rayleigh test for phase preference of ripples
  7. Return results dict ready for group-level analysis

Usage example
-------------
>>> from src.analyze import run_subject
>>> result = run_subject(
...     data_dir='data/raw',
...     pat_idx=1,
...     hipp_channel='LH',
...     nc_channel='Cz',
...     output_dir='results/sub01',
... )
"""
import logging
from pathlib import Path
from typing import Dict, Optional

import numpy as np

from .io import (
    load_eeg,
    load_supplement,
    get_clean_nrem_mask,
)
from .preprocess import (
    preprocess,
    compute_artifact_mask,
    apply_mask,
)
from .detect_events import (
    detect_slow_oscillations,
    detect_spindles,
    detect_ripples,
)
from .tfr import compute_event_locked_tfr
from .pac import compute_pac_comodulogram

logger = logging.getLogger(__name__)


def run_subject(
    data_dir: str,
    pat_idx: int,
    hipp_channel: str = 'HIPP',
    nc_channel: str = 'Cz',
    output_dir: Optional[str] = None,
    fs: int = 1000,
    # Detection parameters (Staresina 2015 defaults)
    so_lo: float = 0.5,
    so_hi: float = 1.25,
    sp_lo: float = 12.0,
    sp_hi: float = 16.0,
    rp_lo: float = 80.0,
    rp_hi: float = 100.0,
) -> Dict:
    """Run the full single-subject Staresina 2015 analysis pipeline.

    Parameters
    ----------
    data_dir     : directory containing subject .mat files
    pat_idx      : patient/subject index (integer)
    hipp_channel : hippocampal channel keyword (e.g. 'LH', 'RH', 'HIPP')
    nc_channel   : neocortical channel keyword (e.g. 'Cz')
    output_dir   : if given, save intermediate results here
    fs           : sampling rate in Hz (default 1000 for this dataset)

    Returns
    -------
    dict with keys:
        'subject_id'   : pat_idx
        'fs'           : sampling rate
        'clean_mask'   : boolean NREM + artifact-free mask
        'so_events'    : pd.DataFrame of slow oscillation events
        'sp_events'    : pd.DataFrame of spindle events
        'rp_events'    : pd.DataFrame of ripple events
        'tfr_so'       : SO-locked TFR dict (avg_power, times, freqs)
        'tfr_sp'       : spindle-locked TFR dict
        'pac_so_sp'    : PAC dict (SO phase x spindle amplitude)
        'pac_sp_rp'    : PAC dict (spindle phase x ripple amplitude)
    """
    logger.info(f"=== Subject {pat_idx:02d} ===")
    results: Dict = {'subject_id': pat_idx, 'fs': fs}

    # ------------------------------------------------------------------
    # 1. Load data
    # ------------------------------------------------------------------
    logger.info("Loading hippocampal EEG...")
    hipp_signal = load_eeg(data_dir, pat_idx, channel=hipp_channel)
    logger.info(f"  signal shape: {hipp_signal.shape}, fs={fs} Hz")

    sup = load_supplement(data_dir, pat_idx, channel=hipp_channel)

    # ------------------------------------------------------------------
    # 2. Build clean NREM mask
    # ------------------------------------------------------------------
    logger.info("Building NREM + artifact mask...")
    # Start with NREM epochs from sleep scoring
    nrem_art_mask = get_clean_nrem_mask(
        sup['scoring'],
        sup['artifacts'],
        sup['datalen'],
        fs=fs,
    )
    # Additionally: run signal-based artifact detection
    signal_art_mask = compute_artifact_mask(hipp_signal, fs)
    clean_mask = nrem_art_mask & signal_art_mask
    results['clean_mask'] = clean_mask
    pct_clean = clean_mask.mean() * 100
    logger.info(f"  {pct_clean:.1f}% of recording is clean NREM")

    # Preprocess: notch + broadband passthrough
    hipp_proc = preprocess(hipp_signal, fs)

    # ------------------------------------------------------------------
    # 3. Detect sleep events
    # ------------------------------------------------------------------
    logger.info("Detecting slow oscillations...")
    so_events = detect_slow_oscillations(
        hipp_proc, fs,
        lo=so_lo, hi=so_hi,
        clean_mask=clean_mask,
    )
    results['so_events'] = so_events
    logger.info(f"  {len(so_events)} SOs detected")

    logger.info("Detecting spindles...")
    sp_events = detect_spindles(
        hipp_proc, fs,
        lo=sp_lo, hi=sp_hi,
        clean_mask=clean_mask,
    )
    results['sp_events'] = sp_events
    logger.info(f"  {len(sp_events)} spindles detected")

    logger.info("Detecting ripples...")
    rp_events = detect_ripples(
        hipp_proc, fs,
        lo=rp_lo, hi=rp_hi,
        clean_mask=clean_mask,
    )
    results['rp_events'] = rp_events
    logger.info(f"  {len(rp_events)} ripples detected")

    # ------------------------------------------------------------------
    # 4. Time-frequency representations
    # ------------------------------------------------------------------
    freqs = np.logspace(np.log10(1), np.log10(120), 60)

    if len(so_events) > 0:
        logger.info("Computing SO-locked TFR...")
        so_samples = so_events['down_sample'].values
        results['tfr_so'] = compute_event_locked_tfr(
            hipp_proc, fs, so_samples,
            tmin=-2.0, tmax=2.0,
            freqs=freqs, n_cycles=7.0,
            baseline=(-1.5, -0.5),
        )
        logger.info(f"  {results['tfr_so']['n_events']} SO epochs used")
    else:
        results['tfr_so'] = None
        logger.warning("No SO events found; skipping SO-locked TFR.")

    if len(sp_events) > 0:
        logger.info("Computing spindle-locked TFR...")
        sp_samples = sp_events['center_sample'].values
        results['tfr_sp'] = compute_event_locked_tfr(
            hipp_proc, fs, sp_samples,
            tmin=-1.0, tmax=1.0,
            freqs=freqs, n_cycles=7.0,
            baseline=(-0.8, -0.2),
        )
        logger.info(f"  {results['tfr_sp']['n_events']} spindle epochs used")
    else:
        results['tfr_sp'] = None
        logger.warning("No spindle events found; skipping spindle-locked TFR.")

    # ------------------------------------------------------------------
    # 5. Phase-amplitude coupling (PAC)
    # ------------------------------------------------------------------
    # SO phase (0.5-1.25 Hz) x spindle amplitude (12-16 Hz)
    so_phase_freqs = np.array([[0.5, 1.25]])
    sp_amp_freqs   = np.array([[12.0, 16.0]])
    rp_amp_freqs   = np.array([[80.0, 100.0]])
    sp_phase_freqs = sp_amp_freqs.copy()

    clean_signal = apply_mask(hipp_proc, clean_mask)

    logger.info("Computing SO->Spindle PAC...")
    try:
        results['pac_so_sp'] = compute_pac_comodulogram(
            clean_signal, fs,
            phase_freqs=so_phase_freqs,
            amp_freqs=sp_amp_freqs,
        )
    except Exception as exc:
        logger.warning(f"SO->Spindle PAC failed: {exc}")
        results['pac_so_sp'] = None

    logger.info("Computing Spindle->Ripple PAC...")
    try:
        results['pac_sp_rp'] = compute_pac_comodulogram(
            clean_signal, fs,
            phase_freqs=sp_phase_freqs,
            amp_freqs=rp_amp_freqs,
        )
    except Exception as exc:
        logger.warning(f"Spindle->Ripple PAC failed: {exc}")
        results['pac_sp_rp'] = None

    # ------------------------------------------------------------------
    # 6. Save results
    # ------------------------------------------------------------------
    if output_dir is not None:
        _save_results(results, output_dir, pat_idx)

    logger.info(f"Subject {pat_idx:02d} done.")
    return results


def _save_results(results: Dict, output_dir: str, pat_idx: int) -> None:
    """Save per-subject numpy arrays and DataFrames to disk."""
    import pickle
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    subj_dir = out / f'pat{pat_idx:02d}'
    subj_dir.mkdir(exist_ok=True)

    # Save event DataFrames as CSVs
    for key in ('so_events', 'sp_events', 'rp_events'):
        df = results.get(key)
        if df is not None and len(df) > 0:
            df.to_csv(subj_dir / f'{key}.csv', index=False)

    # Save TFR power maps as .npy
    for key in ('tfr_so', 'tfr_sp'):
        tfr = results.get(key)
        if tfr is not None:
            np.save(subj_dir / f'{key}_avg_power.npy', tfr['avg_power'])
            np.save(subj_dir / f'{key}_freqs.npy',     tfr['freqs'])
            np.save(subj_dir / f'{key}_times.npy',     tfr['times'])

    # Save PAC matrices
    for key in ('pac_so_sp', 'pac_sp_rp'):
        pac = results.get(key)
        if pac is not None and 'MI_matrix' in pac:
            np.save(subj_dir / f'{key}_MI.npy', pac['MI_matrix'])

    # Full pickle backup
    with open(subj_dir / 'results.pkl', 'wb') as f:
        pickle.dump(results, f)

    logger.info(f"Results saved to {subj_dir}")

"""
pipeline.py - Pipeline orchestration for Staresina et al. 2015 reproduction.

This module coordinates the full analysis workflow from raw EEG data to final
figures. It follows the processing steps described in the paper:
  1. Load and preprocess EEG data
  2. Detect sleep oscillations (SO), spindles, and ripples
  3. Compute time-frequency representations (event-locked)
  4. Calculate phase-amplitude coupling
  5. Statistical testing and visualization
"""
import logging
from pathlib import Path
from typing import Dict, List, Optional

import yaml
import numpy as np
# mne is not used directly in pipeline.py (only in io.py when loading EDF files)

from .io import load_eeg, load_supplement, load_spindle_events, load_ripple_events, get_clean_nrem_mask, list_subjects
from .preprocess import preprocess, extract_nrem_epochs
from .detect_events import detect_slow_oscillations, detect_spindles, detect_ripples
from .tfr import compute_event_locked_tfr          # ← was: compute_morlet_tfr
from .pac import compute_pac_comodulogram
from .stats import cluster_permutation_test
from .plots import (
    plot_so_locked_tfr,
    plot_spindle_locked_tfr,
    plot_pac_comodulogram,
)

logger = logging.getLogger(__name__)


class AnalysisPipeline:
    """Main analysis pipeline coordinator."""

    def __init__(self, config_path: str):
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)

        self.data_dir = Path(self.config['paths']['data_dir'])
        self.output_dir = Path(self.config['paths']['output_dir'])
        self.output_dir.mkdir(parents=True, exist_ok=True)

        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.output_dir / 'pipeline.log'),
                logging.StreamHandler()
            ]
        )
        logger.info("Pipeline initialized")

    def run_full_analysis(self, subject_ids: Optional[List[int]] = None):
        """Run complete analysis pipeline for all subjects."""
        logger.info("Starting full analysis pipeline")

        if subject_ids is None:
            subject_ids = list_subjects(str(self.data_dir))

        results = {}
        for subject_id in subject_ids:
            logger.info(f"Processing subject {subject_id}")
            try:
                results[subject_id] = self.process_subject(subject_id)
            except Exception as e:
                logger.error(f"Error processing subject {subject_id}: {e}")
                continue

        logger.info("Running group-level analysis")
        self.group_analysis(results)
        logger.info("Pipeline completed successfully")
        return results

    def process_subject(self, pat_idx: int) -> Dict:
        """Process a single subject through the full pipeline."""
        results = {'subject_id': pat_idx}

        # 1. Load data
        logger.info(f"Loading data for pat{pat_idx:02d}")
        signal = load_eeg(str(self.data_dir), pat_idx, channel="HIPP")
        sup    = load_supplement(str(self.data_dir), pat_idx, channel="HIPP")
        fs     = self.config.get('fs', 1000)
        results['fs'] = fs

        # 2. Build clean NREM mask
        clean_mask = get_clean_nrem_mask(
            sup['scoring'], sup['artifacts'], sup['datalen'], fs=fs
        )

        # 3. Preprocess signal
        signal_clean = preprocess(signal, fs)

        # 4. Detect events
        logger.info("Detecting sleep events")
        results['events'] = self.detect_events(signal_clean, fs, clean_mask)

        # 5. Time-frequency analysis
        logger.info("Computing time-frequency representations")
        results['tfr'] = self.compute_tfr(signal_clean, fs, results['events'])

        # 6. Phase-amplitude coupling
        logger.info("Computing phase-amplitude coupling")
        results['pac'] = self.compute_pac_analysis(signal_clean, fs)

        # 7. Save results
        self.save_subject_results(f"pat{pat_idx:02d}", results)
        return results

    def detect_events(self, signal: np.ndarray, fs: int, clean_mask: np.ndarray) -> Dict:
        """Detect SO, spindles, and ripples."""
        cfg_so = self.config['detection']['slow_oscillations']
        so_events = detect_slow_oscillations(
            signal, fs,
            lo=cfg_so['freq_range'][0],
            hi=cfg_so['freq_range'][1],
            amp_pct=cfg_so.get('amplitude_threshold', 75),
            min_dur=cfg_so['duration_range'][0],
            max_dur=cfg_so['duration_range'][1],
            clean_mask=clean_mask
        )

        cfg_sp = self.config['detection']['spindles']
        spindle_events = detect_spindles(
            signal, fs,
            lo=cfg_sp['freq_range'][0],
            hi=cfg_sp['freq_range'][1],
            z_thresh=cfg_sp.get('threshold', 2.0),
            min_dur=cfg_sp['duration_range'][0],
            max_dur=cfg_sp['duration_range'][1],
            clean_mask=clean_mask
        )

        cfg_rp = self.config['detection']['ripples']
        ripple_events = detect_ripples(
            signal, fs,
            lo=cfg_rp['freq_range'][0],
            hi=cfg_rp['freq_range'][1],
            z_thresh=cfg_rp.get('threshold', 3.0),
            min_dur=cfg_rp['duration_range'][0],
            max_dur=cfg_rp['duration_range'][1],
            clean_mask=clean_mask
        )

        return {
            'slow_oscillations': so_events,
            'spindles': spindle_events,
            'ripples': ripple_events
        }

    def compute_tfr(self, signal: np.ndarray, fs: int, events: Dict) -> Dict:
        """Compute event-locked TFRs."""
        cfg_tfr = self.config['tfr']
        freqs = np.logspace(
            np.log10(cfg_tfr.get('freq_min', 1)),
            np.log10(cfg_tfr.get('freq_max', 120)),
            cfg_tfr.get('n_freqs', 60)
        )

        tfr_results = {}

        # SO-locked TFR
        if len(events['slow_oscillations']) > 0:
            so_samples = events['slow_oscillations']['down_sample'].values \
                if hasattr(events['slow_oscillations'], 'values') \
                else np.array(events['slow_oscillations'])
            tfr_results['so_locked'] = compute_event_locked_tfr(
                signal, fs, so_samples,
                tmin=cfg_tfr.get('so_tmin', -2.0),
                tmax=cfg_tfr.get('so_tmax', 2.0),
                freqs=freqs,
                n_cycles=cfg_tfr.get('n_cycles', 7.0)
            )

        # Spindle-locked TFR
        if len(events['spindles']) > 0:
            sp_samples = events['spindles']['center_sample'].values \
                if hasattr(events['spindles'], 'values') \
                else np.array(events['spindles'])
            tfr_results['spindle_locked'] = compute_event_locked_tfr(
                signal, fs, sp_samples,
                tmin=cfg_tfr.get('sp_tmin', -1.0),
                tmax=cfg_tfr.get('sp_tmax', 1.0),
                freqs=freqs,
                n_cycles=cfg_tfr.get('n_cycles', 7.0)
            )

        return tfr_results

    def compute_pac_analysis(self, signal: np.ndarray, fs: int) -> Dict:
        """Compute PAC comodulogram."""
        cfg_pac = self.config['pac']
        phase_freqs = np.array(cfg_pac['phase_freqs'])
        amp_freqs   = np.array(cfg_pac['amp_freqs'])

        pac_matrix = compute_pac_comodulogram(
            signal, fs,
            phase_freqs=phase_freqs,
            amp_freqs=amp_freqs,
        )
        return {'comodulogram': pac_matrix}

    def group_analysis(self, all_results: Dict):
        """Perform group-level statistics and save figures."""
        import matplotlib.pyplot as plt

        # Collect all SO-locked TFRs across subjects
        so_maps, sp_maps = [], []
        for res in all_results.values():
            if 'so_locked' in res.get('tfr', {}):
                so_maps.append(res['tfr']['so_locked']['avg_power'])
            if 'spindle_locked' in res.get('tfr', {}):
                sp_maps.append(res['tfr']['spindle_locked']['avg_power'])

        if so_maps:
            avg_so = np.mean(so_maps, axis=0)
            freqs = np.logspace(np.log10(1), np.log10(120), 60)
            tmin = self.config['tfr'].get('so_tmin', -2.0)
            tmax = self.config['tfr'].get('so_tmax', 2.0)
            times = np.linspace(tmin, tmax, avg_so.shape[-1])
            fig = plot_so_locked_tfr(times, freqs, avg_so,
                                      save_path=str(self.output_dir / 'fig2_so_locked_tfr.png'))
            plt.close(fig)
            logger.info("Fig 2 (SO-locked TFR) saved.")

        if sp_maps:
            avg_sp = np.mean(sp_maps, axis=0)
            freqs = np.logspace(np.log10(1), np.log10(120), 60)
            tmin = self.config['tfr'].get('sp_tmin', -1.0)
            tmax = self.config['tfr'].get('sp_tmax', 1.0)
            times = np.linspace(tmin, tmax, avg_sp.shape[-1])
            fig = plot_spindle_locked_tfr(times, freqs, avg_sp,
                                           save_path=str(self.output_dir / 'fig3_spindle_locked_tfr.png'))
            plt.close(fig)
            logger.info("Fig 3 (Spindle-locked TFR) saved.")

        logger.info(f"Group figures saved to {self.output_dir}")

    def save_subject_results(self, subject_id: str, results: Dict):
        """Save individual subject results."""
        subj_dir = self.output_dir / subject_id
        subj_dir.mkdir(exist_ok=True)

        events = results['events']
        for key, arr in [('so_events', events['slow_oscillations']),
                          ('spindle_events', events['spindles']),
                          ('ripple_events', events['ripples'])]:
            np.save(subj_dir / f'{key}.npy', arr)

        if 'pac' in results:
            np.save(subj_dir / 'pac_comodulogram.npy',
                    results['pac']['comodulogram']['MI_matrix'])

        logger.info(f"Results saved for {subject_id}")


def main():
    """Command-line entry point."""
    import argparse
    parser = argparse.ArgumentParser(
        description='Run Staresina et al. 2015 reproduction pipeline'
    )
    parser.add_argument('--config', type=str, default='configs/analysis.yaml',
                        help='Path to configuration file')
    parser.add_argument('--subjects', nargs='+', type=int, default=None,
                        help='Specific patient indices to process (e.g. 1 2 3)')
    args = parser.parse_args()

    pipeline = AnalysisPipeline(args.config)
    pipeline.run_full_analysis(subject_ids=args.subjects)


if __name__ == '__main__':
    main()

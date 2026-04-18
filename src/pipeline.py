"""Pipeline orchestration for Staresina et al. 2015 reproduction.

This module coordinates the full analysis pipeline from raw EEG data to final
figures. It follows the processing steps described in the paper:
1. Load and preprocess EEG data
2. Detect sleep oscillations (SO), spindles, and ripples
3. Analyze temporal coupling between events
4. Compute time-frequency representations
5. Calculate phase-amplitude coupling
6. Statistical testing and visualization

Principle: The pipeline implements a multi-stage signal processing approach
where each stage builds on the previous one. First, we extract basic features
(events), then examine their relationships (coupling), and finally quantify
rhythmic interactions (PAC).
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional
import yaml
import numpy as np
import mne

from .io import load_eeg_data
from .preprocess import preprocess_eeg, extract_nrem_epochs
from .detect_events import detect_slow_oscillations, detect_spindles, detect_ripples
from .tfr import compute_morlet_tfr
from .pac import compute_pac_comodulogram
from .stats import cluster_permutation_test
from .plots import (
    plot_event_counts,
    plot_spindle_locked_tfr,
    plot_comodulogram,
    plot_rose_plot,
)

logger = logging.getLogger(__name__)


class AnalysisPipeline:
    """Main analysis pipeline coordinator.
    
    This class manages the complete analysis workflow, handling data loading,
    processing, analysis, and visualization.
    
    Attributes:
        config: Dictionary containing analysis parameters
        data_dir: Path to input data directory
        output_dir: Path for saving results
    """
    
    def __init__(self, config_path: str):
        """Initialize pipeline with configuration.
        
        Args:
            config_path: Path to YAML configuration file
        """
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        self.data_dir = Path(self.config['paths']['data_dir'])
        self.output_dir = Path(self.config['paths']['output_dir'])
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.output_dir / 'pipeline.log'),
                logging.StreamHandler()
            ]
        )
        logger.info("Pipeline initialized")
    
    def run_full_analysis(self, subject_ids: Optional[List[str]] = None):
        """Run complete analysis pipeline.
        
        Args:
            subject_ids: List of subject IDs to process. If None, process all.
        """
        logger.info("Starting full analysis pipeline")
        
        if subject_ids is None:
            subject_ids = self.config['subjects']
        
        results = {}
        
        for subject_id in subject_ids:
            logger.info(f"Processing subject {subject_id}")
            try:
                results[subject_id] = self.process_subject(subject_id)
            except Exception as e:
                logger.error(f"Error processing subject {subject_id}: {str(e)}")
                continue
        
        # Group-level analysis
        logger.info("Running group-level analysis")
        self.group_analysis(results)
        
        logger.info("Pipeline completed successfully")
        return results
    
    def process_subject(self, subject_id: str) -> Dict:
        """Process single subject through full pipeline.
        
        Args:
            subject_id: Subject identifier
            
        Returns:
            Dictionary containing all analysis results for this subject
        """
        results = {'subject_id': subject_id}
        
        # 1. Load data
        logger.info(f"Loading data for {subject_id}")
        raw = load_eeg_data(
            self.data_dir / subject_id,
            self.config['channels']
        )
        results['raw'] = raw
        
        # 2. Preprocess
        logger.info("Preprocessing EEG")
        raw_filtered = preprocess_eeg(
            raw,
            l_freq=self.config['preprocessing']['l_freq'],
            h_freq=self.config['preprocessing']['h_freq'],
            notch_freq=self.config['preprocessing'].get('notch_freq')
        )
        
        # Extract NREM sleep epochs
        nrem_epochs = extract_nrem_epochs(
            raw_filtered,
            sleep_stages=self.config['sleep_stages']
        )
        results['nrem_epochs'] = nrem_epochs
        
        # 3. Event detection
        logger.info("Detecting sleep events")
        results['events'] = self.detect_events(nrem_epochs)
        
        # 4. Time-frequency analysis
        logger.info("Computing time-frequency representations")
        results['tfr'] = self.compute_tfr(nrem_epochs, results['events'])
        
        # 5. Phase-amplitude coupling
        logger.info("Computing phase-amplitude coupling")
        results['pac'] = self.compute_pac_analysis(nrem_epochs)
        
        # 6. Save subject results
        self.save_subject_results(subject_id, results)
        
        return results
    
    def detect_events(self, epochs: mne.Epochs) -> Dict:
        """Detect all sleep oscillatory events.
        
        Args:
            epochs: NREM sleep epochs
            
        Returns:
            Dictionary with detected events for each oscillation type
        """
        data = epochs.get_data()
        sfreq = epochs.info['sfreq']
        
        cfg_so = self.config['detection']['slow_oscillations']
        so_events = detect_slow_oscillations(
            data,
            sfreq=sfreq,
            freq_so=cfg_so['freq_range'],
            duration_so=cfg_so['duration_range'],
            amplitude_threshold=cfg_so['amplitude_threshold']
        )
        
        cfg_sp = self.config['detection']['spindles']
        spindle_events = detect_spindles(
            data,
            sfreq=sfreq,
            freq_sp=cfg_sp['freq_range'],
            duration_sp=cfg_sp['duration_range'],
            threshold=cfg_sp['threshold']
        )
        
        cfg_rp = self.config['detection']['ripples']
        ripple_events = detect_ripples(
            data,
            sfreq=sfreq,
            freq_ripple=cfg_rp['freq_range'],
            duration_ripple=cfg_rp['duration_range'],
            threshold=cfg_rp['threshold']
        )
        
        return {
            'slow_oscillations': so_events,
            'spindles': spindle_events,
            'ripples': ripple_events
        }
    
    def compute_tfr(self, epochs: mne.Epochs, events: Dict) -> Dict:
        """Compute time-frequency representations locked to events.
        
        Args:
            epochs: NREM sleep epochs
            events: Detected events
            
        Returns:
            Dictionary with TFR results
        """
        cfg_tfr = self.config['tfr']
        
        # Spindle-locked TFR
        tfr_spindle = compute_morlet_tfr(
            epochs,
            freqs=cfg_tfr['freqs'],
            n_cycles=cfg_tfr['n_cycles'],
            event_times=events['spindles']
        )
        
        return {'spindle_locked': tfr_spindle}
    
    def compute_pac_analysis(self, epochs: mne.Epochs) -> Dict:
        """Compute phase-amplitude coupling.
        
        Args:
            epochs: NREM sleep epochs
            
        Returns:
            Dictionary with PAC results
        """
        cfg_pac = self.config['pac']
        
        data = epochs.get_data()
        sfreq = epochs.info['sfreq']
        
        pac_matrix = compute_pac_comodulogram(
            data,
            sfreq=sfreq,
            phase_freqs=cfg_pac['phase_freqs'],
            amp_freqs=cfg_pac['amp_freqs'],
            method=cfg_pac['method']
        )
        
        return {'comodulogram': pac_matrix}
    
    def group_analysis(self, all_results: Dict):
        """Perform group-level statistics and create figures.
        
        Args:
            all_results: Dictionary mapping subject_id to their results
        """
        # Aggregate event counts across subjects
        all_so_counts = []
        all_spindle_counts = []
        all_ripple_counts = []
        
        for subject_id, results in all_results.items():
            events = results['events']
            all_so_counts.append(len(events['slow_oscillations']))
            all_spindle_counts.append(len(events['spindles']))
            all_ripple_counts.append(len(events['ripples']))
        
        # Create group figures
        fig = plot_event_counts(
            all_so_counts,
            all_spindle_counts,
            all_ripple_counts,
            subject_ids=list(all_results.keys())
        )
        fig.savefig(self.output_dir / 'group_event_counts.png', dpi=300)
        
        # Average comodulograms
        all_comods = [r['pac']['comodulogram'] for r in all_results.values()]
        mean_comod = np.mean(all_comods, axis=0)
        
        fig = plot_comodulogram(
            mean_comod,
            phase_freqs=self.config['pac']['phase_freqs'],
            amp_freqs=self.config['pac']['amp_freqs']
        )
        fig.savefig(self.output_dir / 'group_comodulogram.png', dpi=300)
        
        logger.info(f"Group figures saved to {self.output_dir}")
    
    def save_subject_results(self, subject_id: str, results: Dict):
        """Save individual subject results.
        
        Args:
            subject_id: Subject identifier
            results: Analysis results dictionary
        """
        subj_dir = self.output_dir / subject_id
        subj_dir.mkdir(exist_ok=True)
        
        # Save event counts
        events = results['events']
        np.save(subj_dir / 'so_events.npy', events['slow_oscillations'])
        np.save(subj_dir / 'spindle_events.npy', events['spindles'])
        np.save(subj_dir / 'ripple_events.npy', events['ripples'])
        
        # Save PAC results
        np.save(subj_dir / 'pac_comodulogram.npy', results['pac']['comodulogram'])
        
        logger.info(f"Results saved for {subject_id}")


def main():
    """Command-line entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Run Staresina et al. 2015 reproduction pipeline'
    )
    parser.add_argument(
        '--config',
        type=str,
        default='configs/analysis.yaml',
        help='Path to configuration file'
    )
    parser.add_argument(
        '--subjects',
        nargs='+',
        default=None,
        help='Specific subject IDs to process'
    )
    
    args = parser.parse_args()
    
    pipeline = AnalysisPipeline(args.config)
    pipeline.run_full_analysis(subject_ids=args.subjects)


if __name__ == '__main__':
    main()

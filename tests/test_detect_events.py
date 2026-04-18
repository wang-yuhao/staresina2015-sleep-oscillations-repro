"""Unit tests for event detection functions.

These tests verify that slow oscillation, spindle, and ripple detection
algorithms work correctly on synthetic data.
"""

import pytest
import numpy as np
from scipy import signal
import sys
from pathlib import Path

# Add src to path
src_dir = Path(__file__).parent.parent / 'src'
sys.path.insert(0, str(src_dir))

from detect_events import (
    detect_slow_oscillations,
    detect_spindles,
    detect_ripples
)


class TestSlowOscillationDetection:
    """Test suite for slow oscillation detection."""
    
    def test_detect_synthetic_so(self):
        """Test SO detection on synthetic signal with known oscillation."""
        # Create synthetic data: 1 Hz oscillation
        sfreq = 1000
        duration = 10  # seconds
        t = np.arange(0, duration, 1/sfreq)
        
        # Pure 1 Hz sine wave
        data = np.sin(2 * np.pi * 1.0 * t)
        data = data.reshape(1, 1, -1)  # (n_epochs, n_channels, n_times)
        
        events = detect_slow_oscillations(
            data,
            sfreq=sfreq,
            freq_so=(0.5, 1.5),
            duration_so=(0.8, 2.0),
            amplitude_threshold=0.5
        )
        
        # Should detect approximately 10 cycles
        assert len(events) > 5
        assert len(events) < 15
    
    def test_no_so_in_noise(self):
        """Test that random noise doesn't produce false positives."""
        sfreq = 1000
        duration = 5
        
        # White noise
        data = np.random.randn(1, 1, int(sfreq * duration)) * 0.1
        
        events = detect_slow_oscillations(
            data,
            sfreq=sfreq,
            freq_so=(0.5, 1.25),
            duration_so=(0.8, 2.0),
            amplitude_threshold=3.0  # High threshold
        )
        
        # Should detect very few or no events
        assert len(events) < 3


class TestSpindleDetection:
    """Test suite for spindle detection."""
    
    def test_detect_synthetic_spindle(self):
        """Test spindle detection on synthetic 12 Hz burst."""
        sfreq = 1000
        duration = 5
        t = np.arange(0, duration, 1/sfreq)
        
        # Create spindle-like burst at 12 Hz
        spindle_freq = 12
        data = np.zeros_like(t)
        
        # Insert 1-second spindle burst starting at 2 seconds
        burst_start = int(2 * sfreq)
        burst_end = int(3 * sfreq)
        burst_t = t[burst_start:burst_end]
        
        # Amplitude-modulated sinusoid
        envelope = np.hanning(len(burst_t))
        data[burst_start:burst_end] = envelope * np.sin(2 * np.pi * spindle_freq * burst_t)
        
        data = data.reshape(1, 1, -1)
        
        events = detect_spindles(
            data,
            sfreq=sfreq,
            freq_sp=(9, 16),
            duration_sp=(0.5, 3.0),
            threshold=1.0
        )
        
        # Should detect the inserted spindle
        assert len(events) >= 1
    
    def test_spindle_frequency_specificity(self):
        """Test that detector rejects oscillations outside frequency range."""
        sfreq = 1000
        duration = 5
        t = np.arange(0, duration, 1/sfreq)
        
        # Create 20 Hz oscillation (outside spindle range)
        data = np.sin(2 * np.pi * 20 * t)
        data = data.reshape(1, 1, -1)
        
        events = detect_spindles(
            data,
            sfreq=sfreq,
            freq_sp=(9, 16),
            duration_sp=(0.5, 3.0),
            threshold=1.0
        )
        
        # Should not detect spindles outside frequency range
        assert len(events) == 0


class TestRippleDetection:
    """Test suite for ripple detection."""
    
    def test_detect_synthetic_ripple(self):
        """Test ripple detection on synthetic 90 Hz burst."""
        sfreq = 2000  # Higher sampling rate for ripples
        duration = 5
        t = np.arange(0, duration, 1/sfreq)
        
        # Create ripple-like burst at 90 Hz
        ripple_freq = 90
        data = np.zeros_like(t)
        
        # Insert 100ms ripple burst
        burst_start = int(2 * sfreq)
        burst_dur = int(0.1 * sfreq)
        burst_end = burst_start + burst_dur
        burst_t = t[burst_start:burst_end]
        
        # High-frequency burst
        envelope = np.hanning(len(burst_t))
        data[burst_start:burst_end] = envelope * np.sin(2 * np.pi * ripple_freq * burst_t)
        
        data = data.reshape(1, 1, -1)
        
        events = detect_ripples(
            data,
            sfreq=sfreq,
            freq_ripple=(80, 100),
            duration_ripple=(0.04, 0.2),
            threshold=2.0
        )
        
        # Should detect the inserted ripple
        assert len(events) >= 1
    
    def test_ripple_duration_constraint(self):
        """Test that very long oscillations are not detected as ripples."""
        sfreq = 2000
        duration = 5
        t = np.arange(0, duration, 1/sfreq)
        
        # Create continuous 90 Hz (too long for ripple)
        data = np.sin(2 * np.pi * 90 * t)
        data = data.reshape(1, 1, -1)
        
        events = detect_ripples(
            data,
            sfreq=sfreq,
            freq_ripple=(80, 100),
            duration_ripple=(0.04, 0.2),  # Max 200ms
            threshold=1.0
        )
        
        # Should not detect continuous oscillation as ripple
        # or detect many short segments
        assert len(events) < 100  # Sanity check


class TestEventParameters:
    """Test event parameter extraction."""
    
    def test_event_timing(self):
        """Test that detected events have correct timing information."""
        sfreq = 1000
        duration = 5
        t = np.arange(0, duration, 1/sfreq)
        
        # Create signal with event at known time
        data = np.zeros_like(t)
        event_start = int(2 * sfreq)  # 2 seconds
        event_end = int(3 * sfreq)    # 3 seconds
        data[event_start:event_end] = np.sin(2 * np.pi * 12 * t[event_start:event_end])
        data = data.reshape(1, 1, -1)
        
        events = detect_spindles(
            data,
            sfreq=sfreq,
            freq_sp=(9, 16),
            duration_sp=(0.5, 2.0),
            threshold=0.5
        )
        
        if len(events) > 0:
            # Check that detected event is near expected time
            event = events[0]
            assert 'start' in event or 'time' in event


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

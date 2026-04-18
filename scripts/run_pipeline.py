#!/usr/bin/env python
"""Convenience script to run the full analysis pipeline.

This script provides a simple entry point for running the complete
Staresina et al. 2015 reproduction analysis.

Usage:
    python scripts/run_pipeline.py
    python scripts/run_pipeline.py --config configs/custom_config.yaml
    python scripts/run_pipeline.py --subjects sub-01 sub-02
"""

import sys
from pathlib import Path

# Add src to path
src_dir = Path(__file__).parent.parent / 'src'
sys.path.insert(0, str(src_dir))

from pipeline import main

if __name__ == '__main__':
    main()

#!/usr/bin/env python
"""Convenience script to run the full analysis pipeline.

Usage:
    python scripts/run_pipeline.py
    python scripts/run_pipeline.py --config configs/custom_config.yaml
    python scripts/run_pipeline.py --subjects sub-01 sub-02
"""
import sys
from pathlib import Path

# Add repo ROOT (not src/) so that relative imports inside src/ work correctly
repo_root = Path(__file__).parent.parent
sys.path.insert(0, str(repo_root))

from src.pipeline import main       # ← FIXED: was "from pipeline import main"

if __name__ == '__main__':
    main()

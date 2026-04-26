#!/bin/bash
# ============================================================================
# Ngo et al. (2020) Reproduction Pipeline - Master Script
# ============================================================================
# Paper: Sleep spindles mediate hippocampal-neocortical coupling during
#        long-duration ripples. eLife 9:e57011
#
# This script runs the entire reproduction pipeline from preprocessing
# to figure generation.
#
# Usage:
#   bash run_all.sh
#   bash run_all.sh --skip-download  # Skip data download if already done
#   bash run_all.sh --subject sub-01 # Process only one subject
#
# Prerequisites:
#   - Data downloaded to data/raw/ (or run scripts/01_download_data.py first)
#   - Python environment set up (see README.md)
# ============================================================================

set -e  # Exit on error

echo "==============================================="
echo "Ngo et al. (2020) Reproduction Pipeline"
echo "==============================================="
echo ""

# Parse arguments
SKIP_DOWNLOAD=false
SUBJECT_ARG=""

while [[ $# -gt 0 ]]; do
  case $1 in
    --skip-download)
      SKIP_DOWNLOAD=true
      shift
      ;;
    --subject)
      SUBJECT_ARG="--subject $2"
      shift 2
      ;;
    *)
      echo "Unknown option: $1"
      echo "Usage: bash run_all.sh [--skip-download] [--subject SUB_ID]"
      exit 1
      ;;
  esac
done

# Step 1: Download data (optional)
if [ "$SKIP_DOWNLOAD" = false ]; then
  echo "[1/7] Downloading data from OSF..."
  python scripts/01_download_data.py
  echo "Done."
  echo ""
else
  echo "[1/7] Skipping data download (--skip-download specified)"
  echo ""
fi

# Step 2: Preprocess
echo "[2/7] Preprocessing raw data..."
python scripts/02_preprocess.py $SUBJECT_ARG
echo "Done."
echo ""

# Step 3: Detect spindles and ripples
echo "[3/7] Detecting spindles and ripples..."
python scripts/03_detect_spindles_ripples.py $SUBJECT_ARG
echo "Done."
echo "" 

# Step 4: Time-frequency analysis
echo "[4/7] Computing time-frequency representations..."
python scripts/04_tfr_analysis.py $SUBJECT_ARG
echo "Done."
echo ""

# Step 5: Coherence and PDC analysis
echo "[5/7] Computing coherence and directionality (PDC)..."
python scripts/05_coherence_pdc.py $SUBJECT_ARG
echo "Done."
echo ""

# Step 6: Long vs short ripple comparison
echo "[6/7] Comparing long vs. short duration ripples..."
python scripts/06_long_vs_short_ripples.py $SUBJECT_ARG
echo "Done."
echo ""

# Step 7: Generate figures
echo "[7/7] Generating publication figures..."
python scripts/07_plot_figures.py
echo "Done."
echo ""

echo "==============================================="
echo "Pipeline complete!"
echo "==============================================="
echo ""
echo "Results saved to:"
echo "  - Figures: results/figures/"
echo "  - Statistics: results/stats/"
echo ""
echo "Next steps:"
echo "  1. Review figures in results/figures/"
echo "  2. Compare against original paper"
echo "  3. Check statistics in results/stats/"
echo ""
echo "For interactive exploration:"
echo "  jupyter notebook notebooks/reproduction_walkthrough.ipynb"
echo ""

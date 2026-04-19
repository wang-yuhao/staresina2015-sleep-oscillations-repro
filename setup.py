#!/usr/bin/env python3
"""
Setup script for Staresina 2015 Sleep Oscillations Reproduction Project

This setup.py allows easy installation of the project and its dependencies.

Usage:
    # Development installation (editable mode)
    pip install -e .
    
    # Regular installation
    pip install .
    
    # Installation with development dependencies
    pip install -e .[dev]
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read the README file
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text(encoding='utf-8')

setup(
    name="staresina2015-repro",
    version="0.1.0",
    author="wang-yuhao",
    description="Reproduction of Staresina et al. 2015 sleep oscillation coupling study",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/wang-yuhao/staresina2015-sleep-oscillations-repro",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.8",
    install_requires=[
        "numpy>=1.20.0",
        "scipy>=1.7.0",
        "matplotlib>=3.3.0",
        "pandas>=1.3.0",
        "pyyaml>=5.4",
        "mne>=0.23.0",
        "scikit-learn>=0.24.0",
    ],
    extras_require={
        "dev": [
            "pytest>=6.2.0",
            "pytest-cov>=2.12.0",
            "black>=21.6b0",
            "flake8>=3.9.0",
            "jupyter>=1.0.0",
            "ipython>=7.25.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "organize-data=scripts.organize_data:main",
            "run-pipeline=scripts.run_pipeline:main",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Science/Research",
        "Topic :: Scientific/Engineering :: Bio-Informatics",
        "Topic :: Scientific/Engineering :: Medical Science Apps.",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
    ],
    keywords="neuroscience sleep eeg oscillations reproduction",
    project_urls={
        "Bug Reports": "https://github.com/wang-yuhao/staresina2015-sleep-oscillations-repro/issues",
        "Source": "https://github.com/wang-yuhao/staresina2015-sleep-oscillations-repro",
        "Original Paper": "https://www.nature.com/articles/nn.4119",
    },
)

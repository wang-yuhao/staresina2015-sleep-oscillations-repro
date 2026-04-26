#!/usr/bin/env python3
"""
Script 01: Download Data from OSF
==================================
Ngo, Fell & Staresina (2020) — Reproduction Pipeline
Paper: Sleep spindles mediate hippocampal-neocortical coupling during
      long-duration ripples. eLife 9:e57011

Dataset DOI: 10.17605/OSF.IO/3HPVR
Dataset URL: https://osf.io/3hpvr/

This script downloads the raw EEG data from the Open Science Framework (OSF).
The dataset contains whole-night NREM sleep EEG recordings from 14
pre-surgical epilepsy patients.

The OSF data is organized into 4 folders:
  1. ControlEvents/ngo_et_al_eLife2020_controlData_100sets/
       - 100 subdirectories (named 1-100)
       - Each contains: pat01-14_HIPP_controlNREM.mat, pat01-14_HIPP_controlREM.mat
  2. EEGs/
       - pat01-14_HIPP.mat (main EEG data)
       - pat01-14_HIPP_supplement.mat
  3. Ripples/
       - pat01-14_HIPP_ripples.mat
  4. Spindles/
       - pat01-14_HIPP_spindles.mat
       - pat01-14_NC_spindles.mat

Usage:
    python scripts/01_download_data.py
    python scripts/01_download_data.py --dry-run    # Preview without downloading
    python scripts/01_download_data.py --list-files # List available OSF files

Output:
    data/raw/ControlEvents/ngo_et_al_eLife2020_controlData_100sets/<1-100>/*.mat
    data/raw/EEGs/*.mat
    data/raw/Ripples/*.mat
    data/raw/Spindles/*.mat
"""

import argparse
import os
import sys
import json
from pathlib import Path

import requests
from tqdm import tqdm

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
OSF_PROJECT_ID = "3hpvr"  # From DOI: 10.17605/OSF.IO/3HPVR
OSF_API_BASE = "https://api.osf.io/v2"
RAW_DATA_DIR = Path("data/raw")

def list_osf_files(project_id: str, folder_id: str = "osfstorage") -> list:
    """
    List all files in an OSF project using the OSF v2 API.
    
    Args:
        project_id: OSF project identifier (e.g., '3hpvr')
        folder_id: Folder ID or 'osfstorage' for root
    
    Returns:
        List of dicts with file metadata (name, download_url, size, kind, path)
    """
    print(f"Fetching file list from OSF project: {project_id}")
    url = f"{OSF_API_BASE}/nodes/{project_id}/files/{folder_id}/"
    
    all_files = []
    
    def fetch_folder(folder_url, path_prefix=""):
        """Recursively fetch all files from folders."""
        files = []
        page_url = folder_url
        
        while page_url:
            response = requests.get(page_url, timeout=30)
            if response.status_code != 200:
                print(f"ERROR: OSF API returned status {response.status_code}")
                print(f"Response: {response.text}")
                print("\\nPlease download manually from: https://osf.io/3hpvr/")
                sys.exit(1)
            
            data = response.json()
            for item in data.get("data", []):
                attrs = item.get("attributes", {})
                links = item.get("links", {})
                kind = attrs.get("kind", "file")
                name = attrs.get("name", "unknown")
                full_path = f"{path_prefix}/{name}" if path_prefix else name
                
                if kind == "folder":
                    # Recursively fetch folder contents
                    subfolder_url = links.get("fetch", "")
                    if subfolder_url:
                        files.extend(fetch_folder(subfolder_url, full_path))
                else:
                    files.append({
                        "name": name,
                        "size": attrs.get("size", 0),
                        "download_url": links.get("download", ""),
                        "kind": kind,
                        "path": full_path,
                    })
            
            # Handle pagination
            page_url = data.get("links", {}).get("next")
        
        return files
    
    all_files = fetch_folder(url)
    return all_files


def download_file(url: str, dest_path: Path, file_name: str, total_size: int = 0):
    """
    Download a file from a URL with a progress bar.
    
    Args:
        url: Download URL
        dest_path: Local destination path
        file_name: Filename for display
        total_size: Expected file size in bytes (for progress bar)
    """
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    
    if dest_path.exists():
        print(f"  [SKIP] Already exists: {dest_path}")
        return
    
    print(f"  Downloading: {file_name} ({total_size / 1e6:.1f} MB)")
    
    response = requests.get(url, stream=True, timeout=60)
    response.raise_for_status()
    
    with open(dest_path, "wb") as f:
        with tqdm(
            total=total_size,
            unit="B",
            unit_scale=True,
            desc=f"  {file_name}",
            leave=False,
        ) as pbar:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
                pbar.update(len(chunk))


def organize_file_path(file_path: str, dest_dir: Path) -> Path:
    """
    Determine the destination path for a downloaded file based on OSF structure.
    
    The OSF data is structured as:
      - ControlEvents/ngo_et_al_eLife2020_controlData_100sets/1-100/*.mat
      - EEGs/*.mat
      - Ripples/*.mat
      - Spindles/*.mat
    
    Args:
        file_path: Original file path from OSF (includes folder structure)
        dest_dir: Base raw data directory
    
    Returns:
        Destination path for the file
    """
    # Preserve the OSF folder structure in the local directory
    return dest_dir / file_path


def print_inspection_instructions():
    """
    Print instructions for users to inspect downloaded .mat files.
    """
    print("\\n" + "="*60)
    print("IMPORTANT: Inspect downloaded .mat files")
    print("="*60)
    print("""
After downloading, check the .mat file structure:

# Check EEG files
python3 -c "
import scipy.io
mat = scipy.io.loadmat('data/raw/EEGs/pat01_HIPP.mat')
print('Keys:', [k for k in mat.keys() if not k.startswith('_')])
"

# If scipy.io.loadmat fails (MATLAB v7.3 files), use mat73 or h5py:
python3 -c "
import mat73
mat = mat73.loadmat('data/raw/EEGs/pat01_HIPP.mat')
print('Keys:', list(mat.keys()))
"

Expected data structure:
  - EEGs/: Raw EEG signals (hippocampus and neocortex channels)
  - Ripples/: Detected hippocampal ripple events
  - Spindles/: Detected sleep spindle events (HIPP and NC channels)
  - ControlEvents/: Shuffled control data for statistical comparison
""")


def main():
    parser = argparse.ArgumentParser(
        description="Download Ngo et al. (2020) data from OSF (https://osf.io/3hpvr/)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List files that would be downloaded without downloading"
    )
    parser.add_argument(
        "--list-files",
        action="store_true",
        help="List all available files on OSF and exit"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=str(RAW_DATA_DIR),
        help=f"Output directory (default: {RAW_DATA_DIR})"
    )
    
    args = parser.parse_args()
    dest_dir = Path(args.output_dir)
    
    print("=" * 60)
    print("Ngo et al. (2020) Data Downloader")
    print("Dataset: https://osf.io/3hpvr/")
    print("DOI: 10.17605/OSF.IO/3HPVR")
    print("=" * 60)
    
    # Fetch file list
    try:
        files = list_osf_files(OSF_PROJECT_ID)
    except requests.exceptions.ConnectionError:
        print("\\nERROR: Cannot connect to OSF API.")
        print("Please download manually from: https://osf.io/3hpvr/")
        print("Then organize files into data/raw/ as described in README.md")
        sys.exit(1)
    
    if not files:
        print("No files found on OSF. The project may be private or the structure changed.")
        print("Please download manually from: https://osf.io/3hpvr/")
        sys.exit(1)
    
    # Filter .mat files only
    mat_files = [f for f in files if f["name"].endswith(".mat")]
    
    print(f"\\nFound {len(mat_files)} .mat files (total files: {len(files)})")
    
    if args.list_files:
        print("\\nAvailable files:")
        for f in sorted(files, key=lambda x: x["path"]):
            size_mb = f["size"] / 1e6 if f["size"] else 0
            print(f"  {f['path']} ({size_mb:.1f} MB) [{f['kind']}]")
        sys.exit(0)
    
    total_size_gb = sum(f["size"] for f in mat_files if f["size"]) / 1e9
    print(f"Total download size: {total_size_gb:.2f} GB")
    
    if args.dry_run:
        print("\\n[DRY RUN] Files that would be downloaded:")
        for f in sorted(mat_files, key=lambda x: x["path"]):
            dest = organize_file_path(f["path"], dest_dir)
            size_mb = f["size"] / 1e6 if f["size"] else 0
            status = "EXISTS" if dest.exists() else "DOWNLOAD"
            print(f"  [{status}] {f['path']} ({size_mb:.1f} MB) -> {dest}")
        print("\\nRun without --dry-run to download.")
        return
    
    # Download files
    print(f"\\nDownloading to: {dest_dir.absolute()}")
    dest_dir.mkdir(parents=True, exist_ok=True)
    
    downloaded = 0
    skipped = 0
    failed = []
    
    for f in mat_files:
        dest_path = organize_file_path(f["path"], dest_dir)
        
        if dest_path.exists():
            skipped += 1
            continue
        
        try:
            download_file(
                url=f["download_url"],
                dest_path=dest_path,
                file_name=f["path"],
                total_size=f["size"] or 0,
            )
            downloaded += 1
        except Exception as e:
            print(f"  [ERROR] Failed to download {f['path']}: {e}")
            failed.append(f["path"])
    
    print(f"\\nDownload complete!")
    print(f"  Downloaded: {downloaded} files")
    print(f"  Skipped (already exist): {skipped} files")
    if failed:
        print(f"  Failed: {len(failed)} files: {failed}")
        print("  Please download failed files manually from https://osf.io/3hpvr/")
    
    print_inspection_instructions()
    
    print("\\nNext step: python scripts/02_preprocess.py")


if __name__ == "__main__":
    main()

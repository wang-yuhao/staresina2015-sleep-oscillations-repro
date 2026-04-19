#!/usr/bin/env python3
"""
Automatic Data Organization Script for Ngo et al. Dataset

This script automatically organizes the downloaded Ngo dataset files into the
expected structure for the analysis pipeline. It handles hundreds of .mat files
and organizes them by subject ID.

Usage:
    python scripts/organize_data.py --source /path/to/downloaded/data --dest data/raw

Principle:
The Ngo dataset contains EEG/iEEG recordings from multiple subjects stored as
.mat files. Each file follows a naming convention that includes subject identifiers.
This script:
1. Scans the source directory for all .mat files
2. Extracts subject IDs from filenames using pattern matching
3. Creates organized subdirectories (sub-01/, sub-02/, etc.)
4. Copies or moves files to their corresponding subject folders
5. Validates the organization and generates a summary report
"""

import argparse
import shutil
import re
from pathlib import Path
from typing import Dict, List, Tuple
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def extract_subject_id(filename: str) -> str:
    """
    Extract subject ID from filename.
    
    The Ngo dataset uses various naming conventions. This function tries
    multiple patterns to extract subject identifiers.
    
    Args:
        filename: Name of the .mat file
    
    Returns:
        Subject ID (e.g., '01', '02') or 'unknown' if pattern not found
    """
    # Common patterns in sleep study datasets:
    patterns = [
        r'[Ss]ub[ject]*[_-]?(\d+)',  # sub-01, subject_01, Subject01
        r'[Pp]\d+',  # P01, p1
        r'night(\d+)',  # night1_hippocampus
        r'right(\d+)',  # right1_hippocampus  
        r'(\d+)_',  # starts with number
    ]
    
    for pattern in patterns:
        match = re.search(pattern, filename)
        if match:
            # Extract the numeric part and zero-pad to 2 digits
            num = match.group(1) if len(match.groups()) > 0 else match.group(0)
            num = re.sub(r'\D', '', num)  # Remove non-digits
            if num:
                return f"{int(num):02d}"
    
    return 'unknown'


def scan_files(source_dir: Path) -> Dict[str, List[Path]]:
    """
    Scan source directory and group files by subject ID.
    
    Args:
        source_dir: Path to downloaded data directory
    
    Returns:
        Dictionary mapping subject IDs to lists of file paths
    """
    logger.info(f"Scanning directory: {source_dir}")
    
    # Find all .mat files recursively
    mat_files = list(source_dir.rglob('*.mat'))
    logger.info(f"Found {len(mat_files)} .mat files")
    
    # Group by subject
    subject_files: Dict[str, List[Path]] = {}
    
    for mat_file in mat_files:
        subject_id = extract_subject_id(mat_file.name)
        
        if subject_id not in subject_files:
            subject_files[subject_id] = []
        subject_files[subject_id].append(mat_file)
    
    return subject_files


def organize_files(subject_files: Dict[str, List[Path]], 
                   dest_dir: Path,
                   mode: str = 'copy') -> Tuple[int, int]:
    """
    Organize files into subject subdirectories.
    
    Args:
        subject_files: Dictionary mapping subject IDs to file lists
        dest_dir: Destination directory (e.g., data/raw)
        mode: 'copy' or 'move' files
    
    Returns:
        Tuple of (successful_count, failed_count)
    """
    dest_dir.mkdir(parents=True, exist_ok=True)
    
    success_count = 0
    fail_count = 0
    
    for subject_id, files in subject_files.items():
        # Create subject directory
        subject_dir = dest_dir / f"sub-{subject_id}"
        subject_dir.mkdir(exist_ok=True)
        
        logger.info(f"Processing subject {subject_id}: {len(files)} files")
        
        for file_path in files:
            try:
                dest_path = subject_dir / file_path.name
                
                # Skip if file already exists and is identical
                if dest_path.exists():
                    if dest_path.stat().st_size == file_path.stat().st_size:
                        logger.debug(f"Skipping {file_path.name} (already exists)")
                        success_count += 1
                        continue
                
                # Copy or move the file
                if mode == 'copy':
                    shutil.copy2(file_path, dest_path)
                else:
                    shutil.move(str(file_path), str(dest_path))
                
                success_count += 1
                logger.debug(f"  ✓ {file_path.name}")
                
            except Exception as e:
                logger.error(f"  ✗ Failed to process {file_path.name}: {e}")
                fail_count += 1
    
    return success_count, fail_count


def generate_report(subject_files: Dict[str, List[Path]], dest_dir: Path):
    """
    Generate a summary report of the organization.
    
    Args:
        subject_files: Dictionary of organized files
        dest_dir: Destination directory
    """
    report_path = dest_dir / 'organization_report.txt'
    
    with open(report_path, 'w') as f:
        f.write("Data Organization Report\n")
        f.write("=" * 50 + "\n\n")
        
        total_files = sum(len(files) for files in subject_files.values())
        f.write(f"Total subjects: {len(subject_files)}\n")
        f.write(f"Total files: {total_files}\n\n")
        
        f.write("Files per subject:\n")
        f.write("-" * 50 + "\n")
        
        for subject_id in sorted(subject_files.keys()):
            files = subject_files[subject_id]
            f.write(f"  sub-{subject_id}: {len(files)} files\n")
            for file_path in sorted(files, key=lambda x: x.name):
                f.write(f"    - {file_path.name}\n")
        
        f.write("\n" + "=" * 50 + "\n")
    
    logger.info(f"Report saved to: {report_path}")


def main():
    parser = argparse.ArgumentParser(
        description='Organize Ngo dataset files into subject directories',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Example:
    python scripts/organize_data.py --source ~/Downloads/ngo_data --dest data/raw
    python scripts/organize_data.py --source ~/Downloads/ngo_data --dest data/raw --move
        """
    )
    
    parser.add_argument(
        '--source',
        type=Path,
        required=True,
        help='Source directory containing downloaded .mat files'
    )
    
    parser.add_argument(
        '--dest',
        type=Path,
        default=Path('data/raw'),
        help='Destination directory for organized files (default: data/raw)'
    )
    
    parser.add_argument(
        '--move',
        action='store_true',
        help='Move files instead of copying (default: copy)'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be done without actually organizing files'
    )
    
    args = parser.parse_args()
    
    # Validate source directory
    if not args.source.exists():
        logger.error(f"Source directory does not exist: {args.source}")
        return 1
    
    # Scan files
    logger.info("Step 1: Scanning files...")
    subject_files = scan_files(args.source)
    
    if not subject_files:
        logger.error("No .mat files found in source directory")
        return 1
    
    # Print summary
    logger.info(f"\nFound {len(subject_files)} subjects:")
    for subject_id in sorted(subject_files.keys()):
        logger.info(f"  sub-{subject_id}: {len(subject_files[subject_id])} files")
    
    if args.dry_run:
        logger.info("\n[DRY RUN] No files were actually moved or copied.")
        return 0
    
    # Organize files
    logger.info(f"\nStep 2: Organizing files to {args.dest}...")
    mode = 'move' if args.move else 'copy'
    success, failed = organize_files(subject_files, args.dest, mode)
    
    # Generate report
    logger.info("\nStep 3: Generating report...")
    generate_report(subject_files, args.dest)
    
    # Final summary
    logger.info("\n" + "=" * 50)
    logger.info("Organization complete!")
    logger.info(f"  Successfully processed: {success} files")
    logger.info(f"  Failed: {failed} files")
    logger.info(f"  Organized into: {args.dest}")
    logger.info("=" * 50)
    
    return 0 if failed == 0 else 1


if __name__ == '__main__':
    exit(main())

#!/usr/bin/env python3
"""Clean-up processed sub-/ses-folders in the bidsfolder"""

from pathlib import Path

mriqcroot = Path('/project/3015999.02/mriqc_data')
bidsroot  = mriqcroot/'bids'

# Loop over the bids-folders inside the bids project-folders
for bidsfolder in bidsroot.iterdir():
    for subfolder in bidsfolder.glob('sub-*'):
        for sesfolder in subfolder.glob('ses-*'):

            # Delete the bids-folder if there a mriqc html output file
            reports = list((mriqcroot/bidsfolder.name).glob(f"{subfolder.name}_{sesfolder.name}_*.html"))
            if reports:
                print(f"Found {len(reports)} mriqc-reports, deleting nifti-files in: {sesfolder}")
                for niifile in sesfolder.rglob('sub-*.nii*'):
                    niifile.unlink()

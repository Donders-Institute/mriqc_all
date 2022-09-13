#!/usr/bin/env python3
"""bidscoiner / mriqc_sub helper function to run a mriqc_all job locally"""

import pandas as pd
import argparse
import tempfile
import subprocess
import os
import shutil
import sys
sys.path += ['/opt/qsiprep/dccn', '/opt/mriqc/dccn']
from qsiprep_sub import main as qsiprep_run
from mriqc_sub import main as mriqc_run
from mriqc_meta import mriqc_meta as mriqc_meta
from bidscoin import bidscoiner
from pathlib import Path


def main(rawfolder, bidsfolder, bidsmapfile, mriqcfolder, qsiprep):

    rawfolder  = Path(rawfolder)
    bidsfolder = Path(bidsfolder)

    # Make a temporary shadow sub-/ses- directory structure for unstructered (unscheduled) data
    if '^' in rawfolder.name:
        sub = rawfolder.name                    # e.g. JurCla^Prisma_090135.023000
        ses = rawfolder.name.split('_', 2)[1]   # e.g. 090135.023000
        rawshadow = Path(tempfile.mkdtemp())/'sourcedata'/rawfolder.name
        subfolder = rawshadow/f"sub-{sub}"
        subfolder.mkdir(parents=True)
        (subfolder/f"ses-{ses}").symlink_to(rawfolder)
        rawfolder = rawshadow

    # Convert the rawfolder to a BIDS workfolder
    bidswork = Path(tempfile.mkdtemp())/bidsfolder.name
    bidscoiner.bidscoiner(rawfolder, bidswork, bidsmapfile=bidsmapfile)
    if not list(bidswork.glob('sub-*')):
        print(f"No subject data found in: {bidswork}")
        return

    # Run MRIQC participant + group
    mriqc_run(bidswork, mriqcfolder, '', nosub=True, skip=False)
    mriqc_group = f"singularity run --cleanenv {os.getenv('DCCN_OPT_DIR')}/mriqc/{os.getenv('MRIQC_VERSION')}/mriqc-{os.getenv('MRIQC_VERSION')}.simg {bidswork} {mriqcfolder} group --nprocs 1"
    process     = subprocess.run(mriqc_group, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    if process.stderr.decode('utf-8') or process.returncode != 0:
        print(f"ERROR {process.returncode}: MRIQC group report failed\n{process.stderr.decode('utf-8')}\n{process.stdout.decode('utf-8')}")

    # Run QSIPREP (WIP: copy the QC parameters into the MRIQC group report)
    if qsiprep == 'True':
        qsiprep_run(bidswork, mriqcfolder, '', resolution='automatic', args='--dwi-only', nthreads=1, nosub=True, skip=False)

    # Remove all nifti files
    for niifile in bidswork.rglob('sub-*.nii*'):
        niifile.unlink()

    # Copy the remaining BIDS meta data
    bidsfolder.mkdir(parents=True, exist_ok=True)
    for subwork in bidswork.glob('sub-*'):
        subfolder = bidsfolder/subwork.name
        sessions  = sorted(subwork.glob('ses-*'))
        subfolder.mkdir(parents=True, exist_ok=True)
        for seswork in sessions:        # Account for potential previous session in the sub-folder
            sesfolder = subfolder/seswork.name
            shutil.copytree(seswork, sesfolder)

    # Copy the remaining derived (qsiprep) meta data
    for subwork in (bidswork/'derivatives'/'qsiprep').glob('sub-*'):
        subfolder = bidsfolder/'derivatives'/'qsiprep'/subwork.name
        sessions  = sorted(subwork.glob('ses-*'))
        subfolder.mkdir(parents=True, exist_ok=True)
        for seswork in sessions:        # Account for potential previous session in the sub-folder
            sesfolder = subfolder/seswork.name
            shutil.copytree(seswork, sesfolder)

    # Copy/update the participants.tsv file to the BIDS sourcefolder and write BIDS metadata to the MRIQC group reports
    participantsfile = bidsfolder/'participants.tsv'
    if participantsfile.is_file():
        olddata = pd.read_csv(participantsfile, sep='\t', index_col='participant_id')
        newdata = pd.read_csv(bidswork/'participants.tsv', sep='\t', index_col='participant_id')
        alldata = pd.concat([olddata, newdata])
        alldata.to_csv(participantsfile, sep='\t')
    else:
        shutil.copy(bidswork/'participants.tsv', participantsfile)
    mriqc_meta(mriqcfolder)


# Shell usage
if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument('rawfolder')
    parser.add_argument('bidsfolder')
    parser.add_argument('bidsmapfile')
    parser.add_argument('mriqcfolder')
    parser.add_argument('qsiprep')
    args = parser.parse_args()

    main(rawfolder   = args.rawfolder,
         bidsfolder  = args.bidsfolder,
         bidsmapfile = args.bidsmapfile,
         mriqcfolder = args.mriqcfolder,
         qsiprep     = args.qsiprep)

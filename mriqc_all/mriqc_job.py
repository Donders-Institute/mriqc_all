#!/usr/bin/env python3
"""bidscoiner / mriqc_sub wrapper function for mriqc_all"""

import argparse
import tempfile
import subprocess
import os
import sys
sys.path.insert(0, '/opt/mriqc/dccn')
from mriqc_sub import main as mriqc_sub
from mriqc_meta import mriqc_meta as mriqc_meta
from bidscoin import bidscoiner
from pathlib import Path
from distutils.dir_util import copy_tree


def main(rawfolder, bidsfolder, bidsmapfile, mriqcfolder):

    # Convert the rawfolder to a BIDS workfolder
    bidsfolder = Path(bidsfolder)
    bidswork   = Path(tempfile.gettempdir())/bidsfolder.name
    bidscoiner.bidscoiner(rawfolder, bidswork, bidsmapfile=bidsmapfile)

    # Run MRIQC participant + group
    mriqc_sub(bidswork, mriqcfolder, '', skip=False, nosub=True)
    mriqc_group = f"singularity run --cleanenv {os.getenv('DCCN_OPT_DIR')}/mriqc/{os.getenv('MRIQC_VERSION')}/mriqc-{os.getenv('MRIQC_VERSION')}.simg {bidswork} {mriqcfolder} group --nprocs 1"
    process     = subprocess.run(mriqc_group, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    if process.stderr.decode('utf-8') or process.returncode != 0:
        print(f"ERROR {process.returncode}: MRIQC group report failed\n{process.stderr.decode('utf-8')}\n{process.stdout.decode('utf-8')}")

    # Copy the BIDS data without the nifti files
    for niifile in bidswork.rglob('sub-*.nii*'):
        niifile.unlink()
    for subwork in bidswork.glob('sub-*'):
        sessions = sorted(subwork.glob('ses-*'))
        if sessions:
            for seswork in sessions:
                sesfolder = bidsfolder/subwork.name/seswork.name
                sesfolder.mkdir(parents=True, exist_ok=True)
                copy_tree(str(seswork), str(sesfolder))
        else:
            subfolder = bidsfolder/subwork.name
            subfolder.mkdir(parents=True, exist_ok=True)
            copy_tree(str(subwork), str(subfolder))

    # Write BIDS metadata to the MRIQC group reports
    mriqc_meta(mriqcfolder)


parser = argparse.ArgumentParser()
parser.add_argument('rawfolder')
parser.add_argument('bidsfolder')
parser.add_argument('bidsmapfile')
parser.add_argument('mriqcfolder')
args = parser.parse_args()

main(rawfolder   = args.rawfolder,
     bidsfolder  = args.bidsfolder,
     bidsmapfile = args.bidsmapfile,
     mriqcfolder = args.mriqcfolder)

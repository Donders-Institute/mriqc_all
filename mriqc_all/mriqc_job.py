#!/usr/bin/env python3
"""bidscoiner / mriqc_sub helper function to run a mriqc_all job locally"""

import pandas as pd
import argparse
import tempfile
import shutil
import sys
sys.path += ['/opt/qsiprep/dccn', '/opt/mriqc/dccn']
from qsiprep_sub import main as qsiprep_run
from mriqc_sub import main as mriqc_run
from bidscoin import bidscoiner
from pathlib import Path


def main(rawfolder, bidsfolder, bidsmapfile, mriqcfolder, qsiprep):

    rawfolder   = Path(rawfolder)
    bidsfolder  = Path(bidsfolder)
    mriqcfolder = Path(mriqcfolder)

    running = mriqcfolder.parent/'logs'/f"{rawfolder.parent.name}_{rawfolder.name}.running"
    running.write_text(bidsfolder.as_posix())

    try:

        # Make a temporary shadow raw directory structure (with dummy sub-/ses- folders) for unstructered (unscheduled) data
        if '^' in rawfolder.name:
            sub = rawfolder.name                    # e.g. JurCla^Prisma_090135.023000
            ses = rawfolder.name.split('_', 2)[1]   # e.g. 090135.023000
            rawshadow = Path(tempfile.gettempdir())/'sourcedata'/rawfolder.name
            subfolder = rawshadow/f"sub-{sub}"
            subfolder.mkdir(parents=True)
            (subfolder/f"ses-{ses}").symlink_to(rawfolder)
            rawfolder = rawshadow

        # Convert the rawfolder to a BIDS workfolder
        print(f">>> Processing {rawfolder}")
        bidswork = Path(tempfile.gettempdir())/bidsfolder.name
        bidscoiner.bidscoiner(rawfolder, bidswork, bidsmapfile=bidsmapfile)
        if not list(bidswork.glob('sub-*')):
            print(f"No subject data found in: {bidswork}")
            running.rename(running.with_suffix('.empty'))
            return

        # Run MRIQC participant
        mriqc_run(bidswork, mriqcfolder, '', nosub=True, skip=False)

        # Run QSIPREP (WIP: copy the QC parameters into the MRIQC group report)
        if qsiprep == 'True':
            qsiprep_run(bidswork, mriqcfolder, '', resolution='automatic', args='--dwi-only', nthreads=1, nosub=True, skip=False)

        # Replace all nifti files with dummies
        for niifile in bidswork.rglob('sub-*.nii*'):
            niifile.write_text('')

        # Update the participants.tsv file in the BIDS sourcefolder if it already exists
        participantsfile = bidsfolder/'participants.tsv'
        if participantsfile.is_file():
            olddata = pd.read_csv(participantsfile, sep='\t', index_col='participant_id')
            newdata = pd.read_csv(bidswork/'participants.tsv', sep='\t', index_col='participant_id')
            for participant in newdata.index:
                if participant not in olddata.index:
                    olddata.loc[participant] = newdata.loc[participant]
            olddata.to_csv(participantsfile, sep='\t')

        # Copy the mandatory root files
        for rootfile in ('README', 'dataset_description.json', 'participants.tsv'):
            if not (bidsfolder/rootfile).is_file():
                shutil.copy(bidswork/rootfile, bidsfolder/rootfile)

        # Copy the BIDS meta data in each session
        for subwork in bidswork.glob('sub-*'):
            subfolder = bidsfolder/subwork.name
            subfolder.mkdir(parents=True, exist_ok=True)
            for seswork in sorted(subwork.glob('ses-*')):       # Account for potential previous session in the sub-folder
                sesfolder = subfolder/seswork.name
                shutil.copytree(seswork, sesfolder)

        # Copy the derived (qsiprep) meta data
        for subwork in (bidswork/'derivatives'/'qsiprep').glob('sub-*'):
            subfolder = bidsfolder/'derivatives'/'qsiprep'/subwork.name
            subfolder.mkdir(parents=True, exist_ok=True)
            for seswork in sorted(subwork.glob('ses-*')):       # Account for potential previous session in the sub-folder
                sesfolder = subfolder/seswork.name
                shutil.copytree(seswork, sesfolder)

        # Write the processed mriqc project folder to the logs
        if list(mriqcfolder.glob('sub-*.html')):
            mriqclog = mriqcfolder.parent/'logs'/(mriqcfolder.name + '.meta')
            mriqclog.write_text('')
            running.unlink()
        else:
            print(f"WARNING: No subject data found in: {mriqcfolder}")
            running.rename(running.with_suffix('.empty'))

    except Exception as joberror:

        print(f"WARNING: Processing {rawfolder} failed\n{joberror}")
        running.rename(running.with_suffix('.failed')).write_text(f"Error(s) from processing {bidsfolder}:\n{joberror}")


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

#!/usr/bin/env python3
"""Collects meta data from the BIDS sourcedata folder and stores it in the MRIQC group reports"""

import argparse
import pandas as pd
import json
import time
import subprocess
import os
from pathlib import Path

mriqcdata  = Path('/project/3015999.02/mriqc_data')
sourcedata = mriqcdata/'sourcedata'


def copymetadata(report_tsv: Path, bidsmodality: str, participants_tsv: Path, attributes: list, dryrun: bool):

    bidsfolder = sourcedata/report_tsv.parent.name          # e.g. [..]/3015999.02
    wait       = 0                                          # Number of minutes to wait for files to appear

    # Create & load the MRIQC group report
    if not report_tsv.is_file() and list(bidsfolder.glob('sub-*')):
        print(f"Creating: {report_tsv}")
        mriqc_group = f"singularity run --cleanenv {os.getenv('DCCN_OPT_DIR')}/mriqc/{os.getenv('MRIQC_VERSION')}/mriqc-{os.getenv('MRIQC_VERSION')}.simg {bidsfolder} {mriqcdata/bidsfolder.name} group --nprocs 1"
        process     = subprocess.run(mriqc_group, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        if process.stderr.decode() or process.returncode!=0:
            print(f"WARNING {process.returncode}: MRIQC group report could not be made\n{process.stderr.decode()}\n{process.stdout.decode()}")
    if report_tsv.is_file():
        print(f"Reading: {report_tsv}")
        report = pd.read_csv(report_tsv, sep='\t')
        report.set_index(['bids_name'], verify_integrity=True, inplace=True)
    else:
        print(f"WARNING: {report_tsv} could not be found")
        return False

    if participants_tsv.is_file():
        participants = pd.read_csv(participants_tsv, sep = '\t', index_col = 'participant_id')
    else:
        print(f"WARNING: {participants_tsv} could not be found")
        return False

    # Loop over the sessions in the MRIQC report
    succes = False
    for bidsname in report.index:                           # e.g. sub-002_ses-mri01_acq-t1mpragesagipat21p0iso20chheadneck_run-1_T1w

        # Parse the (full) subject and session labels
        sub, ses = bidsname.split('_')[0:2]                 # e.g. sub = 'sub-002', ses = ses-mri01
        if sub not in participants.index:
            print(f"ERROR: Could not find {sub} (from {bidsname}) in {bidsfolder}/participants.tsv")
            continue

        # Copy sex and age from the particpants.tsv file to the group report
        # print(f"Adding data from: {bidsfolder/'participants.tsv'}")
        report.loc[bidsname, 'meta.Sex'] = participants.loc[sub, 'sex']
        report.loc[bidsname, 'meta.Age'] = participants.loc[sub, 'age']

        # Copy the acquisition time from the scans.tsv file to the group report
        scansfile = bidsfolder/sub/ses/f"{sub}{'_' if ses else ''}{ses}_scans.tsv"
        for t in range(wait):
            if scansfile.is_file():
                if t > 0: print(f"Adding ({t} minutes delayed) data from: {scansfile}")
                break
            time.sleep(1 * 60)                              # Could be due to concurrency issues, so wait a bit and try again
        if not scansfile.is_file():
            print(f"ERROR: Could not find {scansfile}\nExisting data:\n{report.loc[bidsname]}")
            continue
        scansdata = pd.read_csv(scansfile, sep='\t', index_col='filename')
        scanpath  = f"{bidsmodality}/{bidsname}.nii"
        if scanpath in scansdata.index:
            report.loc[bidsname, 'meta.AcquisitionTime'] = scansdata.loc[scanpath, 'acq_time']
        else:
            print(f"WARNING: Could not find {scanpath} in {scansfile}")
            continue

        # Copy the BIDS metadata from the jsonfile to the group report
        jsonfile = bidsfolder/sub/ses/bidsmodality/f"{bidsname}.json"
        if not jsonfile.is_file():
            print(f"ERROR: Could not find {jsonfile}")
            continue
        with jsonfile.open() as jsonfid:
            metadata = json.load(jsonfid)
        for attribute in attributes:
            report.loc[bidsname, f"meta.{attribute}"] = metadata.get(attribute)

        succes = True

    # Save the new MRIQC group report
    if not dryrun and succes:
        print(f"Saving metadata to: {report_tsv}")
        report.to_csv(report_tsv, sep='\t', encoding='utf-8')

    return succes


def mriqc_meta(project, meta: tuple=('MagneticFieldStrength', 'ManufacturersModelName', 'StationName', 'SoftwareVersions'), dryrun: bool=False):

    if isinstance(project, Path) and project.name:
        projects = [project]
    elif isinstance(project, str) and project:
        if project == 'all':
            projects = sorted(mriqcdata.glob('*.*'))
        else:
            projects = [mriqcdata/project]
    else:
        projects = [mriqcdata/project.stem for project in (mriqcdata/'logs').glob('*.meta')]

    # Loop over the MRIQC data-folders and collect the meta data
    for n, project in enumerate(projects, 1):

        if project.is_dir():

            # Read / write the MRIQC group reports
            print(f"\n[{n}/{len(projects)}] Adding metadata for: {project}")
            succes = copymetadata(project/'group_T1w.tsv',  'anat', sourcedata/project.name/'participants.tsv', meta, dryrun)
            succes = copymetadata(project/'group_bold.tsv', 'func', sourcedata/project.name/'participants.tsv', meta, dryrun) or succes

            # Remove the project log entry
            if succes:
                (mriqcdata/'logs'/(project.name + '.meta')).unlink(missing_ok=True)
            else:
                print(f"WARNING: Project {project} was not processed succesfully")

        else:
            print(f"WARNING: {project} is not an existing project directory")


def main():

    class CustomFormatter(argparse.ArgumentDefaultsHelpFormatter, argparse.RawDescriptionHelpFormatter): pass

    parser = argparse.ArgumentParser(formatter_class=CustomFormatter,
                                     description=__doc__,
                                     epilog="examples:\n"
                                            "  mriqc_meta\n"
                                            "  mriqc_meta -p 3013091.02\n"
                                            "  mriqc_meta -m ProtocolName Acquisitiondate\n ")
    parser.add_argument('-p','--project', help='The project for which metadata need to be added. Use "all" to process all projects in the mriqc_data folder (default: process all projects in the mriqc_data/logs directory)')
    parser.add_argument('-m','--meta',    help='A list of the json attributes that are added', nargs='+', default=('MagneticFieldStrength', 'ManufacturersModelName', 'StationName', 'SoftwareVersions'))
    parser.add_argument('-d','--dryrun',  help='Add this flag to just print the metadata without actually saving anything', action='store_true')

    args = parser.parse_args()

    mriqc_meta(args.project, args.meta, args.dryrun)


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""Collects meta data from the BIDS sourcedata folder and stores it in the MRIQC group reports"""

import argparse
import pandas as pd
import json
import time
from pathlib import Path

mriqcdata  = Path('/project/3015999.02/mriqc_data')
sourcedata = mriqcdata/'sourcedata'


def copymetadata(attributes: list, report_tsv: Path, modality: str, dryrun: bool, participants_tsv):

    # Load the MRIQC group report
    if report_tsv.is_file():
        print(f"Reading: {report_tsv}")
        report = pd.read_csv(report_tsv, sep='\t')
        report.set_index(['bids_name'], verify_integrity=True, inplace=True)
    else:
        print(f"WARNING: {report_tsv} could not be found")
        return

    # Read the participants.tsv file
    bidsfolder = sourcedata/report_tsv.parent.name          # e.g. [..]/3015999.02

    # Loop over the sessions in the MRIQC report
    for bidsname in report.index:                           # e.g. sub-002_ses-mri01_acq-t1mpragesagipat21p0iso20chheadneck_run-1_T1w

        # Parse the (full) subject and session labels
        sub, ses = bidsname.split('_')[0:2]                 # e.g. sub = 'sub-002', ses = ses-mri01
        if sub not in participants_tsv.index:
            print(f"ERROR: Could not find {sub} (from {bidsname}) in {bidsfolder}/participants.tsv")
            continue

        # Copy sex and age from the particpants.tsv file to the group report
        print(f"Adding data from: {bidsfolder/'participants.tsv'}")
        report.loc[bidsname, 'meta.Sex'] = participants_tsv.loc[sub, 'sex']
        report.loc[bidsname, 'meta.Age'] = participants_tsv.loc[sub, 'age']

        # Copy the acquisition time from the scans.tsv file to the group report
        scansfile = bidsfolder/sub/ses/f"{sub}{'_' if ses else ''}{ses}_scans.tsv"
        for t in range(5):
            if scansfile.is_file():
                print(f"Adding ({t} minutes delayed) data from: {scansfile}")
                break
            time.sleep(1 * 60)                              # Could be due to concurrency issues, so wait a bit and try again
        if not scansfile.is_file() and ('meta.AcquisitionTime' not in report.index or not report.loc[bidsname, 'meta.AcquisitionTime']):
            print(f"ERROR: Could not find {scansfile}\nExisting data:\n{report.loc[bidsname]}")
            continue
        scansdata = pd.read_csv(scansfile, sep='\t', index_col='filename')
        scanpath  = f"{modality}/{bidsname}.nii"
        report.loc[bidsname, 'meta.AcquisitionTime'] = scansdata.loc[scanpath, 'acq_time']

        # Copy the BIDS metadata from the jsonfile to the group report
        jsonfile = bidsfolder/sub/ses/modality/f"{bidsname}.json"
        if not jsonfile.is_file():
            print(f"ERROR: Could not find {jsonfile}")
            continue
        with jsonfile.open() as jsonfid:
            metadata = json.load(jsonfid)
        for attribute in attributes:
            report.loc[bidsname, f"meta.{attribute}"] = metadata.get(attribute)

    # Save the new MRIQC group report
    if not dryrun:
        print(f"Saving metadata to: {report_tsv}")
        report.to_csv(report_tsv, sep='\t', encoding='utf-8')


def mriqc_meta(project, meta: tuple=('MagneticFieldStrength', 'ManufacturersModelName', 'StationName', 'SoftwareVersions'), dryrun: bool=False):

    if isinstance(project, Path) and project.name:
        projects = [project]
    elif isinstance(project, str) and project:
        projects = [mriqcdata/project]
    else:
        projects = mriqcdata.iterdir()

    # Loop over the MRIQC data-folders and collect the meta data
    for project in projects:

        # Read / write the MRIQC group reports
        print(f"Adding metadata for: {project}")
        if project.is_dir():
            participants_tsv = pd.read_csv(sourcedata/project.name/'participants.tsv', sep='\t', index_col='participant_id')
            copymetadata(meta, project/'group_T1w.tsv', 'anat', dryrun, participants_tsv)
            copymetadata(meta, project/'group_bold.tsv', 'func', dryrun, participants_tsv)
        else:
            print(f"WARNING: {project} is not an existing directory")


def main():

    class CustomFormatter(argparse.ArgumentDefaultsHelpFormatter, argparse.RawDescriptionHelpFormatter): pass

    parser = argparse.ArgumentParser(formatter_class=CustomFormatter,
                                     description=__doc__,
                                     epilog="examples:\n"
                                            "  mriqc_meta\n"
                                            "  mriqc_meta -p 3013091.02\n"
                                            "  mriqc_meta -m ProtocolName Acquisitiondate\n ")
    parser.add_argument('-p','--project', help='The project for which metadata need to be added (default: process all projects)')
    parser.add_argument('-m','--meta',    help='A list of the json attributes that are added', nargs='+', default=('MagneticFieldStrength', 'ManufacturersModelName', 'StationName', 'SoftwareVersions'))
    parser.add_argument('-d','--dryrun',  help='Add this flag to just print the metadata without actually saving anything', action='store_true')

    args = parser.parse_args()

    mriqc_meta(args.project, args.meta, args.dryrun)


if __name__ == '__main__':
    main()

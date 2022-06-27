#!/usr/bin/env python3
"""Collects meta data from the BIDS sourcedata folder and stores it in the MRIQC group reports"""

import argparse
import pandas as pd
import json
from pathlib import Path

mriqcdata  = Path('/project/3015999.02/mriqc_data')
sourcedata = mriqcdata/'sourcedata'


def copymetadata(attributes: list, report_tsv: Path, modality: str, dryrun: bool):

    # Load the MRIQC group report
    if report_tsv.is_file():
        print(f"Reading: {report_tsv}")
        report = pd.read_csv(report_tsv, sep='\t')
        report.set_index(['bids_name'], verify_integrity=True, inplace=True)
    else:
        return

    # Loop over the sessions in the MRIQC report
    for bidsname in report.index:

        # Parse the project folder and the (full) subject and session labels
        bidsfolder = sourcedata/report_tsv.parent.name    # e.g. [..]/3015999.02
        sub, ses   = bidsname.split('_')[0:2]             # e.g. sub = 'sub-001'
        if 'ses-' not in ses:
            ses = ''

        # Copy sex and age from the particpants.tsv file to the group report
        scansdata = pd.read_csv(bidsfolder/'participants.tsv', sep='\t', index_col='participant_id')
        report.loc[bidsname, 'meta.Sex'] = scansdata.loc[sub, 'sex']
        report.loc[bidsname, 'meta.Age'] = scansdata.loc[sub, 'age']

        # Copy the acquisition time from the scans.tsv file to the group report
        scansfile = bidsfolder/sub/ses/f"{sub}{'_' if ses else ''}{ses}_scans.tsv"
        scansdata = pd.read_csv(scansfile, sep='\t', index_col='filename')
        scanpath  = f"{modality}/{bidsname}.nii"
        report.loc[bidsname, 'meta.AcquisitionTime'] = scansdata.loc[scanpath, 'acq_time']

        # Copy the BIDS metadata from the jsonfile to the group report
        jsonfile = bidsfolder/sub/ses/modality/f"{bidsname}.json"
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
        if project.is_dir():
            copymetadata(meta, project/'group_T1w.tsv', 'anat', dryrun)
            copymetadata(meta, project/'group_bold.tsv', 'func', dryrun)
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

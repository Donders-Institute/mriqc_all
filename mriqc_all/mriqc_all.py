#!/usr/bin/env python3
"""Converts datasets from the catch-all collection to BIDS and runs MRIQC"""

import argparse
import dateutil.parser
import parsedatetime as pdt
import tarfile
import zipfile
import tempfile
import shutil
import os
import sys
sys.path.insert(0, '/opt/mriqc/dccn')
from mriqc_sub import main as mriqc_sub
from pathlib import Path
from bidscoin import bidscoiner


def run_mriqc_all(date: str, outfolder: str, force: bool=False):
    """Processes selected folders in the catch-all collection"""

    catchallraw = Path('/project/3055010.01/raw')
    bidsmapfile = Path(__file__).parent/'bidsmap_mriqc.yaml'
    outfolder   = Path(outfolder)

    # Parse the datefolders
    if date == 'all':
        datefolders = []
        for year in catchallraw.glob('20*'):
            for datefolder in year.glob(year.name + '*'):
                if datefolder.name == pdt.datetime.datetime.now().date().strftime('%Y%m%d'):
                    print(f"NB: SKIPPING TODAY's FOLDER: {datefolder}")
                    continue
                datefolders += [datefolder]
    else:
        try:
            datetime = dateutil.parser.parse(date)
        except dateutil.parser.ParserError:
            datetime = pdt.Calendar().nlp(date)
            if datetime:
                datetime = datetime[0][0]
            else:
                print(f"Could not parse: {date}")
                return
        datefolders = [catchallraw / f"{datetime.year}" / f"{datetime.year}{datetime.month:02d}{datetime.day:02d}"]
        if not datefolders[0].is_dir():
            print(f"Directory not found: {datefolders[0]}")
            return

    # Loop over the raw data-folders inside the datefolders
    for datefolder in sorted(datefolders, reverse=True):

        # Check the log if we have processed this before
        logfile = outfolder/'log'/datefolder.name
        if not force and logfile.is_file():
            print(f"Skipping processed folder: {datefolder}")
            continue

        for rawfolder in datefolder.iterdir():

            # Unpack old zipped session data to a temporary rawfolder
            rawfile = None
            if rawfolder.is_file():
                rawfile = rawfolder
                if rawfile.suffix in ('.zip','.gz','.tar'):
                    rawfolder = Path(tempfile.mkdtemp())/rawfile.name.replace('.zip','').replace('.gz','').replace('.tar','')
                    ext       = rawfile.suffixes
                    print(f"Extracting: {rawfile} -> {rawfolder}")
                    if ext[-1] == '.zip':
                        with zipfile.ZipFile(rawfile, 'r') as zip_fid:
                            zip_fid.extractall(rawfolder)
                    elif '.tar' in ext:
                        with tarfile.open(rawfile, 'r') as tar_fid:
                            tar_fid.extractall(rawfolder)
                else:
                    print(f"Skipping unexpected file: {rawfile}")
                    continue

            # Process the raw data-folder
            mriqcfolder = outfolder/rawfolder.name
            bidsfolder  = outfolder/'bids'/rawfolder.name
            mriqc_group = f"; singularity run --cleanenv {os.getenv('DCCN_OPT_DIR')}/mriqc/{os.getenv('MRIQC_VERSION')}/mriqc-{os.getenv('MRIQC_VERSION')}.simg {bidsfolder} {mriqcfolder} group --nprocs 1"
            print(f"Processing: {rawfolder} -> {mriqcfolder}")
            bidscoiner.bidscoiner(rawfolder, bidsfolder, bidsmapfile=bidsmapfile)
            mriqc_sub(bidsfolder, mriqcfolder, '', argstr=mriqc_group, skip=False)
            if rawfile:
                shutil.rmtree(rawfolder)

        # Write a datefolder log entry with the current datetime
        logfile.write_text(pdt.datetime.datetime.now().isoformat())


def main():
    """Console script usage"""

    class CustomFormatter(argparse.ArgumentDefaultsHelpFormatter, argparse.RawDescriptionHelpFormatter): pass

    parser = argparse.ArgumentParser(formatter_class=CustomFormatter,
                                     description=__doc__,
                                     epilog="examples:\n"
                                            "  run_mriqc_all\n"
                                            "  run_mriqc_all -d 20220325\n"
                                            "  run_mriqc_all -d today -f\n"
                                            "  run_mriqc_all -d all\n"
                                            "  run_mriqc_all -o test/mriqc_data\n ")
    parser.add_argument('-d','--date',      help='The date of the catch_all/raw/year/[date]/ folders that needs to be run', default='yesterday')
    parser.add_argument('-o','--outfolder', help='The mriqc output folder', default='/project/3015999.02/mriqc_data')
    parser.add_argument('-f','--force',     help='If this flag is given data will be processed, regardless of existing logfiles in the log-folder', action='store_true')

    args = parser.parse_args()

    run_mriqc_all(date=args.date, outfolder=args.outfolder, force=args.force)


if __name__ == '__main__':
    main()

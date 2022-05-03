#!/usr/bin/env python3
"""Converts datasets from the catch-all collection to BIDS and runs MRIQC"""

import argparse
import dateutil.parser
import parsedatetime as pdt
import time
import subprocess
import os
import sys
sys.path.insert(0, '/opt/mriqc/dccn')
from mriqc_sub import main as mriqc_sub
from pathlib import Path
from bidscoin import bidscoiner


def run_mriqc_all(date: str, outfolder: str, force: bool=False, dryrun: bool=False):
    """Processes selected folders in the catch-all collection"""

    catchallraw = Path('/project/3055010.01/raw')
    bidsmapfile = Path(__file__).parent/'bidsmap_mriqc.yaml'
    outfolder   = Path(outfolder)
    maxrunning  = 500

    # Parse the datefolders
    if date == 'all' or '*' in date:
        datefolders = []
        for year in catchallraw.glob('20*' if date=='all' else date):
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

        # Check the logs if we have processed this before
        logfile = outfolder/'logs'/datefolder.name
        logfile.parent.mkdir(parents=True, exist_ok=True)
        if not force and logfile.is_file():
            print(f"Skipping processed folder: {datefolder}")
            continue

        for rawfolder in datefolder.iterdir():

            # Wait until there are less than maxrunning jobs
            running = subprocess.run('if [ ! -z "$(qselect -s RQH)" ]; then qstat -f $(qselect -s RQH) | grep Job_Name | grep mriqc_sub- | wc -l; fi', stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
            if running.stdout.decode():
                while int(running.stdout.decode()) > maxrunning:
                    print(f"Pausing 10 minutes because there are more than {maxrunning} job running already...")
                    time.sleep(10*60)

            # Unpack old zipped session data to a temporary rawfolder
            if rawfolder.is_file():
                print(f"Skipping quasi organized data in: {rawfolder}")
                continue

            # Process the raw data-folder
            mriqcfolder = outfolder/rawfolder.name
            bidsfolder  = outfolder/'sourcedata'/rawfolder.name
            mriqc_group = f"; singularity run --cleanenv {os.getenv('DCCN_OPT_DIR')}/mriqc/{os.getenv('MRIQC_VERSION')}/mriqc-{os.getenv('MRIQC_VERSION')}.simg {bidsfolder} {mriqcfolder} group --nprocs 1"
            print(f"Processing: {rawfolder} -> {mriqcfolder}")
            if not dryrun:
                bidscoiner.bidscoiner(rawfolder, bidsfolder, bidsmapfile=bidsmapfile)
                mriqc_sub(bidsfolder, mriqcfolder, '', argstr=mriqc_group, skip=False)

        # Write a datefolder log entry with the current datetime
        if not dryrun:
            logfile.write_text(pdt.datetime.datetime.now().isoformat())


def main():
    """Console script usage"""

    class CustomFormatter(argparse.ArgumentDefaultsHelpFormatter, argparse.RawDescriptionHelpFormatter): pass

    parser = argparse.ArgumentParser(formatter_class=CustomFormatter,
                                     description=__doc__,
                                     epilog="examples:\n"
                                            "  run_mriqc_all\n"
                                            "  run_mriqc_all -d 20220325\n"
                                            "  run_mriqc_all -d 2021*\n"
                                            "  run_mriqc_all -d today -f\n"
                                            "  run_mriqc_all -d all\n"
                                            "  run_mriqc_all -o test/mriqc_data\n ")
    parser.add_argument('-d','--date',      help='The date of the catch_all/raw/year/[date]/ folders that needs to be run', default='yesterday')
    parser.add_argument('-o','--outfolder', help='The mriqc output folder', default='/project/3015999.02/mriqc_data')
    parser.add_argument('-f','--force',     help='If this flag is given data will be processed, regardless of existing logfiles in the log-folder', action='store_true')
    parser.add_argument('--dryrun',         help='Add this flag to just print the new directories without actually running or submitting anything (useful for debugging)', action='store_true')

    args = parser.parse_args()

    run_mriqc_all(date=args.date, outfolder=args.outfolder, force=args.force, dryrun=args.dryrun)


if __name__ == '__main__':
    main()

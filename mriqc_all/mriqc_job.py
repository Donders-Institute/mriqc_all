#!/usr/bin/env python3
"""bidscoiner / mriqc_sub wrapper function for mriqc_all"""

import argparse
import tempfile
import sys
sys.path.insert(0, '/opt/mriqc/dccn')
from mriqc_sub import main as mriqc_sub
from bidscoin import bidscoiner
from pathlib import Path
from distutils.dir_util import copy_tree


def main(rawfolder, bidsfolder, bidsmapfile, mriqcfolder, mriqc_group):

    bidswork = Path(tempfile.gettempdir())/Path(bidsfolder).name
    bidscoiner.bidscoiner(rawfolder, bidswork, bidsmapfile=bidsmapfile)
    mriqc_sub(bidswork, mriqcfolder, '', args=mriqc_group, skip=False, nosub=True)
    for niifile in bidswork.rglob('sub-*.nii*'):
        niifile.unlink()
    copy_tree(bidswork, bidsfolder)


parser = argparse.ArgumentParser()
parser.add_argument('rawfolder')
parser.add_argument('bidsfolder')
parser.add_argument('bidsmapfile')
parser.add_argument('mriqcfolder')
parser.add_argument('mriqc_group')
args = parser.parse_args()

main(rawfolder   = args.rawfolder,
     bidsfolder  = args.bidsfolder,
     bidsmapfile = args.bidsmapfile,
     mriqcfolder = args.mriqcfolder,
     mriqc_group = args.mriqc_group)

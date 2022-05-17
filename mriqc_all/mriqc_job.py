#!/usr/bin/env python3
"""bidscoiner / mriqc_sub wrapper function for mriqc_all"""

import sys
import argparse
sys.path.insert(0, '/opt/mriqc/dccn')
from mriqc_sub import main as mriqc_sub
from bidscoin import bidscoiner


def main(rawfolder, bidsfolder, bidsmapfile, mriqcfolder, mriqc_group):

    bidscoiner.bidscoiner(rawfolder, bidsfolder, bidsmapfile=bidsmapfile)
    mriqc_sub(bidsfolder, mriqcfolder, '', args=mriqc_group, skip=False, nosub=True)


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

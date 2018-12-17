"""
Uploads stuff to Dynamo:
- GAMS CODE
- Market data

Author: Peeter Meos
Date: 17. December 2018
"""
import argparse
from utils import data
from gms import code
import sys

if __name__ == "__main__":
    # Process command line arguments
    parser = argparse.ArgumentParser(description="Data uploader to Dynamo DB")
    parser.add_argument("-c", action="store", help="Upload GAMS code")
    parser.add_argument("-d", action="store", help="Upload market data CSV")

    args = parser.parse_args()

    if len(sys.argv) == 1:
        parser.print_help()
        parser.exit(1)

    if args.c is not None:
        # Do code upload
        code.upload_code("gamsCode", args.c)

    if args.d is not None:
        # Do market data upload
        data.write_dynamo(args.d, "mktData", "CL")

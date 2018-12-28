"""
Uploads stuff to Dynamo:
- GAMS CODE
- Market data

Author: Peeter Meos
Date: 17. December 2018
"""
import argparse
from utils import data, logger
from gms import code
from tws import snapshot
import sys
import configparser


def get_mkt_data_snapshot(export_dynamo=False):
    """
    Gets market data snapshot from TWS
    :return:
    """
    config = configparser.ConfigParser()
    config.read("config.cf")
    opt = config["optimiser"]

    snap = snapshot.Snapshot(config=opt, log_level=logger.LogLevel.normal)
    snap.connect(opt["host"],
                 int(opt["port"]),
                 int(opt["id"]) + 1)
    snap.create_instruments()
    snap.wait_to_finish()
    df = snap.prepare_df()
    if export_dynamo:
        snap.export_dynamo(config["data"]["mkt.table"])
    snap.disconnect()


if __name__ == "__main__":
    # Process command line arguments
    parser = argparse.ArgumentParser(description="Data uploader to Dynamo DB")
    parser.add_argument("-c", action="store", help="Upload GAMS code from given file")
    parser.add_argument("-d", action="store", help="Upload market data CSV from given file")
    parser.add_argument("-tws", action="store_true", help="Upload market data snapshot from TWS")
    parser.add_argument("--version", action="store", help="Version number for GAMS code")

    args = parser.parse_args()

    if len(sys.argv) == 1:
        parser.print_help()
        parser.exit(1)

    if args.c is not None:
        # Do code upload
        if args.version is not None:
            code.upload_code("gamsCode", args.c, version=args.version)
        else:
            code.upload_code("gamsCode", args.c)

    if args.d is not None:
        # Do market data upload
        data.write_dynamo(args.d, "mktData", "CL")

    if args.tws:
        get_mkt_data_snapshot(export_dynamo=True)

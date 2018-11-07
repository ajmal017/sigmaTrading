"""
Sigma trading main code
Author: Peeter Meos
Date: 6. november 2018
"""
from tws import *
from logger import *
import pandas as pd


def import_option_chain(fn):
    """
    Imports option chain from a TWS csv file, processes it a a little and
    then returns a pandas data frame
    :param fn: filename
    :return: pandas data frame
    """
    df = pd.read_csv(fn)
    return df


def export_trades(df: pd.DataFrame):
    """
    This exports optimal trades as XML and CSV files
    :param df:
    :return: nothing
    """
    df.to_csv("basket.csv")


def main():
    logger = Logger(LogLevel.verbose, "Trader")
    logger.log("Sigma trading main entry point")

    app = Trader()
    app.connect("localhost", 4001, 1)
    app.disconnect()
    df = import_option_chain("./data/181105 options.csv")
    print(df.describe())


if __name__ == "__main__":
    main()

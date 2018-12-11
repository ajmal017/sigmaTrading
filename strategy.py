"""
Generic Portfolio Strategy class with interfaces

Author: Peeter Meos
Date: 11. December 2018
"""
import os
import pandas as pd
import boto3
import datetime
import configparser
from utils import logger


class PortfolioStrategy:
    def __init__(self, name="PortfolioStrategy"):
        """
        Dummy constructor for the data structure
        """

        self.logger = logger.Logger(logger.LogLevel.normal, name)

        self.df = pd.DataFrame()
        self.data_date = 0
        self.config = configparser.ConfigParser()

    # TODO: Market data from Dynamo DB  needs to be implemented
    def get_mkt_data_dynamo(self, dtg=None):
        """
        Downloads market data snapshot from DynamoDB table
        :param dtg: Timestamp, if equals none, return latest snapshot
        :return: pandas data frame
        """
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1',
                                  endpoint_url="https://dynamodb.us-east-1.amazonaws.com")
        table = dynamodb.Table(self.config["data"]["mkt.table"])

        # If dtg is not given, get the latest snapshot, otherwise find the right dtg
        if dtg is None:
            pass
        else:
            pass

        response = table.scan()
        return response

    def get_mkt_data_csv(self, fn: str):
        """
        Gets market data snapshot from CSV file
        :param fn: filename
        :return:
        """
        self.df = pd.read_csv(fn, na_values="NoMD")
        self.data_date = datetime.datetime.fromtimestamp(os.path.getmtime(fn))

"""
Generic Portfolio Strategy class with interfaces

Author: Peeter Meos
Date: 11. December 2018
"""
import os
import pandas as pd
import boto3
from boto3.dynamodb.conditions import Key
import datetime
import configparser
from utils import logger, data
import json


class PortfolioStrategy:
    def __init__(self, name="PortfolioStrategy"):
        """
        Dummy constructor for the data structure
        """

        self.logger = logger.Logger(logger.LogLevel.normal, name)

        self.df = pd.DataFrame()
        self.data_date = datetime.datetime.today()
        self.config = configparser.ConfigParser()
        self.inst = ""

    def save_mkt_data_dynamo(self):
        """
        Saves current strategy's market data snapshot to Dynamo
        :return:
        """
        # File modification date
        dtg = self.data_date.strftime("%y%m%d%H%M%S")

        # Instrument
        dct = self.df.to_dict(orient="split")
        dct["dtg"] = dtg
        dct["inst"] = self.inst
        dct["data"] = json.dumps(dct["data"])

        # DB Connectivity
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1',
                                  endpoint_url="https://dynamodb.us-east-1.amazonaws.com")
        table = dynamodb.Table(self.config["data"]["mkt.table"])
        response = table.put_item(Item=data)
        return response

    def get_mkt_data_dynamo(self, dtg=None):
        """
        Downloads market data snapshot from DynamoDB table
        :param dtg: Timestamp, if equals none, return latest snapshot
        :return: pandas data frame
        """
        self.logger.log("Reading market data from Dynamo DB")

        dynamodb = boto3.resource('dynamodb', region_name='us-east-1',
                                  endpoint_url="https://dynamodb.us-east-1.amazonaws.com")
        table = dynamodb.Table(self.config["data"]["mkt.table"])

        # If dtg is not given, get the latest snapshot, otherwise find the right dtg
        if dtg is None:
            response = table.scan(AttributesToGet=['dtg'])
            d = response["Items"]
            d = pd.DataFrame.from_dict(d)
            dtg = max(d["dtg"])

        response = table.query(KeyConditionExpression=Key('dtg').eq(dtg))
        response = response["Items"][0]
        self.df = pd.DataFrame(json.loads(response["data"]), columns=response["columns"], index=response["index"])
        self.data_date = datetime.datetime.strptime(dtg, "%y%m%d%H%M%S")

    def get_mkt_data_csv(self, fn: str):
        """
        Gets market data snapshot from CSV file
        :param fn: filename
        :return:
        """
        self.logger.log("Reading market data from CSV file " + fn)
        self.df = pd.read_csv(fn, na_values="NoMD", index_col=0)
        self.data_date = datetime.datetime.fromtimestamp(os.path.getmtime(fn))

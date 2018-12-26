"""
Code for handling instrument metadata.
Getting from the database, listing, putting back, etc.
Options and futures will NOT include strikes, expiry dates and sides

Author: Peeter Meos
Date: 20. December 2018
"""
from ibapi.contract import Contract
import boto3
import numpy as np


def list_instruments(tbl: str) -> list:
    """
    Produces a list of instruments stored in Dynamo DB
    :param tbl: Dynamo DB table
    :return:
    """
    dynamodb = boto3.resource('dynamodb', region_name='us-east-1',
                              endpoint_url="https://dynamodb.us-east-1.amazonaws.com")
    table = dynamodb.Table(tbl)
    response = table.scan(AttributesToGet="symbol")
    res = response["Items"]

    while "LastEvaluatedKey" in response:
        response = table.scan(AttributesToGet="symbol",
                              ExclusiveStartKey=response["LastEvaluatedKey"])
        res = res + response["Items"]

    return res


def get_instrument(inst: str, tbl: str) -> (Contract, dict):
    """
    Retrieves an instrument metadata from Dynamo DB
    :param inst: symbol string
    :param tbl: Dynamo DB name
    :return:
    """
    db = boto3.resource('dynamodb', region_name='us-east-1',
                        endpoint_url="https://dynamodb.us-east-1.amazonaws.com")
    table = db.Table(tbl)
    response = table.get_item(Key={"symbol": inst})

    r = response["Item"]

    c = Contract()
    c.symbol = r["symbol"]
    c.secType = r["type"]
    c.currency = r["currency"]
    c.exchange = r["exchange"]
    c.tradingClass = r["class"]
    c.multiplier = r["mult"]

    return {"cont": c, "add_d": {"mon_step": r["mon_step"], "strike_step": r["strike_step"]}}


def put_instrument(inst: Contract, add: dict, tbl: str):
    """
    Inserts inserts instrument to Dynamo DB
    :param inst:
    :param add: additional data
    :param tbl:
    :return:
    """
    my_inst = {"symbol": inst.symbol,
               "type": inst.secType,
               "exchange": inst.exchange,
               "currency": inst.currency,
               "class": inst.tradingClass,
               "mult": inst.multiplier
               }

    dynamodb = boto3.resource('dynamodb', region_name='us-east-1',
                              endpoint_url="https://dynamodb.us-east-1.amazonaws.com")
    table = dynamodb.Table(tbl)
    my_inst.update(add)
    response = table.put_item(Item=my_inst)
    print(response)


def make_strike_chain(beg: float, end: float, step: float):
    """
    Generates list of strikes for option chain
    :param beg:
    :param end:
    :param step:
    :return:
    """
    x = ((float(end) - float(beg)) / float(step))
    r = list(np.array(range(0, int(round(x)))) * float(step) + float(beg))
    r = ["{:g}".format(item) for item in r]
    return r


if __name__ == "__main__":
    print("Inserting instrument")

    cnt = Contract()
    cnt.symbol = "CL"
    cnt.currency = "USD"
    cnt.secType = "FOP"
    cnt.exchange = "NYMEX"
    cnt.multiplier = 1000
    cnt.tradingClass = "LO"

    add_d = {"mon_step": 1,
             "strike_step": "0.5"
             }

    put_instrument(cnt, add_d, "instData")
    get_instrument("CL", "instData")


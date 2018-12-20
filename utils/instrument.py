"""
Code for handling instrument metadata.
Getting from the database, listing, putting back, etc.
Options and futures will NOT include strikes, expiry dates and sides

Author: Peeter Meos
Date: 20. December 2018
"""
from ibapi.contract import Contract
import boto3
from boto3.dynamodb.conditions import Key


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


def get_instrument(inst: str, tbl: str) -> Contract:
    """
    Retrieves an instrument metadata from Dynamo DB
    :param inst: symbol string
    :param tbl: Dynamo DB name
    :return:
    """
    dynamodb = boto3.resource('dynamodb', region_name='us-east-1',
                              endpoint_url="https://dynamodb.us-east-1.amazonaws.com")
    table = dynamodb.Table(tbl)
    response = table.query(KeyConditionExression=Key("symbol").eq(inst))

    r = response["Items"][0]

    c = Contract()
    c.symbol = r["symbol"]
    c.secType = r["type"]
    c.currency = r["currency"]
    c.exchange = r["exchange"]
    c.tradingClass = r["class"]

    return c


def put_instrument(inst: Contract, tbl: str):
    """
    Inserts inserts instrument to Dynamo DB
    :param inst:
    :param tbl:
    :return:
    """
    my_inst = {"symbol": inst.symbol,
               "type": inst.secType,
               "exchange": inst.exchange,
               "currency": inst.currency,
               "class": inst.tradingClass
               }

    dynamodb = boto3.resource('dynamodb', region_name='us-east-1',
                              endpoint_url="https://dynamodb.us-east-1.amazonaws.com")
    table = dynamodb.Table(tbl)
    response = table.put_item(my_inst)
    print(response)

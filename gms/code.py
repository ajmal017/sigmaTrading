"""
Code for handling GAMS optimisation code

Author: Peeter Meos
Date: 10. December 2018
"""
import boto3
from boto3.dynamodb.conditions import Key
import pandas as pd
from utils.logger import Logger, LogLevel


def get_code(tbl: str, version: int = None, loglevel=LogLevel.normal):
    """
    Retrieve GAMS optimisation code from Dynamo DB table
    :param tbl: Table name
    :param version: Code version, if None, then get the latest
    :param loglevel:
    :return: list of code (string) and options file (string)
    """
    log = Logger(loglevel, name="GAMS code import")
    db = boto3.resource('dynamodb', region_name='us-east-1',
                        endpoint_url="https://dynamodb.us-east-1.amazonaws.com")
    table = db.Table(tbl)
    if version is None:
        log.log("Finding the latest version of the optimisation formulation")
        response = table.scan(AttributesToGet=["version"])
        res = response["Items"]

        while "LastEvaluatedKey" in response:
            response = table.scan(AttributesToGet=["version"],
                                  ExclusiveStartKey=response["LastEvaluatedKey"])
            res = res + response["Items"]

        dt = pd.DataFrame.from_dict(res)
        version = max([int(item) for item in dt["version"]])
        log.verbose("The latest version is " + str(version))

    log.log("Importing optimisation formulation version " + str(version))
    response = table.query(KeyConditionExpression=Key("version").eq(str(version)))
    response["Items"][0]["code"] = "* Formulation version " + str(version) + "\n" + \
                                   response["Items"][0]["code"]
    return response["Items"][0]


def upload_code(tbl: str, fn: str, opt: str = None, version=None):
    """
    Upload next version of GAMS code to Dynamo DB
    :param tbl: Dynamo DB table name
    :param fn: Filename for gams code
    :param opt: Filename for CPLEX options file
    :param version: Optional version string
    :return:
    """
    log = Logger(LogLevel.normal, "Gams Upload")
    # Read the file as one long string
    with open(fn, 'r') as m:
        code = m.read()
    if opt is not None:
        with open(opt, 'r') as m:
            opts = m.read()
    else:
        opts = " "

    # Open the data table and insert item
    db = boto3.resource('dynamodb', region_name='us-east-1',
                        endpoint_url="https://dynamodb.us-east-1.amazonaws.com")
    table = db.Table(tbl)

    if version is None:
        log.log("No version given, finding latest version")
        response = table.scan(AttributesToGet=["version"])
        res = response["Items"]

        while "LastEvaluatedKey" in response:
            response = table.scan(AttributesToGet=["version"],
                                  ExclusiveStartKey=response["LastEvaluatedKey"])
            res = res + response["Items"]

        dt = pd.DataFrame.from_dict(res)
        log.log("Latest version in DB is " + str(version))
        version = max(map(int, dt["version"])) + 1

    log.log("Uploading GAMS formulation as version " + str(version))
    response = table.put_item(Item={"code": code, "opts": opts, "version": str(version)})
    log.log(str(response))

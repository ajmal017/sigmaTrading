"""
Code for handling GAMS optimisation code

Author: Peeter Meos
Date: 10. December 2018
"""
import boto3


def get_code(tbl: str, version=None) -> list:
    """
    Retrieve GAMS optimisation code from Dynamo DB table
    :param tbl: Table name
    :param version: Code version, if None, then get the latest
    :return: list of code (string) and options file (string)
    """
    db = boto3.resource('dynamodb', region_name='us-east-1',
                        endpoint_url="https://dynamodb.us-east-1.amazonaws.com")
    table = db.Table(tbl)
    response = table.scan()
    return []


def upload_code(tbl: str, fn: str, opt: str, version=None):
    """
    Upload next version of GAMS code to Dynamo DB
    :param tbl: Dynamo DB table name
    :param fn: Filename for gams code
    :param opt: Filename for CPLEX options file
    :param version: Optional version string
    :return:
    """
    # Read the file as one long string
    with open(fn, 'r') as m:
        code = m.read()
    with open(opt, 'r') as m:
        opts = m.read()

    # TODO: If version is not given, find the latest version and increment by one
    if version is None:
        version = 1

    # Open the data table and insert item
    db = boto3.resource('dynamodb', region_name='us-east-1',
                        endpoint_url="https://dynamodb.us-east-1.amazonaws.com")
    table = db.Table(tbl)
    response = table.put_item(Item={"code": code, "opts": opts, "version": str(version)})
    print(response)

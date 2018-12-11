"""
Code for handling GAMS optimisation code

Author: Peeter Meos
Date: 10. December 2018
"""
import boto3


def get_code(tbl: str, version=None):
    """
    Retrieve GAMS optimisation code from Dynamo DB table
    :param tbl: Table name
    :param version: Code version, if None, then get the latest
    :return:
    """
    pass


def upload_code(tbl: str, fn: str, version=None):
    """
    Upload next version of GAMS code to Dynamo DB
    :param tbl: Dynamo DB table name
    :param fn: Filename
    :param version: Optional version string
    :return:
    """
    # Read the file as one long string
    with open(fn, 'r') as m:
        data = m.read()

    print(data)

    # Open the data table and insert item
    db = boto3.resource('dynamodb', region_name='us-east-1',
                        endpoint_url="https://dynamodb.us-east-1.amazonaws.com")
    table = db.Table(tbl)
    table.put_item({"data": data})

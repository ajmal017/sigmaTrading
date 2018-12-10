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
    pass

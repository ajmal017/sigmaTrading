"""
Saves market data snapshot to DynamoDB.
Simply CSV into JSON into DynamoDB

Author: Peeter Meos, Sigma Research OÜ
Date: 2. December 2018
"""
import boto3
import pandas as pd
import os.path
import json
import decimal
from datetime import datetime


class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, decimal.Decimal):
            return str(o)
        return super(DecimalEncoder, self).default(o)


def get_list_data(tbl=None, attributes=["dtg"]) -> pd.DataFrame:
    """
    Retrieves a list of optimisation results
    :param tbl:
    :param attributes: Attributes to retrieve
    :return:
    """
    db = boto3.resource('dynamodb', region_name='us-east-1',
                        endpoint_url="https://dynamodb.us-east-1.amazonaws.com")

    if tbl is None:
        tbl = "optResults"

    table = db.Table(tbl)

    # If dtg is not given, get the latest snapshot, otherwise find the right dtg
    response = table.scan(AttributesToGet=attributes)
    r_tmp = response["Items"]

    while "LastEvaluatedKey" in response:
        response = table.scan(AttributesToGet=attributes,
                              ExclusiveStartKey=response["LastEvaluatedKey"])
        r_tmp = r_tmp + response["Items"]

    d_tmp1 = pd.DataFrame.from_dict(r_tmp)
    d_tmp1 = d_tmp1.sort_values(by="dtg")
    return d_tmp1


def write_dynamo(filename: str, tbl: str, inst: str):
    """
    Main code for the snapshot upload
    :param filename Filename for CSV data
    :param tbl: Target Dynamo DB table
    :param inst: symbol to be written
    :return: nothing
    """
    mod_time = os.path.getmtime(filename)
    df = pd.read_csv(filename)

    # File modification date
    dtg = datetime.fromtimestamp(mod_time).strftime("%y%m%d%H%M%S")

    # Instrument
    data = df.to_dict(orient="split")
    data["dtg"] = int(dtg)
    data["inst"] = inst
    data["data"] = json.dumps(data["data"])

    dynamodb = boto3.resource('dynamodb', region_name='us-east-1',
                              endpoint_url="https://dynamodb.us-east-1.amazonaws.com")
    table = dynamodb.Table(tbl)
    response = table.put_item(Item=data)

    return response


def write_sqlite(filename: str, tbl: str, inst: str, db: str):
    """
    Snapshot upload to local SQL lite database
    :param filename: File containing snapshot
    :param tbl: Table name
    :param inst: Instrument symbol
    :param db: Path to sqlite
    :return:
    """
    import sqlite3

    mod_time = os.path.getmtime(filename)
    df = pd.read_csv(filename, index_col=0)

    # File modification date
    dtg = datetime.fromtimestamp(mod_time).strftime("%y%m%d%H%M%S")

    # Data
    data = df.to_dict(orient="split")
    idx = json.dumps(data["index"])
    cols = json.dumps(data["columns"])
    data = json.dumps(data["data"])

    conn = sqlite3.connect(db)
    c = conn.cursor()
    c.execute("INSERT INTO " + tbl + " VALUES (" +
              dtg + ", " +
              "'" + inst + "', " +
              "'" + idx + "', " +
              "'" + cols + "', " +
              "'" + data + "')")
    conn.commit()
    conn.close()


def setup_sqlite(tbl: str, db: str):
    """
    Creates empty SQL Lite database
    :param tbl:
    :param db:
    :return:
    """
    import sqlite3

    conn = sqlite3.connect(db)
    c = conn.cursor()
    c.execute("CREATE TABLE " + tbl + " (dtg integer, inst text, index text, columns text, data text)")
    conn.commit()
    conn.close()


def remove_last_csv_newline(fn: str):
    """
    Removes newline from the last row of CSV file
    :param fn: filename
    :return:
    """
    with open(fn) as f:
        lines = f.readlines()
        last = len(lines) - 1
        lines[last] = lines[last].replace('\r', '').replace('\n', '')
    with open(fn, 'w') as wr:
        wr.writelines(lines)



"""
Various necessary tools and helpers for TWS API

Author: Peeter Meos
Date: 12. December 2018
"""
from xml.etree.ElementTree import Element, SubElement, ElementTree
import boto3
import pandas as pd
from utils.logger import LogLevel, Logger


def lookup_contract_id(df, tbl: str):
    """
    Performs contract ID lookup from TWS
    :param df: series, list of instruments
    :param tbl: table containing instrument names
    :return:
    """
    log = Logger(LogLevel.normal, "ConID retrieval")
    if "conid" in df:
        log.log("Contract IDs already present, new query not necessary")
        return df
    else:
        log.log("Getting contract IDs from Dynamo DB table" + tbl)

    db = boto3.resource('dynamodb', region_name='us-east-1',
                        endpoint_url="https://dynamodb.us-east-1.amazonaws.com")
    table = db.Table(tbl)

    response = table.scan()
    res = response["Items"]

    while "LastEvaluatedKey" in response:
        response = table.scan(ExclusiveStartKey=response["LastEvaluatedKey"])
        res = res + response["Items"]

    # res is list of dicts, contains instString and conid
    res = pd.DataFrame(res)
    res.columns = ["conid", "Financial Instrument"]

    res["Financial Instrument"] = res["Financial Instrument"].astype(str)
    df["Financial Instrument"] = df["Financial Instrument"].astype(str)

    df = pd.merge(df, res, left_on="Financial Instrument", right_on="Financial Instrument")

    if pd.isna(df["conid"]).any():
        log.error("Missing contract IDs, consider running ID scraper!")

    log.log("Contract ID retrieval finished")
    return df


"""
 <?xml version="1.0" encoding="UTF-8"?>
   <CustAcct>
     <Portfolio>
       <Position conid="197309044" avgPrice="1.58237" label="CL     JUL2018 71 P (LO)">1.0</Position>
       <Position conid="203476758" avgPrice="0.83763" label="CL     SEP2018 62.5 P (LO)">-1.0</Position>
       <Money currency="EUR">100000.0</Money>
       <Money currency="USD">-15907.37</Money>
     </Portfolio>
   </CustAcct>
"""


def export_portfolio_xml(data: pd.DataFrame, fn: str, trades=False, loglevel: LogLevel = LogLevel.normal):
    """
    Exports basket of trades in Risk Navigator XML format
    :param data: Basket data as data frame
    :param fn: Filename for XML output
    :param trades: Export trades instead of full portfolio
    :param loglevel: Loglevel for the export
    :return:
    """

    log = Logger(loglevel, "XML Export")

    if trades:
        log.log("Exporting trades")
        tmp = data[data["Trade"] != 0].copy()
    else:
        log.log("Exporting new portfolio position")
        tmp = data[data["NewPosition"] != 0].copy()

    tmp = lookup_contract_id(tmp, "instruments")

    x = Element("CustAcct")
    x.set("version", "1.0")

    p = SubElement(x, "Portfolio")

    for i, r in tmp.iterrows():
        pos = SubElement(p, "Position", {"conid": str(int(round(r["conid"]))),
                                         "avgPrice": str(r["Avg Price"]),
                                         "label": str(r["Financial Instrument"])
                                         })
        pos.text = str(r["Trade"]) if trades else str(r["NewPosition"])

    ElementTree(x).write(fn, encoding="UTF-8", xml_declaration=True)
    log.log("XML export finished")

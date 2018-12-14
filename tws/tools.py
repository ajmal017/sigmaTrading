"""
Various necessary tools and helpers for TWS API

Author: Peeter Meos
Date: 12. December 2018
"""
from xml.etree.ElementTree import Element, SubElement, ElementTree
import boto3
import pandas as pd


def lookup_contract_id(df, tbl: str):
    """
    Performs contract ID lookup from TWS
    :param df: series, list of instruments
    :param tbl: table containing instrument names
    :return:
    """
    db = boto3.resource('dynamodb', region_name='us-east-1',
                        endpoint_url="https://dynamodb.us-east-1.amazonaws.com")
    table = db.Table(tbl)

    # First look for Dynamo DB if there is no match, then
    # look TWS get the IDs
    # then update the Dynamo table

    # Loop through the table
    for i, r in df.iterrows():
        response = table.query()
        if len(response["Items"]) == 0:
            # Then request conid from the TWS
            pass

    df["conid"] = "1234"
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


def export_portfolio_xml(data: pd.DataFrame, fn: str):
    """
    Exports basket of trades in Risk Navigator XML format
    :param data: Basket data as data frame
    :param fn: Filename for XML output
    :return:
    """

    tmp = data[data["Trade"] != 0].copy()

    tmp = lookup_contract_id(tmp, "conid")

    x = Element("CustAcct")
    x.set("version", "1.0")

    p = SubElement(x, "Portfolio")

    # TODO: Contract id lookup needs to be added here
    for i, r in tmp.iterrows():
        pos = SubElement(p, "Position", {"conid": str(r["conid"]),
                                         "avgPrice": str(r["Avg Price"]),
                                         "label": str(r["Financial Instrument"])
                                         })
        pos.text = str(r["Trade"])

    ElementTree(x).write(fn, encoding="UTF-8", xml_declaration=True)

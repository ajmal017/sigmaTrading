"""
Various necessary tools and helpers for TWS API

Author: Peeter Meos
Date: 12. December 2018
"""
from xml.etree.ElementTree import Element, SubElement, ElementTree


def lookup_contract_id(df, tbl: str):
    """
    Performs contract ID lookup from TWS
    :param df: series, list of instruments
    :param tbl: table containing instrument names
    :return:
    """
    # First look for Dynamo DB if there is no match, then
    # look TWS get the IDs
    # then update the Dynamo table
    return


"""
# <?xml version="1.0" encoding="UTF-8"?>
#   <CustAcct>
#     <Portfolio>
#       <Position conid="197309044" avgPrice="1.58237" label="CL     JUL2018 71 P (LO)">1.0</Position>
#       <Position conid="203476758" avgPrice="0.83763" label="CL     SEP2018 62.5 P (LO)">-1.0</Position>
#       <Money currency="EUR">100000.0</Money>
#       <Money currency="USD">-15907.37</Money>
#     </Portfolio>
#   </CustAcct>
"""


def export_basket_xml(data: list, fn: str):
    """
    Exports basket of trades in Risk Navigator XML format
    :param data: Basket data as a list
    :param fn: Filename
    :return:
    """
    x = Element("CustAcct")
    x.set("version", "1.0")

    p = SubElement(x, "Portfolio")

    # TODO: Contract id lookup needs to be added here
    for i in data:
        pos = SubElement(p, "Position", {"conid": 123123,
                                         "avgPrice": 12312312321,
                                         "label": "CL JUL2018 71 P (LO)"})
        pos.text = 1.0

    ElementTree(x).write(fn, encoding="UTF-8")

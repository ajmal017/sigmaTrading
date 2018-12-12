"""
XML exports for TWS

Author: Peeter Meos
Date: 6. December 2018
"""
from xml.etree.ElementTree import Element, SubElement, ElementTree


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


# TODO: Write risk manager portfolio export.
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

    for i in data:
        pos = SubElement(p, "Position", {"conid": 123123,
                                         "avgPrice": 12312312321,
                                         "label": "CL JUL2018 71 P (LO)"})
        pos.text = 1.0

    ElementTree(x).write(fn, encoding="UTF-8")
    return x

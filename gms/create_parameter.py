"""
Utility functions for GAMS GDX creation

Author: Peeter Meos
Date: 3. December 2018
"""
from gams import GamsDatabase


def create_parameter(db: GamsDatabase, name, desc, uel, form, val):
    """
    Creates multi dimensional parameter array for GAMS GDX export
    :param db: GAMS database object
    :param name: parameter name
    :param desc: parameter description
    :param uel: parameter dimension names
    :param form: sparse or full
    :param val: value object
    :return: Nothing
    """
    # TODO: That code needs to be completed to loop through all the uel and data elements
    if form == "full" or form == "sparse":
        v = db.add_parameter(name, len(uel), explanatory_text=desc)
        v.add_record(1).value = val

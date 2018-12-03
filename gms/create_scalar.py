"""
Utility functions for GAMS GDX creation

Author: Peeter Meos
Date: 3. December 2018
"""
from gams import GamsDatabase


def create_scalar(db: GamsDatabase, val, name, desc):
    """
    Creates a GDX structure to represent a scalar
    :param db GAMS database
    :param val: scalar value
    :param name: scalar name
    :param desc: explanatory text
    :return:
    """
    # Add zero-dimensional parameter
    v = db.add_parameter(name, 0, explanatory_text=desc)
    v.add_record(1).value = val

    # Is this necessary?
    return v

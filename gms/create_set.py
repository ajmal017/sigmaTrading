"""
Utility and helper functions for GAMS GDX creation
Author: Peeter Meos
Date: 3. December 2018
"""
from gams import GamsDatabase


def create_set(db: GamsDatabase, name, desc, val, dim=1):
    """
    Creates GAMS set for GDX export
    :param db: Target GAMS database
    :param name: Set name
    :param desc: Explanatory text
    :param val: Set member values
    :param dim: Dimension
    :return:
    """
    # TODO implement that for multidimensional sets
    v = db.add_set(db, name, dim, explanatory_text=desc)
    for i in range(1, len(val)):
        v.add_record(i).value = val[i]

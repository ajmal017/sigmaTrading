"""
Copyright (C) 2018 Sigma Research OÜ. All rights reserved.
"""

""" Package implementing the GAMS optimisation of the portfolio """

VERSION = {
    'major': 0,
    'minor': 1,
    'micro': 2}


def get_version_string():
    version = '{major}.{minor}.{micro}'.format(**VERSION)
    return version


__version__ = get_version_string()

__all__ = ["create_parameter", "create_set", "gdx_as_df", "create_scalar"]

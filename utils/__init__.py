"""
Copyright (C) 2018 Sigma Research OÜ. All rights reserved.
"""

""" 
Package implementing  various utilities for trading
"""

VERSION = {
    'major': 0,
    'minor': 1,
    'micro': 1}


def get_version_string():
    version = '{major}.{minor}.{micro}'.format(**VERSION)
    return version


__version__ = get_version_string()

__all__ = ["data", "logger"]
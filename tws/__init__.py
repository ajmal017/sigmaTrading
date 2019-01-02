"""
Copyright (C) 2019 Sigma Research OÜ. All rights reserved.
"""

""" 
Package implementing  various utilities for trading
"""

VERSION = {
    'major': 0,
    'minor': 2,
    'micro': 0}


def get_version_string():
    version = '{major}.{minor}.{micro}'.format(**VERSION)
    return version


__version__ = get_version_string()

__all__ = ["tws", "tools", "snapshot", "portfolio"]

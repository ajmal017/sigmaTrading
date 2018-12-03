"""
Copyright (C) 2018 Sigma Research OÜ. All rights reserved.
"""

""" 
Package implementing quantitative finance bits ie. mathematics
for portfolio optimisation.
"""

VERSION = {
    'major': 0,
    'minor': 1,
    'micro': 2}


def get_version_string():
    version = '{major}.{minor}.{micro}'.format(**VERSION)
    return version


__version__ = get_version_string()
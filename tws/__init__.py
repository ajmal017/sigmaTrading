from .tws import TwsTool
from .conid_scraper import IdScraper


VERSION = {
    'major': 0,
    'minor': 3,
    'micro': 0}


def get_version_string():
    version = '{major}.{minor}.{micro}'.format(**VERSION)
    return version


__version__ = get_version_string()

__all__ = ["tws", "tools", "snapshot", "portfolio", "TwsTool", "IdScraper"]

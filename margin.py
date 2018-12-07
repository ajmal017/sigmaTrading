"""
Margin scraper.
Code connects to TWS and saves margin data for instruments
into Dynamo. Ported from Java

Author: Peeter Meos, Sigma Research OÜ
Date: 2. December 2018
"""
from ibapi.wrapper import EWrapper
from ibapi.client import EClient


class TwsWrapper(EWrapper):
    pass


class MarginCalc(TwsWrapper, EClient):
    """
    Class implements margin request and retrieval logic from TWS
    """
    def __init__(self):
        """
        Standard constructor for the class
        """
        TwsWrapper.__init__(self)
        EClient.__init__(self, wrapper=self)

    def create_instruments(self):
        pass

    def req_margins(self):
        pass


def main():
    """
    Main margin calculation code
    :return:
    """
    tws = MarginCalc()

    tws.connect("localhost", 4001, 2)
    tws.disconnect()


if __name__ == "__main__":
    main()

"""
Theta trader code.
Automation of the theta optimisation strategy.
The idea is something like that:
1) Monitor portfolio delta and gamma
2) When the thresholds are exceeded run portfolio re-balance
- request the whole option chain with greeks
- run optimisation
- create orders
- execute
- save all that to Amazon Dynamo
3) The whole thing should be monitored via a website.
- That shows current portfolio with greeks and PnL
- Draws greeks chart
- Has a OHLC chart of the instrument history
- Shows a log of actions
- Has a capability of manually re-balance the portfolio
- This python will implement back end, front end will be implemented elsewhere

Required libs
- IB api
- Pyomo and GLPK
- AWS Dynamo and S3
"""
from logger import *
from ibapi.wrapper import *
from ibapi.client import *


# TODO: Write extensions for EClient and EWrapper here
class ThetaClient(EClient):
    """
    Extension EClient class
    """
    def __init__(self, wrapper):
        """
        Simple constructor for the client
        :param wrapper:
        """
        EClient.__init__(self, wrapper)


class ThetaWrapper(EWrapper):
    """
    Extension of EWrapper class
    """
    def __init__(self):
        """
        Simple constructor
        """
        EWrapper.__init__(self)


class ThetaTrader(ThetaClient, ThetaWrapper):
    """
    The main trader class for portfolio delta monitoring.
    Keep the portfolio of respective FOPs as a list
    """
    def __init__(self):
        """
        Standard constructor for the class
        """
        self.logger = Logger(LogLevel.normal, "Theta strategy")
        self.symbol = "CL"
        self.portfolio = []

        ThetaWrapper.__init__(self)
        ThetaClient.__init__(self, wrapper=self)

    # TODO: Write a account update code

    # TODO: Implement running loop code
    def run(self):
        """
        Main trading loop code
        :return:
        """
        pass


def main():
    """
    Main entry point for the portfolio trader.

    :return:
    """
    trader = ThetaTrader()
    trader.run()


if __name__ == "__main__":
    # Main entry point
    main()

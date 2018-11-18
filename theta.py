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
from threading import Thread
import time
from logger import *
from ibapi.wrapper import *
from ibapi.client import *


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
    def __init__(self, symbol):
        """
        Simple constructor
        :param symbol Symbol for FOPs
        """
        EWrapper.__init__(self)
        self.logger = Logger(LogLevel.normal, "Theta Wrapper")
        self.logger.log("Theta Wrapper init")
        self.portfolio = {}
        self.symbol = symbol
        self.next_valid_id = -1

    def error(self, req_id: TickerId, error_code: int, error_string: str):
        """
        Error reporting
        :param req_id:
        :param error_code:
        :param error_string:
        :return:
        """
        self.logger.error(error_string)

    def nextValidId(self, order_id: object):
        """
        Update next valid order ID
        :param order_id:
        :return:
        """
        self.next_valid_id = order_id

    def updatePortfolio(self, contract: Contract, position: float, market_price: float, market_value: float,
                        average_cost: float, unrealized_pnl: float, realized_pnl: float, account_name: str):
        """
        Account update override
        :param contract:
        :param position:
        :param market_price:
        :param market_value:
        :param average_cost:
        :param unrealized_pnl:
        :param realized_pnl:
        :param account_name:
        :return:
        """

        # super().updatePortfolio(contract, position, market_price, market_value, average_cost,
        #                        unrealized_pnl, realized_pnl, account_name)
        self.logger.verbose("UpdatePortfolio " + contract.symbol + "" + contract.secType + "@" +
                            str(contract.exchange) + " Pos:" + str(position) + " MktPrice:" +
                            str(market_price) + " MktValue:" + str(market_value) + " AvgCost:" +
                            str(average_cost) + " UnrPNL:" + str(unrealized_pnl) + " RlzPNL:" +
                            str(realized_pnl) + " AcctName:" + account_name)
        if contract.symbol == self.symbol:
            # For some reason TWS returns primary exchange, but we need exchange field
            contract.exchange = contract.primaryExchange
            self.portfolio[contract.conId] = {"id": contract.conId, "pos": position,
                                              "price": market_price, "pnl": unrealized_pnl,
                                              "cont": contract}

    def get_portfolio(self):
        """
        Returns portfolio dict
        :return: Portfolio dict
        """
        return self.portfolio


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
        self.logger.log("Theta trading and balancing init")
        self.twsId = 13
        self.twsPort = 4001
        self.twsHost = "localhost"
        self.symbol = "CL"
        self.acct = "DU337774"

        ThetaWrapper.__init__(self, self.symbol)
        ThetaClient.__init__(self, wrapper=self)

        # Connect to IB and start the event thread
        self.connect(self.twsHost, self.twsPort, self.twsId)
        thread = Thread(target=self.run)
        thread.start()
        setattr(self, "_thread", thread)

        # Wait for next valid ID
        while self.wrapper.next_valid_id == -1:
            time.sleep(0.5)

        # Start receiving account updates
        self.reqAccountUpdates(True, self.acct)

    # TODO: Implement running loop code
    def trade(self):
        """
        Main trading loop code
        :return:
        """
        # Check whether we have market data for all the instruments in the portfolio
        # If not, request it
        for i in self.wrapper.portfolio.values():
            i["req_id"] = self.wrapper.next_valid_id
            self.logger.log("Request for contract " + i["id"])
            self.reqMktData(self.wrapper.next_valid_id, i["cont"], "", False, False, [])
            time.sleep(0.2)

    def stop(self):
        """
        Stops the trader, closes down the connection to TWS API
        :return:
        """
        self.logger.log("Shutting down theta trading and balancing")
        self.reqAccountUpdates(False, self.acct)
        self.disconnect()
        for i in self.portfolio.values():
            self.logger.log(i.values())


def main():
    """
    Main entry point for the portfolio trader.

    :return:
    """
    trader = ThetaTrader()
    trader.logger.log("Wait for account update")
    time.sleep(5)
    trader.logger.log("Requesting market data for the portfolio")
    trader.trade()
    time.sleep(10)
    trader.stop()


if __name__ == "__main__":
    # Main entry point
    main()

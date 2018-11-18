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
# TODO raise exception or quit when connection fails (or do something else?)
from threading import Thread
import time
from logger import *
from ibapi.wrapper import *
from ibapi.client import *
import configparser


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
    def __init__(self, symbol, sec_type):
        """
        Simple constructor
        :param symbol Symbol for FOPs
        """
        EWrapper.__init__(self)
        self.logger = Logger(LogLevel.normal, "Theta Wrapper")
        self.logger.log("Theta Wrapper init")
        self.portfolio = {}
        self.symbol = symbol
        self.sec_type = sec_type
        self.next_valid_id = -1
        self.id_updated = False

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
        super().nextValidId(order_id)
        self.logger.log("Next valid id updated to " + str(order_id))
        self.next_valid_id = order_id
        self.id_updated = True

    def tickPrice(self, req_id: TickerId, tick_type: TickType, price: float,  attrib: TickAttrib):
        """
        Price tick override and processing
        :param req_id:
        :param tick_type:
        :param price:
        :param attrib:
        :return:
        """
        self.logger.verbose("Req id " + str(req_id) + " tick " + str(tick_type) + " price " + str(price))

    def tickOptionComputation(self, req_id: TickerId, tick_type: TickType, implied_vol: float,
                              delta: float, opt_price: float, pv_dividend: float, gamma: float,
                              vega: float, theta: float, und_price: float):
        """
        Option greeks handling
        :param req_id:
        :param tick_type:
        :param implied_vol:
        :param delta:
        :param opt_price:
        :param pv_dividend:
        :param gamma:
        :param vega:
        :param theta:
        :param und_price:
        :return:
        """
        self.logger.log("Req id " + str(req_id) + " delta " + str(delta) + " gamma " +
                        str(gamma) + " theta " + str(theta))

        # Ticks are 10: bid option, 11: ask option, 12: last option
        for i in self.portfolio.values():
            if i["req_id"] == req_id:
                d = {"delta": delta, "gamma": gamma, "theta": theta, "vega": vega}
                if tick_type == 10:
                    i["bid"] = d
                if tick_type == 11:
                    i["ask"] = d

                if i["bid"] and i["ask"]:
                    for k in d.keys():
                        i["mid"][k] = (i["bid"][k] + i["ask"].k) / 2

                i["ul"] = und_price

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
        if contract.symbol == self.symbol and contract.secType == self.sec_type:
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
    def __init__(self, config):
        """
        Standard constructor for the class. Parameters come from a configuration file.
        """
        self.logger = Logger(LogLevel.normal, "Theta strategy")
        self.logger.log("Theta trading and balancing init")
        self.twsId = int(config["id"])
        self.twsPort = int(config["port"])
        self.twsHost = config["host"]
        self.symbol = config["symbol"]
        self.sec_type = config["type"]
        self.acct = "DU337774"

        ThetaWrapper.__init__(self, self.symbol, self.sec_type)
        ThetaClient.__init__(self, wrapper=self)

        # Connect to IB and start the event thread
        self.connect(self.twsHost, self.twsPort, self.twsId)
        thread = Thread(target=self.run)
        thread.start()
        setattr(self, "_thread", thread)

        # Wait for next valid ID
        self.wait_next_order_id()

        # Start receiving account updates
        self.reqAccountUpdates(True, self.acct)

    def reqMktData(self, req_id: TickerId, contract: Contract, generic_tick_list: str, snapshot: bool,
                   reg_snapshot: bool, mkt_options: TagValueList):
        """
        Override of reqMktData
        :param req_id:
        :param contract:
        :param generic_tick_list:
        :param snapshot:
        :param reg_snapshot:
        :param mkt_options:
        :return:
        """
        self.logger.log("Request for contract " + str(contract.conId) + " req id " + str(req_id))
        super().reqMktData(req_id, contract, generic_tick_list, snapshot, reg_snapshot, mkt_options)

    def wait_next_order_id(self):
        """
        Waits until next order id is generated.
        What if it gets generated already before we get here?
        Possible refactoring necessary

        :return:
        """
        self.logger.verbose("Waiting for next id.")
        self.id_updated = False
        self.reqIds(0)
        while not self.id_updated:
            time.sleep(0.1)
        self.id_updated = True
        self.logger.verbose("Next valid id present")

    def trade(self):
        """
        Main trading loop code
        :return:
        """
        # Check whether we have market data for all the instruments in the portfolio
        # If not, request it
        o = 1
        self.logger.log("Requesting market data for the portfolio")
        for i in self.portfolio.values():
            i["req_id"] = o
            self.reqMktData(o, i["cont"], "", True, False, [])
            o += 1

        # Now the main trading loop stuff
        user_input = ""
        while not user_input.upper().strip() == "Q":
            user_input = input("Theta trader ([G]reeks, [B]alance, [Q]uit):")

            # Print out portfolio greeks
            if user_input.upper().strip() == "G":
                self.logger.log("Portfolio greeks:")
                greeks = self.aggregate_greeks()
                for i, j in greeks:
                    self.logger.log(i + " : " + j)

            # Run portfolio rebalance
            if user_input.upper().strip() == "B":
                self.balance()

        self.logger.log("Shutting down trading loop")

    def aggregate_greeks(self) -> []:
        """
        Aggregates portfolio greeks
        :return: list containing greeks
        """
        names = ["delta", "gamma", "theta", "vega"]
        greeks = {"delta": 0, "gamma": 0, "theta": 0, "vega": 0}

        for i in self.portfolio.values():
            for j in names:
                if i["mid"]:
                    greeks[j] += i["mid"][j] if j in i else 0

        return greeks

    def balance(self):
        """
        The portfolio rebalancing code. So what do we need to do:
        1) Request option chain data
        2) Record all the greeks
        3) Cancel option chain data
        4) Compose data frame
        5) Pass that to the optimiser
        6) Compose orders based on the optimiser result
        7) Save the optimal basket, current greeks, target greeks and trades to AWS S3
        8) Execute trades
        9) Optionally, create trade adjustment logic, start from better price and move towards the worse
        10) Create an execution summary?
        If balance is executed manually, then do user review before executing trades.
        :return:
        """
        self.logger.log("Balance not implemented")

    def stop(self):
        """
        Stops the trader, closes down the connection to TWS API
        :return:
        """
        self.logger.log("Shutting down theta trading and balancing")
        self.reqAccountUpdates(False, self.acct)

        for i in self.portfolio.values():
            self.cancelMktData(i["req_id"])

        self.disconnect()
        for i in self.portfolio.values():
            self.logger.log(str(i.keys()))
            self.logger.log(str(i.values()))


def main():
    """
    Main entry point for the portfolio trader.

    :return:
    """
    cf = "config.sample"
    config = configparser.ConfigParser()
    config.read(cf)
    trader = ThetaTrader(config["theta"])
    trader.logger.log("Wait for account update")
    time.sleep(5)
    trader.trade()
    trader.stop()


if __name__ == "__main__":
    # Main entry point
    main()

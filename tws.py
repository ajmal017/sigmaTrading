"""
TWS Code
"""
import numpy as np
import datetime
from dateutil.relativedelta import relativedelta

from ibapi.wrapper import *
from ibapi.client import *
from ibapi.ticktype import *
from logger import *


class TwsClient(EClient):
    """
    Extension of EClient class
    """
    def __init__(self, wrapper):
        EClient.__init__(self, wrapper)


class TwsWrapper(EWrapper):
    """
    Extension of EWrapper class
    """
    def __init__(self):
        EWrapper.__init__(self)

    def tickPrice(self, req_id: TickerId, tick_type: TickType, price: float, attrib: TickAttrib):
        """
        Custom instrument price tick processing
        :param req_id:
        :param tick_type:
        :param price:
        :param attrib:
        :return:
        """

        super().tickPrice(req_id, tick_type, price, attrib)
        print("Tick Price. Ticker Id:", req_id, "tick_type:", tick_type, "Price:", price, "CanAutoExecute:",
              attrib.canAutoExecute, "PastLimit:", attrib.pastLimit, end=' ')
        if tick_type == TickTypeEnum.BID or tick_type == TickTypeEnum.ASK:
            print("PreOpen:", attrib.preOpen)
        else:
            print()

    def tickOptionComputation(self, req_id: TickerId, tick_type: TickType, implied_vol: float, delta: float,
                              opt_price: float, pv_dividend: float, gamma: float, vega: float, theta: float,
                              und_price: float):
        """
        Custom option greeks capture
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

        super().tickOptionComputation(req_id, tick_type, implied_vol, delta,
                                      opt_price, pv_dividend, gamma, vega, theta, und_price)
        print("TickOptionComputation. TickerId:", req_id, "tick_type:", tick_type, "ImpliedVolatility:",
              implied_vol, "Delta:", delta, "OptionPrice:", opt_price, "pvDividend:", pv_dividend, "Gamma: ",
              gamma, "Vega:", vega, "Theta:", theta, "UnderlyingPrice:", und_price)


class Trader(TwsWrapper, TwsClient):
    """
    Actual TWS connectivity and code
    """
    def __init__(self):
        """
        Standard constructor for the class
        """
        TwsWrapper.__init__(self)
        TwsClient.__init__(self, wrapper=self)

        self.logger = Logger(LogLevel.normal, "TWS")
        self.logger.log("TWS init")

        # Now create empty list for option chain
        self.option_chain = []

    def create_option_chain(self):
        """
        This method will create instruments for the option chain but will not request data for them
        :return:
        """
        right = ["PUT", "CALL"]      # We want both puts and calls
        expiry = [1, 2, 3, 4, 5, 6]  # We want instruments 6 months ahead
        strike = np.arange(50.0, 90.0, 0.5)

        next_id = 0
        for e in expiry:
            for s in strike:
                for r in right:
                    inst = Contract()
                    inst.symbol = "CL"
                    inst.right = r
                    inst.strike = s
                    inst.exchange = "NYMEX"

                    exp_date = datetime.datetime.now() + relativedelta(months=+e)
                    inst.lastTradeDateOrContractMonth = exp_date.strftime("%Y%m")

                    self.reqContractDetails(10 + next_id, inst)
                    self.option_chain.append({"id": next_id, "expiry": e, "strike": s, "right": r})
                    next_id += 1

    def print_option_chain(self):
        """
        Prints out option chain for debugging reasons
        :return: nothing
        """
        for o in self.option_chain:
            self.logger.log(o)

    def req_option_chain(self):
        """
        Requesting option chain data from the TWS
        :return: nothing, data comes via wrapper events
        """
        self.logger.log("Requesting option chain")

        inst = Contract()
        inst.secType = "FOP"
        inst.exchange = "NYMEX"
        inst.symbol = "CL"

        self.reqContractDetails(213, inst)
        # Request a snapshot
        self.reqMktData(214, inst, "", True, False, [])


if __name__ == "__main__":
    print("This is not the code you are supposed to run. Import it instead")


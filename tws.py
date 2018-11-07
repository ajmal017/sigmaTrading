"""
TWS Code
"""
import numpy as np
from dateutil.relativedelta import relativedelta
import time

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
        self.option_chain = {}  # Option chain needs to be stored within wrapper
        self.logger = Logger(LogLevel.normal, "Wrapper")

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
        self.logger.verbose("Tick Price. Ticker Id:"+str(req_id)+"tick_type:"+str(tick_type)+ "Price:" +
                            str(price)+"CanAutoExecute:"+str(attrib.canAutoExecute)+"PastLimit:"+
                            str(attrib.pastLimit))

        # Update bid and ask prices
        for i, j in enumerate(self.option_chain):
            if j.id == req_id:
                if tick_type == TickTypeEnum.ASK:
                    self.option_chain[i]['ask'] = price
                if tick_type == TickTypeEnum.BID:
                    self.option_chain[i]['bid'] = price

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
        self.logger.verbose("TickOptionComputation. TickerId:"+str(req_id)+"tick_type:"+str(tick_type) +
                            "ImpliedVolatility:" +str(implied_vol)+"Delta:"+str(delta)+"OptionPrice:" +
                            str(opt_price)+"pvDividend:"+str(pv_dividend)+"Gamma: "+str(gamma)+"Vega:" +
                            str(vega)+"Theta:"+str(theta)+"UnderlyingPrice:"+str(und_price))
        # Update data for option greeks
        for i, j in enumerate(self.option_chain):
            if j.id == req_id:
                self.option_chain[i]['delta'] = delta
                self.option_chain[i]['gamma'] = gamma
                self.option_chain[i]['theta'] = theta
                self.option_chain[i]['vega'] = vega
                self.option_chain[i]['sigma'] = implied_vol
                self.option_chain[i]['ul_price'] = und_price


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

    def create_option_chain(self):
        """
        This method will create instruments for the option chain but will not request data for them
        :return:
        """
        right = ["PUT", "CALL"]              # We want both puts and calls
        expiry = [1, 2, 3, 4, 5, 6]          # We want instruments 6 months ahead
        strike = np.arange(50.0, 90.0, 0.5)  # Strikes from 50 to 90

        next_id = 10
        for e in expiry:
            for s in strike:
                for r in right:
                    inst = Contract()
                    inst.symbol = "CL"
                    inst.secType = "FOP"
                    inst.right = r
                    inst.strike = s
                    inst.exchange = "NYMEX"
                    inst.tradingClass = "LO"

                    exp_date = datetime.datetime.now() + relativedelta(months=+e)
                    exp_date = exp_date.strftime("%Y%m")
                    inst.lastTradeDateOrContractMonth = exp_date

                    time.sleep(0.1)  # In order not to exceed TWS capacities we need to wait 100 milliseconds
                    self.reqContractDetails(next_id, inst)
                    self.wrapper.option_chain.append({"id": next_id, "expiry": exp_date, "strike": s, "right": r})
                    next_id += 1

    def print_option_chain(self):
        """
        Prints out option chain for debugging reasons
        :return: nothing
        """
        for o in self.wrapper.option_chain:
            self.logger.log(o)

    def req_option_chain(self):
        """
        Requesting option chain data from the TWS
        :return: nothing, data comes via wrapper events
        """
        self.logger.log("Requesting option chain price data")

        for i in self.wrapper.option_chain:
            inst = Contract()
            inst.secType = "FOP"
            inst.exchange = "NYMEX"
            inst.symbol = "CL"
            inst.tradingClass = "LO"

            inst.strike = i.strike
            inst.lastTradeDateOrContractMonth = i.expiry
            inst.right = i.right

            # Request a snapshot
            time.sleep(0.1)
            self.reqMktData(i.id + 3000, inst, "", True, False, [])


if __name__ == "__main__":
    print("This is not the code you are supposed to run. Import it instead")


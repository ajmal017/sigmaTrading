"""
Code to handle portfolio snapshots, overviews and everything related.

Author: Peeter Meos
Date: 2. January 2019
"""
import pandas as pd
from tws import TwsTool
from utils.logger import LogLevel
from ibapi.contract import Contract
from ibapi.wrapper import TickType, TickerId
from ibapi.account_summary_tags import AccountSummaryTags
import time
from datetime import datetime


class Portfolio(TwsTool):
    def __init__(self, opt, log_level=LogLevel.normal, name="Portfolio"):
        """
        Standard constructor
        :param opt:
        :param log_level:
        :param name:
        """
        super().__init__(name, log_level=log_level)
        self.haveData = False
        self.acct = opt["account"]
        self.symbol = opt["symbol"]
        self.portfolio = []
        self.value = 0.0
        self.details = False

    def get_account_summary(self):
        """
        Simply prints out account summary
        :return:
        """
        self.connect("localhost", 4001, 32)
        self.haveData = False

        self.logger.log("-------------- Account --------------")
        self.reqAccountSummary(self.nextId, "All", AccountSummaryTags.AllTags)
        while not self.haveData:
            time.sleep(0.01)
        self.logger.log("-------------------------------------")
        self.disconnect()

    def get_account_details(self):
        """
        Simply prints out account details
        :return:
        """
        self.connect("localhost", 4001, 32)
        self.haveData = False
        self.details = True

        self.logger.log("-------------- Account --------------")
        self.reqAccountUpdates(True, self.acct)
        while not self.haveData:
            time.sleep(0.01)
        self.logger.log("-------------------------------------")
        self.reqAccountUpdates(False, self.acct)
        self.disconnect()

    def get_snapshot(self) -> pd.DataFrame:
        """
        Gets portfolio snapshot and does a summary on that
        :return: list of portfolio entries
        """

        # TODO: Get rid of those hardcoded parameters, use config file instead
        self.connect("localhost", 4001, 32)

        self.reqAccountUpdates(True, self.acct)
        while not self.haveData:
            time.sleep(0.01)
        self.reqAccountUpdates(False, self.acct)

        o = self.nextId
        for i in self.portfolio:
            i["id"] = o
            i["Delta"] = None
            self.reqMktData(o, i["cont"], "", True, False, [])
            o += 1

        # Wait until we have all the data
        self.haveData = False
        while not self.haveData:
            self.haveData = True
            for i in self.portfolio:
                if i["Delta"] is None:
                    self.haveData = False
            time.sleep(0.1)

        self.disconnect()

        # TODO: Create a data frame on the results here
        df1 = pd.DataFrame(columns=["Strike", "Side", "Expiry", "Vol", "Underlying Price", "Mid",
                                    "Position", "Delta", "Gamma", "Theta", "Vega"])
        for i in self.portfolio:
            df1 = df1.append({"Strike": i["strike"],
                              "Side": i["side"],
                              "Expiry": i["expiry"],
                              "Mid": i["price"],
                              "Vol": i["Vol"],
                              "Delta": i["Delta"],
                              "Gamma": i["Gamma"],
                              "Theta": i["Theta"],
                              "Vega": i["Vega"],
                              "Position": i["position"],
                              "Underlying Price": i["Underlying Price"]}, ignore_index=True)
        df1["Days"] = pd.to_datetime(df1["Expiry"], format="%Y%m%d") - datetime.today()
        df1["Days"] = df1["Days"].dt.days / 365

        return df1

    def print_snapshot(self, data):
        """
        Prints account snapshot
        :param data:
        :return:
        """
        self.logger.log("-------------------- Portfolio -----------------------")
        self.logger.log("\t\t\t\tDelta\tGamma\tTheta\tVega")
        self.logger.log("------------------------------------------------------")
        s_greeks = {"Delta": 0,
                    "Gamma": 0,
                    "Theta": 0,
                    "Vega": 0}
        for i, row in data.iterrows():
            self.logger.log(self.symbol + " " + str(row["Strike"]) + " " + str(row["Side"]) + " " +
                            str(row["Expiry"]) + " " + str(round(row["Position"])).rjust(3) + " " +
                            str(round(row["Delta"], 4)).rjust(7) + " " + str(round(row["Gamma"], 4)).rjust(7) + " " +
                            str(round(row["Theta"], 4)).rjust(7) + " " + str(round(row["Vega"], 4)).rjust(7))
            s_greeks["Delta"] += row["Delta"] * row["Position"]
            s_greeks["Gamma"] += row["Gamma"] * row["Position"]
            s_greeks["Theta"] += row["Theta"] * row["Position"]
            s_greeks["Vega"] += row["Vega"] * row["Position"]
        self.logger.log("------------------------------------------------------")
        self.logger.log("Total:\t\t     " + str(round(s_greeks["Delta"], 4)).rjust(7) + " " +
                        str(round(s_greeks["Gamma"], 4)).rjust(7) + " " +
                        str(round(s_greeks["Theta"], 4)).rjust(7) + " " +
                        str(round(s_greeks["Vega"], 4)).rjust(7))
        self.logger.log("------------------------------------------------------")

    def updateAccountValue(self, key: str, val: str, currency: str, account_name: str):
        """
        Account value update overload
        :param key:
        :param val:
        :param currency:
        :param account_name:
        :return:
        """
        #if account_name == self.acct:
        if self.details:
            self.logger.log(key.ljust(30) + "\t" + val.rjust(10) + " " + currency)

    def updatePortfolio(self, contract: Contract, position: float, market_price: float, market_value: float,
                        average_cost: float, unrealized_pnl: float, realized_pnl: float, account_name: str):
        """
        Portfolio contents update overload
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
        # if account_name == self.acct:
        if self.details:
            self.logger.log(contract.symbol.ljust(5) + " " + str(position).rjust(6) + " " +
                            str(round(market_price, 3)).rjust(5) +
                            " " + str(unrealized_pnl).rjust(12))
        contract.exchange = contract.primaryExchange
        if contract.symbol == self.symbol:
            self.portfolio.append({"cont": contract,
                                   "position": position,
                                   "price": market_price,
                                   "strike": contract.strike,
                                   "side": contract.right,
                                   "expiry": contract.lastTradeDateOrContractMonth})

    def accountSummary(self, req_id: int, account: str, tag: str, value: str, currency: str):
        """
        Account summary information
        :param req_id:
        :param account:
        :param tag:
        :param value:
        :param currency:
        :return:
        """
        self.logger.log(tag.ljust(25) + "\t" + value.rjust(8) + " " + currency)

    def accountSummaryEnd(self, req_id: int):
        """
        End of account summary
        :param req_id:
        :return:
        """
        self.haveData = True

    def accountDownloadEnd(self, account_name: str):
        """
        My override of end of account download details
        :param account_name:
        :return:
        """
        #if account_name == self.acct:
        self.haveData = True

    def tickOptionComputation(self, req_id: TickerId, tick_type: TickType, implied_vol: float, delta: float,
                              opt_price: float, pv_dividend: float, gamma: float, vega: float, theta: float,
                              und_price: float):
        """
        Save the greeks
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
        for i in self.portfolio:
            if i["id"] == int(req_id):
                i["Delta"] = delta
                i["Gamma"] = gamma
                i["Theta"] = theta
                i["Vega"] = vega
                i["Vol"] = implied_vol
                i["Underlying Price"] = und_price



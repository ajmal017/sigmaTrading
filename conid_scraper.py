"""
Queries contract IDs and puts them to Dynamo DB

Author: Peeter Meos
Date: 15. December 2018
"""
from tws.tws import TwsTool
from datetime import datetime
from dateutil.relativedelta import relativedelta
from ibapi.contract import Contract, ContractDetails
import numpy as np
import time
import locale
import boto3


class IdScraper(TwsTool):
    """
    Class definition
    """
    def __init__(self, name):
        super().__init__(name)

        start_strike = 40
        end_strike = 100
        self.strikes = np.array(range(0, (end_strike - start_strike) * 2)) / 2 + start_strike
        self.months = []
        self.data = []

        for ind in range(1, 9):
            tmp = datetime.today() + relativedelta(months=+ind)
            self.months.append(tmp.strftime("%Y%m"))

        self.c = Contract()
        self.c.symbol = "CL"
        self.c.currency = "USD"
        self.c.secType = "FOP"
        self.c.exchange = "NYMEX"
        self.c.tradingClass = "LO"

    def req_data(self):
        """
        Makes the contract detail requests
        :return:
        """
        self.logger.log("Creating option chain and requesting details")
        o = self.nextId

        for m in self.months:
            self.logger.log("We are at month " + m)
            for j in self.strikes:
                for k in ["P", "C"]:
                    self.c.lastTradeDateOrContractMonth = m
                    self.c.strike = j
                    self.c.right = k
                    self.data.append({"id": o,
                                      "symbol": self.c.symbol,
                                      "sectype": self.c.secType,
                                      "class": self.c.tradingClass,
                                      "exchange": self.c.exchange,
                                      "currency": self.c.currency,
                                      "expiry": self.c.lastTradeDateOrContractMonth,
                                      "side": self.c.right,
                                      "strike": '{:g}'.format(self.c.strike),
                                      "conid": 0})
                    self.reqContractDetails(o, contract=self.c)
                    time.sleep(1/40)
                    o = o + 1

    def contractDetails(self, req_id: int, contract_details: ContractDetails):
        """
        Contract details override
        :param self:
        :param req_id:
        :param contract_details:
        :return:
        """
        for m in self.data:
            if m["id"] == req_id:
                m["conid"] = contract_details.contract.conId
                m["contr_month"] = contract_details.contract.lastTradeDateOrContractMonth

    def wait_for_finish(self):
        """
        Waits for all the contract details to arrive
        :return:
        """
        self.logger.log("Waiting for all contract details to arrive")
        have_all = False
        while not have_all:
            have_all = True
            for m in self.data:
                if m["conid"] == 0:
                    have_all = False
            time.sleep(0.5)
        self.logger.log("All data received, proceeding")

    def postprocess(self):
        """
        Do some data postprocessing - create Financial Instrument string
        :return:
        """
        # We need US locale
        orig_locale = locale.getlocale(locale.LC_TIME)
        locale.setlocale(locale.LC_ALL, "en_US")

        # Now create the fields
        for m in self.data:
            right = "CALL" if m["side"] == "C" else "PUT"
            m["Financial Instrument"] = m["symbol"] + " " + m["sectype"] + " (" + m["class"] + ") " + \
                datetime.strptime(m["expiry"], "%Y%m").strftime("%b'%y") + \
                " " + m["strike"] + " " + right + " @" + \
                m["exchange"]
        # Put the locale back
        locale.setlocale(locale.LC_ALL, orig_locale)

    def write_dynamo(self, tbl: str):
        """
        Writes data to dynamo DB table
        :param tbl:
        :return:
        """
        self.logger.log("Exporting to Dynamo DB table " + tbl)

        db = boto3.resource('dynamodb', region_name='us-east-1',
                            endpoint_url="https://dynamodb.us-east-1.amazonaws.com")
        table = db.Table(tbl)

        with table.batch_writer() as batch:
            for m in self.data:
                batch.put_item(Item={"instString": m["Financial Instrument"],
                                     "conid": m["conid"]})

        self.logger.log("Export finished")


if __name__ == "__main__":
    i = IdScraper("ConID Scraper")
    i.connect("localhost", 4001, 56)
    i.req_data()
    i.wait_for_finish()
    i.postprocess()
    i.write_dynamo("instruments")
    i.disconnect()

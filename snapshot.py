"""
Snapshot scraper.
Code connects to TWS and saves snapshot data for instruments
into Dynamo. Ported from Java

Author: Peeter Meos, Sigma Research OÜ
Date: 11. December 2018
"""
from ibapi.contract import Contract
from ibapi.wrapper import TickType, TickAttrib
from tws.tws import TwsTool
import numpy as np
import time
import boto3
import argparse

"""
The necessary columns are:
Financial Instrument            CL FOP (LO) Feb'19 40 CALL @NYMEX
Underlying Price                51.54
Bid                             11.61
Mid                             11.649999999999999
Ask                             11.69
Spread                          0.08
Position
Avg Price
Implied Vol. %                  50.8%
Delta                           0.964931
Gamma                           0.010373
Vega                            0.012236
Theta                           -0.008877
Days to Last Trading Day        30.0
"""


class Snapshot(TwsTool):
    """
    Class implements option chain snapshot data request and retrieval logic from TWS
    """
    def __init__(self):
        """
        Standard constructor for the class
        """
        super().__init__(name="Snapshot Scraper")

        self.chain = []

        self.strikes = np.array(range(0, 120)) / 2 + 40
        # TODO: This needs to be automatic
        self.months = ["201901", "201902", "201903", "201904", "201905", "201906"]

        self.cont = Contract()
        self.cont.symbol = "CL"
        self.cont.exchange = "NYMEX"
        self.cont.currency = "USD"
        self.cont.secType = "FOP"
        self.cont.tradingClass = "LO"

    def create_instruments(self):
        """
        Creates instruments
        :return:
        """

        sides = ["c", "p"]
        action = ["BUY", "SELL"]
        o = int(self.nextId)
        for m in self.months:
            for i in self.strikes:
                for j in sides:
                    for k in action:
                        self.chain.append({"id": o,
                                           "strike": i,
                                           "side": j,
                                           "action": k,
                                           "expiry": m})
                        o = o + 1

    def req_margins(self):
        """
        Requests data
        :return:
        """
        for i in self.chain:

            self.cont.right = i["side"].upper()
            self.cont.strike = i["strike"]
            self.cont.lastTradeDateOrContractMonth = i["expiry"]

            time.sleep(1/40)
            self.reqMktData(i["id"], self.cont, genericTickList="",
                            snapshot=True, regulatorySnapshot=False,
                            mktDataOptions=[])

    def tickPrice(self, req_id: int, tick_type: TickType, price:float,
                  attrib: TickAttrib):
        """
        Market tick data override for snapshot market data retrieval
        :param req_id:
        :param tick_type:
        :param price:
        :param attrib:
        :return:
        """
        for i in self.chain:
            if i["id"] == req_id:
                # TODO: Check if the tick type values are correct
                if tick_type == 1:
                    i["Bid"] = price
                elif tick_type == 2:
                    i["Ask"] = price

    def tickOptionComputation(self, req_id: int, tick_type: TickType,
                              implied_vol: float, delta: float, opt_price: float, pv_dividend:float,
                              gamma: float, vega: float, theta: float, und_price: float):
        """
        Option computation and greek data retrieval override for saving the snapshot data.
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
        for i in self.chain:
            if i["id"] == req_id:
                # TODO: Check how TWS calculates the greeks, which price does it base them on?
                # TODO: Check that the fields names are indeed correct and match with the
                #  data frame
                i["Delta"] = delta
                i["Gamma"] = gamma
                i["Theta"] = theta
                i["Vega"] = vega
                i["Vol"] = implied_vol
                i["ul price"] = und_price

    def wait_to_finish(self):
        """
        Waits until all margin data has been received
        :return:
        """
        self.logger("Waiting for all market data to arrive")
        found = False
        while not found:
            found = True
            for i in self.chain:
                if "Delta" not in i:
                    found = False
            time.sleep(0.5)
        self.logger("All data has been received, proceeding")

    def prepare_df(self):
        """
        Prepares market snapshot data frame for export
        :return:
        """
        pass

    def export_dynamo(self, tbl="mktData"):
        """
        Exports the margins to dynamoDB
        :param tbl: Dynamo DB table to write the margins to
        :return:
        """
        """
        days: number
        delta: number
        exchange: string
        expiry: string
        lastTradingDay: string
        longId: number
        marginLong: number
        marginShort: number
        shortId: number
        side: string
        symbol: string
        ulPrice: number
        """
        self.logger("Exporting market data snapshot to Dynamo DB table " + str(tbl))
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1',
                                  endpoint_url="https://dynamodb.us-east-1.amazonaws.com")
        table = dynamodb.Table(tbl)
        # TODO: This needs to be in proper format
        # {"inst": self.cont.symbol, "date": dtg, "data":}
        response = table.put_item()
        self.logger.log(str(response))


if __name__ == "__main__":
    # Process command line arguments first
    parser = argparse.ArgumentParser("Market data capture tool")
    parser.add_argument("-v", "--verbose", action="store_true", help="Produce verbose output")
    parser.add_argument("-q", "--quiet", action="store_true", help="Minimal logging, only output errors")
    parser.add_argument("--db", action="store_true", help="Write snapshot to Dynamo DB")
    parser.add_argument("--csv", action="store", help="Write snapshot to given CSV file")

    args = parser.parse_args()

    # Now the actual stuff
    tws = Snapshot()

    tws.connect("localhost", 4001, 12)
    tws.create_instruments()
    tws.req_margins()
    #tws.wait_to_finish()
    #tws.prepare_df()
    #tws.export_dynamo()
    tws.disconnect()

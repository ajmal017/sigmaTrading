"""
Margin scraper.
Code connects to TWS and saves margin data for instruments
into Dynamo. Ported from Java

Author: Peeter Meos, Sigma Research OÜ
Date: 2. December 2018
"""
from ibapi.wrapper import EWrapper
from ibapi.client import EClient
from ibapi.order import Order
from ibapi.contract import Contract, ContractDetails
from ibapi.wrapper import TickType, TickAttrib
from ibapi.order_state import OrderState
from threading import Thread
import pandas as pd
import numpy as np
import time
from datetime import datetime
import boto3


class TwsWrapper(EWrapper):
    """
    TWS Wrapper doesnt need any changes, leave it as it is
    """
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

        self.chain = []
        self.ul_chain = []
        self.nextId = -1

        self.strikes = np.array(range(0, 80)) / 2 + 40
        # TODO: This needs to be automatic
        self.months = ["201901", "201902", "201903", "201904", "201905", "201906"]

        self.cont = Contract()
        self.cont.symbol = "CL"
        self.cont.exchange = "NYMEX"
        self.cont.currency = "USD"
        self.cont.secType = "FOP"
        self.cont.tradingClass = "LO"

        self.ul = Contract()
        self.ul.symbol = "CL"
        self.ul.exchange = "NYMEX"
        self.ul.currency = "USD"
        self.ul.secType = "FUT"

    def connect(self, host, port, con_id):
        """
        Connect to TWS override
        :param host:
        :param port:
        :param con_id:
        :return:
        """
        EClient.connect(self, host, port, con_id)

        thread = Thread(target=self.run)
        thread.start()
        setattr(self, "_thread", thread)

        # Wait until next id
        while self.nextId == -1:
            time.sleep(0.1)

    def create_instruments(self):
        """
        Creates instruments
        :return:
        """

        sides = ["c", "p"]
        o = int(self.nextId)
        for m in self.months:
            for i in self.strikes:
                for j in sides:
                    self.chain.append({"id_long": o,
                                       "id_short": o + 1,
                                       "strike": i,
                                       "side": j,
                                       "expiry": m,
                                       "delta_bid": 0,
                                       "delta_ask": 0})
                    o = o + 2

        # And same for futures
        for m in self.months:
            self.ul_chain.append({"id": o,
                                  "expiry": m})
            o = o + 1

    def req_margins(self):
        """
        Requests data
        :return:
        """
        # Request data for underlying
        for i in self.ul_chain:
            self.ul.lastTradeDateOrContractMonth = i["expiry"]
            self.reqMktData(i["id"], self.ul, genericTickList="",
                            snapshot=True, regulatorySnapshot=False,
                            mktDataOptions=[])

        # Request data for option chain
        for i in self.chain:
            self.cont.right = i["side"].upper()
            self.cont.strike = i["strike"]
            self.cont.lastTradeDateOrContractMonth = i["expiry"]

            order = Order()
            order.whatIf = True
            order.totalQuantity = 1
            order.orderType = "MKT"

            order.orderId = i["id_long"]
            order.action = "BUY"
            self.placeOrder(i["id_long"], self.cont, order)
            time.sleep(1/60)
            self.reqMktData(i["id_long"], self.cont, genericTickList="",
                            snapshot=True, regulatorySnapshot=False,
                            mktDataOptions=[])
            time.sleep(1/60)
            self.reqContractDetails(i["id_long"], self.cont)

            order.orderId = i["id_short"]
            order.action = "SELL"
            self.placeOrder(i["id_short"], self.cont, order)
            time.sleep(1/60)
            self.reqMktData(i["id_short"], self.cont, genericTickList="",
                            snapshot=True, regulatorySnapshot=False,
                            mktDataOptions=[])

    def nextValidId(self, order_id: int):
        """
        Next order ID update
        :param order_id:
        :return:
        """
        self.nextId = int(order_id)

    def contractDetails(self, req_id: int, contract_details: ContractDetails):
        """
        Receives contract details for the instrument
        :param req_id:
        :param contract_details:
        :return:
        """
        for i in self.chain:
            if req_id == i["id_long"]:
                i["lastTradingDay"] = contract_details.realExpirationDate

    def tickPrice(self, req_id: int, tick_type: TickType, price: float,
                  attrib: TickAttrib):
        """
        We need to update underlying price here
        :param req_id:
        :param tick_type:
        :param price:
        :param attrib:
        :return:
        """
        if req_id >= 0:
            # Future, update relevant option chain elements with ul_price
            # We need to do that for last traded price, or bid/ask midpoint?
            if tick_type == 1 or tick_type == 2:
                for i in self.ul_chain:
                    if i["id"] == req_id:
                        if tick_type == 1:
                            i["bid"] = price
                        if tick_type == 2:
                            i["ask"] = price
        else:
            # Options - dont need to do anything
            pass

    def tickOptionComputation(self, req_id: int, tick_type: TickType,
                              implied_vol: float, delta: float, opt_price: float, pv_dividend: float,
                              gamma: float, vega: float, theta: float, und_price: float):
        """
        We need to update option delta here for the chain elements
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
        if tick_type == 11 or tick_type == 12:
            for i in self.chain:
                if i["id_long"] == req_id or i["id_short"] == req_id:
                    if tick_type == 11:
                        i["delta_bid"] = delta
                    if tick_type == 12:
                        i["delta_ask"] = delta

    def openOrder(self, order_id: int, contract: Contract, order: Order,
                  order_state: OrderState):
        """
        Open order rewrite to handle the margin information
        :param order_id:
        :param contract:
        :param order:
        :param order_state:
        :return:
        """
        for i in self.chain:
            if i["id_short"] == order_id:
                print(i["expiry"] + " " + str(i["strike"]) + " " + i["side"])
                i["marginShort"] = order_state.initMarginChange
            if i["id_long"] == order_id:
                print(i["expiry"] + " " + str(i["strike"]) + " " + i["side"])
                i["marginLong"] = order_state.initMarginChange

    def wait_to_finish(self):
        """
        Waits until all margin data has been received
        :return:
        """
        found = False
        while not found:
            found = True
            for i in self.chain:
                if "marginLong" not in i or "marginShort" not in i:
                    found = False
            time.sleep(0.5)

    def summarise_chain(self):
        """
        Generates full option chain for export
        :return:
        """
        # Calculate price midpoints
        ul_price = []
        for i in self.ul_chain:
            ul_price.append((i["bid"] + i["ask"]) / 2)

        # Update underlying prices and greeks
        for i in self.chain:
            if "delta_ask" in i.keys() and "delta_bid" in i.keys():
                if not i["delta_bid"] is None and not i["delta_ask"] is None:
                    i["delta"] = (i["delta_bid"] + i["delta_ask"]) / 2
                elif i["delta_bid"] is None:
                    i["delta"] = i["delta_ask"]
                elif i["delta_ask"] is None:
                    i["delta"] = i["delta_bid"]
                else:
                    i["delta"] = 0
                i["ulPrice"] = ul_price[self.months.index(i["expiry"])]

    def export_dynamo(self, tbl="margin"):
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
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1',
                                  endpoint_url="https://dynamodb.us-east-1.amazonaws.com")
        table = dynamodb.Table(tbl)

        dtg = datetime.today().strftime("%Y%m%d")

        # Dict to data frame for convenience
        df = pd.DataFrame(self.chain)
        df["days"] = pd.to_datetime(df["lastTradingDay"], format="%Y%m%d", errors="ignore")
        df["days"] = df["days"].sub(datetime.today()).dt.days
        print(df)

        d = {"inst": self.cont.symbol, "date": dtg, "data": df.to_json(orient="records")}
        table.put_item(Item=d)


def main():
    """
    Main margin calculation code
    :return:
    """
    tws = MarginCalc()

    tws.connect("localhost", 4001, 12)
    tws.create_instruments()
    tws.req_margins()
    tws.wait_to_finish()
    tws.summarise_chain()
    # tws.export_dynamo()
    tws.disconnect()


if __name__ == "__main__":
    main()

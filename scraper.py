"""
Saves market data to AWS Dynamo
We request 1 sec real time bars and save them to dynamo

Peeter Meos
21. November 2018
"""
from logger import *
from ibapi.wrapper import *
from ibapi.client import *
from threading import Thread
import boto3
import time


class TwsWrapper(EWrapper):
    """
    Wrapper implementation
    """
    def __init__(self):
        """
        Constructor override
        """
        EWrapper.__init__(self)


class Scraper(TwsWrapper, EClient):
    """
    Scraper class definition
    """
    def __init__(self):
        """
        Constructor redefinition
        """
        TwsWrapper.__init__(self)
        EClient.__init__(self, wrapper=self)
        self.logger = Logger(LogLevel.normal, "Scraper")

        self.connect("localhost", 4001, 15)

        thread = Thread(target=self.run)
        thread.start()
        setattr(self, "_thread", thread)

        self.next_order = -1
        self.reqIds(0)
        while self.next_order == -1:
            time.sleep(0.1)
        self.logger.log("Next order ID received")

        self.logger.log("Market scraper init")
        self.symbol = "CL"
        self.exchange = "NYMEX"
        self.type = "FUT"
        self.currency = "USD"
        self.expiry = "201901"

        self.inst = Contract()
        self.inst.symbol = self.symbol
        self.inst.exchange = self.exchange
        self.inst.secType = self.type
        self.inst.currency = self.currency
        self.inst.lastTradeDateOrContractMonth = self.expiry

        self.req_id = self.next_order
        self.reqRealTimeBars(int(self.req_id), self.inst, 5, "TRADES", True, [])
        self.reqMktData(int(self.req_id) + 1, self.inst, "", False, False, [])

    def nextValidId(self, order_id: int):
        """
        Saves next order ID
        :param order_id:
        :return:
        """
        self.next_order = order_id

    def realtimeBar(self, req_id: TickerId, bar_time: int, op: float, high: float, low: float, close: float,
                    volume: int, wap: float, count: int):
        """
        Real time bar reception override
        :param req_id:
        :param bar_time:
        :param op:
        :param high:
        :param low:
        :param close:
        :param volume:
        :param wap:
        :param count:
        :return:
        """
        # TODO: Why is this thing not getting called?
        super().realtimeBar(req_id, bar_time, op, high, low, close, volume, wap, count)
        self.logger.log(str(bar_time) + " O " + str(open) + " H " + str(high) + " L " + str(low) + " C " + str(close))

    def tickPrice(self, req_id: TickerId, tick_type: TickType, price: float, attrib: TickAttrib):
        """
        Price tick override
        :param req_id:
        :param tick_type:
        :param price:
        :param attrib:
        :return:
        """
        self.logger.log(str(tick_type) + " price " + str(price))

    def error(self, req_id: TickerId, error_code: int, error_string: str):
        """
        Error override
        :param self:
        :param req_id:
        :param error_code:
        :param error_string:
        :return:
        """
        self.logger.error(str(req_id) + ":" + error_string)

    def scrape(self):
        """
        Main scraping loop
        :return:
        """
        self.logger.log("Scraper scraping")
        user_input = ""
        while user_input.upper() != "Q":
            time.sleep(1)
            user_input = input("Scraper [Q]uit:")

    def stop(self):
        """
        Cleanup code
        :return:
        """
        self.logger.log("Closing down the scraper")
        self.cancelRealTimeBars(self.req_id)
        self.cancelMktData(int(self.req_id) + 1)
        self.disconnect()
        self.logger.log("Goodbye")


def main():
    """
    Main code for the scraper
    :return:
    """
    db = boto3.resource("dynamodb")
    t = db.Table("mktData")
    print(t.creation_date_time)

    scraper = Scraper()
    scraper.scrape()
    scraper.stop()
    return


if __name__ == "__main__":
    """
    Main entry point for the scraper
    """
    main()

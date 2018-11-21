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
        EWrapper.__init__()


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
        self.reqRealTimeBars(self.next_order, self.inst, 1, "MIDPOINT", True, [])

    def nextValidId(self, order_id: int):
        """
        Saves next order ID
        :param order_id:
        :return:
        """
        self.next_order = order_id

    def realtimeBar(self, req_id: TickerId, time: int, op: float, high: float, low: float, close: float,
                    volume: int, wap: float, count: int):
        """
        Real time bar reception override
        :param req_id:
        :param time:
        :param op:
        :param high:
        :param low:
        :param close:
        :param volume:
        :param wap:
        :param count:
        :return:
        """
        pass

    def error(self, req_id:TickerId, error_code:int, error_string:str):
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
        pass

    def stop(self):
        """
        Cleanup code
        :return:
        """
        self.logger.log("Closing down the scraper")
        self.cancelRealTimeBars(self.req_id)


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


if __name__ == "__main__":
    """
    Main entry point for the scraper
    """
    main()

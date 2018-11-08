"""
News trader implementation in Python

Peeter Meos, 8. November 2018
"""
from ibapi.client import *
from ibapi.wrapper import *
from logger import *


class TwsClient(EClient):
    """
    EClient extension for news trader
    """
    def __init__(self, wrapper):
        """
        Simple constructor for the client
        :param wrapper:
        """
        EClient.__init__(self, wrapper)


class TwsWrapper(EWrapper):
    """
    EWrapper extension for news trader
    """
    def __init__(self):
        """
        Simple constructor for the wrapper
        Also handles creation and initialisation of orders for the
        trading strategy
        """

        # First lets get started with logging
        self.logger = Logger(LogLevel.normal, "Wrapper")
        self.logger.log("Wrapper init")
        EWrapper.__init__(self)

        # The settings for the order structure
        # At some later stage this also needs to be dynamic and be set somewhere else
        self.last_price = -1.0    # Last known price of the instrument
        self.set_price = -1.0     # The price that the order structure is set at
        self.entry_spread = 0.05  # Spread for the order structure
        self.tgt_spread = 0.2     # Target distance
        self.trail_spread = 0.2   # Trailing stop distance
        self.q = 1                # Order quantity

        # Initialize orders
        self.logger.log("Initialising the order structure")
        self.long_entry = Order()
        self.long_tgt = Order()
        self.long_trail = Order()

        self.short_entry = Order()
        self.short_tgt = Order()
        self.short_trail = Order()

        # Long entry
        self.long_entry = "BUY"
        self.long_entry.orderType = "STP LMT"
        self.long_entry.totalQuantity = self.q
        self.long_entry.transmit = False

        # Long target
        self.long_tgt.action = "SELL"
        self.long_tgt.orderType = "LMT"
        self.long_tgt.totalQuantity = self.q
        self.long_tgt.transmit = False
        self.long_tgt.ocaGroup = "News_Long"

        # Long trail
        self.long_trail.action = "SELL"
        self.long_trail.orderType = "TRAIL"
        self.long_trail.totalQuantity = self.q
        self.long_trail.ocaGroup = "News_Long"
        self.long_trail.transmit = True

        # Short entry
        self.short_entry.action = "SELL"
        self.short_entry.orderType = "STP LMT"
        self.short_entry.totalQuantity = self.q
        self.short_entry.transmit = False

        # Short target
        self.short_tgt.action = "BUY"
        self.short_tgt.orderType = "LMT"
        self.short_tgt.totalQuantity = self.q
        self.short_tgt.ocaGroup = "News_Short"
        self.short_tgt.transmit = False

        # Short trail
        self.short_trail.action = "BUY"
        self.short_trail.orderType = "TRAIL"
        self.short_trail.totalQuantity = self.q
        self.short_trail.ocaGroup = "News_Short"
        self.short_trail.transmit = True

    def update_order_prices(self):
        """
        Updates order prices to current market state
        :return:
        """
        self.logger.log("Order price update not yet implemented")

    def transmit_orders(self):
        """
        Finalises the orders and transmits them to TWS
        :return:
        """
        self.logger.log("Order transmission not implemented")

    def tickPrice(self, req_id: TickerId, tick_type: TickType, price: float, attrib: TickAttrib):
        """
        Custom instrument price tick processing
        :param req_id:
        :param tick_type:
        :param price:
        :param attrib:
        :return:
        """
        # Here we need to add checking on the price levels and order adjustments.
        self.logger.log("Price tick data not yet implemented")


class Trader(TwsWrapper, TwsClient):
    """
    Main trader object for news trader
    """
    def __init__(self, symbol, expiry, sec_type, exchange):
        """
        Simple constructor for the trader class
        """
        self.logger = Logger(LogLevel.normal, "Trader")
        self.logger.log("Trader init")

        TwsWrapper.__init__(self)
        TwsClient.__init__(self, wrapper=self)

        # Instrument to be traded.
        self.inst = symbol
        self.exchange = exchange
        self.sec_type = sec_type
        self.expiry = expiry

    def req_data(self):
        """
        Requests market data for the instrument
        :return:
        """
        cont = Contract()
        cont.symbol = self.inst
        cont.exchange = self.exchange
        cont.secType = self.sec_type
        cont.lastTradeDateOrContractMonth = self.expiry

        self.logger.log("Requesting market data for the instrument")
        self.reqMktData(1, cont, "", False, False, [])

    def trade(self):
        """
        Main trading loop
        :return: nothing
        """
        self.logger.log("Entering main trading loop")
        self.logger.log("Shutting down main trading loop")


def main():
    """
    Main trading code and entry point for the trader

    :return: nothing
    """
    logger = Logger(LogLevel.normal, "NewsTrader")
    logger.log("News trader init")

    trader = Trader("CL", "201812", "FUT", "NYMEX")
    trader.connect("localhost", 4001, 12)
    trader.req_data()
    trader.trade()
    trader.disconnect()

    logger.log("News trader exiting")


# Main entry point for the news trader
if __name__ == "__main__":
    main()

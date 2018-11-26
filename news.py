"""
News trader implementation in Python

Peeter Meos, 8. November 2018
"""
# TODO: Somehow separate windows for logging and user input
from threading import Thread, Event
from typing import List
import time
from datetime import datetime
from datetime import timedelta
from ibapi.client import *
from ibapi.wrapper import *
import ibapi.order_condition as order_condition
from logger import *
import configparser
import getopt


class TraderStatus(Enum):
    """
    Statuses are as follows:
    COLD - trader is not on the market, no orders
    HOT - trader is on the market, with orders waiting for execution
    ACTIVE - at least one of the orders has been executed, we have a nonzero position
    """
    COLD = 1
    HOT = 2
    ACTIVE = 3

    def to_string(self) -> str:
        """
        Returns string value of the trader status
        :return: string
        """
        return str(self.name)


class TwsWrapper(EWrapper):
    """
    EWrapper extension for news trader
    """
    def __init__(self, config):
        """
        Simple constructor for the wrapper
        Also handles creation and initialisation of orders for the
        trading strategy
        """

        # First lets get started with logging
        self.logger = Logger(LogLevel.normal, "Wrapper")
        self.logger.log("Wrapper init")
        EWrapper.__init__(self)
        self.nextValidOrderId = -1
        self.orders = []

        # The settings for the order structure
        # At some later stage this also needs to be dynamic and be set somewhere else
        self.last_price = -1.0              # Last known price of the instrument
        self.set_price = -1.0               # The price that the order structure is set at
        self.entry_spread = float(config["entry.spread"])      # Spread for the order structure
        self.tgt_spread = float(config["tgt.spread"])          # Target distance
        self.trail_spread = float(config["trail.spread"])      # Trailing stop distance
        self.delta_adjust = float(config["delta.adjust"])      # After how much movement adjust price
        self.time_adjust = int(config["time.adjust"])        # Time step (ms) for order adjustment
        self.q = int(config["q"])                            # Order quantity
        self.kill_time = int(config["kill.time"])            # Trade kill time in seconds
        self.status = TraderStatus.COLD     # Set default trader status
        self.pos = 0
        self.price = 0
        self.pnl = 0

        # Initialize orders
        self.logger.log("Initialising the order structure")
        self.long_entry = Order()
        self.long_tgt = Order()
        self.long_trail = Order()
        self.long_time = Order()

        self.short_entry = Order()
        self.short_tgt = Order()
        self.short_trail = Order()
        self.short_time = Order()

        # Long entry
        self.long_entry.action = "BUY"
        self.long_entry.orderType = "STP LMT"
        self.long_entry.totalQuantity = self.q
        self.long_entry.transmit = True
        self.long_entry.outsideRth = True

        # Long target
        self.long_tgt.action = "SELL"
        self.long_tgt.orderType = "MIT"
        self.long_tgt.totalQuantity = self.q
        self.long_tgt.transmit = True
        self.long_tgt.outsideRth = True
        self.long_tgt.ocaGroup = "NewsLong"

        # Long trail
        self.long_trail.action = "SELL"
        self.long_trail.orderType = "TRAIL"
        self.long_trail.totalQuantity = self.q
        self.long_trail.ocaGroup = "NewsLong"
        self.long_trail.transmit = True  # Should be true
        self.long_trail.outsideRth = True

        # Long time stop
        self.long_time.action = "SELL"
        self.long_time.orderType = "MKT"
        self.long_time.totalQuantity = self.q
        self.long_time.ocaGroup = "NewsLong"
        self.long_time.transmit = True
        self.long_time.outsideRth = True

        # Short entry
        self.short_entry.action = "SELL"
        self.short_entry.orderType = "STP LMT"
        self.short_entry.totalQuantity = self.q
        self.short_entry.transmit = True
        self.short_entry.outsideRth = True

        # Short target
        self.short_tgt.action = "BUY"
        self.short_tgt.orderType = "MIT"
        self.short_tgt.totalQuantity = self.q
        self.short_tgt.ocaGroup = "NewsShort"
        self.short_tgt.transmit = True
        self.short_tgt.outsideRth = True

        # Short trail
        self.short_trail.action = "BUY"
        self.short_trail.orderType = "TRAIL"
        self.short_trail.totalQuantity = self.q
        self.short_trail.ocaGroup = "NewsShort"
        self.short_trail.transmit = True  # Should be true
        self.short_trail.outsideRth = True

        # Short time stop
        self.short_time.action = "BUY"
        self.short_time.orderType = "MKT"
        self.short_time.totalQuantity = self.q
        self.short_time.ocaGroup = "NewsShort"
        self.short_time.transmit = True
        self.short_time.outsideRth = True

    def nextValidId(self, order_id: int):
        """
        Updates the next valid order ID, when called by the API
        :param order_id: given by the TWS API
        :return: nothing
        """
        super().nextValidId(order_id)
        self.logger.log("Setting nextValidOrderId: "+str(order_id))
        self.nextValidOrderId = int(order_id)

    def get_orders(self) -> List[Order]:
        """
        Returns orders as a list
        :return: list of orders
        """
        return [self.long_entry, self.long_tgt, self.long_trail,
                self.short_entry, self.short_tgt, self.short_trail]

    def prepare_orders(self):
        """
        Finalises the orders and transmits them to TWS
        :return:
        """
        if self.last_price <= 0:
            return

        # Update order ids, set parent order ids
        o = self.nextValidOrderId

        self.orders = []

        # Populate orders

        self.long_entry.orderId = str(o)
        self.orders.append({"id": o})
        self.long_entry.ocaGroup = "News trader" + str(o)
        self.long_tgt.orderId = str(o + 1)
        self.orders.append({"id": o + 1})
        self.long_tgt.parentId = str(self.long_entry.orderId)
        self.long_trail.orderId = str(o + 2)
        self.orders.append({"id": o + 2})
        self.long_trail.parentId = str(self.long_entry.orderId)
        self.orders.append({"id": o + 3})
        self.long_time.parentId = str(self.long_entry.orderId)

        self.short_entry.orderId = str(o + 4)
        self.orders.append({"id": o + 4})
        self.short_entry.ocaGroup = "News trader" + str(o)
        self.short_tgt.orderId = str(o + 5)
        self.orders.append({"id": o + 5})
        self.short_tgt.parentId = str(self.short_entry.orderId)
        self.short_trail.orderId = str(o + 6)
        self.orders.append({"id": o + 6})
        self.short_trail.parentId = str(self.short_entry.orderId)
        self.orders.append({"id": o + 7})
        self.short_time.parentId = str(self.short_entry.orderId)

    def wrapper_price_update(self, set_price):
        """
        Updates the prices of the order structure
        :param set_price:
        :return:
        """
        # TODO Add time conditioned close. time in format 20181126 09:40:32 EET
        # Market orders don't work outside RTH?
        t = datetime.datetime.now() + timedelta(seconds=self.kill_time)
        time_condition = order_condition.Create(order_condition.OrderCondition.Time)
        time_condition.isMore = True
        time_condition.time = t.strftime("%y%m%d %H:%M:%S %Z")

        self.logger.log("Setting order structure around price " + str(set_price))
        self.set_price = set_price

        self.long_entry.lmtPrice = set_price + self.entry_spread
        self.long_entry.auxPrice = set_price + self.entry_spread
        self.long_tgt.auxPrice = set_price + self.tgt_spread
        # self.long_trail.trailStopPrice = set_price - self.trail_spread
        # self.long_trail.lmtPriceOffset = self.trail_spread
        self.long_trail.auxPrice = self.trail_spread  # Trailing amount
        # self.long_time.conditionsCancelOrder = True
        self.long_time.conditions.clear()
        self.long_time.conditions.append(time_condition)

        self.short_entry.lmtPrice = set_price - self.entry_spread
        self.short_entry.auxPrice = set_price - self.entry_spread
        self.short_tgt.auxPrice = set_price - self.tgt_spread
        # self.short_trail.trailStopPrice = set_price + self.trail_spread
        # self.short_trail.lmtPriceOffset = self.trail_spread
        self.short_trail.auxPrice = self.trail_spread  # Trailing amount
        # self.short_time.conditionsCancelOrder = True
        self.short_time.conditions.clear()
        self.short_time.conditions.append(time_condition)

    def tickPrice(self, req_id: TickerId, tick_type: TickType, price: float, attrib: TickAttrib):
        """
        Custom instrument price tick processing
        :param req_id:
        :param tick_type:
        :param price:
        :param attrib:
        :return:
        """
        # super().tickPrice(req_id, tick_type, price, attrib)
        # Here we just update the tick price, order adjustment is run in an
        # endless trader loop in a different thread. Scroll down to see the code.

        if tick_type == TickTypeEnum.LAST:
            self.logger.verbose("Updating last price to " + str(price))
            self.last_price = price

    def execDetails(self, req_id: int, contract: Contract, execution: Execution):
        """
        Execution details processing. Change trade status from HOT to ACTIVE and from
        ACTIVE to COLD, when either target or trail executes.
        :param req_id:
        :param contract:
        :param execution:
        :return:
        """
        self.logger.verbose("Execution details for req_id " + str(req_id))

    def execDetailsEnd(self, req_id: int):
        """
        End of execution details override
        :param req_id:
        :return:
        """
        self.logger.verbose("End of execution details for req_id " + str(req_id))

    def orderStatus(self, req_id: OrderId, status: str, filled: float,
                    remaining: float, avg_fill_price: float, perm_id: int,
                    parent_id: int, last_fill_price: float, client_id: int,
                    why_held: str, mkt_cap_price: float):
        """
        Order status processing for trader status changing
        :param req_id:
        :param status:
        :param filled:
        :param remaining:
        :param avg_fill_price:
        :param perm_id:
        :param parent_id:
        :param last_fill_price:
        :param client_id:
        :param why_held:
        :param mkt_cap_price:
        :return:
        """
        # TODO: For some reason, when entry executes, trader status does not change.
        # This part should be covered by OCA grouping on entry orders
        # For whatever reason order status on one filled order appears twice?

        # Update last known order status
        for i in range(len(self.orders)):
            j = self.orders[i]
            if j["id"] and j["id"] == req_id:
                if i == 0 or i == 4:
                    if self.status == TraderStatus.HOT and status == "Filled":
                        self.logger.log("Changing status to " + str(self.status))
                        self.status = TraderStatus.ACTIVE

                        # For bookkeeping
                        self.price = avg_fill_price
                        if i == 0:
                            self.pos = self.q
                        else:
                            self.pos = -self.q
                else:
                    if self.status == TraderStatus.ACTIVE and status == "Filled":
                        self.logger.log("Changing status to " + str(self.status))
                        self.status = TraderStatus.COLD

                        # For bookkeeping
                        if self.pos > 0:
                            self.pnl = self.pnl + self.q * (avg_fill_price - self.price)
                        else:
                            self.pnl = self.pnl + self.q * (self.price - avg_fill_price)
                        self.pos = 0
            j["status"] = status

        # self.logger.log("Order " + str(req_id) + " status " + status)

    def error(self, req_id: TickerId, error_code: int, error_string: str):
        """
        TWS error reporting
        :param req_id:
        :param error_code:
        :param error_string:
        :return:
        """
        # super().error(req_id, error_code, error_string)
        self.logger.error(str(req_id) + ":" + str(error_code) + ":" + error_string)

    def get_last_price(self):
        """
        Returns last known price of the instrument
        :return: last price
        """
        return self.last_price

    def set_trader_status(self, status: TraderStatus):
        """
        Sets trader status in wrapper
        :param status:
        :return:
        """
        self.logger.log("Setting trader status to " + status.to_string())
        self.status = status

    def get_trader_status(self) -> TraderStatus:
        """
        Returns trader status
        :return:
        """
        return self.status


class Trader(TwsWrapper, EClient):
    """
    Main trader object for news trader
    """
    def __init__(self, config):
        """
        Simple constructor for the trader class
        """
        self.logger = Logger(LogLevel.normal, "Trader")
        self.logger.log("Trader init")

        TwsWrapper.__init__(self, config)
        EClient.__init__(self, wrapper=self)

        self.connect(config["host"], int(config["port"]), int(config["id"]))
        thread = Thread(target=self.run)
        thread.start()
        setattr(self, "_thread", thread)

        # For communicating shutdown
        self.stop_trading_event = Event()

        # Wait until we can do stuff
        while self.nextValidOrderId == -1:
            time.sleep(1)

        # Instrument to be traded.
        self.cont = Contract()
        self.inst = config["symbol"]
        self.exchange = config["exchange"]
        self.sec_type = config["type"]
        self.expiry = config["expiry"]
        self.currency = config["currency"]

    def print_pnl(self):
        """
        Prints out current PnL for the trader
        :return:
        """
        self.logger.log("Current PnL is: " + '{:02.4f}'.format(self.pnl))

    def update_order_prices(self):
        """
        Updates order prices to current market state
        :return:
        """
        self.logger.log("Updating order prices")
        self.wrapper_price_update(self.get_last_price())
        for i in self.get_orders():
            self.placeOrder(i.orderId, self.cont, i)

    def req_data(self):
        """
        Requests market data for the instrument
        :return:
        """
        self.cont.symbol = self.inst
        self.cont.exchange = self.exchange
        self.cont.secType = self.sec_type
        self.cont.currency = self.currency
        self.cont.lastTradeDateOrContractMonth = self.expiry

        self.logger.log("Requesting market data for the instrument")
        self.reqContractDetails(2, self.cont)
        self.reqMktData(3, self.cont, "", False, False, [])

    def place_orders(self):
        """
        Opens orders for both sides: entry, target and trail stop
        If orders are already open, update the prices.
        Mechanics for TWS are the same.
        :return:
        """
        if self.status == TraderStatus.COLD:
            self.logger.log("Placing news trader orders")

        for i in self.get_orders():
            self.logger.verbose("Placing order " + str(i.orderId))
            self.placeOrder(i.orderId, self.cont, i)
        self.status = TraderStatus.HOT

    def trade(self):
        """
        Main trading loop
        :return: nothing
        """
        self.logger.log("Setting up orders")
        self.prepare_orders()
        self.wrapper_price_update(self.get_last_price())
        self.place_orders()
        self.logger.log("Entering main trading loop")

        adj_thread = Thread(target=self.update_loop)
        adj_thread.start()
        setattr(self, "_adj_thread", adj_thread)

        self.stop_trading_event.clear()

        user_input = ""
        while user_input != "Q":
            user_input = input("News trader (Quit, Hot, Cold, Status):").upper()
            if user_input == "S":
                self.logger.log("Status is " + str(self.get_trader_status()))
            if user_input == "H":
                # If cold, enter new orders, start updating prices
                if self.get_trader_status() == TraderStatus.COLD:
                    o = self.nextValidOrderId
                    self.reqIds(0)
                    while self.nextValidOrderId == o:
                        time.sleep(0.1)

                    self.prepare_orders()
                    self.place_orders()
                    self.set_trader_status(TraderStatus.HOT)

                # Do nothing if we are active
                if self.get_trader_status() == TraderStatus.ACTIVE:
                    self.logger.error("We have active positions, will not change state!")

            if user_input == "C":
                # If we are active, show respective error message
                if self.get_trader_status() == TraderStatus.ACTIVE:
                    self.logger.error("Trader active, there are open positions!")

                # If we have open positions, close them
                if self.pos != 0:
                    self.logger.log("Closing open positions")
                    self.close_position()

                # Cancel all open orders
                if self.get_trader_status() == TraderStatus.HOT or self.get_trader_status() == TraderStatus.ACTIVE:
                    self.cancel_orders()
                self.set_trader_status(TraderStatus.COLD)

        self.logger.log("Shutting down main trading loop")
        self.stop_trading_event.set()

    def cancel_orders(self):
        """
        Cancels all open orders
        :return:
        """
        # TODO track order statuses and cancel only those orders that are active
        for i in self.orders:
            if i["id"] and i["status"] and not i["status"] == "Cancelled":
                self.cancelOrder(i["id"])

    def close_position(self):
        """
        Close any open positions
        :return:
        """
        self.logger.log("Closing open positions not implemented")

    def update_loop(self):
        """
        Thread for updating the order structure
        :return:
        """
        while not self.stop_trading_event.is_set():
            time.sleep(self.time_adjust / 1000)
            if self.status == TraderStatus.HOT and abs(self.set_price - self.last_price) > self.delta_adjust:
                self.wrapper_price_update(self.last_price)
                self.place_orders()

    def stop(self):
        """
        Stops all streaming data, cancels all orders
        Closes the TWS connection
        :return:
        """
        self.logger.log("Trader closing down")
        # If we have active orders, cancel them
        if self.status == TraderStatus.HOT:
            self.cancel_orders()

        # Stop market data
        self.cancelMktData(3)  # That 3 is deprecated and means nothing

        # Disconnect from the API
        self.disconnect()

        # Print out the final PnL:
        self.print_pnl()


def main(argv):
    """
    Main trading code and entry point for the trader

    :return: nothing
    """
    logger = Logger(LogLevel.normal, "NewsTrader")
    logger.log("News trader init")

    # Read command line
    cf = "config.sample"
    try:
        opts, args = getopt.getopt(argv, "c:", [])
    except getopt.GetoptError:
        logger.error("Invalid options")
        sys.exit(2)

    for opt, arg in opts:
        if opt == "-c":
            cf = arg

    # Configuration from file
    logger.log("Reading parameters from: " + str(cf))
    config = configparser.ConfigParser()
    config.read(cf)

    trader = Trader(config['news'])
    trader.req_data()
    time.sleep(6)
    trader.trade()
    trader.stop()

    logger.log("News trader exiting")


# Main entry point for the news trader
if __name__ == "__main__":
    main(sys.argv[1:])

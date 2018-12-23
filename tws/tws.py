"""
TWS Code Framework

Author: Peeter Meos
Date: 14. December 2018
"""

from ibapi.wrapper import *
from ibapi.client import *
from ibapi.contract import Contract
from utils.logger import Logger, LogLevel
from threading import Thread
import time


class TwsException(Exception):
    """
    Dummy own exception implementation
    """
    pass


class TwsClient(EClient):
    """
    Extension of EClient class
    """
    def connect(self, host, port, client_id):
        """
        Connection override
        :param host:
        :param port:
        :param client_id:
        :return:
        """
        c = 0
        super().connect(host, port, client_id)
        while not self.isConnected():
            time.sleep(0.1)
            c = c + 1
            if c >= 10:
                raise TwsException


class TwsWrapper(EWrapper):
    """
    Extension of EWrapper class
    """
    pass


class TwsTool(TwsWrapper, TwsClient):
    """
    TWS API framework and basic functionality
    """
    def __init__(self, name="TwsTool", log_level=LogLevel.normal):
        """
        Standard constructor
        :param name:
        :param log_level
        """
        TwsClient.__init__(self, wrapper=self)
        TwsWrapper.__init__(self)

        self.logger = Logger(log_level, name)
        self.nextId = -1
        self.thread = Thread(target=self.run)

        self.req_val_id = -1
        self.req_val = 0

    def nextValidId(self, order_id: int):
        """
        Next order ID update
        :param order_id:
        :return:
        """
        self.logger.verbose("Next ID received: " + str(order_id))
        self.nextId = int(order_id)

    def orderStatus(self, order_id: OrderId, status: str, filled: float,
                    remaining: float, avg_fill_price: float, perm_id: int,
                    parent_id: int, last_fill_price: float, client_id: int,
                    why_held: str, mkt_cap_price: float):
        """
        Order status callback
        :param order_id:
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
        self.logger.verbose("Order " + str(order_id) + " status " + status)

    def openOrder(self, order_id: OrderId, contract: Contract, order: Order,
                  order_state: OrderState):
        """
        Open order callback
        :param order_id:
        :param contract:
        :param order:
        :param order_state:
        :return:
        """
        self.logger.verbose("Order " + str(order_id) + " " +
                            order.action + " " + str(order.totalQuantity) +
                            " open for " + contract.symbol)

    def error(self, req_id: TickerId, error_code: int, error_string: str):
        """
        Error printing override
        :param req_id:
        :param error_code:
        :param error_string:
        :return:
        """
        if error_code == 2104 or error_code == 2106:
            # These two error codes are normal market data connection messages
            # They are not really errors at all
            self.logger.verbose(str(error_code) + ":" + error_string)
        else:
            self.logger.error(str(error_code) + ":" + error_string)

    def connect(self, host: str, port: int, con_id):
        """
        Connect to TWS override
        :param host:
        :param port:
        :param con_id:
        :return:
        """
        self.logger.log("Connecting to TWS at " + host + ":" + str(port))
        TwsClient.connect(self, host, port, con_id)

        self.logger.verbose("Starting event processing thread")
        self.thread.start()
        setattr(self, "_thread", self.thread)

        # Wait until next id
        self.logger.verbose("Waiting for next order ID")
        while self.nextId == -1:
            time.sleep(0.1)

    def disconnect(self):
        """
        Shot down the TWS connection
        :return:
        """
        super().disconnect()

    def get_contract_id(self, cont: Contract):
        """
        Requests and returns contract id for a given contract
        :param cont:
        :return: contract id
        """
        self.logger.verbose("Request contract details for " + cont.symbol)
        self.req_val_id = self.nextId
        self.req_val = 0
        self.reqContractDetails(self.req_val_id, cont)
        while self.req_val == 0:
            time.sleep(0.01)

        return self.req_val

    def get_price_snapshot(self, cont: Contract):
        """
        Requests and returns the latest market price for a given contract
        :param cont:
        :return: last known price
        """
        self.logger.verbose("Requesting snapshot data for " + cont.symbol)
        self.req_val_id = self.nextId
        self.req_val = 0
        self.reqMktData(self.req_val_id, cont, "", True, False, [])
        while self.req_val == 0:
            time.sleep(0.01)

        return self.req_val

    def contractDetails(self, req_id: int, contract_details: ContractDetails):
        """
        Wait and save contract details
        :param req_id:
        :param contract_details:
        :return:
        """
        if req_id == self.req_val_id:
            self.req_val = contract_details.contract.conId

    def tickPrice(self, req_id: TickerId, tick_type: TickType, price: float,
                  attrib: TickAttrib):
        """
        Wait and save last tick price
        :param req_id:
        :param tick_type:
        :param price:
        :param attrib:
        :return:
        """
        if req_id == self.req_val_id and tick_type == 4:
            self.req_val = price

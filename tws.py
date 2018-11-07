"""
TWS Code
"""
from ibapi.wrapper import *
from ibapi.client import *
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

    def req_option_chain(self):
        """
        Requesting option chain data from the TWS
        :return: nothing, data comes via wrapper events
        """
        self.logger.log("Requesting option chain")

        inst = Contract()
        inst.secType = "FOP"
        inst.exchange = "NYMEX"
        inst.symbol = "CL"

        self.reqContractDetails(213, inst)
        # Request a snapshot
        self.reqMktData(214, inst, "", True, False, [])


if __name__ == "__main__":
    print("This is not the code you are supposed to run. Import it instead")


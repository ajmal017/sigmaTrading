"""
Simple logging functionality

Peeter Meos, 7 November 2018
"""
from enum import Enum
import datetime


class LogLevel(Enum):
    """
    Simple log level enumeration class
    """
    silent = 0
    error = 1
    normal = 2
    verbose = 3

    # We need to add custom comparison operators
    def __ge__(self, other):
        if self.__class__ is other.__class__:
            return self.value >= other.value
        return False

    def __gt__(self, other):
        if self.__class__ is other.__class__:
            return self.value > other.value
        return False

    def __le__(self, other):
        if self.__class__ is other.__class__:
            return self.value <= other.value
        return False

    def __lt__(self, other):
        if self.__class__ is other.__class__:
            return self.value < other.value
        return False


class Logger:
    """
    Implementation of simple logging functionality
    TODO: Logging into file, logging into a database
    """
    def __init__(self, l: LogLevel, name):
        self.logLevel = l
        self.name = name

    def my_print(self, l: LogLevel, s):
        """
        Alternative generic printout
        :param l: log level
        :param s: string to be logged
        :return: nothing
        """
        print(datetime.datetime.now(), ":", l.name, ":", self.name, ":", s)

    def log(self, s):
        """
        Normal level logging
        :param s: String to be logged
        :return: nothing
        """
        if self.logLevel >= LogLevel.normal:
            self.my_print(LogLevel.normal, s)

    def error(self, s):
        """
        Logs an error
        :param s: String to be logged
        :return: nothing
        """
        if self.logLevel >= LogLevel.error:
            self.my_print(LogLevel.error, s)

    def verbose(self, s):
        """
        Logs a verbose message
        :param s: string to be logged
        :return: nothing
        """
        if self.logLevel >= LogLevel.verbose:
            self.my_print(LogLevel.verbose, s)

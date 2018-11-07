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
    """
    def __init__(self, l: LogLevel, name):
        self.logLevel = l
        self.name = name

    def myPrint(self, l: LogLevel, s):
        print(datetime.datetime.now(), ":", self.name, ":", l.name, ":", s)

    def log(self, s):
        """
        Normal level logging
        :param s: String to be logged
        :return: nothing
        """
        if self.logLevel >= LogLevel.normal:
            self.myPrint(LogLevel.normal, s)

    def error(self, s):
        """
        Logs an error
        :param s: String to be logged
        :return: nothing
        """
        if self.logLevel >= LogLevel.error:
            self.myPrint(LogLevel.error, s)

    def verbose(self, s):
        """
        Logs a verbose message
        :param s: string to be logged
        :return: nothing
        """
        if self.logLevel >= LogLevel.verbose:
            self.myPrint(LogLevel.verbose, s)

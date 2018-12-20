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
    def __init__(self, l: LogLevel, name: str, fn=""):
        """
        Simple constructor for logging to screen
        :param l: logging level
        :param name: name of for the logger
        :param fn: filename for logging, if empty then log to screen
        """
        self.logLevel = l
        self.name = name
        self.fn = fn
        if not self.fn == "":
            self.f = open(fn, 'a')
        else:
            self.f = None

    def my_print(self, l: LogLevel, s):
        """
        Alternative generic printout
        :param l: log level
        :param s: string to be logged
        :return: nothing
        """
        if self.f is not None:
            print(str(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")) + " :" +
                  l.name + ":" + self.name + ":" + s, file=self.f)
        else:
            print(str(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")) + " :" +
                  l.name + ":" + self.name + ":" + s)

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

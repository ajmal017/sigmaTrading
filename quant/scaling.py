"""
Functions for scaling to -1 to 1 scale and back to original scale.
In this context used for margin estimations.

Author: Peeter Meos
Date: 3. December 2018
"""
import numpy as np


def scale11(x):
    """
    Scales values to -1 ... to 1 scale
    :param x: numpy array
    :return:
    """
    # x = np.array(x)
    v = (2 * ((x - np.amin(x))/(np.amax(x) - np.amin(x)))) - 1
    return v


def rev_scale11(y, min_x, max_x):
    """
    Reverses the -1 to 1 scale back to original scale
    :param y: Scaled vector
    :param min_x: Original minimum
    :param max_x: Original maximum
    :return:
    """
    # y = np.array(y)
    return min_x + ((y + 1) * (max_x - min_x)) / 2

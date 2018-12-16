"""
Code for calculation of more and less esoteric greeks.

Author: Peeter Meos
Date: 3. December 2018
"""
from scipy.stats import norm
import numpy as np


# TODO: Implement value calculation for Black and Scholes
def val(s, k, r, q, d1, d2, t, side: str):
    """
    Standard option value calculation for Black and Scholes
    :param s: spot
    :param k: strike
    :param r:
    :param q:
    :param d1:
    :param d2:
    :param t: time to expiry in years
    :param side: string defining whether put or call
    :return:
    """
    v = np.where(side == "P",
                 np.exp(-r * t) * k * phi(-d2) - s * np.exp(-q * t) * phi(-d1),
                 s * np.exp(-q * t) * phi(d1) - np.exp(-r * t) * k * phi(d2)
    )
    return v


def d_one(s, k, r, q, sigma, t):
    """
    Standard D1 calculation for Black and Scholes
    :param s: spot
    :param k: strike
    :param r:
    :param q:
    :param sigma: implied volatility
    :param t: time to expiry
    :return:
    """
    r = np.float(r)
    q = np.float(q)
    v = (np.log(s / k) + (r - q + sigma * sigma / 2) * t) / (sigma * np.sqrt(t))
    return v


def d_two(s, k, r, q, sigma, t):
    """
    Standard D2 calculation for Black and Scholes
    :param s: spot
    :param k: strike
    :param r:
    :param q:
    :param sigma: implied volatility
    :param t: time to expiry
    :return:
    """
    v = d_one(s, k, r, q, sigma, t) - sigma * np.sqrt(t)
    return v


def phi(x):
    """
    Assistant function phi(x)
    :param x:
    :return:
    """
    v = np.exp(-(x*x)/2) / np.sqrt(2 * np.pi)
    return v


def vega(s, k, r, q, sigma, t):
    """
    Calculates vega (that is d price / d sigma)
    :param s: spot
    :param k: strike
    :param r:
    :param q:
    :param sigma: implied volatility
    :param t: time to expiry
    :return:
    """
    v = k * np.exp(-r * t) * phi(d_two(s, k, r, q, sigma, t)) * np.sqrt(t)
    return v


def speed(gamma, s, d1, sigma, t):
    """
    Calculates d gamma / d price
    :param gamma:
    :param s: spot
    :param d1:
    :param sigma: implied volatility
    :param t: time to expiry
    :return:
    """
    v = (-(gamma / s) * ((d1 / (sigma * np.sqrt(t))) + 1))
    return v


def vanna(v, s, d1, sigma, t):
    """
    Calculates d delta / d sigma
    :param v:
    :param s:
    :param d1:
    :param sigma:
    :param t:
    :return:
    """
    v = v / s * (1 - d1 / (sigma * np.sqrt(t)))
    return v


def zomma(gamma, d2, d1, sigma):
    """
    Calculates d gamma / d sigma
    :param gamma:
    :param d2:
    :param d1:
    :param sigma: implied volatility
    :return:
    """
    v = gamma * (d2 * d1 - 1) / sigma
    return v


def charm(side, d1, d2, r, q, sigma, t):
    """
    Calculates charm (change of delta over time)
    that is: d delta / d time
    :param side: "c" or "p"
    :param d1:
    :param d2:
    :param r:
    :param q:
    :param sigma: implied volatility
    :param t: time to expiry
    :return:
    """
    v1 = np.exp(-q * t) * phi(d1) * (2 * (r - q) * t - d2 * sigma * np.sqrt(t)) / (2 * t * sigma * np.sqrt(t))
    # TODO: This normal cdf is not vectorised. Thus possibly does not work properly
    v = q * np.exp(-q * t) * norm.cdf(d1) - v1 if side == "c" else -q * np.exp(-q * t) * norm.cdf(-d1) - v1
    return v


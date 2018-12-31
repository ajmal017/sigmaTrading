"""
Code for calculation of more and less esoteric greeks.

Author: Peeter Meos
Date: 3. December 2018
"""
from scipy.stats import norm
import numpy as np
import pandas as pd


def val(s, k, r, q, sigma, t, side: str):
    """
    Standard option value calculation for Black and Scholes
    :param s: spot
    :param k: strike
    :param r:
    :param q:
    :param sigma:
    :param t: time to expiry in years
    :param side: string defining whether put or call
    :return:
    """
    d1 = d_one(s, k, r, q, sigma, t)
    d2 = d_two(s, k, r, q, sigma, t)
    v = np.where(side == "p",
                 np.exp(-r * t) * k * norm.cdf(-d2) - s * np.exp(-q * t) * norm.cdf(-d1),
                 s * np.exp(-q * t) * norm.cdf(d1) - np.exp(-r * t) * k * norm.cdf(d2))
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


def delta(s, k, r, q, sigma, t, side: str):
    """
    Calculates Black Scholes delta
    :param s:
    :param k:
    :param r:
    :param q:
    :param sigma:
    :param t:
    :param side: option side
    :return:
    """
    r = np.where(side == "c", np.exp(-q * t) * norm.cdf(d_one(s, k, r, q, sigma, t)),
                 -np.exp(-q * t) * norm.cdf(-d_one(s, k, r, q, sigma, t)))
    return r


def gamma(s, k, r, q, sigma, t):
    """
    Calculates Black Scholes gamma
    :param s:
    :param k:
    :param r:
    :param q:
    :param sigma:
    :param t:
    :return:
    """
    r = np.exp(-q * t) * (phi(d_one(s, k, r, q, sigma, t))) / (s * sigma * np.sqrt(t))
    return r


def theta(s, k, r, q, sigma, t, side: str, unit="day"):
    """
    Calculates Black Scholes theta
    :param s:
    :param k:
    :param r:
    :param q:
    :param sigma:
    :param t:
    :param side:
    :param unit: unit of time, default day, year otherwise
    :return:
    """
    c1 = -np.exp(-q * t) * (s * phi(d_one(s, k, r, q, sigma, t)) * sigma) / (2 * np.sqrt(t))
    c2 = r * k * np.exp(-r * t)
    c3 = q * s * np.exp(-q * t)
    r = np.where(side == "c", c1 - c2 * norm.cdf(d_two(s, k, r, q, sigma, t)) +
                 c3 * norm.cdf(d_one(s, k, r, q, sigma, t)),
                 c1 + c2 * norm.cdf(-d_two(s, k, r, q, sigma, t)) - c3 * norm.cdf(-d_one(s, k, r, q, sigma, t)))
    if unit == "day":
        r = r / 365.0
    return r


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


def speed(g, s, d1, sigma, t):
    """
    Calculates d gamma / d price
    :param g: gamma
    :param s: spot
    :param d1:
    :param sigma: implied volatility
    :param t: time to expiry
    :return:
    """
    v = (-(g / s) * ((d1 / (sigma * np.sqrt(t))) + 1))
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


def zomma(g, d2, d1, sigma):
    """
    Calculates d gamma / d sigma
    :param g:
    :param d2:
    :param d1:
    :param sigma: implied volatility
    :return:
    """
    v = g * (d2 * d1 - 1) / sigma
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
    v = np.where(side == "c", q * np.exp(-q * t) * norm.cdf(d1) - v1,
                 -q * np.exp(-q * t) * norm.cdf(-d1) - v1)
    return v


def norm_cdf_approx(x: float):
    """
    Approximation of Normal CDF to avoid the use of scipy
    :param x:
    :return:
    """
    import math

    ret = 1 / (1 + math.exp(-(0.07056 * math.pow(x, 3) + 1.5976 * x)))
    return ret


def norm_pdf_approx(x: float):
    """
    Approximation of Normal PDF to avoid the use of scipy
    :param x:
    :return:
    """
    import math
    n = range(1, 5)

    res1 = math.exp(-x*x/2)
    res2 = 1 / x

    for i in n:
        res2 += ((math.pow(-1, i) * math.factorial(2*i - 1)) /
                 (math.pow(2, i - 1) * math.factorial(i - 1)) *
                 1 / (math.pow(x, (2*i + 1))))
    return res1 * res2


def build_curves(df: pd.DataFrame, greeks: list, pos_col: str) -> pd.DataFrame:
    """
    Creates futures' curves based on given data
    :param df: DataFrame with underlying data, need the usual s, k, sigma, t
    :param greeks:  returns greeks as snapshot and at closest expiry
    :param pos_col: Position column name
    :return:
    """
    df_tmp = df[df[pos_col] != 0].copy()

    # TODO: Make these ranges adjustable
    # TODO: write the code to work with numpy vectors and return a dict of vectors. Ie. get rid of pandas.
    r = np.array(range(-100, 100, 1)) / 1000
    df_out = pd.DataFrame(r)
    df_out.columns = ["r"]
    df_out.index = r
    for i in greeks:
        df_out[i] = 0

    t_min = min(df_tmp["Days"])

    for i, row in df_tmp.iterrows():
        spot = np.float(row["Underlying Price"])
        p = np.float(row[pos_col])
        s = row["Vol"]
        k = row["Strike"]
        t = row["Days"]
        px = row["Mid"]
        t1 = t - 1/365
        t1 = np.where(t1 == 0, 0.00001, t1)
        t_e = t - t_min
        t_e = np.where(t_e == 0, 0.00001, t_e)
        if "Val" in greeks:
            df_out["Val"] = df_out["Val"].add(p * val((1 + r) * spot, k,  0.01, 0, s, t, row["Side"]) - p*px)
        if "Val_p1" in greeks:
            df_out["Val_p1"] = df_out["Val"].add(p * val((1 + r) * spot, k,  0.01, 0, s, t1, row["Side"]) - p*px)
        if "Val_exp" in greeks:
            df_out["Val_exp"] = df_out["Val_exp"].add(p * val((1 + r) * spot, k,  0.01, 0, s, t_e, row["Side"]) - p*px)
        if "Delta" in greeks:
            df_out["Delta"] = df_out["Delta"].add(p * delta((1 + r) * spot, k,  0.01, 0, s, t, row["Side"]))
        if "Gamma" in greeks:
            df_out["Gamma"] += p * gamma((1 + r) * spot, k,  0.01, 0, s, t)
        if "Theta" in greeks:
            df_out["Theta"] += p * theta((1 + r) * spot, k,  0.01, 0, s, t, row["Side"])
        if "Vega" in greeks:
            df_out["Vega"] += p * vega((1 + r) * spot, k,  0.01, 0, s, t)

    df_out["pct"] = r
    return df_out

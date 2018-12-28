"""
Unit testing for greeks calculation

Author: Peeter Meos
Date: 28. December 2018
"""
import unittest
from quant import greeks
import numpy as np


class GreekTests(unittest.TestCase):
    def test_d1(self):
        s = 45.0
        k = 50.0
        r = 0.02
        q = 0.01
        sigma = 0.55
        t = 0.25

        self.assertEqual(-0.23653824, round(greeks.d_one(s, k, r, q, sigma, t), 8))

    def test_d2(self):
        s = 45.0
        k = 50.0
        r = 0.02
        q = 0.01
        sigma = 0.55
        t = 0.25

        self.assertEqual(-0.51153824, round(greeks.d_two(s, k, r, q, sigma, t), 8))

    def test_value(self):
        s = 45.0
        k = 50.0
        r = 0.02
        q = 0.01
        sigma = 0.55
        t = 0.25

        self.assertEqual(3.09873969, np.round(greeks.val(s, k, r, q, sigma, t, "c"), 8))
        self.assertEqual(7.96172314, np.round(greeks.val(s, k, r, q, sigma, t, "p"), 8))

    def test_gamma(self):
        s = 45.0
        k = 50.0
        r = 0.02
        q = 0.01
        sigma = 0.55
        t = 0.25

        self.assertEqual(0.03127013, np.round(greeks.gamma(s, k, r, q, sigma, t), 8))

    def test_theta(self):
        s = 45.0
        k = 50.0
        r = 0.02
        q = 0.01
        sigma = 0.55
        t = 0.25

        self.assertEqual(-9.69795076, np.round(greeks.theta(s, k, r, q, sigma, t, "c", unit="year"), 8))
        self.assertEqual(-9.15181469, np.round(greeks.theta(s, k, r, q, sigma, t, "p", unit="year"), 8))

    def test_vega(self):
        s = 45.0
        k = 50.0
        r = 0.02
        q = 0.01
        sigma = 0.55
        t = 0.25

        self.assertEqual(8.70677629, np.round(greeks.vega(s, k, r, q, sigma, t), 8))

    def test_vanna(self):
        s = 45.0
        k = 50.0
        r = 0.02
        q = 0.01
        sigma = 0.55
        t = 0.25
        v = greeks.vega(s, k, r, q, sigma, t)
        d1 = greeks.d_one(s, k, r, q, sigma, t)

        self.assertEqual(0.35990699, np.round(greeks.vanna(v, s, d1, sigma, t), 8))


if __name__ == "__main__":
    unittest.main()

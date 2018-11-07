"""
Portfolio optimisation code for trader
"""
import pandas as pd
from pyomo.environ import *
from pyomo.opt import *


def optimise_portfolio(df: pd.DataFrame):
    """
    Runs portfolio optimisation
    :param df: Data frame with option chain data
    :return: data frame with positions to be opened or closed
    """
    print("Running portfolio optimisation")
    print(df.describe())

    model = ConcreteModel()

    sl = pyomo.opt.SolverFactory("glpk")
    sl.solve(model)

    return


if __name__ == "__main__":
    print("This code is not to be run directly, import it instead.")


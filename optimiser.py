"""
Portfolio optimisation code ported mostly from R

Author: Peeter Meos, Sigma Research OÜ
Date: 2. December 2018
"""
from gams import *
import configparser
import pandas as pd
import numpy as np
from quant import greeks
from gms import data

"""
createGDX <- function(in.fn, in.gdx, opt, ignore.existing = FALSE) {

  
  df <- addMargins(df, opt)
  
  df$Month <- factor(df$Days, levels = unique(df$Days), labels = 1:length(unique(df$Days)))

  if (ignore.existing == TRUE) {
    df$long <- df$short <- 0 
  } else {
    df$long  <- ifelse(df$Position > 0,  df$Position, 0)
    df$short <- ifelse(df$Position < 0, -df$Position, 0)
  }

  return(df)
}
"""


class Optimiser:
    def __init__(self):
        # Get the config
        cf = "config.sample"
        self.config = configparser.ConfigParser()
        self.config.read(cf)
        gams_path = self.config["optimiser"]["gams"]
        self.opt = self.config["optimiser"]

        self.ws = GamsWorkspace(system_directory=gams_path,
                                debug=DebugLevel.KeepFiles,
                                working_directory="./tmp/")
        self.db = self.ws.add_database()

    def export_gdx(self):
        """
        Composes dataset for optimisation and exports it as GDX
        Two options - whether we get it from a CSV or from DynamoDB
        :return:
        """
        df = pd.read_csv("data/181105 options.csv", na_values="NoMD")

        # Eliminate all NA
        # df.loc[df['column_name'].isin(some_values)]
        df = df[pd.notnull(df['Mid'])]
        df = df[pd.notnull(df['Delta'])]
        df = df[pd.notnull(df['Gamma'])]
        df = df[pd.notnull(df['Theta'])]
        df = df[pd.notnull(df['Vega'])]
        df = df[pd.notnull(df['Implied Vol. %'])]
        # TODO: The following need to be fixed probably
        # df['Position'] = np.where(df['Position'].isnull(), 0, df['Position'])

        # Add sides
        df['Financial Instrument'] = df['Financial Instrument'].astype(str)
        df['Side'] = np.where(df['Financial Instrument'].str.contains("PUT"), "p", "c")

        df['Put'] = np.where(df['Side'] == "p", 1, 0)
        df['Call'] = np.where(df['Side'] == "c", 1, 0)

        # TODO: This also probably does not work
        df['long'] = np.where(df['Position'] > 0, df['Position'], 0)
        df['short'] = np.where(df['Position'] < 0, -df['Position'], 0)

        # Volatility in percent
        df['Days'] = df['Days to Last Trading Day'] / 365
        df = df[df['Implied Vol. %'] != "N/A"]
        df['Vol'] = df['Implied Vol. %']
        df['Vol'] = df['Implied Vol. %'].str.replace('%', '')
        df['Vol'] = df['Vol'].astype(float) / 100
        # TODO For whatever reason the following row does not work
        # df = df[pd.notnull(df['Vol'])]

        # Strikes
        df['Strike'] = df['Financial Instrument'].str.split(" ").map(lambda x: x[4])
        df['Strike'] = df['Strike'].astype(float)

        # Add greeks
        df['Underlying Price'] = df['Underlying Price'].as_matrix()
        df['Strike'] = df['Strike'].as_matrix()
        df['Vol'] = df['Vol'].as_matrix()
        df['Days'] = df['Days'].as_matrix()
        df['d1'] = greeks.d_one(df['Underlying Price'], df['Strike'], 0.01, 0, df['Vol'], df['Days'])
        df['d2'] = greeks.d_two(df['Underlying Price'], df['Strike'], 0.01, 0, df['Vol'], df['Days'])
        df['Speed'] = greeks.speed(df['Gamma'], df['Underlying Price'], df['d1'], df['Vol'], df['Days'])
        df['Vanna'] = greeks.vanna(df['Vega'], df['Underlying Price'], df['d1'], df['Vol'], df['Days'])
        df['Zomma'] = greeks.zomma(df['Gamma'], df['d2'], df['d1'], df['Vol'])

        # Margins
        # TODO: Margins are yet to me implemented
        #  df <- addMargins(df, opt)
        df["Marg l"] = 0
        df["Marg s"] = 0

        # Create sets for data
        data.create_set(self.db, "s_greeks", "List of greeks",
                        ["delta", "gamma", "theta", "vega", "speed", "vanna", "zomma"])
        data.create_set(self.db, "s_names", "Option names", df["Financial Instrument"])
        data.create_set(self.db, "s_side", "Position side", ["long", "short"])

        levels, unis = pd.factorize(df['Days'])
        df['Month'] = list(levels + 1)

        data.create_set(self.db, "s_month", "Contract months",
                        range(1, len(unis) + 1))

        # So now lets create the scalars
        data.create_scalar(self.db, "v_multiplier", "Instrument multiplier", self.opt["mult"])
        data.create_scalar(self.db, "v_max_delta", "Maximum delta allowed", self.opt["max.delta"])
        data.create_scalar(self.db, "v_max_gamma", "Maximum gamma allowed", self.opt["max.gamma"])
        data.create_scalar(self.db, "v_min_theta", "Minimum theta allowed", self.opt["min.theta"])
        data.create_scalar(self.db, "v_max_vega", "Maximum vega allowed", self.opt["max.vega"])
        data.create_scalar(self.db, "v_max_speed", "Maximum speed allowed", self.opt["max.speed"])
        data.create_scalar(self.db, "v_max_pos", "Maximum position allowed", self.opt["max.pos"])
        data.create_scalar(self.db, "v_max_pos_tot", "Maximum number of contracts", self.opt["max.pos.tot"])
        data.create_scalar(self.db, "v_alpha", "Relative importance of theta in obj function", self.opt["alpha"])
        data.create_scalar(self.db, "v_trans_cost", "Transaction cost for one contract", self.opt["trans.cost"])
        data.create_scalar(self.db, "v_max_margin", "Maximum margin allowed", self.opt["max.margin"])
        data.create_scalar(self.db, "v_max_spread", "Maximum bid ask spread allowed", self.opt["max.spread"])
        data.create_scalar(self.db, "v_min_days", "Minimum days to expiry allowed", self.opt["min.days"])
        data.create_scalar(self.db, "v_max_trades", "Maximum rebalancing trades allowed", self.opt["max.trades"])
        data.create_scalar(self.db, "v_max_pos_mon", "Maximum monthly open positions allowed", self.opt["max.pos.mon"])

        # Parameter now the multi-dimensional parameters
        data.create_parameter(self.db, "p_y", "Existing position data",
                              [df["Financial Instrument"], ["long", "short"]], "full",
                              df[["Financial Instrument", "long", "short"]])
        data.create_parameter(self.db, "p_greeks", "Greeks data",
                              [df["Financial Instrument"],
                               ["delta", "gamma", "theta", "vega", "speed", "vanna", "zomma"]],
                              "full",
                              df[["Financial Instrument", "Delta", "Gamma",
                                  "Theta", "Vega", "Speed", "Vanna", "Zomma"]])
        data.create_parameter(self.db, "p_margin", "Margin data for options",
                              [df["Financial Instrument"], ["long", "short"]],
                              "full", df[["Financial Instrument", "Marg l", "Marg s"]])
        data.create_parameter(self.db, "p_side", "Option side (put/call)",
                              [df["Financial Instrument"], ["o_put", "o_call"]], "full",
                              df[["Financial Instrument", "Put", "Call"]])
        data.create_parameter(self.db, "p_spread", "Bid ask spread", [df["Financial Instrument"]], "sparse",
                              df["Spread"])
        data.create_parameter(self.db, "p_days", "Days until expiry", [df["Financial Instrument"]], "sparse",
                              df["Days"] * 365)
        data.create_parameter(self.db, "p_months", "Months until expiry", [df["Financial Instrument"]], "sparse",
                              df["Month"])

        # All done, now export that to the GDX file
        self.db.export("input.gdx")

    def run_gams(self):
        """
        Retrieves optimisation model from the model repo and runs it
        :return:
        """
        model = self.ws.add_job_from_file("spo.gms")
        opt = self.ws.add_options()
        model.run()

    def import_gdx(self, fn: str):
        """
        Imports optimisation results from the GDX file
        :param fn: name and path of the GDX gdx file
        :return:
        """
        print("Importing from " + fn)
        db_out = self.ws.add_database_from_gdx(fn)
        return db_out

    def save_results_dynamo(self):
        """
        Saves optimisation results to DynamoDB
        :return:
        """
        print("Not implemented")


def main():
    """
    Main optimisation code
    :return:
    """
    o = Optimiser()
    o.export_gdx()
    o.run_gams()
    o.import_gdx("output.gdx")
    # o.save_results_dynamo()


if __name__ == "__main__":
    main()

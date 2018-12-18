"""
Portfolio optimisation code ported mostly from R

Author: Peeter Meos, Sigma Research OÜ
Date: 2. December 2018
"""
from gams import *
from datetime import datetime
import pandas as pd
import numpy as np
from strategy import PortfolioStrategy
from quant import greeks, margins, nnet
from gms import data, code
import boto3
import json
import utils
from utils import logger
from utils.logger import LogLevel
from tws import tools
import argparse


class Optimiser(PortfolioStrategy):
    def __init__(self, cf: str, loglevel: LogLevel = LogLevel.normal):
        """
        Constructor initialises GAMS workspace and reads configuration
        :param cf: config file path
        """
        super().__init__("Optimiser", loglevel=loglevel)

        # Get the config
        self.config.read(cf)
        gams_path = self.config["optimiser"]["gams"]
        self.opt = self.config["optimiser"]

        # Init GAMS
        if self.loglevel == logger.LogLevel.normal:
            gams_debug_level = DebugLevel.KeepFiles
        elif self.loglevel == logger.LogLevel.verbose:
            gams_debug_level = DebugLevel.ShowLog
        else:
            gams_debug_level = DebugLevel.Off

        self.ws = GamsWorkspace(system_directory=gams_path,
                                debug=gams_debug_level,
                                working_directory="./tmp/")
        self.db = self.ws.add_database()

    def create_gdx(self):
        """
        Composes dataset for optimisation and formats it as GDX
        Two options - whether we get it from a CSV or from DynamoDB
        :return:
        """
        self.logger.log("Preparing optimiser input")

        self.df.loc[pd.isna(self.df["Bid"]), "Bid"] = 0.0
        self.df.loc[pd.isna(self.df["Ask"]), "Ask"] = 1000
        self.df.loc[pd.isna(self.df["Spread"]), "Spread"] = 1000

        self.df = self.df[pd.notnull(self.df['Delta'])]
        self.df = self.df[pd.notnull(self.df['Gamma'])]
        self.df = self.df[pd.notnull(self.df['Theta'])]
        self.df = self.df[pd.notnull(self.df['Vega'])]

        # Add sides
        self.df['Financial Instrument'] = self.df.index
        self.df['Financial Instrument'] = self.df['Financial Instrument'].astype(str)
        self.df['Side'] = np.where(self.df.index.str.contains("PUT"), "p", "c")

        self.df['Put'] = np.where(self.df['Side'] == "p", 1, 0)
        self.df['Call'] = np.where(self.df['Side'] == "c", 1, 0)

        self.df['long'] = np.where(self.df['Position'] > 0, self.df['Position'], 0)
        self.df['short'] = np.where(self.df['Position'] < 0, -self.df['Position'], 0)

        # Time in years
        self.df['Days'] = self.df['Days to Last Trading Day'] / 365

        # This is necessary for expiry days, so the greeks are at least somewhat finite
        self.df['Days'] = np.where(self.df['Days'] == 0, 0.00001, self.df['Days'])

        # Strikes
        self.df['Strike'] = self.df['Financial Instrument'].str.split(" ").map(lambda x: x[4])
        self.df['Strike'] = self.df['Strike'].astype(float)

        # Volatility in percent
        self.df['Vol'] = self.df['Implied Vol. %'].str.replace('%', '')
        self.df['Vol'] = self.df['Vol'].astype(float) / 100

        # Use neural net to fix the missing volatility
        self.df = nnet.fit_iv(self.df)

        # Create field for contract month
        self.df['Contract Month'] = \
            [datetime.strptime(item, "%b'%y").strftime("%Y%m") for item in self.df['Financial Instrument'].
                str.split(" ").map(lambda x: x[3])]

        # Add greeks
        self.df['Underlying Price'] = self.df['Underlying Price'].as_matrix()
        self.df['Strike'] = self.df['Strike'].as_matrix()
        self.df['Vol'] = self.df['Vol'].as_matrix()
        self.df['Days'] = self.df['Days'].as_matrix()
        self.df['d1'] = greeks.d_one(self.df['Underlying Price'], self.df['Strike'], 0.01, 0,
                                     self.df['Vol'], self.df['Days'])
        self.df['d2'] = greeks.d_two(self.df['Underlying Price'], self.df['Strike'], 0.01, 0,
                                     self.df['Vol'], self.df['Days'])
        self.df['Speed'] = greeks.speed(self.df['Gamma'], self.df['Underlying Price'], self.df['d1'],
                                        self.df['Vol'], self.df['Days'])
        self.df['Vanna'] = greeks.vanna(self.df['Vega'], self.df['Underlying Price'], self.df['d1'],
                                        self.df['Vol'], self.df['Days'])
        self.df['Zomma'] = greeks.zomma(self.df['Gamma'], self.df['d2'], self.df['d1'], self.df['Vol'])

        # Margins
        margins.add_margins(self.df, self.opt["s3storage"])

        # Calculate asset prices for given percent up and down. Right now lets set it at 3
        #  3% is rather common to be useful for risk management. Actually that level should be
        #  calculated backwards from VaR or something.
        price_up = self.df["Underlying Price"] * (1 + float(self.opt["risk.pct"]))
        price_down = self.df["Underlying Price"] * (1 - float(self.opt["risk.pct"]))
        self.df["Price Up"] = greeks.val(price_up, self.df["Strike"], 0.01, 0, self.df["Vol"],
                                         self.df["Days"], self.df["Side"]) - greeks.val(self.df["Underlying Price"],
                                                                                        self.df["Strike"], 0.01, 0,
                                                                                        self.df["Vol"],
                                                                                        self.df["Days"],
                                                                                        self.df["Side"])

        self.df["Price Down"] = greeks.val(price_down, self.df["Strike"], 0.01, 0,
                                           self.df["Vol"], self.df["Days"],
                                           self.df["Side"]) - greeks.val(self.df["Underlying Price"],
                                                                         self.df["Strike"], 0.01, 0,
                                                                         self.df["Vol"], self.df["Days"],
                                                                         self.df["Side"])

        # ACTUAL GDX CREATION STARTS HERE
        # Create sets for data
        data.create_set(self.db, "s_greeks", "List of greeks",
                        ["delta", "gamma", "theta", "vega", "speed", "vanna", "zomma"])
        data.create_set(self.db, "s_names", "Option names", self.df["Financial Instrument"])
        data.create_set(self.db, "s_side", "Position side", ["long", "short"])

        levels, unis = pd.factorize(self.df['Days'])
        self.df['Month'] = list(levels + 1)

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
        data.create_scalar(self.db, "v_max_risk", "Maximum absolute up and down risk", self.opt["max.risk"])
        data.create_scalar(self.db, "v_min_price", "Minimum option price permitted", self.opt["min.price"])
        data.create_scalar(self.db, "v_max_price", "Maximum option price permitted", self.opt["max.price"])

        # Parameter now the multi-dimensional parameters
        data.create_parameter(self.db, "p_y", "Existing position data",
                              [self.df["Financial Instrument"], ["long", "short"]], "full",
                              self.df[["Financial Instrument", "long", "short"]])
        data.create_parameter(self.db, "p_greeks", "Greeks data",
                              [self.df["Financial Instrument"],
                               ["delta", "gamma", "theta", "vega", "speed", "vanna", "zomma"]],
                              "full",
                              self.df[["Financial Instrument", "Delta", "Gamma",
                                       "Theta", "Vega", "Speed", "Vanna", "Zomma"]])
        data.create_parameter(self.db, "p_margin", "Margin data for options",
                              [self.df["Financial Instrument"], ["long", "short"]],
                              "full", self.df[["Financial Instrument", "Marg l", "Marg s"]])
        data.create_parameter(self.db, "p_side", "Option side (put/call)",
                              [self.df["Financial Instrument"], ["o_put", "o_call"]], "full",
                              self.df[["Financial Instrument", "Put", "Call"]])
        data.create_parameter(self.db, "p_risk", "Upside and downside risk",
                              [self.df["Financial Instrument"], ["up", "down"]], "full",
                              self.df[["Financial Instrument", "Price Up", "Price Down"]])
        data.create_parameter(self.db, "p_spread", "Bid ask spread", [self.df["Financial Instrument"]], "sparse",
                              self.df["Spread"])
        data.create_parameter(self.db, "p_days", "Days until expiry", [self.df["Financial Instrument"]], "sparse",
                              self.df["Days"] * 365)
        data.create_parameter(self.db, "p_months", "Months until expiry", [self.df["Financial Instrument"]], "sparse",
                              self.df["Month"])
        data.create_parameter(self.db, "p_price", "Price data for options",
                              [self.df["Financial Instrument"], ["bid", "ask"]],
                              "full", self.df[["Financial Instrument", "Bid", "Ask"]])

    def run_gams(self, fn=None):
        """
        Retrieves optimisation model from the model repo and runs it
        :param fn: gets formulation from text file
        :return:
        """
        response = ""
        if fn is None:
            self.logger.log("Getting the most recent formulation")
            response = code.get_code("gamsCode")["code"]

        self.logger.log("Running GAMS job")
        if fn is not None:
            model = self.ws.add_job_from_file(fn)
        else:
            model = self.ws.add_job_from_string(response)
        model.run(databases=self.db)

    def import_gdx(self, fn=None):
        """
        Imports optimisation results from the GDX file
        :param fn: name and path of the GDX gdx file, if none given then default to _gams_py_gdb1.gdx
        :return:
        """
        if fn is None:
            fn = "_gams_py_gdb1.gdx"

        self.logger.log("Importing from " + fn)
        db_out = self.ws.add_database_from_gdx(gdx_file_name=fn, database_name="results")

        # Initialise output dict, enumerate the results and read them from GDX
        x = {}
        t = ["trades", "pos_greeks", "total_greeks", "total_pos", "total_margin", "monthly_greeks"]
        for i in t:
            x[i] = data.read_gdx_param(db_out, i)

        x["total_greeks"] = x["total_greeks"].pivot(index="s_greeks", columns="s_age", values="val")
        x["total_greeks"].reset_index(level=0, inplace=True)

        # Dual indexes are a bitch, is there a better way?
        x["monthly_greeks"] = x["monthly_greeks"].set_index(["s_greeks", "s_month", "s_age"]).unstack(level=-1)
        x["monthly_greeks"].reset_index(level=1, inplace=True)
        x["monthly_greeks"].columns = ["s_month", "new", "old"]
        x["monthly_greeks"]["s_greeks"] = x["monthly_greeks"].index

        # After parameters, add variables
        x["x"] = data.read_gdx_var(db_out, "x")
        x["z"] = data.read_gdx_var(db_out, "z")
        self.logger.log("Objective function value " + str(next(iter(x["z"].values()))))

        # And we are done
        return x

    def opt_summary(self, df: dict):
        """
        Outputs summary results of the optimisation run
        :param df: dict with optimisation results
        :return:
        """
        self.logger.log("OPTIMISATION RESULTS")
        # Greeks
        self.logger.log("--------Greeks--------")
        self.logger.log("Greek\t\tNew\t\tOld")
        for i, r in df["total_greeks"].iterrows():
            self.logger.log(r["s_greeks"] + "\t" +
                            str(r["new"]) + "\t\t" +
                            str(r["old"]))
        # Trades
        self.logger.log("--------Trades--------")
        for i, r in df["trades"].iterrows():
            self.logger.log(r["Financial Instrument"] + "\t\t" +
                            r["side"] + "\t" +
                            str(r["q"]))

    def add_trades_to_df(self, res: dict):
        """
        Adds optimiser results to the market data snapshot data frame
        :param res: List containing decision variable values (ie, trades)
        :return:
        """
        self.logger.log("Adding positions to the data frame")

        x = res["trades"]
        x.columns = ["Financial Instrument", "side", "q"]
        x = x.pivot(index="Financial Instrument", columns="side", values="q").fillna(0)

        self.df = self.df.join(x, on="Financial Instrument", rsuffix="_x")
        self.df = self.df.fillna(0)

        # Some final calculations on traded quantities
        self.df["Trade"] = self.df["buy"] - self.df["sell"]
        self.df["NewPosition"] = self.df["Position"] + self.df["Trade"]

    def export_results_dynamo(self, dt: dict, tbl: str = None):
        """
        Saves optimisation results to DynamoDB
        :param tbl: Dynamo table that receives the opt. result data
        :param dt: List of data returned by the optimiser
        :return:
        """
        dt["trades"].columns = ["s_names", "s_trade", "val"]

        x = {"dtg": self.data_date.strftime("%y%m%d%H%M%S"),
             # "data": self.df.to_json(orient="split"),
             "greeks": dt["total_greeks"].to_json(orient="records"),
             "live": False,
             "margin": dt["total_margin"].to_json(orient="records"),
             "opt": json.dumps(dict(self.opt)),
             "pos": dt["total_pos"].to_json(orient="records"),
             "trades": dt["trades"].to_json(orient="records"),
             "monGreeks": dt["monthly_greeks"].to_json(orient="records")}

        self.logger.log("Exporting optimisation results to Dynamo DB")

        db = boto3.resource('dynamodb', region_name='us-east-1',
                            endpoint_url="https://dynamodb.us-east-1.amazonaws.com")
        if tbl is None:
            tbl = self.opt["results.table"]

        table = db.Table(tbl)
        # TODO: This Dynamo upload here needs to be tested!
        #  Position data is somehow weird
        #  Data frame headers for data are different in R and Python!
        response = table.put_item(Item=x)

        self.logger.log(str(response))

    def export_trades_csv(self, fn: str):
        """
        Exports the list of trades in basket trader format (CSV)
        Action,Quantity,Symbol,SecType,LastTradingDayOrContractMonth,Strike,Right,Exchange,Currency,TimeInForce,OrderType,LmtPrice,BasketTag,Account,OrderRef,Multiplier,
        BUY,1,CL,FOP,20181114,53,C,NYMEX,USD,DAY,LMT,8.58,Basket,DU337774,Basket,1000,

        :param fn: filename for exported data
        :return:
        """
        self.logger.log("Exporting trades basket to " + fn)

        df_tmp = self.df[self.df["Trade"] != 0]

        df_new = pd.DataFrame(np.where(df_tmp["Trade"] > 0, "BUY", "SELL"))
        df_new.columns = ["Action"]
        df_new["Quantity"] = np.abs(df_tmp["Trade"].astype(int)).tolist()
        df_new["Symbol"] = self.opt["symbol"]
        df_new["SecType"] = self.opt["sectype"]

        df_new["LastTradingDayOrContractMonth"] = df_tmp["Contract Month"].tolist()

        df_new["Strike"] = ["{:g}".format(item) for item in df_tmp["Strike"].tolist()]
        df_new["Right"] = df_tmp["Side"].str.upper().tolist()
        df_new["Exchange"] = self.opt["exchange"]
        df_new["Currency"] = self.opt["currency"]
        df_new["TimeInForce"] = "DAY"
        df_new["OrderType"] = "LMT"
        df_new["LmtPrice"] = ["{0:.2f}".format(item) for item in df_tmp["Mid"].tolist()]
        df_new["BasketTag"] = "Basket"
        df_new["Account"] = self.opt["account"]
        df_new["OrderRef"] = "Basket"
        df_new["Multiplier"] = self.opt["mult"]

        df_new.to_csv(fn, index=False)
        utils.data.remove_last_csv_newline(fn)

    # TODO: Integrate market snapshot here
    def get_mkt_data_snapshot(self):
        """
        Gets market data snapshot from TWS
        :return:
        """
        self.logger.error("TWS Snapshot retrieval not implemented")

    # TODO: Implement basket orders
    def basket_order(self, live=False):
        """
        Sends basket order to TWS to execute the rebalance
        :param live: when True, transmits orders, otherwise just saves
        :return:
        """
        if live:
            self.logger.log("Composing basket orders for automatic LIVE rebalance")
        else:
            self.logger.log("Composing basket orders for sending them to TWS without execution")

        self.logger.error("Basket orders are not yet implemented")


if __name__ == "__main__":
    # Process command line options
    parser = argparse.ArgumentParser(description="Portfolio optimiser")
    parser.add_argument("-c", action="store", help="Configuration file")
    parser.add_argument("-i", action="store", help="Path to input data CSV file")
    parser.add_argument("-q", "--quiet", action="store_true", help="Quiet mode. Log only errors.")
    parser.add_argument("-v", "--verbose", action="store_true", help="Turn on verbose logging")
    parser.add_argument("--tws", action="store_true", help="Import market data from TWS")
    parser.add_argument("--db", action="store_true", help="Export optimisation results to Dynamo DB")
    parser.add_argument("--xml", action="store", help="Export basket as TWS compatible XML")
    parser.add_argument("--csv", action="store", help="Export basket as TWS compatible CSV")
    parser.add_argument("--dtg", action="store", help="DTG for Dynamo DB market snapshot retrieval.")

    args = parser.parse_args()

    if args.c is None:
        conf_file = "config.cf"
    else:
        conf_file = args.c

    log = LogLevel.normal
    if args.quiet:
        log = LogLevel.error
    if args.verbose:
        log = LogLevel.verbose

    # Now the main code
    o = Optimiser(conf_file, loglevel=log)

    # Figure out where to get input data
    if args.tws:
        o.get_mkt_data_snapshot()
    elif args.i is None:
        o.get_mkt_data_dynamo(dtg=args.dtg)
    else:
        o.get_mkt_data_csv(args.i)

    o.create_gdx()
    o.run_gams()
    d = o.import_gdx()
    o.add_trades_to_df(d)
    o.opt_summary(d)

    # TODO: Here we need to add detection of FUT positions from assigned options
    #  These positions need to be closed and added to both CSV and XML exports

    # Outputs
    if args.db:
        o.export_results_dynamo(d)
    if args.csv:
        o.export_trades_csv(args.csv)
    if args.xml:
        tools.export_portfolio_xml(o.df, args.xml)

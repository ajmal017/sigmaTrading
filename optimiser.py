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
from utils import logger, instrument
from utils.logger import LogLevel
from tws import tools, snapshot, tws
from ibapi.order import Order
import argparse
import os
import sys


class OptException(Exception):
    """
    Own dummy exception
    """
    pass


class Optimiser(PortfolioStrategy):
    def __init__(self, cf: str, loglevel: LogLevel = LogLevel.normal):
        """
        Constructor initialises GAMS workspace and reads configuration
        :param cf: config file path
        """
        super().__init__("Optimiser", loglevel=loglevel)

        # Get the config
        if not os.path.isfile(conf_file):
            self.logger.error("Cannot find config file " + conf_file)
            raise OSError

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

        if not os.path.exists(gams_path):
            self.logger.error("Cannot find GAMS path " + gams_path)
            raise OSError

        self.ws = GamsWorkspace(system_directory=gams_path,
                                debug=gams_debug_level,
                                working_directory="./tmp/")
        self.db = self.ws.add_database()

        self.df_greeks = pd.DataFrame()
        self.df_greeks_before = pd.DataFrame()

    def get_opt(self, op: str):
        """
        Checks if the option exists, if it does, returns it,
        otherwise show an error message and raise exception
        :param op: The configuration option string
        :return:
        """
        if op not in self.opt:
            self.logger.error("The option " + op + " does not exist in configuration!")
            raise OptException
        else:
            return self.opt[op]

    def create_gdx(self, ignore_existing=False):
        """
        Composes dataset for optimisation and formats it as GDX
        Two options - whether we get it from a CSV or from DynamoDB
        :param: ignore_existing: whether  we ignore existing positions
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

        # If fresh portfolio, set positions to 0
        if ignore_existing:
            self.df["Position"] = 0

        # Add sides
        self.df['Financial Instrument'] = self.df['Financial Instrument'].astype(str)
        self.df['Side'] = np.where(self.df["Financial Instrument"].str.contains("PUT"), "p", "c")

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
        if self.df['Vol'].isna().any():
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
        try:
            price_up = self.df["Underlying Price"] * (1 + float(self.get_opt("risk.pct")))
            price_down = self.df["Underlying Price"] * (1 - float(self.get_opt("risk.pct")))
        except OptException:
            self.logger.error("Errors in configuration file, quitting")
            sys.exit(1)

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

        self.df["Theta Up"] = greeks.theta(price_up, self.df["Strike"], 0.01, 0, self.df["Vol"],
                                           self.df["Days"], self.df["Side"])

        self.df["Theta Down"] = greeks.theta(price_down, self.df["Strike"], 0.01, 0,
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
        try:
            data.create_scalar(self.db, "v_direction", "Algorithm direction short or long vol.",
                               self.get_opt("direction"))
            data.create_scalar(self.db, "v_multiplier", "Instrument multiplier", self.get_opt("mult"))
            data.create_scalar(self.db, "v_max_delta", "Maximum delta allowed", self.get_opt("max.delta"))
            data.create_scalar(self.db, "v_max_gamma", "Maximum gamma allowed", self.get_opt("max.gamma"))
            data.create_scalar(self.db, "v_min_theta", "Minimum theta allowed", self.get_opt("min.theta"))
            data.create_scalar(self.db, "v_max_vega", "Maximum vega allowed", self.get_opt("max.vega"))
            data.create_scalar(self.db, "v_max_speed", "Maximum speed allowed", self.get_opt("max.speed"))
            data.create_scalar(self.db, "v_max_pos", "Maximum position allowed", self.get_opt("max.pos"))
            data.create_scalar(self.db, "v_max_pos_tot", "Maximum number of contracts", self.get_opt("max.pos.tot"))
            data.create_scalar(self.db, "v_alpha", "Relative importance of theta in obj function",
                               self.get_opt("alpha"))
            data.create_scalar(self.db, "v_trans_cost", "Transaction cost for one contract",
                               self.get_opt("trans.cost"))
            data.create_scalar(self.db, "v_max_margin", "Maximum margin allowed", self.get_opt("max.margin"))
            data.create_scalar(self.db, "v_max_spread", "Maximum bid ask spread allowed", self.get_opt("max.spread"))
            data.create_scalar(self.db, "v_min_days", "Minimum days to expiry allowed", self.get_opt("min.days"))
            data.create_scalar(self.db, "v_max_trades", "Maximum rebalancing trades allowed",
                               self.get_opt("max.trades"))
            data.create_scalar(self.db, "v_max_pos_mon", "Maximum monthly open positions allowed",
                               self.get_opt("max.pos.mon"))
            data.create_scalar(self.db, "v_max_risk", "Maximum absolute up and down risk", self.get_opt("max.risk"))
            data.create_scalar(self.db, "v_min_price", "Minimum option price permitted", self.get_opt("min.price"))
            data.create_scalar(self.db, "v_max_price", "Maximum option price permitted", self.get_opt("max.price"))
        except OptException:
            self.logger.error("Errors in configuration, quitting")
            sys.exit(1)

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
        data.create_parameter(self.db, "p_theta", "Upside and downside theta",
                              [self.df["Financial Instrument"], ["up", "down"]], "full",
                              self.df[["Financial Instrument", "Theta Up", "Theta Down"]])
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

        self.logger.verbose("Importing from " + fn)
        db_out = self.ws.add_database_from_gdx(gdx_file_name=fn, database_name="results")

        # Initialise output dict, enumerate the results and read them from GDX
        x = {}
        t = ["trades", "pos_greeks", "total_greeks", "total_pos", "total_margin", "monthly_greeks"]
        for i in t:
            x[i] = data.read_gdx_param(db_out, i)

        x["total_greeks"] = x["total_greeks"].pivot(index="s_greeks", columns="s_age", values="val")
        x["total_greeks"].reset_index(level=0, inplace=True)
        # in case of empty portfolio
        if x["total_greeks"].shape[1] == 2:
            x["total_greeks"]["old"] = 0

        # Dual indexes are a bitch, is there a better way?
        x["monthly_greeks"] = x["monthly_greeks"].set_index(["s_greeks", "s_month", "s_age"]).unstack(level=-1)
        x["monthly_greeks"].reset_index(level=1, inplace=True)

        # in case of empty portfolio
        if x["monthly_greeks"].shape[1] == 2:
            x["monthly_greeks"]["old"] = 0

        x["monthly_greeks"].columns = ["s_month", "new", "old"]
        x["monthly_greeks"]["s_greeks"] = x["monthly_greeks"].index

        # After parameters, add variables
        x["x"] = data.read_gdx_var(db_out, "x")
        x["z"] = data.read_gdx_var(db_out, "z")
        self.logger.log("Objective function value " + "{:9.4f}".format(next(iter(x["z"].values()))))

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
        self.logger.log("-------------- Greeks --------------")
        self.logger.log("Greek\t      New\t      Old")
        self.logger.log("------------------------------------")
        for i, r in df["total_greeks"].iterrows():
            self.logger.log(r["s_greeks"] + "\t" +
                            "{:9.4f}".format(r["new"]) + "\t" +
                            "{:9.4f}".format(r["old"]))
        # Trades
        self.logger.log("---------------------- Trades ---------------------")
        self.logger.log("Instrument\t\t\t\tActn  Qty")
        self.logger.log("---------------------------------------------------")
        for i, r in df["trades"].iterrows():
            self.logger.log("{: <35}".format(r["Financial Instrument"]) + "\t" +
                            r["side"] + "\t" +
                            str(r["q"]))
        self.logger.log("---------------------------------------------------")

    def add_trades_to_df(self, res: dict):
        """
        Adds optimiser results to the market data snapshot data frame
        :param res: List containing decision variable values (ie, trades)
        :return:
        """
        self.logger.log("Adding positions to the data frame")

        x = res["trades"]
        if len(x.columns) == 0:
            self.logger.error("No results from optimiser. Infeasible solution or no trades necessary?")
            raise OptException

        x.columns = ["Financial Instrument", "side", "q"]
        x = x.pivot(index="Financial Instrument", columns="side", values="q").fillna(0)

        self.df = self.df.join(x, on="Financial Instrument", rsuffix="_x")
        self.df = self.df.fillna(0)

        if self.df.shape[0] == 0:
            self.logger.error("No trades from optimiser, no reason to continue")
            raise OptException

        # Some final calculations on traded quantities
        # What if there are only buys or sells?
        if "buy" not in self.df:
            self.df["buy"] = 0
        if "sell" not in self.df:
            self.df["sell"] = 0

        self.df["Trade"] = self.df["buy"] - self.df["sell"]
        self.df["NewPosition"] = self.df["Position"] + self.df["Trade"]

        self.df_greeks = greeks.build_curves(self.df,
                                             ["Val", "Val_p1", "Val_exp", "Delta",
                                              "Gamma", "Theta", "Vega"], "NewPosition")
        self.df_greeks_before = greeks.build_curves(self.df, ["Val", "Val_p1", "Val_exp", "Delta",
                                                              "Gamma", "Theta", "Vega"], "Position")
        self.df_greeks = self.df_greeks.multiply(float(self.get_opt("mult")))
        self.df_greeks_before = self.df_greeks_before.multiply(float(self.get_opt("mult")))
        return 0

    def import_results_dynamo(self, dtg: None) -> dict:
        """
        Imports optimisation results from Dynamo
        :param dtg:
        :return: dict
        """
        from boto3.dynamodb.conditions import Key

        self.logger.log("Importing optimisation results from Dynamo DB")

        db = boto3.resource('dynamodb', region_name='us-east-1',
                            endpoint_url="https://dynamodb.us-east-1.amazonaws.com")
        tbl = self.opt["results.table"]

        table = db.Table(tbl)

        # If dtg is not given, get the latest snapshot, otherwise find the right dtg
        if dtg is None:
            d_tmp = utils.data.get_list_data(o.opt["results.table"])
            dtg = max(pd.to_numeric(d_tmp["dtg"]))
            self.logger.log("Latest timestamp in results data table is " + str(dtg))

        response = table.query(KeyConditionExpression=Key('dtg').eq(str(dtg)))
        response = response["Items"][0]
        response["data"] = pd.DataFrame.from_dict(json.loads(response["data"]))
        return response

    def export_results_dynamo(self, dt: dict, tbl: str = None):
        """
        Saves optimisation results to DynamoDB
        :param tbl: Dynamo table that receives the opt. result data
        :param dt: List of data returned by the optimiser
        :return:
        """
        dt["trades"].columns = ["s_names", "s_trade", "val"]

        cols = ["Financial Instrument", "Bid", "Mid", "Ask", "Underlying Price", "Position", "NewPosition",
                "Strike", "Side", "Days", "Vol", "Delta", "Gamma", "Theta", "Vega", "Contract Month"]
        df_tmp = self.df[cols].copy()

        x = {"dtg": self.data_date.strftime("%y%m%d%H%M%S"),
             "data": df_tmp.to_json(orient="records"),
             "greeks": dt["total_greeks"].to_json(orient="records"),
             "live": False,
             "margin": dt["total_margin"].to_json(orient="records"),
             "opt": str(json.dumps(dict(self.opt))),
             "pos": dt["total_pos"].to_json(orient="records"),
             "trades": dt["trades"].to_json(orient="records"),
             "monGreeks": dt["monthly_greeks"].to_json(orient="records")
             }

        self.logger.log("Exporting optimisation results to Dynamo DB")

        db = boto3.resource('dynamodb', region_name='us-east-1',
                            endpoint_url="https://dynamodb.us-east-1.amazonaws.com")
        if tbl is None:
            tbl = self.opt["results.table"]

        table = db.Table(tbl)
        response = table.put_item(Item=x)
        is_ok = response["ResponseMetadata"]["HTTPStatusCode"] == 200

        if is_ok:
            self.logger.verbose("Export completed successfully")
        else:
            self.logger.error("Export failed`")

    def export_trades_csv(self, fn: str):
        """
        Exports the list of trades in basket trader format (CSV)
        Action,Quantity,Symbol,SecType,LastTradingDayOrContractMonth,Strike,Right,Exchange,Currency,TimeInForce,
        OrderType,LmtPrice,BasketTag,Account,OrderRef,Multiplier,
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

    def get_mkt_data_snapshot(self, export_dynamo=False):
        """
        Gets market data snapshot from TWS
        :return:
        """
        self.logger.log("Getting market data from snapshot")
        snap = snapshot.Snapshot(config=self.opt, log_level=self.loglevel)
        snap.connect(self.opt["host"],
                     int(self.opt["port"]),
                     int(self.opt["id"]) + 1)
        snap.create_instruments()
        snap.wait_to_finish()
        self.df = snap.prepare_df()
        if export_dynamo:
            snap.export_dynamo(self.config["data"]["mkt.table"])
        snap.disconnect()

    def basket_order(self, live=False):
        """
        Sends basket order to TWS to execute the rebalance
        :param live: when True, transmits orders, otherwise just saves
        :return:
        """
        # TODO: If live, then consider automatic order adjustments
        if live:
            self.logger.log("Composing basket orders for automatic LIVE rebalance")
        else:
            self.logger.log("Composing basket orders for sending them to TWS without execution")

        t = tws.TwsTool("Basket Order", log_level=self.loglevel)
        t.connect(self.opt["host"], int(self.opt["port"]), int(self.opt["id"])+2)

        # Filter out correct rows
        df_tmp = self.df[self.df["Trade"] != 0]

        d_tmp = instrument.get_instrument(self.opt["symbol"], "instData")
        c = d_tmp["cont"]

        o_id = t.nextId
        for i, r in df_tmp.iterrows():
            self.logger.log(r["Financial Instrument"])
            c.strike = "{:g}".format(r["Strike"])
            c.right = "CALL" if r["Side"] == "c" else "PUT"
            c.lastTradeDateOrContractMonth = r["Contract Month"]

            tws_order = Order()
            tws_order.transmit = live
            tws_order.orderType = "LMT"
            tws_order.action = "BUY" if int(r["Trade"]) > 0 else "SELL"
            tws_order.totalQuantity = np.abs(int(r["Trade"]))
            tws_order.lmtPrice = float(round(r["Mid"] * 2) / 2)

            t.placeOrder(o_id, c, tws_order)
            o_id = o_id + 1
            import time
            time.sleep(0.5)

        t.disconnect()

    def close_fut(self, df: dict):
        """
        Detects if any FUT positions are present, perhaps due to assignments.
        If detected, add closing of these positions to trades.
        :param df: data dict from optimiser
        :return:
        """
        # TODO: Here we need to add detection of FUT positions from assigned options
        #  These positions need to be closed and added to both CSV and XML exports
        self.logger.log("FUT position detection and closing currently not implemented")
        return df

    def plot_greeks(self):
        """
        Plot greeks
        :return:
        """
        from bokeh.plotting import figure, show
        from bokeh.layouts import gridplot

        self.logger.log("Outputting bokeh plots")
        p1 = figure(title="Delta", width=250, height=250)
        p1.line(self.df_greeks.index, self.df_greeks["Delta"], line_color="red", legend="Optimal")
        p1.line(self.df_greeks.index, self.df_greeks_before["Delta"], line_color="black", legend="Current")
        p2 = figure(title="Gamma", width=250, height=250)
        p2.line(self.df_greeks.index, self.df_greeks["Gamma"], line_color="red", legend="Optimal")
        p2.line(self.df_greeks.index, self.df_greeks_before["Gamma"], line_color="black", legend="Current")
        p3 = figure(title="Theta", width=250, height=250)
        p3.line(self.df_greeks.index, self.df_greeks["Theta"], line_color="red", legend="Optimal")
        p3.line(self.df_greeks.index, self.df_greeks_before["Theta"], line_color="black", legend="Current`")
        p4 = figure(title="Val", width=750, height=250)
        p4.line(self.df_greeks.index, self.df_greeks["Val"], line_color="red", legend="Optimal")
        p4.line(self.df_greeks.index, self.df_greeks["Val_p1"], line_color="blue", legend="T+1 day")
        p4.line(self.df_greeks.index, self.df_greeks["Val_exp"], line_color="blue", line_dash="4 4", legend="Expiry")
        p4.line(self.df_greeks.index, self.df_greeks_before["Val"], line_color="black", legend="Current")

        show(gridplot([[p4], [p1, p2, p3]]))


if __name__ == "__main__":
    # Process command line options
    parser = argparse.ArgumentParser(description="Portfolio optimiser",
                                     epilog="Copyright (c) 2019 Sigma Research OÜ")
    parser.add_argument("-c", action="store", help="Configuration file")
    parser.add_argument("-q", "--quiet", action="store_true", help="Quiet mode. Log only errors.", default=False)
    parser.add_argument("-v", "--verbose", action="store_true", help="Turn on verbose logging", default=False)

    subparsers = parser.add_subparsers(title="subcommands", dest="cmd",
                                       description="valid subcommands", help="additional help")

    # Data subcommands
    parser_data = subparsers.add_parser("data", help="Data subcommands")
    parser_data.add_argument("subcmd", choices=["import", "export", "list", "delete", "conid-scraper"],
                             action="store", help="")
    parser_data.add_argument("-i", action="store", help="Path to input data CSV file")
    parser_data.add_argument("--tws", action="store_true", help="Import market data from TWS", default=False)
    parser_data.add_argument("--xml", action="store", help="Export basket as TWS compatible XML")
    parser_data.add_argument("--csv", action="store", help="Export basket as TWS compatible CSV")
    parser_data.add_argument("--dtg", action="store", help="DTG for market snapshot retrieval.")

    # Optimisation subcommands
    parser_run = subparsers.add_parser("run",  help="Optimisation subcommands")
    parser_run.add_argument("subcmd", choices=["optimise", "formulation"],
                            action="store", help="Optimisation subcommands")
    parser_run.add_argument("--db", action="store_true", help="Export optimisation results to Dynamo DB", default=False)
    parser_run.add_argument("--dtg", action="store", help="DTG for market snapshot retrieval.")
    parser_run.add_argument("-f", "--file", action="store", help="Formulation file name for import or export")
    parser_run.add_argument("--ignore_existing", action="store_true",
                            help="Ignore existing positions in dataset", default=False)
    parser_run.add_argument("--version", action="store", help="Specify optimisation formulation version")

    # Results subcommands
    parser_results = subparsers.add_parser("results", help="Results subcommands")
    parser_results.add_argument("subcmd", choices=["list", "plot", "view", "export", "toggle", "delete", "trade"],
                                action="store", help="")
    parser_results.add_argument("--live", action="store_true",
                                help="If set, send live orders, save otherwise", default=False)
    parser_results.add_argument("--dtg", action="store", help="DTG for run result retrieval.")

    # Account subcommands
    parser_account = subparsers.add_parser("account", help="Account handling subcommands")

    args = parser.parse_args()

    # Configuration file setup
    if args.c is None:
        conf_file = "config.cf"
    else:
        conf_file = args.c

    # Logging setup
    log = LogLevel.normal
    if args.quiet:
        log = LogLevel.error
    if args.verbose:
        log = LogLevel.verbose

    # Now the main code
    o = Optimiser(conf_file, loglevel=log)
    # TODO: Something that checks whether TWS is connected to the correct account (cf. config file)
    # TODO: Write a config check code, that verifies the contents of the configuration file before proceeding
    # TODO: Write command line options for workflow: first 'opt' to do optimisation and write results to db
    #       if the run is fine then 'trade' that does either the xml export, csv export or direct TWS trading
    #       additionally 'snapshot' that just pulls the market snapshot and injects it to Dynamo

    # Data input and output handling
    if args.cmd == "data":
        if args.subcmd == "import":
            if args.i:
                o.get_mkt_data_csv(args.i)
                o.save_mkt_data_dynamo()
            elif args.tws:
                o.get_mkt_data_snapshot(export_dynamo=True)
            else:
                o.logger.error("No import method specified")
        elif args.subcmd == "export":
            o.logger.error("Data snapshot export not implemented")
        elif args.subcmd == "list":
            df1 = utils.data.get_list_data(o.config["data"]["mkt.table"])
            print(df1)
        elif args.subcmd == "delete":
            o.logger.error("Data snapshot deletion not implemented")
        elif args.subcmd == "conid-scraper":
            from tws.conid_scraper import IdScraper

            i = IdScraper("ConID Scraper")
            i.connect("localhost", 4001, 56)
            i.req_data()
            i.wait_for_finish()
            i.postprocess()
            i.write_dynamo("instruments")
            i.disconnect()

    # Optimisation handing
    if args.cmd == "run":
        if args.subcmd == "optimise":
            # Get market data from Dynamo and optimise
            # TODO: the snapshot that we retrieve must be for the correct account.
            #  Otherwise, if we get the latest, then we also need a portfolio snapshot!
            o.get_mkt_data_dynamo(dtg=args.dtg)
            o.create_gdx(args.ignore_existing)
            o.run_gams()
            d = o.import_gdx()

            # Add optimisation results to the main data frame
            try:
                status = o.add_trades_to_df(d)
            except OptException:
                status = 1
                parser.exit(1)

            # No solver results, possible infeasible solution or no trades?
            if len(d["trades"]) == 0 or status == 1:
                parser.exit(1)

            # Print out summary
            o.opt_summary(d)
            d = o.close_fut(d)

            # If requested, export results to Dynamo
            if args.db:
                o.export_results_dynamo(d)
            parser.exit(1)
        elif args.subcmd == "formulation":
            o.logger.error("Formulation import and export not implemented")

    # Results handling
    if args.cmd == "results":
        if args.subcmd == "list":
            df1 = utils.data.get_list_data(o.opt["results.table"])
            print(df1)

        elif args.subcmd == "plot":
            r1 = o.import_results_dynamo(dtg=args.dtg)
            o.df = r1["data"]
            o.df_greeks = greeks.build_curves(o.df, ["Val", "Val_p1", "Val_exp", "Delta",
                                                     "Gamma", "Theta", "Vega"], "NewPosition")
            o.df_greeks_before = greeks.build_curves(o.df, ["Val", "Val_p1", "Val_exp", "Delta",
                                                            "Gamma", "Theta", "Vega"], "Position")
            o.df_greeks = o.df_greeks.multiply(float(o.get_opt("mult")))
            o.df_greeks_before = o.df_greeks_before.multiply(float(o.get_opt("mult")))
            o.plot_greeks()

        elif args.subcmd == "view":
            pass
        elif args.subcmd == "export":
            r1 = o.import_results_dynamo(dtg=args.dtg)
            # TODO Implement the importing!
            o.logger.error("Exporting not implemented")
            parser.exit(1)
            if args.csv:
                o.export_trades_csv(args.csv)
            if args.xml:
                tools.export_portfolio_xml(o.df, args.xml)
        elif args.subcmd == "toggle":
            pass
        elif args.subcmd == "delete":
            pass
        elif args.subdmf == "trade":
            o.basket_order(args.live)

    # Account handling
    if args.cmd == "account":
        o.logger.error("Account data handling not implemented")

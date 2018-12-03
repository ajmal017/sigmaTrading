"""
Portfolio optimisation code ported mostly from R

Author: Peeter Meos, Sigma Research OÜ
Date: 2. December 2018
"""
from gams import *
import gms
import configparser
import pandas as pd


"""
#' Creates GDX for optimisation
#'
#' @param in.fn 
#' @param in.gdx 
#' @param opt 
#' @param ignore.existing 
#'
#' @return
#' @export
#'
#' @examples
createGDX <- function(in.fn, in.gdx, opt, ignore.existing = FALSE) {
  toNum <- function(x) {as.numeric(as.character(x))}
  
  df <- read.csv(in.fn, fileEncoding = "ASCII", na.strings = "NoMD") 
  
  # Eliminate all NA
  df <- df[!is.na(df$Mid),]
  df <- df[!is.na(df$Delta),]
  df <- df[!is.na(df$Gamma),]
  df <- df[!is.na(df$Theta),]
  df <- df[!is.na(df$Vega),]
  df <- df[!is.na(df$Implied.Vol...),]
  
  # Add volatility and strike
  df$Financial.Instrument <- as.character(df$Financial.Instrument)
  
  df$Side <- "c"
  df$Side[grepl("PUT", df$Financial.Instrument)] <- "p"
  
  df$Put <- ifelse(df$Side == "p", 1, 0)
  df$Call <- ifelse(df$Side == "c", 1, 0)
  
  df$Days <- df$Days.to.Last.Trading.Day / 365

  df$Implied.Vol... <- as.character(df$Implied.Vol...)
  df <- df[df$Implied.Vol... != "N/A",]
  # In percent
  df$Vol <- as.numeric(sub("%", "", df$Implied.Vol...)) / 100
  df <- df[!is.na(df$Vol),]
  
  df$Strike <- 0
  for (i in 1:nrow(df)) {
    df$Strike[i] <- as.double(unlist(strsplit(df$Financial.Instrument[i], split = " "))[5])
  }

  # Currently using only greeks
  # Add speed
  df$d1 <- d1(df$Underlying.Price, df$Strike, 0.01, 0, df$Vol, df$Days)
  df$d2 <- d2(df$Underlying.Price, df$Strike, 0.01, 0, df$Vol, df$Days)
  df$Speed <- speed(df$Gamma, df$Underlying.Price, df$d1, df$Vol, df$Days)
  
  #df$Vega <- vega(df$Underlying.Price, df$Strike, 0.01, 0, df$Vol, df$Days)
  df$Vanna <- vanna(df$Vega, df$Underlying.Price, df$d1, df$Vol, df$Days)
  df$Zomma <- zomma(df$Gamma, df$d2, df$d1, df$Vol)
  
  df <- addMargins(df, opt)
  
  #return(df)
  
  
  df$Month <- factor(df$Days, levels = unique(df$Days), labels = 1:length(unique(df$Days)))

  # Create the list for data
  df$Position <- toNum(df$Position)
  df$Position[is.na(df$Position)] <- 0
  
  if (ignore.existing == TRUE) {
    df$long <- df$short <- 0 
  } else {
    df$long  <- ifelse(df$Position > 0,  df$Position, 0)
    df$short <- ifelse(df$Position < 0, -df$Position, 0)
  }

  p.y <- list(name = "p_y", ts = "Existing positions data", type = "parameter", dim = 2, form = "full",
                 uels = list(as.character(df$Financial.Instrument), c("long", "short")), 
                 val =  as.matrix(df[, c("long", "short")]))
  

  p.data <- list(name = "p_greeks", ts = "Greeks data", type = "parameter", dim = 2, form = "full",
                 uels = list(as.character(df$Financial.Instrument), c("delta", "gamma", "theta", "vega", 
                                                                    "speed","vanna", "zomma")), 
                 val =  as.matrix(df[, c("Delta", "Gamma", "Theta", "Vega", "Speed", "Vanna", "Zomma")]))
  
  p.marg <- list(name = "p_margin", ts = "Margin data for options", type = "parameter", dim = 2, form = "full",
              uels = list(as.character(df$Financial.Instrument), c("long", "short")), 
              val =  as.matrix(df[, c("Marg.l", "Marg.s")]))
  
  p.side <- list(name = "p_side", ts = "Option side (put/call)", type = "parameter", dim = 2, form = "full",
                 uels = list(as.character(df$Financial.Instrument), c("o_put", "o_call")), 
                 val =  as.matrix(df[, c("Put", "Call")]))
  
  p.spread <- list(name = "p_spread", ts = "Bid ask spread", type = "parameter", dim = 1, form = "sparse",
                 uels = list(as.character(df$Financial.Instrument)), 
                 val =  as.matrix(cbind(seq(1, nrow(df)), df$Spread)))
  
  p.days <- list(name = "p_days", ts = "Days until expiry", type = "parameter", dim = 1, form = "sparse",
                   uels = list(as.character(df$Financial.Instrument)), 
                   val =  as.matrix(cbind(seq(1, nrow(df)), df$Days * 365)))
  
  p.months <- list(name = "p_months", ts = "Months until expiry", type = "parameter", dim = 1, form = "sparse",
                 uels = list(as.character(df$Financial.Instrument)), 
                 val =  as.matrix(cbind(seq(1, nrow(df)), df$Month)))
  

  # Write that to the GDX
  gdxrrw::wgdx.lst(in.gdx, s.greeks, s.names, s.month, 
                   p.data, p.y, p.marg, p.side, p.spread, p.days, p.months,
           createScalar(opt$mult, "v_multiplier", "Instrument multiplier"),
           createScalar(opt$max.delta, "v_max_delta", "Maximum delta allowed"),
           createScalar(opt$max.gamma, "v_max_gamma", "Maximum gamma allowed"),
           createScalar(opt$min.theta, "v_min_theta", "Minimum theta allowed"),
           createScalar(opt$min.vega, "v_min_vega", "Minimum vega allowed"),
           createScalar(opt$max.speed, "v_max_speed", "Maximum speed allowed"),
           createScalar(opt$max.pos, "v_max_pos", "Maximum size of position"),
           createScalar(opt$max.pos.tot, "v_max_pos_tot", "Maximum number of contracts"),
           createScalar(opt$alpha, "v_alpha", "Relative importance of theta in obj fun"),
           createScalar(opt$trans.cost, "v_trans_cost", "Transaction cost for one contract"),
           createScalar(opt$max.margin, "v_max_margin", "Maximum margin allowed"),
           createScalar(opt$max.spread, "v_max_spread", "Maximum bid ask spread allowed"),
           createScalar(opt$min.days, "v_min_days", "Minimum days to expiry allowed"),
           createScalar(opt$max.trades, "v_max_trades", "Maximum rebalancing trades allowed"),
           createScalar(opt$max.pos.mon, "v_max_pos_mon", "Maximum monthly open positions allowed")
           )
  
  return(df)
}
"""


def export_gdx(db: GamsDatabase, opt):
    """
    Composes dataset for optimisation and exports it as GDX
    Two options - whether we get it from a CSV or from DynamoDB
    :return:
    """
    df = pd.read_csv("data/181105 options.csv", na_values="NoMD")
    print(df.describe())

    # Create sets for data
    gms.create_set(db, "s_greeks", "List of greeks",
                   ["delta", "gamma", "theta", "vega", "speed", "vanna", "zomma"])
    gms.create_set(db, "s_names", "Option names", df["Financial.Instrument"])
    gms.create_set(db, "s_month", "Contract months", range(1, 6))  # TODO Should be len(unique(df$Days))

    # So now lets create the scalars
    gms.create_scalar(db, "v_multiplier", "Instrument multiplier", opt["mult"])
    gms.create_scalar(db, "v_max_delta", "Maximum delta allowed", opt["max.delta"])
    gms.create_scalar(db, "v_max_gamma", "Maximum gamma allowed", opt["max.gamma"])
    gms.create_scalar(db, "v_min_theta", "Minimum theta allowed", opt["min.theta"])
    gms.create_scalar(db, "v_min_vega", "Minimum vega allowed", opt["min.vega"])
    gms.create_scalar(db, "v_max_speed", "Maximum speed allowed", opt["max.speed"])
    gms.create_scalar(db, "v_max_pos", "Maximum position allowed", opt["max.pos"])
    gms.create_scalar(db, "v_max_pos_tot", "Maximum number of contracts", opt["max.pos.tot"])
    gms.create_scalar(db, "v_alpha", "Relative importance of theta in obj function", opt["alpha"])
    gms.create_scalar(db, "v_max_trans_cost", "Transaction cost for one contract", opt["trans.cost"])
    gms.create_scalar(db, "v_max_margin", "Maximum margin allowed", opt["max.margin"])
    gms.create_scalar(db, "v_max_spread", "Maximum bid ask spread allowed", opt["max.spread"])
    gms.create_scalar(db, "v_min days", "Minimum days to expiry allowed", opt["min.days"])
    gms.create_scalar(db, "v_max_trades", "Maximum rebalancing trades allowed", opt["max.trades"])
    gms.create_scalar(db, "v_max_pos_mon", "Maximum monthly open positions allowed", opt["max.pos.mon"])

    # Parameter now the multi-dimensional parameters
    # TODO: Check with pandas documentation how to pass those columns as lists
    gms.create_parameter(db, "p_y", "Existing position data", [df["Financial.Instrument"], ["long", "short"]],
                         "full", df["long", "short"])
    gms.create_parameter(db, "p_greeks", "Greeks data",
                         ["delta", "gamma", "theta", "vega", "speed", "vanna", "zomma"], "full",
                         df["Delta", "Gamma", "Theta", "Vega", "Speed", "Vanna", "Zomma"])
    gms.create_parameter(db, "p_margin", "Margin data for options", [df["Financial.Instrument"], ["long", "short"]],
                         "full", df["Marg.l", "Marg.s"])
    gms.create_parameter(db, "p_side", [df["Financial.Instrument"], ["o_put", "o_call"]], "full",
                         [df["Put", "Call"]])
    gms.create_parameter(db, "p_spread", "Bid ask spread", [df["Financial.Instrument"]], "sparse",
                         [range(1, len(df)), df["spread"]])
    gms.create_parameter(db, "p_days", "Days until expiry", [df["Financial.Instrument"]], "sparse",
                         [range(1, len(df)), df["Days"] * 365])
    gms.create_parameter(db, "p_months", "Months until expiry", [df["Financial.Instrument"]], "sparse",
                         [range(1, len(df)), df["Month"]])

    # All done, now export that to the GDX file
    db.export("input.gdx")


def run_gams(ws: GamsWorkspace):
    """
    Retrieves optimisation model from the model repo and runs it
    :return:
    """
    model = ws.add_job_from_string("")
    model.run()


def import_gdx(fn: str):
    """
    Imports optimisation results from the GDX file
    :param fn: name and path of the GDX gdx file
    :return:
    """
    print("Importing from " + fn)
    return {}


def save_results_dynamo():
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

    # Get the config
    cf = "config.sample"
    config = configparser.ConfigParser()
    config.read(cf)
    gams_path = config["optimiser"]["gams"]

    ws = GamsWorkspace(system_directory=gams_path)
    db = ws.add_database()
    export_gdx(db, config["optimiser"])
    run_gams(ws)
    import_gdx("output.gdx")


if __name__ == "__main__":
    main()

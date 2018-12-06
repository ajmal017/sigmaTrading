"""
Code for margin calculation, estimation and fitting.

Author: Peeter Meos
Date: 6. December 2018
"""
import pandas as pd
import numpy as np
from sklearn.neural_network import MLPRegressor
from sklearn.externals import joblib
import boto3
import json
import decimal
from boto3.dynamodb.conditions import Key
from quant import scaling


# Helper class to convert a DynamoDB item to JSON.
class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, decimal.Decimal):
            return str(o)
        return super(DecimalEncoder, self).default(o)


def train_model():
    """
    Trains neural net to estimate margins
    :return:
    """
    """
    p <- ggplot2::ggplot(data = df, aes(x = Mny, y = marginLong, col = side)) +
      ggplot2::ggtitle("Long side") +
      ggplot2::geom_point()
    print(p)
    p <- ggplot2::ggplot(data = df, aes(x = Mny, y = marginShort, col = side)) +
      ggplot2::ggtitle("Short side") +
      ggplot2::geom_point()
    print(p)
  
    #plot(nnet.LI, rep = 'best')
  
    plot(x = df$SI.Scaled, y = nnet.SI$net.result[[1]], main = "Short side model accuracy")
    plot(x = df$LI.Scaled, y = nnet.LI$net.result[[1]], main = "Long side model accuracy")
    #nnet.out <- compute(nnet.LI, df[, c("Mny", "Days.scaled")])$net.result
  
    """
    # Get the data
    inst = "CL"
    dynamodb = boto3.resource('dynamodb', region_name='us-east-1',
                              endpoint_url="https://dynamodb.us-east-1.amazonaws.com")
    table = dynamodb.Table("margin")
    j = table.query(KeyConditionExpression=Key("inst").eq(inst))
    df = json.dumps(j["Items"][1]["data"], cls=DecimalEncoder)
    df = pd.read_json(df, orient="records")

    # Some data handling and conversion
    df = df[df["days"] < 1000]
    df["num_side"] = np.where(df["side"] == "P", -1, 1)

    df["Mny"] = df["num_side"] * np.log(df["ulPrice"] / df["strike"])
    df["Diff"] = df["num_side"] * (df["strike"] - df["ulPrice"])

    # Scaling
    df["Days scaled"] = df["days"] / 365
    df["SI Scaled"] = scaling.scale11(df["marginShort"])
    df["LI Scaled"] = scaling.scale11(df["marginLong"])

    # Now train two neural nets.
    #nnet_si = MLPRegressor()
    #nnet_li = MLPRegressor()
    """
    nnet.SI <- neuralnet::neuralnet(SI.Scaled ~ Mny + Days.scaled + delta, data = df, hidden = c(10,10), 
                                  act.fct = "tanh")
    nnet.LI <- neuralnet::neuralnet(LI.Scaled ~ Mny + Days.scaled + delta, data = df, hidden = c(10,10), 
                                  act.fct = "tanh")
    """

    # And some optional plotting of results

    # Save the models to files and S3
    # Or perhaps with pickle?
    """
    fit.data <- df
    limits <- list(short.min = min(df$marginShort),
                 short.max = max(df$marginShort),
                 long.min = min(df$marginLong),
                 long.max = max(df$marginLong))
    #save(nnet.LI, nnet.SI, limits, file = "./data/fit.RData")
    aws.s3::s3save(nnet.LI, nnet.SI, limits, object = "fit.RData", bucket = "sigma.bucket")
    """
    #joblib.dump(nnet_si, "file.name")
    #joblib.dump(nnet_li, "file.name")
    #s3 = boto3.resource('s3')
    #o = s3.Object('my_bucket_name', 'my/key/including/filename.txt')
    #o.put(Body=nnet_li)

    #return nnet_li, nnet_si


def add_margins(df: pd.DataFrame):
    """
    Adds margins to a price data frame
    :param df:
    :return:
    """
    """
    load("./data/fit.RData")
    #aws.s3::s3load("fit.RData", bucket = "sigma.bucket")
  
    df$numSide <- 1
    df$numSide[grepl("PUT", df$Financial.Instrument)] <- -1
    df$Mny <- df$numSide * log(df$Underlying.Price/df$Strike)
    df$Days.scaled <- df$Days.to.Last.Trading.Day / 365
  
    df$Marg.l <- revscale11(compute(nnet.LI, df[, c("Mny", "Days.scaled", "Delta")])$net.result, limits$long.min, limits$long.max)
    df$Marg.s <- revscale11(compute(nnet.SI, df[, c("Mny", "Days.scaled", "Delta")])$net.result, limits$short.min, limits$short.max)
  
    return(df) 
    """
    pass


if __name__ == "__main__":
    """
    In case of running this file we assume that we want to train a new model
    """
    train_model()

"""
Code for margin calculation, estimation and fitting.

Author: Peeter Meos
Date: 6. December 2018
"""
import pandas as pd
import numpy as np
from sklearn.neural_network import MLPRegressor
import boto3
import json
import decimal
from boto3.dynamodb.conditions import Key
from quant import scaling
import matplotlib.pyplot as plt
import pickle


# Helper class to convert a DynamoDB item to JSON.
class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, decimal.Decimal):
            return str(o)
        return super(DecimalEncoder, self).default(o)


def train_model(s3: str, tbl: str):
    """
    Trains neural net to estimate margins
    :param s3: S3 bucket to save the model
    :param tbl: Dynamo DB table for margin data storage
    :return:
    """
    # Get the data
    inst = "CL"
    dynamodb = boto3.resource('dynamodb', region_name='us-east-1',
                              endpoint_url="https://dynamodb.us-east-1.amazonaws.com")
    table = dynamodb.Table(tbl)
    j = table.query(KeyConditionExpression=Key("inst").eq(inst))
    df = json.dumps(j["Items"][0]["data"], cls=DecimalEncoder)
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
    df = df.dropna()

    # Now train two neural nets.
    # We need some matrices
    x_train = df[["Mny", "Days scaled", "delta"]].as_matrix()
    y_train_l = df["LI Scaled"].as_matrix()
    y_train_s = df["SI Scaled"].as_matrix()

    nnet_si = MLPRegressor(hidden_layer_sizes=(10, 10, 10),
                           learning_rate_init=0.01,
                           activation="relu")
    nnet_li = MLPRegressor(hidden_layer_sizes=(10, 10, 10),
                           learning_rate_init=0.01,
                           activation="relu")
    nnet_si.fit(x_train, y_train_s)
    nnet_li.fit(x_train, y_train_l)

    y_pred_l = nnet_li.predict(x_train)
    y_pred_s = nnet_si.predict(x_train)

    # Save the models to files and S3
    limits = {"short_min": min(df["marginShort"]),
              "short_max": max(df["marginShort"]),
              "long_min": min(df["marginLong"]),
              "long_max": max(df["marginLong"])}
    fit = {"limits": limits,
           "long": nnet_si,
           "short": nnet_li}

    b = boto3.resource('s3')
    o = b.Object(s3, 'fit.data')
    o.put(Body=pickle.dumps(fit))

    return y_train_l, y_pred_l, y_train_s, y_pred_s


def add_margins(df: pd.DataFrame, s3: str):
    """
    Adds margins to a price data frame
    :param df: Data frame to be processed
    :param s3: S3 bucket for model storage
    :return:
    """

    # Load data
    # TODO: Check if the object in S3 exists
    b = boto3.resource('s3')
    o = b.Object(s3, 'fit.data')
    fit = pickle.loads(o.get()["Body"].read())

    # Prepare data frame
    df['num_side'] = np.where(df['Financial Instrument'].str.contains("PUT"), -1, 1)
    df["Mny"] = df["num_side"] * np.log(df["Underlying Price"] / df["Strike"])
    df["Days scaled"] = df["Days to Last Trading Day"] / 365

    # Compute margins
    x_pred = df[["Mny", "Days scaled", "Delta"]].as_matrix()
    df["Marg l"] = scaling.rev_scale11(fit["long"].predict(x_pred),
                                       fit["limits"]["long_min"],
                                       fit["limits"]["long_max"])
    df["Marg s"] = scaling.rev_scale11(fit["short"].predict(x_pred),
                                       fit["limits"]["short_min"],
                                       fit["limits"]["short_max"])


if __name__ == "__main__":
    """
    In case of running this file we assume that we want to train a new model
    """
    y_t_l, y_p_l, y_t_s, y_p_s = train_model("fit.data", "margin")
    plt.scatter(y_t_s, y_p_s)

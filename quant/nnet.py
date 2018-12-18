"""
Neural net model for various applications

Author: Peeter Meos
Date: 18. December 2018
"""
import pandas as pd
from sklearn.neural_network import MLPRegressor


def fit_iv(df: pd.DataFrame):
    """
    Interpolates implied volatilities and fills missing values from market snapshot
    We take strike and time as input values and predict IV
    :param df:
    :return:
    """
    df_tmp = df[["Underlying Price", "Strike", "Days", "Vol"]].copy()
    df_tmp["Mny"] = df_tmp["Strike"] / df_tmp["Underlying Price"]

    df_train = df_tmp[df_tmp["Vol"].notnull()]
    x_train = df_train[["Mny", "Days"]].as_matrix()
    y_train = df_train["Vol"].as_matrix()

    model = MLPRegressor(hidden_layer_sizes=(80, 90, 80, 50),
                         learning_rate_init=0.01,
                         learning_rate="adaptive",
                         activation="relu",
                         max_iter=5000)

    model.fit(x_train, y_train)

    df_test = df_tmp[df_tmp["Vol"].isnull()]
    x_test = df_test[["Mny", "Days"]].as_matrix()
    y_pred = model.predict(x_test)

    df.loc[df["Vol"].isnull(), "Vol"] = list(y_pred)

    return df

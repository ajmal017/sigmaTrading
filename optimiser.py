"""
Portfolio optimisation code ported mostly from R

Author: Peeter Meos, Sigma Research OÜ
Date: 2. December 2018
"""
from gams import *
import configparser
import pandas as pd


def export_gdx(db: GamsDatabase):
    """
    Composes dataset for optimisation and exports it as GDX
    Two options - whether we get it from a CSV or from DynamoDB
    :return:
    """
    df = pd.read_csv("data/181105 options.csv")
    print(df.describe())
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
    export_gdx(db)
    run_gams(ws)
    import_gdx("output.gdx")


if __name__ == "__main__":
    main()

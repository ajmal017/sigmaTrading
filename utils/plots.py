"""
Plotting functionality based on Bokeh

Author: Peeter Meos
Date: 4. January 2019
"""


def plot_greeks(df_greeks, df_greeks_before=None):
    """
    Plot greeks
    :param df_greeks:
    :param df_greeks_before:
    :return:
    """
    from bokeh.plotting import figure, show
    from bokeh.layouts import gridplot

    p1 = figure(title="Delta", width=250, height=250)
    p1.line(df_greeks.index, df_greeks["Delta"], line_color="red", legend="Optimal")
    if df_greeks_before is not None:
        p1.line(df_greeks.index, df_greeks_before["Delta"], line_color="black", legend="Current")

    p2 = figure(title="Gamma", width=250, height=250)
    p2.line(df_greeks.index, df_greeks["Gamma"], line_color="red", legend="Optimal")
    if df_greeks_before is not None:
        p2.line(df_greeks.index, df_greeks_before["Gamma"], line_color="black", legend="Current")

    p3 = figure(title="Theta", width=250, height=250)
    p3.line(df_greeks.index, df_greeks["Theta"], line_color="red", legend="Optimal")
    if df_greeks_before is not None:
        p3.line(df_greeks.index, df_greeks_before["Theta"], line_color="black", legend="Current`")

    p4 = figure(title="Val", width=750, height=250)
    p4.line(df_greeks.index, df_greeks["Val"], line_color="red", legend="Optimal")
    if df_greeks_before is not None:
        p4.line(df_greeks.index, df_greeks_before["Val"], line_color="black", legend="Current")
    p4.line(df_greeks.index, df_greeks["Val_p1"], line_color="blue", legend="T+1 day")
    p4.line(df_greeks.index, df_greeks["Val_exp"], line_color="blue", line_dash="4 4", legend="Expiry")
    if df_greeks_before is not None:
        p4.line(df_greeks.index, df_greeks_before["Val_exp"], line_color="black", line_dash="4 4",
                legend="Expiry before")

    show(gridplot([[p4], [p1, p2, p3]]))

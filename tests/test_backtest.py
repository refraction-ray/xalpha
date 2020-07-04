import sys

sys.path.insert(0, "../")
import xalpha as xa
import pandas as pd


def test_ScheduledSellonXIRR():
    bt = xa.backtest.ScheduledSellonXIRR(
        start="2018-01-01",
        value=1000,
        code="F110026",
        date_range=pd.date_range("2018-01-01", "2020-07-01", freq="W-FRI"),
    )
    bt.backtest()
    sys = bt.get_current_mul()
    assert sys.totcftable.iloc[-1]["date"].strftime("%Y-%m-%d") == "2020-01-17"
